// Camp-marker pixel match. usage: dotnet fsi cmp.fsx <state.json+screen.json> ...
// state = frame i's RAM (records); screen = frame i+1's finished buffer ($f898 snapshot), the frame drawn from state i.
// For every byte6 6/24 record in the state: the port's render with the record (P1), without it (P0), with a wrong frame (PW),
// and the game's screen (G). Counted over the pixels where P1 <> P0 (the port's footprint of the marker):
//   hit = P1 == G, ctl = P0 == G (same snapshot, marker dropped), wrong = PW == G.
// Also the marker's top-left from the footprint's bounding box.
#r "../../../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System
open System.IO
open System.Text.Json
let W, H = Fill.ScreenWidth, Fill.ScreenHeight
let run (arg: string) =
    let path, refPath = match arg.Split('+') with [| a; b |] -> a, b | _ -> arg, arg
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
    let sroot = JsonDocument.Parse(File.ReadAllText refPath).RootElement
    let reff = Convert.FromBase64String(sroot.GetProperty("ref").GetString())
    let stick = sroot.GetProperty("tick").GetInt32()
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
    let ram = ctx.Ram
    let wkind = (int ram.[0x4bb42] <<< 8) ||| int ram.[0x4bb43]
    let wphase = (int ram.[0x1aac8] + 0x40) &&& 0xFF
    let wtables = Array.append ram.[0x1a8a4 .. 0x1a8a4 + 255] ram.[0x1a9c8 .. 0x1a9c8 + 255]
    let render (c: Sprites.EntityCtx) rs =
        let b = Fill.Buffer.Create()
        Scene.render b dith stick c corners map camX camY (yaw / 16) rs
        Weather.draw b wtables wkind wphase
        b
    let img (b: Fill.Buffer) =
        let a = Array.create (W * H) 255uy
        for i in 0 .. W * H - 1 do
            let y, x = i / W, i % W + inset
            if x < W && b.Covered.[i] then a.[y * W + x] <- b.Index.[i]
        a
    let game = Array.create (W * H) 255uy
    for i in 0 .. W * H - 1 do
        let y, x = i / W, i % W + inset
        if x < W then game.[y * W + x] <- reff.[y * W + x]   // same indexing as diff.fsx refAt
    // diff.fsx indexes the game as reff.[y*W + (i%W + inset)] into img position y*W+x; mirror it exactly
    for i in 0 .. W * H - 1 do
        let y, x = i / W, i % W + inset
        game.[y * W + x |> min (W*H-1)] <- game.[y * W + x |> min (W*H-1)]
    let p1 = img (render ctx recs)
    let mutable tot = [| 0; 0; 0; 0 |]  // footprint px, hit, ctl, wrong
    for m in recs |> List.filter (fun r -> r.B6 = 6 || r.B6 = 24) do
        let without = recs |> List.filter (fun r -> r.Addr <> m.Addr)
        let p0 = img (render ctx without)
        // wrong frame: lit -> the next phase; put-out/catch -> b7 + 1
        let pw =
            if m.B6 = 6 && m.B7 = 0x12 then img (render { ctx with RotPhase = ctx.RotPhase + 1 } recs)
            else img (render ctx (recs |> List.map (fun r -> if r.Addr = m.Addr then { r with B7 = r.B7 + 1 } else r)))
        let mutable f, h, c, w = 0, 0, 0, 0
        let mutable x0', x1, y0', y1 = 999, -1, 999, -1
        let mutable gdiff = 0
        for i in 0 .. W * H - 1 do
            if p1.[i] <> p0.[i] then
                f <- f + 1
                if p1.[i] = game.[i] then h <- h + 1
                if p0.[i] = game.[i] then c <- c + 1
                if pw.[i] = game.[i] then w <- w + 1
                x0' <- min x0' (i % W); x1 <- max x1 (i % W); y0' <- min y0' (i / W); y1 <- max y1 (i / W)
        printfn "  rec %x b5=%d b6=%d b7=%02x cell(%d,%d) rot=%d: port footprint %d px, bbox x%d..%d y%d..%d | game==port %d, game==port-without-marker %d, game==port-wrong-frame %d"
            m.Addr m.B5 m.B6 m.B7 m.Wcx m.Wcy ctx.RotPhase f x0' x1 y0' y1 h c w
        // 8x11 rect at the game's own $11f78 D0/D1 (POS=addr:D0:D1,...): the port's pixel vs the game's final screen
        match Environment.GetEnvironmentVariable "POS" with
        | null | "" -> ()
        | pos ->
            for e in pos.Split(',') do
                let q = e.Split(':')
                if Convert.ToInt32(q.[0], 16) = m.Addr then
                    let x0, y0 = int q.[1], int q.[2]
                    let mutable a, b, c2, d = 0, 0, 0, 0
                    for yy in y0 .. y0 + 10 do
                        for xx in x0 .. x0 + 7 do
                            let i = yy * W + xx
                            a <- a + 1
                            if p1.[i] = game.[i] then b <- b + 1
                            if p0.[i] = game.[i] then c2 <- c2 + 1
                            if pw.[i] = game.[i] then d <- d + 1
                    printfn "    rect (%d,%d) 8x11 at the game's D0/D1: %d px; port==game %d, port-without-marker==game %d, port-wrong-frame==game %d; footprint inside rect: %b"
                        x0 y0 a b c2 d (f = 0 || (x0 <= x0' && x1 <= x0 + 7 && y0 <= y0' && y1 <= y0 + 10))
        tot.[0] <- tot.[0] + f; tot.[1] <- tot.[1] + h; tot.[2] <- tot.[2] + c; tot.[3] <- tot.[3] + w
    match Environment.GetEnvironmentVariable "RECT" with
    | null | "" -> ()
    | r ->
        let v = r.Split(',') |> Array.map int
        let p0 = img (render ctx (recs |> List.filter (fun r -> r.B6 <> 6 && r.B6 <> 24)))
        for y in v.[1] .. v.[1] + 10 do
            let row (a: byte[]) = String.Join(" ", [ for x in v.[0] .. v.[0] + 7 -> if a.[y*W+x] = 255uy then "." else sprintf "%x" a.[y*W+x] ])
            printfn "  rect row %d  port %s | port-no-markers %s | game %s" y (row p1) (row p0) (row game)
    // whole-frame: pixels the port covers, matching
    let mutable cov, ok = 0, 0
    for i in 0 .. W * H - 1 do
        if p1.[i] <> 255uy then (cov <- cov + 1; if p1.[i] = game.[i] then ok <- ok + 1)
    printfn "  whole frame: port covers %d px, equal to game %d" cov ok
    tot
let all = fsi.CommandLineArgs |> Array.skip 1
let g = [| 0; 0; 0; 0 |]
for a in all do
    printfn "%s" a
    let t = run a
    for k in 0 .. 3 do g.[k] <- g.[k] + t.[k]
printfn "TOTAL over %d frames: footprint px %d, port==game %d, port-without-marker==game %d, port-wrong-frame==game %d" all.Length g.[0] g.[1] g.[2] g.[3]
