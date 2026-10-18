# Lemmings: handoff

Updated 2026-10-18 by the third working session, which ended at the commit that adds this file.

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

`reversing/lemmings/infographic/` builds the "Inside Lemmings" artifact (published, private:
https://claude.ai/artifact/3M9FDun4B75R8QL7mofGaC). It is a hand-written snapshot of `mechanics.md` plus frame data from the
uncommitted `scratchpad/lemmings/blk/` runs, so it goes stale: update it when a skill, bit role or collision claim changes
(its README says how). It still needs a fully local build (one script from run commands to `inside_lemmings.html`) and a
dark-mode and phone-width check; only light mode at desktop width was looked at.

## Proven so far

Detail and match counts are in `reversing/lemmings/mechanics.md`.

- Boot to gameplay, deterministic (`drive.txt`). Two emulator walls fixed behind the net.
- Lemming array `$23484`, stride `$2c`, 10 of 10; skill click path, hit test `$1540`, digger (`click_digger.txt`).
- Collisions: terrain bitmap `$41806`/`$330` and object map `$62f80`/`$198`; the cell dispatch `$8b6e`.
- Blocker: stamp `02 0a 03`, turn handlers `$8bce`/`$8bdc` once each against 0 and 0 in the control, restored at the
  explosion (`click_blocker.txt`).
- Basher, miner, builder, climber, floater, bomber, fall and splat driven, with steel refusal for basher and miner
  (`py/skilldrive.py`, `py/terrain_diff.py`). Bits 16 and 10 and bits 12 and 13 were mis-assigned in the earlier doc and are corrected.
- Access codes and the level catalogue, 260/260 generator cases and 18/18 typed codes (`extras.md`, `py/codes.py`).

## Open, in priority order

1. Exit and trap cells (codes 1, 4, 5, 6) and their death bits 1, 2, 3: drive a lemming into the level's own exit and a trap
   with `hits` on `$8aca`, `$8a62`, `$8b5c`; needs a level that has them (level 1 has an exit).
2. Ledge hop (bit 13) and the walker's step and wall thresholds: build 1, 2, 3, 4 to 7 row steps with `--wall` and read the
   lemming's y and state per tick.
3. The crater's caller and mask (`$aae8`-`$ac70`): `bp` at the writer and `bt`; the exact erase tick of the basher and miner
   masks with a per-tick `watch`.
4. Fields +10 (frame), +20, +36/+38/+42; the release rate (`72(A5)`/`58(A5)`); the blocker's refusal test (`$1b60`).
5. Make the infographic build local and keep it in step with the doc (see above). Optional: table of all 140 codes,
   `BasicFX`/`FullFX`.

## Known traps

- `ATARI_NOTRACE=1`; `resume <snap> repl --disk-a <st>`; `mouse down l` / `mouse up l`; `m <addr> <len>` takes a decimal length.
- Pinning the pointer to the corner scrolls the level left; read the scroll `+2` of `$26c04` after the last move
  and aim at world `(lx - 8, ly - 13)` (`skilldrive.py` does this for lemming 0 at its fixed offset).
- `w` is a longword: poking a skill count also writes its neighbour (`+36` basher with `+38` floater); level 1 has 0 in every
  count but the digger's, so `skilldrive.py` writes `00050000`.
- A skill refused at once (builder with a hill ahead) is the game's own terrain test, not a failed click: read `+14` and the
  count after the click before concluding.
- The bomber keeps walking during its countdown, so its crater is wherever it stops: aim the window with `--x0`.
- macOS `head -n -1` fails; write the script out in full instead of trimming another.
- The listing at `$2000` misses the input and click code below it; use `$400`.
- An agent's output files go in its own directory only: `make_blank_disk.py` deleted the tracked `blank_80ss.st` (restored).

## Next session

`/resume lemmings`. Item 1: from `sel.snap` find the level-1 exit and walk lemming 0 into it with `hits` on `$8aca` and the
cell dispatch, then a trap level if one is reachable. Fold any change into `mechanics.md` and the matching infographic plate.
