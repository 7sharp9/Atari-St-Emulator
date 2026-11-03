// Does the $ffa2 dither phase offset explain the low terrain scores on the
// rotated captures? Rotating each 128-byte dither slot by `bias` bytes is the
// same as ditherIndex using ((8*y + bias) & 0x7f), for bias a multiple of 8.
//   dotnet fsi phase_test.fsx rot40.json ...   (frames from ../dump_frame.py)
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
open System
open System.IO
open System.Text.Json

let W, H = Fill.ScreenWidth, Fill.ScreenHeight

for path in fsi.CommandLineArgs |> Array.skip 1 do
    let root = JsonDocument.Parse(File.ReadAllText path).RootElement
    let gi (k: string) = root.GetProperty(k).GetInt32()
    let bytes (k: string) = Convert.FromBase64String(root.GetProperty(k).GetString())
    let camX, camY = root.GetProperty("cam").[0].GetInt32(), root.GetProperty("cam").[1].GetInt32()
    let yaw, tick, inset, bias = gi "yaw", gi "tick", gi "x_inset", gi "phase_bias"
    let map : Terrain.Map = { Type = bytes "typ"; HeightPlane = bytes "hgt"; Flag = bytes "flg"; Control = bytes "ctl" }
    let cj = root.GetProperty("corners")
    let corners = Array2D.init 9 9 (fun r c ->
        ({ X = float (cj.[r].[c].[0].GetInt32()); Y = float (cj.[r].[c].[1].GetInt32()) } : Projection.Corner))
    let dith, reff = bytes "dith", bytes "ref"
    let shifted (b: int) = Array.init dith.Length (fun i -> dith.[(i &&& ~~~0x7f) + (((i &&& 0x7f) + b) &&& 0x7f)])
    let score (d: byte[]) =
        let buf = Fill.Buffer.Create()
        Fill.walk buf d corners map camX camY tick (yaw / 16)
        let mutable hit, tot = 0, 0
        for i in 0 .. W * H - 1 do
            let x = i % W + inset
            if buf.Covered.[i] && x < W then
                tot <- tot + 1
                if buf.Index.[i] = reff.[(i / W) * W + x] then hit <- hit + 1
        100.0 * float hit / float tot
    printfn "%-12s yaw $%02x bias %3d   terrain exact: no bias %.1f%%, with bias %.1f%%"
        (Path.GetFileNameWithoutExtension path) yaw bias (score dith) (score (shifted bias))
