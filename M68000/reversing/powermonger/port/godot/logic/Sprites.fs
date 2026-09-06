namespace PmLogic

/// The $11f82 mini-sprite path (assets/sprites/sheet_raw.bin). See ../../SPEC.md
/// section 6 and assets/sprites/sprite_triggers.json.
///
/// 87th: the iso-terrain entities are drawn by $115e0 (pm_draw_cell_entities),
/// called INLINE per cell from the grid-walk handler, right after that cell's
/// triangles, far->near — so painter's order is free and Fill.fs's walk hands
/// off here per cell. ($16738->$e6ee is a different path: the $165b2
/// selected-group marker + HUD glyphs, NOT the terrain men.)
///
/// Ported here: the frame decode ($11f82), the men frame formula ($11c8a), and
/// the sub-cell position lerp ($11f1a). Still open (88th): per-category frame
/// counts, cats 1/8/9/10/11/13/15, the $37c7c cat-2 sheet, the compositing +
/// byte-exact cross-check against pm_render_ref.py.
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
    /// draw nothing for this facing. 87th: this table is read by $16738, which
    /// is the $e6ee marker/HUD path — NOT the iso terrain entities. Kept for
    /// that path; the terrain men use `frameForMan` below.
    let headingFrame =
        [| 0xff; 5; 15; 8; 10; 5; 16; 0xff
           0xff; 8; 10; 15; 12; 5; 16; 0xff |]

    /// Frame index for a heading byte (object record +17, 0..15) — $e6ee path.
    let frameForHeading (heading: int) : int option =
        match headingFrame.[heading &&& 0x0f] with
        | 0xff -> None
        | f -> Some f

    /// Men (category 0) frame index — $11c8a, camera-yaw-relative facing.
    /// faction = record[5] (1..4, blocks of 16), heading = record[17],
    /// yaw = [$ff9a] (0..0xf0). `armed` => the +0x40 variant (trigger bit not
    /// yet pinned, 88th); `anim` = [$4bb41] & 1 (walk frame). Base sheet $33000,
    /// 55 bytes/frame. Excludes the melee/dying mode branches (record[31] in
    /// {0x32,0x34,0x06,0x46}).
    let frameForMan (faction: int) (heading: int) (yaw: int) (armed: bool) (anim: bool) : int =
        let facing = ((heading + yaw + 0x10) &&& 0xff) >>> 5      // 0..7
        (faction - 1) * 16 + facing * 2
        + (if armed then 0x40 else 0)
        + (if anim then 1 else 0)

    /// Animals (category 4) — $11a86. heading = record[14], yaw-relative,
    /// 16 frames at base 0x117.
    let frameForAnimal (heading: int) (yaw: int) (anim: bool) : int =
        0x117 + (((heading + yaw) &&& 0xff) >>> 5) * 2 + (if anim then 1 else 0)

    /// Sub-cell screen position ($11f1a): bilinear lerp of the cell's four
    /// projected corners by the entity's sub-cell fraction, then the sprite
    /// anchor offset. `corner` = (screenX, screenY) for C00/C10/C01/C11 (the
    /// 2x2 corner block, from Projection's grid — same layout Fill.fs uses).
    /// fx = record[8] &&& 0xff, fy = record[10] &&& 0xff.
    ///
    /// NOT byte-exact-verified yet (88th): the 68k does `muls.w` + `asr.w #8`
    /// on 16-bit halves, so large corner deltas can word-overflow and the
    /// rounding is floor (toward -inf), not toward zero. `>>> 8` here matches
    /// the floor; the word-truncation case still needs the cross-check.
    let entityScreenPos
            (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
            (fx: int) (fy: int) : int * int =
        let lerp (a: int) (b: int) (t: int) = a + (((b - a) * t) >>> 8)   // asr #8 = floor div 256
        let lx (a: int * int) (b: int * int) t = lerp (fst a) (fst b) t, lerp (snd a) (snd b) t
        let top = lx c00 c10 fx
        let bot = lx c01 c11 fx
        let x, y = lerp (fst top) (fst bot) fy, lerp (snd top) (snd bot) fy
        x + 0x3c, y - 8

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
