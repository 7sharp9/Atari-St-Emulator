# Impossamole: handoff

Updated 2026-09-29 by the 104th-pass session (seven parallel agents: route, boss, shop, spawn types, level end, four worlds); the
work commits are listed by `git log --oneline -6`, the last being this handoff.

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `pass99/`, `pass103/`, and the new
  `agents/<area>/` directories (`hop3`, `hop4`, `boss`, `spawn`, `wsel`, `world12`, `world34`, each with a `report.md` saved from the agent's final
  message). Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source `~/GitHub/hatari/`. TOS ROM `M68000/TOS100UK.IMG`.
- Start from: `agents/hop4/boss_room_real_settled.snap` (Amazon boss room reached by the whole real-input route, hero landed, weapon 3, 25 coins,
  health 18/18), or `pass103/room188.snap` for the route. For any other world use `agents/world12/{klondike,orient}_gameplay.snap` and
  `agents/world34/snaps/{ice,bermuda}_gameplay.snap` (fresh cold boots, tables resident). **Every `resume ... repl` needs `--disk-a
  "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"`** (relative to `M68000/`) and `ATARI_NOTRACE=1`; the REPL stops
  at the first unknown line (no `#` comments); `snap <path>` is relative to the dotnet process's directory; `watch <addr> <len>` takes a decimal
  length and reports on stderr; `w <addr> <8 hex digits>` writes a longword.
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` carries a pre-existing whitespace-rewrap diff (not this
  workstream's); `.obsidian/` and `Cadaver/` are untracked.

## Proven so far

See `reversing/impossamole/README.md` (Amazon), `graphics.md` (asset formats), `worlds.md` (all five worlds); scripts in `py/` (`py/README.md`).

- **Hand-written 68000 assembly; graphics chain decoded** (level `$27600` -> block defs `$29000` -> tile bank `$29800`, sprite banks `$3b600`
  and `$42e00`, font): 97.4-98.8 % pixel match on all five worlds (`py/tiles.py --check`, offset (32, 8)).
- **The whole Amazon route to the boss room on real input** (from `pass103/room188.snap`: 11 + 5 driven segments, health poked per segment,
  labelled): every segment and the 7397-command chain replay byte-identically, exit records for blocks 283 and 317 match all predicted fields
  (`py/route/verify_route.py` ALL IDENTICAL; `py/shop/real_replay_check.sh` nine identical lines; README "The route to the boss room on real input").
- **Boss killed by real input, no shot poke** (README "Natural aim"): the "shot" is a static melee swipe that only a jumping hero overlaps; weapon
  1/2/3 kills in 60/30/20 hits (`py/boss/swipe_check.py` 108/108, `boss_fight.py`, controls 0 hits in 30 standing pulses vs 8 in 8 airborne).
- **Level end** (README "How a level ends"): boss flag -> 125-frame count -> `$b0b2` -> fade and reload (4.26M steps) -> `$b0ca` -> `$17c9c`
  world-select (Amazon, `py/level_end/win_amazon.repl`, all hit counts match), world 5 -> `$183c0` ending; `$bb79` is a done/unavailable mask and
  unlocks Bermuda after four wins; death goes Game Over -> title, never straight to world-select.
- **The shop** (README "The shop"): the mole is the shop keeper, `$e842` an entrance portal (`$bb77`), prices, bubbles and the TOO MUCH refusal
  driven with real input (poked coins for the purchase).
- **Spawn types** (README "Spawn types"): hit points >= 128 are immune (8 live rows, 0 subtracts), fliers 116-125 reproduced per frame (1,364/1,364),
  the type-251 markers are invisible fruit containers, per-type behaviour tables for 109-132; three earlier readings corrected.
- **Other worlds** (`worlds.md`): loader `$b328` and per-world files, common vs per-world sprite bank ranges, collision categories 5-8, the 53
  exit records of Klondike and Orient (23/23, 30/30), bosses of all five worlds killed with a poked shot, Ice Land slide and conveyor tests.

## Open, in priority order

1. **An unpoked natural run of the Amazon.** Everything on the route and against the boss used health pokes (per segment) and, for the boss, a
   poked weapon in most runs. Needs: the two type-4 upgrades (spawn records at blocks 27 and 134), a dodge policy for the
   bee (kill it with a fire pulse: hp 1, 71 of 99 route hits), and for the boss's type 139/140 shots. Proof: `route_full_real.repl` replayed with the
   `w bb74` lines removed reaching the boss room with health > 0, then `boss_fight.py` with `--weapon` and `--poke-health` removed; watch `$bb74`.
2. **Play a route in another world on real input** (Ice Land is 3 hops, Orient 6, Klondike 12, Bermuda 17): `py/route/route_driver.py` is generic;
   `py/worlds/warp_room.py` stages each room; Ice Land first. Category 7 (slide) and 5/6/8 mechanics are proven on poked positions only.
   Also kill Klondike's or Orient's boss and run the level-end chain (only the Amazon's and poked flags for Ice Land and Bermuda were run).
3. **What water (category 9) costs.** About seven 1-hp drops at the water surface on the route have no `$e80e` contact (inferred from timing).
   Prove with a census `bp eb8c` (the `sub.b D0,$bb74` decrement) against the `$e80e` contacts, then drop the hero into a pit on purpose.
   Same census for the unidentified drain in room `299..318` (1 hp at a time, 18 to 15).
4. **Shop items other than the worm can** (bomb code 2, laser gun 3, extended bar 5 at (72,56), (104,120), (160,88); shelves need the shop ladder at
   about x=136): poke coins to 255, fire on each good, watch `$bb72`, `$227fa`, `$bb74/75`. Re-run the shop branch from `real_seg4_wall_hop.snap`.
5. **Unproven spawn-type readings:** 118, 121, 122 (and 119/120) and 131/132 have no live object (warp to a room whose spawn columns hold them
   and run `py/spawn/verify_fliers.py`); 128's mirrored trigger, 109's sideways push, the crocodile dropping a rider, later monkey throws; special-fire
   shots (`$227fa` 1-3, `$013ae2`); the coconut and plant-spit line steppers.
6. **Per-world code and data:** `$ee16` death dispatch, `$ea92` shop records, `$c028` words 0-1, `$bb7d` cheat-name effects (LUMBAJAK ... in the
   name entry, read from code only), name entry to its end, Orient categories 5/8, Bermuda's 17-hop chain on real input, the Klondike bank-2
   residue's source (`SELECT44.DAT`, not compared byte for byte).
7. **Graphics gaps:** title, world-select and ending art formats (`PICTURES.DCH`, `SELECT44.DAT`), animation order per action, the `$216e2` flash palette.
8. **Merge the two route drivers** (`py/route/route_driver.py` and `py/shop/route_driver.py` overlap) and add categories 5-8 to `tiles.py --cats` /
   `level_map.py` (`worlds/world_pipeline.py` and `render_world.py` patch them at runtime).

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps" (the 104th pass added the health-poke side effects, the 24,000-step
frame, extents from LSD! headers, `spawn_list.py` on non-mid-level snapshots and world-select lock behaviour). Still open here:

- **Agent-written scripts read and write `scratchpad/impossamole/agents/<area>/`**, so a fresh checkout without that scratchpad cannot rerun the
  `.repl` replays (they `snap` into it and several start from snapshots there). `scratchpad/ANCHORS.md` lists what is needed.
- **Two route drivers exist** (`py/route/`, `py/shop/`); use `py/route/route_driver.py` for new work.
- **`route_full_real.repl` takes about 4 minutes and the hazard census about 12**; run them in the background.
- A gate run from `py/` mutates snapshots under `agents/` (`win_amazon.repl` rewrites `agents/wsel/win_amazon_worldselect.snap`); results are
  deterministic, so a changed byte means a real regression.

## Next session

Open item 1: from `pass103/room188.snap`, replay the chain without the health pokes to see where an unpoked hero dies (bees first), add a bee-kill
step (fire pulse when level) to the driver, then attempt the boss with the weapon reached by pickup. If that is too costly for one session, take item
2 for Ice Land (3 hops) with the same driver. Do not re-derive the map, room tables, spawn lists, spawn-type layouts, boss data, shop or level-end
chain: they are in the README, `graphics.md`, `worlds.md` and the scripts.
