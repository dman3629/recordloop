This folder is the only thing the self-editor may change.

- `prompts/system.md`: system message for the code-writing model.
- `prompts/mutation_hints.md`: construction ideas appended to the system message.
- `schedule.yaml`: which (n, k) targets to search and their iteration shares.
- `operators.yaml`: model ids/weights, temperature, population and island settings, per-evaluation budget.

Everything else (`checker/`, `tables/`, `practice/`, `engine/`, `selfedit/`, workflows) is out of reach for automated edits.
run_search.py clamps values read from here, so a bad edit cannot raise budgets or time limits past the engine's caps.
