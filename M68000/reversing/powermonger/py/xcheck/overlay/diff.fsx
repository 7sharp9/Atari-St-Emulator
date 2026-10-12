// Differential score of a poked capture against its no-poke control.
// Copied from py/score.fsx. Original header: score a captured frame against Scene.render (inline order), at all
// four water ticks, and for each byte6 category in view, the pixels its
// sprites change: does the game show the sprite there, or what is under it?
//   dotnet fsi score.fsx cap/x_0.json [...]
#r "../../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System
open System.IO
open System.Text.Json

let W, H = Fill.ScreenWidth, Fill.ScreenHeight

// "a.json+b.json": state from a, the game's screen from b. A $f898 snapshot's
// finished compose buffer is the frame drawn from the PREVIOUS state, so the
// frame drawn from a's state is the one b (the next $f898) holds.
let tick0 = int (fsi.CommandLineArgs.[1])
// load "state.json+screen.json": the port's frame at a tick, and the game's screen
let load (arg: string) =
    let path, refPath = match arg.Split('+') with [| a; b |] -> a, b | _ -> arg, arg
    let root = JsonDocument.Parse(File.ReadAllText path).RootElement
    let gi (k: string) = root.GetProperty(k).GetInt32()
    let bytes (k: string) = Convert.FromBase64String(root.GetProperty(k).GetString())
    // sheets a dump_frame.py older than the 154th did not export read as empty
    let bytesOpt (k: string) =
        match root.TryGetProperty k with | true, v -> Convert.FromBase64String(v.GetString()) | _ -> [||]
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
          RotPhase = gi "rot_phase"; Sheet33 = bytes "sheet33"; SheetProp = bytes "sheet_prop"; Ram = bytes "ram"; Seed = Sprites.seedOf (bytes "ram")
          Zoom = half; SheetProp32 = bytesOpt "sheet_prop32"; SheetProp16 = bytesOpt "sheet_prop16" }
    let recs =
        [ for o in root.GetProperty("objs").EnumerateArray() ->
            let g (k: string) = o.GetProperty(k).GetInt32()
            let go (k: string) = match o.TryGetProperty k with | true, v -> v.GetInt32() | _ -> 0
            ({ Addr = g "addr"; B6 = g "b6"; B5 = g "b5"; B7 = g "b7"; B14 = g "b14"; B17 = g "b17"; B31 = g "b31"
               Fx = g "fx"; Fy = g "fy"; Group = g "group"; Wcx = g "wcx"; Wcy = g "wcy"
               B15 = g "b15"; B32 = g "b32"; W18 = g "w18"; Icons = g "icons"; B33 = g "b33"; B44 = g "b44"
               B16 = go "b16"; W12 = go "w12" } : Sprites.EntityRec) ]
    // WRONG=<field>:<delta>:<addr,addr..> (wrong-frame control): add delta to
    // one field of the named records, on the case side only (the first pair)
    let recs =
        match Environment.GetEnvironmentVariable "WRONG" with
        | null | "" -> recs
        | _ when arg <> fsi.CommandLineArgs.[2] -> recs
        | w ->
            let parts = w.Split(':')
            let d = int parts.[1]
            let addrs = parts.[2].Split(',') |> Array.map (fun a -> Convert.ToInt32(a, 16)) |> set
            recs |> List.map (fun r ->
                if not (addrs.Contains r.Addr) then r
                else
                    match parts.[0] with
                    | "b44" -> { r with B44 = r.B44 + d }
                    | "b5" -> { r with B5 = r.B5 + d }
                    | "b7" -> { r with B7 = r.B7 + d }
                    | "b17" -> { r with B17 = (r.B17 + d) &&& 0xFF }
                    | "b15" -> { r with B15 = (r.B15 + d) &&& 0xFF }
                    | f -> failwithf "WRONG: no field %s" f)
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
    let b = render tick0 recs
    let img = Array.create (W * H) 255uy
    let game = Array.create (W * H) 255uy
    for i in 0 .. W * H - 1 do
        let y, x = i / W, i % W + inset
        if x < W then
            game.[y * W + x] <- (match refAt i with Some r -> r | None -> 255uy)
            if b.Covered.[i] then img.[y * W + x] <- b.Index.[i]
    img, reff, t0

// usage: dotnet fsi diff.fsx <tick> case_0.json+case_1.json ctl_0.json+ctl_1.json
// The port's changed pixels P = {i : port(case) <> port(ctl)}, the game's G =
// {i : game(case) <> game(ctl)} (screen space, whole 320x200 for the game).
// Prints |P|, how many of P the game shows with the port's colour, |G|, and
// how many of G the port reproduces.
let args = fsi.CommandLineArgs |> Array.skip 1
let pc, gc, _ = load args.[1]
let pk, gk, _ = load args.[2]
// the control's own misses (port drew, game shows another colour) are excluded
// from the second pair of counts: they are the same in every run
let ctlMiss i = pk.[i] <> 255uy && pk.[i] <> gk.[i]
let mutable p, pOk, g, gOk, px, pxOk, gx, gxOk, nm = 0, 0, 0, 0, 0, 0, 0, 0, 0
for i in 0 .. W * H - 1 do
    if ctlMiss i then nm <- nm + 1
    if pc.[i] <> pk.[i] then
        p <- p + 1
        if pc.[i] = gc.[i] then pOk <- pOk + 1
        if not (ctlMiss i) then
            px <- px + 1
            if pc.[i] = gc.[i] then pxOk <- pxOk + 1
    if gc.[i] <> gk.[i] then
        g <- g + 1
        if pc.[i] = gc.[i] then gOk <- gOk + 1
        if not (ctlMiss i) then
            gx <- gx + 1
            if pc.[i] = gc.[i] then gxOk <- gxOk + 1
printfn "%s: port changes %d px, game agrees at %d; game changes %d px, port reproduces %d | without the control's %d missed px: %d/%d, %d/%d"
    (System.IO.Path.GetFileName(args.[1].Split('+').[0])) p pOk g gOk nm pxOk px gxOk gx
match System.Environment.GetEnvironmentVariable "MISS" with
| null | "" -> ()
| _ ->
    for i in 0 .. W * H - 1 do
        if (pc.[i] <> pk.[i] || gc.[i] <> gk.[i]) && pc.[i] <> gc.[i] then
            printfn "  (%d,%d) port %d game %d (ctl port %d game %d)" (i % W) (i / W) pc.[i] gc.[i] pk.[i] gk.[i]
