"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A normal query; what's checked is the session. Criterion 3 — the id
        # passed to suggest_outfit matches session["selected_item"]["id"].
        "name": "selected item is the item passed on",
        "query": "silk slip dress in midi length under $40",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 needs five DIFFERENT listings, at least two with brand
        # None. One query can only ever select one listing (search is
        # deterministic), so this scenario gives run_eval.py a list: try k
        # runs queries[k-1]. Each query selects a different listing first
        # (checked against search_listings before the run).
        "name": "fit card uses real listing facts",
        "queries": [
            "corduroy wide-leg pants",  # lst_005 — brand None, depop, $32
            "vintage linen blazer",     # lst_018 — brand None, thredUp, $38
            "suede chelsea boots",      # lst_028 — brand None, poshmark, $44
            "vintage polo shirt",       # lst_024 — Ralph Lauren, thredUp, $18
            "90s track jacket",         # lst_004 — Champion, poshmark, $45
        ],
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes, and
        # criterion 5: a non-empty suggestion and a fit card, naming no item
        # from the example wardrobe.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        queries = scenario.get("queries")
        if queries is not None:
            if not queries or not all(str(q).strip() for q in queries):
                problems.append(f"scenario {i} has an empty entry in queries")
        elif not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
