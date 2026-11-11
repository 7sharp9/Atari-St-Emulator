// Midwinter's terrain generator and grid post-passes in F# (reversing/midwinter/terrain.md).
// A port of py/terrain/terrain_gen.py, gated against the game's own snapshots.
//
//   dotnet fsi terrain.fsx gate <gatedir>             generator over 7 targets + post-passes
//   dotnet fsi terrain.fsx gate <gatedir> --break     negative control: drop the seed XOR from mid
//
// <gatedir> is what py/terrain/gate_terrain.py writes ($MIDWINTER_WORK/terrain/gate/): gen_in.snap
// (the CPU at $19962), the game's grid after $19962 returns for each target (gen_out.snap for the
// natural ski entry, t_<x>_<y>.snap for poked targets), and post_in/post_out around the post-passes.
//
// The model runs on a copy of the snapshot's RAM, not on clean arrays, because the game's grid edges
// read stale scratch memory (terrain.md section 2): the border cells come out right only that way.

open System
open System.IO

// ---- snapshot RAM (same layout as tools/gfxview.py load_ram) --------------------------------------

let loadRam (path: string) : byte[] =
    let d = File.ReadAllBytes path
    if d.[0..3] <> "A68S"B then failwithf "%s: not a snapshot" path
    let regCount = if d.[4] >= 5uy then 19 else 18
    let off = 5 + regCount * 4 + 2
    let len = BitConverter.ToInt32(d, off)
    d.[off + 4 .. off + 3 + len]

/// Big-endian 68000 memory over a byte array.
type Mem(b: byte[]) =
    member _.Bytes = b
    member _.L(a: int) = (uint32 b.[a] <<< 24) ||| (uint32 b.[a + 1] <<< 16) ||| (uint32 b.[a + 2] <<< 8) ||| uint32 b.[a + 3]
    member _.W(a: int) = (int b.[a] <<< 8) ||| int b.[a + 1]
    member _.SetL(a: int, v: uint32) =
        b.[a] <- byte (v >>> 24); b.[a + 1] <- byte (v >>> 16); b.[a + 2] <- byte (v >>> 8); b.[a + 3] <- byte v
    member _.SetW(a: int, v: int) = b.[a] <- byte (v >>> 8); b.[a + 1] <- byte v

let s16 (v: int) = int (int16 (v &&& 0xffff))

// ---- addresses (terrain.md section 1) ------------------------------------------------------------

let GRID, GRID_END = 0x404c4, 0x4a104          // the 100 x 100 working grid
let FILE372 = 0x4a104                            // file 37.2, the 50 x 50 island
let SCR66, WIN = 0x66000, 0x60000                // edge rows; the window copied out before each zoom
let P_SRC, P_DST, P_BUF_A, P_BUF_B, P_SHIFT = 0x2c352, 0x23060, 0x23064, 0x23068, 0x2305e
let LVL, ORG_X, ORG_Y, TGT_X, TGT_Y, OFF_X, OFF_Y = 0x19cd8, 0x19cda, 0x19cdc, 0x19cd4, 0x19cd6, 0x19cde, 0x19ce0
let A6 = 0x2c376

// ---- the generator ------------------------------------------------------------------------------

let mutable seedXor = true                       // false only for the negative control

/// $285a: a new cell (height.w, seed.w) from four parent cells. No random numbers: the seed is a hash
/// of the parents, and the displacement is the seed sum scaled by height and halved per level.
let mid (shift: int) (p1: uint32) (p2: uint32) (p3: uint32) (p4: uint32) : uint32 =
    let s = p1 + p2 + p3 + p4                                     // 32-bit: a seed carry reaches the height
    let seed = if seedXor then ((s ^^^ p1) &&& 0x3fffu) else (s &&& 0x3fffu)
    let avg = s16 (int (s >>> 16)) >>> 2                          // mean of the four heights
    let rough = s16 ((avg <<< 3) + 5000)                          // higher ground is rougher
    let noise = s16 (int s) >>> min shift 31                      // the seed sum, halved per level
    let disp = s16 ((noise * rough) >>> 16)
    (uint32 ((avg + disp) &&& 0xffff) <<< 16) ||| seed

let run285a (m: Mem) a1 a2 a3 a4 a5 =
    let shift = m.W P_SHIFT
    for i in 0 .. 48 do
        m.SetL(a5 + 4 * i, mid shift (m.L(a1 + 4 * i)) (m.L(a2 + 4 * i)) (m.L(a3 + 4 * i)) (m.L(a4 + 4 * i)))

/// $2ca6: one source row S (and the row below it, S') -> two output rows of 100 cells.
let row2ca6 (m: Mem) =
    let src, bufa, bufb = int (m.L P_SRC), int (m.L P_BUF_A), int (m.L P_BUF_B)
    let mutable dst = int (m.L P_DST)
    run285a m src (src + 4) (src + 200) (src + 204) bufa              // centres  C
    run285a m bufa bufb src (src + 4) SCR66                           // row edges H
    run285a m bufa (bufa + 4) (src + 4) (src + 204) (SCR66 + 0x194)   // column edges V
    for i in 0 .. 49 do                                               // S0 H0 S1 H1 ...
        m.SetL(dst, m.L(src + 4 * i)); m.SetL(dst + 4, m.L(SCR66 + 4 * i)); dst <- dst + 8
    for i in 0 .. 49 do                                               // V-1 C0 V0 C1 ...
        m.SetL(dst, m.L(SCR66 + 0x190 + 4 * i)); m.SetL(dst + 4, m.L(bufa + 4 * i)); dst <- dst + 8
    m.SetL(P_SRC, uint32 (src + 200))
    m.SetL(P_BUF_A, uint32 bufb)
    m.SetL(P_BUF_B, uint32 bufa)
    m.SetL(P_DST, uint32 dst)

/// $1999a / $2c60: a 50 x 50 grid at src -> the 100 x 100 working grid.
let subdivide (m: Mem) (src: int) =
    for a in SCR66 .. 4 .. SCR66 + 202 * 8 - 1 do m.SetL(a, 0xffffffffu)
    m.SetL(P_SRC, uint32 src)
    m.SetL(P_DST, uint32 GRID)
    for _ in 1 .. 50 do row2ca6 m

/// $2c20: copy the 50 x 50 window at (12(A6), 14(A6)) out of the working grid. The offset is not
/// clamped: near the island's edge it reads outside the grid.
let window2c20 (m: Mem) =
    let d0 = uint32 (m.W(A6 + 14) * 0x190)
    let d1 = int ((uint32 ((m.W(A6 + 12) * 4) &&& 0xffff) + d0) &&& 0xffffu)
    let mutable a0 = GRID + s16 d1
    let mutable out = WIN
    for _ in 1 .. 50 do
        for c in 0 .. 49 do m.SetL(out, m.L(a0 + 4 * c)); out <- out + 4
        a0 <- a0 + 0x190

/// $199ec: zoom one level towards the target and subdivide again at half the noise.
let zoom199ec (m: Mem) =
    let lvl = m.W LVL
    let dx = s16 (s16 (m.W TGT_X - m.W ORG_X) >>> lvl) - 25
    let dy = s16 (s16 (m.W TGT_Y - m.W ORG_Y) >>> lvl) - 25
    m.SetW(OFF_X, dx); m.SetW(OFF_Y, dy)
    m.SetW(ORG_X, m.W ORG_X + (dx <<< lvl)); m.SetW(ORG_Y, m.W ORG_Y + (dy <<< lvl))
    m.SetW(LVL, lvl - 1)
    m.SetW(A6 + 12, m.W OFF_X); m.SetW(A6 + 14, m.W OFF_Y)
    window2c20 m
    subdivide m WIN
    m.SetW(P_SHIFT, m.W P_SHIFT + 1)

/// $19962: the whole island once, then four zooms to the 100 x 100 finest cells around the target.
let generate (m: Mem) =
    m.SetW(LVL, 4); m.SetW(ORG_X, 0); m.SetW(ORG_Y, 0); m.SetW(P_SHIFT, 4)
    subdivide m FILE372
    for _ in 1 .. 4 do zoom199ec m

// ---- post-passes (terrain.md section 4) -----------------------------------------------------------

/// $1991a: generator units -> render heights; low ground is stretched, the seed word cleared.
let heights1991a (m: Mem) =
    for a in GRID .. 4 .. GRID_END - 4 do
        let h = s16 (m.W a)
        let h' = if h < 0 then 0 elif h <= 9 then (h + 1) * 24 else h + 250
        m.SetL(a, uint32 (h' &&& 0xffff) <<< 16)

/// $1d1d2: each object in the table at $70010 levels the quad it stands on.
let pads1d1d2 (m: Mem) =
    let n = s16 (m.W 0x1d418)
    let coord (v: uint32) = int (((v >>> 2) &&& 0xffffu) >>> 7)
    for k in 0 .. n do
        let obj = 0x70010 + 16 * k
        let x, y = coord (m.L obj), coord (m.L(obj + 4))
        let row = (-(s16 y - 0x63)) &&& 0xffff
        let d0 = s16 (x + ((row * 0x64) &&& 0xffff))
        let a0 = int ((m.L 0x12ce2 + uint32 (4 * d0)) &&& 0xffffffffu)
        let h = m.W a0
        for off in [ -400; 4; -396 ] do m.SetW(a0 + off, h)

/// $198d8: the game's exact floor square root, transcribed register for register.
let isqrt198d8 (x: uint32) : uint32 =
    let mutable d1, d2, d3, d4 = 0u, x, 0u, 0
    if d2 >= 4u then
        let mutable go = true
        while go do
            for _ in 1 .. 2 do
                let c = d2 &&& 1u
                d2 <- d2 >>> 1
                d3 <- (d3 >>> 1) ||| (c <<< 31)
            d4 <- (d4 + 1) &&& 0xffff
            go <- d2 >= 4u
    let mutable first, go = true, true
    while go do
        if not first then
            for _ in 1 .. 2 do
                let c = d3 >>> 31
                d3 <- d3 <<< 1
                d2 <- (d2 <<< 1) ||| c
        first <- false
        d1 <- d1 <<< 1
        if d1 < d2 then
            d1 <- d1 + 2u
            d2 <- d2 - d1 + 1u
        d4 <- (d4 - 1) &&& 0xffff
        go <- d4 <> 0xffff
    d1 >>> 1

/// $1988e: one triangle's shade from its corner height and two edge differences; L = $12c84.
let shade1988e (m: Mem) (t: int) (dx: int) (dy: int) : byte =
    if (t ||| dx ||| dy) &&& 0xffff = 0 then 24uy
    else
        let l = s16 (m.W 0x12c84)
        let dx, dy = s16 dx, s16 dy
        let d6 = s16 (2 * l + 3 * dy)
        let root = s16 (int (isqrt198d8 (uint32 (dx * dx + dy * dy + l * l))))
        let q =
            if root = 0 then d6
            else
                let q = (d6 <<< 3) / root                            // divs: truncates toward 0
                if q < -0x8000 || q > 0x7fff then d6 else q            // overflow leaves D6
        let q = max (s16 q) 0 + 2
        byte (if q >= 24 then 23 else q)

/// $197ec: two triangles per cell, the diagonal alternating with (row + col + $157a8).
let shading197ec (m: Mem) =
    let b = m.Bytes
    let base', par = int (m.L 0x12ce2), m.W 0x157a8
    let h a = m.W a
    for i in 0 .. 9999 do
        let a = base' + 4 * i
        let row, col = i / 100, i % 100
        if (row + col + par) &&& 1 = 1 then
            let t = h (a - 400)
            b.[a + 2] <- shade1988e m t (t - h (a - 396)) (t - h a)
            let t = h (a + 4)
            b.[a + 3] <- shade1988e m t (-(t - h a)) (-(t - h (a - 396)))
        else
            let t = h (a - 396)
            b.[a + 2] <- shade1988e m t (-(t - h (a - 400))) (t - h (a + 4))
            let t = h a
            b.[a + 3] <- shade1988e m t (t - h (a + 4)) (-(t - h (a - 400)))

// ---- gate ----------------------------------------------------------------------------------------

let compare (label: string) (model: byte[]) (game: byte[]) =
    let cells = (GRID_END - GRID) / 4
    let bad = [ for k in 0 .. cells - 1 do
                  let a = GRID + 4 * k
                  if model.[a .. a + 3] <> game.[a .. a + 3] then yield k ]
    printfn "%-16s %d/%d cells match" label (cells - bad.Length) cells
    for k in List.truncate 5 bad do
        let a = GRID + 4 * k
        printfn "    row %d col %d: model %s game %s" (k / 100) (k % 100)
            (Convert.ToHexString model.[a .. a + 3]) (Convert.ToHexString game.[a .. a + 3])
    cells - bad.Length, cells

let gate (dir: string) =
    let snap n = Path.Combine(dir, n + ".snap")
    let entry = loadRam (snap "gen_in")
    let targets =
        [ (368, 1176), "gen_out"                                      // the natural ski entry
          for x, y in [ 800, 800; 400, 1200; 1200, 300; 100, 100; 1500, 1500; 1000, 600 ] do
              (x, y), sprintf "t_%d_%d" x y ]
    let sw = Diagnostics.Stopwatch.StartNew()
    let gen =
        [ for (x, y), name in targets do
              let m = Mem(Array.copy entry)
              m.SetW(TGT_X, x); m.SetW(TGT_Y, y)
              generate m
              yield compare (sprintf "target %d,%d" x y) m.Bytes (loadRam (snap name)) ]
    let ok, total = List.sumBy fst gen, List.sumBy snd gen
    printfn "generator: %d/%d cells over %d targets" ok total gen.Length
    let m = Mem(loadRam (snap "post_in"))
    heights1991a m; pads1d1d2 m; shading197ec m
    let pok, ptotal = compare "post-passes" m.Bytes (loadRam (snap "post_out"))
    printfn "elapsed %d ms" sw.ElapsedMilliseconds
    if ok = total && pok = ptotal then 0 else 1

// ---- "the same place always gets the same hills" ------------------------------------------------

/// Generate around each target and key every final cell by its world position (ORG + col, ORG + row,
/// in finest cells). Where two grids overlap, compare heights. `margin` drops the grid's outer cells,
/// which read stale scratch memory (terrain.md section 2).
let consistency (dir: string) (targets: (int * int) list) (margin: int) =
    let entry = loadRam (Path.Combine(dir, "gen_in.snap"))
    let seen = Collections.Generic.Dictionary<int * int, int * (int * int)>()
    let mutable same, differ, firstBad = 0, 0, []
    for (x, y) in targets do
        let m = Mem(Array.copy entry)
        m.SetW(TGT_X, x); m.SetW(TGT_Y, y)
        generate m
        let ox, oy = s16 (m.W ORG_X), s16 (m.W ORG_Y)
        for row in margin .. 99 - margin do
            for col in margin .. 99 - margin do
                let h = s16 (m.W(GRID + 4 * (row * 100 + col)))
                let key = (ox + col, oy + row)
                match seen.TryGetValue key with
                | true, (h0, t0) ->
                    if h0 = h then same <- same + 1
                    else
                        differ <- differ + 1
                        if firstBad.Length < 5 then firstBad <- (key, t0, (x, y), h0, h) :: firstBad
                | _ -> seen.[key] <- (h, (x, y))
    printfn "margin %d: %d targets, %d overlapping cell pairs agree, %d differ (%d distinct world cells)"
        margin targets.Length same differ seen.Count
    for (k, t0, t1, h0, h1) in List.rev firstBad do
        printfn "    world %A: target %A gave %d, target %A gave %d" k t0 h0 t1 h1

match fsi.CommandLineArgs |> Array.toList |> List.tail with
| [ "same"; dir ] ->
    let rnd = Random(1)
    let near = [ for _ in 1 .. 40 -> 800 + rnd.Next(-60, 61), 800 + rnd.Next(-60, 61) ]
    let wide = [ for _ in 1 .. 40 -> rnd.Next(200, 1400), rnd.Next(200, 1400) ]
    for m in [ 0; 1; 2; 4; 8 ] do consistency dir near m
    for m in [ 0; 1; 2; 8 ] do consistency dir wide m
    exit 0
| [ "gate"; dir ] -> exit (gate dir)
| [ "gate"; dir; "--break" ] -> seedXor <- false; exit (gate dir)
| _ -> eprintfn "usage: dotnet fsi terrain.fsx gate <gatedir> [--break]"; exit 2
