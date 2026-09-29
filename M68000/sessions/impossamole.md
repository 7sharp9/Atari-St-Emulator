# Impossamole: handoff

Updated 2026-09-29 by the 101st-pass session, which changed no code or docs (orientation and the start-room map only);
the last work commit is still the 100th pass (see `git log`).

## Resume point

- Last commit of this workstream: the 100th pass, "impossamole: 100th pass -- the Amazon boss, the enemy damage path and
  the route to the boss room" (`git log --oneline -4`).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/`, `gameplay_explore/` (older trials) and `pass99/` (this pass: `cyc0..7.snap`,
  `warp_down131b.snap`, `warp_up112.snap`, `boss_room.snap`, `boss_dead.snap`, `boss_kill_end.snap`,
  `spawns.txt`, scripts `cyc.repl`/`hops6.repl`/`boss_*.repl`). `scratchpad/ANCHORS.md`
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
- Uncommitted work left behind: none from this session (`scratchpad/impossamole/pass101_map.png`, a start-room
  map crop, is gitignored scratch). `M68000/sessions/README.md` still carries the
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
- **The Amazon boss and the route to it (100th pass, README "Boss").** One kind-2 spawn record (type 138,
  column 1296) in the dead-end room `318..326`; route from the start room is four exits (bottom at block 135,
  top at 168, top at 283, bottom at 317; `py/level_rooms.py <snap> --route 318 326`), the last one forced live.
  Boss: slot 7, handler `$15e9a`, 60 hit points at `$1a645`, alternates a shielded and a vulnerable animation
  (`22(A0)` `$221f6` / `$221d0`) and moves `x` by random multiples of 8 (224 to 64).
- **The projectile-vs-enemy damage path is `$0013a9c`** (`103(A0) -= 104(A1)` at `$13b20`, projectile damage =
  weapon index `$bb72`): live, one shot put on the boss took `$3c` to `$3a` (1 write), and `py/boss_kill.py`
  took it to 0. Shot position was poked, so natural aim at the boss is not proven.
- **Boss death ends the level (live chain).** HP 0 gives `$22803 := $ff` at `$1602e` (death animation
  `$22306`, `boss_kill_end.snap`); with the flag set, `$fb98` counts `$22804` to `$7d`, `$f0ee` runs 46
  frames and `$b0b2` is hit once. The world-5 branch and the return to world-select were not reached in the
  window (static readings).
- The crossbar item is collected by an up+left hop (98th pass; score `003200`, slot 0 type 1 to 0).
- Continuing right from the twin trees works with real input: from `pass90_wall_192.snap`, chained
  up+right hops (`kbd ff`/`kbd 09`, 30,000-step hold) then a 400,000-step right walk scroll the camera
  (`$46c` to `$5ac` over ~11 cycles) past a rock step, onto wooden crossbars, a diagonal staircase and a
  ladder. Health was the constraint: at `1/18` the flying creature killed the hero within two cycles, so
  the exploration poked health to full each cycle (a labelled shortcut, not natural play).
- A level ends when its boss dies (static reading only): `$22803` bit 7 is set at five addresses
  (`$014ad6`, `$015752`, `$01602e`, `$016958`, `$0176a6`), `$00fb98` counts 125 frames, then `$00b0b2`.

## Open, in priority order

1. **Decode and commit the graphics (Dave's direction, 101st pass).** Nothing is decoded yet: no `graphics.md`, no
   tileset or spritesheet PNG (the committed images are screenshots plus a collision-category map, which shows
   categories, not art). Known addresses only, all from the README: 2x2 block definitions `$29000`, block map
   `$27600`, tile map `$31800`, object sprite table `$3b600` (128 bytes per entry), hero bank `$42e00` (384
   bytes per entry, 24 rows x 16 bytes, populated only on a fresh-cold-boot lineage), disk files `CHARS11.DAT`,
   `SPRTS22.DAT`, `SPRTS33.DAT`. Prove it with: (a) tiles: find the 8x8 tile art the `$29000` blocks index (read
   the redraw routine `$18ed4` builds the screen with, or `gfxview.py <snap> --contact`), render a tileset sheet,
   then re-render the level map from real tiles and compare with `amazon_gameplay.png` at match count; (b)
   sprites: read the blit routine the `$3b600`/`$42e00` tables feed, decode with the mask it uses, render a
   contact sheet per bank and check hero/enemy/boss frames against a same-step screenshot; (c) palette per world.
   Commit the PNGs, table-index them in a new `graphics.md`, and run the contact-sheet-vs-screenshot coverage check
   (skill section 4) before calling a catalog complete.
2. **Play the route with real input.** Every hop of the four-exit route is table-derived (one bottom and one
   top exit were forced in the 99th pass, the boss-room entry in the 100th). Hero placement and camera
   are poked; the open work is reaching a trigger by moving. The start room's two bottom exits are the
   blocks 131 (cols 524..527) and 135 (cols 540..543, on the route). The trigger block is
   `(x - $20 + camera + 16) >> 5`, so with camera `$1020` block 131 needs hero `x` 80..111 and block 135 needs
   `x` 208..239 (derived from the README formula, not yet tested live; the earlier "x about 80" was block 131's
   value). The category dump (`level_map.py` loader, cols 500..556) shows both as open shafts from row 4 to row 23,
   with an open passage at rows 16..19 between them and a solid block at cols 528..539, rows 8..11. Confirm `$227f3` is 3
   while falling off the bottom and 2 while leaving through the top, and that the hero can reach the shaft at
   all (walls, hazards).
3. **Natural aim at the boss.** The boss is at `y=96` and shots fly along the hero's `y`; find where the hero
   has to stand (the room's ledges) and which weapon (`$bb72`, damage per shot, and the four-slot pattern in
   `$d4be`) makes 60 hit points reachable, and that a shot really hits without the position poke.
4. **World-select return and the world-5 branch after `$b0b2`** (the `$1c3c8` fade runs longer than the 4M
   steps checked; `hits` on `$b0ca`/`$17c9c` with 10M steps).
5. **Decode the spawn types** (`spawns.txt`: which of types 105-132 are which enemy, item or hazard;
   descriptor `+12..14` radii, `+8` type word, `+28`/`+48` anim and handler pointers), and what the 63
   type-251 markers are. Item 1's sprite banks give these types faces.
6. Pin what the item is (`bpc` on the write that sets slot 0's `type` to 0); slot 8's patrol rate; categories
   `1`/`2`/`3` (render suggests ladder / small ledge / platform, untested; real tiles will settle it); Orient/Ice
   Land/Bermuda from a fresh cold boot; whether slots 9/10 move.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". New this pass:

- **The map and tables are resident, so read them before playing.** The 90th-98th passes drove the hero
  blind for nine passes; the whole level layout, exits and spawn list were sitting in RAM at `$31800`,
  `$e0aa` and `$27200`. Dump the data structure the game's own scroll/loader reads before trial-driving.
- **The transition takes hundreds of thousands of steps** (`$1c3c8` fade). Sampling 200,000 steps after a
  poked trigger showed only `y=-16` and the old camera; 400,000 more steps showed the finished room.
- **Object slots are live-spawned by camera position**, so a slot number is only meaningful on one screen.
- **The boss has a shielded animation**: a fixed aim point stalls at whatever HP the last vulnerable window left
  (16). Read the boss `x`,`y` and animation each pulse (`py/boss_kill.py` does).
- **Driving the REPL from Python needs a sentinel**: `hits 0 fb98` prints a distinctive row after the previous
  command's output; without one the reader cannot tell where a reply ends.
- **`watch` on a counter floods stdout** (`$22804` printed 125 lines); watch a flag, or `hits`, unless the counter is the point.
- Health poked per cycle removes the death risk but also the natural-play evidence; label pokes.

## Next session

Open item 1, graphics first (Dave's call): start from `scratchpad/impossamole/pass99/cyc5.snap` (any Amazon
snapshot has the tables resident), run `gfxview.py <snap> --contact` for a whole-RAM overview, then pin the
tile art format via the screen-rebuild routine `$18ed4`, render the tileset and a real-tile level map, and only
then the sprite banks. Commit PNGs plus a `graphics.md`, and index them in the README files table. The route
walk (item 2) follows once the real-tile map makes the shafts and ledges readable. Do not re-derive the map, room
table, spawn list or boss data: they are in the README and the scripts.
