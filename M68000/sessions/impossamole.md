# Impossamole: handoff

Updated 2026-09-30 by the 107th-pass session (unpoked hop 4, shop and boss; helper agent's secrets and algorithms survey); the work commits are the ones before this handoff in
`git log --oneline -6`.

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `pass99/`, `pass103/`, `agents/<area>/`, `agents/unpoked/` (hop 3 stages, `hop4/`, `hop4s/`
  with the shop branch, `boss/`), `agents/secrets/data/`. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source `~/GitHub/hatari/`. TOS ROM `M68000/TOS100UK.IMG`.
- Start from: `pass103/room188.snap` for the whole recorded run (`agents/unpoked/amazon_unpoked_room188_to_boss_dead.repl`, 3 min 19 s to the dead boss);
  `agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap` for the boss room with health 16; `agents/unpoked/s11/seg11_shaft_exit.snap` for hop 4; `agents/world12/{klondike,orient}_gameplay.snap`
  and `agents/world34/snaps/{ice,bermuda}_gameplay.snap` for other worlds; `agents/secrets/data/name_entry.snap` for the high-score entry.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"`** (relative to `M68000/`) and `ATARI_NOTRACE=1`; the REPL
  stops at the first unknown line (no `#` comments); `snap <path>` is relative to the dotnet process's directory; `watch <addr> <len>` takes a decimal length and reports on stderr;
  `w <addr> <8 hex digits>` writes a longword.
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` carries a pre-existing whitespace-rewrap diff (not this workstream's); `.obsidian/` and `Cadaver/`
  are untracked.

## Proven so far

See `reversing/impossamole/README.md` (Amazon, "Design digest"), `graphics.md`, `worlds.md`, `secrets.md`; scripts in `py/` (`py/README.md`).

- **Hand-written 68000 assembly; graphics chain decoded**: 97.4-98.8 % pixel match on all five worlds (`py/tiles.py --check`).
- **The Amazon from `room188.snap` to a dead boss with no health, weapon or shot poke**: one recorded file of 12,032 commands replays byte-identically (the only `w` is hop 3's no-op
  `w bb74 12120300`); boss at 0 hit points, `$22803 = $ff`, health 10. Pieces: hop 3 `py/route/unpoked_hop3.py` (health 11 at the exit), hop 4 `py/route/route_hop4.py` (2 hp, 1237
  commands), the shop's worm can bought with the natural 100 coins (9 to 16 hp, `route_hop4.py --shop`), the fight `py/boss/boss_unpoked.py` (1 kill in 12 start delays, 20 hits).
  README "Unpoked, the whole Amazon".
- **The boss's damage-7 shot is a lob toward the hero's side** (speed 1 or 2 px per frame from `$016192`, y 121 to 108 then down to 164 on frame 27; `py/boss/shot140_probe.py`); the
  retreat rule keys off it. Earlier facts stand: hop 3 croc pits, `BEST` guard, start delays that do nothing for enemies that spawn as the camera arrives.
- **Secrets and algorithms** (`secrets.md`, `py/secrets/`, all re-run by the parent where noted): the six cheat names (`HEINZ...` has three full stops) and each effect; Space smart bomb
  once per level, Ctrl pause, Esc quit; the crack's five-byte trainer, disabled track-length check and live `DISK.ID` check; LSD! and Huffman depackers (755,712 of 755,712 bytes of the five worlds
  match live RAM); `$1c6de` is a file loader, not a depacker; the `$bef4` generator (200 of 200 calls); the effect engine (189,332 of 189,332 YM register writes) and the music sequencer
  (400 of 400 note-ons per song).

## Open, in priority order

1. **Hops 1 and 2 (`118..137`, `160..173`) and the start room unpoked.** Goal: the whole Amazon from the first screen with no poke and no staged snapshot (the two type-4 upgrades at blocks 27
   and 134 included). The segments are in `py/start_room_route.repl` form, so they need `Driver` segment functions first (as `route_hop4.py` did for hop 4); then `policy.py` `BEST` and
   `segsweep.py`/`wait_opt.py` from the previous segment's snapshot. The heal and shop pattern of hop 4 (two worm cans are stocked, 75 coins each) is the health source. Proof: recorded input
   from a cold boot to `room188.snap`'s state, replayed byte-identically, health above 0.
2. **Boss reliability.** 1 kill in 12 start delays from health 16. Losses are the aimed type-139 shot (flat, 12x12, 1 damage, aimed at the hero's position at spawn) and contact damage, about one
   per 1.5M steps. Two changes to try: dodge the 139 by timing a jump over it (it spawns at about `(229, 101)` and crosses the room in over 40 frames), and fight the boss's left position (x 64) from the
   right side facing left (hero x 88-114) instead of waiting on the platform, which halves the time per kill. Proof: a rate above 6 of 12 delays, one kill replayed identically.
3. **Segment 8's 5 hp and the unfixed drops** (hop 3): monkey `$015934`, leaf bush `$015d9c`, rock `$01439e`, the two temple-exit fliers; segment 3's crocodile drop (1 hp) and segment 5's tentacle
   (1 hp). The block-302 heal (object `(128, 88)` on the `y=96` ledge over the hop-4 start) is unreached: the left ladder is guarded by two `$015b3c` fliers (11 to 8 hp in the one trial); a search
   over their timing could give up to +7. Proof: a lower total in a `stage3_*.out` log with the replay still IDENTICAL.
4. **Play a route in another world on real input** (Ice Land 3 hops, Orient 6, Klondike 12, Bermuda 17): `py/route/route_driver.py` is generic, `py/worlds/warp_room.py` stages each room; the search
   scripts and `contact_census.py` tell the hp cost first. Category 7 (slide) and 5/6/8 mechanics are proven on poked positions only. The cheat names and the trainer's patches apply to every world.
5. **Shop items other than the worm can** (bomb 2, laser gun 3, extended bar 5 at (72,56), (104,120), (160,88); shelves need the shop ladder at about x=136).
6. **Unproven spawn-type readings:** 118, 121, 122 (and 119/120) and 131/132 have no live object; `secrets.md` lists kind-1 types with a descriptor and no static reference (26, 79, 83, 85, 119, 120,
   153, 154, 161, 212, 213, 221, 236) as leads; 128's mirrored trigger, 109's sideways push, the crocodile dropping a rider, later monkey throws; special-fire shots (`$227fa` 1-3, `$013ae2`); the
   coconut and plant-spit line steppers; kind-3 types not enumerated.
7. **Per-world code and data:** `$ee16` death dispatch (now also the smart bomb's dispatch, read), `$ea92` shop records, `$c028` words 0-1, Orient categories 5/8, water cost in the other worlds,
   Bermuda's 17-hop chain, the Klondike bank-2 residue. **Secrets left open** (`secrets.md` "Open"): music at YM-register level (needs a Timer B tick schedule), instrument fields
   (`$db64`..`$dc6e`), E-Motion's trainer, the `$fd0e`/`$22801` mechanism, whether a room change re-arms the smart bomb, the boss-room smart bomb, cheats 3, 5 and 6 through a real name then play.
   **Graphics gaps:** animation order per action, the `$216e2` palette. **Merge the two route drivers** (`py/route/`, `py/shop/`) and add categories 5-8 to `tiles.py --cats`.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". Still open here:

- **A jump's horizontal push is latched at take-off**: `UP` alone jumps straight up and steering in the air does nothing, so a hop needs `UP|dir` held from the start, and the hero walks 2-4 px
  while the game's poll (24-30k steps) picks the jump up. A take-off within about 12 px of a lip walks off it first.
- **`Driver.land` returns as soon as the hero reads grounded twice at the same y**, and a hero standing on a moving crocodile does. Do not use it to wait out a ride; `pits.py` `ride_until_hop`
  reads the crocodile object instead.
- **A search result is tied to the arrival state.** The pit delays, `seg7` delay 24, the wait points and the boss start delay 900,000 were found for one exact chain; change anything upstream and
  rerun (`unpoked_hop3.py --force`, `route_hop4.py --shop`, `boss_unpoked.py --delay`).
- **The boss fight uses `boss/repl.py`'s `Repl`, which does not record.** `boss_unpoked.py --record f.repl` wraps `Repl.run` to keep `kbd`, `s` and `w` lines; without it there is no replayable file.
  A `.repl` ends in `snap` lines that write into `scratchpad/impossamole/agents/<area>/`: replaying a modified copy overwrites the reference snapshots unless the paths are rewritten first.
- **A guard that tests `hp > 0` for "alive" keeps attacking a dying object**: hit points go to 254 on death, use `0 < hp < 128`.
- **`nohup cmd &` inside a `run_in_background` shell returns at once and a REPL's redirected stdout is block-buffered until exit**; wait with `until ! pgrep -f <cmd>`. macOS has no `timeout`,
  and zsh needs `echo "=="` quoted. In a `for` loop of `( cmd & )` jobs, wait with that `until` loop inside a `timeout: 600000` call; a 120 s tool timeout backgrounds it.
- **Agent-written scripts read and write `scratchpad/impossamole/agents/<area>/`**, so a fresh checkout without that scratchpad cannot rerun the `.repl` replays; `scratchpad/ANCHORS.md` lists what is needed.
- **Two route drivers exist** (`py/route/`, `py/shop/`); use `py/route/route_driver.py` for new work. `route_hop4.py` re-uses it.
- **Timings:** `route_full_real.repl` about 4 minutes, hazard census 12, `natural_hop3.py` 6, `unpoked_hop3.py` 1 to 1.5 hours the first time (about 1 minute for the replay), `route_hop4.py --shop` a few minutes (not timed),
  one boss fight 40 s, the whole recorded chain 3 min 19 s.
- A gate run from `py/` mutates snapshots under `agents/` (`win_amazon.repl` rewrites `agents/wsel/win_amazon_worldselect.snap`); results are deterministic, so a changed byte means a real regression.

## Next session

Item 1: wrap the start room and hops 1-2 (`py/start_room_route.repl`) as `Driver` segments in a `route_hop1_2.py` like `route_hop4.py`, run `policy.py` `BEST` and the sweeps from a cold-boot start room, then
chain into `room188.snap`'s state. If that stalls on the start room's enemies, switch to item 2 (a 139 dodge and the right-side left-position fight) to lift the boss from 1 of 12. Do not
re-derive the map, room tables, spawn types, boss data, shop, level-end chain, croc mechanics, hop 3/4 budgets, the cheats or the packers: they are in the README, `graphics.md`, `worlds.md`,
`secrets.md` and the scripts.
