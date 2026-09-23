namespace PmLogic

/// Rain and snow: a pattern ORed over the finished iso frame.
///
/// $1ad74 starts a spell of weather when ([$4bb4a] + [$57fec]) & $a0 == $a0:
/// [$4bb42] := word[$1ad9c + word[$57fd0]] (`kindForSeason`) and
/// [$4bb44] := that sum & $3f + $20 ticks. While [$4bb42] is non-zero,
/// $1ad2a draws it with $1a856 (D0 = 16 groups, D1 = $c2 rows, D2 = 4) and
/// counts [$4bb44] down; below 0 the spell ends. While a spell lasts, $3fb0
/// takes $10 off a group's D3 figure, and winter takes 8 more.
///
/// $1a856 draws into the compose buffer from row 6, x 64 (raw x 0 here),
/// 16 word-groups by 194 rows. Each call adds $40 to the byte at $1aac8
/// (`phase`, 4 frames of animation); row r reads the long at
/// table[(phase - 4r) & $ff], using its low word on even groups and its
/// high word on odd ones. Rain ORs the word into all four planes (colour
/// 15); snow ORs planes 0 and 2 and clears 1 and 3 (colour 5).
module Weather =

    /// word[$1ad9c + word[$57fd0]]: 0 none, 1 rain, 2 snow, by season 0..3.
    let kindForSeason (season: int) = [| 2; 1; 0; 1 |].[season &&& 3]

    /// Row 6 of the screen, 194 rows, 16 groups of 16 px from raw x 0.
    [<Literal>]
    let FirstRow = 6

    [<Literal>]
    let Rows = 0xC2

    /// Draw one frame of weather over `buf`. `tables` = the rain table
    /// ($1a8a4, 256 bytes) followed by the snow table ($1a9c8, 256 bytes);
    /// `phase` = the byte $1a856 draws with (the stored [$1aac8] + $40).
    let draw (buf: Fill.Buffer) (tables: byte[]) (kind: int) (phase: int) =
        if kind = 1 || kind = 2 then
            let t = if kind = 2 then 256 else 0
            let colour = if kind = 2 then 5uy else 15uy
            for r in 0 .. Rows - 1 do
                let i = t + ((phase - 4 * r) &&& 0xFF)
                let word k = (int tables.[i + k] <<< 8) ||| int tables.[i + k + 1]
                let hi, lo = word 0, word 2
                for g in 0 .. 15 do
                    let w = if g % 2 = 0 then lo else hi
                    for b in 0 .. 15 do
                        if (w >>> (15 - b)) &&& 1 = 1 then buf.Set(g * 16 + b, FirstRow + r, colour)
