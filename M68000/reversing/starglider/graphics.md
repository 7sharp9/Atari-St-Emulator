# Starglider graphics: the wireframe pipeline

Starglider draws every object as hidden-line-removed wireframe: each model is a set of convex faces, faces that point
away from the camera are culled, and the edges of the remaining faces are drawn once each with an integer Bresenham
line into the four ST bit-planes. There is no polygon fill and no depth sort. All arithmetic is 16-bit fixed point
with Q14 (16384 = 1.0) rotation matrices. Addresses are runtime absolute; `N(A6)` is the global block at `$5bf00`.

Proof scripts are in `py/render/` (run from that directory or from `M68000/` with `python3`; `models.py` needs the `.venv` python for
PIL). Each gate compares the full `callcap` memory delta against a Python reference (`rref.py`) and has a
broken-model control that fails.

## 1. The frame

`$fb74` runs once per main-loop pass (about 48,000 steps). It does the following in order:

1. Clears the viewport: `$14556` jumps through vector `64(A6)` to `$1455c`, an unrolled `movem.l` zeroing rows 10 to
   128, bytes 8 to 151 of each 160-byte row.
2. Prints text and the HUD (`$bcba`, `$b91a`).
3. Draws the gunsight (`$10124`).
4. Builds the view matrix (`$ede4`).
5. Draws the ground dust (`$f336`).
6. Builds the object lists (`$101a8`, `$10344`).
7. Draws each object on the view list with `$f6a8`.
8. Runs the laser (`$131f8`) and the refuelling message (`$fd14`).

The end of the pass is `$13a4e`, which calls `$150fa`. It increments the frame counter `482(A6)` and waits for the
beam (`$150d4`, polling `$ff8207`). It then writes the palette word `578(A6)` to `$ff8240`, which is how hit flashes
are shown. Finally it toggles the draw buffer `0(A6)` between `$70000` and `$78000` and points the shifter at the
other buffer (read, not gated).

**Proof.** `gate_frame.py <snap> 1 6 20` models a whole `$fb74` call from the pass's start state. The visible lists
and camera-space centres are taken from RAM after the call, because the list builders are gated separately (`objects.md`).
- Every viewport byte outside the gunsight box matches over passes 1, 6 and 20: 49,368 of 49,368 on `g_game2` and
  49,368 of 49,368 on `g_game1`.
- Only 50 to 56 bytes are drawn per frame in these sparse scenes (4 or 5 objects). The per-object gates below carry
  the dense cases.
- The gunsight sprite blit (`$143ce`) is not modelled. All 92 unmatched bytes before the box was excluded lie inside it.
- The control (`--control`, the dust pass omitted) scores 49,283 of 49,368 (99.828%) on `g_game2`.

## 2. Camera and matrices

The camera is the player:
- Position x, y, z are the words `302/304/306(A6)`. y is negative upward.
- Angles are pitch `314`, yaw `316` and roll `318`, with 4096 units per turn.
- The sine table at `108(A6)` = `$1e8f8` and the cosine table at `112(A6)` = `$1f0f8` hold 4096 words each of
  16384·sin and 16384·cos. The cosine table is the sine table shifted by 1024 entries.
- `$fb74` loads sin/cos pairs into `458..468(A6)`: pair 1 from pitch, pair 2 from yaw, pair 3 from roll.
- Roll is negated and indexed as `(a & $1ff) * 16` bytes, so roll has only 512 steps per turn.

`$ede4` builds the 3x3 view matrix at `360..376(A6)`, column-major Q14, from Euler products (for example
`m360 = c2c3 + s2s3s1`, `m370 = -s1`, `m376 = c1c2`). `$eca0` builds the object matrix at `342..358` the same way.
Its angles `378/380/382` are the object's angles plus the camera's (the roll negated). It caches the angles at
`384..388` and rebuilds only when they change.

Three transforms use these matrices. Each term is `muls`, `asl.l #2`, `swap`, so the product is Q14 and the sum wraps
in 16 bits.
- `$ec1e` rotates a world-relative vector by the view matrix and also leaves x and y in `398/400(A6)`.
- `$eb8a` takes a model vertex to view space: object matrix, then `asr.w #4`, then plus the object's view-space
  centre `404..408(A6)`.
- `$eeac` is `$eb8a` with a per-vertex cache. A2 points at a flag byte per vertex, and a hit returns the cached row.

**Proof.** `N=40 python3 gate_math.py`: `$ede4`, `$eca0`, `$ec1e`, `$eb8a`, `$eeac` match 40/40 each. The control,
with a wrong Q14 shift, scores 0/40, 8/40, 0/40, 0/40 and 10/40; the cached routines' passes are cache hits that
change nothing.

## 3. Models

Each object type maps to a model through the word table `$15802`.
- Types 1 to 28 use the model of the same number, except type 6 (the silo), which uses model 18. Model 6 has no type.
- Models 1 and 10 are identical (the Walker).
- Model 28 is the "GAME OVER" lettering.

Each model has a 16-byte header at `$15ada + 16·model`. Its words are vertex count, edge count, face count, then
the offsets of the vertices, edges, faces and end, then 0. The offsets are relative to `120(A6)` = `$15caa`. The data
blocks are:
- **Vertex:** 8 bytes (x, y, z, pad).
- **Edge:** 4 bytes, two words each holding 8 × the vertex index.
- **Face:** an 18-byte header, then the face's vertex indices, then its edge indices. In the header, word 0 is the
  colour (the same for every face of a model); a negative word 6 means the face is never culled; words 14 and 16 are
  the vertex and edge counts. Words 2 and 4 are copied to `546/548(A6)` with no use found.

For 24 of the 28 models the face edge lists end exactly at the model's end offset. Models 3 and 23 to 26 carry
trailing data. Headers past model 28 are not models.

[`models.png`](models.png) renders all 28 models from `g_game1`'s RAM (`py/render/models.py`). Names come from the
in-game database (`objects.md` section 2):

| model | object | model | object |
|---|---|---|---|
| 1, 10 | Walker | 15 | Stomper |
| 2 | Pyramid mine | 16 | Skim fighter |
| 3 | type 3 (fires lasers; unnamed) | 17 | type 17 (static; unnamed) |
| 4 | Energy Tower | 18 | silo (type 6) |
| 5 | type 5 (static; unnamed) | 20 | Juno cannon |
| 7 | Starglider drone | 21 | Lotus Starfighter |
| 8 | Armoured Transport Vehicle | 22 | docking bay |
| 9 | Egron Battle Tank | 23 | Tri-launcher |
| 11 | refuel hub (two lines) | 24 | Egron Neutron Missile |
| 12 | type 12 (missile code, never spawned) | 25 | Egron Homing Missile |
| 13 | Bute fighter | 26 | Pyramid Launcher |
| 14 | Diamond Proximity Mine | 27 | StarGlider One |

## 4. Drawing an object: back-face culling

`$f6a8` draws the object whose type is in D0:

1. It looks up the model, builds the object matrix with `$eca0`, and clears the vertex flags at `1800(A6)` and the
   edge flags at `1930(A6)`.
2. For each face it transforms three vertices (`$eeac`), shifts them right by 2, and takes `(e1 × e2) · P2`.
3. A face is drawn when that dot product is negative, when the face's word 6 is negative, or when `701(A6)` is set.
   `$10070` sets `701` around a call to `$fbb8` and restores it (purpose not read); H in the model viewer toggles it
   (`frontend.md` section 4), which shows every edge of the model.
4. A drawn face flags its vertices and edges.
5. The flagged vertices are transformed once into the cache at `760(A6)`.
6. Each flagged edge is drawn once through `$f8f2`. It is drawn in the colour of the last face visited, which is
   harmless because a model has one colour.

`$f938` draws a destroyed object (records with the exploding flag `36(A4)` set, `objects.md` section 4). It does not
cull. Each face's edges are pushed outward along the face normal, scaled by `610(A6)`, with a fall term from the
table at `$fb34`, so the model flies apart face by face.

**Proof.**
- `python3 gate_obj.py <snap> 30` (the snapshot path relative to `M68000/` or absolute: the REPL runs there):
  `$f6a8` at natural entries matches 30/30 on both `g_game1` (types 3, 7, 8) and `g_game2` (types 3, 8, 13). The
  control, with the cull sign flipped, scores 0/8.
- `python3 gate_obj_all.py 3` (and `FN=f938`): all 28 types in 3 random poses, every screen byte equal, `$f6a8`
  84/84 and `$f938` 84/84. No control was run for this gate.

## 5. Edges: near clip, projection, window clip, Bresenham

`$f8f2` takes one edge in view space through four stages:

- **Near clip, `$14f00`.** The only 3D clip is a near plane at z = 2. The frustum outcode code after it
  (`$14f06/$14f34/$14f76`) is jumped over by a `bra`, and a raw longword scan finds no reference to it.
  - The clip has a scale bug. It computes t = `((2 − z1) << 16) / (z2 − z1)` with `divs`, then `(dx · t · 2) >> 16`,
    which is twice the correct intercept. A true intercept fraction of 0.204 lands at x = 407 instead of 204.
  - For a fraction of 0.5 or more the `divs` overflows, leaves its operands unchanged, and the endpoint is not moved.
  - The reference reproduces both behaviours, and the gate agrees on every case.
- **Projection.** Screen = `(v << 530(A6)) / z + centre`. The shift is 7 in low resolution and the centre
  `508/510(A6)` is (143, 68). A `divs` overflow leaves the shifted dividend in the register, which the reference
  also reproduces.
- **Window clip, `$14cfc`.** A Cohen-Sutherland clip against x 16..303, y 10..128 (`326..332(A6)`), with outcode bits
  y<min 1, x<min 2, y>max 4, x>max 8. It returns the endpoints swapped when the second one was clipped.
  - A random search found an input that never terminates, (589, −1674, −110) to (1532, 1538, 6), in both the
    reference and the emulator (the emulator's loop detector stops at `$14d2c`). Whether play can reach it is open.
- **Line, `jmp 44(A6)`.** In low resolution this is `$13cb4`, an integer Bresenham:
  - x always ascending, row stride ±160, error step `sub dx; bls` for steep lines or `sub dy; bls` for shallow ones.
  - It ORs the pixel mask into the planes selected by the bits of the colour `520(A6)`, through a 16-entry table of
    loop variants.
  - Colour 10's shallow-slope entry jumps into the steep loop. No model uses colour 10, so the bug never shows.
  - Vectors `44..68(A6)` select the line, dot, text, clear and sprite routines. The monochrome high-resolution
    variants (`$13b78`, `$14384`, `$144c4`) were read, not gated.

**Proof.** `N=150 python3 gate_line.py`: line 150/150, colour 10 20/20, window clip 300/300, near clip 300/300,
`$f8f2` 301/301 (the non-terminating input included). The control scores line 129/150, colour 10 12/20 and `$f8f2`
235/301; it does not touch the clippers, which score 300/300 under it.

## 6. Ground dust and dots

The green dots on the ground are drawn by `$f336`:
- There are 40 points at `2060(A6)`, each an x, z pair with y = 0.
- Each frame every point is made relative to the camera and rotated with `$ec1e`.
- A point is plotted when z > 2 and |x|, |y| ≤ 2z, and its projection lies strictly inside the window.
- Otherwise the point respawns at a random place ahead of the camera: two `$f23e` draws (one 13-bit, one 13-bit
  minus `$1000`) rotated by the yaw.
- In missile view (`712(A6)` set) the dust uses the missile camera, angle `626` and position `618/622`.

Points are plotted by `$142f4` → `$142fa`:
- The plane offsets in `522..528(A6)` come from the table `$13af2`, filled by `$13aca`.
- A point is two pixels wide when z < `$700` and two pixels tall when z < `$1000`, so near dust looks bigger.

**Proof.**
- `python3 gate_dust.py 12`: dust 12/12, both RNG draws 12/12, and the poked-camera respawn path 16/16. The control
  scores 2/16 on the poked path. The natural frames contain no respawns, so the control does not fail there.
- `python3 gate_dot.py 30`: natural 30/30 and random 70/70. Controls 9/10 and 59/70.

## 7. Bearings and text helpers

- `$12f1c` returns the 12-bit bearing of a relative vector, using the arctangent tables `$1e0f4` (when |dz| ≥ |dx|)
  and `$1e4f6`, 512 words each. Enemies steer with it (`objects.md` section 3). With dx = 0 the `divs` takes the
  divide-by-zero exception (vector 5); the gate's random inputs hit that twice and exclude both. Whether play can give
  an object exactly dx = 0 when the bearing is taken is open. `python3 gate_bearing.py 200`: 198/198, control 0/39.
- `$f634` converts a nibble to an ASCII hex digit, and `$f60e` writes a word as four hex digits. `python3
  gate_text.py 60`: 60/60 each, controls 0/20 and 15/20.
- `$bfb0` blits one 8-row glyph column into four planes (read, not gated). The text printer is `$bcba`
  (`frontend.md`).

## 8. Dead code: stereo and the debug keys

The image carries the remains of a stereoscopic display. None of these routines has a caller in a raw scan of
`$ab8c..$56264` (branches, `jsr`/`jmp`, PC-relative and absolute longwords):
- **`$ac70`** flips bit 0 of the video base high byte `$ff8201`, which moves the displayed screen by `$10000`, and on
  each flip reads `$fb0000` or `$fa0000`, the two cartridge ROM select ranges. A read there is the only way the ST
  can signal a cartridge-port device.
- **`$d3f8`** negates the eye offset `648(A6)` (set to 10 at game start, `$e596`) and makes the same cartridge read
  for the new sign.
- **`$d40e`** toggles `701` (draw every face), and **`$d414`/`$d41a`** add or subtract 1 from the projection shift
  `530(A6)` (7 for the 320-wide window, 8 for the 640-wide one: `$1382c` branches on `706` bit 1 and the two paths
  end at `$13908`/`$139d4`), which zooms the whole view.

The last three sit between the in-flight key handler `$d29a` and its practice-mode code, in the handler's style
(`not.b` / `addq` / `rts`), but no compare in `$d29a` branches to them. The one live piece is the model viewer's 3
key, which still adds `648` to the camera x around the draw (`$de18`) but never alternates it, so it only nudges the
model sideways.

A screen moved by 64K in step with a cartridge-port strobe and an eye offset that changes sign each frame is how LCD
shutter glasses were driven, one eye per frame (inferred: no stereo product is named in the game). The game's screens
are now at `$70000`/`$78000` and the cockpit picture is kept at `$60022`, so `$ac70`'s 64K flip no longer matches
the memory layout.

## Open

- The gunsight sprite (`$143ce`) and the radar/scanner second view (`618..628(A6)`, window `672..`) are not modelled.
- Face header words 2 and 4 and model header word 7 (`480(A6)`) have no known use.
- The monochrome paths are unread beyond the vector table.
