# Virus: handoff

Updated 2026-11-20 by the session that ended at commit `48bf120`.

## Resume point

- Last commit of this workstream: `48bf120` (four actor gates, the capture fix, the death census, sound against Hatari).
- Working data: `M68000/scratchpad/virus/` (rebuild: README "Running it", `drive.sh`, `py/capture.sh`; `chain/long100/` from
  `py/chain/chain.py` (3.1 h); `pursuer/` from `py/behaviours/build_marks.py` and `cap_nat.py`; `deaths/saved/` from
  `py/deaths/death_census.py` per game; rows in `scratchpad/ANCHORS.md`). Each gate writes its own `W/<area>/`.
- Start from: `chain/long100/starts/main_gNNN.snap` (natural game starts; 050 reaches wave 5), `pursuer/snaps/g0NN_*.snap`
  (waves 1 to 4 mid-game), `demo/S1b.snap` (the first attract flight), `fl/f1.snap` (flight with thrust held).
- Gates: `uv run python tools/gates.py run virus -j 6`: 22/22 PASS at this commit (about 16 min at -j 6, load 3 to 5).
- Uncommitted work left behind: the F# fast simulator, `scratchpad/overseer/virus_fsim2/` (the working copy; `virus_fsim/` is
  its parent). Not promoted because it does not yet track a whole game. Its `report.md` (and `virus_fsim/report.md`) list every
  gate, count and blocker; `bash scratchpad/overseer/virus_fsim2/gate_fsim.sh` and `gate_game.sh` re-run them (builds into its
  own `bin/`, never `M68000/bin`). `.obsidian/` is Dave's.
- Agent records, each with `report.md`, under `scratchpad/overseer/`: `virus_eshot`, `virus_bomber`, `virus_attractor`,
  `virus_damaged`, `virus_swapfix`, `virus_hsound` (the Hatari sound comparison, a record cited by `frontend.md`),
  `virus_deaths`, `virus_fsim`, `virus_fsim2`; shared brief `VIRUS_SIM_BRIEF.md`, promotion rules `VIRUS_SIM_PROMOTE.md`.

## Proven so far

Detail and controls in the cited sections; each gate is in `reversing/virus/gates.toml`.

- Landscape, RNG, scatter, grid, tiles, slope, flight tick, particles (gate `models`); renderer (`shading`, `painter`); models
  and drawers (`models3d`); flight 6631/6631 (`mpc_flight`); player's shot (`mpc_shot`); mouse 180/180 (`flightctl`).
- Actors, all nine fields per tick, natural play (`behaviours.md`): seeder, chaser 1069/1069, mothership chaser 2818/2818
  (`behaviours`); pursuers and patrol 24653, 53992 ... (`pursuer`); two-hit pursuer's hits 16/16, stunned 64/64, kills 12/12
  (`pursuer2`); attractor fly 20670/20670, ship pull 59/59, drain 204/204 (`attractor`); enemy shot 334647/334647 checks with
  its three RNG draws (`eshot`); bomber 35960/35960, RNG 35970/35970, bombs 6447/6447 (`bomber`). The bomber's 16th-tick
  bomb filter at `$22408` never filters (read in the disassembly, control 35890/35970).
- Capture rule: a same-PC `stserver` stop is a re-stop only with equal D0-D7/A0-A6 (`behaviours.md` "The pursuers and the
  patrol"); patrol/home in swapped slots +4 on the corpus.
- Why the demo loses its lives: 126 losses in 23 games, 73 at fuel 0 (38 falls after the tank ran dry), 32 ground impacts
  with fuel left, 19 contact with fuel left; thrust is 66% of the drain; no pad refuel ever (`deaths`, `demo.md` "Why the
  demo loses its lives"). One poke trial (thrust cut while rising) is no remedy, n = 8.
- Sound against Hatari (record): register stream 358/358, the same 17-bit LFSR 396/396; clock 2.005312 MHz and the measured
  volume table now in `virus_sfx.fsx` (`frontend.md` "Sound").
- Attract mode does not learn (`demo.md`, 100 games; `behaviours.md`). Pilot tick 3496/3496 (`pilot_tick`).
- F# simulator (record, uncommitted): every pool behaviour, the pilot 3496/3496, death and restart; interval RNG 47224/47709;
  a whole demo game equals the emulator for 217 to 1117 ticks, then diverges on a missing draw group; 9.6 games/s.

## Running

Nothing running.

## Open, in priority order

1. **Make the demo better** (Dave's aim): waits on Dave's choice below. Either way: check that the simulator's game
   statistics match the emulator's (final wave and loss causes over about 100 games each, chain starts), then search pilot
   settings over hundreds of simulated games, then confirm the winner on many chain games in the emulator. Candidates from
   the census: less thrust duty, a reflex trigger quadratic in vy, landing on the pad to refuel.
2. **Close the simulator's RNG gaps** so a simulated game equals the real one: the 9-draw splash and 4-draw smoke callers,
   the -9/-18 and +54 cases, the g003 tick-13705 queue, the kill explosion's position (`virus_fsim2/report.md`). Each: stop the
   emulator at the divergent tick (`VirusSim compare` names it), `bp` the spawn routines, name the caller. Then promote the
   simulator into `reversing/virus/sim/` with its gates in `gates.toml`.
3. The mothership `$22688`/`$226ac` and its chaser in F#; the object-map rescatter at counter 4; `$201b4`, `$2004a`, `$23c08`.
4. `py/mpc/shot.py`'s `_tilt` is exact only below `$7e` (signed up-branch; `pursuer2.use_signed_tilt()` patches it on import):
   fix it in `shot.py` and rerun `mpc_shot`, `pursuer`, `pursuer2`.
5. The ground-hit kills (two-hit pursuer, attractor) are poke-only; the enemy shot's removal branches are classes only.
6. Landscape 2 naturally (README Open 2), the rocket `$25306` (`behaviours.md` Open 1), sound multi-voice mixing.

## Known traps

- `stserver` re-stop: see the capture rule above; agents' first harnesses used a step bound alone.
- `gates.py -k` takes one substring; several names are a usage error. `flightctl` failed once at its census step under load
  5 to 6 in a `-j 6` run and passed alone: rerun a lone failure before reading it as a regression.
- The simulator's `VirusSim bench` is invalid after the death path (dead ticks return early); use `throughput`.
- Per-routine gates missed two bugs a whole-game compare found (a queue y from the wrong register, droplet jitter carried in
  D0/D2 between calls): compare whole frames before trusting a composed model.
- `drive.sh` timing depends on load; after an ESC or a lost last life the restart runs two scatters (poke a seed at B);
  ESC skips the game-over path; each shot costs a point.

## Waiting on Dave

- Making the demo better: patch the game's own pilot `$2538c` (the attract mode itself plays better), or an outside pilot
  that flies the game (lockstep through `stserver`, or a deadline "fly-by-wire" packet per tick: Dave's question of
  2026-11-20, answered in that session; an emulator feature if wanted).
- Whether to promote the F# simulator now or after it tracks a whole game.
- The demo-variance post (`scratchpad/overseer/virus_post/index.md`): title, hook, images, links, the 200-game chain.
- Whether the stale `scratchpad/overseer/virus_models/svg/` may be deleted.

## Next session

`/resume virus`. Run `uv run python tools/gates.py run virus -j 6` (22 gates) as the control. If Dave chose a pilot route,
start Open 1 with the statistics check (`virus_fsim2`'s `VirusSim game` over chain starts against `chain.jsonl`); otherwise
Open 2, starting from `VirusSim compare` on `main_g001.snap` (diverges at arrival 269, the emulator drew 9 more).
