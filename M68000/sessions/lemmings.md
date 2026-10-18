# Lemmings: handoff

Updated 2026-10-18 by the second working session (state-bit roles, skill click path, agent sweep).

## Resume point

- Last commit of this workstream: `git log --oneline -- M68000/reversing/lemmings` (the one adding `extras.md`
  and `py/`). The emulator fix is `8b6c474`.
- Working data: `scratchpad/lemmings/`: `lemmings.st`, `files/`, `b300000000.snap` (cold boot, cracktro),
  `lvl1_a.snap` (level 1, all 10 out; stops in the cracktro frame, `A5 = $c822`: set `A5 = 272d4` before a
  `callcap`), `sel.snap` (digger selected), `lvl1.asm` (`$2000`-`$27000` only; the whole program is
  `interesting/full.asm`, `$400`-`$27000`). Rebuild with `reversing/lemmings/drive.txt`, then `click_digger.txt`.
- Disk: `~/Library/CloudStorage/Dropbox/Daves/ST games/Lemmings (1990)(Psygnosis)[cr BBC][a].st`.
- Uncommitted work left behind: none (`Cadaver/` is another session's).

## Focus

Lemming behaviour first (record, state machine, terrain collision, update order). `extras.md` holds the
side findings (codes, levels, ending, crack).

## Proven so far

- Boot to gameplay, deterministic (`drive.txt`; `README.md`). Two emulator walls fixed behind the net.
- Lemming array `$23484`, stride `$2c`, 10 of 10 (`mechanics.md`).
- Skill click path: icon index to `$26c1a` (watch hit at `$17ba`), hit test `$1540`, digger click sets
  `+14 = $4000` and y descends (`click_digger.txt`; `mechanics.md` "Skill assignment").
- Access codes and the level catalogue, 260/260 generator cases and 18/18 typed codes (`extras.md`, `py/codes.py`).

## Open, in priority order

1. Drive the other skills: set counts (`$26c18`+ region, `+26..+40` of the struct) from a snapshot, assign
   basher (bit 6), miner (4), builder (9), blocker (7), then bomber (`+21`), climber (`+22`), floater (`+23`),
   each with a same-snapshot control, and `callcap` each handler. Only the digger is proven.
2. Name the unnamed bits 0, 2, 3, 5, 8, 10, 11, 12, 16 from their bodies and the walker's setters (`$797c`,
   `$7a9a`, `$801c`); drive exit (bit 1), splat (8), explosion (16), drowning/trap (2).
3. Terrain: prove the one-plane bitmap at `$41806` (stride `$330`) and the object map `$62f80` (stride `$198`,
   cell codes 1, 2, 3, `$a`) against walk, fall and dig; find how terrain is removed by the digger.
4. Fields +10 (frame), +20, +27..+35 (blocker's saved cells), +36/+38/+42; tick rate of `$7802` per VBL, and
   release rate (`72(A5)`/`58(A5)`).
5. Optional: table of all 140 codes, feedback thresholds, `BasicFX`/`FullFX`.

## Known traps

- `ATARI_NOTRACE=1`; `resume <snap> repl --disk-a <st>`; `mouse down l` / `mouse up l`; `m <addr> <len>` takes a
  decimal length.
- Pinning the pointer to the corner scrolls the level left; read the scroll `+2` of `$26c04` after the last move
  and aim at world `(lx - 8, ly - 13)`.
- The listing at `$2000` misses the input and click code below it; use `$400`.
- An agent's output files go in its own directory only: `make_blank_disk.py` deleted the tracked
  `blank_80ss.st` (restored).

## Next session

`/resume lemmings`. From `sel.snap`-style states, item 1: assign the basher or miner (set its count word first),
then watch `+14` and the terrain bitmap, and `callcap` the handler. Items 2 and 3 follow from the same runs.
