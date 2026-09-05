"""Hill-climbing parameter search: mutate the champion, keep what beats it."""
import gc, os, sys, json, time, random, argparse, copy
from concurrent.futures import ProcessPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BRAIN = os.environ.get("BRAIN", "crop")     # "crop" or "animal"
CJ = os.path.join(ROOT, "champion.json" if BRAIN == "crop" else "champion_animal.json")
LOG = os.path.join(ROOT, "evolve_log.txt")

# name -> (low, high, kind)  kind: f=float, i=int, b=bool
ANIMAL_EXTRA = {
    "open_animals":     (3, 7, "i"),
    "open_days":        (1, 4, "i"),
    "open_seed_cash":   (200.0, 900.0, "f"),
    "open_hands":       (3, 8, "i"),
    "land_min_cash":    (0.0, 600.0, "f"),
    "place_value":      (300.0, 900.0, "f"),
    "fetch_animal_value": (250.0, 700.0, "f"),
    "wheat_tiles":      (0, 20, "i"),
    "wheat_cash_floor": (0.0, 120.0, "f"),
    "build_urgent":     (150.0, 500.0, "f"),
}

SPACE = {
    "hire_overhead":      (2.4, 5.2, "f"),
    "max_hands":          (8, 16, "i"),
    "hire_per_turn":      (2, 6, "i"),
    "keep_frac":          (0.05, 0.6, "f"),
    "keep_frac_premium":  (0.03, 0.5, "f"),
    "endgame_dump_day":   (21, 29, "i"),
    "animal_target":      (8, 22, "i"),
    "land_buffer":        (100, 3000, "f"),
    "land_max":           (0, 2, "i"),
    "land_free_gate":     (10, 45, "i"),
    "wheat_buy_max":      (20, 95, "f"),
    "wheat_reserve_days": (0.5, 3.5, "f"),
    "drop_threshold":     (3, 20, "i"),
    "shed_soft_cap":      (40, 95, "i"),
    "plant_min_value":    (0.0, 15.0, "f"),
    "seed_cash_floor":    (20, 400, "f"),
    "dist_decay":         (0.6, 2.6, "f"),
    "disc_rich":          (0.90, 1.0, "f"),
    "disc_poor":          (0.80, 0.99, "f"),
    "cash_target":        (800, 6500, "f"),
    "cap_mu":             (1.2, 8.0, "f"),
    "cap_mu_ref":         (4.0, 16.0, "f"),
    "mirror":             (0.05, 1.1, "f"),
    "opp_weight":         (0.2, 1.7, "f"),
    "long_frac_min":      (0.25, 1.0, "f"),
    "long_hd":            (5, 9, "i"),
    "fetch_value":        (60.0, 260.0, "f"),
    "hold_bonus":         (0.5, 1.15, "f"),
    "future_shop_weight": (0.6, 1.9, "f"),
    "rush_window":        (2, 8, "i"),
    "value_scaled_care":  (0, 1, "i"),
    "sell_orders_head":   (3, 10, "i"),
    "fetch_value":        (60.0, 260.0, "f"),
    "plant_near":         (0, 1, "i"),
    "early_harvest":      (0, 1, "i"),
    "rush_sell":          (0, 1, "i"),
}


def mutate(base, rng, n=None):
    p = dict(base)
    keys = list(SPACE)
    if BRAIN == "animal":
        keys = keys + list(ANIMAL_EXTRA)
    n = n or rng.choice([1, 1, 2, 2, 3])
    for k in rng.sample(keys, n):
        lo, hi, kind = (ANIMAL_EXTRA[k] if k in ANIMAL_EXTRA and BRAIN == "animal"
                        else SPACE[k])
        cur = p.get(k, (lo + hi) / 2.0)
        span = (hi - lo)
        if kind == "i":
            step = max(1, int(round(abs(rng.gauss(0, span * 0.18)))))
            v = int(cur) + rng.choice([-1, 1]) * step
            p[k] = max(int(lo), min(int(hi), v))
        else:
            v = cur + rng.gauss(0, span * 0.16)
            p[k] = max(lo, min(hi, round(v, 4)))
    return p


def _free_env(env):
    try:
        env.steps = None
        env.state = None
    except Exception:
        pass
    del env
    gc.collect()


def _one(job):
    cand, champ, seed, flip = job
    sys.path.insert(0, ROOT)
    from kaggle_environments import make
    if BRAIN == "animal":
        from agent_animal import AnimalBrain as _B
    else:
        from agent_brain import Brain as _B

    def mk(params):
        b = _B(params)

        def a(obs, config=None):
            try:
                if obs.get("day", 0) == 0 and obs.get("hour", 0) == 0:
                    b.reset()
                return b.act(obs)
            except Exception:
                return {"farmer": ["PASS"], "hands": [], "market": []}
        return a
    ag = [mk(cand), mk(champ)]
    if flip:
        ag = ag[::-1]
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    try:
        env.run(ag)
    except Exception:
        _free_env(env)
        return (0.0, 0.0)
    r = [float(s["reward"] or 0) for s in env.steps[-1]]
    _free_env(env)
    if flip:
        r = r[::-1]
    return (r[0], r[1])


def evaluate(ex, cand, champ, seeds):
    jobs = [(cand, champ, s, f) for s in seeds for f in (False, True)]
    w = l = t = 0
    tot = 0.0
    for ra, rb in ex.map(_one, jobs):
        tot += ra
        if ra > rb: w += 1
        elif ra < rb: l += 1
        else: t += 1
    n = max(1, w + l + t)
    return (w + 0.5 * t) / n, tot / n, (w, l, t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--pop", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--confirm", type=int, default=40)
    ap.add_argument("--accept", type=float, default=0.60)
    ap.add_argument("--anchor", type=float, default=0.55)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    champ = json.load(open(CJ))
    anchor = dict(champ)          # frozen baseline for the whole run
    log = open(LOG, "a")

    def say(msg):
        print(msg, flush=True)
        log.write(msg + "\n"); log.flush()

    say("=== evolve start %s rounds=%d pop=%d ===" % (time.strftime("%H:%M:%S"), a.rounds, a.pop))
    with ProcessPoolExecutor(max_workers=a.workers, max_tasks_per_child=40) as ex:
        for rd in range(a.rounds):
            base_seed = 30000 + rd * 977
            seeds = [base_seed + i for i in range(a.seeds)]
            cands = [mutate(champ, rng) for _ in range(a.pop)]
            results = []
            t0 = time.time()
            for i, c in enumerate(cands):
                wr, mean, wlt = evaluate(ex, c, champ, seeds)
                diff = {k: (champ.get(k), v) for k, v in c.items() if champ.get(k) != v}
                results.append((wr, mean, c, diff, wlt))
            results.sort(key=lambda r: -r[0])
            top = results[0]
            say("round %d (%.0fs) best=%.1f%% %s" % (
                rd, time.time() - t0, 100 * top[0],
                {k: v[1] for k, v in top[3].items()}))
            if top[0] >= 0.60:
                cseeds = [50000 + rd * 613 + i for i in range(a.confirm)]
                wr2, mean2, wlt2 = evaluate(ex, top[2], champ, cseeds)
                say("   confirm: {:.1f}% W{} L{} T{} mean=${:,.0f}".format(
                    100 * wr2, wlt2[0], wlt2[1], wlt2[2], mean2))
                if wr2 >= a.accept:
                    # Individually-confirmed changes can still stack badly, so
                    # re-check the whole candidate against the run's baseline.
                    aseeds = [70000 + rd * 419 + i for i in range(a.confirm)]
                    wr3, mean3, wlt3 = evaluate(ex, top[2], anchor, aseeds)
                    say("   anchor:  {:.1f}% W{} L{} T{}".format(
                        100 * wr3, wlt3[0], wlt3[1], wlt3[2]))
                    if wr3 >= a.anchor:
                        champ = top[2]
                        json.dump(champ, open(CJ, "w"), indent=1, sort_keys=True)
                        say("   PROMOTED -> %s" % {k: v[1] for k, v in top[3].items()})
                    else:
                        say("   rejected vs anchor (drift guard)")
                else:
                    say("   rejected on confirmation")
    say("=== done ===")


if __name__ == "__main__":
    main()
