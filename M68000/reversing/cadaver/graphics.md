# Cadaver — graphics (7th pass, extended 14th pass)

Grounded in `gameplay_empire.snap` (Empire release, "DAY 1 / CAVERN" room). Two distinct
formats identified; the sprite/object sheet below was the open item the README's "Graphics
format" section had previously waved off ("not actually an open question" — true for the live
screen, not for the packed source data it's composited from).

## 1. Live screen (composited output, not source data)

Confirmed since the 5th pass, unchanged. `ScreenBufferA`/`B` (`$19100`/`$20f00`, swapping roles
per frame) are plain standard-ST **st-interleaved 320×200×4bpp**, palette at `$5a9c` (16
big-endian `$0RGB` words, copied to `$ffff8240` at boot by `$015302`). This is the final
rasterised frame — what `screendump.py`/`gfxview.py`'s default st-interleaved layout already
decodes correctly (`gameplay.png`). It is not where room/sprite art is stored; it is what those
sources get composited *into* every VBL by `ScreenFlip_AndCompositeSprites` (`$14d64`).

## 2. The packed sprite/object sheet — `$029800`–`$02de08`

### How it was found

`tools/gfxview.py --contact ram_contact.png --html gfxview.html gameplay_empire.snap` regenerated
against the current `gameplay_empire.snap` gives 7 candidate data spans (never logged as addresses
in earlier passes — logged now):

| # | Range | Size | Entropy | Zero frac |
|---|---|---|---|---|
| 1 | `$000000`–`$048800` | 290 KB | 5.25 | 0.30 |
| 2 | `$04a000`–`$050000` | 24 KB | 4.88 | 0.31 |
| 3 | `$051000`–`$06b000` | 104 KB | 4.77 | 0.41 |
| 4 | `$06b800`–`$06d800` | 8 KB | 2.55 | 0.61 |
| 5 | `$06e000`–`$072000` | 16 KB | 4.38 | 0.43 |
| 6 | `$075800`–`$078000` | 10 KB | 5.67 | 0.24 |
| 7 | `$0fa000`–`$0fc800` | 10 KB | 1.03 | 0.84 |

Span 1 is too broad on its own (it's everything from program code through the sprite-object array
and `CompositeBackBuffer`) to point at anything specific. Span 3 (`$051000`-`$06b000`) looked like
the best a-priori guess — two adjacent 16-word palette tables sit just before it (`$04d21c`,
`$04d23c`, 32 bytes apart) which read like real room-art palettes (12-14 distinct colours, vs. the
6-8-colour UI/HUD tables the palette scan also turns up elsewhere) — but decoding that span as
st-interleaved 4bpp at several widths (`decode_span.py`, ad-hoc this session, not promoted to
`tools/`) produced only noise, no tile structure at any width tried. **Dead end, not the sheet.**

The real approach (per the README's own 6th-pass method — top-down from the known compositor, not
another blind RAM diff): the 5th pass had already flagged `$02ca83`-`$02cd63` as "a per-frame
recompute buffer, not a static sprite-frame table" and downgraded it. Disassembling the actual
recompute routine at `$00bf72`-`$00c242` shows it is **not** a recompute-into-scratch routine —
it's a **sub-pixel (arbitrary bit-shift) masked blitter**: `(A0)+` reads two longwords per 16-byte
group, `ror.l`/`rol.l`-shifts them by an x-offset in `D1`, ANDs/ORs them into the destination
through `(A1)+`, all driven by a 3-word per-entry header read up front (`move.w (A1)+,D0/D1/D2`
at `$00bf86`-`$00bf8a` — width/shift/frame-index fields, not yet individually decoded). **`A0` is
the *source* pointer for this blit**, i.e. exactly the "current sprite bitmap" the 6th pass was
chasing, and it is **not** confined to the `$2ca84`-`$2ca94` neighbourhood — it's fed from a wider
packed region starting well before `CompositeBackBuffer`.

Rendering that wider region at a diagnostic 32×32 px grid (st-interleaved 4bpp, live palette
`$5a9c`) as a scan from `$026800` forward showed a clean transition: streaky noise/pixel-junk
through `$029800`, then coherent, distinct pixel art from `$029800` up to exactly `$02de08` — the
start of `CompositeBackBuffer` itself, with the 6th pass's own `$2ca84`/`$2ca94` frame pointers
landing inside the range. That established the *region*, but the 32×32 grid itself was wrong — see
below for the corrected per-frame size (32×42, not 32×32), found by reading the actual struct
fields the game uses rather than guessing a stride.

### Width and height are struct fields, not guesses — corrected after initial review

The first cut of this pass rendered every sprite as a 32×32 (or, for the props, an eyeballed
32×N-rows-until-it-looks-garbled) diagnostic square, and flagged the format as still open. On review
that output was visibly wrong — most cells repeated the same red-roofed silhouette regardless of
tile size, the telltale sign of decoding at the wrong stride, and the two individual prop crops had
a second, unrelated shape bleeding in at the bottom. Two things fixed it, both read directly out of
the emulator rather than guessed:

1. **Width.** In the `$00bf72` blitter's own caller (`$00bef0`-`$00bf6e`, disassembled this pass),
   a per-call setup block reads a byte from a type-selected sub-table and computes
   `((byte>>1)&~7)+8`, storing the result at global `1246(A5)` — read live off `gameplay_empire.snap`
   (`A5=$18152`) as **`16`**. 16 bytes/row in st-interleaved 4bpp is **32 px** — matches the width
   this pass had already been guessing, now grounded rather than assumed.
2. **Height, and the real per-object source.** `SpriteList_ClipAndCompositeOne` (`$00d856`, already
   named) — not `$00bf72` — turns out to be what actually draws every entry in the sprite-object
   array, player included, via `jsr $14d64` (`SpriteCompositeInner_AndOrMaskLoop`, already named) or
   one of two clipped-composite paths (`$7dd6`/`$7be6`). It reads **`move.b 50(A3),D6` /
   `move.b 51(A3),D7`** directly from each object's own struct — struct offset **`+50` = width in
   16-px groups, `+51` = height in rows** — no per-call global, no guessing. Read from the already-
   captured 22-entry array dump (`$038338`, stride `$46`): slot 0 (player) is `2, 42` (32×42 px);
   slot 1 is `2, 28` (32×28); slot 16 is `2, 23` (32×23); the full range across all 22 slots is
   16-64 px wide (`W`∈{1,2,4}) and 5-42 rows tall — real per-object dimensions, not a fixed grid.
   `$00bf72`'s own role is still open (see below) but it is **not** the path that draws these
   objects onto the visible screen.

Re-rendering at these exact, struct-confirmed sizes fixed both symptoms cleanly — see §3 below for
the full 22-entry catalog this led to. The player's own frames (`$2ca84`/`$2ca94`, 32×42) render as
an unambiguous armoured-knight character sprite, matching what a player character in this game
should look like (`player_frame_alt.png`, and slot 0 of the §3 catalog for the idle frame). The
recurring "red roof"
motif in `spritesheet_29800.png` (now regenerated at the correct 32×42 stride) turned out not to be
a decode artifact either — every frame shares the same isometric diamond-top silhouette at a
consistent position, which is exactly what you'd expect from sprites drawn inside a common
isometric bounding cell, not a bug.

### What's confirmed vs. open

- **Confirmed**: `$029800`-`$02de08` (17,928 bytes) is the player's own packed multi-frame sprite
  sheet — bounded on both sides by independently-known addresses, and the two frames actually
  identified inside it (`$2ca84`/`$2ca94`) decode as recognisable, complete character poses at
  32×42 px under the struct-confirmed dimensions and the game's own live palette.
- **Corrected, 8th pass**: the "~27 frames at 672 B/frame" figure above (17928/672 ≈ 27) was only
  ever a size-based estimate, not a verified per-frame stride. It's wrong: the one confirmed-good
  frame pointer, `$2ca84`, sits at byte offset 12932 from the region base — not a multiple of 672
  (remainder 164) — so frames are not packed back-to-back at a uniform stride starting at
  `$029800`. Real per-frame boundaries/count are still unknown; see the README's 8th-pass entry and
  next-steps for the corrected plan (live gesture-bisection or a real header/pointer table, not
  stride arithmetic).
- **Confirmed**: per-object width/height for every entry in the sprite-object array (`$038338`,
  struct offsets `+50`/`+51`) are stored directly in the struct, read once per object by
  `SpriteList_ClipAndCompositeOne` (`$00d856`) ahead of the actual composite call — no external
  dimension table, no per-call global.
- **Open**: `$00bf72`'s actual role. It's a real, distinct sub-pixel shift-blitter (disassembled in
  full this pass) reading from a type-selected table via a 3-word header, and its own per-call
  globals (`1246(A5)`/`1248(A5)`) happened to match the player's own `+50`/`+51` values at the
  snapshot instant this pass read them — but since `$00d856`→`$14d64` is what actually draws the
  sprite-object array, `$00bf72` is something else (a UI/inventory icon blitter is the leading
  guess, unconfirmed). `callcap`-based differential testing against it (vary `D0`-`D2` register
  presets, diff the write footprint) is the concrete way to settle what it actually draws, not more
  static disassembly.
- **Closed**: this region (`$029800`-`$02de08`) is a **sprite/prop/object catalog**, not a
  floor/wall tile sheet — correct as far as it went, but the room's wall/floor art was never a
  candidate for "hand-painted, not tile-assembled" either. §5 below found the real terrain tile
  sheet: a separate, shared, boot-time-loaded 80-tile catalog (`$03e77e`+, stride `$200`), indexed
  per room by a small compressed tile-ID grid decoded at room load. `gameplay.png`'s walls *are*
  tile-composed; the earlier "one irregular, hand-painted texture, no visible repeating tile seams"
  reading (7th pass, rechecked in §4d) was a real negative result against the wrong test (exact
  byte-block repetition on the final composited screen) — see §4d's own correction and §5's proof.
  "room/level data is not loaded via TOS `Fread`" still stands (confirmed independently by §5: the
  tile catalog and the FDC/XBIOS `Rwabs` question were never actually the same thing — the catalog
  loads once at boot via the ordinary resource-manager asset load, not a per-room disk read).

## 3. The full sprite-object-array catalog — all 22 entries, `tools/sprite_array_export.py`

The 21 non-player entries' `+52` bitmap pointers are **not** inside the `$029800`-`$02de08` player
sheet above; they cluster at `$056fc2`-`~$06975f`, inside the span-3 candidate (`$051000`-`$06b000`)
from the §2 span table that a whole-span 320px-wide render had already written off as a dead end
(correctly — it just wasn't the right way to read it; these are individually-pointed small sprites,
not one big bitmap the width of the span).

Once §2 established that width/height are ordinary struct fields (`+50`/`+51`, not something to
guess), extracting the whole array became mechanical rather than one-off — written up as a reusable
tool, `tools/sprite_array_export.py`, rather than repeating the same manual per-slot render:

```
python tools/sprite_array_export.py reversing/cadaver/gameplay_empire.snap \
    --array-ptr-field 0x1818a --stride 0x46 --count 22 \
    --w-off 50 --h-off 51 --ptr-off 52 --state-off 42 --w-unit 16 \
    --palette 0x5a9c --out-dir reversing/cadaver/sprites
```

(`--array-ptr-field` reads the array's own base from `(A5)+56` fresh out of the snapshot rather than
trusting a hardcoded address — the array is heap-allocated, its base can differ across boots.) Output
is one PNG per slot, a `contact_sheet.png`, and a `manifest.csv` (slot, struct address, state byte,
width, height, bitmap pointer, filename) — all committed under `reversing/cadaver/sprites/`.

All 22 entries decode cleanly with no bleed, and most are immediately identifiable against
`gameplay.png`'s room dressing: player (armoured knight, slot 0), two torches (slots 1-2, sharing one
bitmap), a barrel (3), an axe/pick (4), two red flowers (5, 12), two small stools (6-7), three small
red stemmed items (8-10, two sharing a bitmap), a pale fragment (11), a small teal gem (13), two
bones (14-15), a goblet (16), a **rowing boat** (17, 64×33 — the only entry wider than 32px, matches
`gameplay.png`), and three woven mats/rugs (18-19, 21) plus a **chest** (20) — both also visible in
`gameplay.png`. Full descriptions in `sprites/manifest.csv`.

State byte (`+42`): slot 0 (player) is `0`, slot 16 (the goblet) is `4`, all other 20 are `5`. Every
state-`5`/`4` entry reads as static room dressing, not a creature — so **"monster slot" in the 6th
pass's next-steps framing doesn't have a confirmed target**; nothing in this room's array is a
creature. The goblet's `state=4` outlier remains unexplained (a different animation/interaction
state than the other props, or unrelated to visuals at all) — worth a `watch` on `+42` if a monster
room is ever reached, to see what state value a real creature actually carries.

## 4. The compositing pipeline — full path from back buffer to screen (14th pass)

Full linear disassembly of `$0144b8`, `$00014d64`/`$00014f24`, and `$00bf72`/its caller
`$00bef0`-`$00bf76` against `room2_lever_boundary.snap`. All three share one core primitive — a
horizontally-shiftable 4-plane AND/OR mask composite — used for three different purposes.

### 4a. `ScreenFlip_ScanlineCopy` (`$0144b8`) — the raw buffer-to-screen copy, chunked to avoid tearing

Confirms the README's 2nd-pass description exactly, now grounded in the actual instructions: a
**fully unrolled**, non-looping sequence of `movem.l (A0)+,#$fcff` / `movem.l #$ff3f,-(A1)` pairs —
14 registers each direction, 56 bytes/pair. `A0` = the back buffer (`(A5)+120`), `A1` = the live
screen base (`(A5)`) **plus `$7d00`** (32000 decimal — exactly one full 320×200×4bpp frame), and the
destination side writes with `-(A1)` (predecrement), i.e. **the copy runs from the end of the frame
backward**. Before the first chunk, it installs a resume vector — `move.l #$1498c,$90.w` — at the
`trap #4` vector, then `andi #$dfff,SR` (drops out of supervisor mode / lowers IPL, letting the
already-pending VBL preempt). This is the "spread a 32KB copy across several VBLs" mechanism the
README already named: a `trap #4` mid-loop yield lets a VBL fire between unrolled chunks, and
`$5a98`/`$5a99` (a chunk-position byte and a "first chunk already run" flag) gate which chunks still
need doing on the next resume, so the whole-frame copy never appears half-done on screen — each VBL
either sees the old frame complete or the new one complete, never a torn mix.

### 4b. `ScreenFlip_AndCompositeSprites` (`$14d64`) — a composite-mode dispatcher, not one routine

`$14d64` is the entry point for a small family of inner loops, selected by `D6` (`cmpi.b
#$1/#$2,D6` against `$14f24`/`$15124`/`$150e2`/`$14ee4`/`$15098` — five distinct code bodies, only
`$14f24` disassembled in full this pass, the others structurally similar by inspection but not
individually traced) after first clipping the sprite's row range against the 200-row screen height
(`D1`/`D7` = row offset/height, clamped `0..200` at `$14d8c`-`$14dc2` — this is the actual clip logic
behind `SpriteList_ClipAndCompositeOne`'s "clipped composite path", not a separate routine).

`SpriteCompositeInner_AndOrMaskLoop` (`$14f24`), the aligned/shift-4..8 case, does a **sub-pixel
horizontal shift composite**: for a 16-px-wide, 4-plane group, it reads two source longwords
(`D2`,`D3` — two planes' worth), `ror.l D1,·` both by the sub-word pixel shift (`D1` = `D2_orig & $f`,
computed by the caller), builds a combined AND-mask (`D4` = the OR of both shifted words, then a
swapped-and-OR'd, NOT'd combination — the classic "mask = wherever either shifted source plane has a
set bit" trick for a multi-plane sprite with a shared transparency mask), and mask-blends into the
destination with `and.l (A1),D4 / or.l D2,D4 / move.l D4,(A1)+` per plane pair. The blend mask itself
comes from a **16-entry shift-mask table at `$5870`** (`lea $5870.l,A3; adda.w D2,A3` — `D2` here is
the pre-shift copy of the sub-pixel offset, doubled twice for a 4-byte stride), i.e. one 32-bit mask
constant per possible sub-pixel shift (0-15), not computed per-pixel at runtime. This is the same
"arbitrary bit-shift masked blitter" shape the 7th pass found in `$00bf72` (see below) — they are two
instances of the same underlying primitive, not independent implementations.

### 4c. `$00bf72` — settled: a window/panel compositor into scratch RAM, not the live screen, and not the room background

Full disassembly (`$00bef0`-`$00c242`) rather than the callcap sweep the 8th pass's next-steps
suggested — static analysis alone was conclusive enough to skip the (riskier, register-guessing)
differential test:

- Its caller (`$00bef0`) reads a small resource header via `A2` (a `-2(A2)`-prefixed table: an item
  count/stride word, then two offset words `D5`/`D4`), copies a per-item 4-word record into the
  destination object's own struct (`4(A3,D7.w)`/`6(A3,D7.w)`, `D7` = a per-object slot index read
  from that object's own byte `+14`) and derives a width/height pair that it writes into **a small
  window-descriptor record at `(A5)+372`** — `(width>>3)` and `height` as its first two words — before
  falling through into `$00bf72` itself.
- `$00bf72`'s own body: `subq.w #1,D7; movem.l#$fe40,-(A6)` — a `dbf`-driven, movem-based **bulk-zero
  of the destination window buffer** (all the registers pushed are pre-zeroed by the caller, so a
  `movem` push doubles as a fast block-clear via predecrement addressing on `A6`), then falls into
  the real per-item compositor: reads a 3-word per-entry header (`D0`=width unit, `D1`=sub-pixel
  shift, `D2`=frame index), resolves the source bitmap via `adda.w 0(A2,D2.w),A0` — **an offset table
  indexed by the header's own frame-index field**, not a flat array — reads that frame's own
  width/height (`D6`/`D7`), and composites it with `bsr $bfb0`, which is **the same AND/OR
  shift-mask primitive as `$14f24`** (identical `ror.l`/swap/`not.l`/mask-table-at-`$5870` shape,
  confirmed line-for-line). The whole thing repeats `(A5)+1172` times per call (a per-call item
  count, separate from the `dbf D7` row-clear count above) — i.e. **one call to `$00bf72` composites
  a small batch of independently-addressed frames into one destination window**, which is the shape
  of an inventory/status bar (several icons, each its own small sprite, redrawn together) far more
  than a single full-screen background.
- **Destination confirmed live, not guessed**: `(A5)+372` in `room2_lever_boundary.snap` holds
  `$0002ca80` — inside the region this doc already named `PlayerFrameSheet_Base_32x42Frames`
  (`$029800`-`$02de08`), a few bytes before the two known player-pose pointers `$2ca84`/`$2ca94`.
  This means that region is **not** necessarily static pre-authored art the way the 7th/8th passes
  assumed — it may be (at least in part) a **live composite scratch target** that this routine
  writes into, which would also explain why the 8th pass could never find a consistent per-frame
  stride there (a composited buffer has no fixed record layout; only whatever was drawn into it
  last does). Not fully proven — this is one live pointer read-back, not a differential test across
  multiple UI states — but it reframes the open question from "what is `$00bf72`'s role" (settled:
  the same shift-mask compositor as sprites, used for a multi-item window) to "is
  `$029800`-`$02de08` authored sprite data, a composite scratch buffer, or both at different offsets
  within the same 17KB region" — worth a `watch` on `(A5)+372`'s target across several different UI
  states (inventory open/closed, different items highlighted) before trusting either the 7th pass's
  "art sheet" framing or this pass's "scratch buffer" framing exclusively.

### 4d. Tile-grid vs. hand-painted background, re-checked against a specific counter-claim

The 7th pass concluded rooms are "one hand-painted background, no visible tile seams." Isometric
games of this era are very commonly tile-authored, so that conclusion deserves a concrete recheck,
not just a restatement — done this pass by decoding the live rendered room
(`room2_lever_boundary.snap`, TUNNEL) pixel-for-pixel and testing for repeated texture blocks two
ways: (a) exact block-vs-neighbor repetition on an aligned grid at seven candidate isometric tile
sizes (`32×16` down to `8×8`, plus `64×32`/`48×24`), and (b) a grid-independent scan for any
non-uniform 16×16 patch appearing at more than one arbitrary `(x,y)` offset anywhere in the frame.
Result: **no meaningful repeated texture** — the aligned-grid test's "matches" are dominated by flat
single-colour patches (excluded from test (b)), and test (b) found only 1877 distinct patches out of
1906 non-uniform samples, with the few genuine repeats (max 6 occurrences) falling along a consistent
diagonal stride (`Δx=-8,Δy=+4`, a 2:1 slope) that reads as a shared dither pattern along one wall's
diagonal edge, not a pasted texture tile. This holds as a negative result against the test it
actually ran (exact byte-block repetition on the final *composited* screen), but **the conclusion
drawn from it — "nothing tile-blits the visible room" — was wrong, corrected by §5**: the room's
walls and floor genuinely are placed from a shared 80-entry, 32×32 tile catalog (`$03e77e`+, proven
by direct render, §5), not authored as one flat per-room bitmap. The exact-match scan missed it for
two compounding reasons, both mechanical rather than a flaw in the method: every tile is composited
through the same sub-pixel masked shift-blitter as the sprite/object array (arbitrary x-offset per
isometric placement, not aligned to any fixed screen raster the scan could grid against), and at
least some tile-ID bytes in the per-room grid carry orientation/variant flag bits (high 2 bits of
the byte) that select a blit variant of the same underlying 32×32 source — so even two cells drawn
from the identical catalog tile don't necessarily leave identical final pixels. Isometric tile
authoring was the right instinct; it just isn't visible from the finished frame.

## 5. The room terrain tile catalog found — a shared, boot-loaded, 80-tile 32×32 sheet, indexed
   per room by a small compressed tile-ID grid

Prompted by a direct look at `sprites/contact_sheet.png` (§3) next to `gameplay.png`: the 22-entry
sprite/object catalog accounts for every small prop (player, torches, barrel, boat, chest, ...) but
nothing wall- or floor-sized, even though the walls are visually the dominant content of every
room screenshot. §37/§37d's claim in `mechanics.md` ("a room's background is just its full set of
static objects — walls, furniture, terrain pieces — rendered through the identical entity-rendering
pipeline") doesn't hold up against that: none of CAVERN's 22 objects are wall-scale, and the object
count (22) is far too small to cover a 10×10-tile room's walls and floor one object at a time. That
sent this pass back through §33-40's own trail rather than starting over — §36's "not yet done,
cheap next step" (find what draws the room into the display buffer *before* `120(A5)` archives it)
was never actually completed; §37 pivoted to the object-array explanation instead. Resuming that
thread found the real mechanism:

**5a. A whole-image caller census of `$00c5a8` (the `(type, index)` resource fetch, §38a) shows
every live caller uses `D0` (type) `∈ {0,1,3,4,5,6}` — type 2 (255-entry capacity) is never
referenced anywhere in the loaded program**, despite its per-room data looking superficially
promising (`disassemble.py --snap <snap> --all 0x0 0x20000`, greped for every `bsr $c5a8`/`jsr
$c5a8` site and the `D0` value set immediately before each — 33 call sites, none with `D0=2`). Dead
end, ruled out cleanly rather than left as a guess.

**5b. Types 0 and 1, keyed by the current room slot (`(A5)+1166`), are fetched together by one small
routine pair (`$00ada4`/`$00adba`, both leaf routines: `bsr $c5a8` with `D1=1166(A5)`, `D0=1` then
`D0=0`) — and a third routine, `$00add0`-`$00ae62`, is the actual per-room terrain loader.** Gated
by room-record byte `+23` bit 5 (`btst #5,23(A0)`; set for both CAVERN and TUNNEL, confirmed by
direct read — `$6c` and `$7e` respectively), it fetches the room's **type-3 record** (self) and
**type-1 data** (a small per-room byte stream: CAVERN 122 bytes at `$4eb8a`, TUNNEL 42 bytes at
`$4ec04`), zero-fills an 80-longword (320-byte) table at `(A5)+2914`, then walks the type-1 stream
through a **nibble/byte run-length decoder** (`$00ae64`/`$00ae8c`: read a value byte, read a repeat
count byte, write the value that many times at a 2-byte stride) into that table, using the room
record's own width (byte `+4`) and height (byte `+5`, §38d/§40) as the two pass sizes. **Decoded
output matches a real tile-index grid, not noise**: reading `(A5)+2914` live off both room snapshots
shows CAVERN's width-pass populated with exactly 10 non-zero rows (matching `width=10`) and TUNNEL's
with exactly 3 (matching `width=3`), each cell holding a small byte value (`0x02`-`0xc6` range) —
and CAVERN and TUNNEL's decoded grids share several identical trailing values (`0x37,0x38,0x39,
0x3a,0x3b`) at the same relative position, the first concrete sign of content shared *across* rooms
rather than authored per room.

**5c. The consumer, `$00cab6`-`$00cb28`, is a flat tile-catalog lookup, not another resource-manager
fetch.** For each byte `D7` read from the decoded `(A5)+2914` grid: if `D7` is zero, the row is
done; if `D7`'s top bit is set, execution branches to `$cbd4` (§5f — not an orientation flag, the
next pass's guess here was wrong, see below); otherwise: `A4 := (A5)+16; A4 += D7 * $200` — **a flat
array indexed by the raw tile ID, stride `$200` (512) bytes, no bounds check needed because the
grid's own bytes are already in range.**

**5d. `(A5)+16` is a shared, boot-time-loaded catalog, not a per-room pointer — rendered and proven
by direct decode.** Traced its writer (`$00b412`-`$00b41a`, inside a long boot-time asset-load
sequence at `$00b2ce`+ that also loads type 0/1/3/4/5/6's index tables via the same `jsr $112fc`
loader primitive — this is ordinary resource loading, not a per-room disk read): `16(A5) := 8(A5) +
20(A5)`, where `8(A5)` is a large allocated buffer base and `20(A5)` is itself loaded from the
resource file as a 4-byte value (`$4380` this session). A sibling field, `24(A5)`, is loaded the
same way and reads **exactly `$a000` = 40960 = 80 × 512** — the catalog's byte size, decoding evenly
into 80 tiles at the stride §5c's lookup already established. Rendering all 80 (`sprite_array_export
.py --sequence 3e77e 200 80 32 32 --palette 0x5a9c`, live palette `$5a9c`, same tool and decode path
as §3's proven prop catalog) gives 80 clean, unambiguous isometric cave-wall/floor blocks — carved
grey stone, green dither, gold-flecked rock, corner and floor variants — immediately recognisable
against every room screenshot in this doc, followed by solid-black (genuinely zero, not noise)
frames from index 80 onward, confirming the `80 × 512` boundary exactly rather than by
approximation. **Proven, not inferred**: `reversing/cadaver/tiles/contact_sheet.png` /
`manifest.csv` / `tile00_3e77e_32x32.png`-`tile79_...png`.

**5e. The grid is two ragged column-stacks (a wall height-field), not a rectangular W×H array —
decoded and rendered against the real catalog.** Re-reading `(A5)+2914` programmatically (both
passes are 10 reserved rows of 8 words each, `$00e7b0`/§39's width/height reused as the *populated*
row count, not the array's allocated size) shows each row/column holds a **variable-length run**,
not a fixed-width record: CAVERN's width-pass column 0 is `[0x37,0x38,0x39]` (3 tiles), column 8 is
`[0xc6,0x86,0x86,0x3c,0x15,0x14]` (6), column 9 is `[0x86,0x86,0x86]` (3) — i.e. **one column per
width (or height) unit, each listing the stack of tiles for that column's own visible wall slice,
bottom-to-top or top-to-bottom (direction not yet proven), silhouette-varying exactly the way an
irregular isometric wall elevation should.** This is what the type-1 RLE stream is actually
compressing: not a dense grid, but a per-column run-length list (§5b's "count, then repeat" decoder
is a per-column tile-stack unpacker). Rendered against the real 80-tile catalog
(`reversing/cadaver/py/room_tile_grid.py`, usage in its own header), CAVERN's
width-pass reads as a genuine, coherent wall elevation — neighbouring columns' top/bottom tiles
visually continue each other's carved-stone pattern — matching `gameplay.png`'s uneven cave-wall
skyline far better than a flat repeating grid would. **Proven, not inferred**:
`reversing/cadaver/tiles/cavern_grid.png` / `tunnel_grid.png` (both passes per room, every real
cell labelled with its tile id, every special/bit7 cell marked distinctly per §5f).

**5f. `$cbd4` traced in full: it is not an orientation/variant flag on an ordinary tile — it's a
second, mostly-inert marker byte, with one live sub-case that writes into the sprite/object-array
struct, not the tile catalog.** Full disassembly (`$00cbd4`-`$00cc44`): `btst #6,D7; beq $cc44`
(skip this cell if bit 6 is clear) then `btst #2,D7; bne $cc44` (skip if bit 2 is set) — so only
`D7 & $44 == $40` does anything at all. Checked against every top-bit-set value actually seen in
CAVERN/TUNNEL's grids: `0x82`(`1000 0010`) and `0x86`(`1000 0110`) both have bit 6 clear → **pure
no-op, empty cell**; `0xc6`(`1100 0110`) has bit 2 set → **also a no-op**; only `0xc2`(`1100 0010`)
passes both gates. Its live path (`$cbe0`-`$cc42`) does not touch the tile catalog or `(A5)+16` at
all — it reads a *different* global (`1138(A5)`), calls `$92e8` (not traced further this pass), and
then writes into struct fields at offsets `2,3,10,14` off a pointer taken from `52(A5)` — the same
low-offset shape (`§37d`'s room-load routine writes similar fields at `2(A1)`/`3(A1)`/`10(A1)`)
as **instantiating a sprite/object-array entry**, not drawing a tile. **Reframed, not fully
proven**: the terrain stream's top-bit bytes look like a second, sparser channel for anchoring
*objects* to specific grid cells (candidate: this may be how the boat/chest/barrel of §3's catalog
actually get their room positions, rather than the separate free-floating list `mechanics.md` §37d
already documented) — most such bytes (`bit6` clear, or `bit6` set with `bit2` set) are simply inert
padding in the two rooms sampled here. Confirming the object-anchor reading needs a `callcap`/`watch`
on `$cc2e`'s `bsr $d1f8` against a room whose grid actually reaches that live sub-case in the two
rooms checked here — not done this pass.

**5g. No tile-adjacency/compatibility ruleset exists anywhere in the traced decode or draw path —
placement is level-data, not engine-enforced.** Both the decoder (§5b, `$00add0`-`$00ae62`) and the
plain-tile consumer (§5c, `$00cab6`-`$00cb28`) were read in full this pass: neither contains a
neighbour lookup, an edge/bitmask compatibility table, or any computation that inspects an
already-placed neighbouring cell before choosing a tile. A grid cell's tile id comes directly from
the room's own compressed stream, unconditionally. **This answers the "is it Wang-tile-style rules,
or hand/tool placement" question directly: there is no in-game autotiling system to find — every
room's wall/floor layout is a fixed sequence of tile ids baked into that room's small (42-122 byte)
resource-type-1 entry, chosen by whoever authored the level data (by eye, or by an offline level
tool this codebase has no visibility into), the same way the room's *object* placements (§37d) are a
fixed list rather than a rule-generated one.** The one caveat is §5f's still-unresolved `0xc2`
sub-case — if it turns out to anchor objects by grid position, that is still level *data* naming a
specific cell, not a compatibility rule between tiles.

**Net**: `mechanics.md` §37's "a room's background is just its object array" is wrong and is
corrected there — the walls and floor are a genuinely separate, shared, tile-indexed system, decoded
per room from a tiny compressed stream (well under 128 bytes per room) into a per-column tile stack
(§5e) that a flat-indexed 80-tile catalog is drawn through, with no runtime adjacency rules (§5g).
**Open**: (a) `$92e8`/`$d1f8` (§5f's `0xc2` sub-case) — is it really an object anchor, not traced
past the struct-field writes; (b) stack direction (does column index 0 sit at the floor or the
ceiling) is not proven, only assumed consistent from the visual read in §5e; (c) a full per-room
*pixel* mosaic (grid → exact screen position, via the `2634(A5)+` per-cell screen-offset table
§39/§40 already built, composited through the masked shift-blitter like every other draw in this
engine) has not been assembled and pixel-diffed against `gameplay.png`/`room2_tunnel_entry.png` —
§5e's infographic proves the *catalog and the per-column sequence*, not yet "this exact grid, placed
this way, reproduces this exact room's exact pixels."

## Files

| File | What |
|---|---|
| `graphics.md` | this file |
| `ram_contact.png` | whole-RAM contact sheet (`gfxview.py --contact`), regenerated this pass |
| `gfxview.html` | interactive per-region viewer (`gfxview.py --html`), regenerated this pass |
| `spritesheet_29800.png` | the player's `$029800`-`$02de08` frame sheet, rendered as a 6×5 grid of 32×42 4bpp cells (struct-confirmed stride), live palette `$5a9c` |
| `player_frame_alt.png` | the player's alternate/gesture frame (`$2ca94`, 32×42) — not captured by the array export below, since only the *current* frame pointer is live in any one snapshot |
| `sprites/` | the full 22-entry sprite-object-array catalog (§3) — one PNG per slot, `contact_sheet.png`, `manifest.csv` |
| `tiles/` | the shared 80-tile room-terrain catalog (§5d) — `tile00_3e77e_32x32.png`-`tile79_...png`, `contact_sheet.png`, `manifest.csv`; plus `cavern_grid.png`/`tunnel_grid.png` (§5e) — each room's decoded per-column tile-stack rendered against the catalog |
| `../../tools/sprite_array_export.py` | the (game-agnostic) tool that produced `sprites/` (struct-driven array mode, `--base`/`--array-ptr-field`) and the raw `tiles/` catalog (fixed-stride mode, `--sequence BASE STRIDE COUNT W H`) |
| `py/room_tile_grid.py` | decodes a room's `(A5)+2914` tile-id grid (§5b/5e) and renders it against the shared catalog; usage in its own header |
