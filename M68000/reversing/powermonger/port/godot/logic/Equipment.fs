namespace PmLogic

/// The equipment exchange: what a man does with his lord's weapons and
/// ploughs when he reaches the settlement in mode $8e (a fight won, `$160e4`)
/// or $90 (`$160f2`, after the `$3c08` regroup), and the goods-driven regroup
/// `$16892` that sends him there.
///
/// A line-for-line port of tools/pm_fsm_ref.py `call_160f8`, `call_160e4`,
/// `call_160f2` and `call_16892` (137th pass), which equal the real 68000 on
/// 201 states (385/385 changed bytes, D0.w/D1.w 201/201). It works on a flat
/// RAM image at the game's own absolute addresses, because the original's bug
/// below writes to an address that depends on the lord's index.
///
/// The tail `$160f8`, with A0 = the lord's record (`$4e514 + 32 * lord`):
///   1. A man carrying a weapon (byte 44 = 2 pike, 4 sword, 6 bow) hands it
///      back: `goods[(b44 - 2) >> 1] += 1`, byte 44 := 0.
///   2. He takes the first weapon in stock, trying bow (goods[2]), sword
///      (goods[1]), pike (goods[0]): `goods[k] -= 1`, byte 44 := 2 * (k + 1).
///   3. A farmer (byte 7 bit 0) takes a plough (goods[3]) when one is in
///      stock, first handing back the item in byte 33; byte 33 := 8.
///
/// The original's bug: the 68000 code builds the goods index in D0.w with
/// `move.b 44(A1),D0` (and `move.b 33(A1),D0`), which leaves D0's high byte
/// as it was. After `move.w 14(settlement),D0` that is the high byte of the
/// lord's byte offset, `lord >> 3`, so for a lord numbered 8 or more the
/// returned item is credited `128 * (lord >> 3)` bytes past the lord's goods
/// (into another lord's record or beyond) and the lord's own count is never
/// restored. The farmer's return reuses whatever D0 holds: right after a take
/// (D0 = 2 * (k + 1)), wrong with no take and no weapon return.
/// `Original` reproduces it; `Corrected` clears the high byte, so the item
/// goes to the man's own lord. Lords 0..7 are identical in both modes.
module Equipment =

    /// Which behaviour of the returned-item credit to run.
    type CreditMode =
        /// The shipped game: the stale D0 high byte misdirects the credit for lord >= 8.
        | Original
        /// The credit always goes to the man's own lord.
        | Corrected

    [<Literal>]
    let Leaders = 0x4e514

    /// 18-byte settlement records; word +14 is the home lord's byte offset in `Leaders`.
    [<Literal>]
    let Settlements = 0x4f916

    [<Literal>]
    let private AddressMask = 0xfffff

    let inline private s16 (v: int) = int (int16 v)
    let inline private bu (ram: byte[]) (a: int) = int ram.[a &&& AddressMask]
    let inline private wu (ram: byte[]) (a: int) = (bu ram a <<< 8) ||| bu ram (a + 1)
    let inline private wb (ram: byte[]) (a: int) (v: int) = ram.[a &&& AddressMask] <- byte v
    let inline private addB (ram: byte[]) (a: int) (delta: int) = wb ram a (bu ram a + delta)

    /// `$160f8`. `a1` = the man's 50-byte record. Returns the 68000's final
    /// (D0.w, D1.w); the iterator continues with them, the port need not.
    let tail (mode: CreditMode) (ram: byte[]) (a1: int) : struct (int * int) =
        let lordOff = wu ram (Settlements + s16 (wu ram (a1 + 34)) + 14)
        let a0 = Leaders + s16 lordOff
        // `move.b X,D0` keeps D0's high byte (the stale part); Corrected drops it
        let withByte (d0: int) (b: int) =
            (match mode with Original -> d0 &&& 0xff00 | Corrected -> 0) ||| b
        // `subi.w #2,D0 ; lsr.w #1,D0 ; addi.b #1,24(A0,D0.w)` (D0.w sign-extended as the index)
        let credit (d0: int) =
            let d0 = (((d0 - 2) &&& 0xffff) >>> 1)
            addB ram (a0 + 24 + s16 d0) 1
            d0
        let mutable d0 = withByte lordOff (bu ram (a1 + 44))
        if bu ram (a1 + 44) <> 0 then
            d0 <- credit d0
            wb ram (a1 + 44) 0
        // take the first weapon in stock: bow, sword, pike
        let mutable d1 = 2
        let mutable searching = true
        while searching do
            if bu ram (a0 + 24 + d1) <> 0 then
                addB ram (a0 + 24 + d1) (-1)
                d0 <- 2 * (d1 + 1)
                wb ram (a1 + 44) d0
                searching <- false
            else
                d1 <- (d1 - 1) &&& 0xffff
                if d1 = 0xffff then searching <- false
        // a farmer takes a plough if the lord has one
        if (bu ram (a1 + 7) &&& 1) <> 0 && bu ram (a0 + 27) <> 0 then
            d0 <- withByte d0 (bu ram (a1 + 33))
            if bu ram (a1 + 33) <> 0 then d0 <- credit d0
            addB ram (a0 + 27) (-1)
            wb ram (a1 + 33) 8
        struct (d0 &&& 0xffff, d1 &&& 0xffff)

    /// `$160e4`: arrival in mode $8e. Both mode bytes := $2c, then the tail.
    let arriveFight (mode: CreditMode) (ram: byte[]) (a1: int) =
        wb ram (a1 + 31) 0x2c
        wb ram (a1 + 30) 0x2c
        tail mode ram a1

    /// `$160f2`: arrival in mode $90. `regroup` is `$3c08` (the flag-driven
    /// regroup that sets the walk home, not ported here), run first, then the tail.
    let arriveGoods (mode: CreditMode) (regroup: byte[] -> int -> unit) (ram: byte[]) (a1: int) =
        regroup ram a1
        tail mode ram a1

    /// `$16892`: the goods-driven regroup. `d2` is the caller's mode byte
    /// ($90 from `$157d2`, $8e from `$4f82`). When the lord has any bow, sword,
    /// pike or plough in stock (goods[3..0]) the man is sent to the lord's
    /// cell with mode `d2` and true is returned; otherwise nothing is written.
    let goodsRegroup (ram: byte[]) (a1: int) (d2: int) : bool =
        let a0 = Leaders + s16 (wu ram (Settlements + s16 (wu ram (a1 + 34)) + 14))
        if [ 0 .. 3 ] |> List.exists (fun k -> bu ram (a0 + 24 + k) <> 0) then
            let cell = wu ram (a0 + 4)
            wb ram (a1 + 30) d2
            wb ram (a1 + 31) 0x10
            wb ram (a1 + 20) (cell &&& 0x3f)
            wb ram (a1 + 21) 0x80
            let y = (((cell &&& 0x1fc0) <<< 2) + 0x80) &&& 0xffff
            wb ram (a1 + 22) (y >>> 8)
            wb ram (a1 + 23) y
            true
        else false
