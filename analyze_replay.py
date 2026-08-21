"""Summarise a downloaded Kaggle replay JSON: money curve, prices, action mix."""
import json, sys, collections


def main(path, me=0):
    d = json.load(open(path))
    steps = d["steps"]
    print("steps:", len(steps))
    final = steps[-1]
    print("final rewards:", [s.get("reward") for s in final])
    acts = collections.Counter()
    for st in steps[1:]:
        a = st[me].get("action") or {}
        if not isinstance(a, dict):
            continue
        for u in [a.get("farmer")] + list(a.get("hands") or []):
            if isinstance(u, list) and u:
                acts[u[0]] += 1
    tot = max(1, sum(acts.values()))
    print("action mix:", {k: f"{100.0*v/tot:.0f}%" for k, v in acts.most_common(14)})
    print(f"{'day':>4} {'me':>10} {'opp':>10}")
    for i in range(0, len(steps), 48):
        o = steps[i][0]["observation"]
        f = o.get("farms")
        if not f:
            continue
        print(f"{o.get('day', 0):>4} {f[me]['money']:>10,.0f} {f[1-me]['money']:>10,.0f}")
    o = steps[-1][0]["observation"]
    if o.get("market"):
        print("end prices:", o["market"]["prices"])
        print("mkt delta :", {k: v - 10000 for k, v in o["market"]["inventory"].items()})


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0)
