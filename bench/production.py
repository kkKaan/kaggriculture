"""Count what each player actually harvested, from the replay action log."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_core import ANIMALS


def production(path):
    d = json.load(open(path))
    steps = d["steps"]
    names = [a["Name"] for a in d["info"]["Agents"]]
    out = []
    for p in (0, 1):
        got = collections.Counter()
        # steps[i] records the state AFTER its own action, so pair the action at
        # step i with the board as it stood at step i-1.
        for i in range(1, len(steps)):
            o = steps[i - 1][0]["observation"]
            if "farms" not in o:
                continue
            tiles = o["farms"][p]["tiles"]
            farm = o["farms"][p]
            a = steps[i][p].get("action")
            if not isinstance(a, dict):
                continue
            units = [farm["farmer"]] + list(farm.get("hands") or [])
            ops = [a.get("farmer")] + list(a.get("hands") or [])
            for pos, op in zip(units, ops):
                if not (isinstance(op, list) and op and op[0] == "HARVEST"):
                    continue
                x, y = pos[0], pos[1]
                t = tiles[y][x]
                if not isinstance(t, dict):
                    continue
                n = t.get("yield_units", 0)
                if t.get("kind") == "PLANT":
                    got[t["crop"]] += n
                elif "animal" in t:
                    got[ANIMALS[t["animal"]]["product"]] += n
        out.append((names[p], got))
    return out, d["rewards"]


for path in sys.argv[1:]:
    res, rew = production(path)
    print(f"--- {path.split('/')[-1]}  rewards {rew} ---")
    allk = sorted(set(k for _, g in res for k in g), key=lambda k: -max(g.get(k, 0) for _, g in res))
    print(f"{'product':<12} " + " ".join(f"{n[:14]:>15}" for n, _ in res))
    for k in allk:
        print(f"{k:<12} " + " ".join(f"{g.get(k,0):>15}" for _, g in res))
    print()
