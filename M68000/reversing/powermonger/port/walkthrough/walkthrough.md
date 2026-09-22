# How PowerMonger draws its world

*2026-09-22T22:39:21Z by Showboat 0.6.1*
<!-- showboat-id: cfa48c7d-237a-4b53-b338-b5955598bb15 -->

This walks through one frame of PowerMonger's isometric view (Atari ST, 1990), following the data from the heightmap in RAM to the pixels on screen. The code is the F# port in `../godot/logic/`, which reproduces the 68000 routines closely enough to match the game's own frame buffer at 94-98% of pixels, and the terrain alone at over 99% away from sprites, at all seven zoom levels. Addresses like `$fccc` are routines in the original executable, so every section can be traced back to the disassembly.

The whole renderer, in the order it runs. `$f898` is the driver: once per game tick it re-projects if the camera moved, then runs the walk for the current angle.

| stage | 68000 routine | F# |
|---|---|---|
| read the heightmap window | `$3f86c`, `$438ee` planes | `Terrain.Map` |
| project the grid of corners (9 x 9 at the default zoom) | `$fecc` | `Projection.projectGrid` |
| pick the walk for this camera angle | `$f97e` | `Fill.quadrant`, `Fill.plan` |
| visit the cells (64 at the default zoom), two triangles each | `$f98e` / `$fa9a` / `$fbb4` / `$fccc` | `Fill.planQ0`..`planQ3` |
| fill each triangle with a dither pattern | `$ef62`, `$e420`, `$e3e6` | `Fill.ef62Raster`, `ddaWalk`, `ditherIndex` |
| draw each cell's sprites straight after its triangles | `$115e0` | `Scene.steps`, `Sprites.blitEntity` |

There is no depth buffer and no sort. The order of the walk does all the hidden-surface work, and most of this document is about why that is enough.

Everything below runs against the real code. Build it first with `dotnet build ../godot/logic/PmLogic.fsproj` and `dotnet build ../stepper/PmStepper.fsproj`. The live checks call `probe.fsx` in this folder, which prints facts computed by the port; `uvx showboat verify walkthrough.md` re-runs them all.

## 1. The world is a heightmap

The map is 64 x 128 cells. Each cell has four bytes, stored as four separate planes: a **type** byte (what the ground is), a **height** byte, a **flag** byte, and a **control** byte, which is the height the projector uses to lift the corners.

```bash
sed -n '19,21p;28,36p' ../godot/logic/Terrain.fs
```

```output
    type Map =
        { Type: byte[]        // terrain class / colour of the "type" triangle
          HeightPlane: byte[] // $438ee height plane
          Flag: byte[]
          Control: byte[] }   // $3f86c — the height the projector reads

        member m.Index(x, y) = y * Width + x
        member m.ControlAt(x, y) = int m.Control.[m.Index(x, y)]
        member m.TypeAt(x, y) = int m.Type.[m.Index(x, y)]
        member m.HeightAt(x, y) = int m.HeightPlane.[m.Index(x, y)]
        member m.IsWater(x, y) = m.HeightPlane.[m.Index(x, y)] < WaterLevel
        member m.DiagonalSelector(x, y) = m.Flag.[m.Index(x, y)] &&& DiagonalSelectorBit <> 0uy
```

At the default zoom the camera looks at an 8 x 8 block of cells, which needs a 9 x 9 grid of corners (section 2 covers the other zooms). These are the control-plane heights under that grid at the start of mission 1, camera cell (36,47). The hill in the middle is the one you see on screen.

```bash
dotnet fsi probe.fsx heights
```

```output
control-plane heights, corners (36..44, 47..55):
  0c 0a 0e 15 18 16 14 10 09
  14 14 1c 22 21 1e 1b 14 0a
  16 1c 28 30 2e 27 20 15 0a
  14 1d 2b 37 38 2e 22 13 07
  11 18 25 33 3a 3a 23 14 07
  0e 11 1b 27 3a 3a 20 15 07
  0f 0d 14 1d 23 1f 18 11 07
  10 0c 10 18 1c 17 11 0d 06
  11 0b 0b 10 12 0d 0a 09 04
```

## 2. Projecting the corners

`$fecc` turns each corner of the 9 x 9 grid into a screen position. It rotates the grid by the camera yaw, lifts each corner by its height above the lowest corner in view, then divides by the distance from an eye 320 units back. That is an ordinary perspective projection in 68000 integer maths.

The yaw is a byte, 256 units per turn, stepped 16 at a time: 16 angles of 22.5 degrees. The start pose is yaw 15, byte `$f0`. `Zoom` (21) is the size of a cell in world units, and heights are scaled by `Zoom / 16`. `Horizon` (130) is subtracted from each lifted height before the divide and added back after, so it sets where the horizon sits on screen.

```bash
sed -n '/theta = yaw \* 1.40625/,$p' ../godot/logic/Projection.fs
```

```output
    /// theta = yaw * 1.40625 deg  (the $13f8a table is a plain sine table).
    let yawAngle (p: Params) = deg2rad (float (p.YawSteps * 16) * 1.40625)

    type Corner = { X: float; Y: float }

    /// Project one grid vertex. col,row are relative to the camera cell,
    /// each in -Half .. +Half. h = control-plane height at that cell.
    /// hbias = min control height over the visible window (recomputed per frame).
    let projectVertex (p: Params) (theta: float) (hbias: int) (col: int) (row: int) (h: int) : Corner =
        let sinT = sin theta
        let cosT = cos theta
        let z = ((h - hbias) * int p.Zoom) >>> 4 |> float
        let c = float col * p.Zoom
        let r = float row * p.Zoom
        // rotate by -theta  ($ff36..$ff4e):  rx = (c*Q - r*P)>>15, P=32768 sinT, Q=32768 cosT
        let rx = c * cosT - r * sinT
        let ry = r * cosT + c * sinT
        let d = p.Eye - ry
        let d = if d <= 1.0 then 1.0 else d
        let sx = rx * p.Eye / d
        let sy = (z - p.Horizon) * p.Eye / d + p.Horizon
        { X = sx + 128.0; Y = 124.0 - sy }

    /// Project the whole visible grid. Returns corners indexed [gr, gc],
    /// gr/gc in 0 .. 2*Half. camX,camY = camera cell (already minus $57ffc).
    let projectGrid (p: Params) (m: Terrain.Map) (camX: int) (camY: int) : Corner[,] =
        let n = 2 * p.Half + 1
        let theta = yawAngle p
        // dynamic height bias
        let mutable hbias = 255
        for gr in 0 .. n - 1 do
            for gc in 0 .. n - 1 do
                let hh = m.ControlAt(camX + gc, camY + gr)
                if hh < hbias then hbias <- hh
        Array2D.init n n (fun gr gc ->
            let h = m.ControlAt(camX + gc, camY + gr)
            projectVertex p theta hbias (gc - p.Half) (gr - p.Half) h)
```

Two details matter later. `ry`, the rotated distance along the view direction, is what the divide uses: a larger `ry` means a smaller `d`, so a nearer corner. And nothing is clipped here. All 81 corners are projected whether they are on screen or not; clipping happens one scanline at a time inside the triangle filler.

The result for the start pose, in the raw coordinates the game draws in (it adds 64 px for the HUD strip when it writes to the screen):

```bash
dotnet fsi probe.fsx corners
```

```output
projected corners (screen x, y), rows = grid rows 0..8:
  ( 32, 99) ( 51, 99) ( 68, 92) ( 86, 83) (102, 78) (118, 78) (133, 78) (148, 81) (162, 86)
  ( 34, 95) ( 54, 93) ( 72, 81) ( 90, 73) (108, 72) (124, 74) (140, 75) (155, 81) (170, 90)
  ( 36, 99) ( 57, 89) ( 77, 71) ( 96, 61) (114, 61) (131, 68) (147, 74) (163, 84) (178, 95)
  ( 39,108) ( 61, 93) ( 82, 72) (102, 56) (120, 52) (138, 63) (156, 76) (172, 92) (188,103)
  ( 42,120) ( 65,106) ( 87, 86) (108, 65) (128, 54) (147, 53) (165, 80) (182, 95) (199,109)
  ( 45,133) ( 70,125) ( 93,106) (116, 87) (137, 58) (156, 56) (175, 89) (193,100) (210,116)
  ( 49,143) ( 76,142) (101,126) (124,109) (146, 96) (167, 99) (187,106) (206,112) (224,124)
  ( 53,154) ( 82,156) (109,144) (134,125) (157,115) (180,120) (200,124) (220,127) (239,133)
  ( 59,166) ( 90,171) (119,165) (145,151) (170,142) (194,146) (216,146) (236,143) (256,146)
```

The far edge (row 0) sits higher on screen than the near edge (row 8). Between them the hill lifts rows 1 to 4 above row 0 in places, so the grid folds back on itself on screen. Those back slopes come up again in section 5.

**Zoom.** The game has seven zoom levels, and the zoom index in `$57ffc` does two jobs. It is `Half`, so the window is `2 * zoom` cells square, from 2 x 2 at zoom 1 to 14 x 14 at zoom 7. And it picks `Zoom`, the cell size, from a table at `$13f82`. The zoom buttons call `$13f60`, which sets both and then `$fe04`, which works out every loop count and pointer step the walks use. `$4bb3a/$4bb3c` is the cell in the middle of the view, and the window starts `zoom` cells before it, so zooming keeps the centre where it is.

```bash
sed -n '/13f82\[zoom index\]/,/member p.WithZoom/p' ../godot/logic/Projection.fs
```

```output
    /// $13f82[zoom index]: the cell size in world units for zoom 1..7
    /// ($13f60 copies it to $ff9c). Index 0 is unused.
    let zoomScale = [| 0; 84; 42; 28; 21; 17; 14; 12 |]

    /// Projection parameters, from assets/tables.json -> projection.
    type Params =
        { Eye: float          // $ff98, 320
          Horizon: float      // $ff96, 130
          Zoom: float         // $ff9c, cell size in world units: zoomScale.[Half]
          YawSteps: int       // $ff9a >> 4, 0..15
          Half: int }         // $57ffc = $fdec, the zoom index 1..7: the window is 2*Half cells square

        static member Mission1 =
            { Eye = 320.0; Horizon = 130.0; Zoom = 21.0; YawSteps = 15; Half = 4 }

        /// C#-friendly copy-with (F#'s `{ p with ... }` isn't callable from C#).
        member p.WithYaw(yawSteps: int) = { p with YawSteps = yawSteps }

        /// $13f60: zoom index 1..7 sets both the half-extent and the cell size.
        member p.WithZoom(zoom: int) = { p with Half = zoom; Zoom = float zoomScale.[zoom] }
```

Nothing else in the projection changes with zoom: the eye distance, the horizon and the screen centre are constants.

## 3. The walk: far to near, one cell at a time

The game never sorts anything. It visits the 64 cells in a fixed order and draws each cell completely before moving on. Anything drawn later lands on top. This is the painter's algorithm: paint the background first and let nearer things cover it. It only works if nothing is drawn before something that could be in front of it.

Which order is safe depends on where the camera faces, so the game has four copies of the walk and picks one from the yaw (`$f97e`):

```bash
sed -n '/port of $f97e/,/handler corners map/p' ../godot/logic/Fill.fs
```

```output
    /// port of $f97e/$f982's dispatch: q = ((yaw+8)>>5)&6, handler = q>>1.
    /// yaw here is yawSteps*16 (Projection.Params.YawSteps, 0..15).
    let quadrant (yawSteps: int) = (((yawSteps * 16 + 8) >>> 5) &&& 6) >>> 1

    /// The whole frame's terrain as a draw plan: the n x n cells in the order
    /// the quadrant handler for this yaw visits them.
    let plan (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int) (yawSteps: int) =
        let handler = [| planQ0; planQ1; planQ2; planQ3 |].[quadrant yawSteps]
        handler corners map camX camY
```

Each handler is two nested loops of `2 * zoom` passes, eight at the default zoom; the loop count and every starting point come from the `$fe04` geometry, so the same handler serves all seven zooms. The port splits each one into its two decisions: the order the loops reach the cells, and how each cell is cut into triangles (section 4). In the excerpt, C00 is the cell's top-left corner `corners[row, col]`, C10 the next column, C01 the next row and C11 the diagonal one; `packed` is `(x << 16) | y`, the handlers' way of comparing two screen points. Here is the handler for the start pose, `$fccc`:

```bash
sed -n '/pm_grid_walk_q3 ($fccc)/,/(i, n - 1 - strip) \]/p' ../godot/logic/Fill.fs
```

```output
    /// pm_grid_walk_q3 ($fccc), yaw 0xf0 (quadrant 3). `corners` is the
    /// projected grid from Projection.projectGrid — gr,gc both 0..2*Half,
    /// which is exactly $3f364's own (row,col) layout, so it plugs in
    /// directly (no re-indexing needed).
    ///
    ///   strip = cell column, EAST -> WEST (far -> near)
    ///   i     = cell row,    NORTH -> SOUTH (far -> near)
    ///   (row, col) = (i, n-1 - strip)   ; start offset col n-1 ($fe02)
    ///   flag CLEAR: split C00-C11, unconditional:
    ///     ef62(C10,C11,C00,type) ; ef62(C01,C00,C11,height)
    ///   flag SET: split C10-C01, sub-order by packed(C01) <= packed(C10)
    let planQ3 (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int) : Cell list =
        let visit = visit corners map camX camY (fun q ->
            if not q.Diagonal then
                tri q.C10 q.C11 q.C00 q.TypeByte, tri q.C01 q.C00 q.C11 q.HeightByte
            elif packed q.C01 <= packed q.C10 then
                tri q.C00 q.C10 q.C01 q.HeightByte, tri q.C11 q.C01 q.C10 q.TypeByte
            else
                tri q.C11 q.C01 q.C10 q.TypeByte, tri q.C00 q.C10 q.C01 q.HeightByte)
        let n = cellsPerSide corners
        [ for strip in 0 .. n - 1 do
            for i in 0 .. n - 1 -> visit (strip, i) (i, n - 1 - strip) ]
```

Laid out on the grid, the order `planQ3` produces at yaw 15, then the order at yaw 7, where the camera faces the opposite way and handler q1 runs. Each number is when that cell is drawn:

```bash
dotnet fsi probe.fsx order 15 && dotnet fsi probe.fsx order 7
```

```output
yaw 15 -> handler q3; visit order laid out by grid (row down, col across):
  57 49 41 33 25 17  9  1
  58 50 42 34 26 18 10  2
  59 51 43 35 27 19 11  3
  60 52 44 36 28 20 12  4
  61 53 45 37 29 21 13  5
  62 54 46 38 30 22 14  6
  63 55 47 39 31 23 15  7
  64 56 48 40 32 24 16  8
yaw 7 -> handler q1; visit order laid out by grid (row down, col across):
   8 16 24 32 40 48 56 64
   7 15 23 31 39 47 55 63
   6 14 22 30 38 46 54 62
   5 13 21 29 37 45 53 61
   4 12 20 28 36 44 52 60
   3 11 19 27 35 43 51 59
   2 10 18 26 34 42 50 58
   1  9 17 25 33 41 49 57
```

The order is not strictly far to near. At yaw 15, cell 8 (bottom right, near) is drawn before cell 9 (top of the next column, far). What holds is weaker and enough: every cell is drawn after every cell that is farther along **both** grid axes.

The projection says why. Depth is `ry = row * cos(yaw) + col * sin(yaw)`. For yaw 12 to 15, cos is positive and sin is negative, so a cell gets nearer as its row goes up and as its column goes down. `planQ3` runs columns from high to low and, within a column, rows from low to high, so any cell that is nearer in both directions comes later. The other three handlers do the same for their quarter turn, and `quadrant` switches at yaw 0, 4, 8 and 12, the angles where cos or sin is zero. Within a quarter turn the signs never change, so one grid order serves all four angles.

Cells that are not ordered this way, like 8 and 9, sit side by side across the view. The walk relies on those not overlapping on screen; the port has not tested that beyond matching the game's frames. One pass of the outer loop, `2 * zoom` cells, is what the viewer calls a **strip**.

## 4. Splitting a cell into two triangles

A cell's four corners are generally not in one plane, so the game draws each cell as two triangles. The plan records each one as data:

```bash
sed -n '/One triangle as the walk hands it/,/Second: Tri }/p' ../godot/logic/Fill.fs
```

```output
    /// One triangle as the walk hands it to $ef62: three projected corners
    /// (in the order passed, which $ef62's cyclic sort depends on) and the raw
    /// terrain byte that picks its colour. The water shimmer (+tick) is
    /// applied at draw time by ef62Raster, not here.
    type Tri =
        { A: Projection.Corner
          B: Projection.Corner
          C: Projection.Corner
          Colour: int }

    /// One cell's four projected corners and the three bytes its split reads.
    ///   C00 = corners.[row,   col]    C10 = corners.[row,   col+1]
    ///   C01 = corners.[row+1, col]    C11 = corners.[row+1, col+1]
    type Quad =
        { C00: Projection.Corner; C10: Projection.Corner
          C01: Projection.Corner; C11: Projection.Corner
          TypeByte: int          // type plane: colours one triangle
          HeightByte: int        // height plane: colours the other
          Diagonal: bool }       // flag-plane bit 7 (Terrain.DiagonalSelector)

    /// One cell visit, in walk order.
    type Cell =
        { X: int; Y: int         // world cell
          Row: int; Col: int     // its top-left corner in the (n+1) x (n+1) projected grid
          Strip: int             // outer-loop pass 0..n-1: the far -> near strip it belongs to
          InStrip: int           // inner-loop index 0..n-1 within its strip
          Order: int             // position in the walk, 0..n*n-1 = strip * n + i
          Quad: Quad
          First: Tri             // drawn first ...
          Second: Tri }          // ... then this one over it
```

Three things decide the two triangles:

- **Which diagonal.** Bit 7 of the flag plane picks the diagonal per cell: clear splits C00 to C11, set splits C10 to C01. The map stores the choice, so a ridge can run along the fold instead of across it.
- **Which colour.** One triangle takes the cell's type byte, the other its height byte. There is no lighting model. The byte selects one of 128 dither patterns (section 6), and the patterns are laid out so that height reads as shading. That is why a sloped grass cell shows a subtle two-tone split.
- **Which goes first.** The walk fixes the order of the two triangles, and for some diagonals it compares the corners' packed screen positions to decide. When a steep cell folds over itself on screen, the second triangle is the one you see.

The first cell the start pose draws:

```bash
dotnet fsi probe.fsx split
```

```output
first cell visited: world (43,47), grid row 0 col 7, strip 0
  C00 (148, 81)  C10 (162, 86)  C01 (155, 81)  C11 (170, 90)
  type byte $26  height byte $25  flag bit 7 clear: split C00-C11
  first  tri (162, 86) (170, 90) (148, 81) colour $26
  second tri (155, 81) (148, 81) (170, 90) colour $25
```

## 5. Filling a triangle: `$ef62` and the span walker

`$ef62` takes three corners and a colour byte and fills the triangle one scanline at a time. Its outline, from the port's doc comment:

```bash
sed -n '/pm_tri_raster ($ef62) → the $e420/,/raw plane byte, same as/p' ../godot/logic/Fill.fs
```

```output
    /// pm_tri_raster ($ef62) → the $e420 DDA span walker. Ports:
    ///   * the cyclic-rotate Y sort ($efbe..$efd4)
    ///   * general vs flat-top split ($efe0..$f13c), incl. the $f134 reorder
    ///   * per-edge 16.16 slope via fixedSlope ($f000)
    ///   * "force colourByte 0x1c" on reversed winding ($f072/$f154): general
    ///     -> mid vertex already LEFT (slope(top->bot) > slope(top->mid)); flat-
    ///     top -> right apex X < left. Back-facing; mostly overdrawn.
    ///   * the mid-vertex slope switch: the edge on the mid vertex's side
    ///     reloads to slope(mid->bot) at scanline (mid.y - top.y) — run-
    ///     counter expiry ($e42a/$e43e), consuming record[20]/[22]. Both
    ///     non-apex edges walk from the apex; whichever's run counter expires
    ///     first is the one that bends, so triangle height = max(dy1, dy2),
    ///     NOT necessarily the cyclic-3rd vertex's dy (the cyclic sort does
    ///     not guarantee it is the true bottom).
    ///   * water shimmer: colour += tick if colour < 0x0c (walk_q3 passes the
    ///     raw plane byte, same as $fccc).
```

It finds the top vertex, works out how far each edge moves in x per scanline, then hands two edges to the span walker `$e420`, which fills between them row by row. When one edge reaches the middle vertex it bends toward the bottom one.

The per-scanline step is a 16.16 fixed-point slope from `$f000`. The 68000's `divu` divides 32 bits by 16 and returns a 16-bit quotient, so `(|dx| << 16) / dy` overflows as soon as `|dx| >= dy`. For those edges, flatter than 45 degrees, the routine divides in two stages and loses the low 8 bits of the fraction. (The source comment's "steep" means steep in x.)

```bash
sed -n '/$f000 — signed 16.16/,/if dx < 0 then -v else v/p' ../godot/logic/Fill.fs
```

```output
    /// $f000 — signed 16.16 fixed-point edge-slope magnitude, sign from dx.
    /// dy is the (positive) run in scanlines. Steep (dy <= |dx|) truncates
    /// the divide *before* the final <<8 ($f01a's two-stage divide) — this is
    /// NOT the same value as a single (|dx|<<16)/dy; the rounding difference
    /// matters for span endpoints. divu overflow clamps to exactly 0x10000.
    let fixedSlope (dx: int) (dy: int) : int =
        let adx = abs dx
        let v =
            if dy <= adx then
                let q = (adx <<< 8) / dy
                if q > 0xFFFF then 0x10000 else (q &&& 0xFFFF) <<< 8
            else
                ((adx <<< 16) / dy) &&& 0xFFFF
        if dx < 0 then -v else v
```

```bash
dotnet fsi probe.fsx slope
```

```output
   dx  dy   $f000 16.16     naive (dx<<16)/dy
    7   3   00025500 (   2.3320)   00025555 (   2.3333)
   10   3   00035500 (   3.3320)   00035555 (   3.3333)
    3   7   00006db6 (   0.4286)   00006db6 (   0.4286)
   -5   2   fffd8000 (  -2.5000)   fffd8000 (  -2.5000)
  200   1   00c80000 ( 200.0000)   00c80000 ( 200.0000)
```

7/3 comes out as 2.3320 instead of 2.3333, and 3/7, a steep edge, is exact. The error is about a thousandth of a pixel per row, so it only matters when a span end lands close to a pixel boundary, but then it decides which pixel is drawn. The port keeps it because matching the game pixel for pixel depends on those boundary cases.

The span walker keeps a left and a right x accumulator and adds each edge's slope once per row:

```bash
sed -n '/$e420 — two 16.16 X accumulators/,/^        abortRow/p' ../godot/logic/Fill.fs
```

```output
    /// $e420 — two 16.16 X accumulators (left/right), each stepped one slope
    /// per scanline; row 0 uses the start X with no step ($e41a `bra $e456`).
    /// Draws rows 0 .. totalRows-1: each edge's run counter is decremented per
    /// row ($e42a/$e43e) and a zero run ends the walk before the row is drawn
    /// (the stream ends with a zero run: $f12c / $f13e clear record[20]).
    /// A switching edge reloads its slope at its own `switch` row (the
    /// shorter edge bending toward the far vertex). Aborts the WHOLE triangle
    /// (remaining rows too) the first time ixR < ixL ($e468). The
    /// $ec62/$eca2 partial-word edge masks reduce exactly to "draw pixel x
    /// iff ixL <= x <= ixR" for a per-pixel index buffer — no planar masking
    /// needed. $ef62's own clip is screenX <= 255 (the iso window's right
    /// edge, not the 320px screen). Returns the row it aborted at, if any.
    let private ddaWalk (buf: Buffer) (dith: byte[]) (colour: int) (topY: int) (totalRows: int)
                         (xL: int) (slopeL: int) (switchL: int option) (slopeL2: int)
                         (xR: int) (slopeR: int) (switchR: int option) (slopeR2: int) =
        let mutable pL = int64 xL <<< 16
        let mutable pR = int64 xR <<< 16
        let mutable sL = slopeL
        let mutable sR = slopeR
        let mutable aborted = false
        let mutable abortRow = None
        let mutable row = 0
        while not aborted && row < totalRows do
            if row > 0 then
                pL <- pL + int64 sL
                pR <- pR + int64 sR
            match switchL with
            | Some sw when sw = row -> sL <- slopeL2
            | _ -> ()
            match switchR with
            | Some sw when sw = row -> sR <- slopeR2
            | _ -> ()
            let y = topY + row
            if y >= 0 && y < ScreenHeight then
                let ixL = int (pL >>> 16)
                let ixR = int (pR >>> 16)
                if ixR < ixL then
                    aborted <- true
                    abortRow <- Some row
                elif ixL <= 0xFF then
                    let xs = max 0 ixL
                    let xe = min (ScreenWidth - 1) (min ixR 0xFF)
                    for x in xs .. xe do
                        buf.Set(x, y, ditherIndex dith colour y x)
            row <- row + 1
        abortRow
```

Three behaviours to notice:

- **It clips per row.** Rows off the top or bottom are stepped but not drawn, and x stops at 255, the right edge of the isometric window. Nothing earlier in the pipeline clips.
- **It stops one row short.** The loop runs `row < totalRows`: each edge's run counter is decremented per row, and a count reaching zero ends the walk before that row is drawn. So the bottom vertex's own scanline is never filled; the next triangle down covers it. (The port used to draw that row too, which left a one-pixel line of wrong colour under every triangle; comparing against the game's frames found it.)
- **It can give up.** If the right accumulator ever lands left of the left one, the rest of the triangle is abandoned (`$e468`).
- **It can change the colour.** If the corners arrive with reversed winding (the middle vertex turns out to be on the left), `$ef62` swaps the edges and forces colour byte `$1c`, a dark pattern. SPEC.md records this as an override whose purpose is still open.

Counting what actually happens to the start frame's 128 triangles:

```bash
dotnet fsi probe.fsx rasters
```

```output
reversed winding ($1c forced) on 52 triangles, first at steps [1; 3; 7; 8]
span walk aborted on 0 triangles; rows lost -> how many: []
skipped by $ef62: 0 []; drawn but fully clipped: 0
$1c triangles drew 3298 px; 6 px of them are visible in the finished frame (of 13725 terrain px)
```

No triangle gives up in this frame. Before the row fix there were 21 aborts, every one on the extra last row, where the two edges had already crossed: the abort was the port running past the end of the triangle, not a real early exit.

The `$1c` numbers are more interesting. Two in five triangles come out with reversed winding, and they draw 3298 pixels, but only 6 of those pixels survive to the finished frame. Every walk hands `$ef62` its corners in the same winding on the grid, so a triangle that comes out reversed on screen is facing away from the camera: it is the far side of a slope. The walk then draws nearer terrain over it. At this pose, the override paints back faces dark and the painter's algorithm hides them. That is one pose, so the general purpose stays open.

## 6. The colour is a dither pattern

The ST shows 16 colours at once, so a colour byte cannot be a colour. It is an index into a 16 KB table of patterns at `$2e000`: 128 slots of 128 bytes. For a pixel at (x, y), `$e3e6` and `$e420` read the slot for the colour byte, step 8 bytes per scanline (wrapping inside the slot), and take a 16-pixel, 4-bitplane pattern from there. Every span on a scanline uses the same 16-pixel pattern, tiled from the left edge of the screen:

```bash
sed -n '/$e3e6 setup + the $e420/,/byte (p0 ||| (p1/p' ../godot/logic/Fill.fs
```

```output
    /// $e3e6 setup + the $e420/$e44a roll. Live single-stepped:
    /// A5 wraps MODULO 128 inside the colour's 128-byte slot (the $e44a
    /// roll's `addq.b #8` on `2*A5` byte-overflows at `A5 & 0x7f == 124`), so
    /// the phase depends only on colourByte and the absolute scanline y — the
    /// topY term drops out under the mod. The whole span on one scanline is
    /// ONE 16-px pattern (planes 0/1 = the big-endian long at A5, planes 2/3
    /// = the long at A5+4), tiled screen-X-aligned.
    let ditherIndex (dith: byte[]) (colourByte: int) (y: int) (x: int) : byte =
        let colourByte = max 0 colourByte
        let mutable a5 = colourByte * 128 + ((8 * y) &&& 0x7F)
        if a5 + 8 > dith.Length then
            a5 <- (dith.Length - 8) &&& ~~~1
        let u32be (i: int) =
            (uint32 dith.[i] <<< 24) ||| (uint32 dith.[i + 1] <<< 16)
            ||| (uint32 dith.[i + 2] <<< 8) ||| uint32 dith.[i + 3]
        let l0 = u32be a5
        let l1 = u32be (a5 + 4)
        let b = 15 - (x &&& 15)
        let p0 = (l0 >>> (16 + b)) &&& 1u
        let p1 = (l0 >>> b) &&& 1u
        let p2 = (l1 >>> (16 + b)) &&& 1u
        let p3 = (l1 >>> b) &&& 1u
        byte (p0 ||| (p1 <<< 1) ||| (p2 <<< 2) ||| (p3 <<< 3))
```

The pattern depends only on the colour byte and the screen row, never on where the triangle is, so neighbouring triangles with the same byte join without a seam. The first cell's two bytes, as palette indices:

```bash
dotnet fsi probe.fsx dither
```

```output
colour byte $26, x 0..31, scanlines 0..5 (palette indices, hex):
  y=0  777dddddddd776cc777dddddddd776cc
  y=1  6c6ccc67c7cdd7dd6c6ccc67c7cdd7dd
  y=2  7dc67d77d66ccccc7dc67d77d66ccccc
  y=3  dcc767dd777ddd66dcc767dd777ddd66
  y=4  d6d7c6cc6cd77c77d6d7c6cc6cd77c77
  y=5  c77ddcddcdc666ccc77ddcddcdc666cc
colour byte $25, x 0..31, scanlines 0..5 (palette indices, hex):
  y=0  677ddcddcdc666dd677ddcddcdc666dd
  y=1  6d6ccd77d7ddd7dd6d6ccd77d7ddd7dd
  y=2  7cc66d66d66dddcc7cc66d66d66dddcc
  y=3  ddd776dc676ddc66ddd776dc676ddc66
  y=4  c6c6d6dd6dd77d77c6c6d6dd6dd77d77
  y=5  d66cdcddccc666ddd66cdcddccc666dd
```

In this season both mix the greens 12 and 13 with the browns 6 and 7, in different proportions. Each row repeats every 16 pixels and changes from row to row. Stepping the byte through the table steps through blends, which is how height becomes shading without any lighting maths.

There is one more input: a phase. The pattern pointer lives at `$ffa2`, and every time the camera moves, rotates or zooms, `$f898` flips bit 7 of its low byte (`bchg #7,$ffa5` at `$f8e4`) before re-projecting. After the pointer is halved, that moves every read 64 bytes, 8 scanlines, through the slot, and the next camera change moves it back. So the whole landscape's texture jumps half a pattern each time you turn. The port applies it as `Fill.withPhase`, which rotates each slot by the phase:

```bash
sed -n '/The dither phase. $e3e6 reads/,/else Array.init dith.Length/p' ../godot/logic/Fill.fs
```

```output
    /// The dither phase. $e3e6 reads patterns through the pointer [$ffa2] >> 1.
    /// $f898 sets [$ffa2] = 2 * [$ff9e] (the table base) on its first call,
    /// then flips bit 7 of its low byte (`bchg #7,$ffa5`, $f8e4) every time it
    /// re-projects because the camera cell, yaw or zoom changed. So the read
    /// point moves by 64 bytes (8 scanlines) inside every 128-byte colour slot,
    /// and moves back on the next camera change. Rotating each slot by `phase`
    /// (0 or 64) gives the table $e3e6 effectively reads; pass the result
    /// wherever `dith` goes. Measured on captures rotated in the emulator: terrain
    /// match 43-47% without the phase, 85-94% with it.
    let withPhase (dith: byte[]) (phase: int) : byte[] =
        if phase &&& 0x7F = 0 then dith
        else Array.init dith.Length (fun i -> dith.[(i &&& ~~~0x7F) + (((i &&& 0x7F) + phase) &&& 0x7F)])
```

On captures rotated inside the emulator, modelling the phase takes the port's terrain match from 43-47% to 85-94%. The stepper and the Godot view flip it on every camera change, as the game does.

**Seasons.** The table is not fixed either. The grass and slope slots, colour bytes `$1d` to `$2e`, are a working copy, and the table also holds three source versions of them. `word[$57fd0]` is the season, and it picks the source. At world build `$1ab60` copies the season's source over the working slots. After that, every game tick, `$1abaa` copies 16 more pixels from the source, in an order set by a 13-bit random-number generator. When the generator has been round all 8192 values, every pixel has been copied: the season advances and the next fade begins. So the landscape changes colour gradually, a speckle at a time, over 512 ticks:

```bash
sed -n '/let fading/,/^        t$/p' ../godot/logic/Season.fs
```

```output
    let fading (dith: byte[]) (season: int) (steps: int) : byte[] =
        let t = table dith ((season + 3) &&& 3)
        let src = sourceOffset season
        let mutable x = 0
        for _ in 1 .. min steps FadeSteps do
            x <- nextLcg x
            let row, bit = x >>> 4, x &&& 15
            if row < LiveLength / 8 then
                // bit `bit` of each big-endian plane word: byte 0 holds bits 15..8
                let b = row * 8 + (if bit >= 8 then 0 else 1)
                let mask = byte (1 <<< (bit &&& 7))
                for plane in 0 .. 3 do
                    let i = b + plane * 2
                    t.[LiveStart + i] <- (t.[LiveStart + i] &&& ~~~mask) ||| (dith.[src + i] &&& mask)
        t
```

```bash
dotnet fsi probe.fsx seasons
```

```output
season 0  source $2e000+$2980  trees +0  palette: 3:31% 2:30% 4:22% 1:13% 5:2%
season 1  source $2e000+$2080  trees +3  palette: 12:31% 13:28% 11:20% 1:13% 6:3% 2:2% 10:0%
season 2  source $2e000+$1780  trees +6  palette: 12:17% 13:15% 6:15% 7:13% 1:13% 11:11% 9:8% 2:2% 10:0%
season 3  source $2e000+$2080  trees +9  palette: 12:31% 13:28% 11:20% 1:13% 6:3% 2:2% 10:0%
```

Winter is khaki and grey with no green at all, spring and autumn share a green source, and summer mixes in brown and gold. The trees change too, but all at once: the tree frame adds `{0, 3, 6, 9}` by season, which picks bare, blossoming, leafy or brown trees, and it reads the season word directly. For 512 ticks after the season changes, the game shows last season's grass under this season's trees. The mission-1 captures behind this port are from exactly such a moment, one tick into summer.

![The four seasons at the mission-1 start pose, in the frame stepper (Y cycles them)](../assets/reference/stepper_seasons_119th.png)

## 7. Sprites go inside the walk

Trees, buildings, men, animals and banners hang off the cells. Each cell has a bucket at `$47970` holding a linked list of object records. The walk handler calls `$115e0` for a cell right after drawing that cell's two triangles, and `$115e0` draws every record in the bucket before the walk moves on. `Scene.fs` builds the frame that way, as one list of steps:

```bash
sed -n '/One thing the renderer draws/,/| _ -> () |\]/p' ../godot/logic/Scene.fs
```

```output
    /// One thing the renderer draws, in frame order. Each step carries its
    /// cell, so it can be drawn (or highlighted) on its own.
    type Step =
        | Triangle of cell: Fill.Cell * nth: int * tri: Fill.Tri     // nth = 1 or 2 within the cell
        | Sprite of cell: Fill.Cell * record: Sprites.EntityRec

    /// The cell a step belongs to.
    let cellOf step =
        match step with
        | Triangle(c, _, _) | Sprite(c, _) -> c

    /// Interleave each cell's sprites after its triangles, in the order the
    /// walk visits the cells. Records whose category has no frame to draw
    /// (see Sprites.entityFrame) are left out; records outside the visible
    /// 8x8 are never reached. Within a cell, records keep the order given,
    /// which is their bucket-chain order.
    let steps (ctx: Sprites.EntityCtx) (cells: Fill.Cell list) (recs: Sprites.EntityRec seq) : Step[] =
        let byCell =
            recs
            |> Seq.filter (fun r -> (Sprites.entityFrame ctx r).IsSome)
            |> Seq.groupBy (fun r -> r.Wcx, r.Wcy)
            |> dict
        [| for c in cells do
             yield Triangle(c, 1, c.First)
             yield Triangle(c, 2, c.Second)
             match byCell.TryGetValue((c.X, c.Y)) with
             | true, rs -> for r in rs -> Sprite(c, r)
             | _ -> () |]
```

```bash
dotnet fsi probe.fsx steps
```

```output
173 steps: 128 triangles (64 cells x 2) + 45 sprites
first cell with sprites, in draw order:
  triangle  cell (43,48) colour $24
  triangle  cell (43,48) colour $23
  sprite    cell (43,48) byte6 4
```

(`byte6` is the record's category byte; 4 is a building or tree. SPEC.md §6 lists the categories.)

The obvious simplification, drawing all the terrain first and then all the sprites on top, gives a different picture, and the port did it that way before this document was written. The test is to render a captured frame both ways and compare each with the game's own screen at the pixels where the two orders disagree. On six captures, three of them rotated to other camera angles inside the emulator, the game sides with the inline order almost every time:

```bash
grep -A 7 '| capture | terrain only' ../SPEC.md
```

```output
| capture | terrain only | sprites last (`drawEntities`) | inline (`Scene.render`) | px where the orders differ: game = last / inline / neither |
|---|---|---|---|---|
| `pm88_f1` (yaw `$f0`) | 94.1% | 89.17% | **96.80%** | 1 / 1159 / 18 of 1178 |
| `pm78_settle` (`$f0`) | 94.6% | 86.02% | **93.66%** | 1 / 1159 / 18 of 1178 |
| `pm74_late` (`$f0`) | 94.4% | 90.83% | **96.80%** | 3 / 897 / 14 of 914 |
| `rot40` (`$40`) | 94.4% | 90.98% | **97.83%** | 28 / 1267 / 62 of 1357 |
| `rot90` (`$90`) | 84.8% | 94.03% | **96.57%** | 20 / 361 / 55 of 436 |
| `rotc0` (`$c0`) | 91.1% | 89.78% | **94.26%** | 8 / 624 / 25 of 657 |
```

The inputs are `.ram` captures of the running game, which stay out of the repository, so this table is quoted from SPEC.md rather than re-run here. `pm78_settle` scores lower overall because its two compose buffers are known to disagree on the entity layer; the comparison at the differing pixels still comes out the same way. The yaw only picks men's and animals' facing frames. The camera cell matters more for trees and buildings: their position inside the cell is not stored, but worked out from the addresses of the record, its bucket slot and its cell's corner in the corner buffer, and the corner address depends on where the cell sits in the window. The port exports the records for the whole map and recomputes that jitter for every window, so every camera cell has its sprites. The castle keep in the hilltop fort is its own category (`byte6` 2, `$117d8`): a building frame from the tree sheet, anchored on the cell's centre.

Zoom changes the art as well as the positions. `$12244`, which draws buildings and trees, picks one of three copies of the same pictures by the zoom index: 32 x 32 when zoomed in (1-3), 32 x 24 at the default (4-5) and 16 x 16 zoomed out (6-7). Men, animals and banners stay 8 x 11 at every zoom.

Inline drawing matters because nearer terrain has to be able to cover a sprite. A tree on the far side of a hill is drawn when its cell comes up, and then the hill's nearer cells are drawn over it. How much sprite work the start frame throws away:

```bash
dotnet fsi probe.fsx occlusion
```

```output
45 sprites wrote 4378 px; 2689 of those px were later painted over
most-covered sprites (step, cell, kind, px drawn -> px left visible):
  step  19  cell (42,47) strip 1  byte6  4  181 ->   0
  step  37  cell (41,47) strip 2  byte6  4  181 ->   0
  step  38  cell (41,47) strip 2  byte6  4  181 ->   0
```

More than half the sprite pixels are painted over, and whole trees are drawn only to vanish. The game pays that cost rather than work out what is visible. Sprites drawn after all the terrain (top) put the trees behind the hilltop over the hill; drawn inline (bottom), the hill hides them, as it does in the game:

![Sprites drawn after all the terrain](../assets/reference/godot_screenshot_entities_91st.png)

![Sprites drawn inline, cell by cell, as the game does](../assets/reference/godot_screenshot_inline_118th.png)

## 8. Watching it happen: the frame stepper

Because the frame is now a list of steps, it can be replayed. `../stepper` is a small Mibo (raylib) app that draws the frame one triangle or sprite at a time, with pause, single steps by triangle, cell or strip, rewind, and overlays for the corner grid, the walk order, and the current triangle or sprite frame. Run it with `dotnet run --project ../stepper`. W/A/S/D move the camera a cell, Q/E rotate it, `[`/`]` zoom, Y changes the season, and B toggles the game's backdrop behind the island.

![The seven zoom levels around the mission-1 start](../assets/reference/stepper_zoom_119th.png)

It draws each step once into a buffer that logs its writes, so it knows exactly which pixels each step sets and in what order:

```bash
sed -n '/^\/\/\/ The camera and the season/,/Writes: Write\[\]\[\] }/p' ../stepper/Replay.fs
```

```output
/// The camera and the season: what a frame is built for, apart from the tick.
type View =
    { CamX: int                      // top-left cell of the drawn window
      CamY: int
      YawSteps: int                  // 0..15, [$ff9a] >> 4
      Zoom: int                      // 1..7, [$57ffc]: the window is 2 * Zoom cells square
      DitherPhase: int               // 0 or 64: flips on every camera change ($f8e4)
      Season: int }                  // 0..3, word[$57fd0] / 2 (Season.fs)

type Frame =
    { View: View
      Ctx: Sprites.EntityCtx         // per-frame sprite constants, yaw and tree set included
      Corners: Projection.Corner[,]
      Steps: Scene.Step[]
      Rasters: Fill.Raster option[]  // what $ef62 did, for triangle steps
      Writes: Write[][] }            // Writes.[i] = the pixels Steps.[i] writes, in order
```

A position in the frame is a step number plus a pixel count within that step, and any position can be rebuilt by replaying the log up to it:

```bash
sed -n '/Step. steps are finished/,/else finish f$/p;/^\/\/\/ Replay every write up to the cursor/,/for p in 0 .. c.Pixel - 1/p' ../stepper/Replay.fs
```

```output
/// `Step` steps are finished and `Pixel` pixels of the next one are drawn.
[<Struct>]
type Cursor = { Step: int; Pixel: int }

let start = { Step = 0; Pixel = 0 }
let finish (f: Frame) = { Step = f.Steps.Length; Pixel = 0 }
let isFinished (f: Frame) (c: Cursor) = c.Step >= f.Steps.Length

/// Advance by `n` pixel writes, carrying across step boundaries. Steps that
/// write nothing (a triangle clipped away, say) are passed over.
let advance (f: Frame) (n: int) (c: Cursor) : Cursor =
    let mutable step, pixel, left = c.Step, c.Pixel, n
    while step < f.Steps.Length && left >= f.Writes.[step].Length - pixel do
        left <- left - (f.Writes.[step].Length - pixel)
        step <- step + 1
        pixel <- 0
    if step < f.Steps.Length then { Step = step; Pixel = pixel + left } else finish f
/// Replay every write up to the cursor into `idx` (palette index per pixel,
/// -1 where nothing has been drawn yet).
let composeInto (idx: int[]) (f: Frame) (c: Cursor) =
    System.Array.Fill(idx, -1)
    let put (w: Write) = idx.[w.Y * W + w.X] <- int w.Index
    for s in 0 .. (min c.Step f.Steps.Length) - 1 do
        Array.iter put f.Writes.[s]
    if c.Step < f.Steps.Length then
        for p in 0 .. c.Pixel - 1 do put f.Writes.[c.Step].[p]
```

Playback runs finer than the ST ever drew: `$e420` writes 16-pixel words per bitplane and the sprite blitter writes whole byte rows, so pixel-by-pixel playback is a presentation choice. The order of spans, rows, triangles and sprites is the game's.

The replay is checked against the renderer at every yaw and every zoom, across the seasons: finishing the replay must give exactly the frame `Scene.render` draws, and stepping forward then back by any chunk must land where it started.

```bash
dotnet run --project ../stepper --no-build -- --selfcheck | tr -d '\r'
```

```output
yaw  0  zoom 4  season 0  steps 173  writes 22237  replay==render true  forward/back round trip true
yaw  1  zoom 4  season 0  steps 173  writes 22569  replay==render true  forward/back round trip true
yaw  2  zoom 4  season 1  steps 173  writes 23528  replay==render true  forward/back round trip true
yaw  3  zoom 4  season 1  steps 173  writes 25180  replay==render true  forward/back round trip true
yaw  4  zoom 4  season 2  steps 173  writes 27085  replay==render true  forward/back round trip true
yaw  5  zoom 4  season 2  steps 173  writes 26733  replay==render true  forward/back round trip true
yaw  6  zoom 4  season 3  steps 173  writes 26026  replay==render true  forward/back round trip true
yaw  7  zoom 4  season 3  steps 173  writes 24397  replay==render true  forward/back round trip true
yaw  8  zoom 4  season 0  steps 173  writes 20798  replay==render true  forward/back round trip true
yaw  9  zoom 4  season 0  steps 173  writes 20193  replay==render true  forward/back round trip true
yaw 10  zoom 4  season 1  steps 173  writes 21259  replay==render true  forward/back round trip true
yaw 11  zoom 4  season 1  steps 173  writes 21843  replay==render true  forward/back round trip true
yaw 12  zoom 4  season 2  steps 173  writes 23111  replay==render true  forward/back round trip true
yaw 13  zoom 4  season 2  steps 173  writes 23296  replay==render true  forward/back round trip true
yaw 14  zoom 4  season 3  steps 173  writes 24481  replay==render true  forward/back round trip true
yaw 15  zoom 4  season 3  steps 173  writes 24249  replay==render true  forward/back round trip true
yaw  3  zoom 1  season 1  steps  22  writes  7892  replay==render true  forward/back round trip true
yaw  5  zoom 2  season 2  steps  61  writes 26256  replay==render true  forward/back round trip true
yaw  7  zoom 3  season 3  steps 108  writes 23776  replay==render true  forward/back round trip true
yaw  9  zoom 4  season 0  steps 173  writes 20193  replay==render true  forward/back round trip true
yaw 11  zoom 5  season 1  steps 252  writes 19771  replay==render true  forward/back round trip true
yaw 13  zoom 6  season 2  steps 356  writes 18010  replay==render true  forward/back round trip true
yaw 15  zoom 7  season 3  steps 470  writes 21676  replay==render true  forward/back round trip true
```

## 9. Redoing it in Godot

There are two ways to put this in Godot, and they answer different questions.

**Route A: run the game's renderer and show its output.** This is what `../godot` does today. The F# above draws a 320 x 200 palette-index buffer on the CPU exactly as the game does, and a thin C# node copies it into an `ImageTexture` whenever the camera moves:

```bash
sed -n '/private void RenderFrame()/,/Scene.render(buf, dither/p;/_rect.Texture = ImageTexture/p' ../godot/game/TerrainView.cs
```

```output
    private void RenderFrame()
    {
        var proj = Proj;
        var corners = PmProjection.projectGrid(proj, _map, _camX, _camY);
        var buf = Fill.Buffer.Create();
        var dither = Fill.withPhase(Season.table(_dither, _season), _ditherPhase);

        // Terrain + the per-cell entity pass (SPEC.md section 6). Scene.render
        // draws each cell's sprites straight after its two triangles, the way
        // $f898 calls $115e0 inline (scored against six captured frames, the
        // game's screen matches this order, not sprites-last; SPEC.md 6).
        // Both write RAW $3f364 coordinates, so the XInset shift below places
        // terrain and sprites together.
        var ectx = new Sprites.EntityCtx(
            _yawSteps * 16, _entAnim, _entSelGroup, Season.treeTileOffset(_season), _entRotPhase,
            proj.Half, _sheet33, _sheetProp, _sheetProp32, _sheetProp16, System.Array.Empty<byte>());
        Scene.render(buf, dither, 0, ectx, corners, _map, _camX, _camY, _yawSteps, _entRecs);
        _rect.Texture = ImageTexture.CreateFromImage(img);
```

Everything the port reproduces stays as the game draws it: the dither and its phase, the clipping, the `$1c` override, the row the span walker stops short of. The island is drawn over the game's own `$78000` master screen (HUD, lord portrait, temple backdrop, minimap), exported once as `assets/backdrop.bin`, since the game never changes it. Against the game's frames that is 94-98% of pixels, and nearly all of the rest are sprites.

![The Godot view: the port's island over the game's own backdrop](../assets/reference/godot_screenshot_backdrop_118th.png) The Godot view pans, rotates and changes season like the stepper, and stays at the default zoom. The cost is that Godot is only a window. You cannot zoom smoothly, light it, or run it above 320 x 200 without changing what it is.

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
- `dotnet run --project ../stepper` shows every step above live. Press N to number the cells in walk order, G for the corner grid, Right to step one triangle at a time, and W/A/S/D, `[`/`]` and Y to move, zoom and change the season.

