// Zoom. For each emulator capture at zoom 1..7 (zoomN.json, ../dump_frame.py):
//  1. Projection.projectGrid at that zoom vs the game's own $3f364 corners.
//  2. Terrain vs the game's screen, away from sprites (best of the 4 water ticks:
//     a snapshot taken mid-render shows the previous tick's frame).
//  3. The whole frame with the port's records (entities.json) drawn inline, and
//     the sprite pixels alone: with $12244's zoom sheet, and with the zoom-4
//     sheet forced, to show the branch matters.
//   dotnet fsi zoom_check.fsx zoom1.json ... zoom7.json
// The sprite lines need frames exported with sheet_prop32/sheet_prop16: without
// them zoom 1-3 and 6-7 buildings are missing and count as terrain misses.
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
#load "../../port/stepper/Load.fs"
open PmLogic
open System
open System.IO
open System.Text.Json
let W, H = Fill.ScreenWidth, Fill.ScreenHeight
let assets = PmStepper.Load.load (Path.Combine(__SOURCE_DIRECTORY__, "../../port/assets/"))
let run (path: string) =
    let root = JsonDocument.Parse(File.ReadAllText path).RootElement
    let gi (k: string) = root.GetProperty(k).GetInt32()
    let bytes (k: string) = Convert.FromBase64String(root.GetProperty(k).GetString())
    let bytesOpt (k: string) = match root.TryGetProperty k with | true, v -> Convert.FromBase64String(v.GetString()) | _ -> [||]
    let camX, camY = root.GetProperty("cam").[0].GetInt32(), root.GetProperty("cam").[1].GetInt32()
    let yaw, inset, half = gi "yaw", gi "x_inset", gi "half"
    let map : Terrain.Map = { Type = bytes "typ"; HeightPlane = bytes "hgt"; Flag = bytes "flg"; Control = bytes "ctl" }
    let cj = root.GetProperty("corners")
    let n = 2 * half + 1
    let corners = Array2D.init n n (fun r c -> ({ X = float (cj.[r].[c].[0].GetInt32()); Y = float (cj.[r].[c].[1].GetInt32()) } : Projection.Corner))
    // 1. projection
    let mine = Projection.projectGrid (Projection.Params.Mission1.WithYaw(yaw / 16).WithZoom(half)) map camX camY
    let mutable exact, near = 0, 0
    for r in 0 .. n - 1 do
        for c in 0 .. n - 1 do
            let dx = abs (Math.Round mine.[r, c].X - corners.[r, c].X)
            let dy = abs (Math.Round mine.[r, c].Y - corners.[r, c].Y)
            if dx = 0.0 && dy = 0.0 then exact <- exact + 1
            if dx <= 1.0 && dy <= 1.0 then near <- near + 1
    let reff = bytes "ref"
    let dith = Fill.withPhase (bytes "dith") (gi "phase_bias")
    let refAt i = let y, x = i / W, i % W + inset in if x < W then Some reff.[y * W + x] else None
    let score (b: Fill.Buffer) (want: int -> bool) =
        let mutable hit, tot = 0, 0
        for i in 0 .. W * H - 1 do
            match refAt i with
            | Some r when b.Covered.[i] && want i -> tot <- tot + 1; (if b.Index.[i] = r then hit <- hit + 1)
            | _ -> ()
        100.0 * float hit / float (max tot 1), tot
    // 2. terrain, best tick
    let terrainAt t = let b = Fill.Buffer.Create() in Fill.walk b dith corners map camX camY t (yaw / 16); b
    let tick = [ 0 .. 3 ] |> List.maxBy (fun t -> fst (score (terrainAt t) (fun _ -> true)))
    let terrain = terrainAt tick
    // 3. sprites
    let ctx : Sprites.EntityCtx =
        { assets.EntityCtx with
            Yaw = yaw; Anim = gi "anim" <> 0; SelGroup = gi "sel_group"; TileOff = gi "tile_off"
            RotPhase = gi "rot_phase"; Zoom = half; Ram = bytes "ram"; SheetProp32 = bytesOpt "sheet_prop32"; SheetProp16 = bytesOpt "sheet_prop16" }
    let render (c: Sprites.EntityCtx) =
        let b = Fill.Buffer.Create()
        Scene.render b dith tick c corners map camX camY (yaw / 16) assets.Entities
        b
    let withSheet, forced4 = render ctx, render { ctx with Zoom = 4 }
    let sprite (b: Fill.Buffer) i = b.Covered.[i] && (not terrain.Covered.[i] || terrain.Index.[i] <> b.Index.[i])
    let away i = not (sprite withSheet i) && not (sprite forced4 i)
    let pct (p, t) = sprintf "%6.2f%% of %5d" p t
    printfn "%s  zoom %d  cam (%d,%d)  tick %d" (Path.GetFileNameWithoutExtension path) half camX camY tick
    printfn "  corners: %d/%d exact, %d within 1 px" exact (n * n) near
    printfn "  terrain away from sprites : %s" (pct (score terrain away))
    printfn "  whole frame               : %s  (zoom-4 sheet forced: %s)" (pct (score withSheet (fun _ -> true))) (pct (score forced4 (fun _ -> true)))
    printfn "  sprite px                 : %s  (zoom-4 sheet forced: %s)" (pct (score withSheet (sprite withSheet))) (pct (score forced4 (sprite forced4)))
for p in fsi.CommandLineArgs |> Array.skip 1 do run p
