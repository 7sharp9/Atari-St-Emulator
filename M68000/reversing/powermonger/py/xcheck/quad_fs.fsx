// F# half of the synthetic quadrant-walk cross-check: Fill.planQ0..3 drawn with
// Fill.drawCell on the corner/terrain/dither generators of quad_py.py, one
// "x,y,idx" line per covered pixel in $XCHECK_OUT/q<k>_fs.txt (run.sh diffs them).
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"

open PmLogic
let outDir = match System.Environment.GetEnvironmentVariable "XCHECK_OUT" with null | "" -> "." | d -> d

let corner (r: int) (c: int) : Projection.Corner =
    let x = 50 + ((r * 37 + c * 17) % 40)
    let y = 40 + ((r * 23 + c * 31) % 30)
    { X = float x; Y = float y }

let corners : Projection.Corner[,] = Array2D.init 9 9 corner

// Terrain.Map sized to the real 64x128 planes (constants in Terrain.fs); only
// cells 0..7 in each axis are read (camX=camY=0), matching the Python side.
let typ cx cy = 0x20 + ((cx * 7 + cy * 3) % 20)
let hgt cx cy = 0x18 + ((cx * 5 + cy * 11) % 25)
let flg cx cy = if (cx + cy) % 2 = 0 then 0x80uy else 0x00uy

let n = Terrain.Width * Terrain.Height
let typA = Array.zeroCreate<byte> n
let hgtA = Array.zeroCreate<byte> n
let flgA = Array.zeroCreate<byte> n
let ctlA = Array.zeroCreate<byte> n
for cy in 0 .. 8 do
    for cx in 0 .. 8 do
        let i = cy * Terrain.Width + cx
        typA.[i] <- byte (typ cx cy)
        hgtA.[i] <- byte (hgt cx cy)
        flgA.[i] <- flg cx cy
let map : Terrain.Map = { Type = typA; HeightPlane = hgtA; Flag = flgA; Control = ctlA }

let dith = Array.init 0x4000 (fun i -> byte ((i * 37 + 11) &&& 0xFF))

let run planFn name =
    let buf = Fill.Buffer.Create()
    planFn corners map 0 0 |> List.iter (Fill.drawCell buf dith 1)
    let lines =
        [ for y in 0 .. Fill.ScreenHeight - 1 do
            for x in 0 .. Fill.ScreenWidth - 1 do
                let i = y * Fill.ScreenWidth + x
                if buf.Covered.[i] then yield sprintf "%d,%d,%d" x y buf.Index.[i] ]
    let outPath = System.IO.Path.Combine(outDir, sprintf "%s_fs.txt" name)
    System.IO.File.WriteAllText(outPath, String.concat "\n" lines + "\n")
    printfn "%s: %d covered px -> %s" name (List.length lines) outPath

run Fill.planQ0 "q0"
run Fill.planQ1 "q1"
run Fill.planQ2 "q2"
run Fill.planQ3 "q3"
