# Running FitFindr

Everything about how the starter works and how to use it.

> **Capstone (Path B, local with logs):** the one-command run path, the
> environment it needs, and where the structured log goes are in
> [Capstone — run it from a clean checkout](#capstone--run-it-from-a-clean-checkout-path-b)
> at the end of this file.

---

## Before your first class

Setup happens **before class**. The [environment setup page](../pages/ide_setup)
has the per-operating-system commands and the exact versions.

**Same API key you set up in unit 1.** Nothing new to sign up for. There is one
new package — the MCP SDK, for unit 4 — and it installs with everything else.

From inside this repo after you've forked and cloned it:

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your key into .env
python test.py
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env         # then paste your key into .env
python test.py
```

**You're ready when `python test.py` passes.**

If it doesn't and you've made one honest attempt at the error, post the
**whole** output in the help channel.

> Activate the virtual environment every time you open a new terminal. You
> should see `(.venv)` at the start of your prompt.

---

## Your first five minutes

Start with the data. Your tools will only be as good as your understanding of
what they're reading, and ten minutes here saves an hour of confused debugging.

```bash
python app.py fields                    # what a listing and a wardrobe item hold
python app.py listings --full -n 6      # read six listings all the way through
python app.py examples                  # queries worth trying
python app.py ask 'vintage graphic tee under $30'
```

> **Quote your queries with single quotes**, on every operating system. In
> PowerShell, `"vintage graphic tee under $30"` in double quotes silently
> becomes `vintage graphic tee under ` — PowerShell reads `$30` as a variable
> and substitutes nothing. You get results with no price ceiling and no error
> saying so. Single quotes are literal in PowerShell, bash and zsh alike.

That last one runs the loop. All three tools are stubs, so it will tell you the
loop isn't built yet. **That's the correct starting position** — it runs, and it
does nothing.

---

## Every command

| Command | What it does |
|---|---|
| `python test.py` | Checks your environment. Run it whenever something feels off |
| `python app.py fields` | The fields a listing and a wardrobe item have — **Milestone 1** |
| `python app.py listings` | Browse the data. `--full` for whole records, `-n` for how many |
| `python app.py examples` | Queries worth trying, including one that matches nothing |
| `python app.py ask '...'` | Run the agent on one query — **single quotes** |
| `python app.py ask` | Keep asking until you press Enter on an empty line |
| `python agent.py` | Runs both example paths — one that matches, one that can't |
| `python mcp_server.py` | Starts your MCP server — **unit 4** |
| `python mcp_client.py` | Asks the server what it offers — **unit 4** |
| `python run_eval.py --label before` | Runs every scenario five times and writes the run log — **unit 4** |
| `python serve.py` | Serves the agent over HTTP instead of exiting — **unit 9** |

Useful flags on `ask`:

| Flag | What it does |
|---|---|
| `--trace` | Print the loop step by step, once you've added the trace calls |
| `--empty-wardrobe` | Run as a user with nothing saved — one of unit 4's failure modes |

---

## Which command goes with which milestone

### Unit 3 — the build

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Read the data, run the starter | `app.py fields`, `app.py listings --full`, `app.py ask` |
| 2 | Spec your three tools | README, **Tool Inventory** |
| 3 | Write your acceptance criteria | `criteria.md` |
| 4 | Build the three tools | `tools.py`, tested one at a time from a terminal |
| 5 | Wire the loop and the state | `agent.py::run_agent` |
| 6 | Write it up | README |

### Unit 4 — the test

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Move one tool onto MCP | `mcp_server.py`, then `mcp_client.call_tool` in `run_agent` |
| 2 | Break it on purpose, then trace it | `trace.py`, `app.py ask --trace` |
| 3 | Run your test | `scenarios.py`, then `run_eval.py --label before` |
| 4 | Call each criterion, diagnose the misses | README |
| 5 | Fix one thing and re-run | `run_eval.py --label after` |
| 6 | Say what's still broken | README |

---

## Running it somewhere else — **unit 9**

Everything above exits when the command finishes. A host has nothing to keep
running, so before you can deploy this you need something that stays up.
`serve.py` is that: the same `run_agent()`, behind two HTTP routes.

On your machine:

```bash
python serve.py
curl -X POST http://localhost:5000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query": "vintage graphic tee under $30"}'
```

On a host, the start command is:

```bash
gunicorn serve:app
```

| Thing | What it means |
|---|---|
| `PORT` | The host tells your app which port to listen on by setting this. Both `serve.py` and `gunicorn` read it, and `serve.py` falls back to `5000` on your machine. Don't hard-code a port |
| `POST /ask` | `{"query": "...", "wardrobe": {...}}` — wardrobe optional. Returns the session dict, `error` and all |
| `GET /health` | Says `ok` if the app is awake |
| It answers one request at a time | On purpose. A second request waits for the first to finish, and prints `[serve] another request is still running` while it waits. An MCP tool call starts a whole second Python process, and the free tier's 512 MB has no room for two of those at once — and `generate.py`'s rate-limit counting assumes one caller. The reasoning is written out in `serve.py` |
| `gunicorn serve:app`, exactly | Not `-k gevent`, not `-k eventlet`, not wrapped for uvicorn. `mcp_client.call_tool` uses `asyncio.run()`, which won't start inside a running event loop, so an async worker breaks **every** MCP call — and only once you've deployed it |
| The first request is slow | The free tier puts your app to sleep after about fifteen minutes of nothing. The next request wakes it up and waits for it — around a minute. Not a bug, and worth knowing before you demo it |

`serve.py` ships with **no logging and no timing in it**, on purpose. You add
that yourself in the follow-along, before you deploy — instrumenting first is
the point of the session.

> **Now done** (unit 9 follow-along, extended in the capstone): `serve.py`
> writes one JSON record per request to `logs/runs.jsonl`. On macOS, port
> 5000 is taken by AirPlay Receiver, so the `curl localhost:5000` above gets a
> 403 from macOS rather than FitFindr — start it with `PORT=8000` instead (see
> the capstone section below).

---

## Where everything lives

| File | What it does |
|---|---|
| `config.py` | Every setting worth changing — **TEMPERATURE and the cache are at the top** |
| `tools.py` | Your three tools. **Stubs — you build these** |
| `agent.py` | The planning loop and the session. **Stub — you build this** |
| `generate.py` | The only thing that calls out to a service. Handles pacing and quota |
| `trace.py` | The trace helper, and the loop's stop condition |
| `app.py` | The command line |
| `serve.py` | The same agent over HTTP, for deploying — **unit 9** |
| `mcp_server.py` | Your MCP server — **unit 4, you register the tool** |
| `mcp_client.py` | Calling an MCP tool from your agent. Given to you |
| `scenarios.py` | What your test runs. **You fill this in** |
| `run_eval.py` | Runs the scenarios repeatedly and writes the run log |
| `criteria.md` | Your five acceptance criteria. **You fill this in** |
| `data/` | 40 listings and the wardrobe schema |
| `utils/data_loader.py` | Loading the data. Use this rather than reading the files yourself |
| `results/` | Run logs. **Commit these** — they're your evidence |

---

## The two settings people go looking for

Both are at the top of `config.py`, and the brief points at them by name.

If your fit cards come out **word-for-word identical** every time, it is one of:

- **`CACHE_ENABLED`** — while you build, identical prompts reuse the answer
  already received. That's deliberate; it makes debugging free. `run_eval.py`
  turns it off automatically.
- **`TEMPERATURE`** — at `0.0` the model gives you the same words every time.
  It ships at `0.9`.

---

## About rate limits

**This is the heaviest pair in the course for call volume.** Two of your three
tools call the model, so one agent run is several requests, and a few runs back
to back while debugging can cross the per-minute limit.

`generate.py` handles it:

- **It paces itself** and says when it's waiting. **A pause is the starter
  doing its job, not a bug.**
- **It reuses answers** to prompts already sent, while you build.
- **It stops** if a session makes an unreasonable number of calls, rather than
  draining your day's allowance. For an agent, that usually means a loop isn't
  ending — look for that before raising the number.
- **It counts your calls** and prints the total when you exit.

`config.MAX_ITERATIONS` is the loop's own stop condition. Your loop this unit
is short enough that you may never hit it. Keep it — a missing stop condition
is the most common architectural failure in production agents.

---

## When something goes wrong

| What you see | What it means |
|---|---|
| `The planning loop isn't built yet` | Correct, at the start. That's the TODO in `agent.py` |
| `No GEMINI_API_KEY found` | No `.env`, or the key wasn't pasted in. On Windows check it didn't save as `.env.txt` |
| A message saying the model couldn't be reached | Usually a bad key. This is also **exactly what unit 4 Milestone 2 asks you to trigger on purpose** |
| `[rate limit] ... Waiting 34s` | Working as intended. Leave it |
| `[serve] another request is still running` | Also working as intended. `serve.py` answers one request at a time; yours is queued behind one that's mid-run |
| `QuotaGuard: This session has made 300 requests` | A loop isn't ending. Find it before raising the budget |
| `The loop ran 11 times, past MAX_ITERATIONS` | Same thing, caught earlier |
| `The server doesn't offer a tool called '...'` | Nothing registered in `mcp_server.py` yet, or the name doesn't match |
| MCP returns a string where you expected a list | You're not going through `mcp_client.call_tool`, which unwraps it |
| Fit cards identical every run | `CACHE_ENABLED` or `TEMPERATURE`. See above |
| `--trace` prints nothing | You haven't added `trace.step()` calls yet — unit 4, Milestone 2 |
| `IncompleteFieldDefinitionWarning: Field 'lifespan'` | Harmless noise from the MCP library's dependencies. Not your code, not an error. Ignore it |
| A price ceiling you typed is being ignored | You used double quotes in PowerShell. `$30` vanished. Use single quotes |
| `UnicodeEncodeError: 'charmap' codec can't encode` | Shouldn't happen — `config.py` sets the console to UTF-8. If you see it, you're running a file that doesn't import `config` |

Still stuck after one honest attempt? Post in the help channel with the full
error, what you ran, and what you expected.

---

## A note on committing

At least four new commits in unit 3, at least four more in unit 4. Your commit
history is what shows your criteria existed before your results did.

**Do not delete and recreate this repository.** You submit the same URL both
units.

`results/` is deliberately **not** in `.gitignore`.

---

## Capstone — run it from a clean checkout (Path B)

The capstone runs FitFindr locally behind `serve.py`, with every request
written to a structured log. Tested from a fresh `git clone` into an empty
folder on macOS with Python 3.12.3 (2026-11-17): install took about 16 seconds,
and the first `/ask` returned 200 with a fit card.

### What the environment needs

| Thing | Value |
|---|---|
| Python | 3.11, 3.12 or 3.13 (tested on 3.12.3). **Not 3.14** |
| Dependencies | **`requirements-lock.txt`** — every package pinned to an exact version (`==`), frozen from the tested fresh-clone install; a second fresh install from it reproduced the identical 48 versions and passed all tests. Direct dependencies: Flask 3.1.3, Werkzeug 3.1.9, google-genai 1.75.0, mcp 1.30.0, python-dotenv 1.1.1, gunicorn 23.0.0. `requirements.txt` keeps the course starter's bounded ranges |
| Environment variable | `GEMINI_API_KEY` (required) — put it in `.env`, which git ignores. Never commit it |
| Optional variables | `PORT` (default 5000), `AI201_CACHE=0` to turn off the response cache, `AI201_MODEL` (default `gemini-3.5-flash-lite`) |
| Model files | None. The model is called over the Gemini API; nothing is downloaded |
| Data files | `data/listings.json` (18.6 KB, 40 listings) and `data/wardrobe_schema.json` (3.3 KB), both in the repo |
| Network | Outbound HTTPS to the Gemini API |

### Setup (once)

```bash
git clone <this repo's URL> fitfindr && cd fitfindr
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-lock.txt   # exact versions (or requirements.txt for the ranges)
cp .env.example .env               # then set GEMINI_API_KEY=... in .env
python test.py                     # optional: checks Python, packages, key and one model call
```

### Start it — one command

```bash
PORT=8000 AI201_CACHE=0 python serve.py
```

- `PORT=8000` because on macOS port 5000 belongs to AirPlay Receiver, and a
  request to it gets a 403 from macOS, not from FitFindr. Any free port works.
- `AI201_CACHE=0` makes every request a real model call. Without it, a repeated
  query is answered from `.cache/` with zero model calls, which is fine for
  debugging but makes the logged timings and token counts meaningless.
- It listens on `http://localhost:8000` and runs until Ctrl-C. Windows
  PowerShell: `$env:PORT=8000; $env:AI201_CACHE=0; python serve.py`.

### Send it a request (second terminal)

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"query": "vintage graphic tee under $30"}'
# a bad request, to see the failure path:
curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"query": 123}'
```

| Outcome | HTTP status | `error_type` in the body |
|---|---|---|
| Fit card returned | 200 | `null` |
| Nothing in the listings matched | 200 | `no_results` |
| Malformed or missing input | 400 | `validation_error` |
| The search tool (MCP) or the model failed | 502 | `tool_error` / `model_error` |
| Anything unexpected | 500 | `internal_error` |

Every response carries a `request_id` (also in the `X-Request-ID` header).

### Where the log goes

`logs/runs.jsonl`, created on the first request. One JSON object per line,
appended for every `/ask` call, including rejected and failed ones. Fields:
`timestamp`, `request_id`, `status`, `stage`, `error_type`, `query`, `output`
or `error`, `agent_ms`, `model_calls`, `cache_hits`, `prompt_tokens`,
`output_tokens`, `pacing_wait_ms`, `retry_wait_ms`, `model_retries`,
`duration_ms`. The API key is never logged.

Read it back with:

```bash
tail -n 5 logs/runs.jsonl
grep '"request_id": "<id from the response>"' logs/runs.jsonl
```

### Tests (no API key needed)

```bash
python test_failure_handling.py    # capstone failure layer + wait accounting: 10 tests
python test_search_retry.py        # unit 4 stretch: 10 tests
python test_generate_retry.py      # unit 4 5xx retry: 8 tests
```
