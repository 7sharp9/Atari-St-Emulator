# PowerMonger ST — the graphics pipeline, and what a modern port would change

## Status (68th pass)

PM [cr Replicants] is driven all the way into the **isometric battle view**
(`iso_view.png`): world map -> scroll icon -> "Between Pages 1-5" briefing ->
click OK -> `$b814` commits the population and `$13b9a` builds the world ->
the terrain renderer composites the land onto the stone table. Recipe in
`README.md` ("Drive recipe (68th pass)"); the dialog decode that found the OK
click is in `README.md` "PM's mouse dialog state machine".

The renderer has now been profiled with real hit counts (see "Isometric
renderer, measured" below). The **zoomed-in vs zoomed-out comparison Q2 asked
for is still open**: the iso view only recomposites on camera motion or unit
movement, and it sits idle until then. Forcing motion needs PM's in-game key
handler reversed, the per-frame loop at `$13762` reads a scancode-indexed
key-state array at `$2de6c` (`$4a`/`$4e` keypad -/+ = scroll `$ff96`; `$63`/`$64`
= scroll `$ff98`; `$65`/`$66` keypad `/` `*` = zoom `$ff9c`; `$47`/`$52` =
rotate `$ff9a`), but poking that array is overwritten each frame and `kbd 65`
did not move `$ff9c`, so the real key path (PM's ISR `$18be` -> array) needs
another look. That is a self-contained next step, not a blocker on anything else.

## Observed renderers (world map / menus)

| routine | role | shape |
|---------|------|-------|
| `$88ac`–`$8960` | menu / dialog / credits compositor | 4-bitplane word blit: per plane `move.w (A0)+,Dn / rol.w / andi.w #$fNNN`, OR the 4 planes, `move.w Dn,(A5)+`; unrolled ×6, `lea 152(A5),A5` row stride, `dbf D6` outer; command stream at `A4` |
| `$11422` | world-map per-VBL screen refresh | `lea $3f364,A0` (off-screen composed buffer) → `mulu #$a0,D0` (row×160) → `movem.l (A0)+,#$7cf8` / `movem.l #$7cf8,(A1)` (44 B/`movem`), 58 inner × 3 outer; a register-blit of the viewport strip |
| `$11458` | world-map cursor / sprite mask draw | `and.b`/`or.b` against a mask-pair table at `$1153e` |
| `$1870`–`$1876` | VBL-wait spin | ~1.9 M of ~2 M sampled steps on the static world map — PM composes once then idles |

Screen output is **direct-to-shifter**: displayed base from `$FFFF8201/8203`
(`$024400` at menus), not `_v_bas_ad`. Palette straight to `$FFFF8240`. No
XBIOS `Setscreen` / `Setpalette` — `ATARI_TRACE_OS` sees nothing.

So the whole pipeline is: build the frame into an off-screen RAM buffer with
software plane blits, then one bulk `movem` copy to the shifter buffer per VBL,
double-buffered via the shifter base register.

## Isometric renderer, measured (68th pass)

Profiled from `pm67_p4c.snap` + the OK click, tracing `ATARI_TRACE_EVENTS` over
the world-build (`b2` -> terrain visible, ~13 frames) and over 20 frames of the
settled static view. `trace_cfg.py --blocks`. Addresses are in the relocated
game image (base `$1050`); disassembled from the snapshot RAM.

| routine | role | what it actually does | measured |
|---------|------|-----------------------|----------|
| `$14b62` | entity iteration + projection driver | walks the 50-byte object records `$51b66+$32 .. $57f66` (~490 slots), `tst.b 5(A1)` active-gate, per-type `jmp` table at `$14bba` keyed on `31(A1)`; calls `$163ea` per moved entity | scan hits ~27 active entities/frame (`$14b72`/`$16230` x511 over 19 VBLs) |
| `$163ea` | entity world -> screen-cell projection | `cell = ((worldY & 0xff00) >> 2) + (worldX & 0xff)` (byte-wise add), pure **shift + add, no MUL/DIV** (the iso axis mapping is baked into the world-coord encoding). Stores new (X,Y) at `8(A1)`/`10(A1)`, compares old vs new projected cell, `beq $1648c` **skips the redraw when the cell is unchanged** | per moved entity |
| `$1648e` | terrain height / type sampler | `lea $438ee,A4`; index by `worldX>>2` and `worldX>>6`; reads a type byte at `0(A4)` and a height byte at `-8257(A4)` / flag at `+8257(A4)` (two parallel 8 KB planes) | per terrain cell touched |
| `$164bc` | terrain-quad edge slope | `sub.w D6,D0 / sub.w D7,D1 / ext.l / divu D2,D0 / divu D0,D1`, dx/dy then dy/dx for a scanline walk of a terrain quad edge. **This is the DIVU the 67th-pass overflow / divide-by-zero fix unblocked** (`16(A1)` = edge height, can be 0 or drive the quotient past 16 bits) | per drawn terrain edge |
| `$16738` | per-entity sprite blit | visibility-culled via `btst #7,7(A6)` / `btst #6,7(A6)`; walked in cell order from the per-commander `$13c`-byte records at `$51538` (`mulu #$13c` to index) and the global entity chain, a painter's pass, order comes from the cell bucket, not a sort | per visible entity |
| `$12ce0` | offscreen buffer -> shifter screen | `moveq #32,D1 / move.w #$1f3,D0` then `movem.l (A0)+,#$0cfc` / `movem.l #$0cfc,(A1)` ×2, `adda.w D1,A1`, `dbf`, 500 iterations, 6 longs (24 B) per `movem`, 32-byte row stride. One full loop = one frame's terrain area | runs **once per camera change**, not every VBL (500 block hits total over 20 static frames) |
| `$12d08` | 16x16 -> 32 multiply helper | classic 3-`mulu` partial-product long multiply, called via `$12c9a` | fixed-point scale ops during the build |
| `$1af32` | mouse / timer poll ISR (`rte` at `$1af44`) | **not a renderer**, it is just the hottest thing in the trace because every routine is interrupted by it | ~60/frame |

**Two findings that revise the design section below:**

1. **Projection is not MUL/DIV bound.** `$163ea` projects with a shift and an
   add; the only divides in the terrain path are `$164bc`'s two `DIVU`s for edge
   slopes, one pair per drawn quad edge. The cost is in the fills and the
   per-entity sprite blits, not the geometry, so "cache projected geometry"
   (point 1 below) buys much less than expected on the ST build.

2. **PM already does frame-to-frame coherence.** `$163ea` skips an entity whose
   projected screen cell did not change, and `$12ce0` (the bulk buffer->screen
   copy) only fires when the camera moved. The settled iso view costs almost
   nothing per frame (~27 active-entity checks, no full recomposite). Point 3
   below ("dirty rects / scroll the previous buffer") is a *degree* improvement,
   not a missing capability, the ST engine's version is "recompute nothing
   while the camera is still".

## The isometric view — from PM lore + what the ST engine must be doing

PM's play field is a software isometric height-mapped terrain viewport with
painter's-algorithm sprite compositing (people, buildings, boats, sheep),
recomposited on camera motion or unit movement (not unconditionally every
frame, see the measured section above). Zoom is a discrete LOD select
(3 levels). Zoomed out = more terrain cells + more sprites inside the frustum +
more overdraw, all on an 8 MHz 68000 with **no blitter** on a plain STF. That is
the cause of the zoomed-out slowdown: it is fill-rate and per-primitive-count
bound, not logic bound.

## What a modern port would do differently

Grounded in the pipeline shape above (off-screen compose + bulk blit + software
plane fills), not in general knowledge:

1. **Cache projected geometry.** *Revised by the 68th-pass profile:* the ST
   engine's per-entity projection (`$163ea`) is already a shift + add, not
   `MULS`/`DIVS`, and it skips entities whose screen cell did not move. The only
   divides are `$164bc`'s edge-slope `DIVU`s, one pair per drawn terrain quad
   edge. Precomputing a per-zoom quad mesh still helps the *fill* setup, but the
   projection itself is not the bottleneck it looks like from PM lore.
2. **Span / occlusion buffer.** The `$88ac`-style blit writes every plane word
   whether or not it is later covered. A per-scanline span buffer (draw
   front-to-back, skip covered spans) removes the overdraw that dominates the
   zoomed-out frame.
3. **Frame-to-frame coherence / dirty rects.** *Partly already present:* PM
   recomputes nothing while the camera is still (`$12ce0` bulk copy only fires
   on camera motion; `$163ea` skips unmoved entities). What it does *not* do is
   scroll the previous buffer on camera motion, a scroll still triggers a full
   viewport recomposite. A modern port scrolls the old buffer and redraws only
   the newly-exposed edge strip + the cells under moving sprites.
4. **Per-zoom tile LOD as real assets.** Instead of projecting full-detail
   terrain and letting it shrink, ship pre-rendered tile art per zoom level
   (which PM half-does) and at the furthest zoom draw flat coloured cells with no
   per-vertex math at all.
5. **Blitter-shaped fills.** The terrain-fill and sprite-composite inner loops
   are hand-unrolled `movem`/`rol`/`and` word pushers because the STF has no
   blitter. On an STE (or a modern target) these become blitter ops / a single
   `memcpy`-class span fill, collapsing the fill cost by ~4–8×.
6. **Separate the sprite sort from the redraw.** PM's people/animals move a few
   pixels per frame; their back-to-front order rarely changes. Keep a sorted
   sprite list and insertion-sort the few that moved, rather than re-sorting the
   whole set each frame (this is exactly what Super Sprint's `$e84c` does wrong
   too — full `exg` network every frame).

## To finish Q2: the zoom comparison

Still open: hot-block hit counts and dropped-VBL cadence at zoomed-in vs
zoomed-out. Prerequisite is making the iso view redraw. The per-frame loop at
`$13762` scrolls (`$ff96`/`$ff98`), rotates (`$ff9a`) and zooms (`$ff9c`) from a
scancode-indexed key-held array at `$2de6c`, but:

- poking `$2de6c + scancode` directly is overwritten each frame (PM rebuilds it
  from its own key state), and
- `kbd 65` (keypad `/`, the apparent zoom-out key) did not change `$ff9c`, so
  PM's ISR `$18be` either maps different scancodes into that array or gates on a
  modifier / mouse mode. Trace `$18be` with a key held to find the mapping.

Once the view scrolls: `ATARI_TRACE_EVENTS` over ~10 frames at `$ff9c` low
(zoomed in) then ~10 at `$ff9c` high, `trace_cfg.py --blocks`, and compare
`$14b62` entity-scan count, `$1648e`/`$164bc` terrain-cell/edge counts, and
`$12ce0` copy-loop iterations between the two, plus the `$1270` VBL count per
N steps for the dropped-frame cadence. The renderer routines are catalogued in
"Isometric renderer, measured" above.
