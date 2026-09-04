namespace PmLogic

/// Decode of assets/terrain.bin (see ../../SPEC.md section 2).
/// 64 x 128 cells, row-major, stride 64. 4 bytes/cell: type, height, flag, control.
module Terrain =

    [<Literal>]
    let Width = 64

    [<Literal>]
    let Height = 128

    [<Literal>]
    let WaterLevel = 0x0cuy

    [<Literal>]
    let DiagonalSelectorBit = 0x80uy

    type Map =
        { Type: byte[]        // terrain class / colour of the "type" triangle
          HeightPlane: byte[] // $438ee height plane
          // bit7 was read as "corner unmoved this frame -> skip fill" (76th
          // pass); the 78th pass's live trace of pm_grid_walk_q3 ($fccc)
          // corrected this — it is the per-cell DIAGONAL SELECTOR the walk
          // uses to pick which pair of corners the two triangles split on
          // (see Fill.walkQ3 / ../../SPEC.md section 4). Both branches draw;
          // it is not a skip.
          Flag: byte[]
          Control: byte[] }   // $3f86c — the height the projector reads

        member m.Index(x, y) = y * Width + x
        member m.ControlAt(x, y) = int m.Control.[m.Index(x, y)]
        member m.TypeAt(x, y) = int m.Type.[m.Index(x, y)]
        member m.HeightAt(x, y) = int m.HeightPlane.[m.Index(x, y)]
        member m.IsWater(x, y) = m.HeightPlane.[m.Index(x, y)] < WaterLevel
        member m.DiagonalSelector(x, y) = m.Flag.[m.Index(x, y)] &&& DiagonalSelectorBit <> 0uy

    /// Parse the interleaved [type,height,flag,control] byte stream.
    let parse (raw: byte[]) : Map =
        let n = Width * Height
        if raw.Length < n * 4 then
            failwithf "terrain.bin too short: %d bytes, need %d" raw.Length (n * 4)
        let t = Array.zeroCreate n
        let h = Array.zeroCreate n
        let f = Array.zeroCreate n
        let c = Array.zeroCreate n
        for i in 0 .. n - 1 do
            t.[i] <- raw.[i * 4 + 0]
            h.[i] <- raw.[i * 4 + 1]
            f.[i] <- raw.[i * 4 + 2]
            c.[i] <- raw.[i * 4 + 3]
        { Type = t; HeightPlane = h; Flag = f; Control = c }

    /// Bounding box of the non-zero control-plane cells (the playable island).
    let islandBBox (m: Map) =
        let mutable x0, y0, x1, y1 = Width, Height, 0, 0
        for y in 0 .. Height - 1 do
            for x in 0 .. Width - 1 do
                if m.Control.[m.Index(x, y)] <> 0uy then
                    x0 <- min x0 x; y0 <- min y0 y
                    x1 <- max x1 x; y1 <- max y1 y
        (x0, y0, x1, y1)

    /// The 16-entry palette-index ramp for a flat (non-dither) land fill, keyed
    /// on the raw terrain colour byte. See SPEC.md section 4 "modern port".
    let flatPaletteIndex (colourByte: int) : int =
        if colourByte < int WaterLevel then 14 + (colourByte &&& 1)
        else
            let lo, hi = 0x1c, 0x40
            let t = max 0.0 (min 1.0 (float (colourByte - lo) / float (hi - lo)))
            [| 13; 12; 12; 11; 11; 3; 2; 1 |].[min 7 (int (t * 8.0))]
