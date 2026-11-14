# Modern techniques applied to the reversed games

Ideas for what present-day algorithms could change or add in the games reversed here, mainly
Populous and PowerMonger. Nothing in this file is built or measured unless it says so: each idea
names the facts it rests on (with the doc that proves them) and what a first experiment would be.
Game-specific work that starts from one of these moves into that game's directory and workstream.

## Two routes

- **Inside the game**: a 68000 patch that has to fit an 8 MHz budget and the game's fixed tables
  (511 objects in PowerMonger). Limits the choice to techniques from about 1990 to 2005.
- **Outside the game**: a modern program that reads RAM and writes the game's own inputs. The
  emulator is deterministic and snapshots are exact, and PowerMonger already has the interface: the
  command buffer `$58016` takes orders from a harness once a side's slot is held at state 2
  (`powermonger/commander/README.md`, `gate_inject.sh` 7/7). This route tests an idea against the
  unchanged game before anyone decides a 68000 version is worth writing.

## Rendering: no search problem

A* and its relatives do not apply to either renderer: both draw every cell in a fixed far-to-near
order, with no choice to search over.

- Populous draws an 8x8 window of pre-drawn 32x24 blocks at shift-and-add positions; it is already
  cheap (`populous/graphics.md`, "The terrain renderer").
- PowerMonger is fill-rate bound: the span filler `$e4de` is about 40% of executed instructions
  even in the settled view, because `$f898` refills the island every tick; zoomed out, the cost is
  the `$f000` slope divides for many small triangles (`powermonger/graphics.md`, "Isometric
  renderer, measured").

The gains there are visibility and reuse: a front-to-back span buffer, redrawing only changed cells,
and at far zoom merging adjacent flat, same-colour cells into larger polygons (a quadtree
simplification) to cut the edge divides. The first two are in `powermonger/graphics.md`, "What a
modern port would do differently".

## Movement and pathfinding

**PowerMonger has no pathfinding.** A lead steps straight at its target, tries a fixed fan of
headings when blocked, and stays at the shore (`powermonger/README.md`, "No pathfinding"; `ai.md`
mode `$48`). In six long runs 2417 of 4230 stuck pairs had a land path whose straight line crosses
water, and `commander/astar.py` finds a waypoint path for each (`commander/classify_stuck.py`).
Cheaper relatives that would fit inside the game:

- **Land component labels.** One flood fill at world build makes "reachable on foot" a lookup, so the
  AI stops issuing orders that can only end at a shore. On the six census maps, 4-connected cell labels
  (about 8 KB at a byte per cell) agree with the A* triangle graph on 4196/4196 pairs, and a coarser
  lattice or 8-connected fill does not (4107 and 4169); exact on those maps, not shown for others
  (`powermonger/commander/README.md`, "Wall following against A*").
- **Wall following (Bug2).** On hitting water, follow the coast until the straight line to the target
  clears. A Python model of the mode `$10`/`$48` probe plus a follower, scored on the 2417 reachable
  pairs whose line crosses water (2202 distinct pairs, 133 men, six maps): one hand arrives for 2416
  (left) or 2355 (right), either hand for 2417, with 3 to 7 bytes of extra state per man. The path is the
  weak point: one hand gives a median 3.8x (left) or 1.24x (right) A*'s length and a worst 335x to 613x
  (150 units across a sliver, 135,215 walked), and the 1.17x of the both-hands run is an oracle a unit
  cannot run. It also loops forever on unreachable targets, so it needs the labels. Untested: a cheap hand
  selector (a short look-ahead of both coasts), other maps, moving targets, followers. One pair was walked
  live by poked waypoints (the unpoked control stays at the shore).
- **Flow fields.** One field per destination, every unit descends it. Suits a whole army sent to one
  place, and Populous's walkers converging on the papal magnet.
- **Jump-point A*, cached per order target**, only if coastlines that defeat wall following prove
  common.

**Populous: the cheapest bridge in mana.** Walkers head for the magnet and drown in water; raising
land costs mana and spreads to the neighbours. Getting people somewhere is then a shortest path
where a cell's cost is the earth needed to make it walkable: A* over (cell, raised corners nearby) with
water cells on the path over two times the 14 mana of a sea-corner raise as the admissible heuristic (distance
times the cheapest raise is not admissible: land is free and one raised corner serves two path cells). Uses: a player aid that shows the cheapest causeway, and a
stronger computer god, since `ai_think $13eda` (`populous/ai.md` 3.1, 4800/4800 callcap matches)
only moves the magnet and the levellers `$135fc`/`$13816` work at the walkers' own cells; nothing
plans land to raise. The rules it needs are proven in `populous/terrain.md`: the neighbour-difference
recursion of raise/lower and its cost, `4 * corners changed + 10` mana (`$37f8a`). Across water that cost is a flat
14 per corner, so the problem is geometry: one raised corner makes a 2x2 block walkable, and the cheapest causeway
hops two cells per click. Built (`populous/py/causeway/`): the planner is optimal for sea-corner raises (6/6 gaps
against exhaustive search). Over 31 gaps on three snapshots a straight line costs 1.67 to 5.60 times the planner's mana
(27 lines; the other 4 are blocked by rock), greedy nearest-cell 1.33 to 5.00 times, and the straight line with its
corners chosen best 1.00 to 5.00 times (4 ties); the planner is never the dearer (`py/causeway/table.py`). Four gaps were driven through the game's mouse UI: the
mana charged and the whole height map matched the model (4225/4225 corners against the model on the control run,
mana -42, -28, -28, -70 as predicted). Caveats: the gates poke an own walker into view so the land click acts, no
walker was walked across, and land-corner raises and lowering are not planned. Fewest-clicks flattening of an NxN
site stays an idea: a model-only beam search flattened three sites in 3, 4 and 8 clicks, but the lower bound (total
height difference over the most one click changes) came out 1, 1 and 2, too weak to say how far from optimal.

Populous walker roaming is not a candidate: walkers settle on flat land and gather at the magnet by
design, and pathfinding would change the game rather than improve it.

## AI and decision making

Inside the game:

- **Influence maps.** A coarse grid of each side's strength, spread and decayed each tick. Gives
  PowerMonger's AI a frontline, weak towns and safe supply routes, and lets Populous's computer god
  aim the magnet and earthquakes at the enemy's growing edge instead of its oldest settlement
  (`populous/ai.md`, side record `+38`). One small blur pass per tick.
- **Utility scoring of orders.** Score each candidate order (food `$06`, men `$08`, attack `$0c`,
  invent `$0e`, ...) against current need instead of a fixed priority, so the AI adapts to the state.
- **Adaptive difficulty.** Populous already exposes the dials: AGGRESSION and RATE in "OPTIONS FOR
  EVIL" (`populous/ai.md`, custom game). Steering them from the player's performance is wiring,
  not new AI.

Outside the game:

- **An AI that knows only what its spies report.** PowerMonger has spies and pigeons, but its AI
  reads every side's state. A belief state over enemy positions (a particle filter updated from spy
  reports) makes a commander that can be surprised and bluffed. Reuses the commander harness; the
  strongest candidate here for changing how the game plays.
- **Tree search over exact rollouts, or over a learned model.** An exact rollout costs about 40 s per
  1000 ticks on an idle machine (84 s on a loaded one, `commander/README.md`, "Forecaster"), too slow
  for search. With the renderer stubbed the simulation state is byte-identical and the same 1000
  ticks take about 9 s (`$f898` alone) or 6 s (all draw and frame-sync calls) on land 2
  (`powermonger/commander/renderskip/README.md`; `rollout.py --ticks` is that mode, `gate_ticks.py`
  20/20). That makes a shallow beam search over orders affordable on exact
  rollouts. A learned state-space model is still the route to deep search; its error against the
  rollouts decides it, not the search algorithm.
- **Negotiated alliances.** PowerMonger's alliance `$1e` and spy `$20` orders are fixed actions; an
  LLM commander can bargain terms (food for non-aggression) around them without changing the rules.
- **Orders in plain language.** "Hold the bridge until winter, then take the northern towns",
  compiled into a sequence of command-buffer writes: the commander turned into a player interface.

## World and simulation

- **Ecology.** PowerMonger's weather is one seasonal roll that reads nothing on the land; felling or
  emptying the forest leaves every spell unchanged (`powermonger/README.md`; `py/season/tree_weather.py`,
  3 arms, 125M steps). A small cellular automaton (forest spread, overgrazing, floods along the
  terrain) would give clearing land consequences.
- **World generation.** Populous builds each world from a seed (`populous/README.md`). Noise plus an
  erosion pass would give drainage-shaped coasts and valleys, making land shaping a geography puzzle.
