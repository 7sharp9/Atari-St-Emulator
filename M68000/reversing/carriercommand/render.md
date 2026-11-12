# Carrier Command: the 3D renderer

A filled-polygon engine for an 8 MHz 68000 with no FPU or blitter. Objects are culled and depth-sorted into a
binary tree and drawn far to near; each model is a precompiled BSP tree whose leaves are back-face tested;
polygons are scan-converted into a span filler that rewrites its own code for each colour. There is no
terrain height field: islands, buildings and trees are ordinary models, and sea and sky are one clipped
half-plane fill.

Proof labels as in `ai.md`. Gate: `py/render/gate_render.sh` (`gates.toml` "render"), every proof a callcap
comparison against a Python model from `c_s30.snap`:

| Proof | Script | Count |
|---|---|---|
| sine table `$1864` against `round(16384 sin(2 pi k / 4096))` | `sine_gate.py` | 4096/4096 |
| 2D rotations from the six sin/cos pair slots | `rot_gate.py` | 360/360 |
| rotations by angle `$a12c`/`$a16c` | `rot_gate.py` | 120/120 |
| projection `$53f4` (77 vertices behind the near plane, overflow divides included) | `proj_gate.py` | 480/480 |
| back-face test `$9426` (60 back-facing) | `face_gate.py` | 120/120 |
| span filler `$4678` rows (10 colour codes x 13 spans x 2 parities x 3 prior extents) | `span_gate.py` | 780/780 |

## 1. The frame

`$14152` calls `$76da` (object pass), `$5ec2` (horizon) and `$5d94` (draw), in that order (proven from an
event trace, `py/render/seq.py`).

- `$76da` sets the camera's sin/cos pairs, then walks the 64-byte object records at `$5dcda` (+2 type,
  +4/+6/+8 angles, +10/+14/+18 position longs). Each object gets a bounding-sphere frustum cull, a rotation into
  view space, a near-plane test and a screen-extent test (`$8042`); survivors are inserted by depth into a
  binary tree of 18-byte nodes at `$5a82a` (`$5d06`), at most 128 (the 129th is a `trap #12`).
- `$5ec2` draws the sky and sea as a sloped half-plane split (`$50b6` and on): the horizon is the projection of
  two points at infinity rotated by the camera's pitch and roll, with full-viewport sky or sea fills as the
  degenerate cases.
- `$5d94` walks the tree in order (far to near) and calls `$7624` per object, a painter's sort at object level.

The tree order and the horizon geometry are read from code (inferred).

## 2. Trigonometry and rotation

Angles are 16 bits, 65536 to the turn. The sine table at `$1864` holds 4096 words of `16384 sin`, indexed by
`angle >> 4`; cosine is the entry 1024 further on (proven 4096/4096). The table that looked like a separate
symmetric table at `$1c28..$24b0` is entries 482..1574 of it.

There is no 3 x 3 matrix. A rotation is a chain of 2D rotations, each by a stored (sin, cos) pair:
`$9f76` stores sin and cos for an angle; the object's three angles fill the pairs at `$a64/$a68/$a6c` and the
negated camera angles those at `$a70/$a74/$a78`. Each routine rotates one coordinate pair by one stored pair:
forward `x' = (x c - y s) * 4 >> 16`, `y' = (y c + x s) * 4 >> 16` (`$a036`, `$a040`, `$a0fe`, `$a108`), and
inverse (`$a09a`, `$a0a4`). The wide variants (`$a000`, `$a064`, `$a0c8`) halve their long inputs until they
fit, rotate, and shift back. Angle +6 is the heading: a displayed bearing of 005 is `$3e8`.

## 3. Projection `$53f4` / `$53e4`

Inputs: view-space vertex words, the object centre in view space (`$a7c/$a80/$a84`, longs), the near plane
`$a88`, and the viewport descriptor at `$6fc` (here `$3fea`: clip 32,6 to 287,133, shifts 8,8, centre 160,70,
size 256 x 128).

```
X = x + $a7c;  Y = -y - $a80;  Z = z + $a84
if Z < $a88: vertex invalid (y := $80000000)
halve X, Y, Z until (2Z) >> 16 == 0
sx = trunc((X << 8) / Z) + 160;  sy = trunc((Y << 8) / Z) + 70
```

A `divs` overflow falls back to a long division (`$5492`, `$54ba`). `$53f4` also sets `$121a` when every
vertex is within 16-bit range, which lets the polygon filler skip clipping. Proven 480/480.

## 4. Hidden surfaces

Three methods are stacked:

1. Objects are sorted by depth (section 1).
2. Each model is a BSP tree. `$940a` computes a side flag per plane from three of the model's vertices
   (`$ff` when the eye is on the positive side, using the face test below); `$8e8c` walks the tree, a node
   being `[plane < $80][offset][subtree A][subtree B at A + offset]`, drawing the far subtree first; a leaf is
   `[$ff][item count]`. (Inferred; the 60 decoded models in `models.png` overlap correctly.)
3. Each leaf item can carry three test vertices, and `$9426` drops it when it faces away: with `n` the cross
   product of the halved edge vectors and `d` the vector from the vertex to the eye, it returns `d . n` and the
   caller skips on negative. Proven 120/120.

## 5. Polygons and the span filler

`$444c` fills polygons given as inline (x, y) lists; `$44a6` takes vertex-index bytes into the projected table
and is used when `$121a` says no clipping is needed. The vertex ring is doubled into `$5b22a`, the top vertex
found, and left and right edges walked with 16.16 slopes (`$48aa`, `$48fa`). Polygons that could overflow are
first clipped to +/-16384 by edge bisection, taking midpoints rather than dividing (`$59d8`). Lines go through
`$555c`/`$5766`, discs through `$5bf0`/`$4be6`. (Inferred.)

`$4678`, the most-called routine in the game (2079 calls per 1.2M steps), fills one scanline of 4-plane
words: masked edge words from the tables at `$4658` and `$476c` and an unrolled middle of `move.l A0,(A4)+ /
move.l A5,(A4)+` entered by a computed jump (A0 holds planes 0-1, A5 planes 2-3).

**It is rewritten for each colour.** `$494c` takes a colour code, looks it up in the 64 byte pairs at `$1544`
(codes 0..15 solid, 16..63 two-colour dithers) and patches the filler: the branch opcode at `$46c0` (`bvs`
for solid, `bvc` for dither), the edge instructions at `$46e8..$46ee` and `$4758..$475e`, and the dither
immediates at `$47b4..$47c8` built from the `$aaaa`/`$5555` rows at `$4ae4`/`$4b64`. A dither is a one-pixel
checkerboard whose phase flips each scanline (bit 0 of the line counter in D7's high word).

**Spans are widened to overlap the previous one.** `$9ee`/`$9f0` hold the previous span's ends; the new span
becomes `xr = max(xr, prev_xl)`, `xl = min(xl, prev_xr)`, which closes the gaps a steep edge would leave
between scanlines (the rule is proven; the purpose is inferred). Spans are then clamped to the 256-pixel
viewport offset by 32. Proven 780/780 rows, 0 mismatches in the `$9ee/$9f0` updates; the gate's first models
failed on exactly these details, so it discriminates.

## 6. Models

An object's type indexes the 16-byte records at `$8660` (near and far distance thresholds, three level-of-
detail model ids) and the model id the 99 longs at `$4c4ce`. `$7624`/`$764e` choose the level of detail and
jump to the model's own draw routine (`$8e68` far, `$9066` near):

```
[long draw routine][long LOD distance, $9066 and $9540 only][long builder][builder arguments]
[derived-vertex program][word vertices to project][byte planes][planes x 3 vertex bytes][BSP stream]
```

- The builder makes vertices from the object's angles: `$a2d8` builds 8 box corners from three half-extents;
  `$a3e6` adds vertices as Q14 combinations of the box frame. Others (`$a570`, `$a75e`, `$a1ac`, `$a8f4`) exist,
  and some animate by game state (`$a5c4` rotates a part by a local angle and forces BSP sides).
- The derived-vertex program `$54e4` is `[n][n x (op, index)]` with load, store, average-with and add.
- A leaf item is `[flags]`: bit 0 three test vertices and a skip length; bit 1 polygons `[n][count][indices]
  [colour]`; bit 2 lines; bit 3 discs `[vertex][radius][colour]`.

`models.png` is every table entry decoded and drawn with the engine's own formulas at one orientation
(`py/render/sheet.py`): conifers (24..27), lattice towers built from lines (42, 91), a house (43, 94),
an airstrip (36), a hexagonal pad (21), flat island tops (37 and others). The decode is checked only by
polygon counts agreeing with the leaf structure and the renders looking right; the drawing order has not been
compared with the game's. Models 1, 2, 3 and 38 (animated builders) and the 21 models using the non-BSP draw
routines `$8fac`, `$9514`, `$9516`, `$9540` do not decode yet.

## 7. Open

- Compare the decoded BSP order with the game's own colour sequence (`watch 9de 2` during one model).
- The animated builders, the non-BSP draw routines, the near-clip path `$9098`, the line and disc drawers, and
  `$1ff46` (600 calls per 1.2M steps).
- Which model ids are the carrier, Manta and Walrus.
