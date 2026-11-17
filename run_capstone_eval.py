#!/usr/bin/env python3
"""
Capstone evaluation: runs the five criteria in criteria.md against a real
serve.py over HTTP, three separate trials, and writes the evidence.

    python run_capstone_eval.py --label before
    python run_capstone_eval.py --label after

Each trial starts its own fresh server processes (one with your real key, one
with an invalid key for C3), so trials share nothing but the log file. Nothing
in the code changes between trials. The cache is off for every request.

Writes:
    results/capstone_<label>.md          the run log table + per-request detail
    results/capstone_<label>.json        every raw response and log record

Order inside a trial is deliberate: C5 (the timed one) goes first, so the
model-call pacing in generate.py has a fresh minute when C5 is measured.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "logs" / "runs.jsonl"
RESULTS = ROOT / "results"
PORT = 8010
BASE = f"http://localhost:{PORT}"

MATCHING = ["vintage graphic tee under $30", "denim jacket", "black boots under $60",
            "floral summer dress", "oversized hoodie size L"]
NO_MATCH = ["designer ballgown size XXS under $5", "silk tuxedo under $3", "wedding veil",
            "astronaut helmet", "ski boots under $2"]
MALFORMED = [("{}", "{}"), ('{"query": ""}', '{"query": ""}'),
             ('{"query": 123}', '{"query": 123}'), ('["a"]', '["a"]'),
             ("not json", "not json")]

TARGETS = {
    "C1": ("5 of 5", lambda passed, n: passed == n),
    "C2": ("10 of 10", lambda passed, n: passed == n),
    "C3": ("3 of 3", lambda passed, n: passed == n),
    "C4": ("5 of 5", lambda passed, n: passed == n),
    "C5": ("4 of 5", lambda passed, n: passed >= 4),
}
TITLES = {
    "C1": "Malformed requests get a 400, not a crash",
    "C2": "Every request leaves exactly one matching log line",
    "C3": "A model failure is reported with its stage, not a crash",
    "C4": "\"Nothing matched\" is not logged as success or error",
    "C5": "Normal queries work and come back in under 10 s",
}


# ── talking to the server ─────────────────────────────────────────────────────

def post(raw_body: str) -> dict:
    req = urllib.request.Request(f"{BASE}/ask", data=raw_body.encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            code, ctype, text = resp.status, resp.headers.get("Content-Type", ""), resp.read().decode()
    except urllib.error.HTTPError as err:
        code, ctype, text = err.code, err.headers.get("Content-Type", ""), err.read().decode()
    wall_ms = round((time.perf_counter() - started) * 1000)
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        body = None
    return {"sent": raw_body, "http": code, "content_type": ctype, "json": body,
            "raw": None if body is not None else text[:300], "client_ms": wall_ms}


def ask(query: str) -> dict:
    return post(json.dumps({"query": query}))


def start_server(env_overrides: dict) -> subprocess.Popen:
    env = {**os.environ, "PORT": str(PORT), "AI201_CACHE": "0", **env_overrides}
    proc = subprocess.Popen([sys.executable, "serve.py"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=1)
            return proc
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("serve.py did not come up on port %d" % PORT)


def stop_server(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def log_records() -> dict:
    """request_id -> list of log records with that id."""
    by_id: dict = {}
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                by_id.setdefault(rec.get("request_id"), []).append(rec)
    return by_id


def rid(r: dict):
    return (r["json"] or {}).get("request_id")


def one_log(r: dict, logs: dict):
    found = logs.get(rid(r)) or []
    return found[0] if len(found) == 1 else None


# ── the five checks, exactly as criteria.md words them ───────────────────────

def check_c1(responses, logs):
    out = []
    for r in responses:
        j = r["json"] or {}
        ok = (r["http"] == 400 and "application/json" in r["content_type"]
              and j.get("error_type") == "validation_error")
        out.append((ok, f"HTTP {r['http']}, error_type={j.get('error_type')!r}"))
    return out


def check_c2(responses, logs):
    out = []
    for r in responses:
        found = logs.get(rid(r)) or []
        rec = found[0] if found else {}
        ok = (rid(r) is not None and len(found) == 1
              and "status" in rec and isinstance(rec.get("duration_ms"), int))
        out.append((ok, f"request_id={rid(r)}, log lines={len(found)}, "
                        f"status={rec.get('status')!r}, duration_ms={rec.get('duration_ms')}"))
    return out


def check_c3(responses, logs):
    out = []
    for r in responses:
        j = r["json"] or {}
        rec = one_log(r, logs) or {}
        ok = (r["http"] == 502 and j.get("error_type") == "model_error"
              and j.get("stage") == "suggest_outfit" and len(j.get("search_results") or []) > 0
              and rec.get("status") == "error")
        out.append((ok, f"HTTP {r['http']}, error_type={j.get('error_type')!r}, "
                        f"stage={j.get('stage')!r}, search_results={len(j.get('search_results') or [])}, "
                        f"log status={rec.get('status')!r}"))
    return out


def check_c4(responses, logs):
    out = []
    for r in responses:
        j = r["json"] or {}
        rec = one_log(r, logs) or {}
        ok = (r["http"] == 200 and j.get("error_type") == "no_results"
              and rec.get("status") == "no_results" and rec.get("model_calls") == 0)
        out.append((ok, f"HTTP {r['http']}, error_type={j.get('error_type')!r}, "
                        f"log status={rec.get('status')!r}, model_calls={rec.get('model_calls')}"))
    return out


def check_c5(responses, logs):
    out = []
    for r in responses:
        j = r["json"] or {}
        rec = one_log(r, logs) or {}
        dur = rec.get("duration_ms")
        ok = (r["http"] == 200 and bool(j.get("fit_card")) and j.get("error_type") is None
              and j.get("stage") == "done" and isinstance(dur, int) and dur < 10000)
        out.append((ok, f"HTTP {r['http']}, stage={j.get('stage')!r}, "
                        f"fit_card={'yes' if j.get('fit_card') else 'no'}, duration_ms={dur}, "
                        f"model_calls={rec.get('model_calls')}"))
    return out


CHECKS = {"C1": check_c1, "C2": check_c2, "C3": check_c3, "C4": check_c4, "C5": check_c5}


def run_trial(n: int) -> dict:
    print(f"\n── trial {n} ──", flush=True)
    sent = {}
    proc = start_server({})
    try:
        print("  C5: 5 matching queries (timed)", flush=True)
        sent["C5"] = [ask(q) for q in MATCHING]
        print("  C1: 5 malformed requests", flush=True)
        sent["C1"] = [post(raw) for raw, _ in MALFORMED]
        print("  C4: 5 no-match queries", flush=True)
        sent["C4"] = [ask(q) for q in NO_MATCH]
        print("  C2: 5 matching + 5 malformed", flush=True)
        sent["C2"] = [ask(q) for q in MATCHING] + [post(raw) for raw, _ in MALFORMED]
    finally:
        stop_server(proc)

    proc = start_server({"GEMINI_API_KEY": "invalid-key-for-capstone-c3"})
    try:
        print("  C3: 3 matching queries, invalid key", flush=True)
        sent["C3"] = [ask(q) for q in MATCHING[:3]]
    finally:
        stop_server(proc)

    logs = log_records()
    trial = {"trial": n, "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "criteria": {}}
    for c in ["C1", "C2", "C3", "C4", "C5"]:
        checks = CHECKS[c](sent[c], logs)
        passed = sum(ok for ok, _ in checks)
        trial["criteria"][c] = {
            "passed": passed, "n": len(checks),
            "items": [{"ok": ok, "detail": d, "response": r,
                       "log": (logs.get(rid(r)) or [None])[0]}
                      for (ok, d), r in zip(checks, sent[c])],
        }
        print(f"  {c}: {passed}/{len(checks)}", flush=True)
    return trial


def write_report(label: str, trials: list) -> None:
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"capstone_{label}.json").write_text(
        json.dumps(trials, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"# Capstone run log - {label}", "",
             f"Generated by `run_capstone_eval.py --label {label}` against `serve.py` "
             f"on port {PORT}, cache off. Each trial started fresh server processes.", "",
             "| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |",
             "|---|---|---|---|---|---|"]
    for c in ["C1", "C2", "C3", "C4", "C5"]:
        target, rule = TARGETS[c]
        cells = [f"{t['criteria'][c]['passed']}/{t['criteria'][c]['n']}" for t in trials]
        met = all(rule(t["criteria"][c]["passed"], t["criteria"][c]["n"]) for t in trials)
        lines.append(f"| {c[1]}. {TITLES[c]} | {target} | " + " | ".join(cells)
                     + f" | {'MET' if met else 'MISSED'} |")
    lines.append("")
    for t in trials:
        lines += [f"## Trial {t['trial']} (finished {t['finished']})", ""]
        for c in ["C1", "C2", "C3", "C4", "C5"]:
            crit = t["criteria"][c]
            lines.append(f"**{c}: {crit['passed']}/{crit['n']}**")
            lines.append("")
            for item in crit["items"]:
                lines.append(f"- {'PASS' if item['ok'] else 'FAIL'} `{item['response']['sent']}` "
                             f"- {item['detail']}")
            lines.append("")
    (RESULTS / f"capstone_{label}.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--cooldown", type=int, default=65,
                        help="seconds between trials, so each starts a fresh rate-limit minute")
    args = parser.parse_args()

    trials = []
    for n in range(1, args.trials + 1):
        if n > 1:
            print(f"\n  cooling down {args.cooldown}s before the next trial", flush=True)
            time.sleep(args.cooldown)
        trials.append(run_trial(n))
    write_report(args.label, trials)
    print(f"\nwrote results/capstone_{args.label}.md and .json")


if __name__ == "__main__":
    main()
