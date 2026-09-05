"""Pull every episode + replay for our submissions, then summarise them.

Needs a Kaggle API token at ~/.kaggle/access_token (or $KAGGLE_API_TOKEN).
Safe to re-run: it skips replays already downloaded.
"""
import os, sys, shutil, subprocess, json, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
_VENV = os.path.join(ROOT, ".venv", "bin", "kaggle")
KAGGLE = _VENV if os.path.exists(_VENV) else (shutil.which("kaggle") or "")
RAW = os.path.join(ROOT, "replays", "raw")
COMP = "kaggriculture"


def run(*args):
    return subprocess.run([KAGGLE] + list(args), capture_output=True, text=True)


def have_creds():
    return (os.path.exists(os.path.expanduser("~/.kaggle/access_token"))
            or os.environ.get("KAGGLE_API_TOKEN"))


def main():
    if not KAGGLE:
        print("kaggle CLI not on PATH - pip install -r requirements.txt")
        return 1
    if not have_creds():
        print("No Kaggle credentials. Create a token at "
              "https://www.kaggle.com/settings/api and save the token string to "
              "~/.kaggle/access_token (chmod 600).")
        return 1
    os.makedirs(RAW, exist_ok=True)
    ids = sys.argv[1:]
    if not ids:
        subs = run("competitions", "submissions", COMP)
        for line in subs.stdout.splitlines():
            tok = line.split()
            if tok and tok[0].isdigit() and len(tok[0]) >= 8:
                ids.append(tok[0])
    print("submissions:", ids)
    have = {os.path.basename(p).split(".")[0] for p in glob.glob(RAW + "/*.json")}
    fetched = 0
    for sid in ids:
        eps = run("competitions", "episodes", sid)
        for line in eps.stdout.splitlines():
            tok = line.split()
            if tok and tok[0].isdigit() and len(tok[0]) >= 8:
                eid = tok[0]
                if eid in have:
                    continue
                r = run("competitions", "replay", eid, "-p", RAW)
                if r.returncode == 0:
                    fetched += 1
                    print("fetched", eid)
    print(f"downloaded {fetched} new replays into {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
