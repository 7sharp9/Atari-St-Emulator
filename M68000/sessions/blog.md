# Blog: handoff

Updated 2026-11-18 by the session that ended at commit `f5bfca0` (master; the blog repo at `3443c14`).

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is reversed in its
own workstream; this one reads their docs, checks the claims a post would rest on, and feeds corrections back to the
game docs (committed as that game's commit; the game's own handoff is not edited here). Dave's standing direction:
posts explain algorithms the games use and their relevance today, not emulator fixes (2026-11-11); one infographic per
interesting algorithm (2026-11-12); topic docs stay compressed, clarity goes on figures, posts and README openings by
`reversing/WRITING.md` (2026-11-15); an ML / AI-engineering slant, new games and a long pipeline welcome, Archipelagos
not the next post (2026-11-16). The shape that fits the blog: a game's algorithm ported to idiomatic F#, proven against
the game, ending in a visual the game could not make.

**Dave (2026-11-18): build "Virus flown by optimisation"**, as a real learner (better during a level or between
games), and "player-view first": the pilot may read only what a player has, the 3D view and the radar. He asked for a
video comparison of the most promising runs (made, below). New game lines stay open, racing games excluded.

## Resume point

- Last commit of this workstream: `f5bfca0` (virus: `models` gate inputs declared). Blog repo `3443c14`, unchanged.
  Master is 1 ahead of origin before this file's commit (the earlier commits were pushed); the blog repo is 5 ahead.
- Working data: `scratchpad/virus/mpc/` (its README holds every record below). The player-view work is
  `duel/fly_v7.py` (the working pilot, equal to the second version) and `duel/pv/`: frozen pilots `fly_d1.py` to
  `fly_d3.py`, games `<tag>_s<seed>.json`, `run_seeds.sh`, `tier.py`, `diag.py`, `look.py`, `auto_view.py`,
  `video.py`, and `vid/` (frames, `stitch.sh`, `virus_tiers_s2.mp4`, `virus_tiers_s105.mp4`). Inputs:
  `scratchpad/virus/demo/S1b.snap` and `demo/fl/Q1.snap` (both from `bash reversing/virus/py/demo/capture.sh`; Q1 has
  no `ANCHORS.md` row).
- Start from: a seeded start (`duel/starts.py` pokes the RNG at `Q1.snap`). One game:
  `uv run --no-project --python 3.12 --with torch==2.2.2 --with 'numpy<2' --with pillow python fly_v7.py <out.json>
  --start <seed> --ticks 2000` from `duel/`; eight in parallel: `bash pv/run_seeds.sh <tag> "<seeds>"` (it runs
  `pv/fly_<tag>.py`, a frozen copy with `here` pointed one directory up), about 13 minutes.
- Gates: none run (no model or emulator change). Virus dry run: 0 MISSING, 0/6 gates declare no inputs (was 1/6).
- Uncommitted work left behind: none. The pilots, records and videos are scratchpad-only on purpose.

## Proven so far

- Virus ship tick, shot, wave-0 actors, ship box: gates `mpc_flight` and `mpc_shot` (`reversing/virus/README.md`
  "Off the capture", `behaviours.md` "The player's shot, the targets and the ship box").
- The radar and the 3D view window: `behaviours.md` "What the radar shows" (1,100/1,100 frames,
  `py/scan/radar_check.py`) and "What the 3D view shows" (2,346/2,346 arrivals, `py/scan/view_check.py`).
- Records, not gates (`scratchpad/virus/mpc/README.md`, "duel/pv/" for the first four):
  - Player-view pilot, wave ended / deaths / shots / kills: first version 0 of 8, 0, 4, 4 (seeds 1 to 8); second 3 of
    8, 2, 29, 27 (seeds 1 to 8; ticks 1333, 1301, 1623 against the autopilot's 1253, 1320, 1843); third 1 of 8, 4, 30,
    24; second version held out on seeds 101 to 108, no setting changed: **0 of 8**, 2, 23, 20. The autopilot and the
    full-memory planner each end 7 of 8 on those seeds. `pv/tier.py`.
  - The failures looked at (seeds 3, 5, 8, second version) are the patrol in its attack state or the pursuer
    (`pv/look.py`); the held-out failures were not looked at.
  - The autopilot fires with a hatched enemy inside the view window on 1,535 of 1,609 fire ticks over 16 games, and an
    enemy is in the window on 6,044 of 24,501 ticks (`pv/auto_view.py`; any enemy, not its chosen target). It picks
    and steers at the nearest pool record at any range (`demo.md` "The pilot", read).
  - Seed 106, the eight noise-probe games: the same target order in all eight, wave end 278 to 1968; the second seeder
    dies at ticks 136 to 167 in the three fast games and 508 to 1181 in the others (`duel/order_of.py`; labels by
    position, not checked against a raw pool dump). Target order does not explain the spread on this seed.
  - Earlier: full-memory wave-end pilot (5 of 9 before the autopilot on S1b; first in 4 of 8 seeded starts), the
    during-a-level residual learner, the between-games weight search (no learning) and its noise floor (a 2% weight
    change moves one game with sd 0.31 and 0.47).
- Videos: each of the five ended replays stopped on its record's tick (1320, 1210, 1301; 1735, 961); one frame of the
  seed 2 video was looked at.
- Carried, unchanged: Lander has no autopilot; Archipelagos generator, Captive keys, Midwinter roughness and port
  70000/70000, PowerMonger commander, Populous swamp edge.

## Running

Nothing from this session. An `stserver.dll` started 13:31 (pid 34215) belongs to another Claude process.

## Open, in priority order

1. **The patrol, from what a player sees.** The player-view pilot hits seeders and does not finish a wave. First
   confirm the diagnosis on the held-out games (`pv/diag.py` and `pv/look.py` on `pv/d2_s10*.json`: is the last target
   alive a `b` track, and what is the pilot doing). Then give the tracker a pursuit model for the `b` class: a player
   knows a patrol within `$2800` turns at the ship (`shot.actor_step`, attack state), not its hidden words, so fit
   the turn from sightings or fly a head-on pass and fire inside 10 ticks. Settle by `pv/tier.py` on seeds 1 to 8,
   then once on a fresh held-out set (109 to 116; 101 to 108 are now seen). One change per version: the third version
   changed four settings and its drop cannot be attributed.
2. **Pass conversion as the thing to learn.** On seed 106 the spread is whether the second pass converts, not the
   order. Check it on a second seed (`order_of.py` on `sens1/s101_*.json`, free), then define the learner's target:
   approach speed and turnaround after a miss.
3. **Fast simulator.** The emulator gives about 150 ticks/s, 11 to 13 minutes a game. Tick, shot and seeder are exact
   Python functions in `py/mpc/`; the patrol given the ship's path is `shot.predict`; the wave-end rule is
   `behaviours.md` "When a wave ends". Port to F# (the post's code) and gate against a recorded game.
4. **F# port and TorchSharp**: check TorchSharp's macOS x64 support first (torch stops at 2.2.2 on this Intel Mac;
   gpubox is the fallback).
5. Pilot loose ends: two player-view deaths out of fuel (`d3_s1`, `d3_s3`) and one in `d2_s108` with 46 recoveries;
   the full-memory miss (`duel/s4_K6.json`); seeds 7 and 103 never end the wave for the full-memory pilot.
6. Video overlay of what the player-view pilot can see (window against radar-only, from the logged `obs`), if Dave
   wants it; IDEAS.md entry 10 does not yet carry the player-view result.
7. **Finish Paint It Black** (two TODOs are Dave's), then Mountains of the Moon line 50.
8. **"The placebo arm"**, **"How the agent was kept honest"**, **"Graded by the authors"**, **Cadaver's language**,
   **the planner**; new games (Laser Squad, a chess engine, Kick Off 2; no racing); carried items as in IDEAS.md.

## Known traps

- Settings tuned on eight seeds did not hold on eight others (3 of 8 against 0 of 8), and one game cannot rank two
  settings (`sens.py`): a version is judged on a held-out set it was not tuned on, once.
- `run_seeds.sh` runs the frozen `pv/fly_<tag>.py`, not `fly_v7.py`: copy the working file to a new tag and change
  its `here` line to the parent directory before a run (as `fly_d2.py` has it), so a later edit cannot change a
  version that has results.
- Kills in the pilot's JSON are score steps: the last one in an ended game includes the wave bonus.
- A patrol in its cruise state is on the radar and never in the 3D view, so it never gives a height.
- Poking the RNG at `S1b.snap` changes only later draws; a new layout needs the poke before the scatter (`Q1.snap`).
- The league's score caps at 2000 ticks for a wave not ended; `auto` can exceed it (`baseline2.py` runs to 3000), and
  seed 104's autopilot does not end in its cap.
- `fly.py` and `fly_v7.py` are deterministic: variation is settings or start.
- `view_check.py` labels an arrival with the record's behaviour after the tick ran.
- `scratchpad/virus/mpc/replay/` and `shot/` are pre-promotion copies; use `reversing/virus/py/mpc/`.
- zsh reads `${F}:textfile` wrongly without the braces; MobyGames 403; local Hugo too old; IDEAS.md entries are cited
  by number, leave gaps.

## Waiting on Dave

- `sessions/virus.md` is stale: it does not know `py/mpc/`, the radar and 3D-view sections or `py/scan/radar_check.py`
  and `view_check.py` (this session may not edit it). A `/resume virus` should read `git log -- reversing/virus` first.
- Is stserver stopping twice at a breakpoint after an interrupt a bug to fix in `server/Server.fs`, or the documented
  behaviour?
- Whether the Virus post is one post (planning, with the player-view tier as it stands: a negative result) and a
  learning sequel, or waits for a player-view pilot that finishes a wave.
- Carried: rewrite IDEAS.md around the ML ranking; Captain Blood prior art; Midwinter line 50; Captive keys figure;
  Carrier Command series; "proven" vs "observed" in Crude Buster and Final Fight; Lemmings artifact republish; Hugo
  upgrade; pushing master and the blog repo.

## Next session

`/resume blog`. Read `scratchpad/virus/mpc/README.md` "duel/pv/" and `behaviours.md` "What the 3D view shows". First
step: Open 1's check of the held-out failures (`pv/diag.py pv/d2_s10*.json`, then `pv/look.py` on the last 300 ticks of
two of them), which costs no games. Then the pursuit model for the `b` class as a new tag, one change, seeds 1 to 8,
and a fresh held-out set. Open 2's second-seed check can run beside it.
