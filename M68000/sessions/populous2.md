# Populous II: handoff

Updated 2026-11-13 by the session that ended at commit `cbe35b2`.

## Resume point

- Last commit of this workstream: `cbe35b2` populous2: gen_land byte for byte.
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
- Object heap (scenery `$3f42a`, entities `$3ff1a` 400 x `$34`, `$4505a`, `$46f9a`) with one occupant list per cell
  (cell word 2): 22/22 and 31/31 live records linked at their own cell, low-byte control breaks all (`py/walkers.py`;
  README "Objects and entities").
- `update_entities` `$2309a`: state dispatch on +22 via `$2311c`; over 29 ticks 522 = 18 x 29 first dispatches,
  states 6/2/4 counted to the call (`py/entity_states.sh`). `update_scenery` `$1fcce` read.
- Raise/lower: left/right click → command 2/4 in the record `$473b0` → `cmd_raise` `$1f6ce` / `cmd_lower` `$1f6a0`
  → `raise_point` `$1ec8c` / `lower_point` `$1eed4` (Populous's rule, order N..NW, write after recursion);
  76/76 grid, mana and re-derive on both anchors (`py/raise_gate.py`), click A/B 16 and 1 corners equal to the
  model (`py/click_ab.py`). Lower on your own settlement sets entity +13 bit 2 and charges 20 x stale `$3962c`.
  All six gates in `gates.toml` pass (`tools/gates.py run populous2`).
- `gen_land` `$1ebee` byte for byte: 30/30 seeds, cell map plus seed and counters (`py/gen_gate.py` on
  `anchors/p2_gen_entry.snap`, rebuilt by `py/gen_entry.sh`); walk stops at a rejected corner or height 8;
  controls 16/30 (stop at 6) and 0/30 (write before recursion). README "World generator".

## Running

Nothing running.

## Open, in priority order

1. Name the rest of the main-loop routines (README "Main loop"): `$25652` and `$27faa` (both read the side records
   `$470fe`), `$29c7e`, `$29226` (`$473b0` array), `$2a0b2`, `$2d4c8`, `$136ba`/`$14158` (current player's side record).
   The computer god is likely among them. Then the entity states beyond 2/4/6 (table `$2311c`) and `$24f3a`
   (state 2's test), `$24a92`; drive a walker into a settle or a fight so the other states run under `hits`.
2. Model the rest of the world build `build_world` `$22942` after `gen_land`: the scatter passes `$1f870` and
   `$1fa6c` (rock `$2f`/`$3f` on 10 flat cells for the natural seed; scenery records too?) and `$22986` (people).
   Start from `p2_gen_entry`, `bp 2294e` (after gen_land) then callcap each pass; compare cells and the
   `$3f42a`/`$3ff1a` arrays against `p2_zeus`.
3. Decrunch: port `$2246a` to Python and compare each `.PAK` against its RAM copy (QAZ.PAK's raw 32000 bytes too);
   then `BLOCKn`/`S16`/`S32` formats for `graphics.md`.
4. What bit 2 of entity +13 does (set by a lower on your own settlement; state 2 tests bit 1): drive it from
   `p2_game_60m` with `click_ab.py`'s pointer on cell (12,33) and a right click, then `hits` the entity states.
5. Cell byte 0 bits 3-7 (footfall count, only `$2436e` writes it in play): find its reader; and what the
   `$4505a` array holds (empty on both anchors; `$26644` updates it).

## Known traps

- The disk is MSA: `tools/msa2st.py` first; the game reads through its own FDC code, so `ATARI_TRACE_GEMDOS` goes
  silent after `pop2.tos` starts. Use `ATARI_TRACE_FDC=1` plus `py/fdc_files.py`.
- `mouse down`/`up` need the button (`mouse down l`); a bare `mouse down` is a REPL error and the run goes on.
- REPL `bt` crashes the emulator (unhandled AddressError in `Backtrace`, `Program.fs:1649`) when A6 is odd, as it is
  inside `$2436e` (A6 = `$2558b`): read the stack with `m <A7> 40` instead.
- `pop2_all.asm` is a linear sweep and loses sync after jump tables (`$2311c`): use
  `tools/disassemble.py --rom scratchpad/populous2/pop2_1770.bin --base 1770 <lo> <hi>` for handler bodies.
- The pointer is not visible in every render (drawn into `$392dc` only when the hide count `$2246` is 0); read
  `$393fa`/`$393fc` instead of looking for it.

## Waiting on Dave

None.

## Next session

1. `/resume populous2`; `uv run python tools/gates.py run populous2` should print 6/6 PASS.
2. Open item 2: the scatter passes `$1f870`/`$1fa6c` and the people placement `$22986`, to finish the world build.
3. Then open item 1's remaining main-loop routines (`$25652`, which writes commands 2 and 4 itself, is the
   likeliest computer-god routine).
