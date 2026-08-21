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
    "cap_lambda": 0.0,
    "opp_weight": 1.0,
    "cap_mu": 4.0,
    "long_frac_min": 0.45,
    "operating_per_tile": 8.0,
    "use_zones": 0,
    "dist_decay": 1.2,
    "animal_target": 14,
    "mirror": 0.45,
    "wheat_reserve_days": 1.7,
    "keep_frac": 0.24,
    "fert_min_gain": 1e9,
    "long_frac_min": 0.80,
    "endgame_dump_day": 25,
    "disc_poor": 0.90,
    "land_max": 2,
}

def d(**kw):
    p = dict(CHAMP); p.update(kw); return p

VARIANTS = {"champ": d()}
VARIANTS["prev"] = d(fert_min_gain=15.0, long_frac_min=0.45)
VARIANTS["c_dl"]    = d(disc_poor=0.90, land_max=2)
VARIANTS["c_dm"]    = d(disc_poor=0.90, cap_mu=2.5)
VARIANTS["c_lm"]    = d(land_max=2, cap_mu=2.5)
VARIANTS["c_all"]   = d(disc_poor=0.90, land_max=2, cap_mu=2.5)
VARIANTS["c_all1"]  = d(disc_poor=0.90, land_max=1, cap_mu=2.5)
VARIANTS["c_allf"]  = d(disc_poor=0.90, land_max=2, cap_mu=2.5, future_shop_weight=1.25)

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
for v in (10, 12, 18, 22, 28, 36, 50):
    add("anim%d" % v, animal_target=v)
for v in (0, 200, 1500, 2500):
    add("acf%d" % v, animal_cash_floor=v)
for v in (4, 10, 12):
    add("lmd%d" % v, land_min_day_left=v)
for v in (0.0, 8.0, 20.0):
    add("pmv%d" % v, plant_min_value=v)
for v in (2.0, 3.0, 6.0, 9.0, 14.0, 25.0):
    add("mu%d" % (v * 100), cap_mu=v)
for v in (0.0, 0.3, 1.0, 1.5):
    add("ow%d" % (v * 10), opp_weight=v)
for v in (0.10, 0.20, 0.45, 0.60, 1.0):
    add("lf%d" % (v * 100), long_frac_min=v)
for v in (4, 5, 8, 11, 99):
    add("lh%d" % v, long_hd=v)
for v in (0.0, 4.0, 16.0, 26.0):
    add("opt%d" % v, operating_per_tile=v)
for v in (18, 40, 60):
    add("gate%d" % v, land_free_gate=v)
for v in (6.0, 20.0):
    add("lsp%d" % v, land_seed_per_tile=v)
add("nozone", use_zones=0)
for v in (0.0, 0.15, 0.22, 0.4, 0.5):
    add("mir%d" % (v * 100), mirror=v)
for v in (0.5, 1.5, 2.0):
    add("wrd%d" % (v * 10), wheat_reserve_days=v)
for v in (60.0, 250.0):
    add("fv%d" % v, fetch_value=v)
add("nofert", fert_min_gain=1e9)
for v in (0.0, 40.0, 90.0):
    add("fmg%d" % v, fert_min_gain=v)
for v in (0.25, 0.60, 0.80, 1.0):
    add("lf%d" % (v * 100), long_frac_min=v)
for v in (0.35, 0.55):
    add("mir%d" % (v * 100), mirror=v)
for v in (23, 25, 28, 29, 30):
    add("edd%d" % v, endgame_dump_day=v)
for v in (40, 55, 90, 99):
    add("ssc%d" % v, shed_soft_cap=v)
for v in (0.0, 8.0, 25.0):
    add("pmv%d" % v, plant_min_value=v)
for v in (20, 400, 900):
    add("scf%d" % v, seed_cash_floor=v)
for v in (3.0, 3.2, 3.9, 4.3):
    add("ovh%d" % (v * 10), hire_overhead=v)
for v in (30, 200, 600):
    add("hca%d" % v, hire_cap_abs=v)
for v in (25, 60, 90):
    add("wbm%d" % v, wheat_buy_max=v)
for v in (1.25,):
    add("fsw%d" % (v * 100), future_shop_weight=v)
for v in (1, 2):
    add("land%d" % v, land_max=v)
for _dd in (8, 14):
    for _hh in (14, 16, 18):
        add("late%d_%d" % (_dd, _hh), late_hands_day=_dd, late_hands=_hh)
for v in (2.5, 3.2, 5.5, 7.5):
    add("mu%d" % (v * 100), cap_mu=v)
for v in (0.84, 0.87, 0.92, 0.95):
    add("dp%d" % (v * 100), disc_poor=v)
for v in (0.90, 0.93, 0.999):
    add("dr%d" % (v * 1000), disc_rich=v)
for v in (0.35, 0.55, 0.65, 1.0):
    add("lfm%d" % (v * 100), long_frac_min=v)
for v in (10, 16, 18):
    add("anT%d" % v, animal_target=v)
for v in (1000, 2200, 3500):
    add("lb%d" % v, land_buffer=v)
for v in (18, 34, 50):
    add("gate%d" % v, land_free_gate=v)
for v in (0.1, 0.3, 0.55, 1.0):
    add("elf%d" % (v * 100), early_long_frac=v)
for v in (4, 9, 13):
    add("eld%d" % v, early_long_day=v, early_long_frac=0.3)
for v in (0.05, 0.15, 0.55, 0.8):
    add("zp%d" % (v * 100), zone_penalty=v)
for v in (0.9, 1.6, 2.2, 3.0, 5.0, 9.0):
    add("dd%d" % (v * 100), dist_decay=v)


def make_agent(name):
    if name in ("pass", "random", "starter"):
        return name
    if name == "sub":
        import importlib, os
        sub = os.path.join(os.path.dirname(os.path.abspath(__file__)), "submission")
        if sub not in sys.path:
            sys.path.insert(0, sub)
        import importlib.util
        path = os.path.join(sub, "main.py")
        spec = importlib.util.spec_from_file_location("kaggri_submission", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.agent
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
