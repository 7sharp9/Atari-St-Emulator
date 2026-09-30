# Super Sprint: tracks, data files and the collision world

Where the eight tracks come from, what is in them, and how the game turns a track into the planes that
cars collide with. All eight tracks render from the data files alone and match the game's own buffers
exactly (proof table at the end). Mechanics (how cars use this) are in `mechanics.md`; how the screens are
drawn is in `graphics.md`.

## The four files

The disk holds only `INIT.DAT`, `SSPRINT.HSC`, `SUPER.DAT`, `SUPER1.DAT` and `\AUTO\SSPRINT.PRG` (no
deleted or hidden entries, no unreferenced clusters, not bootable, no protection left). Every file is loaded
by `$106be(name, dest)`: `Fopen`, `Fread` (cap `$493e0`), `Fclose`. `$fbca` mallocs a 309,000-byte pool at
`$21100` and computes the directory of A4-relative pointers into it.

| file | size | loaded to | what |
|---|---|---|---|
| `INIT.DAT` | 5139 | `$59736` (then consumed) | the initialised globals: `$fd9a` does 43 `(dest, len)` copies via `$fd7a` into A4-relative tables. 5133 of 5139 bytes equal live RAM (6 mutable). Holds per-track start grid, scenery, occlusion rectangles, stroke lists, candidate-cell lists, direction tables, palettes, extra polylines, gate tables |
| `SUPER.DAT` | 212650 | `$28e00` verbatim (no depack) | the blob sliced by A4 pointers (next table), plus font, sound instruments and scripts |
| `SUPER1.DAT` | 17024 | `$61436` (scratch), overwritten at step 16.5M | the Electric Dreams splash picture and font/sprite source tables, all consumed at boot; its last 5152 bytes are never read (graphics.md, secrets.md) |
| `SSPRINT.HSC` | 295 | `$1cc30` etc. | the high-score file (secrets.md) |

`SUPER.DAT` is a flat blob cut into blocks B0..B12 by `$fbca`; the runtime address is the file offset + `$28e00` and
block k is reached through the A4 pointer shown (offsets from `secrets/arena_map.py`, contents from `engine/` and
`tracks/trackdata.py`):

| block | file offset | A4 pointer | contents |
|---|---|---|---|
| B0 | `0x00000` | `-98` | big red hi-score car picture |
| B1 | `0x00da0` | `-102` | ready-screen cars picture (RLE) |
| B2 | `0x03140` | `-106` | 64x44 steering-wheel frames |
| B3 | `0x04d56` | `-3602` | car sprites (128 frames) |
| B4 | `0x0cd56` | `-1196` | tile pack: 11 tilemaps (2000 B each, from `0x0cd60`) then the four tile banks (`0x12350 0x13afc 0x18c68 0x1fda6`) |
| B5 | `0x205d6` | `-1722` | object sprite sheet |
| B6 | `0x27b06` | `-8076` | wall polylines and flood seeds |
| B7 | `0x286be` | `-4936` | HUD digit sets |
| B8 | `0x2947e` | `-110` | small animation frames |
| B9 | `0x29c4e` | `-118` | winner's-circle pit-mechanic frames (16) |
| B10 | `0x2cc5a` | `-122` | 6 small 8x8 tiles |
| B11 | `0x2ce3a` | `-4080` | waypoint blocks |
| B12 | `0x2e9f6` | `-126` | credits picture (RLE) |
| tail | `0x30800..` | | fonts (`-7770`, `-7426`), 35 sound instruments, 10000-byte sound scripts |

## Eight tracks, one dial

There are **eight tracks**; there is no hidden ninth (table sizes are 8 everywhere and the dial wraps).
SELECT TRACK (`$19164`) is a 16-position dial held in a stack word; each joystick-right press adds 2, and it
times out after about 166 iterations (a fire press ends it at once). It returns `dial >> 1` (track 0..7) and
stores `dial >> 2` (the tier, 0..3) into `-3954(A4)[0..2]` as the starting wrench count. After each race the
next track is `-8542(A4)[track]` = `[2,4,6,0,7,1,5,3]` (live: a race on T0 enters `$be40` with track 2, on T3 with 0);
the attract loop advances its demo track with the twin table `-8526(A4)`. The wheel thumbnails are tilemap 10
(`png/tracks/screen_select_wheel.png`).

## The tile pack (B4): eleven screens in 80 KB

B4 holds **11 full 320x200 screens**: tilemaps 0-7 are Tracks 1-8, 8 is the title, 9 the winner's circle, 10 the
select-track thumbnails. A tilemap is 25 x 40 word cells (an 8x8 pixel cell each). The word format:

- bit 15 set: a **tile**. Bit 14 flip horizontally, bit 13 flip vertically, bits 12-11 select the bank, bits 10-0
  the tile index. Banks 0-2 store 1, 2 or 3 bitplanes plus a 16-bit **colour-set word**: the k-th set bit of that
  word, counted down from bit 15, is the palette colour of stored pixel value k. Bank 3 (65 tiles) is raw 4-plane.
- bit 15 clear: a **copy word**: copy the 8x8 block already drawn at this screen byte offset (two-dimensional
  dedupe).

Bank sizes 606 / 1158 / 1115 / 65 tiles; 6965 of the 11000 cells are copy words; no tile is unreferenced; 352,000
bytes become 79,984 (about 4.4:1). The grandstand crowd at the top of each track is ordinary tile art, not sprites.
`graphics.md` has the renderers and blit proofs.

## Per-track data

Vector and table data (Track 1 values; `tracks/track_table.py` prints all eight):

- **Wall outline and seeds (B6 `$27b06`)**: polylines plus 1-5 flood-fill seed points. Track 1 is 38 segments and two
  seeds `(201,87)` and `(163,177)`.
- **Start grid** `-1262(A4)`: Track 1 X 162, Y0 27, dY 9, heading 12 (cars side by side across the road).
- **Extra colour-3 "skid" polylines** (`$1bc92`) on Tracks 5, 6 and 7 only.
- **Scenery sprite lists** (18 objects on Track 1), **4-15 occlusion rectangles**, a **20-cell candidate list** per
  track for the wrench, bonus and hazards, and the **surface stroke list** (next section).
- **Waypoint block** `[count][count x 8 B]`: counts 84, 86, 90, 138, 102, 138, 122, 124 (mechanics.md has the record
  format and the control language). Track 4's two lanes differ in length (67 vs 51 segments). World coordinates are 8
  units per pixel, so Track 1 spans about 2400 x 1400 units.

## Collision planes

`$15884(track, screen)` is called from the race initialiser `$be40` about 1.07M steps after the join (the first
`$df18` is 2.68M steps after it). It builds, in order, into the 24,000-byte scratch buffer `[-94(A4)]` (`$61436`):

1. `$1552c`: plane 1 cleared, plane 2 set.
2. `$152d2`: the track art is composed from the tilemap (this is the visible track, not collision).
3. `$14cd4`: the wall polylines are drawn with a Bresenham line (`$14e3e`) and **scanline flood-filled** from the seeds
   (`$14fdc`). This is plane 1.
4. `$15182`: plane 2 from rectangle records (each rectangle writes `$ffff` first, so it replaces the words it touches).
5. `$154d2`: plane 0 from the art colours.
6. `$15550`: the surface map from the stroke list.

The planes are 1 bit per pixel, 320x200, 40-byte stride, 8000 bytes each, MSB leftmost:

| plane | offset | meaning |
|---|---|---|
| 0 | `-94` | car draw mask: 1 unless the art colour is 3, 4 or 7 (the meaning of those colours is inferred) |
| 1 | `-94 + 8000` | **solid**: wall, infield and outside. The only plane collision uses |
| 2 | `-94 + 16000` | foreground/occlusion mask for level-0 cars (role inferred) |

The **surface map** `[-1910(A4)]` (`$671f6`) is 40x25 bytes, one per 8x8 cell, directly after the planes, built from
4-byte stroke records `(x, y, length | bit 7 = horizontal, value)` OR-ed in. It holds lap sectors, tripwires, pickups
and hazard markers (mechanics.md lists the values), not road-versus-grass. Gates re-blit their own mask words every
animation frame (`$142b2`), so collision is partly dynamic. The README's earlier statement that the game flood-fills
"the track bitmap" is wrong: the input is a vector outline.

A data bug on **Track 8**: its stroke list holds an out-of-range stroke `(34, 30, 5 cells, mask 0x80)` (probably meant
for row 5). `$15550` ORs `0x80` into five bytes beyond the 1000-byte map, and the intended tripwire strip on row 5 is
missing (live: the byte at `$671f6+1234` reads `bf` where Track 1 reads `3f`).

## Race setup content

Hazards and pickups are placed from the per-track 20-cell candidate list by the routines listed in mechanics.md;
every placement seen live was inside the list. The wrench cell `0x0d` spans two adjacent cells (16x8 px, sprite id
`0x13`); the bonus cell is `0x11`.

## Images

`png/tracks/`: `track_1.png` ... `track_8.png` (rendered from the files), `index_sheet.png`, `track_N_overlay.png`
(both racing-line lanes, start grid, spawn cells, gates, checkpoints 1-4), `track_N_attr.png` (surface maps),
`screen_title.png`, `screen_winners_circle.png` and `screen_select_wheel.png` (first-band palettes, colours
approximate), `cell_sprites.png`, `gate_frames.png`, `hazards_track5_race0_5_17.png`. `png/physics/` has
`world_geometry.png` (art, wall plane with vectors and seeds, surface map, overlay), `walls_all_tracks.png`,
`collision_plane{0,1,2}.png`. `png/ai_econ/track1_waypoints_overlay.png` shows the two lanes against a real frame.

## Proof table

| claim | script | count |
|---|---|---|
| background rows 6-199 of the game's background buffer `$59736`, all 8 tracks | `tracks/prove_all.py` | 62080/62080 each (rows 0-5 are the HUD strip painted later) |
| collision fill plane (Bresenham + seed fill) vs `-94(A4) + 8000`, all 8 | `tracks/prove_all.py` | 64000/64000 each |
| surface attribute map vs `-1910(A4)`, all 8 | `tracks/prove_all.py` | 1000/1000 each |
| occlusion plane vs `-94 + 16000`, all 8 | `tracks/prove_all.py` | 64000/64000 each |
| wall plane (0 where background is colour 3, 4 or 7) vs `-94`, all 8 | `tracks/prove_all.py` | 64000/64000 each |
| Track 1 render vs a live race frame | `tracks/live_screen_cmp.py` | 61953/64000 (the rest are HUD, cars, wrench, shadows) |
| Track 1 plane 1 from the vector data (physics' independent rebuild) | `physics/rebuild_walls.py` | 64000/64000 |
| Track 1 surface map from the stroke list | `physics/rebuild_surface.py` | 998/1000 (the two misses are the runtime wrench) |
| INIT.DAT split vs live RAM | `tracks/initmap.py` | 5133/5139 |
| every drone waypoint transition on all 8 tracks is a decoded successor | `tracks/check_lap.py T` | 58-127 per car, none outside |
| the lane joins close within 1 px on every track | `tracks/trackpath.py` | max gap 3-8 units |

## Open

- Plane 2's record decode (`physics/rebuild_planes02.py` is unfinished: 7583 pixels are cleared in RAM).
- Live comparison of tracks other than Track 1 against collision behaviour (only rendering is proved for 2-8).
- The consumer of the tripwire strips (`-3842`). Re-driving Track 6 with no player joined ends in a garbage PC (see
  `sessions/supersprint.md`, Known traps).
