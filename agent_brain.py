"""Kaggriculture agent brain. Parameterised so variants can be benchmarked."""
import math
from agent_core import (
    CROPS, ANIMALS, PRODUCTS, MARKET_PARAMS, LAND_PRICES, MOVES,
    market_price, sell_revenue, avg_sell_price,
    quadrant_of, shed_tiles, manhattan, step_toward,
    expected_units, harvest_day, watering_days, water_window,
)

SHOPS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

DEFAULTS = {
    "max_hands": 13,
    "hire_overhead": 1.85,
    "hire_cap_abs": 60.0,        # always affordable floor for hire spend
    "hire_cap_frac": 0.05,
    "keep_frac": 0.30,
    "endgame_dump_day": 27,
    "animal_target": 22,
    "land_buffer": 500,
    "land_min_day_left": 7,
    "land_free_gate": 26,
    "land_seed_per_tile": 12.0,
    "wheat_buy_max": 60,
    "wheat_reserve_days": 2.0,
    "drop_threshold": 9,
    "shed_soft_cap": 70,
    "plant_min_value": 3.0,
    "seed_cash_floor": 120,
    "animal_cash_floor": 700,
    "operating_per_tile": 14.0,
    "operating_base": 200.0,
    "plan_cache_turns": 3,
    "dist_decay": 0.55,
    "disc_rich": 0.97,
    "disc_poor": 0.75,
    "cash_target": 3000.0,
    "cap_lambda": 0.0,
    "cap_mu": 1.0,
    "long_hd": 6,
    "long_frac_min": 0.30,
    "cap_mu_ref": 8.0,
    "opp_weight": 0.6,
    "sticky_bonus": 1.6,
    "last_day_dump": True,
    "land_buffer_per_tile": 32.0,
    "deploy_need_per_tile": 30.0,
}


class Brain:
    def __init__(self, params=None):
        self.P = dict(DEFAULTS)
        if params:
            self.P.update(params)
        self.reset()

    def reset(self):
        self.day_seen = -1
        self._plan_key = None
        self._plan = []
        self._alloc = []
        self.targets = {}
        self._final_day = False

    # ------------------------------------------------------------ market model
    def drain_rate(self, shops, turns_per_day=24, shop_interval=4, center_interval=24):
        per_day = {p: 0.0 for p in PRODUCTS}
        ticks = turns_per_day / float(shop_interval)
        for name in shops:
            prods = SHOPS.get(name, [])
            mult = 2 if len(prods) == 1 else 1
            for it in prods:
                per_day[it] += ticks * mult
        for it in PRODUCTS:
            if it != "FERTILIZER":
                per_day[it] += turns_per_day / float(center_interval)
        return per_day

    # ------------------------------------------------------------ price helper
    def _price_at(self, item, minv, drain, days_ahead, extra_supply=0.0):
        inv = minv.get(item, 10000) - drain.get(item, 0.0) * days_ahead + extra_supply
        return market_price(item, int(round(inv)))

    def _batch_price(self, item, qty, minv, drain, days_ahead, extra_supply=0.0):
        inv = minv.get(item, 10000) - drain.get(item, 0.0) * days_ahead + extra_supply
        return avg_sell_price(item, qty, int(round(inv)))

    # ------------------------------------------------------------ crop scoring
    def crop_score(self, crop, minv, drain, days_left, pipe, opp_pipe, disc=1.0,
                   press=0.0):
        cd = CROPS[crop]
        hd = harvest_day(crop)
        if hd > days_left:
            return None
        units = expected_units(crop)
        actions = 2 + len(watering_days(crop))
        supply = pipe.get(crop, 0) + self.P["opp_weight"] * opp_pipe.get(crop, 0)
        price = self._batch_price(crop, units, minv, drain, hd, supply)
        rev = price * units - cd["seed"]
        raw = rev / float(actions)
        return raw * (disc ** hd), rev, hd, units, raw, actions, cd["seed"]

    def animal_score(self, animal, minv, drain, days_left, pipe, opp_pipe):
        a = ANIMALS[animal]
        active = days_left - a["first_yield_day"] - 1
        if active < 3:
            return None
        rate = (1.0 + a["interval"]) / a["interval"]
        units = rate * active
        prod = a["product"]
        supply = pipe.get(prod, 0) + self.P["opp_weight"] * opp_pipe.get(prod, 0)
        price = self._batch_price(prod, units, minv, drain, a["first_yield_day"], supply)
        fert_units = days_left - 1
        fert_price = self._batch_price("FERTILIZER", fert_units, minv, drain, 1,
                                       pipe.get("FERTILIZER", 0))
        wheat_price = self._price_at("WHEAT", minv, drain, 0)
        rev = (units * price + fert_units * fert_price * 0.85
               - (days_left - 1) * wheat_price - a["cost"])
        actions = 2 + (days_left - 1) * (1.0 + 1.0 + 1.0 + rate / a["max_held"] * a["interval"])
        return rev / max(1.0, actions), rev, units

    # -------------------------------------------------------------- main entry
    def act(self, obs):
        P = self.P
        player = obs.get("player", 0)
        farms = obs.get("farms") or []
        if not farms or player >= len(farms):
            return {"farmer": ["PASS"], "hands": [], "market": []}
        me = farms[player]
        opp = farms[1 - player] if len(farms) > 1 else None
        priv = obs.get("private") or {}
        tiles = me["tiles"]
        n = len(tiles)
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        money = me["money"]
        shed = dict(priv.get("shed") or {})
        seeds = dict(priv.get("seeds") or {})
        invs = [dict(i) for i in (priv.get("inventories") or [{}])]
        market = obs.get("market") or {}
        minv = dict(market.get("inventory") or {})
        shops = (obs.get("town") or {}).get("unlocked_shops") or []

        if day != self.day_seen:
            self.day_seen = day
            self.targets = {}
        days_left = max(0, 29 - day)
        self._final_day = (day >= 29)

        units = [tuple(me["farmer"])] + [tuple(p) for p in me["hands"]]
        while len(invs) < len(units):
            invs.append({})
        sheds = shed_tiles(n)
        shed_set = set(sheds)

        drain = self.drain_rate(shops)
        scan = self._scan(tiles, n)
        opp_pipe = self._pipeline(opp["tiles"]) if opp else {}
        my_pipe = self._pipeline(tiles)

        n_animals = scan["n_animals"]
        wheat_reserve = int(math.ceil(n_animals * P["wheat_reserve_days"]))

        free = len(scan["empty"])
        bought = len(me["unlocked_quadrants"]) - 1
        land_cost = 0
        if (not self._final_day and bought < 3
                and days_left >= P["land_min_day_left"] + 3 * bought):
            c = LAND_PRICES[bought]
            est = P["land_seed_per_tile"] * min(free + 25, 50)
            if money >= c + est + P["land_buffer"] and free <= P["land_free_gate"]:
                land_cost = c
        avail = money - land_cost

        alloc = self._alloc_plants(scan, minv, drain, days_left, my_pipe, opp_pipe,
                                   day, hour, 0, avail)
        seed_spend = sum(CROPS[c]["seed"] for c in alloc[:36])
        seed_spend = max(0.0, seed_spend - sum(
            CROPS[c]["seed"] * seeds.get(c, 0) for c in CROPS))
        buys, need_coop, need_past = self._animal_plan(
            scan, minv, drain, days_left, my_pipe, opp_pipe,
            avail - seed_spend, shed)
        animal_gap = need_coop + need_past
        if animal_gap:
            alloc = self._alloc_plants(scan, minv, drain, days_left, my_pipe,
                                       opp_pipe, day, hour, animal_gap, avail)

        orders = self._market(me, priv, shed, seeds, minv, drain, scan, day, hour,
                              money, days_left, my_pipe, opp_pipe, invs,
                              wheat_reserve, buys, animal_gap, alloc, n, land_cost)

        acts = self._assign(tiles, n, day, hour, units, invs, shed, seeds, scan,
                            minv, drain, days_left, shed_set, money, alloc,
                            need_coop, need_past)
        return {"farmer": acts[0], "hands": acts[1:], "market": orders[:10]}

    # ---------------------------------------------------------------- scanning
    def _scan(self, tiles, n):
        s = {"plants": [], "animals": [], "empty": [], "weeds": [],
             "empty_struct": [], "crop_counts": {}, "n_animals": 0, "locked": 0}
        for y in range(n):
            row = tiles[y]
            for x in range(n):
                t = row[x]
                if t is None:
                    s["empty"].append((x, y))
                elif t == "LOCKED":
                    s["locked"] += 1
                elif isinstance(t, dict):
                    k = t.get("kind")
                    if k == "PLANT":
                        s["plants"].append((x, y, t))
                        s["crop_counts"][t["crop"]] = s["crop_counts"].get(t["crop"], 0) + 1
                    elif k == "WEED":
                        s["weeds"].append((x, y))
                    elif "animal" in t:
                        s["animals"].append((x, y, t))
                        s["n_animals"] += 1
                    else:
                        s["empty_struct"].append((x, y, k))
        return s

    def _pipeline(self, tiles):
        pipe = {}
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    if t.get("kind") == "PLANT":
                        c = t["crop"]
                        pipe[c] = pipe.get(c, 0) + expected_units(c)
                    elif "animal" in t:
                        a = ANIMALS[t["animal"]]
                        pipe[a["product"]] = pipe.get(a["product"], 0) + 8
                        pipe["FERTILIZER"] = pipe.get("FERTILIZER", 0) + 8
        return pipe

    # ------------------------------------------------------------ plant policy
    def cash_pressure(self, money, free_tiles):
        tgt = self.P["cash_target"]
        return max(0.0, min(1.0, (tgt - money) / tgt))

    def _alloc_plants(self, scan, minv, drain, days_left, my_pipe, opp_pipe,
                      day, hour, animal_gap, money):
        P = self.P
        free = len(scan["empty"])
        bucket = int(money // 500)
        key = (day, hour // P["plan_cache_turns"], free, bucket)
        if key == self._plan_key:
            return self._alloc
        slots = min(max(0, free - animal_gap), 60)
        press = self.cash_pressure(money, free)
        disc = P["disc_rich"] - (P["disc_rich"] - P["disc_poor"]) * press
        floor = P["seed_cash_floor"]
        if not scan["plants"] and free > 0:
            floor = 0.0
        budget = max(0.0, money - floor)
        pipe = dict(my_pipe)
        out = []
        long_cap = int(slots * (P["long_frac_min"] + (1.0 - P["long_frac_min"]) * (1.0 - press)))
        n_long = 0
        for _ in range(slots):
            rem = slots - len(out)
            dps = budget / max(1.0, float(rem))
            mu = P["cap_mu"] * P["cap_mu_ref"] / max(1.0, dps)
            best = None
            for crop in CROPS:
                if CROPS[crop]["seed"] > budget:
                    continue
                r = self.crop_score(crop, minv, drain, days_left, pipe, opp_pipe,
                                    disc, press)
                if r is None or r[4] < P["plant_min_value"]:
                    continue
                if r[2] >= P["long_hd"] and n_long >= long_cap:
                    continue
                sc = (r[1] * (disc ** r[2])) / (r[5] + mu * r[6])
                if best is None or sc > best[0]:
                    best = (sc, crop, r[3])
            if best is None:
                break
            out.append(best[1])
            if harvest_day(best[1]) >= P["long_hd"]:
                n_long += 1
            budget -= CROPS[best[1]]["seed"]
            pipe[best[1]] = pipe.get(best[1], 0) + best[2]
        self._plan_key = key
        self._alloc = out
        return out

    def _animal_plan(self, scan, minv, drain, days_left, my_pipe, opp_pipe, money, shed):
        """Decide the animal mix. Returns (buy_list, need_coop, need_pasture)."""
        P = self.P
        if days_left < 5:
            return [], 0, 0
        have = {a: 0 for a in ANIMALS}
        for _, _, t in scan["animals"]:
            have[t["animal"]] = have.get(t["animal"], 0) + 1
        in_shed = {a: shed.get(a, 0) for a in ANIMALS}
        free_coop = sum(1 for _, _, k in scan["empty_struct"] if k == "COOP")
        free_past = sum(1 for _, _, k in scan["empty_struct"] if k == "PASTURE")
        total_have = (sum(have.values()) + sum(in_shed.values())
                      + free_coop + free_past)
        room = P["animal_target"] - total_have
        tiles_free = len(scan["empty"])
        reserve = (P["animal_cash_floor"] + P["operating_base"]
                   + P["operating_per_tile"] * min(len(scan["empty"]), 50))
        cash = max(0.0, money - reserve)
        del reserve
        pipe = dict(my_pipe)
        buys = []
        # slots we could still occupy: empty structures first, then bare tiles
        open_coop, open_past = free_coop, free_past
        budget_tiles = tiles_free
        for _ in range(max(0, min(room + free_coop + free_past, 12))):
            best = None
            for a in ANIMALS:
                if ANIMALS[a]["cost"] > cash:
                    continue
                struct = ANIMALS[a]["structure"]
                if struct == "COOP":
                    if open_coop <= 0 and budget_tiles <= 0:
                        continue
                else:
                    if open_past <= 0 and budget_tiles <= 0:
                        continue
                r = self.animal_score(a, minv, drain, days_left, pipe, opp_pipe)
                if r is None or r[1] <= 0:
                    continue
                if best is None or r[0] > best[0]:
                    best = (r[0], a, r[2])
            if best is None:
                break
            a = best[1]
            buys.append(a)
            cash -= ANIMALS[a]["cost"]
            prod = ANIMALS[a]["product"]
            pipe[prod] = pipe.get(prod, 0) + best[2]
            pipe["FERTILIZER"] = pipe.get("FERTILIZER", 0) + (days_left - 1)
            if ANIMALS[a]["structure"] == "COOP":
                if open_coop > 0:
                    open_coop -= 1
                else:
                    budget_tiles -= 1
            else:
                if open_past > 0:
                    open_past -= 1
                else:
                    budget_tiles -= 1
        # already-owned animals waiting in the shed need housing too
        pend_coop = in_shed.get("GOOSE", 0)
        pend_past = in_shed.get("COW", 0) + in_shed.get("SHEEP", 0)
        want_coop = sum(1 for a in buys if ANIMALS[a]["structure"] == "COOP") + pend_coop
        want_past = len(buys) - (want_coop - pend_coop) + pend_past
        need_coop = max(0, want_coop - free_coop)
        need_past = max(0, want_past - free_past)
        cap = max(0, tiles_free)
        if need_coop + need_past > cap:
            if need_coop >= need_past:
                need_coop = min(need_coop, cap); need_past = cap - need_coop
            else:
                need_past = min(need_past, cap); need_coop = cap - need_past
        return buys, need_coop, need_past

    # ------------------------------------------------------------ market orders
    def _market(self, me, priv, shed, seeds, minv, drain, scan, day, hour, money,
                days_left, my_pipe, opp_pipe, invs, wheat_reserve, buys,
                animal_gap, alloc, n, land_cost):
        P = self.P
        head, tail = [], []

        if hour <= 1:
            held = sum(seeds.values())
            plantable = held + min(len(alloc), int(max(0.0, money - P["seed_cash_floor"]) // 12))
            want = self._hands_wanted(scan, money, n, plantable)
            todo = max(0, want - me["hires_today"])
            for _ in range(min(todo, 7 if hour == 0 else 10)):
                head.append(["HIRE"])

        head.extend(self._sell_orders(shed, minv, drain, day, wheat_reserve))

        if land_cost:
            tail.append(["BUY_LAND"])
            money -= land_cost

        # seeds for what we plan to plant
        need = {}
        for c in ([] if self._final_day else alloc[:36]):
            need[c] = need.get(c, 0) + 1
        floor = P["seed_cash_floor"]
        if not scan["plants"] and len(scan["empty"]) > 0:
            floor = 0.0
        budget = max(0.0, money - floor)
        for c, k in sorted(need.items(), key=lambda kv: -CROPS[kv[0]]["seed"]):
            k -= seeds.get(c, 0)
            cost = CROPS[c]["seed"]
            k = min(k, int(budget // cost))
            if k > 0:
                tail.append(["BUY_SEED", c, k])
                budget -= k * cost

        if buys and not self._final_day:
            want = {}
            for a in buys:
                want[a] = want.get(a, 0) + 1
            for a, k in sorted(want.items(), key=lambda kv: -ANIMALS[kv[0]]["cost"]):
                k = min(k - shed.get(a, 0), 4)
                if k > 0:
                    tail.append(["BUY_ANIMAL", a, k])

        n_animals = scan["n_animals"]
        if n_animals:
            wheat_have = shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in invs)
            wprice = market_price("WHEAT", minv.get("WHEAT", 10000) - 1)
            if wheat_have < wheat_reserve and wprice <= P["wheat_buy_max"]:
                k = wheat_reserve - wheat_have
                k = min(k, int(max(0.0, money - 150) // max(1, wprice)))
                if k > 0:
                    tail.append(["BUY_PRODUCT", "WHEAT", k])
        return head + tail

    def _sell_orders(self, shed, minv, drain, day, wheat_reserve):
        P = self.P
        out = []
        total_shed = sum(shed.values())
        dumping = day >= P["endgame_dump_day"]
        keep = P["keep_frac"]
        if day >= P["endgame_dump_day"] - 2:
            keep *= 0.5
        pressure = total_shed > P["shed_soft_cap"]
        for item in PRODUCTS:
            have = shed.get(item, 0)
            if have <= 0:
                continue
            if item == "WHEAT":
                have -= wheat_reserve
                if have <= 0:
                    continue
            inv = minv.get(item, 10000)
            thresh = max(1.0, MARKET_PARAMS[item]["base"] * keep)
            if dumping or pressure:
                qty = have
            else:
                qty, cur = 0, inv
                while qty < have:
                    pr = market_price(item, cur)
                    if pr < thresh:
                        break
                    qty += 1
                    if pr > 1:
                        cur += 1
            if qty > 0:
                out.append((market_price(item, inv) * qty, ["SELL", item, qty]))
        out.sort(reverse=True, key=lambda kv: kv[0])
        return [o for _, o in out]

    def _hands_wanted(self, scan, money, n, plantable=0):
        P = self.P
        work = 0.0
        for (x, y, t) in scan["plants"]:
            crop = t["crop"]
            hd = max(1, harvest_day(crop))
            work += (len(watering_days(crop)) + 2.0) / float(hd + 1)
        work += scan["n_animals"] * 3.4
        work += min(len(scan["empty"]), plantable) * 1.6
        work += len(scan["weeds"]) * 0.5
        work += len(scan["empty_struct"]) * 1.0
        need = int(math.ceil(work * P["hire_overhead"] / 24.0)) - 1
        if work <= 0 and (scan["empty"] or scan["weeds"]):
            need = max(need, 2)
        need = max(0, min(P["max_hands"], need))
        cap = max(P["hire_cap_abs"], money * P["hire_cap_frac"])
        a, b, tot, k = 1, 1, 0, 0
        while k < need and tot + a <= cap:
            tot += a
            a, b = b, a + b
            k += 1
        return k

    # ------------------------------------------------------------- assignment
    def _assign(self, tiles, n, day, hour, units, invs, shed, seeds, scan, minv,
                drain, days_left, shed_set, money, alloc, need_coop, need_past):
        animal_gap = need_coop + need_past
        P = self.P
        tasks = []
        turns_left = 24 - hour
        center = (n // 2, n // 2)

        for (x, y, t) in scan["plants"]:
            crop = t["crop"]
            cd = CROPS[crop]
            age = day - t["planted_day"]
            hd = harvest_day(crop)
            wdays = watering_days(crop)
            ws = water_window(crop)[0]
            yu = t.get("yield_units", 0)
            ready = False
            if yu > 0 and age >= cd["first_yield_day"]:
                if cd["ongoing"]:
                    ready = yu >= cd["max_yield"] or age >= hd or days_left <= 1
                else:
                    ready = age >= hd or yu >= expected_units(crop)
            if days_left <= 0 and yu > 0 and age >= cd["first_yield_day"]:
                ready = True
            if ready:
                price = self._price_at(crop, minv, drain, 0)
                tasks.append((min(400.0, price * yu * 0.8), x, y, "HARVEST", None))
            if not t["watered_today"] and not (ready and not cd["ongoing"]):
                must = t["consecutive_unwatered"] >= 1
                bonus = (not cd["ongoing"]) and age in wdays and age >= ws
                if must and bonus:
                    val = 95.0
                elif must:
                    val = 70.0
                elif bonus:
                    val = 50.0
                else:
                    val = 0.0
                if val > 0:
                    tasks.append((val, x, y, "WATER", None))

        fert_price = self._price_at("FERTILIZER", minv, drain, 0)
        for (x, y, t) in scan["animals"]:
            a = ANIMALS[t["animal"]]
            pprice = self._price_at(a["product"], minv, drain, 0)
            gain = 1 + t.get("pending_care_bonus", 0)
            if not t["fed_today"] and days_left >= 1:
                tasks.append((140.0 if t["consecutive_unfed"] >= 1 else 88.0,
                              x, y, "FEED", None))
            if not t["cared_today"] and days_left >= 2:
                tasks.append((min(75.0, pprice * 0.85), x, y, "CARE", None))
            if t.get("fertilizer_available"):
                tasks.append((min(90.0, fert_price * 0.8), x, y, "COLLECT_FERTILIZER", None))
            yu = t.get("yield_units", 0)
            if yu > 0 and (yu + gain > a["max_held"] or days_left <= 1 or days_left <= 0):
                tasks.append((min(400.0, pprice * yu * 0.8), x, y, "HARVEST", None))

        buy_pending = sum(shed.get(a, 0) for a in ANIMALS) > 0 or animal_gap > 0
        digval = 30.0 if (days_left > 4 and len(scan["empty"]) < 12) else 12.0
        for (x, y) in scan["weeds"]:
            tasks.append((digval if days_left > 3 else 1.0, x, y, "DIG", None))

        # build structures near the shed, plant far from it
        empties = scan["empty"]
        near_first = sorted(empties, key=lambda p: manhattan(p, center))
        if animal_gap > 0:
            todo = ["BUILD_COOP"] * need_coop + ["BUILD_PASTURE"] * need_past
            for (x, y), struct in zip(near_first[:animal_gap], todo):
                tasks.append((100.0, x, y, struct, None))
        held = {}
        for iv in invs:
            for a in ANIMALS:
                if iv.get(a, 0):
                    held[a] = held.get(a, 0) + iv[a]
        idle_struct = 0
        for (x, y, kind) in scan["empty_struct"]:
            placed = False
            for aname, ad in ANIMALS.items():
                if ad["structure"] == kind and (held.get(aname, 0) or shed.get(aname, 0)):
                    tasks.append((220.0, x, y, "PLACE_" + aname, None))
                    placed = True
            if not placed:
                idle_struct += 1
        # structures nobody will ever fill are just dead land
        if idle_struct and len(scan["empty"]) < 4 and days_left > 4 and not buy_pending:
            for (x, y, kind) in scan["empty_struct"]:
                tasks.append((26.0, x, y, "DIG", None))

        avail = {c: seeds.get(c, 0) for c in CROPS if seeds.get(c, 0) > 0}
        if avail and turns_left >= 3:
            order = []
            for c in avail:
                r = self.crop_score(c, minv, drain, days_left, {}, {})
                order.append((r[0] if r else -1e9, c))
            order.sort(reverse=True)
            order = [c for v, c in order if v > -1e8]
            far_first = sorted(empties, key=lambda p: -manhattan(p, center))
            skip = animal_gap
            for (x, y) in far_first:
                if skip > 0:
                    skip -= 1
                    continue
                crop = None
                for c in order:
                    if avail.get(c, 0) > 0:
                        crop = c
                        break
                if crop is None:
                    break
                avail[crop] -= 1
                tasks.append((78.0, x, y, "PLANT", crop))

        need_feed = any((not t["fed_today"]) for _, _, t in scan["animals"])
        wheat_in_shed = shed.get("WHEAT", 0)
        animals_pending = sum(shed.get(a, 0) for a in ANIMALS)
        open_structs = len(scan["empty_struct"])

        assigned = [None] * len(units)
        used, taken = set(), set()
        pairs = []
        for ui, upos in enumerate(units):
            inv = invs[ui] if ui < len(invs) else {}
            for ti, (val, x, y, kind, payload) in enumerate(tasks):
                if kind == "FEED" and inv.get("WHEAT", 0) <= 0:
                    continue
                if kind.startswith("PLACE_") and inv.get(kind[6:], 0) <= 0:
                    continue
                d = manhattan(upos, (x, y))
                if d > turns_left:
                    continue
                sc = val / (1.0 + P["dist_decay"] * d)
                if self.targets.get(ui) == (x, y, kind):
                    sc *= P["sticky_bonus"]
                pairs.append((sc, ui, ti))
        pairs.sort(reverse=True)
        for sc, ui, ti in pairs:
            if ui in taken or ti in used:
                continue
            taken.add(ui)
            used.add(ti)
            assigned[ui] = ti
        newt = {}
        for ui, ti in enumerate(assigned):
            if ti is not None:
                v, x, y, k, pl = tasks[ti]
                newt[ui] = (x, y, k)
        self.targets = newt

        out = []
        for ui, upos in enumerate(units):
            inv = invs[ui] if ui < len(invs) else {}
            carry = sum(inv.values())
            ti = assigned[ui]
            if ti is not None:
                val, x, y, kind, payload = tasks[ti]
                if (upos[0], upos[1]) == (x, y):
                    out.append(self._do(kind, payload))
                else:
                    mv = step_toward(upos, (x, y))
                    out.append([mv] if mv else ["PASS"])
                continue
            out.append(self._logistics(upos, inv, carry, shed_set, shed, wheat_in_shed,
                                       need_feed, animals_pending, open_structs,
                                       turns_left))
        return out

    def _do(self, kind, payload):
        if kind == "PLANT":
            return ["PLANT", payload]
        if kind.startswith("PLACE_"):
            return ["PLACE", kind[6:], 1]
        return [kind]

    def _logistics(self, upos, inv, carry, shed_set, shed, wheat_in_shed, need_feed,
                   animals_pending, open_structs, turns_left):
        P = self.P
        at_shed = tuple(upos) in shed_set
        if self.P["last_day_dump"] and self._final_day:
            if at_shed:
                return ["DROP"] if carry > 0 else ["PASS"]
            if carry > 0:
                near = min(shed_set, key=lambda p: manhattan(upos, p))
                mv = step_toward(upos, near)
                return [mv] if mv else ["PASS"]
        want_animal_pickup = animals_pending > 0 and open_structs > 0 and not any(
            inv.get(a, 0) for a in ANIMALS)
        want_wheat = need_feed and wheat_in_shed > 0 and inv.get("WHEAT", 0) < 5
        if at_shed:
            if carry >= P["drop_threshold"] or (carry > 0 and turns_left <= 2):
                return ["DROP"]
            if want_animal_pickup:
                for a in ANIMALS:
                    if shed.get(a, 0) > 0:
                        return ["PICKUP", a, 1]
            if want_wheat:
                return ["PICKUP", "WHEAT", min(10, wheat_in_shed)]
            if carry > 0:
                return ["DROP"]
            return ["PASS"]
        if carry >= P["drop_threshold"] or want_animal_pickup or want_wheat:
            near = min(shed_set, key=lambda p: manhattan(upos, p))
            mv = step_toward(upos, near)
            return [mv] if mv else ["PASS"]
        return ["PASS"]
