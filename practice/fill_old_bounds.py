"""Fill old_lower: null entries in practice_set.json. See extract_practice_set.md."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ps = json.loads((here / "practice_set.json").read_text())
tab = here.parent / "tables" / "gf2_bounds.json"
live = json.loads(tab.read_text())["bounds"] if tab.exists() else {}
for t in ps["targets"]:
    if t.get("old_lower") is not None:
        continue
    if t.get("gain") is not None:
        t["old_lower"] = t["record_d"] - t["gain"]
    elif live.get(f"{t['n']},{t['k']}", [t["record_d"]])[0] < t["record_d"]:
        t["old_lower"] = live[f"{t['n']},{t['k']}"][0]
    else:
        raise SystemExit(f"cannot fill old_lower for {t['n']},{t['k']}")
(here / "practice_set.json").write_text(json.dumps(ps, indent=1))
print("ok")
