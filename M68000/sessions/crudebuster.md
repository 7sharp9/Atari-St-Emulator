# Crude Buster (Data East 1990 arcade, MAME): handoff

Updated 2026-10-06 by the session that ended at the commit after `abbe161` (this handoff's own commit).

## Resume point

- Last work commit: `abbe161` crudebuster: level 2 played naturally to the final boss. Before it: `4cec4b6`, `b9a366b` (natural level 1), `b7c47d3`, `9c7eed9`, `4c80624`, `a2d6644`, `4540b20`, `1ba0b7c`, `b1d86d3`.
- Workspace: `M68000/reversing/crudebuster/` (`README.md` file index; docs `architecture.md`, `graphics.md`, `sound.md`, `world/world.md`, `player/player.md`, `player/natural.md`, `enemies1/enemies1.md`, `enemies2/enemies2.md`; `infographic/`). Emulator and oracle: **MAME 0.289**, set `cbuster` of `~/mame-roms/cbuster.zip`.
- Working data (gitignored): `M68000/scratchpad/crudebuster/`, indexed in `scratchpad/ANCHORS.md` (this pass: `ce_l1`, `ce_l2` enemy-log runs, `run_h8/sta/cbuster/nb_stall2.sta` = level 2 ground state after the helicopter, `run_h16/sta/cbuster/boss2.sta` = type 36 boss at frame 22,300, `natbot.snapshot*.lua` = the bot between edits).
- Start from: `player/natural.md` "Reproduce" (`CB_LEVEL=N`, absolute script path, `CB_TIMER=1`). A level takes about 3 minutes without `CB_ENEMYLOG`, 15 to 25 with it. A replay from a saved state (`CB_LOAD=<state>` for the bot, `CB_STATE` for the labs) runs at about 7x real time: 2 minutes for 8,000 frames.
- Uncommitted work left behind: none of this workstream (`sessions/README.md` carries another session's rewraps).

## Proven so far

Detail in the docs; counts from this pass unless a doc says otherwise.

- Architecture, graphics, sound, world, player, enemies of levels 0 to 5: as before (`py/kernel/gates.sh`, `gfx/proof.sh`, `snd/`, `world/py/gates.sh`, `player/py/gates.sh`, `enemies*/`).
- **Natural level 1 clear at frame 13,582** with the current bot (five runs, same frame; the bot before the `heli` rule cleared at 14,262). 33 of 33 list A entries spawned in script order (`enemies1/py/census.py 1 scratchpad/crudebuster/ce_l1/enemylog.txt`).
- **Level 2 played naturally to its last arena** (`player/natural.md` results and rules table): 55 of 59 list A entries seen, entry 58 (type 23 var 2, trigger `$a00`) at frame 18,523 (`census.py 2 ce_l2/enemylog.txt`; the unmatched 2, 35, 44, 57). Three bot rules did it, each with its lab:
  - helicopter parts 47 to 49 are hit-tested in state 0 and come within a standing jab only at the low point of their sweep (`lua/helilab.lua`: part hp 32 -> 5 and 48 -> 12 in 720 frames); the bot ignored state 0 records before;
  - the `$e800`/`0003` floor change at x `$900` is passed by a real jump, and a jump needs a fresh b2 edge after a punch chain (`lua/seqlab.lua`: right+b2 jumps 2291 -> 2329, the pattern with punches before it does not);
  - the raised block after it is a leftward conveyor (1 px/frame) with a solid girder tower on it; repeated hops cross it (x 2329 -> 2380 in the second hop; up+b2 at x 2321 climbs to y 256, not followed).
- Level 3 `$5d4`, level 4 `$664`, level 5 `$1c0` with the current bot: unchanged. Level 4's wall at x 1779 is not passed by a jump (the wall is 96 px tall, `world/py/terrain.py 4 1744 1824 400 620`).
- **Level 2's final boss**: type 16 (hp 32) then, at hp 16, type 36 (hp 16) with parts 37 to 44; standing jab pulses hurt it (14 -> 6 in 1,500 frames in the lab, `lua/poollog.lua` with `CB_PULSE=5`), but it grabs and throws the player about every 160 to 240 frames, and the bot did not kill it (`enemies1.md` 4.3).
- Level geometry reader `world/py/terrain.py` (the `$ebb0` attribute map; the probe `$a868` reads (x +- 12, y + 32); which attribute bits block is not decoded).

## Open, in priority order

1. **Kill the level 2 boss, then clear levels 3 to 5.** The bot is pinned at the screen clamp (x 2800) in a grab-throw loop (hp 32 -> 30 in 5,000 frames), or in a replay takes type 16 to hp 16 and type 36 to hp 14 and stops. Tried and dropped: staying left of x 2680 (worse). Next: read the grab condition (states `$b` to `$d` of `$15b3a` and `$1b066`, shared routines `$2409a`, `$24126`, `$24286`; the idle chooser `$2438a`, `py/brain_probs.py`) and the boss's reach in state 7/8 (hit object C23 spawned every frame of the run, speed `+2.5`), then fight with a rule that avoids the grab (jump kicks, hit and retreat). Prove it by `$80040` bit 4 and a census with entry 58 killed. Then the `heli`, hop and belt rules need checking on levels 3 to 5 (their stalls: level 3 `$5d4` ladder search at x 500 to 535 and the type 12 boss at 59 px, level 4 the 96 px wall at x 1779 and an enemy waiting below, level 5 the first fight loop at x 641).
2. **Confirm the brain probabilities live** and decode the 12 missing cells (types 13 and 75, case A, buckets 4 to 9): `enemies1/lua/lab.lua`, count next states after state 6 or 7 against `brain_probs.py`. It also tells what the type 16/36 idle chooser does.
3. Level 4 camera rule (which `$81e12` phase), the five-enemy hang at y >= `$210`.
4. Unnamed or fingerprinted types (23, 16, 52, 37, 36, 38 to 44 now added), sound ids to events, graphics remainder, Hard/Hardest damage, name entry, the other four sets: `enemies1.md` section 8, `enemies2.md` section 8, `sound.md`, `graphics.md`.
5. **Infographic: sprites under the move boxes** (unchanged from the previous handoff): replace the bare body box in "What each move reaches" with the player's actual sprite frame per move (capture pose `+24`, variant `+25`, frame `+21` while the attack flag `+28` is set, `player/py/boxes.py`, `lua/reclog.lua`; render with `gfx/py/cbrender.py`; gate: equals MAME's screenshot of the frame); edit `infographic/py/build.py` `moves_svg`, re-publish to `https://claude.ai/artifact/LrXZswtLBoDa85CyGyKJic` (same file path keeps the URL).
6. A design digest or port plan in `README.md` once 1 to 3 are done (none exists).

## Known traps

- **A state sampled every N frames can look permanent when the real cycle is close to N.** This pass read "the player is stuck in the thrown action for 5,000 frames" from rows sampled every 200 frames; an idle player from that state is thrown every 160 to 240 frames (`seqlab.lua`, every frame). Print every frame (or a period coprime to the cycle) before calling a state a deadlock.
- A jump (b2) is an edge: pressed or held while a punch chain runs it is lost. The bot's old `hop` (b2 for 3 frames) never jumped and level 1 depends on that pause: it hops for real only when nothing stands within 70 px ahead (`natural.md`). Any change to `hop`/`heli`/`belt-hop` needs level 1 re-run (clear at 13,582, census 33 of 33).
- `natbot.lua` is not monotonic; copy it aside before each change (`scratchpad/crudebuster/natbot.snapshot*.lua`, the numbered ones are this pass's order) and re-run the level that last cleared. Level 2's helicopter fight takes 14,500 to 16,700 frames depending on the run, so full runs differ in when the last arena is reached.
- `CB_ARENA` is a hex scroll x (`a00`), parsed with base 16; a bad value makes the policy error every frame and the bot keeps its last inputs.
- zsh: `rm -rf $S/$k` is refused by the harness; use `mkdir -p` on fresh run directories (they do not need removing) or `"${S:?}"/...`. `pgrep -f` right after a background start can miss the process: sleep a few seconds before waiting on it.
- Sub-action 7 means the turn-around kick in actions 2 and 6 and the ladder climb in actions 0 and 4. Pool A records in state 0 are not fight targets except types 47 to 49 (helicopter parts); records with `type 28`, 45 to 50, 65 are parts or waiting records.
- The level timer kills in god mode (`CB_TIMER=1` refills it); `-seconds_to_run` counts machine time; `CB_ENEMYLOG=1` makes a run about 7 times slower; `cbmame.sh` needs absolute script paths; write `"${f}:name"` in zsh.
- Earlier traps still apply: `rdis.py` misses state tables, the level-cleared poke hangs at the stage card, edge-latched inputs need an odd period, pool C hit boxes live one frame, `$80016` is shared (`architecture.md`, `world.md`).

## Next session

Run `/resume crudebuster`. First re-run level 1 (13,582) and level 2 to the last arena (`CB_LEVEL=2`, about 6 minutes; or `CB_LOAD=nb_stall2` in `run_h8`). Then work open item 1: decode the grab condition of types 16 and 36 with `showtype.py`/`brain_probs.py`, pick a fight rule, and test it in replays from `boss2` before a full run. Agents can take the type naming of 16, 36, 23, 37, 52, 38 to 44 in parallel (addresses in a `BRIEF.md`, not roles).
