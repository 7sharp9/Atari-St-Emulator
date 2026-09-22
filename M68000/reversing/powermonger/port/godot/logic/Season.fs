namespace PmLogic

/// The seasons: the landscape's grass colours and the tree frames change
/// over game time. See ../../SPEC.md section 4, "Seasons".
///
/// word[$57fd0] holds the season as 0, 2, 4 or 6; here `season` is that
/// value / 2, so 0..3. Colour slots $1d..$2e of the pattern table
/// (18 slots x 128 bytes at $2e000 + $e80) are a working copy. The table
/// also holds three source versions of those 18 slots, and
/// word[$1aba2 + word[$57fd0]] picks one per season:
///
///   season 0  $2e000 + $2980   khaki and rock (palette 1-5), no green
///   season 1  $2e000 + $2080   green (11-13)
///   season 2  $2e000 + $1780   green mixed with brown and gold (6, 7, 9)
///   season 3  $2e000 + $2080   green again (the same source as season 1)
///
/// Everything outside the 18 live slots, the three sources included, is the
/// same in every capture, so assets/dither.bin plus a season gives the whole
/// table.
///
/// $1ab60 (world build) copies the season's source over the live slots in
/// one go. After that $1abaa, once per simulation tick, fades towards the
/// source a few pixels at a time; when the fade is done it advances the
/// season and starts the next one. The tree frames (Sprites.frameForProp)
/// follow word[$57fd0] directly, so they change the moment the season
/// advances, while the grass takes the whole fade to catch up.
module Season =

    /// Offset of the live slots ($1d..$2e) in the pattern table.
    [<Literal>]
    let LiveStart = 0xE80

    /// 18 colour slots of 128 bytes.
    [<Literal>]
    let LiveLength = 0x900

    /// word[$1aba2 + 2 * season]: where each season's source slots start.
    let sourceOffset (season: int) = [| 0x2980; 0x2080; 0x1780; 0x2080 |].[season &&& 3]

    /// word[$11746 + 2 * season]: the tree / building frame offset, added at
    /// $116c6 (in $1168c; Sprites.frameForProp's `tileOff`).
    let treeTileOffset (season: int) = [| 0; 3; 6; 9 |].[season &&& 3]

    /// $1ab60: the table with `season`'s source copied over the live slots,
    /// as world build leaves it. A completed fade ends on the same table: the
    /// one pixel a fade never copies (see `fading`) is equal in all three
    /// sources.
    let table (dith: byte[]) (season: int) : byte[] =
        let t = Array.copy dith
        Array.blit dith (sourceOffset season) t LiveStart LiveLength
        t

    /// $1abaa's 13-bit LCG ([$57ff6]). From 0 it visits all 8192 values and
    /// comes back to 0, so it visits every pixel of the fade exactly once.
    let nextLcg (x: int) = (x * 0x24A1 + 0x24DF) &&& 0x1FFF

    /// LCG steps in one fade: 8191 nonzero values; reaching 0 ends it.
    [<Literal>]
    let FadeSteps = 8191

    /// $1abaa takes 16 LCG steps per simulation tick, so a fade lasts 512
    /// ticks; [$57fec] counts them.
    [<Literal>]
    let StepsPerTick = 16

    /// The table `steps` LCG steps into the fade from season - 1 to `season`,
    /// which is what the game shows while word[$57fd0] = 2 * season, once a
    /// whole fade has run since world build. The first fade after world build
    /// starts from `table dith season` itself, so it changes nothing.
    ///
    /// Each LCG value x names one pixel: bit x & 15 of the 8-byte pattern row
    /// x >> 4. Values from $1200 up (row 288 and on, past the 18 slots) copy
    /// nothing. The pixel is copied in all four bitplanes at once, from the
    /// season's source into the live slots. x = 0 ends the fade instead of
    /// copying, so pixel 0 of row 0 only ever changes at world build.
    let fading (dith: byte[]) (season: int) (steps: int) : byte[] =
        let t = table dith ((season + 3) &&& 3)
        let src = sourceOffset season
        let mutable x = 0
        for _ in 1 .. min steps FadeSteps do
            x <- nextLcg x
            let row, bit = x >>> 4, x &&& 15
            if row < LiveLength / 8 then
                // bit `bit` of each big-endian plane word: byte 0 holds bits 15..8
                let b = row * 8 + (if bit >= 8 then 0 else 1)
                let mask = byte (1 <<< (bit &&& 7))
                for plane in 0 .. 3 do
                    let i = b + plane * 2
                    t.[LiveStart + i] <- (t.[LiveStart + i] &&& ~~~mask) ||| (dith.[src + i] &&& mask)
        t
