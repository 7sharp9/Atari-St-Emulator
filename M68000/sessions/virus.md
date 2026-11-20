# Virus: handoff

Updated 2026-11-20 by the session that ended at commit `1bed1c3` (pushed). Virus game work between `36da14e` and `d76cf76` was
done under the blog workstream (`sessions/blog.md`; `git log -- reversing/virus` for the commits); this file now covers
it and the blog file keeps only the posts.

## Resume point

- Last commit of this workstream: `d10fd5e` (the Hatari speed record); before it `d6e9ab6` (sound, models, pursuer and
  patrol; gates `sound`, `models3d`, `pursuer`). Lessons: `b270dd3` (DEVELOPING Hatari), `1bed1c3` (skill 3c re-stop).
- Working data: `M68000/scratchpad/virus/` (rebuild: README "Running it", `drive.sh`, `py/capture.sh`, the demo capture
  scripts; `chain/long100/` from `py/chain/chain.py` (3.1 h); `pursuer/` from `py/behaviours/build_marks.py` and
  `cap_nat.py`; rows in `scratchpad/ANCHORS.md`). Each gate writes its own `W/<area>/` output (`sound/wav/` holds the 54
  WAVs, `models3d/svg/` the SVGs).
- Start from: `chain/long100/starts/main_g050.snap` (reaches wave 5 and the mothership), `fl/f1.snap` (flight with
  thrust held), `demo/S1b.snap` (the first attract flight's start), a seeded start (`mpc/duel/starts.py` on
  `demo/fl/Q1.snap`) for pilot work.
- Gates: `uv run python tools/gates.py run virus -j 8`: 17/17 PASS at `d6e9ab6` (about 5 min, load 2.3).
- Uncommitted work left behind: none (`.obsidian/` is Dave's).
- Agent working directories, each with `report.md`: `scratchpad/overseer/virus_post/` (the demo-variance post draft),
  `virus_sound/`, `virus_models/` (its `svg/` is a stale render with wrong names; `out_svg/` was the agent's final set,
  superseded by the gate's `W/models3d/svg/`), `virus_learner/`, `hatari_speed/`.

## Proven so far

Detail and controls are in the cited sections; each gate is in `reversing/virus/gates.toml`.

- Landscape, RNG and scatter, grid, tiles, slope table, flight tick, particles: gate `models` (README sections).
- Renderer: no slope shading; spans 1440/1440, slope table 16320/16320, depth buckets 39523/39523 (gates `shading`,
  `painter`).
- Model data and drawers: 43 models at `$aa72..$ce9a`; vertices, shadows and the `$26780` call stream exact on natural
  frames (f1 1853/1853, 251/251) and for all models in 40 poses (14680/14680); control 1456/1853 (gate `models3d`, README
  "Model data and the model drawers"; `models3d.png`).
- Flight: the ship tick off the capture 6631/6631 (gate `mpc_flight`); the player's shot, wave-0 actors, ship box (gate
  `mpc_shot`); mouse 180/180 (gate `flightctl`).
- Actors: seeder, chaser `$21afe` 1069/1069, mothership chaser 4064/4064 (gate `behaviours`); pursuer `$21f00`
  24653/24653, `$2202c` 22805/22807, patrol home 53992/53992, attack 6317/6317, cruise 5877/5877, wait 2213/2213,
  conversion 34/34 over 25 natural captures of waves 1 to 4 (gate `pursuer`, `behaviours.md` "The pursuers and the patrol").
  A kill swap-removes the last record into the slot, walked there that tick with that slot's phase.
- Sound: records and `Sound_ChannelStep` modelled; the game's own routines match on 6305/6305 and 6000/6000 ticks and
  400/400 natural ticks; WAVs from an assumed YM2149 synthesis (gate `sound`, `frontend.md` "Sound").
- Pilot tick `$2538c` 3496/3496 (gate `pilot_tick`); the radar and the 3D view window (`behaviours.md`).
- Attract mode: 100 unpoked games, final wave 1/2/3/4/5 in 2/21/69/7/1, no trend (rank +0.19, p 0.052); lives held at the
  first wave-3 death set a long game apart (4 of 13 with 4 or 5 lives reach wave 4, 4 of 64 with 1 to 3) (`demo.md` "A
  hundred games"; the post draft recomputed every figure). Nothing in the carried state adapts (`behaviours.md`).
- Divergence (record, `scratchpad/virus/mpc/README.md` "chaos/"): one-unit nudges separate the ship only closed loop.
- Speed: Hatari runs the demo flight 1.7 to 1.9x as fast as ours (205 to 209 against 110 ticks/s), about 4x with
  `--cpu-exact off --compatible off --timer-d on` from a transplanted state, same state at ticks 4,790 and 11,000 (record,
  README "Running long").
- `fly_v8.py` (re-stop bound 2,000) equals `fly_v7.py` (d2) on seeds 1 to 8 on every key but `args`: no re-stop occurred
  in 12,896 ticks (record, `mpc/README.md` "duel/pv/").

## Running

Nothing running.

## Open, in priority order

1. **Fast simulator** (what makes a learner affordable; ours runs about 110 ticks/s, Hatari 200 to 450 with no fork or exact stop): tick, shot, seeder,
   chasers, pursuers and patrol are now exact models. Still needed: the pursuers' and patrols' shots `$22e38` with the
   object pool and RNG draws, the bomber `$22316`, the attractor `$224a6`, the damaged pursuer `$221ac` (`behaviours.md`
   Open 5). Then port to F# and gate against a recorded game tick by tick.
2. **The player-view pilot's patrol gap** (`sessions/blog.md` Open 2): a pursuit model for the `b` class, judged on seeds
   1 to 8 with `fly_v8.py` and once on a fresh held-out set.
3. `shot_capture.py` (`py/mpc/`) and `gate_actor.py`, `gate_chaser.py` still use a 64-step re-arrival test and the old pool
   index after a kill; neither has shown a miss on their gates, but a change is a gate rerun, not a doc edit.
4. Sound against real audio: record one effect from Hatari (`--sound on` with its WAV recording) and compare with
   `virus_sfx.fsx`'s render (noise rate and taps, volume curve).
5. Landscape 2 naturally (README Open 2), the enemy exit writer `$257fa` (Open 3), the rocket `$25306` and whether the pilot
   can kill the mothership (`behaviours.md` Open 1), the drawers' unread parts `$265e4`, `$26972` (README Open 1).

## Known traps

- `stserver` stops twice at a breakpoint when an interrupt is taken there; Virus's handlers return 181 to 243 steps later
  (CLAUDE.md). Agents' first harnesses used 64 steps; three of this session's four agents hit or checked it.
- `drive.sh` timing depends on load time; if its last snapshot shows the title, run it again.
- After an ESC or a lost last life the restart runs two scatters (A in `$25bc0`, B at `$230a6`); poke a seed at B.
- A test of what carries between attract flights must let the flight end by itself (ESC skips the game-over path).
- The demo's score goes negative early: each shot costs a point.
- `virus_sfx.fsx`'s summary file was empty while it used a top-level `use` (fsi does not dispose it); fixed in `d6e9ab6`.

## Waiting on Dave

- The demo-variance post (`scratchpad/overseer/virus_post/index.md`, draft): title ("Infected" or plain), hook A/B/C,
  image path `/images/posts/virus/`, links, and whether to run a 200-game chain for the p 0.052 no-trend claim. Not yet
  run through `write-like-dave`; nothing is in the blog repo.
- Whether the stale `scratchpad/overseer/virus_models/svg/` may be deleted.

## Next session

`/resume virus`. Run `uv run python tools/gates.py run virus -j 8` (17 gates) as the control. Then Open 1: gate the
pursuers' shots `$22e38` with the object pool, then the bomber, then start the F# simulator port; or the post if Dave
has settled its questions.
