// Virus (Atari ST, 1988) sound effects: the 54 records of SoundEffectTable $177d2 run through the decoded
// Sound_ChannelStep model (reversing/virus/frontend.md "Sound") at 50 Hz and a YM2149 synthesis, one 44.1 kHz mono WAV per id.
//   dotnet fsi virus_sfx.fsx <records.bin> <outdir> [capSeconds]
// records.bin: the 54 records, 18 bytes each (9 big-endian words), dumped from a snapshot (dump.py).
open System
open System.IO

let args = fsi.CommandLineArgs |> Array.skip 1
let recPath, outDir = args.[0], args.[1]
let capTicks = (if args.Length > 2 then float args.[2] else 3.0) * 50.0 |> int
Directory.CreateDirectory outDir |> ignore

let s16 (x: int) = int (int16 (x &&& 0xffff))
let raw = File.ReadAllBytes recPath
let recs : int[][] =
    [| for i in 0 .. raw.Length / 18 - 1 ->
        [| for w in 0 .. 8 -> int (int16 ((int raw.[18*i + 2*w] <<< 8) ||| int raw.[18*i + 2*w + 1])) |] |]

// channel words: 0 ticks left, 1 family, 2 priority, 3 chain, 4 volume 8.8, 5 volume slide, 6 mode (b0 tone, b1 noise),
// 7 period 8.8, 8 period slide, 9 tone fine reg, 10 volume reg, 11 tone-disable mixer bit, 12 noise-disable mixer bit
type Engine() =
    member val Ch : int[][] = [| [|0;0;0;0;0;0;0;0;0;0;8;0;3|]; [|0;0;0;0;0;0;0;0;0;2;9;1;4|]; [|0;0;0;0;0;0;0;0;0;4;10;2;5|] |]
    member val Mix = 0 with get, set
    member val NMax = 0 with get, set
    member val W = ResizeArray<int * int>() with get

let trigger (e: Engine) (id: int) =
    // a clean engine, no attenuation: the first free channel takes the record whole (Sound_Trigger $17932)
    let c = e.Ch |> Array.find (fun c -> c.[0] = 0)
    Array.blit recs.[id] 0 c 0 9

let kill (e: Engine) (c: int[]) =
    c.[0] <- 0; c.[1] <- 0
    e.W.Add((c.[10], 0))

let rec step (e: Engine) (c: int[]) =
    if c.[0] <> 0 then
        let d0 = (c.[0] - 1) &&& 0xffff
        if d0 = 0 then
            if c.[3] = 0 then kill e c
            else
                let r = recs.[((c.[3] <<< 2) &&& 0xffff) >>> 2]
                Array.blit r 0 c 0 4
                Array.blit r 5 c 5 4
                step e c
        else
            let d1 = s16 (c.[4] + c.[5])
            if d1 < 0 then kill e c
            else
                let d1 = if d1 >= 0x1000 then 0xfff else d1
                let mutable d4 = c.[7]
                e.W.Add((c.[10], d1 >>> 8))
                let a4, a5 = c.[11], c.[12]
                if c.[6] &&& 1 <> 0 then
                    e.Mix <- (e.Mix &&& ~~~(1 <<< a4)) ||| (1 <<< a5)
                    e.W.Add((7, e.Mix &&& 0xff))
                    d4 <- s16 (d4 + c.[8])
                    e.W.Add((c.[9], (d4 &&& 0xffff) >>> 8))
                    if c.[6] &&& 2 <> 0 then
                        e.Mix <- e.Mix &&& ~~~(1 <<< a5)
                        e.W.Add((7, e.Mix &&& 0xff))
                        if d1 >= e.NMax then
                            e.NMax <- d1
                            e.W.Add((6, ((d4 &&& 0xffff) >>> 8) >>> 3))
                else
                    e.Mix <- (e.Mix ||| (1 <<< a4)) &&& ~~~(1 <<< a5)
                    e.W.Add((7, e.Mix &&& 0xff))
                    if d1 >= e.NMax then
                        e.NMax <- d1
                        d4 <- s16 (d4 + c.[8])
                        e.W.Add((6, ((d4 &&& 0xffff) >>> 8) >>> 3))
                c.[0] <- d0
                c.[4] <- d1; c.[7] <- d4

let tick (e: Engine) =
    e.W.Clear(); e.NMax <- 0
    for c in e.Ch do step e c

// ---- YM2149: 2 MHz clock, tone toggles every TP steps of clock/8 (f = 2e6/(16 TP)), noise LFSR shifts every 2 NP steps
let ymVol = Array.init 16 (fun n -> if n = 0 then 0.0 else Math.Pow(10.0, -3.0 * float (15 - n) / 20.0))
let stepsPerTick = 5000                   // 250 kHz / 50 Hz
let sampleRate = 44100
let samplesPerTick = sampleRate / 50      // 882

type Ym() =
    member val R : int[] = Array.zeroCreate 16
    member val TCnt : int[] = [|0;0;0|]
    member val TOut : bool[] = [|false;false;false|]
    member val NCnt = 0 with get, set
    member val Lfsr = 1 with get, set
    member val NOut = false with get, set

let ymStep (y: Ym) =
    for c in 0 .. 2 do
        let tp = max 1 (y.R.[2*c] ||| ((y.R.[2*c+1] &&& 15) <<< 8))
        y.TCnt.[c] <- y.TCnt.[c] + 1
        if y.TCnt.[c] >= tp then
            y.TCnt.[c] <- 0
            y.TOut.[c] <- not y.TOut.[c]
    let np = max 1 (y.R.[6] &&& 31)
    y.NCnt <- y.NCnt + 1
    if y.NCnt >= 2 * np then
        y.NCnt <- 0
        let fb = (y.Lfsr ^^^ (y.Lfsr >>> 3)) &&& 1
        y.Lfsr <- (y.Lfsr >>> 1) ||| (fb <<< 16)
        y.NOut <- y.Lfsr &&& 1 = 1
    let mutable s = 0.0
    for c in 0 .. 2 do
        let tOn = y.TOut.[c] || (y.R.[7] >>> c) &&& 1 = 1
        let nOn = y.NOut || (y.R.[7] >>> (c + 3)) &&& 1 = 1
        if tOn && nOn then s <- s + ymVol.[y.R.[8 + c] &&& 15]
    s

let render (id: int) (log: StreamWriter) =
    let e = Engine()
    let y = Ym()
    y.R.[7] <- 0x3f
    trigger e id
    let samples = ResizeArray<float>()
    let mutable t = 0
    let mutable fin = false
    while not fin && t < capTicks do
        tick e
        log.WriteLine(sprintf "%d: %s" t (String.Join(" ", e.W |> Seq.map (fun (r, v) -> sprintf "r%d=%d" r v))))
        for (r, v) in e.W do y.R.[r] <- v
        // average the 5000 steps of this tick down to 882 samples
        let acc = Array.zeroCreate<float> samplesPerTick
        let cnt = Array.zeroCreate<int> samplesPerTick
        for k in 0 .. stepsPerTick - 1 do
            let v = ymStep y
            let sIdx = min (samplesPerTick - 1) (k * samplesPerTick / stepsPerTick)
            acc.[sIdx] <- acc.[sIdx] + v
            cnt.[sIdx] <- cnt.[sIdx] + 1
        for i in 0 .. samplesPerTick - 1 do samples.Add(acc.[i] / float (max 1 cnt.[i]))
        t <- t + 1
        if e.Ch |> Array.forall (fun c -> c.[0] = 0) then fin <- true
    // remove the DC of the unipolar sum with a one-pole high pass (about 20 Hz), fixed gain 1.0 across all files
    let out = Array.zeroCreate<int16> samples.Count
    let mutable lp = 0.0
    for i in 0 .. samples.Count - 1 do
        lp <- lp + 0.0028 * (samples.[i] - lp)
        out.[i] <- int16 (Math.Round(Math.Clamp((samples.[i] - lp) * 1.0, -1.0, 1.0) * 32767.0))
    out, t, e.Ch |> Array.forall (fun c -> c.[0] = 0)

let writeWav (path: string) (pcm: int16[]) =
    use w = new BinaryWriter(File.Create path)
    let n = pcm.Length * 2
    w.Write("RIFF"B); w.Write(36 + n); w.Write("WAVE"B); w.Write("fmt "B)
    w.Write(16); w.Write(1s); w.Write(1s); w.Write(sampleRate); w.Write(sampleRate * 2); w.Write(2s); w.Write(16s)
    w.Write("data"B); w.Write(n)
    for s in pcm do w.Write s

let names =
    dict [ 0,"periodic_tick"; 1,"periodic_tick_b"; 2,"shot_impact"; 3,"kill_award"; 4,"explosion"; 5,"thrust"; 6,"thrust_tail"
           7,"small_burst"; 8,"large_burst"; 9,"enemy_shot"; 10,"player_fire"; 11,"chaser_drone"; 12,"chaser_drone_b"
           13,"enemy_thrust"; 14,"enemy_thrust_tail"; 15,"chaser_stop"; 16,"seeder_hum"; 17,"seeder_hum_b"; 18,"seeder_stop"
           19,"bomb_landing"; 20,"shot_landing"; 21,"shot_landing_b"; 22,"bomber_hum"; 23,"bomber_hum_b"; 24,"bomber_stop"
           25,"fuel_warning"; 26,"fuel_warning_c26"; 27,"fuel_warning_c27"; 28,"fuel_warning_c28"; 29,"fuel_silence"
           30,"rocket_flight"; 31,"rocket_flight_b"; 32,"extra_life"; 33,"extra_life_b"; 34,"fuel_low_a"; 35,"fuel_low_b"
           36,"fuel_low_c"; 37,"attractor"; 38,"attractor_stop"; 39,"no_trigger_site"; 40,"wave_jingle_a1"; 41,"wave_jingle_a2"
           42,"wave_jingle_a3"; 43,"wave_jingle_b1"; 44,"wave_jingle_b2"; 45,"wave_jingle_b3"; 46,"wave_jingle_c1"
           47,"wave_jingle_c2"; 48,"wave_jingle_c3"; 49,"mothership"; 50,"mothership_stop"; 51,"mothership_chaser"
           52,"mothership_chaser_b"; 53,"mothership_chaser_stop" ]

let summary = new StreamWriter(Path.Combine(outDir, "summary.txt"))
for id in 0 .. recs.Length - 1 do
    let name = sprintf "id%02d_%s" id names.[id]
    use log = new StreamWriter(Path.Combine(outDir, name + ".ticks.txt"))
    let pcm, ticks, ended = render id log
    writeWav (Path.Combine(outDir, name + ".wav")) pcm
    let line = sprintf "%s: %d ticks, %.2f s%s" name ticks (float pcm.Length / float sampleRate) (if ended then "" else " (chain repeats; capped)")
    summary.WriteLine line
    printfn "%s" line
summary.Dispose()
