# Black Tiger: handoff

Updated 2026-10-04 by the session that ended at commit `3de9413`.

## Resume point

- Last commit of this workstream: `3de9413` black_tiger: first pass (six parallel agents). Lessons for
  `CLAUDE.md` and the skill are in `a2cbcd4`.
- Working data: `M68000/scratchpad/black_tiger/` (about 540 MB, gitignored; indexed in
  `scratchpad/ANCHORS.md`). Rebuild recipe: `reversing/black_tiger/README.md` "How it was run"
  (unzip, `extract_disk.py`, `add_file_to_disk.py` with the 8.3 name `BLTIGER.PRG`, cold boot 20M, then
  `drive.txt`). Every gate script reads/writes under `$BT_WORK/agents/<area>/` (default that directory).
- Start from: `scratchpad/black_tiger/play_start.snap` (level 1, 5 lives, controllable; byte-identical to
  the scripted `drive.txt` run). Levels 2-8: `agents/systems/lvl1..7.snap`. Bosses/shop/ending:
  `agents/systems/boss/`. Attract demo: `tl/t01..t30.snap`.
- Uncommitted work left behind: none of this workstream. `M68000/sessions/README.md` carries another
  session's unrelated line-rewrap, left in the working tree; only the Black Tiger row is staged/committed.

## Proven so far

Detail and scripts in `reversing/black_tiger/*.md` (README has the table of proofs and counts).

- Boot chain, file roles, frame driver (main loop `$c574`, 5 VBL per frame, 49/49), 32 `trap #3`
  services of the resident BL_TIGER library, Timer A = sample player, demo = recorded stream
  (`py/systems/gates.py all`, 8 PASS).
- Graphics: software scroll with full tile redraw; tiles 94.5-96.3% of 40,960 pixels on 15 snapshots over
  8 levels; hero attack frames 100%; 10 pictures 100%; bosses 71/132 instances exact; title 64000/64000
  (`py/graphics/*_check.py`).
- Mechanics: level files and marker scanner 8/8; class table collision; hero vertical step 393/393,
  391/391, 396/396; weapon 25/25; urn 160/160; shop 200/200; bonus 8/8; rng 300/300; chest 30/30; drops
  18/18; vitality 0 is not a death condition (`py/mechanics`).
- AI: `$dbde` 2500/2500 over all 19 types; spawner 9/9; activation window 160/160; ambient + boss fire
  800/800; urn 96/96; event attacks 600/600 (`py/ai`).
- Sound: 8-bit samples through PSG volume registers, 23,813/23,813 and 52,887/52,887 ticks
  (`py/sound/verify_psg.py`, `verify_natural.py`).
- Secrets: built-in level skip, invisible dungeon doors `$1b/$1c`, checkpoint `$1f`, pause, ending by
  level-8 clear, trainer = 1000 lives + 14336 zenny; no cheat word, debug key or extra life; 9 drives
  twice each md5-identical (`py/secrets/run_all.py`).

## Open, in priority order

1. Fight a boss for real: no hero has killed a boss by weapon hits (the state was poked to 4); boss
   death/dissolve frames, the boss HP bar `$101b0`, the level-clear flow from a real kill are unexercised.
   Prove with a scripted fight from `boss<L>_fight.snap` (hero position poke is labelled), checking a
   signal that only changes when the weapon-hit path fires (`$e930`).
2. Walk levels 2-8 naturally (all were reached by the level skip plus a hero-position poke): route scripts
   like Cadaver's `route_*.py` would also give the real item/enemy pacing and let `$1d`/`$1e` traps,
   old-men dialogues and the second advice text be seen on screen.
3. Emulator: make the keyboard ACIA data register retain the last received byte (`MMU.fs` ~913, ~295)
   behind the full regression net, then delete the two pokes from `drive.txt`. Falsifier: `verify`,
   30M snapshot compare and a game snapshot compare must not change for games that read through the
   ISR; Black Tiger's cracktro must pass on a real SPACE press with no poke.
4. Gate the remaining AI/graphics code: hostile-projectile handlers `$10e94 $10b84 $10894`, the
   animation engine inside `$e19e` and the animation-script data (frame banks via `$1eea2`); actor types
   15 and 12 do not match any sprite within +-10 px; BTOBJ pictures named by look; width codes 3,5,6,7
   exist in no shipped bank.
5. Names still inferred: boss names by level (order of `BTIGER.DOC`), actor types 4/11/16, flail/
   lantern names, `$17712`. Hi-score and game-over screens use the systems agent's snapshots, not
   graphics-agent captures.
6. If a port or pixel-for-pixel renderer is wanted (the PowerMonger route, skill section 4b): tiles,
   sprites, HUD and palettes are decoded; the missing part is a full-frame renderer scored per category
   against consecutive snapshots paired as state i with screen i+1.

## Known traps

- `\AUTO\` name must be 8.3 (`AUTO_BL_TIGER.PRG` is silently not found); `add_file_to_disk.py` accepts it.
- Keyboard: the game proper reads keys through TOS services; only `$a562` and the trainer poll
  `$c658/$c662` read the ACIA directly (stalled by the emulator divergence, bypassed by pokes).
  Joystick 1 is `kbd ff <state>`, hold >= 30,000 steps; `kbd fe` (joystick 0) is read nowhere.
- `play_start.snap` is mid tile-blit (PC `$b2fa`): a callcap from it begins mid-redraw (harmless for the
  gates). "Please insert Disk A/B" prompts block on any key (`kbd 39` then `kbd b9`).
- Reaching a boss with the hero-position poke also needs the camera poked, else the boss is pushed to
  the old camera position by `y >= scrolly+$21` at `$e7b4..$e7c0` (`py/ai/drive_boss.py`).
- `$cf20` is the map-object kind table (kinds `$11..$16` share `$d194`), not an actor table; `BTCLIPS`
  and `BTOBJ` are picture banks, not collision data (collision is the tile class byte at tileset `+$40`).
- The sound renderer reads Hatari's measured YM2149 table at render time from `$HATARI_YM_TABLE` or
  `$HATARI_SRC` (not copied into the repo); gates do not depend on it.
- Always `export ATARI_NOTRACE=1`; `w <addr> <8 hex>` writes a longword.

## Next session

Pick open item 1 or 3. For item 1: `/resume black_tiger`, start `agents/systems/boss/boss0_fight.snap`
(level 1 boss, type 1, hp 16), script weapon hits with `kbd ff 80` bursts held >= 30,000 steps, watch
`$e930` and the boss record at `$1f020`. For item 3: coordinate with any live session before touching
`MMU.fs` or `bin/` (`sessions/README.md` "Shared resources").
