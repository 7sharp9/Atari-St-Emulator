# Blog: handoff

Updated 2026-11-18 by the session that ended at commit `26edfaa` (master; the blog repo at `3443c14`).

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is reversed in its
own workstream; this one reads their docs, checks the claims a post would rest on, and feeds corrections back to the
game docs (committed as that game's commit; the game's own handoff is not edited here). Dave's standing direction:
posts explain algorithms the games use and their relevance today, not emulator fixes (2026-11-11); one infographic per
interesting algorithm (2026-11-12); topic docs stay compressed, clarity goes on figures, posts and README openings by
`reversing/WRITING.md` (2026-11-15); an ML / AI-engineering slant, new games and a long pipeline welcome, Archipelagos
not the next post (2026-11-16). The shape that fits the blog: a game's algorithm ported to idiomatic F#, proven against
the game, ending in a visual the game could not make.

**Dave (2026-11-18): build "Virus flown by optimisation"** (he picked it over "The placebo arm" after the spike), and
he wants the next version to be a real learner: one that gets better during a level or between games. He then chose
the between-games learner, pointed out that the pilot reads memory a player cannot see (a player has the 3D view and
the radar), and chose "player-view first" over building the fast simulator. New game lines stay open, racing games
excluded.

## Resume point

- Last commit of this workstream: `26edfaa` (virus: `chain2` gate input declared), after `784a329` (what the 3D view
  shows) and `d967be8` (what the radar shows). Blog repo `3443c14`, unchanged. Master is 3 ahead of origin before this
  file's commit, the blog repo 5; neither pushed.
- Working data: `scratchpad/virus/mpc/` (README there holds every record below: `plan/` the waypoint spike and
  `plan/learn/` the residual learner, `duel/` the pilot, its sweeps, seeded starts, the league `lg1/` and the noise
  probe `sens1/`), `scratchpad/virus/radar/` (radar and view check outputs). Inputs: `scratchpad/virus/demo/S1b.snap`
  and `demo/fl/Q1.snap` (both from `bash reversing/virus/py/demo/capture.sh`; Q1 has no `ANCHORS.md` row),
  `fl/f1.snap`, `cap/flight_bp.txt`.
- Start from: `demo/S1b.snap` (demo flight 1, wave 0), or a seeded start: `duel/starts.py` pokes the RNG at `Q1.snap`
  and runs to the first tick (a new enemy layout, same landscape). Pilot: `scratchpad/virus/mpc/duel/fly.py
  <out.json> [--start <seed>]` with the torch env `uv run --no-project --python 3.12 --with torch==2.2.2 --with
  'numpy<2' --with pillow python`. Earlier pilots are kept as `fly_v4.py` to `fly_v6.py`.
- Gates: none run this session (no model or emulator change). Virus dry run: 0 MISSING, 1/6 gates declare no inputs
  (`models`; was 2/6).
- Uncommitted work left behind: none. The pilot, league and learner scripts are scratchpad-only on purpose.

## Proven so far

- Virus ship tick, shot, wave-0 actors, ship box: gates `mpc_flight` and `mpc_shot` (`reversing/virus/README.md`
  "Off the capture", `behaviours.md` "The player's shot, the targets and the ship box").
- The radar: one pixel per hatched enemy at its x and z, `$400` units a pixel, kind as colour, no height, velocity or
  unhatched records; dot list == pool + ship on 1,100/1,100 frames (`behaviours.md` "What the radar shows";
  `py/scan/radar_check.py`).
- The 3D view: an enemy is drawn only within `$680` of the ship in x and `$600` in z; the window test predicts the
  draw on 2,346/2,346 arrivals and the queued set on 1,100/1,100 frames; a pixel is 8 to 20 units (inferred)
  (`behaviours.md` "What the 3D view shows"; `py/scan/view_check.py`).
- Records, not gates (`scratchpad/virus/mpc/README.md`):
  - Wave-end pilot on S1b: wave 0 ended before the autopilot's tick 1189 in 5 of 9 settings (best 778), 0/9 crashes.
  - Eight seeded starts, default pilot: first in 4 of 8; 31 shots, 31 kills, no deaths.
  - During-a-level learner (recursive least squares on the tick's residual): miss at tick 300, naive / known / learned,
    619/241/123, 1403/430/228, 478/186/51, 662/65/505; learned in about 40 ticks. A small panel, not a curve.
  - Between-games learner (cross-entropy search over 8 cost weights, `league.py lg1`): no learning; held-out mean ratio
    0.784 before, 0.919 after; generation means 0.900, 0.980, 0.829, 1.076, 1.085, 1.059.
  - Noise floor (`sens.py sens1`): a 2% weight change moves one game's ratio with sd 0.31 (seed 101) and 0.47 (seed
    106); on seed 106 three of eight weight sets end the wave at ticks 278 to 292 against the autopilot's 1164.
  - The pilot fired 52 of 63 shots (16 default games) at enemies outside the 3D view's window.
- Lander (Archimedes, Mark Moxon's source): no demo or autopilot and no enemies; the same tick shape. The ST
  autopilot was added for the full game.
- Carried, unchanged: Archipelagos generator, Captive keys, Midwinter roughness and port 70000/70000, PowerMonger
  commander, Populous swamp edge.

## Running

Nothing from this session. An `stserver.dll` started 13:31 (pid 34215) belongs to another Claude process.

## Open, in priority order

1. **Player-view pilot (Dave's choice).** Restrict what the pilot reads to what a player has: per frame the radar's
   dot list (kind, x and z to `$400`) and, for records inside the view window, position to screen precision; no
   velocity, no state, no unhatched records. First design step: an observation function over `read_world` in `fly.py`
   that masks the pool this way, a tracker that estimates velocity from successive observations, and a two-phase
   pilot (fly to the dot, aim inside the window). Settle by the three-tier table on seeded starts: autopilot,
   full-memory planner, player-view pilot, wave-end tick each. Open sub-question: does the autopilot itself read
   beyond the window (`demo.md` "The pilot": its scan and the `D4 < $900` fire test)?
2. **What to learn.** Weight search is ruled out by the noise floor. The reading to test: the outcome turns on a few
   discrete decisions (which enemy next, whether an approach is abandoned). Test it by forcing the target order on
   seed 106 (all 6 orders of the 3 seeders, patrol last) and seeing whether order alone explains 280 against 1146.
   If so, learn a value for "target X from this state" from many games.
3. **Fast simulator.** Needed for item 2's data: the emulator gives about 150 ticks/s, 11 minutes a game. Tick, shot
   and seeder are exact Python functions in `py/mpc/`; the patrol given the ship's path is in `shot.predict`; the
   wave-end rule is `behaviours.md` "When a wave ends". Port to F# (the post's code) and gate against a recorded game.
4. **F# port and TorchSharp**: check TorchSharp's macOS x64 support first (torch stops at 2.2.2 on this Intel Mac;
   gpubox is the fallback).
5. Pilot loose ends: the one miss (`duel/s4_K6.json`); seed 7 and seed 103 never end the wave; a held-out game with
   the league's weights fired no shot in 2,000 ticks (seed 105).
6. **Finish Paint It Black** (two TODOs are Dave's), then Mountains of the Moon line 50.
7. **"The placebo arm"**, **"How the agent was kept honest"**, **"Graded by the authors"**, **Cadaver's language**,
   **the planner**; new games (Laser Squad, a chess engine, Kick Off 2; no racing); carried items as in IDEAS.md.

## Known traps

- One game cannot rank two weight sets: measure the noise floor (`sens.py`) before any outcome-ranked search.
- Poking the RNG at `S1b.snap` changes only later draws; a new layout needs the poke before the scatter (`Q1.snap`).
- The league's score caps at 2000 ticks for a wave not ended and adds 300 for a death; `auto` in its JSON can exceed
  2000 because `baseline2.py` runs the autopilot to 3000.
- `fly.py` is deterministic (the default weights reproduced two games tick for tick): variation is settings or start.
- "Cleared" in older records means the three seeders only; newer records use the game's wave end.
- The fire rule fires only on a hit certain under jitter; the exact pull-up check (`safe`) is what stops crashes.
- `view_check.py` labels an arrival with the record's behaviour after the tick ran, so a home tick that hands over to
  cruise is counted under `$21c64`.
- `scratchpad/virus/mpc/replay/` and `shot/` are pre-promotion copies; use `reversing/virus/py/mpc/`.
- zsh reads `${F}:textfile` wrongly without the braces; MobyGames 403; local Hugo too old; IDEAS.md entries are cited
  by number, leave gaps.

## Waiting on Dave

- `sessions/virus.md` is stale: it does not know `py/mpc/`, the radar and 3D-view sections or `py/scan/radar_check.py`
  and `view_check.py` (this session may not edit it). A `/resume virus` should read `git log -- reversing/virus` first.
- Is stserver stopping twice at a breakpoint after an interrupt a bug to fix in `server/Server.fs`, or the documented
  behaviour?
- Whether the Virus post is one post (planning, with the player-view tier) and a learning sequel, or waits.
- Carried: rewrite IDEAS.md around the ML ranking; Captain Blood prior art; Midwinter line 50; Captive keys figure;
  Carrier Command series; "proven" vs "observed" in Crude Buster and Final Fight; Lemmings artifact republish; Hugo
  upgrade; pushing master and the blog repo.

## Next session

`/resume blog`. Read `scratchpad/virus/mpc/README.md` and `behaviours.md` "What the radar shows" and "What the 3D view
shows". First step: Open 1, the observation mask over `read_world` (copy `fly.py` to `fly_v7.py` first), and check
what the autopilot reads (`demo.md` "The pilot"). The forced-order test of Open 2 is six games on seed 106, about 15
minutes in parallel, and can run beside it.
