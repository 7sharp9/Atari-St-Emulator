# Midwinter: handoff

Updated 2026-10-31 by the session that ended at the handoff commit after `4d29cbe` (recruitment).

## Resume point

- Last commit of this workstream: `4d29cbe` (recruitment, `ai.md` section 8).
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`, which does not list `sabotage/`,
  `shot/` or `recruit/` yet: another session holds uncommitted edits to it). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`), then `py/sabotage/drive_sabotage.sh` (15 min) and `py/recruit/drive_recruit.sh`
  (1 min) for the driven snapshots.
- Start from: `d_team.snap` (The Team, 08:00); `d_stark.snap` (Stark's bio); `d_decisions.snap` (Decisions, flags
  `$3f`); `d_ski.snap` (3D view, unit 27 engaged); `recruit/r3_screen.snap` (RESISTANCE with Rudzinski present).
  Every resume needs `--disk-a scratchpad/midwinter/zuul067.st`.
- Uncommitted work left behind: none of this workstream (`scratchpad/ANCHORS.md`, root `Cadaver/` and the other
  games' files are other sessions').

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`); architecture skeleton with census counts (`architecture.md`).
- Terrain (`terrain.md`): `py/terrain/gate_terrain.py` 70000/70000 cells, post-passes 10000/10000.
- Character records (`ai.md` 1): Stark's 14 bio ratings 14/14.
- Enemy army (`ai.md` 2): `py/army/gate_army.py` ticks 42/42 and 9/9, supply 10/10, chained 1000/1000 and 284/284.
- Encounters and losses (`ai.md` 3): `py/army/gate_encounter.py` search 96/96, frames 9600/9600, kills 512/512.
- Attacks on the player (`ai.md` 4): `py/attack/gate_attack.py` launches 768/768 x2, odds 1452/1452, bomb 1494/1494.
- Period end and endings (`ai.md` 5): `py/army/gate_period.py` 6/6, 200/200 per routine, the report 14/14.
- The player's weapons and the kill (`ai.md` 6): `py/attack/gate_shot.py`, `drive_kill.py`.
- Sabotage (`ai.md` 7): `py/sabotage/gate_sabotage.py` clicks 1500/1500, blast 100/100 per type, driven legs.
- Recruitment (`ai.md` 8): `py/recruit/gate_recruit.py` presence, offer, radio offer, answer 500/500 each, radio pick
  427/427, seven controls fail; `py/recruit/drive_recruit.sh` a driven join of Rudzinski against a one-byte refusal
  control. Every `$2b16c` writer listed (18 `lea` sites).
- All eight gates: `uv run python tools/gates.py run midwinter`. The design digest covers all.

## Running

Nothing running.

## Open, in priority order

1. **3D pipeline**: `$18304` -> `$16d9c`, draw list `$19ce2`/`$1d5a6`, polygon fill; proof by rendering a frame
   pixel for pixel. Unlocks matching encounter slots to on-screen objects and the sniping pick `$19ec4`.
2. **Combat and sabotage leftovers** (`ai.md` Open): a driven sniping kill ('S' at speed 0, `$131d8`, then Space,
   reusing `drive_kill.py`); an ordinary vehicle's kill; the glider shot `$20be6`; the surrender screen `$1137a`.
3. **Recruitment leftovers** (`ai.md` Open): drive Kristiansen's radio (poke 12 as current, in the team, inside a
   Radio Station; `$f94c` from Decisions, check the team against `radio_pick`); name `$2553c`; the k = 20 screen
   `$5c84`; the S.O.S icon `$5784` (sets record +0 bit 2, `$f76e`).
4. Leftovers: character +72's name, `$13f28`, `$14774`, record +0 bits 2 and 7, travel mode 1, the Bomber's drop and
   the missile's detonation; `$2bb2e`, node names; terrain leftovers.

## Known traps

- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- Options and character-screen snapshots catch the pointer mid-redraw: compare with a 34-pixel tolerance.
- A `u <addr>` into the menu stops inside its packer stub: the drive pokes after a fixed `s 60000000`.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`; the bytes before `$ec8c` are data. Use `--linear`.
- `stserver`'s `mouse` click does not register here: click in the REPL, `u <routine>`, `snap`, load in `stserver`.
- The army moves only at a situation report.
- From `d_ski.snap` a missile hits at frame 170: bound natural 3D runs below that, or set TRAINING `$2c180`.
- Unit coordinates are twice the terrain target's (`$19cd4`).
- `$cbbe`'s kill ends in the radio message `$d048`, which waits for a key: `stops=[0xcd6e]` under `call`.
- `$f374` loops 65536 times on a record with kind `$80`: never poke one.
- Decisions offers nothing once the character's clock +32 has reached the game clock, or with +15 at 0.
- `tables/action_tables.txt` has two mispaired rows: confirm a pairing from a live snapshot.
- Absolute addresses in `$2c376..$2c47f` are `A6` fields: `$2c3d6` is `96(A6)`, the current character (a gate
  that randomised it as a separate "capper" changed the asker). Check `addr - $2c376` before treating one as its own
  variable.
- Positions poked alone leave the presence list `$22da6` stale: select the character (bio arrow `$3024`) so `$12be`
  rebuilds it (`py/recruit/dnext.txt`).
- `$70000` is the game's scratch list (`$fab4`): put a gate's scratch tables elsewhere (`$71000`).
- The bio's mouse is 1:1 and icon rows are `(3, icon, x, y)` after a count word; the pointer is at `$24fa2`/`$24fa6`.

## Waiting on Dave

Nothing.

## Next session

`/resume midwinter`. Item 1 (the 3D pipeline) is the largest remaining unknown. For a shorter task, item 2's sniping
kill reuses `drive_kill.py`, or item 3's radio drive reuses `py/recruit/` (poke Kristiansen into the team and a Radio
Station on `d_stark.snap`, select him with the bio arrow, then Decisions).
