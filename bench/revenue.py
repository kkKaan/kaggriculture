import sys, os, collections
sys.path.insert(0, os.path.abspath('.'))
from kaggle_environments import make
from variants import make_agent
from agent_core import market_price, PRODUCTS, CROPS, ANIMALS

def run(a, b, seed=3):
    ag = make_agent(a)
    log = collections.Counter(); qty = collections.Counter()
    spend = collections.Counter()
    prices = {}
    def wrap(obs, config=None):
        r = ag(obs)
        inv = (obs.get("market") or {}).get("inventory") or {}
        for o in r.get("market", []):
            if not isinstance(o, list) or not o: continue
            if o[0] == "SELL":
                it, n = o[1], int(o[2])
                have = ((obs.get("private") or {}).get("shed") or {}).get(it, 0)
                n = min(n, have)
                p = market_price(it, inv.get(it, 10000))
                log[it] += p * n; qty[it] += n
            elif o[0] == "BUY_SEED":
                spend["seed:" + o[1]] += CROPS[o[1]]["seed"] * int(o[2])
            elif o[0] == "BUY_ANIMAL":
                spend["animal:" + o[1]] += ANIMALS[o[1]]["cost"] * int(o[2])
            elif o[0] == "BUY_PRODUCT":
                spend["buy:" + o[1]] += market_price(o[1], inv.get(o[1], 10000)-1) * int(o[2])
            elif o[0] == "BUY_LAND":
                spend["land"] += 1
            elif o[0] == "HIRE":
                spend["hire"] += 1
        return r
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([wrap, make_agent(b)])
    print(f"{a} vs {b} seed{seed}: {[s['reward'] for s in env.steps[-1]]}")
    tot = sum(log.values())
    print("REVENUE (approx):")
    for k, v in log.most_common():
        print(f"   {k:<12} ${v:>9,.0f}  {100.0*v/max(1,tot):>5.1f}%   units={qty[k]:>5}  avg=${v/max(1,qty[k]):>6.1f}")
    print(f"   {'TOTAL':<12} ${tot:>9,.0f}")
    print("SPEND:", dict(spend.most_common()))

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else "champ",
        int(sys.argv[3]) if len(sys.argv)>3 else 3)
