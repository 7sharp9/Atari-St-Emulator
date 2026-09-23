// 121st: score a captured frame against Scene.render (inline order), at all
// four water ticks, and for each byte6 category in view, the pixels its
// sprites change: does the game show the sprite there, or what is under it?
//   dotnet fsi score.fsx cap/x_0.json [...]
#r "../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System
open System.IO
open System.Text.Json

let W, H = Fill.ScreenWidth, Fill.ScreenHeight

// "a.json+b.json": state from a, the game's screen from b. A $f898 snapshot's
// finished compose buffer is the frame drawn from the PREVIOUS state, so the
// frame drawn from a's state is the one b (the next $f898) holds.
let run (arg: string) =
    let path, refPath = match arg.Split('+') with [| a; b |] -> a, b | _ -> arg, arg
    let root = JsonDocument.Parse(File.ReadAllText path).RootElement
    let gi (k: string) = root.GetProperty(k).GetInt32()
    let bytes (k: string) = Convert.FromBase64String(root.GetProperty(k).GetString())
    let camX, camY = root.GetProperty("cam").[0].GetInt32(), root.GetProperty("cam").[1].GetInt32()
    let yaw, inset, half = gi "yaw", gi "x_inset", gi "half"
    let map : Terrain.Map = { Type = bytes "typ"; HeightPlane = bytes "hgt"; Flag = bytes "flg"; Control = bytes "ctl" }
    let cj = root.GetProperty("corners")
    let n = 2 * half + 1
    let corners = Array2D.init n n (fun r c ->
        ({ X = float (cj.[r].[c].[0].GetInt32()); Y = float (cj.[r].[c].[1].GetInt32()) } : Projection.Corner))
    let reff =
        Convert.FromBase64String(JsonDocument.Parse(File.ReadAllText refPath).RootElement.GetProperty("ref").GetString())
    let dith = Fill.withPhase (bytes "dith") (gi "phase_bias")
    let ctx : Sprites.EntityCtx =
        { Yaw = yaw; Anim = gi "anim" <> 0; SelGroup = gi "sel_group"; TileOff = gi "tile_off"
          RotPhase = gi "rot_phase"; Sheet33 = bytes "sheet33"; SheetProp = bytes "sheet_prop"; Ram = bytes "ram"
          Zoom = half; SheetProp32 = [||]; SheetProp16 = bytes "sheet_prop16" }
    let recs =
        [ for o in root.GetProperty("objs").EnumerateArray() ->
            let g (k: string) = o.GetProperty(k).GetInt32()
            ({ Addr = g "addr"; B6 = g "b6"; B5 = g "b5"; B7 = g "b7"; B14 = g "b14"; B17 = g "b17"; B31 = g "b31"
               Fx = g "fx"; Fy = g "fy"; Group = g "group"; Wcx = g "wcx"; Wcy = g "wcy"
               B15 = g "b15"; B32 = g "b32"; W18 = g "w18"; Icons = g "icons"; B33 = g "b33"; B44 = g "b44" } : Sprites.EntityRec) ]
    let refAt i = let y, x = i / W, i % W + inset in if x < W then Some reff.[y * W + x] else None
    // weather ($1ad2a -> $1a856): kind [$4bb42], drawn with [$1aac8] + $40
    let ram = ctx.Ram
    let wkind = (int ram.[0x4bb42] <<< 8) ||| int ram.[0x4bb43]
    let wphase = (int ram.[0x1aac8] + 0x40) &&& 0xFF
    let wtables = Array.append ram.[0x1a8a4 .. 0x1a8a4 + 255] ram.[0x1a9c8 .. 0x1a9c8 + 255]
    let render tick rs =
        let b = Fill.Buffer.Create()
        Scene.render b dith tick ctx corners map camX camY (yaw / 16) rs
        if Environment.GetEnvironmentVariable "NO_WEATHER" = null then Weather.draw b wtables wkind wphase
        b
    let score (b: Fill.Buffer) =
        let mutable hit, tot = 0, 0
        for i in 0 .. W * H - 1 do
            match refAt i with
            | Some r when b.Covered.[i] -> tot <- tot + 1; (if b.Index.[i] = r then hit <- hit + 1)
            | _ -> ()
        100.0 * float hit / float (max tot 1)
    let t0 = gi "tick"
    let scores = [ for k in 0 .. 3 -> let t = (t0 - k + 4) % 4 in t, score (render t recs) ]
    let bestT, best = scores |> List.maxBy snd
    printfn "%s  cam (%d,%d) yaw $%02x  RAM tick %d: %s  best tick %d = %.2f%%"
        (Path.GetFileNameWithoutExtension path) camX camY yaw t0
        (scores |> List.map (fun (t, s) -> sprintf "t%d %.2f" t s) |> String.concat " ") bestT best
    let full = render bestT recs
    // PLACE=<byte6>: print every blit the port makes for that category
    match Environment.GetEnvironmentVariable "PLACE" with
    | null | "" -> ()
    | c ->
        for cell in Fill.plan corners map camX camY (yaw / 16) do
            for r in recs do
                if r.B6 = int c && r.Wcx = cell.X && r.Wcy = cell.Y then
                    let ps = Scene.placement ctx cell r
                    printfn "    $%05x cell (%d,%d) %s" r.Addr r.Wcx r.Wcy
                        (ps |> List.map (fun p -> sprintf "f%03x@(%d,%d)" p.Frame (p.X + inset) p.Y) |> String.concat " ")
    // PORT_OUT=<file>: the port frame, shifted into screen space (255 = not drawn)
    match Environment.GetEnvironmentVariable "PORT_OUT" with
    | null | "" -> ()
    | o ->
        let img = Array.create (W * H) 255uy
        for i in 0 .. W * H - 1 do
            let y, x = i / W, i % W + inset
            if x < W && full.Covered.[i] then img.[y * W + x] <- full.Index.[i]
        File.WriteAllBytes(o, img)
    let cats = recs |> List.filter (Sprites.draws ctx) |> List.map (fun r -> r.B6) |> List.distinct |> List.sort
    for c in cats do
        let without = render bestT (recs |> List.filter (fun r -> r.B6 <> c))
        let mutable px, spr, under = 0, 0, 0
        for i in 0 .. W * H - 1 do
            match refAt i with
            | Some r when full.Covered.[i] && (not without.Covered.[i] || without.Index.[i] <> full.Index.[i]) ->
                px <- px + 1
                if full.Index.[i] = r then spr <- spr + 1
                if without.Covered.[i] && without.Index.[i] = r then under <- under + 1
            | _ -> ()
        let nrec = recs |> List.filter (fun r -> r.B6 = c) |> List.length
        if px > 0 then
            printfn "    byte6 %2d (%2d recs): %4d visible px, game shows the sprite at %4d (%.0f%%), what is under it at %d"
                c nrec px spr (100.0 * float spr / float px) under

for p in fsi.CommandLineArgs |> Array.skip 1 do run p
