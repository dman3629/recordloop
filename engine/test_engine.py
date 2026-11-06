import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "selfedit"))
ROOT = Path(__file__).resolve().parent.parent


def test_budget_caps(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDLOOP_LEDGER", str(tmp_path / "l.jsonl"))
    import budget
    assert budget.remaining("search") == 60.0
    budget.charge("search", "gemini-2.5-flash", 1_000_000, 0)
    assert abs(budget.spent("search") - 0.30) < 1e-6 and budget.spent("selfedit") == 0
    budget.charge("selfedit", "x-pro", 40_000_000, 0)
    assert budget.paused("selfedit")


def test_seed_program_evaluates(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDLOOP_TABLE", str(ROOT / "practice/fixtures/gf2_bounds.json"))
    monkeypatch.setenv("RECORDLOOP_CERTS", str(tmp_path / "certs"))
    monkeypatch.setenv("RECORDLOOP_TARGET", "16,6")
    monkeypatch.setenv("RECORDLOOP_TIME_BUDGET", "4")
    import evaluator
    m = evaluator.evaluate(str(ROOT / "engine/initial_program.py"))
    assert m["best_d"] >= 4 and 0 < m["combined_score"] <= 1 and "error" not in m


def test_timeout_scores_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDLOOP_TARGET", "16,6")
    monkeypatch.setenv("RECORDLOOP_TIME_BUDGET", "1")
    monkeypatch.setenv("RECORDLOOP_TABLE", str(ROOT / "practice/fixtures/gf2_bounds.json"))
    p = tmp_path / "slow.py"
    p.write_text("import time\ndef search(n,k,t,s):\n    time.sleep(60)\n")
    import evaluator
    assert evaluator.evaluate(str(p))["combined_score"] == 0.0


def test_selfedit_rules():
    from propose import valid
    assert valid("--- a/engine/x\n+++ b/engine/x\n") is not None
    assert valid("--- a/strategy/schedule.yaml\n+++ b/strategy/schedule.yaml\n@@\n") is None
