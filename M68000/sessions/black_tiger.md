# Black Tiger: handoff

Updated 2026-10-31 by the session that ended at commit `8718607`.

## Resume point

- Last commit of this workstream: `8718607` black_tiger: level-1 boss killed by joystick input alone.
- Working data: `M68000/scratchpad/black_tiger/` (about 540 MB, gitignored; indexed in `scratchpad/ANCHORS.md`).
  Rebuild recipe: `reversing/black_tiger/README.md` "How it was run". Gate scripts read/write under
  `$BT_WORK/agents/<area>/` (default that directory). Boss-fight output: `agents/bossfight/L<L>/` (fight.log,
  per-frame PNGs, `kill.snap`, `prompt.snap`, `next_level.snap`; L0 complete, L2/L3 failed runs).
- Start from: `scratchpad/black_tiger/play_start.snap` (level 1, controllable; every gate reads it). Levels 2-8:
  `agents/systems/lvl1..7.snap`. Bosses/shop/ending: `agents/systems/boss/` (its README has the boss table).
  Level 2 reached through a real boss kill: `agents/bossfight/L0/next_level.snap`.
- Uncommitted work left behind: none of this workstream. `scratchpad/ANCHORS.md` carries another session's
  uncommitted edit, so the `agents/bossfight/` snapshots are not indexed there yet.

## Proven so far

Detail and scripts in `reversing/black_tiger/*.md` (README has the table of proofs and counts).

- Boot chain, frame driver (5 VBL per frame), 32 `trap #3` services, Timer A sample player, demo stream
  (`py/systems/gates.py all`, 8 PASS).
- Graphics: tiles 94.5-96.3%, hero attack frames 100%, pictures 100%, bosses 71/132, title 64000/64000.
- Mechanics: scanner 8/8, vertical step 393/391/396, weapon 25/25, urn 160/160, shop 200/200, bonus 8/8, rng
  300/300, chest 30/30, drops 18/18 (`py/mechanics`).
- AI: `$dbde` 2500/2500, spawner 9/9, window 160/160, ambient + boss fire 800/800, urn 96/96, events 600/600.
- Level-1 boss killed by joystick input alone (`py/ai/boss_fight.py 0`, two runs, logs and snapshots identical):
  17 knife hits (`$e6c2`), clear on the frame the first record empties with an escort alive, bonus, disk
  prompt, level 2 loads; HP bar `$101b0(hp>>4)` (`ai.md` section 9, `mechanics.md` section 13).
- Sound: 23,813/23,813 and 52,887/52,887 ticks. Secrets: 9 drives twice md5-identical (`py/secrets/run_all.py`).
- Keyboard ACIA retention (old open item 3) is fixed in the emulator and `drive.txt` needs no pokes (`7e5b688`).

## Running

Nothing running.

## Open, in priority order

1. Kill bosses 2-8: `boss_fight.py` steers only in x. In `boss2_fight.snap` and `boss3_fight.snap` the boss is far
   off vertically (y `$989` vs hero `$e0`; `$399` vs `$150`, dormant), so first read where each boss actually
   sits (the marker positions in `ai.md` section 9 differ from the fight snapshots), then add y steering
   (ladders/jumps) or start from a snapshot taken after the boss comes on screen. Proven when a run reaches
   `$1025c` with no pokes, twice identical. A melee kill (`$e9b2` writes on the boss) is still unseen: try
   standing inside 64 px with knives on cooldown.
2. Walk levels 2-8 naturally (all were reached by the level skip plus a hero-position poke); start level 2 from
   `agents/bossfight/L0/next_level.snap`. Route scripts like Cadaver's `route_*.py` would show the `$1d`/`$1e`
   traps, old-men dialogues and the second advice text on screen.
3. Gate the remaining AI/graphics code: hostile-projectile handlers `$10e94 $10b84 $10894`, the animation engine
   inside `$e19e`, animation scripts (frame banks via `$1eea2`); actor types 15 and 12 match no sprite within
   +-10 px; width codes 3,5,6,7 in no shipped bank.
4. Names still inferred: boss names by level (order of `BTIGER.DOC`), actor types 4/11/16, flail/lantern names,
   `$17712`.
5. Port or pixel renderer only if wanted (skill section 4b): a full-frame renderer scored per category.

## Known traps

- `\AUTO\` name must be 8.3 (`AUTO_BL_TIGER.PRG` is silently not found).
- One game frame is 5 VBL = 60,000 steps. A 30,000-step `kbd ff` packet followed by a release can fall between
  two joystick reads: the hero moved one step per about 2.4 such packets. `boss_fight.py` holds 60,000.
- Fire at weapon level 0 swings and throws knives; knives (1 hp each, `$e6c2`) do almost all the damage, so a
  signal on `$e930`/`$e9b2` alone undercounts hits: watch the hp byte with the writer PC.
- The level is a ring of width `$1effe` (2048 px on level 1): bosses wrap in x, so take dx modulo the width.
- `stserver` results: `watch_events` returns a list (one entry per watch), `hits` returns `{"hits": [...]}`.
- Reaching a boss with the hero-position poke also needs the camera poked (`py/ai/drive_boss.py`).
- `$cf20` is the map-object kind table, not an actor table; `BTCLIPS`/`BTOBJ` are picture banks.
- Always `export ATARI_NOTRACE=1`; `w <addr> <8 hex>` writes a longword.

## Waiting on Dave

Nothing.

## Next session

`/resume black_tiger`, then open item 1: load `boss2_fight.snap` in `stserver`, step until the boss record at
`$1f020` comes within the screen (or read its y path), add y steering to `boss_fight.py` and re-run L2..L7.
Index `agents/bossfight/` in `scratchpad/ANCHORS.md` once the other session's edit there is committed.
