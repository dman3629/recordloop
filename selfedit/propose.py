"""Ask the LLM for ONE change to strategy/ as a unified diff. Rejects diffs touching anything else.
Usage: python selfedit/propose.py [--n-runs 5] [--out-dir selfedit/out]. Needs LLM_API_KEY (+ LLM_BASE_URL)."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import budget  # noqa: E402

MAX_DIFF_LINES = 200


def diff_paths(diff):
    paths = set()
    for line in diff.splitlines():
        m = re.match(r"^(?:---|\+\+\+) (?:[ab]/)?(\S+)", line)
        if m and m.group(1) != "/dev/null":
            paths.add(m.group(1))
    return paths


def valid(diff):
    ps = diff_paths(diff)
    if not ps:
        return "empty diff"
    bad = [p for p in ps if not p.startswith("strategy/") or ".." in p]
    if bad:
        return f"touches outside strategy/: {bad}"
    if len(diff.splitlines()) > MAX_DIFF_LINES:
        return "diff too long"
    return None


def tail(dirpath, n):
    fs = sorted(Path(dirpath).glob("*.json"), key=lambda p: p.stat().st_mtime)[-n:]
    return [json.loads(p.read_text()) for p in fs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-runs", type=int, default=5)
    ap.add_argument("--out-dir", default=str(ROOT / "selfedit" / "out"))
    args = ap.parse_args()
    if budget.paused("selfedit"):
        print("BUDGET_PAUSED lane=selfedit"); return 0
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["LLM_API_KEY"], max_retries=6,
                    base_url=os.environ.get("LLM_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta/openai/")
    sdir = ROOT / "strategy"
    files = {str(p.relative_to(ROOT)): p.read_text() for p in sorted(sdir.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    runs = [{k: r.get(k) for k in ("run_id", "targets", "wall_s")} for r in tail(ROOT / "results" / "runs", args.n_runs)]
    prac = [{k: r.get(k) for k in ("strategy_sha", "mean_score")} for r in tail(ROOT / "results" / "practice", 5)]
    prompt = ("You improve the STRATEGY folder of a loop that searches for binary linear codes with record minimum distance.\n"
              "Propose exactly ONE small change that should raise the practice score (mean over practice targets).\n"
              "Output a single unified diff (git format, paths like a/strategy/...) inside one ```diff fence, then one line "
              "starting with `SUMMARY:` (under 70 characters, plain words). Touch only files under strategy/. No other text.\n\n"
              f"Recent search runs:\n{json.dumps(runs, default=str)[:6000]}\n\nRecent practice scores:\n{json.dumps(prac)}\n\n"
              + "\n\n".join(f"=== {k} ===\n{v}" for k, v in files.items()))
    model = yaml.safe_load((sdir / "operators.yaml").read_text())["models"][0]["name"]
    r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.7)
    u = r.usage
    budget.charge("selfedit", model, getattr(u, "prompt_tokens", 0) or len(prompt) // 4,
                  getattr(u, "completion_tokens", 0) or 1000)
    text = r.choices[0].message.content or ""
    m = re.search(r"```(?:diff)?\n(.*?)```", text, re.S)
    s = re.search(r"SUMMARY:\s*(.+)", text)
    if not m:
        print("REJECT: no diff in reply"); return 1
    diff = m.group(1).rstrip("\n") + "\n"
    err = valid(diff)
    if err:
        print("REJECT:", err); return 1
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "proposal.diff").write_text(diff)
    msg = (s.group(1).strip() if s else "strategy tweak")[:70]
    (out / "proposal.msg").write_text(msg)
    chk = subprocess.run(["git", "apply", "--check", str(out / "proposal.diff")], cwd=ROOT, capture_output=True, text=True)
    if chk.returncode:
        print("REJECT: does not apply:", chk.stderr[:300]); return 1
    print(f"PROPOSED: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
