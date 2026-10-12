// F# half of the real-record entity cross-check: Sprites.drawEntitiesArr on the
// port's entities.json record stream and the $3f364 corners of a frame RAM
// (default scratchpad/pm88_f1.ram), covered pixels in $XCHECK_OUT/ent_fs.txt.
//   dotnet fsi ent_fs.fsx [frame.ram]
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System.Text.Json
open System.IO
let outDir = match System.Environment.GetEnvironmentVariable "XCHECK_OUT" with null | "" -> "." | d -> d

let assets = Path.Combine(__SOURCE_DIRECTORY__, "../../port/assets")
let ramPath = fsi.CommandLineArgs |> Array.tryItem 1 |> Option.defaultValue (Path.Combine(__SOURCE_DIRECTORY__, "../../../../scratchpad/pm88_f1.ram"))
let ram = File.ReadAllBytes ramPath
let u16 a = (int ram.[a] <<< 8) ||| int ram.[a+1]
let u32 a = (int ram.[a] <<< 24) ||| (int ram.[a+1] <<< 16) ||| (int ram.[a+2] <<< 8) ||| int ram.[a+3]

let inset = (u32 0xE3E2 &&& 0x3F) * 2
let inset2 = if inset = 0 then 64 else inset
let camX = u16 0x4BB3A - u16 0x57FFC
let camY = u16 0x4BB3C - u16 0x57FFC
// 9x9 corner buffer, packed (sx<<16)|sy at $3f364 + r*64 + c*4
let mkCorner x y : Projection.Corner = { X = x; Y = y }
let corners = Array2D.init 9 9 (fun r c ->
    let p = u32 (0x3F364 + r*64 + c*4)
    mkCorner (float ((p >>> 16) + inset2)) (float (p &&& 0xFFFF)))

let doc = JsonDocument.Parse(File.ReadAllText(assets + "/entities.json"))
let ctxj = doc.RootElement.GetProperty("entity_ctx")
let gi (e: JsonElement) (k: string) = e.GetProperty(k).GetInt32()
let sheet33 = File.ReadAllBytes(assets + "/sprites/sheet_raw.bin")
let sheetProp = File.ReadAllBytes(assets + "/sprites/prop_sheet_raw.bin")
let ctx : Sprites.EntityCtx =
    { Yaw = gi ctxj "yaw"; Anim = (gi ctxj "anim" <> 0); SelGroup = gi ctxj "sel_group"
      TileOff = Season.treeTileOffset (gi ctxj "season"); RotPhase = gi ctxj "rot_phase"
      Sheet33 = sheet33; SheetProp = sheetProp; Ram = [||]; Zoom = 4; SheetProp32 = [||]; SheetProp16 = [||] }

let mkRec (e: JsonElement) : Sprites.EntityRec =
    { Addr = gi e "addr"; B6 = gi e "b6"; B5 = gi e "b5"; B7 = gi e "b7"; B14 = gi e "b14"
      B17 = gi e "b17"; B31 = gi e "b31"; Fx = gi e "fx"; Fy = gi e "fy"
      Group = gi e "group"
      Wcx = gi e "wcx"; Wcy = gi e "wcy"; B15 = 0; B32 = 0; W18 = 0; Icons = 0; B33 = 0; B44 = 0; B16 = 0; W12 = 0 }
let recs =
    [| for e in doc.RootElement.GetProperty("render_entities").EnumerateArray() -> mkRec e |]

let buf = Fill.Buffer.Create()
Sprites.drawEntitiesArr buf ctx corners camX camY recs

let sb = System.Text.StringBuilder()
for y in 0 .. Fill.ScreenHeight - 1 do
    for x in 0 .. Fill.ScreenWidth - 1 do
        let i = y * Fill.ScreenWidth + x
        if buf.Covered.[i] then sb.AppendLine(sprintf "%d,%d,%d" x y (int buf.Index.[i])) |> ignore
File.WriteAllText(Path.Combine(outDir, "ent_fs.txt"), sb.ToString())
printfn "F#: %d recs, %d covered px, inset=%d cam=(%d,%d)" recs.Length (Seq.filter id buf.Covered |> Seq.length) inset2 camX camY
