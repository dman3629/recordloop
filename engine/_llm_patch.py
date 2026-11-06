"""Wraps OpenEvolve's OpenAILLM._call_api to charge the budget ledger after each response, and feeds a
circuit breaker: every call outcome is appended to the file named by RECORDLOOP_BREAKER (OpenEvolve calls the
LLM from worker processes, so the state lives in a file the runner polls). The breaker trips after
MAX_CONSECUTIVE_FAILS failed calls in a row, or when attempts keep failing and no call has succeeded for
NO_SUCCESS_S seconds. The runner then shuts the run down cleanly with stopped_reason "llm_unavailable"."""
import os
import time

MAX_CONSECUTIVE_FAILS = 25
NO_SUCCESS_S = 20 * 60


def _record(kind):
    path = os.environ.get("RECORDLOOP_BREAKER")
    if path:
        try:
            with open(path, "a") as f:  # one short append is atomic enough across processes
                f.write(f"{kind} {time.time():.3f}\n")
        except OSError:
            pass


def breaker_init(path):
    """Start a fresh breaker file; the no-success window counts from now."""
    with open(path, "w") as f:
        f.write(f"S {time.time():.3f}\n")


def breaker_tripped(path, now=None):
    """Return a reason string if the breaker has tripped, else None."""
    try:
        lines = [l.split() for l in open(path).read().splitlines() if l.strip()]
    except OSError:
        return None
    now = now or time.time()
    fails, last_ok = 0, None
    for kind, ts in lines:
        if kind == "S":
            fails, last_ok = 0, float(ts)
        else:
            fails += 1
    if fails >= MAX_CONSECUTIVE_FAILS:
        return f"{fails} consecutive failed LLM calls"
    if fails and last_ok is not None and now - last_ok > NO_SUCCESS_S:
        return f"no successful LLM call for {int(now - last_ok)} s"
    return None


class BudgetExhausted(RuntimeError):
    pass


def install():
    from openevolve.llm import openai as oai
    if getattr(oai.OpenAILLM, "_recordloop_patched", False):
        return
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import budget
    orig = oai.OpenAILLM._call_api

    async def wrapped(self, params):
        lane = os.environ.get("RECORDLOOP_LANE", "search")
        if budget.remaining(lane) <= 0:
            raise BudgetExhausted(f"BUDGET_PAUSED lane={lane}")
        self.last_usage = None
        try:
            out = await orig(self, params)
        except Exception:
            _record("F")
            raise
        _record("S")
        u = self.last_usage or {}
        tin = u.get("prompt_tokens") or sum(len(str(m.get("content", ""))) for m in params["messages"]) // 4
        tout = u.get("completion_tokens") or len(out or "") // 4
        budget.charge(lane, str(self.model), tin, tout)
        return out

    oai.OpenAILLM._call_api = wrapped
    oai.OpenAILLM._recordloop_patched = True
