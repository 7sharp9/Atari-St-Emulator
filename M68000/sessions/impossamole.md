# Impossamole: handoff

Updated 2026-09-29 by the 102nd-pass session (graphics decode); the last work commit is `7eaa725`, this handoff is the
commit after it (`git log --oneline -4`).

## Resume point

- Last commit of this workstream: `7eaa725` "impossamole: 102nd pass -- graphics decoded: tileset, real-tile level map,
  sprite banks, font, palettes".
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image, `coldboot_census/`,
  `gameplay_explore/` (older trials), `pass99/` (`cyc0..7.snap`, `boss_room.snap`, `boss_dead.snap`, `boss_kill_end.snap`,
  `spawns.txt`, `*.repl`) and `pass102/` (scratch renders only; the committed ones are in `reversing/impossamole/graphics/`).
  `scratchpad/ANCHORS.md` indexes them. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source at
  `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/pass99/cyc5.snap` (Amazon, camera `$57a`, hero alive on the ground, health poked
  to full). Any Amazon snapshot has the map, block tables, tile bank and sprite banks resident; the scripts run on
  any of them (`uv run python reversing/impossamole/py/<script>.py <snap> ...`, from `M68000/`).
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) and `ATARI_NOTRACE=1`. The REPL stops at the first unknown line (no
  `#` comments); `snap <path>` writes relative to the dotnet process's directory, give the full path; `watch <addr> <len>`
  takes a **decimal** length; `w <addr> <8 hex digits>` writes a longword.
- Uncommitted work left behind: none from this session. `M68000/sessions/README.md` still carries a pre-existing
  whitespace-rewrap diff (not this workstream's); `.obsidian/` and `Cadaver/` are untracked.

## Proven so far

See `reversing/impossamole/README.md` for detail, match counts and addresses:

- **The program is hand-written 68000 assembly.** No decompile route; live `watch`/`bpc`/`callcap` plus
  `disassemble.py --all` is the path.
- **The graphics are decoded (102nd pass, `graphics.md`).** Level (420 block columns x 6 bytes at `$27600`) -> block
  definitions (`$29000`, 8 bytes, 2x2 word tile ids) -> tile bank (`$29800`, 256 tiles x 128 bytes, 16x16, 4-plane words).
  Rendering the whole Amazon level from real tiles matches the live screen at 98.2-99.3 % of sampled pixels at offset
  (32, 8) on six snapshots (`py/tiles.py --check`). Sprite bank 1 (`$3b600`, 240 x 16x16, plane words) and bank 2
  (`$42e00`, 140 x 32x24, plane longwords; hero, shop bubbles, plants, monkeys), colour 0 transparent; declared-position
  checks hero 273/319 and 276/319, slot-7 plant 297/339, boss-room banana 124/124 (`py/sprites.py --check`, two snapshots
  only, one slot at 17/339 unexplained). 8x8 font at `$24000` (ASCII glyph index). Palette pointer table `$2166e`
  indexed by `$bb76 - 1`. Collision categories confirmed on the art: 1 ladder, 2 branch-stub ledge, 3 log walkway/stair/
  bridge, 9 spike poles and water pits (visual correlation over blocks 0-79).
- **Hazard/collision, jump and camera-follow mechanisms** are proven (README "Past the first screen":
  `$00b71a`/`$00e80e`/`$00e82e`/`$00eb8c`/`$00ec50`, object array stride 108 at `$1a2ea`, jump
  `$00c742`/`$00cbbc`, `x=192` is the camera trigger via `$00c450`/`$018f7e`).
- **The level is one 1680x24 tile map at `$31800` holding connected rooms (99th pass).** Room tables (`$c028`, `$e0aa`),
  the transition routine `$00df4a`/`$00e02c`, the spawn list `$27200`; two exit records forced live and every predicted
  field matched. `py/level_map.py`, `py/level_rooms.py`, `py/spawn_list.py`.
- **The Amazon boss and the route to it (100th pass, README "Boss").** One kind-2 spawn (type 138, column 1296) in
  room `318..326`; route from the start room is four exits (`py/level_rooms.py <snap> --route 318 326`), the last one
  forced live. Boss: slot 7, handler `$15e9a`, 60 hit points at `$1a645`, shielded/vulnerable animations, `x` moves by
  random multiples of 8.
- **The projectile-vs-enemy damage path is `$0013a9c`** (`103(A0) -= 104(A1)` at `$13b20`, damage = weapon index
  `$bb72`): one poked shot took the boss `$3c` to `$3a`; `py/boss_kill.py` took it to 0. Natural aim is not proven.
- **Boss death ends the level (live chain).** HP 0 gives `$22803 := $ff` at `$1602e`; `$fb98` counts `$22804` to `$7d`,
  `$f0ee` runs 46 frames, `$b0b2` is hit once. The world-5 branch and the world-select return were not reached.
- Item collection and real-input progress: the crossbar item is collected by an up+left hop (98th pass); chained up+right
  hops plus right walks scroll the camera past the twin trees (health poked to full each cycle, a labelled shortcut).

## Open, in priority order

1. **Play the route with real input.** Every hop of the four-exit route is table-derived; hero placement and camera are
   poked. The real-tile map (`graphics/amazon_level_tiles.png`, `graphics/amazon_categories_start.png`) now makes the
   shafts and ledges readable, which the flat category render did not. The start room's two bottom exits are blocks 131
   (cols 524..527) and 135 (cols 540..543, on the route). The trigger block is `(x - $20 + camera + 16) >> 5`, so with
   camera `$1020` block 131 needs hero `x` 80..111 and block 135 needs `x` 208..239 (derived from the README formula, not
   tested live). Confirm `$227f3` is 3 while falling off the bottom and 2 while leaving through the top, and that the hero
   can reach the shaft at all (walls, hazards); read the art around cols 500..556 first.
2. **Natural aim at the boss.** The boss is at `y=96` and shots fly along the hero's `y`; find where the hero has to stand
   (the boss room's ledges, now readable from the tile render) and which weapon (`$bb72`, four-slot pattern in `$d4be`)
   makes 60 hit points reachable, and that a shot really hits without the position poke.
3. **Decode the spawn types** (`spawns.txt`: which of types 105-132 are which enemy, item or hazard; descriptor `+12..14`
   radii, `+8` type word, `+28`/`+48` anim and handler pointers) and what the 63 type-251 markers are. The sprite banks now
   give these types faces: match each descriptor's animation frame numbers to `graphics/sprites_bank*.png`, and check by
   drawing (`py/sprites.py --check` on a snapshot with the object on screen).
4. **World-select return and the world-5 branch after `$b0b2`** (the `$1c3c8` fade runs longer than the 4M steps checked;
   `hits` on `$b0ca`/`$17c9c` with 10M steps).
5. **Graphics gaps** (`graphics.md` "Open"): the other worlds' tile banks, blocks and levels (needs a fresh cold boot per
   world; `py/tiles.py` works unchanged, the palette table is world-indexed); title, world-select and logo art and their disk
   files (`CHARS11.DAT`, `SPRTS22.DAT`, `SPRTS33.DAT`); animation frame order per action; the `$216e2` flash palette in use;
   why slot 8 frame 121 (x=10) fails the sprite check.
6. Pin what the item is (`bpc` on the write that sets slot 0's `type` to 0); slot 8's patrol rate; Orient/Ice Land/Bermuda
   from a fresh cold boot; whether slots 9/10 move.

## Known traps

Workstream traps live in `reversing/impossamole/README.md`'s "Known traps". From the recent passes:

- **The map and tables are resident, so read them before playing.** Nine passes drove the hero blind; the level layout,
  exits, spawn list, and now the tile art and sprite banks were all in RAM.
- **The transition takes hundreds of thousands of steps** (`$1c3c8` fade); sample well after a poked trigger.
- **Object slots are live-spawned by camera position**, so a slot number is only meaningful on one screen.
- **The boss has a shielded animation**: a fixed aim point stalls at whatever HP the last vulnerable window left.
- **Driving the REPL from Python needs a sentinel**; **`watch` on a counter floods stdout**.
- **Bank 2 (`$42e00`) is empty on the old `after_select3` snapshot lineage**; use the `pass99/` snapshots or a fresh cold boot.
- **Sprite bank 2 rows are four plane longwords, not two interleaved 4-word groups**; the second guess rendered garbage
  until the blitter's `or.l x4` mask gave the layout.
- Health poked per cycle removes the death risk but also the natural-play evidence; label pokes.

## Next session

Open item 1: with `graphics/amazon_level_tiles.png` open, walk the start room to the block-131 or block-135 shaft with
real input from `pass99/cyc5.snap` (or `pass90_wall_192.snap`), health poked only if labelled, and confirm the exit fires
from a reached position. Then item 3, since the sprite banks let the spawn types be matched by picture. Do not re-derive
the map, room table, spawn list, boss data or the graphics chain: they are in the README, `graphics.md` and the scripts.
