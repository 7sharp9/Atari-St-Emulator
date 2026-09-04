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
    /// stone border + the pre-baked sea, SPEC.md section 7) — walkQ3 draws
    /// only the island, same as the game's own per-frame $f898.
    type Buffer =
        { Index: byte[]
          Covered: bool[] }

        static member Create() =
            { Index = Array.zeroCreate (ScreenWidth * ScreenHeight)
              Covered = Array.zeroCreate (ScreenWidth * ScreenHeight) }

        member b.Set(x: int, y: int, idx: byte) =
            if x >= 0 && x < ScreenWidth && y >= 0 && y < ScreenHeight then
                let i = y * ScreenWidth + x
                b.Index.[i] <- idx
                b.Covered.[i] <- true

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

    /// $ef62 $efbe..$efd4 — rotate the min-Y vertex to the front; the other
    /// two keep their original cyclic order. NOT a full sort (b and c are
    /// never independently swapped) — this is why the "3rd vertex" is not
    /// guaranteed to be the true bottom (see ef62Raster's general branch).
    let private cyclicYSort (v: (float * float)[]) : (float * float)[] =
        let sy = v |> Array.map snd
        if sy.[0] <= sy.[1] && sy.[0] <= sy.[2] then [| v.[0]; v.[1]; v.[2] |]
        elif sy.[1] < sy.[0] && sy.[1] <= sy.[2] then [| v.[1]; v.[2]; v.[0] |]
        else [| v.[2]; v.[0]; v.[1] |]

    /// $e420 — two 16.16 X accumulators (left/right), each stepped one slope
    /// per scanline; row 0 uses the start X with no step ($e41a `bra $e456`).
    /// A switching edge reloads its slope at its own `switch` row (the
    /// shorter edge bending toward the far vertex). Aborts the WHOLE triangle
    /// (remaining rows too) the first time ixR < ixL ($e468). The
    /// $ec62/$eca2 partial-word edge masks reduce exactly to "draw pixel x
    /// iff ixL <= x <= ixR" for a per-pixel index buffer — no planar masking
    /// needed. $ef62's own clip is screenX <= 255 (the iso window's right
    /// edge, not the 320px screen).
    let private ddaWalk (buf: Buffer) (dith: byte[]) (colour: int) (topY: int) (totalRows: int)
                         (xL: int) (slopeL: int) (switchL: int option) (slopeL2: int)
                         (xR: int) (slopeR: int) (switchR: int option) (slopeR2: int) =
        let mutable pL = int64 xL <<< 16
        let mutable pR = int64 xR <<< 16
        let mutable sL = slopeL
        let mutable sR = slopeR
        let mutable aborted = false
        let mutable row = 0
        while not aborted && row <= totalRows do
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
                elif ixL <= 0xFF then
                    let xs = max 0 ixL
                    let xe = min (ScreenWidth - 1) (min ixR 0xFF)
                    for x in xs .. xe do
                        buf.Set(x, y, ditherIndex dith colour y x)
            row <- row + 1

    /// pm_tri_raster ($ef62) → the $e420 DDA span walker. Ports:
    ///   * the cyclic-rotate Y sort ($efbe..$efd4)
    ///   * general vs flat-top split ($efe0..$f13c), incl. the $f134 reorder
    ///   * per-edge 16.16 slope via fixedSlope ($f000)
    ///   * the "force colourByte 0x1c" coast rule ($f072/$f154): general ->
    ///     when the mid vertex is already the LEFT vertex (slope(top->bot) >
    ///     slope(top->mid)); flat-top -> when the right apex X < the left
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
                    (p2: Projection.Corner) (colourIn: int) (tick: int) =
        // sort by float Y first ($efbe compares the fixed-point screenY words),
        // THEN round to nearest int — matches pm_render_ref.py exactly.
        let sorted = cyclicYSort [| p0.X, p0.Y; p1.X, p1.Y; p2.X, p2.Y |]
        let toInt (x: float, y: float) = int (System.Math.Round x), int (System.Math.Round y)
        let mutable x0, y0 = toInt sorted.[0]
        let mutable x1, y1 = toInt sorted.[1]
        let mutable x2, y2 = toInt sorted.[2]
        if y0 = y2 && y0 = y1 then
            ()                                                  // degenerate ($f13c rts)
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
                        ddaWalk buf dith colour y0 h
                            xl (fixedSlope (x2 - xl) h) None 0
                            xr (fixedSlope (x2 - xr) h) None 0
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
                    ddaWalk buf dith colour2 y0 totalRows xLs sL switchL sL2 xRs sR switchR sR2

    /// pm_grid_walk_q3 ($fccc), yaw 0xf0 (quadrant 3). `corners` is the
    /// projected 9x9 grid from Projection.projectGrid — gr,gc both 0..2*Half,
    /// which is exactly $3f364's own (row,col) layout, so it plugs in
    /// directly (no re-indexing needed).
    ///
    ///   outer k = 0..7: cell column, EAST -> WEST (far -> near)
    ///   inner j = 0..7: cell row,    NORTH -> SOUTH (far -> near)
    ///   cell (cx, cy) = (camX + 7-k, camY + j) ; corner (row, col) = (j, 7-k)
    ///     C00 = corner(col,   row)    C10 = corner(col+1, row)
    ///     C01 = corner(col,   row+1)  C11 = corner(col+1, row+1)
    ///   flag-plane bit 7 (Terrain.DiagonalSelector) CLEAR:
    ///     split on the C00-C11 diagonal — ef62(C10,C11,C00,type) ; ef62(C01,C00,C11,height)
    ///   SET: split on the C10-C01 diagonal, sub-order by packed(C01) vs packed(C10)
    let walkQ3 (buf: Buffer) (dith: byte[]) (corners: Projection.Corner[,]) (m: Terrain.Map)
               (camX: int) (camY: int) (tick: int) =
        let packed (c: Projection.Corner) =
            (int (System.Math.Round(c.X: float)) <<< 16) ||| (int (System.Math.Round(c.Y: float)) &&& 0xFFFF)
        for k in 0 .. 7 do
            let col = 7 - k
            let cx = camX + col
            for j in 0 .. 7 do
                let row = j
                let cy = camY + row
                let c00 = corners.[row, col]
                let c10 = corners.[row, col + 1]
                let c01 = corners.[row + 1, col]
                let c11 = corners.[row + 1, col + 1]
                let typ = m.TypeAt(cx, cy)
                let hgt = m.HeightAt(cx, cy)
                if not (m.DiagonalSelector(cx, cy)) then
                    ef62Raster buf dith c10 c11 c00 typ tick
                    ef62Raster buf dith c01 c00 c11 hgt tick
                elif packed c01 <= packed c10 then
                    ef62Raster buf dith c00 c10 c01 hgt tick
                    ef62Raster buf dith c11 c01 c10 typ tick
                else
                    ef62Raster buf dith c11 c01 c10 typ tick
                    ef62Raster buf dith c00 c10 c01 hgt tick
