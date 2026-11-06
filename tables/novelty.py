#!/usr/bin/env python3
"""Usage: novelty.py n k d  ->  prints beats_table | matches | below (vs table lower bound)."""
import json
import sys
from pathlib import Path

BOUNDS = Path(__file__).resolve().parent / "gf2_bounds.json"


def classify(n, k, d, bounds_path=BOUNDS):
    data = json.loads(Path(bounds_path).read_text())
    lo, hi = data["bounds"][f"{n},{k}"]
    if d > lo:
        return "beats_table"
    return "matches" if d == lo else "below"


def main(argv):
    if len(argv) != 4:
        print("usage: novelty.py n k d", file=sys.stderr)
        return 1
    n, k, d = map(int, argv[1:])
    try:
        print(classify(n, k, d))
    except KeyError:
        print(f"no table entry for n={n} k={k}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
