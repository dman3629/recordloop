import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "tables"
sys.path.insert(0, str(TAB))
import fetch_codetables as fc  # noqa: E402
import novelty  # noqa: E402


def test_parse_sample():
    html = (TAB / "samples" / "tables_sample.html").read_text()
    b = fc.parse_tables(html)
    assert b[(1, 1)] == (1, 1)
    assert b[(7, 4)] == (3, 3)
    assert b[(24, 12)] == (8, 8)
    assert b[(172, 21)] == (64, 74)
    assert b[(200, 21)] == (77, 87)
    assert b[(128, 20)] == (48, 53)
    assert all(lo <= hi for lo, hi in b.values())


def test_targets_sorted_and_strict():
    b = {(10, 3): (4, 5), (20, 5): (8, 8), (30, 4): (10, 14), (31, 2): (12, 16), (32, 9): (6, 7)}
    t = fc.make_targets(b)
    assert (20, 5) not in {(e["n"], e["k"]) for e in t}
    assert [(e["n"], e["k"]) for e in t] == [(31, 2), (30, 4), (10, 3), (32, 9)]
    assert all(e["upper"] > e["lower"] and e["gap"] == e["upper"] - e["lower"] for e in t)


def test_write_outputs(tmp_path):
    fc.write_outputs({(10, 3): (4, 5), (7, 4): (3, 3)}, "2026-11-06", tmp_path)
    d = json.loads((tmp_path / "gf2_bounds.json").read_text())
    assert d == {"fetched": "2026-11-06", "q": 2, "bounds": {"7,4": [3, 3], "10,3": [4, 5]}}
    assert len(json.loads((tmp_path / "targets.json").read_text())) == 1


def test_committed_tables_shape():
    d = json.loads((TAB / "gf2_bounds.json").read_text())
    assert d["q"] == 2 and len(d["bounds"]) == 6331
    assert d["bounds"]["24,12"] == [8, 8]
    t = json.loads((TAB / "targets.json").read_text())
    assert t and all(e["upper"] > e["lower"] for e in t)


def test_novelty(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps({"fetched": "x", "q": 2, "bounds": {"172,21": [64, 74]}}))
    assert novelty.classify(172, 21, 65, p) == "beats_table"
    assert novelty.classify(172, 21, 64, p) == "matches"
    assert novelty.classify(172, 21, 60, p) == "below"


def test_novelty_cli():
    out = subprocess.run([sys.executable, str(TAB / "novelty.py"), "24", "12", "8"], capture_output=True, text=True)
    assert out.stdout.strip() == "matches" and out.returncode == 0
    out = subprocess.run([sys.executable, str(TAB / "novelty.py"), "172", "21", "65"], capture_output=True, text=True)
    assert out.stdout.strip() == "beats_table"
