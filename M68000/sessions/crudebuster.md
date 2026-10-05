# Crude Buster (Data East 1990 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `b9a366b` (plus the CLAUDE.md commit and this handoff).

## Resume point

- Last commit of this workstream: `b9a366b` crudebuster: natural level 1 clear (natbot), decoded enemy brain probabilities, infographic. Before it: `b7c47d3` enemies of levels 3-5, `9c7eed9` player, `4c80624` enemies 0-2, `a2d6644` world, `4540b20` sound, `1ba0b7c` graphics, `b1d86d3` architecture.
- Workspace: `M68000/reversing/crudebuster/` (`README.md` file index; docs `architecture.md`, `graphics.md`, `sound.md`, `world/world.md`, `player/player.md`, `player/natural.md` (new), `enemies1/enemies1.md`, `enemies2/enemies2.md`; `infographic/` (new)). Emulator and oracle: **MAME 0.289**, set `cbuster` of `~/mame-roms/cbuster.zip` (`CB_SET` selects a clone).
- Working data (gitignored): `M68000/scratchpad/crudebuster/` (`rom/`, `all_lin.txt`, `agents/`, and this pass's `ng_l1/` natural level 1 log with `enemylog.txt`, `nh_l1/`, `nz_l2..5/` final runs, `nb_cap/` box captures, `natbot.snapshot*.lua` copies of the bot; indexed in `scratchpad/ANCHORS.md`). A natural level 1 clear state is `run_ng_l1/sta/cbuster/nb_clear.sta`.
- Start from: `player/natural.md` "Reproduce" (`CB_LEVEL=N`, absolute script path, `CB_TIMER=1`). A level takes about 3 minutes without `CB_ENEMYLOG` and about 15 with it (the log reads about 1,500 bytes per frame from Lua).
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's line rewraps in the working tree; not touched.
- Published copy of the infographic: `https://claude.ai/artifact/LrXZswtLBoDa85CyGyKJic` (private; the repo file is `infographic/crudebuster_hitboxes_and_ai.html`, rebuilt by `infographic/py/build.py`).

## Proven so far

Detail in the docs; counts re-run this pass except where a doc says otherwise.

- Architecture, graphics, sound, world, player, enemies of levels 0-5: as in the previous handoff (`py/kernel/gates.sh`, `gfx/proof.sh`, `snd/`, `world/py/gates.sh`, `player/py/gates.sh`, `enemies*/`).
- **Natural level 1 clear** (`player/natural.md`): `$80040` bit 4 at frame 14262 in two runs (`ng_l1` with the enemy log, `nh_l1` without), 33 of 33 list A entries spawned in script order (`enemies1/py/census.py 1 ng_l1/enemylog.txt`; the assisted run saw 25 of 33), roller dead 5998, leader dead 14006, clear 256 frames later.
- **Lock walls wear down under jabs** (three hits, about 150 frames; `player/lua/walllab.lua`; natural level 0 at scroll `$2f4`, level 1, 3, 4): corrects `world.md` section 4 and `player.md` open item (d).
- **Level 4 descent is a ladder 5 px wide**: a plain down press at x 1502 to 1506, y 448 enters it (`player/lua/ladderlab.lua`; found by the bot's sweep at frame 13879). Answers how a player gets down; which `$81e12` phase lets the camera pass is still open.
- **Enemy brain decoded** (`enemies1/py/brain_probs.py`): exact next-state probabilities for 1,524 of 1,536 (type, table, bucket) cells of the 32 types with their own table, player standing; four types plotted in the infographic. Decoded from the ROM, not yet confirmed by counting live decisions.
- Box overlay: `infographic/py/overlay.py` predicts the game's hit flag in 4 of 4 captured fight frames.

## Open, in priority order

1. **Levels 2 to 5 are not cleared naturally.** The bot is not monotonic: earlier versions (not kept) reached level 2 `$864` (helicopter destroyed), level 3 `$801` (boss at `$600` passed), level 5 `$e21` (the last screen, ladder up at x 990), the final version reaches 2 `$802`, 3 `$5d4`, 4 `$664` (ladder found, lower floor), 5 `$1c0` (`player/natural.md` results table). Known blockers: a wall tile at x `$900` (level 2) and x 1779 (level 4 lower floor) that a walking player cannot pass (a jump is untested: `hop` mode exists), the level 3 type 12 boss attacking from off screen at 59 px, a ledge at level 3 `$801`, the level 5 first fight loop at x 641, an enemy waiting on a lower level in level 4. Prove with a bot that clears each level from `startlevel.lua` and re-run the census (`enemies1/py/census.py <level> <enemylog>`, expect all entries) and the render gate (`gfx/proof.sh`) on the natural frames; then the boss fights of levels 1 and 2 and the final boss can be studied.
2. **Confirm the brain probabilities live** and decode the 12 missing cells (types 13 and 75, case A, buckets 4 to 9): spawn a type at a fixed distance from a standing P1 (`enemies1/lua/lab.lua`), pin its x, count the next states after each state 6 or 7 against `brain_probs.py` (a breakpoint on each setter gives the idle decisions).
3. Level 4 camera rule (which `$81e12` phase), the hang with five enemies at y >= `$210`: now reachable by the natural run through the ladder.
4. Unnamed or fingerprinted types, sound ids to events, graphics remainder, Hard/Hardest damage, name entry, the other four sets: as in `enemies1.md` section 8, `enemies2.md` section 8, `sound.md`, `graphics.md` (unchanged this pass).
5. **Infographic: sprites under the move boxes.** The "What each move reaches" section draws the attack boxes against a bare green body box. Replace each cell with the player's actual sprite frame for that move (jab, finisher, walking jab, turn-around kick, jump kick, weapon swing, grab) with the body and attack boxes overlaid on it, so the reach reads against a character. Needs the sprite-per-object lookup that `graphics.md` still lists as open (the actor animation table `$22540`/`$30000[type][state]` against live frames; `gfx/py/animatlas.py` already composes actor frames to `gfx/assets/anim_*.png`, and `gfx/py/cbrender.py` renders sprites that equal MAME on 215,915 of 215,915 entries). Per move: capture the player's pose (`+24`), variant (`+25`) and animation frame (`+21`) on the frames where the attack flag `+28` is set (`player/py/boxes.py`, `lua/reclog.lua`), render that frame at the player's position, draw the boxes from the same record. Gate: the rendered sprite equals MAME's screenshot of the same frame. Optionally do the same for an enemy body box (`$6b000[type][state]`). Edit `infographic/py/build.py` `moves_svg` and re-publish the artifact (same file path keeps the URL).
6. A design digest or port plan in `README.md` once 1 to 3 are done (none exists, so no digest was re-checked).

## Known traps

- `natbot.lua` was edited in place for a whole session without keeping versions; fix one behaviour at a time, copy the file aside before each change and re-run level 1 (it must still clear at frame 14262). A change that helped one level (hop, `others` height targets, enemy ban) stalled another; `CB_BAN=1` is off by default for that reason.
- Sub-action 7 means the turn-around kick in actions 2 and 6 and the ladder climb in actions 0 and 4. Pool A records in state 0 and records with `type 28`, 45 to 50, 65 are parts or waiting records: they are not fight targets.
- The level timer kills in god mode (frame about 19,800 of a stalled run); `CB_TIMER=1` refills it, which is a poke to state in the final table.
- `-seconds_to_run` counts machine time: a state loaded at frame F needs F/58 seconds more (a lab of 60 seconds exited at once).
- In zsh `CB_SAVEAT=$f:name` loses the value (`:name` is a history modifier): write `"${f}:name"` (now in `CLAUDE.md`). `cbmame.sh` needs absolute script paths.
- `CB_ENEMYLOG=1` makes a run about 7 times slower; leave it off except for the census run.
- Earlier traps still apply: `rdis.py` misses state tables, the level-cleared poke hangs at the stage card, edge-latched inputs need an odd period, pool C hit boxes live one frame, `$80016` is shared (`architecture.md`, `world.md`).

## Next session

Run `/resume crudebuster`. First re-run level 1 from `natbot.lua` and confirm the clear at 14262; then take the levels one at a time (2 first: test `hop` at x 2291 from a saved stall state with `walllab.lua`), copying the bot aside before each change. When two levels clear naturally, run the census and `gfx/proof.sh` on them and use agents (addresses in `BRIEF.md`, not roles) for the open type naming. Do the live brain count (open item 2) in parallel; it needs no bot.
