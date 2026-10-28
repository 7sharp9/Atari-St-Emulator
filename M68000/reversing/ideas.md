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
  AI stops issuing orders that can only end at a shore.
- **Wall following (Bug2).** On hitting water, follow the coast until the straight line to the target
  clears. One or two bytes of state per man, no search. Inferred to resolve most of the 2417; the
  first experiment is a Python model of the mode `$10`/`$48` probe plus a Bug2 follower, scored on
  the `classify_stuck.py` pairs against A*'s 2417.
- **Flow fields.** One field per destination, every unit descends it. Suits a whole army sent to one
  place, and Populous's walkers converging on the papal magnet.
- **Jump-point A*, cached per order target**, only if coastlines that defeat wall following prove
  common.

**Populous: the cheapest bridge in mana.** Walkers head for the magnet and drown in water; raising
land costs mana and spreads to the neighbours. Getting people somewhere is then a shortest path
where a cell's cost is the earth needed to make it walkable: A* with distance times the cheapest
raise as an admissible heuristic. Uses: a player aid that shows the cheapest causeway, and a
stronger computer god, since `ai_think $13eda` (`populous/ai.md` 3.1, 4800/4800 callcap matches)
only moves the magnet and the levellers `$135fc`/`$13816` work at the walkers' own cells; nothing
plans land to raise. The same framing gives fewest-clicks flattening of an NxN site, with total
height difference over the most one click changes as the lower bound. The rules it needs are
proven in `populous/terrain.md`: the neighbour-difference recursion of raise/lower and its cost,
`4 * corners changed + 10` mana (`$37f8a`), which makes a cell's crossing cost exact rather than
estimated. The gate is to drive the planner's clicks in the emulator and compare the mana spent.

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
- **Tree search over a learned model.** Exact rollouts cost about 84 s per 1000-tick candidate
  (`commander/README.md`, "Forecaster"), too slow for search. If the state-space model forecasts
  the rollouts well enough, MCTS or beam search over orders becomes affordable. The model's error
  against the rollouts decides it, not the search algorithm.
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
