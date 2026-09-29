# Impossamole: graphics

Everything below is decoded from a running snapshot's RAM (all of it is resident once a world is loaded)
with `py/tiles.py` and `py/sprites.py`; the PNGs in `graphics/` are their output from
`scratchpad/impossamole/pass99/cyc5.snap` (Amazon, world index `$bb76 = 3`). The display is ST low
resolution, 320x200, 16 colours; the playfield is 256x192 at screen offset `(32, 8)`, with the HUD text and the
blue border around it.

## Pipeline

| stage | address | format |
|---|---|---|
| level | `$27600` | 420 block columns x 6 bytes; one byte per 32px row = a block id |
| block definition | `$29000` | 8 bytes per block: four big-endian words, row-major 2x2, each a tile id (high byte 0) |
| tile bank | `$29800` | 256 tiles x 128 bytes, 16x16 px, 4-plane interleaved words (the ST low-res row: 4 words = planes 0..3 of 16 pixels), row 0 first |
| collision map | `$31800` | 1680 x 24 bytes at 8px, a separate layer, see "Collision categories" |

`$18ed4` installs a room (README "The level is one tile map of connected rooms"): it copies the nine block
columns around the camera into an 18x12-word tile-id table at `$1883e` (`$18f0c`-`$18f34`, two words per row per
block) and `$19006` copies each distinct tile into a scroll cache at `$53000` (116 slots of 128 bytes; each row is
stored eight times, `rol.w #2` per plane word between copies, so eight 2px-shifted versions `$3a00` apart). The tile
drawer reads `$29800 + id*128` (`$19064`-`$1906e`). The bank ends exactly where the collision map starts
(`$29800 + 256*128 = $31800`). In Amazon the level uses 219 distinct ids (maximum 241); ids 242-255 are solid
filler and never referenced, and ids 0 (black) and 201 (blue water) are the other single-colour tiles.

Proof (`py/tiles.py <snap> --check`): render the level at the live camera `$227b6`, slide it over the live screen
and take the best offset. Every snapshot lands on the same offset `(32, 8)`, matching 98.2 to 99.3 % of the sampled
pixels (10,560 samples each: `cyc0` 98.3, `cyc2` 98.2, `cyc5` 98.7, `cyc7` 98.3, `boss_room` 98.6, `boss_dead`
99.3); the remainder are sprites and the HUD drawn over the background.

## Files

| file | contents |
|---|---|
| `graphics/amazon_tileset.png` | the 256-tile bank, 16 per row, tile 0 top left, 3x |
| `graphics/amazon_level_tiles.png` | the whole Amazon level from real tiles, 13440x192 (420 blocks), 1x |
| `graphics/amazon_categories_start.png` | the first 80 blocks with the collision categories tinted over the art (40 blocks per row) |
| `graphics/world_palettes.png` | the five world palettes, one row per world, 16 swatches |
| `graphics/sprites_bank1.png` | bank 1 (`$3b600`), frame indices labelled, colour 0 drawn magenta |
| `graphics/sprites_bank2.png` | bank 2 (`$42e00`), frames 0-171, same conventions |
| `graphics/amazon_spawn_types.png` | one row per spawn type of the Amazon list: header (kind, hit points, damage, descriptor), then the frames reachable from its animation pointers |
| `graphics/hud_font.png` | the 8x8 font (`$24000`), 4x |

## Palettes

The gameplay templates (`$b19a`, `$e082`) load palette `pointer[$bb76 - 1]` from a table of five longword
pointers at `$2166e` (`$1c352` installs it): `$216a2`, `$216c2`, `$21722` (world 3, Amazon: identical to the live
hardware palette in every Amazon snapshot), `$21682`, `$21762`. `$216e2` is a brighter set that `$151dc`/`$151ee`
switch to and from in an enemy handler (a flash, inferred from the code, not observed); `$21682` is also what the
text screens `$bc3a`, `$17de2`, `$1812a` install. All are STF `$0RGB` (3 bits per gun). The five tables differ only
in a few entries (`$216a2`/`$21722` are the same 16 words); each equals the live hardware palette of its own world
(`graphics/world_palettes.png`, `worlds.md`). The sprite banks below are described for the Amazon: only the low part of each
bank is common to the five worlds (see "Per-world banks").

## Sprites

Both banks are 4-plane, colour index 0 is transparent: the blitters (`$1ad32` and `$1b5a4`, which `$1b25a`/`$1b3ec`
jump to) build the mask as the OR of the four planes, `and` it into the screen and `or` the planes in, shifting by
`x & 15` and clipping to the playfield. Screen address `y*160 + (x & ~15)/2`, so an object's `2(A0)`/`4(A0)` are
literal screen x/y and `14(A0)` is the row count.

| bank | address | frame | layout | picked by |
|---|---|---|---|---|
| 1 | `$3b600`, 240 frames | 128 bytes, 16x16 | 8 bytes per row: planes 0..3 as words | `6(A0)` of a `type 1` object (`$1b25a`) |
| 2 | `$42e00`, up to 172 frames (0-171; 160 in Klondike) | 384 bytes, 32x24 | 16 bytes per row: planes 0..3 as longwords (the blitter ORs four longs for the mask, `$1b67c`) | `6(A0)` of a `type 2` object (`$1b3ec`, base `$3b600 + $7800`) |

Bank 1 holds projectile and effect art (smoke rings 1-36, bombs 37-42, laser beams 43-54, explosions 55-127), pickups
(barrel, tin, coins, fruit, bananas: frames 129-147, 174-187) and small enemies (snakes 164-167, the brown winged
flier 168-173, sparkles 179-182). Bank 2 holds the hero (frames 0-59 and 90-99: walk, jump, weapon, scarf, kneeling),
the mole climbing out of the ground (60-70), the shop speech bubbles (71-79: "175 LASER GUN", "250 SOUP CAN",
"125 BOMB", "200 EXT'D BAR", "75 WORM CAN", "150 BIG GUN", "EXIT?", "THANK YOU", "TOO MUCH"), explosion rings
(80-89), and the Amazon's enemies: tentacles 100-104, leaf bush 105-106, crumbling rock 107-114, plants 115-128,
bees 129-130 (facing left) and 170-171 (facing right), monkeys 131-136 and 159, a stone-textured strip 137,
crocodiles 138-145, chameleons 146-149 and 153-156 with their tongues 150-152 and 157-158, the boss's eyes 160-165
and mouth shapes 166-169. The bank ends at frame 171 (`$53000`); frames 172 on are not art (the first 140-frame
reading of this table stopped at `$50000` and dropped the last 32 frames, including both bee directions and the
boss face). Bank 2 is populated only on a fresh-cold-boot lineage (README "Why no hero sprite was visible"). Some
32x24 slots hold a shorter picture: frames 60, 61 and 63 use only rows 19-23, 137 rows 0-7, 138-139 and 142-143
only a water line, and 62 is blank. Which enemy uses which frames is in README "Spawn types"
(`graphics/amazon_spawn_types.png`).

Proof (`py/sprites.py <snap> --check`): for each live `type 1`/`type 2` slot, the frame is decoded and compared
pixel by pixel with the screen at its declared `(2(A0), 4(A0))`. `cyc5.snap`: hero frame 0 at (192,152) 273/319
opaque pixels, slot 7 frame 128 (a plant) 297/339, slot 3 frame 140 (a pickup) 130/171, slots 9/11 frame 170 45/106;
`boss_room.snap`: hero frame 0 276/319, slot 12 frame 183 (a banana) 124/124. Mismatches are pixels other sprites drew
over, and one slot (8, frame 121, at x=10, mostly inside the border) fails (17/339): the check is a lower bound,
not a full render of the frame. It ran on two snapshots only.

### Per-world banks

Bank 1 frames 0-159 and bank 2 frames 0-99 (hero, shop, mole, explosion rings, effects, the common pickups) are byte-identical in every
world; bank 1 frames 160-239 (`$40600`) and bank 2 frames 100-171 (`$4c400`) are overwritten from the world's `*22.DAT` and `*33.DAT`
(`worlds.md`, "Loading"). The frame ranges written above for bank 2 (tentacles 100-104 ... boss face 160-169) and bank 1 frames 168-187
are the Amazon's. A bank's extent comes from the LSD! header of its file: Klondike's bank 2 is 60 frames (100-159, real art to 150) and
its frames 160-171 are noise from an earlier load of `SELECT44.DAT`, so the "172 frames" of this table is right for the Amazon, Orient and
Bermuda only. Per-world sheets: `graphics/<world>_sprites_bank1.png`, `_sprites_bank2.png`, `_spawn_types.png`, `_tileset.png`,
`_level_tiles.png`, `_level_map.png` (`worlds.md`, "Files").

## HUD font

`$24000`, 8x8 glyphs of 32 bytes (8 rows of 4 plane bytes), glyph index = the byte in the string
(`$1c0aa`: `glyph * 32`); it shares its address range with the `$25000` classification table, so at most 128
glyphs. Glyph `$20` is blank, `$21`-`$2f` are punctuation and arrows, `$30`-`$39` digits, `$41`-`$5a` capitals
(the ASCII layout), and glyphs `$00`-`$09` are the coloured and grey pip/icon cells the health bar draws from (`$fdc4`, `$07` is the
empty pip per the README), `$0a`-`$0b` two further icons.

## Collision categories

`amazon_categories_start.png` tints the `$25000` category of every 8px map cell over the real art. The tints line
up with what the art shows in all 80 blocks of the first stretch: category 1 (green) is the ladders and the tree
trunk climbs, 2 (blue) the small branch-stub ledges, 3 (magenta) the log walkways, staircases and the suspension
bridge (one-way platforms), 9 (red) the red spike poles and the water pits. This settles the "1/2/3" labels the
99th pass had only guessed from the flat category render, as a visual correlation: which categories block
movement and which are pass-through is still the `$be96` reading, not retested here.

The other worlds add categories 5 and 6 (conveyors, one pixel per update left/right), 7 (slide, Ice Land and Bermuda) and 8 (half
speed), and use 9 for water, sludge and the sea; the table, tile ids, code addresses and live tests are in `worlds.md`
("Collision categories"), and `graphics/<world>_categories.png` tints all eight over the art (the stock `tiles.py --cats` knows only the
Amazon's set).

## Open

- Other worlds: tile banks, levels, sprite banks and spawn types are dumped and rendered for all five (`worlds.md`); still open there are
  the animation order per action, the `$216e2` flash palette in use, and Orient's category 5/8 behaviour.
- Animation-list boundaries: an animation pointer addresses a run of sub-animations (each ended by `$fffe` loop,
  `$fffd` hold or `$ffff` end), and where one object's states stop and the next object's list begins is not decoded;
  `py/spawn_types.py` shows the first sub-animation of each entry pointer plus the next three.
- The title, world-select and logo art (`PICTURES.DCH`, `SELECT44.DAT`; the world-select screen and the Bermuda ending screen are
  captured as PNGs but their picture formats are not decoded).
- Animation sequences (frame order per action) and the `$216e2` flash palette in use.
