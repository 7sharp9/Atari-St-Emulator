# Impossamole: handoff

Updated 2026-10-31 by the 108th-pass session (boss reliability 13 of 24; cold-boot start room segments 1-3); the work commit is `9650ffe`, the one before this
handoff.

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `pass99/`, `pass103/`, `agents/<area>/`, `agents/unpoked/` (hop 3 stages, `hop4/`, `hop4s/`
  with the shop branch, `boss/`), `agents/secrets/data/`, and `pass108/` (not yet in `ANCHORS.md`: another session had that file uncommitted): `start_install.snap` (rebuilt in 17 s by
  `py/route/coldboot_start_room.repl`), `route/` and `nohop/` (start-room segments), `sweep/`, and `boss/` (every sweep's `.out` per delay from `py/boss/sweep_delays.sh`, `kill_d700000.repl` and its snapshots). Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source `~/GitHub/hatari/`. TOS ROM `M68000/TOS100UK.IMG`.
- Start from: `pass108/start_install.snap` for the start room (hero not yet placed; `route_hop1_2.py` waits for it), `pass108/nohop/BEST/seg3_pit_a.snap` for its furthest point (wx 692, health 12);
  `pass103/room188.snap` for the whole recorded run (`agents/unpoked/amazon_unpoked_room188_to_boss_dead.repl`, 3 min 19 s to the dead boss);
  `agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap` for the boss room with health 16; `agents/unpoked/s11/seg11_shaft_exit.snap` for hop 4; `agents/world12/{klondike,orient}_gameplay.snap`
  and `agents/world34/snaps/{ice,bermuda}_gameplay.snap` for other worlds; `agents/secrets/data/name_entry.snap` for the high-score entry.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"`** (relative to `M68000/`) and `ATARI_NOTRACE=1`; the REPL
  stops at the first unknown line (no `#` comments); `snap <path>` is relative to the dotnet process's directory; `watch <addr> <len>` takes a decimal length and reports on stderr;
  `w <addr> <8 hex digits>` writes a longword.
- Uncommitted work left behind: none from this session. `scratchpad/ANCHORS.md` and `reversing/powermonger/commander/README.md` carry other sessions' diffs; `Cadaver/` is untracked.

## Proven so far

See `reversing/impossamole/README.md` (Amazon, "Design digest"), `graphics.md`, `worlds.md`, `secrets.md`; scripts in `py/` (`py/README.md`).

- **Hand-written 68000 assembly; graphics chain decoded**: 97.4-98.8 % pixel match on all five worlds (`py/tiles.py --check`).
- **The Amazon from `room188.snap` to a dead boss with no health, weapon or shot poke**: one recorded file of 12,032 commands replays byte-identically (the only `w` is hop 3's no-op
  `w bb74 12120300`); boss at 0 hit points, `$22803 = $ff`, health 10. Pieces: hop 3 `py/route/unpoked_hop3.py` (health 11 at the exit), hop 4 `py/route/route_hop4.py` (2 hp, 1237
  commands), the shop's worm can bought with the natural 100 coins (9 to 16 hp, `route_hop4.py --shop`), the fight `py/boss/boss_unpoked.py` (1 kill in 12 start delays, 20 hits).
  README "Unpoked, the whole Amazon".
- **The boss is about an even chance unpoked** (`py/boss/boss_dodge139.py --reach 100 --t-lo 4 --t-hi 10 --max-iter 12000`): 13 kills in 24 start delays from health 16 against 3 in 24
  for the old policy at the same cap (the subclass with both changes off reproduces `boss_unpoked.py` run for run); one kill (delay 700,000, health 6, 5141 commands) replays IDENTICAL.
  The two changes: retreat 100 px from the 140's spawn point (at 80 it hit for 7 at x 152-154, where the floor is 8 px lower) and a straight jump when a 139 is due in 4-10 frames.
  README "Unpoked, the whole Amazon", "Dodging the 139". The left-position fight from the right side fails (step at x 118, the hop lands in the boss's contact box).
- **The cold-boot start room on real input is begun** (`py/route/coldboot_start_room.repl`, `route_hop1_2.py` seg1-3, `hop12_sweep.py`): 6 hp lost in the first 600 px with weapon 1, the same
  for every start delay 0-112 frames (the flier `$015b3c`, the monkey `$015934` drop, a snake `$015c82` and two water hits in pit A, whose crocodile reads hp 254).
- **The boss's damage-7 shot is a lob toward the hero's side** (speed 1 or 2 px per frame from `$016192`, y 121 to 108 then down to 164 on frame 27; `py/boss/shot140_probe.py`); the
  retreat rule keys off it. Earlier facts stand: hop 3 croc pits, `BEST` guard, start delays that do nothing for enemies that spawn as the camera arrives.
- **Secrets and algorithms** (`secrets.md`, `py/secrets/`, all re-run by the parent where noted): the six cheat names (`HEINZ...` has three full stops) and each effect; Space smart bomb
  once per level, Ctrl pause, Esc quit; the crack's five-byte trainer, disabled track-length check and live `DISK.ID` check; LSD! and Huffman depackers (755,712 of 755,712 bytes of the five worlds
  match live RAM); `$1c6de` is a file loader, not a depacker; the `$bef4` generator (200 of 200 calls); the effect engine (189,332 of 189,332 YM register writes) and the music sequencer
  (400 of 400 note-ons per song).

## Open, in priority order

1. **Hops 1 and 2 (`118..137`, `160..173`) and the start room unpoked.** Goal: the whole Amazon from the first screen with no poke and no staged snapshot (the two type-4 upgrades at blocks 27
   and 134 included). Started: `route_hop1_2.py` has seg1-3 (to box 2, wx 692) from `pass108/start_install.snap`, 6 hp lost, start delay no help. The binding constraint is the health
   budget: at that rate the 4400 px room plus hops 1-2 cost far more than 18, and the recorded room-188 chain starts there with 18, so each segment needs the hop-3 treatment (wait points by
   `wait_opt.py`-style search, kills timed against the monkey drop, the pit-A crocodile phase), and the route must take the type-5 heal at block 46 (col 186) and the upgrade at block 27
   (col 110, y 80, from the ledge over the ladder at cols 104-105) early, since weapon 1 needs 8 swipes for a monkey. Not tried: wait points, a kill-first policy for the monkey, the
   crocodile-phase search for pit A, any terrain past wx 692 (camera `$5ac` to `$ec0` has never been walked by any pass). Proof: recorded input from a cold boot to `room188.snap`'s
   state, replayed byte-identically, health above 0.
2. **Boss reliability past one half.** 13 of 24 with `boss_dodge139.py`. Of 266 health drops in those runs, 254 are 1-point (143 airborne during the jump-and-fire phases, 111 grounded),
   12 are lobs. Next levers: dodge or abort during `air_phase` (it fires blind to a 139 in flight), and pick the recording's start delay from the sweep (the 700,000 kill is the reference).
   Proof: a rate above 18 of 24 on the same two delay sets.
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
- **`multiprocessing.Pool` workers on macOS are spawned, not forked**: a module global set in the parent (`route_hop1_2.SET` from `--set`) is empty in the workers, so the first
  `hop12_sweep.py` run silently used plain `BEST`; pass such overrides in the task arguments.
- **Two route drivers exist** (`py/route/`, `py/shop/`); use `py/route/route_driver.py` for new work. `route_hop4.py` re-uses it.
- **Timings:** `route_full_real.repl` about 4 minutes, hazard census 12, `natural_hop3.py` 6, `unpoked_hop3.py` 1 to 1.5 hours the first time (about 1 minute for the replay), `route_hop4.py --shop` a few minutes (not timed),
  one boss fight 40 s, the whole recorded chain 3 min 19 s.
- A gate run from `py/` mutates snapshots under `agents/` (`win_amazon.repl` rewrites `agents/wsel/win_amazon_worldselect.snap`); results are deterministic, so a changed byte means a real regression.

## Next session

Item 1, start room: from `pass108/nohop/BEST/seg3_pit_a.snap`, scout past wx 692 with `route_hop1_2.py --guard explore` (labelled refills) to get the hurt census of the whole start room
and hops 1-2 first, then cut it into segments and search each (`hop12_sweep.py`, a `wait_opt.py` port) before chaining unpoked. Decide early from the census whether 18 hp can reach
room 188 at all with the block-46 heal; if not, say so and return to item 2 (dodging the 139 inside `air_phase`). Do not re-derive the map, room tables, spawn types, boss data, shop,
level-end chain, croc mechanics, hop 3/4 budgets, the cheats or the packers: they are in the README, `graphics.md`, `worlds.md`, `secrets.md` and the scripts.
