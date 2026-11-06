# Why this exists, and why it is shaped this way

## The verifier principle

An unattended research loop can only produce a real discovery where checking a candidate is
cheap and cannot be gamed. Every autonomous-research success of 2024 to 2026 that held up used an
automatic exact checker or a proof assistant to close the loop (AlphaEvolve-style constructions,
Lean-verified proofs, record codes, record packings). Every failure mode that showed up came from
the other side: paper factories graded by reviewers, scorers that the optimiser learned to exploit,
wet-lab claims that shrank on re-analysis.

Second rule, learned in November 2026 when Packomania paused submissions with 5,000 candidates in
its queue: go where the checker is cheap AND the referee is not flooded.

## Why binary linear codes

- The checker is exact by construction: enumerate every codeword, take the minimum weight.
- The record table (Grassl, codetables.de) is canonical, public, and maintained by one person who
  accepts submissions by email.
- A precedent exists: an evolutionary LLM loop put 7 new record codes into the table in 2026
  (LinCodeEvolve, arXiv 2609.37056).
- No submission queue is visible, unlike the geometric packing tables.

## Two loops, one frozen wall

- Inner loop: the model writes a construction program; CPUs grind; the checker certifies.
- Outer loop: once a week the system proposes one change to its own strategy (prompts, mutation
  hints, which targets get compute, model mix), measures it on a practice set, and keeps it only
  if practice got better at equal compute.
- Frozen wall: checker, tables, practice set, budget caps, and the human submission step. The
  self-editor's diff is rejected if it touches anything outside `strategy/`.

## The practice score is honest because of dates

The practice targets are records set in September to November 2026, after the training cutoffs
of the models in use. A strategy that re-finds them fast is searching, not remembering.

## Budget and kill gate

- Compute: GitHub Actions on a public repo (free, 6-hour jobs, 20 in parallel).
- Tokens: free-tier Gemini by default; a monthly cap of 60 USD-equivalent for search and 40 for
  self-edits is enforced in `engine/budget.py` even on free routes, so usage stays visible.
- Kill gate: 60 days with zero verified records AND no practice gain for 3 weeks → stop the loop.

## What would prove this wrong

Survivorship in the precedents (failed solo runs are never published); the table being swept by
others before us; a checker exploit through a bug rather than floating point (so `verify.py` is
an independent second implementation); a maintainer refusing AI-assisted submissions.
