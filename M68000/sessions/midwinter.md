# Midwinter: handoff

Updated 2026-10-27 by the session that ended at the handoff commit after `53b4b97` (the player's weapons and
sabotage).

## Resume point

- Last commit of this workstream: `53b4b97` (the player's weapons and sabotage proven); the lessons and this handoff
  follow it.
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`, which does not list the new
  `sabotage/` and `shot/` dirs yet: another session holds uncommitted edits to it). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`), then `py/sabotage/drive_sabotage.sh` (15 min) for the sabotage snapshots.
- Start from: `d_team.snap` (The Team, 08:00) for turn-level and recruitment work; `d_stark.snap` (Stark's bio) for
  the bio icons; `d_ski.snap` (3D view, unit 27 in the window, slot 0 engaged) for combat;
  `sabotage/s4_sab.snap` (PLANT EXPLOSIVES at node 74). Every resume needs
  `--disk-a scratchpad/midwinter/zuul067.st`.
- Uncommitted work left behind: none of this workstream (`scratchpad/ANCHORS.md` and the root `Cadaver/` are another
  session's). The two agents' working dirs `scratchpad/midwinter/agents/shot/` and `agents/sabotage/` hold their
  reports (`report.md`) and probes; the promoted copies are in `py/attack/` and `py/sabotage/`.

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`); architecture skeleton with census counts (`architecture.md`).
- Terrain (`terrain.md`): `py/terrain/gate_terrain.py` 70000/70000 cells, post-passes 10000/10000.
- Character records (`ai.md` 1): Stark's 14 bio ratings 14/14; +60 explosives, +63/+64 the building, +65..+70 rounds.
- Enemy army (`ai.md` 2): `py/army/gate_army.py` ticks 42/42 and 9/9, supply 10/10, chained 1000/1000 and 284/284.
- Encounters and losses (`ai.md` 3): `py/army/gate_encounter.py` search 96/96, frames 9600/9600, kills 512/512.
- Attacks on the player (`ai.md` 4): `py/attack/gate_attack.py` launches 768/768 x2, odds 1452/1452, bomb 1494/1494,
  shell 361/361; nothing but the army's walk takes a site.
- Period end and endings (`ai.md` 5): `py/army/gate_period.py` 6/6, 200/200 per routine, the report's numbers 14/14.
- The player's weapons, the engagement and the kill (`ai.md` 6): `py/attack/gate_shot.py` 400/400, 36/36 x5, 798/798
  x3, 48/48, 300/300, 144/144, nine controls fail; `py/attack/drive_kill.py` a driven grenade kill of unit 27 against
  a no-fire control.
- Sabotage (`ai.md` 7): `py/sabotage/gate_sabotage.py` clicks 1500/1500, blast 100/100 per type, 1700/1700 untouched,
  supply 110/110, eight controls fail; driven at a village, a held Warehouse (all 32 units slower), the HQ (win
  screen) and the three Radio Stations (full team), each against a control.
- All seven gates: `uv run python tools/gates.py run midwinter` (about 2 minutes). The README's design digest covers
  all of the above.

## Open, in priority order

1. **Relationships and recruitment one by one**: the only part of the player's turn not decoded, and what decides
   who can join. Find the team list `$2b16c`'s writers other than `$f8d8` (whole-image `find_field_writers.py`),
   drive the bio icons `$3054`/`$3024` and S.O.S `$5784` from `d_stark.snap`, and gate the join rule against a model
   over poked character pairs.
2. **3D pipeline**: `$18304` -> `$16d9c`, draw list `$19ce2`/`$1d5a6`, polygon fill; proof by rendering a frame
   pixel for pixel. It also matches encounter slots and attackers to on-screen objects and unlocks the sniping pick
   `$19ec4`.
3. **Combat and sabotage leftovers** (`ai.md` Open): a driven sniping kill ('S' at speed 0, `$131d8`, then Space); a
   kill of an ordinary vehicle and one with no position poke; the glider shot `$20be6` that never reaches `$cbbe`;
   the surrender screen `$1137a`; a ruined cable car's travel (`$fc6`).
4. Leftovers: character +72's name, `$13f28` (missile 1-in-5), `$14774` (driving mask skip), record +0 bit 7 after a
   hit, travel mode 1 (mask 0, inferred cable car), the Bomber's drop rule and the missile's detonation (read, not
   gated); the non-spread branch and `$2bb2e`, node names; terrain leftovers; the snipe icon `$3dd2` driven.

## Known traps

- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- Options and character-screen snapshots catch the pointer mid-redraw: compare with a 34-pixel tolerance.
- A `u <addr>` into the menu stops inside its packer stub before the depacked code exists: the drive pokes after a
  fixed `s 60000000`.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`; the bytes before `$ec8c` are data. Use `--linear` there.
- `stserver`'s `mouse` click does not register in this game, while the same REPL lines do: click in the REPL,
  `u <routine>`, `snap`, load in `stserver` (`gate_army.py`, `gate_period.py`, `py/sabotage/repl.py`).
- The army moves only at a situation report: a long ski run with no report shows no army change.
- From `d_ski.snap` a missile from the engaged vehicle hits at frame 170 and the trip ends: bound natural 3D runs
  below that, poke the missile object `$1ce02` +38 busy, or set TRAINING `$2c180` (`drive_kill.py`).
- Unit coordinates (and the feature list) are twice the terrain target's (`$19cd4`): poke the target to `unit / 2`.
- `$cbbe`'s unit-kill path ends in the radio message `$d048`, which waits for a key: under `call`, stop it with
  `stops=[0xcd6e]`; in a run, send a key.
- `$f374` loops 65536 times on a record with kind `$80` (held, no buildings): never poke one.
- Decisions offers no actions once the character's clock +32 has reached the game clock, or with +15 at 0: end the
  period first. Node numbers are `$14a8`'s 1-based record numbers.
- `tables/action_tables.txt` pairs rect lists with the next icon table by the nearest `lea`: two rows are mispaired
  (noted in the file). Confirm a pairing from a live snapshot before citing it.

## Next session

`/resume midwinter`. Start on item 1: list every writer of the team list `$2b16c` and of the bio's friend/enemy data
(whole-image scan, not `rdis`), then click the bio icons `$3054`/`$3024` and S.O.S on `d_stark.snap` under `hits` to
find the recruit path. If a shorter task is wanted, item 3's sniping kill reuses `drive_kill.py` almost as is.
