# tables/

Frozen reference data: Grassl's table of bounds on binary linear codes (https://www.codetables.de/BKLC/).

Files
- `fetch_codetables.py` fetches the table and writes `gf2_bounds.json` and `targets.json`.
- `refresh.sh` runs the fetch (use from the scheduled workflow).
- `novelty.py n k d` prints `beats_table`, `matches` or `below` against the table lower bound.
- `samples/` holds saved HTML used by the tests (no network in tests).

URL that works (one request for the whole table, about 800 KB, n 1..256, k 1..26):
`https://www.codetables.de/BKLC/Tables.php?q=2&n0=1&n1=256&k0=1&k1=26`
Per-entry page (construction and bound history): `https://www.codetables.de/BKLC/BKLC.php?q=2&n=172&k=21`

Parse rule
Each cell is a link `title="n=N, k=K"` with text `L-U`, or a single number `L` when L = U (optimal).
- L (lower) is the best minimum distance achieved by a known code. A new code with d > L is a record.
- U (upper) is the best proven upper bound on d. No code can exceed it.
The per-entry page confirms this: it shows "lower bound" and "upper bound", and a construction
for the lower-bound code only.

Example (fetched 2026-11-06)
- n=172, k=21: cell `64-74`; entry page says lower bound 64, upper bound 74, construction [172,21,64]
  (subcode of an extended, padded [165,22,63] code). Gap 10.
- n=200, k=21: `77-87`. n=128, k=20: `48-53`.

Notes
- The page header says "last change: 30.12.2011" (a static footer), but the data is current.
- The fetcher refuses to overwrite the tables if fewer than 6000 of the expected 6331 entries parse.
- `targets.json` lists every entry with upper > lower, sorted by gap desc then k asc.
