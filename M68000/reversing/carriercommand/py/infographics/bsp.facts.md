# bsp.svg: facts and sources

Figure: `gen_bsp.py` writes `scratchpad/carrier/infographics/bsp.svg` (PNG: `rsvg-convert -z 2 bsp.svg -o bsp.png`).
The model is `py/render/model.py`'s decode of model 5 (builder `$a2d8` run by callcap from `c_s30.snap`), parsed into a
tree by `bsp_survey.py`. Panel C is one draw captured by `bsp_order.py`; the check totals are `bsp_order_sum.py` over
every run of `bsp_order_all.sh` (outputs in `scratchpad/carrier/infographics/bsp/`). Docs: `render.md` sections 1, 4, 6.

Regenerate: `cd M68000 && reversing/carriercommand/py/infographics/bsp_order_all.sh` (about a minute), then
`uv run python -I reversing/carriercommand/py/infographics/gen_bsp.py`, then `rsvg-convert` as above.

| fact in the figure | source |
|---|---|
| no z-buffer; objects depth-sorted, each model a BSP tree, back-face test per leaf item | render.md intro, 1, 4 |
| model 5 is the Manta | render.md 6 (entity `$5df5a` type 5 in `m_takeoff.snap`; re-read here: `8603 0005 ...` in both `m_deck` and `m_takeoff`) |
| 18 vertices from a box builder (`$a2d8`, half-extents 50, 20, 100), 3 planes, 3 nodes, 4 leaves, 20 items, 22 polygons | `bsp_survey.py 5` / `gen_bsp.py` printout |
| planes are vertex triples (10,6,4), (1,4,11), (13,11,10) | model 5 plane table, `gen_bsp.py` printout |
| all three normals have x = 0 (0,0,-880), (0,-3750,-250), (0,-2775,185), so the side view shows them edge-on | computed with `$9426`'s halved cross product |
| P0 is z = 50; P1 passes y = 0 at z = 50 and y = 10 at z = -100 ("rises 10 in 150 toward the tail"); P2 is the deck polygon's plane | vertex coordinates (1, 4 at y 0, z 50; 11 at y 10, z -100; 10, 13 at y 20, z 50) |
| leaves L1 nose (6 items, 6 polygons), L2 fin (3, 3), L3 deck and flanks (3, 3), L4 belly and wings (8, 10) | tree parse; names from the polygons' vertices (fin = vertices 14..17, deck = [13,10,11,12]) |
| every polygon vertex of a leaf lies on its subtree's side of each ancestor plane or on it: A side <= 0, B side >= 0 | `gen_bsp.py` side check, all 9 (leaf, plane) pairs |
| node `[plane][offset.w][A][B]`, B at A + offset; leaf `[$ff][count][items]`; stream at `$4703c` starts `00 00 46 ff 06 03` | render.md 4; bytes read from `c_s30.snap` (identical in `m_deck.snap`, asserted) |
| flag `$ff` (eye on the positive side) draws A then B, otherwise B then A | `$8e98..$8ece` (read); matched in every draw below |
| side flags computed by `$940a` with the same test (`spl`) | `$940a..$9424` (read); 684 of 684 flags matched |
| panel C: the game's own draw of model 5 from `m_deck.snap` with `$5df5e`/`$5df60` poked to `$e000`/`$2000`, step 172859993, centre (-1, -60, 349) | `bsp/order_deck_e000_2000.json`, first model-5 draw |
| its flags P0 `$ff`, P1 `$00`, P2 `$00`; leaf order L1, L4, L3, L2; 10 of 20 items back-facing; 12 of 22 polygons filled | same capture |
| render: the captured view-space vertices projected by `X * 256 / Z`, game palette of `m_deck.snap` through `$1544`, dithers averaged | `gen_bsp.py`; projection as render.md 3 / model.py `render` |
| back-face test `n = (v1-v0)/2 x (v2-v0)/2`, `d = eye - v0`, skip on negative, halved to 16 bits | render.md 4; `face_gate.py` 120/120 |
| object layer: 18-byte nodes at `$5a82a`, 128 max, `$5d94` walks far to near | render.md 1, labelled "from code" |
| model layer: 1264 draws of 6 models, every item, face sign and polygon in model.py's order | `bsp_order_all.sh` totals below |

## The drawing-order check (render.md 7 first item, session item 5)

Command: `M68000/reversing/carriercommand/py/infographics/bsp_order_all.sh`, raw totals in
`scratchpad/carrier/infographics/bsp/order_sum.txt`. `bsp_order.py` runs its own `stserver`, stops at every entry to
`$8e68` (the far draw routine, also reached from `$9066` when the object is beyond its LOD distance), and records the
game's view-space vertex table (`($8de)`), its plane flags (`($8e2)`, 72 bytes), the object centre `$a7c/$a80/$a84`,
every leaf item visited (`$8ee0`, A0), every `$9426` result (`$8ef4`, D0) and every polygon filled (`$8f14` clipping
path, `$8f9e` direct path; A0 = the polygon's index list). It then runs model.py's walk (`model.dot` for flags and
faces) on the same vertices and compares. Runs: `m_takeoff`, `m_deck`, `m_air`, `c_s30`, `c60`, `c80`, `c_mv`
(2.4M steps each) and `m_deck` with the Manta's two angle words poked to 8 x 3 values (600k steps each); 31 runs.

| measure | result |
|---|---|
| draws compared (models 1, 5, 37, 88, 95, 96; 43, 185, 257, 261, 257, 261 draws) | 1264, all identical |
| leaf items visited, in order | 12314 / 12314 |
| polygons filled, in order | 6189 / 6189 |
| back-face signs | 12228 / 12228 (6664 back-facing) |
| plane side flags | 684 / 684 |
| control: the walk with A/B swapped differs from the game | in 228 of 228 draws that have planes |
| Manta flag patterns covered (P0,P1,P2) | `ff,00,00` 88, `00,ff,ff` 34, `00,00,00` 33, `ff,ff,ff` 30 draws |

So the decoded BSP order is the game's for these draws. `c80` and `c60` drew no `$8e68` model in their budgets.

## Flags

- **`watch 9de 2` cannot do this check.** `$9de` is written only at `$8f46` (the clipping path, taken when `$121a` is 0)
  and `$91b6` (`$9066`'s near path). The direct path `$8f9e` -> `$44a6` reads the colour from the stream at `$4518`
  without storing it. All 6189 polygons above went the direct path (0 through `$8f14`), so the watch would have recorded
  nothing. render.md 7 and `sessions/carriercommand.md` item 5 name that method.
- **render.md 4 "(Inferred ...)", render.md 6 "the drawing order has not been compared with the game's" and README line
  280** are superseded for the `$8e68` path by the table above. Not covered: `$9066`'s near path (`$9098` on), the
  clipping path `$8f14`, the routines `$8fac`/`$9514`/`$9516`/`$9540`, and the Manta flag patterns where P1 and P2
  differ: P1 and P2 had the same flag in every Manta draw, so 4 of the 8 patterns were exercised.
- **Node "planes" 64 and 65 are not planes**, and that is why model.py's walk fails (IndexError) on models 1, 2, 3 and
  38: `$940a` sets flag 64 to `$ff` (`st 64(A2)` at `$9412`) and model 2's builder `$a60a` sets 65 (`sle`/`seq 65(A2)`
  at `$a644`, `$a650`). Node plane lists: model 1 `[0, 1, 64, 64, 2]`, 2 `[0, 3, 4, 1, 64, 64, 2, 5, 8, 6, 7, 65]`,
  3 `[..., 64, ..., 65]`, 38 `[64, 0, 1]`. render.md 6 attributes the failure to decode 1, 2, 3, 38 to animated
  builders; the pseudo-planes are at least part of it (read from code; with flag 64 taken from the game's table,
  model 1 matched in all 43 draws, flag 64 `$ff` in each).
- **model.py's `dot` does not halve to 16 bits as `$9426` does** (`face_gate.model` does). Its sign agreed in all 12228
  tests here, but a far or large object could differ.
- **Interrupt re-entry at a stserver breakpoint**: an interrupt taken at `$8ee0`/`$8ef4` stops there again after the RTE;
  `bsp_order.py` drops the repeat (4 in all runs), the same effect CLAUDE.md records for REPL `hits`.
- "Far subtree first" (render.md 4) holds geometrically for the Manta: each A subtree lies on its plane's negative side
  (side check above), and `$ff` (eye positive) draws A first.
