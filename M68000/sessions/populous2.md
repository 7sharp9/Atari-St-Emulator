# Populous II: handoff

Updated 2026-11-20 by the session that ended at commit `a55faca` (fights, entity states, people on later battles,
world-name entry).

## Resume point

- Last commit of this workstream: `a55faca` populous2: fights are deterministic (rand drawn, unused ...).
- Working data: `M68000/scratchpad/populous2/` (`src/WILD29.MSA` from the Dropbox `WILD! #29.zip`, `wild29.st`,
  `files/`, `anchors/`, `pop2_1770.bin` the depacked image, `pop2_all.asm` the whole-image listing). Rebuild:
  `reversing/populous2/README.md` "Provenance" and "Drive recipe".
- Start from: `scratchpad/populous2/anchors/p2_game_start.snap` (battle 0's first play frames) or `p2_game_60m.snap`.
  Crowded later battles (fights, states `$a`..`$18`): `scratchpad/populous2/states/b445_start.snap` and
  `b775_start.snap` (rebuilt by `bash reversing/populous2/py/god/battle_census.sh <out> 1 445 775`), fight rounds
  `fight445.snap`/`fight775.snap` there (`py/gate_fight.sh` rebuilds them). Any battle by name:
  `py/name_entry.py NAME <out> --to-start`.
- Uncommitted work left behind: none. `uv run python tools/gates.py run populous2`: 13/13 PASS at `3baecef` (19:44,
  about 10 minutes, `claim_25168` 7 of them); the two gates added (`people_battles`, `fight_238dc`) and
  `people_22986` re-run on the edited script PASS on the files `a55faca` commits. `--dry-run`: 0 MISSING,
  0/15 gates declare no inputs (was 13/13 undeclared).

## Proven so far

Each line's detail and script are in `reversing/populous2/README.md` (section named) and `py/README.md`.

- Boot, crack patch, deterministic drive: five anchors byte-identical over two cold boots ("Boot path", "Drive recipe").
- Landscape: 64x64 4-byte cells, corners from (b0&7, b1) via `$36b7a`: 4225/4225, 4071/4071, `$1f176` 915/915;
  no 65x65 grid in RAM ("The landscape").
- `rand` `$215dc` 50/50; main loop `$12524`; loader `$2cc98` 11 of 13 files ("Random numbers", "Main loop", "Loader").
- Object heap and occupant lists 22/22, 31/31 ("Objects and entities").
- Raise/lower from a click to the cell map 76/76 ("Raise and lower"); `gen_land` 30/30 and scatters 30/30
  ("World generator").
- Computer god `ai_run_sides` `$25652` modelled: 1424/1424, 1000/1000, 498/498 ("The computer god").
- Land claim `$25168` 917/917 ("Settlement land claim").
- Conquest battle records decoded, plan sizes 8/8; god on battles 485 and 260 600/600, 300/300 ("Conquest battles").
- People placement `$22986`: 66/66 poked on battle 0, and unpoked 5/5 on battles 0, 290, 445, 690, 775 (pass 2,
  side-2 leader, flag at 16,16, entity array full: side 2 gets 199 of 200). Both sides take the same bit-0 cells,
  so on 290/445/775 every such cell starts with opposing walkers on it (7/26/105) (gate `people_battles`;
  "World generator", People placement).
- World-name entry driven: click the field, keys through `$22036`/table `$2208a`, `$2222c` match; UMHEAB's play
  start equals the title-poke `b10_start` on all game state; 1000 names all distinct ("Conquest battles";
  `py/name_entry.py`).
- Entity state table `$2311c` is 36 entries (states 0..`$46`), 25 handlers; census per battle; states 8, `$a`,
  `$c` (merge `$24752` / engage `$24934`), `$10`, the death `$242f8`, the end-of-battle test `$242b8` read
  ("Objects and entities", the other states; `py/state_census.sh`).
- Fights deterministic: state `$e` draws `rand` and discards it; damage = opponent byte 25 x (attacker strength /
  `$30af0`) + 10 each way: 16/16 and 16/16 per round, control 6/16, 5/16; whole fight to `$247e2` 5/5 twice
  (winner, strengths, 400 mana moved) (gate `fight_238dc`; "Objects and entities", Fights).

## Running

Nothing running.

## Open, in priority order

1. The end of a battle: `$242b8` calls `$14fb2` when a side's strength total +4 is 0. Drive a win (or poke one
   side's walkers away on a crowded battle) to see `$14fb2` run under `bp`, then read the battle-number step at
   `$15206..$15242` the README calls inferred. This unlocks the conquest's progression and a played second battle.
2. States `$12`, `$16`, `$18`/`$20` and `$24f3a` (state 2's test, which decides when a walker settles or meets):
   they run naturally from `states/b775_start.snap`; read each handler, then `callcap`/model the way the fight was
   (`fight_gate.py` is the pattern: stop at the handler under `bp`, poke, compare). Also why battle 290's shared-cell
   walkers never fight in 30M steps (state `$c` runs only on arrival at a cell, by the read).
3. The computer god's kinds 6 and `$a` in play: a battle whose side 2 can afford kind 6 (260 stayed short 300M
   steps), or a kind-`$a` battle where the leader outgrows the enemy's. Controller `$12` from the options screen.
4. Shape bit 0 of `$3697a`: every bit-0 code is level (mask `$f`) but codes 47, 63, 79.. are level without it;
   find what else reads bit 0 (`hits` census or whole-image scan for `$3697a`). The magnets as `$46f9a` type `$14`
   (`hits` on `ai_magnet_and_mode`).
5. Decrunch: port `$2246a`, compare each `.PAK` against its RAM copy; then `BLOCKn`/`S16`/`S32` for `graphics.md`.
6. Entity +13 bit 2 releases a walker group at a settlement's next state-6 expiry (`$236b8`): drive it as the player
   from `p2_game_60m` with a right click on (12,33) against a no-click control; model the share (`114(A2)`).
7. Cell byte 0 bits 3-7 (footfall; only `$2436e` writes) and its reader; the `$4505a` array (`$26644`); the reader
   of the byte map `$3d79e` the land claim fills.
8. The enemy-land quirk in play: a settlement next to enemy land taking it on its next claim tick.

## Known traps

- The disk is MSA: `tools/msa2st.py` first; the game reads through its own FDC code, so use `ATARI_TRACE_FDC=1` plus
  `py/fdc_files.py`, not GEMDOS tracing.
- `pop2_all.asm` is a linear sweep and loses sync after jump tables (`$2311c`, `$22bcc`, `$25b00`, `$1561a`): use
  `tools/disassemble.py --rom scratchpad/populous2/pop2_1770.bin --base 1770 --linear <addr> <n>` for bodies, and
  resolve a `jmp 2(PC,D0.w)` table as table address + word.
- The pointer is not visible in every render: read `$393fa`/`$393fc`. Briefing hotspots are text cells: read the
  layout at `$1c33a` (row stride `$1c340`+1, 8 pixels a cell) rather than guessing from a render (x 90 missed the
  name field, which starts at x 104).
- A later battle's number is read at the CONQUEST GAME click: poke `$473a0` on `p2_title`, never on the briefing; or
  type the name (`py/name_entry.py`). Read battle records from `p2_briefing` (`$47d28` holds other data later).
- `anchors/p2_gen_entry.snap` was made by an older DLL: `gen_entry.sh` on the current one stops 2,203 steps earlier
  (8,055,102 after `p2_briefing`) with the same game state; only stack bytes differ (`py/README.md`).
- `gates.toml` plain `expect` entries are `a/b` counts only; a sentence needs `re:` (`tools/gates.py` docstring).
- `py/god/god_gate.py --poke` addresses need `0x`. `stserver`'s `hits` counts a VBL taken at the address twice.

## Waiting on Dave

Nothing.

## Next session

1. `/resume populous2`; `uv run python tools/gates.py run populous2` should print 15/15 PASS (about 11 minutes).
2. Open item 1: from `states/b775_start.snap`, `bp 14fb2` with a long budget; if no side dies, poke one side's
   walkers' strength +26 to 1 on a crowded battle and run to `$14fb2`, then read it and `$15206`.
3. Then open item 2's state `$12` (399 runs on 775): read `$23a0a` (it gates on side record +12 = `$10` and calls
   `$24f3a`), model it with a `fight_gate.py`-style stop-and-poke harness.
