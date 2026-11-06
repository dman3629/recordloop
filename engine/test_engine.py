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


def test_prices_and_breaker(tmp_path):
    import budget, _llm_patch as lp
    assert abs(budget.estimate_usd("claude-haiku-5-5", 1_000_000, 1_000_000) - 0.60) < 1e-9
    assert abs(budget.estimate_usd("claude-sonnet-5-5", 1_000_000, 0) - 2.0) < 1e-9
    assert abs(budget.estimate_usd("mystery", 1_000_000, 1_000_000) - 12.0) < 1e-9
    f = str(tmp_path / "b.log")
    lp.breaker_init(f)
    assert lp.breaker_tripped(f) is None
    with open(f, "a") as h:
        h.write("F 1.0\n" * 24)
    assert lp.breaker_tripped(f) is None
    with open(f, "a") as h:
        h.write("F 1.0\n")
    assert "25 consecutive" in lp.breaker_tripped(f)
    lp.breaker_init(f)
    with open(f, "a") as h:
        h.write("F 1.0\n")
    import time
    assert lp.breaker_tripped(f, now=time.time() + 60) is None
    assert "no successful" in lp.breaker_tripped(f, now=time.time() + 1300)


def test_progress_report(tmp_path, monkeypatch):
    import json, subprocess, progress
    monkeypatch.setenv("RECORDLOOP_PROGRESS_DIR", str(tmp_path / "out"))
    monkeypatch.delenv("RECORDLOOP_PROGRESS_PUSH", raising=False)
    monkeypatch.setenv("RECORDLOOP_PROGRESS_REMOTE", str(tmp_path / "nope.git"))
    p = progress.report("r1", "0of3", {"n": 172, "k": 21, "iteration": 10, "best_d": 40})
    d = json.loads(p.read_text())
    assert d["run_id"] == "r1" and d["best_d"] == 40 and d["updated_at"] and d["group"] == "0of3"
    assert not (tmp_path / "nope.git").exists()  # no push attempted
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    monkeypatch.setenv("RECORDLOOP_PROGRESS_PUSH", "1")
    monkeypatch.setenv("RECORDLOOP_PROGRESS_REMOTE", str(bare))
    progress._last_push.clear()
    progress.report("r1", "0of3", {"iteration": 10, "best_d": 40})
    progress.report("r1", "0of3", {"iteration": 11, "best_d": 41})  # rate-limited: no second push
    progress.report("r1", "1of3", {"iteration": 5, "best_d": 30})
    log = subprocess.run(["git", "-C", str(bare), "log", "--format=%an|%s", "progress"], capture_output=True, text=True).stdout.split("\n")
    assert log[0] == "Derezar Master|progress: 1of3 5" and len(log) == 2  # single commit
    files = subprocess.run(["git", "-C", str(bare), "ls-tree", "--name-only", "progress"], capture_output=True, text=True).stdout.split()
    assert files == ["0of3.json", "1of3.json"]
    shown = json.loads(subprocess.run(["git", "-C", str(bare), "show", "progress:0of3.json"], capture_output=True, text=True).stdout)
    assert shown["iteration"] == 10
    monkeypatch.setenv("RECORDLOOP_PROGRESS_REMOTE", str(tmp_path / "missing"))
    assert progress.report("r1", "2of3", {"iteration": 1}, force=True)  # failing push never raises
