"""Evaluate a candidate against a DIVERSE opponent pool, not just the mirror.

Mirror self-play systematically undervalues anything both sides would flood:
if both agents build cows, milk crashes and the mirror concludes cows are bad.
Real ladders are diverse, so score against a spread of strategies.
"""
import sys, os, gc, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kaggle_environments import make
from variants import make_agent

POOL = ["champ", "premium", "flooder", "bigfarm"]


def evaluate(cand, pool=None, seeds=5, base=8100, verbose=True):
    pool = pool or POOL
    total_w = total_n = 0
    rows = []
    for opp in pool:
        w = l = t = 0
        sa = sb = 0.0
        for s in range(seeds):
            for flip in (False, True):
                ag = [make_agent(cand), make_agent(opp)]
                if flip:
                    ag = ag[::-1]
                env = make("kaggriculture",
                           configuration={"episodeSteps": 720, "seed": base + s})
                env.run(ag)
                r = [float(x["reward"] or 0) for x in env.steps[-1]]
                if flip:
                    r = r[::-1]
                sa += r[0]; sb += r[1]
                if r[0] > r[1]: w += 1
                elif r[0] < r[1]: l += 1
                else: t += 1
                env.steps = None; del env; gc.collect()
        n = w + l + t
        total_w += w + 0.5 * t; total_n += n
        rows.append((opp, w, l, t, 100.0 * (w + 0.5 * t) / n, sa / n, sb / n))
    if verbose:
        for opp, w, l, t, wr, ma, mb in rows:
            print(f"   vs {opp:<10} W{w:<3} L{l:<3} T{t:<2} {wr:5.1f}%   ${ma:>9,.0f} vs ${mb:>9,.0f}")
    wr = 100.0 * total_w / max(1, total_n)
    print(f"   POOL winrate {wr:.1f}%  ({total_n} games)")
    return wr


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cands", nargs="+")
    p.add_argument("-n", "--seeds", type=int, default=5)
    a = p.parse_args()
    res = []
    for c in a.cands:
        print(f"[{c}]")
        res.append((evaluate(c, seeds=a.seeds), c))
    print()
    for wr, c in sorted(res, reverse=True):
        print(f"{wr:5.1f}%  {c}")
