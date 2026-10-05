# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `71a1fe4` (plus the handoff commit).

## Resume point

- Last commit of this workstream: `71a1fe4` finalfight: unread code read (pass 5: `py/objects/`, `py/engine/`, kernel/frame/placement/ai/boss/twoplayer/transitions/player doc edits).
  Before it: `17a59d3` (handoff), `25a0a25` (stage 0 played by a bot, pool 4 and DAMND, placement, transitions, two players), `4b2a1aa` (fighter AI and player mechanics).
- Workspace: `M68000/reversing/finalfight/` (`README.md` with the script index; docs `hardware.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`, `boss.md`, `placement.md`, `transitions.md`,
  `twoplayer.md`). The emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `ff_main.bin` (sha256 `8535dd51...e6ec`), `ff_z80.bin`, `src/` (MAME driver sources),
  the old states `ff_gameplay`, `ff_enemies`, `ff_kinds123`, **`stage/run/sta/ffightuc/sb_boss.sta`, `sb_s1.sta`, `sb_s6.sta`, `sb_s2.sta`** (regenerate with `py/stage/run.sh boss`, `stage1`, `chain.sh`)
  and the pass-5 poke states `engine/run/sta/ffightuc/p5b_bs7`, `p5b_k7`, `p5b_s5pre` (recipes in `py/engine/README.md`). `p4/` and `p5/` hold the agents' working directories (disposable, up to 600 MB each).
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). Not committed.
- Start from: `sb_s2` (stage 2 area 0, where the bot stalls) for item 1; `sb_boss` (frame 8298, camera `$aa0`, DAMND about to be allocated) for the first boss; `sb_s6` for the bonus stage and, with the
  `175`/`193(A5)` pokes of `py/engine/README.md`, bonus stage 7 and stage 5. Copy the `.sta` into the MAME run directory's `sta/ffightuc/`; load **without `-debug`**.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's line-rewrap in the working tree; do not stage it.

## Proven so far

Detail in the docs; every count is from a fresh run of the promoted gate. Earlier passes (hardware, kernel, TIME, pools, health, boxes, damage, the nine pool-2 fighter handlers, the player's states,
moves, items, score, continue scene; stage 0 by the bot, pool 4 and DAMND, the placement path, transitions, two players, Guy, Haggar, PvP) are in `README.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`,
`boss.md`, `placement.md`, `transitions.md`, `twoplayer.md`. Pass 5 (unread code, two agents, merged and gated from the promoted paths):

- **Two deferred rings** (`kernel.md`, `py/engine/gates.sh`, 16 of 16 gates). `324(A5)` is the **text and tile command ring** (producer `$2874`, 120 static callers, consumer the slot 11 idle loop `$4b5c`,
  13 types through `$4ba6`: text, typewriter, layer clears, tile strings, big-font strings); cold boot to frame 2300: 15 written, 15 consumed, 15 dispatched. **Sound is the ring at `388(A5)`**
  (pump `$984` on odd frames, one command per two frames): 26 queued / 26 latch writes cold, 321 of 321 queued sounds of a stage 0 play have a caller. Z80: id mod `$60` below `$f0`; n < `$40` is OKI
  phrase n+1 (64 of 64); `$40-$5f` YM2151 music or jingle; `$f0` stops all. Id names are by caller, not by ear.
- **Screen shaker** `$1b428` / pool 8 kind 3: 13 call sites (Haggar's two landings, the ANDORE family's entrances and aimed leap, DAMND and three more boss deaths, the ending scene); 13 displaced frames
  (4,3,3,2x6,1x4); rendered shift equals camera y two frames earlier in 35 of 35 frames for each of the three axes. Haggar's pile driver and slam damage are `$d9b6`/`$d9e2` (10 of 10 victim health values).
- **`$726e0` is the ROM region word** (0 Japan, 2 USA, 4 World; 26 read sites; the alternate script and placement sets differ in 2 DRUMCAN entries). **`$1fa5a` bits are invisible terrain codes**
  (code 5 pushes right, 3 pushes left; render identical in 4 of 4 frames; Cody held at `$1df` by a code-3 block).
- **Fire bottle and fire** (`ai.md`, `py/objects/gates.sh`, about 12 min): fire schedule 11/32/19/24 in 26 of 26 runs, 40 damage with reaction 8 in 7 of 7, box replay equals the observed hit frame 7 of 7;
  fighters are hurt by a separate 2-in-8-frame sampling (`$639e`, 8 of 8 phases); a punch deflects the bottle with no fire and +2,000 (5 of 5). Pool 6 kind 3 is EDI.E's gun bullet (40 damage, knockdown);
  kinds 3 and 4 can never be picked up (`74 != 0`, 4 of 4).
- **Pool 8, all 60 handlers have a role and creator** (`placement.md`): kind 0 is a palette-RAM animation (45 of 59 frames live, 0 hidden), `$1e`/`$1f` are ground shadows, elevator, subway, drip and hand-strap
  objects, the bonus-stage car board and tally objects. Kinds placed in stages 1 to 5: one live observation each.
- Props: DRUMCAN `$711a` 6 of 6 intro kicks, GLASS kind 12 `$7222`/`$7232` 12 of 12, bonus-2 car pane `$71a2` 2 of 2. Pool-4 kind 7 is a carrier (stage 2 area 0 clear), type 12 is the `$ffb228` lift actor
  (elevator 807 of 807 and 341 of 341 frames), type 16 has no entries. The EDI.E "reset" was `py/boss/dm.lua` zeroing `+78`; fixed, EDI.E dies normally (`$477bc`, shaker, no exception).

## Open, in priority order

1. **Stages 2 to 5 by play.** The bot stalls at stage 2 area 0 (cause not found: it stands still with a target set; lane direction and props are ruled out, `py/stage/README.md`). Debug with
   `FF_BOT_LANEFIX=1 FF_BOT_PROPS=1` from `sb_s2` and a `D` dump at the stall (`FF_BOT_DUMP`), or skip areas with the pokes in `transitions.md` (`297(A5)` = 1, `191(A5)` = 3). Then census each stage against
   `placement.md`, play the bosses of stages 1 to 5 (kinds 1, 3, 4, 5 of pool 4 do not behave when hand-spawned: they need the area's init data; EDI.E does), and the natural versions of everything pass 5
   could only poke: the kind 7 carrier at the stage 2 area 0 clear (`297` was poked, 2 of 2), pool 8 kinds `$d`, `$e`, `$2b` (flags poked), kind 8's barrier push, the stage 5 elevator scene.
2. **Still read-only**: terrain codes 6 to 38 and the lift lookup `$8a28`; the shaker sites `$426d8` (SODOM death), `$4d550` (ABIGAIL death), `$184b2` (ending); glass kinds 11, 13, 14; pool 8 kinds `$35`-`$3a`,
   `$13`, `$14`, `$33`, `$26`-`$29` (roles from partial reads); the fire against a pool-4 boss, a prop and player 2; the popped-bottle fire (`$3d0d2`) re-run; `$f1`-`$f6` and the silent ids `$4a $4b $4d-$4f $56 $59-$5c`
   (need the Z80 code); the look-back pairing of `$2874` and sound-wrapper callers is a heuristic (a few branch-reached sites may be mispaired).
3. **Paths no run took**: DAMND attack A2 and hit types 2, 4 to 8, grounded-death variants of every kind, thrown flight `$6c96`, entrance types 9 and 11 to 14, kind 2's guard slide, TWO.P's attack roll
   (21% observed against 44% expected), Haggar's chain-end back grab, PvP hard boxes and the `$78c6` clash.
4. **Re-run the `ai.md` gates on script-spawned records** of stage 0 (`py/stage` logs give the records; the gates start from `ff_enemies` spawns).
5. **Read the Z80 program** (control commands, music ids by ear), then **graphics** (decode a tile, commit a PNG), then Ghouls'n Ghosts only after 1 to 3.

## Known traps

- A web-fetch summary of a source file is a paraphrase from a small model: `curl` the raw file (`scratchpad/finalfight/src/`).
- A ROM zip's file name does not say which MAME set it is: find the set by CRC, then rename the copy.
- MAME on macOS grabs focus even with `-video none` unless `SDL_VIDEODRIVER=dummy`; all wrappers export it. Never launch `mame` directly from a Bash call.
- `-seconds_to_run` counts **emulated** seconds (6000 = 357,000 frames); `ffdrive.lua`'s `FF_STOP` defaults to 60,000 frames unless the wrapper raises it (`py/stage/run.sh` does).
- **A state loaded under `-debug` resumes on a different trajectory** from the same state without `-debug`. Cold boots are identical either way. Take breakpoint evidence from cold boots; run state-resume gates without `-debug`.
- Parallel MAME runs collide on a shared `run/`: every promoted script takes its own run directory from an environment variable (`FFS_RUN`, `FFD_RUN`, `FFT_RUN`, `BB_RUN`, `DM_*`, `FF_RUN`, `FFA_RUN`, `FFB_BASE`, ...).
- `FF_SAVE` (`lua/stagebot.lua`) writes the state into the run directory's `sta/ffightuc/`; a run that hits the frame limit is saved as `<prefix>stuck<stage>`.
- **`stagebot.lua` defaults are pinned to what `sb_boss` and `sb_s1` came from, and two of them are wrong**: a pool-4 record at hp 0 is alive (`FF_BOT_HP0=1`), and Up raises the lane word, the bot presses
  it the other way (`FF_BOT_LANEFIX=1`). Changing a default changes every downstream state and gate frame.
- **A hand-spawned record must keep what the game keeps across a free** (`+78` is the effect-group handle that `$3a52` reads): zeroing `+0..+191` made EDI.E take an address error at `$44fc` and look like a
  game reset for a whole pass. Spawn through the allocator logic, then diff the record against a natural one.
- Briefs that name a role mislead: the pass-5 brief called `$2874` a sound sender (from `kernel.md` slot 15, which was wrong) and `$f1ca` a scripted-scene block; both agents corrected it from the bodies.
- Lua `install_write_tap` handles must be held in a global; ranges must be [even, odd]; `screen:vpos()` does not exist; in `callcap.lua` use `CURPC`; debugger `b@(a6+n)` expressions read 0
  (A5-based addresses sign-extend): mask with `&ffffff`; inside a task `d@(sp)` is the supervisor stack, use `usp` for a task's return address.
- Inputs are levels read once per frame: hold several frames; test movement only after frame ~1700.
- A fighter dies at `+24 < 0`; hp 0 is alive (HOLLY WOOD, DAMND). A pool-4 boss that the bot ignores keeps the stage script paused for ever.
- Props (pool `$a`) have no ground-line copy at `+14`: use `+10`. Pool `$14` is 30 records of 64 bytes.
- `tools/rdis.py` sizes a dispatch table by its first word / 2 and goes out of sync over back-to-back tables (`$3d5b8`/`$3d5c6`, `$e8f8`): use `py/boss/rdis2.py` (`--end`) or hand roots.
- `py/ai_kind6/scripts.py` labels the stage and area of an entry wrongly where the parse follows a jump past an area's end; the table in `ai.md` is recomputed.
- A task's variable (`$ff1288`) keeps its last value after the task dies: read the TCB state first. The `.sta` file differs by one byte of device state between boots: compare RAM. System `python3`
  has no numpy: use `M68000/.venv/bin/python`. zsh does not word-split `$D`, and an unquoted `export A=.. B=$A/x` on one line expands `$A` before it is set.
- `py/engine/gates.py` and `py/objects/gates.sh` run 10 to 25 minutes and up to 12 MAME processes; run a subset by name (`gates.py shaker haggar`), after the batch that produces its logs (`gates.sh cold` for `drums`, `ring_live`).

## Next session

Run `/resume final_fight`. Item 1: find why the bot stalls at stage 2 area 0 (a `D` dump and a screenshot at the stall from `sb_s2`), or jump areas with the poke recipes, and play on to the bosses of
stages 1 to 5; check each against `boss.md` and `placement.md`, and turn pass 5's poked claims (carrier, `$d`/`$e`/`$2b`, kind 8 push) into natural ones on the way. Then item 2 where a play reaches it. Reading
the Z80 program is the next self-contained task if the bot work stalls. Do not start graphics or Ghouls'n Ghosts before 1 to 3.
