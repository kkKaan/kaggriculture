"""Run many challengers against a champion; report winrates."""
import os, sys, argparse, time
from concurrent.futures import ProcessPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _one(job):
    a, b, seed, flip = job
    sys.path.insert(0, ROOT)
    from kaggle_environments import make
    from variants import make_agent
    ag = [make_agent(a), make_agent(b)]
    if flip:
        ag = ag[::-1]
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    try:
        env.run(ag)
    except Exception as e:
        return (a, None, None, str(e))
    r = [float(s["reward"] or 0) for s in env.steps[-1]]
    if flip:
        r = r[::-1]
    return (a, r[0], r[1], None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("champ")
    p.add_argument("challengers", nargs="+")
    p.add_argument("-n", "--seeds", type=int, default=8)
    p.add_argument("-w", "--workers", type=int, default=10)
    a = p.parse_args()
    jobs = []
    for c in a.challengers:
        for s in range(a.seeds):
            jobs.append((c, a.champ, 2000 + s, False))
            jobs.append((c, a.champ, 2000 + s, True))
    t0 = time.time()
    agg = {c: [0, 0, 0, 0.0, 0.0, 1e18] for c in a.challengers}  # w,l,t,sumA,sumB,minA
    errs = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for name, ra, rb, err in ex.map(_one, jobs):
            if err:
                errs.append((name, err)); continue
            g = agg[name]
            if ra > rb: g[0] += 1
            elif ra < rb: g[1] += 1
            else: g[2] += 1
            g[3] += ra; g[4] += rb; g[5] = min(g[5], ra)
    rows = []
    for c, (w, l, t, sa, sb, mn) in agg.items():
        n = max(1, w + l + t)
        rows.append((100.0 * (w + 0.5 * t) / n, c, w, l, t, sa / n, sb / n, mn))
    rows.sort(reverse=True)
    print(f"vs {a.champ}  ({a.seeds*2} games each, {time.time()-t0:.0f}s)")
    for wr, c, w, l, t, ma, mb, mn in rows:
        flag = "  !!LOW" if mn < 0.25 * ma else ""
        print(f"  {wr:5.1f}%  {c:<14} W{w:<3} L{l:<3} T{t:<3}  ${ma:>9,.0f} vs ${mb:>9,.0f}  min=${mn:>8,.0f}{flag}")
    if errs:
        print("ERR:", errs[:3])


if __name__ == "__main__":
    main()
