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

FitFindr takes a plain-language request like "graphic tee under $30, size M"
and pulls out a description, a size and a price ceiling. `search_listings`
filters the thrift listings by size and price and ranks what's left by how many
keywords match. If something matches, the top listing goes to `suggest_outfit`,
which suggests one or two outfits using pieces from the user's wardrobe (or
general styling ideas if the wardrobe is empty), and then `create_fit_card`
writes a short caption with the item's title, price and platform. If nothing
matches, the agent stops before either of those steps and tells the user what
to change: broader words, a different size, or a higher price.

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

**Where it lives:** `agent.py::run_agent`, in the
`if not session["search_results"]:` check. The "nothing found" message is
built in `agent.py::_nothing_found_message`.

**Second branch (extra credit):** after selecting the item, `run_agent` checks
its price with `compare_price`. If it's above typical for its category, it
looks for a cheaper same-category listing in the search results. See
[Extra Credit](#extra-credit).

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
   `wardrobe` was put in the session at the start of the run. (Extra credit:
   with style memory on, an empty `session["wardrobe"]` is replaced by the
   saved one first. See [Extra Credit](#extra-credit).)
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

**One full query** (example wardrobe, `--trace` on so every step is visible)

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] compare_price
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    below typical
[5] branch
      →    price is fine: no alternative needed
[6] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give yo…
      →    10 wardrobe item(s)
[7] create_fit_card
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Channel your inner early-2000s pop star with this Y2K Baby Tee — Butterfly Print, giving you that authentic fi…

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give you that *chef’s kiss* authentic fitted look. 

Here are two super cute ways to style it using pieces you already own:

**Outfit 1: The Ultimate Y2K Contrast**
Pair the baby tee with your **Baggy straight-leg jeans, dark wash** to play with that classic fitted-on-top, baggy-on-bottom silhouette. Throw on the **Chunky white sneakers** and your **Black crossbody bag** to keep it effortlessly cool and casual for everyday wear. 

**Outfit 2: Grunge-meets-Sweet**
Layer the tee under your **Vintage black denim jacket** and pair it with the **Wide-leg khaki trousers** for an earthy, 90s-meets-Y2K vibe. Tie the whole look together by lacing up your **Black combat boots** to add a little bit of edge to the sweet butterfly print! 

Go grab it—you’ll get so much wear out of this one!

  Fit card: Channel your inner early-2000s pop star with this Y2K Baby Tee — Butterfly Print, giving you that authentic fitted silhouette for just $18.00 on Depop. You can easily dress it down with baggy jeans and chunky sneakers for a casual day out, or toughen up the sweet butterfly graphic with wide-leg trousers and black combat boots for an edgy grunge-meets-sweet vibe. Grab this versatile piece before it's gone and get ready to live in it all season long!

0 model calls this session, 2 served from cache
```

**The impossible query** (empty-search branch). The trace stops at step 3,
before `select_item`, `suggest_outfit` and `create_fit_card`:

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

  Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.

0 model calls this session
```

The same query through `run_agent`, printing the session fields afterwards:

```
$ python -c "
from agent import run_agent; from utils.data_loader import get_example_wardrobe
s = run_agent('designer ballgown size XXS under \$5', get_example_wardrobe())
for k in ('search_results','selected_item','outfit_suggestion','fit_card','error'): print(f'{k}: {s[k]!r}')
"
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit
search_results: []
selected_item: None
outfit_suggestion: None
fit_card: None
error: "Nothing in the listings matched description 'designer ballgown', size XXS, under $5.\nThings to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5."
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Hey there! I am so excited for you to look at these vintage Levi's 501s—they are an absolute thrift store holy grail and fill a great gap since your other jeans are baggy dark wash! Here are two super easy, effortless ways to style them using what’s already in your closet:

**Outfit 1: The Off-Duty Casual Look**
Tuck your **White ribbed tank top** into the Levi's, thread through the **Brown leather belt**, and layer your **Oversized grey crewneck sweatshirt** right over top (or drape it casually over your shoulders). Slip into your **Chunky white sneakers** and grab the **Black crossbody bag** for an effortlessly cool, everyday streetwear vibe that lets the classic medium wash shine.

**Outfit 2: The Edgy Denim-on-Denim Vibe**
Pair the 501s with your **Black cropped zip hoodie**, and layer the **Vintage black denim jacket** on top for a cool mix of black and blue denim. Lace up your **Black combat boots** to ground the look, and you've got an instant, grunge-leaning outfit that takes zero effort to pull together. 

Go grab those jeans—they're totally worth it!
```

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('white tank top with sneakers', load_listings()[0]))"
Nothing beats a broken-in pair of Vintage Levi's 501 Jeans — Medium Wash for that effortless, off-duty model look. I kept it super casual by styling them with a crisp white tank top and my favorite sneakers for the ultimate laid-back weekend fit. Grab them over on Depop right now for just $38.00 before someone else snags them!
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I asked Claude to implement `search_listings()` from the
  existing contract in `tools.py`, using `load_listings()` and my own
  stopword and size helpers.
- *What came back:* An implementation that filters by price and size, scores
  by keyword overlap and caps results at `SEARCH_RESULT_LIMIT`. It also pointed
  out two bugs in my helpers: `re` was never imported, and `_size_tokens` used
  `.upper` without the `()`.
- *What I changed:* I tested it from the terminal with a normal search
  (`'graphic tee', max_price=30`), with a size filter (`size='L'`) and with a
  nonsense query to check that the empty case returns `[]`.

**Moment 2**

- *What I asked for:* I asked Claude to wire the Unit 3 loop in `run_agent()`
  so that every tool reads its input back out of the session, while keeping
  the professor's Unit 4 MCP code (`_search()`).
- *What came back:* Its first pass treated the older stub in my last commit as
  the professor's original and restored docstring text from it, which wasn't
  in the version my professor gave me.
- *What I changed:* I gave it the professor's original `agent.py` and asked
  for the replaced lines (`results = _search(parsed)` and the lines that used
  `results`) to be kept as comments next to the Unit 3 code instead of
  deleted. I then asked Claude to run a matching query and an impossible
  query, and checked the output: the matching one reached all three tools with
  the same item in `selected_item` and in `suggest_outfit`, and the impossible
  one stopped after the search with `fit_card` still `None`.

---

## Extra Credit

All three optional features are built and tested from the terminal. None of
them change `search_listings`, `create_fit_card`, the empty-search branch, or
which item is selected.

**1. Fourth tool: `compare_price(item)`** (`tools.py`). It compares a listing's
price with the median price of the *other* listings in its category, with no
model call. It returns `category`, `price`, `typical_price`, `compared_with`
and a `verdict`: `"above typical"` / `"below typical"` (more than 10% off the
median) or `"about typical"`. If no other listing shares the category, it
returns `typical_price: None` and `"no comparison"` instead of raising. I chose
this because the data has a clear price spread by category (median tops $21,
bottoms $30, outerwear $41, shoes $46).

Called directly, on an above-typical item (lst_022) and a below-typical one (lst_002):

```
$ python -c "from tools import compare_price; from utils.data_loader import load_listings; L = {l['id']: l for l in load_listings()}; print(compare_price(L['lst_022'])); print(compare_price(L['lst_002']))"
{'category': 'outerwear', 'price': 75.0, 'typical_price': 40.0, 'compared_with': 7, 'verdict': 'above typical'}
{'category': 'tops', 'price': 18.0, 'typical_price': 21.5, 'compared_with': 14, 'verdict': 'below typical'}
```

Called by the agent: step `[4] compare_price` in the full trace under
[Sample Run](#sample-run) (`→ below typical`), and in the `'leather jacket'`
trace below (`→ above typical`).

**2. Second branch: price check** (`agent.py::run_agent`, after `select_item`).
`run_agent` calls `compare_price(session["selected_item"])` and stores the
result in `session["price_check"]`.
- **If the verdict is `"above typical"`:** look through the rest of
  `session["search_results"]` for listings in the same category that cost less,
  and put the cheapest one in `session["cheaper_alternative"]`.
- **Otherwise:** no extra step, and `cheaper_alternative` stays `None`.

Either way, `selected_item` is still `search_results[0]` and the run goes on to
`suggest_outfit`. An empty search still stops before this step (see the
impossible query under [Sample Run](#sample-run)).

**Branch taken:** `'leather jacket'` selects the $75 bomber, which is above
typical, so step `[5] branch` finds the $33 Olive Canvas Shacket. (Trace shown;
the outfit and fit card printed after it are left out here. The full output
of this query is in Run 2 of style memory below.)

```
$ python app.py ask 'leather jacket' --trace
[1] parse_query
      in:  leather jacket
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: 7 items: 90s Leather Bomber — Black, 90s Track Jacket — Navy/White Stripe, Denim Jacket — Light Wash, Cropped … +4 more
      →    7 match(es)
[3] select_item
      out: 90s Leather Bomber — Black ($75.0, depop)
[4] compare_price
      in:  90s Leather Bomber — Black ($75.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    above typical
[5] branch
      out: Shacket — Olive Canvas ($33.0, poshmark)
      →    above typical: looked for a cheaper result in the same category
[6] suggest_outfit
      in:  90s Leather Bomber — Black ($75.0, depop)
      out: Hey there! You *need* that leather bomber—it’s an absolute wardrobe MVP. Here are two effortless ways to style…
      →    10 wardrobe item(s)
[7] create_fit_card
      in:  90s Leather Bomber — Black ($75.0, depop)
      out: Every closet needs a true 90s Leather Bomber — Black to nail that perfect model-off-duty grunge or high-low co…
```

**Branch not taken:** `'vintage graphic tee under $30'` selects the $18 baby
tee, which is below typical, so step `[5]` prints `price is fine: no alternative
needed` (full trace under [Sample Run](#sample-run)). Both sides, read from the
session (the per-step trace lines are filtered out with `grep`):

```
$ python -c "
from agent import run_agent; from utils.data_loader import get_example_wardrobe
for q in ('leather jacket', 'vintage graphic tee under \$30'):
    s = run_agent(q, get_example_wardrobe())
    alt = s['cheaper_alternative']
    print(q, '->', s['selected_item']['title'], s['selected_item']['price'], '|', s['price_check'], '| cheaper_alternative:', alt and (alt['title'], alt['price']))
" 2>&1 | grep -v '^\[\|^      '
leather jacket -> 90s Leather Bomber — Black 75.0 | {'category': 'outerwear', 'price': 75.0, 'typical_price': 40.0, 'compared_with': 7, 'verdict': 'above typical'} | cheaper_alternative: ('Shacket — Olive Canvas', 33.0)
vintage graphic tee under $30 -> Y2K Baby Tee — Butterfly Print 18.0 | {'category': 'tops', 'price': 18.0, 'typical_price': 21.5, 'compared_with': 14, 'verdict': 'below typical'} | cheaper_alternative: None
```

**3. Style memory: the agent remembers a wardrobe between runs**
(`utils/style_memory.py`). It's off by default and turned on with
`AI201_MEMORY=1`, so evaluation runs (including the empty-wardrobe scenario)
aren't affected by earlier runs. When it's on, `run_agent` checks the wardrobe
just before `suggest_outfit`:
- **Wardrobe has items:** save it to `style_memory.json` in the project root.
- **Wardrobe is empty:** load the saved wardrobe into `session["wardrobe"]`
  and set `session["wardrobe_from_memory"]` to `True`. If nothing is saved
  yet, the run carries on with the empty wardrobe as before.

`suggest_outfit` is unchanged and still takes `(new_item, wardrobe)`. It just
receives the remembered wardrobe. The file is gitignored; delete it to forget.

Two separate processes, starting with no `style_memory.json`.

**Run 1:** memory on, example wardrobe. Step `[6] save wardrobe` saves it.
(The `in:`/`out:` trace lines are filtered out with `grep` to keep this short.)

```
$ AI201_MEMORY=1 python app.py ask 'vintage graphic tee under $30' --trace 2>&1 | grep -v '^      in:\|^      out:'
[1] parse_query
[2] search_listings
      →    10 match(es)
[3] select_item
[4] compare_price
      →    below typical
[5] branch
      →    price is fine: no alternative needed
[6] save wardrobe
      →    10 item(s) remembered
[7] suggest_outfit
      →    10 wardrobe item(s)
[8] create_fit_card

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give you that *chef’s kiss* authentic fitted look. 

Here are two super cute ways to style it using pieces you already own:

**Outfit 1: The Ultimate Y2K Contrast**
Pair the baby tee with your **Baggy straight-leg jeans, dark wash** to play with that classic fitted-on-top, baggy-on-bottom silhouette. Throw on the **Chunky white sneakers** and your **Black crossbody bag** to keep it effortlessly cool and casual for everyday wear. 

**Outfit 2: Grunge-meets-Sweet**
Layer the tee under your **Vintage black denim jacket** and pair it with the **Wide-leg khaki trousers** for an earthy, 90s-meets-Y2K vibe. Tie the whole look together by lacing up your **Black combat boots** to add a little bit of edge to the sweet butterfly print! 

Go grab it—you’ll get so much wear out of this one!

  Fit card: Channel your inner early-2000s pop star with this Y2K Baby Tee — Butterfly Print, giving you that authentic fitted silhouette for just $18.00 on Depop. You can easily dress it down with baggy jeans and chunky sneakers for a casual day out, or toughen up the sweet butterfly graphic with wide-leg trousers and black combat boots for an edgy grunge-meets-sweet vibe. Grab this versatile piece before it's gone and get ready to live in it all season long!

0 model calls this session, 2 served from cache
```

What was saved:

```
$ python -c "import json; w=json.load(open('style_memory.json'))['wardrobe']; print(len(w['items']), 'items saved:'); [print(' ', i['id'], i['name']) for i in w['items']]"
10 items saved:
  w_001 Baggy straight-leg jeans, dark wash
  w_002 Wide-leg khaki trousers
  w_003 White ribbed tank top
  w_004 Oversized grey crewneck sweatshirt
  w_005 Black cropped zip hoodie
  w_006 Vintage black denim jacket
  w_007 Chunky white sneakers
  w_008 Black combat boots
  w_009 Brown leather belt
  w_010 Black crossbody bag
```

**Run 2:** a new process, memory on, an **empty** wardrobe, and the cache off
so the outfit is newly generated. Step `[6] load wardrobe` loads the 10 saved
items, and the outfit names saved pieces (white ribbed tank top, baggy
straight-leg jeans, black combat boots, black cropped zip hoodie, wide-leg khaki
trousers, chunky white sneakers):

```
$ AI201_MEMORY=1 AI201_CACHE=0 python app.py ask 'leather jacket' --empty-wardrobe --trace
(running with an empty wardrobe)
[1] parse_query
      in:  leather jacket
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: 7 items: 90s Leather Bomber — Black, 90s Track Jacket — Navy/White Stripe, Denim Jacket — Light Wash, Cropped … +4 more
      →    7 match(es)
[3] select_item
      out: 90s Leather Bomber — Black ($75.0, depop)
[4] compare_price
      in:  90s Leather Bomber — Black ($75.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    above typical
[5] branch
      out: Shacket — Olive Canvas ($33.0, poshmark)
      →    above typical: looked for a cheaper result in the same category
[6] load wardrobe
      →    10 remembered item(s)
[7] suggest_outfit
      in:  90s Leather Bomber — Black ($75.0, depop)
      out: Hey friend! That 90s leather bomber is an absolute holy grail find—you definitely need to grab it. Here are tw…
      →    10 wardrobe item(s)
[8] create_fit_card
      in:  90s Leather Bomber — Black ($75.0, depop)
      out: I’m still not over finding this 90s Leather Bomber — Black for just $75.00 on Depop. It’s got that perfectly b…

  Found:    90s Leather Bomber — Black — $75.0 on depop

  Outfit:   Hey friend! That 90s leather bomber is an absolute holy grail find—you definitely need to grab it. Here are two effortless ways to style it using pieces you already own:

**Outfit 1: The Ultimate 90s Grunge Look**
Pair the leather bomber with your **white ribbed tank top** tucked into the **baggy straight-leg jeans, dark wash**, and ground the whole vibe with your **black combat boots**. The fitted tank balances out the boxy jacket, and the boots tie the edgy 90s aesthetic together seamlessly. 

**Outfit 2: High-Low Streetwear**
Throw the bomber over your **black cropped zip hoodie** and pair them with your **wide-leg khaki trousers** and **chunky white sneakers**. Mixing the tailored khaki trousers with the sporty hoodie and tough leather jacket creates that cool, effortlessly thrown-together look.

  Fit card: I’m still not over finding this 90s Leather Bomber — Black for just $75.00 on Depop. It’s got that perfectly broken-in leather and boxy fit that makes throwing together a 90s grunge or high-low streetwear look ridiculously easy. Run, don't walk, to grab this holy grail before I keep it for myself!

2 model calls this session, 774 prompt + 263 output tokens
```

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
