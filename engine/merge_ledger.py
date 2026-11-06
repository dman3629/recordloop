"""Union several ledger.jsonl files into results/ledger.jsonl (parallel Actions jobs each append their own lines).
Usage: python engine/merge_ledger.py extra1.jsonl extra2.jsonl ..."""
import sys
from pathlib import Path

target = Path(__file__).resolve().parent.parent / "results" / "ledger.jsonl"
lines = target.read_text().splitlines() if target.exists() else []
seen = set(lines)
for f in sys.argv[1:]:
    for ln in Path(f).read_text().splitlines():
        if ln.strip() and ln not in seen:
            seen.add(ln); lines.append(ln)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(lines) + ("\n" if lines else ""))
print(f"ledger: {len(lines)} lines")
