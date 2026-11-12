// stserver: one long-lived AtartSt behind newline-delimited JSON-RPC 2.0 on stdin/stdout, also
// served as MCP tools (initialize / tools/list / tools/call) on the same transport. Everything that
// is not a response (core diagnostics, Diag.result, state loaded/saved lines) goes to stderr.
// Method table and rationale: M68000/DEVELOPING.md, "Memory hooks and the stserver process".
module StServer.Main

open System
open System.IO
open System.Collections.Generic
open System.Text.Json
open System.Text.Json.Nodes
open Atari

exception RpcError of code: int * message: string
let fail fmt = Printf.kprintf (fun s -> raise (RpcError(-32602, s))) fmt

///The live screen as a PNG: base from the shifter registers ($ff8201/$ff8203), resolution from
///$ff8260 and the palette from $ff8240, as tools/snap_render.py. Reads with Peek (no read hooks).
module Render =
    let private crcTable =
        Array.init 256 (fun n ->
            let mutable c = uint32 n
            for _ in 0 .. 7 do c <- if c &&& 1u <> 0u then 0xEDB88320u ^^^ (c >>> 1) else c >>> 1
            c)
    let private crc (data: byte[]) =
        let mutable c = 0xFFFFFFFFu
        for b in data do c <- crcTable.[int ((c ^^^ uint32 b) &&& 0xFFu)] ^^^ (c >>> 8)
        c ^^^ 0xFFFFFFFFu
    let private be (v: int) = [| byte (v >>> 24); byte (v >>> 16); byte (v >>> 8); byte v |]
    let private deflate (raw: byte[]) =
        use ms = new MemoryStream()
        do
            use z = new Compression.ZLibStream(ms, Compression.CompressionLevel.Optimal, true)
            z.Write(raw, 0, raw.Length)
        ms.ToArray()

    let png (mmu: MMU) (path: string) =
        let baseAddr = (uint32 (mmu.PeekByte 0xFFFF8201u) <<< 16) ||| (uint32 (mmu.PeekByte 0xFFFF8203u) <<< 8)
        let rez = int (mmu.PeekByte 0xFFFF8260u) &&& 3
        let planes, w, h = match rez with 0 -> 4, 320, 200 | 1 -> 2, 640, 200 | _ -> 1, 640, 400
        let scale v = byte ((v &&& 7) * 255 / 7)
        let palette =
            if planes = 1 then [| (255uy, 255uy, 255uy); (0uy, 0uy, 0uy) |]
            else Array.init 16 (fun i ->
                    let c = int (uint16 (mmu.PeekWord (0xFFFF8240u + uint32 (i * 2))))
                    scale (c >>> 8), scale (c >>> 4), scale c)
        let rowBytes = w * planes / 8
        let raw = Array.zeroCreate (h * (1 + w * 3))
        for y in 0 .. h - 1 do
            let o = y * (1 + w * 3)
            for x in 0 .. w - 1 do
                let group = baseAddr + uint32 (y * rowBytes + (x / 16) * planes * 2)
                let bit = 15 - (x % 16)
                let mutable idx = 0
                for pl in 0 .. planes - 1 do
                    let word = int (uint16 (mmu.PeekWord (group + uint32 (pl * 2))))
                    idx <- idx ||| (((word >>> bit) &&& 1) <<< pl)
                let r, g, b = palette.[idx]
                raw.[o + 1 + x * 3] <- r
                raw.[o + 2 + x * 3] <- g
                raw.[o + 3 + x * 3] <- b
        use fs = File.Create path
        let chunk (typ: string) (data: byte[]) =
            let td = Array.append (Text.Encoding.ASCII.GetBytes typ) data
            fs.Write(be data.Length, 0, 4)
            fs.Write(td, 0, td.Length)
            fs.Write(be (int (crc td)), 0, 4)
        fs.Write([| 137uy; 80uy; 78uy; 71uy; 13uy; 10uy; 26uy; 10uy |], 0, 8)
        chunk "IHDR" (Array.concat [ be w; be h; [| 8uy; 2uy; 0uy; 0uy; 0uy |] ])
        chunk "IDAT" (deflate raw)
        chunk "IEND" [||]
        w, h

// ---- JSON helpers -------------------------------------------------------------------------------

let jstr (s: string) : JsonNode = JsonValue.Create s
let jint (i: int64) : JsonNode = JsonValue.Create i
let jbool (b: bool) : JsonNode = JsonValue.Create b
let jarr (xs: JsonNode seq) : JsonNode = JsonArray(Seq.toArray xs)
let obj (kvs: (string * JsonNode) list) : JsonNode =
    let o = JsonObject()
    for k, v in kvs do o.[k] <- v
    o
let hx (v: uint32) = jstr (sprintf "$%06x" v)

///Addresses and values: a JSON number (decimal), or a string in hex with optional `$`/`0x`.
let toU32 (name: string) (n: JsonNode) : uint32 =
    match n with
    | null -> fail "%s: null" name
    | n when n.GetValueKind() = JsonValueKind.Number -> uint32 (n.GetValue<int64>())
    | n when n.GetValueKind() = JsonValueKind.String ->
        let s = n.GetValue<string>().Trim().Replace("$", "").Replace("0x", "").Replace("0X", "")
        try Convert.ToUInt32(s, 16) with _ -> fail "%s: '%s' is not hex" name s
    | _ -> fail "%s: want a number or a hex string" name
let has (p: JsonObject) k = p.ContainsKey k && not (isNull p.[k])
let req (p: JsonObject) k = if has p k then p.[k] else fail "missing parameter '%s'" k
let addr (p: JsonObject) k = toU32 k (req p k)
let optAddr (p: JsonObject) k = if has p k then Some (toU32 k p.[k]) else None
let toInt64 (k: string) (n: JsonNode) =
    if n.GetValueKind() = JsonValueKind.Number then n.GetValue<int64>() else fail "%s: want an integer" k
let int' (p: JsonObject) k = int (toInt64 k (req p k))
let optInt (p: JsonObject) k d = if has p k then int (toInt64 k p.[k]) else d
let str (p: JsonObject) k = match req p k with n when n.GetValueKind() = JsonValueKind.String -> n.GetValue<string>() | _ -> fail "%s: want a string" k
let optBool (p: JsonObject) k d = if has p k then p.[k].GetValue<bool>() else d
let addrList (p: JsonObject) k =
    match req p k with
    | :? JsonArray as a -> [ for n in a -> toU32 k n ]
    | n -> [ toU32 k n ]

// ---- machine state ------------------------------------------------------------------------------

///ROM: `--rom`, else TOS100UK.IMG in the cwd or the first ancestor of the server's own directory
///that holds one (so it works from any cwd).
let findRom () =
    let rec up (d: DirectoryInfo) =
        if isNull d then None
        else
            let f = Path.Combine(d.FullName, "TOS100UK.IMG")
            if File.Exists f then Some f else up d.Parent
    match up (DirectoryInfo(Directory.GetCurrentDirectory())) with
    | Some f -> Some f
    | None -> up (DirectoryInfo(AppContext.BaseDirectory))

let mutable romPath : string option = None
let mutable machine : AtartSt option = None
let need () = match machine with Some s -> s | None -> fail "no machine: call load or boot first"

type Watch =
    { Id: int; Lo: uint32; Hi: uint32; Kind: string; Stop: bool
      PcLo: uint32 option; PcHi: uint32 option; Value: uint32 option; Mask: uint32
      Source: AccessSource option; MaxEvents: int
      Events: ResizeArray<MemAccess>
      mutable Hits: int64; mutable Dropped: int64; mutable New: int64 }

let watches = Dictionary<int, Watch>()
let mutable nextWatchId = 1
let mutable stopRequest : int option = None
let breakpoints = HashSet<uint32>()
let forks = Dictionary<int, MachineCheckpoint>()
let recordings = Dictionary<int, Recording>()
let mutable nextForkId = 1

let installWatch (mmu: MMU) (w: Watch) =
    let pass (a: MemAccess) =
        (match w.PcLo with Some lo -> uint32 a.Pc >= lo | None -> true)
        && (match w.PcHi with Some hi -> uint32 a.Pc <= hi | None -> true)
        && (match w.Value with Some v -> (a.Value &&& w.Mask) = (v &&& w.Mask) | None -> true)
        && (match w.Source with Some s -> a.Source = s | None -> true)
    mmu.AddHook
        { Id = w.Id; Lo = w.Lo; Hi = w.Hi; OnRead = w.Kind.Contains "r"; OnWrite = w.Kind.Contains "w"
          Fire = fun a ->
            if pass a then
                w.Hits <- w.Hits + 1L
                w.New <- w.New + 1L
                if w.Events.Count < w.MaxEvents then w.Events.Add a else w.Dropped <- w.Dropped + 1L
                if w.Stop && stopRequest.IsNone then stopRequest <- Some w.Id }

let sourceName (s: AccessSource) =
    match s with AccessSource.Dma -> "dma" | AccessSource.Host -> "host" | _ -> "cpu"

let eventJson (a: MemAccess) =
    obj [ "step", jint (int64 a.Step); "pc", hx (uint32 a.Pc); "addr", hx a.Address; "width", jint (int64 a.Width)
          "value", jstr (sprintf "$%x" a.Value); "write", jbool a.IsWrite; "source", jstr (sourceName a.Source) ]

///Per-watch counts of events since the last step/run reply.
let newHits () =
    let o = JsonObject()
    for w in watches.Values do
        if w.New > 0L then
            o.[string w.Id] <- jint w.New
            w.New <- 0L
    o :> JsonNode

let status (s: AtartSt) extra =
    obj ([ "pc", hx (uint32 s.Cpu.PC); "step", jint (int64 s.StepCount) ] @ extra)

// ---- execution profile: coverage and compare log ------------------------------------------------

///An execution profile over the steps 'step', 'run' and 'hits' take: every executed instruction
///start (24-bit PC) with its count, and for each compare-class instruction (cmp, cmpa, cmpi, cmpm,
///tst) the distinct operand pairs it ran with. Operands are read before the instruction runs, with
///Peek (no read hooks). An operand in I/O space ($ff8000 and up, 24-bit) or at an odd word address
///is not read, since a device read has side effects: it is recorded as unknown (None). A step that
///takes an interrupt, or idles STOPped or halted, ran no instruction and is not counted. DEVELOPING.md,
///"Execution profile".
module Profile =
    [<Struct; CustomEquality; NoComparison>]
    type CmpKey =
        { Pc: uint32; Size: int; Src: uint32; Dst: uint32; SrcOk: bool; DstOk: bool }
        override k.GetHashCode() = HashCode.Combine(k.Pc, k.Size, k.Src, k.Dst, k.SrcOk, k.DstOk)
        override k.Equals(o) = match o with :? CmpKey as b -> k.Same b | _ -> false
        member k.Same (b: CmpKey) =
            k.Pc = b.Pc && k.Size = b.Size && k.Src = b.Src && k.Dst = b.Dst && k.SrcOk = b.SrcOk && k.DstOk = b.DstOk
        interface IEquatable<CmpKey> with member k.Equals b = k.Same b

    type State =
        { Coverage: Dictionary<uint32, int64>
          Pairs: Dictionary<CmpKey, int64>
          PairsAt: Dictionary<uint32, int>
          Overflow: Dictionary<uint32, int64>
          Kind: Dictionary<uint32, string>
          MaxPairs: int
          BaseStep: uint64
          mutable Steps: int64
          mutable Skipped: int64
          mutable FlagChecks: int64
          mutable FlagMismatches: int64
          MismatchPcs: HashSet<uint32> }

    let mask sz = match sz with 1 -> 0xffu | 2 -> 0xffffu | _ -> 0xffffffffu

    let create maxPairs baseStep =
        { Coverage = Dictionary(); Pairs = Dictionary(); PairsAt = Dictionary(); Overflow = Dictionary()
          Kind = Dictionary(); MaxPairs = maxPairs; BaseStep = baseStep; Steps = 0L; Skipped = 0L
          FlagChecks = 0L; FlagMismatches = 0L; MismatchPcs = HashSet() }

    ///N, Z, V, C (CCR bits 3..0) that `kind` sets from these operands: dst - src, or tst of src.
    let flags (kind: string) sz (src: uint32) (dst: uint32) =
        let m = mask sz
        let msb = (m >>> 1) + 1u
        let src, dst = src &&& m, dst &&& m
        if kind = "tst" then (if src &&& msb <> 0u then 8 else 0) ||| (if src = 0u then 4 else 0)
        else
            let r = (dst - src) &&& m
            (if r &&& msb <> 0u then 8 else 0) ||| (if r = 0u then 4 else 0)
            ||| (if (dst ^^^ src) &&& (dst ^^^ r) &&& msb <> 0u then 2 else 0) ||| (if src > dst then 1 else 0)

    let private dreg (c: Cpu) n =
        match n with 0 -> c.D0 | 1 -> c.D1 | 2 -> c.D2 | 3 -> c.D3 | 4 -> c.D4 | 5 -> c.D5 | 6 -> c.D6 | _ -> c.D7
    let private areg (c: Cpu) n =
        match n with 0 -> c.A0 | 1 -> c.A1 | 2 -> c.A2 | 3 -> c.A3 | 4 -> c.A4 | 5 -> c.A5 | 6 -> c.A6 | _ -> c.A7

    let private peek (mmu: MMU) (a: uint32) sz =
        match sz with
        | 1 -> uint32 (mmu.PeekByte a)
        | 2 -> uint32 (uint16 (mmu.PeekWord a))
        | _ -> uint32 (mmu.PeekLong a)

    ///Memory operand at `a`, or None for I/O space, an odd word/long address or a bus error.
    let private mem (mmu: MMU) (a: int) sz =
        let a = uint32 a &&& 0xffffffu
        if a >= 0xff8000u || (sz > 1 && a % 2u <> 0u) then ValueNone
        else try ValueSome (peek mmu a sz) with _ -> ValueNone

    ///Brief-format index extension word (the only one the 68000 has): Xn.w/.l + d8.
    let private index (c: Cpu) (ext: int) =
        let r = (ext >>> 12) &&& 7
        let v = if ext &&& 0x8000 <> 0 then areg c r else dreg c r
        (if ext &&& 0x0800 <> 0 then v else int (int16 v)) + int (sbyte (byte ext))

    ///The value of effective address (mode, reg) of size `sz`, its extension words starting at `x`.
    let private ea (c: Cpu) (mmu: MMU) mode reg sz (x: uint32) : uint32 voption =
        let w (a: uint32) = int (int16 (mmu.PeekWord a))
        match mode with
        | 0 -> ValueSome (uint32 (dreg c reg))
        | 1 -> ValueSome (uint32 (areg c reg))
        | 2 | 3 -> mem mmu (areg c reg) sz
        | 4 -> mem mmu (areg c reg - (if sz = 1 && reg = 7 then 2 else sz)) sz
        | 5 -> mem mmu (areg c reg + w x) sz
        | 6 -> mem mmu (areg c reg + index c (w x)) sz
        | 7 ->
            match reg with
            | 0 -> mem mmu (w x) sz
            | 1 -> mem mmu (mmu.PeekLong x) sz
            | 2 -> mem mmu (int x + w x) sz
            | 3 -> mem mmu (int x + index c (w x)) sz
            | 4 -> ValueSome (peek mmu (if sz = 1 then x + 1u else x) sz)
            | _ -> ValueNone
        | _ -> ValueNone

    ///A compare-class instruction at the CPU's PC: kind, operand size, source, destination (the
    ///flags are those of destination - source; tst compares its operand with 0).
    let decode (c: Cpu) : struct (string * int * uint32 voption * uint32 voption) voption =
        let mmu = c.MMU
        let pc = uint32 c.PC
        let op = int (uint16 (mmu.PeekWord pc))
        let mode, reg = (op >>> 3) &&& 7, op &&& 7
        let szOf b = match b with 0 -> 1 | 1 -> 2 | _ -> 4
        if op &&& 0xf000 = 0xb000 then
            let rn = (op >>> 9) &&& 7
            match (op >>> 6) &&& 7 with
            | 0 | 1 | 2 as om ->
                let sz = szOf om
                ValueSome (struct ("cmp", sz, ea c mmu mode reg sz (pc + 2u), ValueSome (uint32 (dreg c rn))))
            | 3 ->
                let src = ea c mmu mode reg 2 (pc + 2u) |> ValueOption.map (fun v -> uint32 (int (int16 v)))
                ValueSome (struct ("cmpa", 4, src, ValueSome (uint32 (areg c rn))))
            | 7 -> ValueSome (struct ("cmpa", 4, ea c mmu mode reg 4 (pc + 2u), ValueSome (uint32 (areg c rn))))
            | om when mode = 1 ->
                let sz = szOf (om - 4)
                ValueSome (struct ("cmpm", sz, mem mmu (areg c reg) sz, mem mmu (areg c rn) sz))
            | _ -> ValueNone
        elif op &&& 0xff00 = 0x0c00 && (op >>> 6) &&& 3 <> 3 then
            let sz = szOf ((op >>> 6) &&& 3)
            let imm = peek mmu (if sz = 1 then pc + 3u else pc + 2u) sz
            ValueSome (struct ("cmpi", sz, ValueSome imm, ea c mmu mode reg sz (pc + (if sz = 4 then 6u else 4u))))
        elif op &&& 0xff00 = 0x4a00 && (op >>> 6) &&& 3 <> 3 then
            let sz = szOf ((op >>> 6) &&& 3)
            ValueSome (struct ("tst", sz, ea c mmu mode reg sz (pc + 2u), ValueSome 0u))
        else ValueNone

    let private bump (d: Dictionary<'k, int64>) (k: 'k) =
        match d.TryGetValue k with
        | true, n -> d.[k] <- n + 1L
        | _ -> d.[k] <- 1L

    ///One machine step, profiled.
    let step (p: State) (s: AtartSt) =
        let c = s.Cpu
        if c.Stopped || c.Halted then
            s.Step()
            p.Skipped <- p.Skipped + 1L
        else
            let mmu = c.MMU
            let pc = uint32 c.PC &&& 0xffffffu
            let acks = mmu.InterruptAcks
            let cmp = if pc >= 0xff8000u then ValueNone else (try decode c with _ -> ValueNone)
            s.Step()
            if mmu.InterruptAcks <> acks then p.Skipped <- p.Skipped + 1L
            else
                p.Steps <- p.Steps + 1L
                bump p.Coverage pc
                match cmp with
                | ValueSome (struct (kind, sz, src, dst)) ->
                    let m = mask sz
                    let k = { Pc = pc; Size = sz; Src = (src |> ValueOption.defaultValue 0u) &&& m; SrcOk = src.IsSome
                              Dst = (dst |> ValueOption.defaultValue 0u) &&& m; DstOk = dst.IsSome }
                    p.Kind.[pc] <- kind
                    //Self-check of the operand reads: the flags the instruction left must be the
                    //ones these operands give.
                    if src.IsSome && dst.IsSome then
                        p.FlagChecks <- p.FlagChecks + 1L
                        if int s.Cpu.CCR &&& 0xf <> flags kind sz src.Value dst.Value then
                            p.FlagMismatches <- p.FlagMismatches + 1L
                            if p.MismatchPcs.Count < 32 then p.MismatchPcs.Add pc |> ignore
                    match p.Pairs.TryGetValue k with
                    | true, n -> p.Pairs.[k] <- n + 1L
                    | _ ->
                        let have = match p.PairsAt.TryGetValue pc with | true, n -> n | _ -> 0
                        if have < p.MaxPairs then
                            p.Pairs.[k] <- 1L
                            p.PairsAt.[pc] <- have + 1
                        else bump p.Overflow pc
                | ValueNone -> ()

    let toJson (p: State) (endStep: uint64) : JsonNode =
        let v (ok: bool) (x: uint32) = if ok then jstr (sprintf "$%x" x) else null
        let byPc = p.Pairs |> Seq.groupBy (fun kv -> kv.Key.Pc) |> Map.ofSeq
        let cmpPcs = Seq.append byPc.Keys p.Overflow.Keys |> Seq.distinct |> Seq.sort
        obj [ "base_step", jint (int64 p.BaseStep); "end_step", jint (int64 endStep)
              "steps", jint p.Steps; "skipped", jint p.Skipped
              "flag_checks", jint p.FlagChecks; "flag_mismatches", jint p.FlagMismatches
              "mismatch_pcs", jarr [ for pc in Seq.sort p.MismatchPcs -> hx pc ]
              "coverage", jarr [ for kv in p.Coverage |> Seq.sortBy (fun kv -> kv.Key) ->
                                    obj [ "pc", hx kv.Key; "count", jint kv.Value ] ]
              "compares",
              jarr [ for pc in cmpPcs ->
                      let pairs = match byPc.TryFind pc with Some xs -> List.ofSeq xs | None -> []
                      obj [ "pc", hx pc; "kind", jstr p.Kind.[pc]
                            "size", jint (match pairs with kv :: _ -> int64 kv.Key.Size | [] -> 0L)
                            "overflow", jint (match p.Overflow.TryGetValue pc with | true, n -> n | _ -> 0L)
                            "pairs", jarr [ for kv in pairs |> List.sortByDescending (fun kv -> kv.Value) ->
                                              obj [ "src", v kv.Key.SrcOk kv.Key.Src; "dst", v kv.Key.DstOk kv.Key.Dst
                                                    "count", jint kv.Value ] ] ] ] ]

///The active profile; None costs the step loops one test per step.
let mutable profile : Profile.State option = None
let stepOne (s: AtartSt) =
    match profile with
    | None -> s.Step()
    | Some p -> Profile.step p s

// ---- methods ------------------------------------------------------------------------------------

///A recording's journal holds only inputs, so a jump to another state would break it.
let notRecording (verb: string) =
    match machine |> Option.bind (fun s -> s.Recording) with
    | Some r when r.Active -> fail "%s: a recording is active; call record_stop first" verb
    | _ -> ()

///The machine for `load`/`boot`, with drive A set from the required `disk` key.
let prepare (verb: string) (p: JsonObject) =
    notRecording verb
    if not (p.ContainsKey "disk") then
        fail "%s: 'disk' is required: the .st the snapshot was taken with, or null for none" verb
    let disk = if isNull p.["disk"] then None else Some (str p "disk")
    disk |> Option.iter (fun d -> if not (File.Exists d) then fail "load: no such disk image %s" d)
    let rom = if has p "rom" then Some (str p "rom") else romPath |> Option.orElse (findRom ())
    let rom = match rom with Some r -> r | None -> fail "%s: no TOS100UK.IMG found; pass rom" verb
    let s =
        match machine with
        | Some s when romPath = Some rom -> s
        | _ ->
            let s = AtartSt(rom)
            forks.Clear()
            recordings.Clear()
            for w in watches.Values do installWatch s.Cpu.MMU w
            machine <- Some s
            romPath <- Some rom
            s
    s.MountDiskA disk
    s

let methods : (string * string * (string * string * bool * string) list * (JsonObject -> JsonNode)) list =
  [ "load", "Load a snapshot. 'disk' is required unless the snapshot has a provenance sidecar (<snap>.prov.json), which remounts the disk it records: the .st it was taken with, or null if it had none.",
    [ "snapshot", "string", true, "snapshot path"; "disk", "string|null", false, ".st image for drive A, or null; omit to use the sidecar's"
      "rom", "string", false, "TOS ROM (default: TOS100UK.IMG found from the cwd or the server's directory)" ],
    fun p ->
        let snap = str p "snapshot"
        if not (File.Exists snap) then fail "load: no such snapshot %s" snap
        let fromSidecar = not (p.ContainsKey "disk") && (match Provenance.tryRead snap with Some (Ok _) -> true | _ -> false)
        if fromSidecar then p.["disk"] <- null
        let s = prepare "load" p
        s.LoadState(snap, remountDisk = fromSidecar)
        status s []

    "boot", "Cold boot (reset) with a disk in drive A or none; then 'run' or 'step'.",
    [ "disk", "string|null", true, ".st image, or null"; "rom", "string", false, "TOS ROM" ],
    fun p ->
        let s = prepare "boot" p
        s.Reset()
        status s []

    "save", "Save the machine to a snapshot file.",
    [ "path", "string", true, "output path" ],
    fun p -> let s = need () in s.SaveState (str p "path"); status s []

    "regs", "CPU registers, SR and the step counter.", [],
    fun _ ->
        let s = need ()
        let c = s.Cpu
        let r n (v: int) = n, jstr (sprintf "$%08x" v)
        obj [ r "d0" c.D0; r "d1" c.D1; r "d2" c.D2; r "d3" c.D3; r "d4" c.D4; r "d5" c.D5; r "d6" c.D6; r "d7" c.D7
              r "a0" c.A0; r "a1" c.A1; r "a2" c.A2; r "a3" c.A3; r "a4" c.A4; r "a5" c.A5; r "a6" c.A6; r "a7" c.A7
              r "usp" c.USP; r "ssp" c.SSP; r "pc" c.PC; "sr", jstr (sprintf "$%04x" (uint16 c.CCR))
              "step", jint (int64 s.StepCount); "stopped", jbool c.Stopped; "halted", jbool c.Halted ]

    "set_reg", "Set one register (d0-d7, a0-a7, usp, ssp, pc, sr).",
    [ "name", "string", true, "register"; "value", "addr", true, "value" ],
    fun p ->
        let s = need ()
        let v = int (addr p "value")
        let c = s.Cpu
        s.Input (SetCpu <|
            match (str p "name").ToLowerInvariant() with
            | "d0" -> { c with D0 = v } | "d1" -> { c with D1 = v } | "d2" -> { c with D2 = v } | "d3" -> { c with D3 = v }
            | "d4" -> { c with D4 = v } | "d5" -> { c with D5 = v } | "d6" -> { c with D6 = v } | "d7" -> { c with D7 = v }
            | "a0" -> { c with A0 = v } | "a1" -> { c with A1 = v } | "a2" -> { c with A2 = v } | "a3" -> { c with A3 = v }
            | "a4" -> { c with A4 = v } | "a5" -> { c with A5 = v } | "a6" -> { c with A6 = v } | "a7" -> { c with A7 = v }
            | "usp" -> { c with USP = v } | "ssp" -> { c with SSP = v } | "pc" -> { c with PC = v }
            | "sr" -> { c with CCR = int16 v }
            | n -> fail "set_reg: unknown register %s" n)
        status s []

    "peek", "Read 'count' values of 'width' bytes (1, 2 or 4) from addr. Does not fire read watches.",
    [ "addr", "addr", true, "address"; "width", "int", true, "1, 2 or 4"; "count", "int", false, "default 1" ],
    fun p ->
        let mmu = (need ()).Cpu.MMU
        let a = addr p "addr"
        let w = int' p "width"
        let rd (x: uint32) =
            match w with
            | 1 -> uint32 (mmu.PeekByte x)
            | 2 -> uint32 (uint16 (mmu.PeekWord x))
            | 4 -> uint32 (mmu.PeekLong x)
            | _ -> fail "peek: width must be 1, 2 or 4"
        jarr [ for i in 0 .. optInt p "count" 1 - 1 -> jstr (sprintf "$%0*x" (w * 2) (rd (a + uint32 (i * w)))) ]

    "read", "Read len bytes from addr as a hex string. Does not fire read watches.",
    [ "addr", "addr", true, "address"; "len", "int", true, "byte count" ],
    fun p ->
        let mmu = (need ()).Cpu.MMU
        let a = addr p "addr"
        jstr (String.Join("", [| for i in 0 .. int' p "len" - 1 -> sprintf "%02x" (mmu.PeekByte (a + uint32 i)) |]))

    "poke", "Write a value of 'width' bytes (1, 2 or 4). Fires write watches with source 'host'.",
    [ "addr", "addr", true, "address"; "width", "int", true, "1, 2 or 4"; "value", "addr", true, "value" ],
    fun p ->
        let s = need ()
        let w = int' p "width"
        if w <> 1 && w <> 2 && w <> 4 then fail "poke: width must be 1, 2 or 4"
        s.Input (HostWrite (addr p "addr", w, addr p "value"))
        obj [ "watch_hits", newHits () ]

    "step", "Run exactly n instructions (breakpoints and stop watches are not checked).",
    [ "n", "int", true, "instructions" ],
    fun p ->
        let s = need ()
        let n = int' p "n"
        let mutable i = 0
        let err =
            try
                while i < n do
                    stepOne s
                    i <- i + 1
                None
            with e -> Some e.Message
        status s ([ "steps", jint (int64 i); "watch_hits", newHits () ]
                  @ (match err with Some m -> [ "error", jstr m ] | None -> []))

    "run", "Run up to max_steps, stopping at a breakpoint, a stop watch, or the count-th arrival at an until_pc address.",
    [ "max_steps", "int", true, "step budget"; "until_pc", "addr[]", false, "addresses to run to"
      "count", "int", false, "stop on the count-th until_pc arrival (default 1)" ],
    fun p ->
        let s = need ()
        let maxSteps = int' p "max_steps"
        let until = HashSet<uint32>(if has p "until_pc" then addrList p "until_pc" else [])
        let count = optInt p "count" 1
        stopRequest <- None
        let mutable n = 0
        let mutable untilHits = 0
        let mutable reason = ""
        let mutable extra = []
        (try
            while reason = "" && n < maxSteps do
                stepOne s
                n <- n + 1
                let pc = uint32 s.Cpu.PC
                match stopRequest with
                | Some id ->
                    reason <- "watch"
                    extra <- [ "watch", jint (int64 id) ]
                | None ->
                    if breakpoints.Contains pc then reason <- "breakpoint"
                    elif until.Contains pc then
                        untilHits <- untilHits + 1
                        if untilHits >= count then reason <- "until"
                    elif s.Cpu.Halted then reason <- "halted"
            if reason = "" then reason <- "max_steps"
         with e ->
            reason <- "error"
            extra <- [ "error", jstr e.Message ])
        stopRequest <- None
        status s ([ "reason", jstr reason; "steps", jint (int64 n); "watch_hits", newHits () ] @ extra)

    "bp_set", "Add PC breakpoints that 'run' stops on.", [ "addrs", "addr[]", true, "addresses" ],
    fun p -> (for a in addrList p "addrs" do breakpoints.Add a |> ignore); jarr [ for b in breakpoints -> hx b ]

    "bp_clear", "Remove breakpoints (all when addrs is absent).", [ "addrs", "addr[]", false, "addresses" ],
    fun p ->
        if has p "addrs" then (for a in addrList p "addrs" do breakpoints.Remove a |> ignore) else breakpoints.Clear()
        jarr [ for b in breakpoints -> hx b ]

    "bp_list", "List breakpoints.", [], fun _ -> jarr [ for b in breakpoints -> hx b ]

    "watch_add",
    "Watch [lo,hi] (inclusive) for reads ('r'), writes ('w') or both ('rw'); an access matches if any of its bytes overlap. Reads include instruction fetches. Optional filters: writer PC range, value under mask, source (cpu/dma/host). stop=true makes 'run' stop after the matching instruction.",
    [ "lo", "addr", true, "first address"; "hi", "addr", false, "last address (default lo)"; "kind", "string", false, "r, w or rw (default w)"
      "stop", "bool", false, "stop 'run' on a match"; "pc_lo", "addr", false, "accessing PC >= this"; "pc_hi", "addr", false, "accessing PC <= this"
      "value", "addr", false, "value to match"; "mask", "addr", false, "mask for value (default $ffffffff)"
      "source", "string", false, "cpu, dma or host"; "max_events", "int", false, "events kept (default 10000; the rest are counted as dropped)" ],
    fun p ->
        let mmu = (need ()).Cpu.MMU
        let lo = addr p "lo"
        let kind = if has p "kind" then str p "kind" else "w"
        if kind <> "r" && kind <> "w" && kind <> "rw" then fail "watch_add: kind must be r, w or rw"
        let w =
            { Id = nextWatchId; Lo = lo; Hi = defaultArg (optAddr p "hi") lo; Kind = kind; Stop = optBool p "stop" false
              PcLo = optAddr p "pc_lo"; PcHi = optAddr p "pc_hi"; Value = optAddr p "value"
              Mask = defaultArg (optAddr p "mask") 0xffffffffu
              Source = (if has p "source" then
                            match str p "source" with
                            | "cpu" -> Some AccessSource.Cpu | "dma" -> Some AccessSource.Dma | "host" -> Some AccessSource.Host
                            | s -> fail "watch_add: source %s" s
                        else None)
              MaxEvents = optInt p "max_events" 10000; Events = ResizeArray(); Hits = 0L; Dropped = 0L; New = 0L }
        nextWatchId <- nextWatchId + 1
        watches.[w.Id] <- w
        installWatch mmu w
        obj [ "id", jint (int64 w.Id) ]

    "watch_remove", "Remove a watch.", [ "id", "int", true, "watch id" ],
    fun p ->
        let id = int' p "id"
        if not (watches.Remove id) then fail "watch_remove: no watch %d" id
        machine |> Option.iter (fun s -> s.Cpu.MMU.RemoveHook id)
        obj []

    "watch_list", "List watches with their hit counts.", [],
    fun _ ->
        jarr [ for w in watches.Values ->
                obj [ "id", jint (int64 w.Id); "lo", hx w.Lo; "hi", hx w.Hi; "kind", jstr w.Kind; "stop", jbool w.Stop
                      "hits", jint w.Hits; "buffered", jint (int64 w.Events.Count); "dropped", jint w.Dropped ] ]

    "watch_events", "Buffered events of one watch (or all), oldest first; cleared unless clear=false.",
    [ "id", "int", false, "watch id (default all)"; "clear", "bool", false, "default true" ],
    fun p ->
        let ws = if has p "id" then (match watches.TryGetValue (int' p "id") with | true, w -> [ w ] | _ -> fail "no watch %d" (int' p "id")) else List.ofSeq watches.Values
        let res =
            jarr [ for w in ws ->
                    obj [ "id", jint (int64 w.Id); "dropped", jint w.Dropped; "events", jarr [ for a in w.Events -> eventJson a ] ] ]
        if optBool p "clear" true then for w in ws do w.Events.Clear(); w.Dropped <- 0L
        res

    "hits", "Run exactly 'steps' instructions and count PC arrivals at each address (first and last step, 1-based).",
    [ "steps", "int", true, "instructions"; "addrs", "addr[]", true, "addresses" ],
    fun p ->
        let s = need ()
        let targets = addrList p "addrs"
        let counts = Dictionary<uint32, int64 * int64 * int64>()
        for t in targets do counts.[t] <- (0L, -1L, -1L)
        for i in 1L .. int64 (int' p "steps") do
            stepOne s
            match counts.TryGetValue (uint32 s.Cpu.PC) with
            | true, (n, f, _) -> counts.[uint32 s.Cpu.PC] <- (n + 1L, (if f < 0L then i else f), i)
            | _ -> ()
        status s [ "hits", jarr [ for t in targets ->
                                    let n, f, l = counts.[t]
                                    obj [ "addr", hx t; "count", jint n; "first", jint f; "last", jint l ] ]
                   "watch_hits", newHits () ]

    "profile_start", "Start an execution profile over the instructions 'step', 'run' and 'hits' execute from now: each executed PC with its count, and each compare (cmp, cmpa, cmpi, cmpm, tst) with the distinct operand pairs it ran with (up to max_pairs per PC; the rest are counted as overflow). Replaces a running profile. The profile follows the server, not the machine: stop it before a restore or load you do not want in it.",
    [ "max_pairs", "int", false, "distinct operand pairs kept per compare PC (default 256)" ],
    fun p ->
        let s = need ()
        profile <- Some (Profile.create (optInt p "max_pairs" 256) s.StepCount)
        status s []

    "profile_stop", "End the profile and write it to 'path' as JSON (coverage and compares; diff two with tools/profdiff.py). Returns the counts.",
    [ "path", "string", true, "output .json" ],
    fun p ->
        let s = need ()
        match profile with
        | None -> fail "profile_stop: no profile running"
        | Some pr ->
            profile <- None
            File.WriteAllText(str p "path", (Profile.toJson pr s.StepCount).ToJsonString())
            status s [ "steps", jint pr.Steps; "skipped", jint pr.Skipped; "pcs", jint (int64 pr.Coverage.Count)
                       "compare_pcs", jint (int64 pr.Kind.Count); "pairs", jint (int64 pr.Pairs.Count)
                       "overflow_pcs", jint (int64 pr.Overflow.Count)
                       "flag_checks", jint pr.FlagChecks; "flag_mismatches", jint pr.FlagMismatches
                       "mismatch_pcs", jarr [ for pc in Seq.sort pr.MismatchPcs -> hx pc ] ]

    "fork", "Checkpoint the whole machine in memory; returns an id for 'restore'.", [],
    fun _ ->
        let s = need ()
        let id = nextForkId
        nextForkId <- nextForkId + 1
        forks.[id] <- s.Capture()
        obj [ "id", jint (int64 id); "pc", hx (uint32 s.Cpu.PC); "step", jint (int64 s.StepCount) ]

    "restore", "Return the machine to a fork (the fork stays usable).", [ "id", "int", true, "fork id" ],
    fun p ->
        let s = need ()
        notRecording "restore"
        match forks.TryGetValue (int' p "id") with
        | true, c -> s.Restore c; status s []
        | _ -> fail "restore: no fork %d" (int' p "id")

    "drop", "Free a fork.", [ "id", "int", true, "fork id" ],
    fun p -> (if not (forks.Remove (int' p "id")) then fail "drop: no fork %d" (int' p "id")); obj []

    "render", "Write the live screen as a PNG (shifter base, resolution and palette).",
    [ "path", "string", true, "output .png" ],
    fun p -> let w, h = Render.png (need ()).Cpu.MMU (str p "path") in obj [ "width", jint (int64 w); "height", jint (int64 h) ]

    "kbd", "Queue raw IKBD bytes (make/break scancodes, packets).", [ "bytes", "addr[]", true, "hex bytes" ],
    fun p -> (need ()).Input (Ikbd [| for b in addrList p "bytes" -> byte b |]); obj []

    "mouse", "Mouse: action 'move' with dx/dy, or 'down'/'up' with button 'l'/'r'.",
    [ "action", "string", true, "move, down or up"; "dx", "int", false, "move x"; "dy", "int", false, "move y"; "button", "string", false, "l or r" ],
    fun p ->
        let s = need ()
        match str p "action" with
        | "move" -> s.Input (MouseMove (optInt p "dx" 0, optInt p "dy" 0))
        | "down" | "up" as ud -> s.Input (MouseButton ((str p "button").StartsWith "l", (ud = "down")))
        | a -> fail "mouse: action %s" a
        obj []

    "disk", "Swap drive A's image (null ejects).", [ "path", "string|null", true, "a .st, or null" ],
    fun p ->
        let s = need ()
        if not (p.ContainsKey "path") then fail "disk: 'path' is required (or null)"
        s.Input (DiskA (if isNull p.["path"] then None else Some (str p "path")))
        obj []

    "record_start", "Start a recording here: a base checkpoint, one every 'every' steps, and a journal of every input (poke, set_reg, kbd, mouse, disk). load, boot and restore are refused until record_stop. With 'dir', every checkpoint is also written there as a snapshot (base.snap, ck_<step>.snap), only the newest 'keep' stay in memory, and record_stop writes journal.jsonl and recording.json for record_load.",
    [ "every", "int", true, "steps between checkpoints"
      "dir", "string", false, "directory to write the recording to (new or empty of a recording)"
      "keep", "int", false, "with dir: checkpoints kept in memory, default 16" ],
    fun p ->
        let s = need ()
        let every = uint64 (toInt64 "every" (req p "every"))
        if has p "dir" then s.RecordStart (every, str p "dir", optInt p "keep" 16) else s.RecordStart every
        status s []

    "record_stop", "End the recording and keep it under the returned id; replay_to and last_writer then work on it (record_use picks another).", [],
    fun _ ->
        let s = need ()
        s.RecordStop ()
        let r = s.Recording.Value
        let id = recordings.Count + 1
        recordings.[id] <- r
        status s [ "id", jint (int64 id); "base", jint (int64 r.Checkpoints.[0].At); "end", jint (int64 r.End)
                   "checkpoints", jint (int64 r.Checkpoints.Count); "inputs", jint (int64 r.Journal.Count)
                   "dir", (match r.Dir with Some d -> jstr d | None -> null); "disk_written", jbool r.DiskWritten ]

    "record_load", "Load a recording record_start wrote to 'dir': loads its base.snap as 'load' does (the sidecar remounts the disk unless 'disk' is given), then keeps the recording under the returned id and makes it the current one. Refused for a run that wrote to disk A.",
    [ "dir", "string", true, "the recording's directory"; "disk", "string|null", false, ".st image for drive A, or null; omit to use the base snapshot's sidecar"
      "rom", "string", false, "TOS ROM" ],
    fun p ->
        let dir = str p "dir"
        let snap = Path.Combine(dir, "base.snap")
        if not (File.Exists snap) then fail "record_load: no base.snap in %s" dir
        let fromSidecar = not (p.ContainsKey "disk") && (match Provenance.tryRead snap with Some (Ok _) -> true | _ -> false)
        if fromSidecar then p.["disk"] <- null
        let s = prepare "record_load" p
        let r = s.RecordLoad dir
        s.LoadState(snap, remountDisk = fromSidecar)
        if s.StepCount <> r.Checkpoints.[0].At then fail "record_load: base.snap is at step %d, the manifest's base at %d" s.StepCount r.Checkpoints.[0].At
        let id = recordings.Count + 1
        recordings.[id] <- r
        s.Recording <- Some r
        status s [ "id", jint (int64 id); "base", jint (int64 r.Checkpoints.[0].At); "end", jint (int64 r.End)
                   "checkpoints", jint (int64 r.Checkpoints.Count); "inputs", jint (int64 r.Journal.Count) ]

    "record_use", "Make a stopped recording the one replay_to and last_writer work on.", [ "id", "int", true, "recording id" ],
    fun p ->
        let s = need ()
        match recordings.TryGetValue (int' p "id") with
        | true, r -> s.Recording <- Some r; obj []
        | _ -> fail "record_use: no recording %d" (int' p "id")

    "first_divergence", "The first step at which two stopped recordings from the same base differ (RAM, registers, device phase), both PCs and the first differing RAM bytes; null if none up to the shorter's end. Assumes a divergence persists to the next checkpoint. The machine is left at an arbitrary point.",
    [ "a", "int", true, "recording id"; "b", "int", true, "recording id" ],
    fun p ->
        let s = need ()
        let get k = match recordings.TryGetValue (int' p k) with | true, r -> r | _ -> fail "first_divergence: no recording %d" (int' p k)
        match s.FirstDivergence (get "a", get "b") with
        | None -> obj [ "divergence", null ]
        | Some d ->
            obj [ "divergence",
                  obj [ "step", jint (int64 d.At); "pc_a", hx (uint32 d.PcA); "pc_b", hx (uint32 d.PcB)
                        "journal_step", (match d.JournalAt with Some j -> jint (int64 j) | None -> null)
                        "bytes", jarr [ for (ad, va, vb) in d.Bytes -> obj [ "addr", hx ad; "a", jstr (sprintf "$%02x" va); "b", jstr (sprintf "$%02x" vb) ] ] ] ]

    "replay_to", "Put the machine where the stopped recording was at step 'step' (after the inputs journalled there): restore the last checkpoint at or before it and re-apply the journal. Watches fire during the replay.",
    [ "step", "int", true, "absolute step count" ],
    fun p ->
        let s = need ()
        let from = s.ReplayTo (uint64 (toInt64 "step" (req p "step")))
        status s [ "from_checkpoint", jint (int64 from); "watch_hits", newHits () ]

    "last_writer", "The last write overlapping [lo,hi] at or before step 'step' of the stopped recording (event as watch_events gives it, or null), found by replaying checkpoint intervals backwards. The machine is left at the end of the last interval replayed; replay_to to continue.",
    [ "lo", "addr", true, "first address"; "hi", "addr", false, "last address (default lo)"; "step", "int", true, "absolute step count" ],
    fun p ->
        let s = need ()
        let lo = addr p "lo"
        let ev, searched = s.LastWriter (lo, defaultArg (optAddr p "hi") lo, uint64 (toInt64 "step" (req p "step")))
        status s [ "event", (match ev with Some a -> eventJson a | None -> null); "intervals", jint (int64 searched)
                   "watch_hits", newHits () ]

    "last_reg_change", "The last step at or before 'step' of the stopped recording at which register 'reg' (d0-d7, a0-a7, usp, ssp, sr) changed in the bits of 'mask': step (as last_writer gives it: the instruction that took step-1 to step), pc (that instruction's address), value, previous, source (cpu, exception for an interrupt entry, host for a journalled set_reg), or null back to the base. Found by stepping checkpoint intervals backwards. A write that leaves the value unchanged is not a change. The machine is left at the end of the last interval replayed.",
    [ "reg", "string", true, "register"; "step", "int", true, "absolute step count"; "mask", "addr", false, "bits that count (default $ffffffff)" ],
    fun p ->
        let s = need ()
        let target = uint64 (toInt64 "step" (req p "step"))
        let mask = defaultArg (optAddr p "mask") 0xffffffffu
        let name = (str p "reg").ToLowerInvariant()
        let names = [| "d0"; "d1"; "d2"; "d3"; "d4"; "d5"; "d6"; "d7"; "a0"; "a1"; "a2"; "a3"; "a4"; "a5"; "a6"; "a7"; "usp"; "ssp"; "sr" |]
        let ri = match Array.tryFindIndex ((=) name) names with Some i -> i | None -> fail "last_reg_change: unknown register %s" name
        let get (c: Cpu) : uint32 =
            match ri with
            | 0 -> uint32 c.D0 | 1 -> uint32 c.D1 | 2 -> uint32 c.D2 | 3 -> uint32 c.D3
            | 4 -> uint32 c.D4 | 5 -> uint32 c.D5 | 6 -> uint32 c.D6 | 7 -> uint32 c.D7
            | 8 -> uint32 c.A0 | 9 -> uint32 c.A1 | 10 -> uint32 c.A2 | 11 -> uint32 c.A3
            | 12 -> uint32 c.A4 | 13 -> uint32 c.A5 | 14 -> uint32 c.A6 | 15 -> uint32 c.A7
            | 16 -> uint32 c.USP | 17 -> uint32 c.SSP | _ -> uint32 (uint16 c.CCR)
        let r =
            match s.Recording with
            | Some r when r.Active -> fail "last_reg_change: stop the recording first"
            | Some r -> r
            | None -> fail "last_reg_change: no recording"
        if target < r.Checkpoints.[0].At || target > r.End then
            fail "last_reg_change: step %d is outside the recording (%d..%d)" target r.Checkpoints.[0].At r.End
        let mmu = s.Cpu.MMU
        //Interval k covers changes at steps (ck.At, upto]: a change at ck.At itself needs the state at
        //ck.At-1, which the interval before holds. The journal is re-applied as ReplayTo does
        //(AtartSt.ReplayFrom): after the step it was recorded at, and `Input` does not journal into a
        //stopped recording. A disk swap is refused by ReplayTo itself.
        let scan (k: int) =
            let ck = r.Checkpoints.[k]
            let upto = if k + 1 < r.Checkpoints.Count then min target r.Checkpoints.[k + 1].At else target
            s.ReplayTo ck.At |> ignore
            let mutable j = ck.Index
            while j < r.Journal.Count && r.Journal.[j].At <= ck.At do j <- j + 1
            let mutable last = None
            while s.StepCount < upto do
                let pre = s.Cpu
                let acks = mmu.InterruptAcks
                s.Step()
                let v = get s.Cpu
                if (v ^^^ get pre) &&& mask <> 0u then
                    last <- Some (s.StepCount, uint32 pre.PC, v, get pre, (if mmu.InterruptAcks <> acks then "exception" else "cpu"))
                while j < r.Journal.Count && r.Journal.[j].At = s.StepCount do
                    let before = get s.Cpu
                    s.Input r.Journal.[j].Input
                    j <- j + 1
                    let v = get s.Cpu
                    if (v ^^^ before) &&& mask <> 0u then
                        last <- Some (s.StepCount, uint32 s.Cpu.PC, v, before, "host")
            last
        let mutable k = r.Checkpoints |> Seq.findIndexBack (fun c -> c.At <= target)
        let mutable found = None
        let mutable searched = 0
        let mutable stop = false
        while not stop do
            found <- scan k
            searched <- searched + 1
            if found.IsSome || k = 0 then stop <- true else k <- k - 1
        let ev =
            match found with
            | None -> null
            | Some (at, pc, v, prev, src) ->
                obj [ "step", jint (int64 at); "pc", hx pc; "reg", jstr name; "value", jstr (sprintf "$%08x" v)
                      "previous", jstr (sprintf "$%08x" prev); "source", jstr src ]
        status s [ "event", ev; "intervals", jint (int64 searched); "watch_hits", newHits () ] ]

let table = dict [ for (n, _, _, f) in methods -> n, f ]

// ---- MCP ----------------------------------------------------------------------------------------

let schemaType (t: string) : JsonNode =
    match t with
    | "addr" -> obj [ "type", jarr [ jstr "integer"; jstr "string" ] ]
    | "addr[]" -> obj [ "type", jarr [ jstr "array"; jstr "integer"; jstr "string" ]
                        "items", obj [ "type", jarr [ jstr "integer"; jstr "string" ] ] ]
    | "string|null" -> obj [ "type", jarr [ jstr "string"; jstr "null" ] ]
    | "int" -> obj [ "type", jstr "integer" ]
    | "bool" -> obj [ "type", jstr "boolean" ]
    | t -> obj [ "type", jstr t ]

let toolList () =
    obj [ "tools",
          jarr [ for (name, desc, ps, _) in methods ->
                  let props = JsonObject()
                  for (pn, pt, _, pd) in ps do
                      let s = schemaType pt :?> JsonObject
                      s.["description"] <- jstr pd
                      props.[pn] <- s
                  obj [ "name", jstr name
                        "description", jstr (desc + " Addresses and values: integers, or hex strings ($189ca, 0x189ca, 189ca).")
                        "inputSchema", obj [ "type", jstr "object"; "properties", props
                                             "required", jarr [ for (pn, _, r, _) in ps do if r then yield jstr pn ] ] ] ] ]

let call (name: string) (p: JsonObject) =
    match table.TryGetValue name with
    | true, f -> f p
    | _ -> raise (RpcError(-32601, sprintf "unknown method %s" name))

let dispatch (methodName: string) (p: JsonObject) : JsonNode =
    match methodName with
    | "initialize" ->
        let v = if has p "protocolVersion" then p.["protocolVersion"].DeepClone() else jstr "2025-06-18"
        obj [ "protocolVersion", v; "capabilities", obj [ "tools", obj [] ]
              "serverInfo", obj [ "name", jstr "stserver"; "version", jstr "1.0" ] ]
    | "ping" -> obj []
    | "tools/list" -> toolList ()
    | "tools/call" ->
        let args = if has p "arguments" then p.["arguments"] :?> JsonObject else JsonObject()
        let text, isErr =
            try (call (str p "name") args).ToJsonString(), false
            with
            | RpcError(_, m) -> m, true
            | e -> e.Message, true
        obj [ "content", jarr [ obj [ "type", jstr "text"; "text", jstr text ] ]; "isError", jbool isErr ]
    | m -> call m p

[<EntryPoint>]
let main argv =
    let argOf k = argv |> Array.tryFindIndex ((=) k) |> Option.map (fun i -> argv.[i + 1])
    romPath <- argOf "--rom" |> Option.map Path.GetFullPath
    let out = new StreamWriter(Console.OpenStandardOutput(), Text.UTF8Encoding(false))
    out.AutoFlush <- true
    // The core's result lines (Diag.result) and everything else go to stderr; stdout carries only
    // JSON-RPC responses. Trace is off: there is no per-instruction output to opt out of.
    Console.SetOut(Console.Error)
    Diag.captureResultOut ()
    Console.SetOut(IO.TextWriter.Null)
    Trace.enabled <- false
    let reply (id: JsonNode) (body: string * JsonNode) =
        if not (isNull id) then
            out.WriteLine((obj [ "jsonrpc", jstr "2.0"; "id", id.DeepClone(); body ]).ToJsonString())
    let error code (msg: string) = "error", obj [ "code", jint (int64 code); "message", jstr msg ]
    let mutable running = true
    while running do
        let line = Console.In.ReadLine()
        if isNull line then running <- false
        elif line.Trim() <> "" then
            match (try Ok (JsonNode.Parse line) with e -> Error e.Message) with
            | Error m -> out.WriteLine((obj [ "jsonrpc", jstr "2.0"; "id", null; error -32700 m ]).ToJsonString())
            | Ok msg ->
                let msg = msg :?> JsonObject
                let id = if msg.ContainsKey "id" then msg.["id"] else null
                let methodName = if has msg "method" then msg.["method"].GetValue<string>() else ""
                let p = if has msg "params" then msg.["params"] :?> JsonObject else JsonObject()
                if methodName = "shutdown" then
                    reply id ("result", obj [])
                    running <- false
                elif methodName.StartsWith "notifications/" then ()
                else
                    let body =
                        try "result", dispatch methodName p
                        with
                        | RpcError(c, m) -> error c m
                        | e -> error -32000 e.Message
                    reply id body
    0
