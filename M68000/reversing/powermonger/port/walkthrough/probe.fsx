// Live probes for walkthrough.md: each prints a small, deterministic fact
// computed by the real PmLogic code, so `showboat verify` re-checks the
// walkthrough's claims. Build the logic first:
//   dotnet build ../godot/logic/PmLogic.fsproj
//   dotnet fsi probe.fsx <heights|corners|order <yaw>|split|slope|dither|steps|occlusion|rasters>
#r "../godot/logic/bin/Debug/net8.0/PmLogic.dll"
open System
open System.IO
open System.Text.Json
open PmLogic

// LF line endings on every platform, so showboat verify compares like with like
Console.Out.NewLine <- "\n"

let assets = Path.Combine(__SOURCE_DIRECTORY__, "..", "assets")
let map = Terrain.parse (File.ReadAllBytes(Path.Combine(assets, "terrain.bin")))
let dith = File.ReadAllBytes(Path.Combine(assets, "dither.bin"))
let camX, camY, yaw = 36, 47, 15                        // mission-1 start pose
let corners = Projection.projectGrid (Projection.Params.Mission1.WithYaw yaw) map camX camY

let ctx, recs =
    use doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(assets, "entities.json")))
    let c = doc.RootElement.GetProperty("entity_ctx")
    let gi (e: JsonElement) (k: string) = e.GetProperty(k).GetInt32()
    let file (k: string) = File.ReadAllBytes(Path.Combine(assets, string (c.GetProperty(k).GetString())))
    ({ Yaw = gi c "yaw"; Anim = gi c "anim" <> 0; SelGroup = gi c "sel_group"; TileOff = gi c "tile_off"
       RotPhase = gi c "rot_phase"; Sheet33 = file "sheet33"; SheetProp = file "sheet_prop"; Ram = [||] }
     : Sprites.EntityCtx),
    [| for e in doc.RootElement.GetProperty("render_entities").EnumerateArray() ->
         ({ B6 = gi e "b6"; B5 = gi e "b5"; B7 = gi e "b7"; B14 = gi e "b14"; B17 = gi e "b17"
            B31 = gi e "b31"; Fx = gi e "fx"; Fy = gi e "fy"; Fx4 = gi e "fx4"; Fy4 = gi e "fy4"
            Group = gi e "group"; Wcx = gi e "wcx"; Wcy = gi e "wcy" } : Sprites.EntityRec) |]

let hex (n: int) = sprintf "%02x" n
let pt (c: Projection.Corner) = sprintf "(%3.0f,%3.0f)" c.X c.Y

match fsi.CommandLineArgs |> Array.skip 1 |> List.ofArray with
| [ "heights" ] ->
    // the control plane under the 9x9 corner window: what the projector lifts
    printfn "control-plane heights, corners (%d..%d, %d..%d):" camX (camX + 8) camY (camY + 8)
    for r in 0 .. 8 do
        printfn "  %s" (String.Join(" ", [ for c in 0 .. 8 -> hex (map.ControlAt(camX + c, camY + r)) ]))
| [ "corners" ] ->
    printfn "projected corners (screen x, y), rows = grid rows 0..8:"
    for r in 0 .. 8 do
        printfn "  %s" (String.Join(" ", [ for c in 0 .. 8 -> pt corners.[r, c] ]))
| [ "order"; y ] ->
    let y = int y
    let cells = Fill.plan corners map camX camY y
    let at = cells |> List.mapi (fun i c -> (c.Row, c.Col), i + 1) |> dict
    printfn "yaw %d -> handler q%d; visit order laid out by grid (row down, col across):" y (Fill.quadrant y)
    for r in 0 .. 7 do
        printfn "  %s" (String.Join(" ", [ for c in 0 .. 7 -> sprintf "%2d" at.[(r, c)] ]))
| [ "split" ] ->
    let c = Fill.plan corners map camX camY yaw |> List.head
    let q = c.Quad
    printfn "first cell visited: world (%d,%d), grid row %d col %d, strip %d" c.X c.Y c.Row c.Col c.Strip
    printfn "  C00 %s  C10 %s  C01 %s  C11 %s" (pt q.C00) (pt q.C10) (pt q.C01) (pt q.C11)
    printfn "  type byte $%s  height byte $%s  flag bit 7 %s" (hex q.TypeByte) (hex q.HeightByte)
        (if q.Diagonal then "set: split C10-C01" else "clear: split C00-C11")
    for name, t in [ "first ", c.First; "second", c.Second ] do
        printfn "  %s tri %s %s %s colour $%s" name (pt t.A) (pt t.B) (pt t.C) (hex t.Colour)
| [ "slope" ] ->
    printfn "   dx  dy   $f000 16.16     naive (dx<<16)/dy"
    for dx, dy in [ 7, 3; 10, 3; 3, 7; -5, 2; 200, 1 ] do
        let naive = (abs dx <<< 16) / dy * sign dx
        printfn "  %3d %3d   %08x (%9.4f)   %08x (%9.4f)" dx dy (Fill.fixedSlope dx dy)
            (float (Fill.fixedSlope dx dy) / 65536.0) naive (float naive / 65536.0)
| [ "dither" ] ->
    for colour in [ 0x26; 0x25 ] do
        printfn "colour byte $%s, x 0..31, scanlines 0..5 (palette indices, hex):" (hex colour)
        for y in 0 .. 5 do
            printfn "  y=%d  %s" y (String.Join("", [ for x in 0 .. 31 -> sprintf "%x" (Fill.ditherIndex dith colour y x) ]))
| [ "steps" ] ->
    let steps = Scene.steps ctx (Fill.plan corners map camX camY yaw) recs
    let tris = steps |> Array.filter (function Scene.Triangle _ -> true | _ -> false) |> Array.length
    printfn "%d steps: %d triangles (64 cells x 2) + %d sprites" steps.Length tris (steps.Length - tris)
    printfn "first cell with sprites, in draw order:"
    let firstSpriteCell = steps |> Array.pick (function Scene.Sprite(c, _) -> Some c | _ -> None)
    for s in steps |> Array.filter (fun s -> Scene.cellOf s = firstSpriteCell) do
        match s with
        | Scene.Triangle(c, _, t) -> printfn "  triangle  cell (%d,%d) colour $%s" c.X c.Y (hex t.Colour)
        | Scene.Sprite(c, r) -> printfn "  sprite    cell (%d,%d) byte6 %d" c.X c.Y r.B6
| [ "occlusion" ] ->
    // For each sprite, how many of its pixels does later (nearer) terrain paint over?
    let steps = Scene.steps ctx (Fill.plan corners map camX camY yaw) recs
    // owner.[p] = the last step to write pixel p, i.e. the one left visible
    let owner = Array.create (Fill.ScreenWidth * Fill.ScreenHeight) -1
    let written = Array.zeroCreate steps.Length
    steps |> Array.iteri (fun i s ->
        let one = Fill.Buffer.Create()
        Scene.drawStep one dith 0 ctx s |> ignore
        for p in 0 .. one.Covered.Length - 1 do
            if one.Covered.[p] then
                owner.[p] <- i
                written.[i] <- written.[i] + 1)
    let survived = Array.zeroCreate steps.Length
    for p in owner do if p >= 0 then survived.[p] <- survived.[p] + 1
    let sprites = [ for i in 0 .. steps.Length - 1 do
                      match steps.[i] with
                      | Scene.Sprite(c, r) -> yield i, c, r
                      | _ -> () ]
    let hidden = sprites |> List.sumBy (fun (i, _, _) -> written.[i] - survived.[i])
    printfn "%d sprites wrote %d px; %d of those px were later painted over" sprites.Length
        (sprites |> List.sumBy (fun (i, _, _) -> written.[i])) hidden
    printfn "most-covered sprites (step, cell, kind, px drawn -> px left visible):"
    for i, c, r in sprites |> List.sortByDescending (fun (i, _, _) -> written.[i] - survived.[i]) |> List.truncate 3 do
        printfn "  step %3d  cell (%d,%d) strip %d  byte6 %2d  %3d -> %3d" i c.X c.Y c.Strip r.B6 written.[i] survived.[i]
| [ "rasters" ] ->
    // what $ef62 actually did with each of the frame's 128 triangles
    let steps = Scene.steps ctx (Fill.plan corners map camX camY yaw) recs
    let mutable coast, aborted, skipped, clipped = [], [], [], 0
    for i in 0 .. steps.Length - 1 do
        match steps.[i] with
        | Scene.Triangle(_, _, t) ->
            let buf = Fill.Buffer.Create()
            match Fill.drawTri buf dith 0 t with
            | Fill.Skipped why -> skipped <- (i, why) :: skipped
            | Fill.Walked(colour, rows, stop) ->
                if colour <> t.Colour then coast <- i :: coast
                match stop with Some r -> aborted <- (i, r, rows) :: aborted | None -> ()
                if not (Array.contains true buf.Covered) then clipped <- clipped + 1
        | _ -> ()
    printfn "reversed winding ($1c forced) on %d triangles, first at steps %A" coast.Length (List.rev coast |> List.truncate 4)
    let lost = aborted |> List.countBy (fun (_, r, rows) -> rows - r) |> List.sort
    printfn "span walk aborted on %d triangles; rows lost -> how many: %A" aborted.Length lost
    printfn "skipped by $ef62: %d %A; drawn but fully clipped: %d" skipped.Length (List.rev skipped) clipped
    // how much of the $1c-forced area is still visible once the frame is done?
    let owner = Array.create (Fill.ScreenWidth * Fill.ScreenHeight) -1
    let drawn = Array.zeroCreate steps.Length
    steps |> Array.iteri (fun i s ->
        let one = Fill.Buffer.Create()
        Scene.drawStep one dith 0 ctx s |> ignore
        one.Covered |> Array.iteri (fun p c -> if c then owner.[p] <- i; drawn.[i] <- drawn.[i] + (if c then 1 else 0)))
    let visible = owner |> Array.filter (fun o -> List.contains o coast) |> Array.length
    printfn "$1c triangles drew %d px; %d px of them are visible in the finished frame (of %d terrain px)"
        (coast |> List.sumBy (fun i -> drawn.[i])) visible
        (owner |> Array.filter (fun o -> o >= 0 && (match steps.[o] with Scene.Triangle _ -> true | _ -> false)) |> Array.length)
| _ -> eprintfn "usage: probe.fsx heights|corners|order <yaw>|split|slope|dither|steps|occlusion|rasters"
