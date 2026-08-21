import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_brain import Brain

_BRAIN = Brain()


def agent(obs, config=None):
    global _BRAIN
    try:
        if obs.get("step", 0) == 0 or (obs.get("day", 0) == 0 and obs.get("hour", 0) == 0):
            _BRAIN.reset()
        return _BRAIN.act(obs)
    except Exception:
        import traceback
        traceback.print_exc()
        return {"farmer": ["PASS"], "hands": [], "market": []}
