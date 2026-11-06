# recordloop: interface contract

A self-improving loop that hunts new records in Grassl's table of binary linear codes
(codetables.de, GF(2), n <= 256) and can only improve its own *strategy*, never its checker.

Two loops, one frozen wall.

- Inner loop (search): the model writes a program that constructs candidate generator matrices;
  the frozen checker computes the exact minimum distance; anything above the table's lower bound
  becomes a certificate.
- Outer loop (self-edit): weekly, the model proposes a change confined to `strategy/`; the change is
  kept only if the practice score gets better at equal compute (strict gate).
- Frozen wall (never edited by any automated step): `checker/`, `tables/`, `practice/`, the budget
  caps in `engine/budget.py`, and the human submission step.

## Directory ownership

| dir | owner | editable by self-editor? |
|---|---|---|
| `checker/` | frozen wall | no |
| `tables/` | frozen wall | no |
| `practice/` | frozen wall | no |
| `engine/` | humans | no |
| `strategy/` | self-editor + humans | YES (only this) |
| `selfedit/` | humans | no |
| `.github/workflows/` | humans | no |
| `certs/`, `results/` | written by runs | no |

## Checker CLI (checker/mindist)

Input file format (text): first line `n k`, then k lines, each a string of n characters `0`/`1`
(one generator row per line). Constraints: 1 <= n <= 256, 1 <= k <= 26.

```
checker/mindist <matrix.txt>
```

stdout: one JSON object:
```
{"n":172,"k":21,"rank":21,"d":66,"min_codeword":"<hex of n bits, MSB first, padded to a multiple of 4 bits>",
 "codewords_enumerated":2097151,"elapsed_s":0.41,"checker_version":"1.0.0"}
```
If rank < k: `{"error":"rank_deficient","rank":<r>,...}` and exit code 2. Bad input: exit code 1.
The checker enumerates every non-zero codeword (Gray code over 2^k - 1 combinations) with 64-bit
word XORs; it never stops early. `d` is exact by construction.

`checker/verify.py <certificate.json>` recomputes `d` by an independent numpy enumeration and
exits 0 only if it agrees with the certificate.

## Certificate format (certs/pending/<n>_<k>_<d>_<sha8>.json)

```
{"n":172,"k":21,"d":66,"generator_rows":["0101...", ...],
 "table_lower_at_run":65,"table_upper_at_run":72,"table_fetched":"2026-11-06",
 "checker_version":"1.0.0","checker_sha256":"...","program_sha256":"...",
 "found_at":"2026-11-07T03:12:00Z","run_id":"gha-<run id>","strategy_version":"<git sha>"}
```

## Tables (tables/gf2_bounds.json)

`{"fetched":"YYYY-MM-DD","q":2,"bounds":{"n,k":[lower,upper], ...}}` for 1<=n<=256, 1<=k<=26.
`tables/targets.json`: list of `{"n":..,"k":..,"lower":..,"upper":..,"gap":..}` with `upper > lower`,
sorted by gap desc then k asc. `tables/novelty.py n k d` prints `beats_table | matches | below`.

## Evaluator (engine/evaluator.py), OpenEvolve contract

`evaluate(program_path) -> dict` runs the candidate program's `search(n, k, time_budget_s, rng_seed)`
which must return a list of generator matrices (lists of row strings). The evaluator checks each
with the checker, keeps the best `d`, and returns metrics:
`{"combined_score": best_d / table_upper, "best_d": .., "table_lower": .., "beats_table": 0|1,
  "candidates": .., "elapsed_s": ..}`. On `beats_table`, it writes a certificate to `certs/pending/`.
Targets come from `strategy/schedule.yaml`. Time budget per evaluation is set in `engine/config.yaml`.

## Budget (engine/budget.py)

Ledger at `results/ledger.jsonl` (one line per LLM call: tokens in/out, model, est_usd, lane).
Caps per calendar month: search lane 60 USD, selfedit lane 40 USD (estimated from token counts and
a price table; free routes count at their list price so the cap still means something).
At the cap, the lane exits 0 with `BUDGET_PAUSED` in the log.

## LLM access

OpenAI-compatible endpoint. Env: `OMNIROUTE_URL` (e.g. https://llm.drezar.site/v1), `OMNIROUTE_API_KEY`.
Model ids live in `strategy/operators.yaml` (the self-editor may change them to any id the gateway lists).

## Practice set (practice/practice_set.json)

Records set in Sept to Nov 2026 (after model training cutoffs), each with the table's lower bound
*before* the record. Score for a strategy = mean over targets of
`min(1, (best_d_reached - old_lower) / (record_d - old_lower))` under a fixed per-target budget and
fixed seeds. The self-edit gate keeps a change only if the mean score rises by >= 0.02 and no
target's score falls by more than 0.1.

## Git

All commits by automated steps: author `Derezar Master <derezarmaster@gmail.com>`, no co-author
trailers, no generated-by footers. Commit messages are plain: `record: [n,k,d] beats table lower x`,
`selfedit: <one line>`, `tables: refresh YYYY-MM-DD`.
