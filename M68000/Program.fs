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

[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath: string) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mmu = MMU(rom)
    let mutable cpu = Cpu.Create(mmu)

    //Loop detection: the (PC, all registers, CCR) tuple after each step is deterministic given
    //the current MMU state, so seeing the exact same tuple twice means execution is provably
    //stuck forever from there (e.g. polling an MMU address whose value never changes) - not
    //merely a slow bounded loop, which would show a changing register (like a loop counter) on
    //every pass. Registers alone are NOT enough, though: a shared subroutine called from two
    //different call sites with identical register inputs reaches the same PC with the same
    //registers on both calls, but returns to a different place each time (the return address
    //sitting in memory at the stack pointer, not in any register) - so the top-of-stack long is
    //folded into the key too, to tell those apart. Even with that, this only inspects a slice of
    //memory near A7, not the full MMU state, so it can in principle miss a loop whose exit
    //depends on other memory content; that's an acceptable gap for a diagnostic tool used to
    //steer instruction implementation, not for emulator correctness.
    //A state repeating exactly once is common and often innocent (see stateKey's comment on why:
    //a coincidental match on the compared slice of state while something else, outside that
    //slice, is still genuinely progressing - confirmed empirically: a one-off "repeat" here
    //turned out to just be a subroutine re-entered with matching visible state, which then
    //diverged and made real progress on its very next step). A truly stuck loop, by contrast,
    //revisits the same state indefinitely, so requiring several repeats before concluding "stuck
    //forever" filters out the coincidental case almost for free while still catching real loops
    //within a handful of extra iterations.
    let loopThreshold = 8
    let seenStateCounts = Collections.Generic.Dictionary<string, int>()
    let stateKey (c: Cpu) =
        //A7 can transiently point outside the emulated RAM array (e.g. the raw reset-vector SSP,
        //before the ROM's own early boot code replaces it with something sane), which makes
        //ReadLong throw. That's a real gap in MMU's bounds checking, not something to paper over
        //there - but this diagnostic only needs "some distinguishing value," so falling back to 0
        //on a bad read is fine here specifically.
        let topOfStack = try c.MMU.ReadLong (uint32 c.A7) with _ -> 0
        sprintf "%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%08x|%04x|%08x"
            c.PC c.D0 c.D1 c.D2 c.D3 c.D4 c.D5 c.D6 c.D7
            c.A0 c.A1 c.A2 c.A3 c.A4 c.A5 c.A6 c.A7 c.CCR topOfStack

    member x.Reset() =
        cpu <- cpu.Reset()
    member x.Rom =
        rom

    member x.Step() =
        let key = stateKey cpu
        let visits = (match seenStateCounts.TryGetValue key with true, n -> n | false, _ -> 0) + 1
        seenStateCounts.[key] <- visits
        if visits = loopThreshold then
            eprintfn "LOOP DETECTED at PC=$%08x (not a missing instruction) - this exact register/CCR/top-of-stack state has now been visited %d times, so execution is stuck and can never leave this loop; further stepping is pointless until the MMU/peripheral behavior it depends on changes." cpu.PC visits
            eprintfn "%A" cpu
            failwithf "Loop detected at PC=$%08x" cpu.PC
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
        printfn "--- preview done, state restored to PC=$%08x ---" cpu.PC

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
    [<EntryPoint>]
    let main argv =
        let st = AtartSt("TOS100UK.IMG")
        st.Reset()
        match argv with
        | [| stepsArg |] ->
            //Non-interactive mode, e.g. `dotnet run --no-build -- 20000`: run N steps (or until
            //an unimplemented instruction fails - Step() prints diagnostics and reraises) then
            //exit. No stdin required, so this can be driven from a plain shell command with no
            //piping and no risk of hanging on Console.ReadLine if the run completes cleanly.
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
            let steps = int stepsArg
            (try for _ in 1 .. steps do st.Step() with _ -> ())
            IO.File.WriteAllText("checkpoint.txt", st.Debug)
            printfn "Checkpoint written to checkpoint.txt at step count %d (PC=$%08x)" steps st.Cpu.PC
            0
        | [| stepsArg; "verify" |] ->
            //Runs N steps (or until failure), then diffs the resulting dump against
            //checkpoint.txt. Exit code reflects the result (0 = match), so this is scriptable
            //rather than needing a human to compare two register dumps by eye.
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
        | args ->
            //Interactive REPL. Entry step count defaults to 20000 (`dotnet run --no-build`) but
            //can be overridden with `dotnet run --no-build -- <n> repl` - previously this required
            //hand-editing the hardcoded `20000` below and rebuilding just to inspect state at a
            //specific point, then editing it back afterward (an easy step to forget, and a real
            //time sink across past debugging sessions).
            let entrySteps =
                match args with
                | [| stepsArg; "repl" |] -> int stepsArg
                | _ -> 20000
            (try for _ in 1..entrySteps do st.Step() with _ -> ())
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
            0
#endif