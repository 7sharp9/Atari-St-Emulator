// Pan check. Render a panned capture with the port's own records (entities.json,
// pm88_f1, jitter recomputed for this window) and with the capture's own records,
// each inline, and score both against the game's screen. Terrain is scored away
// from sprites (pixels where neither render has a sprite).
//   dotnet fsi pan_check.fsx pan_e.json pan_w.json   (frames from ../dump_frame.py)
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
#load "../../port/stepper/Load.fs"
open PmLogic
open System
open System.IO
open System.Text.Json
// fields the pre-121st dump_frame.py did not export read as 0
let go (o: JsonElement) (k: string) = match o.TryGetProperty k with | true, v -> v.GetInt32() | _ -> 0
let W, H = Fill.ScreenWidth, Fill.ScreenHeight
let assets = PmStepper.Load.load (System.IO.Path.Combine(__SOURCE_DIRECTORY__, "../../port/assets/"))
let run (path: string) =
    let root = JsonDocument.Parse(File.ReadAllText path).RootElement
    let gi (k: string) = root.GetProperty(k).GetInt32()
    let bytes (k: string) = Convert.FromBase64String(root.GetProperty(k).GetString())
    let camX, camY = root.GetProperty("cam").[0].GetInt32(), root.GetProperty("cam").[1].GetInt32()
    let yaw, tick, inset = gi "yaw", gi "tick", gi "x_inset"
    let map : Terrain.Map = { Type = bytes "typ"; HeightPlane = bytes "hgt"; Flag = bytes "flg"; Control = bytes "ctl" }
    let cj = root.GetProperty("corners")
    let corners = Array2D.init 9 9 (fun r c -> ({ X = float (cj.[r].[c].[0].GetInt32()); Y = float (cj.[r].[c].[1].GetInt32()) } : Projection.Corner))
    let reff = bytes "ref"
    let dith = Fill.withPhase (bytes "dith") (gi "phase_bias")
    let ctx : Sprites.EntityCtx =
        { Yaw = yaw; Anim = gi "anim" <> 0; SelGroup = gi "sel_group"; TileOff = gi "tile_off"
          RotPhase = gi "rot_phase"; Sheet33 = bytes "sheet33"; SheetProp = bytes "sheet_prop"; Ram = bytes "ram"
          Zoom = 4; SheetProp32 = [||]; SheetProp16 = [||] }   // zoom-4 captures: only the 32x24 sheet is used
    let own =
        [ for o in root.GetProperty("objs").EnumerateArray() ->
            let g (k: string) = o.GetProperty(k).GetInt32()
            ({ Addr = g "addr"; B6 = g "b6"; B5 = g "b5"; B7 = g "b7"; B14 = g "b14"; B17 = g "b17"; B31 = g "b31"
               Fx = g "fx"; Fy = g "fy"; Group = g "group"; Wcx = g "wcx"; Wcy = g "wcy"; B15 = go o "b15"; B32 = go o "b32"; W18 = go o "w18"; Icons = go o "icons"; B33 = go o "b33"; B44 = go o "b44" } : Sprites.EntityRec) ]
    let render recs =
        let b = Fill.Buffer.Create()
        Scene.render b dith tick ctx corners map camX camY (yaw / 16) recs
        b
    let terrain = Fill.Buffer.Create()
    Fill.walk terrain dith corners map camX camY tick (yaw / 16)
    let port, game = render assets.Entities, render own
    let refAt i = let y, x = i / W, i % W + inset in if x < W then Some reff.[y * W + x] else None
    let sprite (b: Fill.Buffer) i = b.Covered.[i] && (not terrain.Covered.[i] || terrain.Index.[i] <> b.Index.[i])
    let score (b: Fill.Buffer) (want: int -> bool) =
        let mutable hit, tot = 0, 0
        for i in 0 .. W * H - 1 do
            match refAt i with
            | Some r when b.Covered.[i] && want i -> tot <- tot + 1; (if b.Index.[i] = r then hit <- hit + 1)
            | _ -> ()
        sprintf "%5.2f%% of %5d" (100.0 * float hit / float (max tot 1)) tot
    let away i = not (sprite port i) && not (sprite game i)
    printfn "%s cam (%d,%d)" (Path.GetFileNameWithoutExtension path) camX camY
    printfn "  terrain away from sprites  : %s" (score terrain away)
    printfn "  whole frame, port records  : %s   capture records: %s" (score port (fun _ -> true)) (score game (fun _ -> true))
    printfn "  sprite px,   port records  : %s   capture records: %s" (score port (sprite port)) (score game (sprite game))
    let same = Seq.forall (fun i -> port.Index.[i] = game.Index.[i] && port.Covered.[i] = game.Covered.[i]) (seq { 0 .. W * H - 1 })
    printfn "  port render == capture-records render: %b" same
for p in fsi.CommandLineArgs |> Array.skip 1 do run p
