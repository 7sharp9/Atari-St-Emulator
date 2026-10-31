# Crude Buster (Data East 1990 arcade, MAME): handoff

Updated 2026-10-31 by the session that ended at the commit after `5cdce0b` (this handoff's own commit).

## Resume point

- Last commit of this workstream: `5cdce0b` crudebuster: level 2 cleared naturally; final boss grab rule decoded and proven. Before it: `abbe161`, `4cec4b6`, `b9a366b`.
- Workspace: `M68000/reversing/crudebuster/` (`README.md` file index; docs `architecture.md`, `graphics.md`, `sound.md`, `world/world.md`, `player/player.md`, `player/natural.md`, `enemies1/enemies1.md`, `enemies2/enemies2.md`; `infographic/`). Emulator and oracle: **MAME 0.289**, set `cbuster` of `~/mame-roms/cbuster.zip` (present on the Mac). Run MAME through `cbmame.sh` (it sets `SDL_VIDEODRIVER=dummy`).
- Working data (gitignored, on the Mac): `M68000/scratchpad/crudebuster/`. Not yet in `scratchpad/ANCHORS.md` (another session held uncommitted edits to it): `run_b16/sta/cbuster/boss1.sta` (type 16, hp 31, frame 19,700 of a level 2 replay from `nb_stall2`), `run_bb_loop/sta/cbuster/loop1.sta` (frame 22,400 of the standing-jab bot: P1 at the left clamp x 2576 in the grab loop, type 16 hp 19 at x 2554), `bb_l2b/` (the natural level 2 clear with the enemy log), `bl_*`, `b1_*`, `b2_*`, `lp_*` (bosslab runs), `natbot.snapshot13..15*.lua` (the bot before each boss-mode edit). Older anchors: `run_h8/sta/cbuster/nb_stall2.sta` (post-helicopter), `run_h16/sta/cbuster/boss2.sta` (type 36, hp 14).
- Start from: `player/natural.md` "Reproduce" (`CB_LEVEL=N`, absolute script path, `CB_TIMER=1`); a level takes about 3 minutes without `CB_ENEMYLOG`, 15 to 25 with it. Labs: `player/lua/bosslab.lua` header (`CB_STATE`, `CB_POLICY`), summary `player/py/bosslab_sum.py`.
- Uncommitted work left behind: none of this workstream.

## Proven so far

- Architecture, graphics, sound, world, player, enemies of levels 0 to 5: as before (`py/kernel/gates.sh`, `gfx/proof.sh`, `snd/`, `world/py/gates.sh`, `player/py/gates.sh`, `enemies*/`).
- **Level 1 natural clear at frame 13,582**: every run of the current bot, including after the boss mode (`ctl_l1`, `bb_l1`); 33 of 33 list A (`census.py 1 ce_l1/enemylog.txt`).
- **Level 2 natural clear at frame 22,811** (`bb_l2b`; replay from `nb_stall2`: 23,145). 55 of 59 list A, entry 58 (the final boss) killed (`census.py 2 bb_l2b/enemylog.txt`; unmatched 2, 35, 44, 57). `player/natural.md` results and rules table.
- **Final boss grab rule** (types 16, 36; brain leaf `$26d7a`, shared states `$b`/`$c`/`$d` = `$2409a`/`$24126`/`$24286`): 85 of 85 predicted grabs followed by state `$b`, 85 of 85 entries fit, nine lab runs (`bosslab_sum.py`); jump kicks clear the level from `boss1`, `boss2`, `loop1` (standing jabs only from the first two). `enemies1.md` 4.3, section 7.
- **The brain indexes the player's pose (+24 & 15) and variant (+25)**, not action/sub-action (`$22bd0` reads `$80118`/`$80119`); standing is pose 0. `brain_probs.py` corrected; standing row still 1,524 of 1,536 cells decoded. `enemies1.md` 2.1, 2.6.
- Level 3 `$5d4`, level 4 `$664`, level 5 `$1c0` with the bot: unchanged (not re-run this session; the boss mode is gated to level 2).

## Running

Nothing running.

## Open, in priority order

1. **Levels 3 to 5.** Re-run each with the current bot (`CB_LEVEL=3..5`), then attack the stalls: level 3 `$5d4` ladder search at x 500 to 535 and the type 12 boss at 59 px; level 4 the 96 px wall at x 1779 and an enemy waiting below; level 5 the first fight loop at x 641. Before writing a fight rule for a boss, decode its grab/attack leaves with `brain_probs.py` (per-pose rows, as in this session's type 16 check) and test policies with a `bosslab.lua`-style lab (it finds the boss by type 16/36: generalise with a `CB_BTYPES` list). Proof: `$80040` bit 4 and a census per level.
2. **Infographic is stale on two points**: `infographic/py/page.html` says the brain reads the player's "action and sub-action" (it is pose and variant), and `build.py` now gets a different standing row for type 3 (buckets 0-1: idle 50%, f 25%, grab 25%). Rebuild with `infographic/py/build.py` and re-publish to `https://claude.ai/artifact/LrXZswtLBoDa85CyGyKJic` (same file path keeps the URL), together with item 6 (sprites under the move boxes).
3. **Confirm the brain probabilities live** and decode the 12 missing cells (types 13 and 75, case A, buckets 4 to 9): `enemies1/lua/lab.lua`, count next states after state 6/7 against `brain_probs.py` by pose; `bosslab_sum.py`'s predicted-vs-entered test is the model.
4. Level 4 camera rule (which `$81e12` phase), the five-enemy hang at y >= `$210`.
5. Unnamed or fingerprinted types (23, 52, 37, 38 to 44; 16 and 36 now have their states read in 4.3), sound ids, graphics remainder, Hard/Hardest damage, name entry, the other four sets: `enemies1.md` 8, `enemies2.md` 8, `sound.md`, `graphics.md`.
6. Infographic sprites under the move boxes (capture pose `+24`, variant `+25`, frame `+21` while `+28` is set; `player/py/boxes.py`, `lua/reclog.lua`, `gfx/py/cbrender.py`; gate: equals MAME's screenshot).
7. A design digest in `README.md` once levels 3 to 5 are done (none exists).

## Known traps

- **Within a frame the player record is updated before the pool A handlers**: an enemy's decision on frame N sees the player's frame-N state, not frame N-1's. Testing a rule against the previous row gave 34 false "violations" of the grab rule (`bosslab_sum.py` now uses the same row).
- **A field copied by a routine is named from the addresses it reads**, not from the doc that first described the copy: the brain's +46/+47 were documented as action/sub-action from the first pass and were the pose/variant (`$22bd0`). Read the copier before building on a copied field.
- **A thrown player lands where it was grabbed** (the boss throw is vertical), and inputs between landing and the next grab did nothing in the clamp loop. Fighting from the ground beside a clamp loses; stay airborne.
- A state sampled every N frames can look permanent when the real cycle is close to N; print every frame before calling a state a deadlock.
- A jump (b2) is an edge: pressed or held while a punch chain runs it is lost. The level 1 clear depends on the old hop's pause (`natural.md`); any change to `hop`/`heli`/`belt-hop` needs level 1 re-run (13,582).
- `natbot.lua` is not monotonic; copy it aside before each change (`scratchpad/crudebuster/natbot.snapshot*.lua`) and re-run the level that last cleared.
- One full level 2 run with `CB_ENEMYLOG=1` (`bb_l2`, an older bot) ended at frame 23,829 with a normal MAME exit and no stop condition in the script; cause unknown (possibly an external kill). Check `events.txt` reaches the expected end before using a run.
- `CB_ARENA` is a hex scroll x (`a00`); `cbmame.sh` needs absolute script paths; `"${f}:name"` in zsh; the level timer kills in god mode (`CB_TIMER=1`); `CB_ENEMYLOG=1` makes a run about 7 times slower. Earlier traps (`rdis.py` misses state tables, the level-cleared poke hangs at the stage card, edge-latched inputs need an odd period, pool C hit boxes live one frame, `$80016` is shared) are in `architecture.md` and `world.md`.

## Waiting on Dave

Nothing.

## Next session

Run `/resume crudebuster`. Re-run level 1 (13,582) and level 2 (22,811, or the `nb_stall2` replay at 23,145) as the control, and index the new anchors (`boss1`, `loop1`, `bb_l2b`) in `scratchpad/ANCHORS.md` once nobody else holds uncommitted edits to it. Then open item 1: run levels 3 to 5 with the current bot and decode the level 3 boss (type 12) leaves before writing its fight rule. Item 2 (infographic correction) is a short side task.
