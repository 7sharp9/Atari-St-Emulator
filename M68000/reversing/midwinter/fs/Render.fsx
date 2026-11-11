/// Pictures of the island: a lit height field, still images and video through ffmpeg.
/// None of this is the game's renderer (its 3D view is not decoded): the look is ours.
module Render

open System
open System.Diagnostics
open Island

type Image = { Width: int; Height: int; Pixels: byte[] }        // RGB, 3 bytes a pixel, rows top first

type Colour = float32 * float32 * float32                         // 0..1

let image w h = { Width = w; Height = h; Pixels = Array.zeroCreate (w * h * 3) }

let inline setPixel (img: Image) x y ((r, g, b): Colour) =
    let i = 3 * (y * img.Width + x)
    let byte' (v: float32) = byte (Math.Clamp(v * 255.0f, 0.0f, 255.0f))
    img.Pixels.[i] <- byte' r; img.Pixels.[i + 1] <- byte' g; img.Pixels.[i + 2] <- byte' b

let lerp (a: float32) b t = a + (b - a) * t
let mix ((r1, g1, b1): Colour) ((r2, g2, b2): Colour) t : Colour = lerp r1 r2 t, lerp g1 g2 t, lerp b1 b2 t

// ---------------------------------------------------------------- the ground

/// A level as heights the renderer can sample: ground height (sea flat at 0) per cell.
type Terrain = { Size: int; Height: float32[,]; Colour: Colour[,] }

let sea: Colour = 0.10f, 0.22f, 0.42f
let snow: Colour = 0.96f, 0.97f, 1.0f
let rock: Colour = 0.42f, 0.45f, 0.52f
let shadow: Colour = 0.36f, 0.44f, 0.62f       // snow in shadow goes blue, not grey

/// Light the ground from a low sun in the north-west: snow by slope, rock where it is steep.
/// `cellSize` is how many height units one cell spans, so slopes come out the same at every level.
let terrain (cellSize: float32) (level: Grid) : Terrain =
    let n = Array2D.length1 level
    let h = Array2D.init n n (fun r c -> float32 (Cell.groundHeight level.[r, c]))
    let at r c = h.[Math.Clamp(r, 0, n - 1), Math.Clamp(c, 0, n - 1)]
    let sx, sy, sz = -0.6f, -0.6f, 0.53f                             // towards the sun (west, north, up)
    let colour r c =
        if h.[r, c] = 0.0f then sea
        else
            let dx = (at r (c + 1) - at r (c - 1)) / (2.0f * cellSize)
            let dy = (at (r + 1) c - at (r - 1) c) / (2.0f * cellSize)
            let len = MathF.Sqrt(dx * dx + dy * dy + 1.0f)
            let nx, ny, nz = -dx / len, -dy / len, 1.0f / len
            let light = max 0.0f (nx * sx + ny * sy + nz * sz) / 0.85f
            let steep = Math.Clamp((1.0f - nz - 0.25f) * 3.0f, 0.0f, 1.0f)
            let ground = mix snow rock steep
            mix shadow ground (Math.Clamp(light, 0.0f, 1.0f))
    { Size = n; Height = h; Colour = Array2D.init n n colour }

/// The terrain from above, one pixel per cell.
let topDown (t: Terrain) : Image =
    let img = image t.Size t.Size
    for r in 0 .. t.Size - 1 do
        for c in 0 .. t.Size - 1 do setPixel img c r t.Colour.[r, c]
    img

let scale (k: int) (src: Image) : Image =
    let img = image (src.Width * k) (src.Height * k)
    for y in 0 .. img.Height - 1 do
        for x in 0 .. img.Width - 1 do
            let i, j = 3 * (y * img.Width + x), 3 * ((y / k) * src.Width + x / k)
            Array.blit src.Pixels j img.Pixels i 3
    img

/// Images side by side with a gap.
let row (gap: int) (images: Image list) : Image =
    let w = (images |> List.sumBy _.Width) + gap * (images.Length - 1)
    let h = images |> List.map _.Height |> List.max
    let img = { image w h with Pixels = Array.create (w * h * 3) 255uy }
    let mutable x0 = 0
    for src in images do
        for y in 0 .. src.Height - 1 do
            Array.blit src.Pixels (3 * y * src.Width) img.Pixels (3 * (y * w + x0)) (3 * src.Width)
        x0 <- x0 + src.Width + gap
    img

// ---------------------------------------------------------------- out through ffmpeg

/// Frames of raw RGB into ffmpeg; `output` is ffmpeg's output arguments.
let encode (w: int) (h: int) (fps: int) (output: string) (frames: seq<Image>) =
    let args = sprintf "-y -loglevel error -f rawvideo -pix_fmt rgb24 -s %dx%d -r %d -i - %s" w h fps output
    let psi = ProcessStartInfo("ffmpeg", args, RedirectStandardInput = true, UseShellExecute = false)
    use p = Process.Start psi
    for f in frames do p.StandardInput.BaseStream.Write(f.Pixels, 0, f.Pixels.Length)
    p.StandardInput.Close()
    p.WaitForExit()
    if p.ExitCode <> 0 then failwithf "ffmpeg %s failed (%d)" args p.ExitCode

let savePng (path: string) (img: Image) =
    encode img.Width img.Height 1 (sprintf "-frames:v 1 \"%s\"" path) [ img ]
