# Virus: handoff

Updated by an overseer session that promoted the pilot-tick model and the 24-game attract chain (`git log -- reversing/virus`).

## Resume point

- Last commit of this workstream: the pilot and chain promotion (`git log -1 -- reversing/virus`). A separate session
  ("Virus: static code scan for demo, AI and behaviours") is folding `behaviours.md` into the docs after it.
- Working data: `M68000/scratchpad/virus/` (`disk/aha.msa` from the Dropbox `A-HA #[no number].zip`, `aha.st`,
  `drive/`, `fl/`, `cap/`, `gates/`, `demo/`). Rebuild: `tools/msa2st.py` on the MSA, `bash reversing/virus/drive.sh`
  (about 21 s), `bash reversing/virus/py/capture.sh`, then for the demo `bash reversing/virus/py/demo/capture.sh` and
  `capture_death.sh` (several minutes); anchors in `scratchpad/ANCHORS.md`.
- Start from: `drive/g_game2.snap` (wave-1 launch pad, a live game), `fl/f1.snap` (flight with thrust held),
  `demo/S1b.snap` (game start of the first attract flight, `$62a5f = $ff`).
- Uncommitted work left behind: none of this session's. `uv run python tools/gates.py run virus`: 4/4 PASS (`models`
  re-reads saved captures, the fresh part is `py/capture.sh`; `pilot_tick`, `pilot_scan_census` and `chain2` run the
  emulator, about 8 minutes together). The older demo gates are not in `gates.toml`:
  `bash reversing/virus/py/demo/gate_demo.sh`, `gate_death.sh` (over ten minutes), `queue_check.sh`.
- Subagent working directories: `scratchpad/overseer/aha/`, `virus_demo/` (first looks), `virus_pilot/` and
  `virus_long/` (pilot model, chain; `report.md` in each, `virus_long/work/main/` holds the 24 start snapshots).

## Proven so far

- The disk is Virus (D. Braben 1988, Union crack, TEX trainer), not Archipelagos; `drive.sh` reaches the wave-1 pad
  with the trainer's three cheats declined (README "Running it").
- Landscape: one byte per cell of a 256x256 map from a sum of eight table sines, three variants made by patching
  instruction words in `$245b8`: 65455/65455 on each landscape, controls 29124 and 10965
  (`bash reversing/virus/py/gate_all.sh`). Landscapes 1 and 2 come from poked stubs.
- RNG `$2706e/$27072` (`a += b; b = swap(old a)`) and the object scatter `$236f8`: 571/571 and 1774 of 1775 cells,
  controls 1767 and 1586 (same script; the counts are exact for the pad snapshot's own RNG state).
- Renderer: the 11x10 projected vertex grid and tile type words 330/330 on four flight frames (control 117/330);
  132/132 tile calls take those vertices and colours (control 33/132); the edge slope table 8064/8064 for dy 1..63
  (control 1431). The tile colour is a height band; no slope term was found in that path.
- Flight tick `$255c2`: 119/119 ticks on a mouse-driven run, control 99/119; under the poked autopilot pos, vel and
  attitude 119/119.
- Particles: stage-1 behaviour `$21792` 447/447, control 334/447.
- `$20e74(n)` selects landscape 1 at n = 4 and 2 at n = 9 (poked-stub callcaps; n is the wave counter `$32a50`, read).
- Attract mode (`demo.md`): the only write to `$62a5f` in a no-key run is `$ff` from `$24d14` after the 769-frame
  title loop; SPACE gives 0 from `$24cfc` (`py/demo/gate_demo.sh`).
- The demo runs to its natural end unaided (six life losses, game over, next demo). After a natural game over the
  next flight matches flight 1 on 205/500 samples, after an ESC on 500/500, and after a natural game over with four
  bytes of `$27134..$27147` cleared on 500/500 (`py/demo/gate_death.sh`).
- A chain of 24 complete attract games in one lineage from `S1b.snap`, no pokes, each ending by itself: game-over
  waves (`$32a50`) 3,3,3,2,3,3,2,3,3,2,3,2,3,4,3,3,2,3,2,3,3,3,3,3; Spearman rho with game number +0.09, permutation
  p 0.67 (recomputed from `chain.jsonl`); no trend in score, tick or flight length either. n = 24 detects only
  |rho| >= about 0.4. The first six games reproduce the older six-game chain exactly. `py/chain/gate_chain.sh long 24`
  (about 50 minutes); the 2-game form is gate `chain2` (demo.md "Twenty-four games").
- Speed: one lineage runs at about 4.3M steps/s (about 127 s per game); `bp` costs about 7%, `stserver` about 10%;
  headless runs draw nothing, so there is nothing to skip. Independent emulators scale to about 23M steps/s aggregate
  at 8 (load 5 to 10, indicative). The game-over and title wait is 8.2% of steps (README "Running long").
- Pilot tick `$2538c` as a model: equals `callcap` on 3496/3496 natural ticks of demo flight 1 (registers, aim,
  controller, matrix `$270d4`), five broken controls 11 to 3494 of 3496 (`py/pilot/gate_pilot.sh`, gate `pilot_tick`).
  The D0 = `$1000` output and the `$228de` scan skip were not reached. The nearest-record scan picks 14 behaviour
  kinds; homing records (`$21d08`) were present in 1069 of 1563 scans and chosen in 263 (gate `pilot_scan_census`).
- What carries over a game over: the high-score table (the demo's score under a stock name), `$32a52` (the previous
  game's wave, copied by `$25bdc`), the random state, and the four-entry target queue at `$27134`, which a homing
  pool-record behaviour steers at (`$21d62` through `$22c1e`). The queue is refilled each game: 0 of 92 entries at
  games 2 to 24's starts equal an entry of the previous start. The pilot's scan reads only the pool records, so it
  reaches the queue only through records that home on it.

## Running

Nothing running.

## Open, in priority order

1. The attract mode's remaining gaps (`demo.md` "Not tested"): the six memory blocks that start at 0 and step up over
   the chain (`$27ce9..$27d11`, `$289c2..$28a02`, `$29703..$29769`, `$2b591`, `$2ca81..$2cbcb`, `$2e2c3..$2e2d3`;
   a candidate list from about 1M scanned bytes, no multiple-comparison correction): `watch` their writers over one
   game (`behaviours.md` may already answer this). A 100-game chain (`py/chain/gate_chain.sh long 100`, about 3.5 h)
   would detect rho about 0.2. The pilot model from a later-wave snapshot for its two unreached branches; the
   `$62a60` reload at pilot call 1191 (a life loss, inferred: `watch 32a54 1`); the homing records on screen; a
   mouse-flown game before an attract flight.
2. Slope shading: check `$18322`, `$23a2c` and the `$1f2bc` span routines; change one vertex height and diff the
   screen. The game is known for slope-shaded tiles and the gated colour path has none.
3. A played route to wave 5 or 10 with a `watch` on `$32a4e`, so landscapes 1 and 2 stand on play, not stubs.
4. The depth buckets (`$1fa72`, `$2157c`, painter `$243ec..$24474`): dump a bucket's records at the start of the
   painter and gate the order. The grid's edge blocks. Slope-table entries for dy 64..127.
5. The autopilot's matrix mismatch in `virus_flight.py` (4/119 against 119/119 for pos, vel, attitude): the pilot model
   matches all 3496 `$270d4` writes, so capture timing in that gate is the likelier cause (not tested).
6. The mouse routine `$254aa`, ground contact in the tick, the other particle behaviours, object types 1..9 and
   markers 10..12, the launch-pad colour table `$246ba`.

## Known traps

- `drive.sh` timing depends on load time (the title needs about 10M steps): if the last snapshot shows the title, run
  it again. The trainer drops early key presses, so the drive sends five N keys.
- `g_game*.snap` is a live game. The press page says "demo mode", but the demo starts only after about 8.7M idle
  steps on that page.
- After an ESC or a lost last life the restart runs two scatters, A inside `$25bc0` and B at `$230a6`; `bp 236f8`
  stops at A or B depending on the key hold. Check the return word at `$6fffe` (`5bee` is A, `30ac` is B), and poke a
  seed at B, not A.
- A test of what carries between attract flights must let the flight end by itself: an ESC skips the game-over path
  and leaves the `$27134` queue zero.
- A `bp` stop followed by `r` prints the registers twice; the log parsers take every second block.
- The demo's score goes negative early: each shot costs a point (`$25752`).

## Waiting on Dave

- Whether 24 natural games with no wave trend (waves 2 to 4) settle "the demo gets better between plays", or whether
  to run the 100-game chain (Open 1). Dave recalls it reaching higher levels with repeats; it may be the Archimedes
  original, which is not this code.
- Whether Virus continues as a workstream, and with the renderer's shading or the attract mode first.

## Next session

`/resume virus`. Run `uv run python tools/gates.py run virus` (4/4) and `bash reversing/virus/py/demo/gate_demo.sh`
as the controls. Read `behaviours.md` (the static scan), then Open 1's monotone blocks, or Open 2 (slope shading)
for the renderer.
