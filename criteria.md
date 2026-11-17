# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My search depends on matching words in the listing data, so some reasonable phrasings may not find a match. That is why I chose 4 of 5 instead of 5 of 5.
---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path is controlled by a simple rule in the agent. When the search returns an empty list, it should always stop before calling suggest_outfit, so 5 of 5 is expected.

---

## 3. Something about state

After a successful search, the id of the item given to suggest_outfit matches the id of session["selected_item"] in 5 of 5 tries.


**Why this target:**
The selected item is saved in the session before suggest_outfit runs, so the same item should be passed to the next tool every time. A mismatch would mean the agent changed the item between steps.


---

## 4. The fit card uses the real listing facts

For 5 different listings, including at least 2 where `brand` is `None`, each
fit card is 2–4 sentences, states that listing's exact price and platform, and
never shows the word "None" or names a brand the listing doesn't have — in at
least 4 of 5 cards.

**Why this target:**
The caption comes from the model, so it can sometimes drop the price or make up a brand, and 32 of the 40 listings have no brand at all. I allowed one miss out of 5 because the wording changes every run, but more than one would mean my prompt isn't giving the model the right facts.

---

## 5. An empty wardrobe still gets a full run

Given a matching query and `get_empty_wardrobe()`, the agent finishes with a
non-empty outfit suggestion and a fit card, and the suggestion doesn't name any
item from the example wardrobe (like "Chunky white sneakers") — 5 of 5 tries.

**Why this target:**
An empty wardrobe is a normal case for a new user, and `suggest_outfit` is supposed to fall back to general styling advice instead of returning nothing. Naming a piece the user doesn't own would mean the tool is making things up, so I expect this every time.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Capstone criteria - FitFindr, Shape B (harden against failure)

Written before any capstone results existed. C1-C4 are about the
failure-handling extension; C1 and C3 are bad paths on purpose. C5 checks that
the extension didn't break the normal run.

> These were drafted with AI help (Claude) at my request, based on my unit 3
> criteria and the capstone scope in the README. See How I Used AI under
> `## Capstone` in the README.

**The fixed inputs every trial uses** (so anyone can re-run them):

- Matching queries: `vintage graphic tee under $30`, `denim jacket`,
  `black boots under $60`, `floral summer dress`, `oversized hoodie size L`
- No-match queries: `designer ballgown size XXS under $5`,
  `silk tuxedo under $3`, `wedding veil`, `astronaut helmet`,
  `ski boots under $2`
- Malformed requests: `{}`, `{"query": ""}`, `{"query": 123}`, `["a"]`, and
  the raw body `not json`

## C1. Malformed requests get a 400, not a crash

For the same 5 malformed requests - `{}`, `{"query": ""}`, `{"query": 123}`,
`["a"]` and a body that isn't JSON - `/ask` returns HTTP 400 with a JSON body
whose `error_type` is `validation_error`, and never an HTML page or a 500 - in
5 of 5 requests, every trial.

**Why this target:**
Before the capstone, 2 of these 5 (`{"query": 123}` and `["a"]`) crashed with
Flask's HTML 500 page. Validation is a plain rule that runs before the agent
and never touches the model, so nothing random can make it miss. One miss
would mean a bad request still reaches code that can crash.

---

## C2. Every request leaves exactly one log line that matches it

For a batch of 10 requests (the 5 matching queries and the 5 malformed
requests), every
response's `request_id` appears in exactly one line of `logs/runs.jsonl`, and
that line has a `status` and a `duration_ms` - 10 of 10, every trial.

**Why this target:**
The request_id is only useful if I can always go from a response to its log
line. Before the capstone, the two requests that crashed left no log record at
all, so the failures I most needed to see were the ones that were missing. A
single missing or doubled line means the log can't be trusted, so I expect
every one.

---

## C3. A model failure is reported with its stage, not a crash

With the server started with an invalid but non-empty `GEMINI_API_KEY`, the
first 3 matching queries each return HTTP 502 with `error_type` `model_error`, `stage`
`suggest_outfit`, and the search results still in the response, and each
leaves a log line with `status` `error` - 3 of 3, every trial.

**Why this target:**
The model is the part of FitFindr most likely to fail in real use, and a bad
key fails fast (`generate.py` only retries 5xx and rate limits), so it can be
triggered the same way every time. The search runs before the model, so the
listings found should never be thrown away. Any miss means the failure layer
lost the stage or turned a model problem into a crash.

---

## C4. "Nothing matched" is not logged as a success or an error

For the 5 no-match queries, `/ask` returns HTTP 200 with
`error_type` `no_results`, the log line has `status` `no_results` (never `ok`
or `error`) and `model_calls` of 0 - 5 of 5, every trial.

**Why this target:**
Before the capstone these were logged as `"status": "ok"`, which would make
the success rate look better than it is. An empty search is a normal answer,
not a system failure, so it shouldn't be a 5xx either. The branch that stops
before `suggest_outfit` is a fixed rule, so I expect 5 of 5.

---

## C5. Normal queries still work, and come back in under 10 seconds

For the 5 matching queries, with the cache off (`AI201_CACHE=0`), at
least 4 of 5 return HTTP 200 with a fit card, `error_type` null, `stage`
`done`, and a logged `duration_ms` under 10000 - every trial.

**Why this target:**
The extension wraps every run, so it must not break the normal path. A normal
run makes 2 model calls, and `generate.py` paces calls to stay under the free
tier's 15 per minute, so a slow call or a pacing wait can push one run over.
That is why I allow 1 miss in 5 instead of 5 of 5. Past 10 seconds with no
answer, a user would think the app had hung.
