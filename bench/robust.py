"""Robustness: many seeds vs several opponents, checking for errors, zeros, slow turns."""
import os, sys, time, argparse
from concurrent.futures import ProcessPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _one(job):
    opp, seed, flip = job
    sys.path.insert(0, ROOT)
    import time as _t
    from kaggle_environments import make
    from variants import make_agent
    sub_agent = make_agent("sub")
    times = []

    def timed(obs, config=None):
        t0 = _t.perf_counter()
        r = sub_agent(obs)
        times.append(_t.perf_counter() - t0)
        return r

    other = make_agent(opp) if opp in ("pass", "random", "starter") else make_agent(opp)
    ag = [timed, other]
    if flip:
        ag = ag[::-1]
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed},
               debug=False)
    err = None
    try:
        env.run(ag)
    except Exception as e:
        return (opp, seed, None, None, 0.0, "RUN:%s" % e)
    last = env.steps[-1]
    r = [float(s["reward"] or 0) for s in last]
    st = [s["status"] for s in last]
    if flip:
        r = r[::-1]; st = st[::-1]
    if st[0] != "DONE":
        err = "STATUS:%s" % st[0]
    return (opp, seed, r[0], r[1], max(times) if times else 0.0, err)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-n", "--seeds", type=int, default=25)
    p.add_argument("-w", "--workers", type=int, default=10)
    p.add_argument("--opps", nargs="+", default=["champ", "starter", "random", "pass"])
    a = p.parse_args()
    jobs = [(o, 7000 + s, f) for o in a.opps for s in range(a.seeds) for f in (False, True)]
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(_one, jobs):
            res.append(r)
    by = {}
    worst_t = 0.0
    problems = []
    for opp, seed, ra, rb, mt, err in res:
        worst_t = max(worst_t, mt)
        d = by.setdefault(opp, [0, 0, 0, 0.0, 1e18])
        if err or ra is None:
            problems.append((opp, seed, err)); continue
        if ra > rb: d[0] += 1
        elif ra < rb: d[1] += 1
        else: d[2] += 1
        d[3] += ra
        d[4] = min(d[4], ra)
        if ra < 5000:
            problems.append((opp, seed, "LOW:%.0f" % ra))
    print(f"robustness over {a.seeds*2} games/opponent ({time.time()-t0:.0f}s)")
    for opp, (w, l, t, s, mn) in by.items():
        n = max(1, w + l + t)
        print(f"  vs {opp:<9} W{w:<3} L{l:<3} T{t:<3} winrate={100.0*(w+0.5*t)/n:5.1f}%"
              f"  mean=${s/n:>9,.0f}  min=${mn:>9,.0f}")
    print(f"  worst single-turn time: {1000*worst_t:.0f} ms")
    print(f"  problems: {len(problems)}")
    for pr in problems[:10]:
        print("   ", pr)


if __name__ == "__main__":
    main()
