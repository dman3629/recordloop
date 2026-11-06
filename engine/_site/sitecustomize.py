# Loaded in worker processes (via PYTHONPATH) when RECORDLOOP_PATCH=1.
import os
if os.environ.get("RECORDLOOP_PATCH") == "1":
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import _llm_patch
        _llm_patch.install()
    except Exception:
        pass
