import sys, os, json, collections
sys.path.insert(0, os.path.abspath('.'))
from kaggle_environments import make
from agent_core import market_price, PRODUCTS

def diag(a, b="starter", seed=3, steps=720):
    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env.run([a, b])
    steps_ = env.steps
    print("final:", [s["reward"] for s in steps_[-1]])
    hdr = f"{'day':>4} {'money0':>8} {'money1':>8} {'hands':>5} {'tiles':>6} {'plants':>6} {'anim':>5} {'weed':>5} {'shed':>5} {'quad':>4}"
    print(hdr)
    for d in range(0, 30, 2):
        st = steps_[min(d*24+23, len(steps_)-1)]
        o = st[0]["observation"]
        f0 = o["farms"][0]; f1 = o["farms"][1]
        tl = f0["tiles"]
        plants = sum(1 for r in tl for t in r if isinstance(t, dict) and t.get("kind")=="PLANT")
        anim = sum(1 for r in tl for t in r if isinstance(t, dict) and "animal" in t)
        weed = sum(1 for r in tl for t in r if isinstance(t, dict) and t.get("kind")=="WEED")
        empty = sum(1 for r in tl for t in r if t is None)
        shed = sum((st[0]["observation"].get("private") or {}).get("shed", {}).values())
        print(f"{d:>4} {f0['money']:>8.0f} {f1['money']:>8.0f} {len(f0['hands']):>5} {empty:>6} {plants:>6} {anim:>5} {weed:>5} {shed:>5} {len(f0['unlocked_quadrants']):>4}")
    o = steps_[-1][0]["observation"]
    print("prices:", {k: v for k, v in o["market"]["prices"].items()})
    print("mkt inv delta:", {k: o["market"]["inventory"][k]-10000 for k in PRODUCTS})
    print("shops:", collections.Counter(o["town"]["unlocked_shops"]))
    # crop mix over season
    mix = collections.Counter()
    for i in range(0, len(steps_), 24):
        o = steps_[i][0]["observation"]
        for r in o["farms"][0]["tiles"]:
            for t in r:
                if isinstance(t, dict) and t.get("kind")=="PLANT":
                    mix[t["crop"]] += 1
    print("crop tile-days(sampled):", dict(mix))
    return env

if __name__ == "__main__":
    from main import agent
    diag(agent, sys.argv[1] if len(sys.argv)>1 else "starter", int(sys.argv[2]) if len(sys.argv)>2 else 3)
