# Impossamole: handoff

Updated 2026-09-29 by the 103rd-pass session (route walk and spawn types); the last work commit is `0bd6ae7`, and the
skill commit and this handoff follow it (`git log --oneline -4`).

## Resume point

- Last work commit of this workstream: `0bd6ae7` "impossamole: 103rd pass -- spawn types decoded (descriptor layouts,
  38 types drawn), bank 2 is 172 frames not 140"; before it `3809a60` (three route exits with real input).
- Working data: `M68000/scratchpad/impossamole/` (gitignored): `pass99/` (`cyc0..7.snap`, `boss_room.snap`, `warp_up112.snap`,
  ...), `pass103/` (checkpoints of `py/start_room_route.repl` plus `live_*.snap`), `pass102/`. `scratchpad/ANCHORS.md` indexes
  them. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source `~/GitHub/hatari/`. TOS ROM `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/pass103/room188.snap` (room `188..285`, just entered by real input through block 168,
  camera `$1780`, hero `x=$60`, health full). Any Amazon snapshot has the map, tables, tile bank and sprite banks resident.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"`**
  (path relative to `M68000/`) and `ATARI_NOTRACE=1`. The REPL stops at the first unknown line (no `#` comments); `snap <path>`
  is relative to the dotnet process's directory; `watch <addr> <len>` takes a decimal length; `w <addr> <8 hex digits>`
  writes a longword; there is no register-set command.
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` carries a pre-existing whitespace-rewrap
  diff (not this workstream's); `.obsidian/` and `Cadaver/` are untracked.

## Proven so far

See `reversing/impossamole/README.md` for detail, match counts and addresses:

- **The program is hand-written 68000 assembly.** Live `watch`/`bpc`/`callcap` plus `disassemble.py --all` is the path.
- **Graphics are decoded (`graphics.md`).** Level (`$27600`) -> block definitions (`$29000`) -> tile bank (`$29800`), 98-99 % of
  sampled pixels match the live screen (`py/tiles.py --check`). Sprite bank 1 (`$3b600`, 240 x 16x16) and **bank 2 (`$42e00`,
  172 frames, 32x24; the earlier "140" was wrong)**, font, palettes. `graphics/sprites_bank2.png` now shows all 172.
- **Spawn types (103rd pass, README "Spawn types", `py/spawn_types.py`, `graphics/amazon_spawn_types.png`).** Descriptor layouts
  for kind 0 and kind 1 read off `$10056`/`$100ec`; 38 types decoded and drawn. Picture identity checked against the live
  screen for bees (114/115), snakes (127), chameleons (128/129), rock (113), fliers (117, 125), monkey (109), plant (112):
  best matches 80/80 to 566/566 (`py/spawn_types.py --check`). Kind 1 `hp` 254/255 presumably means unkillable (untested).
- **Route hops with real input (103rd pass, README "Three exits fired from positions reached by real joystick input",
  `py/start_room_route.repl`).** From `warp_up112.snap` (poked to the block-151 exit) to room `188..285`: blocks 135 and 168 (and
  131 by an alternative fall) fired with every predicted field matching. Ladder, shaft-hop and top-out mechanics are in the
  README. The replay is byte-identical to the interactive run (`cmp`). Health is poked at each segment start; the staging into
  room `118..137` is a labelled poke.
- **Hazard/collision, jump and camera-follow, the level as one 1680x24 tile map of rooms, the boss (60 hit points, handler
  `$15e9a`, damage path `$13a9c`) and boss death ending the level** are proven (README "Past the first screen", "The level is
  one tile map", "Boss").

## Open, in priority order

1. **Finish the route on real input: hop 3 (block 283) and hop 4 (block 317).** Room `188..285` is 3104 px: a jungle half (water
   pit at blocks 203..206, more further on) and a stone-temple half; the exit is the shaft at block 283 with a ladder and bead
   platforms (`level_rooms.py` graph, art in `graphics/amazon_level_tiles.png` blocks 261..284). Then room `299..318` down through
   block 317 into the boss room. The stepwise REPL drive costs about 6 tool calls per 100 px; write an event-driven driver (poll
   hero state, act on state changes) instead of hand nudging.
2. **Natural aim at the boss.** The boss is at `y=96` and shots fly along the hero's `y`; find where the hero must stand and which
   weapon (`$bb72`) makes 60 hit points reachable without the position poke.
3. **What is left of the spawn types.** Which sub-animation each handler selects (the frame lists are not delimited per object);
   what separates types 116-125 (descriptor `+4`, `+14`, `+16`); what the 63 type-251 markers are (dormant effect: blank, smoke
   rings, explosion); whether types 0/9 (mole climbing out of the ground, blocks 416 and 313, handler `$e842`) are the shop; what
   `hp` 254/255 does in `$13a9c`; the kind-3 allocator (no record in this level). Prove the shop by reaching a type-9 object with
   `bpc $e842`.
4. **World-select return and the world-5 branch after `$b0b2`** (the `$1c3c8` fade runs longer than 4M steps; `hits` on
   `$b0ca`/`$17c9c` with 10M steps).
5. **Graphics gaps** (`graphics.md` "Open"): other worlds' tile banks, blocks, levels (fresh cold boot per world; `py/tiles.py` works
   unchanged); title/world-select/logo art and disk files; animation order per action; the `$216e2` flash palette.
6. Slot 8's patrol rate; Orient/Ice Land/Bermuda from a fresh cold boot; whether slots 9/10 move.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". From this pass:

- **A stated bank size can be wrong.** The 102nd pass's "bank 2 = 140 frames" hid 32 frames of enemies and made the first
  spawn-type sheet miss bees, crocodiles, chameleons and the boss face. Scan for the last non-zero frame.
- **`$227b4` is the leftmost visible block (`camera >> 5`), not only the room start**: it equals the start block just after an install
  and tracks the scroll afterwards. Read the camera `$227b6` when checking a room.
- **Ladder climbs stall if the hero's `x` is misaligned**: state 4 climbs only while `$227ec`/`$227ed` are category < 4, and the
  sensors refresh only when `y & 7 == 0`. Steer sideways on the ladder, step down once, climb again. Release up at the top or
  the hero jumps.
- **The hero is pinned at `x=192` while the camera scrolls**, so hero `x` alone shows no progress; sample `$227b6`.
- **Rebuild a long driven chain from the saved segment files, not from memory** (one wrong nudge count broke the first replay).
- **The transition takes hundreds of thousands of steps** (`$1c3c8` fade); sample well after a poked or reached trigger.
- **Object slots are live-spawned by camera position**, so a slot number is only meaningful on one screen.
- **Driving the REPL from Python needs a sentinel**; **`watch` on a counter floods stdout**; `timeout` does not exist on the Mac.
- Health poked per segment removes the death risk but also the natural-play evidence; label pokes.

## Next session

Open item 1: start from `pass103/room188.snap`, write a small event-driven driver (poll `$227f3`, hero `x`/`y`, camera, health;
act on state changes) and walk room `188..285` to the block-283 shaft, then the last hop into the boss room. If a hazard needs
health poked, label it. Item 3's shop check (`bpc $e842` near a type-9 object) is a cheap side proof once a snapshot is near
block 313. Do not re-derive the map, room table, spawn list, spawn-type layouts, boss data or the graphics chain: they are in the
README, `graphics.md` and the scripts.
