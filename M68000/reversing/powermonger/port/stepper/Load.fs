/// Loads the extracted assets (../assets, written by tools/pm_export.py) into
/// the types PmLogic draws with. Same files and fields TerrainView.cs reads.
module PmStepper.Load

open System.IO
open System.Text.Json
open PmLogic

type Assets =
    { Map: Terrain.Map
      Dither: byte[]
      Palette: (byte * byte * byte)[]      // the 16 shifter colours, RGB
      Backdrop: byte[]                     // the $78000 master, screen space; [||] if not exported
      Entities: Sprites.EntityRec[]        // every record in the map's $47970 buckets, one frame
      EntityCtx: Sprites.EntityCtx
      // the view the entity records were captured in (the mission-1 start):
      // the viewer opens here
      EntityCamX: int
      EntityCamY: int
      EntityYawSteps: int
      EntityZoom: int                      // [$57ffc]
      EntitySeason: int }                  // word[$57fd0] / 2: the tree frames are this season's

let load (dir: string) : Assets =
    let file name = Path.Combine(dir, name)
    let palette =
        use doc = JsonDocument.Parse(File.ReadAllText(file "palette.json"))
        let rgb = doc.RootElement.GetProperty("palettes").[0].GetProperty("rgb")
        Array.init 16 (fun i ->
            let c = rgb.[i]
            byte (c.[0].GetInt32()), byte (c.[1].GetInt32()), byte (c.[2].GetInt32()))
    use doc = JsonDocument.Parse(File.ReadAllText(file "entities.json"))
    let root = doc.RootElement
    let ctx = root.GetProperty("entity_ctx")
    let gi (e: JsonElement) (k: string) = e.GetProperty(k).GetInt32()
    // fields added for the later-land categories; older exports lack them
    let gio (e: JsonElement) (k: string) =
        match e.TryGetProperty k with
        | true, v -> v.GetInt32()
        | _ -> 0
    let gs (e: JsonElement) (k: string) =
        match e.GetProperty(k).GetString() with
        | null -> failwithf "entities.json: entity_ctx.%s is null" k
        | s -> s
    let entities =
        [| for e in root.GetProperty("render_entities").EnumerateArray() ->
             ({ Addr = gi e "addr"; B6 = gi e "b6"; B5 = gi e "b5"; B7 = gi e "b7"; B14 = gi e "b14"
                B17 = gi e "b17"; B31 = gi e "b31"; Fx = gi e "fx"; Fy = gi e "fy"
                Group = gi e "group"; Wcx = gi e "wcx"; Wcy = gi e "wcy"
                B15 = gio e "b15"; B32 = gio e "b32"; W18 = gio e "w18"; Icons = gio e "icons"
                B33 = gio e "b33"; B44 = gio e "b44" } : Sprites.EntityRec) |]
    { Map = Terrain.parse (File.ReadAllBytes(file "terrain.bin"))
      Dither = File.ReadAllBytes(file "dither.bin")
      Palette = palette
      Backdrop = (let p = file "backdrop.bin" in if File.Exists p then File.ReadAllBytes p else [||])
      Entities = entities
      EntityCtx =
        { Yaw = gi ctx "yaw"; Anim = gi ctx "anim" <> 0; SelGroup = gi ctx "sel_group"
          TileOff = Season.treeTileOffset (gi ctx "season"); RotPhase = gi ctx "rot_phase"
          Zoom = gi ctx "half"                 // $fdec, equal to the zoom index $57ffc
          Sheet33 = File.ReadAllBytes(file (gs ctx "sheet33"))
          SheetProp = File.ReadAllBytes(file (gs ctx "sheet_prop"))
          SheetProp32 = File.ReadAllBytes(file (gs ctx "sheet_prop32"))
          SheetProp16 = File.ReadAllBytes(file (gs ctx "sheet_prop16"))
          Ram = [||] }
      EntityCamX = gi ctx "cam_x"
      EntityCamY = gi ctx "cam_y"
      EntityYawSteps = gi ctx "yaw" / 16
      EntityZoom = gi ctx "half"
      EntitySeason = gi ctx "season" }
