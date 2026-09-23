// 121st: the season check of pm119/season_check.fsx on later lands built in
// other seasons: Season.fading(mission-1 dither.bin, word[$57fd0]/2, steps)
// must equal the RAM's whole $2e000 table.
#r "../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System.IO
let dith = File.ReadAllBytes(System.IO.Path.Combine(__SOURCE_DIRECTORY__, "../port/assets/dither.bin"))
let w16 (r: byte[]) a = (int r.[a] <<< 8) ||| int r.[a + 1]
let stepsTo target =
    if target = 0 then 0
    else
        let mutable x, n = Season.nextLcg 0, 1
        while x <> target do x <- Season.nextLcg x; n <- n + 1
        n
for cap in fsi.CommandLineArgs |> Array.skip 1 do
    let r = File.ReadAllBytes cap
    let season, steps, ticks = w16 r 0x57fd0 / 2, stepsTo (w16 r 0x57ff6), w16 r 0x57fec
    let t = Season.fading dith season steps
    let bad = Seq.sum (seq { for i in 0 .. 0x3fff -> if t.[i] <> r.[0x2e000 + i] then 1 else 0 })
    let settled = Seq.sum (seq { let s = Season.table dith season in for i in 0 .. 0x3fff -> if s.[i] <> r.[0x2e000 + i] then 1 else 0 })
    printfn "  settled table: %d bytes differ" settled
    printfn "%-12s season %d  tree offset %d (RAM word[$11746+s] %d)  steps %4d (16*$57fec = %4d)  fading: %d bytes differ"
        (Path.GetFileNameWithoutExtension cap) season (Season.treeTileOffset season) (w16 r (0x11746 + 2 * season)) steps (16 * ticks) bad
