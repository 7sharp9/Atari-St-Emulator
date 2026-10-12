// Which draw order does the game use? Render one captured frame two ways and
// score each against the game's own screen:
//   post   = all terrain, then all sprites (Sprites.drawEntities, = pm_render_ref)
//   inline = each cell's sprites straight after its triangles (Scene.render, = $f898)
// Only pixels where the two orders disagree can tell them apart.
//   dotnet fsi order_test.fsx pm88_f1.json [more.json ...]   (frames from ../dump_frame.py)
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System
open System.IO
open System.Text.Json

let W, H = Fill.ScreenWidth, Fill.ScreenHeight

let run (path: string) =
    let root = JsonDocument.Parse(File.ReadAllText path).RootElement
    let gi (k: string) = root.GetProperty(k).GetInt32()
    let bytes (k: string) = Convert.FromBase64String(root.GetProperty(k).GetString())
    let bytesOpt (k: string) =
        match root.TryGetProperty k with | true, v -> Convert.FromBase64String(v.GetString()) | _ -> [||]
    let camX, camY = root.GetProperty("cam").[0].GetInt32(), root.GetProperty("cam").[1].GetInt32()
    let yaw, tick, inset = gi "yaw", gi "tick", gi "x_inset"
    let map : Terrain.Map = { Type = bytes "typ"; HeightPlane = bytes "hgt"; Flag = bytes "flg"; Control = bytes "ctl" }
    let half = gi "half"
    let cj = root.GetProperty("corners")
    let corners = Array2D.init (2 * half + 1) (2 * half + 1) (fun r c ->
        ({ X = float (cj.[r].[c].[0].GetInt32()); Y = float (cj.[r].[c].[1].GetInt32()) } : Projection.Corner))
    let reff = bytes "ref"
    let dith = Fill.withPhase (bytes "dith") (gi "phase_bias")   // $f8e4 camera-change phase
    let ctx : Sprites.EntityCtx =
        { Yaw = yaw; Anim = gi "anim" <> 0; SelGroup = gi "sel_group"; TileOff = gi "tile_off"
          RotPhase = gi "rot_phase"; Sheet33 = bytes "sheet33"; SheetProp = bytes "sheet_prop"; Ram = bytes "ram"
          Zoom = half; SheetProp32 = bytesOpt "sheet_prop32"; SheetProp16 = bytesOpt "sheet_prop16" }
    let recs =
        [ for o in root.GetProperty("objs").EnumerateArray() ->
            let g (k: string) = o.GetProperty(k).GetInt32()
            let go (k: string) = match o.TryGetProperty k with | true, v -> v.GetInt32() | _ -> 0
            ({ Addr = g "addr"; B6 = g "b6"; B5 = g "b5"; B7 = g "b7"; B14 = g "b14"; B17 = g "b17"; B31 = g "b31"
               Fx = g "fx"; Fy = g "fy"; Group = g "group"
               Wcx = g "wcx"; Wcy = g "wcy"; B15 = go "b15"; B32 = go "b32"; W18 = go "w18"; Icons = go "icons"; B33 = go "b33"; B44 = go "b44"; B16 = go "b16"; W12 = go "w12" } : Sprites.EntityRec) ]

    let terrain = Fill.Buffer.Create()
    Fill.walk terrain dith corners map camX camY tick (yaw / 16)
    let post = Fill.Buffer.Create()
    Fill.walk post dith corners map camX camY tick (yaw / 16)
    Sprites.drawEntities post ctx corners camX camY recs
    let inl = Fill.Buffer.Create()
    Scene.render inl dith tick ctx corners map camX camY (yaw / 16) recs

    // buffers are raw $3f364 space; the screen is +inset px to the right
    let refAt i = let y, x = i / W, i % W + inset in if x < W then Some reff.[y * W + x] else None
    let score (b: Fill.Buffer) =
        let mutable hit, tot = 0, 0
        for i in 0 .. W * H - 1 do
            match refAt i with
            | Some r when b.Covered.[i] -> tot <- tot + 1; (if b.Index.[i] = r then hit <- hit + 1)
            | _ -> ()
        hit, tot
    let pct (h, t) = 100.0 * float h / float (max t 1)
    let ph, pt = score post
    let ih, it = score inl
    let mutable diff, postWins, inlWins, neither = 0, 0, 0, 0
    for i in 0 .. W * H - 1 do
        match refAt i with
        | Some r when post.Covered.[i] && inl.Covered.[i] && post.Index.[i] <> inl.Index.[i] ->
            diff <- diff + 1
            if post.Index.[i] = r then postWins <- postWins + 1
            elif inl.Index.[i] = r then inlWins <- inlWins + 1
            else neither <- neither + 1
        | _ -> ()
    // pixels where a visible sprite changes the inline frame: does the game
    // show the sprite there, or the bare terrain?
    let mutable sprPx, sprHit, terrHit = 0, 0, 0
    for i in 0 .. W * H - 1 do
        match refAt i with
        | Some r when inl.Covered.[i] && (not terrain.Covered.[i] || terrain.Index.[i] <> inl.Index.[i]) ->
            sprPx <- sprPx + 1
            if inl.Index.[i] = r then sprHit <- sprHit + 1
            if terrain.Covered.[i] && terrain.Index.[i] = r then terrHit <- terrHit + 1
        | _ -> ()
    printfn "  visible sprite px: %d -> game shows the sprite at %d, the bare terrain at %d" sprPx sprHit terrHit
    let nSteps = Scene.steps ctx (Fill.plan corners map camX camY (yaw / 16)) recs |> Array.length
    printfn "%s  cam (%d,%d) yaw $%02x  steps %d" (Path.GetFileNameWithoutExtension path) camX camY yaw nSteps
    printfn "  terrain only        : %.1f%% exact" (pct (score terrain))
    printfn "  post  (sprites last): %d/%d = %.2f%%" ph pt (pct (ph, pt))
    printfn "  inline ($f898 order): %d/%d = %.2f%%" ih it (pct (ih, it))
    printfn "  pixels where the orders differ: %d -> game matches post %d, inline %d, neither %d"
        diff postWins inlWins neither

for p in fsi.CommandLineArgs |> Array.skip 1 do run p
