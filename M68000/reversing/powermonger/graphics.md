# PowerMonger ST — the graphics pipeline, and what a modern port would change

## Status (67th pass)

PM [cr Replicants] is driven past the campaign world map (click the top-left
scroll icon) into the **mission-briefing screen** ("Between Pages 1-5", three
commanders, a stone table, "How many People in this land?"). Reaching it needed
two 68000 divide fixes (DIVU/DIVS quotient-overflow, and divide-by-zero to
vector 5) that the isometric-view setup overlay exercises; see `README.md`
"Bug 4".
The briefing → **isometric zoomable battle view** transition (the renderer Q2 is
about) is still not found: the OK-button clicks reach PM's mouse state machine
but the data-driven dialog hit-test doesn't accept them. So **the terrain
rasteriser still has not been profiled with real hit counts**. Everything below
the "observed" line is grounded in routines seen running; the "modern port"
section is design analysis that holds regardless of the profiling gap.

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

## The isometric view — from PM lore + what the ST engine must be doing

PM's play field is a software isometric height-mapped terrain viewport, redrawn
each frame, with painter's-algorithm sprite compositing (people, buildings,
boats, sheep). Zoom is a discrete LOD select (3 levels). Zoomed out = more
terrain cells + more sprites inside the frustum + more overdraw, all on an 8 MHz
68000 with **no blitter** on a plain STF. That is the entire cause of the
slowdown: it is fill-rate and per-primitive-count bound, not logic bound.

## What a modern port would do differently

Grounded in the pipeline shape above (off-screen compose + bulk blit + software
plane fills), not in general knowledge:

1. **Cache projected geometry.** The isometric projection of a terrain cell is a
   fixed function of (cell height, zoom, view angle). PM re-derives it every
   frame with `MULS`/`DIVS`. Precompute one screen-space quad mesh per zoom level
   at territory load; per frame you only translate by the scroll offset.
2. **Span / occlusion buffer.** The `$88ac`-style blit writes every plane word
   whether or not it is later covered. A per-scanline span buffer (draw
   front-to-back, skip covered spans) removes the overdraw that dominates the
   zoomed-out frame.
3. **Frame-to-frame coherence / dirty rects.** The view scrolls slowly and most
   of the terrain is unchanged between frames. A modern port scrolls the previous
   buffer and redraws only the newly-exposed edge strip + the cells under moving
   sprites, instead of the `$11422`-style full-viewport recomposite every VBL.
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

## To finish Q2

Get past the briefing screen into the iso view. From `pm66_newconq.snap` (world
map): `mouse move` onto the top-left scroll icon (~18,18 in 320-space) +
`mouse down l`/`up l` → the "How many People in this land?" briefing. Then the
open problem is the briefing's OK-button (or population-arrow) click — decode the
menu descriptor at `$7a36` that the hit-test at `$7298` walks (see README "PM's
mouse dialog state machine"), or find whether a non-zero population / double-click
is the precondition. Once in the iso view: `ATARI_TRACE_EVENTS` over ~10 frames
zoomed-in vs zoomed-out, `trace_cfg.py --blocks`, compare hot-block hit counts +
dropped VBLs between the two zooms. The renderer overlay loads above `$1050`.
