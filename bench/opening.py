"""Day-by-day opening: when does each player buy land vs animals?"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def opening(path, days=16):
    d = json.load(open(path))
    steps = d["steps"]
    names = [a["Name"] for a in d["info"]["Agents"]]
    print(f"=== {os.path.basename(path)}  {names[0]} {d['rewards'][0]:,.0f}  vs  "
          f"{names[1]} {d['rewards'][1]:,.0f} ===")
    # count market orders by type per day per player
    orders = [collections.defaultdict(collections.Counter) for _ in range(2)]
    for i in range(1, len(steps)):
        o = steps[i - 1][0]["observation"]
        if "farms" not in o:
            continue
        day = o.get("day", 0)
        for p in (0, 1):
            a = steps[i][p].get("action")
            if not isinstance(a, dict):
                continue
            for m in (a.get("market") or []):
                if isinstance(m, list) and m:
                    key = m[0] if m[0] in ("BUY_LAND", "HIRE") else f"{m[0]}:{m[1]}"
                    orders[p][day][key] += 1
    hdr = (f"{'day':>3} | {names[0][:13]:>13} {'$':>8} {'q':>2} {'an':>3} {'pl':>3} "
           f"| {names[1][:13]:>13} {'$':>8} {'q':>2} {'an':>3} {'pl':>3}")
    print(hdr)
    for day in range(days):
        i = min(day * 24 + 23, len(steps) - 1)
        o = steps[i][0]["observation"]
        row = f"{day:>3} |"
        for p in (0, 1):
            f = o["farms"][p]
            an = pl = 0
            for r in f["tiles"]:
                for t in r:
                    if isinstance(t, dict):
                        if "animal" in t: an += 1
                        elif t.get("kind") == "PLANT": pl += 1
            buys = orders[p][day]
            tag = []
            if buys.get("BUY_LAND"): tag.append(f"LAND x{buys['BUY_LAND']}")
            for k, v in buys.items():
                if k.startswith("BUY_ANIMAL"): tag.append(f"{k.split(':')[1][:3]}x{v}")
            row += (f" {','.join(tag)[:13]:>13} {f['money']:>8,.0f} "
                    f"{len(f['unlocked_quadrants']):>2} {an:>3} {pl:>3} |")
        print(row)
    # totals
    for p in (0, 1):
        tot = collections.Counter()
        for day, c in orders[p].items():
            tot.update(c)
        land_days = [day for day, c in sorted(orders[p].items()) if c.get("BUY_LAND")]
        anim = {k.split(":")[1]: v for k, v in tot.items() if k.startswith("BUY_ANIMAL")}
        print(f"[{names[p]}] land bought on days {land_days}   animals bought {anim}")
    print()


for path in sys.argv[1:]:
    opening(path)
