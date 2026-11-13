# Populous II: handoff

Updated 2026-11-13 by the session that ended at commit `9fd979c`.

## Resume point

- Last commit of this workstream: `9fd979c` populous2: boot to gameplay from WILD! #29, anchors, first program map.
- Working data: `M68000/scratchpad/populous2/` (`src/WILD29.MSA` from the Dropbox `WILD! #29.zip`, `wild29.st`,
  `files/`, `anchors/`, `pop2_1770.bin` the depacked image, `pop2_all.asm` the whole-image listing). Rebuild:
  `reversing/populous2/README.md` "Provenance" and "Drive recipe".
- Start from: `scratchpad/populous2/anchors/p2_game_start.snap` (first play frames, conquest battle 0 vs
  Epimetheus; sidecar remounts `wild29.st`), or `p2_game_60m.snap` 60M steps on with no input.
- Uncommitted work left behind: none.

## Proven so far

- Boot path, crack patch (`$600` NOPs the `bne.w` at `$14a88` after the Zeus question) and deterministic drive:
  five anchors byte-identical over two cold boots (`drive.txt`; README "Boot path", "Drive recipe").
- Landscape is 64x64 4-byte cell records at `$3979e` with no corner grid; corners derive from (b0&7, b1) via `$36b7a`:
  4225/4225 shared corners, cells re-derive 4071/4071 by Populous 1's rule minus the shore codes, `$1f176`
  915/915 callcaps (`py/corners.py --callcap`; README "The landscape").
- No separate 65x65 grid in RAM: best 2875/4086 vs planted 4071 (`py/find_corner_grid.py --control`).
- `rand` `$215dc`: 32-bit LCG `$bb40e62d` on `$47382`, 50/50 (`py/rand_gate.py`).
- Main loop `$12524`, one tick per about 7 VBLs: 23 call targets at 29 calls in 200 VBLs (`tools/call_census.py`).
- Loader `$2cc98` + file table `$2cdb6`: 11 of 13 files at their table address (`py/fdc_files.py`).

## Running

Nothing running.

## Open, in priority order

1. Name the main-loop routines (README "Main loop" list): read each to its first branch, then `hits`/`callcap` from
   `p2_game_60m`; the entity update and the computer god are among them. Start with the walker array: find the
   writer of cell byte 3 (`tools/find_field_writers.py`, then `watch 3979e $4000` filtered to byte 3).
2. Drive a raise and a lower through the UI and compare with Populous's raise (`terrain.md` section 2): find the
   land-click hit test, then a same-snapshot click vs no-click A/B; gate `raise_point` `$1ec8c` under callcap.
3. Gate `gen_land` `$1ebee`: snapshot before the briefing's world build, model hill walk + raise in Python,
   compare the cell map byte for byte (Populous's `verify_gen.py` is the template); pin the walk's D4 stop rule.
4. Decrunch: port `$2246a` to Python and compare each `.PAK` against its RAM copy (QAZ.PAK's raw 32000 bytes too);
   then `BLOCKn`/`S16`/`S32` formats for `graphics.md`.
5. Cell bytes 0 bits 3-4 and byte 2 (`$f5`, `$70`): find their writers.

## Known traps

- The disk is MSA: `tools/msa2st.py` first; the game reads through its own FDC code, so `ATARI_TRACE_GEMDOS` goes
  silent after `pop2.tos` starts. Use `ATARI_TRACE_FDC=1` plus `py/fdc_files.py`.
- `mouse down`/`up` need the button (`mouse down l`); a bare `mouse down` is a REPL error and the run goes on.
- The pointer is not visible in every render (drawn into `$392dc` only when the hide count `$2246` is 0); read
  `$393fa`/`$393fc` instead of looking for it.

## Waiting on Dave

None.

## Next session

1. `/resume populous2`; check `p2_game_60m.snap` exists (else rerun `drive.txt`).
2. Open item 1: list the 23 per-tick routines' first instructions from `pop2_all.asm`, `hits` them over 2.4M steps,
   and find the entity array from the writer of cell byte 3.
3. Then open item 2 (raise/lower through the UI), keeping Populous's `terrain.md` section 2 beside it.
