# Blog: handoff

Updated 2026-11-18 by the session that ended at commit `2cb2ff4` (master; the blog repo at `3443c14`).

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is reversed in its
own workstream; this one reads their docs, checks the claims a post would rest on, and feeds corrections back to the
game docs (committed as that game's commit; the game's own handoff is not edited here). Dave's standing direction:
posts explain algorithms the games use and their relevance today, not emulator fixes (2026-11-11); one infographic per
interesting algorithm (2026-11-12); topic docs stay compressed, clarity goes on figures, posts and README openings by
`reversing/WRITING.md` (2026-11-15); an ML / AI-engineering slant, new games and a long pipeline welcome, Archipelagos
not the next post (2026-11-16). The shape that fits the blog: a game's algorithm ported to idiomatic F#, proven against
the game, ending in a visual the game could not make.

**Dave (2026-11-18): build "Virus flown by optimisation"** (he picked it over "The placebo arm" after the spike), and
he wants the next version to be a real learner: one that gets better during a level or between games, which the
present pilot does not. New game lines stay open, racing games excluded.

## Resume point

- Last commit of this workstream: `620c3d6` (virus: replay harness, flight, shot and actor models, gates
  `mpc_flight` and `mpc_shot`), then two CLAUDE.md commits (the `stserver` double-stop rule). Blog repo `3443c14` (IDEAS entry 10). Master is 5
  ahead of origin before this file's commit, the blog repo 5; neither pushed.
- Working data: `scratchpad/virus/mpc/` (README there: `plan/` the waypoint spike, `duel/` the pilot, its sweeps and
  `virus_duel.mp4`, `gate/` the gates' outputs). Inputs: `scratchpad/virus/fl/f1.snap`, `cap/flight_bp.txt`,
  `demo/S1b.snap` (rebuild: `sessions/virus.md` "Resume point").
- Start from: `demo/S1b.snap` (demo flight 1, wave 0). Pilot: `scratchpad/virus/mpc/duel/fly.py` with the torch env
  `uv run --no-project --python 3.12 --with torch==2.2.2 --with 'numpy<2' --with pillow python fly.py <out.json>`.
- Gates: `uv run python tools/gates.py run virus -k mpc_flight` and `-k mpc_shot` PASS (92 s, 114 s) on M68000.dll
  `1620cb81c9ee3538`, stserver.dll `e0f474f6e858bbb5`. Virus: 0 MISSING, 2/6 gates declare no inputs (`models`, `chain2`).
- Uncommitted work left behind: none. The pilot is scratchpad-only on purpose (not robust yet).

## Proven so far

- Virus ship tick as functions, off the capture: 6,631/6,631 free-flight ticks, 17/17 deaths named, landing 618/618
  (`reversing/virus/README.md` "Off the capture, and where free flight ends"; gate `mpc_flight`).
- Virus player's shot, wave-0 actors, ship box: spawn 2,354/2,354, hit 15/15 and 43,488/43,488, seeder fly 7,701/7,701,
  ship box 90/90 poked (`reversing/virus/behaviours.md` "The player's shot, the targets and the ship box"; `mpc_shot`).
- Records, not gates (`scratchpad/virus/mpc/README.md`): a float copy of the tick misses a 300-tick waypoint by 14,712
  units in the game, 3,092 with the rounding mean, 241 replanned every 20 ticks; the wave-0 pilot kills the three
  seeders before the autopilot's tick 901 in 6 of 9 settings (best 534), 0/9 crashes with the pull-up guard, 21 of 22
  shots kill, first kill never before the autopilot's 271. It does not kill the patrol, so it does not end the wave.
- Carried, unchanged: Archipelagos generator, Captive keys, Midwinter roughness and port 70000/70000, PowerMonger
  commander (now also an 80M horizon 6/30 against 40M 7/30, `powermonger/commander/README.md`), Populous swamp edge.

## Running

Nothing from this session. The `M68000.dll resume ... cmd17 ...` processes are the commander's control run.

## Open, in priority order

1. **Pilot v-next: the game's end condition, then robustness.** (a) Target the patrol too and stop on the wave end
   (the tick that does not return to `$255d4`, autopilot 1189; `behaviours.md` "When a wave ends"), so the table
   compares wave-end ticks. `shot.predict` is exact for the patrol given the ship's path, so the planner must roll
   the patrol inside the plan; start with a frozen-ship prediction and measure. (b) Target order by estimated time,
   not nearest-first with hysteresis (first kill is 401 to 882 against 271). (c) Replace hand-set cost weights: the
   sweep shows `--mscale 120` gives 0 kills and `--vmax 180` 2. Settle by a held-out design: tune on some starts,
   report on others (perturbed starts as the commander did, or later demo flights from `chain/long/starts/`).
   (d) The one miss (`duel/s4_K6.json`): check for a seeder take-off draw between fire and hit.
2. **The learner (Dave's ask).** Two experiments, each with a curve to plot:
   - *During a level:* start the pilot on the plain float tick and fit the residual online (recursive least squares on
     next-state error, per axis, features 1, thrust, sign of v) from the ticks it flies; plot waypoint or shot miss
     against ticks flown. Known answer to recover: +31.5/64 per axis and about +0.5 per thrust tick. Same for the
     enemies: learn the seeder's velocity and height spring from observation in place of `shot.predict`. Gravity
     changes by wave (3, 4, 5, 6: README, read), so a later wave tests whether it re-adapts.
   - *Between games:* keep every transition and outcome; after each game refit (i) the model, (ii) the cost weights
     by an outcome-driven search (CMA-ES or a bandit over the nine settings), (iii) a small policy network distilled
     from the planner (DAgger), then fly game n+1 with it. Plot wave-end tick and score against game number beside
     the autopilot's flat 24-game line (`demo.md` "Twenty-four games": rho +0.09, p 0.67). A learned value function as
     the plan's terminal cost is the principled fix for the target-order myopia in item 1b.
   Needs a fast exact simulator for (iii): the emulator gives about 150 ticks/s; port tick, shot and seeder (already
   pure Python functions in `py/mpc/`) to F#.
3. **F# port and TorchSharp** for the post's code: check TorchSharp's macOS x64 support first (torch stops at 2.2.2 on
   this Intel Mac; gpubox is the fallback).
4. **Finish Paint It Black** (two TODOs are Dave's), then Mountains of the Moon line 50.
5. **"The placebo arm"** (commander results; add the 80M arm and the same-build control when scored), then **"How the
   agent was kept honest"** (evidence rules and recorded failure modes; breaks the algorithms-only rule, Dave's call),
   **"Graded by the authors"** (needs a held-out design), **Cadaver's language** and **the planner**.
6. **New games** (no racing; prior art unchecked): Laser Squad, a chess engine (Psion Chess or Colossus Chess X: Elo
   as the metric), Kick Off 2. LCP is demoted: a fixed-priority cascade, Kroah 2006 is prior art.
7. Carried: Midwinter draft line 50, Captive emulator-check sampled bases, Carrier Command series, unsourced figures,
   `gen_takeoff.py` cache, Black Tiger stale claim; cut list as in IDEAS.md.

## Known traps

- "Cleared" was the script's stop test (no seeder left), not the wave's end: name results by the game's rule.
- `fly.py` is deterministic: `--seed` changes nothing. Variation comes from settings or start state only.
- Gradient planning can blow up (cost in the 1e5 range, tilt saturated, engine off): the exact pull-up check (`safe`
  in `fly.py`) is what stops crashes, not the cost.
- The fire rule fires only on a hit certain under jitter (-2..1 per axis, times moves + 1): a looser box wastes
  shots, a strict symmetric one (v2) never fires from range.
- `replay.py` `ext` entries wrap `watch_events`' `{id, dropped, events}`; only non-emptiness is meaningful.
- `scratchpad/virus/mpc/replay/` and `shot/` are the agents' pre-promotion copies; use `reversing/virus/py/mpc/`.
  `fly.py` still imports the scratch copies.
- zsh reads `${F}:textfile` wrongly without the braces (ffmpeg drawtext); MobyGames 403; local Hugo too old;
  IDEAS.md entries are cited by number, leave gaps.

## Waiting on Dave

- `sessions/virus.md` is stale: it does not know `py/mpc/`, the new gates or the doc sections (this session may not
  edit it). A `/resume virus` should read `git log -- reversing/virus` first.
- Is stserver stopping twice at a breakpoint after an interrupt a bug to fix in `server/Server.fs` (emulator
  workstream), or the documented behaviour (CLAUDE.md now states it)?
- Whether the Virus post is one post (planning) with a learning sequel, or waits for the learner.
- Carried: rewrite IDEAS.md around the ML ranking; Captain Blood prior art (Kroah) for that workstream; Midwinter
  line 50; Captive keys figure; Carrier Command series; "proven" vs "observed" in Crude Buster and Final Fight;
  Lemmings artifact republish; Hugo upgrade; pushing master and the blog repo.

## Next session

`/resume blog`. Read `scratchpad/virus/mpc/README.md` and `behaviours.md` "When a wave ends" and "The player's shot".
First step: make `fly.py` import `reversing/virus/py/mpc/`, add the patrol as a target and stop on the wave end; rerun
`sweep4.sh` and report wave-end ticks against the autopilot's 1189. Then the during-a-level learner (Open 2, first
bullet): it needs only `plan/` and `py/mpc/exact.py`, and gives the first learning curve. Copy `fly.py` aside before
each behaviour change.
