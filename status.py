"""Fetch any new replays and report each submission's real record.

    python status.py

Safe to re-run; only downloads episodes not already present.
"""
import os, sys, json, subprocess, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
KAGGLE = os.path.join(ROOT, ".venv", "bin", "kaggle")
PY = os.path.join(ROOT, ".venv", "bin", "python")


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


def main():
    subs = sh(KAGGLE, "competitions", "submissions", "kaggriculture")
    print(subs.stdout or subs.stderr)
    ids, desc = [], {}
    for line in subs.stdout.splitlines():
        tok = line.split()
        if tok and tok[0].isdigit() and len(tok[0]) >= 8:
            ids.append(tok[0])
            # description sits between the date and the status column
            d = line.split("  ")
            desc[tok[0]] = next((x.strip() for x in d[3:] if x.strip()
                                 and "Submission" not in x), "")[:34]
    sh(PY, os.path.join(ROOT, "fetch_replays.py"), *ids)
    sh(PY, os.path.join(ROOT, "bench", "corpus.py"))

    m = {}
    for sid in ids:
        out = sh(KAGGLE, "competitions", "episodes", sid).stdout
        for line in out.splitlines():
            tok = line.split()
            if tok and tok[0].isdigit() and len(tok[0]) >= 8:
                m[tok[0]] = sid
    rows = json.load(open(os.path.join(ROOT, "data", "corpus.json")))
    agg = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
    for r in rows:
        sid = m.get(r["ep"])
        if not sid:
            continue
        a = agg[sid]
        a[0] += 1 if r["win"] else 0
        a[1] += 1
        a[2] += r["us"]; a[3] += r["them"]
    print(f"{'submission':<12}{'description':<36}{'W':>4}{'N':>5}{'winrate':>9}"
          f"{'+/-':>6}{'mean us':>11}")
    for sid, (w, n, su, so) in sorted(agg.items(),
                                      key=lambda kv: -(kv[1][0] / max(1, kv[1][1]))):
        wr = 100.0 * w / max(1, n)
        se = 100.0 * (0.25 / max(1, n)) ** 0.5   # 1 s.e. on a proportion near 0.5
        print(f"{sid:<12}{desc.get(sid,''):<36}{w:>4}{n:>5}{wr:>8.1f}%{se:>5.1f}%{su/max(1,n):>11,.0f}")
    print("\nDifferences smaller than roughly 2x the +/- column are noise.")


if __name__ == "__main__":
    sys.exit(main() or 0)
