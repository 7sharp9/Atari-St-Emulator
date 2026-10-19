# Lemmings: handoff

Updated 2026-10-19 by the fifth working session.

## Resume point

- Last commit of this workstream: `git log --oneline -- M68000/reversing/lemmings` (the handoff and infographic commit).
  The emulator fix is `8b6c474`.
- Working data: `scratchpad/lemmings/`: `lemmings.st`, `files/`, `b300000000.snap` (cold boot, cracktro),
  `lvl1_a.snap` (level 1, all 10 out; stops in the cracktro frame, `A5 = $c822`: set `A5 = 272d4` before a
  `callcap`), `sel.snap` (digger selected; every skill run starts here), `blk/post.snap` (blocker placed),
  `blk/<run>/` (each `skilldrive.py` run: `drive.txt`, `raw.txt`, `frames.txt`), `info/` (infographic build),
  `interesting/full.asm` (whole program, `$400`-`$27000`). Rebuild with `reversing/lemmings/drive.txt`, then `click_digger.txt`.
- Disk: `~/Library/CloudStorage/Dropbox/Daves/ST games/Lemmings (1990)(Psygnosis)[cr BBC][a].st`.
- Uncommitted work left behind: none (`Cadaver/` is another session's).

## Focus

Lemming behaviour (record, state machine, terrain collision, update order). `extras.md` holds the side findings
(codes, levels, ending, crack).

## Infographic

`reversing/lemmings/infographic/` builds the "Inside Lemmings" artifact (published, private, still says the basher tick is open until republished:
https://claude.ai/artifact/3M9FDun4B75R8QL7mofGaC, version 2). `infographic/build.sh` now rebuilds it entirely locally
(runs, blocker arms, data, page); the eight skill runs and both blocker arms regenerate byte for byte. Plate text and
the driven/read labels are hand-written in `template.html`: update them when `mechanics.md` changes, rebuild, and
republish to the same URL. Only light mode at desktop width was looked at (the preview pane cannot emulate dark or
phone for a local file): check dark mode and phone width on the published page.

## Proven so far

Detail and match counts are in `reversing/lemmings/mechanics.md`.

- Boot to gameplay, deterministic (`drive.txt`). Two emulator walls fixed behind the net.
- Lemming array `$23484`, stride `$2c`, 10 of 10; skill click path, hit test `$1540`, digger (`click_digger.txt`).
- Collisions: terrain bitmap `$41806`/`$330` and object map `$62f80`/`$198`; the cell dispatch `$8b6e`.
- Blocker: stamp `02 0a 03`, turn handlers `$8bce`/`$8bdc` once each against 0 and 0 in the control, restored at the
  explosion (`click_blocker.txt`).
- Basher, miner, builder, climber, floater, bomber, fall and splat driven, with steel refusal for basher and miner
  (`py/skilldrive.py`, `py/terrain_diff.py`). Bits 16 and 10 and bits 12 and 13 were mis-assigned in the earlier doc and are corrected.
- Walker thresholds (`py/stepsweep.sh`): step 1 to 2 rows smooth, 3 to 6 rows ledge hop (bit 13, 2 rows a tick), 7 or more a wall.
- Basher erase ticks (`py/maskwatch.py`): `$81d0` increments the tick, then post-increment 2 to 5 (and 18 to 21) erase one 10-row mask frame each, 12 bursts of 80 word writes, one a tick. Miner (`--miner`): post-increment ticks 1 and 2 of 24, 13-row frames, 104 words each, 4 of 4.
- Exit, trap and reversal cells (`py/objdrive.py`): codes 1 (exit, 8 ticks, saved counter +1), 2, 3, 4, 5, 6 each driven.
- The crater: `$8156` frame 1 stores the record in `152(A5)`, `$55b6` (main loop `$109a`) ANDs the 16 by 22 mask `$14fd2` at
  `(x-8, y-14)` through the blitter `$8cf8`; 113 of 113 pixels predicted; refused by cell codes 9, 5, 1.
- Access codes and the level catalogue, 260/260 generator cases and 18/18 typed codes (`extras.md`, `py/codes.py`).

## Open, in priority order

1. The object table behind a cell's high nibble (`$23044`, stride `$22`): exit and trap animations and sounds; level 1's other
   object cells (`$20` at (217..218, 31)).
2. Fields +10 (frame), +20, +36/+38/+42; the release rate (`72(A5)`/`58(A5)`); the blocker's refusal test (`$1b60`) and
   ground-loss release.
3. Walls and one-way cells 7 and 8 (read only); a level with a real trap (not a poked cell) and a climber or digger path to the exit.
4. Optional: table of all 140 codes, `BasicFX`/`FullFX`; dark-mode and phone check of the published infographic.

## Known traps

- `ATARI_NOTRACE=1`; `resume <snap> repl --disk-a <st>`; `mouse down l` / `mouse up l`; `m <addr> <len>` takes a decimal length.
- Pinning the pointer to the corner scrolls the level left; read the scroll `+2` of `$26c04` after the last move
  and aim at world `(lx - 8, ly - 13)` (`skilldrive.py` does this for lemming 0 at its fixed offset).
- `w` is a longword: poking a skill count also writes its neighbour (`+36` basher with `+38` floater); level 1 has 0 in every
  count but the digger's, so `skilldrive.py` writes `00050000`.
- A skill refused at once (builder with a hill ahead) is the game's own terrain test, not a failed click: read `+14` and the
  count after the click before concluding.
- The bomber keeps walking during its countdown, so its crater is wherever it stops: aim the window with `--x0`.
- Inside the blitter `$8cf8` `A5` is the blit block `$c822`, not `$272d4`, and `bt` throws AddressError down the `A6` chain there: read
  the caller from the stack yourself (`m <A7+56> 4` after its `movem.l` of 14 registers).
- Stop a `hits` or `bp` census at the exact phase: a `hits` first-step is relative to the run's own start, not the snapshot's.
- macOS `head -n -1` fails; write the script out in full instead of trimming another.
- The listing at `$2000` misses the input and click code below it; use `$400`.
- An agent's output files go in its own directory only: `make_blank_disk.py` deleted the tracked `blank_80ss.st` (restored).

## Next session

`/resume lemmings`. Item 1 (object table `$23044`), then rebuild and republish the infographic (it still lists the basher/miner ticks as open). Fold any change into
`mechanics.md` and the matching infographic plate, then `infographic/build.sh` and republish.
