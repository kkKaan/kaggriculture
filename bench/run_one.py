import sys, time, json
from kaggle_environments import make

def run(a, b, seed=None, steps=720, debug=False):
    cfg = {"episodeSteps": steps}
    if seed is not None:
        cfg["seed"] = int(seed)
    env = make("kaggriculture", configuration=cfg, debug=debug)
    env.run([a, b])
    last = env.steps[-1]
    return [float(s["reward"] or 0) for s in last], env

if __name__ == "__main__":
    t = time.time()
    r, env = run("starter", "random", seed=1)
    print("rewards", r, "elapsed %.1fs" % (time.time()-t))
