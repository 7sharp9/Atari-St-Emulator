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
    { PC: int; CCR: int16; USP: int
      D0: int; D1: int; D2: int; D3: int; D4: int; D5: int; D6: int; D7: int
      A0: int; A1: int; A2: int; A3: int; A4: int; A5: int; A6: int; A7: int }
    static member Of (c: Cpu) =
        { PC = c.PC; CCR = c.CCR; USP = c.USP
          D0 = c.D0; D1 = c.D1; D2 = c.D2; D3 = c.D3; D4 = c.D4; D5 = c.D5; D6 = c.D6; D7 = c.D7
          A0 = c.A0; A1 = c.A1; A2 = c.A2; A3 = c.A3; A4 = c.A4; A5 = c.A5; A6 = c.A6; A7 = c.A7 }
    ///Explicit, PC-first comparison rather than relying on F#'s generated structural equality -
    ///short-circuits on the field most likely to differ, and this stays on the fast/unboxed path
    ///for certain regardless of how the compiler happens to implement `=` for the record.
    member a.SameAs (b: MachineState) =
        a.PC = b.PC && a.A7 = b.A7 && a.CCR = b.CCR && a.USP = b.USP
        && a.D0 = b.D0 && a.D1 = b.D1 && a.D2 = b.D2 && a.D3 = b.D3
        && a.D4 = b.D4 && a.D5 = b.D5 && a.D6 = b.D6 && a.D7 = b.D7
        && a.A0 = b.A0 && a.A1 = b.A1 && a.A2 = b.A2 && a.A3 = b.A3
        && a.A4 = b.A4 && a.A5 = b.A5 && a.A6 = b.A6

[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath: string) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mmu = MMU(rom)
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

    ///Resets the loop detector's epoch. Must be called after anything that changes CPU/MMU state
    ///without going through Step() - currently Reset() and Preview's post-rollback restore -
    ///otherwise the saved anchor describes a state from before/outside the real run, and a
    ///genuinely-progressing later step could spuriously "match" it.
    let resetLoopDetector() =
        loopAnchorMutations <- UInt64.MaxValue

    member x.Reset() =
        cpu <- cpu.Reset()
        resetLoopDetector()
    member x.Rom =
        rom

    member x.Step() =
        let state = MachineState.Of cpu
        let currentMutations = mmu.Mutations
        if currentMutations <> loopAnchorMutations then
            loopAnchor <- state
            loopAnchorMutations <- currentMutations
            loopPower <- 1
            loopLambda <- 0
        elif state.SameAs loopAnchor then
            eprintfn "LOOP DETECTED at PC=$%08x (not a missing instruction) - this exact CPU state has recurred with a provably unchanged MMU (no RAM/peripheral state has moved since the last snapshot), so execution is stuck in an infinite loop; further stepping is pointless until the MMU/peripheral behavior it depends on changes." cpu.PC
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
        try
            cpu <- cpu.Step()
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
        printfn "--- preview: up to %d step(s), state will be restored afterward ---" n
        (try
            for _ in 1 .. n do x.Step()
         with e ->
            printfn "--- preview stopped early: %s ---" e.Message)
        cpu <- savedCpu
        mmu.RestoreRam savedRam
        resetLoopDetector() //the anchor may describe a state from the just-reverted speculative branch
        printfn "--- preview done, state restored to PC=$%08x ---" cpu.PC

    ///Serializes full CPU + MMU state (registers, RAM, video/YM2149/MFP register banks, Timer B
    ///scalars) to a binary file, so a later run can jump straight to this point instead of
    ///replaying every step from address 0 - see LoadState. Self-describing (array lengths are
    ///written alongside the data) so it isn't brittle against MMU's array sizes changing later.
    member x.SaveState(path: string) =
        use fs = IO.File.Create(path)
        use w = new IO.BinaryWriter(fs)
        w.Write("A68S".ToCharArray())
        w.Write(1uy) //format version
        for v in [| cpu.D0; cpu.D1; cpu.D2; cpu.D3; cpu.D4; cpu.D5; cpu.D6; cpu.D7
                    cpu.A0; cpu.A1; cpu.A2; cpu.A3; cpu.A4; cpu.A5; cpu.A6; cpu.A7
                    cpu.USP; cpu.PC |] do w.Write(v: int)
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
        printfn "--- state saved to %s: PC=$%08x ---" path cpu.PC

    ///Inverse of SaveState - replaces the current CPU/MMU state wholesale (does NOT call Reset()
    ///first; the caller decides whether to Reset() or LoadState(), never both). Resets the loop
    ///detector's epoch afterward for the same reason Preview does: the saved anchor would
    ///otherwise describe a state from outside this run.
    member x.LoadState(path: string) =
        use fs = IO.File.OpenRead(path)
        use r = new IO.BinaryReader(fs)
        let magic = String(r.ReadChars(4))
        if magic <> "A68S" then failwithf "Not a valid state file (bad magic): %s" path
        r.ReadByte() |> ignore //format version, only one exists so far
        let regs = [| for _ in 1..18 -> r.ReadInt32() |]
        let ccr = r.ReadInt16()
        cpu <-
            { cpu with
                D0=regs.[0]; D1=regs.[1]; D2=regs.[2]; D3=regs.[3]; D4=regs.[4]; D5=regs.[5]; D6=regs.[6]; D7=regs.[7]
                A0=regs.[8]; A1=regs.[9]; A2=regs.[10]; A3=regs.[11]; A4=regs.[12]; A5=regs.[13]; A6=regs.[14]; A7=regs.[15]
                USP=regs.[16]; PC=regs.[17]; CCR=ccr }
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
        mmu.RestoreRam
            { Ram = ramArr; VideoDisplayRegisters = vidArr; Ym2149 = ymArr; MfpRegisters = mfpArr
              Tbcr = tbcr; Tbdr = tbdr; TbdrReload = tbdrReload; TbdrReadCount = tbdrReadCount }
        resetLoopDetector()
        printfn "--- state loaded from %s: PC=$%08x ---" path cpu.PC

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
            printfn "--- reached PC=$%08x after %d step(s) ---" cpu.PC stepsRun
        else
            printfn "--- gave up after %d step(s), PC=$%08x never reached (still at $%08x) ---" stepsRun target cpu.PC

#if INTERACTIVE
let st = AtartSt("TOS100UK.IMG")
st.Reset()
for _ in 1..100 do
    st.Step()
#else
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
                printfn "s [n] = step (n times, default 1), p <n> = preview n steps then roll back (state unchanged), u <hexaddr> [maxSteps] = run until PC reaches address (default cap 200000), r = print registers, m <hexaddr> <len> = dump memory bytes, q = quit, help = this"
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
                printfn "%s" st.Debug
                loop()
            | [| "m"; addr; len |] ->
                printfn "%s" (st.DumpMemory (Convert.ToUInt32(addr, 16)) (int len))
                loop()
            | [| "quit" |] | [| "q" |] ->
                ()
            | _ ->
                ()
        loop()

    [<EntryPoint>]
    let main argv =
        let st = AtartSt("TOS100UK.IMG")
        match argv with
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
            printfn "Checkpoint written to checkpoint.txt at step count %d (PC=$%08x)" steps st.Cpu.PC
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
                let expected = IO.File.ReadAllText "checkpoint.txt"
                let actual = st.Debug
                if actual = expected then
                    printfn "VERIFY PASS at step count %d (PC=$%08x)" steps st.Cpu.PC
                    0
                else
                    printfn "VERIFY FAIL at step count %d" steps
                    printfn "--- expected (checkpoint.txt) ---%s" expected
                    printfn "--- actual ---%s" actual
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