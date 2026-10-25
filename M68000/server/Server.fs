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

// ---- methods ------------------------------------------------------------------------------------

///The machine for `load`/`boot`, with drive A set from the required `disk` key.
let prepare (verb: string) (p: JsonObject) =
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
            for w in watches.Values do installWatch s.Cpu.MMU w
            machine <- Some s
            romPath <- Some rom
            s
    s.Cpu.MMU.LoadDiskA (disk |> Option.map File.ReadAllBytes)
    s

let methods : (string * string * (string * string * bool * string) list * (JsonObject -> JsonNode)) list =
  [ "load", "Load a snapshot. 'disk' is required: the .st it was taken with, or null if it had none.",
    [ "snapshot", "string", true, "snapshot path"; "disk", "string|null", true, ".st image for drive A, or null"
      "rom", "string", false, "TOS ROM (default: TOS100UK.IMG found from the cwd or the server's directory)" ],
    fun p ->
        let snap = str p "snapshot"
        if not (File.Exists snap) then fail "load: no such snapshot %s" snap
        let s = prepare "load" p
        s.LoadState snap
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
        s.Cpu <-
            match (str p "name").ToLowerInvariant() with
            | "d0" -> { c with D0 = v } | "d1" -> { c with D1 = v } | "d2" -> { c with D2 = v } | "d3" -> { c with D3 = v }
            | "d4" -> { c with D4 = v } | "d5" -> { c with D5 = v } | "d6" -> { c with D6 = v } | "d7" -> { c with D7 = v }
            | "a0" -> { c with A0 = v } | "a1" -> { c with A1 = v } | "a2" -> { c with A2 = v } | "a3" -> { c with A3 = v }
            | "a4" -> { c with A4 = v } | "a5" -> { c with A5 = v } | "a6" -> { c with A6 = v } | "a7" -> { c with A7 = v }
            | "usp" -> { c with USP = v } | "ssp" -> { c with SSP = v } | "pc" -> { c with PC = v }
            | "sr" -> { c with CCR = int16 v }
            | n -> fail "set_reg: unknown register %s" n
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
        let mmu = (need ()).Cpu.MMU
        let a = addr p "addr"
        let v = addr p "value"
        mmu.HostAccess <- true
        try
            match int' p "width" with
            | 1 -> mmu.WriteByte a (byte v)
            | 2 -> mmu.WriteWord a (int16 v)
            | 4 -> mmu.WriteLong a (int v)
            | _ -> fail "poke: width must be 1, 2 or 4"
        finally mmu.HostAccess <- false
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
                    s.Step()
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
                s.Step()
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
            s.Step()
            match counts.TryGetValue (uint32 s.Cpu.PC) with
            | true, (n, f, _) -> counts.[uint32 s.Cpu.PC] <- (n + 1L, (if f < 0L then i else f), i)
            | _ -> ()
        status s [ "hits", jarr [ for t in targets ->
                                    let n, f, l = counts.[t]
                                    obj [ "addr", hx t; "count", jint n; "first", jint f; "last", jint l ] ]
                   "watch_hits", newHits () ]

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
        match forks.TryGetValue (int' p "id") with
        | true, c -> s.Restore c; status s []
        | _ -> fail "restore: no fork %d" (int' p "id")

    "drop", "Free a fork.", [ "id", "int", true, "fork id" ],
    fun p -> (if not (forks.Remove (int' p "id")) then fail "drop: no fork %d" (int' p "id")); obj []

    "render", "Write the live screen as a PNG (shifter base, resolution and palette).",
    [ "path", "string", true, "output .png" ],
    fun p -> let w, h = Render.png (need ()).Cpu.MMU (str p "path") in obj [ "width", jint (int64 w); "height", jint (int64 h) ]

    "kbd", "Queue raw IKBD bytes (make/break scancodes, packets).", [ "bytes", "addr[]", true, "hex bytes" ],
    fun p -> (need ()).Cpu.MMU.EnqueueIkbd [| for b in addrList p "bytes" -> byte b |]; obj []

    "mouse", "Mouse: action 'move' with dx/dy, or 'down'/'up' with button 'l'/'r'.",
    [ "action", "string", true, "move, down or up"; "dx", "int", false, "move x"; "dy", "int", false, "move y"; "button", "string", false, "l or r" ],
    fun p ->
        let mmu = (need ()).Cpu.MMU
        match str p "action" with
        | "move" -> mmu.MoveMouse (optInt p "dx" 0) (optInt p "dy" 0)
        | "down" | "up" as ud -> mmu.EnqueueMouseButton ((str p "button").StartsWith "l") (ud = "down")
        | a -> fail "mouse: action %s" a
        obj []

    "disk", "Swap drive A's image (null ejects).", [ "path", "string|null", true, "a .st, or null" ],
    fun p ->
        let mmu = (need ()).Cpu.MMU
        if not (p.ContainsKey "path") then fail "disk: 'path' is required (or null)"
        mmu.LoadDiskA (if isNull p.["path"] then None else Some (File.ReadAllBytes (str p "path")))
        obj [] ]

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
