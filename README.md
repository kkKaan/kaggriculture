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
