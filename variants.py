"""Named agent variants for benchmarking."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_brain import Brain, DEFAULTS

import json as _json
_CJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "champion.json")
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
    "land_max": 1,
    "hire_per_turn": 3,
    "value_scaled_care": 1,
    "hold_bonus": 0.75,
    "keep_frac_premium": 0.15,
}

if os.path.exists(_CJ):
    try:
        CHAMP = _json.load(open(_CJ))
    except Exception:
        pass


def d(**kw):
    p = dict(CHAMP); p.update(kw); return p

VARIANTS = {"champ": d()}
VARIANTS["prev"] = dict({'animal_target': 11, 'cap_lambda': 0.0, 'cap_mu': 2.1598, 'cap_mu_ref': 8.0, 'disc_poor': 0.9586, 'dist_decay': 1.2, 'drop_threshold': 9, 'endgame_dump_day': 25, 'fert_min_gain': 1000000000.0, 'fetch_value': 130.0, 'final_run_slack': 6, 'future_shop_weight': 1.725, 'hire_overhead': 3.5, 'hire_per_turn': 3, 'hold_bonus': 0.75, 'keep_frac': 0.24, 'keep_frac_premium': 0.0516, 'land_buffer': 500, 'land_buffer_per_tile': 0.0, 'land_max': 2, 'long_frac_min': 0.7055, 'max_hands': 12, 'mirror': 0.45, 'operating_per_tile': 8.0, 'opp_weight': 1.0, 'rush_window': 3, 'sell_orders_head': 10, 'sticky_bonus': 1.0, 'use_zones': 0, 'value_scaled_care': 1, 'wheat_reserve_days': 0.5})
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
add("l0", land_max=0)
for v in (0.15, 0.35, 0.7, 1.2):
    add("cb%d" % (v * 100), cluster_bonus=v)
for v in (1.3, 1.7, 2.2):
    add("cmm%d" % round(v * 10), crop_move_mult=v)
for v in (0.7, 0.85, 1.2):
    add("amm%d" % round(v * 100), animal_move_mult=v)
add("mm_both", crop_move_mult=1.7, animal_move_mult=0.85)
add("L2", land_max=2)
add("fix", value_scaled_care=1, long_frac_min=0.7055, drop_threshold=9)
add("revA", animal_target=12, wheat_reserve_days=0.7885)
add("revB", keep_frac_premium=0.15, future_shop_weight=1.0)
add("revC", value_scaled_care=1)
add("revD", long_frac_min=0.7055, drop_threshold=9)
add("revE", disc_poor=0.9297)
add("aT14", animal_target=14)
add("nogoose", no_animal=("GOOSE",))
add("nogoose_aT14", no_animal=("GOOSE",), animal_target=14)
for _fd in (2.0, 4.0, 6.0):
    VARIANTS["fd%d" % _fd] = d(feed_days=_fd)
# animal-first opening: buy animals before seeds, house them fast, hold feed cash
for _wr in (2.0, 4.0, 6.0):
    for _wb in (60, 95):
        VARIANTS["op_w%d_b%d" % (_wr, _wb)] = d(
            animals_first=1, house_stranded=1, build_urgent=320.0,
            early_animals=4, early_animal_day=1, land_min_day=5,
            animal_target=16, wheat_reserve_days=_wr, wheat_buy_max=_wb)
add("field2", house_stranded=1, animals_first=1, build_urgent=320.0,
    early_animals=4, early_animal_day=1, land_min_day=5, animal_target=16)
add("field", house_stranded=1, build_urgent=320.0, early_animals=4,
    early_animal_day=1, land_min_day=5, animal_target=16)
add("orig",   house_stranded=0, build_urgent=100.0)
add("houseonly", build_urgent=100.0)
add("urgentonly", house_stranded=0)
add("L8",  land_min_day=8)
add("L10", land_min_day=10)
add("L10T16", land_min_day=10, animal_target=16)
add("L10A4T16", land_min_day=10, early_animals=4, animal_target=16)
add("L5",     land_min_day=5)
add("L5A4",   land_min_day=5, early_animals=4)
add("L5A4T14",land_min_day=5, early_animals=4, animal_target=14)
add("L4A4T14",land_min_day=4, early_animals=4, animal_target=14)
add("L6A5T15",land_min_day=6, early_animals=5, animal_target=15)
add("nowheat", no_grow=("WHEAT",))
add("cmu10", cap_mu=1.0)
add("cmu05", cap_mu=0.5)
add("cmu14", cap_mu=1.4)
add("cmu07", cap_mu=0.7)
add("nowheat_cmu10", no_grow=("WHEAT",), cap_mu=1.0)
add("ow04", opp_weight=0.4)
add("ow07", opp_weight=0.7)
add("mir20", mirror=0.20)
add("aT13", animal_target=13)
add("aT15", animal_target=15)
add("aT16", animal_target=16)
add("aT14m5", animal_target=14, animal_mu_scale=0.5)
add("aT18m5", animal_target=18, animal_mu_scale=0.5)
add("aT18m25", animal_target=18, animal_mu_scale=0.25)
add("aT18", animal_target=18)
add("aT22", animal_target=22)
add("nodig", dig_spent=0)
add("dig25", dig_spent_value=25.0)
add("dig70", dig_spent_value=70.0)
add("ea2", early_animals=2)
add("ea4", early_animals=4)
add("ea6", early_animals=6)
add("ea4d5", early_animals=4, early_animal_day=5)
add("flooder", keep_frac=0.0, keep_frac_premium=0.0, mirror=0.0, opp_weight=0.0,
    endgame_dump_day=1)
add("premium", long_frac_min=1.0, mirror=0.0, opp_weight=0.0, animal_target=4)
add("animalrush", animal_target=30, long_frac_min=0.3)
add("bigfarm", land_max=3, max_hands=16, hire_overhead=2.6)
add("M1", max_hands=16)
add("M2", max_hands=14)
add("M3", hire_overhead=3.0)
add("M4", hire_overhead=4.0)
add("M5", animal_target=14)
add("M6", animal_target=10)
add("M7", land_max=3, land_min_day_left=5)
add("K1", land_max=2, long_frac_min=0.85)
add("K2", land_max=2, animal_target=10)
add("K3", land_max=2, long_frac_min=0.85, animal_target=10)
add("K4", land_max=3)
add("K5", land_max=2, animal_target=12)
add("L2h", land_max=2, max_hands=16)
add("aT10", animal_target=10)
add("aT18", animal_target=18)
add("lfm85", long_frac_min=0.85)
add("lfm55", long_frac_min=0.55)
add("fertA", fert_min_gain=10.0, fert_fetch=0)
add("fertB", fert_min_gain=30.0, fert_fetch=0)
add("fertC", fert_min_gain=10.0, fert_fetch=1)
add("frs6", final_run_slack=6)
add("frs1", final_run_slack=1)
add("hb75x", hold_bonus=0.75)
add("C1", value_scaled_care=1, hold_bonus=0.75, keep_frac_premium=0.15)
add("C2", value_scaled_care=1, hold_bonus=0.75, keep_frac_premium=0.10)
add("C3", hold_bonus=0.75, keep_frac_premium=0.15)
add("C4", value_scaled_care=1, hold_bonus=0.6)
add("C5", value_scaled_care=1, hold_bonus=0.85)
add("vsc", value_scaled_care=1)
add("vsc_hb", value_scaled_care=1, hold_bonus=0.75)
for v in (0.15, 0.3, 0.45, 0.6):
    add("kfp%d" % round(v * 100), keep_frac_premium=v)
add("no_eh", early_harvest=0)
add("no_rush", rush_sell=0)
add("no_both", early_harvest=0, rush_sell=0)
for v in (0.75, 0.9, 1.15, 1.4):
    add("hb%d" % round(v * 100), hold_bonus=v)
for v in (2, 5, 8):
    add("rw%d" % v, rush_window=v)
for lb in (2500, 5000, 9000):
    add("l2b%d" % lb, land_max=2, land_buffer=lb)
for g in (10, 16):
    add("l2g%d" % g, land_max=2, land_free_gate=g)
add("l2", land_max=2)
for v in (8, 10, 12, 16, 18):
    add("aT%d" % v, animal_target=v)
for v in (8, 10, 14, 16):
    add("H%d" % v, max_hands=v)
for v in (2.6, 3.0, 4.0, 4.6):
    add("ovhx%d" % (v * 10), hire_overhead=v)
for v in (0.1, 0.3, 0.55, 1.0):
    add("elf%d" % (v * 100), early_long_frac=v)
for v in (4, 9, 13):
    add("eld%d" % v, early_long_day=v, early_long_frac=0.3)
for v in (0.05, 0.15, 0.55, 0.8):
    add("zp%d" % (v * 100), zone_penalty=v)
for v in (0.9, 1.6, 2.2, 3.0, 5.0, 9.0):
    add("dd%d" % (v * 100), dist_decay=v)


_SUB = None


def make_agent(name):
    if name in ("pass", "random", "starter"):
        return name
    if name == "sub":
        global _SUB
        if _SUB is None:
            import importlib.util
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "submission", "main.py")
            spec = importlib.util.spec_from_file_location("kaggri_submission", path)
            _SUB = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_SUB)
        return _SUB.agent
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
