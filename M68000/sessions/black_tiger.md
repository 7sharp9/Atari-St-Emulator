# Black Tiger: handoff

Updated 2026-11-20 by the session that ended at commit `98b786e` (the per-level code census).

## Resume point

- Last commit of this workstream: `98b786e` black_tiger: census scripts find the repo root by walking up to tools/rdis.py
  (the census itself: `1544c79`; the tool `tools/code_census.py`: `d98224f`).
- Working data: `M68000/scratchpad/black_tiger/` (about 540 MB, gitignored; indexed in `scratchpad/ANCHORS.md`).
  Rebuild recipe: `reversing/black_tiger/README.md` "How it was run". Gate scripts read/write under
  `$BT_WORK/agents/<area>/` (default that directory). Boss-fight output: `agents/bossfight/L<L>/` (L0 complete, L2/L3
  failed runs). Census output: `census/<run>/chunk_NNN.npz` (25 runs; rebuild `py/census/run_levels.sh`, about 2 min, then
  `report_levels.sh`).
- Start from: `scratchpad/black_tiger/play_start.snap` (level 1, controllable; every gate reads it). Levels 2-8:
  `agents/systems/lvl1..7.snap`. Bosses/shop/ending: `agents/systems/boss/` (its README has the boss table).
  Level 2 reached through a real boss kill: `agents/bossfight/L0/next_level.snap`.
- Uncommitted work left behind: none. `agents/bossfight/` snapshots are still not indexed in `scratchpad/ANCHORS.md`.

## Proven so far

Detail and scripts in `reversing/black_tiger/*.md` (README has the table of proofs and counts).

- Boot chain, frame driver (5 VBL per frame), 32 `trap #3` services, Timer A sample player, demo stream
  (`py/systems/gates.py all`, 8 PASS).
- Graphics: tiles 94.5-96.3%, hero attack frames 100%, pictures 100%, bosses 71/132, title 64000/64000.
- Mechanics: scanner 8/8, vertical step 393/391/396, weapon 25/25, urn 160/160, shop 200/200, bonus 8/8, rng
  300/300, chest 30/30, drops 18/18 (`py/mechanics`).
- AI: `$dbde` 2500/2500, spawner 9/9, window 160/160, ambient + boss fire 800/800, urn 96/96, events 600/600.
- Level-1 boss killed by joystick input alone (`py/ai/boss_fight.py 0`, two runs identical; `ai.md` section 9).
- Sound: 23,813/23,813 and 52,887/52,887 ticks. Secrets: 9 drives twice md5-identical (`py/secrets/run_all.py`).
- Levels 2-8 add no subsystem: 2,630 bytes in 37 spans that level 1 never ran, all inside named routines (1,966 in routines a
  `py/` script cites, 594 doc-only, 70 in neither), against a level-1 base with a forced death; bounded by a no-route joystick
  loop, levels 2, 4, 7, 8 unsaturated (README "Code each level adds", `py/census/`).

## Running

Nothing running.

## Open, in priority order

1. Gate the hostile-shot handlers `$10e94`, `$10b84`, `$10894` and the animation engine inside `$e19e`: the census puts the
   P-shot handlers (436 bytes) and the aimed shot `$df12` at the top of what later levels add, and `$10e94` is doc-only. Gate
   like `ai.md` section 4, match counts per handler. Corpus: `boss5_fight.snap` (its census run `B5_walk` runs 224 of the
   290-byte span, all 146 of `$10f66..$10ffc` and 240 of `$df12`'s 260; `B6_walk` 136, the other boss runs 8).
2. Kill bosses 2-8: `boss_fight.py` steers only in x. In `boss2_fight.snap` and `boss3_fight.snap` the boss is far off
   vertically (y `$989` vs hero `$e0`; `$399` vs `$150`), so read where each boss sits, then add y steering or start after
   the boss comes on screen. Proven when a run reaches `$1025c` with no pokes, twice identical. A melee kill (`$e9b2` on the
   boss) is still unseen. The census says this is play-driving: the boss code it would reach is already named.
3. Saturate the census on levels 2, 4, 7, 8 (740 to 944 new bytes in their second 15M steps): a route script per level
   (open item 4's), then re-run `report_levels.sh` with those runs added; done when a second half adds under 50 bytes.
   Read the 70 unmentioned bytes `$10d9c..$10dea` (effect kind 8 handler `$10d94`) with `bp 10d9c` on `L2_walk`'s start.
4. Walk levels 2-8 naturally (all reached by the level skip plus a hero-position poke); start level 2 from
   `agents/bossfight/L0/next_level.snap`. Would show the `$1d`/`$1e` traps, old-men dialogues and the second advice text.
5. Names still inferred: boss names by level, actor types 4/11/16, flail/lantern names, `$17712`; types 15 and 12 match
   no sprite within +-10 px; width codes 3,5,6,7 in no shipped bank.
6. Port or pixel renderer only if wanted (skill section 4b).

## Known traps

- `\AUTO\` name must be 8.3 (`AUTO_BL_TIGER.PRG` is silently not found).
- One game frame is 5 VBL = 60,000 steps. A 30,000-step `kbd ff` packet followed by a release can fall between
  two joystick reads. `boss_fight.py` holds 60,000.
- Fire at weapon level 0 swings and throws knives; knives (1 hp each, `$e6c2`) do almost all the damage: watch the hp byte
  with the writer PC, not `$e930`/`$e9b2` alone.
- The level is a ring of width `$1effe` (2048 px on level 1): bosses wrap in x, so take dx modulo the width.
- `stserver` results: `watch_events` returns a list (one entry per watch), `hits` returns `{"hits": [...]}`.
- Reaching a boss with the hero-position poke also needs the camera poked (`py/ai/drive_boss.py`).
- `$cf20` is the map-object kind table, not an actor table; `BTCLIPS`/`BTOBJ` are picture banks.
- Level 1 standing idle never dies in 40M steps (TIME is 9000 VBL, about 108M steps); a census death control pokes TIME
  `$1eedc` (`py/census/timeout.txt`).
- Always `export ATARI_NOTRACE=1`; `w <addr> <8 hex>` writes a longword.

## Waiting on Dave

Nothing.

## Next session

`/resume black_tiger`, then open item 1: build a callcap corpus of `$10e94`'s handlers from `boss5_fight.snap` (the one
boss run that fires them all; `boss6_fight.snap` for a second), model each handler and gate it. Index `agents/bossfight/` in
`scratchpad/ANCHORS.md`.
