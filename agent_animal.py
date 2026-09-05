"""Animal-centric allocator. WORK IN PROGRESS - not competitive yet.

Status 2026-08-23: scores $15-35k against the crop agent's $83-129k. The economic
plan is right (5 animals by day 3, land on days 5 and 8, fertiliser sold daily)
but execution fails: animals sit unplaced in the shed and placed ones die. Debug
the place-and-feed loop before touching parameters again.


The shipped agent runs a crop economy: it buys land immediately, fills tiles with
strawberries, and adds animals only when spare capital appears. Traces of the
stronger ladder agents show a different engine entirely:

  day 0   buy 4-5 animals (no land), a handful of melon and wheat seeds
  day 1+  collect fertiliser from every animal, every day
  day 2+  SELL FERTILIZER ~5/day  ->  ~$500/day of cash before any crop matures
  day 5   buy the 2nd quadrant     (funded by fertiliser, not by harvests)
  day 8   buy the 3rd quadrant
  steady  ~15 animals, ~62 crop tiles

Animals here are bought as a *cash instrument* first and a milk/wool source
second: five animals repay their own cost in roughly four days on fertiliser
alone, which is what funds the early land. Bolting pieces of this onto the crop
allocator measured worse every time (see README), because spending the last $130
on feed wheat is right only when fertiliser is the income. So this is a separate
economic layer that reuses the (well-tested) execution layer unchanged.
"""
import math

from agent_brain import Brain, DEFAULTS
from agent_core import CROPS, ANIMALS, LAND_PRICES, market_price, harvest_day, expected_units

ANIMAL_DEFAULTS = dict(DEFAULTS)
ANIMAL_DEFAULTS.update({
    # opening
    "open_animals": 5,        # animals to place as fast as possible on day 0
    "open_days": 2,           # days the forced opening lasts
    "open_seed_cash": 500.0,  # cash reserved for seeds during the opening
    "open_hands": 5,          # hands to hire during the opening, to place animals fast
    "open_species": ("COW", "SHEEP"),   # geese are the worst animal; the field avoids them
    "land_days": (5, 8),      # days the 2nd and 3rd quadrants are bought
    "land_min_cash": 200.0,   # cash to keep back after buying land
    # steady state
    "animal_target": 14,   # rank 1 runs 14; 19 overshoots and floods milk/wool
    "wheat_tiles": 0,   # tiles reserved for wheat: feed we grow is feed we do not
                        # buy, and buying drives the scarcity price up on ourselves
    "wheat_cash_floor": 10.0,
    "animals_first": 1,
    "house_stranded": 1,
    "build_urgent": 340.0,
    "fetch_animal_value": 460.0,   # an unplaced animal is $400-500 doing nothing
    "place_value": 700.0,          # and it earns nothing until it is on a tile
    "fetch_animal_slots": 4,
    "fert_early": 1,
    "land_max": 2,
    "no_animal": ("GOOSE",),  # eggs are $50 where milk is $170 and wool $200;
                              # rank 1 and Crop Dusta both use zero geese
    "use_zones": 0,      # DEFAULTS still has 1; the champion overrides it and the
                         # zoning path is both slower and measurably worse
    "dist_decay": 1.2,
    "sticky_bonus": 1.0,
    "cap_mu": 1.4,
    "disc_poor": 0.9586,
    "keep_frac": 0.24,
    "keep_frac_premium": 0.0516,
    "future_shop_weight": 1.725,
    "hire_overhead": 3.5,
    "hire_per_turn": 3,
    "long_frac_min": 0.7145,
    "endgame_dump_day": 25,
    "final_run_slack": 6,
    "mirror": 0.45,
    "opp_weight": 1.0,
    "drop_threshold": 9,
    "wheat_reserve_days": 0.5,
    "hold_bonus": 0.75,
    "value_scaled_care": 1,
    "max_hands": 12,
})


class AnimalBrain(Brain):
    def __init__(self, params=None):
        p = dict(ANIMAL_DEFAULTS)
        if params:
            p.update(params)
        Brain.__init__(self)
        # champion_animal.json round-trips through JSON, so tuple params arrive as lists
        for k in ("no_animal", "no_grow", "land_days"):
            if k in p and isinstance(p[k], list):
                p[k] = tuple(p[k])
        self.P = p

    def _hands_wanted(self, scan, money, n, plantable=0):
        want = Brain._hands_wanted(self, scan, money, n, plantable)
        if self.day_seen < self.P["open_days"] + 1:
            # The opening is action-bound, not work-bound: every animal needs a
            # build, a pickup, a walk and a place before it earns anything.
            want = max(want, self.P["open_hands"])
        return min(want, self.P["max_hands"])

    # Land is bought on a schedule funded by fertiliser, not gated on free tiles.
    def land_decision(self, bought, free, money, day, days_left, scan):
        P = self.P
        if self._final_day or bought >= P["land_max"]:
            return 0
        days = P["land_days"]
        if bought >= len(days) or day < days[bought]:
            return 0
        cost = LAND_PRICES[bought]
        if money >= cost + P["land_min_cash"]:
            return cost
        return 0

    def _alloc_farm(self, scan, minv, drain, days_left, my_pipe, opp_pipe,
                    day, hour, money, shed):
        P = self.P
        if day >= P["open_days"]:
            res = Brain._alloc_farm(self, scan, minv, drain, days_left,
                                    my_pipe, opp_pipe, day, hour, money, shed)
            n_wheat = P["wheat_tiles"]
            if n_wheat and days_left > harvest_day("WHEAT"):
                crops, animals, nc, npa = res
                growing = scan["crop_counts"].get("WHEAT", 0)
                short = n_wheat - growing
                if short > 0 and crops:
                    # replace the lowest-priority planned crops with wheat
                    keep = max(0, len(crops) - short)
                    crops = crops[:keep] + ["WHEAT"] * min(short, len(crops) - keep)
                    res = (crops, animals, nc, npa)
            return res

        # --- forced opening: animals first, then whatever seeds the rest buys
        free_coop = sum(1 for _, _, k in scan["empty_struct"] if k == "COOP")
        free_past = sum(1 for _, _, k in scan["empty_struct"] if k == "PASTURE")
        have = scan["n_animals"] + sum(shed.get(a, 0) for a in ANIMALS)
        want = max(0, P["open_animals"] - have - free_coop - free_past)

        budget = money
        animals_out = []
        # Cow and sheep only, alternating: milk and wool are worth 3x eggs, and
        # splitting across two products keeps either from cratering.
        order = [a for a in P["open_species"] if a not in P["no_animal"]] or ["COW"]
        i = 0
        while len(animals_out) < want:
            a = order[i % len(order)]
            cost = ANIMALS[a]["cost"]
            if budget - cost < P["open_seed_cash"]:
                break
            animals_out.append(a)
            budget -= cost
            i += 1

        # Fill the rest of the quadrant with fast, cheap crops; melon for the
        # one big payday, wheat because the animals eat it. Reserve tiles for
        # every animal still needing a home, including any already in the shed,
        # or the whole quadrant gets planted and they can never be placed.
        homes_needed = (len(animals_out) + shed.get("COW", 0)
                        + shed.get("SHEEP", 0) + shed.get("GOOSE", 0))
        slots = max(0, len(scan["empty"]) - homes_needed)
        crops_out = []
        for _ in range(slots):
            pick = None
            for c in ("WHEAT", "MELON", "CARROT"):
                if c in P["no_grow"]:
                    continue
                if harvest_day(c) > days_left:
                    continue
                if CROPS[c]["seed"] <= budget:
                    pick = c
                    break
            if pick is None:
                break
            crops_out.append(pick)
            budget -= CROPS[pick]["seed"]

        want_coop = sum(1 for a in animals_out if ANIMALS[a]["structure"] == "COOP")
        want_past = len(animals_out) - want_coop
        stranded_coop = shed.get("GOOSE", 0)
        stranded_past = shed.get("COW", 0) + shed.get("SHEEP", 0)
        need_coop = max(0, want_coop - free_coop, stranded_coop - free_coop)
        need_past = max(0, want_past - free_past, stranded_past - free_past)
        cap = len(scan["empty"])
        if need_coop + need_past > cap:
            need_past = min(need_past, cap)
            need_coop = cap - need_past
        return crops_out, animals_out, need_coop, need_past
