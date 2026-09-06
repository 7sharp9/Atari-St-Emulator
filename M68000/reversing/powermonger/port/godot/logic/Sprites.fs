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
/// 88th (live-traced pm78_settle, $115e0 / $11f88 register probes): records are
/// walked from the $47970 per-cell bucket array with a SIGNED $51b66-relative
/// offset (`adda.w D4,A3`), so scenery/animal records live BELOW $51b66 too;
/// dispatch is `word[$1162e + byte6]` with **byte6 even, 0..30** (the 87th's
/// "cat N" == byte6 / 2 — keying frame formulas on byte6 read as 0..15 was the
/// cause of both of the 87th's "blockers"). The 26-record marching group is
/// byte6 == 14 (flag/banner), every member frame 0x13f, and it IS drawn by
/// $115e0 -> $11bf4 -> $11f78 -> $11f82. Position (sub-cell lerp + $3c/-8) is
/// byte-exact against the probe.
///
/// Ported here: the frame decode ($11f82 8x11 + $12326/$124a8 32x24), the men
/// frame formula ($11c8a), the banner/group-member formula ($11bf4), the animal
/// formula ($11a86), the $37c7c building/tree formula ($1168c), the settlement
/// marker ($117b0), the sub-cell position lerp ($11f1a), and the prop
/// address-jitter.
///
/// 89th (live-traced pm88_f1, D2 at $12288 / $11ab6): byte6 == 4 (buildings /
/// trees, $37c7c 32x24 word-plane sheet) frame =
///   r7 == 0x0d            -> 0x0d                        ($116a8 special-case)
///   (r7 & 0x7f) == 0x0e   -> 0x0e                        ($116c0 special-case)
///   else                 -> (r7 & 0x7f) + word[$11746 + word[$57fd0]]
/// where word[$57fd0] is a per-mission tile-set selector (($58146 & 3) * 2,
/// even 0..6) and the table at $11746 is {0:0, 2:3, 4:6, 6:9}. Mission 1:
/// word[$57fd0] == 4 -> +6, so r7 0x11 -> frame 0x17, 0x10 -> 0x16, 0x0f ->
/// 0x15. The 32x24 decode is visually byte-exact vs $24400's live tree pixels.
/// byte6 == 8 (animal) frame = 0x117 + (((r14 + yaw) & 0xff) >> 5) * 2 [+anim]
/// (D2 0x123/0x124 observed). byte6 == 24 (settlement marker, $33000 8x11,
/// CENTROID-positioned via $1182a) frame = r7 + 0x100.
///
/// Still open: the per-category frame counts, the byte6 == 16 goods-icon loop
/// ($1192e -> $11886 table over $4e514 goods[]), and a CLEAN populated capture
/// to score byte6 == 4/8/24 compositing against (pm78_settle's two compose
/// buffers disagree on the entity layer -- $115e0 redraws a subset per frame).
/// In pm_render_ref.py only byte6 == 14 composites (94.4% -> 94.9%).
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

    /// Animals / sheep (byte6 == 8, 87th "cat 4") — $11a86. heading = record[14],
    /// yaw-relative, 16 frames at base 0x117. Base $33000. NOT composited yet.
    let frameForAnimal (heading: int) (yaw: int) (anim: bool) : int =
        0x117 + (((heading + yaw) &&& 0xff) >>> 5) * 2 + (if anim then 1 else 0)

    /// Building / tree (byte6 == 4) — $1168c. `r7` = record[7]; `tileOff` =
    /// word[$11746 + word[$57fd0]] (mission 1 = 6). Sheet $37c7c, 32x24
    /// word-plane frames, 480 bytes/frame; CENTRE-anchored via the sub-cell
    /// lerp (see `propScreenPos`). Returns -1 for "frame >= 28 / out of sheet".
    /// 89th: live-verified (D2 at $12288).
    let frameForProp (r7: int) (tileOff: int) : int =
        let f =
            if r7 = 0x0D then 0x0D
            elif (r7 &&& 0x7F) = 0x0E then 0x0E
            else (r7 &&& 0x7F) + tileOff
        if f < 28 then f else -1

    /// word[$11746 + word[$57fd0]] — the byte6 == 4 tile-set frame offset.
    /// `tileSel` = word[$57fd0] = ($58146 & 3) * 2. Table {0:0, 2:3, 4:6, 6:9}.
    let propTileOffset (tileSel: int) : int =
        [| 0; 3; 6; 9 |].[(tileSel >>> 1) &&& 3]

    /// Settlement / territory marker (byte6 == 24, and byte6 == 6) — $117b0.
    /// frame = record[7] + 0x100 (+ [$57fec]&3 if the result is 0x112, a
    /// 4-frame anim). Sheet $33000 8x11, CENTROID-positioned ($1182a). 89th.
    let frameForSettlementMarker (r7: int) (rotPhase: int) : int =
        let f = r7 + 0x100
        if f = 0x112 then f + (rotPhase &&& 3) else f

    /// byte6 == 4 sub-cell fraction: NOT a record field. $1168c derives it from
    /// the record/bucket/corner POINTER values (a deterministic per-record
    /// jitter so trees don't sit dead-centre):
    ///   a2 = $47970 + (cellY*64 + cellX)*2        ; bucket-array slot address
    ///   a3 = record address
    ///   a0 = $3f364 + row*64 + col*4              ; the cell's TL corner addr
    ///   fx = (((a2 + a3) &&& 0xffff) <<< 3) &&& 0xff       ; $11692 lsl.w #3
    ///   fy = (((a2 + a3) &&& 0xffff) + (a0 &&& 0xffff)) &&& 0xff ; $11698
    /// This is exact only for a port that replays the game's own record pool
    /// layout; a from-scratch port substitutes any deterministic scatter.
    let propJitter (bucketSlotAddr: int) (recordAddr: int) (cornerAddr: int) : int * int =
        let s = (bucketSlotAddr + recordAddr) &&& 0xFFFF
        (s <<< 3) &&& 0xFF, (s + (cornerAddr &&& 0xFFFF)) &&& 0xFF

    /// Banner / flag / marching-group member (byte6 == 14, 87th "cat 7") —
    /// $11bf4: frame = record[5] + 0x13e (faction-indexed). Base $33000.
    /// 88th: every member of pm78_settle's 26-record group has record[5] == 1
    /// => frame 0x13f, live-verified at $11f82 entry. This is the one entity
    /// category pm_render_ref.py composites today.
    let frameForBanner (faction: int) : int =
        (faction &&& 0xff) + 0x13e

    /// Sub-cell screen position ($11f1a): bilinear lerp of the cell's four
    /// projected corners by the entity's sub-cell fraction, then the sprite
    /// anchor offset. `corner` = (screenX, screenY) for C00/C10/C01/C11 (the
    /// 2x2 corner block, from Projection's grid — same layout Fill.fs uses).
    /// $11f12 does `move.w 8(A3),D6; andi.w #$ff,D6`, i.e. fx is the LOW byte
    /// of the big-endian word at record+8 == record[9], and fy == record[11].
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

    /// byte6 == 4 (building/tree) screen anchor. Same $11f1a sub-cell lerp as
    /// the men, but $12272 then applies a further (-4, -8): net raw anchor is
    /// (lerpX + 0x38, lerpY - 16). `fx`/`fy` come from `propJitter`, NOT record
    /// fields. Corners are the RAW $3f364 values (no +64 HUD inset). 89th:
    /// byte-exact vs the live D0/D1 at $12288.
    let propScreenPos
            (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
            (fx: int) (fy: int) : int * int =
        let x, y = entityScreenPos c00 c10 c01 c11 fx fy
        x - 4, y - 8

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

    /// Decode a word-plane frame ($37c7c 32x24 / $312a0 16x16). Rows of
    /// `w / 16` groups of five big-endian words [mask, p0, p1, p2, p3]; opaque
    /// where the mask bit is 0 (matches $12326/$124a8's `and.w mask` +
    /// `or.w plane`). `frameStride` = 480 for $37c7c, 160 for $312a0. 89th:
    /// verified byte-exact against $24400's live byte6 == 4 tree pixels.
    let decodeFrameWord (sheet: byte[]) (index: int) (w: int) (h: int) (frameStride: int) : int[] * int * int =
        let groups = w / 16
        let baseOff = index * frameStride
        let pixels = Array.create (w * h) -1
        if baseOff + frameStride <= sheet.Length then
            for row in 0 .. h - 1 do
                for g in 0 .. groups - 1 do
                    let o = baseOff + row * groups * 10 + g * 10
                    let rd i = (int sheet.[o + i * 2] <<< 8) ||| int sheet.[o + i * 2 + 1]
                    let mask, p0, p1, p2, p3 = rd 0, rd 1, rd 2, rd 3, rd 4
                    for b in 0 .. 15 do
                        let bit = 15 - b
                        if (mask >>> bit) &&& 1 = 0 then
                            pixels.[row * w + g * 16 + b] <-
                                ((p0 >>> bit) &&& 1)
                                ||| (((p1 >>> bit) &&& 1) <<< 1)
                                ||| (((p2 >>> bit) &&& 1) <<< 2)
                                ||| (((p3 >>> bit) &&& 1) <<< 3)
        pixels, w, h
