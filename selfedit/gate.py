"""Strict gate: apply the proposed diff in a temp copy, score current vs candidate at equal budget and seeds.
KEEP only if mean score rises by >= 0.02 and no target falls by more than 0.1. Exit 0 = KEEP, 1 = DISCARD.
Usage: python selfedit/gate.py [--diff selfedit/out/proposal.diff] [--targets "172,21;200,21"]"""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from propose import valid  # noqa: E402

MIN_GAIN, MAX_DROP = 0.02, 0.1


def practice(sd, out, targets):
    cmd = [sys.executable, str(ROOT / "practice" / "run_practice.py"), "--strategy-dir", str(sd), "--out", str(out)]
    if targets:
        cmd += ["--targets", targets]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"DISCARD (practice failed): {r.stderr[-300:]}")
    return json.loads(Path(out).read_text())


def decide(base, cand):
    drops = [(b["n"], b["k"], b["score"] - c["score"]) for b, c in zip(base["targets"], cand["targets"])]
    ok = cand["mean_score"] - base["mean_score"] >= MIN_GAIN - 1e-9 and all(d <= MAX_DROP + 1e-9 for _, _, d in drops)
    return ok, drops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", default=str(ROOT / "selfedit" / "out" / "proposal.diff"))
    ap.add_argument("--targets")
    args = ap.parse_args()
    diff = Path(args.diff).read_text()
    err = valid(diff)
    if err:
        print("DISCARD (invalid diff):", err); return 1
    tmp = Path(tempfile.mkdtemp(prefix="gate_"))
    cand_root = tmp / "cand"
    cand_root.mkdir()
    shutil.copytree(ROOT / "strategy", cand_root / "strategy", ignore=shutil.ignore_patterns("__pycache__"))
    p = subprocess.run(["git", "apply", "-p1", str(Path(args.diff).resolve())], cwd=cand_root,
                       capture_output=True, text=True)
    if p.returncode:
        print("DISCARD (does not apply):", p.stderr[:300]); return 1
    base = practice(ROOT / "strategy", tmp / "base.json", args.targets)
    cand = practice(cand_root / "strategy", tmp / "cand.json", args.targets)
    ok, drops = decide(base, cand)
    worst = max(drops, key=lambda t: t[2])
    print(f"{'KEEP' if ok else 'DISCARD'}: current={base['mean_score']:.4f} candidate={cand['mean_score']:.4f} "
          f"gain={cand['mean_score'] - base['mean_score']:+.4f} (need >= {MIN_GAIN}); worst target drop "
          f"{worst[2]:.3f} at [{worst[0]},{worst[1]}] (limit {MAX_DROP})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
