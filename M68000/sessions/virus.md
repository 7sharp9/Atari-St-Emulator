# Virus: handoff

Updated 2026-11-14 by an overseer session that promoted two subagents' first passes (commit `b71d38b`).

## Resume point

- Last commit of this workstream: `b71d38b` virus: first look (A-HA disk).
- Working data: `M68000/scratchpad/virus/` (`disk/aha.msa` from the Dropbox `A-HA #[no number].zip`, `aha.st`,
  `drive/`, `fl/`, `cap/`, `gates/`, `demo/`). Rebuild: `tools/msa2st.py` on the MSA, `bash reversing/virus/drive.sh`
  (about 21 s), `bash reversing/virus/py/capture.sh`, then for the demo `bash reversing/virus/py/demo/capture.sh` and
  `capture_death.sh` (several minutes); anchors in `scratchpad/ANCHORS.md`.
- Start from: `drive/g_game2.snap` (wave-1 launch pad, a live game), `fl/f1.snap` (flight with thrust held),
  `demo/S1b.snap` (game start of the first attract flight, `$62a5f = $ff`).
- Uncommitted work left behind: none. `uv run python tools/gates.py run virus`: 1/1 PASS (gate `models`; it re-reads
  saved captures and runs no emulator, the fresh part is `py/capture.sh`). The demo gates are not in `gates.toml`:
  `bash reversing/virus/py/demo/gate_demo.sh`, `gate_death.sh` (over ten minutes), `queue_check.sh`.
- The two first looks' working directories are `scratchpad/overseer/aha/` and `scratchpad/overseer/virus_demo/`
  (their reports and the overseer's checks).

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
- A chain of six complete attract games with no pokes: game-over ticks 12088, 12894, 15018, 7106, 8178, 13052; scores
  17526, 19770, 16984, 9763, 13302, 19369; rank correlation with game number -0.03 and -0.26
  (`py/demo/chain.py`, `chain_table.py` over `scratchpad/virus/demo/chain/chain.jsonl`). No trend; six games can
  only show a large effect.
- What carries over a game over: the high-score table (the demo's score under a stock name), `$32a52`, the random
  state, and the four-entry target queue at `$27134`, which a homing pool-record behaviour steers at (`$21d62`
  through `$22c1e`). The game start does not clear the queue. The pilot's routines `$2529a` and `$2538c` do not read
  it (read from code).

## Running

Nothing running.

## Open, in priority order

1. The attract mode's remaining gaps (`demo.md` "Not tested"): a gated model of one pilot tick (`$2538c` against
   `callcap`; only the launch branch is captured, the rules are read from code); what the homing records and the
   queue at `$27134` are on screen (`$205f6` is named `Infection_Plant` from its body only), and whether the pilot's
   nearest-record scan picks those records (a `bp` on `$253a4` comparing `$270a6` with the homing records); a longer
   unpoked chain (20 or more games, about 3 minutes each) if "better between plays" is still in question; a
   mouse-flown game before an attract flight (two attempts stuck on a game-over or name-entry screen).
2. Slope shading: check `$18322`, `$23a2c` and the `$1f2bc` span routines; change one vertex height and diff the
   screen. The game is known for slope-shaded tiles and the gated colour path has none.
3. A played route to wave 5 or 10 with a `watch` on `$32a4e`, so landscapes 1 and 2 stand on play, not stubs.
4. The depth buckets (`$1fa72`, `$2157c`, painter `$243ec..$24474`): dump a bucket's records at the start of the
   painter and gate the order. The grid's edge blocks. Slope-table entries for dy 64..127.
5. The autopilot's matrix mismatch (4/119 against 119/119 for pos, vel, attitude): `watch` the writers of `$270d4`.
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

- Whether "the demo gets better between plays" is settled for you by six games with no trend, or whether to run
  the longer chain (Open 1). It may also be a memory of the Archimedes original, which is not this code.
- Whether Virus continues as a workstream, and with the renderer's shading or the attract mode first.

## Next session

`/resume virus`. Run `uv run python tools/gates.py run virus` (1/1) and `bash reversing/virus/py/demo/gate_demo.sh`
as the controls. Then Open 1's pilot-tick model, which turns the autopilot's rules from read into gated and answers
whether the pilot targets the homing records; or Open 2 (slope shading) for the renderer.
