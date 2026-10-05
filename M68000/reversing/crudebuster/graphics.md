# Crude Buster: graphics

Everything here is proven by a pure-Python renderer (`gfx/py/cbrender.py`) that reproduces MAME's own snapshot from dumps of tilemap, rowscroll, sprite and palette RAM plus the tilemap control registers:
**1126 of 1126 frames identical (61440 of 61440 pixels each, 256 x 240)**. The set is the attract run (325 frames, natural), level 0 (121, natural, `plans/play1.lua`) and levels 1 to 5 (136 each).
**Levels 1 to 5 were reached by a poke** (`$80046 = N-1` plus bit 4 of `$80040` at frame 900, cleared again at 1500: `gfx/lua/level_poke.sh`); their camera and game state is the game's own next-level path, but a natural play of those
levels was not rendered. The visible area is x 0-255, y 8-247 (240 lines). Re-run: `gfx/proof.sh` (about 3 minutes, over the captured dumps in `scratchpad/crudebuster/agents/gfx/dumps`, symlinked as `gfx/dumps`;
`gfx/run.sh` captures new ones). Details of the gates and scripts: `gfx/README.md`.

| claim | count | script |
|---|---|---|
| tiles1, tiles2, sprites assembled from the zip equal MAME's regions | 1,048,576 / 524,288 / 1,310,720 bytes | `gfx/py/gfxlib.py` |
| full-frame render equals the MAME snapshot | 1126 / 1126 frames | `gfx/py/compare.py` |
| each rule is exercised (wrong priority differs in 245 frames, wrong flash parity in 238, unclamped palette in 1107) | | `gfx/py/sensitivity.py` |
| mid-frame control writes split a frame into row bands, and the band model reproduces it | 2 attract frames (frame 370: the plain model fails on 2816 pixels) | `gfx/py/ctllog.py` |
| palette load model: the ROM sets chosen by the mailbox values are what palette RAM holds | 256 / 256 entries per level (252 / 256 on one block in level 4: the cycle or blink mailbox) | `gfx/py/palcheck.py` |
| the four sprite emitters equal the model | 215,915 / 215,915 list entries | `gfx/py/emitcheck.py` |
| layer A (chip 0 playfield 2) equals the ROM strip column (c mod 64) | 2668, 2193, 3253, 1972, 2587 columns in levels 1 to 5, 2058 in level 0; 0 mismatches | `gfx/py/levelcheck.py` |
| layer C (chip 1 playfield 2) streamed model | levels 0, 3, 4: 1629, 2396, 1725 columns, 0 mismatches | `gfx/py/levelcheck.py` |

Not proven: the actor animation lookup `$22540` against live frame pointers (read from code); layers B and C of levels 1, 2, 5 as static strips.

## ROM formats

- **tiles1** (1 MB): `mab-00` at 0 plus the 8x8 chars `fu05`/`fu06` interleaved by byte at `$80000`. Chars 8x8 and tiles 16x16, 4 bits per pixel, planes `{24,16,8,0}` (plane 0 is the most significant pen bit); a 16-wide tile is two 8-wide halves 64 bytes apart. Chip 0 playfield 1 uses char bank `ctl[7]` low byte `$41`: char code `(tile & $fff) + $4000`; only chars `$4000-$4bff` hold data.
- **tiles2** is `mab-01`. **Sprites**: 16x16 tiles, 10,240 elements; the two `mab` ROMs interleave as 16-bit groups, the four `fu` ROMs byte-wise at `$100000`. Tile bank is `(ctl7 & $70) << 8`.

## Tilemaps and palette

- Playfield word: `tile & $fff` plus bank, colour in bits 12-15 (bit 15 would enable flips only if control1 bits 0/1 are set, which the game never does). 16x16 mode uses `scan_rows` layout, 8x8 uses plain 64-column rows. Chip 0 pf1 is the 8x8 text/HUD layer; the other three are 16x16. Colour banks per playfield: pens `$000`, `$200` (chip 0), `$300`, `$400` (chip 1).
- Control words (`$b5000` chip 0, `$b6000` chip 1; write-only on the bus, taken from write taps): 0 bit 7 flip (inverted: `$90` = none); 1-4 pf1 X/Y, pf2 X/Y; 5 enable (bit 7), row-scroll style (bits 3-6), column-scroll style (bits 0-2) per playfield (low byte pf1, high byte pf2); 6 control1 (bit 7 = 8x8, bit 6 rowscroll, bit 5 colscroll); 7 bank bytes. Row-scroll index is `(map y) >> style`. Observed: chip 0 `$8080`/`$0080`, and `$9880`/`$4080` (2 frames); chip 1 `$8890`/`$4040` (level 1 water, rowscroll styles 1 and 2), colscroll `$0020` on pf1 (level 3 snow).
- Palette: 32 bits per entry, low word at `$b8000`, extension at `$b9000` (R bits 0-7, G 8-15, B 16-23: the extension word is blue). `xbgr_888` clamps each channel at `$8e` and scales by 255/`$8e`.
- Sprite entry (4 words): y word `efFbSssy yyyyyyyy`, tile word, x word `ppcccccx xxxxxxxxx`; screen position `240 - x`, `240 - y`; height multiplier `(1 << bitswap(y bit 10, bit 9)) - 1`, tiles stack upward; y bit 12 blinks (hidden on odd frames); the sprite bitmap holds `(colour << 4) | pen` with y bit 15 as bit 7 of the colour. The sprite buffer is the copy made at the write to `$bc000`.
- Layer order (`screen_update`): chip 1 pf2 opaque; sprites with `(pix & $900) == $800` (base `$100`) and `$900` (base `$500`); then, if `m_pri`, chip 0 pf2 then chip 1 pf1, otherwise the reverse; sprites with priority 0; chip 0 pf1. **`m_pri` is set by the level setup's `$bc004` write** (the protection key of `architecture.md`): levels 0 and 4 give 0, levels 1, 2, 3, 5 give 1 (keys `f1`, `80`, `40`, `ff` with responses `36`, `2e`, `1e`, `76`; `3e` for level 4).

## Game side

- **Frame upload** `$810c` (called from the VBL handler when the main loop had asked): `$80404` to `$bc000` (sprite latch), scroll shadows `$80420-$8042c` to `$b5002-$b5008`, `$80438-$80444` to `$b6002-$b6008`, `$8044a` to `$b600c`. 24,481 writes to each register in a run, all from `$8116-$815c`; mid-frame writes only from the attract code (`$4c52`, `$4c5a`, `$4caa`, `$4cb2`; frames 330 and 370).
- **Sprite lists** (RAM `$82000 + $400*i`, 7 lists, count word then 8-byte entries, cap `$78`): actor handlers call an emitter (`$efc0` plain, `$f084` mirrors when obj+7 = 1, `$f150` mirrors when obj+4 != 1, `$f21c` mirrors when obj+4 = 1) with D7 = list index, A5 = a parts list, A6 = the actor. `$da2` copies lists in the order of table `$e00` (`$83800` first, `$82000` last, so list 0 is on top), zeroes the counts and pads with `y = $100` entries to 256. A part record is 8 bytes: x offset, y offset, tile word, size/flip byte, colour/priority byte. Emitter position: `D4 = -(objX - (camX + $100)) & $1ff`, same for y with `camY = $80406`.
- **Actor drawing**: `$22540` draws through the animation database at `$30000`: type table (80 types) -> state table (record+3; type 0 has 24 states) -> animation (ticks per frame, last frame, sound word, frame pointers) -> frame (part count, parts). `$22612` advances ticks and frames, `$22664` moves. Full index: `gfx/data/anim_index.txt`. Position fields +8/+12 are longs whose high word is pixels (so the "word" reads of `architecture.md` are the high words).
- **Camera**: `$80406` = camera Y, `$8040a` = camera X (high byte = screen index, origin `$100`); layer B uses `$80412`, layer C `$8041a`.
- **Background maps**: a block is 16 x 16 words (256 x 256 px). Layer A blocks at `$41000 + $200*i`, layer B at `$4ba00`, layer C at `$4da00`; a per-screen table word picks the block for tile rows 0-15 (low byte) and 16-31 (high byte), `$ff` = none; tables `$8c94` (A), `$98fe` (B), `$9d20` (C). `$8bea` pumps one column per 16 px (`$8d26` via `$8172`, 16 rows), the strip column c lands in map column `c mod 64`. Screens per level: 8, 8, 10, 10, 9, and 15 valid for level 5 (`levelcheck.py` reads 40 because the table runs on past its terminator). Room map at `$8908` carries scroll-lock flags, event table `$8f52` with function table `$8ff2` (`$8f14`), water rowscroll `$9a3e`. Tables: `gfx/data/level_tables.txt`.
- **Level setup**: `$81c4` resets the camera and calls the per-level routine through table `$8246` (`$825e`, `$82a8`, `$83b8`, `$83f8`, `$84d6`, `$8516`), then `$85fc`, `$8e18`, `$984e`, `$a090`. These pick palette mailboxes, scroll shadows, control words, the `$bc004` key and static map blocks (level 1 `$4d200`/`$4e000`, level 3 `$4c600`, level 5 `$4fe00-$51c00`).
- **Palette mailboxes** (consumed in the VBL handler): `$80008` four nibbles pick ROM sets for the blocks at pens `$000`, `$200`, `$300`, `$400` (0 keeps, `f` clears); `$8000a` the sprite set (1-7, two 512-byte halves to pens `$100` and `$500`; `$ff` clears); `$8000c` 16-colour cycling by `($8004a >> 2) & mask`; `$8000e` single-entry blink pairs by a bit of `$8004b`. Routines `$70f0`, `$7324`, `$74b6`, `$7526`, clear `$75de`, request-and-wait `$70c2`. ROM sets: low halves `$52000-$57xxx`, extension `$58800-$5b600`. Per-level values: mailbox A table `$708c` = `1111 2121 3131 4141 5151 6162`, mailbox B table `$70b6` = 1 to 6. If `$80041` bit 5 is set, set block 2 is halved bytewise (`$71d4`).
- **Text and HUD** (into chip 0 pf1 RAM, `$80` bytes per 8x8 row): `$28fa` `write_glyph_message` over table `$2962` (80 messages: attribute word, destination long, glyph codes; `$fffe` starts another record, `$ffff` ends; glyph g writes g and g+1 below, then g+2 and g+3 one column left; destination advances 4 per glyph; `g = $8c + 4k`, k 0-9 digits, 10-35 A-Z). Decoded: `gfx/data/messages.txt`. `$1c8a` byte-coded tile strings (`$1cce`), `$1ab2` BCD number writer with zero blanking, `$3d66` energy bars, `$3e84` face icons, `$3f06` boss bar, `$3c68` two-digit counter.

## Assets (committed)

`gfx/assets/`: `chars_4000-4fff.png`, `tiles1_*`, `tiles2_*`, `sprites_*` sheets (1024 elements each, coloured with the brightest palette each code was seen with), `palette_sets.png`, `palettes_by_level.png`, `anim_types_state0.png`, `anim_type0.png`,
`frames/` (MAME | renderer | difference), `levels/level<N>_A.png` (layer A strip from ROM; `level<N>_composite.png` lays it over the live B/C pages and is not parallax-correct). Routine names: `gfx/gfx.sym`.

## Open

Layers B and C of levels 1, 2, 5 and B everywhere as static strips; room-map flag meanings (`$80400-$80402`) and the event functions behind `$8f14`/`$8ff2`; the animation lookup `$22540` against live frames; natural (not poked) renders of levels 1 to 5.
