"""Budget ledger and monthly caps. Frozen wall: the self-editor never touches this file.

Ledger: results/ledger.jsonl (override with RECORDLOOP_LEDGER), one JSON line per LLM call.
Lanes: "search" (cap 60 USD / calendar month) and "selfedit" (cap 40 USD; practice runs also
charge this lane). USD is estimated from token counts and LIST prices, so free-tier routes
still count and the cap stays meaningful.

How calls get charged: engine/_llm_patch.py wraps OpenEvolve's OpenAILLM._call_api and calls
charge() with the token usage the API returned (falls back to chars/4 if usage is missing).
engine/_site/sitecustomize.py installs that wrapper in every worker process (fork or spawn).
`charge_from_log()` below is the fallback: it parses OpenEvolve's "LLM Token Usage" log lines.
"""
import json, os, re, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPS_USD = {"search": 60.0, "selfedit": 40.0}  # per calendar month (UTC)

# USD per 1M tokens (input, output). First substring match wins; last row is the default.
PRICES = [
    ("flash-lite", (0.10, 0.40)),
    ("flash", (0.30, 2.50)),
    ("gemini-2.5-pro", (1.25, 10.0)),
    ("pro", (1.25, 10.0)),
    ("best-coding", (3.0, 15.0)),
    ("", (1.0, 4.0)),
]


def ledger_path():
    return Path(os.environ.get("RECORDLOOP_LEDGER", ROOT / "results" / "ledger.jsonl"))


def estimate_usd(model, tokens_in, tokens_out):
    for key, (pin, pout) in PRICES:
        if key in model:
            return (tokens_in * pin + tokens_out * pout) / 1e6


def _month(ts=None):
    return (ts or datetime.now(timezone.utc)).strftime("%Y-%m")


def charge(lane, model, tokens_in, tokens_out):
    """Append one ledger line; returns the estimated USD."""
    usd = estimate_usd(model, tokens_in, tokens_out)
    rec = {"id": uuid.uuid4().hex[:8], "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "lane": lane,
           "model": model, "tokens_in": tokens_in, "tokens_out": tokens_out, "est_usd": round(usd, 6)}
    p = ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:  # single small write in append mode is atomic enough across processes
        f.write(json.dumps(rec) + "\n")
    return usd


def spent(lane):
    p, tot, m = ledger_path(), 0.0, _month()
    if not p.exists():
        return 0.0
    for line in p.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("lane") == lane and str(r.get("ts", ""))[:7] == m:
            tot += r.get("est_usd", 0.0)
    return tot


def remaining(lane):
    return CAPS_USD[lane] - spent(lane)


def paused(lane):
    return remaining(lane) <= 0


_LOG_RE = re.compile(r"LLM Token Usage \((.+?)\): prompt_tokens=(\d+), completion_tokens=(\d+)")


def charge_from_log(lane, log_text):
    """Fallback: charge from OpenEvolve log text. Returns number of calls charged."""
    n = 0
    for m in _LOG_RE.finditer(log_text):
        charge(lane, m.group(1), int(m.group(2)), int(m.group(3)))
        n += 1
    return n


if __name__ == "__main__":
    for lane in CAPS_USD:
        print(f"{lane}: spent {spent(lane):.2f} / {CAPS_USD[lane]:.0f} USD this month")
