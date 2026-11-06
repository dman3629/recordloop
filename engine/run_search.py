"""Run the inner search loop: pick targets, run OpenEvolve with resume, stop on a wall clock, write a summary.

Env: LLM_API_KEY (required), LLM_BASE_URL (default Anthropic OpenAI-compatible endpoint; any OpenAI-compatible
URL works, including a gateway), RECORDLOOP_RUN_ID. Exit 0 also when paused by the budget cap (BUDGET_PAUSED).
"""
import argparse, asyncio, json, os, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
import budget  # noqa: E402
import _llm_patch  # noqa: E402
import progress  # noqa: E402

DEFAULT_BASE = "https://api.anthropic.com/v1/"
CLAMPS = {"temperature": (0.0, 1.5), "max_tokens": (1024, 16384), "population_size": (10, 1000),
          "archive_size": (5, 200), "num_islands": (1, 5), "migration_interval": (5, 200),
          "migration_rate": (0.0, 0.5), "elite_selection_ratio": (0.0, 0.5),
          "exploration_ratio": (0.0, 1.0), "exploitation_ratio": (0.0, 1.0),
          "full_rewrite_probability": (0.0, 1.0), "num_top_programs": (0, 6), "num_diverse_programs": (0, 6)}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def load_targets(sd, override, group):
    if override:
        ts = [{"n": int(a), "k": int(b), "iterations_share": 1.0}
              for a, b in (x.split(",") for x in override.split(";"))]
    else:
        sch = yaml.safe_load((sd / "schedule.yaml").read_text())
        ts = sch.get("targets", [])
        if sch.get("fill_from_targets") and (not ts or any(not t.get("n") for t in ts)):
            rows = json.loads((ROOT / "tables" / "targets.json").read_text())[: int(sch.get("count", 6))]
            ts = [{"n": r["n"], "k": r["k"], "iterations_share": 1.0} for r in rows]
    if group:
        i, n = (int(x) for x in group.split("/"))
        ts = ts[i::n]
    return ts


def build_config(sd, set_overrides):
    from openevolve.config import Config
    d = yaml.safe_load((ENGINE / "config.yaml").read_text())
    rl = d.pop("recordloop", {})
    op = yaml.safe_load((sd / "operators.yaml").read_text())
    cl = lambda key: clamp(op[key], *CLAMPS[key]) if op.get(key) is not None else None
    models = [{"name": str(m["name"]), "weight": float(m["weight"])} for m in op["models"][:4] if m["weight"] > 0]
    d["llm"].update(models=models, api_base=os.environ.get("LLM_BASE_URL") or DEFAULT_BASE,
                    api_key=os.environ["LLM_API_KEY"], temperature=cl("temperature"),
                    max_tokens=int(cl("max_tokens")))
    if op.get("top_p") is not None:
        d["llm"]["top_p"] = op["top_p"]
    for k in ("population_size", "archive_size", "num_islands", "migration_interval", "migration_rate",
              "elite_selection_ratio", "exploration_ratio", "exploitation_ratio"):
        if op.get(k) is not None:
            d["database"][k] = cl(k)
    for k in ("num_top_programs", "num_diverse_programs"):
        if op.get(k) is not None:
            d["prompt"][k] = int(cl(k))
    d["full_rewrite_probability"] = cl("full_rewrite_probability") or 0.0
    sysmsg = (sd / "prompts" / "system.md").read_text() + "\n\n" + (sd / "prompts" / "mutation_hints.md").read_text()
    d["prompt"]["system_message"] = sysmsg
    for item in set_overrides:  # --set a.b.c=value (YAML-parsed)
        path, val = item.split("=", 1)
        cur = d
        for p in path.split(".")[:-1]:
            cur = cur[p]
        cur[path.split(".")[-1]] = yaml.safe_load(val)
    ev = op.get("eval", {})
    force = os.environ.get("RECORDLOOP_FORCE_TIME_BUDGET")  # set by practice so budgets are equal
    if force:
        ev = {"time_budget_s": float(force), "max_candidates": ev.get("max_candidates", 8)}
    return Config.from_dict(d), {"time_budget_s": clamp(ev.get("time_budget_s", rl.get("time_budget_s", 40)), 5, 120),
                                 "max_candidates": int(clamp(ev.get("max_candidates", rl.get("max_candidates", 8)), 1, 16))}


def latest_checkpoint(out):
    cps = [p for p in (out / "checkpoints").glob("checkpoint_*") if p.name.split("_")[-1].isdigit()] \
        if (out / "checkpoints").exists() else []
    return max(cps, key=lambda p: int(p.name.split("_")[-1])) if cps else None


async def run_target(t, cfg, args, deadline, iters, ev_env):
    from openevolve import OpenEvolve
    n, k = t["n"], t["k"]
    out = Path(args.state_dir) / f"{n}_{k}"
    ckpt = None if args.no_resume else latest_checkpoint(out)
    os.environ["RECORDLOOP_TARGET"] = f"{n},{k}"
    os.environ["RECORDLOOP_TIME_BUDGET"] = str(ev_env["time_budget_s"])
    os.environ["RECORDLOOP_MAX_CANDIDATES"] = str(ev_env["max_candidates"])
    certs_dir = Path(os.environ.get("RECORDLOOP_CERTS", ROOT / "certs" / "pending"))
    before = set(certs_dir.glob("*.json")) if certs_dir.exists() else set()
    spent0 = budget.spent(args.lane)
    oe = OpenEvolve(str(ENGINE / "initial_program.py"), str(ENGINE / "evaluator.py"), cfg, output_dir=str(out))
    status = "done"
    group_tag = (args.group or "all").replace("/", "of")
    last_rep = 0

    def snap(stage, force=False):
        try:
            b = oe.database.get_best_program()
            m = (b.metrics if b else None) or {}
            ok, bad, ok_at, bstate = progress.breaker_stats(os.environ["RECORDLOOP_BREAKER"],
                                                            _llm_patch.breaker_tripped(os.environ["RECORDLOOP_BREAKER"]))
            progress.report(os.environ.get("RECORDLOOP_RUN_ID"), group_tag, {
                "n": n, "k": k, "iteration": oe.database.last_iteration, "best_d": m.get("best_d"),
                "table_lower": m.get("table_lower"), "table_upper": m.get("table_upper"),
                "beats_table": m.get("beats_table"), "llm_calls_ok": ok, "llm_calls_failed": bad,
                "last_llm_ok_at": ok_at, "breaker_state": bstate, "stage": stage,
                "est_usd": round(budget.spent(args.lane) - spent0, 4)}, force=force)
        except Exception as e:  # noqa: BLE001  progress must never hurt the search
            print(f"progress: snapshot failed: {e}", flush=True)

    async def watcher():
        nonlocal status, last_rep
        while True:
            await asyncio.sleep(3)
            it = oe.database.last_iteration
            if it >= last_rep + 10:
                last_rep = it
                await asyncio.to_thread(snap, "running")
            if time.time() > deadline or budget.paused(args.lane):
                status = "budget_paused" if budget.paused(args.lane) else "time_stop"
                pc = getattr(oe, "parallel_controller", None)
                if pc:
                    pc.request_shutdown()
                return
            reason = _llm_patch.breaker_tripped(os.environ["RECORDLOOP_BREAKER"])
            if reason:
                print(f"LLM_UNAVAILABLE: {reason}; stopping the run", flush=True)
                status = "llm_unavailable"
                pc = getattr(oe, "parallel_controller", None)
                if pc:
                    pc.request_shutdown()
                return

    w = asyncio.create_task(watcher())
    err = None
    try:
        await oe.run(iterations=iters, checkpoint_path=str(ckpt) if ckpt else None)
    except Exception as e:  # keep going with the other targets
        err = str(e)[:300]
        status = status if status == "llm_unavailable" else "error"
    finally:
        w.cancel()
    snap(status, force=True)
    last = oe.database.last_iteration
    if last > 0:
        oe._save_checkpoint(last)
    best = oe.database.get_best_program()
    new = sorted(p.name for p in (set(certs_dir.glob("*.json")) - before)) if certs_dir.exists() else []
    return {"n": n, "k": k, "status": status, "error": err, "resumed_from": str(ckpt) if ckpt else None,
            "iterations_reached": last, "best_metrics": best.metrics if best else None,
            "new_certs": new, "usd_spent_est": round(budget.spent(args.lane) - spent0, 4)}


async def main_async(args):
    sd = Path(args.strategy_dir)
    if budget.paused(args.lane):
        print(f"BUDGET_PAUSED lane={args.lane}")
        return 0
    if not os.environ.get("LLM_API_KEY"):
        print("LLM_API_KEY is required (key for any OpenAI-compatible endpoint; see README)", file=sys.stderr)
        return 1
    run_id = args.run_id or os.environ.get("RECORDLOOP_RUN_ID") or datetime.now(timezone.utc).strftime("local-%Y%m%dT%H%M%S")
    os.environ.update(RECORDLOOP_RUN_ID=run_id, RECORDLOOP_LANE=args.lane, RECORDLOOP_STRATEGY_DIR=str(sd),
                      RECORDLOOP_PATCH="1")
    os.environ["PYTHONPATH"] = str(ENGINE / "_site") + os.pathsep + os.environ.get("PYTHONPATH", "")
    _llm_patch.install()
    bpath = os.path.join(tempfile.mkdtemp(prefix="recordloop-"), "breaker.log")
    _llm_patch.breaker_init(bpath)
    os.environ["RECORDLOOP_BREAKER"] = bpath
    targets = load_targets(sd, args.targets, args.group)
    cfg, ev_env = build_config(sd, args.set)
    total_iters = args.iterations or cfg.max_iterations
    start = time.time()
    stop_at = start + args.stop_after_s
    shares = [float(t.get("iterations_share", 1.0)) for t in targets]
    results, left, stopped_reason = [], sum(shares), None
    for t, s in zip(targets, shares):
        now = time.time()
        if now >= stop_at or budget.paused(args.lane):
            break
        deadline = now + (stop_at - now) * s / left
        iters = max(1, round(total_iters * s / sum(shares)))
        results.append(await run_target(t, cfg, args, deadline, iters, ev_env))
        left -= s
        if results[-1]["status"] == "llm_unavailable":
            stopped_reason = "llm_unavailable"
            break
    summary = {"run_id": run_id, "lane": args.lane, "started": datetime.fromtimestamp(start, timezone.utc).isoformat(timespec="seconds"),
               "wall_s": round(time.time() - start, 1), "targets": results,
               "stopped_reason": stopped_reason,
               "budget_remaining_usd": round(budget.remaining(args.lane), 2),
               "paused": budget.paused(args.lane)}
    outp = Path(args.summary_out) if args.summary_out else ROOT / "results" / "runs" / f"{run_id}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))
    if summary["paused"]:
        print(f"BUDGET_PAUSED lane={args.lane}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy-dir", default=str(ROOT / "strategy"))
    ap.add_argument("--targets", help='override, e.g. "172,21;200,21"')
    ap.add_argument("--group", help="i/N: take targets[i::N] (for the Actions matrix)")
    ap.add_argument("--iterations", type=int, help="total iterations across targets (default config max_iterations)")
    ap.add_argument("--stop-after-s", type=float, default=5.5 * 3600)
    ap.add_argument("--state-dir", default=str(ROOT / "openevolve_state"))
    ap.add_argument("--run-id")
    ap.add_argument("--lane", default="search", choices=["search", "selfedit"])
    ap.add_argument("--summary-out")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--set", action="append", default=[], help="dotted config override, e.g. llm.timeout=30")
    sys.exit(asyncio.run(main_async(ap.parse_args())))


if __name__ == "__main__":
    main()
