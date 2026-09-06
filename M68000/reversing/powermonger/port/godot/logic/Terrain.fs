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

    // -- HUD world minimap ($78000 top-left corner) -------------------------
    // 90th (live-traced pm67_ok_pre -> the briefing-OK click -> $13b9a): the
    // minimap is NOT drawn per frame. $13b9a bakes it once into the $78000
    // master (SPEC.md section 7): it builds a 64x128 byte per-cell source
    // buffer at $418ae (stride 64, ~= the terrain type plane; `src - type` is
    // 0 for 7424/8192 cells, -1..-4 for a shaded coastal fringe), then $e6ee
    // (pm_blit_hud_sprite) rasters it 1:1 into the master at screen origin
    // (1, 6): cell (wx, wy) -> screen pixel (wx + 1, wy + 6), colour =
    // MinimapRamp[src byte]. On a settled still frame the composed buffer's
    // minimap region is byte-identical to the master (verified by frame diff);
    // the per-frame $11f82 8x11 sprite near it (~screen 33..47, 46..60) is a
    // generic HUD marker, not a minimap raster.

    [<Literal>]
    let MinimapOriginX = 1

    [<Literal>]
    let MinimapOriginY = 6

    /// $e6ee's source-byte -> shifter palette-index lookup, reconstructed from
    /// a live trace of the $13b9a minimap raster (every source byte mapped to
    /// exactly one palette index; 100% against pm88_f1's $78000 master). The
    /// source byte is a terrain elevation/type value: 0 = sea, then a khaki ->
    /// green -> yellow -> gold ramp with height. A from-scratch port that does
    /// not replay $13b9a's $418ae buffer feeds `TypeAt` here instead (93.7%
    /// against the master -- the shaded fringe is the only miss).
    let minimapPaletteIndex (srcByte: int) : int =
        let s = srcByte &&& 0xFF
        if s = 0 then 14                     // sea
        elif s <= 0x1C then 3               // lowest land (khaki)
        elif s = 0x1D then 2
        elif s = 0x1E then 12
        elif s <= 0x22 then 1              // (sparse, HUD-adjacent)
        elif s <= 0x27 then 13            // dark green
        elif s = 0x28 then 12
        elif s <= 0x2C then 11           // light green
        elif s <= 0x38 then 10          // yellow
        elif s = 0x39 then 6
        elif s = 0x3A then 7          // brown
        else 9                        // gold (coast / peaks)

    /// Render the minimap into a caller-supplied 320x200 palette-index buffer
    /// (only the covered cells are written; `set` is `x y idx -> unit`). Mirrors
    /// $e6ee's 1:1 plot. `src` is the per-cell source byte (default: the type
    /// plane, the from-scratch stand-in for $418ae).
    let renderMinimap (m: Map) (set: int -> int -> int -> unit) =
        for wy in 0 .. Height - 1 do
            for wx in 0 .. Width - 1 do
                let sx = wx + MinimapOriginX
                let sy = wy + MinimapOriginY
                if sx >= 0 && sx < 320 && sy >= 0 && sy < 200 then
                    set sx sy (minimapPaletteIndex (m.TypeAt(wx, wy)))
