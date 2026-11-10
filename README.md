# recordloop

A self-improving search for new records in Markus Grassl's table of binary linear codes
(codetables.de, GF(2), n <= 256). An LLM-driven evolutionary loop (OpenEvolve) writes programs that build
generator matrices; a frozen exact checker measures the minimum distance; anything above the table's lower bound
becomes a certificate. A weekly outer loop may edit only `strategy/`, and only if the practice score improves.

## The verifier principle

1. The model proposes, the checker decides: `checker/mindist` enumerates every non-zero codeword, so `d` is exact.
2. `checker/verify.py` recomputes `d` independently (numpy) before any record is committed.
3. Nothing automated can edit `checker/`, `tables/`, `practice/`, the budget caps, or the human submission step.

## How a record travels

search job (`search.yml`, every 6 h, 3 target groups) -> certificate in `certs/pending/` -> `checker/verify.py`
and `tables/novelty.py` re-check -> `certs/verified/` and commit `record: [n,k,d] beats table lower x` ->
a human re-checks the live table and emails Grassl (see `SUBMISSION.md`). Nothing is submitted automatically.

Live progress during a run: the [`progress` branch](https://github.com/dman3629/recordloop/tree/progress), one JSON per group.

## Practice score

`practice/practice_set.json` holds seven records from the LinCodeEvolve paper (Sept 2026, after model training
cutoffs). A strategy's score is the mean over targets of `min(1, (best_d - old_lower) / (record_d - old_lower))`
at a fixed budget and fixed seeds. `selfedit/gate.py` keeps a change only if the mean rises by at least 0.02 and no
target falls by more than 0.1.

## Kill gate

60 days with zero records and no practice gain for 3 weeks: stop the project.

## Layout

`engine/` OpenEvolve seed, evaluator, runner, budget ledger (caps: search 60 USD, selfedit 40 USD per month) |
`strategy/` prompts, targets, model and population settings (the only self-editable folder) |
`practice/` scoring set and runner | `selfedit/` propose, gate, apply | `checker/`, `tables/` frozen wall.

## Run it

```
pip install -r requirements.txt && make -C checker
export LLM_API_KEY=...   # any OpenAI-compatible endpoint; LLM_BASE_URL defaults to Anthropic's (https://api.anthropic.com/v1/)
python engine/run_search.py --targets "172,21" --iterations 20
```
In Actions the key comes from secret `ANTHROPIC_API_KEY` (a key from the Console organisation linked to the Max plan, so the plan's monthly API credits cover it; optional `LLM_BASE_URL` secret); a gateway such as OmniRoute works by setting `LLM_BASE_URL` and swapping model ids in `strategy/operators.yaml`.
Offline test: `python engine/_mock_llm.py 8765` and `LLM_BASE_URL=http://127.0.0.1:8765/v1 LLM_API_KEY=x`.

## Results

<!-- RESULTS:START -->
| code [n,k,d] | previous lower | found | status |
|---|---|---|---|
| none yet | | | |

Search runs logged: 39
<!-- RESULTS:END -->

## Run log

- 2026-11-06 run 42243385832: 29 Gemini calls succeeded in the first 25 min, then HTTP 429 on every call until the 5h30m stop (about 2150 per job); no certificate. Retries raised to 8 with 60 s delay.
- 2026-11-06: switched from Gemini free tier to Claude Haiku 5.5 (`claude-haiku-5-5`) via Anthropic's OpenAI-compatible endpoint; added an LLM circuit breaker (25 consecutive failures, or no success in 20 min, ends the run cleanly with `stopped_reason: llm_unavailable`); retries back to 3 / 30 s.
- 2026-11-07 runs 42303271215 (1h29m) and 42308510174 (2h15m) on Claude Haiku 5.5: no 429s, no breaker trips, no certificate (best_d 72-92 vs table lower 76-100). Run 42308510174's publish failed on a ledger rebase conflict; its results were recovered by hand, and the publish step now resets to latest main before merging.
