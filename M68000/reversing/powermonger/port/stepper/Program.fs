/// PowerMonger frame stepper: replays one iso frame the way the game draws
/// it, a triangle or sprite at a time, in slow motion. Mibo (raylib) host.
///
///   dotnet run                          window
///   dotnet run -- --selfcheck           headless: replay == Scene.render
///   dotnet run -- --export <dir> [cell|strip|shape]
///                                       headless: one PNG per chunk boundary
///   dotnet run -- --shot <png> <step> [g] [n] [yN]
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
    { StartStep: int; Grid: bool; Order: bool; Yaw: int option; ShotFile: string option }

let private init (a: Load.Assets) (o: LaunchOptions) (_: GameContext) =
    // starting at another yaw is one camera change away, so one phase flip
    let yaw = defaultArg o.Yaw a.EntityYawSteps
    let f = Replay.build a a.EntityCamX a.EntityCamY yaw (if yaw = a.EntityYawSteps then 0 else 64) 0
    struct ({ Assets = a; Frame = f; Cursor = { Step = min o.StartStep f.Steps.Length; Pixel = 0 }
              Playing = false; Speed = 1500.0; Carry = 0.0; ShowGrid = o.Grid; ShowOrder = o.Order; ShowBackdrop = true
              Shot = o.ShotFile |> Option.map (fun file -> file, 0) },
            Cmd.none)

/// A camera change re-projects, and $f898 flips the dither phase when it does.
let private rotate (m: Model) (by: int) =
    let f = Replay.build m.Assets m.Frame.CamX m.Frame.CamY ((m.Frame.YawSteps + by + 16) % 16)
                (m.Frame.DitherPhase ^^^ 64) 0
    { m with Frame = f; Cursor = Replay.start; Playing = false; Carry = 0.0 }

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

/// The explanation panel: where the walk is and what the current step is.
let private describe (m: Model) =
    let f, c = m.Frame, m.Cursor
    let head =
        [ "PowerMonger frame replay"
          sprintf "camera cell (%d,%d)   yaw %d/16 (%s, handler q%d)"
              f.CamX f.CamY f.YawSteps (hex2 (f.YawSteps * 16)) (Fill.quadrant f.YawSteps)
          (if f.HasSprites then sprintf "sprites: %d records at this camera cell" m.Assets.Entities.Length
           else sprintf "sprites: none here, only at camera cell (%d,%d)" m.Assets.EntityCamX m.Assets.EntityCamY)
          sprintf "dither phase %d (flips on every camera change, $f8e4)" f.DitherPhase
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
                [ sprintf "cell (%d,%d): cell %d of 64 in the walk" cell.X cell.Y (cell.Order + 1)
                  sprintf "  strip %d of 8, cell %d of 8 in the strip" (cell.Strip + 1) (cell.InStrip + 1)
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
          "PgDn / PgUp       one strip (8 cells)"
          "Home / End        start / finish"
          "+ / -             speed"
          "Q / E             rotate the camera"
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
        let current = if Replay.isFinished f c then 64 else (Scene.cellOf f.Steps.[c.Step]).Order
        for cell in Fill.plan f.Corners m.Assets.Map f.CamX f.CamY f.YawSteps do
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
    for yaw in 0 .. 15 do
        let f = Replay.build a a.EntityCamX a.EntityCamY yaw (yaw % 2 * 64) 0
        let buf = Fill.Buffer.Create()
        Scene.render buf (Fill.withPhase a.Dither f.DitherPhase) 0 f.Ctx f.Corners a.Map f.CamX f.CamY yaw
            (if f.HasSprites then a.Entities else [||])
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
        printfn "yaw %2d  steps %3d  writes %5d  replay==render %b  forward/back round trip %b"
            yaw f.Steps.Length (Replay.total f) same roundTrip
    if failures = 0 then 0 else 1

/// One PNG per chunk boundary, at the window's 3x scale, for GIFs / the post.
let private export (a: Load.Assets) (dir: string) (chunk: Chunk) =
    Directory.CreateDirectory dir |> ignore
    let f = Replay.build a a.EntityCamX a.EntityCamY a.EntityYawSteps 0 0
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
    | [] -> runWindow a { StartStep = 0; Grid = false; Order = false; Yaw = None; ShotFile = None }
    | "--shot" :: png :: step :: flags ->
        let yaw = flags |> List.tryPick (fun f -> if f.StartsWith "y" then Some(int f.[1..] % 16) else None)
        runWindow a { StartStep = int step; Grid = List.contains "g" flags; Order = List.contains "n" flags
                      Yaw = yaw; ShotFile = Some(Path.GetFullPath png) }
    | _ ->
        eprintfn "usage: PmStepper [--selfcheck | --export <dir> [cell|strip|shape] | --shot <png> <step> [g] [n] [yN]]"
        2
