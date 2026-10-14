# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** - setup, every
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
> **The rest of this file is the submission.**

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to - don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 - THE BUILD ═══════════════════════ -->

## Milestone 1: Reading the Data and Running the Starter

### Listing fields

`data/listings.json` holds **40 listings**. Each one has these fields (from
`python app.py fields` and `python app.py listings --full -n 6`):

| Field | Type | Example | Notes |
|---|---|---|---|
| `id` | str | `lst_001` | Unique ID |
| `title` | str | `Vintage Levi's 501 Jeans - Medium Wash` | Best text to match a query against |
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

`suggest_outfit` has to handle that case - it still gets an item, but there's
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
Things to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; raise the price ceiling above $30.

0 model calls this session
```

The starter runs. `search_listings` is still a stub, so it returns `[]` and
the loop stops before `suggest_outfit`, which is expected at this point.

**Three fields from memory:** `price`, `size`, `style_tags`.

---

## What This Does

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

#### MCP contract: `search_listings`

Derived from `mcp_server.py`, `tools.search_listings`, and `data/listings.json`.
The agent calls it with `call_tool("search_listings", {...})` from `mcp_client.py`.

- **Tool name:** `search_listings` (FastMCP registers the function name).
  Any other name, such as `search_listing`, fails with `MCPError`.
- **Arguments:**
  - `description` (string, **required**): free-text keywords. It is lowercased,
    split into words, and common stopwords plus one-letter words are dropped.
    A listing is returned only if it shares at least one remaining word with its
    `title`, `description`, `category`, `style_tags`, `colors` or `brand`.
    Matching is on exact whole words, with no stemming, so `"tees"` does not match `"tee"`.
    If nothing is left after stopwords are removed (e.g. `"the a"`), the result is `[]`.
  - `size` (string or null, optional, default null): null or `""` turns off the
    size filter. The match is case-insensitive. The listing's size has
    parentheticals removed and is split on `/`, and the request must equal one
    of those parts. So `"M"` matches `"M"`, `"S/M"` and `"M/L"`, but not `"XL"`.
    Listings whose size starts with `One Size` match any request.
    Sizes in the data: `S`, `M`, `L`, `XL`, `S/M`, `M/L`, `L/XL`,
    `US 7`/`8`/`8.5`/`9`, `W27`–`W32`, `W30 L30`, `One Size` variants.
    ⚠️ `"W30"` does not match `"W30 L30"`, and `"US9"` does not match `"US 9"`.
    The tool does not reject unknown sizes. They just match nothing.
  - `max_price` (number or null, optional, default null): price ceiling in the
    listing's `price` units, inclusive (`price <= max_price`). Null turns off the filter.
    ⚠️ The code and data don't name a currency. The `$` comes from user queries
    and from the server docstring, so read it as dollars. Data prices range $12–$75.
- **Returns:** a JSON array of at most `config.SEARCH_RESULT_LIMIT` (10) listing
  objects, sorted by keyword-overlap count, highest first. Ties stay in
  `listings.json` order. They are **not** sorted by price. Each object is the
  listing unchanged: `id` (str), `title` (str), `description` (str), `category`
  (str: tops/bottoms/outerwear/shoes/accessories), `style_tags` (list[str]),
  `size` (str), `condition` (str: excellent/good/fair), `price` (float),
  `colors` (list[str]), `brand` (str or null, null for 32 of 40), `platform` (str).
  Over MCP, `call_tool` returns the same `list[dict]` as calling the function
  directly (checked: same output for `"graphic tee"`, `"M"`, `30`).
- **Empty results:** `[]`, never null and never an error. The agent sets
  `session["error"]` and stops before `suggest_outfit`.
- **Errors:** the tool itself does not raise for bad matches. A wrong tool name,
  a missing `description`, a wrongly typed argument (e.g. `max_price: "cheap"`),
  or a server that won't start makes `call_tool` raise `MCPError`. The message
  is currently a generic "unhandled errors in a TaskGroup" wrapper, not the
  specific cause. `run_agent` does not catch `MCPError`, so it reaches the caller.

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

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` that names what was searched for and what the user could
change (broader words, drop or change the size, raise the price ceiling), then
return the session without calling `suggest_outfit` or `create_fit_card`.
Otherwise, take the first result (the best match), store it in
`session["selected_item"]`, and go on to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`, in the `if not results:` check,
where `results` is what `search_listings` returned (also stored in
`session["search_results"]`). The "nothing found" message is built in
`agent.py::_nothing_found_message`. (In Unit 3 the check read
`if not session["search_results"]:`. Unit 4's MCP move renamed the variable,
not the rule.)

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
3. `search_results`: `run_agent` calls `search_listings` with the three
   `parsed` values, and the returned list is stored in
   `session["search_results"]`. Since Unit 4 Milestone 1 this call goes
   through MCP: `call_tool("search_listings", {"description": ..., "size": ...,
   "max_price": ...})`.
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

Recorded in Unit 3, before the MCP move, so step 2 reads `search_listings`
rather than `search_listings (via MCP)`. The Unit 4 version of the same query
is under [Loop Trace](#loop-trace).

**One full query** (example wardrobe, `--trace` on so every step is visible)

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee - Butterfly Print, Graphic Tee - 2003 Tour Bootleg Style, Vintage Band Tee - Faded Grey … +7 more
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee - Butterfly Print ($18.0, depop)
[4] compare_price
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    below typical
[5] branch
      →    price is fine: no alternative needed
[6] suggest_outfit
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give yo…
      →    10 wardrobe item(s)
[7] create_fit_card
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: Channel your inner early-2000s pop star with this Y2K Baby Tee - Butterfly Print, giving you that authentic fi…

  Found:    Y2K Baby Tee - Butterfly Print - $18.0 on depop

  Outfit:   Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give you that *chef’s kiss* authentic fitted look. 

Here are two super cute ways to style it using pieces you already own:

**Outfit 1: The Ultimate Y2K Contrast**
Pair the baby tee with your **Baggy straight-leg jeans, dark wash** to play with that classic fitted-on-top, baggy-on-bottom silhouette. Throw on the **Chunky white sneakers** and your **Black crossbody bag** to keep it effortlessly cool and casual for everyday wear. 

**Outfit 2: Grunge-meets-Sweet**
Layer the tee under your **Vintage black denim jacket** and pair it with the **Wide-leg khaki trousers** for an earthy, 90s-meets-Y2K vibe. Tie the whole look together by lacing up your **Black combat boots** to add a little bit of edge to the sweet butterfly print! 

Go grab it-you’ll get so much wear out of this one!

  Fit card: Channel your inner early-2000s pop star with this Y2K Baby Tee - Butterfly Print, giving you that authentic fitted silhouette for just $18.00 on Depop. You can easily dress it down with baggy jeans and chunky sneakers for a casual day out, or toughen up the sweet butterfly graphic with wide-leg trousers and black combat boots for an edgy grunge-meets-sweet vibe. Grab this versatile piece before it's gone and get ready to live in it all season long!

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
Things to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.

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
error: "Nothing in the listings matched description 'designer ballgown', size XXS, under $5.\nThings to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5."
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee - Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee - 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top - Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee - Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants - Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie - Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Hey there! I am so excited for you to look at these vintage Levi's 501s-they are an absolute thrift store holy grail and fill a great gap since your other jeans are baggy dark wash! Here are two super easy, effortless ways to style them using what’s already in your closet:

**Outfit 1: The Off-Duty Casual Look**
Tuck your **White ribbed tank top** into the Levi's, thread through the **Brown leather belt**, and layer your **Oversized grey crewneck sweatshirt** right over top (or drape it casually over your shoulders). Slip into your **Chunky white sneakers** and grab the **Black crossbody bag** for an effortlessly cool, everyday streetwear vibe that lets the classic medium wash shine.

**Outfit 2: The Edgy Denim-on-Denim Vibe**
Pair the 501s with your **Black cropped zip hoodie**, and layer the **Vintage black denim jacket** on top for a cool mix of black and blue denim. Lace up your **Black combat boots** to ground the look, and you've got an instant, grunge-leaning outfit that takes zero effort to pull together. 

Go grab those jeans-they're totally worth it!
```

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('white tank top with sneakers', load_listings()[0]))"
Nothing beats a broken-in pair of Vintage Levi's 501 Jeans - Medium Wash for that effortless, off-duty model look. I kept it super casual by styling them with a crisp white tank top and my favorite sneakers for the ultimate laid-back weekend fit. Grab them over on Depop right now for just $38.00 before someone else snags them!
```

---

## How I Used AI

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
      out: 7 items: 90s Leather Bomber - Black, 90s Track Jacket - Navy/White Stripe, Denim Jacket - Light Wash, Cropped … +4 more
      →    7 match(es)
[3] select_item
      out: 90s Leather Bomber - Black ($75.0, depop)
[4] compare_price
      in:  90s Leather Bomber - Black ($75.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    above typical
[5] branch
      out: Shacket - Olive Canvas ($33.0, poshmark)
      →    above typical: looked for a cheaper result in the same category
[6] suggest_outfit
      in:  90s Leather Bomber - Black ($75.0, depop)
      out: Hey there! You *need* that leather bomber-it’s an absolute wardrobe MVP. Here are two effortless ways to style…
      →    10 wardrobe item(s)
[7] create_fit_card
      in:  90s Leather Bomber - Black ($75.0, depop)
      out: Every closet needs a true 90s Leather Bomber - Black to nail that perfect model-off-duty grunge or high-low co…
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
leather jacket -> 90s Leather Bomber - Black 75.0 | {'category': 'outerwear', 'price': 75.0, 'typical_price': 40.0, 'compared_with': 7, 'verdict': 'above typical'} | cheaper_alternative: ('Shacket - Olive Canvas', 33.0)
vintage graphic tee under $30 -> Y2K Baby Tee - Butterfly Print 18.0 | {'category': 'tops', 'price': 18.0, 'typical_price': 21.5, 'compared_with': 14, 'verdict': 'below typical'} | cheaper_alternative: None
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

  Found:    Y2K Baby Tee - Butterfly Print - $18.0 on depop

  Outfit:   Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give you that *chef’s kiss* authentic fitted look. 

Here are two super cute ways to style it using pieces you already own:

**Outfit 1: The Ultimate Y2K Contrast**
Pair the baby tee with your **Baggy straight-leg jeans, dark wash** to play with that classic fitted-on-top, baggy-on-bottom silhouette. Throw on the **Chunky white sneakers** and your **Black crossbody bag** to keep it effortlessly cool and casual for everyday wear. 

**Outfit 2: Grunge-meets-Sweet**
Layer the tee under your **Vintage black denim jacket** and pair it with the **Wide-leg khaki trousers** for an earthy, 90s-meets-Y2K vibe. Tie the whole look together by lacing up your **Black combat boots** to add a little bit of edge to the sweet butterfly print! 

Go grab it-you’ll get so much wear out of this one!

  Fit card: Channel your inner early-2000s pop star with this Y2K Baby Tee - Butterfly Print, giving you that authentic fitted silhouette for just $18.00 on Depop. You can easily dress it down with baggy jeans and chunky sneakers for a casual day out, or toughen up the sweet butterfly graphic with wide-leg trousers and black combat boots for an edgy grunge-meets-sweet vibe. Grab this versatile piece before it's gone and get ready to live in it all season long!

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
      out: 7 items: 90s Leather Bomber - Black, 90s Track Jacket - Navy/White Stripe, Denim Jacket - Light Wash, Cropped … +4 more
      →    7 match(es)
[3] select_item
      out: 90s Leather Bomber - Black ($75.0, depop)
[4] compare_price
      in:  90s Leather Bomber - Black ($75.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    above typical
[5] branch
      out: Shacket - Olive Canvas ($33.0, poshmark)
      →    above typical: looked for a cheaper result in the same category
[6] load wardrobe
      →    10 remembered item(s)
[7] suggest_outfit
      in:  90s Leather Bomber - Black ($75.0, depop)
      out: Hey friend! That 90s leather bomber is an absolute holy grail find-you definitely need to grab it. Here are tw…
      →    10 wardrobe item(s)
[8] create_fit_card
      in:  90s Leather Bomber - Black ($75.0, depop)
      out: I’m still not over finding this 90s Leather Bomber - Black for just $75.00 on Depop. It’s got that perfectly b…

  Found:    90s Leather Bomber - Black - $75.0 on depop

  Outfit:   Hey friend! That 90s leather bomber is an absolute holy grail find-you definitely need to grab it. Here are two effortless ways to style it using pieces you already own:

**Outfit 1: The Ultimate 90s Grunge Look**
Pair the leather bomber with your **white ribbed tank top** tucked into the **baggy straight-leg jeans, dark wash**, and ground the whole vibe with your **black combat boots**. The fitted tank balances out the boxy jacket, and the boots tie the edgy 90s aesthetic together seamlessly. 

**Outfit 2: High-Low Streetwear**
Throw the bomber over your **black cropped zip hoodie** and pair them with your **wide-leg khaki trousers** and **chunky white sneakers**. Mixing the tailored khaki trousers with the sporty hoodie and tough leather jacket creates that cool, effortlessly thrown-together look.

  Fit card: I’m still not over finding this 90s Leather Bomber - Black for just $75.00 on Depop. It’s got that perfectly broken-in leather and boxy fit that makes throwing together a 90s grunge or high-low streetwear look ridiculously easy. Run, don't walk, to grab this holy grail before I keep it for myself!

2 model calls this session, 774 prompt + 263 output tokens
```

<!-- ═══════════════════════ UNIT 4 - THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log - Before

**What this baseline measures.** The 5xx retry in `generate.py` was committed
(`9771322`) before this formal baseline was run. It is the candidate for this
unit's one improvement, so the baseline was run **without** it, so that it can
be compared fairly later. For this run only, `generate.py` was temporarily
replaced with its version from `760370b` (Milestone 1: MCP move done, no 5xx
retry). Every other file was the current code, including the MCP call. After
the run, the committed retry version was restored and checked with
`git diff HEAD -- generate.py` (no difference). The temporary file was never
committed.

**How it was run.** `run_eval.py --label before` (5 tries per scenario, cache
off, temperature 0.9). Raw output: `results/run_2026-10-13_1921_before.md`.
It ran through a small wrapper kept outside the repo. The wrapper called
`run_eval.main()` unchanged, added a pass-through recorder on
`agent.suggest_outfit` to capture the exact `id` it received (criterion 3), and
saved each session for scoring. 25 tries, 30 model calls. All 10 outfit
suggestions and all 8 fit cards produced were different from each other, so the
cache was not reusing answers.

**Evaluation setup added in this milestone** (test harness only, not agent code):
`scenarios.py` now has one scenario per criterion. Criterion 4 needs five
different listings, and a single query always selects the same listing, so that
scenario lists five `queries`. `run_eval.py` runs `queries[k-1]` on try *k*. The
five are `lst_005`, `lst_018`, `lst_028` (brand `None`) and `lst_024`
(Ralph Lauren), `lst_004` (Champion), across depop, thredUp and poshmark.

**Summary** (the run-log format the assignment asks for; details per try below):

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | FAIL | FAIL | MISSED (3/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item id passed to `suggest_outfit` matches `session["selected_item"]` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card uses the real listing facts | 4 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |
| 5. An empty wardrobe still gets a full run | 5 of 5 | FAIL | FAIL | FAIL | PASS | PASS | MISSED (2/5) |

Each table below is one criterion. The quoted criterion is copied from
`criteria.md`.

#### Criterion 1 - A matching query completes all three tools (target: 4 of 5)

> Given a query that matches at least one listing, the agent completes all three
> tool calls and returns a fit card - in at least 4 of 5 tries.

PASS = no early stop, `suggest_outfit` was called, and a non-empty fit card came back.

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `vintage graphic tee under $30` | PASS | 10 results, selected `lst_002` (Y2K Baby Tee, $18, depop). All 7 steps ran, fit card returned (275 chars). |
| 2 | `vintage graphic tee under $30` | PASS | Same item. All 7 steps ran, fit card returned (302 chars). |
| 3 | `vintage graphic tee under $30` | PASS | Same item. All 7 steps ran, fit card returned (336 chars). |
| 4 | `vintage graphic tee under $30` | FAIL | Same item. `503 UNAVAILABLE` during `suggest_outfit`. Stopped with "The model couldn't be reached". No fit card. |
| 5 | `vintage graphic tee under $30` | FAIL | Same item. Outfit suggestion returned, then `503 UNAVAILABLE` during `create_fit_card`. No fit card. |

**Result: 3 of 5 - MISSED** (target 4 of 5).

#### Criterion 2 - An impossible query stops before the second tool (target: 5 of 5)

> Given a query that matches no listings, the agent stops before calling
> `suggest_outfit` and returns a message naming what to change - 5 of 5 tries.

PASS = `session["error"]` set with a "Things to change" message, and `suggest_outfit` never called.

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 2 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 3 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 4 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 5 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |

**Result: 5 of 5 - MET** (target 5 of 5).

#### Criterion 3 - The item passed on matches the item in the session (target: 5 of 5)

> After a successful search, the id of the item given to suggest_outfit matches
> the id of session["selected_item"] in 5 of 5 tries.

PASS = the id recorded going into `suggest_outfit` equals `session["selected_item"]["id"]`.

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `silk slip dress in midi length under $40` | PASS | `selected_item` = `lst_013`, passed to `suggest_outfit` = `lst_013`. The model then hit `503 UNAVAILABLE` inside `suggest_outfit`, after the item was passed. |
| 2 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. The model then hit `503 UNAVAILABLE` inside `suggest_outfit`, after the item was passed. |
| 3 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 307 chars). |
| 4 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 354 chars). |
| 5 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 340 chars). |

**Result: 5 of 5 - MET** (target 5 of 5). Tries 1-2 still pass because this
criterion checks which item was passed, and the right one was passed before the
model failed.

#### Criterion 4 - The fit card uses the real listing facts (target: 4 of 5)

> For 5 different listings, including at least 2 where `brand` is `None`, each
> fit card is 2-4 sentences, states that listing's exact price and platform, and
> never shows the word "None" or names a brand the listing doesn't have - in at
> least 4 of 5 cards.

PASS = a fit card exists, is 2-4 sentences, contains the exact price and
platform, and has no "None" or invented brand. Each try uses a different listing.

| Try | Input (listing) | Result | Evidence |
|---|---|---|---|
| 1 | `corduroy wide-leg pants` (`lst_005`, brand `None`, $32, depop) | FAIL | `503 UNAVAILABLE` during `suggest_outfit`. No fit card. |
| 2 | `vintage linen blazer` (`lst_018`, brand `None`, $38, thredUp) | FAIL | `503 UNAVAILABLE` during `suggest_outfit`. No fit card. |
| 3 | `suede chelsea boots` (`lst_028`, brand `None`, $44, poshmark) | FAIL | `503 UNAVAILABLE` during `suggest_outfit`. No fit card. |
| 4 | `vintage polo shirt` (`lst_024`, Ralph Lauren, $18, thredUp) | FAIL | `503 UNAVAILABLE` during `suggest_outfit`. No fit card. |
| 5 | `90s track jacket` (`lst_004`, Champion, $45, poshmark) | FAIL | Outfit suggestion returned, then `503 UNAVAILABLE` during `create_fit_card`. No fit card. |

**Result: 0 of 5 - MISSED** (target 4 of 5). No try produced a fit card, so the
sentence, price, platform and brand checks were never reached in this baseline.

#### Criterion 5 - An empty wardrobe still gets a full run (target: 5 of 5)

> Given a matching query and `get_empty_wardrobe()`, the agent finishes with a
> non-empty outfit suggestion and a fit card, and the suggestion doesn't name any
> item from the example wardrobe (like "Chunky white sneakers") - 5 of 5 tries.

PASS = non-empty outfit suggestion and fit card, and the suggestion names none
of the 10 example-wardrobe items.

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `denim jacket under $50`, empty wardrobe | FAIL | Selected `lst_007` (Wrangler denim jacket, $42, poshmark). `503 UNAVAILABLE` during `suggest_outfit`. No outfit or fit card. |
| 2 | `denim jacket under $50`, empty wardrobe | FAIL | Same item. `503 UNAVAILABLE` during `suggest_outfit`. No outfit or fit card. |
| 3 | `denim jacket under $50`, empty wardrobe | FAIL | Same item. `503 UNAVAILABLE` during `suggest_outfit`. No outfit or fit card. |
| 4 | `denim jacket under $50`, empty wardrobe | PASS | Outfit suggestion and fit card returned (340 chars). No example-wardrobe item named. |
| 5 | `denim jacket under $50`, empty wardrobe | PASS | Outfit suggestion and fit card returned (306 chars). No example-wardrobe item named. |

**Result: 2 of 5 - MISSED** (target 5 of 5).

**Every FAIL in this run is the same observed error.** All 10 FAIL cells
(criterion 1 tries 4–5, criterion 4 tries 1–5, criterion 5 tries 1–3) stopped
with `503 UNAVAILABLE ... This model is currently experiencing high demand`.
The same error also hit criterion 3 tries 1–2, which still passed (see
above), so 12 of the 25 tries hit it in total. None crashed. The diagnosis
goes in Verdicts and Diagnoses (Milestone 4).

**Real output, one try per criterion**

Criterion 1, try 1. Trace from `agent.py::run_agent` (via `trace.step`),
fit card from `tools.py::create_fit_card`:

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee - Butterfly Print, Graphic Tee - 2003 Tour Bootleg Style, Vintage Band Tee - Faded Grey … +7 more
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee - Butterfly Print ($18.0, depop)
[4] compare_price
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    below typical
[5] branch
      →    price is fine: no alternative needed
[6] suggest_outfit
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: Hey friend! That Y2K butterfly baby tee is an absolute score-fitted graphic baby tees are so much fun and supe…
      →    10 wardrobe item(s)
[7] create_fit_card
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: Just scored the absolute dreamiest Y2K Baby Tee - Butterfly Print for only $18.00 on Depop! I am totally obses…

Fit card: Just scored the absolute dreamiest Y2K Baby Tee - Butterfly Print for only $18.00 on Depop! I am totally obsessed with styling this sweet little graphic tee for an effortless mix of retro streetwear and grunge edge. Grab it now before I change my mind and keep it for myself!
```

Criterion 2, try 1. `session["error"]` from `agent.py::_nothing_found_message`.
The trace stops at `[3] branch → search returned []: stopping before suggest_outfit`:

```
Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.
```

Criterion 3, try 3. Trace from `agent.py::run_agent`. The selected item and the
`suggest_outfit` input are the same listing. Recorded ids: `selected_item` =
`lst_013`, passed to `suggest_outfit` = `lst_013`.

```
[3] select_item
      out: 90s Silk Slip Dress - Floral, Midi Length ($30.0, depop)
...
[6] suggest_outfit
      in:  90s Silk Slip Dress - Floral, Midi Length ($30.0, depop)
      out: Hey there! That 90s floral slip dress is an absolute goldmine-plus, a tiny side-seam snag is totally worth ove…
      →    10 wardrobe item(s)
```

Criterion 4, try 1 (`corduroy wide-leg pants`, `lst_005`). `session["error"]`
from the `ModelUnavailable` handler in `agent.py::run_agent`. No fit card:

```
The model couldn't be reached, so the outfit and caption steps didn't run. The search worked - 5 listing(s) were found. Check GEMINI_API_KEY in your .env, then run the same query again.
What the service said: Couldn't reach the model: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
```

Criterion 5, try 4 (empty wardrobe). Suggestion from `tools.py::suggest_outfit`
(trimmed), fit card from `tools.py::create_fit_card`:

```
Outfit: Hey there! Oh, a cropped Wrangler jacket is an absolute thrift store holy grail-the structure on those vintage shoulders is unmatched!

Here are two super easy ways to style it with things you probably already own:

**1. The Off-Duty Model Look**
Throw this jacket right over a fitted black ribbed tank top and your favorite straight-leg blue jeans ... Add a pair of simple white canvas sneakers and a baseball cap ...
**2. Sweet Meets Street**
... tossing it over a simple black or olive green slip dress. Ground the outfit with chunky black boots or classic canvas sneakers ...

Fit card: Nothing beats the structured shoulders on a vintage Wrangler Denim Jacket - Light Wash, Cropped, which gives off major off-duty model energy when thrown over a simple tank and straight-leg jeans. This versatile piece is a total blank canvas just waiting to be customized for your wardrobe. Snag it now for $42.00 over on my Poshmark closet!
```

**Aborted first attempt (disclosed, not counted).** An earlier start of this
baseline used a scenario layout that would have run 45 tries (five separate
criterion-4 scenarios). I stopped it after 2 tries to switch to the 25-try
layout above. Those 2 tries (criterion 1: one completed, one stopped on a 503)
were run with the same pre-retry `generate.py`. They are not in the table.

---

## Verdicts and Diagnoses

Verdicts are read against the targets in `criteria.md`, using the baseline
above (pre-retry `generate.py` from `760370b`, 5 tries per criterion).

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | **MISSED (3/5)** | Counted tries that called all three tools and returned a fit card: tries 1-3. Tries 4-5 stopped with no fit card. 3 is below 4. |
| 2 | An impossible query stops before the second tool | 5 of 5 | **MET (5/5)** | All 5 tries returned 0 results, stopped at the branch, never called `suggest_outfit`, and returned a "Things to change" message. |
| 3 | Item id passed to `suggest_outfit` matches `session["selected_item"]` | 5 of 5 | **MET (5/5)** | Compared the recorded id going into `suggest_outfit` with `session["selected_item"]["id"]`: `lst_013` = `lst_013` in all 5. The criterion checks the hand-off, not whether the run finished, so tries 1-2 count even though the model failed afterwards. |
| 4 | The fit card uses the real listing facts | 4 of 5 | **MISSED (0/5)** | The criterion is scored on fit cards, and none of the 5 tries produced one. A missing card can't meet "each fit card is 2-4 sentences, states the price and platform...", so each try is a FAIL. |
| 5 | An empty wardrobe still gets a full run | 5 of 5 | **MISSED (2/5)** | Counted tries that returned a non-empty suggestion and a fit card, with no example-wardrobe item named: tries 4-5. Tries 1-3 returned neither. 2 is below 5. |

**Diagnoses**

**The pattern: one problem, not three.** All three misses come from the same
cause. Twelve of the 25 tries hit the same error from the model service,
`503 UNAVAILABLE ... This model is currently experiencing high demand`
(12 `model unavailable` steps and 12 `503 UNAVAILABLE` messages in
`results/run_2026-10-13_1921_before.md`). Those 12 tries became 10 FAIL cells,
not 12, because criterion 3 tries 1-2 hit the error after the step that
criterion checks, so they still passed. No try crashed, and nothing failed for
any other reason.

**Where and how it happens.** The failure is in the tool layer, at the shared
model call that both model-calling tools go through. It isn't in the branch,
the session or the model's text, because no text came back at all.

1. `tools.py::suggest_outfit` (line 221) and `tools.py::create_fit_card`
   (line 291) both call `generate()`.
2. In the baseline `generate.py` (`760370b`), `generate()` catches the error
   and only retries if it looks like a rate limit: `"429"`,
   "resource ... exhaust", or "rate ... limit" (lines 326-330). A 503 matches
   none of these, so on the **first** attempt it goes to
   `if not rate_limited: raise ModelUnavailable(_explain(exc))` (lines 331-332).
   `_explain` falls through to `"Couldn't reach the model: {exc}"` (line 220),
   which is the exact text in every failed try.
3. `agent.py::run_agent` catches `ModelUnavailable` (line 283), sets
   `session["error"]`, records the `model unavailable` trace step and returns.
   The remaining model steps never run, so no fit card is produced.

So a temporary, server-side error ends the run on its first attempt, with no
retry. The error can clear quickly: in Milestone 2's empty-wardrobe run, the
retry version recovered from 503s after waits of 2-5 seconds. The tool code
and prompts were never the problem in these tries. They never got a response
to work with.

**Criterion 1 - MISSED (3/5).** Step and mechanism, per try:
- Try 4: the 503 hit during step `[6] suggest_outfit`, so neither model tool returned anything.
- Try 5: `suggest_outfit` returned an outfit, then the 503 hit during step `[7] create_fit_card`.

Both go through the mechanism above. Tries 1-3 show that when the model
responds, the loop gets through all three tools.

**Criterion 4 - MISSED (0/5), and what this baseline cannot tell us.** All
five tries ended at the same mechanism: tries 1-4 in `suggest_outfit` and try 5
(`lst_004`, Champion) in `create_fit_card` after an outfit came back. The
verdict is a real miss as the criterion is written, because it requires a card.

**What the baseline cannot say:** the checks the criterion is really about (2-4
sentences, exact price, platform, no "None", no invented brand) were **never
reached**. No card for any of the five listings was produced, so this run
contains no evidence either way about whether `create_fit_card` gets listing
facts right. That includes the three no-brand listings (`lst_005`, `lst_018`,
`lst_028`), which are the risky case. Nothing here shows a wrong price, a
missing platform or an invented brand, and I am not claiming one. I'm also not
revising the criterion: it is measurable and measured the right thing. It was
blocked by an upstream failure, not broken.

**Criterion 5 - MISSED (2/5).** Tries 1-3 hit the 503 during step `[6]
suggest_outfit`, on the empty-wardrobe prompt branch (`tools.py` lines 197-204),
before any text came back. The two tries where the model responded (4-5) both
passed: non-empty general advice, a fit card, and none of the 10
example-wardrobe item names. Two passes is a small sample, but nothing in the
run points to a fault in the empty-wardrobe handling itself.

**Criteria that were met**

- **Criterion 2 - MET (5/5).** The empty-search branch (`agent.py::run_agent`,
  `if not results:` at line 189) stopped all 5 tries at step `[3] branch` with
  0 search results, before `suggest_outfit`, and
  `agent.py::_nothing_found_message` named the description, size and price to
  change. This path makes no model calls, so the 503s couldn't affect it. The
  limitation: all 5 tries used the same impossible query.
- **Criterion 3 - MET (5/5).** In every try, the id that went into
  `suggest_outfit` was `lst_013`, the same as `session["selected_item"]["id"]`.
  This was recorded from the call, not inferred from the trace. The hand-off
  happens before any model call (`session["selected_item"] = results[0]` at
  line 203, then `suggest_outfit(session["selected_item"], ...)` at line 262), so
  the 503 in tries 1-2 came after the step the criterion checks. The
  limitation: one query and one listing, so it shows the hand-off is consistent
  across 5 runs, not across different items.

**What this points to for Milestone 5.** All three misses share one step and
one mechanism: no retry on a temporary 503 in `generate()`. That is what the
already-committed 5xx retry (`9771322`) targets, and the after-run will measure
whether it works. A rerun is also the first chance to actually score criterion
4's listing-fact checks.

---

## Loop Trace

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee - Butterfly Print, Graphic Tee - 2003 Tour Bootleg Style, Vintage Band Tee - Faded Grey … +7 more
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee - Butterfly Print ($18.0, depop)
[4] compare_price
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: dict with keys: category, price, typical_price, compared_with, verdict
      →    below typical
[5] branch
      →    price is fine: no alternative needed
[6] suggest_outfit
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: Hey friend! That butterfly baby tee is a total Y2K dream, and since it runs a bit small, it’s going to give yo…
      →    10 wardrobe item(s)
[7] create_fit_card
      in:  Y2K Baby Tee - Butterfly Print ($18.0, depop)
      out: Channel your inner early-2000s pop star with this Y2K Baby Tee - Butterfly Print, giving you that authentic fi…

  Found:    Y2K Baby Tee - Butterfly Print - $18.0 on depop
  [outfit and fit card text trimmed]

0 model calls this session, 2 served from cache
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

  Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.

0 model calls this session
```

The empty-search trace stops at step 3 and the happy path runs to step 7, so
the branch works. Step 2 in both is the MCP call.

**On the MCP move:** it worked. `search_listings` now runs through MCP (step 2
in both traces above), and nothing behaved differently afterwards: the MCP call
returns the same `list[dict]` as the direct call. Details and evidence below.

### Milestone 1 - MCP Move: `search_listings` (works)

- **Server (`mcp_server.py`):** registered `search_listings` with `@mcp.tool()`.
  Inputs match the Tool Inventory: `description: str` (required),
  `size: str | None = None`, `max_price: float | None = None`. The tool
  description states units (dollars, inclusive), the size-matching rule, the
  returned fields, and that nothing found means `[]`. It delegates to
  `tools.search_listings`, so the search logic is unchanged.
- **Agent (`agent.py`):** `run_agent()` no longer calls `search_listings(...)`
  directly. It calls `call_tool("search_listings", {...})` from `mcp_client.py`
  and logs the step as `search_listings (via MCP)`. The other tools are still
  called directly.
- **`python mcp_client.py`:** lists `search_listings` with
  `description: string`, `size: string (optional)`, `max_price: number (optional)`.
- **Same return value:** the direct call and the MCP call returned equal
  `list[dict]` results (`==` is `True`) for `"vintage graphic tee"` / `max_price=30.0`
  (10 results), `"graphic tee"` / `"M"` / `30` (2 results) and `"zzzz"` (`[]`).
  Nothing changed shape going through MCP.
- **End to end:** `python app.py ask 'vintage graphic tee under $30' --trace`
  ran all 7 steps. Step 2 was `search_listings (via MCP)` with 10 matches. It
  picked *Y2K Baby Tee - Butterfly Print ($18.0, depop)*, then went through
  compare_price → suggest_outfit → create_fit_card. (The two model calls in this
  run were served from the build-mode cache.)
- **Also fixed:** typos in the server's tool description. It had also claimed
  ties were sorted "cheaper first". `tools.search_listings` sorts only by
  keyword score, so ties keep catalog order, and the description now says that.
- **Not MCP-related, still open:** `python test.py` passes 9/10. The MCP check
  ("server and client both import") passes. The live **Model call** check fails
  with `ServerError: 503 UNAVAILABLE ... This model is currently experiencing
  high demand`. That is a temporary error on Google's side, and it failed again
  on a second run. *Update:* a later `python test.py` run (during Milestone 2)
  passed 10/10, so the 503 had cleared by then.

### Milestone 2 - Failure Modes

I triggered each failure on purpose, one at a time. The handlers were already
in place from unit 3 (`_nothing_found_message` and the `ModelUnavailable`
handler in `agent.py`, and the empty-wardrobe path in `tools.suggest_outfit`).
None of the three crashed or went silent, so **no code was changed for this
milestone.**

| # | Failure | How I triggered it | Result |
|---|---|---|---|
| 1 | Empty search | `python app.py ask 'designer ballgown size XXS under $5' --trace` | **PASS** |
| 2 | Empty wardrobe | `python app.py ask 'denim jacket under $50' --empty-wardrobe --trace` | **PASS** |
| 3 | Model unavailable | Changed the last character of `GEMINI_API_KEY` in `.env`, ran `python app.py ask 'oversized flannel shirt for fall' --trace` (a query not run before), then restored the original key (checksum-verified) | **PASS** |

**1. Empty search:** search returned `[]` over MCP and the branch stopped
before `suggest_outfit`, with 0 model calls (full trace above). The agent said:

```
Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.
```

It names each constraint in play and how to loosen it. Suggestions only appear
for constraints the user set: a query with no size or price (e.g. `'striped
wool scarf for winter'`) only gets "try broader words".

**2. Empty wardrobe:** the CLI printed `(running with an empty wardrobe)`, and
`suggest_outfit` ran with `0 wardrobe item(s)`. It returned general advice,
not a crash or an empty string (5 live model calls, including retries after
503 "server busy" errors, which the retry handling recovered from). The start
of the output:

```
Outfit:   Ooh, a vintage Wrangler cropped jacket is such a wardrobe MVP! Since I don't know your closet yet, here are two super easy ways to style it using basics you probably already own:

**1. The Off-Duty Casual Look**
Throw it on over a plain white crewneck tee and your favorite black leggings or straight-leg jeans. ...
```

The fit card was produced as well. Note: the "I don't know your closet yet"
wording comes from the model, not a fixed message, so it may vary between runs.
The empty-wardrobe prompt branch in `tools.suggest_outfit` is what asks for
general advice. (Style memory is off by default, `AI201_MEMORY=0`, so no saved
wardrobe was swapped in.)

**3. Model unavailable:** the run finished in about 2 seconds, with no hang and
no stack trace. Search and price check still ran, then the loop stopped:

```
[6] model unavailable
      →    stopping, search results kept

  The model couldn't be reached, so the outfit and caption steps didn't run. The search worked - 7 listing(s) were found. Check GEMINI_API_KEY in your .env, then run the same query again.
What the service said: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

1 model calls this session
```

It says what broke (the model rejected the key), what still worked (the search)
and what to do (check or replace the key, then re-run). The key never appears
in the output. My first attempt used `'striped wool scarf for winter'`, which
matched no listings, so it took the empty-search branch and never called the
model. A query has to reach `suggest_outfit` to test this failure.

---

## The Improvement

**What I changed:** `generate.py`, commit `9771322`. One change: `generate()`
now retries a temporary server-side error (HTTP 500/502/503/504, or "503" in
the message) up to 3 attempts in total. It waits about 2 s, then about 4 s,
plus 0-1 s of random jitter, and prints `[server busy] ... Retrying in Ns`
before each wait. If all 3 attempts fail, it raises `ModelUnavailable` with a
message that says the service is overloaded. Before this change, a 503 matched
none of the rate-limit checks and raised `ModelUnavailable` on the first
attempt (see Verdicts and Diagnoses). Nothing else changed:
`git diff 760370b 9771322` touches only `generate.py`, and both runs used the
same `scenarios.py`, `run_eval.py`, criteria, 5 tries, cache off and
temperature 0.9.

**Which failure it was meant to fix:** the one mechanism behind all three
baseline misses (criteria 1, 4 and 5). A Gemini `503 UNAVAILABLE` from
`suggest_outfit` or `create_fit_card` ended the run with no retry. That hit 12
of 25 baseline tries.

**How it was run.** `run_eval.py --label after` on the committed
`generate.py` (HEAD, retry version), through the same wrapper as the baseline
(it records the id passed to `suggest_outfit` for criterion 3). Raw output:
`results/run_2026-10-13_1949_after.md`. 25 tries, 40 model calls, no crashes.
The console showed three normal rate-limit pauses (`[rate limit] 15 requests
used this minute. Waiting ...`) and **no `[server busy]` lines**.

### Run Log - After

**Summary**, in the same format as the baseline:

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item id passed to `suggest_outfit` matches `session["selected_item"]` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card uses the real listing facts | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. An empty wardrobe still gets a full run | 5 of 5 | FAIL | PASS | PASS | PASS | FAIL | MISSED (3/5) |

Scoring rules are the same as the baseline's (see Run Log - Before).

#### Criterion 1 - A matching query completes all three tools (target: 4 of 5)

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `vintage graphic tee under $30` | PASS | 10 results, selected `lst_002` (Y2K Baby Tee, $18, depop). All 7 steps ran, fit card returned (383 chars). |
| 2 | `vintage graphic tee under $30` | PASS | Same item. All 7 steps ran, fit card returned (409 chars). |
| 3 | `vintage graphic tee under $30` | PASS | Same item. All 7 steps ran, fit card returned (310 chars). |
| 4 | `vintage graphic tee under $30` | PASS | Same item. All 7 steps ran, fit card returned (419 chars). |
| 5 | `vintage graphic tee under $30` | PASS | Same item. All 7 steps ran, fit card returned (285 chars). |

**Result: 5 of 5 - MET** (target 4 of 5).

#### Criterion 2 - An impossible query stops before the second tool (target: 5 of 5)

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 2 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 3 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 4 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |
| 5 | `designer ballgown size XXS under $5` | PASS | 0 results. Stopped at `[3] branch`. `suggest_outfit` not called. "Things to change" message returned. |

**Result: 5 of 5 - MET** (target 5 of 5).

#### Criterion 3 - The item passed on matches the item in the session (target: 5 of 5)

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `silk slip dress in midi length under $40` | PASS | `selected_item` = `lst_013`, passed to `suggest_outfit` = `lst_013`. Full run completed (fit card 267 chars). |
| 2 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 359 chars). |
| 3 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 240 chars). |
| 4 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 304 chars). |
| 5 | `silk slip dress in midi length under $40` | PASS | `lst_013` = `lst_013`. Full run completed (fit card 324 chars). |

**Result: 5 of 5 - MET** (target 5 of 5).

#### Criterion 4 - The fit card uses the real listing facts (target: 4 of 5)

Each card was checked by script and then read by hand.

| Try | Input (listing) | Result | Evidence |
|---|---|---|---|
| 1 | `corduroy wide-leg pants` (`lst_005`, brand `None`, $32, depop) | PASS | 3 sentences. "$32.00" and "depop" present. No "None", no brand named. |
| 2 | `vintage linen blazer` (`lst_018`, brand `None`, $38, thredUp) | PASS | 2 sentences. "$38.00" and "thredUp" present. No "None", no brand named. |
| 3 | `suede chelsea boots` (`lst_028`, brand `None`, $44, poshmark) | PASS | 3 sentences. "$44.00" and "Poshmark" present. No "None", no brand named. |
| 4 | `vintage polo shirt` (`lst_024`, Ralph Lauren, $18, thredUp) | PASS | 3 sentences. "$18.00" and "thredUp" present. Names only its own brand, Ralph Lauren. |
| 5 | `90s track jacket` (`lst_004`, Champion, $45, poshmark) | PASS | 3 sentences. "$45.00" and "Poshmark" present. Names only its own brand, Champion. |

**Result: 5 of 5 - MET** (target 4 of 5). This is the first run where the
criterion's content checks were actually reached.

#### Criterion 5 - An empty wardrobe still gets a full run (target: 5 of 5)

| Try | Input | Result | Evidence |
|---|---|---|---|
| 1 | `denim jacket under $50`, empty wardrobe | FAIL | Outfit and fit card returned (fit card 362 chars), but the suggestion says "Finish it off with chunky white sneakers", the exact name of example-wardrobe item `w_007` ("Chunky white sneakers"). |
| 2 | `denim jacket under $50`, empty wardrobe | PASS | Outfit and fit card returned (279 chars). No example-wardrobe item named. |
| 3 | `denim jacket under $50`, empty wardrobe | PASS | Outfit and fit card returned (336 chars). No example-wardrobe item named. |
| 4 | `denim jacket under $50`, empty wardrobe | PASS | Outfit and fit card returned (274 chars). No example-wardrobe item named. |
| 5 | `denim jacket under $50`, empty wardrobe | FAIL | Outfit and fit card returned (357 chars), but the suggestion again says "Finish it off with chunky white sneakers". |

**Result: 3 of 5 - MISSED** (target 5 of 5).

**Real output from the after-run** (model text copied from
`results/run_2026-10-13_1949_after.md`; em dashes in titles shown as hyphens)

Criterion 1, try 1. Fit card from `tools.py::create_fit_card`:

```
Channel your inner early-2000s pop star with this gorgeous Y2K Baby Tee - Butterfly Print, featuring the dreamiest pastel graphics. I'm totally obsessed with styling it either oversized with baggy jeans for a casual streetwear vibe or toughened up with combat boots for some edgy contrast. Snag this little wardrobe staple right now on depop for just $18.00 before someone else does!
```

Criterion 2, try 1. `session["error"]` from `agent.py::_nothing_found_message`:

```
Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words - 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.
```

Criterion 3, try 1. Trace from `agent.py::run_agent` (recorded ids: `lst_013` = `lst_013`):

```
[3] select_item
      out: 90s Silk Slip Dress - Floral, Midi Length ($30.0, depop)
...
[6] suggest_outfit
      in:  90s Silk Slip Dress - Floral, Midi Length ($30.0, depop)
      out: Hey there! That 90s floral silk slip dress is an absolute goldmine-and don't sweat that little side seam snag,…
      →    10 wardrobe item(s)
```

Criterion 4, all five cards. From `tools.py::create_fit_card`, one per listing:

```
lst_005: Channel your inner 70s icon with these dreamy Corduroy Wide-Leg Pants in rust, giving major cozy autumn vibes. Just $32.00 on depop, they pair effortlessly with your favorite basics for either an edgy coffee run look or a slouchy, laid-back weekend fit. Snag them now before someone else beats you to it!

lst_018: Scored this dreamy Vintage Linen Blazer on thredUp for just $38.00, and it is the ultimate transitional layering piece. Whether you're throwing it over baggy denim and chunky sneakers for a cool streetwear contrast or pairing it with khaki trousers for a minimal tonal look, the relaxed fit brings instant effortless style.

lst_028: Give your wardrobe an instant vintage vibe with these Tan Suede Chelsea Boots, listed on Poshmark for just $44.00! Style them with baggy dark-wash denim and a black denim jacket for an effortless streetwear look, or lean into cozy earth tones with wide-leg trousers and a slouchy crewneck. They are a timeless staple, and any minor scuffing easily buffs right out with a little TLC.

lst_024: Scored this dreamy Vintage Polo Shirt - Forest Green from Ralph Lauren on thredUp for just $18.00, and I am obsessed with the boxy 90s fit! Whether you're leaning into casual streetwear with baggy denim or keeping it earthy and relaxed with wide-leg trousers, this rich tone goes with literally everything. Which vibe are you wearing first?

lst_004: Scored this authentic Champion 90s Track Jacket - Navy/White Stripe for just $45.00 over on Poshmark, and it brings the ultimate retro streetwear vibe to any outfit. I love layering it open over a white tank with baggy denim or wide-leg khakis for that effortless, high-low look you'll reach for constantly. Grab it before it's gone!
```

Criterion 5, try 1 (a FAIL). Suggestion from `tools.py::suggest_outfit`, empty wardrobe:

```
Hey there! Oh, a cropped Wrangler jacket is an absolute thrift-store holy grail-the structured shoulders give it such a cool, vintage shape.

Here are two super easy ways to style it with things you probably already own:

**1. The Off-Duty Model Look**
Throw this jacket right over a simple white crop top or basic tee, and pair it with your favorite high-waisted black leggings or biker shorts. Finish it off with chunky white sneakers and a baseball cap for a comfy, effortless weekend vibe.

**2. The Elevated Casual**
Layer it over a plain black or grey hoodie (letting the hood hang out the back) and pair it with straight-leg trousers or wide-leg cargo pants. Step into some classic canvas sneakers or retro runners, and you've got an instant streetwear look that's equal parts cozy and cool.
```

### Before and after

| Criterion | Target | Before | After | Change |
|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | MISSED (3/5) | MET (5/5) | +2 |
| 2. An impossible query stops before the second tool | 5 of 5 | MET (5/5) | MET (5/5) | none |
| 3. Item id passed to `suggest_outfit` matches `session["selected_item"]` | 5 of 5 | MET (5/5) | MET (5/5) | none |
| 4. The fit card uses the real listing facts | 4 of 5 | MISSED (0/5) | MET (5/5) | +5 |
| 5. An empty wardrobe still gets a full run | 5 of 5 | MISSED (2/5) | MISSED (3/5) | +1 |
| **All tries** | | **15/25 PASS, 2 of 5 criteria met** | **23/25 PASS, 4 of 5 criteria met** | **+8** |
| Tries that hit a model error (503) | | 12/25 | 0/25 | |

**Did it help, and how do I know:** The results are much better, but this run
**does not show that the retry caused it.** The retry never ran during the
after-run:
- There were no `[server busy]` lines.
- There is no 503 anywhere in `results/run_2026-10-13_1949_after.md`.
- There were 40 model calls, exactly 2 per model-calling try (20 tries), so
  no call was retried.

The 503s that broke 12 of 25 baseline tries simply did not happen this time.
So the before/after difference measures **the model service being available**,
not the retry. Because the retry branch never ran, the code that actually
executed in this run behaved the same as the pre-retry version, so this run
cannot tell the two apart.

What the after-run does show:

- **When the model responds, criteria 1, 3 and 4 meet their targets.** In
  particular, criterion 4's content checks ran for the first time and all five
  cards passed. That includes the three no-brand listings, where no brand was
  invented and "None" never appeared. This is new evidence that the baseline
  could not give.
- **Criterion 2 is unchanged at 5/5.** It makes no model calls, so neither the
  503s nor the retry could affect it.
- **Criterion 5 still missed, for a different reason.** Both FAILs are model
  output, not errors. The empty-wardrobe prompt (`tools.py::suggest_outfit`,
  lines 197-204) asks for "common, easy-to-find pieces (e.g. basic jeans, a
  plain white tee, simple sneakers)", and in 2 of 5 tries the model chose
  "chunky white sneakers". That phrase is exactly the name of example-wardrobe
  item `w_007`, which is the example the criterion itself gives. The model
  never saw the example wardrobe (it was empty), so this is a common styling
  phrase colliding with the check, not the tool leaking wardrobe data. The
  criterion as written still counts it as a FAIL, and I have kept that verdict
  rather than loosening the check. The baseline's two passes had near misses
  ("chunky black boots", "white canvas sneakers"), so this didn't come from
  nowhere. Five tries were too few to see it before.

The only direct evidence that the retry works is from outside this
measurement: in Milestone 2's empty-wardrobe run, the retry version printed
`[server busy] ... Retrying in 2s` and `... Retrying in 5s`, then completed
(5 model calls for one run). That shows the retry can recover. It does not
measure how often, so I am not counting it as a result.

**In one sentence:** the after-run met 4 of 5 criteria (up from 2), but no
503s occurred, so it does not demonstrate that the retry fixed the baseline
misses. Criterion 5 still misses, now because of the model's wording, not
model errors.

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST - unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted - WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST - unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log - Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log - After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
