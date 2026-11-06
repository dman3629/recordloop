"""Live progress for long runs. Job logs are locked until a job ends, so each group writes progress/<group_tag>.json
and, with RECORDLOOP_PROGRESS_PUSH=1, force-pushes it to the orphan branch `progress` (one commit, all groups'
files). Never raises: a failed push is logged and the search carries on. Pushes are limited to one per 5 minutes
per group unless force=True (used at stops).

Env: RECORDLOOP_PROGRESS_PUSH=1 enables the push; RECORDLOOP_PROGRESS_REMOTE overrides the remote (name or path,
default origin); RECORDLOOP_PROGRESS_DIR overrides the output dir (default <repo>/progress).
The push runs in a throwaway clone and reuses the auth header that actions/checkout persisted in the repo config.
"""
import json, os, shutil, subprocess, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_PUSH_S = 300
BRANCH = "progress"
FIELDS = ("run_id", "n", "k", "iteration", "best_d", "table_lower", "table_upper", "beats_table", "llm_calls_ok",
          "llm_calls_failed", "last_llm_ok_at", "breaker_state", "est_usd")
_last_push = {}


def breaker_stats(path, tripped_reason=None):
    """(ok, failed, last_ok_iso, state) from the breaker file (lines 'S ts' / 'F ts')."""
    ok = failed = 0
    last = None
    try:
        for line in open(path).read().splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            if parts[0] == "S":
                ok += 1
                last = float(parts[1])
            else:
                failed += 1
    except (OSError, ValueError):
        pass
    ok = max(ok - 1, 0)  # the first S line is the init marker, not a call
    iso = datetime.fromtimestamp(last, timezone.utc).isoformat(timespec="seconds") if last and ok else None
    return ok, failed, iso, ("tripped: " + tripped_reason) if tripped_reason else "ok"


def _git(args, cwd, env=None):
    return subprocess.run(["git"] + args, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)


def _push(src_file, group_tag, iteration):
    remote = os.environ.get("RECORDLOOP_PROGRESS_REMOTE") or "origin"
    is_path = os.path.exists(remote)
    url = remote if is_path else _git(["remote", "get-url", remote], ROOT).stdout.strip()
    if not url:
        raise RuntimeError(f"no remote url for {remote}")
    auth = []  # auth header that actions/checkout persisted in the main checkout's config
    if not is_path:
        out = _git(["config", "--get-regexp", r"^http\..*\.extraheader$"], ROOT).stdout
        for line in out.splitlines():
            key, _, val = line.partition(" ")
            auth += ["-c", f"{key}={val}"]
    tmp = tempfile.mkdtemp(prefix="progress-")
    try:
        g = lambda *a: _git(auth + list(a), tmp)
        g("init", "-q")
        g("symbolic-ref", "HEAD", f"refs/heads/{BRANCH}")
        g("remote", "add", "origin", url)
        if g("fetch", "-q", "--depth", "1", "origin", BRANCH).returncode == 0:
            g("checkout", "-q", "FETCH_HEAD", "--", ".")  # keep the other groups' files
        shutil.copy(src_file, Path(tmp) / f"{group_tag}.json")
        g("add", "-A")
        r = g("-c", "user.name=Derezar Master", "-c", "user.email=derezarmaster@gmail.com", "commit", "-q",
              "-m", f"progress: {group_tag} {iteration}")
        if r.returncode:
            raise RuntimeError("commit failed: " + r.stderr.strip()[:200])
        r = g("push", "-q", "--force", "origin", f"{BRANCH}:{BRANCH}")
        if r.returncode:
            raise RuntimeError("push failed: " + r.stderr.strip()[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def report(run_id, group_tag, payload, force=False):
    """Write progress/<group_tag>.json; push it when enabled. Returns the path written (or None). Never raises."""
    try:
        d = {f: payload.get(f) for f in FIELDS}
        d["run_id"] = run_id
        d["group"] = group_tag
        d["stage"] = payload.get("stage")
        d["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        outdir = Path(os.environ.get("RECORDLOOP_PROGRESS_DIR") or ROOT / "progress")
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / f"{group_tag}.json"
        p.write_text(json.dumps(d, indent=1, default=str))
    except Exception as e:  # noqa: BLE001
        print(f"progress: write failed: {e}", flush=True)
        return None
    if os.environ.get("RECORDLOOP_PROGRESS_PUSH") == "1":
        now = time.time()
        if force or now - _last_push.get(group_tag, 0) >= MIN_PUSH_S:
            _last_push[group_tag] = now
            try:
                _push(p, group_tag, d["iteration"])
            except Exception as e:  # noqa: BLE001
                print(f"progress: push failed: {e}", flush=True)
    return p
