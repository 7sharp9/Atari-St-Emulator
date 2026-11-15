// dotnet fsi wraps.fsx <gatedir>   Which of mid's 68000 behaviours shape the island: each removed in turn, the finest
// level (2,560,000 cells) compared with Island.levels (gated against the game). terrain.md section 1.
#load "Heritage.fsx" "Island.fsx"
open Island
let ram = Heritage.loadRam (System.IO.Path.Combine(fsi.CommandLineArgs.[1], "gen_in.snap"))
let base0 = readGrid ram Heritage.Addr.file372 50
let eager = levels base0 |> List.toArray

// The same mid with each 68000-ism switchable: wrapH (height sum to 16 bits), carry (seed carry into height),
// wrapR (roughness to 16 bits), wrapD (displacement to 16 bits), wrapN (noise taken as a signed 16-bit word).
// Heights are kept as int inside; the result is stored back as int16 (checked for overflow below).
let mutable overflow = 0
let midV (wrapH, carry, wrapR, wrapD, wrapN) shift (a: Cell) (b: Cell) (c: Cell) (d: Cell) : Cell =
    let seeds = int a.Seed + int b.Seed + int c.Seed + int d.Seed
    let height = int a.Height + int b.Height + int c.Height + int d.Height + (if carry then seeds >>> 16 else 0)
    let avg = (if wrapH then int (int16 height) else height) >>> 2
    let noise = (if wrapN then int (int16 seeds) else seeds &&& 0xffff) >>> shift
    let roughness = if wrapR then int (int16 (avg * 8 + 5000)) else avg * 8 + 5000
    let displacement = if wrapD then int (int16 ((noise * roughness) >>> 16)) else (noise * roughness) >>> 16
    let h = avg + displacement
    if h < -32768 || h > 32767 then overflow <- overflow + 1
    { Height = int16 h; Seed = uint16 ((seeds ^^^ int a.Seed) &&& 0x3fff) }

let refineV v shift (g: Grid) =
    let n = Array2D.length1 g
    let s r c = if r >= 0 && r < n && c >= 0 && c < n then g.[r, c] else Cell.outside
    let m = midV v shift
    let centres = Array2D.init (n + 1) (n + 1) (fun r c -> let r, c = r - 1, c - 1 in m (s r c) (s r (c + 1)) (s (r + 1) c) (s (r + 1) (c + 1)))
    let centre r c = centres.[r + 1, c + 1]
    Array2D.init (2 * n) (2 * n) (fun y x ->
        let r, c = y / 2, x / 2
        match y % 2, x % 2 with
        | 0, 0 -> s r c
        | 0, _ -> m (centre r c) (centre (r - 1) c) (s r c) (s r (c + 1))
        | _, 1 -> centre r c
        | _ -> m (centre r (c - 1)) (centre r c) (s r c) (s (r + 1) c))

let run name v =
    overflow <- 0
    let g5 = List.fold (fun g sh -> refineV v sh g) base0 shifts
    let e = eager.[5]
    let n = Array2D.length1 e
    let mutable diff, maxd = 0, 0
    for y in 0 .. n - 1 do
        for x in 0 .. n - 1 do
            let d = abs (int e.[y, x].Height - int g5.[y, x].Height)
            if d > 0 || e.[y, x].Seed <> g5.[y, x].Seed then diff <- diff + 1
            maxd <- max maxd d
    printfn "%-34s level 5: %8d of %d cells differ, max height change %5d, int16 overflows %d" name diff (n * n) maxd overflow

let all = (true, true, true, true, true)
run "all 68000 behaviours (control)" all
run "no 16-bit wrap on the height sum" (false, true, true, true, true)
run "no seed carry into the height" (true, false, true, true, true)
run "no 16-bit wrap on roughness" (true, true, false, true, true)
run "no 16-bit wrap on displacement" (true, true, true, false, true)
run "noise unsigned, not a signed word" (true, true, true, true, false)
run "plain int everywhere (carry kept)" (false, true, false, false, true)
