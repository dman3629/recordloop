"""Rewrite the results table in README.md (between RESULTS markers) from certs/verified and results/runs."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
certs = [json.loads(p.read_text()) for p in sorted((ROOT / "certs" / "verified").glob("*.json"))]
runs = list((ROOT / "results" / "runs").glob("*.json"))
rows = ["| code [n,k,d] | previous lower | found | status |", "|---|---|---|---|"]
for c in certs:
    rows.append(f"| [{c['n']},{c['k']},{c['d']}] | {c['table_lower_at_run']} | {c['found_at'][:10]} | verified, awaiting submission |")
if not certs:
    rows.append("| none yet | | | |")
block = f"<!-- RESULTS:START -->\n{chr(10).join(rows)}\n\nSearch runs logged: {len(runs)}\n<!-- RESULTS:END -->"
p = ROOT / "README.md"
s = p.read_text()
p.write_text(re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->", lambda m: block, s, flags=re.S))
