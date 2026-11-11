// Midwinter's terrain in F# (reversing/midwinter/terrain.md). Three layers:
//   Heritage.fsx  the 68000's memory: snapshots, big-endian cells, where the game keeps its grids
//   Island.fsx    the domain: Cell, Grid, mid, refine; the whole island as a value
//   Faithful.fsx  the proof: the game's routines transcribed on a copy of its RAM, edges and all
//   Render.fsx, Drone.fsx  pictures and a flight over the island (our look, not the game's renderer)
//
//   dotnet fsi terrain.fsx gate <gatedir> [--break]   Faithful against the game: every cell of 7 windows
//   dotnet fsi terrain.fsx domain <gatedir>           Island against the game, inside a 2-cell margin
//   dotnet fsi terrain.fsx same <gatedir>             overlapping game windows agree (terrain.md section 6)
//   dotnet fsi terrain.fsx map <gatedir> <out.png>    the whole island at the finest level, from above
//   dotnet fsi terrain.fsx zoom <gatedir> <out.png>   the five levels around the ski entry
//   dotnet fsi terrain.fsx drone <gatedir> <out.mp4> [seconds]      coast to coast
//   dotnet fsi terrain.fsx reveal <gatedir> <out.mp4> [seconds]     rise on a locked focus, then orbit
//   dotnet fsi terrain.fsx skier <gatedir> <ski.snap> <out.png>     the game's own camera and lens, 320 x 200
//
// <gatedir> is what py/terrain/gate_terrain.py writes ($MIDWINTER_WORK/terrain/gate/): gen_in.snap (the CPU
// at $19962, file 37.2 loaded), the game's grid after $19962 returns for each target (gen_out.snap for the
// natural ski entry, t_<x>_<y>.snap for poked ones), and post_in/post_out around the post-passes.

#load "Heritage.fsx" "Island.fsx" "Faithful.fsx" "Render.fsx" "Drone.fsx"

open System
open System.IO
open Island

let targets =
    [ (368, 1176), "gen_out"                                          // the natural ski entry
      for x, y in [ 800, 800; 400, 1200; 1200, 300; 100, 100; 1500, 1500; 1000, 600 ] do
          (x, y), sprintf "t_%d_%d" x y ]

/// The island from the file the game loaded, every level.
let islandFrom (dir: string) =
    let ram = Heritage.loadRam (Path.Combine(dir, "gen_in.snap"))
    levels (readGrid ram Heritage.Addr.file372 50)

// ---- gate ----------------------------------------------------------------------------------------

let compare (label: string) (model: byte[]) (game: byte[]) =
    let cells = (Faithful.GRID_END - Faithful.GRID) / 4
    let bad = [ for k in 0 .. cells - 1 do
                  let a = Faithful.GRID + 4 * k
                  if model.[a .. a + 3] <> game.[a .. a + 3] then yield k ]
    printfn "%-16s %d/%d cells match" label (cells - bad.Length) cells
    for k in List.truncate 5 bad do
        let a = Faithful.GRID + 4 * k
        printfn "    row %d col %d: model %s game %s" (k / 100) (k % 100)
            (Convert.ToHexString model.[a .. a + 3]) (Convert.ToHexString game.[a .. a + 3])
    cells - bad.Length, cells

let gate (dir: string) =
    let snap n = Path.Combine(dir, n + ".snap")
    let entry = Heritage.loadRam (snap "gen_in")
    let sw = Diagnostics.Stopwatch.StartNew()
    let gen =
        [ for (x, y), name in targets do
              let m = Faithful.Mem(Array.copy entry)
              m.SetW(Faithful.TGT_X, x); m.SetW(Faithful.TGT_Y, y)
              Faithful.generate m
              yield compare (sprintf "target %d,%d" x y) m.Bytes (Heritage.loadRam (snap name)) ]
    let ok, total = List.sumBy fst gen, List.sumBy snd gen
    printfn "generator: %d/%d cells over %d targets" ok total gen.Length
    let m = Faithful.Mem(Heritage.loadRam (snap "post_in"))
    Faithful.heights1991a m; Faithful.pads1d1d2 m; Faithful.shading197ec m
    let pok, ptotal = compare "post-passes" m.Bytes (Heritage.loadRam (snap "post_out"))
    printfn "elapsed %d ms" sw.ElapsedMilliseconds
    if ok = total && pok = ptotal then 0 else 1

// ---- "the same place always gets the same hills" ------------------------------------------------

/// Generate around each target and key every final cell by its world position (ORG + col, ORG + row,
/// in finest cells). Where two grids overlap, compare heights. `margin` drops the grid's outer cells,
/// which read stale scratch memory (terrain.md section 2).
let consistency (dir: string) (targets: (int * int) list) (margin: int) =
    let entry = Heritage.loadRam (Path.Combine(dir, "gen_in.snap"))
    let seen = Collections.Generic.Dictionary<int * int, int * (int * int)>()
    let mutable same, differ, firstBad = 0, 0, []
    for (x, y) in targets do
        let m = Faithful.Mem(Array.copy entry)
        m.SetW(Faithful.TGT_X, x); m.SetW(Faithful.TGT_Y, y)
        Faithful.generate m
        let ox, oy = Faithful.s16 (m.W Faithful.ORG_X), Faithful.s16 (m.W Faithful.ORG_Y)
        for row in margin .. 99 - margin do
            for col in margin .. 99 - margin do
                let h = Faithful.s16 (m.W(Faithful.GRID + 4 * (row * 100 + col)))
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


// ---- the domain model against the game -----------------------------------------------------------

/// The game's final window for each target, cell for cell against the whole island's finest level at the
/// window's origin. The outer cells of the game's window read stale memory; `margin` leaves them out.
let domainGate (dir: string) (margin: int) =
    let sw = Diagnostics.Stopwatch.StartNew()
    let finest = List.last (islandFrom dir)
    let n = Array2D.length1 finest
    printfn "island: %d levels, finest %d x %d, built in %d ms" 6 n n sw.ElapsedMilliseconds
    let results =
        [ for (x, y), name in targets do
              let ram = Heritage.loadRam (Path.Combine(dir, name + ".snap"))
              let game = readGrid ram Heritage.Addr.grid 100
              let ox, oy = Heritage.sword ram Heritage.Addr.origin, Heritage.sword ram (Heritage.Addr.origin + 2)
              let cells =
                  [ for r in margin .. 99 - margin do
                      for c in margin .. 99 - margin do
                          let wy, wx = oy + r, ox + c
                          if wy >= 0 && wy < n && wx >= 0 && wx < n then yield (wx, wy), game.[r, c] = finest.[wy, wx] ]
              let bad = cells |> List.filter (snd >> not) |> List.map fst
              let where =
                  if bad.IsEmpty then ""
                  else sprintf "  (mismatches at x %d..%d, y %d..%d)" (bad |> List.map fst |> List.min) (bad |> List.map fst |> List.max)
                                                                      (bad |> List.map snd |> List.min) (bad |> List.map snd |> List.max)
              printfn "target %4d,%-4d origin %4d,%-4d  %d/%d cells match%s" x y ox oy (cells.Length - bad.Length) cells.Length where
              yield cells.Length - bad.Length, cells.Length ]
    let ok, total = List.sumBy fst results, List.sumBy snd results
    printfn "margin %d: %d/%d cells over %d windows" margin ok total results.Length
    ok = total

match fsi.CommandLineArgs |> Array.toList |> List.tail with
| [ "same"; dir ] ->
    let rnd = Random(1)
    let near = [ for _ in 1 .. 40 -> 800 + rnd.Next(-60, 61), 800 + rnd.Next(-60, 61) ]
    let wide = [ for _ in 1 .. 40 -> rnd.Next(200, 1400), rnd.Next(200, 1400) ]
    for m in [ 0; 1; 2; 4; 8 ] do consistency dir near m
    for m in [ 0; 1; 2; 8 ] do consistency dir wide m
    exit 0
| [ "gate"; dir ] -> exit (gate dir)
| [ "gate"; dir; "--break" ] -> Faithful.seedXor <- false; exit (gate dir)
| [ "domain"; dir ] ->
    let inside = domainGate dir 2
    domainGate dir 0 |> ignore
    exit (if inside then 0 else 1)
| [ "map"; dir; out ] ->
    let finest = List.last (islandFrom dir)
    Render.savePng out (Render.topDown (Render.terrain Drone.finestCell finest))
    exit 0
| [ "zoom"; dir; out ] -> Drone.zoomFigure (islandFrom dir) (368, 1176) out; exit 0
| [ "drone"; dir; out ] -> Drone.fly (List.last (islandFrom dir)) out 20.0; exit 0
| [ "drone"; dir; out; secs ] -> Drone.fly (List.last (islandFrom dir)) out (float secs); exit 0
| [ "reveal"; dir; out ] -> Drone.reveal (List.last (islandFrom dir)) out 30.0; exit 0
| [ "reveal"; dir; out; secs ] -> Drone.reveal (List.last (islandFrom dir)) out (float secs); exit 0
| [ "skier"; dir; snap; out ] -> Drone.skier (List.last (islandFrom dir)) (Heritage.loadRam snap) out; exit 0
| _ -> eprintfn "usage: see the header of terrain.fsx"; exit 2
