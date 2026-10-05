# Crude Buster (Data East 1990 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `b7c47d3` (plus the handoff commits).

## Resume point

- Last commit of this workstream: `b7c47d3` crudebuster: enemies of levels 3-5. Before it, in order: `9c7eed9` player, `4c80624` enemies 0-2, `a2d6644` world, `4540b20` sound, `1ba0b7c` graphics, `b1d86d3` architecture.
- Workspace: `M68000/reversing/crudebuster/` (`README.md` file index; `architecture.md`, `graphics.md`, `sound.md`, `world/world.md`, `player/player.md`, `enemies1/enemies1.md`, `enemies2/enemies2.md` with `grunts/`, `special34/`, `l5a/`, `l5b/`). Emulator and oracle: **MAME 0.289**, set `cbuster` (World FX) of the merged zip `~/mame-roms/cbuster.zip` (also holds `cbusterw`, `cbusterj`, `twocrude`, `twocrudea`; select with `CB_SET`).
- Working data (gitignored): `M68000/scratchpad/crudebuster/` (`rom/<set>_main.bin` decrypted program, `<set>_huc.bin`, `src/` MAME driver sources, `all_lin.txt` linear listing of `$0-$2d000`, `agents/*/out` logs of the seven agents, indexed in `scratchpad/ANCHORS.md`). Regenerate the dumps with the `dumprom.lua` line in `README.md`; `agents/` logs by the gates named below (about 200 MB, disposable).
- Start from: `lua/startlevel.lua` (`CB_LEVEL=0..5`, level starts about frame 720) or a cold boot with `lua/plans/play1.lua` (coin 600, start 700). Run through `cbmame.sh` only (never `mame` directly); own `CB_RUN` per parallel run.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's line rewrap in the working tree; its crudebuster row was committed through the index only.

## Proven so far

Detail in the docs; every count was re-run from the promoted paths this session except where a doc says "agent's number".

- Architecture (`architecture.md`, `py/kernel/gates.sh`): one real vector (IRQ4 `$b1e`), one logic step per VBL (1600 of 1600), three object pools (16 + 32 + 8 records, 80 + 84 + 44 type handlers), script lists `$6c000`/`$6d000` (6 levels, 32 of 32 entries matched), at most 5 script enemies (21 of 21), protection key/response pairs.
- Graphics (`graphics.md`, `gfx/proof.sh`): a Python renderer equals MAME on 1126 of 1126 frames, 215,915 of 215,915 sprite entries, layer A strips in all six levels. Levels 1 to 5 came through a poked level change.
- Sound (`sound.md`, `snd/`): HuC6280 disassembler equals MAME's (31,182 of 31,182), 94 `jsr $e1c` senders, command classes, sequencer grammar, OKI tables (542 of 542), patch formats (67 of 67, 29 of 29).
- World (`world/world.md`, `world/py/gates.sh`): attract table and demo streams (3798 of 3798 frames), clear sequence, scroll maps and lock rule, four text engines (every string in `strings.md`), pool B classes, pool C hit boxes and damage (16 of 16), flags named.
- Player (`player/player.md`, `player/py/gates.sh`): field map, 3-button moves, hit geometry (397 and 2628 tests, 0 disagreements), damage and score tables (83 of 83), lives/continue/timer, two players (35 checks PASS).
- Enemies (`enemies1/`, `enemies2/`): the shared engine contract, hit/damage/score rules, brain `$2438a`, levels 0-2 types and bosses (natural level 0 clear at frame 14882: 42 of 42 spawns), levels 3-5 types, bosses, final boss `0x48` and the ending, level-end writers (`$c86a`, `$ca6e`, `$20bd4`: 12 of 12; two re-runs identical).

## Open, in priority order

1. **Natural plays of levels 1, 2, 4 and 5.** The bots stall (level 1 roller fight, level 2 freeze after a jump, level 4 descent, a `0x35` soft lock at the level 3 wall). Without them levels 1 to 5 are known from lab spawns and poked states, the graphics renders of levels 1-5 are poked, and the boss fights of levels 1 and 2 were never played. Prove with a bot that clears each level from `startlevel.lua` (`player/lua/bot.lua` is the base; it needs the pick-up, ladder and hold-escape moves) and re-runs the render gate (`gfx/proof.sh`) and the census (`enemies*/py/census.py`) on the natural frames.
2. **Level 4 descent rule** (which `$81e12` phase lets the camera pass; `$1948` needs `$81e02` == 2) and the **hang** in level 4 (5 or more pool A records and the player at y >= `$210` loops between `$a7ec` and `$a85e`): reproduce by hand and write the rule.
3. **Unnamed or fingerprinted types**: pool A 15, 16, 23, 37, 52 and the read-only list of `enemies2.md` section 8; pool B 69-72, 74-79, 83 and unspawned types (`world.md` section 10); the per-distance probabilities of the shared brain `$2438a`. Prove by a lab spawn per type (`enemies1/lua/lab.lua`, `world/lua/forcespawn.lua`) with a count each.
4. **Sound ids to game events**: 16 of 94 sites were reached; `$a358` values 42 and 43 have no source; attract music (demo sounds on). Needs a play that reaches more sites (item 1).
5. **Graphics remainder**: layers B and C of levels 1, 2, 5 as static strips, room-map flag meanings (`$80400-$80402`), the actor animation lookup `$22540` against live frames (the first sprite-per-object proof).
6. **Read, not played**: Hard and Hardest damage tables (change the DIP), name entry, continue with a credit, the escape from an enemy hold (player action `$d`), thrown-enemy input (only a `+17` bit 6 poke is known), the ending (read; its timeline from `l5b`).
7. The other four sets (`cbusterw`, `cbusterj`, `twocrude`, `twocrudea`): program ROM differences (translation fixes; text in `strings.md` is the `cbuster` FX set's). Then a design digest or port plan in the README once 1 to 3 are done.

## Known traps

- `tools/rdis.py` misses everything behind the longword state tables of the type handlers; scan the raw image or `scratchpad/crudebuster/all_lin.txt` (regenerate: `tools/disassemble.py --rom scratchpad/crudebuster/rom/cbuster_main.bin --base 0 --all 0 2d000 > all_lin.txt`).
- Forcing the level-cleared flag (`$80040` bit 4) by poke hangs at the stage card unless the bit is cleared about 400 frames later; `startlevel.lua` replaces the level byte written at `$146e` instead (a write tap whose return value changes the data).
- Levels started with `startlevel.lua` above 0 leave spare lives at 0; edge-latched inputs are lost when a logic step spans 2 VBLs (press with an odd period); a write tap sees the Lua script's own pokes (filter pc `$bbe-$bd4`); writing `$80113` >= `$40` corrupts the tilemap.
- Pool C hit boxes live one frame: a census sampled at frame end never sees them; attribute damage to the owner's state. Damage is indexed by the pool C type, not the owner's type (`tables_decode.py`'s owner column was wrong).
- `-seconds_to_run` counts emulated time from machine start (a state loaded at frame 12000 needs `SECS` above 210); a state loaded under `-debug` resumes on a different trajectory.
- The `.sta` bytes are not stable across boots: compare RAM. `$80016` is shared by four scene runners; `$81e03` is cleared every frame and set by several types, not only the dispatcher.
- Monitor/`pgrep -f gates.sh` matches other agents' gates: wait on the output sentinel of your own run.
- The attract demo spawns pollute census columns of runs that continue past a game over (`world.md` section 10).

## Next session

Run `/resume crudebuster`. Item 1: build the natural-play bot from `player/lua/bot.lua` until levels 1, 2, 4 and 5 clear from `startlevel.lua`, saving a state at each level start and boss, then re-run the render gate and the census on those natural frames. Item 2 falls out of the level 4 run. Use agents for the type naming of item 3 only after the natural states exist (`/resume` brief: put addresses in `BRIEF.md`, not roles).
