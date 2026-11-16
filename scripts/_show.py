"""Tiny print helpers shared by the demo scripts."""
import json
from pprint import pformat


def heading(text):
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)


def step(title, query=None):
    print(f"\n--- {title}")
    if query:
        print("    mongosh :", query)


def show(obj, limit=6):
    if isinstance(obj, list):
        for item in obj[:limit]:
            print("   ", _short(item))
        if len(obj) > limit:
            print(f"    ... ({len(obj) - limit} more)")
        if not obj:
            print("    (no documents)")
    else:
        print("   ", _short(obj))


def _short(x):
    s = pformat(x, width=110, compact=True, sort_dicts=False).replace("\n", "\n     ")
    return s if len(s) < 900 else s[:900] + " ..."


def as_json(x):
    return json.dumps(x, indent=2, default=str)
