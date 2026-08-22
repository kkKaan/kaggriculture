"""Deep-dive a replay: per-player farm composition, action mix, economy curve."""
import json, sys, collections


def load(path):
    return json.load(open(path))


def study(path):
    d = load(path)
    steps = d["steps"]
    names = [a["Name"] for a in d["info"]["Agents"]]
    print(f"{names[0]}  vs  {names[1]}")
    print("final:", d["rewards"], "seed:", d["info"].get("seed"))
    print()

    # ---- action mix per player
    acts = [collections.Counter(), collections.Counter()]
    hands_seen = [collections.Counter(), collections.Counter()]
    for st in steps[1:]:
        for p in (0, 1):
            a = st[p].get("action")
            if not isinstance(a, dict):
                continue
            units = [a.get("farmer")] + list(a.get("hands") or [])
            for u in units:
                if isinstance(u, list) and u:
                    acts[p][u[0]] += 1
    for p in (0, 1):
        tot = max(1, sum(acts[p].values()))
        top = ", ".join(f"{k} {100.0*v/tot:.0f}%" for k, v in acts[p].most_common(10))
        move = sum(acts[p][k] for k in ("NORTH", "SOUTH", "EAST", "WEST"))
        print(f"[{names[p]}] actions={tot}  move={100.0*move/tot:.0f}%  pass={100.0*acts[p]['PASS']/tot:.0f}%")
        print(f"   {top}")
    print()

    # ---- per-day farm snapshot
    hdr = f"{'day':>3} | {'$0':>8} {'q0':>2} {'h0':>3} {'pl0':>3} {'an0':>3} | {'$1':>8} {'q1':>2} {'h1':>3} {'pl1':>3} {'an1':>3}"
    print(hdr)
    for day in range(0, 30, 2):
        i = min(day * 24 + 12, len(steps) - 1)
        o = steps[i][0]["observation"]
        row = f"{day:>3} |"
        for p in (0, 1):
            f = o["farms"][p]
            pl = an = 0
            for r in f["tiles"]:
                for t in r:
                    if isinstance(t, dict):
                        if t.get("kind") == "PLANT": pl += 1
                        elif "animal" in t: an += 1
            row += (f" {f['money']:>8,.0f} {len(f['unlocked_quadrants']):>2} "
                    f"{len(f['hands']):>3} {pl:>3} {an:>3} |")
        print(row)
    print()

    # ---- crop / animal tile-days
    for p in (0, 1):
        mix, amix = collections.Counter(), collections.Counter()
        for i in range(0, len(steps), 24):
            for r in steps[i][0]["observation"]["farms"][p]["tiles"]:
                for t in r:
                    if isinstance(t, dict):
                        if t.get("kind") == "PLANT": mix[t["crop"]] += 1
                        elif "animal" in t: amix[t["animal"]] += 1
        print(f"[{names[p]}] crops {dict(mix)}  animals {dict(amix)}")
    print()

    # ---- hires per day
    for p in (0, 1):
        peak = []
        for day in range(30):
            hi = 0
            for h in range(24):
                i = min(day * 24 + h, len(steps) - 1)
                hi = max(hi, len(steps[i][0]["observation"]["farms"][p]["hands"]))
            peak.append(hi)
        print(f"[{names[p]}] peak hands/day: {peak}")
    print()

    o = steps[-1][0]["observation"]
    print("end prices:", o["market"]["prices"])
    print("mkt delta :", {k: v - 10000 for k, v in o["market"]["inventory"].items()})
    print("shops:", dict(collections.Counter(o["town"]["unlocked_shops"])))


if __name__ == "__main__":
    study(sys.argv[1])
