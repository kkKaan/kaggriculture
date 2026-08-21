"""Kaggriculture agent core.

Self-contained: constants mirrored from the environment so the agent can
predict market prices and yield curves without importing kaggle_environments.
"""
import math

# ---------------------------------------------------------------- constants
CROPS = {
    "WHEAT":      {"seed": 10, "first_yield_day": 2,  "max_yield_day": 4,  "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20, "first_yield_day": 2,  "max_yield_day": 3,  "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50, "first_yield_day": 8,  "max_yield_day": 8,  "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100,"first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
CROP_PRODUCT = {c: c for c in CROPS}
MARKET_I0 = 10000
PRICE_FLOOR = 1
HINGE_GAIN = 8.0
MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt",  "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": MARKET_I0, "T": 450, "below_func": "hinge", "below_target": 1.00, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": MARKET_I0, "T": 200, "below_func": "hinge", "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": MARKET_I0, "T": 100, "below_func": "sqrt",  "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": MARKET_I0, "T": 300, "below_func": "log",   "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": MARKET_I0, "T": 332, "below_func": "hinge", "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": MARKET_I0, "T": 122, "below_func": "sqrt",  "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": MARKET_I0, "T": 105, "below_func": "log",   "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": MARKET_I0, "T": 200, "below_func": "linear","below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}
LAND_PRICES = [1000, 2000, 4000]
LAND_ORDER = ["NE", "SW", "SE"]
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}


def _shape(func, x, T=None):
    x = max(0.0, x)
    if func == "linear": return x
    if func == "sq":     return x * x
    if func == "sqrt":   return math.sqrt(x)
    if func == "log":    return math.log(1.0 + x)
    if func == "log10":  return math.log10(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + HINGE_GAIN * max(0.0, u - 1.0) ** 2
    return x


_AMP = {}
for _it, _p in MARKET_PARAMS.items():
    _AMP[_it] = (
        _p["below_target"] * _p["base"] / _shape(_p["below_func"], _p["T"], _p["T"]),
        _p["above_target"] * _p["base"] / _shape(_p["above_func"], _p["T"], _p["T"]),
    )


def market_price(item, inventory):
    p = MARKET_PARAMS[item]
    base, I0, T = p["base"], p["I0"], p["T"]
    if inventory < I0:
        price = base + _AMP[item][0] * _shape(p["below_func"], I0 - inventory, T)
    else:
        price = base - _AMP[item][1] * _shape(p["above_func"], inventory - I0, T)
    return max(PRICE_FLOOR, int(round(price)))


def sell_revenue(item, qty, inv):
    """Total revenue from selling `qty` units starting at market inventory `inv`.
    Units sold at the $1 floor do not raise inventory, matching the engine."""
    if qty <= 0:
        return 0.0
    total = 0.0
    cur = inv
    n = int(qty)
    # Cheap path: price is flat once floored.
    for _ in range(min(n, 400)):
        pr = market_price(item, cur)
        total += pr
        if pr > 1:
            cur += 1
    if n > 400:
        total += (n - 400) * market_price(item, cur)
    return total


def avg_sell_price(item, qty, inv):
    if qty <= 0:
        return market_price(item, inv)
    return sell_revenue(item, qty, inv) / qty


# ------------------------------------------------------------------ helpers
def quadrant_of(x, y, n):
    h = n // 2
    return ("N" if y < h else "S") + ("W" if x < h else "E")


def shed_tiles(n):
    h = n // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(pos, target):
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    if abs(dx) >= abs(dy):
        if dx > 0: return "EAST"
        if dx < 0: return "WEST"
    if dy > 0: return "SOUTH"
    if dy < 0: return "NORTH"
    if dx > 0: return "EAST"
    if dx < 0: return "WEST"
    return None


def water_window(crop):
    cd = CROPS[crop]
    return (cd["max_yield_day"] + 1) // 2, cd["max_yield_day"]


def expected_units(crop, fertilized=False):
    """Harvestable units for a one-time crop under the alternate-day + window watering plan."""
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["max_yield"]
    ws, we = water_window(crop)
    per = 2 if fertilized else 1
    return min(cd["max_yield"], 1 + per * (we - ws + 1))


def harvest_day(crop, fertilized=False):
    """Earliest day (age) at which the plant reaches its achievable max yield."""
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["first_yield_day"] + cd["interval"] * (cd["max_yield"] - 1)
    ws, we = water_window(crop)
    per = 2 if fertilized else 1
    need = cd["max_yield"] - 1
    days = math.ceil(need / per)
    return min(we, ws + days - 1)


def watering_days(crop, fertilized=False):
    """Set of ages on which the plant must be watered: survival (alternate) + bonus window."""
    hd = harvest_day(crop, fertilized)
    ws, we = water_window(crop)
    days = set()
    for d in range(ws, min(we, hd) + 1):
        days.add(d)
    if CROPS[crop]["ongoing"]:
        days = set()
    # survival watering: must water day 0 (planting day counts as unwatered),
    # then never skip two in a row.
    d = 0
    last = 0
    days.add(0)
    for d in range(1, hd + 1):
        if d in days:
            last = d
        elif d - last >= 2:
            days.add(d)
            last = d
    return days
