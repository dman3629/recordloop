"""Wraps OpenEvolve's OpenAILLM._call_api to charge the budget ledger after each response."""
import os


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
        out = await orig(self, params)
        u = self.last_usage or {}
        tin = u.get("prompt_tokens") or sum(len(str(m.get("content", ""))) for m in params["messages"]) // 4
        tout = u.get("completion_tokens") or len(out or "") // 4
        budget.charge(lane, str(self.model), tin, tout)
        return out

    oai.OpenAILLM._call_api = wrapped
    oai.OpenAILLM._recordloop_patched = True
