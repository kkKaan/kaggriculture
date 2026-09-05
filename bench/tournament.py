"""Head-to-head benchmark: run A vs B over N seeds on both sides, in parallel."""
import gc, os, sys, argparse, time, json
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _free_env(env):
    try:
        env.steps = None
        env.state = None
    except Exception:
        pass
    del env
    gc.collect()


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
        return (seed, flip, None, None, str(e))
    last = env.steps[-1]
    r = [float(s["reward"] or 0) for s in last]
    if flip:
        r = r[::-1]
    return (seed, flip, r[0], r[1], None)


def tournament(a, b, seeds=12, workers=8):
    jobs = []
    for s in range(seeds):
        jobs.append((a, b, 1000 + s, False))
        jobs.append((a, b, 1000 + s, True))
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=40) as ex:
        for r in ex.map(_one, jobs):
            res.append(r)
    wins = losses = ties = 0
    sa = sb = 0.0
    errs = []
    for seed, flip, ra, rb, err in res:
        if err:
            errs.append((seed, flip, err)); continue
        sa += ra; sb += rb
        if ra > rb: wins += 1
        elif ra < rb: losses += 1
        else: ties += 1
    n = max(1, wins + losses + ties)
    print(f"{a} vs {b}: W{wins} L{losses} T{ties}  winrate={100.0*(wins+0.5*ties)/n:.1f}%")
    print(f"  mean {a}=${sa/n:,.0f}   mean {b}=${sb/n:,.0f}   ({time.time()-t0:.0f}s, {n} games)")
    if errs:
        print("  ERRORS:", errs[:3])
    return (wins + 0.5 * ties) / n, sa / n, sb / n


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("a"); p.add_argument("b")
    p.add_argument("-n", "--seeds", type=int, default=12)
    p.add_argument("-w", "--workers", type=int, default=4)
    args = p.parse_args()
    tournament(args.a, args.b, args.seeds, args.workers)
