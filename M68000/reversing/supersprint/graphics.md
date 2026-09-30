# Super Sprint: art, blitters and the frame pipeline

How the pictures are stored and drawn. Every renderer below is a Python transcription compared with the
real routine via `callcap` on whole screens (counts in the proof table). The track tile pack and the
collision planes are in `tracks.md`; the sound driver is in `sound.md`. The image sheets are in
`png/engine/` (`INDEX.txt` lists each sheet with source, format, routine and proved/read status).

## Memory map

`$fbca` mallocs a 309,000-byte pool at `$21100`. `SUPER.DAT` is read verbatim to `$28e00` and cut into blocks
B0..B12 (`tracks.md` lists offsets and A4 pointers). The screens and scratch:

- `-78(A4)` the draw screen, `-82(A4)` the shown screen (swapped each frame by `$1464a`);
- `-86/-90` a 32000-byte **static background stash** (`$59736`): the composed track, used to restore dirty rects
  (it is not a HUD stash);
- `-94` the three 8000-byte **depth bitmaps** (`$61436`): collision plane 1 and the two masks (tracks.md);
- `-5396(A4)` a 320-byte, 10-step AND-mask table for the dither **dissolve** (`$147e0/$1480a`). The "palette
  ramp" that `gfxview.md` once described is this table plus per-screen palettes, not a fade.

## Depacker: word RLE `$1484a(src, dst)`

The first word of a stream is the escape token. A word equal to the token starts a `(token, value, count)` run;
any other word is a literal. The output is 4 planes x 4000 words stored interleaved at `i*4 + plane`. The
credits picture B12, the ready-screen cars B1 and the `SUPER1.DAT` splash use it; everything else in
`SUPER.DAT` is stored raw or in the tile pack.

## Sprite formats and blitters

Stored plane words `[w0, w1, w2, w3]` reach the screen as `[w0, w2, w1, w3]`. The sprite art lives in B3 and
B5 and is decoded by the blitters' own code:

- **Cars** (B3, 128 frames, `png/engine/07_cars_128_frames.png`): `$14a4a` via `$149b8`. It draws the car, builds the
  collision window (mechanics.md) and records a **dirty rectangle** `(byte offset, 11)` at `-3634(A4) + (frame&1)*16 +
  car*4`. A drone uses the `+$40` (grey) frames; the drone flag `-3914(A4)` also picks the HUD caption.
- **B5** (`$205d6`): a grey tornado (3 frames), a 26-frame car explosion (forcing `-3778(A4)[0] = 1` in a live race turns
  car 0 into it), a helicopter in two sizes (32x36 and 64x26, 8 frames each), 22 small images (score pop-ups
  1/10/100/1000/15/150/2/20/200/25/250, three oil/water slicks, the wrench #19, a cone), trees, tree shadows, smoke
  puffs, track dressing, barriers, posts, the HUD captions (BLUE CAR / RED CAR / YELLOW CAR / DRONE, wrench, LAP) and
  0-9 icons. The tornado, helicopter and oil names are read from the pixels and the call context (the explosion has a
  live test).
- **Text**: a 42-glyph 5x6 font (digits, `.`, `!`, A-Z, blank, `-`, `'`, block) and a 12x12 A-Z font; the glyph blitter is
  `$16528` (not a car draw). Cells are opaque 6x6 with explicit foreground and background colours and a 6-pixel
  advance. `$1b522` formats tenths as `[hundreds] tens . units`.
- **HUD digits** (B7 set 5) are 32x11; car 0 draws in colour 1, car 1 in 10, car 2 in 12. Sets 0-4 are pre-shifted
  variants; only set 5 is pixel-proven.
- B9 is 16 frames of the pit-mechanic animation; B0 the big red hi-score car; B2 the steering wheel (5 stored plus 11
  derived frames).

## Depth layers

Layer 0 of `-94(A4)` is 1 unless the background colour index is 3, 4 or 7. The car blitter ANDs stored plane 3 with
layer 0, and when the car's level flag is 0 ANDs the opaque mask with layer 2 (also written by the HUD digit code), which
lets cars pass behind overpass graphics. The depth-sort key is `Y` plus 255 when bit 0 of `-3826(A4)[car]` is set (car on
the elevated level), so an elevated car always sorts in front (`$e84c`: a stable bubble sort with `exg` on
`(index << 16 | Y)`). What colours 3, 4 and 7 mean in the art is inferred.

## One race frame

`$1464a` swaps the buffers, increments `-8072(A4)` (low bit = buffer parity), calls `Setscreen(-82,-82,-1)` then `Vsync`.
TOS writes the shifter base at once and the hardware latches it at the next frame start. A frame is about 11,784 steps:
the first ~3,660 are the ROM Setscreen and Vsync wait, about 8,100 are game work. Order (steps after the Vsync return;
`engine/frame_census.py`):

| step | routine | role |
|---|---|---|
| 3663 | `$10658` | F-key poll |
| 3794 | `$14972` x4 | restore car rectangles from the stash |
| 4333 | `$14620` | restore the bottom strip |
| 4373-4407 | `$aa60 $abd4 $ae0e` | bonus and animation state |
| 4447 | `$eaea` x3 | drone control |
| 4803 | `$d4fa` | human control |
| 4810 | `$105a0` | input |
| 5108 | `$12450` | engine sound |
| 5922 | `$13bbe` | HUD (`$158ea`, `$15e5a`); one of the three panels per frame, `(frame % 6) >> 1` |
| 7459 | `$df18` | physics and draw |
| 7467-7594 | `$e8e6` x6 pairs, `$e84c` | car-car collision, depth sort |
| 7696 | `$149b8` x4 | render |
| 8434 | `$bda4` x4, `$b798` x4 | obstacle test, surface sample |
| 11740 | `$afc6` | smoke particles |

Each of the two screen buffers keeps its own rectangle record, so a car's rectangle is restored two frames after it was
drawn (`$14972` restores a 32-pixel-wide strip of `rows + 1` rows from the stash).

## Interrupts: Timer B is not used in the race

The **race runs on the ROM VBL handler** (`$70` = `$fc0634`); `$f9ea`, `$fa36` and `$f6e0` have zero hits over 1M race
steps. The game's own VBL and MFP Timer B event-count handlers (installed by `$f8d0`: VBL `$fa36`, Timer B `$f9ea`) are
installed only for the menu and results screens (select, options, hi-score, prepare, winner's circle). There the VBL loads
palette 0 and starts Timer B in event-count mode with data 2, and each Timer B interrupt counts toward a per-band list and
loads the next 16-colour palette at band boundaries: select-screen counts `[17, 26, 31, 255]` (four palettes),
winner's-circle counts `[9, 28, 33, 255]`. That is the raster split that colours the three ready-screen cars. A second
set (`$f5be`: `$f71e`/`$f6e0`, a splash palette cycle and a bit-rotate marquee) is dead in this release: its `trap #14` is
NOPed at `$f632`. The band heights in scanlines (count x 2) are inferred.

## Images

`png/engine/` (31 sheets): splash, credits picture, title, winner's circle (banded), the eight track tilemaps, the select
icons, the four tile banks, 128 car frames, tornado/trees/explosion/puffs/dressing/score+oil+wrench+cone/barriers/posts/
helicopters/HUD captions and icons, both fonts, B7 HUD digits, B8-B10, the steering wheel. `INDEX.txt` is the table.
`png/secrets/` has the prize sprites (`prize_sprites.png`), the reset credits picture and the tail of `SUPER1.DAT`.

## Proof table

| claim | script | count |
|---|---|---|
| RLE depacker on B12, B1 (and the reset routine `$10236`) | `engine/proof_reset_pic.py`, `proof_tiles_callcap.py` | 32000/32000 bytes each |
| `SUPER1.DAT` splash equals the live screen (3 cold-boot steps) | `engine/proof_reset_pic.py` | 64000/64000 pixels |
| tilemap renderer `$152d2`, all 11 maps | `engine/proof_tiles_callcap.py` | 352000/352000 bytes; title 64000/64000 pixels vs `title.png` |
| Track-1 background from tiles + trees + shadows vs live stash | `engine/proof_playfield.py` | 54347/54400 (53 = the wrench tile) |
| cars `$14a4a` | `engine/proof_cars.py` | 7680/7680 (40 trials) |
| tree+shadow `$15642`, tornado `$1404e`, explosion `$14b8e` | `engine/proof_sprites.py` | 960000/960000 each (30 trials) |
| smoke `$143ca`, dressing `$1416c`, score/oil/wrench tiles `$14262`, helicopter `$13cbc`, captions `$144ca` | `engine/proof_sprites2.py` | 960000/960000 each |
| wrench-count icon `$1453a` | `engine/proof_sprites2.py` | 1920000/1920000 (screen + stash) |
| text glyphs `$16528`, number formatter `$1b522` | `engine/proof_text.py`, `proof_numfmt.py` | 1280000/1280000 each (40 trials) |
| HUD big digits `$15e5a` | `engine/proof_hud.py` | 960000 screen, 960000 stash, 23040 depth |
| steering wheel `$16926/$16962` | `engine/proof_wheel.py` | 15488/15488 |
| layer 0 builder `$154d2` | `engine/proof_layer0.py` | 32000/32000 |
| dirty rectangles `$14a4a` write, `$14972` restore | `engine/proof_dirty.py` | 20/20, 960000/960000 |
| depth sort `$e84c` | `engine/proof_depthsort.py` | 60/60 |

## Open

- The lap-panel composition `$158ea` with B7 sets 0-4 is not reproduced (1627 pixels of the top HUD rows still differ
  from the rebuilt background); B5 barriers and posts, B8, B9, B10, B0 and the big font are read from the blitters, not
  diffed.
- The 150-byte header of B2 and the real-hardware band heights of the Timer B screens.
- Seven 4 KB blocks of `SUPER.DAT` (28,672 bytes) that no tested flow consumed (`secrets.md`).
