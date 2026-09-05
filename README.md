# Kaggriculture agent

Agent for the Kaggle [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture)
simulation competition: a two-player, 720-turn farming/market game where the
winner is whoever has the most coins after 30 in-game days.

## Where this actually stands

The animal-centric allocator (`agent_animal.py`) is the first change that moved
the ladder rating. Ratings: **animal v2 898.1**, animal v1 844.6, then the whole
crop-economy fleet at 799-836. Note ratings converge slowly - animal v1 read
810 at 33 games and 845 at 41, so early readings understate.

Compare submissions by **rating**, not winrate: Elo raises you until you are even
with your opponents, so winrate tends to 50% by construction.

Margin analysis over 209 of our games against 29 of rank 1's and 51 of Crop
Dusta's:

| agent | win% | median margin | sd | p10 |
|---|---|---|---|---|
| us | 56.0% | +$3,979 | 26,760 | -$24,176 |
| Crop Dusta | 80.4% | +$9,198 | 23,006 | -$4,837 |
| Ryo (rank 1) | 93.1% | +$11,437 | 24,833 | +$548 |

Variance is the same for everyone. The gap is purely mean margin, and rank 1's
own score ($104k) is only ~9% above ours ($95k). The target is about **$9-10k
more output per game**, not a different game.

Note winrate converges to 50% by construction as Elo raises you to your level -
compare submissions by *rating*, or by winrate over the same early game count.

## Timeline

- 2026-09-23 — entry and team-merger deadline (rules must be accepted by then)
- 2026-09-30 — final submission deadline
- ~2026-10-15 — leaderboard freezes after a Bradley-Terry tournament

5 submissions/day; only the **latest 2** are played and scored, so the last
uploads before the deadline are the ones that count.

## Setup

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Everything below assumes `.venv/bin/python`. The agent that gets submitted is a
single stdlib-only file - `kaggle-environments` is only needed to run episodes
offline, and `kaggle` only to talk to the API.

## Layout

| Path | Purpose |
|---|---|
| `agent_core.py` | Game constants mirrored from the environment, market price model, yield/watering math |
| `agent_brain.py` | The crop agent: economic planner + per-turn task assignment |
| `agent_animal.py` | `AnimalBrain(Brain)` - replaces only the economic layer with the animal/fertiliser opening. Best rated agent |
| `variants.py` | Named parameter variants for benchmarking; loads `champion.json` |
| `champion.json` / `champion_animal.json` | Current best parameter vector per brain |
| `build_submission.py` | Bundles everything into a standalone `submission/main.py` and self-tests it |
| `bench/tournament.py` | Head-to-head A vs B over N seeds, both sides |
| `bench/sweep.py` | Many challengers vs the champion in one parallel run |
| `bench/evolve.py` | Hill-climbing search over the parameter vector |
| `bench/diag2.py` | Per-day farm/market trace + action breakdown |
| `bench/revenue.py` | Revenue and spend attribution by product |
| `bench/robust.py` | Multi-opponent robustness + per-turn latency check |
| `fetch_replays.py` / `status.py` | Pull every ladder episode via the Kaggle API and report each submission's real record |
| `bench/corpus.py` | Rebuild `data/corpus.json` from downloaded replays |
| `analyze_replay.py` | Day-by-day trace of a single downloaded episode |
| `data/top_agent_summaries.json` | Curated summaries of 16 top-agent games. Kept in git because rebuilding it means re-downloading ~11 GB of replays |

Not in git, all regenerable: `.venv/`, `replays/` (downloaded episodes, ~11 GB),
`data/corpus.json` and `data/episode_submission.json` (rebuilt by `bench/corpus.py`
and `status.py`), and the `*.tar.gz` submission archives.

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
.venv/bin/python bench/tournament.py champ starter -n 20
```

```bash
.venv/bin/python bench/test_model.py
```

```bash
.venv/bin/python bench/sweep.py champ variantA variantB -n 14
```

```bash
.venv/bin/python bench/robust.py -n 25
```

## Building and submitting

```bash
.venv/bin/python build_submission.py            # crop agent  -> submission/main.py
VARIANT=animal .venv/bin/python build_submission.py   # animal agent -> submission/animal/main.py
```

Each writes one self-contained file and runs a full episode against `starter`,
failing loudly on any exception or a weak score. The bundles are committed, so
a fresh clone plus a rebuild produces no diff — that is the reproducibility
check.

Submitting needs a Kaggle API token — generate one at
https://www.kaggle.com/settings/api, save it to `~/.kaggle/access_token`, accept
the competition rules on the website, then:

```bash
VARIANT=animal ./submit.sh "animal v3"
```

See [SUBMIT.md](SUBMIT.md) for which file to upload and how ratings behave
afterwards.

## Learned from a top-agent replay

Episode 96870933, Ryo Hasegawa (rank 1) vs Subramanya N (rank 3), $99,534 vs
$100,127. Our agent scores ~$95k in self-play on the same seed, so the same
league — though not directly comparable, since the opponent and the random shop
draw both differ.

**Independently converged on the same answers.** Both leaders run exactly three
quadrants, cap at exactly twelve hands, build on strawberry + wheat + cows and
sheep, and neither uses geese at all. The land and hiring tuning here reached
those numbers from measurement alone.

**Three visible differences, all three tested, all three rejected:**

| Their behaviour | Hypothesis | Result |
|---|---|---|
| WATER 16-17% vs our 13% | daily watering is safer than alternate-day | rejected before coding — neglect deaths are 3 for us, 0 and 6 for them |
| 15-41 plants left to rot vs our 57 | clearing spent crops frees tiles | implemented; rot 56 -> 36/game, score *down* $89.8k -> $88.6k |
| 4 animals on day 0 vs our 1 | animals should start compounding sooner | 18.8% (4 animals) and 31.2% (2 animals) winrate |

Both features are kept in the code behind `dig_spent` and `early_animals`,
defaulted off, so the measurement isn't repeated. The lesson: surface behaviour
of a strong agent is not transferable — those choices work inside their strategy,
and our capital allocator has good reasons to buy animals later.

The one gap still unexplained is idle time: they PASS 5-7% of turns, we PASS 15%.

## The real finding: mirror self-play mis-tunes capital

Three lost ladder games (episodes 96907293, 96911898, 96918784) showed our agent
producing 2-7x more **wheat** than the winners while producing far less wool,
milk and egg:

| product | bsenst | us | Dread | us | Bushel | us |
|---|---|---|---|---|---|---|
| WHEAT | 121 | **223** | 186 | **300** | 38 | **275** |
| MILK | 230 | 206 | 216 | **111** | 252 | 205 |
| WOOL | 168 | **33** | 48 | 60 | 71 | **30** |
| EGG | 0 | 42 | 171 | **0** | 0 | 39 |

Wheat is the cheapest product in the game. The cause was `cap_mu`, the capital
penalty that biases the allocator toward cheap seeds when cash is short — it had
been tuned to 2.16 **in mirror self-play**, which is a biased instrument: when
both sides build cows, milk crashes, so the mirror concludes cows are bad and
wheat is safe. A real ladder is diverse and never floods uniformly.

Re-tuned against a pool of dissimilar opponents (`bench/pool.py`), `cap_mu` 1.4
beats 2.16 by a wide margin:

| | pool base 8400 | pool base 9000 |
|---|---|---|
| cap_mu 2.16 (old) | 78.6% | 90.0% |
| cap_mu 1.0 | 96.4% | 92.5% |
| **cap_mu 1.4** | **97.5%** | **100.0%** |

Animal tile-days rose 526 -> 640 and geese dropped to zero in favour of sheep and
cows — the composition every strong opponent runs.

### Land timing does not transfer

High-Elo agents demonstrably stay on **one quadrant until day 10** with ~19 crop
tiles and 11+ animals, then buy both remaining quadrants at once. Ours buys land
on day 0 and runs ~65 crop tiles with ~9 animals.

Tested as `land_min_day` at days 5, 8 and 10, alone and combined with forced
early animals and a raised animal target. Every variant loses badly:

| variant | winrate vs champion |
|---|---|
| land_min_day 5 | 72.5% (pool) |
| land_min_day 5 + 4 early animals | 35.0% (pool) |
| land_min_day 8 | 20.0% |
| land_min_day 10 | 10.0% |
| land_min_day 10 + animal_target 16 | 10.0% |

These are two coherent economies: ours extracts value from crop tiles, theirs
from animal density. Grafting one piece of theirs onto ours breaks the coherence.
Adopting it properly would mean rebuilding the allocator around animal density,
not changing a parameter.

### Stranded animals: a real inefficiency whose fix costs more

The agent leaves bought animals sitting in the shed on 12-22 of 30 days (up to 3
at once, $400-500 each of dead capital). Cause: `room` subtracts shed animals
from `animal_target`, so once at target the allocator cannot select them and no
housing is ever built.

Two fixes implemented and measured against the unmodified agent:

| change | winrate |
|---|---|
| house stranded animals regardless of target (`house_stranded`) | 29.2% |
| raise build priority while animals wait (`build_urgent` 320) | 20.8% |
| both | 37.5% |

All lose. Housing a surplus animal costs an action and a tile that would
otherwise grow strawberries, and pushes past the tuned `animal_target`. Both are
kept as parameters, defaulted off, with the measurement in the code comment.

Enabling them also allowed the first *valid* test of the top-agent opening (my
earlier `early_animals` test was invalid — it never actually placed animals on
day 0). Even with housing forced on, the agent places 0 animals on day 0 against
their 4, and the variant still loses at 15%.

### The field's opening needs a redesign, not parameters

A corpus of 16 top-agent games (`data/top_agent_summaries.json`) shows a
remarkably uniform meta:

| | field (16/16 games) | ours |
|---|---|---|
| animals placed on day 0 | **exactly 4, every game** | 1 |
| 2nd quadrant | day 5-6 | day 0 |
| 3rd quadrant | day 9-11 | day 11-15 |
| peak animals | 14-23 | 10-11 |
| idle turns | 3-11% | 15% |

Five of those opponents share byte-identical statistics (6914 actions, land on
[6,11]) — a widely-copied public baseline. The rank-1 agent runs the same
template with better execution (land [5,10], ~7280 actions, 3-5% idle).

Replicating it failed three times, each for a different concrete reason:

1. Animals bought but never placed — `room` subtracts shed animals from
   `animal_target`, so housing never gets built.
2. Fixed that; still 2 animals by day 5 — `BUY_SEED` is emitted before
   `BUY_ANIMAL`, so seeds consume the day-0 cash (`animals_first` param added).
3. Fixed that; 3 animals placed by day 1, **down to 1 by day 3** — they starve.
   Spending the full $3000 on animals and seeds leaves nothing for feed wheat,
   and an animal escapes after two unfed days.

Their opening budgets purchases, feed supply and placement speed *together*;
our allocator optimises each independently. That is an allocator redesign.
The best replica scores $77-87k against the champion's $100-117k.

Raising `animal_target` 11 -> 14 is exactly 50.0% over 60 mirror games, and
measurement shows why: peak animals barely move (11->12, 13->15, 8->8, 8->7)
because the cap was never binding — cash and tiles are. Wool even drops 65 -> 58.

### Ground truth from 145 real ladder games

`fetch_replays.py` pulls every episode for every submission; `bench/corpus.py`
reduces them to `data/corpus.json`. As of 2026-08-23:

**Record: 81W 64L = 55.9%**, mean $94,773 against $88,233. Rank 2795 / 5959.

All four submissions score within noise of each other (836.5, 822.8, 821.8,
799.2) despite v2 measuring **+79%** over v1 locally. Local winrate has not
predicted ladder rating even once.

Our behaviour is **identical in wins and losses** — peak animals 9.5 vs 9.4,
peak plants 65.5 vs 65.5, actions 6999 vs 6982, same land days, same crop mix.
We play one game and win when the opponent is weak:

| | opponents we beat | opponents who beat us | us |
|---|---|---|---|
| peak animals | 12.8 | 13.8 | **9.4** |
| peak plants | 49.0 | 56.0 | **65.5** |
| animal tile-days | 286 | 318 | **224** |
| geese share | 3% | 3% | **13%** |

Animal markets are **not** saturated in real games (median end price: milk $172,
wool $199; floored in only 16% and 33% of games), so the extra animals the field
runs are genuinely profitable. Yet every configuration that reproduces the field
profile loses locally:

| variant | local mirror | animals produced |
|---|---|---|
| champion | — | 9.2 |
| cap_mu 1.4 + target 16 | 40.0% (40 games) | 14.2 |
| no geese + target 16 | 37.5% (40 games) | 14.2 |

### The benchmark cannot discriminate — this is the real blocker

Seven v2 ladder losses against opponents at our own rating (~830 Elo):

| | opponents (7) | us (v2) |
|---|---|---|
| animals on day 0 | 3-6 | **1** |
| peak animals | 9-18 (median 14) | 9-12 (median 10) |
| land bought | day 6-11 | **day 0** |
| geese | **none, all seven** | 24-50 tile-days |

Every one of those field-consensus behaviours measures neutral or negative here:

| change | local measurement |
|---|---|
| exclude geese (`no_animal`) | 47.5% over 40 games |
| animal_target 11 -> 14 | 50.0% over 60 games |
| delay land to day 5 / 8 / 10 | 72.5% / 20.0% / 10.0% |
| 4 animals on day 0 | 15-35% |
| reserve feed cash (`feed_days`) | loses, fewer animals |

v2 measured **+79%** over v1 head-to-head and +19 points on the pool, yet the
ladder shows it still losing to ~830-rated opponents. The local environment
(mirror + synthetic archetypes) reaches a different market equilibrium from the
real ladder, so local winrate is not predicting ladder winrate.

Further parameter tuning against this benchmark is not expected to help. The
prerequisite is an opponent model calibrated to real replays.

**Always validate against `bench/pool.py`, not just the mirror.** Note that
`nowheat` (never planting wheat, buying all feed) scores 27.5% — growing your own
feed is still necessary; the error was the *degree*.

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
.venv/bin/python bench/sweep.py champ myvariant -n 40
```

40 seeds = 80 games = about 1 sigma of 5.6% on winrate. Anything under 60% at
that sample size is noise; re-run at `-n 80` before believing it.

**Unattended search:** `bench/evolve.py` mutates 1-3 parameters at a time,
screens candidates on one seed set, then re-confirms the leader on a fresh set
before promoting it to `champion.json`. The two-stage design is what keeps it
from chasing noise.

```bash
.venv/bin/python bench/evolve.py --rounds 40 --pop 6 --seeds 12 --confirm 32 --workers 4
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
