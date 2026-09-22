/// Slow-motion replay of one PowerMonger frame.
///
/// Scene.steps gives the frame as the game draws it: for each cell, far to
/// near, two terrain triangles and then that cell's sprites. Each step is
/// drawn once into a logging buffer, which records every pixel write in the
/// order the port makes it: the $e420 span walker fills a triangle one
/// scanline at a time, top down, left to right, and the sprite blitters copy
/// rows top down. So the frame can be rebuilt to any point, down to a single
/// pixel, and scrubbed backwards as easily as forwards.
///
/// The ST itself writes 16-pixel words per bitplane ($e420) and byte-wide
/// rows ($11f82), so pixel-by-pixel playback is finer than the hardware ever
/// drew; the order of spans and rows is the game's.
module PmStepper.Replay

open PmLogic

let W, H = Fill.ScreenWidth, Fill.ScreenHeight

/// One pixel write: position in the raw $3f364 screen space, palette index.
[<Struct>]
type Write = { X: int; Y: int; Index: byte }

/// The camera and the season: what a frame is built for, apart from the tick.
type View =
    { CamX: int                      // top-left cell of the drawn window
      CamY: int
      YawSteps: int                  // 0..15, [$ff9a] >> 4
      Zoom: int                      // 1..7, [$57ffc]: the window is 2 * Zoom cells square
      DitherPhase: int               // 0 or 64: flips on every camera change ($f8e4)
      Season: int }                  // 0..3, word[$57fd0] / 2 (Season.fs)

type Frame =
    { View: View
      Ctx: Sprites.EntityCtx         // per-frame sprite constants, yaw and tree set included
      Corners: Projection.Corner[,]
      Steps: Scene.Step[]
      Rasters: Fill.Raster option[]  // what $ef62 did, for triangle steps
      Writes: Write[][] }            // Writes.[i] = the pixels Steps.[i] writes, in order

/// Draw one step alone and keep its write log.
let private record (dith: byte[]) (ctx: Sprites.EntityCtx) (tick: int) (step: Scene.Step) =
    let buf = Fill.Buffer.Logged()
    let raster = Scene.drawStep buf dith tick ctx step
    let writes =
        [| for packed in buf.Log.Value ->
             let i = packed >>> 8
             { X = i % W; Y = i / W; Index = byte (packed &&& 0xFF) } |]
    raster, writes

/// Build the replay for one view. Sprites come from the whole map's bucket
/// walk, so any window has its own: positions come from the cell's projected
/// corners, the tree jitter from the cell's place in the window, and the yaw
/// only picks men's and animals' facing frames. The season picks the grass
/// colours and the tree frames together.
let build (a: Load.Assets) (v: View) (tick: int) : Frame =
    let p = Projection.Params.Mission1.WithYaw(v.YawSteps).WithZoom(v.Zoom)
    let corners = Projection.projectGrid p a.Map v.CamX v.CamY
    let ctx = { a.EntityCtx with Yaw = v.YawSteps * 16; Zoom = v.Zoom; TileOff = Season.treeTileOffset v.Season }
    let dith = Fill.withPhase (Season.table a.Dither v.Season) v.DitherPhase
    let steps = Scene.steps ctx (Fill.plan corners a.Map v.CamX v.CamY v.YawSteps) a.Entities
    let recorded = steps |> Array.map (record dith ctx tick)
    { View = v; Ctx = ctx; Corners = corners
      Steps = steps
      Rasters = Array.map fst recorded
      Writes = Array.map snd recorded }

// -- where playback is ---------------------------------------------------

/// `Step` steps are finished and `Pixel` pixels of the next one are drawn.
[<Struct>]
type Cursor = { Step: int; Pixel: int }

let start = { Step = 0; Pixel = 0 }
let finish (f: Frame) = { Step = f.Steps.Length; Pixel = 0 }
let isFinished (f: Frame) (c: Cursor) = c.Step >= f.Steps.Length

/// Advance by `n` pixel writes, carrying across step boundaries. Steps that
/// write nothing (a triangle clipped away, say) are passed over.
let advance (f: Frame) (n: int) (c: Cursor) : Cursor =
    let mutable step, pixel, left = c.Step, c.Pixel, n
    while step < f.Steps.Length && left >= f.Writes.[step].Length - pixel do
        left <- left - (f.Writes.[step].Length - pixel)
        step <- step + 1
        pixel <- 0
    if step < f.Steps.Length then { Step = step; Pixel = pixel + left } else finish f

/// How much one keypress steps over.
type Chunk =
    | Shape         // one triangle or one sprite
    | Cell          // a cell: its two triangles, then its sprites
    | Strip         // one pass of the walk's outer loop: 2 * zoom cells

let private chunkOf (f: Frame) (chunk: Chunk) (i: int) =
    match chunk with
    | Shape -> i
    | Cell -> (Scene.cellOf f.Steps.[i]).Order
    | Strip -> (Scene.cellOf f.Steps.[i]).Strip

/// Jump to the end of the chunk being drawn.
let forward (f: Frame) (chunk: Chunk) (c: Cursor) : Cursor =
    if isFinished f c then c
    else
        let k = chunkOf f chunk c.Step
        let mutable b = c.Step + 1
        while b < f.Steps.Length && chunkOf f chunk b = k do b <- b + 1
        { Step = b; Pixel = 0 }

/// Jump back to the start of the chunk last drawn into, or to the start of
/// the one before it if already at a boundary.
let back (f: Frame) (chunk: Chunk) (c: Cursor) : Cursor =
    let last = if c.Pixel > 0 then c.Step else c.Step - 1
    if last < 0 then start
    else
        let k = chunkOf f chunk last
        let mutable b = last
        while b > 0 && chunkOf f chunk (b - 1) = k do b <- b - 1
        { Step = b; Pixel = 0 }

/// Pixel writes up to the cursor, and in the whole frame (for a progress bar).
let written (f: Frame) (c: Cursor) =
    (Array.sumBy Array.length f.Writes.[.. c.Step - 1]) + c.Pixel
let total (f: Frame) = Array.sumBy Array.length f.Writes

/// Replay every write up to the cursor into `idx` (palette index per pixel,
/// -1 where nothing has been drawn yet).
let composeInto (idx: int[]) (f: Frame) (c: Cursor) =
    System.Array.Fill(idx, -1)
    let put (w: Write) = idx.[w.Y * W + w.X] <- int w.Index
    for s in 0 .. (min c.Step f.Steps.Length) - 1 do
        Array.iter put f.Writes.[s]
    if c.Step < f.Steps.Length then
        for p in 0 .. c.Pixel - 1 do put f.Writes.[c.Step].[p]

/// What a sprite record is, by its dispatch byte (record byte 6, SPEC.md §6).
let spriteKind (b6: int) =
    match b6 with
    | 0 -> "man"
    | 4 -> "building / tree"
    | 6 | 24 -> "settlement marker"
    | 8 -> "animal"
    | 14 -> "banner / group member"
    | 26 -> "faction marker"
    | 28 -> "marker"
    | n -> sprintf "byte6 %d" n
