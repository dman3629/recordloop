# Practice set: source and extraction

`practice_set.json` lists the seven record codes from "Evolving Towards Better Codes: LLM-Guided Search for
High-Distance Binary Linear Codes" (Seddas, Shashkov, Viazovska, Abbe; arXiv 2609.37056v1,
https://arxiv.org/abs/2609.37056v1, HTML at https://arxiv.org/html/2609.37056v1).
The records date from Sept 2026, after the training cutoff of the models we use, so a strategy cannot have memorised them.

Extracted by reading the abstract page (the seven [n,k,d]) and the HTML page (Table 2, previous CodeTables lower
bound, gain). Cross-check: `tables/gf2_bounds.json` (fetched 2026-11-06) still shows the old lower bound for six
of the seven; [200,21] already shows 77 (the table was updated after the paper). `upper` comes from that live table.

Fields: `record_d` (the paper's new d), `old_lower` (lower bound before the record), `gain` = record_d - old_lower,
`upper` (upper bound). If a paper ever lacks the old bound, set `old_lower: null`; `fill_old_bounds.py` then sets it
to `record_d - gain` when `gain` is known, else to the live table lower bound when that is still below `record_d`.

Score (CONTRACT): per target `min(1, (best_d_reached - old_lower) / (record_d - old_lower))`, clipped at 0,
averaged over targets and seeds. Budgets, seeds and targets are fixed in `practice/config.yaml`.
During practice the table seen by the evaluator is a temporary one built from `old_lower`/`upper`, certificates
go to a temp dir, and no certificate is ever written to `certs/`.
