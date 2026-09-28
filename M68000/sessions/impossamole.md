# Impossamole: handoff

Updated 2026-09-28 by the session that ended at the 99th-pass commit (see `git log`).

## Resume point

- Last commit of this workstream: the 99th pass, "impossamole: 99th pass -- the level is one tile map
  of connected rooms ..." plus a follow-up doc commit for the level-end paragraph (`git log --oneline -4`).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/`, `gameplay_explore/` (older trials) and `pass99/` (this pass: `cyc0..7.snap`,
  `warp_down131b.snap`, `warp_up112.snap`, scripts `cyc.repl`/`hops6.repl`). `scratchpad/ANCHORS.md`
  indexes them. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source at
  `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/pass99/cyc5.snap` (Amazon, camera `$57a`, hero alive on the ground,
  health poked to full) for anything about the map, rooms or spawns (all resident in RAM, any Amazon
  snapshot works). `pass98_item_try.snap` / `pass90_wall_192.snap` are the older natural-play anchors.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) and `ATARI_NOTRACE=1`. The REPL stops at the first
  unknown line (no `#` comments); `snap <path>` writes relative to the dotnet process's directory, give
  the full path; `watch <addr> <len>` takes a **decimal** length; `w <addr> <8 hex digits>` writes a
  longword (`w bb74 12120300` sets health `$12` and keeps `$bb76=3`).
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` still carries the
  pre-existing whitespace-rewrap diff (not this workstream's), and `.obsidian/`, `Cadaver/` are untracked.

## Proven so far

See `reversing/impossamole/README.md` for detail, match counts and addresses:

- **The program is hand-written 68000 assembly.** No decompile route; live `watch`/`bpc`/`callcap` plus
  `disassemble.py --all` is the path.
- **Hazard/collision, jump and camera-follow mechanisms** are proven (README "Past the first screen":
  `$00b71a`/`$00e80e`/`$00e82e`/`$00eb8c`/`$00ec50`, object array stride 108 at `$1a2ea`, jump
  `$00c742`/`$00cbbc`, `x=192` is the camera trigger via `$00c450`/`$018f7e`).
- **The level is one 1680x24 tile map at `$31800` holding connected rooms (99th pass).** The first-room
  scroll limit `$1020` is the end of the 137-block start room, not of the level. Room tables (`$c028` start
  room, `$e0aa` per-world exit lists), the transition routine `$00df4a`/`$00e02c`, and the spawn list at
  `$27200` are decoded. Two exit records (one bottom, one top) were forced live and every predicted field
  matched (`$227b4`, camera, limit, hero x/y). `py/level_map.py` and `py/level_rooms.py` reproduce the map
  and graph from any snapshot; `amazon_level_map.png` is the render.
- The crossbar item is collected by an up+left hop (98th pass; score `003200`, slot 0 type 1 to 0).
- Continuing right from the twin trees works with real input: from `pass90_wall_192.snap`, chained
  up+right hops (`kbd ff`/`kbd 09`, 30,000-step hold) then a 400,000-step right walk scroll the camera
  (`$46c` to `$5ac` over ~11 cycles) past a rock step, onto wooden crossbars, a diagonal staircase and a
  ladder. Health was the constraint: at `1/18` the flying creature killed the hero within two cycles, so
  the exploration poked health to full each cycle (a labelled shortcut, not natural play).
- A level ends when its boss dies (static reading only): `$22803` bit 7 is set at five addresses
  (`$014ad6`, `$015752`, `$01602e`, `$016958`, `$0176a6`), `$00fb98` counts 125 frames, then `$00b0b2`.

## Open, in priority order

1. **Find the Amazon boss and the route to it.** Decode the spawn list (`$27200`, 4-byte records: column
   word, row byte, type byte; type indexes the descriptor table at `$10474`, first descriptor byte picks the
   allocator via `$10046`). Tabulate all ~256 records with their room, find which of the five `$22803`
   writers belongs to world 3 (a `bp` on each while a boss is alive would settle it, or read which handler
   the descriptor's `22(A0)` pointer targets), and locate that record in the room graph. Then plan a route
   with `level_rooms.py`.
2. **Reach a room exit with real input**, not pokes: climb through the ceiling gap at block 112 (col 448,
   x=3584) or drop through blocks 131/135. The camera has to get to about `$e00` (from `$5ac`, roughly 3,000px
   at 8-100px per cycle); a poked camera (`w 227b4 ...`) plus a natural jump/fall is the cheaper hybrid, but
   say so. Confirm the state byte `$227f3` really is 2 while climbing off the top and 3 while falling.
3. **Pin what the item is** (`bpc` on the write that sets slot 0's `type` to 0; is `$00b71a` the generic
   test or a pickup handler).
4. Slot 8's patrol rate; the projectile-vs-enemy damage path (`$00d3cc`); categories `1`/`2`/`3` (the render
   suggests ladder / small ledge / one-way platform, untested); Orient/Ice Land/Bermuda from a fresh cold boot;
   whether slots 9/10 move.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". New this pass:

- **The map and tables are resident, so read them before playing.** The 90th-98th passes drove the hero
  blind for nine passes; the whole level layout, exits and spawn list were sitting in RAM at `$31800`,
  `$e0aa` and `$27200`. Dump the data structure the game's own scroll/loader reads before trial-driving.
- **The transition takes hundreds of thousands of steps** (`$1c3c8` fade). Sampling 200,000 steps after a
  poked trigger showed only `y=-16` and the old camera; 400,000 more steps showed the finished room.
- **Object slots are live-spawned by camera position**, so a slot number is only meaningful on one screen.
- Health poked per cycle removes the death risk but also the natural-play evidence; label pokes.

## Next session

Open item 1: tabulate the spawn list per room, find the world-3 boss and its room, and write the route
graph from the start room to it. Do not resume the hop-chain exploration; use the room table.
