import sys, os, collections
sys.path.insert(0, os.path.abspath('.'))
from kaggle_environments import make
from variants import make_agent
from agent_core import PRODUCTS

def diag(a, b, seed=3):
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([make_agent(a), make_agent(b)])
    S = env.steps
    print(f"{a} vs {b} seed{seed} final:", [s["reward"] for s in S[-1]])
    print(f"{'day':>3} {'$0':>8} {'$1':>8} {'hd':>3} {'emp':>4} {'pl':>3} {'an':>3} {'wd':>3} {'shed':>4} {'q':>2} | idle%")
    for d in range(0, 30, 2):
        i = min(d*24+12, len(S)-1)
        st = S[i]; o = st[0]["observation"]
        f0, f1 = o["farms"][0], o["farms"][1]
        tl = f0["tiles"]
        cnt = collections.Counter()
        for r in tl:
            for t in r:
                if t is None: cnt["e"] += 1
                elif t == "LOCKED": cnt["L"] += 1
                elif t.get("kind") == "PLANT": cnt["p"] += 1
                elif t.get("kind") == "WEED": cnt["w"] += 1
                elif "animal" in t: cnt["a"] += 1
                else: cnt["s"] += 1
        shed = sum((st[0]["observation"].get("private") or {}).get("shed", {}).values())
        print(f"{d:>3} {f0['money']:>8.0f} {f1['money']:>8.0f} {len(f0['hands']):>3} {cnt['e']:>4} {cnt['p']:>3} {cnt['a']:>3} {cnt['w']:>3} {shed:>4} {len(f0['unlocked_quadrants']):>2}")
    o = S[-1][0]["observation"]
    print("end prices:", o["market"]["prices"])
    print("mkt delta :", {k: o["market"]["inventory"][k]-10000 for k in PRODUCTS})
    mix = collections.Counter()
    for i in range(0, len(S), 24):
        for r in S[i][0]["observation"]["farms"][0]["tiles"]:
            for t in r:
                if isinstance(t, dict) and t.get("kind")=="PLANT": mix[t["crop"]] += 1
    print("crop tile-days:", dict(mix))
    # action utilisation
    acts = collections.Counter()
    for st in S[1:]:
        a = st[0].get("action") or {}
        if not isinstance(a, dict): continue
        for u in [a.get("farmer")] + list(a.get("hands") or []):
            if isinstance(u, list) and u: acts[u[0]] += 1
    tot = sum(acts.values())
    print("actions:", {k: f"{100.0*v/max(1,tot):.0f}%" for k, v in acts.most_common(12)}, "total", tot)

if __name__ == "__main__":
    diag(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 3)
