"""Runs a candidate program's search() in an isolated process. Usage:
python -I _run_program.py program.py n k budget_s seed. Prints one JSON line: {"candidates": [[rows]...]}"""
import importlib.util, json, sys

try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (3 << 30, 3 << 30))
except Exception:
    pass

path, n, k, budget, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
spec = importlib.util.spec_from_file_location("candidate", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = mod.search(n, k, budget, seed)
clean = []
for mat in out:
    rows = [str(r) for r in mat]
    if len(rows) == k and all(len(r) == n and set(r) <= {"0", "1"} for r in rows):
        clean.append(rows)
print("RESULT:" + json.dumps({"candidates": clean}))
