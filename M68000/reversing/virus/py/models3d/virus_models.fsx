// virus_models.fsx  --  renders Virus's 43 object models as SVG from a dump of the model data.
//   dotnet fsi virus_models.fsx <models.bin> <palette.txt> <outdir>
// models.bin = RAM $aa72..$ce9a of a Virus snapshot (dump_data.py); palette.txt = the 16 live ST palette words (hex, 0RGB).
// Model record (all words big endian, see M68000/reversing/virus/README.md "Model data"):
//   +0 byte flags (bit0 rotated by the 3x3 matrix, bit1 casts a ground shadow), +1 byte 0
//   +2 word vertex count - 1, +4 word face count - 1, +6 word offset of the face list from the record start
//   +8 vertices, 6 bytes each (x, y, z as signed words; y is DOWN, z is away from the camera)
//   face list, 22 bytes a face: normal (3 signed words, 1.15 fixed), then three longs = the address $27154 + 8 * i of the
//   projected-vertex slot of vertex i, then a long colour index (0..15 flat, 16..23 a 2-colour checker, see README).
open System
open System.IO
open System.Text

let inv = Globalization.CultureInfo.InvariantCulture
let args = fsi.CommandLineArgs |> Array.skip 1
let data = File.ReadAllBytes args.[0]
let palWords = (File.ReadAllText args.[1]).Split([|' '; '\n'|], StringSplitOptions.RemoveEmptyEntries) |> Array.map (fun s -> Convert.ToInt32(s, 16))
let outDir = args.[2]
Directory.CreateDirectory outDir |> ignore
let baseAddr = 0xaa72

let u16 o = (int data.[o] <<< 8) ||| int data.[o + 1]
let s16 o = let v = u16 o in if v >= 0x8000 then v - 0x10000 else v
let u32 o = (u16 o <<< 16) ||| u16 (o + 2)

type Face = { Normal: float * float * float; Idx: int[]; Colour: int }
type Model = { Addr: int; Flags: int; Verts: (float * float * float)[]; Faces: Face[] }

let parse () =
    let ms = ResizeArray<Model>()
    let mutable o = 0
    while o < data.Length do
        let flags = int data.[o]
        let nv = u16 (o + 2) + 1
        let nf = u16 (o + 4) + 1
        let off = u16 (o + 6)
        let verts = [| for i in 0 .. nv - 1 -> (float (s16 (o + 8 + 6 * i)), float (s16 (o + 10 + 6 * i)), float (s16 (o + 12 + 6 * i))) |]
        let faces =
            [| for f in 0 .. nf - 1 do
                let p = o + off + 22 * f
                yield { Normal = (float (s16 p) / 32767.0, float (s16 (p + 2)) / 32767.0, float (s16 (p + 4)) / 32767.0)
                        Idx = [| for k in 0 .. 2 -> (u32 (p + 6 + 4 * k) - 0x27154) / 8 |]
                        Colour = u32 (p + 18) } |]
        ms.Add { Addr = baseAddr + o; Flags = flags; Verts = verts; Faces = faces }
        o <- o + off + 22 * nf
    if o <> data.Length then failwithf "chain ends at %d, data is %d bytes" o data.Length
    List.ofSeq ms

// names from the routine that draws the model (README "The object types", behaviours.md, virus.sym)
let names =
    dict [ 0xaa72, "debris chunk"; 0xaab8, "mothership chaser"; 0xab62, "player ship"; 0xac66, "bonus craft (type 12)"
           0xae30, "palm tree (types 1, 4)"; 0xaee8, "tall palm (type 5)"; 0xafc8, "grey wreck (damaged types 1, 5, 10)"; 0xb01a, "grey wreck (damaged types 3, 4, 6)"
           0xb06c, "grey wreck (damaged type 2)"; 0xb0be, "fir (type 6)"; 0xb110, "pine (type 3)"; 0xb162, "bush (type 2)"
           0xb1ca, "infected bush"; 0xb23e, "infected palm (type 1)"; 0xb2f6, "infected pine"; 0xb348, "infected palm (type 4)"
           0xb400, "infected tall palm"; 0xb4e0, "archway (type 9)"; 0xb5e6, "long house (type 7)"; 0xb756, "wreck (damaged type 7)"
           0xb806, "cottage (type 8)"; 0xb920, "wreck (damaged type 8)"; 0xb9d0, "wreck (damaged type 9)"; 0xba54, "pad marker (type 10)"
           0xbb88, "chaser"; 0xbc64, "patrol"; 0xbda4, "pursuer"; 0xbee4, "seeder, flying"; 0xc088, "seeder, landing"
           0xc2b4, "bomber"; 0xc390, "bomb"; 0xc472, "pursuer 2"; 0xc5b2, "pursuer 2, damaged"; 0xc6f2, "tower, disc (type 11)"
           0xc79c, "tower, cone (type 11)"; 0xc7e8, "wreck (damaged type 11)"; 0xc834, "attractor"; 0xc9a6, "rocket"; 0xcb30, "mothership (launch call)"
           0xcce2, "spray plume A1"; 0xcd50, "spray plume A2"; 0xcdbe, "spray plume B1"; 0xce2c, "spray plume B2" ]
let nameOf a = match names.TryGetValue a with | true, n -> n | _ -> "?"

// ST palette word 0x0RGB, 3 bits a channel
let rgb (w: int) =
    let c v = int (Math.Round(float v * 255.0 / 7.0))
    (c ((w >>> 8) &&& 7), c ((w >>> 4) &&& 7), c (w &&& 7))
let hex (r, g, b) = sprintf "#%02x%02x%02x" r g b
// colour index 0..15 flat; 16..23 planes 0..2 from c-16 and plane 3 a checker of colours c-16 and c-8: drawn as the 50% blend
let colour (c: int) =
    if c < 16 then rgb palWords.[c]
    else
        let (r1, g1, b1) = rgb palWords.[c - 16]
        let (r2, g2, b2) = rgb palWords.[c - 8]
        ((r1 + r2) / 2, (g1 + g2) / 2, (b1 + b2) / 2)

// fixed view: yaw about the vertical (y, down), then pitch about x looking down; screen x right, y down, depth z away
let yaw, pitch = 35.0 * Math.PI / 180.0, 25.0 * Math.PI / 180.0
let rotate (x, y, z) =
    let x1 = x * cos yaw + z * sin yaw
    let z1 = -x * sin yaw + z * cos yaw
    let y2 = y * cos pitch - z1 * sin pitch
    let z2 = y * sin pitch + z1 * cos pitch
    (x1, y2, z2)
let rotateN (x, y, z) = rotate (x, y, z)

let f (v: float) = v.ToString("0.##", inv)

/// the faces to paint, far to near: back faces dropped by the stored normal (visible when n_view.z <= 0, the game's own
/// test on a rotated model, here with the view direction (0,0,1)), then sorted by the centroid depth
let shaded (m: Model) =
    let rv = m.Verts |> Array.map rotate
    m.Faces
    |> Array.choose (fun fc ->
        let (_, _, nz) = rotateN fc.Normal
        if nz > 0.0 then None
        else
            let pts = fc.Idx |> Array.map (fun i -> rv.[i])
            let zc = (pts |> Array.sumBy (fun (_, _, z) -> z)) / 3.0
            Some (zc, fc.Colour, pts))
    |> Array.sortByDescending (fun (z, _, _) -> z)

let bounds (pts: (float * float) seq) =
    let xs = pts |> Seq.map fst
    let ys = pts |> Seq.map snd
    (Seq.min xs, Seq.min ys, Seq.max xs, Seq.max ys)

/// emits the <g> of one drawing fitted into the box (bx, by, size, size)
let fit (box: float * float * float) (pts2: (float * float) seq) =
    let (bx, by, size) = box
    let (x0, y0, x1, y1) = bounds pts2
    let w, h = max (x1 - x0) 1.0, max (y1 - y0) 1.0
    let sc = (size * 0.84) / max w h
    let ox = bx + size / 2.0 - (x0 + x1) / 2.0 * sc
    let oy = by + size / 2.0 - (y0 + y1) / 2.0 * sc
    fun (x: float, y: float) -> (ox + x * sc, oy + y * sc), sc

let filledGroup (m: Model) (box: float * float * float) =
    let sh = shaded m
    let rall = m.Verts |> Array.map rotate |> Array.map (fun (x, y, _) -> (x, y))
    let tr = fit box rall
    let sb = StringBuilder()
    for (_, c, pts) in sh do
        let col = hex (colour c)
        let s = pts |> Array.map (fun (x, y, _) -> let (px, py), _ = tr (x, y) in sprintf "%s,%s" (f px) (f py)) |> String.concat " "
        sb.AppendFormat(inv, "<polygon points=\"{0}\" fill=\"{1}\" stroke=\"{1}\" stroke-width=\"0.7\" stroke-linejoin=\"round\"/>\n", s, col) |> ignore
    sb.ToString()

let header w h =
    sprintf "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 %d %d\" width=\"%d\" height=\"%d\" font-family=\"Helvetica,Arial,sans-serif\">\n<rect width=\"%d\" height=\"%d\" fill=\"#dfe2e8\"/>\n" w h w h w h
let bg = "#dfe2e8"

let models = parse ()
printfn "%d models, chain from $%x to $%x" models.Length baseAddr (baseAddr + data.Length)

// one SVG per model: a fixed 3/4 view, painter's order
for m in models do
    let name = nameOf m.Addr
    let sb = StringBuilder()
    sb.Append(header 480 500) |> ignore
    sb.AppendFormat(inv, "<text x=\"14\" y=\"26\" font-size=\"15\" fill=\"#222\">${0:x5}  {1}</text>\n", m.Addr, name) |> ignore
    sb.AppendFormat(inv, "<text x=\"14\" y=\"44\" font-size=\"11\" fill=\"#555\">flags {0} ({1}{2}), {3} vertices, {4} faces</text>\n<text x=\"14\" y=\"58\" font-size=\"11\" fill=\"#555\">view: yaw 35, pitch 25 deg, painter's order by centroid depth, back faces dropped by the stored normal</text>\n",
                    m.Flags, (if m.Flags &&& 1 = 1 then "rotated" else "unrotated"), (if m.Flags &&& 2 = 2 then ", shadow" else ""), m.Verts.Length, m.Faces.Length) |> ignore
    sb.Append(filledGroup m (20.0, 60.0, 440.0)) |> ignore
    sb.Append("</svg>\n") |> ignore
    File.WriteAllText(Path.Combine(outDir, sprintf "model_%05x_%s.svg" m.Addr (name |> String.map (fun c -> if Char.IsLetterOrDigit c then c else '_'))), sb.ToString())

// contact sheet of the filled 3/4 views and a wireframe sheet (orthographic front XY and top XZ per model)
let cols = 6
let cell = 220.0
let rows = (models.Length + cols - 1) / cols
let sheetW, sheetH = int (float cols * cell), int (float rows * cell) + 30

let filledSheet =
    let sb = StringBuilder()
    sb.Append(header sheetW sheetH) |> ignore
    sb.AppendFormat(inv, "<text x=\"10\" y=\"20\" font-size=\"14\" fill=\"#222\">Virus models, 3/4 view (yaw 35, pitch 25), each fitted to its cell, palette of fl/f1.snap</text>\n") |> ignore
    models |> List.iteri (fun i m ->
        let cx, cy = float (i % cols) * cell, float (i / cols) * cell + 30.0
        sb.AppendFormat(inv, "<rect x=\"{0}\" y=\"{1}\" width=\"{2}\" height=\"{2}\" fill=\"none\" stroke=\"#b8bcc6\"/>\n", f cx, f cy, f cell) |> ignore
        sb.Append(filledGroup m (cx + 6.0, cy + 18.0, cell - 12.0)) |> ignore
        sb.AppendFormat(inv, "<text x=\"{0}\" y=\"{1}\" font-size=\"10\" fill=\"#333\">${2:x5} {3}</text>\n", f (cx + 6.0), f (cy + 13.0), m.Addr, nameOf m.Addr) |> ignore)
    sb.Append("</svg>\n") |> ignore
    sb.ToString()
File.WriteAllText(Path.Combine(outDir, "sheet_filled.svg"), filledSheet)

let wireSheet =
    let sb = StringBuilder()
    let wcell = 300.0
    let wcols = 4
    let wrows = (models.Length + wcols - 1) / wcols
    let w, h = int (float wcols * wcell), int (float wrows * 190.0) + 30
    sb.Append(header w h) |> ignore
    sb.AppendFormat(inv, "<text x=\"10\" y=\"20\" font-size=\"14\" fill=\"#222\">Virus models, orthographic wireframe: front (x right, y down) and top (x right, z away = up), each view fitted to its box; faces as stored (triangles)</text>\n") |> ignore
    models |> List.iteri (fun i m ->
        let cx, cy = float (i % wcols) * wcell, float (i / wcols) * 190.0 + 30.0
        sb.AppendFormat(inv, "<rect x=\"{0}\" y=\"{1}\" width=\"{2}\" height=\"190\" fill=\"none\" stroke=\"#b8bcc6\"/>\n", f cx, f cy, f wcell) |> ignore
        sb.AppendFormat(inv, "<text x=\"{0}\" y=\"{1}\" font-size=\"10\" fill=\"#333\">${2:x5} {3}  ({4}v {5}f, flags {6})</text>\n", f (cx + 6.0), f (cy + 13.0), m.Addr, nameOf m.Addr, m.Verts.Length, m.Faces.Length, m.Flags) |> ignore
        let draw (proj: float * float * float -> float * float) (bx: float) =
            let pts = m.Verts |> Array.map proj
            let tr = fit (bx, cy + 18.0, 150.0) pts
            for fc in m.Faces do
                let p = fc.Idx |> Array.map (fun k -> fst (tr pts.[k]))
                let s = p |> Array.map (fun (x, y) -> sprintf "%s,%s" (f x) (f y)) |> String.concat " "
                sb.AppendFormat(inv, "<polygon points=\"{0}\" fill=\"none\" stroke=\"#1d3557\" stroke-width=\"0.8\" stroke-linejoin=\"round\"/>\n", s) |> ignore
            for p in pts do
                let (x, y), _ = tr p
                sb.AppendFormat(inv, "<circle cx=\"{0}\" cy=\"{1}\" r=\"1.4\" fill=\"#c1121f\"/>\n", f x, f y) |> ignore
        draw (fun (x, y, _) -> (x, y)) (cx + 0.0)
        draw (fun (x, _, z) -> (x, -z)) (cx + 150.0))
    sb.Append("</svg>\n") |> ignore
    sb.ToString()
File.WriteAllText(Path.Combine(outDir, "sheet_wireframe.svg"), wireSheet)
printfn "wrote %d model SVGs, sheet_filled.svg, sheet_wireframe.svg to %s" models.Length outDir
