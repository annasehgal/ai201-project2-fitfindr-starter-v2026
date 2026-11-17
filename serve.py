#!/usr/bin/env python3
"""
FitFindr over HTTP. ← UNIT 9

    python serve.py                       run it on your machine
    gunicorn serve:app                    run it the way a host runs it

Everything else in this repo exits after one command. A host has nothing to
keep running, so a command line cannot be deployed. This file is the smallest
thing that can: it starts a web server, waits, and hands each request to the
same `run_agent()` your CLI calls. **No new agent logic lives here.** If your
loop works from `python app.py ask`, it works from here; if it doesn't, fix it
there, not in this file.

Two routes:

    POST /ask       {"query": "vintage graphic tee under $30",
                     "wardrobe": {...}}     ← wardrobe is optional
    GET  /health    is it awake?

`/ask` returns the session dict from `run_agent()` as JSON, unchanged — the
same keys you print from the command line, including `error`. Read
`session["error"]` first, exactly as you do everywhere else.

It runs **one request at a time**, and one route is deliberately slower than a
web server has to be. The reason is worth reading before you deploy: see the
note above `_one_at_a_time` below — it also decides which gunicorn worker you
can use.

Unit 9 follow-along (done): every /ask call appends one JSON record to
logs/runs.jsonl — timestamp, status, query, output or error, and timing.
Capstone: each record also carries a request_id (returned to the caller in the
body and the X-Request-ID header), the stage the run ended at, an error_type,
and the model calls and tokens that request spent, plus how long it waited on
the pacing limiter and on retries, and why each retry happened.
"""

import os
import sys
import json
import threading
import time
import uuid
from datetime import datetime, timezone

# config first, and before anything that talks to the model: it loads your .env
# and fixes the Windows console encoding for every module that imports it.
import config  # noqa: F401

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

import generate
from agent import run_agent
from utils.data_loader import get_example_wardrobe

app = Flask(__name__)

# Unit 9 follow-along: one JSON object per line, appended for every /ask call,
# whether it succeeded, found nothing, was rejected or crashed.
LOG_FILE = config.ROOT / "logs" / "runs.jsonl"


def log_run(**fields):
    """Append one structured record to logs/runs.jsonl and echo it to stdout."""
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "request_id": getattr(g, "request_id", None), **fields}
    started = getattr(g, "started", None)
    if started is not None:
        # Whole request, arrival to log line: what the caller actually waited.
        entry["duration_ms"] = round((time.perf_counter() - started) * 1000)
    line = json.dumps(entry, ensure_ascii=False)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


# ── one request at a time ─────────────────────────────────────────────────────
# Here's why this exists.
#
# A web server will happily run two requests at once. Two things in this repo
# assume otherwise:
#
#   • If you moved a tool onto MCP in unit 4, `mcp_client.call_tool` starts
#     `mcp_server.py` as a separate process over stdio, one per call. Two
#     overlapping requests means two extra Python interpreters, and the free
#     tier you're deploying to has 512 MB for all of it. That is the reason
#     that would still be here even if everything else were perfect.
#   • `generate.py`'s pacing window and its call counter are plain module
#     globals — deliberately, because that file is teaching pacing and quota,
#     not locking. Two threads sharing them means the per-minute limiter is
#     counting something that isn't true.
#
# What the lock covers is exactly the agent run: the part that spawns
# processes and calls the model. Reading the request, rejecting a bad one, and
# turning the answer into JSON all happen outside it — so a request with a
# malformed body comes straight back with a 400 instead of queueing behind
# somebody else's agent.
#
# Serialising the runs costs you nothing here — this is one user asking one
# question — and it keeps the deployed behaviour identical to the CLI's. When
# that stops being an acceptable trade, the fix is a real queue, not a bigger
# lock.
#
# The same constraint decides your start command, and this is the part that
# bites in deployment rather than on your machine. `mcp_client.call_tool`
# wraps `asyncio.run()`, and `asyncio.run()` refuses to start when an event
# loop is already running. An async worker always has one running. So under
# `gunicorn -k gevent` (or `-k eventlet`, or `serve:app` wrapped for an ASGI
# server like uvicorn) EVERY MCP call fails with "asyncio.run() cannot be
# called from a running event loop" — not some of them under load, all of
# them, every time, in a place your laptop never showed you.
#
#     gunicorn serve:app              ← right: the DEFAULT sync worker
#     gunicorn -k gevent serve:app    ← breaks every MCP call you make

_one_at_a_time = threading.Lock()


# ── capstone: one failure layer at the service boundary ──────────────────────
# Every /ask outcome maps to one status code. "Found nothing" is a normal
# answer (200); a tool or model failure is the service's fault (502); anything
# unexpected is ours (500). The caller can tell them apart without parsing
# the error sentence.
_HTTP_STATUS = {
    None: 200,
    "no_results": 200,
    "tool_error": 502,
    "model_error": 502,
    "internal_error": 500,
}

_EXAMPLE = '{"query": "vintage graphic tee under $30"}'


def _validate(payload):
    """
    Check the request body before the agent runs. Returns (query, problem):
    exactly one of them is None.
    """
    if not isinstance(payload, dict):
        return None, f"The request body must be a JSON object, e.g. {_EXAMPLE}"
    if "query" not in payload or payload["query"] is None:
        return None, f"Send JSON with a 'query' field, e.g. {_EXAMPLE}"
    if not isinstance(payload["query"], str):
        return None, (f"'query' must be a string, not "
                      f"{type(payload['query']).__name__}, e.g. {_EXAMPLE}")
    query = payload["query"].strip()
    if not query:
        return None, f"'query' is empty. Say what you're looking for, e.g. {_EXAMPLE}"
    return query, None


@app.errorhandler(Exception)
def _unhandled(exc):
    """
    Last line of defence: anything that escapes a route becomes a JSON 500 with
    a log record, never Flask's HTML error page and never an absent log line.
    """
    if isinstance(exc, HTTPException):
        return exc  # 404, 405 and friends keep their own codes
    log_run(status="error", stage="serve", error_type="internal_error",
            error=f"{type(exc).__name__}: {exc}")
    return jsonify({"error": "Something went wrong inside the server.",
                    "error_type": "internal_error", "stage": "serve",
                    "request_id": g.request_id}), 500


@app.before_request
def _start_request():
    """Give every request an id and a start time before anything else runs."""
    g.request_id = uuid.uuid4().hex[:12]
    g.started = time.perf_counter()


@app.after_request
def _tag_response(response):
    """The id goes back to the caller, so a reported failure maps to a log line."""
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    return response


def _usage_snapshot():
    """Model calls, cache hits, tokens and waiting done so far by this process."""
    tokens = generate.token_counts()
    waits = generate.wait_counts()
    return (generate.call_count(), generate._cache_hits,
            tokens["prompt"], tokens["output"],
            waits["pacing_wait_s"], waits["retry_wait_s"], waits["retry_reasons"])


@app.get("/health")
def health():
    """Is the server awake? A host pings something like this to find out."""
    return jsonify({"status": "ok"})


@app.post("/ask")
def ask():
    """
    Run the agent on one query.

    In:   {"query": "...", "wardrobe": {...}}   wardrobe optional — leave it
                                                out and you get the same
                                                example wardrobe the CLI uses.
    Out:  the session dict from run_agent(), as JSON.
    """
    payload = request.get_json(silent=True)
    query, problem = _validate(payload)
    if problem:
        # 400 rather than a stack trace: the caller can act on this one.
        log_run(status="rejected", stage="validate_request",
                error_type="validation_error", query=_preview(payload), error=problem)
        return jsonify({"error": problem, "error_type": "validation_error",
                        "stage": "validate_request",
                        "request_id": g.request_id}), 400

    wardrobe = payload.get("wardrobe")
    if not isinstance(wardrobe, dict):
        wardrobe = get_example_wardrobe()

    # A queued request should look like a queued request. Without this the
    # second caller just sits there, and "slow" and "waiting its turn" are
    # indistinguishable from the outside — which is how people conclude the
    # deployment is broken when it is behaving exactly as designed.
    #
    # This is NOT the logging you add in the follow-along. It prints nothing
    # on the normal path, carries no timing and counts nothing; it says only
    # that this request had to wait. `locked()` can be a moment out of date,
    # so the note is occasionally missed — which costs nothing, because
    # nothing depends on it.
    if _one_at_a_time.locked():
        print(
            "  [serve] another request is still running. This one is waiting "
            "its turn — serve.py handles one at a time, on purpose.",
            file=sys.stderr,
            flush=True,
        )

    failure = None
    session = None
    with _one_at_a_time:
        # agent_ms is the agent run alone; duration_ms (added in log_run) is
        # the whole request, including any wait for the lock. Snapshot usage inside the lock, so a queued request's counts are
        # never mixed into this one's.
        before = _usage_snapshot()
        started = time.perf_counter()
        try:
            session = run_agent(query, wardrobe)
        except Exception as exc:  # noqa: BLE001 — a 500 with a sentence beats a hang
            failure = f"{type(exc).__name__}: {exc}"
        agent_ms = round((time.perf_counter() - started) * 1000)
        after = _usage_snapshot()
    usage = {
        "agent_ms": agent_ms,
        "model_calls": after[0] - before[0],
        "cache_hits": after[1] - before[1],
        "prompt_tokens": after[2] - before[2],
        "output_tokens": after[3] - before[3],
        # Capstone improvement: why a slow run was slow.
        "pacing_wait_ms": round((after[4] - before[4]) * 1000),
        "retry_wait_ms": round((after[5] - before[5]) * 1000),
        "model_retries": after[6][len(before[6]):],
    }

    # Outside the lock: building a response is not work the next caller should
    # be waiting on.
    if failure is not None:
        # run_agent catches its own failures now, so this should not happen;
        # if it does, it is still a JSON 500 with a log record.
        log_run(status="error", stage="run_agent", error_type="internal_error",
                query=query, error=failure, **usage)
        return jsonify({"error": failure, "error_type": "internal_error",
                        "stage": "run_agent", "request_id": g.request_id}), 500

    error_type = session.get("error_type")
    status = {None: "ok", "no_results": "no_results"}.get(error_type, "error")
    log_run(status=status, stage=session.get("stage"), error_type=error_type,
            query=query, output=session["fit_card"] or session["error"],
            **usage)
    return jsonify({**session, "request_id": g.request_id}), _HTTP_STATUS.get(error_type, 500)


def _preview(payload, limit=200):
    """What came in, short enough for a log line, whatever shape it was."""
    if payload is None:
        raw = request.get_data(as_text=True)
        return raw[:limit] if raw else None
    if isinstance(payload, dict) and isinstance(payload.get("query"), str):
        return payload["query"][:limit]
    return json.dumps(payload, ensure_ascii=False)[:limit]


if __name__ == "__main__":
    # PORT and 0.0.0.0 are not decoration. A host tells you which port to
    # listen on through PORT, and it reaches your process from outside the
    # container — bind 127.0.0.1 and nothing but the container itself can
    # connect, which looks exactly like a broken app from the browser.
    port = int(os.getenv("PORT", "5000"))

    # Never on by default. Flask's debugger executes code typed into a browser,
    # and a deployed app with it on is a stranger's shell. Set AI201_DEBUG=1 in
    # your own terminal when you want the reloader.
    debug = os.getenv("AI201_DEBUG", "0") == "1"

    print(f"\nFitFindr is listening on http://localhost:{port}")
    print("It runs one request at a time — a second one waits for the first.")
    print("Ask it something (single quotes, as always):\n")
    print(
        f"  curl -X POST http://localhost:{port}/ask \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"query\": \"vintage graphic tee under $30\"}}'\n"
    )
    print("Ctrl-C to stop.\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
