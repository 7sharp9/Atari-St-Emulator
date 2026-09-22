namespace PmLogic

/// Port of PowerMonger's terrain rasteriser: pm_grid_walk_q3 ($fccc, yaw
/// 0xf0/quadrant 3) + pm_tri_raster ($ef62) + the $e420 16.16 DDA span walker
/// + the $e3e6/$e420 dither fill. See ../../SPEC.md section 4.
///
/// This is a 1:1 port of tools/pm_render_ref.py's walk_q3 / ef62_raster /
/// _fixed_slope / _dda_walk / dither_index (80th pass closed both the DDA and
/// the dither phase's mod-128 wrap — there is no DITHER_COLOUR_BIAS fudge or
/// float+floor() span left to carry over; that was the stated blocker for
/// this file in the 76th/79th passes). Scored ~94% exact / ~95% within ±1
/// palette index against the game's own frame buffer (SPEC.md verification
/// status). No Godot reference — see PmLogic.fsproj's rationale comment.
module Fill =

    [<Literal>]
    let ScreenWidth = 320

    [<Literal>]
    let ScreenHeight = 200

    /// One rendered frame's terrain layer: a 320x200 palette-index buffer
    /// plus a coverage mask. Uncovered pixels are the $78000 master (HUD +
    /// stone border + the pre-baked sea, SPEC.md section 7) — the walk draws
    /// only the island, same as the game's own per-frame $f898.
    type Buffer =
        { Index: byte[]
          Covered: bool[]
          /// When present, every write in the order it happens, packed as
          /// (pixel offset <<< 8) ||| palette index. The frame stepper replays it.
          Log: ResizeArray<int> option }

        static member Create() =
            { Index = Array.zeroCreate (ScreenWidth * ScreenHeight)
              Covered = Array.zeroCreate (ScreenWidth * ScreenHeight)
              Log = None }

        /// A buffer that also records its writes, in order.
        static member Logged() = { Buffer.Create() with Log = Some(ResizeArray()) }

        member b.Set(x: int, y: int, idx: byte) =
            if x >= 0 && x < ScreenWidth && y >= 0 && y < ScreenHeight then
                let i = y * ScreenWidth + x
                b.Index.[i] <- idx
                b.Covered.[i] <- true
                match b.Log with
                | Some log -> log.Add((i <<< 8) ||| int idx)
                | None -> ()

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

    /// $e3e6 setup + the $e420/$e44a roll. Live single-stepped (80th pass):
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

    /// $ef62 $efbe..$efd4 — rotate the min-Y vertex to the front; the other
    /// two keep their original cyclic order. NOT a full sort (b and c are
    /// never independently swapped) — this is why the "3rd vertex" is not
    /// guaranteed to be the true bottom (see ef62Raster's general branch).
    let private cyclicYSort (v: (float * float)[]) : (float * float)[] =
        let sy = v |> Array.map snd
        if sy.[0] <= sy.[1] && sy.[0] <= sy.[2] then [| v.[0]; v.[1]; v.[2] |]
        elif sy.[1] < sy.[0] && sy.[1] <= sy.[2] then [| v.[1]; v.[2]; v.[0] |]
        else [| v.[2]; v.[0]; v.[1] |]

    /// What $ef62 did with one triangle. The frame stepper shows this, since
    /// the colour drawn is not always the colour byte passed in (reversed
    /// winding forces $1c) and the span walk can stop early.
    type Raster =
        | Skipped of reason: string
        | Walked of colour: int * rows: int * abortedAt: int option

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

    /// pm_tri_raster ($ef62) → the $e420 DDA span walker. Ports:
    ///   * the cyclic-rotate Y sort ($efbe..$efd4)
    ///   * general vs flat-top split ($efe0..$f13c), incl. the $f134 reorder
    ///   * per-edge 16.16 slope via fixedSlope ($f000)
    ///   * "force colourByte 0x1c" on reversed winding ($f072/$f154): general
    ///     -> mid vertex already LEFT (slope(top->bot) > slope(top->mid)); flat-
    ///     top -> right apex X < left. Back-facing; mostly overdrawn (118th).
    ///   * the mid-vertex slope switch: the edge on the mid vertex's side
    ///     reloads to slope(mid->bot) at scanline (mid.y - top.y) — run-
    ///     counter expiry ($e42a/$e43e), consuming record[20]/[22]. Both
    ///     non-apex edges walk from the apex; whichever's run counter expires
    ///     first is the one that bends, so triangle height = max(dy1, dy2),
    ///     NOT necessarily the cyclic-3rd vertex's dy (the cyclic sort does
    ///     not guarantee it is the true bottom).
    ///   * water shimmer: colour += tick if colour < 0x0c (walk_q3 passes the
    ///     raw plane byte, same as $fccc).
    let ef62Raster (buf: Buffer) (dith: byte[]) (p0: Projection.Corner) (p1: Projection.Corner)
                    (p2: Projection.Corner) (colourIn: int) (tick: int) : Raster =
        // sort by float Y first ($efbe compares the fixed-point screenY words),
        // THEN round to nearest int — matches pm_render_ref.py exactly.
        let sorted = cyclicYSort [| p0.X, p0.Y; p1.X, p1.Y; p2.X, p2.Y |]
        let toInt (x: float, y: float) = int (System.Math.Round x), int (System.Math.Round y)
        let mutable x0, y0 = toInt sorted.[0]
        let mutable x1, y1 = toInt sorted.[1]
        let mutable x2, y2 = toInt sorted.[2]
        if y0 = y2 && y0 = y1 then
            Skipped "all three corners on one scanline"         // degenerate ($f13c rts)
        else
            let mutable colour = if colourIn < 0x0C then (colourIn + tick) &&& 0xFF else colourIn
            if y1 = y0 || y2 = y0 then
                // flat-top ($f138), incl. the $f134 reorder (top,mid,bot)->(bot,top,mid)
                if y2 = y0 && y1 <> y0 then
                    let nx0, ny0, nx1, ny1, nx2, ny2 = x2, y2, x0, y0, x1, y1
                    x0 <- nx0; y0 <- ny0
                    x1 <- nx1; y1 <- ny1
                    x2 <- nx2; y2 <- ny2
                if y1 = y0 then
                    let h = y2 - y0
                    if h > 0 then
                        let mutable xl, xr = x0, x1
                        if xr < xl then
                            let t = xl in xl <- xr; xr <- t
                            colour <- 0x1C
                        let aborted =
                            ddaWalk buf dith colour y0 h
                                xl (fixedSlope (x2 - xl) h) None 0
                                xr (fixedSlope (x2 - xr) h) None 0
                        Walked(colour, h, aborted)
                    else Skipped "flat top with no height"
                else Skipped "flat top with no height"
            else
                // general: apex v0, other two = v1 (cyclic 2nd), v2 (cyclic 3rd).
                // Both non-apex edges walk from the apex; run-counter expiry
                // decides which bends toward the far vertex (see doc comment).
                let dy1 = y1 - y0
                let dy2 = y2 - y0
                let s1 = fixedSlope (x1 - x0) dy1               // apex -> v1 ($f000 -> D4)
                let s2 = fixedSlope (x2 - x0) dy2               // apex -> v2 ($f036 -> D5)
                if s1 <> s2 then
                    // $f072 bgt $f07a: s2 > s1 -> v1 is the LEFT vertex, force 0x1c.
                    let colour2, left, right =
                        if s2 > s1 then
                            0x1C,
                            (x0, s1, dy1, (x1, y1), (x2, y2)),
                            (x0, s2, dy2, (x2, y2), (x1, y1))
                        else
                            colour,
                            (x0, s2, dy2, (x2, y2), (x1, y1)),
                            (x0, s1, dy1, (x1, y1), (x2, y2))
                    let totalRows = max dy1 dy2
                    let edge (xs, sl, run, (ax, ay), (bx, by)) =
                        if run < totalRows && by > ay then
                            xs, sl, Some run, fixedSlope (bx - ax) (by - ay)
                        else
                            xs, sl, None, 0
                    let xLs, sL, switchL, sL2 = edge left
                    let xRs, sR, switchR, sR2 = edge right
                    let aborted = ddaWalk buf dith colour2 y0 totalRows xLs sL switchL sL2 xRs sR switchR sR2
                    Walked(colour2, totalRows, aborted)
                else Skipped "both edges have the same slope"

    // -- the grid walk as a draw plan (118th) -------------------------------
    // Each quadrant handler makes two decisions: the order it visits the 8x8
    // cells (far -> near), and how it splits each cell into two triangles.
    // planQn returns both as data, a Cell list in exact draw order, and `walk`
    // just draws it. Nothing is reordered: drawing the plan is byte-identical
    // to the old direct walk (scratchpad/pm118/baseline.fsx, all 16 yaws x 5
    // cams x 2 ticks). The plan exists so a viewer can replay the frame one
    // triangle at a time, and so Scene.fs can put each cell's sprites straight
    // after its triangles, as $f898 does.
    //
    // Every handler is two nested 8-step loops. Below, `strip` is the outer
    // loop and `i` the inner one; each handler differs only in how (strip, i)
    // maps to the cell's (row, col) and in its split rule.

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
          Row: int; Col: int     // its top-left corner in the 9x9 projected grid
          Order: int             // position in the walk, 0..63 = strip * 8 + i
          Quad: Quad
          First: Tri             // drawn first ...
          Second: Tri }          // ... then this one over it

        /// Outer-loop pass 0..7: the far -> near strip of 8 cells it belongs to.
        member c.Strip = c.Order / 8
        /// Inner-loop index 0..7 within its strip.
        member c.InStrip = c.Order % 8

    let private tri a b c colour = { A = a; B = b; C = c; Colour = colour }

    /// (sx << 16) | sy -- the handlers' longword compare of two packed corners.
    let private packed (c: Projection.Corner) =
        (int (System.Math.Round(c.X: float)) <<< 16) ||| (int (System.Math.Round(c.Y: float)) &&& 0xFFFF)

    /// Build the Cell the loops reach at (strip, i), which sits at grid
    /// position (row, col), splitting it with `split`.
    let private visit (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int)
                      (split: Quad -> Tri * Tri) (strip: int, i: int) (row: int, col: int) : Cell =
        let x, y = camX + col, camY + row
        let q =
            { C00 = corners.[row, col];     C10 = corners.[row, col + 1]
              C01 = corners.[row + 1, col]; C11 = corners.[row + 1, col + 1]
              TypeByte = map.TypeAt(x, y); HeightByte = map.HeightAt(x, y)
              Diagonal = map.DiagonalSelector(x, y) }
        let first, second = split q
        { X = x; Y = y; Row = row; Col = col; Order = strip * 8 + i; Quad = q; First = first; Second = second }

    /// pm_grid_walk_q3 ($fccc), yaw 0xf0 (quadrant 3). `corners` is the
    /// projected 9x9 grid from Projection.projectGrid — gr,gc both 0..2*Half,
    /// which is exactly $3f364's own (row,col) layout, so it plugs in
    /// directly (no re-indexing needed).
    ///
    ///   strip = cell column, EAST -> WEST (far -> near)
    ///   i     = cell row,    NORTH -> SOUTH (far -> near)
    ///   (row, col) = (i, 7 - strip)
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
        [ for strip in 0 .. 7 do
            for i in 0 .. 7 -> visit (strip, i) (i, 7 - strip) ]

    /// pm_grid_walk_q0 ($f98e -- NOT $f98c; powermonger.sym's old address was
    /// 2 bytes low, landing on the tail of the jump table itself, fixed 83rd
    /// pass), yaw in {$00,$10,$20,$30}. Live-trace-verified (83rd,
    /// scratchpad/pm83_q0c.ram, cell (36,49)): the CLEAR "else" branch's
    /// first ef62 call landed with D0=C11 D1=C00 D2=C10 D3=$2c, matching
    /// tri(C11,C00,C10,type) exactly (packed C11 > packed C00 at that cell).
    ///
    ///   strip = cell row,    NORTH -> SOUTH (far -> near)
    ///   i     = cell column, WEST  -> EAST  (far -> near)
    ///   (row, col) = (strip, i)   (no start offset -- A0/A1/A2 are already at the camCell base)
    ///   flag CLEAR: split C00-C11, sub-order by packed(C11) <= packed(C00)
    ///     (q3 leaves CLEAR unconditional and sub-orders SET instead)
    ///   flag SET: split C10-C01, unconditional
    let planQ0 (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int) : Cell list =
        let visit = visit corners map camX camY (fun q ->
            if not q.Diagonal then
                if packed q.C11 <= packed q.C00 then
                    tri q.C00 q.C11 q.C01 q.HeightByte, tri q.C00 q.C10 q.C11 q.TypeByte
                else
                    tri q.C11 q.C00 q.C10 q.TypeByte, tri q.C11 q.C01 q.C00 q.HeightByte
            else
                tri q.C00 q.C10 q.C01 q.HeightByte, tri q.C11 q.C01 q.C10 q.TypeByte)
        [ for strip in 0 .. 7 do
            for i in 0 .. 7 -> visit (strip, i) (strip, i) ]

    /// pm_grid_walk_q1 ($fa9a), yaw in {$40,$50,$60,$70}. Live-trace-verified
    /// (83rd, scratchpad/pm83_q1c.ram, cell (40,50)): the CLEAR branch's
    /// first ef62 call landed with D0=C01 D1=C00 D2=C11 D3=$29, matching
    /// tri(C01,C00,C11,height) exactly (hgt(40,50) = $29).
    ///
    ///   strip = cell column, WEST  -> EAST  (far -> near)
    ///   i     = cell row,    SOUTH -> NORTH (far -> near)
    ///   (row, col) = (7 - i, strip)   ; start offset row7,col0
    ///   flag CLEAR: split C00-C11, unconditional
    ///   flag SET: split C10-C01, sub-order by packed(C01) < packed(C10)
    ///     (same diagonal as q3's SET branch, but a STRICT < here)
    let planQ1 (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int) : Cell list =
        let visit = visit corners map camX camY (fun q ->
            if not q.Diagonal then
                tri q.C01 q.C00 q.C11 q.HeightByte, tri q.C10 q.C11 q.C00 q.TypeByte
            elif packed q.C01 < packed q.C10 then
                tri q.C00 q.C10 q.C01 q.HeightByte, tri q.C11 q.C01 q.C10 q.TypeByte
            else
                tri q.C11 q.C01 q.C10 q.TypeByte, tri q.C00 q.C10 q.C01 q.HeightByte)
        [ for strip in 0 .. 7 do
            for i in 0 .. 7 -> visit (strip, i) (7 - i, strip) ]

    /// pm_grid_walk_q2 ($fbb4), yaw in {$80,$90,$a0,$b0}. Live-trace-verified
    /// (83rd, scratchpad/pm83_q2c.ram, cell (40,47)): the CLEAR "if" branch's
    /// first ef62 call landed with D0=C01 D1=C00 D2=C11 D3=$2b, matching
    /// tri(C01,C00,C11,height) exactly (packed C11 <= packed C00, hgt(40,47) = $2b).
    ///
    ///   strip = cell row,    SOUTH -> NORTH (far -> near)
    ///   i     = cell column, EAST  -> WEST  (far -> near)
    ///   (row, col) = (7 - strip, 7 - i)   ; start offset row7,col7
    ///   flag CLEAR: split C00-C11, sub-order by packed(C11) <= packed(C00)
    ///     (mirrors q0's CLEAR branch)
    ///   flag SET: split C10-C01, unconditional
    let planQ2 (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int) : Cell list =
        let visit = visit corners map camX camY (fun q ->
            if not q.Diagonal then
                if packed q.C11 <= packed q.C00 then
                    tri q.C01 q.C00 q.C11 q.HeightByte, tri q.C10 q.C11 q.C00 q.TypeByte
                else
                    tri q.C10 q.C11 q.C00 q.TypeByte, tri q.C01 q.C00 q.C11 q.HeightByte
            else
                tri q.C11 q.C01 q.C10 q.TypeByte, tri q.C00 q.C10 q.C01 q.HeightByte)
        [ for strip in 0 .. 7 do
            for i in 0 .. 7 -> visit (strip, i) (7 - strip, 7 - i) ]

    /// port of $f97e/$f982's dispatch: q = ((yaw+8)>>5)&6, handler = q>>1.
    /// yaw here is yawSteps*16 (Projection.Params.YawSteps, 0..15).
    let quadrant (yawSteps: int) = (((yawSteps * 16 + 8) >>> 5) &&& 6) >>> 1

    /// The whole frame's terrain as a draw plan: the 64 cells in the order
    /// the quadrant handler for this yaw visits them.
    let plan (corners: Projection.Corner[,]) (map: Terrain.Map) (camX: int) (camY: int) (yawSteps: int) =
        let handler = [| planQ0; planQ1; planQ2; planQ3 |].[quadrant yawSteps]
        handler corners map camX camY

    /// Draw one triangle ($ef62 -> the $e420 DDA + dither fill).
    let drawTri (buf: Buffer) (dith: byte[]) (tick: int) (t: Tri) : Raster =
        ef62Raster buf dith t.A t.B t.C t.Colour tick

    /// Draw one cell's two triangles, in walk order.
    let drawCell (buf: Buffer) (dith: byte[]) (tick: int) (c: Cell) =
        drawTri buf dith tick c.First |> ignore
        drawTri buf dith tick c.Second |> ignore

    /// Terrain only: draw the plan for this yaw. Scene.render interleaves
    /// each cell's sprites; this is the sprite-free walk.
    let walk (buf: Buffer) (dith: byte[]) (corners: Projection.Corner[,]) (map: Terrain.Map)
             (camX: int) (camY: int) (tick: int) (yawSteps: int) =
        plan corners map camX camY yawSteps |> List.iter (drawCell buf dith tick)
