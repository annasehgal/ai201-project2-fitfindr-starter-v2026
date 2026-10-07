import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable

# Extra credit: fourth tool and style memory.
from tools import compare_price
from utils.style_memory import load_wardrobe, save_wardrobe


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        # extra credit
        "price_check": None,         # what compare_price returned for selected_item
        "cheaper_alternative": None, # set by the price branch when one exists
        "wardrobe_from_memory": False, # True when an empty wardrobe was swapped for the saved one
    }


# ── parsing the query ─────────────────────────────────────────────────────────

# Sizes a user is likely to type. Matched as whole words so that the "M" in
# "Medium Wash" or the "L" in "L/XL" can't be mistaken for a request.
_SIZE_WORDS = r"XXS|XS|S|M|L|XL|XXL"

_PRICE_RE = re.compile(r"(?:under|below|less than|max|up to)?\s*\$\s*(\d+(?:\.\d+)?)", re.I)
_SIZE_RE = re.compile(rf"\bsize\s+({_SIZE_WORDS}|US\s*\d+(?:\.\d+)?|W\d+)\b", re.I)
_BARE_SIZE_RE = re.compile(rf",\s*({_SIZE_WORDS})\s*$", re.I)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a price ceiling out of what the user typed.

    Regex rather than a model call, for three reasons worth writing down: it
    costs nothing, it returns the same answer twice (which the unit 4 state
    criterion depends on), and when it gets something wrong the reason is
    readable in the pattern instead of being a model's opinion.

    What it gives up is phrasing it has never seen. "nothing over thirty
    dollars" parses to no price at all, and the run then quietly ignores the
    ceiling. That limitation is in the README rather than hidden here.

    Returns a dict with keys `description` (str), `size` (str or None) and
    `max_price` (float or None).
    """
    text = query or ""

    max_price = None
    price_match = _PRICE_RE.search(text)
    if price_match:
        max_price = float(price_match.group(1))
        text = text[: price_match.start()] + " " + text[price_match.end() :]

    size = None
    size_match = _SIZE_RE.search(text) or _BARE_SIZE_RE.search(text)
    if size_match:
        size = re.sub(r"\s+", " ", size_match.group(1)).strip().upper()
        text = text[: size_match.start()] + " " + text[size_match.end() :]

    description = re.sub(r"[,\s]+", " ", text).strip(" ,")
    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def _search(parsed: dict) -> list[dict]:
    """
    Call search_listings — over MCP when the server has it registered.

    ⚠️ UNIT 4, MILESTONE 1. In unit 3 this function does not exist and
    `run_agent` calls `search_listings(...)` directly. The fallback is not
    belt-and-braces for its own sake: `python agent.py` has to keep working
    while the MCP side is half-built, and a student whose 40 minutes ran out
    still needs the rest of the week to run.
    """
    try:
        from mcp_client import call_tool

        results = call_tool(
            "search_listings",
            {
                "description": parsed["description"],
                "size": parsed["size"],
                "max_price": parsed["max_price"],
            },
        )
        return results or []
    except Exception:  # noqa: BLE001 — MCP unavailable is not a user-facing error
        return search_listings(
            parsed["description"], parsed["size"], parsed["max_price"]
        )


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    The branch rule, stated once so the code below can be read against it:

        If search_listings returns an empty list, put a message in
        session["error"] naming what the user could change, and return the
        session without calling suggest_outfit. Otherwise take the first
        result, put it in session["selected_item"], and continue.
    """
    session = new_session(query, wardrobe)
    steps = 0

    # ⚠️ UNIT 4, MILESTONE 2 — everything in the try/except is unit 3 code; the
    # handler around it is what unit 4 adds, so that a bad key produces a
    # sentence rather than a stack trace.
    try:
        steps += 1
        trace.check_iterations(steps)
        parsed = parse_query(query)
        session["parsed"] = parsed
        trace.step("parse_query", inputs=query, returned=parsed)

        steps += 1
        trace.check_iterations(steps)
        # PROFESSOR ORIGINAL / UNIT 4 MCP VERSION:
        # results = _search(parsed)
        # session["search_results"] = results
        # trace.step(
        #     "search_listings (via MCP)",
        #     inputs=parsed,
        #     returned=results,
        #     note=f"{len(results)} match(es)",
        # )

        # UNIT 3:
        session["search_results"] = search_listings(
            session["parsed"]["description"],
            session["parsed"]["size"],
            session["parsed"]["max_price"],
        )
        trace.step(
            "search_listings",
            inputs=session["parsed"],
            returned=session["search_results"],
            note=f"{len(session['search_results'])} match(es)",
        )

        # ── THE BRANCH ────────────────────────────────────────────────────────
        # PROFESSOR ORIGINAL / UNIT 4 MCP VERSION:
        # if not results:
        #     session["error"] = _nothing_found_message(parsed)

        # UNIT 3:
        if not session["search_results"]:
            session["error"] = _nothing_found_message(session["parsed"])
            trace.step(
                "branch",
                note="search returned []: stopping before suggest_outfit",
            )
            return session

        steps += 1
        trace.check_iterations(steps)
        # PROFESSOR ORIGINAL / UNIT 4 MCP VERSION:
        # session["selected_item"] = results[0]

        # UNIT 3:
        session["selected_item"] = session["search_results"][0]
        trace.step("select_item", returned=session["selected_item"])

        # ── EXTRA CREDIT: SECOND BRANCH (price check) ─────────────────────────
        # If the selected item is priced above typical for its category, look
        # for a cheaper listing in the same category among the search results.
        # selected_item does not change either way.
        steps += 1
        trace.check_iterations(steps)
        session["price_check"] = compare_price(session["selected_item"])
        trace.step(
            "compare_price",
            inputs=session["selected_item"],
            returned=session["price_check"],
            note=session["price_check"]["verdict"],
        )
        if session["price_check"]["verdict"] == "above typical":
            cheaper = [
                listing
                for listing in session["search_results"][1:]
                if listing["category"] == session["selected_item"]["category"]
                and listing["price"] < session["selected_item"]["price"]
            ]
            if cheaper:
                session["cheaper_alternative"] = min(cheaper, key=lambda l: l["price"])
            trace.step(
                "branch",
                returned=session["cheaper_alternative"],
                note="above typical: looked for a cheaper result in the same category",
            )
        else:
            trace.step("branch", note="price is fine: no alternative needed")

        # ── EXTRA CREDIT: style memory (wardrobe) ─────────────────────────────
        # A wardrobe with items is saved for later runs. An empty one is
        # replaced by the saved wardrobe, if there is one.
        if config.STYLE_MEMORY_ENABLED:
            if (session["wardrobe"] or {}).get("items"):
                save_wardrobe(session["wardrobe"])
                trace.step(
                    "save wardrobe",
                    note=f"{len(session['wardrobe']['items'])} item(s) remembered",
                )
            else:
                remembered = load_wardrobe()
                if remembered:
                    session["wardrobe"] = remembered
                    session["wardrobe_from_memory"] = True
                trace.step(
                    "load wardrobe",
                    note=(
                        f"{len(remembered['items'])} remembered item(s)"
                        if remembered
                        else "nothing saved yet"
                    ),
                )

        steps += 1
        trace.check_iterations(steps)
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"], session["wardrobe"]
        )
        trace.step(
            "suggest_outfit",
            inputs=session["selected_item"],
            returned=session["outfit_suggestion"],
            note=f"{len(session['wardrobe'].get('items') or [])} wardrobe item(s)",
        )

        steps += 1
        trace.check_iterations(steps)
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"], session["selected_item"]
        )
        trace.step(
            "create_fit_card",
            inputs=session["selected_item"],
            returned=session["fit_card"],
        )

    except ModelUnavailable as exc:
        session["error"] = (
            f"The model couldn't be reached, so the outfit and caption steps "
            f"didn't run. The search worked — "
            f"{len(session['search_results'])} listing(s) were found. "
            f"Check GEMINI_API_KEY in your .env, then run the same query "
            f"again.\nWhat the service said: {exc}"
        )
        trace.step("model unavailable", note="stopping, search results kept")

    return session


def _nothing_found_message(parsed: dict) -> str:
    """
    What to say when the search comes back empty.

    "No results" is not this message. This one names the three things the user
    actually controls, and says which of them were in play — a ceiling they
    never set is not a ceiling worth suggesting they raise.
    """
    tried = [f"description {parsed['description']!r}"]
    if parsed["size"]:
        tried.append(f"size {parsed['size']}")
    if parsed["max_price"] is not None:
        tried.append(f"under ${parsed['max_price']:g}")

    suggestions = ["try broader words — 'jacket' finds more than 'cropped corduroy jacket'"]
    if parsed["size"]:
        suggestions.append("drop the size, or try a neighbouring one")
    if parsed["max_price"] is not None:
        suggestions.append(f"raise the price ceiling above ${parsed['max_price']:g}")

    return (
        "Nothing in the listings matched " + ", ".join(tried) + ".\n"
        "Things to change: " + "; ".join(suggestions) + "."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")
    # extra credit
    print(f"  price:    {(session['price_check'] or {}).get('verdict')}")
    if session["cheaper_alternative"]:
        alt = session["cheaper_alternative"]
        print(f"  cheaper:  {alt['title']} — ${alt['price']} on {alt['platform']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
