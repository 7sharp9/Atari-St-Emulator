namespace PmLogic

/// Decode stub for the $11f82 mini-sprite blitter (assets/sprites/sheet_raw.bin).
/// See ../../SPEC.md section 6. Only the frame decode is ported here — the
/// per-category frame base/count (SPEC.md §9 item 3, the sprite/HUD rip) and
/// the heading->frame selection are still open; this exists so Fill.fs's
/// terrain walk has somewhere to hand off to once sprite compositing lands
/// (walkQ3 draws terrain only, painter's order is free — SPEC.md §4/§6).
module Sprites =

    [<Literal>]
    let FrameWidth = 8

    [<Literal>]
    let FrameHeight = 11

    /// 11 rows of [mask, p0, p1, p2, p3] = 55 bytes/frame.
    [<Literal>]
    let FrameStride = 55

    /// One decoded 8x11 four-bitplane (16-colour) sprite frame.
    /// Pixel = -1 for "transparent" (mask bit set -> background shows through).
    type Frame = { Pixels: int[] }               // FrameWidth * FrameHeight, row-major

    /// t_heading_frame ($1675a) — 16 headings -> sprite frame index, 0xff =
    /// draw nothing for this facing (folds to ~8 drawn frames + a horiz flip).
    let headingFrame =
        [| 0xff; 5; 15; 8; 10; 5; 16; 0xff
           0xff; 8; 10; 15; 12; 5; 16; 0xff |]

    /// Frame index for a heading byte (object record +17, 0..15).
    let frameForHeading (heading: int) : int option =
        match headingFrame.[heading &&& 0x0f] with
        | 0xff -> None
        | f -> Some f

    /// Decode frame `index` from the raw sheet (assets/sprites/sheet_raw.bin).
    /// Ports $11f82's row layout: [AND-mask, plane0, plane1, plane2, plane3],
    /// mask/plane bytes are read as the high byte of a byte-wide row (8px);
    /// a pixel is opaque where the mask bit is 0, and its 4-bit palette index
    /// is plane0..plane3's bit at that column (msb-first, matching the
    /// $11fe4..$12034 rol.w decode).
    let decodeFrame (sheet: byte[]) (index: int) : Frame =
        let baseOff = index * FrameStride
        let pixels = Array.create (FrameWidth * FrameHeight) -1
        for row in 0 .. FrameHeight - 1 do
            let o = baseOff + row * 5
            let mask = sheet.[o]
            let p0 = sheet.[o + 1]
            let p1 = sheet.[o + 2]
            let p2 = sheet.[o + 3]
            let p3 = sheet.[o + 4]
            for x in 0 .. FrameWidth - 1 do
                let bit = 7 - x
                if (int mask >>> bit) &&& 1 = 0 then             // opaque where mask bit is 0
                    let idx =
                        ((int p0 >>> bit) &&& 1)
                        ||| (((int p1 >>> bit) &&& 1) <<< 1)
                        ||| (((int p2 >>> bit) &&& 1) <<< 2)
                        ||| (((int p3 >>> bit) &&& 1) <<< 3)
                    pixels.[row * FrameWidth + x] <- idx
        { Pixels = pixels }
