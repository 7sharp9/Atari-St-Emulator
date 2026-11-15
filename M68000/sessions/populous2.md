# Populous II: handoff

Updated 2026-11-15 by the session that ended at commit `31f1e70` (land claim, later conquest battles).

## Resume point

- Last commit of this workstream: `31f1e70` populous2: conquest battles from CONQUEST.PAK (the handoff's script fixes follow it).
- Working data: `M68000/scratchpad/populous2/` (`src/WILD29.MSA` from the Dropbox `WILD! #29.zip`, `wild29.st`,
  `files/`, `anchors/`, `pop2_1770.bin` the depacked image, `pop2_all.asm` the whole-image listing). Rebuild:
  `reversing/populous2/README.md` "Provenance" and "Drive recipe".
- Start from: `scratchpad/populous2/anchors/p2_game_start.snap` (first play frames, conquest battle 0 vs
  Epimetheus; sidecar remounts `wild29.st`), or `p2_game_60m.snap` 60M steps on with no input.
- Later battles: `bash reversing/populous2/py/god/battle_census.sh <out> 1 <N>...` writes `<out>/b<N>_start.snap`
  (battle N's first play frame, by a `$473a0` poke at `p2_title`); this pass's are in `scratchpad/populous2/battle/`
  (0, 10, 40, 100, 260, 285, 485, 635, plus 300M-step `b<N>_end.snap` for 10, 40, 100, 260, 285, 485, 635).
- Uncommitted work left behind: none. `uv run python tools/gates.py run populous2`: 13/13 PASS at `15a8272` with this
  pass's files (about 11 minutes; `claim_25168` takes 7 of them, rebuilding its corpus in `scratchpad/populous2/claim/`).
  Full-run outputs: the god model `scratchpad/populous2/god/run_all.out`, the claim (`claim_gate.py all`, 917 cases,
  12 minutes) `scratchpad/populous2/claim/all.out`, the battle runs `scratchpad/populous2/battle/*.out`.

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
  `$22cde` from the side's +112 power bytes; side 2's is empty on battle 0; later battles run kinds 0, 2, 4 and the magnet move unpoked (Conquest battles line,
  below); kinds 6 and `$a` have run only in poked states (README "The computer god").
- Cell codes `$2f`/`$3f` are side 1/side 2 settlement land, not rock: 13/13 settlements on their code, swapped
  0/13, unoccupied ones within 2 cells 28/28 (`py/owned_cells.py`); written by the land claim (next line).
- Land claim `claim_tick` `$25168` / `claim_land` `$251d8`: rings counted outward (ring 1 if the centre counts,
  ring 2 if all 9, ring 3 if all 25 and `$25368` clears it, then count 26), size `$2547e[count]`, other
  settlements in range demoted, shrink reset to `$0f`, footprint bytes into `$3d79e`; runs every 4th tick by
  record index, or at once for size 0 or a lowered own cell. Model equals `callcap` on all RAM and D0.w in
  917/917 (164 natural, 753 poked); controls 751..887/917 (`py/claim/claim_gate.py all`; gate `claim_25168`,
  367/367). The enemy-land `btst` reads a byte that is always 0, so enemy cells count and are taken (README
  "Settlement land claim").
- Conquest battles: `$22e8c` copies `CONQUEST.PAK` record battle/5 (250 bytes) to `$30470`, side records from it,
  seed from +182 plus (battle mod 5) x `$2d7`; the setup runs right after the CONQUEST GAME click, so the battle number
  is poked at the title. Plan sizes predicted 8/8 (`py/god/conquest_records.py`). Side 2 casts unpoked on later
  battles: kind 0 (10, 40, 100), kind 4 x 72 (485), kind 2 x 1 (285), magnet command 8 (260); god model 600/600
  (485) and 300/300 (260), radius control 99/100 (gate `battle_god`). Kind 8 is not in the power stage's entry table;
  kinds 6 and `$a` never entered. World names from `$22266` (battle 0 DOEGAC) (README "Conquest battles").
- People placement `place_people` `$22986`, the last pass of `build_world`: model equals `callcap` on every changed RAM
  byte (dead stack aside) in 66/66 cases, 30 poked seeds plus 36 poked side-record variants
  (`py/people/people_gate.py 30`, gate `people_22986`); controls 0/66 except no-leader 12/66 and no-second-pass 42/66
  (equal where the branch is unused). No `rand`: flags on (32,32), side 1 scans forward and side 2 backward for cells
  with shape bit 0; README "People placement".

## Running

Nothing running.

## Open, in priority order

1. Replace the battle-number poke with the game's own route: type a world name on the briefing (`$15632` reads the
   buffer `$1572e`; read how keys reach it, then type UMHEAB for battle 10 and compare its start with
   `battle_census.sh`'s `b10_start`). Then kinds 6 and `$a` in play: a battle whose side 2 has the mana for kind 6
   (battle 260 stayed short for 300M steps; try a run past it, or a record with a cheap kind-6 power), and a kind-`$a`
   battle where the leader outgrows the enemy's. Then the entity states beyond 2/4/6 (table `$2311c`), `$24f3a`
   (state 2's test) and `$24a92`: drive a walker into a settle or a fight so the other states run under `hits`.
   Controller `$12` from the options screen.
2. The per-battle side-record fields `place_people` reads: count `+90`, `+92` (strength, inferred), `+95`, `+97`,
   `+98`, `+100`, `+102`, flag position `+110`, copied by `$22c40` from the battle record (README "Conquest
   battles"). Run `py/people/people_gate.py`'s model on later battles' build: rebuild a `p2_gen_entry` for battle N
   (`py/gen_entry.sh` from a `p2_briefing` reached with the title poke) and compare unpoked; pick battles whose
   records give `+110` non-negative and counts other than 10 and 3 (extend `conquest_records.py` to list them: record bytes 0 and 20, 58 and 78). Also: shape bit 0 of `$3697a` as "flat land" (find another reader or `hits` census), and
   the two type-`$14` `$46f9a` records as the magnets (`hits` on `ai_magnet_and_mode`).
3. Decrunch: port `$2246a` to Python and compare each `.PAK` against its RAM copy (QAZ.PAK's raw 32000 bytes too);
   then `BLOCKn`/`S16`/`S32` formats for `graphics.md`.
4. Bit 2 of entity +13 releases a walker group at the settlement's next state-6 expiry (`$236b8`; seen once, strength
   411 to 293, after the computer's own command): drive it as the player from `p2_game_60m` with `click_ab.py`'s
   pointer on cell (12,33) and a right click against a no-click control, and model the share that leaves (`114(A2)`).
5. Cell byte 0 bits 3-7 (footfall count, only `$2436e` writes it in play): find its reader; and what the
   `$4505a` array holds (empty on both anchors; `$26644` updates it); and the reader of the byte map `$3d79e`
   the land claim fills (a building footprint by Populous's analogy, inferred).
6. Drive the enemy-land quirk in play: a settlement next to enemy land should take it on its next claim tick
   (`claim_gate.py`'s "enemy code" variants show it under `callcap` only).

## Known traps

- The disk is MSA: `tools/msa2st.py` first; the game reads through its own FDC code, so `ATARI_TRACE_GEMDOS` goes
  silent after `pop2.tos` starts. Use `ATARI_TRACE_FDC=1` plus `py/fdc_files.py`.
- `mouse down`/`up` need the button (`mouse down l`); a bare `mouse down` is a REPL error and the run goes on.
- `pop2_all.asm` is a linear sweep and loses sync after jump tables (`$2311c`, `$22bcc`, `$25b00`): use
  `tools/disassemble.py --rom scratchpad/populous2/pop2_1770.bin --base 1770 <lo> <hi>` for handler bodies, and
  resolve a `jmp 2(PC,D0.w)` table from the image words (base = the table address). `disassemble.py` ended the
  `$251d8` range at `$2526e`, mid-routine; the linear listing read on from there.
- The pointer is not visible in every render (drawn into `$392dc` only when the hide count `$2246` is 0); read
  `$393fa`/`$393fc` instead of looking for it.
- A later battle's number is read at the title's CONQUEST GAME click: poke `$473a0` on `p2_title`, never on the
  briefing (`py/god/battle_census.sh`). The buffer `$47d28` holds `CONQUEST.PAK` at `p2_briefing` but other
  data by `p2_game_start` (fourteen of the file table's 29 records load there): read battle records from `p2_briefing`.
- `py/god/god_gate.py --poke` addresses need `0x`: a bare `47118` is decimal and pokes `$b80e`.
- `stserver`'s `hits` counted `$25bf4` twice when the VBL was taken exactly there (tick 808 of the side-1 arm:
  `$25bf4`, `$2aa4e`, `$25bf4`; 385 against the model's 384, `py/god/god_hits.py`). The REPL census was not tried.

## Waiting on Dave

Nothing.

## Next session

1. `/resume populous2`; `uv run python tools/gates.py run populous2` should print 13/13 PASS (about 11 minutes).
2. Open item 2: list the records' `+90`/`+110` with `conquest_records.py`, rebuild a gen-entry snapshot for two or three
   battles with other values (title poke to the briefing, then `py/gen_entry.sh`'s click and `bp 1ebee`; the script
   hard-codes `p2_briefing` and its output path, so give it arguments first) and run the people model on them.
3. Then open item 1's world-name entry (read how keys reach `$1572e`).
