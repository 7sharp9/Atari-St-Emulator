/// A drone over Midwinter's island: a height-field ray caster (one ray per screen column, nearest ground
/// first, as the voxel landscapes of the early 1990s drew) flying a smooth path at a fixed height over the
/// ground. The island is the domain model's finest level; the camera, light and colours are ours.
module Drone

open System
open System.Threading.Tasks
open Island
open Render

/// Height units one finest cell spans: the game's own ratio. Its landscape routine $16d9c steps 64 camera units per
/// cell (row step $1720c, column step $171f8, 16.16) and multiplies a height by 16384/65536 = 0.25 ($17212), so a
/// cell is as wide as 256 height units are tall (terrain.md section 5).
let finestCell = 256.0f

type Camera = { X: float32; Y: float32; Alt: float32; Yaw: float32; Pitch: float32; Roll: float32 }   // X column, Y row, in cells

/// Field of view across the screen, where the view's centre sits down it (0.5 is the middle), and the nearest and
/// farthest ground it draws, in cells.
type Lens = { Fov: float32; CentreY: float32; Near: float32; Far: float32 }

module Lens =
    let drone = { Fov = 70.0f * MathF.PI / 180.0f; CentreY = 0.5f; Near = 0.5f; Far = 1400.0f }

    /// At a skier's eye height the ground under the bottom of the screen is a few metres ahead, so start there.
    let ski = { Fov = 75.0f * MathF.PI / 180.0f; CentreY = 0.5f; Near = 0.01f; Far = 600.0f }

    /// The game's ski view ($16d9c): focal length 163 ($17216) on a 320-pixel screen, centre (160, 132) of 200. It can
    /// draw only the 100 x 100 window it holds, and the camera sits at row 49, so it sees at most 49 cells ahead.
    let midwinter = { Fov = 2.0f * MathF.Atan(160.0f / 163.0f); CentreY = 132.0f / 200.0f; Near = 0.5f; Far = 49.0f }

// ---------------------------------------------------------------- sampling the ground

let private sample (t: Terrain) (x: float32) (y: float32) : float32 * Colour =
    let n = t.Size
    if x < 0.0f || y < 0.0f || x >= float32 (n - 1) || y >= float32 (n - 1) then 0.0f, sea
    else
        let c, r = int x, int y
        let fx, fy = x - float32 c, y - float32 r
        let blend (a: float32) b c' d = lerp (lerp a b fx) (lerp c' d fx) fy
        let h = blend t.Height.[r, c] t.Height.[r, c + 1] t.Height.[r + 1, c] t.Height.[r + 1, c + 1]
        // close up, straight-line blending shows every cell edge as a crease in the shading: ease the colour (only the
        // colour, so the ground keeps the game's shape) for the textured surface
        let fx, fy = if t.Grain > 0.0f then fx * fx * (3.0f - 2.0f * fx), fy * fy * (3.0f - 2.0f * fy) else fx, fy
        let blend (a: float32) b c' d = lerp (lerp a b fx) (lerp c' d fx) fy
        let k (sel: Colour -> float32) = blend (sel t.Colour.[r, c]) (sel t.Colour.[r, c + 1]) (sel t.Colour.[r + 1, c]) (sel t.Colour.[r + 1, c + 1])
        h, (k (fun (a, _, _) -> a), k (fun (_, b, _) -> b), k (fun (_, _, c) -> c))

let groundAt (t: Terrain) x y = fst (sample t x y) / finestCell

/// Value noise in 0..1 on a unit lattice, from a hash of the lattice point: the same place always has the same grain.
let private noise (x: float32) (y: float32) =
    let hash (i: int) (j: int) =
        let h = i * 374761393 + j * 668265263
        let h = (h ^^^ (h >>> 13)) * 1274126177
        float32 ((h ^^^ (h >>> 16)) &&& 0xffff) / 65535.0f
    let i, j = int (MathF.Floor x), int (MathF.Floor y)
    let fx, fy = x - float32 i, y - float32 j
    let sx, sy = fx * fx * (3.0f - 2.0f * fx), fy * fy * (3.0f - 2.0f * fy)
    lerp (lerp (hash i j) (hash (i + 1) j) sx) (lerp (hash i (j + 1)) (hash (i + 1) (j + 1)) sx) sy

/// Brightness of the snow's grain at (x, y) in cells: ripples drawn out along the wind (west to east, ours), about a
/// metre across at the ski scale, under a coarser mottle.
let private grain (x: float32) (y: float32) =
    0.65f * noise (x * 12.0f) (y * 48.0f) + 0.35f * noise (x * 5.0f + 17.0f) (y * 5.0f + 31.0f) - 0.5f

// ---------------------------------------------------------------- one frame

/// The air between the camera and the ground: the sky's colour overhead and at the horizon, and the distance in
/// cells over which the ground fades to the horizon colour.
type Air = { Zenith: Colour; Horizon: Colour; Thickness: float32 }

module Air =
    /// Air at well below freezing holds almost no water, so there is little haze: a deep blue sky that pales only
    /// near the horizon, and distance tints the ground blue rather than greying it.
    let cold = { Zenith = (0.04f, 0.22f, 0.60f); Horizon = (0.66f, 0.82f, 0.98f); Thickness = 2200.0f }

    /// One flat colour and no fade, as the game draws its sky.
    let flat (sky: Colour) = { Zenith = sky; Horizon = sky; Thickness = infinityf }

/// Pitch shears the view (the horizon moves, verticals stay vertical), as height-field renderers of the time did:
/// fine for a gimbal tilted a few tens of degrees, wrong for looking straight down.
let frame (t: Terrain) (lens: Lens) (air: Air) (w: int) (h: int) (cam: Camera) : Image =
    let img = image w h
    let fov = lens.Fov
    let focal = float32 w / 2.0f / MathF.Tan(fov / 2.0f)
    let horizon = float32 h * lens.CentreY - focal * MathF.Tan cam.Pitch
    let tilt = -MathF.Tan cam.Roll                                     // roll as a shear, as the voxel engines did;
                                                                       // positive Roll leans right
    let fx, fy = MathF.Cos cam.Yaw, MathF.Sin cam.Yaw
    let rx, ry = -fy, fx                                               // rows run south, so right is (-fy, fx)
    let far = lens.Far
    Parallel.For(0, w, fun col ->
        let u = (2.0f * (float32 col + 0.5f) / float32 w - 1.0f) * MathF.Tan(fov / 2.0f)
        let dx, dy = fx + rx * u, fy + ry * u
        let horizon = horizon + (float32 col - float32 w / 2.0f) * tilt
        let mutable top = h                                            // everything below `top` is drawn
        let mutable z = lens.Near
        while z < far && top > 0 do
            let gx, gy = cam.X + dx * z, cam.Y + dy * z
            let height, colour = sample t gx gy
            let sy = horizon + (cam.Alt - height / finestCell) / z * focal
            if sy < float32 top then
                let colour =
                    // the ripples are 1/48 cell apart: past about 0.4 cell a screen row spans several, so fade them out
                    // there or they shimmer
                    if t.Grain = 0.0f || z > 1.5f || height = 0.0f then colour
                    else
                        let k = 1.0f - t.Grain * MathF.Exp(-z / 0.25f) * (grain gx gy + 0.5f)    // shade only: snow is at white
                        let r, g, b = colour in r * k, g * k, b * k
                let c = mix colour air.Horizon (1.0f - MathF.Exp(-z / air.Thickness))
                let y0 = max 0 (int sy)
                for y in y0 .. top - 1 do setPixel img col y c
                top <- y0
            z <- z + max (min 0.02f (lens.Near * 0.5f)) (z * 0.004f)
        for y in 0 .. top - 1 do                                       // sky
            let t' = Math.Clamp((horizon - float32 y) / (0.6f * float32 h), 0.0f, 1.0f)
            setPixel img col y (mix air.Horizon air.Zenith (MathF.Sqrt t'))) |> ignore
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

/// The heading at each point: towards the point `lead` samples ahead, smoothed as unit vectors so it never wraps.
let private headings (lead: int) (pts: (float32 * float32)[]) =
    let ahead i = pts.[min (pts.Length - 1) (i + lead)]
    pts |> Array.mapi (fun i (x, y) -> let ax, ay = ahead i in MathF.Atan2(ay - y, ax - x))
    |> Array.map (fun a -> MathF.Cos a, MathF.Sin a)
    |> fun v -> Array.zip (smooth 20 (Array.map fst v)) (smooth 20 (Array.map snd v))
    |> Array.map (fun (c, s) -> MathF.Atan2(s, c))

let cameras (t: Terrain) (frames: int) : Camera[] =
    let pts = path frames route
    let ahead i k = pts.[min (pts.Length - 1) (i + k)]
    // clearance over the highest ground in the next stretch, smoothed so the drone does not bob
    let ground =
        pts |> Array.mapi (fun i _ ->
            [ 0 .. 4 .. 60 ] |> List.map (fun k -> let x, y = ahead i k in groundAt t x y) |> List.max)
    let alt = ground |> smooth 25 |> Array.map (fun g -> g + 6.0f)
    let yaw = headings 40 pts
    Array.init frames (fun i ->
        let x, y = pts.[i]
        { X = x; Y = y; Alt = alt.[i]; Yaw = yaw.[i]; Pitch = 0.16f; Roll = 0.0f })

let private film (t: Terrain) (cams: Camera[]) (out: string) =
    let fps, w, h = 30, 1280, 720
    let sw = Diagnostics.Stopwatch.StartNew()
    cams
    |> Seq.mapi (fun i cam ->
        if i % 60 = 0 then eprintfn "frame %d/%d (%d ms)" i cams.Length sw.ElapsedMilliseconds
        frame t Lens.drone Air.cold w h cam)
    |> encode w h fps (sprintf "-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \"%s\"" out)
    eprintfn "%d frames in %d ms" cams.Length sw.ElapsedMilliseconds

/// The coast-to-coast flight along `route`.
let fly (finest: Grid) (out: string) (seconds: float) =
    let t = terrain finestCell finest
    film t (cameras t (int (seconds * 30.0))) out

// ---------------------------------------------------------------- the reveal: rise on a locked focus, then orbit

let private smoothstep (u: float32) = let u = Math.Clamp(u, 0.0f, 1.0f) in u * u * (3.0f - 2.0f * u)

/// The highest ground near the island's centre, smoothed over 9 x 9 cells so a single spike does not win.
let focus (t: Terrain) : float32 * float32 =
    let smoothed x y = Seq.average (seq { for dy in -4 .. 4 do for dx in -4 .. 4 -> groundAt t (x + float32 dx) (y + float32 dy) })
    seq { for y in 600.0f .. 4.0f .. 1000.0f do for x in 600.0f .. 4.0f .. 1000.0f -> (x, y), smoothed x y }
    |> Seq.maxBy snd |> fst

/// A camera at (x, y, alt) looking at the point (tx, ty, th).
let lookAt (tx: float32, ty: float32, th: float32) (x: float32, y: float32, alt: float32) : Camera =
    let dx, dy = tx - x, ty - y
    let dist = MathF.Sqrt(dx * dx + dy * dy)
    { X = x; Y = y; Alt = alt; Yaw = MathF.Atan2(dy, dx); Pitch = MathF.Atan2(alt - th, dist); Roll = 0.0f }

/// Rise and pull back with the gimbal locked on the peak, hold, then a full orbit at that height, eased at both
/// ends. `riseShare` of the frames rise, the rest orbit.
let revealCameras (t: Terrain) (frames: int) (riseShare: float32) : Camera[] =
    let tx, ty = focus t
    let th = groundAt t tx ty
    let a0 = 0.75f * MathF.PI                                            // come in from the south-west
    let r0, r1 = 45.0f, 190.0f
    let at a r = tx + r * MathF.Cos a, ty + r * MathF.Sin a
    // the orbit's height: above the target and clear of everything on the circle
    let circleMax = Seq.max (seq { for k in 0 .. 359 -> let x, y = at (float32 k * MathF.PI / 180.0f) r1 in groundAt t x y })
    let alt1 = max (th + 45.0f) (circleMax + 15.0f)
    // the lowest height at (x, y) that still sees the focus over the ground between (to 85% of the way)
    let clear (x, y) =
        seq { for k in 0 .. 40 do
                let f = 0.85f * float32 k / 40.0f
                let g = groundAt t (lerp x tx f) (lerp y ty f) + 0.5f
                yield (g - th * f) / (1.0f - f) }
        |> Seq.max
    let alt0 = clear (at a0 r0)
    let rise = int (float32 frames * riseShare)
    Array.init frames (fun i ->
        if i < rise then
            let u = smoothstep (float32 i / float32 (rise - 1))
            let x, y = at a0 (lerp r0 r1 u)
            lookAt (tx, ty, th) (x, y, max (lerp alt0 alt1 u) (clear (x, y)))
        else
            let u = smoothstep (float32 (i - rise) / float32 (frames - rise - 1))
            let x, y = at (a0 + 2.0f * MathF.PI * u) r1
            lookAt (tx, ty, th) (x, y, alt1))

let reveal (finest: Grid) (out: string) (seconds: float) =
    let t = terrain finestCell finest
    let tx, ty = focus t
    eprintfn "focus (%.0f, %.0f), ground %.1f cells" tx ty (groundAt t tx ty)
    film t (revealCameras t (int (seconds * 30.0)) 0.4f) out

// ---------------------------------------------------------------- on skis

/// The skier's eye over the snow: the game's camera sits 8 height units above the ground under it (660 over 652 on
/// `d_ski`, `$1721c`), which is 8/256 of a cell.
let skierEye = 8.0f / finestCell

/// Metres in a cell, if the game's camera height over the snow is a person's eye, 1.7 m: an inference, the game
/// states no unit.
let cellMetres = 1.7f / skierEye

// ---------------------------------------------------------------- choosing a line

/// What a step down the hill costs a skier, per cell of ground covered: nothing extra on the 12 to 30 degrees a skier
/// picks, a little on ground too flat to keep speed, a lot uphill, and fast-rising costs on faces over 30 degrees
/// along the step or over 40 degrees across it. The weights are ours.
let private stepCost (along: float32) (fall: float32) =
    let deg v = MathF.Atan v * 57.3f
    let a, f = deg along, deg fall
    let alongCost =
        if a < 0.0f then 2.0f * -a
        elif a < 12.0f then 1.5f * (12.0f - a) / 12.0f
        elif a <= 30.0f then 0.0f
        else 2.0f * ((a - 30.0f) / 5.0f) ** 2.0f
    let acrossCost = if f > 40.0f then 2.0f * ((f - 40.0f) / 5.0f) ** 2.0f else 0.0f
    1.0f + alongCost + acrossCost

/// The cheapest line from `start` to the lowest ground 10 to 16 cells away: Dijkstra over a quarter-cell lattice
/// within 20 cells of the start, eight neighbours, `stepCost` per step; then smoothed, as points in cells.
let skiLine (t: Terrain) (x0: float32, y0: float32) : (float32 * float32)[] =
    let h, radius = 0.25f, 80                                          // lattice step in cells, half-size in steps
    let size = 2 * radius + 1
    let pos i j = x0 + float32 (i - radius) * h, y0 + float32 (j - radius) * h
    let ground = Array2D.init size size (fun i j -> let x, y = pos i j in groundAt t x y)
    let fall = Array2D.init size size (fun i j ->
        let x, y = pos i j
        let gx, gy = groundAt t (x + 0.5f) y - groundAt t (x - 0.5f) y, groundAt t x (y + 0.5f) - groundAt t x (y - 0.5f)
        MathF.Sqrt(gx * gx + gy * gy))
    let goal =
        seq { for i in 0 .. size - 1 do
                for j in 0 .. size - 1 do
                    let r = h * MathF.Sqrt(float32 ((i - radius) * (i - radius) + (j - radius) * (j - radius)))
                    if r >= 10.0f && r <= 16.0f && ground.[i, j] >= 1.0f then yield (i, j) }
        |> Seq.minBy (fun (i, j) -> ground.[i, j])
    let cost = Array2D.create size size infinityf
    let from = Array2D.create size size (-1, -1)
    let queue = Collections.Generic.PriorityQueue<int * int, float32>()
    cost.[radius, radius] <- 0.0f
    queue.Enqueue((radius, radius), 0.0f)
    let mutable finished = false
    while not finished && queue.Count > 0 do
        let i, j = queue.Dequeue()
        if (i, j) = goal then finished <- true
        else
            for di in -1 .. 1 do
                for dj in -1 .. 1 do
                    let ni, nj = i + di, j + dj
                    if (di, dj) <> (0, 0) && ni >= 0 && nj >= 0 && ni < size && nj < size then
                        let run = h * MathF.Sqrt(float32 (di * di + dj * dj))
                        let along = (ground.[i, j] - ground.[ni, nj]) / run
                        let c = cost.[i, j] + run * stepCost along fall.[ni, nj]
                        if c < cost.[ni, nj] then
                            cost.[ni, nj] <- c
                            from.[ni, nj] <- (i, j)
                            queue.Enqueue((ni, nj), c)
    let rec back node acc = if node = (radius, radius) then node :: acc else back from.[fst node, snd node] (node :: acc)
    back goal [] |> List.map (fun (i, j) -> pos i j) |> Array.ofList
    |> fun p -> Array.zip (smooth 6 (Array.map fst p)) (smooth 6 (Array.map snd p))

// ---------------------------------------------------------------- skiing it

/// A descent from just below the island's central peak, following `skiLine`, as simple physics: gravity along the
/// slope against sliding friction and air drag; turns as a skier makes them, about the line (pure pursuit, 1 cell
/// ahead), each half-turn's length and width drawn from a fixed seed and scaled by the slope: short and wide on steep
/// ground, long and shallow on gentle ground, so the rhythm changes with the hill; the turn rate held to 70 degrees a
/// second and 1.2 g of sideways pull. Speed is braked by skidding only where the line ahead is steep, so the skier
/// runs out on open ground and checks before a steep pitch. The camera is at `skierEye` over the ground, looks
/// towards where the line goes next before the skis turn, leans into each turn by half the body's lean, and shakes
/// a little with speed. Everything but the ground and the eye height is ours.
let skiCameras (t: Terrain) (frames: int) : Camera[] =
    let dt, gravity, friction, drag = 1.0f / 30.0f, 9.81f, 0.06f, 0.0045f       // drag per metre: about 21 m/s on 15 degrees
    let slope x y =                                                    // height gain per cell, east and south
        (groundAt t (x + 0.5f) y - groundAt t (x - 0.5f) y), (groundAt t x (y + 0.5f) - groundAt t x (y - 0.5f))
    let tx, ty = focus t
    let rec start r =                                                  // out from the peak to the first ground over 7 degrees
        let x, y = tx - r, ty + 0.3f * r
        let gx, gy = slope x y
        if MathF.Sqrt(gx * gx + gy * gy) > 0.12f || r > 60.0f then x, y else start (r + 1.0f)
    let x0, y0 = start 4.0f
    let line = skiLine t (x0, y0)
    let lineLength = line |> Array.pairwise |> Array.sumBy (fun ((ax, ay), (bx, by)) -> MathF.Sqrt((bx - ax) ** 2.0f + (by - ay) ** 2.0f))
    eprintfn "line: %d points, %.1f cells (%.0f m), from %.1f to %.1f cells high" line.Length lineLength (lineLength * cellMetres) (groundAt t x0 y0) (let x, y = Array.last line in groundAt t x y)
    let nearest x y = line |> Array.mapi (fun i (lx, ly) -> i, (lx - x) ** 2.0f + (ly - y) ** 2.0f) |> Array.minBy snd |> fst
    let ahead i (cells: float32) =                                     // the line's point `cells` beyond index i
        let mutable k, d = i, 0.0f
        while k < line.Length - 1 && d < cells do
            let (ax, ay), (bx, by) = line.[k], line.[k + 1]
            d <- d + MathF.Sqrt((bx - ax) ** 2.0f + (by - ay) ** 2.0f)
            k <- k + 1
        line.[k]
    let random = Random 1989
    let between (lo: float32) hi = lo + (hi - lo) * float32 (random.NextDouble())
    let mutable x, y, speed = x0, y0, 4.0f
    let mutable heading = let ax, ay = ahead 0 1.0f in MathF.Atan2(ay - y, ax - x)
    let mutable roll, pitch, look = 0.0f, 0.0f, 0.0f
    let mutable side, turnLeft, turnLength, turnWidth = 1.0f, 0.0f, 1.0f, 0.3f
    Array.init frames (fun f ->
        let time = float32 f * dt
        let i = nearest x y
        let gx, gy = slope x y
        let steep = Math.Clamp((MathF.Atan(MathF.Sqrt(gx * gx + gy * gy)) * 57.3f - 10.0f) / 30.0f, 0.0f, 1.0f)
        if turnLeft <= 0.0f then                                       // the next half-turn, the other way
            side <- -side
            turnLength <- lerp 3.2f 1.3f steep * between 0.75f 1.3f
            turnWidth <- lerp 0.12f 0.6f steep * between 0.6f 1.2f
            turnLeft <- turnLength
        turnLeft <- turnLeft - dt
        let px, py = ahead i 1.0f
        let toLine = MathF.Atan2(py - y, px - x)
        let wanted = toLine + side * turnWidth * MathF.Sin(MathF.PI * (1.0f - turnLeft / turnLength))
        let turn = MathF.Atan2(MathF.Sin(wanted - heading), MathF.Cos(wanted - heading))
        let maxRate = min 1.2f (1.2f * gravity / speed)
        let rate = Math.Clamp(turn / dt, -maxRate, maxRate)
        heading <- heading + rate * dt
        let fx, fy = MathF.Cos heading, MathF.Sin heading
        let down = -(gx * fx + gy * fy)                                // drop per cell along the skis
        let cos = 1.0f / MathF.Sqrt(1.0f + down * down)
        // the steepest drop on the line over the next 2 cells sets the speed the skier will allow
        let pitchAhead =
            [ 0.5f; 1.0f; 1.5f; 2.0f ] |> List.map (fun d -> let ax, ay = ahead i d in (groundAt t x y - groundAt t ax ay) / d) |> List.max
        let allowed = lerp 26.0f 14.0f (Math.Clamp((MathF.Atan pitchAhead * 57.3f - 20.0f) / 20.0f, 0.0f, 1.0f))
        let skid = 2.0f * max 0.0f (speed - allowed)
        speed <- max 3.0f (speed + (gravity * (down * cos - friction * cos) - drag * speed * speed - skid) * dt)
        let ground = speed * cos / cellMetres * dt                     // the speed is along the slope; the map sees its level part
        x <- x + fx * ground
        y <- y + fy * ground
        roll <- lerp roll (0.5f * MathF.Atan(speed * rate / gravity)) 0.1f
        let lx, ly = ahead i 0.6f                                      // the head looks where the line goes next
        let lookTo = MathF.Atan2(ly - y, lx - x)
        look <- lerp look (0.5f * MathF.Atan2(MathF.Sin(lookTo - heading), MathF.Cos(lookTo - heading))) 0.08f
        let eye = groundAt t x y + skierEye
        let lookUp =
            seq { for k in 1 .. 16 do
                    let d = 0.01f * float32 k
                    yield MathF.Atan2(groundAt t (x + d * fx) (y + d * fy) - eye, d) } |> Seq.max
        pitch <- lerp pitch (min (0.5f * MathF.Atan down + 0.05f) (0.3f - lookUp)) 0.15f
        let shake = 0.0006f * speed
        if f % 90 = 0 then
            eprintfn "t %4.1fs line %3d/%d speed %4.1f m/s (allowed %4.1f), along the skis %5.1f deg, turn %.1f s x %.0f deg, roll %5.1f deg"
                time i line.Length speed allowed (MathF.Atan down * 57.3f) turnLength (turnWidth * 57.3f) (roll * 57.3f)
        { X = x; Y = y; Alt = eye; Yaw = heading + look
          Pitch = pitch + shake * MathF.Sin(time * 37.0f) * MathF.Sin(time * 11.3f)
          Roll = roll + shake * MathF.Sin(time * 29.0f + 1.0f) })

/// The planned line and the skier's track from above, over the ground coloured by steepness (white under 12 degrees,
/// clear blue for the 12 to 30 a skier picks, then darkening to red at 50): 10 pixels a cell, 44 cells across.
let skiFigure (finest: Grid) (seconds: float) (out: string) =
    let t = { terrain finestCell finest with Grain = 0.20f }
    let cams = skiCameras t (int (seconds * 30.0))
    let tx, ty = focus t
    let rec start r =
        let x, y = tx - r, ty + 0.3f * r
        let gx, gy = groundAt t (x + 0.5f) y - groundAt t (x - 0.5f) y, groundAt t x (y + 0.5f) - groundAt t x (y - 0.5f)
        if MathF.Sqrt(gx * gx + gy * gy) > 0.12f || r > 60.0f then x, y else start (r + 1.0f)
    let x0, y0 = start 4.0f
    let line = skiLine t (x0, y0)
    let k, cells = 10, 44
    let ox, oy = x0 - 22.0f, y0 - 22.0f
    let img = image (k * cells) (k * cells)
    for py in 0 .. img.Height - 1 do
        for px in 0 .. img.Width - 1 do
            let x, y = ox + float32 px / float32 k, oy + float32 py / float32 k
            let gx, gy = groundAt t (x + 0.5f) y - groundAt t (x - 0.5f) y, groundAt t x (y + 0.5f) - groundAt t x (y - 0.5f)
            let a = MathF.Atan(MathF.Sqrt(gx * gx + gy * gy)) * 57.3f
            let c =
                if groundAt t x y < 1.0f then sea
                elif a < 12.0f then mix snow (0.62f, 0.80f, 0.98f) (a / 12.0f)
                elif a <= 30.0f then (0.62f, 0.80f, 0.98f)
                else mix (0.30f, 0.45f, 0.80f) (0.80f, 0.15f, 0.10f) (Math.Clamp((a - 30.0f) / 20.0f, 0.0f, 1.0f))
            setPixel img px py c
    let plot (x: float32, y: float32) (c: Colour) =
        let px, py = int ((x - ox) * float32 k), int ((y - oy) * float32 k)
        for dy in -1 .. 1 do
            for dx in -1 .. 1 do
                if px + dx >= 0 && py + dy >= 0 && px + dx < img.Width && py + dy < img.Height then setPixel img (px + dx) (py + dy) c
    for p in line do plot p (0.0f, 0.0f, 0.0f)
    for c in cams do plot (c.X, c.Y) (1.0f, 0.55f, 0.0f)
    savePng out img

/// The ski run, at the ski lens with the snow's grain.
let ski (finest: Grid) (out: string) (seconds: float) =
    let t = { terrain finestCell finest with Grain = 0.20f }
    let cams = skiCameras t (int (seconds * 30.0))
    let fps, w, h = 30, 1280, 720
    cams
    |> Seq.map (frame t Lens.ski Air.cold w h)
    |> encode w h fps (sprintf "-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \"%s\"" out)

// ---------------------------------------------------------------- the skier's own view, in the game's colours

/// A $0RGB shifter word as a colour: 3 bits a gun, 7 is full.
let stColour (w: int) : Colour = float32 ((w >>> 8) &&& 7) / 7.0f, float32 ((w >>> 4) &&& 7) / 7.0f, float32 (w &&& 7) / 7.0f

/// Reduce an image to a few colours with a 4 x 4 ordered dither, the way the game shades its snow (alternate pixels
/// of two palette colours). `spread` is how far the dither may push a pixel towards a neighbouring colour.
let quantise (palette: Colour[]) (spread: float32) (img: Image) : Image =
    let bayer = [| 0; 8; 2; 10; 12; 4; 14; 6; 3; 11; 1; 9; 15; 7; 13; 5 |]
    let out = image img.Width img.Height
    for y in 0 .. img.Height - 1 do
        for x in 0 .. img.Width - 1 do
            let i = 3 * (y * img.Width + x)
            let d = (float32 bayer.[(y % 4) * 4 + x % 4] + 0.5f) / 16.0f - 0.5f
            let r, g, b = (float32 img.Pixels.[i] / 255.0f + d * spread), (float32 img.Pixels.[i + 1] / 255.0f + d * spread), (float32 img.Pixels.[i + 2] / 255.0f + d * spread)
            let dist ((pr, pg, pb): Colour) = (pr - r) ** 2.0f + (pg - g) ** 2.0f + (pb - b) ** 2.0f
            setPixel out x y (Array.minBy dist palette)
    out

/// The ski view of a snapshot, as the game's projection places it: eye at the camera height `$1721c` over the
/// camera cell `$12c80`, facing north (a row step is +64 in camera Z), level, the game's lens, 320 x 200. The
/// picture is in the game's own colours, read from the snapshot's shifter palette: the flat sky (colour 2, $157)
/// and the three snow colours the goggle view uses (colours 5, 6 and 1: $245, $467, $777), level snow in the
/// middle one as on the game's screen. Which colour the game gives each slope is not decoded; the ramp is ours.
let skier (finest: Grid) (ram: byte[]) (palette: int[]) (out: string) =
    let dark, level, lit = stColour palette.[5], stColour palette.[6], stColour palette.[1]
    let ramp (light: float32) (_: float32) =
        if light < 1.0f then mix dark level (Math.Clamp((light - 0.4f) / 0.5f, 0.0f, 1.0f))
        else mix level lit (Math.Clamp((light - 1.1f) / 0.3f, 0.0f, 1.0f))
    let t = terrainWith ramp finestCell finest
    let ox, oy = Heritage.sword ram Heritage.Addr.origin, Heritage.sword ram (Heritage.Addr.origin + 2)
    let cell = (Heritage.long ram Heritage.Addr.camCell - Heritage.Addr.grid) / 4
    let row, col = cell / 100, cell % 100
    let eye = float32 (Heritage.sword ram Heritage.Addr.camHeight) / finestCell
    eprintfn "camera cell row %d col %d, world (%d, %d), eye %.2f cells over ground %.2f" row col (ox + col) (oy + row) eye (groundAt t (float32 (ox + col)) (float32 (oy + row)))
    let cam = { X = float32 (ox + col); Y = float32 (oy + row); Alt = eye; Yaw = -MathF.PI / 2.0f; Pitch = 0.0f; Roll = 0.0f }
    let sky = stColour palette.[2]
    let colours = [| sky; dark; level; lit |]
    frame t Lens.midwinter (Air.flat sky) 320 200 cam |> quantise colours 0.2f |> savePng out

// ---------------------------------------------------------------- every level of the whole island

/// The whole island at each level, file 37.2's 50 x 50 to the finest 1600 x 1600, each drawn `size` pixels square
/// (a coarse level's cells blown up, a fine level's averaged down) and laid out three to a row. Each level loses the
/// same south and east band, 64 finest cells, as the map does.
let levelsFigure (levels: Grid list) (size: int) (out: string) =
    let panel k (level: Grid) =
        let per = 1 <<< (5 - k)
        let n = Array2D.length1 level - 64 / per
        let src = topDown (terrain (finestCell * float32 per) level.[0 .. n - 1, 0 .. n - 1])
        let img = image size size
        for y in 0 .. size - 1 do
            for x in 0 .. size - 1 do
                let x0, x1 = x * n / size, max (x * n / size + 1) ((x + 1) * n / size)
                let y0, y1 = y * n / size, max (y * n / size + 1) ((y + 1) * n / size)
                let mutable r, g, b = 0, 0, 0
                for sy in y0 .. y1 - 1 do
                    for sx in x0 .. x1 - 1 do
                        let i = 3 * (sy * n + sx)
                        r <- r + int src.Pixels.[i]; g <- g + int src.Pixels.[i + 1]; b <- b + int src.Pixels.[i + 2]
                let count = float32 ((x1 - x0) * (y1 - y0)) * 255.0f
                setPixel img x y (float32 r / count, float32 g / count, float32 b / count)
        img
    let panels = levels |> List.mapi panel
    let rows = panels |> List.chunkBySize 3 |> List.map (row 8)
    let w = rows.Head.Width
    let h = (rows |> List.sumBy _.Height) + 8 * (rows.Length - 1)
    let img = { image w h with Pixels = Array.create (w * h * 3) 255uy }
    rows |> List.iteri (fun i r -> Array.blit r.Pixels 0 img.Pixels (3 * w * i * (r.Height + 8)) r.Pixels.Length)
    savePng out img

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
