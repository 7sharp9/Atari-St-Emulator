#!/usr/bin/env bash
# Regenerates walkthrough.md with showboat, then verifies it. Run from anywhere:
#   bash port/walkthrough/build_walkthrough.sh
# Needs the logic and stepper built first (see the document intro).
set -euo pipefail
cd "$(dirname "$0")"
D=walkthrough.md
sb() { uvx showboat "$@"; }
note() { sb note "$D"; }                       # text on stdin
run() { sb exec "$D" bash "$1" >/dev/null; }

rm -f "$D"
sb init "$D" "How PowerMonger draws its world" >/dev/null

note <<'EOF'
This walks through one frame of PowerMonger's isometric view (Atari ST, 1990), following the data from the heightmap in RAM to the pixels on screen. The code is the F# port in `../godot/logic/`, which reproduces the 68000 routines closely enough to match the game's own frame buffer at 94-98% of pixels, and the terrain alone at 99.7-99.96% away from sprites. Addresses like `$fccc` are routines in the original executable, so every section can be traced back to the disassembly.

The whole renderer, in the order it runs. `$f898` is the driver: once per game tick it re-projects if the camera moved, then runs the walk for the current angle.

| stage | 68000 routine | F# |
|---|---|---|
| read the heightmap window | `$3f86c`, `$438ee` planes | `Terrain.Map` |
| project the 9 x 9 grid of corners | `$fecc` | `Projection.projectGrid` |
| pick the walk for this camera angle | `$f97e` | `Fill.quadrant`, `Fill.plan` |
| visit the 64 cells, two triangles each | `$f98e` / `$fa9a` / `$fbb4` / `$fccc` | `Fill.planQ0`..`planQ3` |
| fill each triangle with a dither pattern | `$ef62`, `$e420`, `$e3e6` | `Fill.ef62Raster`, `ddaWalk`, `ditherIndex` |
| draw each cell's sprites straight after its triangles | `$115e0` | `Scene.steps`, `Sprites.blitEntity` |

There is no depth buffer and no sort. The order of the walk does all the hidden-surface work, and most of this document is about why that is enough.

Everything below runs against the real code. Build it first with `dotnet build ../godot/logic/PmLogic.fsproj` and `dotnet build ../stepper/PmStepper.fsproj`. The live checks call `probe.fsx` in this folder, which prints facts computed by the port; `uvx showboat verify walkthrough.md` re-runs them all.
EOF

note <<'EOF'
## 1. The world is a heightmap

The map is 64 x 128 cells. Each cell has four bytes, stored as four separate planes: a **type** byte (what the ground is), a **height** byte, a **flag** byte, and a **control** byte, which is the height the projector uses to lift the corners.
EOF
run "sed -n '19,21p;28,36p' ../godot/logic/Terrain.fs"
note <<'EOF'
The camera looks at an 8 x 8 block of cells, which needs a 9 x 9 grid of corners. These are the control-plane heights under that grid at the start of mission 1, camera cell (36,47). The hill in the middle is the one you see on screen.
EOF
run "dotnet fsi probe.fsx heights"

note <<'EOF'
## 2. Projecting the corners

`$fecc` turns each corner of the 9 x 9 grid into a screen position. It rotates the grid by the camera yaw, lifts each corner by its height above the lowest corner in view, then divides by the distance from an eye 320 units back. That is an ordinary perspective projection in 68000 integer maths.

The yaw is a byte, 256 units per turn, stepped 16 at a time: 16 angles of 22.5 degrees. The start pose is yaw 15, byte `$f0`. `Zoom` (21) is the size of a cell in world units, and heights are scaled by `Zoom / 16`. `Horizon` (130) is subtracted from each lifted height before the divide and added back after, so it sets where the horizon sits on screen.
EOF
run "sed -n '26,61p' ../godot/logic/Projection.fs"
note <<'EOF'
Two details matter later. `ry`, the rotated distance along the view direction, is what the divide uses: a larger `ry` means a smaller `d`, so a nearer corner. And nothing is clipped here. All 81 corners are projected whether they are on screen or not; clipping happens one scanline at a time inside the triangle filler.

The result for the start pose, in the raw coordinates the game draws in (it adds 64 px for the HUD strip when it writes to the screen):
EOF
run "dotnet fsi probe.fsx corners"
note <<'EOF'
The far edge (row 0) sits higher on screen than the near edge (row 8). Between them the hill lifts rows 1 to 4 above row 0 in places, so the grid folds back on itself on screen. Those back slopes come up again in section 5.

## 3. The walk: far to near, one cell at a time

The game never sorts anything. It visits the 64 cells in a fixed order and draws each cell completely before moving on. Anything drawn later lands on top. This is the painter's algorithm: paint the background first and let nearer things cover it. It only works if nothing is drawn before something that could be in front of it.

Which order is safe depends on where the camera faces, so the game has four copies of the walk and picks one from the yaw (`$f97e`):
EOF
run "sed -n '406,414p' ../godot/logic/Fill.fs"
note <<'EOF'
Each handler is two nested loops of eight. The port splits each one into its two decisions: the order the loops reach the cells, and how each cell is cut into triangles (section 4). In the excerpt, C00 is the cell's top-left corner `corners[row, col]`, C10 the next column, C01 the next row and C11 the diagonal one; `packed` is `(x << 16) | y`, the handlers' way of comparing two screen points. Here is the handler for the start pose, `$fccc`:
EOF
run "sed -n '314,334p' ../godot/logic/Fill.fs"
note <<'EOF'
Laid out on the grid, the order `planQ3` produces at yaw 15, then the order at yaw 7, where the camera faces the opposite way and handler q1 runs. Each number is when that cell is drawn:
EOF
run "dotnet fsi probe.fsx order 15 && dotnet fsi probe.fsx order 7"
note <<'EOF'
The order is not strictly far to near. At yaw 15, cell 8 (bottom right, near) is drawn before cell 9 (top of the next column, far). What holds is weaker and enough: every cell is drawn after every cell that is farther along **both** grid axes.

The projection says why. Depth is `ry = row * cos(yaw) + col * sin(yaw)`. For yaw 12 to 15, cos is positive and sin is negative, so a cell gets nearer as its row goes up and as its column goes down. `planQ3` runs columns from high to low and, within a column, rows from low to high, so any cell that is nearer in both directions comes later. The other three handlers do the same for their quarter turn, and `quadrant` switches at yaw 0, 4, 8 and 12, the angles where cos or sin is zero. Within a quarter turn the signs never change, so one grid order serves all four angles.

Cells that are not ordered this way, like 8 and 9, sit side by side across the view. The walk relies on those not overlapping on screen; the port has not tested that beyond matching the game's frames. One pass of the outer loop, eight cells, is what the viewer calls a **strip**.

## 4. Splitting a cell into two triangles

A cell's four corners are generally not in one plane, so the game draws each cell as two triangles. The plan records each one as data:
EOF
run "sed -n '261,293p' ../godot/logic/Fill.fs"
note <<'EOF'
Three things decide the two triangles:

- **Which diagonal.** Bit 7 of the flag plane picks the diagonal per cell: clear splits C00 to C11, set splits C10 to C01. The map stores the choice, so a ridge can run along the fold instead of across it.
- **Which colour.** One triangle takes the cell's type byte, the other its height byte. There is no lighting model. The byte selects one of 128 dither patterns (section 6), and the patterns are laid out so that height reads as shading. That is why a sloped grass cell shows a subtle two-tone split.
- **Which goes first.** The walk fixes the order of the two triangles, and for some diagonals it compares the corners' packed screen positions to decide. When a steep cell folds over itself on screen, the second triangle is the one you see.

The first cell the start pose draws:
EOF
run "dotnet fsi probe.fsx split"

note <<'EOF'
## 5. Filling a triangle: `$ef62` and the span walker

`$ef62` takes three corners and a colour byte and fills the triangle one scanline at a time. Its outline, from the port's doc comment:
EOF
run "sed -n '166,181p' ../godot/logic/Fill.fs"
note <<'EOF'
It finds the top vertex, works out how far each edge moves in x per scanline, then hands two edges to the span walker `$e420`, which fills between them row by row. When one edge reaches the middle vertex it bends toward the bottom one.

The per-scanline step is a 16.16 fixed-point slope from `$f000`. The 68000's `divu` divides 32 bits by 16 and returns a 16-bit quotient, so `(|dx| << 16) / dy` overflows as soon as `|dx| >= dy`. For those edges, flatter than 45 degrees, the routine divides in two stages and loses the low 8 bits of the fraction. (The source comment's "steep" means steep in x.)
EOF
run "sed -n '50,63p' ../godot/logic/Fill.fs"
run "dotnet fsi probe.fsx slope"
note <<'EOF'
7/3 comes out as 2.3320 instead of 2.3333, and 3/7, a steep edge, is exact. The error is about a thousandth of a pixel per row, so it only matters when a span end lands close to a pixel boundary, but then it decides which pixel is drawn. The port keeps it because matching the game pixel for pixel depends on those boundary cases.

The span walker keeps a left and a right x accumulator and adds each edge's slope once per row:
EOF
run "sed -n '119,164p' ../godot/logic/Fill.fs"
note <<'EOF'
Three behaviours to notice:

- **It clips per row.** Rows off the top or bottom are stepped but not drawn, and x stops at 255, the right edge of the isometric window. Nothing earlier in the pipeline clips.
- **It stops one row short.** The loop runs `row < totalRows`: each edge's run counter is decremented per row, and a count reaching zero ends the walk before that row is drawn. So the bottom vertex's own scanline is never filled; the next triangle down covers it. (The port used to draw that row too, which left a one-pixel line of wrong colour under every triangle; comparing against the game's frames found it.)
- **It can give up.** If the right accumulator ever lands left of the left one, the rest of the triangle is abandoned (`$e468`).
- **It can change the colour.** If the corners arrive with reversed winding (the middle vertex turns out to be on the left), `$ef62` swaps the edges and forces colour byte `$1c`, a dark pattern. SPEC.md records this as an override whose purpose is still open.

Counting what actually happens to the start frame's 128 triangles:
EOF
run "dotnet fsi probe.fsx rasters"
note <<'EOF'
No triangle gives up in this frame. Before the row fix there were 21 aborts, every one on the extra last row, where the two edges had already crossed: the abort was the port running past the end of the triangle, not a real early exit.

The `$1c` numbers are more interesting. Two in five triangles come out with reversed winding, and they draw 3298 pixels, but only 6 of those pixels survive to the finished frame. Every walk hands `$ef62` its corners in the same winding on the grid, so a triangle that comes out reversed on screen is facing away from the camera: it is the far side of a slope. The walk then draws nearer terrain over it. At this pose, the override paints back faces dark and the painter's algorithm hides them. That is one pose, so the general purpose stays open.

## 6. The colour is a dither pattern

The ST shows 16 colours at once, so a colour byte cannot be a colour. It is an index into a 16 KB table of patterns at `$2e000`: 128 slots of 128 bytes. For a pixel at (x, y), `$e3e6` and `$e420` read the slot for the colour byte, step 8 bytes per scanline (wrapping inside the slot), and take a 16-pixel, 4-bitplane pattern from there. Every span on a scanline uses the same 16-pixel pattern, tiled from the left edge of the screen:
EOF
run "sed -n '65,88p' ../godot/logic/Fill.fs"
note <<'EOF'
The pattern depends only on the colour byte and the screen row, never on where the triangle is, so neighbouring triangles with the same byte join without a seam. The first cell's two bytes, as palette indices:
EOF
run "dotnet fsi probe.fsx dither"
note <<'EOF'
Both are mostly palette 12 and 13, in different proportions, with a few other indices scattered in. Each row repeats every 16 pixels and changes from row to row. Stepping the byte through the table steps through blends, which is how height becomes shading without any lighting maths.

There is one more input: a phase. The pattern pointer lives at `$ffa2`, and every time the camera moves, rotates or zooms, `$f898` flips bit 7 of its low byte (`bchg #7,$ffa5` at `$f8e4`) before re-projecting. After the pointer is halved, that moves every read 64 bytes, 8 scanlines, through the slot, and the next camera change moves it back. So the whole landscape's texture jumps half a pattern each time you turn. The port applies it as `Fill.withPhase`, which rotates each slot by the phase:
EOF
run "sed -n '89,100p' ../godot/logic/Fill.fs"
note <<'EOF'
On captures rotated inside the emulator, modelling the phase takes the port's terrain match from 43-47% to 85-94%. The stepper and the Godot view flip it on every camera change, as the game does.

## 7. Sprites go inside the walk

Trees, buildings, men, animals and banners hang off the cells. Each cell has a bucket at `$47970` holding a linked list of object records. The walk handler calls `$115e0` for a cell right after drawing that cell's two triangles, and `$115e0` draws every record in the bucket before the walk moves on. `Scene.fs` builds the frame that way, as one list of steps:
EOF
run "sed -n '15,42p' ../godot/logic/Scene.fs"
run "dotnet fsi probe.fsx steps"
note <<'EOF'
(`byte6` is the record's category byte; 4 is a building or tree. SPEC.md §6 lists the categories.)

The obvious simplification, drawing all the terrain first and then all the sprites on top, gives a different picture, and the port did it that way before this document was written. The test is to render a captured frame both ways and compare each with the game's own screen at the pixels where the two orders disagree. On six captures, three of them rotated to other camera angles inside the emulator, the game sides with the inline order almost every time:
EOF
run "grep -A 7 '| capture | terrain only' ../SPEC.md"
note <<'EOF'
The inputs are `.ram` captures of the running game, which stay out of the repository, so this table is quoted from SPEC.md rather than re-run here. `pm78_settle` scores lower overall because its two compose buffers are known to disagree on the entity layer; the comparison at the differing pixels still comes out the same way. The records only depend on the camera cell, so the same sprites are drawn at every yaw; only men's and animals' facing frames follow the camera. The castle keep in the hilltop fort is its own category (`byte6` 2, `$117d8`): a building frame from the tree sheet, anchored on the cell's centre.

Inline drawing matters because nearer terrain has to be able to cover a sprite. A tree on the far side of a hill is drawn when its cell comes up, and then the hill's nearer cells are drawn over it. How much sprite work the start frame throws away:
EOF
run "dotnet fsi probe.fsx occlusion"
note <<'EOF'
More than half the sprite pixels are painted over, and whole trees are drawn only to vanish. The game pays that cost rather than work out what is visible. Sprites drawn after all the terrain (top) put the trees behind the hilltop over the hill; drawn inline (bottom), the hill hides them, as it does in the game:

![Sprites drawn after all the terrain](../assets/reference/godot_screenshot_entities_91st.png)

![Sprites drawn inline, cell by cell, as the game does](../assets/reference/godot_screenshot_inline_118th.png)

## 8. Watching it happen: the frame stepper

Because the frame is now a list of steps, it can be replayed. `../stepper` is a small Mibo (raylib) app that draws the frame one triangle or sprite at a time, with pause, single steps by triangle, cell or strip, rewind, and overlays for the corner grid, the walk order, and the current triangle or sprite frame. Run it with `dotnet run --project ../stepper`; B toggles the game's backdrop behind the island.

It draws each step once into a buffer that logs its writes, so it knows exactly which pixels each step sets and in what order:
EOF
run "sed -n '34,54p' ../stepper/Replay.fs"
note <<'EOF'
A position in the frame is a step number plus a pixel count within that step, and any position can be rebuilt by replaying the log up to it:
EOF
run "awk 'NR>=58 && NR<=75; NR==76 {print \"...\"}; NR>=113 && NR<=122' ../stepper/Replay.fs"
note <<'EOF'
Playback runs finer than the ST ever drew: `$e420` writes 16-pixel words per bitplane and the sprite blitter writes whole byte rows, so pixel-by-pixel playback is a presentation choice. The order of spans, rows, triangles and sprites is the game's.

The replay is checked against the renderer at every yaw: finishing the replay must give exactly the frame `Scene.render` draws, and stepping forward then back by any chunk must land where it started.
EOF
run "dotnet run --project ../stepper --no-build -- --selfcheck | tr -d '\r'"

note <<'EOF'
## 9. Redoing it in Godot

There are two ways to put this in Godot, and they answer different questions.

**Route A: run the game's renderer and show its output.** This is what `../godot` does today. The F# above draws a 320 x 200 palette-index buffer on the CPU exactly as the game does, and a thin C# node copies it into an `ImageTexture` whenever the camera moves:
EOF
run "awk 'NR>=156 && NR<=181; NR==182 {print \"        ...\"}; NR==192; NR==193 {print \"        ...\"}; NR==233' ../godot/game/TerrainView.cs"
note <<'EOF'
Everything the port reproduces stays as the game draws it: the dither and its phase, the clipping, the `$1c` override, the row the span walker stops short of. The island is drawn over the game's own `$78000` master screen (HUD, lord portrait, temple backdrop, minimap), exported once as `assets/backdrop.bin`, since the game never changes it. Against the game's frames that is 94-98% of pixels, and nearly all of the rest are sprites.

![The Godot view: the port's island over the game's own backdrop](../assets/reference/godot_screenshot_backdrop_118th.png) The cost is that Godot is only a window. You cannot zoom smoothly, light it, or run it above 320 x 200 without changing what it is.

**Route B: rebuild it with the engine's own tools.** Each stage maps onto something Godot already does, and several of the game's tricks become unnecessary:

| the game | why it does it | Godot equivalent |
|---|---|---|
| `$fecc` projects 81 corners with an integer perspective divide | no GPU | a `Camera3D` with a perspective projection, and the grid (or the whole 64 x 128 map) built once as an `ArrayMesh` with the control plane as vertex heights |
| per-cell diagonal from flag bit 7 | ridges follow the terrain | the same choice, made when writing the mesh indices: emit each cell's two triangles along the flagged diagonal |
| one colour byte per triangle | no lighting model | flat shading: give each triangle its own three vertices carrying its colour byte, or write the byte into a small per-cell texture |
| 128-slot dither table indexed by colour byte and screen row | 16 colours on screen | a fragment shader that samples `dither.bin` as a texture using the colour byte and `FRAGCOORD`, which keeps the screen-locked look; or drop it and use the palette colours directly |
| four walk handlers and sprites drawn inline | painter's algorithm instead of a depth buffer | the depth buffer; draw order stops mattering |
| `$1c` on reversed winding, then covered by nearer terrain | back faces have to be drawn and hidden | back-face culling, which a spatial shader does by default |
| sprites anchored on their cell's corners | 2D blitter | `Sprite3D` billboards at the same sub-cell point, with `alpha_cut` set to discard and nearest filtering, so they write depth and a hill hides a tree for free |

Route B is the better engine port and the worse history lesson: the walk order, the inline sprites and the `$1c` override all disappear into the depth buffer and back-face culling. Seeing the two side by side shows that those three pieces of the game exist to get the effect of a depth buffer on a machine without one.

For the look of Route A with the structure of Route B, keep the mesh and camera from Route B and move the fill into the shader: a flat colour byte per triangle, the dither looked up from `FRAGCOORD`, and the palette applied at the end. `../../graphics.md` ("What a modern port would do differently") covers the performance side of the same question for a port that stays in software.

## Where to go from here

- `../SPEC.md` is the full porting contract, with every constant and address.
- `../../graphics.md` has the 68000-level detail behind each section here.
- `dotnet run --project ../stepper` shows every step above live. Press N to number the cells in walk order, G for the corner grid, and Right to step one triangle at a time.
EOF

sb verify "$D" >/dev/null && echo "verify: clean"
