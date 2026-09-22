/// PowerMonger frame stepper: replays one iso frame the way the game draws
/// it, a triangle or sprite at a time, in slow motion. Mibo (raylib) host.
///
///   dotnet run                          window
///   dotnet run -- --selfcheck           headless: replay == Scene.render
///   dotnet run -- --export <dir> [cell|strip|shape]
///                                       headless: one PNG per chunk boundary
///   dotnet run -- --shot <png> <step> [g] [n] [yN] [sN] [zN] [cX,Y]
///                                       window at a step, screenshot, exit
module PmStepper.Program

open System
open System.IO
open System.Numerics
open Raylib_cs
open Mibo.Elmish
open Mibo.Elmish.Graphics
open Mibo.Elmish.Graphics2D
open Mibo.Input
open PmLogic
open PmStepper.Replay

let private W, H = Replay.W, Replay.H
let private Scale = 3.0f
let private Origin = Vector2(16.0f, 16.0f)
let private PanelX = Origin.X + float32 W * Scale + 24.0f
let private Background = Color(byte 24, byte 26, byte 32, byte 255)

let private assetsDir = Path.GetFullPath(Path.Combine(__SOURCE_DIRECTORY__, "..", "assets"))

/// raylib writes screenshots into the working directory, under this name.
let private shotName (path: string) =
    match Path.GetFileName path with
    | null -> path
    | name -> name

// ===========================================================================
// Model / update
// ===========================================================================

type Model =
    { Assets: Load.Assets
      Frame: Frame
      Cursor: Cursor
      Playing: bool
      Speed: float                     // pixel writes per second
      Carry: float                     // fractional writes owed from the last tick
      ShowGrid: bool                   // the projected 9x9 corner grid
      ShowOrder: bool                  // each cell's position in the walk
      ShowBackdrop: bool               // the $78000 master behind the island
      Shot: (string * int) option }    // --shot: file, frames rendered so far

type Msg =
    | Tick of GameTime
    | Key of KeyCode

type LaunchOptions =
    { StartStep: int; Grid: bool; Order: bool
      Yaw: int option; Season: int option; Zoom: int option; Cam: (int * int) option
      ShotFile: string option }

    /// Open on the captured view, at the first step.
    static member Default =
        { StartStep = 0; Grid = false; Order = false
          Yaw = None; Season = None; Zoom = None; Cam = None; ShotFile = None }

/// Keep the window's corner grid, (2 * zoom + 1) square from the top-left
/// cell, inside the 64 x 128 map.
let private clampCam (zoom: int) (x: int, y: int) =
    Math.Clamp(x, 0, Terrain.Width - 1 - 2 * zoom), Math.Clamp(y, 0, Terrain.Height - 1 - 2 * zoom)

/// The view the records were captured in, with any of its parts overridden.
/// The season defaults to the capture's: the tree frames in entities.json
/// are that season's.
let private startView (a: Load.Assets) (o: LaunchOptions) : Replay.View =
    let yaw = defaultArg o.Yaw a.EntityYawSteps
    let zoom = defaultArg o.Zoom a.EntityZoom
    // at another zoom, the window keeps the capture's centre cell, as $13f60 does
    let centred = a.EntityCamX + a.EntityZoom - zoom, a.EntityCamY + a.EntityZoom - zoom
    let camX, camY = clampCam zoom (defaultArg o.Cam centred)
    // starting anywhere else is one camera change away, so one phase flip
    let moved = (yaw, zoom, camX, camY) <> (a.EntityYawSteps, a.EntityZoom, a.EntityCamX, a.EntityCamY)
    { CamX = camX; CamY = camY; YawSteps = yaw; Zoom = zoom
      DitherPhase = (if moved then 64 else 0); Season = defaultArg o.Season a.EntitySeason }

let private init (a: Load.Assets) (o: LaunchOptions) (_: GameContext) =
    let f = Replay.build a (startView a o) 0
    struct ({ Assets = a; Frame = f; Cursor = { Step = min o.StartStep f.Steps.Length; Pixel = 0 }
              Playing = false; Speed = 1500.0; Carry = 0.0; ShowGrid = o.Grid; ShowOrder = o.Order; ShowBackdrop = true
              Shot = o.ShotFile |> Option.map (fun file -> file, 0) },
            Cmd.none)

/// Rebuild the replay for a new view and rewind to its start.
let private withView (m: Model) (v: Replay.View) =
    { m with Frame = Replay.build m.Assets v 0; Cursor = Replay.start; Playing = false; Carry = 0.0 }

/// A camera change re-projects, and $f898 flips the dither phase when it does.
let private rotate (m: Model) (by: int) =
    let v = m.Frame.View
    withView m { v with YawSteps = (v.YawSteps + by + 16) % 16; DitherPhase = v.DitherPhase ^^^ 64 }

/// Move the camera by whole cells, keeping the corner grid on the map.
/// A move is a camera change: re-project, flip the phase.
let private pan (m: Model) (dx: int) (dy: int) =
    let v = m.Frame.View
    let x, y = clampCam v.Zoom (v.CamX + dx, v.CamY + dy)
    if x = v.CamX && y = v.CamY then m
    else withView m { v with CamX = x; CamY = y; DitherPhase = v.DitherPhase ^^^ 64 }

/// One zoom step, as the game's own zoom buttons do ($1338e / $133a0: +-1,
/// clamped to 1..7, then $13f60). The game keeps the centre cell
/// ($4bb3a/$4bb3c) and draws from centre - zoom, so the top-left cell moves
/// by the change in zoom. A zoom change re-projects: flip the phase.
let private zoom (m: Model) (by: int) =
    let v = m.Frame.View
    let z = Math.Clamp(v.Zoom + by, 1, 7)
    if z = v.Zoom then m
    else
        let x, y = clampCam z (v.CamX + v.Zoom - z, v.CamY + v.Zoom - z)
        withView m { v with Zoom = z; CamX = x; CamY = y; DitherPhase = v.DitherPhase ^^^ 64 }

/// The next season. Not a camera change, so the phase stays.
let private nextSeason (m: Model) =
    let v = m.Frame.View
    withView m { v with Season = (v.Season + 1) % 4 }

let private update (msg: Msg) (m: Model) =
    let move f = struct ({ m with Cursor = f m.Frame m.Cursor; Playing = false; Carry = 0.0 }, Cmd.none)
    let set m' = struct (m', Cmd.none)
    match msg with
    | Tick _ when m.Shot.IsSome ->
        // a few frames in, so the window has presented the view at least once
        let file, frames = m.Shot.Value
        if frames = 5 then Raylib.TakeScreenshot(shotName file)
        struct ({ m with Shot = Some(file, frames + 1) }, if frames >= 6 then Cmd.signalExit else Cmd.none)
    | Tick gt when m.Playing ->
        let owed = m.Carry + m.Speed * gt.ElapsedGameTime.TotalSeconds
        let n = int owed
        let c = Replay.advance m.Frame n m.Cursor
        set { m with Cursor = c; Carry = owed - float n; Playing = not (Replay.isFinished m.Frame c) }
    | Tick _ -> set m
    | Key KeyCode.Space ->
        let c = if Replay.isFinished m.Frame m.Cursor then Replay.start else m.Cursor
        set { m with Cursor = c; Playing = not m.Playing; Carry = 0.0 }
    | Key KeyCode.Right -> move (fun f c -> Replay.forward f Shape c)
    | Key KeyCode.Left -> move (fun f c -> Replay.back f Shape c)
    | Key KeyCode.Down -> move (fun f c -> Replay.forward f Cell c)
    | Key KeyCode.Up -> move (fun f c -> Replay.back f Cell c)
    | Key KeyCode.PageDown -> move (fun f c -> Replay.forward f Strip c)
    | Key KeyCode.PageUp -> move (fun f c -> Replay.back f Strip c)
    | Key KeyCode.Home -> move (fun _ _ -> Replay.start)
    | Key KeyCode.End -> move (fun f _ -> Replay.finish f)
    | Key (KeyCode.Equal | KeyCode.KpAdd) -> set { m with Speed = min 64000.0 (m.Speed * 2.0) }
    | Key (KeyCode.Minus | KeyCode.KpSubtract) -> set { m with Speed = max 25.0 (m.Speed / 2.0) }
    | Key KeyCode.Q -> set (rotate m -1)
    | Key KeyCode.E -> set (rotate m 1)
    | Key KeyCode.Y -> set (nextSeason m)
    | Key KeyCode.W -> set (pan m 0 -1)
    | Key KeyCode.S -> set (pan m 0 1)
    | Key KeyCode.A -> set (pan m -1 0)
    | Key KeyCode.D -> set (pan m 1 0)
    | Key KeyCode.LeftBracket -> set (zoom m -1)
    | Key KeyCode.RightBracket -> set (zoom m 1)
    | Key KeyCode.G -> set { m with ShowGrid = not m.ShowGrid }
    | Key KeyCode.N -> set { m with ShowOrder = not m.ShowOrder }
    | Key KeyCode.B -> set { m with ShowBackdrop = not m.ShowBackdrop }
    | Key KeyCode.Escape -> struct (m, Cmd.signalExit)
    | Key _ -> set m

// ===========================================================================
// View
// ===========================================================================

/// The frame texture and the scratch arrays that fill it. A cache of
/// (Frame, Cursor), not model state; made once the window exists.
type private Screen =
    { Texture: Texture2D
      Idx: int[]                       // composed palette indices
      Rgba: byte[] }                   // texture upload

let private createScreen () =
    let img = Raylib.GenImageColor(W, H, Background)
    let tex = Raylib.LoadTextureFromImage img
    Raylib.UnloadImage img
    Raylib.SetTextureFilter(tex, TextureFilter.Point)
    { Texture = tex; Idx = Array.zeroCreate (W * H); Rgba = Array.zeroCreate (W * H * 4) }

let inline private ly (n: int) : int<RenderLayer> = LanguagePrimitives.Int32WithMeasure n
let private rgba r g b a = Mibo.Color.create (byte r) (byte g) (byte b) (byte a)
let private text (r, g, b) = rgba r g b 255

/// The game draws the island 64 px in from the screen's left edge, past the
/// HUD strip: screen x = raw $3f364 x + 64.
let private Inset = 64

/// Raw $3f364 coordinates -> window pixels.
let private toScreen (x: float) (y: float) =
    Origin + Vector2(float32 (x + float Inset) * Scale, float32 y * Scale)

/// Palette index shown at screen pixel (sx, sy): the replayed frame where it
/// has drawn, else the $78000 backdrop (if shown), else -1 for none.
let private screenIndex (a: Load.Assets) (idx: int[]) (backdrop: bool) (sx: int) (sy: int) =
    let raw = sx - Inset
    if raw >= 0 && idx.[sy * W + raw] >= 0 then idx.[sy * W + raw]
    elif backdrop && a.Backdrop.Length > 0 then int a.Backdrop.[sy * W + sx]
    else -1
let private corner (p: Projection.Corner) = toScreen p.X p.Y
let private quadOutline (q: Fill.Quad) =
    [| corner q.C00; corner q.C10; corner q.C11; corner q.C01; corner q.C00 |]

let private hex2 (n: int) = sprintf "$%02x" n

/// What each season's grass source looks like (Season.fs).
let private seasonName (season: int) =
    [| "khaki and rock"; "green"; "green, brown and gold"; "green" |].[season]

/// The explanation panel: where the walk is and what the current step is.
let private describe (m: Model) =
    let f, c = m.Frame, m.Cursor
    let v = f.View
    let head =
        [ "PowerMonger frame replay"
          sprintf "camera cell (%d,%d)   yaw %d/16 (%s, handler q%d)"
              v.CamX v.CamY v.YawSteps (hex2 (v.YawSteps * 16)) (Fill.quadrant v.YawSteps)
          sprintf "zoom %d: %d x %d cells, cell size %d, %s trees"
              v.Zoom (2 * v.Zoom) (2 * v.Zoom) Projection.zoomScale.[v.Zoom]
              (let s, _ = Sprites.propSheet f.Ctx in sprintf "%dx%d" s.W s.H)
          sprintf "sprites: %d drawn in this window, of %d records on the map"
              (f.Steps |> Array.sumBy (function
                  | Scene.Sprite(cell, r) when (Scene.placement f.Ctx cell r).IsSome -> 1
                  | _ -> 0))
              m.Assets.Entities.Length
          sprintf "season %d (word[$57fd0] = %d): %s, trees +%d"
              v.Season (2 * v.Season) (seasonName v.Season) (Season.treeTileOffset v.Season)
          sprintf "dither phase %d (flips on every camera change, $f8e4)" v.DitherPhase
          sprintf "step %d / %d    pixels %d / %d" (min (c.Step + 1) f.Steps.Length) f.Steps.Length
              (Replay.written f c) (Replay.total f)
          sprintf "%s   %.0f px/s" (if m.Playing then "PLAYING" else "paused") m.Speed
          "" ]
    let now =
        if Replay.isFinished f c then [ "frame complete" ]
        else
            let step = f.Steps.[c.Step]
            let cell = Scene.cellOf step
            let q = cell.Quad
            let px = f.Writes.[c.Step].Length
            let where =
                let n = 2 * v.Zoom
                [ sprintf "cell (%d,%d): cell %d of %d in the walk" cell.X cell.Y (cell.Order + 1) (n * n)
                  sprintf "  strip %d of %d, cell %d of %d in the strip" (cell.Strip + 1) n (cell.InStrip + 1) n
                  sprintf "  split on %s (flag bit 7 %s)"
                      (if q.Diagonal then "C10-C01" else "C00-C11") (if q.Diagonal then "set" else "clear")
                  sprintf "  type byte %s, height byte %s" (hex2 q.TypeByte) (hex2 q.HeightByte) ]
            let what =
                match step, f.Rasters.[c.Step] with
                | Scene.Triangle(_, nth, t), Some raster ->
                    let plane =
                        if q.TypeByte = q.HeightByte then "the type = height plane"
                        elif t.Colour = q.TypeByte then "the type plane"
                        else "the height plane"
                    [ yield sprintf "drawing triangle %d of 2" nth
                      yield sprintf "  colour byte %s from %s" (hex2 t.Colour) plane
                      match raster with
                      | Fill.Skipped reason -> yield sprintf "  not drawn: %s" reason
                      | Fill.Walked(colour, rows, aborted) ->
                          if colour <> t.Colour then
                              yield sprintf "  drawn as %s: winding came out reversed" (hex2 colour)
                              yield "  (faces away; nearer terrain usually covers it)"
                          if t.Colour < 0x0c then
                              yield "  water: the game adds a 0..3 tick to shimmer"
                          match aborted with
                          | Some row -> yield sprintf "  span walk gave up at row %d of %d" row rows
                          | None -> yield sprintf "  %d scanlines" rows
                          yield (if px = 0 then "  0 px: clipped, off the iso window"
                                 else sprintf "  %d px" px) ]
                | Scene.Sprite(_, r), _ ->
                    [ yield sprintf "drawing sprite: %s (record byte6 %d)" (Replay.spriteKind r.B6) r.B6
                      yield "  after this cell's triangles, before the next cell"
                      match Scene.placement f.Ctx cell r with
                      | Some p ->
                          yield sprintf "  frame %s of the %s sheet" (hex2 p.Frame)
                                    (if p.IsProp then "32x24 $37c7c" else "8x11 $33000")
                          yield sprintf "  anchor: %s" p.Rule
                      | None -> ()
                      yield sprintf "  %d px" px ]
                | _ -> []
            where @ [ "" ] @ what
    let keys =
        [ ""; "Space  play / pause"
          "Right / Left      one triangle or sprite"
          "Down / Up         one cell"
          "PgDn / PgUp       one strip (an outer-loop pass)"
          "Home / End        start / finish"
          "+ / -             speed"
          "W / A / S / D     move the camera a cell"
          "[ / ]             zoom in / out"
          "Q / E             rotate the camera"
          "Y                 next season"
          "G  corner grid    N  visit order"
          "B  backdrop on / off"
          "Esc  quit" ]
    String.Join("\n", head @ now @ keys)

let private view (screen: Screen) (_: GameContext) (m: Model) (buffer: RenderBuffer2D) =
    let f, c = m.Frame, m.Cursor
    let font = Raylib.GetFontDefault()
    let fw, fh = float32 W * Scale, float32 H * Scale

    // the frame so far, as a texture
    Replay.composeInto screen.Idx f c
    for i in 0 .. screen.Idx.Length - 1 do
        let r, g, b =
            match screenIndex m.Assets screen.Idx m.ShowBackdrop (i % W) (i / W) with
            | -1 -> Background.R, Background.G, Background.B
            | v -> m.Assets.Palette.[v &&& 0x0f]
        screen.Rgba.[i * 4] <- r
        screen.Rgba.[i * 4 + 1] <- g
        screen.Rgba.[i * 4 + 2] <- b
        screen.Rgba.[i * 4 + 3] <- 255uy
    buffer
        .drawImmediate((fun () -> Raylib.UpdateTexture(screen.Texture, screen.Rgba)), ly 0)
        .sprite({ SpriteState.create (screen.Texture, Rectangle(Origin.X, Origin.Y, fw, fh),
                                      Rectangle(0.0f, 0.0f, float32 W, float32 H))
                  with Layer = ly 0 })
        .rectOutline(Origin.X - 1.0f, Origin.Y - 1.0f, fw + 2.0f, fh + 2.0f, rgba 80 84 96 255, layer = ly 1)
        .drop()

    if m.ShowGrid then
        let n = Array2D.length1 f.Corners
        for r in 0 .. n - 1 do
            for k in 0 .. n - 2 do
                buffer
                    .line(corner f.Corners.[r, k], corner f.Corners.[r, k + 1], rgba 255 255 255 70, layer = ly 2)
                    .line(corner f.Corners.[k, r], corner f.Corners.[k + 1, r], rgba 255 255 255 70, layer = ly 2)
                    .drop()

    if m.ShowOrder then
        let current = if Replay.isFinished f c then Int32.MaxValue else (Scene.cellOf f.Steps.[c.Step]).Order
        for cell in Fill.plan f.Corners m.Assets.Map f.View.CamX f.View.CamY f.View.YawSteps do
            let q = cell.Quad
            let mid = (corner q.C00 + corner q.C10 + corner q.C01 + corner q.C11) / 4.0f
            let col =
                if cell.Order < current then (150, 150, 160)
                elif cell.Order = current then (255, 230, 90)
                else (235, 235, 245)
            buffer.text(font, string (cell.Order + 1), mid - Vector2(6.0f, 6.0f), 14.0f,
                        tint = text col, layer = ly 3).drop()

    // the step being drawn: its cell, and the triangle or sprite itself
    if not (Replay.isFinished f c) then
        let step = f.Steps.[c.Step]
        let cell = Scene.cellOf step
        buffer.lineStrip(quadOutline cell.Quad, rgba 255 255 255 150, layer = ly 4).drop()
        match step with
        | Scene.Triangle(_, _, t) ->
            let a, b, cc = corner t.A, corner t.B, corner t.C
            buffer.lineStrip([| a; b; cc; a |], rgba 255 220 60 255, layer = ly 5).drop()
        | Scene.Sprite(_, r) ->
            match Scene.placement f.Ctx cell r with
            | Some p ->
                // the whole frame the blitter copies (transparent pixels too),
                // and the anchor point its position was computed from
                let tl = toScreen (float p.X) (float p.Y)
                let anchor = toScreen (float p.AnchorX) (float p.AnchorY)
                buffer
                    .rectOutline(tl.X, tl.Y, float32 p.W * Scale, float32 p.H * Scale,
                                 rgba 90 220 255 255, thickness = 2.0f, layer = ly 5)
                    .fillCircle(anchor, 4.0f, rgba 255 90 90 255, layer = ly 5)
                    .drop()
            | None -> ()

    // progress bar under the frame, then the explanation panel
    let barY = Origin.Y + fh + 10.0f
    let frac = float32 (Replay.written f c) / float32 (max 1 (Replay.total f))
    buffer
        .fillRect(Origin.X, barY, fw, 8.0f, rgba 50 54 64 255, layer = ly 1)
        .fillRect(Origin.X, barY, fw * frac, 8.0f, rgba 255 220 60 255, layer = ly 2)
        .text(font, describe m, Vector2(PanelX, Origin.Y), 18.0f, tint = text (230, 232, 238), layer = ly 6)
        .drop()

let private subscribe (ctx: GameContext) (_: Model) = Keyboard.onPressed Key ctx

let private runWindow (a: Load.Assets) (o: LaunchOptions) =
    let program =
        Program.mkProgram (init a o) update
        |> Program.withConfig (fun cfg ->
            { cfg with
                Width = int PanelX + 480
                Height = int (Origin.Y * 2.0f + float32 H * Scale) + 30
                TargetFPS = ValueSome 60
                Title = "PowerMonger frame replay" })
        |> Program.withInput
        |> Program.withSubscription subscribe
        |> Program.withTick Tick
        |> Program.withRenderer (fun () ->
            let screen = createScreen ()
            Renderer2D.createWith { Renderer2DConfig.defaults with ClearColor = ValueSome Background } (view screen))
    let game = new RaylibGame<Model, Msg>(program)
    game.Run()
    match o.ShotFile with
    | Some dest when File.Exists(shotName dest) ->
        File.Move(shotName dest, dest, true)
        printfn "screenshot -> %s" dest
    | _ -> ()
    0

// ===========================================================================
// Headless modes
// ===========================================================================

/// The replay must end on exactly the frame Scene.render draws, and stepping
/// forward then back by any chunk must land where it started.
let private selfCheck (a: Load.Assets) =
    let mutable failures = 0
    // all 16 yaws at the capture's zoom, then every zoom around the capture's
    // centre cell; every season, both phases and every zoom appear
    let centreX, centreY = a.EntityCamX + a.EntityZoom, a.EntityCamY + a.EntityZoom
    let views : Replay.View list =
        [ for yaw in 0 .. 15 ->
            { CamX = a.EntityCamX; CamY = a.EntityCamY; YawSteps = yaw; Zoom = a.EntityZoom
              DitherPhase = yaw % 2 * 64; Season = (yaw >>> 1) &&& 3 }
          for z in 1 .. 7 ->
            let x, y = clampCam z (centreX - z, centreY - z)
            { CamX = x; CamY = y; YawSteps = (2 * z + 1) % 16; Zoom = z; DitherPhase = z % 2 * 64; Season = z % 4 } ]
    for v in views do
        let yaw = v.YawSteps
        let f = Replay.build a v 0
        let buf = Fill.Buffer.Create()
        Scene.render buf (Fill.withPhase (Season.table a.Dither v.Season) v.DitherPhase) 0 f.Ctx f.Corners a.Map
            v.CamX v.CamY yaw a.Entities
        let idx = Array.zeroCreate (W * H)
        Replay.composeInto idx f (Replay.finish f)
        let same =
            Array.forall2 (fun (i: int) (cov: bool, v: byte) -> if cov then i = int v else i = -1)
                idx (Array.zip buf.Covered buf.Index)
        let roundTrip =
            [ Shape; Cell; Strip ] |> List.forall (fun chunk ->
                let mutable cur, ok = Replay.start, true
                while not (Replay.isFinished f cur) do
                    let next = Replay.forward f chunk cur
                    if Replay.back f chunk next <> cur then ok <- false
                    cur <- next
                ok)
        if not (same && roundTrip) then failures <- failures + 1
        printfn "yaw %2d  zoom %d  season %d  steps %3d  writes %5d  replay==render %b  forward/back round trip %b"
            yaw v.Zoom v.Season f.Steps.Length (Replay.total f) same roundTrip
    if failures = 0 then 0 else 1

/// One PNG per chunk boundary, at the window's 3x scale, for GIFs / the post.
let private export (a: Load.Assets) (dir: string) (chunk: Chunk) =
    Directory.CreateDirectory dir |> ignore
    let f =
        Replay.build a (startView a LaunchOptions.Default) 0
    let idx = Array.zeroCreate (W * H)
    let save (n: int) (c: Cursor) =
        Replay.composeInto idx f c
        let mutable img = Raylib.GenImageColor(W, H, Background)
        for i in 0 .. idx.Length - 1 do
            match screenIndex a idx true (i % W) (i / W) with
            | -1 -> ()
            | v ->
                let r, g, b = a.Palette.[v &&& 0x0f]
                Raylib.ImageDrawPixel(&img, i % W, i / W, Color(r, g, b, 255uy))
        Raylib.ImageResizeNN(&img, W * int Scale, H * int Scale)
        Raylib.ExportImage(img, Path.Combine(dir, sprintf "frame_%03d.png" n)) |> ignore
        Raylib.UnloadImage img
    let mutable c, n = Replay.start, 0
    save n c
    while not (Replay.isFinished f c) do
        c <- Replay.forward f chunk c
        n <- n + 1
        save n c
    printfn "%d frames -> %s" (n + 1) dir
    0

[<EntryPoint>]
let main argv =
    let a = Load.load assetsDir
    let chunkNamed = function "strip" -> Some Strip | "shape" -> Some Shape | "cell" -> Some Cell | _ -> None
    match List.ofArray argv with
    | [ "--selfcheck" ] -> selfCheck a
    | [ "--export"; dir ] -> export a dir Cell
    | [ "--export"; dir; name ] when (chunkNamed name).IsSome -> export a dir (chunkNamed name).Value
    | [] -> runWindow a LaunchOptions.Default
    | "--shot" :: png :: step :: flags ->
        // a flag is a letter and a value: y3 (yaw), s1 (season), z6 (zoom), c20,37 (camera cell)
        let valueOf (c: char) = flags |> List.tryPick (fun f -> if f.Length > 1 && f.[0] = c then Some f.[1..] else None)
        let wrapped c n = valueOf c |> Option.map (fun v -> ((int v % n) + n) % n)
        let clamped c lo hi = valueOf c |> Option.map (fun v -> Math.Clamp(int v, lo, hi))
        let cell c = valueOf c |> Option.map (fun v -> let xy = v.Split ',' in int xy.[0], int xy.[1])
        runWindow a { LaunchOptions.Default with
                        StartStep = int step; Grid = List.contains "g" flags; Order = List.contains "n" flags
                        Yaw = wrapped 'y' 16; Season = wrapped 's' 4; Zoom = clamped 'z' 1 7; Cam = cell 'c'
                        ShotFile = Some(Path.GetFullPath png) }
    | _ ->
        eprintfn "usage: PmStepper [--selfcheck | --export <dir> [cell|strip|shape] | --shot <png> <step> [g] [n] [yN] [sN] [zN] [cX,Y]]"
        2
