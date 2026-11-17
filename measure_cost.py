#!/usr/bin/env python3
"""
Capstone cost measurement: 10 representative /ask requests against a real
serve.py, cache off, and the per-run cost read back from each request's own
log line (tokens reported by the Gemini API, model calls, and wall-clock time).

    python measure_cost.py

Writes results/capstone_cost.md. Requests are spaced 9 s apart so the
15-calls-per-minute pacing in generate.py doesn't add waiting time to the
measurement (2 calls per run means about 7 runs a minute at most).
"""

import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "logs" / "runs.jsonl"
PORT = 8020
BASE = f"http://localhost:{PORT}"

QUERIES = [
    "vintage graphic tee under $30", "denim jacket", "black boots under $60",
    "floral summer dress", "oversized hoodie size L", "leather jacket",
    "white sneakers", "plaid skirt", "knit sweater", "cargo pants",
]


def main():
    env = {**os.environ, "PORT": str(PORT), "AI201_CACHE": "0"}
    proc = subprocess.Popen([sys.executable, "serve.py"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{BASE}/health", timeout=1)
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        ids = []
        for i, q in enumerate(QUERIES):
            if i:
                time.sleep(9)
            req = urllib.request.Request(f"{BASE}/ask", method="POST",
                                         data=json.dumps({"query": q}).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    body = json.loads(resp.read())
            except urllib.error.HTTPError as err:
                body = json.loads(err.read())
            ids.append(body["request_id"])
            print(f"  {i + 1:2}. {q!r}: {body.get('error_type') or 'ok'}", flush=True)
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    by_id = {}
    for line in LOG.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        by_id[rec.get("request_id")] = rec
    rows = [by_id[i] for i in ids]

    lines = ["# Capstone cost measurement", "",
             "`python measure_cost.py`: 10 requests to `serve.py` (port 8020, cache off), "
             "9 s apart. Every number is read from that request's line in `logs/runs.jsonl`.", "",
             "| # | request_id | query | status | model calls | prompt tokens | output tokens "
             "| total tokens | duration_ms |", "|---|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(rows, 1):
        total = r["prompt_tokens"] + r["output_tokens"]
        lines.append(f"| {n} | {r['request_id']} | {r['query']} | {r['status']} | "
                     f"{r['model_calls']} | {r['prompt_tokens']} | {r['output_tokens']} | "
                     f"{total} | {r['duration_ms']} |")

    def avg(key):
        return statistics.mean(r[key] for r in rows)

    tot = [r["prompt_tokens"] + r["output_tokens"] for r in rows]
    lines += ["", f"- Average model calls per run: {avg('model_calls'):.1f}",
              f"- Average prompt tokens per run: {avg('prompt_tokens'):.1f}",
              f"- Average output tokens per run: {avg('output_tokens'):.1f}",
              f"- Average total tokens per run: {statistics.mean(tot):.1f}",
              f"- Average duration per run: {avg('duration_ms') / 1000:.2f} s "
              f"(min {min(r['duration_ms'] for r in rows) / 1000:.2f}, "
              f"max {max(r['duration_ms'] for r in rows) / 1000:.2f})"]
    out = ROOT / "results" / "capstone_cost.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-5:]))
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
