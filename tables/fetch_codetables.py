#!/usr/bin/env python3
"""Fetch Grassl's table of bounds on binary linear codes and write gf2_bounds.json + targets.json.

One request for the whole table (n 1..256, k 1..26). Each cell is "lower-upper", or a single
number when lower == upper (the code is optimal). Lower = best d achieved by a known code,
upper = best proven upper bound.
"""
import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://www.codetables.de/BKLC/Tables.php?q=2&n0=1&n1=256&k0=1&k1=26"
UA = "recordloop/0.1 (research; contact via GitHub dman3629)"
CELL = re.compile(r'title="n=(\d+), k=(\d+)" class="tab" HREF="[^"]*">\s*(\d+)(?:-(\d+))?\s*</A>')
MIN_ENTRIES = 6000  # full table has 6331 entries; refuse to overwrite with less


def parse_tables(html):
    """-> {(n, k): (lower, upper)}"""
    out = {}
    for n, k, lo, hi in CELL.findall(html):
        lo = int(lo)
        hi = int(hi) if hi else lo
        if hi < lo:
            raise ValueError(f"upper < lower at n={n} k={k}")
        out[(int(n), int(k))] = (lo, hi)
    return out


def make_targets(bounds):
    t = [{"n": n, "k": k, "lower": lo, "upper": hi, "gap": hi - lo}
         for (n, k), (lo, hi) in bounds.items() if hi > lo]
    t.sort(key=lambda e: (-e["gap"], e["k"], e["n"]))
    return t


def write_outputs(bounds, fetched, outdir=HERE):
    outdir = Path(outdir)
    b = {f"{n},{k}": [lo, hi] for (n, k), (lo, hi) in sorted(bounds.items())}
    (outdir / "gf2_bounds.json").write_text(
        json.dumps({"fetched": fetched, "q": 2, "bounds": b}, separators=(",", ":")) + "\n")
    (outdir / "targets.json").write_text(json.dumps(make_targets(bounds), indent=0) + "\n")


def fetch(url=URL, retries=3):
    import requests
    for i in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=120)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"fetch failed ({e}); retry {i + 1}/{retries}", file=sys.stderr)
            time.sleep(5)  # be gentle with the server
    raise SystemExit("could not fetch codetables.de")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", help="parse a saved HTML page instead of fetching")
    ap.add_argument("--outdir", default=str(HERE))
    a = ap.parse_args()
    html = Path(a.from_file).read_text() if a.from_file else fetch()
    bounds = parse_tables(html)
    if len(bounds) < MIN_ENTRIES:
        raise SystemExit(f"only {len(bounds)} entries parsed; refusing to overwrite tables")
    write_outputs(bounds, datetime.date.today().isoformat(), a.outdir)
    t = make_targets(bounds)
    print(f"entries={len(bounds)} targets={len(t)} gap>=2={sum(e['gap'] >= 2 for e in t)}")


if __name__ == "__main__":
    main()
