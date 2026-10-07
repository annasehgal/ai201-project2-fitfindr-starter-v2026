"""
Style memory (extra credit): FitFindr remembers a wardrobe between runs.

When a run is given a wardrobe with items, it's saved to a small JSON file. A
later run that's given an empty wardrobe loads the saved one instead, so
suggest_outfit can still name pieces the user owns.

It's off unless AI201_MEMORY=1 (see config.py), so evaluation runs, including
the empty-wardrobe scenario, aren't changed by earlier runs. Delete the file to
forget.
"""

import json

import config


def load_wardrobe() -> dict | None:
    """
    The saved wardrobe, or None when nothing usable is saved.

    A missing file, unreadable JSON, or a saved wardrobe with no items all
    give None rather than an error.
    """
    path = config.STYLE_MEMORY_PATH
    if not path.exists():
        return None
    try:
        wardrobe = json.loads(path.read_text(encoding="utf-8")).get("wardrobe")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(wardrobe, dict) or not wardrobe.get("items"):
        return None
    return wardrobe


def save_wardrobe(wardrobe: dict) -> None:
    """Save a wardrobe (same shape as get_example_wardrobe()) for later runs."""
    config.STYLE_MEMORY_PATH.write_text(
        json.dumps({"wardrobe": wardrobe}, indent=2), encoding="utf-8"
    )
