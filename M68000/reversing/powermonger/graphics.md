# PowerMonger ST — the graphics pipeline, and what a modern port would change

## Status (68th pass)

PM [cr Replicants] is driven all the way into the **isometric battle view**
(`iso_view.png`): world map, scroll icon, "Between Pages 1-5" briefing, click OK
(`$b814` commits the population, `$13b9a` builds the world), then the terrain
renderer composites the land onto the stone table. Recipe and the dialog decode
that found the OK click are in `README.md`.

The renderer is profiled with real per-frame hit counts (below). Q2's
zoomed-in vs zoomed-out comparison is **still open**, the iso view only
recomposites on camera motion, and it sits idle until PM's in-game key handler
is reversed. See "To finish Q2" at the bottom.

## Pipeline shape (world map / menus / iso view all share it)

| routine | role | shape |
|---------|------|-------|
| `$88ac`–`$8960` | menu / dialog / credits compositor | 4-bitplane word blit: per plane `move.w (A0)+,Dn / rol.w / andi.w #$fNNN`, OR the 4 planes, `move.w Dn,(A5)+`; unrolled ×6, `lea 152(A5),A5` row stride, `dbf D6` outer; command stream at `A4` |
| `$11422` | world-map per-VBL screen refresh | `lea $3f364,A0` (off-screen composed buffer), `mulu #$a0,D0` (row×160), `movem.l (A0)+,#$7cf8` / `movem.l #$7cf8,(A1)` (44 B/`movem`), 58 inner × 3 outer |
| `$1870`–`$1876` | VBL-wait spin | dominates every static screen (world map, briefing, settled iso view) |

Screen output is **direct-to-shifter**: displayed base from `$FFFF8201/8203`
(`$024400` at menus, `$01c700` in the iso view), not `_v_bas_ad`. Palette
straight to `$FFFF8240`. No XBIOS `Setscreen` / `Setpalette`. The whole pipeline
is: build the frame into an off-screen RAM buffer with software plane blits,
then one bulk `movem` copy to the shifter buffer, double-buffered via the
shifter base register.

## Isometric renderer, measured (68th pass)

Profiled from `pm67_p4c.snap` + the OK click: `ATARI_TRACE_EVENTS` over the
world-build (terrain appears ~13 frames in) and over 20 frames of the settled
view; `trace_cfg.py --blocks`. Addresses are in the relocated game image
(base `$1050`), disassembled from the snapshot RAM.

| routine | role | what it does | measured |
|---------|------|--------------|----------|
| `$14b62` | entity iteration + projection driver | walks the 50-byte object records `$51b66+$32 .. $57f66` (~490 slots), `tst.b 5(A1)` active-gate, per-type `jmp` table `$14bba` keyed on `31(A1)`; calls `$163ea` per moved entity | ~27 active entities scanned/frame (x511 over 19 VBLs) |
| `$163ea` | entity world → screen-cell projection | `cell = ((worldY & $ff00) >> 2) + (worldX & $ff)` (byte-wise add): **shift + add, no MUL/DIV**, the iso axis mapping is baked into the world-coord encoding. Compares old vs new projected cell, `beq $1648c` skips the redraw when unchanged | per moved entity |
| `$1648e` | terrain height / type sampler | `lea $438ee,A4`, index by `worldX>>2` / `worldX>>6`; type byte at `0(A4)`, height/flag at `∓8257(A4)` (two parallel 8 KB planes) | per terrain cell touched |
| `$164bc` | terrain-quad edge slope | `sub.w D6,D0 / sub.w D7,D1 / ext.l / divu D2,D0 / divu D0,D1`, dx/dy then dy/dx for a scanline walk of a quad edge. **The DIVU the 67th-pass overflow / divide-by-zero fix unblocked** (`16(A1)` = edge height, can be 0 or push the quotient past 16 bits) | per drawn terrain edge |
| `$16738` | per-entity sprite blit | visibility-culled via `btst #7,7(A6)` / `btst #6,7(A6)`; painter order from cell buckets and the per-commander `$13c`-byte records at `$51538` (`mulu #$13c` index), not from a sort | per visible entity |
| `$12ce0` | offscreen buffer → shifter screen | `move.w #$1f3,D0` then `movem.l (A0)+,#$0cfc` / `movem.l #$0cfc,(A1)` ×2, `adda.w D1,A1`, `dbf`: 500 rows, 24 B/`movem`, 32-byte stride | **once per camera change, not every VBL** (500 block hits total over 20 static frames) |
| `$12d08` | 16×16 → 32 multiply helper | classic 3-`mulu` partial-product long multiply, via `$12c9a` | fixed-point scale during the build |
| `$1af32` | mouse / timer poll ISR (`rte` at `$1af44`) | **not a renderer**, hottest in the trace only because it interrupts everything | ~60/frame |

Two findings:

1. **Projection is not MUL/DIV bound.** `$163ea` is a shift and an add. The only
   divides in the terrain path are `$164bc`'s two `DIVU`s per drawn quad edge.
   The cost is fills and per-entity sprite blits, not geometry.
2. **PM already does frame-to-frame coherence.** `$163ea` skips an entity whose
   projected cell did not move; `$12ce0` (the bulk buffer→screen copy) only fires
   when the camera moved. The settled iso view costs almost nothing per frame
   (~27 active-entity checks, no recomposite). What PM does *not* do is scroll
   the old buffer on camera motion, a scroll triggers a full viewport rebuild.

The zoomed-out slowdown is fill-rate and per-primitive-count bound (more terrain
cells + more sprites + more overdraw, on an 8 MHz 68000 with no blitter on a
plain STF), not logic bound. Zoom is a discrete 3-level LOD select.

## What a modern port would do differently

Grounded in the pipeline above (off-screen compose + bulk blit + software plane
fills):

1. **Cache the fill setup per zoom.** Projection itself is already cheap
   (finding 1), but a precomputed per-zoom screen-space quad mesh removes the
   per-frame edge-slope `DIVU`s and fill-span setup; per frame you only translate
   by the scroll offset.
2. **Span / occlusion buffer.** The `$88ac`-style blit writes every plane word
   whether or not it is later covered. A per-scanline span buffer drawn
   front-to-back removes the overdraw that dominates the zoomed-out frame.
3. **Scroll the previous buffer.** PM recomputes nothing while the camera is
   still (finding 2) but does a full rebuild the moment it moves. Scroll the old
   buffer and redraw only the newly-exposed edge strip + the cells under moving
   sprites.
4. **Per-zoom tile LOD as real assets.** Ship pre-rendered tile art per zoom
   level (PM half-does this); at the furthest zoom draw flat coloured cells with
   no per-vertex math.
5. **Blitter-shaped fills.** The hand-unrolled `movem`/`rol`/`and` word pushers
   become blitter ops / a single `memcpy`-class span fill on an STE or a modern
   target, roughly 4–8× off the fill cost.
6. **Separate the sprite sort from the redraw.** Sprites move a few pixels/frame
   and their back-to-front order rarely changes, insertion-sort the few that
   moved (same mistake as Super Sprint's `$e84c`, a full `exg` network every
   frame).

## To finish Q2: the zoom comparison

Open: hot-block hit counts + dropped-VBL cadence at zoomed-in vs zoomed-out.
Prerequisite is making the iso view redraw. The per-frame loop `$13762` scrolls
(`$ff96`/`$ff98`), rotates (`$ff9a`) and zooms (`$ff9c`) from a scancode-indexed
key-held array at `$2de6c` (`$4a`/`$4e` keypad -/+ → `$ff96`; `$63`/`$64` →
`$ff98`; `$65`/`$66` keypad `/` `*` → `$ff9c`; `$47`/`$52` → `$ff9a`). But
poking `$2de6c + scancode` is overwritten each frame and `kbd 65` did not move
`$ff9c`, PM's ISR `$18be` maps scancodes into that array some other way (or
gates on a modifier). **Trace `$18be` with a key held to find the mapping.**

Then: `ATARI_TRACE_EVENTS` ~10 frames at `$ff9c` low, ~10 at `$ff9c` high;
`trace_cfg.py --blocks`; compare `$14b62` / `$1648e` / `$164bc` / `$12ce0`
counts and the `$1270` VBL count per N steps between the two.
