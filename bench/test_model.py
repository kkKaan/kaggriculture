"""Verify expected_units / watering_days / harvest_day against the real engine."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kaggle_environments import make
from agent_core import CROPS, expected_units, harvest_day, watering_days


def test_crop(crop, fertilize=False):
    """Plant one tile of `crop` at (0,0), follow our schedule, report the harvest."""
    wd = watering_days(crop, fertilize)
    hd = harvest_day(crop, fertilize)
    state = {"harvested": 0, "done": False, "weeded": False}

    def agent(obs, config=None):
        me = obs["farms"][obs["player"]]
        day, hour = obs["day"], obs["hour"]
        priv = obs["private"]
        fx, fy = me["farmer"]
        tile = me["tiles"][fy][fx]
        market = []
        if day == 0 and hour == 0:
            return {"farmer": ["PASS"], "hands": [],
                    "market": [["BUY_SEED", crop, 1]]}
        # walk to (0,0)
        if (fx, fy) != (0, 0):
            if fx > 0:
                return {"farmer": ["WEST"], "hands": [], "market": []}
            return {"farmer": ["NORTH"], "hands": [], "market": []}
        if tile is None and priv["seeds"].get(crop, 0) > 0 and not state["done"]:
            return {"farmer": ["PLANT", crop], "hands": [], "market": []}
        if isinstance(tile, dict) and tile.get("kind") == "WEED":
            if not state["done"]:
                state["weeded"] = True
            return {"farmer": ["PASS"], "hands": [], "market": []}
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            age = day - tile["planted_day"]
            if age in wd and not tile["watered_today"]:
                return {"farmer": ["WATER"], "hands": [], "market": []}
            if age >= hd and tile["yield_units"] > 0:
                state["harvested"] = tile["yield_units"]
                state["done"] = True
                return {"farmer": ["HARVEST"], "hands": [], "market": []}
            if fertilize and age == 0 and tile["fertilized_until_day"] < 0:
                pass
            if age in wd and not tile["watered_today"]:
                return {"farmer": ["WATER"], "hands": [], "market": []}
        return {"farmer": ["PASS"], "hands": [], "market": []}

    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 5})
    env.run([agent, "pass"])
    return state


ok = True
print(f"{'crop':<12} {'predicted':>9} {'actual':>7} {'weeded':>7} {'waters':>4}")
for crop in CROPS:
    st = test_crop(crop)
    pred = expected_units(crop)
    good = (st["harvested"] == pred) and not st["weeded"]
    ok = ok and good
    print(f"{crop:<12} {pred:>9} {st['harvested']:>7} {str(st['weeded']):>7} "
          f"{len(watering_days(crop)):>4}  {'OK' if good else 'MISMATCH'}")
print("ALL OK" if ok else "FAILURES PRESENT")
