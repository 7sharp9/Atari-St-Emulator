# Populous II: handoff

Updated 2026-11-14 by an overseer session that promoted a subagent's computer-god model (commit `6d78094`).

## Resume point

- Last commit of this workstream: `6d78094` populous2: the computer god as a model, 10 gates.
- Working data: `M68000/scratchpad/populous2/` (`src/WILD29.MSA` from the Dropbox `WILD! #29.zip`, `wild29.st`,
  `files/`, `anchors/`, `pop2_1770.bin` the depacked image, `pop2_all.asm` the whole-image listing). Rebuild:
  `reversing/populous2/README.md` "Provenance" and "Drive recipe".
- Start from: `scratchpad/populous2/anchors/p2_game_start.snap` (first play frames, conquest battle 0 vs
  Epimetheus; sidecar remounts `wild29.st`), or `p2_game_60m.snap` 60M steps on with no input.
- Uncommitted work left behind: none. `uv run python tools/gates.py run populous2`: 10/10 PASS at `6d78094`. The
  first god pass's listings are in `scratchpad/populous2/agents/god/`; the model's full-run output is
  `scratchpad/populous2/god/run_all.out`.

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
- `gen_land` `$1ebee` byte for byte: 30/30 seeds, cell map plus seed and counters (`py/gen_gate.py` on
  `anchors/p2_gen_entry.snap`, rebuilt by `py/gen_entry.sh`); walk stops at a rejected corner or height 8;
  controls 16/30 (stop at 6) and 0/30 (write before recursion). README "World generator".
- Scenery scatters `$1f870` (trees, type `$16`) and `$1fa6c` (type `$18`): 30/30 each against the model
  (`py/scatter_gate.py`); `$1f870`'s attempt bonus reads byte `$3f6a9` through the stale D2 `$ff9d`, proven with
  the byte poked (30/30, no-bonus control 0/30).
- The computer god is `ai_run_sides` `$25652`: one command a tick into the mouse's command record, human skipped by
  side record +26 (2 human, 4 computer); computer branch 143 / 0 / 268 over 12M steps unpoked / side 2 human / side 1
  computer, every executed command one of its posts (`py/god_census.sh`, gate `god_census`; README "The computer
  god"). Its cascade is modelled (next line).
- The god as a literal port, `py/god/god_model.py`: its changed-byte set equals `callcap` of `$25652` on 1424/1424
  unpoked ticks, 1000/1000 with side 1 switched to computer (one poke, the controller word `$47118`), and 498/498
  labelled poked stage variants; broken controls 0/400, 211/400, 493/498, 488/498
  (`bash reversing/populous2/py/god/run_all.sh`, 60 to 70 minutes; the short form is gate `god_model`,
  `py/god/gate_short.sh`). Side 1's reload word +104 is 0, so its cascade runs every tick; plan lists are built by
  `$22cde` from the side's +112 power bytes; side 2's is empty on battle 0. Power kinds 2, 4, 6, 8 and the magnet
  move onto the enemy's oldest settlement have run only in poked states (README "The computer god").
- Cell codes `$2f`/`$3f` are side 1/side 2 settlement land, not rock: 13/13 settlements on their code, swapped
  0/13, unoccupied ones within 2 cells 28/28 (`py/owned_cells.py`); written by `$25298` in `$25168` (state 6).

## Running

Nothing running.

## Open, in priority order

1. The computer god in a later battle (README "The computer god"): side 2's plan list is empty on battle 0, and
   poking the battle number `$473a0` to 10, 40 or 100 before the briefing click changed nothing. Read how `$22ec0`
   fills the +112 power bytes from `$47d3e`/`$47d78`, reach a later battle through the conquest map, and `hits`
   census `$25a32` and `$25b5e` there; that also runs power kinds 2, 4, 6, 8 and the magnet move unpoked. Drive
   controller `$12` from the options screen. Then the entity states beyond 2/4/6 (table `$2311c`) and `$24f3a`
   (state 2's test), `$24a92`; drive a walker into a settle or a fight so the other states run under `hits`.
2. People placement `$22986` (last pass of `build_world`): from `build/c_22986.snap` callcap it and model the
   entity, `$46f9a` and side-record writes (listed by diffing `c_22986` and `d_after`).
3. Settlement land claim `$25168`/`$25298`: radius against settlement size byte 1 (`owned_cells.py` gives the cells).
4. Decrunch: port `$2246a` to Python and compare each `.PAK` against its RAM copy (QAZ.PAK's raw 32000 bytes too);
   then `BLOCKn`/`S16`/`S32` formats for `graphics.md`.
5. Bit 2 of entity +13 releases a walker group at the settlement's next state-6 expiry (`$236b8`; seen once, strength
   411 to 293, after the computer's own command): drive it as the player from `p2_game_60m` with `click_ab.py`'s
   pointer on cell (12,33) and a right click against a no-click control, and model the share that leaves (`114(A2)`).
6. Cell byte 0 bits 3-7 (footfall count, only `$2436e` writes it in play): find its reader; and what the
   `$4505a` array holds (empty on both anchors; `$26644` updates it).

## Known traps

- The disk is MSA: `tools/msa2st.py` first; the game reads through its own FDC code, so `ATARI_TRACE_GEMDOS` goes
  silent after `pop2.tos` starts. Use `ATARI_TRACE_FDC=1` plus `py/fdc_files.py`.
- `mouse down`/`up` need the button (`mouse down l`); a bare `mouse down` is a REPL error and the run goes on.
- REPL `bt` crashes the emulator (fix `a85441e` on branch `claude/modest-dirac-449d9c`, not merged) (unhandled AddressError in `Backtrace`, `Program.fs:1649`) when A6 is odd, as it is
  inside `$2436e` (A6 = `$2558b`): read the stack with `m <A7> 40` instead.
- `pop2_all.asm` is a linear sweep and loses sync after jump tables (`$2311c`): use
  `tools/disassemble.py --rom scratchpad/populous2/pop2_1770.bin --base 1770 <lo> <hi>` for handler bodies.
- The pointer is not visible in every render (drawn into `$392dc` only when the hide count `$2246` is 0); read
  `$393fa`/`$393fc` instead of looking for it.
- `py/god/god_gate.py --poke` addresses need `0x`: a bare `47118` is decimal and pokes `$b80e`.
- `stserver`'s `hits` counted `$25bf4` twice when the VBL was taken exactly there (tick 808 of the side-1 arm:
  `$25bf4`, `$2aa4e`, `$25bf4`; 385 against the model's 384, `py/god/god_hits.py`). The REPL census was not tried.

## Waiting on Dave

- Whether to merge the `bt` fix branch `refs/heads/claude/modest-dirac-449d9c` (session "Fix REPL bt crash on odd A6",
  cut from `8222db3`; it reports the net and gates passing and was re-running them against master). Not needed here.

## Next session

1. `/resume populous2`; `uv run python tools/gates.py run populous2` should print 10/10 PASS.
2. Open item 2 (`$22986` people placement), which finishes the world build; then item 3 (land claim).
3. Then open item 1: a later battle where side 2's plan list is not empty.
