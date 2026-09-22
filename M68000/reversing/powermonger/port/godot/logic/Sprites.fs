namespace PmLogic

/// PowerMonger's iso-view sprites: what $115e0 (pm_draw_cell_entities) draws
/// for one cell, straight after the cell's two terrain triangles. See
/// ../../SPEC.md section 6 and assets/sprites/sprite_triggers.json.
///
/// Records. Each cell has a word in the $47970 bucket array (index
/// (cellY*64 + cellX)*2); a non-zero head is a SIGNED offset from $51b66, so
/// records live below $51b66 as well as above, and word 0 of each record is
/// the (signed) offset of the next one in the cell. Record byte 6 is the
/// category, an even value 0..30, dispatched through the jump tables at
/// $1162e (prepare: position and frame) and $1165c (blit).
///
/// Ported categories and their frames:
///   0      man                 ($11c8a) facing is camera-relative, +$40 armed
///   2      settlement building ($117d8) frame record[7]
///   4      building / tree     ($1168c) record[7] + the season's tile offset
///   6, 24  settlement marker   ($117b0) record[7] + $100
///   8      animal              ($11a86) facing is camera-relative
///   14     banner / group      ($11bf4) record[5] + $13e
///   26     faction marker      record[5] + $149
///   28     marker              $14e/$14f (blinking) or $150
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
/// Not ported: the byte6 == 16 goods icons ($1192e), byte6 == 2 with
/// record[7] == $0a (its $119b2 overlay), and the per-category frame counts.
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
    /// fraction (fx, fy) — $11f1a WITHOUT the sprite anchor offset. Matches
    /// pm_render_ref._packed_lerp (floor `>>> 8`, done on each axis).
    let packedLerp
            (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
            (fx: int) (fy: int) : int * int =
        let lerp (a: int) (b: int) (t: int) = a + (((b - a) * t) >>> 8)
        let lx (a: int * int) (b: int * int) t = lerp (fst a) (fst b) t, lerp (snd a) (snd b) t
        let top = lx c00 c10 fx
        let bot = lx c01 c11 fx
        lerp (fst top) (fst bot) fy, lerp (snd top) (snd bot) fy

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
          Wcx: int; Wcy: int }      // world cell

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
            if r.B31 = 0x32 || r.B31 = 0x34 then None
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
        | 26 -> Some(false, (r.B5 &&& 0xFF) + 0x149 + anim)
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
        | _ -> None

    /// Where one entity is drawn: its frame, the anchor point the game
    /// computes from the cell's corners, the rule that picked that anchor,
    /// and the frame's top-left and size.
    type Placement =
        { IsProp: bool          // a building/tree sheet (propSheet), else $33000 8x11
          Frame: int
          AnchorX: int; AnchorY: int
          Rule: string
          X: int; Y: int        // blit top-left
          W: int; H: int }

    /// Place one entity on its cell's four projected corners (result in the
    /// corners' space, see above), or None if its category draws nothing or
    /// is not ported. (row, col) is the cell's place in the camera window,
    /// which the byte6 == 4 (building/tree) jitter depends on.
    ///   men / animals / banners : sub-cell lerp at record (fx, fy) ($11f1a), then (-4, -8)
    ///   markers (6/24)          : cell centroid ($1182a), then (-8, -8)
    ///   buildings / trees (4)   : sub-cell lerp at the address jitter ($1168c), then
    ///                             (-4, -8) and propSheet's offset
    ///   settlement building (2) : cell centroid ($117d8 -> $1182a), then (-8, -8)
    ///                             and propSheet's offset
    let placeEntity (ctx: EntityCtx)
                    (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
                    (row: int) (col: int) (r: EntityRec) : Placement option =
        match entityFrame ctx r with
        | None -> None
        | Some(true, fi) ->
            let sheet, _ = propSheet ctx
            // $1182a adds (+$38, -8) to the raw centroid and $11f1a (+$3c, -8)
            // to the raw lerp point: (-8, -8) and (-4, -8) once the +64 HUD
            // inset is taken off. $12244 then adds the sheet's own offset.
            let ax, ay, bx, rule =
                if r.B6 = 2 then
                    let cx = (fst c00 + fst c10 + fst c01 + fst c11) >>> 2
                    let cy = (snd c00 + snd c10 + snd c01 + snd c11) >>> 2
                    cx, cy, cx - 8, "cell centroid ($117d8 -> $1182a)"
                else
                    let fx4, fy4 = recordJitter row col r
                    let px, py = packedLerp c00 c10 c01 c11 fx4 fy4
                    px, py, px - 4, "sub-cell lerp at the address jitter ($1168c)"
            Some { IsProp = true; Frame = fi; AnchorX = ax; AnchorY = ay; Rule = rule
                   X = bx + sheet.Dx; Y = ay - 8 + sheet.Dy; W = sheet.W; H = sheet.H }
        | Some(false, fi) when r.B6 = 6 || r.B6 = 24 ->
            let cx = (fst c00 + fst c10 + fst c01 + fst c11) >>> 2
            let cy = (snd c00 + snd c10 + snd c01 + snd c11) >>> 2
            Some { IsProp = false; Frame = fi; AnchorX = cx; AnchorY = cy
                   Rule = "cell centroid ($1182a)"
                   X = cx - 8; Y = cy - 8; W = FrameWidth; H = FrameHeight }
        | Some(false, fi) ->
            let lx, ly = packedLerp c00 c10 c01 c11 r.Fx r.Fy
            Some { IsProp = false; Frame = fi; AnchorX = lx; AnchorY = ly
                   Rule = "sub-cell lerp at record (fx, fy) ($11f1a)"
                   X = lx - 4; Y = ly - 8; W = FrameWidth; H = FrameHeight }

    /// Blit one entity over `buf`, given its cell's four projected corners
    /// and its (row, col) in the camera window.
    let blitEntity (buf: Fill.Buffer) (ctx: EntityCtx)
                   (c00: int * int) (c10: int * int) (c01: int * int) (c11: int * int)
                   (row: int) (col: int) (r: EntityRec) =
        match placeEntity ctx c00 c10 c01 c11 row col r with
        | None -> ()
        | Some p ->
            let pixels =
                if p.IsProp then
                    let sheet, bytes = propSheet ctx
                    let pix, _, _ = decodeFrameWord bytes p.Frame sheet.W sheet.H sheet.Stride
                    pix
                else (decodeFrame ctx.Sheet33 p.Frame).Pixels
            for dy in 0 .. p.H - 1 do
                let yy = p.Y + dy
                if yy >= 0 && yy < Fill.ScreenHeight then
                    for dx in 0 .. p.W - 1 do
                        let v = pixels.[dy * p.W + dx]
                        if v >= 0 then buf.Set(p.X + dx, yy, byte v)

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
