#if INTERACTIVE
#load "Extensions.fs"
#load "MMU.fs"
#load "Instructions.fs"
#load "68k.fs"
open Atari
#else
namespace Atari
#endif

open System
open Bits
open Instructions

///Plain snapshot of every CPU-visible register - a struct, so comparing/copying it is a handful
///of int compares, not an allocation. Exists solely for the loop detector below.
[<Struct>]
type MachineState =
    { PC: int; CCR: int16; USP: int; SSP: int
      D0: int; D1: int; D2: int; D3: int; D4: int; D5: int; D6: int; D7: int
      A0: int; A1: int; A2: int; A3: int; A4: int; A5: int; A6: int; A7: int }
    static member Of (c: Cpu) =
        { PC = c.PC; CCR = c.CCR; USP = c.USP; SSP = c.SSP
          D0 = c.D0; D1 = c.D1; D2 = c.D2; D3 = c.D3; D4 = c.D4; D5 = c.D5; D6 = c.D6; D7 = c.D7
          A0 = c.A0; A1 = c.A1; A2 = c.A2; A3 = c.A3; A4 = c.A4; A5 = c.A5; A6 = c.A6; A7 = c.A7 }
    ///Explicit, PC-first comparison rather than relying on F#'s generated structural equality -
    ///short-circuits on the field most likely to differ, and this stays on the fast/unboxed path
    ///for certain regardless of how the compiler happens to implement `=` for the record.
    member a.SameAs (b: MachineState) =
        a.PC = b.PC && a.A7 = b.A7 && a.CCR = b.CCR && a.USP = b.USP && a.SSP = b.SSP
        && a.D0 = b.D0 && a.D1 = b.D1 && a.D2 = b.D2 && a.D3 = b.D3
        && a.D4 = b.D4 && a.D5 = b.D5 && a.D6 = b.D6 && a.D7 = b.D7
        && a.A0 = b.A0 && a.A1 = b.A1 && a.A2 = b.A2 && a.A3 = b.A3
        && a.A4 = b.A4 && a.A5 = b.A5 && a.A6 = b.A6

[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath: string, ?diskAPath: string, ?monitor: string) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mmu = MMU(rom)
    do
        //Optional real floppy image for drive A (see MMU.LoadDiskA) - mirrors romPath's own
        //"load bytes from a path supplied by the caller" shape exactly.
        match diskAPath with
        | Some p when not (String.IsNullOrEmpty p) -> mmu.LoadDiskA (Some (IO.File.ReadAllBytes p))
        | _ -> ()
        //Monitor type for MFP GPIP bit 7 (see MMU.SetMonitor). Anything other than "mono"
        //(case-insensitive) is treated as colour, which is also the default when unset.
        match monitor with
        | Some m when m.Trim().ToLowerInvariant() = "mono" -> mmu.SetMonitor false
        | _ -> mmu.SetMonitor true
    let mutable cpu = Cpu.Create(mmu)

    //Loop detection: Cpu.Step() is a pure function of (Cpu, MMU state) - no other mutable state
    //exists anywhere in the interpreter (every `mutable` in 68k.fs is a local inside a CCR/EA
    //helper, not instance state; Instructions.fs/Extensions.fs hold none at all). So if the full
    //CPU state matches an earlier snapshot AND the MMU provably mutated nothing since that
    //snapshot was taken (MMU.Mutations unchanged), execution is PROVABLY stuck in an infinite
    //loop - not a heuristic guess from "this exact state has now recurred N times", which is what
    //this used to be: a `sprintf`-formatted string key in a `Dictionary<string,int>` that lived
    //(and grew) for the entire run, with a `loopThreshold` constant that had to be reactively
    //raised (8 -> 750) whenever a new peripheral stub changed how many times a legitimate poll
    //revisits the same state before making real progress. That old design also folded the
    //top-of-stack long into its key to distinguish a shared subroutine reached from two different
    //call sites (same registers, different return address) - under the mutation-counter design
    //that's subsumed for free: writing a different return address is itself a real mutation, so
    //the two calls are never compared against each other in the first place, and the old need to
    //require "several repeats before concluding stuck" (to filter out that kind of coincidental,
    //not-actually-stuck match) goes away with it - a match now IS a proof, first time it happens.
    //
    //Implementation is Brent's cycle-detection algorithm: keep one saved "anchor" state and
    //compare the current state against it every step. If MMU.Mutations hasn't moved since the
    //anchor was taken and the state matches, that's the proof. If Mutations *has* moved, some
    //real change happened somewhere since the anchor (RAM, a peripheral register, anything
    //backing it), so the epoch restarts with a fresh anchor. O(1) space and O(1) time per step
    //(one uint64 compare, then at most 19 int compares, usually far fewer thanks to PC-first
    //short-circuiting in SameAs) - versus the old design's per-step string format + dictionary
    //probe and its unbounded (one entry per distinct state ever visited across the whole run)
    //memory growth.
    let mutable loopAnchor = Unchecked.defaultof<MachineState>
    let mutable loopAnchorMutations = UInt64.MaxValue //sentinel: forces a fresh epoch on step 1
    let mutable loopPower = 1
    let mutable loopLambda = 0
    //Blind spot in the pure-state proof: Step()'s own scheduled interrupts (VBL, Timer C) are an
    //external input not captured in (Cpu, MMU) state. TOS's `vsync` ($fc0726) spins reading
    //`frclock` until the VBL ISR bumps it - a pure, memory-read-only cycle that recurs in a few
    //steps and looks "provably stuck" even though the VBL will break it within one frame. Track
    //the last step at which an interrupt was actually taken; only declare a loop once a whole
    //frame has passed with none (i.e. interrupts have genuinely stopped - an IPL-masked lock -
    //not just "we haven't reached the next VBL boundary yet").
    let mutable loopLastAckCount = 0UL
    let mutable loopLastAckStep = 0UL

    // --- Emulated time --------------------------------------------------------
    //
    // There is still no per-instruction cycle counting here (every 68000 opcode
    // costs a different number of clocks and none of that is tracked). What this
    // block does instead is derive *every* periodic event from one constant, so
    // their rates stay consistent with each other and roughly real-time, rather
    // than three unrelated magic numbers drifting apart.
    //
    // The unit is "one emulator step == one instruction". Measured against real
    // Hatari on this same ROM (tools/hatari_trace.py --trace cpu_disasm, boot to
    // 120 VBLs): ~12,000 instructions execute between consecutive VBLs, i.e. per
    // ~50 Hz PAL video frame. That is the anchor.
    //
    //   - VBL (autovector level 4, vector 28): once per frame, 50 Hz.
    //   - MFP Timer C (channel 5, level 6, vector $45): the 200 Hz system tick,
    //     exactly 4x the frame rate. This is what advances etv_timer and the
    //     GEMDOS/BIOS software clock, and the AES double-click timeout - keeping
    //     it a fixed 4:1 against the VBL is what makes a stationary click
    //     complete and keeps the TOS clock from drifting against wall time.
    //   - The live window (Video.fs) renders one host frame per emulated frame
    //     and decodes the framebuffer exactly on the VBL boundary (see below).
    //
    // 12,000 is an estimate, not a cycle-accurate figure - within ~2x is enough
    // for "the clock ticks at roughly the right rate and the sub-rates agree".
    let instructionsPerFrame = 12000UL
    /// Timer C is 4x the VBL rate; the 4:1 ratio is the invariant, not the absolute period.
    let timerCPeriod = instructionsPerFrame / 4UL
    let mutable stepCount = 0UL

    ///Headless keyboard/mouse test hook (ATARI_KEY_INPUT / ATARI_KEY_DELAY env vars, set up in
    ///main). Raw IKBD serial bytes - make/break scancodes, 3-byte mouse packets - dropped into
    ///the ACIA receive FIFO. The first burst must land past the point where TOS has master-reset
    ///and configured the ACIA (~2.5M steps for a cold boot to the desktop) or the bytes get
    ///flushed. Independent of any window - the REPL `kbd` command does the same interactively.
    ///
    ///Scheduled IKBD bursts, each (absolute step at which to enqueue it, the raw bytes). Groups
    ///come from `;`-separated sections of ATARI_KEY_INPUT and fire `ATARI_KEY_DELAY` steps apart,
    ///so a scripted interaction can move the pointer, let the desktop react, then click - a single
    ///burst would be drained by the ISR in one go and the ROM would only ever see the final state.
    ///Empty (the default) injects nothing.
    let mutable keyInjectGroups : (uint64 * byte[]) list = []

    ///Pexec / basepage hook (gated on ATARI_TRACE_GEMDOS, like the GEMDOS_CALL trace it extends).
    ///When a `trap #1` with function $4B (Pexec) is about to execute, we stash the mode, the
    ///filename, and the address execution will return to; once the CPU is back there we read D0 as
    ///the candidate basepage pointer and, if it looks like a real basepage, dump its
    ///TEXT/DATA/BSS layout (so a later trace PC in that program maps back to a file offset) and
    ///append it to `<ATARI_TRACE_EVENTS>.basepages.json` when that log is being written.
    let traceGemdos = Diag.traceGemdos
    let basepageSidecar =
        match Environment.GetEnvironmentVariable "ATARI_TRACE_EVENTS" with
        | null | "" -> None
        | p -> Some (p + ".basepages.json")
    //A stack, not a single slot: TOS's mode-4/6 Pexec ("just go") never returns to its caller, so
    //a single pending slot would be pinned forever and block detection of every later Pexec -
    //including a mode-0 load launched by the running shell (e.g. \AUTO\*.PRG). Entries that never
    //return (mode 4/6) simply sit at the bottom; the ones we care about (load modes) are LIFO.
    let mutable pexecStack : (int * int * string) list = []  // (returnPC, mode, filename)
    let mutable basepagesWritten = 0
    //Set once we've dumped the basepage for the load-and-go Pexec currently on top of the stack,
    //keyed by its return PC, so the per-step $602C sample doesn't re-dump it every instruction.
    let mutable basepageCapturedFor = -1

    let readCString (addr: int) =
        if addr <= 0 then ""
        else
            let sb = Text.StringBuilder()
            let mutable a = uint32 addr
            let mutable go = sb.Length < 128
            while go do
                let b = mmu.ReadByte a
                if b = 0uy || sb.Length >= 128 then go <- false
                else
                    sb.Append(if b >= 0x20uy && b < 0x7fuy then char b else '?') |> ignore
                    a <- a + 1u
            sb.ToString()

    ///Reads the 8 standard basepage longwords at `bp`. Returns None unless they are internally
    ///consistent (lowtpa < hitpa, text base inside the TPA) - so a stale/garbage D0 on a
    ///non-load Pexec mode doesn't produce a bogus record.
    let readBasepage (bp: int) =
        if bp < 0x700 || (bp &&& 1) <> 0 then None
        else
            let rl off = mmu.ReadLong (uint32 (bp + off))
            let lowtpa, hitpa = rl 0x00, rl 0x04
            let tbase, tlen = rl 0x08, rl 0x0C
            let dbase, dlen = rl 0x10, rl 0x14
            let bbase, blen = rl 0x18, rl 0x1C
            if lowtpa > 0 && lowtpa < hitpa && tbase >= lowtpa && tbase < hitpa
               && tlen >= 0 && dlen >= 0 && blen >= 0 && tlen < 0x400000 then
                Some (lowtpa, hitpa, tbase, tlen, dbase, dlen, bbase, blen)
            else None

    ///Emits the basepage record (stderr + JSON sidecar) for a loaded program. `step` is the
    ///emulated-time stamp; `bp` is the basepage pointer.
    let dumpBasepage (step: uint64) (mode: int) (fname: string) (bp: int) =
        match readBasepage bp with
        | Some (lowtpa, hitpa, tbase, tlen, dbase, dlen, bbase, blen) ->
            eprintfn "GEMDOS Pexec basepage=$%08x tpa=$%08x..$%08x text=$%08x+$%x data=$%08x+$%x bss=$%08x+$%x (\"%s\")"
                bp lowtpa hitpa tbase tlen dbase dlen bbase blen fname
            match basepageSidecar with
            | Some path ->
                let sep = if basepagesWritten = 0 then "[\n" else ",\n"
                let json =
                    sprintf "%s  {\"step\":%d,\"mode\":%d,\"file\":\"%s\",\"basepage\":%d,\"lowtpa\":%d,\"hitpa\":%d,\"tbase\":%d,\"tlen\":%d,\"dbase\":%d,\"dlen\":%d,\"bbase\":%d,\"blen\":%d}"
                        sep step mode (fname.Replace("\\", "\\\\").Replace("\"", "\\\"")) bp lowtpa hitpa tbase tlen dbase dlen bbase blen
                IO.File.AppendAllText(path, json)
                basepagesWritten <- basepagesWritten + 1
            | None -> ()
            true
        | None -> false

    ///Resets the loop detector's epoch. Must be called after anything that changes CPU/MMU state
    ///without going through Step() - currently Reset() and Preview's post-rollback restore -
    ///otherwise the saved anchor describes a state from before/outside the real run, and a
    ///genuinely-progressing later step could spuriously "match" it.
    let resetLoopDetector() =
        loopAnchorMutations <- UInt64.MaxValue

    member x.Reset() =
        cpu <- cpu.Reset()
        stepCount <- 0UL
        resetLoopDetector()

    ///Flush the structured trace outputs on shutdown: close the JSON array in the basepage
    ///sidecar (it is written incrementally with AppendAllText) and the flow-event BinaryWriter.
    member x.CloseTraces() =
        if basepagesWritten > 0 then
            match basepageSidecar with
            | Some path -> IO.File.AppendAllText(path, "\n]\n")
            | None -> ()
            basepagesWritten <- 0
        TraceEvents.close()

    ///See `keyInjectGroups`. Arms the headless key-injection hook: group i fires at
    ///`firstStep + i*gap`.
    member x.QueueKeyInput (groups: byte[] list) (firstStep: uint64) (gap: uint64) =
        keyInjectGroups <- groups |> List.mapi (fun i g -> (firstStep + uint64 i * gap, g))
    member x.Rom =
        rom

    ///Total instructions executed since the last Reset()/LoadState() - the emulated-time base.
    ///The live window uses this to align framebuffer capture to the VBL boundary.
    member x.StepCount = stepCount
    ///See the emulated-time block above: instructions per ~50 Hz video frame.
    member x.InstructionsPerFrame = int instructionsPerFrame

    member x.Step() =
        stepCount <- stepCount + 1UL
        if stepCount % instructionsPerFrame = 0UL then
            mmu.RaiseInterrupt 4 28
        if stepCount % timerCPeriod = 0UL then
            mmu.RaiseTimerC()
        match keyInjectGroups with
        | (at, bytes) :: rest when stepCount >= at ->
            keyInjectGroups <- rest
            mmu.EnqueueIkbd bytes
            eprintfn "ATARI_KEY_INPUT: injected %d IKBD byte(s) at step %d (%d group(s) left)" bytes.Length stepCount rest.Length
        | _ -> ()
        let state = MachineState.Of cpu
        let currentMutations = mmu.Mutations
        if mmu.InterruptAcks <> loopLastAckCount then
            loopLastAckCount <- mmu.InterruptAcks
            loopLastAckStep <- stepCount
        if currentMutations <> loopAnchorMutations then
            loopAnchor <- state
            loopAnchorMutations <- currentMutations
            loopPower <- 1
            loopLambda <- 0
        elif state.SameAs loopAnchor && stepCount - loopLastAckStep >= instructionsPerFrame then
            eprintfn "LOOP DETECTED at PC=$%08x (not a missing instruction) - this exact CPU state has recurred with a provably unchanged MMU (no RAM/peripheral state has moved since the last snapshot) and no interrupt has been taken for a full frame, so execution is stuck in an infinite loop; further stepping is pointless until the MMU/peripheral behavior it depends on changes." cpu.PC
            eprintfn "%A" cpu
            failwithf "Loop detected at PC=$%08x" cpu.PC
        else
            loopLambda <- loopLambda + 1
            if loopLambda >= loopPower then
                loopAnchor <- state
                loopPower <- min (loopPower * 2) 0x40000000
                loopLambda <- 0
        //Every instruction's own printfn (in 68k.fs) prints its disassembly text and a trailing
        //newline; prefixing the PC here with printf (no newline) - one call site, instead of
        //touching every printfn in 68k.fs - makes a captured trace directly greppable/correlatable
        //against ROM addresses, instead of needing a separate disassembly pass just to figure out
        //which address a given trace line came from (a real time sink in past debugging sessions).
        printf "$%06x: " cpu.PC
        //Structured flow-event trace (ATARI_TRACE_EVENTS) - one emission point, here, rather than
        //the 221 printfn sites. Capture the pre-step PC/opcode and the interrupt-ack count, then
        //classify the transition once cpu.Step() has produced the new PC. See Atari.TraceEvents.
        let preEventsPc = cpu.PC
        let preEventsOpcode = if TraceEvents.enabled then int (mmu.ReadWord (uint32 cpu.PC)) else 0
        let preEventsAcks = mmu.InterruptAcks
        //Pexec detection: a `trap #1` ($4E41) whose GEMDOS function word on the caller stack is
        //$4B. Record where it will return to and the args; the basepage is read back on return.
        if traceGemdos && int (mmu.ReadWord (uint32 cpu.PC)) = 0x4E41
           && (int (mmu.ReadWord (uint32 cpu.A7)) &&& 0xFFFF) = 0x004B then
            let mode = int (mmu.ReadWord (uint32 (cpu.A7 + 2)))
            let fname = readCString (mmu.ReadLong (uint32 (cpu.A7 + 4)))
            pexecStack <- (cpu.PC + 2, mode, fname) :: pexecStack
            eprintfn "GEMDOS Pexec mode=%d file=\"%s\" pc=$%08x" mode fname cpu.PC
        try
            cpu <- cpu.Step()
            if TraceEvents.enabled then
                TraceEvents.record stepCount preEventsPc preEventsOpcode cpu.PC (mmu.InterruptAcks <> preEventsAcks)
            match pexecStack with
            | (retpc, mode, fname) :: rest when cpu.PC = retpc ->
                pexecStack <- rest
                eprintfn "GEMDOS Pexec mode=%d returned d0=$%08x" mode cpu.D0
                //Mode 3 (load, don't run) returns the basepage in D0. Modes 0/1 (load and run)
                //return the *child's exit code* - their basepage was captured below while the
                //child was live.
                if mode = 3 || mode = 4 || mode = 6 then dumpBasepage stepCount mode fname cpu.D0 |> ignore
                if basepageCapturedFor = retpc then basepageCapturedFor <- -1
            | (retpc, mode, fname) :: _ when (mode = 0 || mode = 1) && basepageCapturedFor <> retpc ->
                //Load-and-run: the child is executing now. GEMDOS keeps the running process's
                //basepage pointer at act_pd ($602C - see [[atari-st-emulator-next-instructions]]);
                //sample it until it resolves to a valid basepage, then stop.
                let actpd = mmu.ReadLong 0x602Cu
                if dumpBasepage stepCount mode fname actpd then basepageCapturedFor <- retpc
            | _ -> ()
        with e ->
            //Diagnostics for implementing the next instruction: the opcode word, its common
            //sub-fields (most 68k formats split a word into these positions, though which fields
            //are meaningful depends on the instruction family - cross-check against the relevant
            //active pattern in Instructions.fs), and the raw words following it (covers immediate
            //values/displacements without a separate ROM read).
            let pc = uint32 cpu.PC
            let opcode = cpu.MMU.ReadWord pc
            let nextWords = [ for i in 1..5 -> cpu.MMU.ReadWord (pc + uint32 (i * 2)) ]
            eprintfn "Step failed at PC=$%08x" cpu.PC
            eprintfn "  opcode  $%04x  %s" opcode (int16 opcode).toBits
            eprintfn "  fields  [15-12]=%x [11-9]=%x [8-6]=%x [5-3]=%x [2-0]=%x   size[13-12]=%x"
                ((opcode >>> 12) &&& 0xf) ((opcode >>> 9) &&& 0x7) ((opcode >>> 6) &&& 0x7)
                ((opcode >>> 3) &&& 0x7) (opcode &&& 0x7) ((opcode >>> 12) &&& 0x3)
            eprintfn "  next words (PC+2, PC+4, ...): %s" (nextWords |> List.map (sprintf "$%04x") |> String.concat " ")
            eprintfn "  %s" e.Message
            eprintfn "%A" cpu
            reraise()
        //printfn "%A" x

    ///Runs up to n further steps, then unconditionally rolls back all CPU registers and memory
    ///to exactly what they were before the call - even if a step failed (the diagnostics are
    ///still printed, same as a normal Step() failure, but execution isn't left stuck at the
    ///failing instruction). Useful from the REPL to look ahead without disturbing the real run.
    member x.Preview(n: int) =
        let savedCpu = cpu
        let savedRam = mmu.SnapshotRam()
        Diag.result "--- preview: up to %d step(s), state will be restored afterward ---" n
        (try
            for _ in 1 .. n do x.Step()
         with e ->
            Diag.result "--- preview stopped early: %s ---" e.Message)
        cpu <- savedCpu
        mmu.RestoreRam savedRam
        resetLoopDetector() //the anchor may describe a state from the just-reverted speculative branch
        Diag.result "--- preview done, state restored to PC=$%08x ---" cpu.PC

    ///Serializes full CPU + MMU state (registers, RAM, video/YM2149/MFP register banks, Timer B
    ///scalars) to a binary file, so a later run can jump straight to this point instead of
    ///replaying every step from address 0 - see LoadState. Self-describing (array lengths are
    ///written alongside the data) so it isn't brittle against MMU's array sizes changing later.
    member x.SaveState(path: string) =
        use fs = IO.File.Create(path)
        use w = new IO.BinaryWriter(fs)
        w.Write("A68S".ToCharArray())
        w.Write(8uy) //format version - v2 adds the 5 FDC state bytes after TbdrReadCount, v3 adds the 3 DMA address counter bytes after those, v4 adds the MMU memory-config byte after those, v5 adds SSP after USP, v6 adds stepCount after MemConfig, v7 adds the keyboard ACIA control byte + IKBD RX FIFO after stepCount, v8 makes the Ym2149 array the 16-register PSG file and adds the PSG select + read-data bytes at the end
        for v in [| cpu.D0; cpu.D1; cpu.D2; cpu.D3; cpu.D4; cpu.D5; cpu.D6; cpu.D7
                    cpu.A0; cpu.A1; cpu.A2; cpu.A3; cpu.A4; cpu.A5; cpu.A6; cpu.A7
                    cpu.USP; cpu.SSP; cpu.PC |] do w.Write(v: int)
        w.Write(cpu.CCR)
        let snap = mmu.SnapshotRam()
        let writeArr (a: byte[]) =
            w.Write(a.Length)
            w.Write(a)
        writeArr snap.Ram
        writeArr snap.VideoDisplayRegisters
        writeArr snap.Ym2149
        writeArr snap.MfpRegisters
        w.Write(snap.Tbcr)
        w.Write(snap.Tbdr)
        w.Write(snap.TbdrReload)
        w.Write(snap.TbdrReadCount)
        w.Write(snap.FdcSelectedReg)
        w.Write(snap.FdcStatus)
        w.Write(snap.FdcTrack)
        w.Write(snap.FdcSector)
        w.Write(snap.FdcData)
        w.Write(snap.DmaAddrHigh)
        w.Write(snap.DmaAddrMid)
        w.Write(snap.DmaAddrLow)
        w.Write(snap.MemConfig)
        w.Write(stepCount)
        w.Write(snap.KbdAciaControl)
        writeArr snap.IkbdRxFifo
        w.Write(snap.PsgSelectedReg)
        w.Write(snap.PsgReadData)
        Diag.result "--- state saved to %s: PC=$%08x ---" path cpu.PC

    ///Inverse of SaveState - replaces the current CPU/MMU state wholesale (does NOT call Reset()
    ///first; the caller decides whether to Reset() or LoadState(), never both). Resets the loop
    ///detector's epoch afterward for the same reason Preview does: the saved anchor would
    ///otherwise describe a state from outside this run.
    member x.LoadState(path: string) =
        use fs = IO.File.OpenRead(path)
        use r = new IO.BinaryReader(fs)
        let magic = String(r.ReadChars(4))
        if magic <> "A68S" then failwithf "Not a valid state file (bad magic): %s" path
        let version = r.ReadByte()
        //v1-v4 snapshots predate SSP (the supervisor-stack shadow WithSR introduced) - one fewer
        //int in the register block, and PC shifts down by one slot to match.
        let regCount = if version >= 5uy then 19 else 18
        let regs = [| for _ in 1..regCount -> r.ReadInt32() |]
        let ccr = r.ReadInt16()
        cpu <-
            { cpu with
                D0=regs.[0]; D1=regs.[1]; D2=regs.[2]; D3=regs.[3]; D4=regs.[4]; D5=regs.[5]; D6=regs.[6]; D7=regs.[7]
                A0=regs.[8]; A1=regs.[9]; A2=regs.[10]; A3=regs.[11]; A4=regs.[12]; A5=regs.[13]; A6=regs.[14]; A7=regs.[15]
                USP=regs.[16]
                SSP=(if version >= 5uy then regs.[17] else 0)
                PC=regs.[regCount-1]; CCR=ccr }
        let readArr() =
            let len = r.ReadInt32()
            r.ReadBytes(len)
        let ramArr = readArr()
        let vidArr = readArr()
        let ymArr = readArr()
        let mfpArr = readArr()
        let tbcr = r.ReadByte()
        let tbdr = r.ReadByte()
        let tbdrReload = r.ReadByte()
        let tbdrReadCount = r.ReadUInt32()
        //v1 snapshots (format version 1) predate FDC emulation - default to "idle, no command
        //issued yet", matching the always-0 status those snapshots were actually captured with.
        let fdcSelectedReg, fdcStatus, fdcTrack, fdcSector, fdcData =
            if version >= 2uy then r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte()
            else 0uy, 0uy, 0uy, 0uy, 0uy
        //v1/v2 snapshots predate the DMA address counter registers - default to 0, matching the
        //chip's own power-on reset state (and what those snapshots were actually captured with,
        //since nothing could set them to anything else before this fix existed).
        let dmaAddrHigh, dmaAddrMid, dmaAddrLow =
            if version >= 3uy then r.ReadByte(), r.ReadByte(), r.ReadByte()
            else 0uy, 0uy, 0uy
        //v1-v3 snapshots predate the MMU memory-config register - default to 0, its real
        //cold-reset value (see MMU.fs's memConfigByte comment), matching what those snapshots were
        //actually captured with since nothing could set it to anything else before this fix existed.
        let memConfig = if version >= 4uy then r.ReadByte() else 0uy
        //v1-v5 snapshots predate stepCount being persisted - default to 0, matching the bug this
        //field's addition fixes (a resumed run's VBL-injection phase, `stepCount % instructionsPerFrame`,
        //restarting from 0 instead of continuing from the point the snapshot was taken at, which is
        //exactly the resume/cold-boot step-count divergence this fix targets). Snapshots taken
        //before this fix can't recover their true step count and stay subject to the old bug.
        stepCount <- if version >= 6uy then r.ReadUInt64() else 0UL
        //v1-v6 snapshots predate the keyboard ACIA receive path - default to "control register 0,
        //empty FIFO", matching what those snapshots were captured with (no RX path existed).
        let kbdAciaControl, ikbdRxFifo =
            if version >= 7uy then r.ReadByte(), readArr()
            else 0uy, [||]
        //v1-v7 snapshots stored the PSG as a raw 4-byte port array, not the 16-register file - a
        //restored v7 blob won't reproduce PSG state (they are scratchpad-local and never carried
        //between sessions anyway). Default the select/read-data bytes to the cold-reset values.
        let psgSelectedReg, psgReadData =
            if version >= 8uy then r.ReadByte(), r.ReadByte()
            else 0uy, 0xFFuy
        mmu.RestoreRam
            { Ram = ramArr; VideoDisplayRegisters = vidArr; Ym2149 = ymArr; MfpRegisters = mfpArr
              PsgSelectedReg = psgSelectedReg; PsgReadData = psgReadData
              Tbcr = tbcr; Tbdr = tbdr; TbdrReload = tbdrReload; TbdrReadCount = tbdrReadCount
              FdcSelectedReg = fdcSelectedReg; FdcStatus = fdcStatus; FdcTrack = fdcTrack
              FdcSector = fdcSector; FdcData = fdcData
              DmaAddrHigh = dmaAddrHigh; DmaAddrMid = dmaAddrMid; DmaAddrLow = dmaAddrLow
              MemConfig = memConfig
              KbdAciaControl = kbdAciaControl; IkbdRxFifo = ikbdRxFifo }
        resetLoopDetector()
        Diag.result "--- state loaded from %s: PC=$%08x ---" path cpu.PC

    member x.Debug =
       sprintf """
-------------
CPU Registers
%A
-------------""" cpu

    member x.Cpu = cpu

    member x.DumpMemory (addr: uint32) (length: int) =
        String.concat " " [ for i in 0 .. length - 1 -> sprintf "%02x" (cpu.MMU.ReadByte (addr + uint32 i)) ]

    ///Steps until PC reaches `target` or `maxSteps` real steps have run, whichever first - lets
    ///you get straight to a known address of interest (e.g. "right before the instruction I'm
    ///investigating") without hand-counting how many steps that takes, or editing the REPL's
    ///hardcoded entry step count and rebuilding just to inspect one spot (the previous workflow).
    ///maxSteps is a safety cap, not a target - if PC never reaches `target` this stops with a
    ///clear message rather than spinning indefinitely.
    member x.Until (target: uint32) (maxSteps: int) =
        let mutable stepsRun = 0
        while stepsRun < maxSteps && uint32 cpu.PC <> target do
            x.Step()
            stepsRun <- stepsRun + 1
        if uint32 cpu.PC = target then
            Diag.result "--- reached PC=$%08x after %d step(s) ---" cpu.PC stepsRun
        else
            Diag.result "--- gave up after %d step(s), PC=$%08x never reached (still at $%08x) ---" stepsRun target cpu.PC

#if INTERACTIVE
let st = AtartSt("TOS100UK.IMG")
st.Reset()
for _ in 1..100 do
    st.Step()
#else
///Table-driven CPU regression harness. Runs the SingleStepTests/ProcessorTests 68000 vectors
///(github.com/SingleStepTests/ProcessorTests, `680x0/68000/v1/*.json.gz` - one file per opcode,
///~8000 randomised cases each carrying an initial machine state and the expected final
///registers / SR / memory) straight against `Cpu.Step`. This is the regression net the project
///has never had: the silent-for-many-passes shift bug (`LSR.L`/`ROR.L` smearing bit 31 down via
///F#'s arithmetic `>>>`, only found on the 39th pass) would have failed thousands of `LSR.l` /
///`ROR.l` cases the instant it was written.
///
///Usage: `dotnet exec M68000.dll selftest <dir-or-file> [name-substring]`. `<dir>` is a folder of
///`*.json` / `*.json.gz` vector files; the optional substring filters by file name (e.g. `lsr`,
///`shift` won't match - use `lsr`, `ror`). Fetch the vectors with `tools/fetch_680x0_tests.py`.
///
///Deliberate scope limits - a case that trips one is SKIPPED (counted, not failed):
/// - Only the low 1 MB of address space is backed here, as flat identity-mapped RAM (`memConfig`
///   = $05). A case whose PC or listed RAM addresses fall outside [$8, $100000) is skipped. The
///   overwhelming majority of register/immediate/near-stack cases still run.
///Known imperfections that surface as real FAILs (gaps to close, not harness bugs):
/// - No prefetch queue: `pc` is checked as "address of the next instruction", correct for this
///   interpreter, but a few instruction classes still differ by the 68000's real prefetch amount.
/// - Exception entry uses the project's simplified 6-byte frame, so TRAP / CHK / privilege /
///   address-error cases mismatch on the stacked frame.
/// - Where the 68000 officially leaves a flag undefined, the vectors encode the real chip's
///   actual behaviour and this core may pick a different (still-legal) value.
module SelfTest =
    open System
    open System.IO
    open System.IO.Compression
    open System.Text.Json

    /// One decoded processor-state object (the `initial` or `final` half of a case).
    type private St =
        { D: int[]; A: int[]; Usp: int; Ssp: int; Sr: int; Pc: int
          Prefetch: int[]; Ram: (uint32 * byte)[] }

    /// Register values are unsigned 32-bit in the JSON; keep the bit pattern as a native int.
    let private u32 (e: JsonElement) = int (uint32 (e.GetInt64()))

    let private parseSt (o: JsonElement) : St =
        { D = [| for i in 0..7 -> u32 (o.GetProperty("d" + string i)) |]
          A = [| for i in 0..6 -> u32 (o.GetProperty("a" + string i)) |]
          Usp = u32 (o.GetProperty("usp"))
          Ssp = u32 (o.GetProperty("ssp"))
          Sr = o.GetProperty("sr").GetInt32() &&& 0xFFFF
          Pc = u32 (o.GetProperty("pc"))
          Prefetch = [| for p in o.GetProperty("prefetch").EnumerateArray() -> p.GetInt32() |]
          Ram = [| for pair in o.GetProperty("ram").EnumerateArray() ->
                     uint32 (pair.[0].GetInt64()), byte (pair.[1].GetInt32()) |] }

    /// Shared zero "ROM": each case builds a fresh MMU so its RAM starts clean, but the ROM image
    /// is immutable and never written, so one copy is safe to share across every case.
    let private zeroRom : byte[] = Array.zeroCreate 0x40000

    /// How a failing case failed - so triage can tell the real wrong-answers apart from the two
    /// large known-structural classes at a glance:
    ///  - Unimplemented: Cpu.Step threw (opcode / EA-mode not decoded yet - ROM-driven scope).
    ///  - ExceptionFrame: the vectors expect this instruction to fault and push a frame; we push a
    ///    simplified 6-byte frame (not the real 14-byte group-0 one) or don't fault at all. One fix
    ///    (a real exception frame) clears the whole class - see the memory notes.
    ///  - WrongAnswer: a genuine flag / register / memory divergence. THESE are the ones to chase.
    type private FailKind = Unimplemented | ExceptionFrame | WrongAnswer
    type private Outcome = Pass | Skip | Fail of FailKind * string

    let private runCase (ini: St) (fin: St) : Outcome =
        let outOfRange (a: uint32) = a < 8u || a >= 0x100000u
        let refAddrs = Array.append (ini.Ram |> Array.map fst) (fin.Ram |> Array.map fst)
        if ini.Pc % 2 <> 0 || outOfRange (uint32 ini.Pc) || Array.exists outOfRange refAddrs then Skip
        else
        let mmu = MMU(zeroRom)
        mmu.WriteByte 0xFF8001u 0x05uy   // bank0 = bank1 = 512 KB -> identity RAM map over the low 1 MB
        mmu.WriteWord (uint32 ini.Pc) (int16 ini.Prefetch.[0])
        mmu.WriteWord (uint32 ini.Pc + 2u) (int16 ini.Prefetch.[1])
        for (a, v) in ini.Ram do mmu.WriteByte a v
        let supervisor = ini.Sr &&& 0x2000 <> 0
        let cpu0 =
            { Cpu.Create(mmu) with
                D0 = ini.D.[0]; D1 = ini.D.[1]; D2 = ini.D.[2]; D3 = ini.D.[3]
                D4 = ini.D.[4]; D5 = ini.D.[5]; D6 = ini.D.[6]; D7 = ini.D.[7]
                A0 = ini.A.[0]; A1 = ini.A.[1]; A2 = ini.A.[2]; A3 = ini.A.[3]
                A4 = ini.A.[4]; A5 = ini.A.[5]; A6 = ini.A.[6]
                A7 = (if supervisor then ini.Ssp else ini.Usp)
                USP = ini.Usp; SSP = ini.Ssp
                PC = ini.Pc; CCR = int16 ini.Sr }
        match (try Choice1Of2 (cpu0.Step()) with e -> Choice2Of2 e) with
        | Choice2Of2 e ->
            // A raised exception here is the emulator refusing to decode this opcode/EA-mode
            // combination (ROM-driven scope - many modes simply aren't implemented yet), not a
            // wrong-answer bug. Report it distinctly so the two are easy to tell apart.
            let firstLine = e.Message.Split('\n').[0]
            Fail (Unimplemented, sprintf "Cpu.Step raised (unimplemented?): %s" (firstLine.Substring(0, min 100 firstLine.Length)))
        | Choice1Of2 cpu ->
        let diffs = ResizeArray<string>()
        let cmp label (act: int) (exp: int) =
            if act <> exp then diffs.Add(sprintf "%s exp=%08x act=%08x" label exp act)
        let dn = [| cpu.D0; cpu.D1; cpu.D2; cpu.D3; cpu.D4; cpu.D5; cpu.D6; cpu.D7 |]
        let an = [| cpu.A0; cpu.A1; cpu.A2; cpu.A3; cpu.A4; cpu.A5; cpu.A6 |]
        for i in 0..7 do cmp ("d" + string i) dn.[i] fin.D.[i]
        for i in 0..6 do cmp ("a" + string i) an.[i] fin.A.[i]
        cmp "pc" cpu.PC fin.Pc
        // The emulator keeps the live stack in A7 and shadows the *other* mode's pointer in
        // USP/SSP; recover both real pointers from the post-step S bit to compare against the case.
        cmp "usp" (if cpu.S then cpu.USP else cpu.A7) fin.Usp
        cmp "ssp" (if cpu.S then cpu.A7 else cpu.SSP) fin.Ssp
        let actSr = int cpu.CCR &&& 0xFFFF
        if actSr <> fin.Sr then diffs.Add(sprintf "sr exp=%04x act=%04x" fin.Sr actSr)
        for (a, v) in fin.Ram do
            let got = mmu.ReadByte a
            if got <> v then diffs.Add(sprintf "ram[%06x] exp=%02x act=%02x" a v got)
        if diffs.Count = 0 then Pass
        else
            // The vectors expect an exception if the final state entered/stayed supervisor AND the
            // supervisor stack moved DOWN (a frame was pushed). Our simplified 6-byte frame vs the
            // real 14-byte group-0 frame makes every legitimate address/bus-error case diverge on
            // ssp + stacked bytes; bucket those separately from real wrong-answers.
            let expectedException = (fin.Sr &&& 0x2000 <> 0) && fin.Ssp < ini.Ssp
            Fail ((if expectedException then ExceptionFrame else WrongAnswer), String.concat ", " diffs)

    let private loadDoc (path: string) : JsonDocument =
        if path.EndsWith(".gz") then
            use fs = File.OpenRead path
            use gz = new GZipStream(fs, CompressionMode.Decompress)
            use ms = new MemoryStream()
            gz.CopyTo ms
            ms.Position <- 0L
            JsonDocument.Parse ms
        else
            use fs = File.OpenRead path
            JsonDocument.Parse fs

    let private baseName (path: string) =
        Path.GetFileNameWithoutExtension(Path.GetFileNameWithoutExtension path)  // strips .json.gz

    /// Per-file tally: pass / skip / and fails split three ways (see FailKind).
    type Tally = { Pass: int; Skip: int; Wrong: int; Frame: int; Unimpl: int }
    let private zeroTally = { Pass = 0; Skip = 0; Wrong = 0; Frame = 0; Unimpl = 0 }
    let private totalFail t = t.Wrong + t.Frame + t.Unimpl

    let private runFile (path: string) (maxReport: int) : Tally =
        use doc = loadDoc path
        let mutable t = zeroTally
        // Collect failing samples, then print them WrongAnswer-first - those are the actionable ones,
        // and the 5-line cap otherwise fills up with the (large, known) frame / unimplemented classes.
        let samples = ResizeArray<int * string * string>()   // rank, name, msg  (rank: 0=wrong 1=frame 2=unimpl)
        for caseEl in doc.RootElement.EnumerateArray() do
            match runCase (parseSt (caseEl.GetProperty("initial"))) (parseSt (caseEl.GetProperty("final"))) with
            | Pass -> t <- { t with Pass = t.Pass + 1 }
            | Skip -> t <- { t with Skip = t.Skip + 1 }
            | Fail (kind, msg) ->
                let rank =
                    match kind with
                    | WrongAnswer   -> t <- { t with Wrong  = t.Wrong  + 1 }; 0
                    | ExceptionFrame -> t <- { t with Frame  = t.Frame  + 1 }; 1
                    | Unimplemented -> t <- { t with Unimpl = t.Unimpl + 1 }; 2
                samples.Add(rank, caseEl.GetProperty("name").GetString(), msg)
        for (_, name, msg) in samples |> Seq.sortBy (fun (r, _, _) -> r) |> Seq.truncate maxReport do
            Diag.result "    FAIL  %s :: %s" name msg
        Diag.result "%-14s  %5d pass  %5d fail (%5d wrong %5d frame %5d unimpl)  %5d skip"
            (baseName path) t.Pass (totalFail t) t.Wrong t.Frame t.Unimpl t.Skip
        t

    /// `pathArg` = a directory of `*.json` / `*.json.gz` vector files, or a single such file.
    /// `filter` (may be "") keeps only files whose name contains it, case-insensitively.
    let run (pathArg: string) (filter: string) (maxReport: int) : int =
        let keep (name: string) =
            filter = "" || name.ToLowerInvariant().Contains(filter.ToLowerInvariant())
        let files =
            if Directory.Exists pathArg then
                Directory.GetFiles pathArg
                |> Array.filter (fun f -> (f.EndsWith(".json") || f.EndsWith(".json.gz")) && keep (Path.GetFileName f))
                |> Array.sort
            elif File.Exists pathArg then [| pathArg |]
            else [||]
        if files.Length = 0 then
            Diag.result "selftest: no matching .json / .json.gz vector files under %s" pathArg
            2
        else
            let mutable g = zeroTally
            let perFile = ResizeArray<string * Tally>()
            for file in files do
                let t = runFile file maxReport
                perFile.Add(baseName file, t)
                g <- { Pass = g.Pass + t.Pass; Skip = g.Skip + t.Skip
                       Wrong = g.Wrong + t.Wrong; Frame = g.Frame + t.Frame; Unimpl = g.Unimpl + t.Unimpl }
            Diag.result "----"
            Diag.result "TOTAL  %d pass  %d fail  %d skip  across %d file(s)" g.Pass (totalFail g) g.Skip files.Length
            Diag.result "       fail breakdown: %d wrong-answer  %d exception-frame  %d unimplemented"
                g.Wrong g.Frame g.Unimpl
            // The actionable digest: files with genuine wrong-answers, worst first. An empty list
            // here means every remaining failure is a known structural class (frame / unimplemented).
            let wrongFiles = perFile |> Seq.filter (fun (_, t) -> t.Wrong > 0) |> Seq.sortByDescending (fun (_, t) -> t.Wrong) |> Seq.toList
            if not wrongFiles.IsEmpty then
                Diag.result "       wrong-answer files (chase these): %s"
                    (wrongFiles |> List.map (fun (n, t) -> sprintf "%s(%d)" n t.Wrong) |> String.concat " ")
            if totalFail g > 0 then 1 else 0

module Main =

    ///Interactive REPL command loop - factored out so both the plain entry (`repl`, Reset()+N
    ///steps) and the snapshot-resuming entry (`resume <path> repl`, LoadState() instead) can share
    ///it instead of duplicating the command dispatch.
    let runRepl (st: AtartSt) =
        let rec loop() =
            let input = Console.ReadLine()
            let parts =
                if isNull input then [||]
                else input.Split(' ') |> Array.filter (fun s -> s <> "")
            match parts with
            | [| "help" |] | [| "h" |] ->
                Diag.result "s [n] = step (n times, default 1), p <n> = preview n steps then roll back (state unchanged), u <hexaddr> [maxSteps] = run until PC reaches address (default cap 200000), r = print registers, m <hexaddr> <len> = dump memory bytes, w <hexaddr> <hexvalue> = write a longword, snap <path> = save current state to a snapshot file, watch <hexaddr> [len] = print every write into [addr,addr+len) to stderr (default len 1), unwatch = clear it, q = quit, help = this"
                loop()
            | [| "step" |] | [| "s" |] ->
                st.Step()
                loop()
            | [| "step"; n |] | [| "s"; n |] ->
                for _ in 1 .. int n do st.Step()
                loop()
            | [| "peek"; n |] | [| "p"; n |] ->
                st.Preview (int n)
                loop()
            | [| "until"; addr |] | [| "u"; addr |] ->
                st.Until (Convert.ToUInt32(addr, 16)) 200000
                loop()
            | [| "until"; addr; maxSteps |] | [| "u"; addr; maxSteps |] ->
                st.Until (Convert.ToUInt32(addr, 16)) (int maxSteps)
                loop()
            | [| "registers" |] | [| "r" |] ->
                Diag.result "%s" st.Debug
                loop()
            | [| "m"; addr; len |] ->
                Diag.result "%s" (st.DumpMemory (Convert.ToUInt32(addr, 16)) (int len))
                loop()
            | [| "w"; addr; value |] ->
                //Direct memory-write for debugging (e.g. patching a resumed snapshot's system
                //variables to test a hypothesis without needing a fresh cold boot to produce them).
                //Writes a longword via the same MMU path real 68k code would use.
                st.Cpu.MMU.WriteLong (Convert.ToUInt32(addr, 16)) (Convert.ToInt32(value, 16))
                loop()
            | [| "snap"; path |] ->
                st.SaveState path
                Diag.result "Snapshot written to %s at PC=$%08x" path st.Cpu.PC
                loop()
            | [| "watch"; addr |] ->
                let a = Convert.ToUInt32(addr, 16)
                st.Cpu.MMU.SetWatch a a
                Diag.result "Watching $%08x (stderr, survives ATARI_NOTRACE)" a
                loop()
            | [| "watch"; addr; len |] ->
                let a = Convert.ToUInt32(addr, 16)
                st.Cpu.MMU.SetWatch a (a + uint32 (int len - 1))
                Diag.result "Watching [$%08x,$%08x] (stderr, survives ATARI_NOTRACE)" a (a + uint32 (int len - 1))
                loop()
            | [| "unwatch" |] ->
                st.Cpu.MMU.ClearWatch()
                loop()
            | _ when parts.Length >= 2 && (parts.[0] = "kbd" || parts.[0] = "key") ->
                //Enqueue raw IKBD serial bytes into the keyboard ACIA FIFO (and raise the MFP
                //channel-6 interrupt) - e.g. `kbd 1f 9f` = press+release the 'A' key ($1f make,
                //$9f break), `kbd fa 05 00` = a mouse-move-right packet. See MMU.EnqueueIkbd.
                let bytes = parts.[1..] |> Array.map (fun s -> Convert.ToByte(s, 16))
                st.Cpu.MMU.EnqueueIkbd bytes
                Diag.result "enqueued %d IKBD byte(s): %s" bytes.Length (bytes |> Array.map (sprintf "%02x") |> String.concat " ")
                loop()
            | [| "quit" |] | [| "q" |] ->
                ()
            | _ ->
                ()
        loop()

    [<EntryPoint>]
    let main argv =
        //Capture the real stdout before the ATARI_NOTRACE redirect below can replace it with a
        //null sink - result output (REPL replies, verify/selftest verdicts) prints through
        //Diag.result so ATARI_NOTRACE only silences the per-instruction trace. See Diag.
        Diag.captureResultOut()
        //Flush/close the structured flow-event log (ATARI_TRACE_EVENTS) on any process exit,
        //including the reraise path when an unimplemented instruction aborts the run.
        AppDomain.CurrentDomain.ProcessExit.Add(fun _ -> TraceEvents.close())
        //Every executed instruction calls printfn (221 call sites in 68k.fs) to build the
        //PC-tagged trace this project's debugging workflow depends on - see
        //atari-st-emulator-efficiency-tooling. That's the right default, but it means tracing
        //cost is paid on every step even for bulk snapshot/resume runs where nobody reads the
        //output. ATARI_NOTRACE=1 redirects Console.Out to a null sink so printfn's formatting
        //and I/O are skipped entirely, without touching any of the 221 call sites.
        if not (isNull (Environment.GetEnvironmentVariable "ATARI_NOTRACE")) then
            Console.SetOut(IO.TextWriter.Null)
        //ATARI_ROM_PATH lets a caller point this at a different ROM dump (e.g. for an A/B
        //comparison against a different TOS revision) without touching the default TOS100UK.IMG.
        let romPath =
            match Environment.GetEnvironmentVariable "ATARI_ROM_PATH" with
            | null | "" -> "TOS100UK.IMG"
            | p -> p
        //ATARI_DISK_A mounts a real disk image in drive A (see MMU.LoadDiskA) - unset (the
        //default) preserves the existing diskless-boot behavior exactly.
        let diskAPath =
            match Environment.GetEnvironmentVariable "ATARI_DISK_A" with
            | null | "" -> None
            | p -> Some p
        //ATARI_MONITOR=colour|mono (default colour) - drives MFP GPIP bit 7, which the boot ROM
        //at $fc0366 uses to pick colour rez vs forced high-res mono. See MMU.SetMonitor.
        let monitor =
            match Environment.GetEnvironmentVariable "ATARI_MONITOR" with
            | null | "" -> None
            | m -> Some m
        let st = AtartSt(romPath, ?diskAPath = diskAPath, ?monitor = monitor)
        AppDomain.CurrentDomain.ProcessExit.Add(fun _ -> st.CloseTraces())
        //ATARI_KEY_INPUT: space/comma-separated hex bytes (raw IKBD serial - make/break
        //scancodes, mouse packets). A ';' starts a new burst: bursts fire ATARI_KEY_DELAY steps
        //apart (first one at ATARI_KEY_DELAY, default 2,500,000 - past the boot-time ACIA master
        //reset), so a scripted move / react / click sequence works. See AtartSt.QueueKeyInput.
        match Environment.GetEnvironmentVariable "ATARI_KEY_INPUT" with
        | null | "" -> ()
        | s ->
            let groups =
                s.Split(';')
                |> Array.map (fun g ->
                    g.Split([| ' '; ','; '\t' |], StringSplitOptions.RemoveEmptyEntries)
                    |> Array.map (fun t -> Convert.ToByte(t, 16)))
                |> Array.filter (fun g -> g.Length > 0)
                |> Array.toList
            let gap =
                match Environment.GetEnvironmentVariable "ATARI_KEY_DELAY" with
                | null | "" -> 2500000UL
                | d -> uint64 d
            st.QueueKeyInput groups gap gap
        match argv with
        | [| "window" |] ->
            //Opt-in live SDL2 window (see Video.fs): cold-boots then runs the emulator with a
            //~50Hz render loop, feeding real host keyboard/mouse in as IKBD packets. F12 or the
            //window close button exits. Everything else here stays headless by default.
            st.Reset()
            Video.run st.Step (fun () -> st.StepCount) st.InstructionsPerFrame st.Cpu.MMU
            0
        | [| "window"; "resume"; path |] ->
            //Same window, but starting from a snapshot instead of a cold boot.
            st.LoadState path
            Video.run st.Step (fun () -> st.StepCount) st.InstructionsPerFrame st.Cpu.MMU
            0
        | [| "selftest"; pathArg |] ->
            //680x0 instruction-level regression vectors against Cpu.Step - see the SelfTest module.
            SelfTest.run pathArg "" 5
        | [| "selftest"; pathArg; filter |] ->
            SelfTest.run pathArg filter 5
        | [| stepsArg |] ->
            //Non-interactive mode, e.g. `dotnet run --no-build -- 20000`: run N steps (or until
            //an unimplemented instruction fails - Step() prints diagnostics and reraises) then
            //exit. No stdin required, so this can be driven from a plain shell command with no
            //piping and no risk of hanging on Console.ReadLine if the run completes cleanly.
            st.Reset()
            let steps = int stepsArg
            for _ in 1 .. steps do st.Step()
            0
        | [| stepsArg; "checkpoint" |] ->
            //Runs N steps (or until failure), then saves the resulting register/PC/CCR dump as a
            //golden snapshot for regression checking (see "verify" below), instead of relying on
            //manually eyeballing two dumps to confirm an instruction fix didn't regress a
            //previous one. checkpoint.txt is local/untracked working data, like TOS100UK.IMG -
            //not meant to be committed, since it encodes both this ROM and whatever opcode
            //coverage exists right now.
            st.Reset()
            let steps = int stepsArg
            (try for _ in 1 .. steps do st.Step() with _ -> ())
            IO.File.WriteAllText("checkpoint.txt", st.Debug)
            Diag.result "Checkpoint written to checkpoint.txt at step count %d (PC=$%08x)" steps st.Cpu.PC
            0
        | [| stepsArg; "verify" |] ->
            //Runs N steps (or until failure), then diffs the resulting dump against
            //checkpoint.txt. Exit code reflects the result (0 = match), so this is scriptable
            //rather than needing a human to compare two register dumps by eye.
            st.Reset()
            let steps = int stepsArg
            (try for _ in 1 .. steps do st.Step() with _ -> ())
            if not (IO.File.Exists "checkpoint.txt") then
                eprintfn "No checkpoint.txt found - run with 'checkpoint' instead of 'verify' first"
                1
            else
                // Normalise line endings: st.Debug's "%A cpu" template picks up whatever the source
                // file used (LF vs CRLF), and checkpoint.txt can have been written by a build with
                // the other convention - a spurious mismatch on otherwise-identical register dumps.
                let norm (s: string) = s.Replace("\r\n", "\n")
                let expected = IO.File.ReadAllText "checkpoint.txt"
                let actual = st.Debug
                if norm actual = norm expected then
                    Diag.result "VERIFY PASS at step count %d (PC=$%08x)" steps st.Cpu.PC
                    0
                else
                    Diag.result "VERIFY FAIL at step count %d" steps
                    Diag.result "--- expected (checkpoint.txt) ---%s" expected
                    Diag.result "--- actual ---%s" actual
                    1
        | [| stepsArg; "snapshot"; path |] ->
            //Runs N steps from address 0 (or until failure - in which case nothing is saved, same
            //as a normal failing run), then saves full CPU+MMU state to `path`. Exists because
            //replaying millions of already-correct steps from scratch on every single instruction
            //fix is the dominant cost of this project's ROM-driven debugging loop once boot
            //progresses past a few million steps (measured: the last several fixes in the twelfth
            //pass each replayed ~4.4M steps just to reach a wall a handful of instructions further
            //out) - see 'resume' below for the other half of this workflow.
            st.Reset()
            let steps = int stepsArg
            for _ in 1 .. steps do st.Step()
            st.SaveState(path)
            0
        | [| stepsArg; "resume"; path |] ->
            //Loads state saved by 'snapshot' and runs N further steps (or until failure) from
            //there, instead of from address 0 - the counterpart to 'snapshot' above.
            st.LoadState(path)
            let steps = int stepsArg
            for _ in 1 .. steps do st.Step()
            0
        | [| "resume"; path; "repl" |] ->
            //Same as the plain REPL entry below, but starting from a saved snapshot instead of
            //Reset()+N steps - for interactively poking around near a resume point without paying
            //the full replay cost first.
            st.LoadState(path)
            runRepl st
            0
        | [| "teartest"; snapPath; framesArg |] ->
            //Headless reproduction of the live window's mouse-cursor path, for the cursor-tearing
            //investigation (see atari-st-emulator-next-instructions). Mirrors Video.run's frame
            //loop exactly - front-load one coalesced IKBD mouse packet at frame start, run to the
            //next VBL boundary, decode the framebuffer - but drives a synthetic per-frame pointer
            //drift instead of host input and writes each decoded frame as a 24-bit BMP. The white
            //trailing block, if present, shows up in the frame sequence; no live window needed.
            st.LoadState snapPath
            let frames = int framesArg
            let ipf = uint64 st.InstructionsPerFrame
            // TEARTEST_PHASE = signed step offset from the VBL boundary at which to decode the
            // framebuffer (0 = on the boundary, exactly as Video.run does today). Sweeping this
            // finds a tear-free capture phase.
            let phase =
                match Environment.GetEnvironmentVariable "TEARTEST_PHASE" with
                | null | "" -> 0L
                | s -> int64 s
            let mmu = st.Cpu.MMU
            let W, H = 640, 400
            let pixels = Array.zeroCreate<byte> (W * H * 4) // ARGB8888 = B,G,R,A in memory
            let outDir = "teartest_out"
            IO.Directory.CreateDirectory outDir |> ignore
            let writeBmp (path: string) =
                use fs = IO.File.Create path
                use w = new IO.BinaryWriter(fs)
                let rowBytes = W * 3 // 1920, already a multiple of 4 - no padding
                let imgSize = rowBytes * H
                w.Write("BM".ToCharArray())
                w.Write(14 + 40 + imgSize)
                w.Write(0); w.Write(54)
                w.Write(40); w.Write(W); w.Write(H)
                w.Write(1s); w.Write(24s); w.Write(0); w.Write(imgSize)
                w.Write(2835); w.Write(2835); w.Write(0); w.Write(0)
                for y in H - 1 .. -1 .. 0 do // BMP rows are bottom-up
                    for x in 0 .. W - 1 do
                        let o = (y * W + x) * 4
                        w.Write(pixels.[o]); w.Write(pixels.[o + 1]); w.Write(pixels.[o + 2])
            for f in 0 .. frames - 1 do
                // A hand-waggle: drift right for 20 frames, left for 20, repeat - a fresh packet
                // every frame so TOS keeps redrawing the cursor (a lone packet barely moves it).
                let dx = if (f / 20) % 2 = 0 then 6y else -6y
                let boundary = (st.StepCount / ipf + 1UL) * ipf
                let target = uint64 (max 1L (int64 boundary + phase))
                mmu.EnqueueIkbd [| 0xF8uy; byte dx; 2uy |] // front-loaded, exactly as Video.run does
                while st.StepCount < target do st.Step()
                Video.decodeFramebuffer mmu pixels
                writeBmp (IO.Path.Combine(outDir, sprintf "frame_%03d.bmp" f))
                let rw a = mmu.ReadWord a &&& 0xFFFF
                let mcsAddr = mmu.ReadLong 0x27F2u
                eprintfn "frame %3d: newx=%d newy=%d mcs.len=%d mcs.flags=$%02x mcs.addr=$%06x"
                    f (rw 0x27E2u) (rw 0x27E4u) (rw 0x27F0u) (mmu.ReadByte 0x27F6u) mcsAddr
            Diag.result "teartest: wrote %d frames to %s/" frames outDir
            0
        | args ->
            //Interactive REPL. Entry step count defaults to 20000 (`dotnet run --no-build`) but
            //can be overridden with `dotnet run --no-build -- <n> repl` - previously this required
            //hand-editing the hardcoded `20000` below and rebuilding just to inspect state at a
            //specific point, then editing it back afterward (an easy step to forget, and a real
            //time sink across past debugging sessions).
            st.Reset()
            let entrySteps =
                match args with
                | [| stepsArg; "repl" |] -> int stepsArg
                | _ -> 20000
            (try for _ in 1..entrySteps do st.Step() with _ -> ())
            runRepl st
            0
#endif