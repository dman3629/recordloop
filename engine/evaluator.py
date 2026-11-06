"""OpenEvolve evaluator for recordloop. evaluate(program_path) -> metrics dict.

Env (all optional): RECORDLOOP_TARGET "n,k" | RECORDLOOP_TABLE (table json) | RECORDLOOP_CERTS (cert dir)
RECORDLOOP_CHECKER (checker command) | RECORDLOOP_TIME_BUDGET | RECORDLOOP_MAX_CANDIDATES
RECORDLOOP_STRATEGY_DIR | RECORDLOOP_RUN_ID | RECORDLOOP_STRATEGY_VERSION
The checker is called as a subprocess and is never imported or modified here.
"""
import hashlib, json, os, signal, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
MAX_TIME_BUDGET = 120.0


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checker_cmd():
    env = os.environ.get("RECORDLOOP_CHECKER")
    if env:
        return env.split()
    real = ROOT / "checker" / "mindist"
    if real.exists():
        return [str(real)]
    return [sys.executable, str(ENGINE / "_stub_checker.py")]  # local tests only, k <= 12


def checker_file(cmd):
    c = ROOT / "checker" / "mindist.c"
    if cmd == [str(ROOT / "checker" / "mindist")] and c.exists():
        return c  # hash the source: the binary differs between builds
    return Path(cmd[-1]) if len(cmd) > 1 and cmd[-1].endswith(".py") else Path(cmd[0])


def load_table():
    p = Path(os.environ.get("RECORDLOOP_TABLE", ROOT / "tables" / "gf2_bounds.json"))
    if not p.exists():
        return {"fetched": "none", "bounds": {}}
    return json.loads(p.read_text())


def active_target():
    t = os.environ.get("RECORDLOOP_TARGET")
    if t:
        n, k = (int(x) for x in t.split(","))
        return n, k
    sd = Path(os.environ.get("RECORDLOOP_STRATEGY_DIR", ROOT / "strategy"))
    for e in yaml.safe_load((sd / "schedule.yaml").read_text()).get("targets", []):
        if isinstance(e.get("n"), int) and isinstance(e.get("k"), int):
            return e["n"], e["k"]
    raise RuntimeError("no active target")


def _settings():
    cfg = yaml.safe_load((ENGINE / "config.yaml").read_text()).get("recordloop", {})
    tb = float(os.environ.get("RECORDLOOP_TIME_BUDGET", cfg.get("time_budget_s", 60)))
    mc = int(os.environ.get("RECORDLOOP_MAX_CANDIDATES", cfg.get("max_candidates", 8)))
    return min(max(tb, 1.0), MAX_TIME_BUDGET), mc, float(cfg.get("check_timeout_s", 60))


def run_program(program_path, n, k, budget, seed):
    """Run search() in a child process with a hard kill. Returns (candidates, error)."""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0", "HOME": tempfile.gettempdir()}
    cmd = [sys.executable, "-I", str(ENGINE / "_run_program.py"), str(program_path), str(n), str(k),
           str(budget), str(seed)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=budget + 10)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        return [], "timeout"
    for line in out.splitlines():
        if line.startswith("RESULT:"):
            return json.loads(line[7:])["candidates"], None
    return [], "program_failed: " + err.strip()[-600:]


def check(rows, timeout):
    """Exact distance via the frozen checker. Returns dict or None."""
    n, k = len(rows[0]), len(rows)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(f"{n} {k}\n" + "\n".join(rows) + "\n")
        name = f.name
    try:
        r = subprocess.run(checker_cmd() + [name], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return None
    finally:
        os.unlink(name)


def _git_sha():
    v = os.environ.get("RECORDLOOP_STRATEGY_VERSION")
    if v:
        return v
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def write_cert(rows, d, lower, upper, table, chk, program_path):
    n, k = len(rows[0]), len(rows)
    cdir = Path(os.environ.get("RECORDLOOP_CERTS", ROOT / "certs" / "pending"))
    cdir.mkdir(parents=True, exist_ok=True)
    sha8 = hashlib.sha256("".join(rows).encode()).hexdigest()[:8]
    cert = {"n": n, "k": k, "d": d, "generator_rows": rows,
            "table_lower_at_run": lower, "table_upper_at_run": upper,
            "table_fetched": table.get("fetched", "none"),
            "checker_version": chk.get("checker_version", "unknown"),
            "checker_sha256": _sha256(checker_file(checker_cmd())),
            "program_sha256": _sha256(program_path),
            "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": os.environ.get("RECORDLOOP_RUN_ID", "local"),
            "strategy_version": _git_sha()}
    path = cdir / f"{n}_{k}_{d}_{sha8}.json"
    path.write_text(json.dumps(cert, indent=1))
    return str(path)


def evaluate(program_path):
    t0 = time.time()
    try:
        n, k = active_target()
        table = load_table()
        lower, upper = table["bounds"].get(f"{n},{k}", [0, n - k + 1])
        budget, max_cand, chk_timeout = _settings()
        seed = int(os.environ.get("RECORDLOOP_SEED", "1"))
        cands, err = run_program(program_path, n, k, budget, seed)
        if err:
            return {"combined_score": 0.0, "best_d": 0, "table_lower": lower, "beats_table": 0,
                    "candidates": 0, "elapsed_s": time.time() - t0, "error": err}
        best_d, best_rows, best_chk, seen, checked = 0, None, None, set(), 0
        hard_end = t0 + budget + 10 + 150  # total evaluation wall cap, below evaluator.timeout (300)
        for rows in cands:
            key = tuple(rows)
            if key in seen:
                continue
            seen.add(key)
            if checked >= max_cand or time.time() > hard_end:
                break
            checked += 1
            res = check(rows, min(chk_timeout, max(5.0, hard_end - time.time())))
            if res and res.get("d", 0) > best_d:
                best_d, best_rows, best_chk = res["d"], rows, res
        beats = 0
        if best_d > upper:  # impossible if the table is right: treat as a bug, never as a record
            return {"combined_score": 0.0, "best_d": best_d, "table_lower": lower, "beats_table": 0,
                    "candidates": checked, "elapsed_s": time.time() - t0, "error": "d_exceeds_upper_bound"}
        if best_rows and best_d > lower and f"{n},{k}" in table["bounds"]:
            beats = 1
            write_cert(best_rows, best_d, lower, upper, table, best_chk, program_path)
        return {"combined_score": best_d / max(upper, 1), "best_d": best_d, "table_lower": lower,
                "table_upper": upper, "beats_table": beats, "candidates": checked,
                "elapsed_s": time.time() - t0}
    except Exception as e:  # never crash the worker
        return {"combined_score": 0.0, "best_d": 0, "beats_table": 0, "candidates": 0,
                "elapsed_s": time.time() - t0, "error": f"evaluator_error: {e}"}


if __name__ == "__main__":
    print(json.dumps(evaluate(sys.argv[1])))
