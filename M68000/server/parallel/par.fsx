// par.fsx: step K independent AtartSt machines in one process, on K threads (--mode threads) or one after another on
// the main thread (--mode seq), then save each end state. Writes one JSON line to stdout. See README.md.
//   dotnet fsi par.fsx --rom <TOS100UK.IMG> --n <steps> --out <dir> --tag <tag>
//        --job <name>=<snap>|<disk> ... --assign <name>,<name>,...   (K = number of names in --assign)
//        [--mode threads|seq] [--extra <i>=<steps>] [--poke <i>=<hexaddr>=<hexbyte>]
// Run from this directory (global.json pins the 10.0.303 SDK: the DLL references FSharp.Core 10.1, which the 8.0 SDK fsi cannot load).
#r "../../scratchpad/insights/parallel/dll/M68000.dll"
open System
open System.Diagnostics
open System.Threading
open System.Runtime
open Atari

let args = fsi.CommandLineArgs |> Array.skip 1
let opt (k: string) = args |> Array.tryFindIndex ((=) k) |> Option.map (fun i -> args.[i + 1])
let opts (k: string) = [ for i in 0 .. args.Length - 2 do if args.[i] = k then yield args.[i + 1] ]
let req k = match opt k with Some v -> v | None -> failwithf "%s required" k

// Tracing off the way Main does it under ATARI_NOTRACE (Program.fs Main.main): Trace.enabled starts true.
Trace.enabled <- false
let realOut = Console.Out
Console.SetOut(IO.TextWriter.Null)

let rom = req "--rom"
let n = int64 (req "--n")
let outDir = req "--out"
let tag = req "--tag"
let mode = defaultArg (opt "--mode") "threads"
let jobs =
    opts "--job" |> List.map (fun j ->
        let name, rest = match j.Split('=', 2) with [| a; b |] -> a, b | _ -> failwith "--job name=snap|disk"
        let snap, disk = match rest.Split('|') with [| s; d |] -> s, d | _ -> failwith "--job name=snap|disk"
        name, (snap, disk)) |> Map.ofList
let assign = (req "--assign").Split(',')
let k = assign.Length
let extra = opts "--extra" |> List.map (fun s -> match s.Split('=') with [| i; v |] -> int i, int64 v | _ -> failwith "--extra i=n") |> Map.ofList
let pokes = opts "--poke" |> List.map (fun s -> match s.Split('=') with [| i; a; v |] -> int i, (Convert.ToUInt32(a, 16), Convert.ToByte(v, 16)) | _ -> failwith "--poke i=addr=byte")
IO.Directory.CreateDirectory outDir |> ignore

let gc0 = [| GC.CollectionCount 0; GC.CollectionCount 1; GC.CollectionCount 2 |]
let swLoad = Stopwatch.StartNew()
let machines =
    assign |> Array.mapi (fun i name ->
        let snap, disk = jobs.[name]
        let st = AtartSt(rom, diskAPath = disk)
        st.LoadState(snap, false)
        for (j, (a, v)) in pokes do if j = i then st.Cpu.MMU.WriteByte a v
        st)
let loadMs = swLoad.Elapsed.TotalMilliseconds

let steps i = n + defaultArg (Map.tryFind i extra) 0L
let ms = Array.zeroCreate<float> k
let alloc = Array.zeroCreate<int64> k
let run i =
    let st = machines.[i]
    let a0 = GC.GetAllocatedBytesForCurrentThread()
    let sw = Stopwatch.StartNew()
    let m = steps i
    let mutable s = 0L
    while s < m do
        st.Step()
        s <- s + 1L
    ms.[i] <- sw.Elapsed.TotalMilliseconds
    alloc.[i] <- GC.GetAllocatedBytesForCurrentThread() - a0

let pause0 = GC.GetTotalPauseDuration()
let swRun = Stopwatch.StartNew()
match mode with
| "threads" ->
    use go = new ManualResetEventSlim(false)
    let ts = Array.init k (fun i -> Thread((fun () -> go.Wait(); run i), IsBackground = false))
    for t in ts do t.Start()
    swRun.Restart()
    go.Set()
    for t in ts do t.Join()
| "seq" -> for i in 0 .. k - 1 do run i
| m -> failwithf "unknown --mode %s" m
let runMs = swRun.Elapsed.TotalMilliseconds
let pauseMs = (GC.GetTotalPauseDuration() - pause0).TotalMilliseconds
let gc1 = [| GC.CollectionCount 0; GC.CollectionCount 1; GC.CollectionCount 2 |]
let proc = Process.GetCurrentProcess()
proc.Refresh()
let rss = proc.WorkingSet64
let peak = proc.PeakWorkingSet64

let outs =
    machines |> Array.mapi (fun i st ->
        let p = IO.Path.Combine(outDir, sprintf "%s_%02d_%s.snap" tag i assign.[i])
        st.SaveState p
        p)

let total = Array.init k steps |> Array.sum
let js (s: string) = "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""
let arr (f: int -> string) = "[" + String.Join(",", Array.init k f) + "]"
realOut.WriteLine(
    sprintf "{\"tag\":%s,\"mode\":%s,\"k\":%d,\"n\":%d,\"assign\":%s,\"server_gc\":%b,\"concurrent_gc\":%b,\"latency\":%s,\"runtime\":%s,\"cpus\":%d,\"load_ms\":%.1f,\"run_ms\":%.1f,\"steps_total\":%d,\"steps_per_s\":%.0f,\"thread_ms\":%s,\"alloc_bytes\":%s,\"gc0\":%d,\"gc1\":%d,\"gc2\":%d,\"gc_pause_ms\":%.1f,\"rss\":%d,\"peak_rss\":%d,\"outs\":%s,\"extra\":%s,\"pokes\":%d}"
        (js tag) (js mode) k n (arr (fun i -> js assign.[i])) GCSettings.IsServerGC
        (AppContext.TryGetSwitch("System.GC.Concurrent") |> function | true, v -> v | _ -> true)
        (js (string GCSettings.LatencyMode)) (js (Environment.Version.ToString())) Environment.ProcessorCount
        loadMs runMs total (float total / (runMs / 1000.0)) (arr (fun i -> sprintf "%.1f" ms.[i])) (arr (fun i -> string alloc.[i]))
        (gc1.[0] - gc0.[0]) (gc1.[1] - gc0.[1]) (gc1.[2] - gc0.[2]) pauseMs rss peak (arr (fun i -> js outs.[i]))
        (js (sprintf "%A" (Map.toList extra))) (List.length pokes))
