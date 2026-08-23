"""Summarise every downloaded replay into one compact table."""
import json, os, glob, gc, collections, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ME = "kkKaan"
OUT = "data/corpus.json"


def profile(S, p):
    land = []; prev = 1; pk = 0; pkpl = 0; d0 = 0
    mix = collections.Counter()
    for day in range(30):
        i = min(day * 24 + 23, len(S) - 1)
        f = S[i][0]["observation"]["farms"][p]
        q = len(f["unlocked_quadrants"])
        if q > prev:
            land.append(day); prev = q
        an = pl = 0
        for r in f["tiles"]:
            for t in r:
                if isinstance(t, dict):
                    if "animal" in t: an += 1; mix[t["animal"]] += 1
                    elif t.get("kind") == "PLANT": pl += 1; mix[t["crop"]] += 1
        pk = max(pk, an); pkpl = max(pkpl, pl)
        if day == 0: d0 = an
    acts = collections.Counter()
    for st in S[1:]:
        a = st[p].get("action")
        if isinstance(a, dict):
            for u in [a.get("farmer")] + list(a.get("hands") or []):
                if isinstance(u, list) and u: acts[u[0]] += 1
    tot = max(1, sum(acts.values()))
    return dict(d0_animals=d0, peak_animals=pk, peak_plants=pkpl, land=land,
                acts=tot, pas=round(100.0 * acts["PASS"] / tot),
                mix={k: v for k, v in mix.items()})


rows = []
for path in sorted(glob.glob("replays/raw/*.json")):
    try:
        d = json.load(open(path))
    except Exception:
        continue
    S = d.get("steps") or []
    if len(S) < 700:
        del d; gc.collect(); continue
    names = [a["Name"] for a in d["info"]["Agents"]]
    if ME not in names:
        del d; gc.collect(); continue
    me = names.index(ME); opp = 1 - me
    rows.append(dict(
        ep=os.path.basename(path).split(".")[0].replace("episode-", "").replace("-replay", ""),
        opponent=names[opp],
        us=d["rewards"][me], them=d["rewards"][opp],
        win=d["rewards"][me] > d["rewards"][opp],
        seed=d["info"].get("seed"),
        ours=profile(S, me), theirs=profile(S, opp),
        end_prices=S[-1][0]["observation"]["market"]["prices"],
        shops=dict(collections.Counter(S[-1][0]["observation"]["town"]["unlocked_shops"])),
    ))
    del d, S; gc.collect()

os.makedirs("data", exist_ok=True)
json.dump(rows, open(OUT, "w"))
w = sum(1 for r in rows if r["win"])
print(f"{len(rows)} games with us | record {w}W {len(rows)-w}L = {100.0*w/max(1,len(rows)):.1f}%")
print(f"mean ours ${sum(r['us'] for r in rows)/max(1,len(rows)):,.0f}  "
      f"mean theirs ${sum(r['them'] for r in rows)/max(1,len(rows)):,.0f}")
