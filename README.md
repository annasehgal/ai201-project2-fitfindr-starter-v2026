# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## Milestone 1: Reading the Data and Running the Starter

### Listing fields

`data/listings.json` holds **40 listings**. Each one has these fields (from
`python app.py fields` and `python app.py listings --full -n 6`):

| Field | Type | Example | Notes |
|---|---|---|---|
| `id` | str | `lst_001` | Unique ID |
| `title` | str | `Vintage Levi's 501 Jeans — Medium Wash` | Best text to match a query against |
| `description` | str | `Classic 501s in a perfect medium wash...` | Longer text; mentions fit and flaws |
| `category` | str | `bottoms` | One of tops (15), bottoms (10), outerwear (8), shoes (4), accessories (3) |
| `style_tags` | list[str] | `['vintage', 'classic', 'denim', 'streetwear']` | Good for matching words like "vintage" or "graphic tee" |
| `size` | str | `W30 L30` | **Not standardized**: `M`, `S/M`, `XL (oversized)`, `W28`, `US 8`, `One Size` |
| `condition` | str | `good` | One of excellent, good, fair |
| `price` | float | `38.0` | Ranges $12–$75 |
| `colors` | list[str] | `['blue', 'indigo']` | |
| `brand` | str or **null** | `Levi's` | 32 of 40 listings have `null` here |
| `platform` | str | `depop` | One of depop, thredUp, poshmark |

**What `search_listings` can filter on:** `price` (a number, so `max_price`
is an easy `<=` check), `size` (string matching, but it has to handle `S/M`
matching a request for `M`), and the free-text fields `title`, `description`,
and `style_tags` for the description words.

**Things that could break the tools later:**
- `brand` is usually `null`, so `create_fit_card` can't assume there's a brand.
- Sizes are messy: tops use letters, bottoms use waist sizes, shoes use `US`
  numbers. An exact `==` match on size would miss `S/M` when someone asks for `M`.
- Some descriptions say the size runs different from the tag (e.g. lst_002:
  "Tag says medium but fits like a small").

### Wardrobe shape

From `python app.py fields` and `data/wardrobe_schema.json`, a wardrobe is a
dict with an `items` list. Each item has:

| Field | Type | Example |
|---|---|---|
| `id` | str | `w_001` |
| `name` | str | `Baggy straight-leg jeans, dark wash` |
| `category` | str | `bottoms` (tops, bottoms, outerwear, shoes, accessories) |
| `colors` | list[str] | `['dark blue', 'indigo']` |
| `style_tags` | list[str] | `['denim', 'streetwear', 'baggy']` |
| `notes` | str or null | `High-waisted, sits above the hip` |

**An empty wardrobe** looks like this:

```json
{ "items": [] }
```

`suggest_outfit` has to handle that case — it still gets an item, but there's
nothing to pair it with, so it should suggest general styling instead of crashing.

### Running the starter

```
$ python app.py ask 'vintage graphic tee under $30'
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

  Nothing in the listings matched description 'vintage graphic tee', under $30.
Things to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; raise the price ceiling above $30.

0 model calls this session
```

The starter runs. `search_listings` is still a stub, so it returns `[]` and
the loop stops before `suggest_outfit`, which is expected at this point.

**Three fields from memory:** `price`, `size`, `style_tags`.

---

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches `data/listings.json` for listings whose words
  match the description, keeps only those that fit the size and price filters
  (when given), and returns them best match first.
- **Inputs:**
  - `description` (str): keywords for what the user wants, e.g. `"vintage graphic tee"`.
  - `size` (str or None): size to filter by, case-insensitive; `None` skips the
    size filter. A size matches when it equals one of the listing's
    slash-separated size parts after parentheticals are removed (`"M"` matches
    `"S/M"` and `"M/L"`, but not `"XL"` or `"US 9"`). Listings marked
    `One Size` match any size.
  - `max_price` (float or None): price ceiling, inclusive (`price <= max_price`);
    `None` skips the price filter.
- **Returns:** `list[dict]`: up to `config.SEARCH_RESULT_LIMIT` (10) listing
  dicts, sorted by keyword-overlap score, highest first. Listings that share
  no keywords with `description` are left out. Each dict is a full listing with
  `id` (str), `title` (str), `description` (str), `category` (str),
  `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float),
  `colors` (list[str]), `brand` (str or None, usually None), `platform` (str).
- **When it has nothing:** Returns an empty list `[]`, never `None` and never
  an exception. The planning loop branches on this.

### `suggest_outfit`

- **What it does:** Uses the model to suggest one or two outfits built around
  the new item, using pieces from the user's wardrobe.
- **Inputs:**
  - `new_item` (dict): one listing dict (same fields as above), the item the
    user is considering.
  - `wardrobe` (dict): a wardrobe dict with an `items` key holding a list of
    wardrobe item dicts (`id`, `name`, `category`, `colors`, `style_tags`,
    `notes`). The list may be empty.
- **Returns:** `str`: a non-empty string of outfit suggestions. When the
  wardrobe has items, the suggestions name specific pieces the user already
  owns by their `name`.
- **When it has nothing:** If `wardrobe["items"]` is empty, it still returns a
  non-empty string of general styling advice for the item (what kinds of
  pieces it goes with). It never returns `""` and never raises because the
  wardrobe is empty.

### `create_fit_card`

- **What it does:** Uses the model to write a short social-media caption about
  the find, in the voice of a real post rather than a product description.
- **Inputs:**
  - `outfit` (str): the outfit suggestion string returned by `suggest_outfit`.
  - `new_item` (dict): the listing dict for the item.
- **Returns:** `str`: a caption of 2–4 sentences. It mentions the item, its
  `price`, and its `platform` once each, and is specific about the vibe. It
  does not assume `brand` is set. Because the model runs at temperature 0.9,
  repeated calls on the same input should not give word-for-word identical
  captions (unless the cache in `config.py` is on).
- **When it has nothing:** If `outfit` is empty or only whitespace, it does not
  call the model and does not raise. It returns a descriptive message string
  saying no outfit was given, so no caption could be written.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` that names what was searched for and what the user could
change (broader words, drop or change the size, raise the price ceiling), then
return the session without calling `suggest_outfit` or `create_fit_card`.
Otherwise, take the first result (the best match), store it in
`session["selected_item"]`, and go on to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent` (the `if not results:` check). The
"nothing found" message is built in `agent.py::_nothing_found_message`.

**How the query is parsed:** With regex, in `agent.py::parse_query`. No model
call is made. In order:
1. **Price:** `_PRICE_RE` finds a dollar amount, optionally after "under",
   "below", "less than", "max" or "up to" (e.g. `under $30` → `30.0`). The
   match is cut out of the text.
2. **Size:** `_SIZE_RE` finds `size <X>`, where X is XXS–XXL, `US <n>` or
   `W<n>`. If that finds nothing, `_BARE_SIZE_RE` looks for a bare letter size
   at the end after a comma (e.g. `..., M`). The size is uppercased and cut out
   of the text.
3. **Description:** whatever text is left, with commas and extra spaces cleaned up.

It returns `{"description": str, "size": str or None, "max_price": float or None}`.
Known limit: phrasing the regex doesn't know, like "nothing over thirty
dollars", gives `max_price = None`, so the price ceiling is ignored without
any warning.

**What moves through the session:** `agent.py::new_session` creates one
session dict per run, and `run_agent` fills it in this order:
1. `query`: the raw text the user typed.
2. `parsed`: the `parse_query` output (`description`, `size`, `max_price`).
3. `search_results`: `run_agent` calls
   `search_listings(description, size, max_price)` with the three `parsed`
   values, and the returned list is stored in `session["search_results"]`.
4. `selected_item`: `search_results[0]`. **This is the item that reaches
   `suggest_outfit` on its own, so the user never types it again.**
5. `outfit_suggestion`: the string from
   `suggest_outfit(session["selected_item"], session["wardrobe"])`, where
   `wardrobe` was put in the session at the start of the run.
6. `fit_card`: the string from
   `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.

`error` stays `None` on a full run. On the empty-search branch it holds the
"nothing found" message, and `selected_item`, `outfit_suggestion` and
`fit_card` stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
