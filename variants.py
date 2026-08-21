"""Named agent variants for benchmarking."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_brain import Brain, DEFAULTS

CHAMP = {
    "land_buffer_per_tile": 0.0,
    "land_buffer": 500,
    "hire_overhead": 3.5,
    "max_hands": 12,
    "sticky_bonus": 1.0,
    "disc_poor": 0.94,
    "cap_lambda": 0.0,
    "opp_weight": 1.0,
    "cap_mu": 4.0,
}

def d(**kw):
    p = dict(CHAMP); p.update(kw); return p

VARIANTS = {"champ": d()}

def add(name, **kw):
    VARIANTS[name] = d(**kw)

# hiring
for v in (2.8, 3.2, 4.0, 4.6):
    add("ovh%d" % (v * 10), hire_overhead=v)
for v in (8, 10, 11, 13, 14):
    add("H%d" % v, max_hands=v)
for v in (0.03, 0.09, 0.15):
    add("hcf%d" % (v * 100), hire_cap_frac=v)
for v in (25.0, 150.0, 400.0):
    add("hca%d" % v, hire_cap_abs=v)
# economy
for v in (0.82, 0.85, 0.92, 0.95, 0.97):
    add("dp%d" % (v * 100), disc_poor=v)
add("flat", disc_poor=1.0, disc_rich=1.0)
for v in (0.92, 0.95, 0.999):
    for w in (0.88, 0.94):
        add("dr%d_dp%d" % (v * 1000, w * 100), disc_rich=v, disc_poor=w)
for v in (0.92, 0.999):
    add("dr%d" % (v * 1000), disc_rich=v)
for v in (800.0, 1500.0, 2200.0, 4500.0):
    add("ct%d" % v, cash_target=v)
for v in (0.15, 0.22, 0.45, 0.65):
    add("keep%d" % (v * 100), keep_frac=v)
# logistics
for v in (3, 6, 14):
    add("drop%d" % v, drop_threshold=v)
for v in (0.3, 0.42, 0.7, 1.0):
    add("decay%d" % (v * 100), dist_decay=v)
# farm composition
for v in (10, 16, 30, 45):
    add("anim%d" % v, animal_target=v)
for v in (300, 1200, 2000):
    add("acf%d" % v, animal_cash_floor=v)
for v in (4, 10, 12):
    add("lmd%d" % v, land_min_day_left=v)
for v in (0.0, 8.0, 20.0):
    add("pmv%d" % v, plant_min_value=v)
for v in (2.0, 3.0, 6.0, 9.0, 14.0, 25.0):
    add("mu%d" % (v * 100), cap_mu=v)
for v in (0.0, 0.3, 1.0, 1.5):
    add("ow%d" % (v * 10), opp_weight=v)


def make_agent(name):
    if name in ("pass", "random", "starter"):
        return name
    params = VARIANTS.get(name)
    if params is None:
        raise KeyError(name)
    brain = Brain(params)

    def agent(obs, config=None):
        try:
            if obs.get("day", 0) == 0 and obs.get("hour", 0) == 0:
                brain.reset()
            return brain.act(obs)
        except Exception:
            import traceback; traceback.print_exc()
            return {"farmer": ["PASS"], "hands": [], "market": []}
    return agent
