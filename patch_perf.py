"""Apply performance + market-order-priority patches to agent_core/agent_brain."""
import re

core = open("agent_core.py").read()
if "_PRICE_CACHE" not in core:
    core = core.replace('''def market_price(item, inventory):
    p = MARKET_PARAMS[item]''', '''_PRICE_CACHE = {}


def market_price(item, inventory):
    key = (item, inventory)
    v = _PRICE_CACHE.get(key)
    if v is not None:
        return v
    v = _market_price_uncached(item, inventory)
    if len(_PRICE_CACHE) < 300000:
        _PRICE_CACHE[key] = v
    return v


def _market_price_uncached(item, inventory):
    p = MARKET_PARAMS[item]''')
    core = core.replace('''def sell_revenue(item, qty, inv):''', '''_REV_CACHE = {}


def sell_revenue(item, qty, inv):
    key = (item, int(qty), inv)
    v = _REV_CACHE.get(key)
    if v is not None:
        return v
    v = _sell_revenue_uncached(item, qty, inv)
    if len(_REV_CACHE) < 200000:
        _REV_CACHE[key] = v
    return v


def _sell_revenue_uncached(item, qty, inv):''')
    open("agent_core.py", "w").write(core)
    print("patched agent_core (price caches)")
else:
    print("agent_core already patched")

brain = open("agent_brain.py").read()
if '"sell_orders_head"' not in brain:
    brain = brain.replace('''    "hire_per_turn": 7,''', '''    "hire_per_turn": 7,
    "sell_orders_head": 10,''')
    brain = brain.replace('''        head.extend(self._sell_orders(shed, minv, drain, day, wheat_reserve))''',
                          '''        sells = self._sell_orders(shed, minv, drain, day, wheat_reserve)
        nhead = P["sell_orders_head"]
        head.extend(sells[:nhead])
        spill = sells[nhead:]''')
    brain = brain.replace('''        return head + tail''', '''        return head + tail + spill''')
    open("agent_brain.py", "w").write(brain)
    print("patched agent_brain (order priority)")
else:
    print("agent_brain already patched")
