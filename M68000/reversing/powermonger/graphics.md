# PowerMonger ST — the graphics pipeline, and what a modern port would change

## Status (69th pass)

PM [cr Replicants] is driven all the way into the **isometric battle view**
(`iso_view.png`): world map, scroll icon, "Between Pages 1-5" briefing, click OK
(`$b814` commits the population, `$13b9a` builds the world), then the terrain
renderer composites the land onto the stone table. Recipe and the dialog decode
that found the OK click are in `README.md`.

The 69th pass reversed PM's in-game key handling (the "input-gated idle"
blocker), drove the camera, and profiled the renderer settled vs moving. The
literal zoomed-in / zoomed-out hit-count table is **not delivered**: this build's
keypad zoom is a latent no-op and the functional zoom path needs a
snapshot-register harness to trigger. What that path is, and why the settled
view is not actually idle, is below ("In-game camera control" and "To finish
Q2").

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

## Isometric renderer, measured (68th–69th pass)

Profiled from `pm67_p4c.snap` / `pm68_isoview.snap` + the OK click:
`ATARI_TRACE_EVENTS` over the world-build (terrain appears ~13 frames in) and
over 20–30 frames of the settled view; `trace_cfg.py --blocks`. Addresses are in
the relocated game image (base `$1050`), disassembled from the snapshot RAM.

| routine | role | what it does | measured |
|---------|------|--------------|----------|
| `$14b62` | entity iteration + projection driver | walks the 50-byte object records `$51b66+$32 .. $57f66` (~490 slots), `tst.b 5(A1)` active-gate, per-type `jmp` table `$14bba` keyed on `31(A1)`; calls `$163ea` per moved entity | ~27 active entities scanned/frame (x511 over 19 VBLs) |
| `$163ea` | entity world → screen-cell projection | `cell = ((worldY & $ff00) >> 2) + (worldX & $ff)` (byte-wise add): **shift + add, no MUL/DIV**, the iso axis mapping is baked into the world-coord encoding. Compares old vs new projected cell, `beq $1648c` skips the redraw when unchanged | per moved entity |
| `$1648e` | terrain height / type sampler | `lea $438ee,A4`, index by `worldX>>2` / `worldX>>6`; type byte at `0(A4)`, height/flag at `∓8257(A4)` (two parallel 8 KB planes) | per terrain cell touched |
| `$164bc` | terrain-quad edge slope | `sub.w D6,D0 / sub.w D7,D1 / ext.l / divu D2,D0 / divu D0,D1`, dx/dy then dy/dx for a scanline walk of a quad edge. **The DIVU the 67th-pass overflow / divide-by-zero fix unblocked** (`16(A1)` = edge height, can be 0 or push the quotient past 16 bits) | per drawn terrain edge |
| `$16738` | per-entity sprite blit | visibility-culled via `btst #7,7(A6)` / `btst #6,7(A6)`; painter order from cell buckets and the per-commander `$13c`-byte records at `$51538` (`mulu #$13c` index), not from a sort | per visible entity |
| `$e4de`+ | unrolled span filler | `$e4da: jmp 82(PC,D6.w)` into a ~120-deep `move.l D0/D1,(A2)+` chain (Duff device), span length in D6; the caller loop is `$e45a`/`$e45e`/`$e462`. **This is the fill-rate hot path** | ~40% of all instructions in the settled view (69th) |
| `$f000`–`$f13c` | fixed-point slope divide | `divu` + `lsl.l #8` normalise, dx/dy and dy/dx, feeds the span walk | ~8800 instr-equiv / 30 settled frames |
| `$12ce0` | offscreen buffer → shifter screen | `move.w #$1f3,D0` then `movem.l (A0)+,#$0cfc` / `movem.l #$0cfc,(A1)` ×2, `adda.w D1,A1`, `dbf`: 500 rows, 24 B/`movem`, 32-byte stride | **~once per 3 frames** (10 hits / 30 frames, 69th — periodic double-buffer flush, *not* motion-gated) |
| `$fe04` | zoom → geometry | from D1 = zoom index (1–7) derives 13 tile-size / stride / cell-count words at `$fdea`–`$fe02`; the renderer reads those, **not `$ff9c`** | on every zoom change (via `$13f60`) |
| `$fe8e`–`$ff94` | rotation terrain re-scan | per-cell height scan, bounds `$fdec`/`$fdee` (zoom-dependent); runs when `$ff9a` (rotation angle, `& $f0`, 16 steps) changes | ~4600 cell iterations per angle step (69th) |
| `$12d08` | 16×16 → 32 multiply helper | classic 3-`mulu` partial-product long multiply, via `$12c9a` | fixed-point scale during the build |
| `$1af32` | timer ISR (`rte` at `$1af44`) | **not a renderer**, hottest in the trace only because it interrupts everything | fixed ~12–15% of instructions, settled == moving |

Findings (69th pass, `pm68_isoview.snap` at zoom index 4, `trace_cfg.py --blocks`,
instruction-weighted, 30 frames settled vs 30 with the rotate key poked):

1. **Fill-rate bound, not geometry bound.** The `$e4de` unrolled `move.l` span
   filler is ~40% of all executed instructions. `$163ea` projection (shift + add)
   and `$164bc` DIVU are together <1%. The 68th-pass conclusion holds and is now
   quantified.
2. **A rotation step is nearly free in aggregate (+0.6%).** One angle change adds
   ~4600 `$fe8e` cell iterations but removes an almost equal amount of `$e4de`
   fill / `$e4xx` idle spin (settled 382k instr-equiv, rotating 384k). The view
   has large idle headroom — the `$1870` / `$e4xx` spin absorbs the transform
   cost. There is no per-frame full recomposite; `$163ea` / `$1648e` / `$16738`
   counts are byte-identical settled vs moving.
3. **The settled view is not idle.** It still runs `$163ea` (~14/frame),
   `$16738` (~4/frame) and flushes `$12ce0` every ~3 frames. The 68th-pass claim
   "`$12ce0` only fires when the camera moved / settled costs almost nothing" was
   imprecise — the flush is periodic, and unit-animation projection runs every
   frame.

The zoomed-out slowdown on real hardware is fill-rate and primitive-count bound
(more terrain cells + more sprites + more overdraw, 8 MHz 68000, no blitter on a
plain STF), not logic bound. Zoom is a discrete 7-level LOD select
(`$13f83` table `[_,84,42,28,21,17,14,12]`, index → `$fe04`).

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

## In-game camera control (69th pass)

**IKBD ISR `$18be`** (vector `$118`, confirmed installed). On each `$fffc02`
byte: `$f7` starts a 5-byte mouse abs-position packet (→ `$1c48f` / `$2df92` /
`$2df94`); anything `< $f6` is a scancode → `$1962`:

- `$2a` / `$36` (left / right **shift** make) are intercepted and only set the
  flag `$2df8a` — they are **never written to the key array**.
- every other make code → `array[sc] = $ff` at `$2de6c`; break code (`bit7`) →
  `array[sc & $7f] = 0`.

**Per-frame camera loop `$13762`** reads that array:

| slot (dec) | scancode | effect |
|-----------|----------|--------|
| 54 | `$36` right-shift | **master gate**: `tst.b 54(A0) / beq` skips the whole block |
| 71 / 82 | `$47` / `$52` | rotate `$ff9a += / -= $10`, then `& $f0` |
| 74 / 78 | `$4a` / `$4e` | `$ff96 += / -= $a` |
| 99 / 100 | `$63` / `$64` | `$ff98 -= / += $a` |
| 101 / 102 | `$65` / `$66` | `$ff9c -= / += 1` |
| 51 / 52 | `$33` / `$34` | commander select `$57ffc ∓ 1`, then `jsr $fe04` |

The blocker resolves: the gate at slot 54 is the right-shift scancode slot, and
`$18be` **never sets it** (shift is special-cased out). `kbd 65` did nothing
because slot 54 was 0. To drive the camera from the REPL, poke both:

```
w 2dea2 ff000000     # slot 54 (gate) = $ff   -- $2de6c + $36
w 2deb2 00ff0000     # slot 71 ($47, rotate +) = $ff  -- covers $2de6c+$46..49
s 12000              # one frame; re-poke each frame, the loop only steps ~1 in 6
```

What actually moves the view:

- **`$ff9a` (rotation) is the only live camera parameter.** Poking it via the
  keypad path re-projects the whole terrain (full-screen frame diff, visually
  confirmed — `iso_rotated.png`). 16 discrete angles.
- **`$ff96` / `$ff98` (scroll) have no reader** in the loaded iso overlay
  (checked abs-long and abs-short). 20 keypad increments → byte-identical frame.
  Iso-view scrolling is cursor/edge driven (`$13118`+), not these vars.
- **`$ff9c` (keypad zoom) is a latent no-op.** `$137da` / `$137e8` bump `$ff9c`
  but — unlike the rotate/commander cases — **never call `$fe04`**, so the tile
  geometry (`$fdea`–`$fe02`) is never recomputed. 11 increments → byte-identical
  frame. The only real reader of `$ff9c` is a coincidental data constant.

## To finish Q2: the zoom comparison

The functional zoom path is **`$13f60`** (reached from the `$13212` mouse-cursor
command dispatch, cases `$13386` / `$1338a` / `$1338e` / `$133a0`): it sets
`$ff9c = $13f83[index]` **and** `jsr $fe04` with `D1 = index` (1–7). `$fe04`
derives the 13 render constants at `$fdea`–`$fe02`. Current state = index 4
(`$fdea..$fe02` == the D1=4 row; formulas transcribed in a comment in
`scratchpad/`).

Hand-poking `$fdea`–`$fe02` to another index's constants is **unsafe**: an
inconsistent stride sends the `$e4de` span filler past its buffer into code at
`$f0xx`, and the emulator then executes the corrupted word (`$4c45`) as an
illegal instruction. This is the filler scribbling on itself, **not** an
emulator gap — `$f0xx` is never written during normal play (`watch` clean over
settled + rotating runs).

Next: a snapshot register-edit harness — load `pm68_isoview.snap`, set
`PC = $fe04`, `D1 = 1` (or `7`), run to the `rts` at `$fe8c`, restore PC, then
force a re-render with a rotation step and capture `ATARI_TRACE_EVENTS`. Compare
`$e4de` / `$fe8e` / `$163ea` / `$16738` / `$12ce0` instruction-weight and the
`$1270` VBL cadence at index 1 vs index 7. The renderer-cost model above
predicts index 7 (zoomed out, small tiles, more cells) shifts weight from
`$e4de` fills toward `$fe8e` / projection but stays within frame budget on this
sparse early-mission map.
