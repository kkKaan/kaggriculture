# How to submit

**Upload this one file:** `submission/main.py` (50 KB)

It is fully self-contained — no imports beyond `math`, no data files, no
network. The `agent` function is the last callable in the file, which is what
kaggle-environments looks for.

`submission/kaggriculture-agent.tar.gz` is the same file packaged as an archive
with `main.py` at the root. Only use it if the upload form rejects a bare `.py`.

## Before the first submission

You must accept the rules once, or the upload is rejected:
open https://www.kaggle.com/competitions/kaggriculture and click
**Join Competition**.

## Option A — web upload (no setup)

1. Go to https://www.kaggle.com/competitions/kaggriculture
2. Click **Submit Agent** (top right)
3. Upload `submission/main.py`
4. Description: `v1 - task-assignment planner, 75 tiles, 11 animals`

## Option B — command line

Generate a token at https://www.kaggle.com/settings/api ("Create New Token"),
save the token string to `~/.kaggle/access_token`, then:

```bash
chmod 600 ~/.kaggle/access_token && ./submit.sh "v1 - task-assignment planner"
```

## After submitting

A validation episode runs first — the agent plays a copy of itself. If it errors
the submission is marked Error and agent logs can be downloaded. This case is
tested locally and passes.

Then it joins the ladder at rating 600.

- ~15 games/hour for the first 4-5 hours, then 1-2/hour
- **Do not judge it before ~60 games (~5 hours).** At 20-40 games the opponent
  draw alone moves it 100-200 points
- Treat gaps under ~50 points as noise even at 200 games

Check progress with `./results.sh`, or the Submissions tab on the site.

## Submission budget

5 per day, but **only the most recent 2 stay active**, and those same 2 are what
enter the final evaluation. A third upload retires the oldest. Every upload
restarts at 600, so re-submitting an unchanged agent only throws away a
converged rating. Submit real improvements only.
