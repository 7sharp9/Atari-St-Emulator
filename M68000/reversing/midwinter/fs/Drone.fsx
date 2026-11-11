/// A drone over Midwinter's island: a height-field ray caster (one ray per screen column, nearest ground
/// first, as the voxel landscapes of the early 1990s drew) flying a smooth path at a fixed height over the
/// ground. The island is the domain model's finest level; the camera, light and colours are ours.
module Drone

open System
open System.Threading.Tasks
open Island
open Render

/// Height units one finest cell spans. The game's 3D view is not decoded, so the vertical scale is a choice.
let finestCell = 110.0f

type Camera = { X: float32; Y: float32; Alt: float32; Yaw: float32; Pitch: float32 }   // X column, Y row, in cells

// ---------------------------------------------------------------- sampling the ground

let private sample (t: Terrain) (x: float32) (y: float32) : float32 * Colour =
    let n = t.Size
    if x < 0.0f || y < 0.0f || x >= float32 (n - 1) || y >= float32 (n - 1) then 0.0f, sea
    else
        let c, r = int x, int y
        let fx, fy = x - float32 c, y - float32 r
        let blend (a: float32) b c' d = lerp (lerp a b fx) (lerp c' d fx) fy
        let h = blend t.Height.[r, c] t.Height.[r, c + 1] t.Height.[r + 1, c] t.Height.[r + 1, c + 1]
        let k (sel: Colour -> float32) = blend (sel t.Colour.[r, c]) (sel t.Colour.[r, c + 1]) (sel t.Colour.[r + 1, c]) (sel t.Colour.[r + 1, c + 1])
        h, (k (fun (a, _, _) -> a), k (fun (_, b, _) -> b), k (fun (_, _, c) -> c))

let groundAt (t: Terrain) x y = fst (sample t x y) / finestCell

// ---------------------------------------------------------------- one frame

let skyTop: Colour = 0.33f, 0.50f, 0.78f
let haze: Colour = 0.82f, 0.87f, 0.94f

let frame (t: Terrain) (w: int) (h: int) (cam: Camera) : Image =
    let img = image w h
    let fov = 70.0f * MathF.PI / 180.0f
    let focal = float32 w / 2.0f / MathF.Tan(fov / 2.0f)
    let horizon = float32 h / 2.0f - focal * MathF.Tan cam.Pitch
    let fx, fy = MathF.Cos cam.Yaw, MathF.Sin cam.Yaw
    let rx, ry = -fy, fx                                               // rows run south, so right is (-fy, fx)
    let far, fogDistance = 1400.0f, 650.0f
    Parallel.For(0, w, fun col ->
        let u = (2.0f * (float32 col + 0.5f) / float32 w - 1.0f) * MathF.Tan(fov / 2.0f)
        let dx, dy = fx + rx * u, fy + ry * u
        let mutable top = h                                            // everything below `top` is drawn
        let mutable z = 0.5f
        while z < far && top > 0 do
            let height, colour = sample t (cam.X + dx * z) (cam.Y + dy * z)
            let sy = horizon + (cam.Alt - height / finestCell) / z * focal
            if sy < float32 top then
                let fog = 1.0f - MathF.Exp(-z / fogDistance)
                let c = mix colour haze fog
                let y0 = max 0 (int sy)
                for y in y0 .. top - 1 do setPixel img col y c
                top <- y0
            z <- z + max 0.02f (z * 0.004f)
        for y in 0 .. top - 1 do                                       // sky
            let t' = Math.Clamp((horizon - float32 y) / (0.6f * float32 h), 0.0f, 1.0f)
            setPixel img col y (mix haze skyTop t')) |> ignore
    img

// ---------------------------------------------------------------- the flight

/// Catmull-Rom through the waypoints, resampled to `count` points evenly spaced along the curve.
let path (count: int) (waypoints: (float32 * float32) list) : (float32 * float32)[] =
    let p = Array.ofList waypoints
    let at i = p.[Math.Clamp(i, 0, p.Length - 1)]
    let point i (t: float32) =
        let (x0, y0), (x1, y1), (x2, y2), (x3, y3) = at (i - 1), at i, at (i + 1), at (i + 2)
        let cr a b c d =
            0.5f * (2.0f * b + (c - a) * t + (2.0f * a - 5.0f * b + 4.0f * c - d) * t * t + (3.0f * b - a - 3.0f * c + d) * t * t * t)
        cr x0 x1 x2 x3, cr y0 y1 y2 y3
    let dense = [| for i in 0 .. p.Length - 2 do for k in 0 .. 199 -> point i (float32 k / 200.0f) |]
    let dist = dense |> Array.pairwise |> Array.scan (fun d ((ax, ay), (bx, by)) -> d + MathF.Sqrt((bx - ax) ** 2.0f + (by - ay) ** 2.0f)) 0.0f
    let total = Array.last dist
    Array.init count (fun k ->
        let target = total * float32 k / float32 (count - 1)
        let i = Math.Clamp(Array.findIndexBack (fun d -> d <= target) dist, 0, dense.Length - 2)
        let seg = dist.[i + 1] - dist.[i]
        let f = if seg > 0.0f then (target - dist.[i]) / seg else 0.0f
        let (ax, ay), (bx, by) = dense.[i], dense.[i + 1]
        lerp ax bx f, lerp ay by f)

/// Box smoothing over a window of +-k samples.
let smooth (k: int) (xs: float32[]) =
    Array.init xs.Length (fun i ->
        let lo, hi = max 0 (i - k), min (xs.Length - 1) (i + k)
        Array.average xs.[lo..hi])

/// In from the sea on the west coast, east along the island's middle, then north over the ridges to the
/// north coast (waypoints in finest cells, x then y; read off the top-down map).
let route =
    [ -80.0f, 840.0f; 100.0f, 820.0f; 260.0f, 800.0f; 420.0f, 820.0f; 600.0f, 860.0f; 780.0f, 880.0f
      900.0f, 800.0f; 980.0f, 680.0f; 1000.0f, 540.0f; 960.0f, 400.0f; 900.0f, 240.0f; 880.0f, 60.0f ]

let cameras (t: Terrain) (frames: int) : Camera[] =
    let pts = path frames route
    let ahead i k = pts.[min (pts.Length - 1) (i + k)]
    // clearance over the highest ground in the next stretch, smoothed so the drone does not bob
    let ground =
        pts |> Array.mapi (fun i _ ->
            [ 0 .. 4 .. 60 ] |> List.map (fun k -> let x, y = ahead i k in groundAt t x y) |> List.max)
    let alt = ground |> smooth 25 |> Array.map (fun g -> g + 12.0f)
    let yaw =
        pts |> Array.mapi (fun i (x, y) -> let ax, ay = ahead i 40 in MathF.Atan2(ay - y, ax - x))
        |> Array.map (fun a -> MathF.Cos a, MathF.Sin a)
        |> fun v -> Array.zip (smooth 20 (Array.map fst v)) (smooth 20 (Array.map snd v))
        |> Array.map (fun (c, s) -> MathF.Atan2(s, c))
    Array.init frames (fun i ->
        let x, y = pts.[i]
        { X = x; Y = y; Alt = alt.[i]; Yaw = yaw.[i]; Pitch = 0.16f })

let fly (finest: Grid) (out: string) (seconds: float) =
    let t = terrain finestCell finest
    let fps, w, h = 30, 1280, 720
    let cams = cameras t (int (seconds * float fps))
    let sw = Diagnostics.Stopwatch.StartNew()
    cams
    |> Seq.mapi (fun i cam ->
        if i % 60 = 0 then eprintfn "frame %d/%d (%d ms)" i cams.Length sw.ElapsedMilliseconds
        frame t w h cam)
    |> encode w h fps (sprintf "-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \"%s\"" out)
    eprintfn "%d frames in %d ms" cams.Length sw.ElapsedMilliseconds

// ---------------------------------------------------------------- the zoom, as a figure

/// Each level around the target: the whole island at levels 0 and 1, then the 100 x 100 cells the game
/// keeps at each finer level, centred on the target (the game's own window placement is in $199ec).
/// The square marks the part the next panel refines.
let zoomFigure (levels: Grid list) (targetX: int, targetY: int) (out: string) =
    let panel k (level: Grid) =
        let n = Array2D.length1 level
        let per = 1 <<< (5 - k)                                       // finest cells per cell at level k
        let size = min n 100
        let cx, cy = targetX / per, targetY / per
        let ox, oy = Math.Clamp(cx - size / 2, 0, n - size), Math.Clamp(cy - size / 2, 0, n - size)
        let crop = Array2D.init size size (fun r c -> level.[oy + r, ox + c])
        let img = topDown (terrain (finestCell * float32 per) crop) |> scale (200 / size)
        if k > 0 && k < 5 then                                        // the next panel's extent: 50 cells
            let s = 200 / size
            let nx, ny = (Math.Clamp(cx - 25, 0, n - 50) - ox) * s, (Math.Clamp(cy - 25, 0, n - 50) - oy) * s
            let red: Colour = 0.85f, 0.15f, 0.1f
            for d in 0 .. 50 * s - 1 do
                for e in [ 0; 1 ] do
                    setPixel img (nx + d) (ny + e) red; setPixel img (nx + d) (ny + 50 * s - 1 - e) red
                    setPixel img (nx + e) (ny + d) red; setPixel img (nx + 50 * s - 1 - e) (ny + d) red
        img
    levels |> List.mapi panel |> row 8 |> savePng out
