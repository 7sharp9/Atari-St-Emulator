# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `4b2a1aa` (plus the handoff commit).

## Resume point

- Last commit of this workstream: `4b2a1aa` finalfight: fighter AI (`ai.md`, kinds 0 to 8) and player mechanics (`player.md`) read and proven live,
  scripts promoted to `py/ai_kind0/`, `py/ai_kind123/`, `py/ai_kind45/`, `py/ai_kind6/`, `py/ai_kind78/`, `py/player/`. Separate commits: `27d459f`
  `tools/rdis.py` (recursive-descent lister), `7544589` the one-line `CLAUDE.md` rule about it.
- Workspace: `M68000/reversing/finalfight/` (`README.md` with the script index, `hardware.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`,
  `ffmame.sh`, `ffrun.sh`, `lua/`, `py/`). The emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`, which is tracked): `ff_main.bin` (sha256
  `8535dd51...e6ec`), `ff_z80.bin`, `src/`, the states `ff_gameplay.sta`, `ff_enemies.sta`, `ff_kinds123.sta`, and under `p3/`: `BRIEF.md`, each agent's
  directory with its `report_*.md`, saved states (`d/states/k6_*.sta`, `c/run_promoted/sta/ffightuc/p3c_*.sta`, `e/ff_k8.sta`) and the corpora named in
  ANCHORS. The `p3/<letter>/out*` and `run*` directories are disposable logs (several hundred MB).
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). Not committed.
- Start from: `ff_enemies` (stage 1, frame 4150, five enemies) for anything stage-1; `ff_kinds123` (frame 4300, ANDORE, SLASH, AXL, TWO.P, J next to
  Cody, stage script parked) for kinds 1 to 3. Copy the `.sta` into the MAME run directory's `sta/ffightuc/` and start with `FF_LOAD=<name>`.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's line-rewrap in the working tree; do not stage it.

## Proven so far

Detail in `reversing/finalfight/` docs; every count below is from a fresh run of the promoted script.

- Hardware, task kernel, TIME, object pools, health, hit and hurt boxes, damage chain: earlier passes (`README.md`, `kernel.md`, `frame.md`).
- **The nine pool-2 fighter handlers** (`ai.md`): kind 0 BRED, DUG, JAKE, SIMONS; 1 J, TWO.P; 2 AXL, SLASH; 3 ANDORE Jr., ANDORE, G., U., F.ANDORE; 4 G.ORIBER,
  BILL BULL, WONG WHO; 5 HOLLY WOOD, EL GADO; 6 ROXY, POISON; 7 an invisible placeholder; 8 the fire-bottle thrower. Names from the game's own HUD text
  (`$5b640`, `$5b6fc`; HUD name object 9/9 and 5/5). State tables, decision logic, attack scripts and damage rows per kind, shared helpers.
- Target rule (nearest by |dx|, ties to P2; `$3068`, `$280c8`: 8/8 with a cloned P2), formation slots and attack tokens (`$ff1154`, `$ff115a` equal the record
  counts 8450/8450), the LFSR `$3c26` (505/505), damage equals the ROM table byte (kind 0 59/59, kinds 1 to 3 98/98, kinds 4 and 5 151/151, kind 6 85/85),
  spawn caps `$3e88` (16/16), difficulty rank `168(A5)` +1 per 600 frames (steps at 4677, 5277, 5877 in 3 of 4 runs).
- Score award ring `516(A5)`: `$288c` queues, `$4b00-$4b5c` pops into the BCD add `$1a22`; kill awards by fighter (`ai.md` "Score"; Dug +1200 in the same
  frame, 1/1 each for kinds 4 to 6).
- **The player** (`player.md`): states 0, 2, 4, 6, 8, 10, 12 (not 0 to 6), the `$a7a6` sub-states, Cody's move set with the attack-box catalogue, grapple, throws,
  items (24/24), weapons (3/3), props and the drop rule, extra life at 100,000, the continue scene (`$5da78`), per-character tables for Guy and Haggar (ROM
  only). 19 of 19 gates in `py/player/gates.sh`.
- Corrections to earlier docs, all in place: `$288c` is a score ring; the damage byte is `byte[92 + word(box +8)]` with the variant already in `92`; the live
  stage script is `$5f7e` through `$5e36 -> $5e84 -> $5ee6`; `+20` is the character byte and `+21` the entrance type; `$c840` is player state 12, not the continue screen;
  `$3f7a` is the thrown-fighter landing damage.

## Open, in priority order

1. **Play a stage instead of spawning into `ff_enemies`.** Every live check ran on `ff_enemies` or on records spawned through the real allocator or script engine; no run
   reached a boss by play. Extend `lua/plans/plan3.lua` to camera x `$aa0` (stage 0 area 2, the kind 4 and 6 group at `$707a0`), then into stage 2; census with
   `py/poolcensus.py` and rerun the `ai.md` gates on script-spawned records. This reaches pools 4 and `$14`, pool 8's other kinds, the kind 4 stage entries, the
   kind 7 scroll-lock reading (stage 5 area 0 at camera `$1280`: watch `278(A5)` and the script pointer) and the unnamed tag-`$a` props.
2. **Two players and the other characters.** Drive player 2 through `$ff8000+94`, and Guy and Haggar by poking `+20`, `+56`, `+92` from table `$a124` on a saved state.
   Proves the two-player spawn flag (script byte 15), the two-player cap tables, Guy's wall jump and Haggar's moves, and the player-versus-player path `$7766-$7920`.
3. **Unread code**: the fire bottle `$5957a` and fire prop `$54b4a` (described from logs only), `$6026`/`$61e24`/`$6241e`, the tag-`$a` victim handlers
   `$711a`, `$71a2`, `$7222-$7232`, the enemy-bar ring producer, the player state 8, 10 and 12 scripts, the `324(A5)` command ring (written by `$2874`, dispatched
   through the long table at `$4ba6` by each word's high byte). Method as in `frame.md`: read to the first branch, grep the docs, write-tap the field.
4. **Paths no run took** (each section of `ai.md` lists its own): the grounded-death variant (`+2 = 4, +3 = 2`) of every kind, thrown flight and `$6c96`, hit types 4 to 8 on
   the fighters, entrance types 9 and 11 to 14, kind 2's guard slide (the terrain probe undid it in the test arena), TWO.P's attack roll (21% observed against 44% expected,
   cause not found). Poke `63(A6)` and the sub-state, or place a prop or a second fighter in the line.
5. **The sound queue and the Z80**: tap `$800180`/`$800188`, match to the ring at `388(A5)`, then read the Z80. **Graphics**: decode one known tile, render a sheet, commit the PNG.
   Then Ghouls'n Ghosts (is Capcom's object engine shared?) only after items 1 to 3.

## Known traps

- A web-fetch summary of a source file is a paraphrase from a small model (it gave the wrong CPS-B row): `curl` the raw file (`scratchpad/finalfight/src/`).
- A ROM zip's file name does not say which MAME set it is: find the set by CRC (`mame -listxml | awk ...`), then rename the copy.
- MAME on macOS grabs focus even with `-video none` unless `SDL_VIDEODRIVER=dummy` is set; all wrappers export it. Never launch `mame` directly from a Bash call.
- Parallel MAME runs collide on a shared `run/` (cfg, nvram, states): every promoted script takes its own run directory from an environment variable (`FF_RUN`, `AI123_RUN`,
  `AI45_RUN`, `K6_RUN_DIR`, `FF_E_RUN`, `FFP_RUN`). Six at once ran fine.
- Lua `install_write_tap` handles must be held in a global; `screen:vpos()` does not exist in 0.289; in `callcap.lua` use `CURPC`, not `PC`; a tap callback that errors prints `LUA ERROR`.
- Inputs are levels read once per frame: hold several frames; test movement only after frame ~1700. `ff_enemies` starts Cody in grapple mode (`66 = 2`) with a dead partner: poke
  `+64`, `+66`, `+3`, `+4` before driving him.
- **`92(A6)` after `$2fa2` is `base + $60 + level`**, not the character record: the census names keyed by it (`$23f8c` BRED ...) hold only at the rank the fighter spawned with. The
  record is `base` (health words), `base + 64` (defence class), `base + $60` (damage rows). The player table `$a124` is ordered Guy, Cody, Haggar: entry 1 is Cody.
- **Linear listings lie over handlers that interleave tables and animation data**: `$389b8` is not an instruction line in `scratchpad/finalfight/p3/fighters.asm`. Use `tools/rdis.py`.
- **Spawning a fighter from Lua**: copy the allocator `$3892` (pop `20242(A5)`, zero `+0..+127` **except `+78`**, the effect-group handle `$3a1c` keeps; zeroing it makes the first hit spark
  fault into the boot RAM test), bump the `$3e88` counter, and zero the token word `$ff115a` with the counters, or the caps starve. The stage script spawns extra enemies later
  (frames 4161 and 5806 in the `ff_enemies` continuation): park it (`FF_NOSCRIPT`) or orphan the live records for a clean arena.
- `py/ai_kind6/scripts.py` labels the stage and area of an entry wrongly where the parse follows a jump past an area's end; the entry addresses and fields are right, the table in `ai.md` is recomputed.
- A task's variable (`$ff1288`) keeps its last value after the task dies: read the TCB state first. `py/jt.py` takes the address of the `move.w` of a dispatch, not the routine start.
- The `.sta` file differs by one byte of device state between boots: compare RAM. System `python3` has no numpy: use `M68000/.venv/bin/python` where a script needs it.
- zsh does not word-split `$D`: use a shell function for repeated `disassemble.py` arguments.

## Next session

Run `/resume final_fight`. Item 1: extend `plans/plan3.lua` to play to the stage-0 boss group (camera x `$aa0`), save a state, and census the script-spawned records against
`ai.md`; that also closes most of item 4's stage-only questions. Then item 3's unread code with one agent per area (bottle and fire, `$6026`/`$61e24`, the PvP path), briefed
with `DEVELOPING.md` "Other tools" and `tools/rdis.py`. Item 2 (player 2, Guy, Haggar) is a second drive on the same states. Do not start graphics or Ghouls'n Ghosts before 1 to 3.
