"""Score a strategy directory on the practice set.
Usage: python practice/run_practice.py [--strategy-dir DIR] [--targets 172,21;...] [--out FILE]
Writes results/practice/<strategy_sha>.json (sha256 over the strategy dir's files). Needs LLM_API_KEY."""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def strategy_sha(sd):
    h = hashlib.sha256()
    for p in sorted(Path(sd).rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(sd)).encode()); h.update(p.read_bytes())
    return h.hexdigest()[:12]


def score(best_d, old, rec):
    return max(0.0, min(1.0, (best_d - old) / (rec - old)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy-dir", default=str(ROOT / "strategy"))
    ap.add_argument("--targets", help='subset, e.g. "172,21;200,21"')
    ap.add_argument("--out")
    ap.add_argument("--lane", default="selfedit")
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    ps = json.loads((HERE / "practice_set.json").read_text())["targets"]
    if args.targets:
        want = {tuple(int(x) for x in t.split(",")) for t in args.targets.split(";")}
        ps = [t for t in ps if (t["n"], t["k"]) in want]
    if any(t["old_lower"] is None for t in ps):
        sys.exit("old_lower missing: run practice/fill_old_bounds.py")
    sha = strategy_sha(args.strategy_dir)
    tmp = Path(tempfile.mkdtemp(prefix="practice_"))
    table = {"fetched": "practice", "q": 2,
             "bounds": {f"{t['n']},{t['k']}": [t["old_lower"], t["upper"]] for t in ps}}
    (tmp / "table.json").write_text(json.dumps(table))
    results = []
    for t in ps:
        per_seed = []
        for seed in cfg["seeds"]:
            env = dict(os.environ, RECORDLOOP_TABLE=str(tmp / "table.json"), RECORDLOOP_CERTS=str(tmp / "certs"),
                       RECORDLOOP_FORCE_TIME_BUDGET=str(cfg["time_budget_s"]), RECORDLOOP_SEED=str(seed))
            summ = tmp / f"s_{t['n']}_{t['k']}_{seed}.json"
            cmd = [sys.executable, str(ROOT / "engine" / "run_search.py"), "--strategy-dir", args.strategy_dir,
                   "--targets", f"{t['n']},{t['k']}", "--iterations", str(cfg["iterations_per_target"]),
                   "--stop-after-s", str(cfg["stop_after_s_per_target"]), "--lane", args.lane, "--no-resume",
                   "--state-dir", str(tmp / f"state_{t['n']}_{t['k']}_{seed}"), "--summary-out", str(summ),
                   "--run-id", f"practice-{sha}-{t['n']}-{t['k']}-{seed}",
                   "--set", f"random_seed={seed}", "--set", f"database.random_seed={seed}"]
            r = subprocess.run(cmd, env=env, capture_output=True, text=True)
            d = 0
            if summ.exists():
                tg = json.loads(summ.read_text())["targets"]
                d = int((tg[0]["best_metrics"] or {}).get("best_d", 0)) if tg else 0
            else:
                print(f"run failed {t['n']},{t['k']} seed {seed}: {r.stderr[-300:]}", file=sys.stderr)
            per_seed.append({"seed": seed, "best_d": d, "score": score(d, t["old_lower"], t["record_d"])})
        results.append({"n": t["n"], "k": t["k"], "old_lower": t["old_lower"], "record_d": t["record_d"],
                        "per_seed": per_seed, "score": sum(s["score"] for s in per_seed) / len(per_seed)})
    out = {"strategy_sha": sha, "strategy_dir": str(args.strategy_dir), "config": cfg,
           "mean_score": sum(r["score"] for r in results) / len(results), "targets": results}
    path = Path(args.out) if args.out else ROOT / "results" / "practice" / f"{sha}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps({"strategy_sha": sha, "mean_score": out["mean_score"], "file": str(path)}))


if __name__ == "__main__":
    main()
