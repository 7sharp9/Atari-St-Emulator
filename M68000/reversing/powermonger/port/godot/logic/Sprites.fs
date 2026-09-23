namespace PmLogic

/// PowerMonger's iso-view sprites: what $115e0 (pm_draw_cell_entities) draws
/// for one cell, straight after the cell's two terrain triangles. See
/// ../../SPEC.md section 6 and assets/sprites/sprite_triggers.json.
///
/// Records. Each cell has a word in the $47970 bucket array (index
/// (cellY*64 + cellX)*2); a non-zero head is a SIGNED offset from $51b66, so
/// records live below $51b66 as well as above, and word 0 of each record is
/// the (signed) offset of the next one in the cell. Record byte 6 is the
/// category, an even value 0..44, dispatched through the jump tables at
/// $1162e (prepare: position and frame) and $1165c (blit).
///
/// Ported categories and their frames:
///   0      man                 ($11c8a) facing is camera-relative, +$40 armed;
///                              melee frames; plough / siege-engine overlays
///   2      settlement building ($117d8) frame record[7]
///   4      building / tree     ($1168c) record[7] + the season's tile offset
///   6, 24  settlement marker   ($117b0) record[7] + $100
///   8      animal              ($11a86) facing is camera-relative
///   14     banner / group      ($11bf4) record[5] + $13e
///   26     faction marker      ($1174e) record[5] + $149, bobbing a pixel
///   28     marker              $14e/$14f (blinking) or $150
///   12     dead man            ($11bbc) body + the figure rising from it
///   16     leader's base       ($1192e) building frame 7 + the leader's goods
///   20     carrier pigeon      ($11b3c) shadow + bird at record[15] height
///   22     bird of a flock     ($11b2a) as 20
///   44     dropped goods pile  ($1184e) the goods icons
///   10     dropped equipment   ($11772) what a dead man carried
///   30     building going up   ($1198a) frame $0c, rising as word[8] counts down
///   40     projectile          ($11c64) one colour-0 pixel
///
/// Positions come from the cell's four projected corners ($3f364): a bilinear
/// lerp at a sub-cell fraction ($11f1a) or the cell centroid ($1182a). Men,
/// animals and banners take the fraction from record[9]/[11]; buildings and
/// trees derive it from the record, bucket-slot and corner ADDRESSES
/// (`propJitter`), so it depends on the cell's place in the camera window and
/// is worked out per frame (`recordJitter`).
///
/// Sheets: men, animals, banners and markers are 8x11 frames at $33000
/// ($11f82). Buildings and trees go through $12244, which picks one of three
/// copies of the same art by the zoom index [$57ffc]: 32x32 at $3af1c
/// (zoom 1-3), 32x24 at $37c7c (zoom 4-5), 16x16 at $312a0 (zoom 6-7).
///
/// $e6ee (byte6 40, and byte6 20/22 with record[14] != 0) plots ONE pixel
/// (`movep.l` into the four planes), not a glyph.
///
/// Not ported: byte6 == 2 with record[7] == $0a (its $119b2 overlay), the
/// $312a0 category 18 (projectiles), and the per-category frame counts.
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
    /// draw nothing for this facing. Read by $16738, the $e6ee marker/HUD
    /// path, not by the iso terrain entities; the terrain men use
    /// `frameForMan` below.
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
    /// yaw = [$ff9a] (0..0xf0). `armed` => the +0x40 variant (see `entityFrame`
    /// for its trigger); `anim` = [$4bb41] & 1 (walk frame). Base sheet $33000,
    /// 55 bytes/frame. Excludes the melee/dying mode branches (record[31] in
    /// {0x32,0x34,0x06,0x46}).
    let frameForMan (faction: int) (heading: int) (yaw: int) (armed: bool) (anim: bool) : int =
        let facing = ((heading + yaw + 0x10) &&& 0xff) >>> 5      // 0..7
        (faction - 1) * 16 + facing * 2
        + (if armed then 0x40 else 0)
        + (if anim then 1 else 0)

    /// Animals / sheep (byte6 == 8) — $11a86. heading = record[14],
    /// yaw-relative, 16 frames at base 0x117. Base $33000.
    let frameForAnimal (heading: int) (yaw: int) (anim: bool) : int =
        0x117 + (((heading + yaw) &&& 0xff) >>> 5) * 2 + (if anim then 1 else 0)

    /// Building / tree (byte6 == 4) — $1168c. `r7` = record[7]; `tileOff` =
    /// word[$11746 + word[$57fd0]] (Season.treeTileOffset). Returns -1 for
    /// "frame >= 27", past the end of the 27-frame sheets. Live-verified (D2 at $12288).
    let frameForProp (r7: int) (tileOff: int) : int =
        let f =
            if r7 = 0x0D then 0x0D
            elif (r7 &&& 0x7F) = 0x0E then 0x0E
            else (r7 &&& 0x7F) + tileOff
        if f < 27 then f else -1

    /// Settlement / territory marker (byte6 == 24, and byte6 == 6) — $117b0.
    /// frame = record[7] + 0x100 (+ [$57fec]&3 if the result is 0x112, a
    /// 4-frame anim). Sheet $33000 8x11, CENTROID-positioned ($1182a).
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

    /// Banner / flag / marching-group member (byte6 == 14) — $11bf4:
    /// frame = record[5] + 0x13e (faction-indexed). Base $33000. Every member
    /// of pm78_settle's 26-record group has record[5] == 1 => frame 0x13f,
    /// live-verified at $11f82 entry.
    let frameForBanner (faction: int) : int =
        (faction &&& 0xff) + 0x13e

    /// Sub-cell screen position ($11f1a): bilinear lerp of the cell's four
    /// projected corners by the entity's sub-cell fraction, then the sprite
    /// anchor offset. `corner` = (screenX, screenY) for C00/C10/C01/C11 (the
    /// 2x2 corner block, from Projection's grid — same layout Fill.fs uses).
    /// $11f12 does `move.w 8(A3),D6; andi.w #$ff,D6`, i.e. fx is the LOW byte
    /// of the big-endian word at record+8 == record[9], and fy == record[11].
    ///
    /// Not byte-exact-verified: the 68k does `muls.w` + `asr.w #8`
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

    /// Decode a word-plane frame ($3af1c 32x32 / $37c7c 32x24 / $312a0 16x16).
    /// Rows of `w / 16` groups of five big-endian words [mask, p0, p1, p2, p3];
    /// opaque where the mask bit is 0 (matches $12326/$124a8's `and.w mask` +
    /// `or.w plane`). `frameStride` = 640, 480 or 160. Verified byte-exact
    /// against $24400's live byte6 == 4 tree pixels (32x24).
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

    /// Raw bilinear lerp of the four projected corners by the sub-cell
    /// fraction (fx, fy) -- $11f1a WITHOUT the sprite anchor offset, word for
    /// word. The corners are packed (x << 16) | y and subtracted as longs, so
    /// a borrow out of the low half leaks into the high half: y into x for
    /// the two edge deltas, then x into y for the final delta, because the
    /// edge points are built swapped ((y << 16) | x). Each step is `muls`
    /// with only the low word kept, then `asr.w #8` (floor).
    let packedLerp
            (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
            (fx: int) (fy: int) : int * int =
        let pack (x, y) = (uint32 (x &&& 0xFFFF) <<< 16) ||| uint32 (y &&& 0xFFFF)
        let hi (v: uint32) = int (int16 (v >>> 16))
        let lo (v: uint32) = int (int16 (v &&& 0xFFFFu))
        let step (d: int) (t: int) = int (int16 ((d * t) &&& 0xFFFF)) >>> 8   // muls, asr.w #8
        let w (v: int) = v &&& 0xFFFF
        // one edge: a + (b - a) * t, returned swapped as (y << 16) | x
        let edge (a: uint32) (b: uint32) (t: int) =
            let d = b - a
            let y = w (lo a + step (lo d) t)
            let x = w (hi a + step (hi d) t)
            (uint32 y <<< 16) ||| uint32 x
        let top = edge (pack c00) (pack c10) fx
        let bot = edge (pack c01) (pack c11) fx
        let d = bot - top
        lo (uint32 (w (lo top + step (lo d) fy))), lo (uint32 (w (hi top + step (hi d) fy)))

    // -- the per-cell entity pass -----------------------------------------
    // Blit top-left corners, from the lerp point (px, py) or the centroid
    // (cx, cy) of the cell's corners, at zoom 4-5:
    //   byte6 0/8/14  (8x11)  : (px - 4,  py - 8)
    //   byte6 6/24    (8x11)  : (cx - 8,  cy - 8)
    //   byte6 4       (32x24) : (px - 8,  py - 16), (px, py) at the address jitter
    //   byte6 2       (32x24) : (cx - 12, cy - 16)
    // These hold in any space where the corners and the result agree: the port
    // uses raw $3f364 corners and a raw buffer (the +64 HUD inset is added at
    // display), pm_render_ref.py +64-inset corners and screen pixels.

    /// One object record, only the fields the drawn categories read.
    type EntityRec =
        { Addr: int                 // record address: byte6 == 4 records derive their sub-cell jitter from it
          B6: int; B5: int; B7: int; B14: int; B17: int; B31: int
          Fx: int; Fy: int          // record[9] / record[11]
          Group: int
          Wcx: int; Wcy: int        // world cell
          B15: int                  // byte6 20/22: flight height (signed)
          B32: int                  // byte6 12: rising figure's flap phase 0..3
          W18: int                  // byte6 12: word[18], counts $a0 -> 0 after the kill
          Icons: int                // byte6 16/44: bit e = draw $11886 entry e (see goodsIcon)
          B33: int; B44: int }      // byte6 10: the dead man's equipment codes

    /// The byte6 == 4 sub-cell jitter for a record drawn in the cell at
    /// (row, col) of the camera window: $1168c's A2 is the cell's $47970
    /// bucket slot, A3 the record, A0 the cell's corner in $3f364 (row stride
    /// 64 bytes, 4 per corner). It depends on the camera, so it is worked out
    /// per frame, not stored.
    let recordJitter (row: int) (col: int) (r: EntityRec) : int * int =
        propJitter (0x47970 + (r.Wcy * 64 + r.Wcx) * 2) r.Addr (0x3F364 + row * 64 + col * 4)

    /// Per-frame constants shared by every record.
    type EntityCtx =
        { Yaw: int; Anim: bool; SelGroup: int; TileOff: int; RotPhase: int
          Zoom: int                 // [$57ffc], 1..7: picks the building/tree sheet
          Sheet33: byte[]           // $33000, 8x11
          SheetProp: byte[]         // $37c7c, 32x24 (zoom 4-5)
          SheetProp32: byte[]       // $3af1c, 32x32 (zoom 1-3)
          SheetProp16: byte[]       // $312a0, 16x16 (zoom 6-7)
          Ram: byte[] }             // for the men $51538 group-word probe; may be [||]

    /// One of $12244's three building/tree sheets: frame size, bytes per
    /// frame, and the offset it adds to the anchor before blitting.
    type PropSheet = { W: int; H: int; Stride: int; Dx: int; Dy: int }

    /// $12244: pick the building/tree sheet by the zoom index [$57ffc].
    ///   <= 3 : $3af1c 32x32, anchor (-8, -16)   ($12294)
    ///   4, 5 : $37c7c 32x24, anchor (-4, -8)    ($12272)
    ///   >= 6 : $312a0 16x16, anchor unchanged   ($12258)
    let propSheet (ctx: EntityCtx) : PropSheet * byte[] =
        if ctx.Zoom <= 3 then { W = 32; H = 32; Stride = 640; Dx = -8; Dy = -16 }, ctx.SheetProp32
        elif ctx.Zoom <= 5 then { W = 32; H = 24; Stride = 480; Dx = -4; Dy = -8 }, ctx.SheetProp
        else { W = 16; H = 16; Stride = 160; Dx = 0; Dy = 0 }, ctx.SheetProp16

    /// (isProp, frameIndex) for a record, or None if it draws nothing / is a
    /// category not ported. The same formulas as pm_render_ref._entity_frame.
    let entityFrame (ctx: EntityCtx) (r: EntityRec) : (bool * int) option =
        let anim = if ctx.Anim then 1 else 0
        match r.B6 with
        | 0 ->
            if r.B31 = 0x32 || r.B31 = 0x34 || r.B7 &&& 0x20 <> 0 then None   // placeEntity draws these
            else
                let facing = ((r.B17 + ctx.Yaw + 0x10) &&& 0xFF) >>> 5
                let mutable f = (r.B5 - 1) * 16 + facing * 2
                let bit4 = (r.B7 >>> 4) &&& 1
                let bit7 = (r.B7 >>> 7) &&& 1
                let mutable grp = 0
                if bit7 = 1 && ctx.Ram.Length > 0 then
                    let ga = 0x51538 + r.Group - 48
                    if ga >= 0 && ga + 1 < ctx.Ram.Length then
                        grp <- (int ctx.Ram.[ga] <<< 8) ||| int ctx.Ram.[ga + 1]
                if bit4 = 1 && (bit7 = 0 || grp = ctx.SelGroup) then f <- f + 0x40
                Some(false, f + anim)
        | 8 -> Some(false, 0x117 + (((r.B14 + ctx.Yaw) &&& 0xFF) >>> 5) * 2 + anim)
        | 6 | 24 ->
            let mutable f = r.B7 + 0x100
            if f = 0x112 then f <- f + (ctx.RotPhase &&& 3)
            Some(false, f)
        | 14 -> Some(false, (r.B5 &&& 0xFF) + 0x13E)
        | 26 -> Some(false, (r.B5 &&& 0xFF) + 0x149)             // the anim bit moves it, see placeEntity
        | 28 -> Some(false, (if r.B5 > 0 then 0x14E + (ctx.RotPhase &&& 1) else 0x150))
        | 2 ->
            // settlement building ($117d8): frame record[7] from the 32x24
            // $37c7c sheet, no tile-set offset. record[7] == $0a also draws an
            // overlay via $119b2 (from record[12]/[16]) -- not ported.
            if r.B7 <> 0x0A && r.B7 < 27 then Some(true, r.B7) else None
        | 4 ->
            match frameForProp r.B7 ctx.TileOff with
            | -1 -> None
            | f -> Some(true, f)
        // both $115e0 dispatch passes send byte6 32 to $1168a, a bare rts:
        // the game draws nothing for it (seen on later lands, not mission 1)
        | 32 -> None
        | _ -> None

    /// The sheet a blit reads.
    type Sheet =
        | Mini          // $33000 8x11 ($11f82)
        | Prop          // $12244's building/tree sheet for the zoom (propSheet)
        | Struct16      // $312a0 16x16 ($1225c), at every zoom
        | Dot           // $e6ee: one pixel, Frame = its colour

    /// The goods table at $11886: nine entries, each an offset from the
    /// anchor's blit corner and a frame, laid out as a 3x3 block 2 px apart
    /// (entry 8 in the middle). byte6 44 (`$1184e`, a dropped goods pile)
    /// draws entry e when word[record + 10 + 2e] is non-zero; byte6 16
    /// (`$1192e`, a leader's base) draws entry i+1 when the leader's goods
    /// byte i ($4e514 + word[record+14] + 24 + i) is non-zero. Entries 7 and
    /// 8 are 16x16 $312a0 frames ($12258), the rest 8x11 $33000 frames.
    let goodsIcon =
        [| -2, -2, Mini, 0x116
           0, -2, Mini, 0x143
           2, -2, Mini, 0x144
           -2, 0, Mini, 0x145
           2, 0, Mini, 0x109
           -2, 2, Mini, 0x110
           0, 2, Mini, 0x146
           2, 2, Struct16, 0x1B
           0, 0, Struct16, 0x23 |]

    /// $11e40 / $11e50 / $11e60: a man carrying a plough (record[33] == 8,
    /// record[7] == 1) gets frame carryFrame[k] at carryOffset[k] from his
    /// blit corner, k = his frame & 7 (0, 2, 4 or 6), drawn before him.
    let carryOffset = [| 0, -4; 6, -2; 8, 0; 6, 2; 0, 4; -6, 2; -8, 0; -6, -2 |]
    let carryFrame = [| 0x109; 0x10A; 0x10B; 0x10C; 0x10D; 0x10E; 0x10F; 0x110 |]

    /// $11ebc: a man hauling a siege engine (record[44] >= $e: $e catapult,
    /// $10 cannon) gets the 16x16 $312a0 frame $1b + (record[44] - $e) * 4 + k
    /// at siegeOffset[k] from his blit corner, drawn before him ($12258).
    let siegeOffset = [| 0, -4; 6, -2; 8, 0; 6, 2; 0, 4; -6, 2; -8, 0; -6, -2 |]

    /// Where one entity is drawn: its frame, the anchor point the game
    /// computes from the cell's corners, the rule that picked that anchor,
    /// and the frame's top-left and size.
    type Placement =
        { Sheet: Sheet
          Frame: int
          Skip: int             // rows cut off the top of the frame (byte6 30); Y is the first drawn row
          AnchorX: int; AnchorY: int
          Rule: string
          X: int; Y: int        // blit top-left
          W: int; H: int }

    /// Place one entity on its cell's four projected corners (result in the
    /// corners' space, see above): the frames it draws, in draw order, or []
    /// if its category draws nothing or is not ported. (row, col) is the
    /// cell's place in the camera window, which the byte6 == 4
    /// (building/tree) jitter depends on.
    ///   men / animals / banners : sub-cell lerp at record (fx, fy) ($11f1a), then (-4, -8)
    ///   markers (6/24)          : cell centroid ($1182a), then (-8, -8)
    ///   buildings / trees (4)   : sub-cell lerp at the address jitter ($1168c), then
    ///                             (-4, -8) and propSheet's offset
    ///   settlement building (2) : cell centroid ($117d8 -> $1182a), then (-8, -8)
    ///                             and propSheet's offset
    ///   dead man (12)           : sub-cell lerp; body, then the figure lifted $a0 - word[18]
    ///   pigeon / flock (20, 22) : sub-cell lerp; shadow, then the bird lifted record[15]
    ///   leader's base (16)      : centroid; building frame 7, then the goods icons
    ///   goods pile (44)         : centroid; the goods icons
    ///   dropped equipment (10)  : sub-cell lerp; record[33] then record[44] frames
    /// Every blitter puts the frame's top-left at (D0 - 64, D1) of the
    /// handler's D0/D1: raw (lx - 4, ly - 8) after $11f1a, (cx - 8, cy - 8)
    /// after $1182a.
    let placeEntity (ctx: EntityCtx)
                    (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
                    (row: int) (col: int) (r: EntityRec) : Placement list =
        let centroid () =
            (fst c00 + fst c10 + fst c01 + fst c11) >>> 2, (snd c00 + snd c10 + snd c01 + snd c11) >>> 2
        let dot colour ax ay rule x y =
            { Sheet = Dot; Frame = colour; Skip = 0; AnchorX = ax; AnchorY = ay; Rule = rule
              X = x; Y = y; W = 1; H = 1 }
        let mini fi ax ay rule x y =
            { Sheet = Mini; Frame = fi; Skip = 0; AnchorX = ax; AnchorY = ay; Rule = rule
              X = x; Y = y; W = FrameWidth; H = FrameHeight }
        // a $11886 goods icon at blit corner (x, y)
        let icon ax ay rule x y e =
            let dx, dy, sheet, fi = goodsIcon.[e]
            let w = if sheet = Struct16 then 16 else FrameWidth
            let h = if sheet = Struct16 then 16 else FrameHeight
            { Sheet = sheet; Frame = fi; Skip = 0; AnchorX = ax; AnchorY = ay; Rule = rule
              X = x + dx; Y = y + dy; W = w; H = h }
        let icons first ax ay rule x y =
            [ for e in 0 .. 8 do if (r.Icons >>> e) &&& 1 = 1 && e >= first then yield icon ax ay rule x y e ]
        match r.B6 with
        | 0 when r.B7 &&& 0x20 = 0 ->
            // $11c8a. Melee ($32/$34): base $80 + weapon * 8 + (side - 1) * 4,
            // + 1 on tick parity ($57fec & 1; with weapon 6 only when byte 18
            // is $14), + 2 when facing away (2 facings), + $40 if flags bit 4.
            // Otherwise (side - 1) * 16 + facing * 2 (8 facings), + $40 armed,
            // + [$4bb41] & 1. Both draw the siege engine first; the walk
            // frame also a plough.
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            let rule = "sub-cell lerp at record (fx, fy) ($11c8a)"
            let x0, y0 = lx - 4, ly - 8
            let siege k =
                let dx, dy = siegeOffset.[k]
                { Sheet = Struct16; Frame = 0x1B + ((r.B44 - 0x0E) <<< 2) + k; Skip = 0
                  AnchorX = lx; AnchorY = ly; Rule = rule; X = x0 + dx; Y = y0 + dy; W = 16; H = 16 }
            let bit4 = r.B7 &&& 0x10 <> 0
            if r.B31 = 0x32 || r.B31 = 0x34 then
                let weapon = if r.B44 >= 0x0E then 0 else r.B44
                let mutable f = (weapon <<< 3) + ((r.B5 - 1) <<< 2) + 0x80
                if r.B44 = 6 then (if (r.W18 >>> 8) = 0x14 then f <- f + 1)
                else f <- f + (ctx.RotPhase &&& 1)
                f <- f + ((((r.B17 + ctx.Yaw + 0x40) &&& 0xFF) >>> 7) <<< 1)
                if bit4 then f <- f + 0x40
                [ if r.B44 >= 0x0E then yield siege ((r.B44 &&& 0x0F) >>> 1)
                  yield mini f lx ly rule x0 y0 ]
            else
                let f0 = (r.B5 - 1) * 16 + ((((r.B17 + ctx.Yaw + 0x10) &&& 0xFF) >>> 5) <<< 1)
                let f = match entityFrame ctx r with Some(_, f) -> f | None -> f0
                [ if r.B33 = 8 && r.B7 = 1 then
                      let k = f0 &&& 7
                      let dx, dy = carryOffset.[k]
                      yield mini carryFrame.[k] lx ly rule (x0 + dx) (y0 + dy)
                  if r.B44 >= 0x0E then yield siege ((f0 &&& 0x0F) >>> 1)
                  yield mini f lx ly rule x0 y0 ]
        | 0 | 26 ->
            // $1174e (byte6 26, and a man with flags bit 5): frame
            // $149 + record[5]; [$4bb41] & 1 moves it down a pixel
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            [ mini (0x149 + (r.B5 &&& 0xFF)) lx ly "sub-cell lerp at record (fx, fy) ($1174e)"
                   (lx - 4) (ly - 8 + (if ctx.Anim then 1 else 0)) ]
        | 12 ->
            // $11bbc: body $103 + (-record[5] & $ff) (the $5590 kill negated
            // record[5], so it is the dead man's side), then the figure
            // $100 + record[32] raised by $a0 - word[18]: 1 px a frame as
            // $1623c counts word[18] down
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            let rule = "sub-cell lerp at record (fx, fy) ($11f1a)"
            [ mini (0x103 + ((-r.B5) &&& 0xFF)) lx ly rule (lx - 4) (ly - 8)
              mini (0x100 + r.B32) lx ly rule (lx - 4) (ly - 8 - (0xA0 - r.W18)) ]
        | 20 | 22 ->
            // $11b3c / $11b2a: a colour-5 dot record[14] px above the ground
            // if record[14] != 0 ($e6ee; sub.b on the low byte of D1), the
            // shadow $148 on the ground, then (record at $4c112 only) $151 and
            // the 8-frame bird ($127 + tick & 7), raised by record[15]
            // (signed, + $30 if negative)
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            let rule = "sub-cell lerp at record (fx, fy) ($11f1a)"
            let h = let s = int (sbyte (byte r.B15)) in if s < 0 then s + 0x30 else s
            [ if r.B14 <> 0 then
                  let y = ((ly - 8) &&& 0xFF00) ||| (((ly - 8) - r.B14) &&& 0xFF)
                  yield dot 5 lx ly rule (lx - 4) y
              yield mini 0x148 lx ly rule (lx - 4) (ly - 8)
              if r.Addr = 0x4C112 then yield mini 0x151 lx ly rule (lx - 4) (ly - 8 - h)
              yield mini (0x127 + (ctx.RotPhase &&& 7)) lx ly rule (lx - 4) (ly - 8 - h) ]
        | 16 ->
            // $1192e: building frame 7 through $12244, then goods slot i as
            // $11886 entry i + 1
            let cx, cy = centroid ()
            let rule = "cell centroid ($1192e -> $1182a)"
            let sheet, _ = propSheet ctx
            { Sheet = Prop; Frame = 7; Skip = 0; AnchorX = cx; AnchorY = cy; Rule = rule
              X = cx - 8 + sheet.Dx; Y = cy - 8 + sheet.Dy; W = sheet.W; H = sheet.H }
            :: icons 1 cx cy rule (cx - 8) (cy - 8)
        | 10 ->
            // $11772: $10f + (record[33] - 8) >> 1 (lsr.w on the word), then
            // $142 + record[44] >> 1, each only if its byte is non-zero
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            let rule = "sub-cell lerp at record (fx, fy) ($11f1a)"
            [ if r.B33 <> 0 then yield mini (0x10F + (((r.B33 - 8) &&& 0xFFFF) >>> 1)) lx ly rule (lx - 4) (ly - 8)
              if r.B44 <> 0 then yield mini (0x142 + (r.B44 >>> 1)) lx ly rule (lx - 4) (ly - 8) ]
        | 40 ->
            // $11c64: a projectile ($57f0) is one colour-0 pixel ($e6ee)
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            [ dot 0 lx ly "sub-cell lerp at record (fx, fy) ($11c64 -> $11f1a)" (lx - 4) (ly - 8) ]
        | 30 ->
            // $1198a: building frame $0c at the centroid, its top rows cut
            // off while word[8] (set to $10 by $5e3a) counts down: word[8]
            // rows at zoom 6-7, word[8] * 3 / 2 at 4-5, 2 * word[8] at 1-3,
            // so the building rises out of the ground as it is built
            let cx, cy = centroid ()
            let sheet, _ = propSheet ctx
            let d6 = r.Fx                                  // word[8]; its high byte is 0 ($10 down)
            let skip = if ctx.Zoom <= 3 then 2 * d6 elif ctx.Zoom <= 5 then (d6 * 3) >>> 1 else d6
            if skip >= sheet.H then []
            else
                [ { Sheet = Prop; Frame = 0x0C; Skip = skip; AnchorX = cx; AnchorY = cy
                    Rule = "cell centroid ($1198a), rows cut off by word[8]"
                    X = cx - 8 + sheet.Dx; Y = cy - 8 + sheet.Dy + skip; W = sheet.W; H = sheet.H - skip } ]
        | 44 ->
            let cx, cy = centroid ()
            icons 0 cx cy "cell centroid ($1184e -> $1182a)" (cx - 8) (cy - 8)
        | _ ->
        match entityFrame ctx r with
        | None -> []
        | Some(true, fi) ->
            let sheet, _ = propSheet ctx
            // $1182a adds (+$38, -8) to the raw centroid and $11f1a (+$3c, -8)
            // to the raw lerp point: (-8, -8) and (-4, -8) once the +64 HUD
            // inset is taken off. $12244 then adds the sheet's own offset.
            let ax, ay, bx, rule =
                if r.B6 = 2 then
                    let cx, cy = centroid ()
                    cx, cy, cx - 8, "cell centroid ($117d8 -> $1182a)"
                else
                    let fx4, fy4 = recordJitter row col r
                    let px, py = packedLerp c00 c10 c01 c11 fx4 fy4
                    px, py, px - 4, "sub-cell lerp at the address jitter ($1168c)"
            [ { Sheet = Prop; Frame = fi; Skip = 0; AnchorX = ax; AnchorY = ay; Rule = rule
                X = bx + sheet.Dx; Y = ay - 8 + sheet.Dy; W = sheet.W; H = sheet.H } ]
        | Some(false, fi) when r.B6 = 6 || r.B6 = 24 ->
            let cx, cy = centroid ()
            [ mini fi cx cy "cell centroid ($1182a)" (cx - 8) (cy - 8) ]
        | Some(false, fi) ->
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            [ mini fi lx ly "sub-cell lerp at record (fx, fy) ($11f1a)" (lx - 4) (ly - 8) ]

    /// True if the record's category draws anything (Scene.steps skips the rest).
    let draws (ctx: EntityCtx) (r: EntityRec) =
        match r.B6 with
        | 0 | 12 | 16 | 20 | 22 | 26 | 30 | 40 -> true
        | 44 -> r.Icons <> 0
        | 10 -> r.B33 <> 0 || r.B44 <> 0
        | _ -> (entityFrame ctx r).IsSome

    /// Blit one entity over `buf`, given its cell's four projected corners
    /// and its (row, col) in the camera window.
    let blitEntity (buf: Fill.Buffer) (ctx: EntityCtx)
                   (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
                   (row: int) (col: int) (r: EntityRec) =
        for p in placeEntity ctx c00 c10 c01 c11 row col r do
            let pixels =
                match p.Sheet with
                | Mini when (p.Frame + 1) * FrameStride > ctx.Sheet33.Length -> [||]   // past the sheet: draw nothing
                | Mini -> (decodeFrame ctx.Sheet33 p.Frame).Pixels
                | Prop ->
                    let sheet, bytes = propSheet ctx
                    let pix, _, _ = decodeFrameWord bytes p.Frame sheet.W sheet.H sheet.Stride
                    pix
                | Struct16 ->
                    let pix, _, _ = decodeFrameWord ctx.SheetProp16 p.Frame 16 16 160
                    pix
                | Dot -> [| p.Frame |]
            for dy in 0 .. p.H - 1 do
                let yy = p.Y + dy
                if yy >= 0 && yy < Fill.ScreenHeight then
                    for dx in 0 .. p.W - 1 do
                        let i = (dy + p.Skip) * p.W + dx
                        if i < pixels.Length && pixels.[i] >= 0 then buf.Set(p.X + dx, yy, byte pixels.[i])

    /// Replay $115e0 as a post-terrain far->near pass in fixed q3 (planQ3) cell
    /// order. Kept for the pm_render_ref.py cross-check; the game draws each
    /// cell's sprites inline, right after its triangles (Scene.render).
    /// `corners` = Projection.projectGrid's [gr, gc] array (2*Half+1 square);
    /// `recs` are the records already bucketed to their world cell. Cross-check
    /// target: pm_render_ref.py draw_entities.
    let drawEntities (buf: Fill.Buffer) (ctx: EntityCtx) (corners: Projection.Corner[,])
                     (camX: int) (camY: int) (recs: EntityRec list) =
        let byCell = System.Collections.Generic.Dictionary<int * int, ResizeArray<EntityRec>>()
        for r in recs do
            match byCell.TryGetValue((r.Wcx, r.Wcy)) with
            | true, l -> l.Add r
            | _ -> let l = ResizeArray<EntityRec>() in l.Add r; byCell.[(r.Wcx, r.Wcy)] <- l
        let corner (gr: int) (gc: int) =
            let c = corners.[gr, gc]
            int (System.Math.Round c.X), int (System.Math.Round c.Y)
        let n = Fill.cellsPerSide corners
        for k in 0 .. n - 1 do
            let col = n - 1 - k
            for j in 0 .. n - 1 do
                let row = j
                match byCell.TryGetValue((camX + col, camY + row)) with
                | true, l ->
                    let c00 = corner row col
                    let c10 = corner row (col + 1)
                    let c01 = corner (row + 1) col
                    let c11 = corner (row + 1) (col + 1)
                    for r in l do blitEntity buf ctx c00 c10 c01 c11 row col r
                | _ -> ()

    /// C#-friendly wrapper: same as `drawEntities` but takes an array (the
    /// Godot port builds a `Sprites.EntityRec[]` from entities.json's
    /// `render_entities` block — see game/TerrainView.cs).
    let drawEntitiesArr (buf: Fill.Buffer) (ctx: EntityCtx) (corners: Projection.Corner[,])
                        (camX: int) (camY: int) (recs: EntityRec[]) =
        drawEntities buf ctx corners camX camY (List.ofArray recs)
