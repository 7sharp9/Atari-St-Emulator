# Impossamole: handoff

Updated 2026-09-29 by the 106th-pass session (unpoked hop 3 with a helper agent); the work commit is the one before this handoff in
`git log --oneline -3`.

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `pass99/`, `pass103/`, `agents/<area>/` and the new
  `agents/unpoked/` (every stage of `py/route/unpoked_hop3.py`; `s11/seg11_shaft_exit.snap` is the unpoked start of room `299..318`, health 11,
  weapon 3). Earlier hand-run copies: `agents/natural/seg6/`, `agents/policy/`. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source
  `~/GitHub/hatari/`. TOS ROM `M68000/TOS100UK.IMG`.
- Start from: `agents/unpoked/s11/seg11_shaft_exit.snap` for hop 4 unpoked; `pass103/room188.snap` for hop 3; `agents/hop4/boss_room_real_settled.snap` for the
  boss; `agents/world12/{klondike,orient}_gameplay.snap` and `agents/world34/snaps/{ice,bermuda}_gameplay.snap` for other worlds.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"`** (relative to `M68000/`) and
  `ATARI_NOTRACE=1`; the REPL stops at the first unknown line (no `#` comments); `snap <path>` is relative to the dotnet process's directory;
  `watch <addr> <len>` takes a decimal length and reports on stderr; `w <addr> <8 hex digits>` writes a longword.
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` carries a pre-existing whitespace-rewrap diff (not this
  workstream's); `.obsidian/` and `Cadaver/` are untracked.

## Proven so far

See `reversing/impossamole/README.md` (Amazon, "Design digest"), `graphics.md`, `worlds.md`; scripts in `py/` (`py/README.md`).

- **Hand-written 68000 assembly; graphics chain decoded**: 97.4-98.8 % pixel match on all five worlds (`py/tiles.py --check`).
- **Amazon route to the boss room on real input** with health poked per segment: 11 + 5 driven segments replay byte-identically
  (`py/route/verify_route.py` ALL IDENTICAL; `py/shop/real_replay_check.sh`). Boss killed by real input (`py/boss/`), level end, shop, spawn types, other
  worlds' loaders and bosses: README and `worlds.md`.
- **Hop 3 (`188..285` to the block-283 exit) is playable with no health poke** (`py/route/unpoked_hop3.py`, 106th pass): one recorded file of 7720 commands
  replays in a single process from `room188.snap` to a snapshot byte-identical to the live one, health 11 (`$bb74` in `room188.snap` is already
  `12120300`, so the leading `w` is a no-op). Segments 1-5 lose 2 hp under the `BEST` guard (`py/route/policy.py`: bee rule, monkey snipe from the air,
  lure-and-kill; ablation 6/5/3 hp without each), the four pits 0 hp by a rollout search over the take-off delay that lands on a shut-jawed crocodile
  (`pits.py`, `auto_pits.py`; croc jaw entries 10-13, 18-19, 30-44 of 45, patrol 1 px per frame, hero back offset 5..22), segments 7-11 lose 5 hp
  (7: 0 by start delay 24, 8: 5, 9 and 10: 0 by wait points, 11: 0). README "Unpoked, hop 3 is playable".
- **A start delay does nothing for enemies that spawn as the camera arrives** (segment 8: every delay 0-132 frames loses 6); waits placed just before the
  hazard (`wait_opt.py`) do change patrolling ones (fliers `$0142be`, `$015b3c`).

## Open, in priority order

1. **Hop 4 unpoked (room `299..318` to the boss room) and the boss without pokes.** The route costs 4 contact hp at the tunnel wall (wx 9900-9954: fliers
   `$0142be` x3, `$015c7a` x1) with a heal at block 302; from health 11 that is affordable. The segments live in `py/shop/route_driver.py` (`--real`, five
   segments from `agents/hop3/room299.snap`), a second driver: merge it into `py/route/route_driver.py` (open item 7) or wrap its segment functions in
   `Driver` subclasses, then run `segsweep.py`/`wait_opt.py` from `agents/unpoked/s11/seg11_shaft_exit.snap`. Proof: recorded input reaching the boss room with
   health > 0 and no `w bb74`, replayed byte-identically; then `boss/boss_fight.py --weapon` removed (the natural kill was marginal: 2 of 12 unpoked runs).
2. **Hops 1 and 2 (`118..137`, `160..173`) and the start room unpoked**, plus the two type-4 upgrades at blocks 27 and 134 (`room188.snap` already carries
   weapon 3, 25 coins). The same `policy.py` guard and search scripts apply; the segments are in `py/start_room_route.repl` form, so they need `Driver`
   segment functions first. Goal: the whole Amazon from the first screen with no poke and no staged snapshot.
3. **Segment 8's 5 hp and the two unfixed drops:** monkey `$015934` (segment 8 near wx 8230), leaf bush `$015d9c` (walks 3 px/frame once triggered), rock `$01439e`
   (immune, at the stone roof wx 8384, 2 hp), the two temple-exit fliers (wx 8540-8558); segment 3's crocodile drop (1 hp) and segment 5's tentacle (1 hp).
   `POLICY=BEST wait_opt.py seg8_stairs_roof ...` was only tried once by hand (BEST alone: 5 hp) and not combined with waits. Proof: a lower total in the
   `stage3_*.out` logs with the replay still IDENTICAL.
4. **Play a route in another world on real input** (Ice Land 3 hops, Orient 6, Klondike 12, Bermuda 17): `py/route/route_driver.py` is generic, `py/worlds/warp_room.py`
   stages each room; the search scripts and `contact_census.py` tell the hp cost first. Category 7 (slide) and 5/6/8 mechanics are proven on poked positions only.
5. **Shop items other than the worm can** (bomb 2, laser gun 3, extended bar 5 at (72,56), (104,120), (160,88); shelves need the shop ladder at about x=136).
6. **Unproven spawn-type readings:** 118, 121, 122 (and 119/120) and 131/132 have no live object; 128's mirrored trigger, 109's sideways push, the crocodile
   dropping a rider, later monkey throws; special-fire shots (`$227fa` 1-3, `$013ae2`); the coconut and plant-spit line steppers.
7. **Per-world code and data:** `$ee16` death dispatch, `$ea92` shop records, `$c028` words 0-1, `$bb7d` cheat-name effects, name entry to its end, Orient
   categories 5/8, water cost in the other worlds, Bermuda's 17-hop chain, the Klondike bank-2 residue. **Graphics gaps:** title, world-select and ending art
   formats (`PICTURES.DCH`, `SELECT44.DAT`), animation order per action, the `$216e2` palette. **Merge the two route drivers** and add categories 5-8 to `tiles.py --cats`.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". Still open here:

- **A jump's horizontal push is latched at take-off**: `UP` alone jumps straight up and steering in the air does nothing, so a hop needs `UP|dir` held from the
  start, and the hero walks 2-4 px while the game's poll (24-30k steps) picks the jump up. A take-off within about 12 px of a lip walks off it first.
- **`Driver.land` returns as soon as the hero reads grounded twice at the same y**, and a hero standing on a moving crocodile does. Do not use it to wait out
  a ride; `pits.py` `ride_until_hop` reads the crocodile object instead.
- **A search result is tied to the arrival state.** The pit delays, `seg7` delay 24 and the wait points were found for one exact chain; change anything upstream
  (segments 1-5 policy, a delay) and rerun `unpoked_hop3.py --force` (or delete the affected stage's snapshot). Stages are skipped when their snapshot exists.
- **A recorded `.repl` ends in `snap` lines that write into `scratchpad/impossamole/agents/<area>/`.** Replaying a modified copy overwrites the reference
  snapshots unless the paths are rewritten first (`sed -E 's#agents/hop4/#agents/natural/#'`; BSD sed needs `-i ''`).
- **A guard that tests `hp > 0` for "alive" keeps attacking a dying object**: hit points go to 254 on death, use `0 < hp < 128`.
- **`nohup cmd &` inside a `run_in_background` shell returns at once and a REPL's redirected stdout is block-buffered until exit**; wait with `until ! pgrep -f <cmd>`.
  macOS has no `timeout`, and zsh needs `echo "=="` quoted.
- **Agent-written scripts read and write `scratchpad/impossamole/agents/<area>/`**, so a fresh checkout without that scratchpad cannot rerun the `.repl` replays;
  `scratchpad/ANCHORS.md` lists what is needed.
- **Two route drivers exist** (`py/route/`, `py/shop/`); use `py/route/route_driver.py` for new work.
- **Timings:** `route_full_real.repl` about 4 minutes, hazard census 12, `natural_hop3.py` 6, `unpoked_hop3.py` 1 to 1.5 hours the first time (about 1 minute for the replay).
- A gate run from `py/` mutates snapshots under `agents/` (`win_amazon.repl` rewrites `agents/wsel/win_amazon_worldselect.snap`); results are deterministic,
  so a changed byte means a real regression.

## Next session

Item 1: wrap the five hop-4 segments as `Driver` segment functions (or merge the two drivers), start from `agents/unpoked/s11/seg11_shaft_exit.snap`, run the
`policy.py` guard with `segsweep.py`/`wait_opt.py` per segment, then the boss with weapon 3 and no health poke. Check `contact_census.py` on the poked
`real_seg3/4` first to know which contacts (fliers at the tunnel wall) the search has to avoid. Do not re-derive the map, room tables, spawn types, boss data,
shop, level-end chain, the croc mechanics or hop 3's hp budget: they are in the README, `graphics.md`, `worlds.md` and the scripts.
