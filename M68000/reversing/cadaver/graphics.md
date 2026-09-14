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

Rendering that wider region (`decode_span.py --grid`, 32×32 px cells, st-interleaved 4bpp, live
palette `$5a9c`) as a scan from `$026800` forward shows a clean transition: streaky
noise/pixel-junk through `$029800`, then **35 consecutive cells of coherent, distinct pixel art**
(varied objects — a repeated red-roofed motif, cream/tan highlights, green) from `$029800` up to
exactly `$02de08` — the start of `CompositeBackBuffer` itself. Past that point the same grid
render degrades back into horizontal-streak noise, matching `CompositeBackBuffer` holding live,
constantly-rewritten frame state rather than static source art. Both boundaries line up with
already-known addresses (`CompositeBackBuffer` at the end; the 6th pass's own `$2ca84`/`$2ca94`
frame pointers fall *inside* the range, at byte offsets 25×512+132 and 25×512+148 — **not**
tile-index-aligned to the 32×32 grid used to render it).

That non-alignment is the tell: **the 32×32 grid was a diagnostic rendering choice, not the real
packing.** The true format is almost certainly variable-size entries prefixed by the 3-word header
`$00bf72` reads (`D0`/`D1`/`D2` — likely dimensions/x-shift/palette or frame-select fields, not
individually decoded this pass), packed back-to-back with no fixed stride. The 32×32 grid happened
to produce recognisable, non-garbled art because most entries are close enough to that size to
render legibly, not because 512 bytes is the real per-entry size.

### What's confirmed vs. open

- **Confirmed**: `$029800`-`$02de08` (17,928 bytes) is real packed source art, not code or scratch
  state — bounded on both sides by independently-known addresses, decodes cleanly under the game's
  own live palette, and directly precedes `CompositeBackBuffer`. The player's known animation-frame
  pointers (6th pass) land inside it.
- **Confirmed**: it is read by a sub-pixel masked blitter (`$00bf72`) that is a *second*, more
  general compositor than the already-named `SpriteCompositeInner_AndOrMaskLoop` (`$14f24`) —
  worth a `.sym` entry (`SpritePlot_ShiftedMaskBlit_00bf72`) and cross-checking whether it's what
  actually draws the sprite-object array entries, or a separate prop/room-furniture layer.
- **Open**: the exact per-entry header format (width/height/shift/count — which word is which).
  `dump_vector.py`/`callcap`-style differential testing against `$00bf72` (snapshot before/after,
  vary `D0`-`D2` register presets per the REPL's `callcap Rn=` convention) is the concrete way in,
  not more static disassembly.
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

## Files

| File | What |
|---|---|
| `graphics.md` | this file |
| `ram_contact.png` | whole-RAM contact sheet (`gfxview.py --contact`), regenerated this pass |
| `gfxview.html` | interactive per-region viewer (`gfxview.py --html`), regenerated this pass |
| `spritesheet_29800.png` | the `$029800`-`$02de08` region, rendered as a 7×5 grid of 32×32 4bpp cells (diagnostic framing, not the true per-entry stride — see above), live palette `$5a9c` |
