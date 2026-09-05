"""Serial head-to-head A/B — slow but survives a memory-starved machine."""
import sys, os, gc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kaggle_environments import make
from variants import make_agent


def ab(a, b, seeds=8, base=6100):
    w = l = t = 0
    sa = sb = 0.0
    for s in range(seeds):
        for flip in (False, True):
            ag = [make_agent(a), make_agent(b)]
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
    n = max(1, w + l + t)
    print(f"{a} vs {b}: W{w} L{l} T{t}  winrate={100.0*(w+0.5*t)/n:.1f}%"
          f"  mean ${sa/n:,.0f} vs ${sb/n:,.0f}  ({n} games)")
    return (w + 0.5 * t) / n


if __name__ == "__main__":
    ab(sys.argv[1], sys.argv[2],
       int(sys.argv[3]) if len(sys.argv) > 3 else 8)
