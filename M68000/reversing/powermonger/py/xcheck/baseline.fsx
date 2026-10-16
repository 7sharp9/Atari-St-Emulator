// Regression baseline for the port's renderer: hashes the terrain buffer for all
// 16 yaws at five cameras and two water ticks, plus the post-terrain entity pass
// at the mission-1 pose (162 lines). baseline.txt beside this script is the
// record; a renderer change that is meant to leave the output alone must
// reproduce it exactly (run.sh diffs it).
//   dotnet fsi baseline.fsx <out.txt>
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System.IO
open System.Text.Json

let assets = Path.Combine(__SOURCE_DIRECTORY__, "../../port/assets")
let map = Terrain.parse (File.ReadAllBytes(Path.Combine(assets, "terrain.bin")))
let dith = File.ReadAllBytes(Path.Combine(assets, "dither.bin"))

let hash (b: Fill.Buffer) =
    use sha = System.Security.Cryptography.SHA256.Create()
    let bytes = Array.append b.Index (b.Covered |> Array.map (fun c -> if c then 1uy else 0uy))
    System.Convert.ToHexString(sha.ComputeHash bytes).Substring(0, 16)

let covered (b: Fill.Buffer) = b.Covered |> Array.filter id |> Array.length

let out = ResizeArray<string>()
for (cx, cy) in [ 36, 47; 20, 50; 30, 60; 10, 45; 40, 70 ] do
    for yaw in 0 .. 15 do
        for tick in [ 0; 2 ] do
            let p = Projection.Params.Mission1.WithYaw yaw
            let corners = Projection.projectGrid p map cx cy
            let buf = Fill.Buffer.Create()
            Fill.walk buf dith corners map cx cy tick yaw
            out.Add(sprintf "terrain cam=%d,%d yaw=%d tick=%d px=%d %s" cx cy yaw tick (covered buf) (hash buf))

// Entity pass at the baked pose, drawn the current way (after the terrain).
let doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(assets, "entities.json")))
let ctxj = doc.RootElement.GetProperty("entity_ctx")
let gi (e: JsonElement) (k: string) = e.GetProperty(k).GetInt32()
let ctx : Sprites.EntityCtx =
    { Yaw = gi ctxj "yaw"; Anim = (gi ctxj "anim" <> 0); SelGroup = gi ctxj "sel_group"
      TileOff = Season.treeTileOffset (gi ctxj "season"); RotPhase = gi ctxj "rot_phase"; Zoom = 4
      SheetProp32 = [||]; SheetProp16 = [||]
      Sheet33 = File.ReadAllBytes(Path.Combine(assets, ctxj.GetProperty("sheet33").GetString()))
      SheetProp = File.ReadAllBytes(Path.Combine(assets, ctxj.GetProperty("sheet_prop").GetString()))
      Seed = (match ctxj.TryGetProperty "seed" with | true, v -> int (v.GetInt64()) | _ -> 0)
      Ram = [||] }
let recs =
    [| for e in doc.RootElement.GetProperty("render_entities").EnumerateArray() ->
        ({ B6 = gi e "b6"; B5 = gi e "b5"; B7 = gi e "b7"; B14 = gi e "b14"
           B17 = gi e "b17"; B31 = gi e "b31"; Fx = gi e "fx"; Fy = gi e "fy"
           Addr = gi e "addr"; Group = gi e "group"
           Wcx = gi e "wcx"; Wcy = gi e "wcy"; B15 = 0; B32 = 0; W18 = 0; Icons = 0; B33 = 0; B44 = 0; B16 = 0; W12 = 0 } : Sprites.EntityRec) |]
let ecx, ecy, eyaw = gi ctxj "cam_x", gi ctxj "cam_y", gi ctxj "yaw"
let p = Projection.Params.Mission1.WithYaw(eyaw / 16)
let corners = Projection.projectGrid p map ecx ecy
let ebuf = Fill.Buffer.Create()
Sprites.drawEntitiesArr ebuf ctx corners ecx ecy recs
// entities.json holds the whole map (276 records); the count printed is the 53 in
// the 11 x 11 window around the camera
let nearby = recs |> Array.filter (fun r -> r.Wcx >= ecx - 1 && r.Wcx <= ecx + 9 && r.Wcy >= ecy - 1 && r.Wcy <= ecy + 9)
out.Add(sprintf "entities-only cam=%d,%d yaw=%d recs=%d px=%d %s" ecx ecy eyaw nearby.Length (covered ebuf) (hash ebuf))
let fbuf = Fill.Buffer.Create()
Fill.walk fbuf dith corners map ecx ecy 0 (eyaw / 16)
Sprites.drawEntitiesArr fbuf ctx corners ecx ecy recs
out.Add(sprintf "terrain-then-entities px=%d %s" (covered fbuf) (hash fbuf))

let target = fsi.CommandLineArgs |> Array.tryItem 1 |> Option.defaultValue "baseline.txt"
File.WriteAllLines(target, out)
printfn "%d lines -> %s" out.Count target
