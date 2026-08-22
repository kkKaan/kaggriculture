# Kaggriculture agent

Agent for the Kaggle [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture)
simulation competition: a two-player, 720-turn farming/market game where the
winner is whoever has the most coins after 30 in-game days.

## Timeline

- 2026-09-23 — entry and team-merger deadline (rules must be accepted by then)
- 2026-09-30 — final submission deadline
- ~2026-10-15 — leaderboard freezes after a Bradley-Terry tournament

5 submissions/day; only the **latest 2** are played and scored, so the last
uploads before the deadline are the ones that count.

## Layout

| Path | Purpose |
|---|---|
| `agent_core.py` | Game constants mirrored from the environment, market price model, yield/watering math |
| `agent_brain.py` | The agent: economic planner + per-turn task assignment |
| `variants.py` | Named parameter variants for benchmarking; loads `champion.json` |
| `champion.json` | Current best parameter vector |
| `build_submission.py` | Bundles everything into a standalone `submission/main.py` and self-tests it |
| `bench/tournament.py` | Head-to-head A vs B over N seeds, both sides |
| `bench/sweep.py` | Many challengers vs the champion in one parallel run |
| `bench/evolve.py` | Hill-climbing search over the parameter vector |
| `bench/diag2.py` | Per-day farm/market trace + action breakdown |
| `bench/revenue.py` | Revenue and spend attribution by product |
| `bench/robust.py` | Multi-opponent robustness + per-turn latency check |

## How the agent works

**Economic layer** — every few turns it re-solves a greedy allocation of the two
scarce resources (tiles and cash) across all crop types and animal types:

- Each option is scored as `revenue / (actions + mu * capital)`, time-discounted
  by `disc ** harvest_day`. `mu` rises as cash per free tile falls, so a broke
  farm plants wheat and a rich one plants strawberries.
- Revenue uses a full replica of the environment's price curve, priced at the
  quantity actually being sold (`avg_sell_price`), at the inventory expected on
  the harvest day.
- That inventory forecast subtracts town demand — including **shops that have
  not unlocked yet** (they unlock every 3 days up to 8 instances, drawn at
  random, so expected demand is computable). Without this the agent thinks
  premium crops will crash and refuses to plant them.
- Supply added by the opponent is read directly off their visible tiles, plus a
  `mirror` term that assumes a rival will match your own production.

**Execution layer** — each turn every unit (farmer + hired hands) is matched to a
task by greedy assignment on `value / (1 + dist_decay * distance)`:

- Watering only fires when a plant would otherwise weed (`consecutive_unwatered
  >= 1`) or when the day falls in its yield-bonus window — roughly halving
  watering actions versus watering daily.
- Animals get FEED / CARE / COLLECT_FERTILIZER / HARVEST tasks whose value scales
  with the current price of what they produce.
- Shed errands (fetch wheat for feeding, fetch a bought animal, fetch fertilizer)
  are first-class tasks, not an idle-unit fallback — otherwise busy units never
  resupply and the animals starve.
- Harvest fires early if selling now beats waiting once the opponent's maturing
  crops are priced in.

## Strategy findings

Measured by head-to-head winrate over 24-64 seeded games, both sides.

**What won:**

1. **Hire hard.** Hand cost is Fibonacci (1, 1, 2, 3, 5, …) and resets daily, so
   a dozen hands costs a few hundred a day against tens of thousands of output.
   Under-hiring was the single largest early loss.
2. **Don't buy all the land.** 50 tiles (NW + NE) beat 75 (84%) and 100 (94%).
   Labour binds, not land, and $2000/$4000 buys far more as animals and seeds.
3. **Forecast shops that have not unlocked yet.** Shops unlock every 3 days up
   to 8 instances; pricing off only the currently-unlocked ones makes premium
   crops look like they will crash, so the agent refuses to plant them.
4. **Assume the opponent mirrors you.** Without a `mirror` supply term both
   players flood melon and crater it — 0% winrate against a version that has it.
5. **Water before harvesting on the final bonus day.** The last watering is what
   lifts yield to maximum; harvesting first silently forfeited one unit per
   wheat/carrot/melon tile.
6. **Shed errands must be real tasks.** As an idle-unit fallback they never fire
   on a busy farm, and every animal starves.
7. **Sell fast, invest long.** Strawberry alone is ~40% of revenue at ~$275/unit.

**What lost, despite looking promising:**

- Pacing sales into town demand instead of selling immediately (8-38%).
- Spending fertiliser on crops rather than selling it, in any configuration.
- Hard spatial zoning of units (25%); a strong distance preference in the
  assignment score does the same job better.
- Compact planting near the shed (6%) — crops belong far from it, animals near.
- Biasing the opening toward fast cash crops (17-29%).

## Measured results

Head-to-head, both sides, vs the tuned champion (`bench/sweep.py`):

| Opponent style | Winrate for champion |
|---|---|
| `flooder` — dumps every product immediately, ignores opponent supply | 100% |
| `premium` — long crops only, no market modelling | 100% |
| `animalrush` — 30 animals, short crops | 97.5% |
| `bigfarm` — all four quadrants, 16 hands | 92.5% |

Against the built-in baselines (`bench/robust.py`), 100% winrate with mean bank
around $125-133k versus ~$3.5k.

## Benchmarking

```bash
python bench/tournament.py champ starter -n 20
```

```bash
python bench/test_model.py
```

```bash
python bench/sweep.py champ variantA variantB -n 14
```

```bash
python bench/robust.py -n 25
```

## Building and submitting

```bash
python build_submission.py
```

This writes `submission/main.py` (single self-contained file) and runs a full
episode against `starter`, failing loudly on any exception or a weak score.

Submitting needs a Kaggle API token — generate one at
https://www.kaggle.com/settings/api, save it to `~/.kaggle/access_token`, accept
the competition rules on the website, then:

```bash
kaggle competitions submit kaggriculture -f submission/main.py -m "v1"
```

## Pre-submission checklist

Run before every upload:

```bash
python build_submission.py && python bench/test_model.py
```

`build_submission.py` bundles and then plays a full episode, failing on any
exception or a weak score. `bench/test_model.py` asserts the yield model still
matches the engine.

Two non-obvious things this bundle already handles:

- **Kaggle's validation episode plays the agent against a copy of itself**, which
  can share module state between both seats. The entry point keeps one planner
  per `obs["player"]`; with a single shared planner the same episode dropped from
  ~$96k to ~$87k.
- **Season length comes from the configuration, not a constant.** With a
  hardcoded 30-day season the agent scored $127 on a 240-step episode because it
  planted 16-day crops that never matured and never reached its endgame dump.

Verified across `boardSize` 8/12, `episodeSteps` 240/480/720, `turnsPerDay`
12/24/48, starting money 500/3000/9000, `shedCapacity` 30, 10x weed rate,
`maxMarketOrdersPerTurn` 3, and 50x hire cost — wins every one.

## Iterating from here

The champion parameter vector lives in `champion.json` and is read by both
`variants.py` and `build_submission.py`, so tuning never requires editing code.

**Hand-testing one idea:** add a named variant in `variants.py`, then

```bash
python bench/sweep.py champ myvariant -n 40
```

40 seeds = 80 games = about 1 sigma of 5.6% on winrate. Anything under 60% at
that sample size is noise; re-run at `-n 80` before believing it.

**Unattended search:** `bench/evolve.py` mutates 1-3 parameters at a time,
screens candidates on one seed set, then re-confirms the leader on a fresh set
before promoting it to `champion.json`. The two-stage design is what keeps it
from chasing noise.

```bash
python bench/evolve.py --rounds 40 --pop 6 --seeds 12 --confirm 32 --workers 4
```

**Do not exceed 4 workers on this machine.** It has 4 performance cores and
little free RAM; each `env` retains 720 deep-copied steps, and over-subscribing
sends the whole run into swap (a 20-game sweep went from 25 s to 1100 s).

**When the engine changes:** re-run `python bench/test_model.py`. It plants one
of every crop, follows the agent's own watering schedule, and asserts the
harvest matches `expected_units`. That test is what caught the agent harvesting
a turn early and silently forfeiting a unit per tile.

**With Kaggle credentials**, the highest-value next step is the competition's
"Daily Top Episodes" dataset — replays of the current leaders. `analyze_replay.py`
parses a downloaded replay into a money curve, action mix, and end-of-game market
state, which is far better signal than self-play alone.
