# Cadaver — graphics (7th pass)

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

- **Confirmed**: `$029800`-`$02de08` (17,928 bytes, ~27 frames at 672 B/frame) is the player's own
  packed multi-frame sprite sheet — bounded on both sides by independently-known addresses, and
  every frame decodes as a recognisable, complete character pose at 32×42 px under the struct-
  confirmed dimensions and the game's own live palette.
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
- **Open, corrected framing**: this is almost certainly a **sprite/prop/object catalog**, not a
  floor/wall *tile* sheet. `gameplay.png`'s cave walls read as one irregular, hand-painted texture
  (no visible repeating tile seams), which argues against a room being tile-assembled at runtime at
  all. A live re-run with `ATARI_TRACE_GEMDOS=1` from cold boot (20M steps, stalled before
  gameplay — the restore-game prompt needs a scripted ESC keypress this pass didn't send) showed
  only 2 GEMDOS calls total, meaning **room/level data is not loaded via TOS `Fread`** — consistent
  with the Medway-Boys section's existing finding that this game's loader reads by raw sector
  number, bypassing GEMDOS entirely. Confirming "one pre-rendered background bitmap per room" vs.
  "some other room-layout structure" needs either (a) tracing the FDC/XBIOS `Rwabs` sector-read
  destinations during an actual room load (not yet captured — the gameplay snapshot is already
  past that point), or (b) triggering a room transition in-game and diffing `ScreenBufferA`/`B`
  around it (blocked on the still-open "how does the player actually move between
  rooms/tiles" question — see README Next steps).

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

## Files

| File | What |
|---|---|
| `graphics.md` | this file |
| `ram_contact.png` | whole-RAM contact sheet (`gfxview.py --contact`), regenerated this pass |
| `gfxview.html` | interactive per-region viewer (`gfxview.py --html`), regenerated this pass |
| `spritesheet_29800.png` | the player's `$029800`-`$02de08` frame sheet, rendered as a 6×5 grid of 32×42 4bpp cells (struct-confirmed stride), live palette `$5a9c` |
| `player_frame_alt.png` | the player's alternate/gesture frame (`$2ca94`, 32×42) — not captured by the array export below, since only the *current* frame pointer is live in any one snapshot |
| `sprites/` | the full 22-entry sprite-object-array catalog (§3) — one PNG per slot, `contact_sheet.png`, `manifest.csv` |
| `../../tools/sprite_array_export.py` | the (game-agnostic) tool that produced `sprites/` — struct-driven sprite/object array batch export |
