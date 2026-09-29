# Impossamole: handoff

Updated 2026-09-29 by the 105th-pass session (damage budget of the Amazon route, unpoked run attempt, Design digest); the work commits are
listed by `git log --oneline -4`, the last being this handoff.

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `pass99/`, `pass103/`, `agents/<area>/`
  (`hop3`, `hop4`, `boss`, `spawn`, `wsel`, `world12`, `world34`) and the new `agents/natural/` (`hop3/` unpoked segment snapshots, logs and
  `.repl` files, `census_*` snapshots and `.out` files, `route_unpoked.repl`, probe scripts). Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source `~/GitHub/hatari/`. TOS ROM `M68000/TOS100UK.IMG`.
- Start from: `pass103/room188.snap` (room `188..285`, weapon 3, 25 coins, health 18) for the route; `agents/hop4/boss_room_real_settled.snap`
  for the boss; `agents/world12/{klondike,orient}_gameplay.snap` and `agents/world34/snaps/{ice,bermuda}_gameplay.snap` for other worlds.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"`** (relative to
  `M68000/`) and `ATARI_NOTRACE=1`; the REPL stops at the first unknown line (no `#` comments); `snap <path>` is relative to the dotnet process's
  directory; `watch <addr> <len>` takes a decimal length and reports on stderr; `w <addr> <8 hex digits>` writes a longword.
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` carries a pre-existing whitespace-rewrap diff (not this
  workstream's); `.obsidian/` and `Cadaver/` are untracked.

## Proven so far

See `reversing/impossamole/README.md` (Amazon, and its new "Design digest"), `graphics.md`, `worlds.md`; scripts in `py/` (`py/README.md`).

- **Hand-written 68000 assembly; graphics chain decoded**: 97.4-98.8 % pixel match on all five worlds (`py/tiles.py --check`).
- **The whole Amazon route to the boss room on real input** (health poked per segment): 11 + 5 driven segments replay byte-identically
  (`py/route/verify_route.py` ALL IDENTICAL; `py/shop/real_replay_check.sh`).
- **Boss killed by real input, no shot poke** (`py/boss/`): weapon 1/2/3 in 60/30/20 hits; only a jumping hero overlaps the swipe.
- **Level end, shop, spawn types, other worlds**: README "How a level ends", "The shop", "Spawn types"; `worlds.md` (loader, banks, categories 5-8,
  53 exit records 23/23 and 30/30, five bosses).
- **What the Amazon route costs in health (105th pass).** Two decrement sites of `$bb74`: `$eb8c` (object contact, `$227f6` written at `$e82e`) and
  `$ebca` (category-9 tile path: 1 hp, cooldown 3, forced hit-reaction jump). `hits n eb8c ebca` over `route_full_real.repl` (7,397 commands,
  final snapshot byte-identical to the live one): `$eb8c` 96, `$ebca` 9 (92 and 9 before the block-283 exit, 4 and 0 in room `299..318`). Room
  `299..318`'s "unidentified drain" is `$0142be` fliers x3 and `$015c7a` x1 (`py/route/contact_census.py`). The chasing bee is 71 of 99
  contacts only because a poked hero idles in the pits for 12M steps; one swipe kills it for good (README "What the route costs in health").
- **Unpoked hop 3 dies** (`py/route/natural_hop3.py`, three guard variants: bee pulse only, fire pulse at killable enemies ahead within 34/50 px plus
  hops over immune ones): health 18, 15, 14, 12, 10 at the ends of segments 1-5, dead in the segment-6 pits (8 water hits, 2 contacts). README
  "Unpoked, the same route does not survive".

## Open, in priority order

1. **An unpoked natural run of the Amazon.** Measured budget: about 8 hp to walkers and hoppers in segments 2-5, 10 in the four pits, then segments
   7-10 (fliers `$0142be` hp 255, plants `$015ac8` hp 4, monkeys `$015934` hp 8), against 18 hp and heals at blocks 244, 302 (46 and 140 are
   earlier). Needs (a) an approach model for the hp-8 monkey and hp-4 plant (they come diagonally from above; three swipes at 6-frame cooldown
   is longer than their approach) so it is killed or hopped, (b) a pit crossing that lands on a crocodile with the jaws shut (animation entry
   frames 140/144 of `$015d26`, `$e5fe` carries the hero) instead of the water, (c) a pickup step (heal at block 244), (d) the two type-4 upgrades
   at blocks 27 and 134 from the level start. Proof: `natural_hop3.py` (or its successor) reaching room `299..318` with health > 0 and no `w bb74`,
   then `route_full_real.repl`'s second half and `boss_fight.py --weapon` removed. Cheaper first cut: run each segment from a poked hp 18 and count
   hp lost per segment under a policy, to rank which policy is worth building.
2. **Play a route in another world on real input** (Ice Land 3 hops, Orient 6, Klondike 12, Bermuda 17): `py/route/route_driver.py` is generic;
   `py/worlds/warp_room.py` stages each room; Ice Land first. Category 7 (slide) and 5/6/8 mechanics are proven on poked positions only. Also kill
   Klondike's or Orient's boss and run the level-end chain. Use `contact_census.py` on each segment to know its hp cost first.
3. **Shop items other than the worm can** (bomb code 2, laser gun 3, extended bar 5 at (72,56), (104,120), (160,88); shelves need the shop ladder
   at about x=136): poke coins to 255, fire on each good, watch `$bb72`, `$227fa`, `$bb74/75`. Re-run the shop branch from `real_seg4_wall_hop.snap`.
4. **Unproven spawn-type readings:** 118, 121, 122 (and 119/120) and 131/132 have no live object; 128's mirrored trigger, 109's sideways push, the
   crocodile dropping a rider, later monkey throws; special-fire shots (`$227fa` 1-3, `$013ae2`); the coconut and plant-spit line steppers.
5. **Per-world code and data:** `$ee16` death dispatch, `$ea92` shop records, `$c028` words 0-1, `$bb7d` cheat-name effects, name entry to its end,
   Orient categories 5/8, water cost in the other worlds (same `$eb8c`/`$ebca` census), Bermuda's 17-hop chain, the Klondike bank-2 residue.
6. **Graphics gaps:** title, world-select and ending art formats (`PICTURES.DCH`, `SELECT44.DAT`), animation order per action, the `$216e2` palette.
7. **Merge the two route drivers** (`py/route/route_driver.py` and `py/shop/route_driver.py`) and add categories 5-8 to `tiles.py --cats` / `level_map.py`.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". Still open here:

- **A recorded `.repl` ends in `snap` lines that write into `scratchpad/impossamole/agents/<area>/`.** Replaying a modified copy (health pokes
  stripped, `s n` turned into `hits n ...`) overwrites the reference snapshots (`boss_room_real_settled.snap`) unless the paths are rewritten first;
  the 105th pass caught it before the run had reached the first `snap`. `sed -E 's#agents/hop4/#agents/natural/#'` (BSD sed needs `-i ''`).
- **A guard that tests `hp > 0` for "alive" keeps attacking a dying object**: hit points go to 254 on death (immune range), so use `0 < hp < 128`.
- **`nohup cmd &` inside a `run_in_background` shell returns at once and a REPL's redirected stdout is block-buffered until exit**: the output
  file looks empty or truncated while the emulator still runs. Wait with `until ! pgrep -f <cmd>`.
- **Agent-written scripts read and write `scratchpad/impossamole/agents/<area>/`**, so a fresh checkout without that scratchpad cannot rerun
  the `.repl` replays; `scratchpad/ANCHORS.md` lists what is needed.
- **Two route drivers exist** (`py/route/`, `py/shop/`); use `py/route/route_driver.py` for new work.
- **`route_full_real.repl` takes about 4 minutes, the hazard census about 12, `natural_hop3.py` about 6**; run them in the background.
- A gate run from `py/` mutates snapshots under `agents/` (`win_amazon.repl` rewrites `agents/wsel/win_amazon_worldselect.snap`); results are
  deterministic, so a changed byte means a real regression.

## Next session

Item 1, cheaper first cut: from `room188.snap` run each hop-3 segment separately with health poked to 18 at its start, under two policies (walk
straight; swipe-when-ahead plus hop), and tabulate hp lost per segment with `hits eb8c ebca` to see which segments a policy has to fix. Build the
croc-timed pit crossing for segment 6 first (8 of the route's 9 water hits), since no swipe policy helps there. If that finishes, chain
segments 7-11 unpoked; otherwise take item 2 for Ice Land. Do not re-derive the map, room tables, spawn lists, spawn-type layouts, boss data, shop,
level-end chain or the route's hp budget: they are in the README, `graphics.md`, `worlds.md` and the scripts.
