# How to submit

**Upload one file.** Which one:

| File | Agent | Ladder rating |
|---|---|---|
| `submission/animal/main.py` | animal/fertiliser economy (`AnimalBrain`) | **904** — best measured |
| `submission/main.py` | crop economy (`Brain`) | 799-836 |

Both are fully self-contained — no imports beyond `math`, no data files, no
network. The `agent` function is the last callable in the file, which is what
kaggle-environments looks for. Rebuild either with:

```bash
VARIANT=animal .venv/bin/python build_submission.py   # or omit VARIANT for the crop agent
```

The build runs a full episode against `starter` and fails loudly on any
exception or a weak score, so a file that got written is a file that ran.

## Before the first submission

You must accept the rules once, or the upload is rejected:
open https://www.kaggle.com/competitions/kaggriculture and click
**Join Competition**.

## Option A — web upload (no setup)

1. Go to https://www.kaggle.com/competitions/kaggriculture
2. Click **Submit Agent** (top right)
3. Upload `submission/animal/main.py`
4. Give it a description that names the variant, so `status.py` can attribute
   episodes to it later

If the upload form rejects a bare `.py`, package it:

```bash
tar -czf submission/kaggriculture-agent.tar.gz -C submission/animal main.py
```

## Option B — command line

Generate a token at https://www.kaggle.com/settings/api ("Create New Token"),
save the token string to `~/.kaggle/access_token`, then:

```bash
chmod 600 ~/.kaggle/access_token && VARIANT=animal ./submit.sh "animal v3"
```

## After submitting

A validation episode runs first — the agent plays a copy of itself. If it errors
the submission is marked Error and agent logs can be downloaded. This case is
covered by the build's self-test.

Then it joins the ladder at rating 600 and climbs.

- ~15 games/hour for the first 4-5 hours, then 1-2/hour
- Ratings converge slowly upward: animal v1 read 810 at 33 games and 845 at 41.
  Early readings *understate* a good agent, so a low number at 30 games is not
  yet evidence against it
- Compare submissions by **rating**, not winrate — matchmaking pulls winrate to
  50% by construction
- A strong agent still wins its early games outright: the rank-1 agent went
  21W-1L over its first 22

Check progress with `./results.sh`, or `.venv/bin/python status.py` for a
per-submission record with error bars.

## Submission budget

5 per day, but **only the most recent 2 stay active**, and those same 2 are what
enter the final evaluation. A third upload retires the oldest. Every upload
restarts at 600, so re-submitting an unchanged agent only throws away a
converged rating. Submit real improvements only.
