namespace Atari
open System
open Bits
open Instructions

type TraceMode =
    | No_Trace
    | Trace_On_Any_Instruction
    | Trace_On_Change_of_Flow
    | Undefined_Trace
        
type ActiveStack =
    | USP | ISP | MSP

module Diag =
    ///`ATARI_TRACE_GEMDOS=1` prints every GEMDOS trap#1 call's PC and function code to stderr
    ///(survives ATARI_NOTRACE, like `watch` - see [[atari-st-emulator-efficiency-tooling]]). Added
    ///after this exact print, added ad-hoc, was what cracked a real bug (TOS's own boot-supervisor
    ///restarting the whole Pexec/Pterm0 desktop-launch cycle every ~650,000 steps, something a
    ///per-instruction disasm trace alone was too noisy to spot) - kept as a permanent, opt-in tool
    ///instead of being thrown away, since "which GEMDOS calls happened, in what order, how often"
    ///is a question likely to come up again for any future GEMDOS-level investigation.
    let traceGemdos = not (isNull (Environment.GetEnvironmentVariable "ATARI_TRACE_GEMDOS"))

    ///Result output (REPL replies, `verify`/`selftest` verdicts, snapshot/until status lines) goes
    ///through `result` so it survives `ATARI_NOTRACE`. That env var redirects `Console.Out` to a
    ///null sink to skip the per-instruction trace's formatting cost - which also silenced the
    ///output you actually asked for, a recurring foot-gun (see [[atari-st-emulator-efficiency-tooling]]).
    ///`captureResultOut` is called once at the very top of `main`, before the redirect, so the
    ///captured writer is the real stdout regardless of when this module's initializer ran.
    let mutable private resultOut : IO.TextWriter = Console.Out
    let captureResultOut () = resultOut <- Console.Out
    let result fmt = Printf.kprintf resultOut.WriteLine fmt

///Structured, machine-readable execution trace for program analysis (control-flow reconstruction,
///basic blocks, call graphs, coverage) - a compact binary alternative to the 221 per-instruction
///`printfn` disassembly sites, which are meant for a human reading a text trace, not for tooling.
///
///`ATARI_TRACE_EVENTS=<path>` writes a binary record per flow-control instruction (or per
///instruction, with `ATARI_TRACE_EVENTS_ALL=1`). It writes straight to its own file via a
///`BinaryWriter`, so it is unaffected by `ATARI_NOTRACE` (which only redirects `Console.Out`).
///
///File layout (little-endian, matching `BinaryWriter` on x86/x64):
///  header: "A68E" (4 bytes) · version:u8 (=1) · recLen:u8 (=20) · reserved:u16 · startStep:u64
///  record x N: stepCount:u64 · pc:u32 · target:u32 · opcode:u16 · kind:u8 · flags:u8 (=0)
///`pc` is the executing instruction's address; `target` is the address actually executed next
///(post-step PC); `kind` classifies the flow effect (see the byte constants below).
///
///Post-processor: `tools/trace_cfg.py`.
module TraceEvents =
    // kind byte values - keep in sync with tools/trace_cfg.py
    let KSeq = 0uy             // linear fall-through (only emitted with ATARI_TRACE_EVENTS_ALL)
    let KBranchTaken = 1uy     // Bcc/DBcc taken, BRA, JMP, or an unclassified non-linear jump
    let KBranchNotTaken = 2uy  // Bcc/DBcc fell through to the next instruction
    let KCall = 3uy            // BSR / JSR
    let KRet = 4uy             // RTS / RTE / RTR
    let KTrap = 5uy            // TRAP #n, TRAPV (taken), Line-A, Line-F, ILLEGAL, CHK (taken), address/bus error
    let KInterrupt = 6uy       // a hardware interrupt was taken before this instruction ran

    let private path = Environment.GetEnvironmentVariable "ATARI_TRACE_EVENTS"
    let enabled = not (String.IsNullOrWhiteSpace path)
    let private logAll = not (isNull (Environment.GetEnvironmentVariable "ATARI_TRACE_EVENTS_ALL"))

    let mutable private writer : IO.BinaryWriter = null
    let mutable private sinceFlush = 0

    let private ensureOpen (startStep: uint64) =
        if isNull writer then
            let fs = IO.File.Create path
            writer <- new IO.BinaryWriter(fs)
            writer.Write("A68E".ToCharArray())
            writer.Write(1uy)
            writer.Write(20uy)
            writer.Write(0us)
            writer.Write(startStep)

    ///Classify an executed instruction purely from its opcode word and the PC transition. The
    ///bit patterns mirror the active extractors in Instructions.fs (BCC/DBcc/JSR/JMP/RTS/TRAP).
    ///`inRange` = the post-step PC advanced linearly by a plausible instruction length; anything
    ///non-linear that isn't a recognised branch opcode (address/bus error, a decode we don't model
    ///as flow) is reported as KBranchTaken so the post-processor still sees a block boundary.
    let classify (opcode: int) (pc: int) (newPc: int) (interruptTaken: bool) : byte =
        if interruptTaken then KInterrupt else
        let inRange = newPc >= pc && newPc <= pc + 16
        match (opcode >>> 12) &&& 0xF with
        | 0xA | 0xF -> KTrap
        | 0x6 ->
            let cond = (opcode >>> 8) &&& 0xF
            if cond = 1 then KCall                       // BSR
            elif cond = 0 then KBranchTaken              // BRA (unconditional)
            else
                let len = match opcode &&& 0xFF with 0x00 -> 4 | 0xFF -> 6 | _ -> 2
                if newPc = pc + len then KBranchNotTaken else KBranchTaken
        | 0x4 ->
            if opcode = 0x4E75 || opcode = 0x4E73 || opcode = 0x4E77 then KRet          // RTS / RTE / RTR
            elif (opcode &&& 0xFFC0) = 0x4E80 then KCall                                // JSR
            elif (opcode &&& 0xFFC0) = 0x4EC0 then KBranchTaken                         // JMP
            elif (opcode &&& 0xFFF0) = 0x4E40 then KTrap                                // TRAP #n
            elif opcode = 0x4E76 then (if inRange then KSeq else KTrap)                 // TRAPV
            elif opcode = 0x4AFC then KTrap                                             // ILLEGAL
            elif (opcode &&& 0xF1C0) = 0x4180 then (if inRange then KSeq else KTrap)    // CHK
            elif inRange then KSeq
            else KBranchTaken
        | 0x5 ->
            if (opcode &&& 0xF0F8) = 0x50C8 then                                        // DBcc
                if newPc = pc + 4 then KBranchNotTaken else KBranchTaken
            elif inRange then KSeq
            else KBranchTaken
        | _ ->
            if inRange then KSeq else KBranchTaken

    ///Called once per executed instruction from AtartSt.Step(). No-op unless ATARI_TRACE_EVENTS is set.
    let record (stepCount: uint64) (pc: int) (opcode: int) (newPc: int) (interruptTaken: bool) =
        if enabled then
            ensureOpen stepCount
            let kind = classify opcode pc newPc interruptTaken
            if logAll || kind <> KSeq then
                writer.Write(stepCount)
                writer.Write(uint32 pc)
                writer.Write(uint32 newPc)
                writer.Write(uint16 opcode)
                writer.Write(kind)
                writer.Write(0uy)
                sinceFlush <- sinceFlush + 1
                if sinceFlush >= 65536 then
                    writer.Flush()
                    sinceFlush <- 0

    let close () =
        if not (isNull writer) then
            writer.Flush()
            writer.Dispose()
            writer <- null

module CCR =
    let Subtract_IgnoringX currentCCR dest source =
        //unset all flag bits apart from x
        let mutable ccr = currentCCR &&& ~~~0xFs
        let result = dest - source
        if (result &&& 0x80000000) <> 0 then ccr <- ccr ||| 0x8s //N
        if result = 0 then ccr <- ccr ||| 0x4s //Z
        if ((dest^^^source) < 0 && (source^^^result) >= 0) then ccr <- ccr ||| 0x2s //V
        if ((result&&&source) < 0 || (~~~dest &&& (result ||| source)) < 0) then ccr <- ccr ||| 0x1s //C
        ccr

    let Subtract_IgnoringX_Word currentCCR (dest: int16) (source: int16) =
        //unset all flag bits apart from x
        let mutable ccr = currentCCR &&& ~~~0xFs
        let result = int16 (int dest - int source)
        let dm = dest < 0s
        let sm = source < 0s
        let rm = result < 0s
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0s then ccr <- ccr ||| 0x4s //Z
        if (dm <> sm) && (sm = rm) then ccr <- ccr ||| 0x2s //V
        if (sm && not dm) || (rm && not dm) || (sm && rm) then ccr <- ccr ||| 0x1s //C
        ccr

    let Subtract_IgnoringX_Byte currentCCR (dest: byte) (source: byte) =
        //unset all flag bits apart from x
        let mutable ccr = currentCCR &&& ~~~0xFs
        let result = byte (int dest - int source)
        let dm = dest &&& 0x80uy <> 0uy
        let sm = source &&& 0x80uy <> 0uy
        let rm = result &&& 0x80uy <> 0uy
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0uy then ccr <- ccr ||| 0x4s //Z
        if (dm <> sm) && (sm = rm) then ccr <- ccr ||| 0x2s //V
        if (sm && not dm) || (rm && not dm) || (sm && rm) then ccr <- ccr ||| 0x1s //C
        ccr

    // SUB / SUBI / SUBQ / NEG set X the same as C (the Subtract_IgnoringX_* helpers above are for
    // CMP / CMPA / CMPI / CMPM, which set NZVC but leave X alone). Same story as ADD vs CMP: fold
    // the just-computed C into X. NEGX has its own inline flag logic and does not route here.
    let private foldCintoX (ccr: int16) = if ccr &&& 0x1s <> 0s then ccr ||| 0x10s else ccr &&& ~~~0x10s
    let Subtract currentCCR dest source = foldCintoX (Subtract_IgnoringX currentCCR dest source)
    let Subtract_Word currentCCR (dest: int16) (source: int16) = foldCintoX (Subtract_IgnoringX_Word currentCCR dest source)
    let Subtract_Byte currentCCR (dest: byte) (source: byte) = foldCintoX (Subtract_IgnoringX_Byte currentCCR dest source)

    ///Calculate CCR
    let IgnoreX_ZeroV_And_ZeroC currentCCR (input:int16) =
        //TODO: Expand logic as more variations of flag ignorance is needed
        let mutable ccr = currentCCR &&& ~~~0xFs
        //set N,Z 
        if (input &&& 0x8000s) <> 0s then ccr <- ccr ||| 0x8s //N
        if input = 0s then ccr <- ccr ||| 0x4s //Z
        //clear V,C
        ccr <- ccr &&& ~~~0x2s //V
        ccr <- ccr &&& ~~~0x1s //C
        ccr

    ///Calculate CCR for a 32-bit result
    let IgnoreX_ZeroV_And_ZeroC_Long currentCCR (input:int) =
        let mutable ccr = currentCCR &&& ~~~0xFs
        //set N,Z
        if (input &&& 0x80000000) <> 0 then ccr <- ccr ||| 0x8s //N
        if input = 0 then ccr <- ccr ||| 0x4s //Z
        //clear V,C
        ccr <- ccr &&& ~~~0x2s //V
        ccr <- ccr &&& ~~~0x1s //C
        ccr

    // ADD / ADDI / ADDQ set X the same as C (unlike ADDA, which touches no flags, and CMP/CMPA,
    // which set NZVC but leave X - those use the Subtract_IgnoringX helpers). These were once named
    // Add_IgnoringX and left X untouched, which was wrong: the 680x0 vectors fail ~1 in 4 cases when
    // the incoming X differs from the computed C. Clear X with the rest of the low nibble, then set
    // it alongside C.
    let Add currentCCR (dest: int) (source: int) =
        let mutable ccr = currentCCR &&& ~~~0x1Fs
        let result = dest + source
        let dm = dest < 0
        let sm = source < 0
        let rm = result < 0
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0 then ccr <- ccr ||| 0x4s //Z
        if (dm && sm && not rm) || (not dm && not sm && rm) then ccr <- ccr ||| 0x2s //V
        if (dm && sm) || (not rm && sm) || (dm && not rm) then ccr <- ccr ||| 0x1s ||| 0x10s //C, X=C
        ccr

    let Add_Word currentCCR (dest: int16) (source: int16) =
        let mutable ccr = currentCCR &&& ~~~0x1Fs
        let result = int16 (int dest + int source)
        let dm = dest < 0s
        let sm = source < 0s
        let rm = result < 0s
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0s then ccr <- ccr ||| 0x4s //Z
        if (dm && sm && not rm) || (not dm && not sm && rm) then ccr <- ccr ||| 0x2s //V
        if (dm && sm) || (not rm && sm) || (dm && not rm) then ccr <- ccr ||| 0x1s ||| 0x10s //C, X=C
        ccr

    let Add_Byte currentCCR (dest: byte) (source: byte) =
        let mutable ccr = currentCCR &&& ~~~0x1Fs
        let result = byte (int dest + int source)
        let dm = dest &&& 0x80uy <> 0uy
        let sm = source &&& 0x80uy <> 0uy
        let rm = result &&& 0x80uy <> 0uy
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0uy then ccr <- ccr ||| 0x4s //Z
        if (dm && sm && not rm) || (not dm && not sm && rm) then ccr <- ccr ||| 0x2s //V
        if (dm && sm) || (not rm && sm) || (dm && not rm) then ccr <- ccr ||| 0x1s ||| 0x10s //C, X=C
        ccr

    ///Calculate CCR for a byte result
    let IgnoreX_ZeroV_And_ZeroC_Byte currentCCR (input: byte) =
        let mutable ccr = currentCCR &&& ~~~0xFs
        //set N,Z
        if (input &&& 0x80uy) <> 0uy then ccr <- ccr ||| 0x8s //N
        if input = 0uy then ccr <- ccr ||| 0x4s //Z
        //clear V,C
        ccr <- ccr &&& ~~~0x2s //V
        ccr <- ccr &&& ~~~0x1s //C
        ccr

    let SetZero currentCCR =
        currentCCR ||| 0x4s //Z

    let ClearZero ccr =
        ccr &&& ~~~0x4s //Z

///Size-code helpers shared by the extended-arith instructions (ADDX/SUBX; 00=byte, 01=word, 10=long).
module ExtendedArith =
    ///(operand mask, sign bit) for a two-bit size code. The long mask is -1 (all 32 bits).
    let sizeInfo (size: byte) =
        match size with
        | 0b00uy -> 0xff, 0x80
        | 0b01uy -> 0xffff, 0x8000
        | _      -> -1, (1 <<< 31)
    let sizeChar (size: byte) = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"

    ///One ADDX/SUBX step. `dest`/`source` must already be masked to `m`. Returns (result, newCCR).
    ///Z is only ever cleared here, never set - the multi-precision quirk that lets a chain across a
    ///wider value report whether the whole thing came out zero. X mirrors carry/borrow.
    let step (isAdd: bool) (m: int) (sb: int) (curCCR: int16) (xFlag: bool) (dest: int) (source: int) =
        let e = if xFlag then 1 else 0
        let result = (if isAdd then dest + source + e else dest - source - e) &&& m
        let carry =
            if isAdd then uint64 (uint32 dest) + uint64 (uint32 source) + uint64 e > uint64 (uint32 m)
            else uint64 (uint32 source) + uint64 e > uint64 (uint32 dest)
        let overflow =
            let dsSame = (dest &&& sb) = (source &&& sb)
            (if isAdd then dsSame else not dsSame) && ((result &&& sb) <> (dest &&& sb))
        let mutable ccr = curCCR &&& ~~~0x8s &&& ~~~0x2s &&& ~~~0x1s &&& ~~~0x10s
        if (result &&& sb) <> 0 then ccr <- ccr ||| 0x8s //N
        if result <> 0 then ccr <- ccr &&& ~~~0x4s //Z
        if overflow then ccr <- ccr ||| 0x2s //V
        if carry then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
        result, ccr

//type AddressRegister =
    //| A0 of int
    //| A1 of int
    //| A2 of int
    //| A3 of int
    //| A4 of int
    //| A5 of int
    //| A6 of int
    //| A7 of int
           
///Decoded brief extension word for (d8,An,Xn) addressing.
///Offset is the index register's contribution (sign-extended per Word/Long, per UseLong) plus Disp,
///i.e. what the base address register still needs added to it to form the effective address.
type IndexedAddressing =
    { Disp: int; Offset: int; IndexIsAddress: bool; IndexReg: byte; UseLong: bool }

///A resolved effective-address operand (see Cpu.ResolveEa). The address arithmetic and any
///extension-word reads are already done; `EaMem` carries the final byte address. Auto
///pre-decrement / post-increment is NOT applied to the register here - it is returned as a
///separate `Cpu -> Cpu` writeback so the instruction can order it against its own result write
///(e.g. a read-modify-write on `-(An)` must decrement once, then read and write that address).
type EaResolved =
    | EaDn of byte      // Dn  - low byte/word or full long, per the access size
    | EaAn of byte      // An  - always the full 32-bit register
    | EaMem of uint32   // any memory operand: (An), (An)+, -(An), (d16,An), (d8,An,Xn),
                        // (xxx).W, (xxx).L, (d16,PC), (d8,PC,Xn) - address already formed
    | EaImm of int      // #imm - zero-extended to the access size

[<StructuredFormatDisplay("{DisplayRegisters}")>]
type Cpu =
    {D0: int; D1: int; D2: int; D3: int; D4: int; D5: int; D6: int; D7: int
     A0: int; A1: int; A2: int; A3: int; A4: int; A5: int; A6: int; A7: int
     //A7 always holds whichever physical stack pointer is "live" right now, mirroring real 68000
     //hardware register banking - USP/SSP are shadow copies of the *other* one, updated only at
     //the moment a privilege-mode transition (TRAP/exception entry, RTE) swaps which stack A7
     //refers to. This used to be a single shared A7 with USP existing only so MOVE USP,An/MOVE
     //An,USP had somewhere to read and write ("this emulator has no real supervisor/user stack
     //switching") - that simplification broke down once real ROM code (GEMDOS's trap#1 handler)
     //relied on the hardware swap to bridge from its own supervisor stack back to the caller's:
     //it does `move usp,An` expecting USP to hold the value A7 had the instant before the trap,
     //which is only true if trap entry actually performed the swap. See
     //[[atari-st-emulator-next-instructions]]'s twenty-fifth pass for the live trace that caught
     //this (cmpi comparing a function-code word against stale/zero data at the "wrong" address).
     USP: int
     SSP: int
     PC: int
     CCR: int16
     MMU: MMU }

    static member Create(mmu: MMU) =
        //TODO review MMU creation / ownership
        { D0=0; D1=0; D2=0; D3=0; D4=0; D5=0; D6=0; D7=0
          A0=0; A1=0; A2=0; A3=0; A4=0; A5=0; A6=0; A7=0
          USP=0; SSP=0
          PC=0; CCR=0s; MMU=mmu}
          
    member x.C = not (x.CCR &&& 0x1s = 0s)
    member x.V = not (x.CCR &&& 0x2s = 0s)
    member x.Z = not (x.CCR &&& 0x4s = 0s)
    member x.N = not (x.CCR &&& 0x8s = 0s)
    member x.X = not (x.CCR &&& 0x10s = 0s)
    member x.InterruptMask = x.CCR &&& 0x700s
    member x.M = not (x.CCR &&& 0x1000s = 0s)
    member x.S = not (x.CCR &&& 0x2000s = 0s)
    member x.T0 = not (x.CCR &&& 0x4000s = 0s)
    member x.T1 = not (x.CCR &&& 0x8000s = 0s)

    ///Applies real 68000 privilege-mode stack switching for any place the full SR gets replaced
    ///(TRAP/exception entry, RTE, or a direct MOVE-to-SR that changes the S bit) - entering or
    ///leaving supervisor mode swaps which physical stack A7 refers to, parking the outgoing one
    ///in USP/SSP so it's there to restore the next time that mode is re-entered. No swap at all
    ///if the S bit isn't actually changing (staying supervisor across a nested trap, or a
    ///MOVE-to-SR that only touches other bits) - same as real hardware only re-maps A7 on an
    ///actual transition. See the record's USP/SSP field comment for the bug this fixes.
    member x.WithSR (newCcr: int16) : Cpu =
        let willBeSupervisor = not (newCcr &&& 0x2000s = 0s)
        if x.S = willBeSupervisor then {x with CCR = newCcr}
        elif willBeSupervisor then {x with CCR = newCcr; USP = x.A7; A7 = x.SSP}
        else {x with CCR = newCcr; SSP = x.A7; A7 = x.USP}

    ///Shared "plain 6-byte-frame" software-trap machinery: enters supervisor mode via WithSR
    ///(pushing onto the correct, just-switched-to stack - see WithSR's comment for why that
    ///order matters), pushes the caller-supplied return PC and the pre-trap CCR, then jumps to
    ///the vector table entry at vectorNumber*4. Used by TRAP #n and the Line-A/Line-F emulator
    ///traps (vectors 10/11) - all three are real 68000 vectors sharing this exact frame shape.
    member x.EnterVector (vectorNumber: int) (returnPC: int) : Cpu =
        let vectorAddr = uint32 (vectorNumber * 4)
        let switched = x.WithSR (x.CCR ||| 0x2000s)
        let pcPushAddr = switched.A7 - 4
        x.MMU.WriteLong (uint32 pcPushAddr) returnPC
        let srPushAddr = pcPushAddr - 2
        x.MMU.WriteWord (uint32 srPushAddr) x.CCR
        let newPC = x.MMU.ReadLong vectorAddr
        {switched with A7 = srPushAddr; PC = newPC}

    ///Real 68000 autovectored interrupt entry (levels 1-7, vector = 24+level - e.g. VBL is level 4
    ///= vector 28, the MFP is level 6 = vector 30, matching Hatari's own exception trace for this
    ///same ROM - see [[atari-st-emulator-next-instructions]]'s twenty-eighth pass). Unlike
    ///EnterVector's software traps (TRAP/Line-A/Line-F), a real interrupt exception ALSO raises the
    ///CCR's own interrupt-priority mask to `level` (masking further same-or-lower-priority
    ///interrupts until software explicitly lowers it again) and clears the trace bit - both are
    ///real hardware side effects of interrupt entry specifically, not shared with software traps.
    ///The pushed SR is the CALLER's original `x.CCR` (matching EnterVector) - only the *resulting*
    ///CPU state carries the raised mask/cleared trace bit, exactly like real hardware pushes the
    ///pre-exception SR and only then updates the live one. Returns the PC unchanged as the return
    ///address (an interrupt doesn't complete or skip whatever instruction was about to run).
    member x.EnterInterrupt (level: int) (vectorNumber: int) : Cpu =
        let raisedCcr = (x.CCR &&& ~~~0x8700s) ||| 0x2000s ||| int16 (level <<< 8)
        let switched = x.WithSR raisedCcr
        let pcPushAddr = switched.A7 - 4
        x.MMU.WriteLong (uint32 pcPushAddr) x.PC
        let srPushAddr = pcPushAddr - 2
        x.MMU.WriteWord (uint32 srPushAddr) x.CCR
        let newPC = x.MMU.ReadLong (uint32 (vectorNumber * 4))
        {switched with A7 = srPushAddr; PC = newPC}

    member x.AddressRegister (register: byte) =
        match register with
        | 0uy -> x.A0 | 1uy -> x.A1 | 2uy -> x.A2 | 3uy -> x.A3
        | 4uy -> x.A4 | 5uy -> x.A5 | 6uy -> x.A6 | 7uy -> x.A7
        | _ -> failwithf "Invalid register %uy" register
        
    member x.DataRegister (register: byte) =
        match register with
        | 0uy -> x.D0 | 1uy -> x.D1 | 2uy -> x.D2 | 3uy -> x.D3
        | 4uy -> x.D4 | 5uy -> x.D5 | 6uy -> x.D6 | 7uy -> x.D7
        | _ -> failwithf "Invalid register %uy" register

    member x.WithAddressRegister (register: byte) (value: int) =
        match register with
        | 0uy -> {x with A0 = value} | 1uy -> {x with A1 = value} | 2uy -> {x with A2 = value} | 3uy -> {x with A3 = value}
        | 4uy -> {x with A4 = value} | 5uy -> {x with A5 = value} | 6uy -> {x with A6 = value} | 7uy -> {x with A7 = value}
        | _ -> failwithf "Invalid register %uy" register

    member x.WithDataRegister (register: byte) (value: int) =
        match register with
        | 0uy -> {x with D0 = value} | 1uy -> {x with D1 = value} | 2uy -> {x with D2 = value} | 3uy -> {x with D3 = value}
        | 4uy -> {x with D4 = value} | 5uy -> {x with D5 = value} | 6uy -> {x with D6 = value} | 7uy -> {x with D7 = value}
        | _ -> failwithf "Invalid register %uy" register
      
    ///ADDX / SUBX, both the Dy,Dx register form and the -(Ay),-(Ax) memory predecrement form.
    ///`isAdd` picks the operation; `size` is the 2-bit size code. PC always advances by 2.
    member x.ExtendedArith (isAdd: bool) (size: byte) (usePredecrement: bool) (rx: byte) (ry: byte) : Cpu =
        let m, sb = ExtendedArith.sizeInfo size
        let mnem = (if isAdd then "addx." else "subx.") + ExtendedArith.sizeChar size
        if usePredecrement then
            // -(Ay),-(Ax): decrement Ay and read source, then decrement Ax and read dest, write back
            // to (Ax). A7 steps by 2 even for a byte op. Ay and Ax can alias (both decrement it).
            let stepFor r = match size with 0b10uy -> 4 | 0b01uy -> 2 | _ -> (if r = 7uy then 2 else 1)
            let read a = match size with 0b10uy -> x.MMU.ReadLong a | 0b01uy -> x.MMU.ReadWord a &&& 0xffff | _ -> int (x.MMU.ReadByte a)
            let yAddr = x.AddressRegister ry - stepFor ry
            let afterY = x.WithAddressRegister ry yAddr
            let source = read (uint32 yAddr) &&& m
            let xAddr = afterY.AddressRegister rx - stepFor rx
            let afterX = afterY.WithAddressRegister rx xAddr
            let dest = read (uint32 xAddr) &&& m
            let result, ccr = ExtendedArith.step isAdd m sb x.CCR x.X dest source
            match size with
            | 0b10uy -> x.MMU.WriteLong (uint32 xAddr) result
            | 0b01uy -> x.MMU.WriteWord (uint32 xAddr) (int16 result)
            | _      -> x.MMU.WriteByte (uint32 xAddr) (byte result)
            printfn "%s -(a%u),-(a%u)" mnem ry rx
            {afterX with PC = x.PC+2; CCR = ccr}
        else
            let dest = x.DataRegister rx &&& m
            let source = x.DataRegister ry &&& m
            let result, ccr = ExtendedArith.step isAdd m sb x.CCR x.X dest source
            let newValue = (x.DataRegister rx &&& ~~~m) ||| result
            printfn "%s D%u,D%u" mnem ry rx
            {x.WithDataRegister rx newValue with PC = x.PC+2; CCR = ccr}

    ///Decodes a (d8,An,Xn) brief extension word. Index register is D/A bit15, register bits14-12,
    ///W/L bit11 (sign-extend word vs full long), displacement is the low signed byte.
    member x.DecodeBriefExtension (extWord: int) : IndexedAddressing =
        let indexIsAddress = extWord &&& 0x8000 <> 0
        let indexReg = byte ((extWord >>> 12) &&& 0x7)
        let useLong = extWord &&& 0x0800 <> 0
        let disp = int (sbyte (extWord &&& 0xff))
        let indexValue =
            let raw = if indexIsAddress then x.AddressRegister indexReg else x.DataRegister indexReg
            if useLong then raw else int (int16 raw)
        { Disp = disp; Offset = indexValue + disp; IndexIsAddress = indexIsAddress; IndexReg = indexReg; UseLong = useLong }

    member x.DescribeIndexed (baseReg: byte) (ext: IndexedAddressing) =
        sprintf "%i(a%u,%s%u.%s)" ext.Disp baseReg (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w")

    ///Bytes an operand of this access size occupies in memory / an immediate consumes as extension.
    static member private EaOpBytes (size: OperandSize) =
        match size with
        | OperandSize.Byte -> 1 | OperandSize.Word -> 2 | OperandSize.Long -> 4
        | other -> failwithf "ResolveEa: unsupported access size %A" other

    ///Shared effective-address decoder for the classic 68000 modes. Given the 3-bit mode and
    ///register fields, the access size, and the address of this operand's first extension word
    ///(`extAddr`, normally `x.PC + 2`; for a MOVE destination it is past the source's extension
    ///words), returns:
    ///  - the resolved operand (`EaResolved`): a register selector, a formed memory address, or an
    ///    immediate value already masked to `size`;
    ///  - `extBytes`: how many bytes of extension words this operand consumed (add to the PC);
    ///  - a short description string for the instruction trace;
    ///  - a `Cpu -> Cpu` writeback applying the `(An)+` / `-(An)` register update (identity for
    ///    every other mode). Apply it once, after any result write, so a read-modify-write on
    ///    `-(An)` decrements exactly once.
    ///This is the replacement for the per-instruction hand-decoded `match eamode, eareg` ladders;
    ///migrate instruction buckets onto it one at a time (the 30M diskless boot must stay
    ///byte-identical after each). Unknown modes still `failwithf`, same as before.
    member x.ResolveEa (size: OperandSize) (mode: byte) (reg: byte) (extAddr: int) : EaResolved * int * string * (Cpu -> Cpu) =
        let readW a = x.MMU.ReadWord (uint32 a)
        let readL a = x.MMU.ReadLong (uint32 a)
        match mode, reg with
        | 0b000uy, r -> EaDn r, 0, sprintf "D%u" r, id
        | 0b001uy, r -> EaAn r, 0, sprintf "A%u" r, id
        | 0b010uy, r -> EaMem (uint32 (x.AddressRegister r)), 0, sprintf "(a%u)" r, id
        | 0b011uy, r ->
            let a = x.AddressRegister r
            let step = if r = 7uy && Cpu.EaOpBytes size = 1 then 2 else Cpu.EaOpBytes size
            EaMem (uint32 a), 0, sprintf "(a%u)+" r, (fun (c: Cpu) -> c.WithAddressRegister r (a + step))
        | 0b100uy, r ->
            let step = if r = 7uy && Cpu.EaOpBytes size = 1 then 2 else Cpu.EaOpBytes size
            let a = x.AddressRegister r - step
            EaMem (uint32 a), 0, sprintf "-(a%u)" r, (fun (c: Cpu) -> c.WithAddressRegister r a)
        | 0b101uy, r ->
            let d = int (int16 (readW extAddr))
            EaMem (uint32 (x.AddressRegister r + d)), 2, sprintf "%i(a%u)" d r, id
        | 0b110uy, r ->
            let ext = x.DecodeBriefExtension (readW extAddr)
            EaMem (uint32 (x.AddressRegister r + ext.Offset)), 2, x.DescribeIndexed r ext, id
        | 0b111uy, 0b000uy ->
            let a = int (int16 (readW extAddr))
            EaMem (uint32 a), 2, sprintf "$%x.w" a, id
        | 0b111uy, 0b001uy ->
            let a = readL extAddr
            EaMem (uint32 a), 4, sprintf "$%x.l" a, id
        | 0b111uy, 0b010uy ->
            let d = int (int16 (readW extAddr))
            EaMem (uint32 (extAddr + d)), 2, sprintf "%i(pc)" d, id
        | 0b111uy, 0b011uy ->
            let ext = x.DecodeBriefExtension (readW extAddr)
            EaMem (uint32 (extAddr + ext.Offset)), 2,
                (sprintf "%i(pc,%s%u.%s)" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w")), id
        | 0b111uy, 0b100uy ->
            match size with
            | OperandSize.Byte -> EaImm (readW extAddr &&& 0xff), 2, sprintf "#$%x" (readW extAddr &&& 0xff), id
            | OperandSize.Word -> EaImm (readW extAddr &&& 0xffff), 2, sprintf "#$%x" (readW extAddr &&& 0xffff), id
            | _ -> EaImm (readL extAddr), 4, sprintf "#$%x" (readL extAddr), id
        | _ -> failwithf "ResolveEa: unimplemented addressing mode %d reg %d" mode reg

    ///Read a resolved operand, returning the value zero-extended to `size`
    ///(byte -> 0..255, word -> 0..65535, long -> full 32 bits).
    member x.ReadEa (size: OperandSize) (loc: EaResolved) : int =
        let mask v = match size with OperandSize.Byte -> v &&& 0xff | OperandSize.Word -> v &&& 0xffff | _ -> v
        match loc with
        | EaDn r -> mask (x.DataRegister r)
        | EaAn r -> mask (x.AddressRegister r)
        | EaImm i -> i
        | EaMem a ->
            match size with
            | OperandSize.Byte -> int (x.MMU.ReadByte a)
            | OperandSize.Word -> x.MMU.ReadWord a &&& 0xffff
            | _ -> x.MMU.ReadLong a

    ///Write `value` to a resolved operand at `size`. Register writes preserve the unaffected high
    ///bits (byte/word); memory writes go straight through the MMU. Returns the updated Cpu.
    ///An `EaImm` destination is a decode bug and throws.
    member x.WriteEa (size: OperandSize) (loc: EaResolved) (value: int) (cpu: Cpu) : Cpu =
        match loc with
        | EaDn r ->
            let cur = cpu.DataRegister r
            let nv =
                match size with
                | OperandSize.Byte -> (cur &&& ~~~0xff) ||| (value &&& 0xff)
                | OperandSize.Word -> (cur &&& ~~~0xffff) ||| (value &&& 0xffff)
                | _ -> value
            cpu.WithDataRegister r nv
        | EaAn r -> cpu.WithAddressRegister r value
        | EaMem a ->
            (match size with
             | OperandSize.Byte -> x.MMU.WriteByte a (byte value)
             | OperandSize.Word -> x.MMU.WriteWord a (int16 value)
             | _ -> x.MMU.WriteLong a value)
            cpu
        | EaImm _ -> failwith "WriteEa: immediate operand is not a valid destination"

    ///Shared "#imm <op> <ea>" decoder for the bucket-0 immediates (ORI/ANDI/EORI/ADDI/SUBI/CMPI).
    ///The immediate is at PC+2 (one word for byte/word, one long for long); the destination EA's
    ///extension words follow it. `combine size dest imm -> result * ccr` does the op at the masked
    ///size and computes the CCR; `write` is false for CMPI (compare only). `(An)+ / -(An)` register
    ///updates are applied after any result write, exactly as the shared EA decoder intends.
    member x.ImmediateToEa (mnemonic: string) (sizeCode: byte) (mode: byte) (reg: byte)
                           (write: bool) (combine: OperandSize -> int -> int -> int * int16) : Cpu =
        let size =
            match sizeCode with
            | 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | 0b10uy -> OperandSize.Long
            | s -> failwithf "%s: bad size %x" mnemonic s
        let immBytes = match size with OperandSize.Long -> 4 | _ -> 2
        let imm =
            match size with
            | OperandSize.Byte -> x.MMU.ReadWord (uint32 (x.PC + 2)) &&& 0xff
            | OperandSize.Word -> x.MMU.ReadWord (uint32 (x.PC + 2)) &&& 0xffff
            | _ -> x.MMU.ReadLong (uint32 (x.PC + 2))
        let loc, extBytes, desc, regUpdate = x.ResolveEa size mode reg (x.PC + 2 + immBytes)
        let dest = x.ReadEa size loc
        let result, ccr = combine size dest imm
        let after = if write then x.WriteEa size loc result (regUpdate x) else regUpdate x
        printfn "%s.%s #$%x,%s" mnemonic (match size with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l") imm desc
        { after with PC = x.PC + 2 + immBytes + extBytes; CCR = ccr }

    ///N/Z from a logical result at `size`, V and C cleared, X untouched - the ORI/ANDI/EORI CCR.
    member x.LogicalCcr (size: OperandSize) (v: int) : int16 =
        match size with
        | OperandSize.Byte -> CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte v)
        | OperandSize.Word -> CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 v)
        | _ -> CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR v

    ///Shared BTST / BCHG / BCLR / BSET (`opmode` 00/01/10/11), both the Dn-bit-number (dynamic) and
    ///immediate-bit-number (static) encodings - the caller supplies the already-extracted bit number
    ///and the address of the EA's first extension word (`extAddr` = PC+2 dynamic, PC+4 static, which
    ///also fixes the PC advance since the opcode+immediate size is baked into `extAddr`). A Dn
    ///destination is 32 bits wide with the bit number taken mod 32; every memory destination is a
    ///byte with the bit number mod 8. Z is set from the *old* value of the addressed bit (Z <- ~bit);
    ///no other CCR bit is touched. BTST performs no write.
    member x.BitOp (mnemonic: string) (opmode: byte) (bitNumber: int) (eamode: byte) (eareg: byte) (extAddr: int) : Cpu =
        let isReg = eamode = 0b000uy
        let size = if isReg then OperandSize.Long else OperandSize.Byte
        let bit = bitNumber &&& (if isReg then 31 else 7)
        let loc, extBytes, desc, regUpdate = x.ResolveEa size eamode eareg extAddr
        let current = x.ReadEa size loc
        let mask = 1 <<< bit
        let ccr = if current &&& mask <> 0 then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
        let after =
            match opmode with
            | 0b00uy -> regUpdate x                                              // BTST
            | 0b01uy -> x.WriteEa size loc (current ^^^ mask) (regUpdate x)      // BCHG
            | 0b10uy -> x.WriteEa size loc (current &&& ~~~mask) (regUpdate x)   // BCLR
            | _      -> x.WriteEa size loc (current ||| mask) (regUpdate x)      // BSET
        printfn "%s %s" mnemonic desc
        { after with PC = extAddr + extBytes; CCR = ccr }

    ///Shared "<ea> op Dn -> Dn" / "Dn op <ea> -> <ea>" decoder for the register data buckets
    ///(OR bucket 8, SUB 9, CMP/EOR B, AND C, ADD D). `opmode` is the raw 3-bit opmode field: the
    ///low two bits are the size (00/01/10 = byte/word/long), bit 2 the direction - 0 means the EA
    ///is the source and Dn the destination (`<ea> op Dn -> Dn`), 1 means the EA is the destination
    ///(`Dn op <ea> -> <ea>`). `combine size dest source -> result * ccr` performs the op at the
    ///masked size and computes the CCR; `dest` is the current value of whichever operand is written
    ///back (Dn in the ea->Dn direction, the EA otherwise) and `source` is the other operand. `write`
    ///is false for CMP (flags only). ADDX/SUBX/ABCD/SBCD/CMPM/EXG share this opcode space and must
    ///be matched by their own patterns first. The `(An)+` / `-(An)` writeback is applied after the
    ///result write, exactly as the shared EA decoder intends.
    member x.RegEaOp (mnemonic: string) (opmode: byte) (dn: byte) (eamode: byte) (eareg: byte)
                     (write: bool) (combine: OperandSize -> int -> int -> int * int16) : Cpu =
        let size =
            match opmode &&& 0b011uy with
            | 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | _ -> OperandSize.Long
        let eaToDn = opmode &&& 0b100uy = 0uy
        let loc, extBytes, desc, regUpdate = x.ResolveEa size eamode eareg (x.PC + 2)
        let eaVal = x.ReadEa size loc
        let dnVal = x.ReadEa size (EaDn dn)
        let dest, source, target = if eaToDn then dnVal, eaVal, EaDn dn else eaVal, dnVal, loc
        let result, ccr = combine size dest source
        let after = if write then x.WriteEa size target result (regUpdate x) else regUpdate x
        printfn "%s.%s %s" mnemonic
            (match size with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l")
            (if eaToDn then sprintf "%s,D%u" desc dn else sprintf "D%u,%s" dn desc)
        { after with PC = x.PC + 2 + extBytes; CCR = ccr }

    member x.EvaluateCondition (cond: Condition) =
        match cond with
        | Condition.T -> true
        | Condition.F -> false
        | Condition.H -> (not x.C) && (not x.Z)
        | Condition.LS -> x.C || x.Z
        | Condition.CC_HI -> not x.C
        | Condition.CC_LO -> x.C
        | Condition.NE -> not x.Z
        | Condition.EQ -> x.Z
        | Condition.VC -> not x.V
        | Condition.VS -> x.V
        | Condition.PL -> not x.N
        | Condition.MI -> x.N
        | Condition.GE -> x.N = x.V
        | Condition.LT -> x.N <> x.V
        | Condition.GT -> (x.N = x.V) && not x.Z
        | Condition.LE -> x.Z || (x.N <> x.V)
        | other -> failwithf "Unknown condition %A" other

    member x.TraceMode =
        match (x.T1, x.T0) with
        | false, false -> No_Trace
        | true,  false -> Trace_On_Any_Instruction
        | false, true ->  Trace_On_Change_of_Flow
        | true,  true ->  Undefined_Trace
        
    member x.ActiveStack =
        match x.S, x.M with
        | false, _ -> USP
        | true, false -> ISP
        | true, true -> MSP
        
    member x.Reset() =
        //SSP is loaded form $0
        //PC is loaded from $4
        //reset and CCR setup should come from rom (first 8 bytes copied to $0-$8)
        //Real 68000 RESET forces supervisor mode with interrupts fully masked (S=1, IPL=7, T=0)
        //as part of loading the initial SSP/PC from vectors 0/1 - CCR previously defaulted to 0
        //(S=0) here, which never mattered while no code path checked S, but WithSR's introduction
        //(see its comment) makes S's starting value load-bearing: without this, the ROM's own
        //first instruction (`move #$2700,sr`, redundantly re-asserting the same state real
        //hardware already establishes) would misread the reset-loaded SSP as a *user* stack to
        //park and replace A7 with the still-empty SSP shadow instead of just keeping it.
        { x with A7 = x.MMU.ReadLong 0u
                 PC = x.MMU.ReadLong 4u
                 CCR = 0x2700s }
    
    ///See MMU.FastForwardTbdrTo's comment for the "why". Peeks (without executing or mutating
    ///state) at the instruction the CPU is about to run and, only if it's exactly the "read TBDR
    ///cmp.b against a fixed register / branch back to the read if unequal" 3-instruction shape,
    ///resolves the whole busy-wait in one step instead of interpreting every intervening
    ///iteration. Deliberately narrow: TOS also uses this same register for a debounce idiom
    ///(snapshot TBDR once, then re-check across many reads that it hasn't changed), but that
    ///compares against a value snapshotted at runtime rather than a fixed compare wired into this
    ///exact loop shape, so it can never match here and keeps running for real - which it must, to
    ///actually do its job of confirming the value is stable.
    ///Takes the already-fetched first word rather than re-reading x.PC itself - this runs
    ///unconditionally on every single Step(), so re-fetching the same address Step() is about to
    ///fetch again anyway would double the cost of every instruction's first-word read, not just
    ///the rare ones this guard actually resolves.
    member x.TryFastForwardTbdrPoll(instruction: int) : Cpu option =
        match instruction with
        | Move(OperandSize.Byte, dReg, 0b000uy, 0b010uy, sReg)
                when (uint32 (x.AddressRegister sReg) &&& 0xFFFFFFu) = x.MMU.TbdrAddress
                     && x.MMU.PeekTbcr <> 0uy ->
            match x.MMU.ReadWord (uint32 (x.PC + 2)) with
            | CMP(cmpDest, 0b000uy, 0b000uy, cmpSource) when cmpDest = dReg ->
                match x.MMU.ReadWord (uint32 (x.PC + 4)) with
                | BCC(Condition.NE, disp) when disp <> 0x00uy && disp <> 0xFFuy
                                                && x.PC + 6 + int (sbyte disp) = x.PC ->
                    let target = byte (x.DataRegister cmpSource)
                    if x.MMU.PeekTbdr = target then
                        None //already converged - let the normal single-step path exit it
                    else
                        x.MMU.FastForwardTbdrTo target
                        let newValue = (x.DataRegister dReg &&& ~~~0xff) ||| int target
                        let ccr = CCR.Subtract_IgnoringX_Byte x.CCR target target
                        let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC + 6; CCR = ccr}
                        printfn "fastforward: tbdr poll -> D%u=$%02x (skipped busy-wait)" dReg target
                        Some newCpu
                | _ -> None
            | _ -> None
        | _ -> None

    member x.Step() =
    //TODO implement prefetch ops
        let pendingLevel = x.MMU.PendingInterruptLevel
        if pendingLevel > 0 && int16 (pendingLevel <<< 8) > x.InterruptMask then
            //Real 68000 hardware samples IPL2-0 between instructions and takes any request whose
            //level exceeds the current mask (or is level 7, always taken - not modeled separately
            //since no level-7 source exists yet) - see EnterInterrupt's own comment for why this
            //needs different handling than TRAP/Line-A/Line-F's shared EnterVector path.
            let vector = x.MMU.PendingInterruptVector
            x.MMU.AcknowledgeInterrupt()
            printfn "interrupt: level %d -> vector %d" pendingLevel vector
            x.EnterInterrupt pendingLevel vector
        else
        try
            let instruction = x.MMU.ReadWord (uint32 x.PC)
            match x.TryFastForwardTbdrPoll(instruction) with
            | Some fastForwarded -> fastForwarded
            | None ->
            //printfn "instruction: %x" instruction
            match (instruction >>> 12) &&& 0xF with
            | 0x0 -> x.DecodeBucket0 instruction
            | 0x1 | 0x2 | 0x3 -> x.DecodeBucketMove instruction
            | 0x4 -> x.DecodeBucket4 instruction
            | 0x5 -> x.DecodeBucket5 instruction
            | 0x6 -> x.DecodeBucket6 instruction
            | 0x7 -> x.DecodeBucket7 instruction
            | 0x8 -> x.DecodeBucket8 instruction
            | 0x9 -> x.DecodeBucket9 instruction
            | 0xA -> //Line-A emulator trap (vector 10, $028) - real 68000 hardware traps
                     //unconditionally on any top-nibble-0xA opcode; the ST uses this for VDI
                     //linkage. Confirmed against Atari's own "Atari ST Internals" exception
                     //vector table and cross-checked against Hatari's newcpu.c cycle table.
                     //Pushes x.PC (the trapped opcode's OWN address), not x.PC+2: real hardware's
                     //exception frame for this trap points AT the offending opcode so the installed
                     //handler can re-fetch and decode it (TOS's own $a30e dispatcher does exactly
                     //that via `move.w (a0)+,d1`, using the opcode's own low 12 bits as a function
                     //number) - confirmed via a direct Hatari cpu_disasm trace of $a30e live, see
                     //[[atari-st-emulator-next-instructions]]'s twenty-ninth pass.
                     let newCpu = x.EnterVector 10 x.PC
                     printfn "line-a $%04x" instruction
                     newCpu
            | 0xB -> x.DecodeBucketB instruction
            | 0xC -> x.DecodeBucketC instruction
            | 0xD -> x.DecodeBucketD instruction
            | 0xE -> x.DecodeBucketE instruction
            | 0xF -> //Line-F emulator trap (vector 11, $02C) - same unconditional-trap hardware
                     //behavior as Line-A above; the ST uses this for AES linkage, with the low
                     //12 bits of the opcode ITSELF carrying the dispatch function number, which
                     //the installed handler recovers by re-reading the trapped opcode from the
                     //pushed PC (see the Line-A case above for the full explanation - same fix,
                     //same reason).
                     let newCpu = x.EnterVector 11 x.PC
                     printfn "line-f $%04x" instruction
                     newCpu
            | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x
        with
        | AddressError faultAddress ->
            //Real 68000 hardware traps to the Address Error vector (vector 3, at address $C)
            //instead of performing a word/long access to an odd address. Mirrors TRAP's
            //simplified 6-byte exception frame (this emulator doesn't model the larger real
            //Address Error frame's extra fault-address/access-type diagnostic words, same
            //simplification TRAP already makes) and pushes the faulting instruction's own PC
            //(not PC+2 - there's no well-defined "next instruction" for an access that never
            //completed). Found via a differential comparison against a real 68000 core
            //(dmcoles/estyjs) - see [[atari-st-emulator-next-instructions]]'s nineteenth pass:
            //without this, a misaligned access was silently performed instead of trapping,
            //diverging from what real hardware (and TOS's own error handler) would do.
            //Entering supervisor mode (see TRAP below for why this swap matters) - if already
            //supervisor (nested fault), the supervisor stack just keeps being used as-is.
            let vectorAddr = 3u * 4u
            let switched = x.WithSR (x.CCR ||| 0x2000s)
            let pcPushAddr = switched.A7 - 4
            x.MMU.WriteLong (uint32 pcPushAddr) x.PC
            let srPushAddr = pcPushAddr - 2
            x.MMU.WriteWord (uint32 srPushAddr) x.CCR
            let newPC = x.MMU.ReadLong vectorAddr
            let newCpu = {switched with A7 = srPushAddr; PC = newPC}
            printfn "address error: misaligned access at $%08x -> vector 3 ($%08x)" faultAddress newPC
            newCpu
        | BusError faultAddress ->
            //Real 68000 hardware traps to the Bus Error vector (vector 2, at address $8) when an
            //access hits an address no device claims (DTACK never asserted) - mirrors AddressError's
            //simplified 6-byte frame just above, for the same reason (this emulator doesn't model
            //the larger real Bus Error frame's extra fault-address/access-type diagnostic words).
            //See [[atari-st-emulator-next-instructions]]'s twentieth pass: previously an unmapped
            //access silently read 0 / dropped the write instead of trapping, letting execution wander
            //into whatever garbage that produced (e.g. an `rte` to a genuinely unmapped address) as
            //if it were valid code, instead of giving TOS's own bus-error handler a chance to run.
            let vectorAddr = 2u * 4u
            let switched = x.WithSR (x.CCR ||| 0x2000s)
            let pcPushAddr = switched.A7 - 4
            x.MMU.WriteLong (uint32 pcPushAddr) x.PC
            let srPushAddr = pcPushAddr - 2
            x.MMU.WriteWord (uint32 srPushAddr) x.CCR
            let newPC = x.MMU.ReadLong vectorAddr
            let newCpu = {switched with A7 = srPushAddr; PC = newPC}
            printfn "bus error: unmapped access at $%08x -> vector 2 ($%08x)" faultAddress newPC
            newCpu

    member x.DecodeBucket0 (instruction: int) : Cpu =
        match instruction with
        | OriToSR ->
            //Mask the immediate to the bits the 68000 SR actually implements (T=15, S=13, I=10..8,
            //CCR=4..0) so an OR can never leave the unused bits set - the 680x0 vectors check this.
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xA71F)
            let newCcr = x.CCR ||| immediate
            printfn "ori #$%x,SR" immediate
            {x with PC = x.PC+4; CCR = newCcr}

        | AndiToSR ->
            //Privileged, and unlike OriToSR (bits only ever set) an AND can clear the S bit -
            //route through WithSR so a supervisor->user transition swaps A7/USP/SSP correctly,
            //matching real hardware and this project's own Move2SR/RTE convention.
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
            let newCcr = x.CCR &&& immediate
            let switched = x.WithSR newCcr
            printfn "andi #$%x,SR" immediate
            {switched with PC = x.PC+4}

        | OriToCcr ->
            //Opcode-space alias of ORI's mode=111/reg=100 EA slot (see [[68k-opcode-space-aliasing]]).
            //Byte operation on the condition-code half of SR; the unused CCR bits 5-7 stay 0.
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0x1f)
            printfn "ori #$%x,CCR" immediate
            {x with PC = x.PC+4; CCR = x.CCR ||| immediate}

        | AndiToCcr ->
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
            printfn "andi #$%x,CCR" immediate
            {x with PC = x.PC+4; CCR = x.CCR &&& (immediate ||| 0xff00s)}

        | EoriToSR ->
            //Privileged word operation on the whole SR; an EOR can flip the S bit, so route the
            //result through WithSR (matches AndiToSR / RTE), which swaps A7/USP/SSP on a mode change.
            //Mask to the implemented SR bits so the unused ones can't be toggled (see OriToSR).
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xA71F)
            let switched = x.WithSR (x.CCR ^^^ immediate)
            printfn "eori #$%x,SR" immediate
            {switched with PC = x.PC+4}

        | ORI(size, mode, register) ->
            x.ImmediateToEa "ori" size mode register true
                (fun sz dest imm -> let r = dest ||| imm in r, x.LogicalCcr sz r)

        | ANDI(size, mode, register) ->
            x.ImmediateToEa "andi" size mode register true
                (fun sz dest imm -> let r = dest &&& imm in r, x.LogicalCcr sz r)

        | EoriToCcr ->
            //Opcode-space alias: mode=111/reg=100 in EORI's general EA encoding is reserved for
            //this dedicated "EORI to CCR" form - see [[68k-opcode-space-aliasing]]. Byte operation
            //on the condition codes; only the 5 implemented CCR bits can be toggled, the unused
            //bits 5-7 stay 0 (the 680x0 vectors check this).
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0x1f)
            let newCcr = x.CCR ^^^ immediate
            printfn "eori #$%x,CCR" immediate
            {x with PC = x.PC+4; CCR = newCcr}

        | EORI(size, mode, register) ->
            x.ImmediateToEa "eori" size mode register true
                (fun sz dest imm -> let r = dest ^^^ imm in r, x.LogicalCcr sz r)

        | ADDI(size, mode, register) ->
            //ADDI folds C into X (CCR.Add*), unlike ADDA/ADDQ-to-An which touch no flags.
            x.ImmediateToEa "addi" size mode register true (fun sz dest imm ->
                match sz with
                | OperandSize.Byte -> let d, i = byte dest, byte imm in int (d + i), CCR.Add_Byte x.CCR d i
                | OperandSize.Word -> let d, i = int16 dest, int16 imm in int (d + i), CCR.Add_Word x.CCR d i
                | _ -> dest + imm, CCR.Add x.CCR dest imm)

        | SUBI(size, mode, register) ->
            x.ImmediateToEa "subi" size mode register true (fun sz dest imm ->
                match sz with
                | OperandSize.Byte -> let d, i = byte dest, byte imm in int (d - i), CCR.Subtract_Byte x.CCR d i
                | OperandSize.Word -> let d, i = int16 dest, int16 imm in int (int16 (int d - int i)), CCR.Subtract_Word x.CCR d i
                | _ -> dest - imm, CCR.Subtract x.CCR dest imm)

        | CMPI(size, mode, register) ->
            x.ImmediateToEa "cmpi" size mode register false (fun sz dest imm ->
                match sz with
                | OperandSize.Byte -> 0, CCR.Subtract_IgnoringX_Byte x.CCR (byte dest) (byte imm)
                | OperandSize.Word -> 0, CCR.Subtract_IgnoringX_Word x.CCR (int16 dest) (int16 imm)
                | _ -> 0, CCR.Subtract_IgnoringX x.CCR dest imm)
        | MOVEP(register, opmode, addressReg) ->
            match opmode with
            | 0b111uy -> //MOVEP.L Dx,(d16,Ay)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister addressReg + int displacement
                let value = x.DataRegister register
                x.MMU.WriteByte (uint32 addr) (byte (value >>> 24))
                x.MMU.WriteByte (uint32 (addr+2)) (byte (value >>> 16))
                x.MMU.WriteByte (uint32 (addr+4)) (byte (value >>> 8))
                x.MMU.WriteByte (uint32 (addr+6)) (byte value)
                let newCpu = {x with PC = x.PC+4}
                printfn "movep.l D%u,%i(a%u)" register displacement addressReg
                newCpu
            | _ -> failwithf "movep: not implemented for opmode %x" opmode

        | BitOpDynamic(register, opmode, eamode, eareg) ->
            let mnem = match opmode with 0b00uy -> "btst" | 0b01uy -> "bchg" | 0b10uy -> "bclr" | _ -> "bset"
            x.BitOp mnem opmode (int (x.DataRegister register)) eamode eareg (x.PC + 2)

        | BitOpImmediate(opmode, eamode, eareg) ->
            //Static bit number: a literal byte in the extension word at PC+2, so the EA's own
            //extension words start at PC+4. opmode is never 00 here (that is BTSTImmediate).
            let mnem = match opmode with 0b01uy -> "bchg" | 0b10uy -> "bclr" | _ -> "bset"
            let bitnumber = x.MMU.ReadWord (uint32 (x.PC + 2)) &&& 0xff
            x.BitOp mnem opmode bitnumber eamode eareg (x.PC + 4)

        | BTSTImmediate(eamode, eareg) ->
            let bitnumber = x.MMU.ReadWord (uint32 (x.PC + 2)) &&& 0xff
            x.BitOp "btst" 0b00uy bitnumber eamode eareg (x.PC + 4)

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    ///MOVE / MOVEA, every size and every addressing-mode combination, through the shared EA decoder.
    ///Source EA is resolved at `x.PC + 2`; its post-increment / pre-decrement writeback is applied
    ///*before* the destination EA is formed (real 68000 order - this is what makes the same-register
    ///`(An)+,(An)+` / `(An)+,-(An)` / `(An)+,(d16,An)` aliasing come out right for free). MOVEA (dest
    ///mode An) sign-extends a word source to 32 bits, takes a long source whole, and leaves the CCR
    ///alone; every other destination sets N/Z from the moved value and clears V/C, X untouched.
    member x.DecodeBucketMove (instruction: int) : Cpu =
        match instruction with
        | Move(size, dReg, dMode, sMode, sReg) ->
            let sizeChar = match size with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | OperandSize.Long -> "l" | other -> failwithf "Move invalid operand size %A" other
            //MOVE.B with an address register as source or destination is an illegal encoding on the
            //68000 - keep it an explicit failure rather than silently executing it.
            if size = OperandSize.Byte && (sMode = 0b001uy || dMode = 0b001uy) then
                failwithf "MOVE.B with An operand is illegal (instruction 0x%x)" instruction

            let srcLoc, srcExt, srcDesc, srcUpdate = x.ResolveEa size sMode sReg (x.PC + 2)
            let rawSource = x.ReadEa size srcLoc
            let x = srcUpdate x
            let dstLoc, dstExt, dstDesc, dstUpdate = x.ResolveEa size dMode dReg (x.PC + 2 + srcExt)
            let newPC = x.PC + 2 + srcExt + dstExt

            match dstLoc with
            | EaAn r ->
                let value = match size with OperandSize.Word -> int (int16 rawSource) | _ -> rawSource
                printfn "movea.%s %s,A%u" sizeChar srcDesc r
                { x.WithAddressRegister r value with PC = newPC }
            | _ ->
                let ccr =
                    match size with
                    | OperandSize.Byte -> CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte rawSource)
                    | OperandSize.Word -> CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 rawSource)
                    | _ -> CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR rawSource
                let written = x.WriteEa size dstLoc rawSource (dstUpdate x)
                printfn "move.%s %s,%s" sizeChar srcDesc dstDesc
                { written with PC = newPC; CCR = ccr }

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket4 (instruction: int) : Cpu =
        match instruction with
        | Move2CCR(mode, register) ->
            //Unprivileged, unlike Move2SR - only the low byte (condition codes) is replaced,
            //S/T/interrupt-mask (the CCR's upper byte) are left untouched, and no WithSR/A7
            //swap applies since this can never change the S bit.
            match mode with
            | 0b000uy -> //Dn
                let source = int16 (x.DataRegister register)
                //Only CCR bits 0-4 exist on the 68000; bits 5-7 of the source byte are discarded
                //(they read back as 0), same masking bug as commit a4f473e for the -to-CCR immediates.
                let newCcr = (x.CCR &&& ~~~0xffs) ||| (source &&& 0x1fs)
                printfn "move D%u,ccr" register
                {x with PC = x.PC+2; CCR = newCcr}
            | 0b111uy when register = 0b100uy -> //#imm
                let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                //Only CCR bits 0-4 exist on the 68000; bits 5-7 of the source byte are discarded
                //(they read back as 0), same masking bug as commit a4f473e for the -to-CCR immediates.
                let newCcr = (x.CCR &&& ~~~0xffs) ||| (source &&& 0x1fs)
                printfn "move #$%x,ccr" source
                {x with PC = x.PC+4; CCR = newCcr}
            | _ ->
                //Memory source: MOVE <ea>,CCR reads a word, only the low byte reaches the CCR.
                let addr, pcAdv, regFix =
                    match mode with
                    | 0b010uy -> uint32 (x.AddressRegister register), 2, id                                  //(An)
                    | 0b011uy -> uint32 (x.AddressRegister register), 2, (fun (c: Cpu) -> c.WithAddressRegister register (x.AddressRegister register + 2)) //(An)+
                    | 0b100uy -> uint32 (x.AddressRegister register - 2), 2, (fun (c: Cpu) -> c.WithAddressRegister register (x.AddressRegister register - 2)) //-(An)
                    | 0b101uy -> uint32 (x.AddressRegister register + int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))), 4, id //(d16,An)
                    | 0b111uy when register = 0b000uy -> uint32 (int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))), 4, id  //(xxx).W
                    | 0b111uy when register = 0b001uy -> uint32 (x.MMU.ReadLong(uint32 (x.PC+2))), 6, id               //(xxx).L
                    | _ -> failwithf "move2ccr not implemented for mode %x" mode
                let source = int16 (x.MMU.ReadWord addr)
                //Only CCR bits 0-4 exist on the 68000; bits 5-7 of the source byte are discarded
                //(they read back as 0), same masking bug as commit a4f473e for the -to-CCR immediates.
                let newCcr = (x.CCR &&& ~~~0xffs) ||| (source &&& 0x1fs)
                printfn "move <ea mode %x reg %u>,ccr" mode register
                { regFix x with PC = x.PC + pcAdv; CCR = newCcr }

        | Move2SR(mode, register) ->
            //Hack, not sure about this
            //Goes through WithSR (not a plain `CCR = newCcr`) because this instruction can change
            //the S bit directly, without going through TRAP/RTE - real TOS's own boot code does
            //exactly this as its very first instruction (`move #$2700,sr`), which must swap A7
            //over to the supervisor stack same as a trap would (see USP/SSP field comment).
            //Only SR bits T(15), S(13), I2-I0(10-8) and CCR(4-0) are implemented on the 68000;
            //bits 14,12,11,7,6,5 read back as 0, so mask every written value to 0xA71F - same
            //unused-bit-leak bug as commit a4f473e (ORI/ANDI/EORI to SR).
            if mode = 0x7 && register = 0b100 then
                //load data
                let register = int16 (x.MMU.ReadWord (uint32 (x.PC+2)) &&& 0xA71F)
                printfn "move #%0x, sr" register
                {x.WithSR register with PC = x.PC + 4}
            elif mode = 0x0 then //Dn
                let reg = byte register
                let newCcr = int16 (x.DataRegister reg &&& 0xA71F)
                printfn "move D%u,sr" reg
                {x.WithSR newCcr with PC = x.PC + 2}
            elif mode = 0x3 then //(An)+
                let reg = byte register
                let addr = x.AddressRegister reg
                let newCcr = int16 (x.MMU.ReadWord(uint32 addr) &&& 0xA71F)
                //Post-increment BEFORE the privilege switch: for MOVE (A7)+,SR the bump must land
                //on the stack we actually popped from (the pre-switch A7), leaving the other
                //stack pointer untouched. WithSR then swaps A7/USP/SSP from that bumped state.
                let bumped = x.WithAddressRegister reg (addr + 2)
                let newCpu = {bumped.WithSR newCcr with PC = x.PC + 2}
                printfn "move (a%u)+,sr" reg
                newCpu
            elif mode = 0x7 && register = 0b001 then //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let newCcr = int16 (x.MMU.ReadWord addr &&& 0xA71F)
                printfn "move $%x.l,sr" addr
                {x.WithSR newCcr with PC = x.PC + 6}
            else
                failwithf "mode %A, register %A not implemented for move2sr" mode register
        | MoveFromSR(eamode, eareg) ->
            match eamode with
            | 0b000uy -> //Dn
                let currentValue = x.DataRegister eareg
                let newValue = (currentValue &&& ~~~0xffff) ||| (int x.CCR &&& 0xffff)
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2}
                printfn "move sr,D%u" eareg
                newCpu
            | 0b100uy -> //-(An)
                let newAddr = x.AddressRegister eareg - 2
                x.MMU.WriteWord (uint32 newAddr) x.CCR
                let newCpu = {x.WithAddressRegister eareg newAddr with PC = x.PC+2}
                printfn "move sr,-(a%u)" eareg
                newCpu
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                x.MMU.WriteWord addr x.CCR
                let newCpu = {x with PC = x.PC+6}
                printfn "move sr,$%x.l" addr
                newCpu
            | _ -> failwithf "move sr not implemented for eamode %x" eamode

        | Reset ->
            if x.S then printfn "reset"
                //Asserted for 124 cycles
            else printfn "TRAP: Not supervisor"
            {x with PC = x.PC + 2}
        | NOP ->
            printfn "nop"
            {x with PC = x.PC + 2}
        | CHK(dn, eamode, eareg) ->
            //CHK.W <ea>,Dn: trap to vector 6 if Dn.w < 0 or Dn.w > <ea>.w. Flags (matching MAME's
            //68000 core): Z = (Dn.w == 0) always, V = C = 0 always, X untouched; N is left alone
            //when in range, else set to (Dn.w < 0). The stacked PC is the address of the next
            //instruction (CHK completes before trapping).
            let src = int (int16 (x.DataRegister dn))
            let ext () = x.MMU.ReadWord (uint32 (x.PC + 2))
            let bound, afterEA =
                match eamode with
                | 0b000uy -> int (int16 (x.DataRegister eareg)), { x with PC = x.PC + 2 }
                | 0b010uy -> int (int16 (x.MMU.ReadWord (uint32 (x.AddressRegister eareg)))), { x with PC = x.PC + 2 }
                | 0b011uy ->
                    let a = x.AddressRegister eareg
                    int (int16 (x.MMU.ReadWord (uint32 a))), { x.WithAddressRegister eareg (a + 2) with PC = x.PC + 2 }
                | 0b100uy ->
                    let a = x.AddressRegister eareg - 2
                    int (int16 (x.MMU.ReadWord (uint32 a))), { x.WithAddressRegister eareg a with PC = x.PC + 2 }
                | 0b101uy ->
                    let a = x.AddressRegister eareg + int (int16 (ext ()))
                    int (int16 (x.MMU.ReadWord (uint32 a))), { x with PC = x.PC + 4 }
                | 0b110uy ->
                    let idx = x.DecodeBriefExtension (int (ext ()))
                    int (int16 (x.MMU.ReadWord (uint32 (x.AddressRegister eareg + idx.Offset)))), { x with PC = x.PC + 4 }
                | 0b111uy when eareg = 0b000uy -> //(xxx).W
                    int (int16 (x.MMU.ReadWord (uint32 (int (int16 (ext ())))))), { x with PC = x.PC + 4 }
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    int (int16 (x.MMU.ReadWord (uint32 (x.MMU.ReadLong (uint32 (x.PC + 2)))))), { x with PC = x.PC + 6 }
                | 0b111uy when eareg = 0b010uy -> //(d16,PC)
                    let a = (x.PC + 2) + int (int16 (ext ()))
                    int (int16 (x.MMU.ReadWord (uint32 a))), { x with PC = x.PC + 4 }
                | 0b111uy when eareg = 0b011uy -> //(d8,PC,Xn)
                    let idx = x.DecodeBriefExtension (int (ext ()))
                    int (int16 (x.MMU.ReadWord (uint32 ((x.PC + 2) + idx.Offset)))), { x with PC = x.PC + 4 }
                | 0b111uy when eareg = 0b100uy -> //#imm.w
                    int (int16 (ext ())), { x with PC = x.PC + 4 }
                | _ -> failwithf "chk.w not implemented for eamode %x reg %x" eamode eareg
            let z16 = (src &&& 0xFFFF) = 0
            let ccr0 =
                let c = if z16 then afterEA.CCR ||| 0x4s else afterEA.CCR &&& ~~~0x4s
                c &&& ~~~0x3s  // V = C = 0
            printfn "chk.w <ea mode %x reg %x>,D%u" eamode eareg dn
            if src >= 0 && src <= bound then
                { afterEA with CCR = ccr0 }
            else
                let ccrTrap = if src < 0 then ccr0 ||| 0x8s else ccr0 &&& ~~~0x8s
                ({ afterEA with CCR = ccrTrap }).EnterVector 6 afterEA.PC
        | LEA(a_reg, eamode,eareg) ->
            match eamode with
            | 0b010uy -> //(An)
                let addr = x.AddressRegister eareg
                let newCpu = {x.WithAddressRegister a_reg addr with PC = x.PC+2}
                printfn "lea (a%u),a%i" eareg a_reg
                newCpu
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let newCpu = {x.WithAddressRegister a_reg addr with PC = x.PC+4}
                printfn "lea %i(a%u),a%i" displacement eareg a_reg
                newCpu
            | 0b110uy -> //(d8,An,Xn)
                let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + ext.Offset
                let newCpu = {x.WithAddressRegister a_reg addr with PC = x.PC+4}
                printfn "lea %s,a%i" (x.DescribeIndexed eareg ext) a_reg
                newCpu
            | 0b111uy ->
                match eareg with
                | 0b000uy -> failwith "not implemented" //(xxx).W
                | 0b001uy -> //(xxx).L
                    //load the next long into a_reg
                    let addr = x.MMU.ReadLong(uint32 (x.PC+2))
                    let newCpu = {x.WithAddressRegister a_reg addr with PC = x.PC+6}
                    printfn "lea %x, A%i" addr a_reg
                    newCpu

                | 0b010uy -> //(d16,PC)
                    let displacedPC =
                        let disp = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        (x.PC+2) + int disp
                    let newCpu = {x.WithAddressRegister a_reg displacedPC with PC = x.PC + 4}
                    printfn "lea $%x,a%i" displacedPC a_reg
                    newCpu
                    
                | 0b011uy -> failwith "not implemented" //(d8,PC,Xn)
                | _ -> failwithf "unknown Register %x for mode %x" eareg eamode
            | _ -> failwithf "lea: unknown mode %x" eamode

        | NEGX(size, eamode, eareg) ->
            //Negate with extend: dest = 0 - dest - X. CCR: N/V from the result, C+X set on borrow
            //(which happens unless both the operand and X are 0), and Z is only ever *cleared*
            //(left unchanged when the result is 0) so it accumulates across a multi-word negate.
            let xin = if x.X then 1 else 0
            let oldZ = x.CCR &&& 0x4s
            let opBits = match size with 0b00uy -> 8 | 0b01uy -> 16 | _ -> 32
            let signBit = 1 <<< (opBits - 1)
            let mask = if opBits = 32 then -1 else (1 <<< opBits) - 1
            let sz = match size with 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | 0b10uy -> OperandSize.Long | _ -> failwithf "negx: bad size %x" size
            let loc, extBytes, desc, regUpdate = x.ResolveEa sz eamode eareg (x.PC + 2)
            let src = x.ReadEa sz loc
            let result = (0 - src - xin) &&& mask
            let borrow = (src &&& mask) <> 0 || x.X
            let mutable ccr = x.CCR &&& ~~~0xFs
            if result &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
            if result <> 0 then ccr <- ccr &&& ~~~0x4s else ccr <- ccr ||| oldZ //Z: clear on nonzero, else keep
            if (src &&& signBit <> 0) && (result &&& signBit <> 0) then ccr <- ccr ||| 0x2s //V
            if borrow then ccr <- ccr ||| 0x1s ||| 0x10s else ccr <- ccr &&& ~~~0x10s //C and X=C
            let newCpu = { x.WriteEa sz loc result (regUpdate x) with PC = x.PC + 2 + extBytes; CCR = ccr }
            printfn "negx.%s %s" (match sz with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l") desc
            newCpu

        | NEG(size, eamode, eareg) ->
            //Two's complement negation (0 - operand). Reuses the existing Subtract_* helpers for
            //N/Z/V/C (dest=0); those already fold C into X, and NEG wants X=C, so no extra work.
            //Migrated to the shared EA decoder - one path covers Dn and every alterable memory mode.
            let sz = match size with 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | 0b10uy -> OperandSize.Long | _ -> failwithf "neg: bad size %x" size
            let loc, extBytes, desc, regUpdate = x.ResolveEa sz eamode eareg (x.PC + 2)
            let raw = x.ReadEa sz loc
            let result, ccr =
                match sz with
                | OperandSize.Byte -> let s = byte raw in int (byte (0 - int s)), CCR.Subtract_Byte x.CCR 0uy s
                | OperandSize.Word -> let s = int16 raw in (int (int16 (0 - int s)) &&& 0xffff), CCR.Subtract_Word x.CCR 0s s
                | _ -> let s = raw in (0 - s), CCR.Subtract x.CCR 0 s
            let ccr = if ccr &&& 0x1s <> 0s then ccr ||| 0x10s else ccr &&& ~~~0x10s
            let newCpu = { x.WriteEa sz loc result (regUpdate x) with PC = x.PC + 2 + extBytes; CCR = ccr }
            printfn "neg.%s %s" (match sz with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l") desc
            newCpu

        | NOT(size, eamode, eareg) ->
            //One's complement. CCR: N/Z from result, V/C cleared, X unaffected. Migrated to the
            //shared EA decoder (one path for Dn and every alterable memory mode).
            let sz = match size with 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | 0b10uy -> OperandSize.Long | _ -> failwithf "not: bad size %x" size
            let loc, extBytes, desc, regUpdate = x.ResolveEa sz eamode eareg (x.PC + 2)
            let raw = x.ReadEa sz loc
            let result, ccr =
                match sz with
                | OperandSize.Byte -> let r = ~~~(byte raw) in int r, CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR r
                | OperandSize.Word -> let r = ~~~(int16 raw) in (int r &&& 0xffff), CCR.IgnoreX_ZeroV_And_ZeroC x.CCR r
                | _ -> let r = ~~~raw in r, CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR r
            let newCpu = { x.WriteEa sz loc result (regUpdate x) with PC = x.PC + 2 + extBytes; CCR = ccr }
            printfn "not.%s %s" (match sz with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l") desc
            newCpu

        | CLR(size, eamode, eareg) ->
            //CLR: writes 0 to the destination, sets Z, clears N/V/C, leaves X. Migrated to the
            //shared EA decoder. (The real 68000 also performs a dummy read first; we don't model
            //that read - it is only observable as an odd-address fault, which the write raises too.)
            let sz = match size with 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | 0b10uy -> OperandSize.Long | _ -> failwithf "clr: bad size %x" size
            let loc, extBytes, desc, regUpdate = x.ResolveEa sz eamode eareg (x.PC + 2)
            let ccr =
                match sz with
                | OperandSize.Byte -> CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR 0uy
                | OperandSize.Word -> CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                | _ -> CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
            let written = x.WriteEa sz loc 0 (regUpdate x)
            let newCpu = { written with PC = x.PC + 2 + extBytes; CCR = ccr }
            printfn "clr.%s %s" (match sz with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l") desc
            newCpu

        | TAS(eamode, eareg) ->
            //TAS: byte-only atomic test-and-set. Read the operand byte, set N/Z from it (V/C
            //cleared, X untouched - same as TST), then write it back with bit 7 forced to 1.
            let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Byte eamode eareg (x.PC + 2)
            let value = byte (x.ReadEa OperandSize.Byte loc)
            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR value
            let written = x.WriteEa OperandSize.Byte loc (int (value ||| 0x80uy)) (regUpdate x)
            let newCpu = { written with PC = x.PC + 2 + extBytes; CCR = ccr }
            printfn "tas %s" desc
            newCpu

        | TST(size, eamode, eareg) ->
            //TST: sets N/Z from the operand, clears V/C, X unaffected. CCR-only, no write-back.
            //Migrated to the shared EA decoder (x.ResolveEa / x.ReadEa) - one path covers every
            //classic 68000 mode plus (xxx).W, which the old hand-rolled ladder was missing.
            let sz = match size with 0b00uy -> OperandSize.Byte | 0b01uy -> OperandSize.Word | 0b10uy -> OperandSize.Long | _ -> failwithf "tst: bad size %x" size
            let loc, extBytes, desc, regUpdate = x.ResolveEa sz eamode eareg (x.PC + 2)
            let raw = x.ReadEa sz loc
            let ccr =
                match sz with
                | OperandSize.Byte -> CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte raw)
                | OperandSize.Word -> CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 raw)
                | _ -> CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR raw
            let newCpu = { regUpdate x with PC = x.PC + 2 + extBytes; CCR = ccr }
            printfn "tst.%s %s" (match sz with OperandSize.Byte -> "b" | OperandSize.Word -> "w" | _ -> "l") desc
            newCpu

        | MOVEM(direction, size, eamode, eareg) ->
            let mask = uint16 (x.MMU.ReadWord(uint32 (x.PC+2)))
            match direction, size, eamode with
            | 0uy, 1uy, 0b100uy -> //MOVEM.L reglist,-(An)
                let mutable addr = x.AddressRegister eareg
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        addr <- addr - 4
                        let value =
                            if bit < 8 then x.AddressRegister (byte (7 - bit))
                            else x.DataRegister (byte (15 - bit))
                        x.MMU.WriteLong (uint32 addr) value
                let newCpu = {x.WithAddressRegister eareg addr with PC = x.PC+4}
                printfn "movem.l #$%04x,-(a%u)" mask eareg
                newCpu
            | 0uy, 0uy, 0b100uy -> //MOVEM.W reglist,-(An)
                let mutable addr = x.AddressRegister eareg
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        addr <- addr - 2
                        let value =
                            if bit < 8 then x.AddressRegister (byte (7 - bit))
                            else x.DataRegister (byte (15 - bit))
                        x.MMU.WriteWord (uint32 addr) (int16 value)
                let newCpu = {x.WithAddressRegister eareg addr with PC = x.PC+4}
                printfn "movem.w #$%04x,-(a%u)" mask eareg
                newCpu
            | 0uy, 1uy, 0b101uy -> //MOVEM.L reglist,(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                let mutable addr = x.AddressRegister eareg + int displacement
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value =
                            if bit < 8 then x.DataRegister (byte bit)
                            else x.AddressRegister (byte (bit - 8))
                        x.MMU.WriteLong (uint32 addr) value
                        addr <- addr + 4
                let newCpu = {x with PC = x.PC+6}
                printfn "movem.l #$%04x,%i(a%u)" mask displacement eareg
                newCpu
            | 1uy, 1uy, 0b101uy -> //MOVEM.L (d16,An),reglist
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                let mutable addr = x.AddressRegister eareg + int displacement
                let mutable cpu = x
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value = x.MMU.ReadLong(uint32 addr)
                        cpu <-
                            if bit < 8 then cpu.WithDataRegister (byte bit) value
                            else cpu.WithAddressRegister (byte (bit - 8)) value
                        addr <- addr + 4
                let newCpu = {cpu with PC = x.PC+6}
                printfn "movem.l %i(a%u),#$%04x" displacement eareg mask
                newCpu
            | 1uy, 1uy, 0b011uy -> //MOVEM.L (An)+,reglist
                let mutable addr = x.AddressRegister eareg
                let mutable cpu = x
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value = x.MMU.ReadLong(uint32 addr)
                        cpu <-
                            if bit < 8 then cpu.WithDataRegister (byte bit) value
                            else cpu.WithAddressRegister (byte (bit - 8)) value
                        addr <- addr + 4
                let newCpu = {cpu.WithAddressRegister eareg addr with PC = x.PC+4}
                printfn "movem.l (a%u)+,#$%04x" eareg mask
                newCpu
            | 1uy, 0uy, 0b011uy -> //MOVEM.W (An)+,reglist - each word sign-extends to fill its register
                let mutable addr = x.AddressRegister eareg
                let mutable cpu = x
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value = int (int16 (x.MMU.ReadWord(uint32 addr)))
                        cpu <-
                            if bit < 8 then cpu.WithDataRegister (byte bit) value
                            else cpu.WithAddressRegister (byte (bit - 8)) value
                        addr <- addr + 2
                let newCpu = {cpu.WithAddressRegister eareg addr with PC = x.PC+4}
                printfn "movem.w (a%u)+,#$%04x" eareg mask
                newCpu
            | 0uy, 1uy, 0b111uy when eareg = 0b001uy -> //MOVEM.L reglist,(xxx).L
                let target = x.MMU.ReadLong(uint32 (x.PC+4))
                let mutable addr = uint32 target
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value =
                            if bit < 8 then x.DataRegister (byte bit)
                            else x.AddressRegister (byte (bit - 8))
                        x.MMU.WriteLong addr value
                        addr <- addr + 4u
                let newCpu = {x with PC = x.PC+8}
                printfn "movem.l #$%04x,$%x.l" mask target
                newCpu
            | 1uy, 1uy, 0b111uy when eareg = 0b001uy -> //MOVEM.L (xxx).L,reglist
                let source = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                let mutable addr = source
                let mutable cpu = x
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value = x.MMU.ReadLong(uint32 addr)
                        cpu <-
                            if bit < 8 then cpu.WithDataRegister (byte bit) value
                            else cpu.WithAddressRegister (byte (bit - 8)) value
                        addr <- addr + 4u
                let newCpu = {cpu with PC = x.PC+8}
                printfn "movem.l $%x.l,#$%04x" source mask
                newCpu
            | 1uy, 1uy, 0b111uy when eareg = 0b010uy -> //MOVEM.L (d16,PC),reglist
                //PC-relative displacement is relative to the address of the extension word itself
                //(PC+4: PC+2 holds the register mask, PC+4 holds the displacement) - see LEA's
                //(d16,PC) case above for the same convention.
                let extAddr = x.PC + 4
                let displacement = int16 (x.MMU.ReadWord(uint32 extAddr))
                let source = uint32 (extAddr + int displacement)
                let mutable addr = source
                let mutable cpu = x
                for bit in 0 .. 15 do
                    if (mask >>> bit) &&& 1us = 1us then
                        let value = x.MMU.ReadLong(uint32 addr)
                        cpu <-
                            if bit < 8 then cpu.WithDataRegister (byte bit) value
                            else cpu.WithAddressRegister (byte (bit - 8)) value
                        addr <- addr + 4u
                let newCpu = {cpu with PC = x.PC+6}
                printfn "movem.l %d(pc),#$%04x == $%x" displacement mask source
                newCpu
            | _ -> failwithf "movem: not implemented for direction %x size %x mode %x" direction size eamode

        | EXT(size, register) ->
            //EXT: sign-extends the low half of Dn into the high half, in place. N/Z set from the
            //result, V/C cleared, X unaffected.
            match size with
            | 0uy -> //EXT.W: byte -> word
                let current = x.DataRegister register
                let extended = int16 (sbyte current)
                let newValue = (current &&& ~~~0xffff) ||| (int extended &&& 0xffff)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR extended
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                printfn "ext.w D%u" register
                newCpu
            | _ -> //EXT.L: word -> long
                let current = x.DataRegister register
                let extended = int (int16 current)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR extended
                let newCpu = {x.WithDataRegister register extended with PC = x.PC+2; CCR = ccr}
                printfn "ext.l D%u" register
                newCpu

        | SWAP register ->
            //SWAP: exchanges the two 16-bit halves of Dn. N/Z set from the 32-bit result, V/C
            //cleared, X unaffected.
            let current = x.DataRegister register
            let swapped = (current <<< 16) ||| ((current >>> 16) &&& 0xffff)
            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR swapped
            let newCpu = {x.WithDataRegister register swapped with PC = x.PC+2; CCR = ccr}
            printfn "swap D%u" register
            newCpu

        | PEA(eamode, eareg) ->
            //PEA: pushes the effective address itself (not its contents) onto the stack. CCR unaffected.
            //Only the control addressing modes are legal here, so the shared EA decoder always
            //resolves to an EaMem address - push that, no operand read. `extBytes` carries the PC
            //advance for whichever mode's extension words were consumed.
            let loc, extBytes, desc, _ = x.ResolveEa OperandSize.Long eamode eareg (x.PC + 2)
            match loc with
            | EaMem addr ->
                let newSP = x.A7 - 4
                x.MMU.WriteLong (uint32 newSP) (int addr)
                printfn "pea %s == $%x" desc addr
                {x with PC = x.PC + 2 + extBytes; A7 = newSP}
            | _ -> failwithf "pea: illegal addressing mode %x/%x" eamode eareg

        | RTS ->
            let returnAddr = x.MMU.ReadLong(uint32 x.A7)
            let newCpu = {x with PC = returnAddr; A7 = x.A7 + 4}
            printfn "rts"
            newCpu

        | RTE ->
            //Inverse of TRAP's push order: SR at [A7], PC(long) at [A7+2], SP += 6. RTE only ever
            //executes in supervisor mode, so x.A7 here is always the supervisor stack; the popped
            //SR's own S-bit decides whether we're staying supervisor (nested trap returning to
            //another supervisor context - no stack swap, just keep using the now-popped pointer)
            //or dropping back to user mode (swap A7 over to USP, and park the popped supervisor
            //pointer in SSP for whenever a later trap re-enters supervisor mode).
            //Mask to the implemented SR bits (T, S, I2-I0, CCR); the unused ones read back as 0.
            let sr = int16 (x.MMU.ReadWord(uint32 x.A7) &&& 0xA71F)
            let pc = x.MMU.ReadLong(uint32 (x.A7+2))
            let poppedCpu = {x with A7 = x.A7 + 6}
            let newCpu = {poppedCpu.WithSR sr with PC = pc}
            printfn "rte"
            newCpu

        | RTR ->
            //Pop the condition codes (low byte of a word; only bits 0-4 are implemented, the rest
            //read 0) then the return PC (long); SP += 6. The system byte of SR is left untouched -
            //RTR restores CCR only, not privilege/mask/trace.
            let poppedCcr = int16 (x.MMU.ReadWord(uint32 x.A7) &&& 0x1f)
            let pc = x.MMU.ReadLong(uint32 (x.A7+2))
            let newCcr = (x.CCR &&& ~~~0x1fs) ||| poppedCcr
            printfn "rtr"
            {x with A7 = x.A7 + 6; PC = pc; CCR = newCcr}

        | TRAPV ->
            //Trap to vector 7 when V is set, otherwise fall through. The stacked return PC is the
            //instruction after TRAPV (a completed instruction, unlike an address error).
            if x.CCR &&& 0x2s <> 0s then
                printfn "trapv (taken)"
                x.EnterVector 7 (x.PC+2)
            else
                printfn "trapv (not taken)"
                {x with PC = x.PC+2}

        | TRAP(vector) ->
            //Pushes return PC then SR (SR ends up on top, matching RTE's SR@SP/PC@SP+2 layout),
            //enters supervisor mode, and jumps to the vector table entry at (32+n)*4 - see
            //EnterVector's comment for why the privilege swap has to happen before the push
            //(GEMDOS's trap#1 handler's `move usp,An` depends on it).
            if Diag.traceGemdos && vector = 1uy then
                let func = x.MMU.ReadWord(uint32 x.A7)
                eprintfn "GEMDOS_CALL pc=$%08x func=$%04x" x.PC (uint16 func)
            let newCpu = x.EnterVector (32 + int vector) (x.PC+2)
            printfn "trap #%u" vector
            newCpu

        | MoveUsp(direction, register) ->
            if direction = 0uy then //MOVE An,USP
                let newCpu = {x with USP = x.AddressRegister register; PC = x.PC+2}
                printfn "move A%u,usp" register
                newCpu
            else //MOVE USP,An
                let newCpu = {x.WithAddressRegister register x.USP with PC = x.PC+2}
                printfn "move usp,A%u" register
                newCpu

        | LINK(register) ->
            //Push An, then An = (new, post-push) SP, then SP += sign-extended displacement.
            let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
            let newSP = x.A7 - 4
            //The SP pre-decrement happens before An is read, so LINK A7 pushes the already
            //decremented SP, not the entry value.
            let pushed = if register = 0b111uy then newSP else x.AddressRegister register
            x.MMU.WriteLong (uint32 newSP) pushed
            let newCpu = (x.WithAddressRegister register newSP).WithAddressRegister 0b111uy (newSP + int displacement)
            let newCpu = {newCpu with PC = x.PC+4}
            printfn "link A%u,#%d" register displacement
            newCpu

        | UNLK(register) ->
            //SP = An, then pop long back into An.
            let addr = x.AddressRegister register
            let restored = x.MMU.ReadLong(uint32 addr)
            let newCpu = (x.WithAddressRegister 0b111uy (addr+4)).WithAddressRegister register restored
            let newCpu = {newCpu with PC = x.PC+2}
            printfn "unlk A%u" register
            newCpu

        | JSR(eamode, eareg) ->
            match eamode with
            | 0b010uy -> //(An)
                let target = x.AddressRegister eareg
                let returnAddr = x.PC + 2
                let newSP = x.A7 - 4
                x.MMU.WriteLong (uint32 newSP) returnAddr
                printfn "jsr (a%u)" eareg
                {x with PC = target; A7 = newSP}
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let target = x.MMU.ReadLong(uint32 (x.PC+2))
                let returnAddr = x.PC + 6
                let newSP = x.A7 - 4
                x.MMU.WriteLong (uint32 newSP) returnAddr
                printfn "jsr $%x.l" target
                {x with PC = target; A7 = newSP}
            | 0b110uy -> //(d8,An,Xn)
                let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                let target = x.AddressRegister eareg + ext.Offset
                let returnAddr = x.PC + 4
                let newSP = x.A7 - 4
                x.MMU.WriteLong (uint32 newSP) returnAddr
                printfn "jsr %s" (x.DescribeIndexed eareg ext)
                {x with PC = target; A7 = newSP}
            | _ -> failwithf "JSR not implemented for eamode %u reg %u" eamode eareg

        | JMP(eamode, eareg) ->
            match eamode with
            | 0b010uy ->
                let jump = x.AddressRegister eareg
                let newCpu = {x with PC = jump}
                printfn "jmp.l A%u" eareg
                newCpu
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let jump = x.MMU.ReadLong(uint32 (x.PC+2))
                let newCpu = {x with PC = jump}
                printfn "jmp $%x.l" jump
                newCpu
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let jump = x.AddressRegister eareg + int displacement
                let newCpu = {x with PC = jump}
                printfn "jmp %i(a%u)" displacement eareg
                newCpu
            | _ -> failwithf "JMP not implemented for mode %u reg %u" eamode eareg
        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket5 (instruction: int) : Cpu =
        match instruction with
        | ADDQ(quickData, size, eamode, eareg) ->
            let amount = if quickData = 0uy then 8 else int quickData
            match eamode with
            | 0b001uy -> //An - always a 32-bit add, CCR unaffected (like ADDA)
                let dest = x.AddressRegister eareg
                let result = dest + amount
                let newCpu = {x.WithAddressRegister eareg result with PC = x.PC+2}
                printfn "addq.%s #%u,A%u" (match size with 0uy -> "b" | 1uy -> "w" | _ -> "l") amount eareg
                newCpu
            | 0b000uy -> //Dn
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.DataRegister eareg)
                    let result = dest + int16 amount
                    let ccr = CCR.Add_Word x.CCR dest (int16 amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "addq.w #%u,D%u" amount eareg
                    newCpu
                | 0b00uy -> //byte
                    let dest = byte (x.DataRegister eareg)
                    let result = dest + byte amount
                    let ccr = CCR.Add_Byte x.CCR dest (byte amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xff) ||| int result
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "addq.b #%u,D%u" amount eareg
                    newCpu
                | _ -> //long
                    let dest = x.DataRegister eareg
                    let result = dest + amount
                    let ccr = CCR.Add x.CCR dest amount
                    let newCpu = {x.WithDataRegister eareg result with PC = x.PC+2; CCR = ccr}
                    printfn "addq.l #%u,D%u" amount eareg
                    newCpu
            | 0b010uy -> //(An)
                let addr = x.AddressRegister eareg
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = dest + int16 amount
                    let ccr = CCR.Add_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord (uint32 addr) result
                    printfn "addq.w #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let result = dest + byte amount
                    let ccr = CCR.Add_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte (uint32 addr) result
                    printfn "addq.b #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let result = dest + amount
                    let ccr = CCR.Add x.CCR dest amount
                    x.MMU.WriteLong (uint32 addr) result
                    printfn "addq.l #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = dest + int16 amount
                    let ccr = CCR.Add_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord (uint32 addr) result
                    printfn "addq.w #%u,%i(a%u)" amount displacement eareg
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let result = dest + byte amount
                    let ccr = CCR.Add_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte (uint32 addr) result
                    printfn "addq.b #%u,%i(a%u)" amount displacement eareg
                    {x with PC = x.PC+4; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let result = dest + amount
                    let ccr = CCR.Add x.CCR dest amount
                    x.MMU.WriteLong (uint32 addr) result
                    printfn "addq.l #%u,%i(a%u)" amount displacement eareg
                    {x with PC = x.PC+4; CCR = ccr}
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + int16 amount
                    let ccr = CCR.Add_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord addr result
                    printfn "addq.w #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte addr
                    let result = dest + byte amount
                    let ccr = CCR.Add_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte addr result
                    printfn "addq.b #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong addr
                    let result = dest + amount
                    let ccr = CCR.Add x.CCR dest amount
                    x.MMU.WriteLong addr result
                    printfn "addq.l #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
            | _ -> failwithf "addq not implemented for eamode %x" eamode

        | SUBQ(quickData, size, eamode, eareg) ->
            let amount = if quickData = 0uy then 8 else int quickData
            match eamode with
            | 0b001uy -> //An - always a 32-bit subtract, CCR unaffected (like SUBA)
                let dest = x.AddressRegister eareg
                let result = dest - amount
                let newCpu = {x.WithAddressRegister eareg result with PC = x.PC+2}
                printfn "subq.%s #%u,A%u" (match size with 0uy -> "b" | 1uy -> "w" | _ -> "l") amount eareg
                newCpu
            | 0b000uy -> //Dn
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.DataRegister eareg)
                    let result = dest - int16 amount
                    let ccr = CCR.Subtract_Word x.CCR dest (int16 amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "subq.w #%u,D%u" amount eareg
                    newCpu
                | 0b00uy -> //byte
                    let dest = byte (x.DataRegister eareg)
                    let result = dest - byte amount
                    let ccr = CCR.Subtract_Byte x.CCR dest (byte amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xff) ||| int result
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "subq.b #%u,D%u" amount eareg
                    newCpu
                | 0b10uy -> //long
                    let dest = x.DataRegister eareg
                    let result = dest - amount
                    let ccr = CCR.Subtract x.CCR dest amount
                    let newCpu = {x.WithDataRegister eareg result with PC = x.PC+2; CCR = ccr}
                    printfn "subq.l #%u,D%u" amount eareg
                    newCpu
                | _ -> failwithf "subq not implemented for size %x on Dn" size
            | 0b010uy -> //(An)
                let addr = x.AddressRegister eareg
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = dest - int16 amount
                    let ccr = CCR.Subtract_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord (uint32 addr) result
                    printfn "subq.w #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let result = dest - byte amount
                    let ccr = CCR.Subtract_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte (uint32 addr) result
                    printfn "subq.b #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let result = dest - amount
                    let ccr = CCR.Subtract x.CCR dest amount
                    x.MMU.WriteLong (uint32 addr) result
                    printfn "subq.l #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
            | 0b101uy -> //(d16,An)
                match size with
                | 0b01uy -> //word
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - int16 amount
                    let ccr = CCR.Subtract_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "subq.w #%u,%i(a%u)" amount displacement eareg
                    newCpu
                | 0b10uy -> //long
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = x.MMU.ReadLong addr
                    let result = dest - amount
                    let ccr = CCR.Subtract x.CCR dest amount
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "subq.l #%u,%i(a%u)" amount displacement eareg
                    newCpu
                | _ -> //byte
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = x.MMU.ReadByte addr
                    let result = dest - byte amount
                    let ccr = CCR.Subtract_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "subq.b #%u,%i(a%u)" amount displacement eareg
                    newCpu
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - int16 amount
                    let ccr = CCR.Subtract_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord addr result
                    printfn "subq.w #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte addr
                    let result = dest - byte amount
                    let ccr = CCR.Subtract_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte addr result
                    printfn "subq.b #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong addr
                    let result = dest - amount
                    let ccr = CCR.Subtract x.CCR dest amount
                    x.MMU.WriteLong addr result
                    printfn "subq.l #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
            | _ -> failwithf "subq not implemented for eamode %x" eamode

        | Scc(cond, eamode, eareg) ->
            //Scc: sets the byte at <ea> to $FF if cond is true, $00 otherwise. CCR unaffected.
            //Byte-only, alterable modes; migrated to the shared EA decoder.
            let value = if x.EvaluateCondition cond then 0xff else 0x00
            let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Byte eamode eareg (x.PC + 2)
            let newCpu = { x.WriteEa OperandSize.Byte loc value (regUpdate x) with PC = x.PC + 2 + extBytes }
            printfn "s%s %s" (conditionName cond) desc
            newCpu

        | DBcc(cond, register) ->
            if x.EvaluateCondition cond then
                {x with PC = x.PC + 4}
            else
                let currentValue = x.DataRegister register
                let newLowWord = int16 currentValue - 1s
                let newValue = (currentValue &&& ~~~0xffff) ||| (int (uint16 newLowWord))
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let branch = newLowWord <> -1s
                let newPC = if branch then x.PC + 2 + int displacement else x.PC + 4
                let newCpu = {x.WithDataRegister register newValue with PC = newPC}
                printfn "db%s D%u,$%x" (conditionName cond) register newPC
                newCpu

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket6 (instruction: int) : Cpu =
        match instruction with
        | BCC(cond, disp) ->
            //Note: condition F within Bcc's encoding is BSR (subroutine call), not "never branch" -
            //it must not fall through to the generic condition evaluator below.
            match cond with
            | Condition.F -> //BSR
                let newSP = x.A7 - 4
                match disp with
                | 0x00uy ->
                    let wordDisp = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let returnAddr = x.PC + 4
                    x.MMU.WriteLong (uint32 newSP) returnAddr
                    let newPC = (x.PC+2) + int wordDisp
                    printfn "bsr.w $%x" newPC
                    {x with PC = newPC; A7 = newSP}
                | 0xFFuy -> failwith "Not yet supprted" //32-bit displacement (68020+)
                | byteDisp ->
                    let returnAddr = x.PC + 2
                    x.MMU.WriteLong (uint32 newSP) returnAddr
                    let newPC = (x.PC+2) + int (sbyte byteDisp)
                    printfn "bsr.s $%x" newPC
                    {x with PC = newPC; A7 = newSP}
            | _ ->
                let takeBranch = x.EvaluateCondition cond
                match disp with
                | 0x00uy ->
                    let wordDisp = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let newPC = if takeBranch then (x.PC+2) + int wordDisp else x.PC + 4
                    printfn "b%s.w $%x (%b)" (conditionName cond) newPC takeBranch
                    {x with PC = newPC}
                | 0xFFuy -> failwith "Not yet supprted" //32-bit displacement (68020+)
                | byteDisp ->
                    let newPC = if takeBranch then (x.PC+2) + int (sbyte byteDisp) else x.PC + 2
                    printfn "b%s.s $%x (%b)" (conditionName cond) newPC takeBranch
                    {x with PC = newPC}
        
        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket7 (instruction: int) : Cpu =
        match instruction with
        | MOVEQ(register, data) ->
            let value = int data
            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
            let newCpu = {x.WithDataRegister register value with PC = x.PC+2; CCR = ccr}
            printfn "moveq #$%x,D%u" value register
            newCpu

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket8 (instruction: int) : Cpu =
        match instruction with
        | DIVU(register, eamode, eareg) ->
            //Word divisor from any data-addressing mode (not An direct); dividend is the full 32-bit
            //Dn. Source EA resolved through the shared decoder - `regUpdate` carries the (An)+/-(An)
            //writeback, `extBytes` the PC advance past the extension words.
            let doDivide (divisor: uint32) (regUpdate: Cpu -> Cpu) extBytes desc =
                if divisor = 0u then failwith "DIVU: divide by zero (trap not implemented)"
                let dividend = uint32 (x.DataRegister register)
                let quotient = dividend / divisor
                let remainder = dividend % divisor
                if quotient > 0xffffu then failwith "DIVU: quotient overflow (V flag not implemented)"
                let result = int ((remainder <<< 16) ||| quotient)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 quotient)
                let newCpu = {(regUpdate x).WithDataRegister register result with PC = x.PC + 2 + extBytes; CCR = ccr}
                printfn "divu.w %s,D%u" desc register
                newCpu
            let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Word eamode eareg (x.PC + 2)
            doDivide (uint32 (uint16 (x.ReadEa OperandSize.Word loc))) regUpdate extBytes desc

        | DIVS(register, eamode, eareg) ->
            //Truncating division/remainder (F#'s / and % on signed ints truncate toward zero) is
            //exactly real 68000 DIVS.W semantics: quotient truncates toward zero, remainder takes
            //the dividend's sign - so no extra sign-fixup is needed beyond what DIVU already does.
            let doDivide (divisor: int16) (regUpdate: Cpu -> Cpu) extBytes desc =
                if divisor = 0s then failwith "DIVS: divide by zero (trap not implemented)"
                let dividend = x.DataRegister register
                let quotient = dividend / int divisor
                let remainder = dividend % int divisor
                if quotient > 32767 || quotient < -32768 then failwith "DIVS: quotient overflow (V flag not implemented)"
                let result = ((remainder &&& 0xffff) <<< 16) ||| (quotient &&& 0xffff)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 quotient)
                let newCpu = {(regUpdate x).WithDataRegister register result with PC = x.PC + 2 + extBytes; CCR = ccr}
                printfn "divs.w %s,D%u" desc register
                newCpu
            let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Word eamode eareg (x.PC + 2)
            doDivide (int16 (x.ReadEa OperandSize.Word loc)) regUpdate extBytes desc

        | OR(register, opmode, eamode, eareg) ->
            //Plain OR reg forms via the shared EA decoder. opmode 011/111 are DIVU/DIVS (their own
            //patterns, matched first). opmode 100 with eamode 000/001 is the SBCD opcode slot (no
            //handler yet) - keep the old failure rather than silently doing an OR there.
            if opmode = 0b100uy && eamode < 0b010uy then
                failwithf "or.b not implemented for eamode %x" eamode
            else
                x.RegEaOp "or" opmode register eamode eareg true
                    (fun sz dest source -> let r = dest ||| source in r, x.LogicalCcr sz r)

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket9 (instruction: int) : Cpu =
        match instruction with
        | SUBX(registerX, size, usePredecrement, registerY) ->
            //Extend-aware subtract, dest - source - X (see ExtendedArith.step for the Z quirk).
            x.ExtendedArith false size usePredecrement registerX registerY

        | SUB(address, opmode, eamode, eareg) ->
            //1001regopmEAmEAr
            //----reg
            //-------opm 
            //----------EAm
            //-------------EAr

            match opmode with
            | 0b000uy -> //SUB.B ea-Dn->Dn
                match eamode with
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = x.MMU.ReadByte(uint32 addr)
                    let dest = byte (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Subtract_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "sub.b %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b000uy -> //Dn
                    let source = byte (x.DataRegister eareg)
                    let dest = byte (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Subtract_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "sub.b D%u,D%u" eareg address
                    newCpu
                | _ -> failwithf "sub.b(ea->dn) not implemented for eamode %x" eamode
            | 0b010uy -> //SUB.L Dn-ea->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = x.DataRegister eareg
                    let dest = x.DataRegister address
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+2; CCR = ccr}
                    printfn "sub.l D%u,D%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "sub.l #$%x,D%u" source address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 addr)
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+4; CCR = ccr}
                    printfn "sub.l %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "sub.l $%x.l,D%u" addr address
                    newCpu
                | _ -> failwithf "sub.l(ea->dn) not implemented for eamode %x" eamode
            | 0b001uy -> //SUB.W ea-Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = int16 (x.DataRegister eareg)
                    let dest = int16 (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "sub.w D%u,D%u" eareg address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "sub.w %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "sub.w #$%x,D%u" source address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.MMU.ReadWord addr)
                    let dest = int16 (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+6; CCR = ccr}
                    printfn "sub.w $%x.l,D%u" addr address
                    newCpu
                | _ -> failwithf "sub.w(ea->dn) not implemented for eamode %x" eamode
            | 0b101uy -> //SUB.W Dn,<ea> (ea-Dn->ea, result written to memory)
                match eamode with
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - source
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "sub.w D%u,$%x.l" address addr
                    newCpu
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - source
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "sub.w D%u,(a%u)" address eareg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - source
                    let ccr = CCR.Subtract_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "sub.w D%u,%i(a%u)" address displacement eareg
                    newCpu
                | _ -> failwithf "sub.w(dn->ea) not implemented for eamode %x" eamode
            | 0b011uy -> //SUBA.W - operand's low word sign-extended to 32 bits, subtracted from An, no flags
                let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Word eamode eareg (x.PC + 2)
                let source = int (int16 (x.ReadEa OperandSize.Word loc))
                let afterEa = regUpdate x
                let result = afterEa.AddressRegister address - source
                let newCpu = { afterEa.WithAddressRegister address result with PC = x.PC + 2 + extBytes }
                printfn "suba.w %s,A%u" desc address
                newCpu
            | 0b110uy -> //SUB.L Dn,<ea> (ea-Dn->ea, result written to memory)
                match eamode with
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = x.DataRegister address
                    let dest = x.MMU.ReadLong addr
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "sub.l D%u,(a%u)" address eareg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = x.DataRegister address
                    let dest = x.MMU.ReadLong addr
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "sub.l D%u,%i(a%u)" address displacement eareg
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = x.DataRegister address
                    let dest = x.MMU.ReadLong addr
                    let result = dest - source
                    let ccr = CCR.Subtract x.CCR dest source
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "sub.l D%u,$%x.l" address addr
                    newCpu
                | _ -> failwithf "sub.l(dn->ea) not implemented for eamode %x" eamode
            | 0b111uy -> //long op mode
                //
                match eamode with
                | 0b000uy -> //Dn addressing mode
                    let dest = x.AddressRegister address
                    let source = x.DataRegister eareg
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "suba.l D%u,A%u" eareg address
                    newCpu
                | 0b001uy ->
                    //An addressing mode
                    let dest = x.AddressRegister address
                    let source = x.AddressRegister eareg
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "suba.%s A%u, A%u" (if opmode = 0x7uy then "l" else "w" ) address eareg
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm.L
                    let dest = x.AddressRegister address
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+6}
                    printfn "suba.l #$%x,A%u" source address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.AddressRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+6}
                    printfn "suba.l $%x.l,A%u" addr address
                    newCpu
                | _ -> failwithf "Not implmented eamode %uy, eareg %uy" eamode eareg
            | _ -> failwithf "Not implemented op mode %uy" opmode //word operation

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucketB (instruction: int) : Cpu =
        match instruction with
        | CMP(register, opmode, eamode, eareg) ->
            match opmode with
            | 0b000uy -> //CMP.B <ea>,Dn
                match eamode with
                | 0b000uy -> //Dn
                    let dest = byte (x.DataRegister register)
                    let source = byte (x.DataRegister eareg)
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    printfn "cmp.b D%u,D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b010uy -> //(An)
                    let dest = byte (x.DataRegister register)
                    let source = x.MMU.ReadByte(uint32 (x.AddressRegister eareg))
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    printfn "cmp.b (a%u),D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b110uy -> //(d8,An,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + ext.Offset
                    let dest = byte (x.DataRegister register)
                    let source = x.MMU.ReadByte(uint32 addr)
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    printfn "cmp.b %s,D%u" (x.DescribeIndexed eareg ext) register
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = byte (x.DataRegister register)
                    let source = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    printfn "cmp.b #$%x,D%u" source register
                    {x with PC = x.PC+4; CCR = ccr}
                | _ -> failwithf "cmp.b eamode %u not implemented" eamode
            | 0b001uy -> //CMP.W <ea>,Dn
                match eamode with
                | 0b000uy -> //Dn
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.DataRegister eareg)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    printfn "cmp.w D%u,D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    printfn "cmp.w #$%x,D%u" source register
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b011uy -> //(An)+ - word always postincrements by 2, even for A7
                    let addr = x.AddressRegister eareg
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithAddressRegister eareg (addr+2) with PC = x.PC+2; CCR = ccr}
                    printfn "cmp.w (a%u)+,D%u" eareg register
                    newCpu
                | 0b100uy -> //-(An) - word always predecrements by 2, even for A7
                    let addr = x.AddressRegister eareg - 2
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithAddressRegister eareg addr with PC = x.PC+2; CCR = ccr}
                    printfn "cmp.w -(a%u),D%u" eareg register
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.MMU.ReadWord addr)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    printfn "cmp.w $%x.l,D%u" addr register
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    printfn "cmp.w %i(a%u),D%u" displacement eareg register
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b010uy -> //(An)
                    let dest = int16 (x.DataRegister register)
                    let source = int16 (x.MMU.ReadWord(uint32 (x.AddressRegister eareg)))
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    printfn "cmp.w (a%u),D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | _ -> failwithf "cmp.w eamode %u not implemented" eamode
            | 0b010uy -> //CMP.L <ea>,Dn
                match eamode with
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = x.DataRegister register
                    let source = x.MMU.ReadLong(uint32 addr)
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.l %i(a%u),D%u" displacement eareg register
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.DataRegister register
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.l #$%x,D%u" source register
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.DataRegister register
                    let source = x.MMU.ReadLong addr
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.l $%x.l,D%u" addr register
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b000uy -> //Dn
                    let dest = x.DataRegister register
                    let source = x.DataRegister eareg
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.l D%u,D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b010uy -> //(An)
                    let dest = x.DataRegister register
                    let source = x.MMU.ReadLong(uint32 (x.AddressRegister eareg))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.l (a%u),D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b011uy -> //(An)+ - long postincrements by 4
                    let addr = x.AddressRegister eareg
                    let dest = x.DataRegister register
                    let source = x.MMU.ReadLong(uint32 addr)
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    let newCpu = {x.WithAddressRegister eareg (addr+4) with PC = x.PC+2; CCR = ccr}
                    printfn "cmp.l (a%u)+,D%u" eareg register
                    newCpu
                | _ -> failwithf "cmp.l eamode %u not implemented" eamode
            | 0b111uy -> //CMPA.L <ea>,An - full 32-bit compare against An; X untouched. Shared EA decoder.
                let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Long eamode eareg (x.PC + 2)
                let source = x.ReadEa OperandSize.Long loc
                let ccr = CCR.Subtract_IgnoringX x.CCR (x.AddressRegister register) source
                let newCpu = { regUpdate x with PC = x.PC + 2 + extBytes; CCR = ccr }
                printfn "cmpa.l %s,A%u" desc register
                newCpu
            | 0b011uy -> //CMPA.W <ea>,An - source word sign-extended to long, full 32-bit compare
                //against An; X untouched (CMP-family). Migrated to the shared EA decoder.
                let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Word eamode eareg (x.PC + 2)
                let source = int (int16 (x.ReadEa OperandSize.Word loc))
                let ccr = CCR.Subtract_IgnoringX x.CCR (x.AddressRegister register) source
                let newCpu = { regUpdate x with PC = x.PC + 2 + extBytes; CCR = ccr }
                printfn "cmpa.w %s,A%u" desc register
                newCpu
            | 0b101uy -> //EOR.W Dn,<ea>-><ea> - except eamode=001 (the "An-direct" EA slot, illegal
                         //as a real EOR destination), which real hardware repurposes for
                         //CMPM.W (An)+,(An)+ instead - NOT eamode=011 (plain (An)+, which stays a
                         //normal, legal EOR destination). Caught and fixed this pass: the first
                         //version of this case wrongly put CMPM at eamode=011, silently stealing
                         //the real EOR.W Dn,(An)+ opcode space instead of the actual CMPM slot.
                match eamode with
                | 0b001uy -> //CMPM.W (An)+,(An)+ - both sides always postincrement by 2
                    let srcAddr = x.AddressRegister eareg
                    let source = int16 (x.MMU.ReadWord(uint32 srcAddr))
                    //The source postincrement completes before the destination is read, so when
                    //both operands name the same register the destination reads the next word.
                    let destAddr = if eareg = register then srcAddr + 2 else x.AddressRegister register
                    let dest = int16 (x.MMU.ReadWord(uint32 destAddr))
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    let newCpu =
                        (x.WithAddressRegister eareg (srcAddr+2)).WithAddressRegister register (destAddr+2)
                    printfn "cmpm.w (a%u)+,(a%u)+" eareg register
                    {newCpu with PC = x.PC+2; CCR = ccr}
                | 0b011uy -> //(An)+
                    let source = int16 (x.DataRegister register)
                    let addr = x.AddressRegister eareg
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = source ^^^ dest
                    x.MMU.WriteWord (uint32 addr) result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithAddressRegister eareg (addr+2) with PC = x.PC+2; CCR = ccr}
                    printfn "eor.w D%u,(a%u)+" register eareg
                    newCpu
                | 0b000uy -> //Dn
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.DataRegister eareg)
                    let result = source ^^^ dest
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "eor.w D%u,D%u" register eareg
                    newCpu
                | 0b010uy -> //(An)
                    let source = int16 (x.DataRegister register)
                    let addr = uint32 (x.AddressRegister eareg)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source ^^^ dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "eor.w D%u,(a%u)" register eareg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source ^^^ dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "eor.w D%u,%i(a%u)" register displacement eareg
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source ^^^ dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "eor.w D%u,$%x.l" register addr
                    newCpu
                | _ -> failwithf "eor.w/cmpm.w not implemented for eamode %x" eamode
            | 0b100uy -> //EOR.B Dn,<ea>-><ea> - eamode=001 repurposed for CMPM.B (An)+,(An)+
                match eamode with
                | 0b001uy -> //CMPM.B (An)+,(An)+ - A7 postincrements by 2, others by 1
                    let srcAddr = x.AddressRegister eareg
                    let source = x.MMU.ReadByte(uint32 srcAddr)
                    let sStep = if eareg = 0b111uy then 2 else 1
                    //Source postincrement completes before the destination read; same register on
                    //both operands means the destination reads srcAddr + the source's step.
                    let destAddr = if eareg = register then srcAddr + sStep else x.AddressRegister register
                    let dest = x.MMU.ReadByte(uint32 destAddr)
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    let dStep = if register = 0b111uy then 2 else 1
                    let newCpu =
                        (x.WithAddressRegister eareg (srcAddr+sStep)).WithAddressRegister register (destAddr+dStep)
                    printfn "cmpm.b (a%u)+,(a%u)+" eareg register
                    {newCpu with PC = x.PC+2; CCR = ccr}
                | 0b000uy -> //Dn
                    let source = byte (x.DataRegister register)
                    let dest = byte (x.DataRegister eareg)
                    let result = source ^^^ dest
                    let newValue = (x.DataRegister eareg &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "eor.b D%u,D%u" register eareg
                    newCpu
                | 0b010uy -> //(An)
                    let source = byte (x.DataRegister register)
                    let addr = uint32 (x.AddressRegister eareg)
                    let dest = x.MMU.ReadByte addr
                    let result = source ^^^ dest
                    x.MMU.WriteByte addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "eor.b D%u,(a%u)" register eareg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = byte (x.DataRegister register)
                    let dest = x.MMU.ReadByte addr
                    let result = source ^^^ dest
                    x.MMU.WriteByte addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "eor.b D%u,%i(a%u)" register displacement eareg
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = byte (x.DataRegister register)
                    let dest = x.MMU.ReadByte addr
                    let result = source ^^^ dest
                    x.MMU.WriteByte addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "eor.b D%u,$%x.l" register addr
                    newCpu
                | _ -> failwithf "eor.b/cmpm.b not implemented for eamode %x" eamode
            | _ -> failwithf "cmp opmode %u not implemented" opmode

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucketC (instruction: int) : Cpu =
        match instruction with
        | EXG(rx, mode, ry) ->
            match mode with
            | 0b01000uy -> //Dx,Dy
                let vx = x.DataRegister rx
                let vy = x.DataRegister ry
                let newCpu = {(x.WithDataRegister rx vy).WithDataRegister ry vx with PC = x.PC+2}
                printfn "exg D%u,D%u" rx ry
                newCpu
            | 0b01001uy -> //Ax,Ay
                let vx = x.AddressRegister rx
                let vy = x.AddressRegister ry
                let newCpu = {(x.WithAddressRegister rx vy).WithAddressRegister ry vx with PC = x.PC+2}
                printfn "exg A%u,A%u" rx ry
                newCpu
            | 0b10001uy -> //Dx,Ay
                let vx = x.DataRegister rx
                let vy = x.AddressRegister ry
                let newCpu = {(x.WithDataRegister rx vy).WithAddressRegister ry vx with PC = x.PC+2}
                printfn "exg D%u,A%u" rx ry
                newCpu
            | _ -> failwithf "exg: unknown mode %x" mode

        | MULU(register, eamode, eareg) ->
            match eamode with
            | 0b000uy -> //Dn
                let source = uint32 (uint16 (x.DataRegister eareg))
                let dest = uint32 (uint16 (x.DataRegister register))
                let result = int (source * dest)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+2; CCR = ccr}
                printfn "mulu.w D%u,D%u" eareg register
                newCpu
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let source = uint32 (uint16 (x.MMU.ReadWord addr))
                let dest = uint32 (uint16 (x.DataRegister register))
                let result = int (source * dest)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+6; CCR = ccr}
                printfn "mulu.w $%x.l,D%u" addr register
                newCpu
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let source = uint32 (uint16 (x.MMU.ReadWord(uint32 addr)))
                let dest = uint32 (uint16 (x.DataRegister register))
                let result = int (source * dest)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+4; CCR = ccr}
                printfn "mulu.w %i(a%u),D%u" displacement eareg register
                newCpu
            | _ -> failwithf "mulu.w not implemented for eamode %x" eamode

        | MULS(register, eamode, eareg) ->
            match eamode with
            | 0b000uy -> //Dn
                let source = int (int16 (x.DataRegister eareg))
                let dest = int (int16 (x.DataRegister register))
                let result = source * dest
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+2; CCR = ccr}
                printfn "muls.w D%u,D%u" eareg register
                newCpu
            | 0b111uy when eareg = 0b100uy -> //#imm
                let source = int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))
                let dest = int (int16 (x.DataRegister register))
                let result = source * dest
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+4; CCR = ccr}
                printfn "muls.w #$%x,D%u" source register
                newCpu
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let source = int (int16 (x.MMU.ReadWord(uint32 addr)))
                let dest = int (int16 (x.DataRegister register))
                let result = source * dest
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+4; CCR = ccr}
                printfn "muls.w %i(a%u),D%u" displacement eareg register
                newCpu
            | 0b010uy -> //(An)
                let source = int (int16 (x.MMU.ReadWord(uint32 (x.AddressRegister eareg))))
                let dest = int (int16 (x.DataRegister register))
                let result = source * dest
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+2; CCR = ccr}
                printfn "muls.w (a%u),D%u" eareg register
                newCpu
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let source = int (int16 (x.MMU.ReadWord addr))
                let dest = int (int16 (x.DataRegister register))
                let result = source * dest
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister register result with PC = x.PC+6; CCR = ccr}
                printfn "muls.w $%x.l,D%u" addr register
                newCpu
            | _ -> failwithf "muls.w not implemented for eamode %x" eamode

        | AND(register, opmode, eamode, eareg) ->
            match opmode with
            | 0b000uy -> //AND.B ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = byte (x.DataRegister eareg)
                    let dest = byte (x.DataRegister register)
                    let result = source &&& dest
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                    printfn "and.b D%u,D%u" eareg register
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let result = source &&& dest
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "and.b #$%x,D%u" source register
                    newCpu
                | _ -> failwithf "and.b(ea->dn) not implemented for eamode %x" eamode
            | 0b001uy -> //AND.W ea+Dn->Dn
                match eamode with
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let result = source &&& dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "and.w #$%x,D%u" source register
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L - absolute long; this was previously
                    //mislabeled/implemented as absolute SHORT (mode 7 reg 0, not reg 1 - see
                    //[[68k-opcode-space-aliasing]]), which both computed the wrong address (a
                    //sign-extended single word instead of the real 32-bit long) and only consumed
                    //4 bytes of PC instead of the correct 6, desyncing every instruction decoded
                    //afterward - the real root cause behind a genuine, repeating Bus Error this
                    //project's own emulator was hitting that TOS's own recovery handler ($fc0a1a)
                    //was correctly (if silently) catching by terminating and hard-resetting, which
                    //is what looked like "GEM.PRG restarting the desktop" from the GEMDOS call
                    //trace alone.
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.MMU.ReadWord addr)
                    let dest = int16 (x.DataRegister register)
                    let result = source &&& dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+6; CCR = ccr}
                    printfn "and.w $%x.l,D%u" addr register
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister register)
                    let result = source &&& dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "and.w %i(a%u),D%u" displacement eareg register
                    newCpu
                | 0b000uy -> //Dn
                    let source = int16 (x.DataRegister eareg)
                    let dest = int16 (x.DataRegister register)
                    let result = source &&& dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                    printfn "and.w D%u,D%u" eareg register
                    newCpu
                | _ -> failwithf "and.w(ea->dn) not implemented for eamode %x" eamode
            | 0b010uy -> //AND.L ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = x.DataRegister eareg
                    let dest = x.DataRegister register
                    let result = source &&& dest
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+2; CCR = ccr}
                    printfn "and.l D%u,D%u" eareg register
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let dest = x.DataRegister register
                    let result = source &&& dest
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+6; CCR = ccr}
                    printfn "and.l #$%x,D%u" source register
                    newCpu
                | 0b010uy -> //(An)
                    let source = x.MMU.ReadLong(uint32 (x.AddressRegister eareg))
                    let result = source &&& x.DataRegister register
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+2; CCR = ccr}
                    printfn "and.l (a%u),D%u" eareg register
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = x.MMU.ReadLong(uint32 addr)
                    let result = source &&& x.DataRegister register
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+4; CCR = ccr}
                    printfn "and.l %i(a%u),D%u" displacement eareg register
                    newCpu
                | _ -> failwithf "and.l(ea->dn) not implemented for eamode %x" eamode
            | 0b100uy -> //AND.B Dn,ea -> ea
                match eamode with
                | 0b010uy -> //(An)
                    let source = byte (x.DataRegister register)
                    let addr = uint32 (x.AddressRegister eareg)
                    let dest = x.MMU.ReadByte addr
                    let result = source &&& dest
                    x.MMU.WriteByte addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "and.b D%u,(a%u)" register eareg
                    newCpu
                | _ -> failwithf "and.b not implemented for eamode %x" eamode
            | 0b101uy -> //AND.W Dn,ea -> ea
                match eamode with
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source &&& dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "and.w D%u,(a%u)" register eareg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source &&& dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "and.w D%u,%i(a%u)" register displacement eareg
                    newCpu
                | _ -> failwithf "and.w(dn->ea) not implemented for eamode %x" eamode
            | _ -> failwithf "and: not implemented for opmode %x" opmode

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucketD (instruction: int) : Cpu =
        match instruction with
        | ADDX(registerX, size, usePredecrement, registerY) ->
            //Extend-aware add for multi-precision arithmetic (see ExtendedArith.step for the Z quirk).
            x.ExtendedArith true size usePredecrement registerX registerY

        | ADD(address, opmode, eamode, eareg) ->
            match opmode with
            | 0b000uy -> //ADD.B ea+Dn->Dn
                match eamode with
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Add_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.b #$%x,D%u" source address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = x.MMU.ReadByte(uint32 addr)
                    let dest = byte (x.DataRegister address)
                    let result = dest + source
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Add_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.b %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b000uy -> //Dn
                    let source = byte (x.DataRegister eareg)
                    let dest = byte (x.DataRegister address)
                    let result = dest + source
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Add_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "add.b D%u,D%u" eareg address
                    newCpu
                | _ -> failwithf "add.b(ea->dn) not implemented for eamode %x" eamode
            | 0b001uy -> //ADD.W ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = int16 (x.DataRegister eareg)
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "add.w D%u,D%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.w #$%x,D%u" source address
                    newCpu
                | 0b001uy -> //An - word source from an address register is legal for ADD (not ADDA)
                    let source = int16 (x.AddressRegister eareg)
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "add.w A%u,D%u" eareg address
                    newCpu
                | 0b010uy -> //(An)
                    let addr = x.AddressRegister eareg
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "add.w (a%u),D%u" eareg address
                    newCpu
                | 0b011uy -> //(An)+
                    let addr = x.AddressRegister eareg
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {(x.WithDataRegister address newValue).WithAddressRegister eareg (addr+2) with PC = x.PC+2; CCR = ccr}
                    printfn "add.w (a%u)+,D%u" eareg address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.w %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.MMU.ReadWord addr)
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+6; CCR = ccr}
                    printfn "add.w $%x.l,D%u" addr address
                    newCpu
                | _ -> failwithf "add.w(ea->dn) not implemented for eamode %x" eamode
            | 0b010uy -> //ADD.L ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let dest = x.DataRegister address
                    let source = x.DataRegister eareg
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+2; CCR = ccr}
                    printfn "add.l D%u,D%u" eareg address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 addr)
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+4; CCR = ccr}
                    printfn "add.l %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b001uy -> //An
                    let dest = x.DataRegister address
                    let source = x.AddressRegister eareg
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+2; CCR = ccr}
                    printfn "add.l A%u,D%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "add.l #$%x,D%u" source address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "add.l $%x.l,D%u" addr address
                    newCpu
                | _ -> failwithf "add.l not implemented for eamode %x" eamode
            | 0b011uy -> //ADDA.W - operand's low word sign-extended to 32 bits, added to An, no flags
                let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Word eamode eareg (x.PC + 2)
                let source = int (int16 (x.ReadEa OperandSize.Word loc))
                let afterEa = regUpdate x
                let result = afterEa.AddressRegister address + source
                let newCpu = { afterEa.WithAddressRegister address result with PC = x.PC + 2 + extBytes }
                printfn "adda.w %s,A%u" desc address
                newCpu
            | 0b111uy -> //ADDA.L
                match eamode with
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.AddressRegister address
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+6}
                    printfn "adda.l #$%x,A%u" source address
                    newCpu
                | 0b000uy -> //Dn
                    let dest = x.AddressRegister address
                    let source = x.DataRegister eareg
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "adda.l D%u,A%u" eareg address
                    newCpu
                | 0b001uy -> //An
                    let dest = x.AddressRegister address
                    let source = x.AddressRegister eareg
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "adda.l A%u,A%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.AddressRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+6}
                    printfn "adda.l $%x.l,A%u" addr address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = x.AddressRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+4}
                    printfn "adda.l %i(a%u),A%u" displacement eareg address
                    newCpu
                | _ -> failwithf "adda.l not implemented for eamode %x" eamode
            | 0b101uy -> //ADD.W Dn,<ea> (ea+Dn->ea, result written to memory)
                match eamode with
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + source
                    let ccr = CCR.Add_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "add.w D%u,$%x.l" address addr
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + source
                    let ccr = CCR.Add_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "add.w D%u,%i(a%u)" address displacement eareg
                    newCpu
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + source
                    let ccr = CCR.Add_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "add.w D%u,(a%u)" address eareg
                    newCpu
                | _ -> failwithf "add.w(dn->ea) not implemented for eamode %x" eamode
            | 0b110uy -> //ADD.L Dn,<ea> (ea+Dn->ea, result written to memory)
                match eamode with
                | 0b111uy when eareg = 0b001uy -> //(xxx).L - the BIOS 200Hz clock's `add.l D0,$5ffa.l` ms accumulator
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = x.DataRegister address
                    let dest = x.MMU.ReadLong addr
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "add.l D%u,$%x.l" address addr
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = x.DataRegister address
                    let dest = x.MMU.ReadLong addr
                    let result = dest + source
                    let ccr = CCR.Add x.CCR dest source
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "add.l D%u,%i(a%u)" address displacement eareg
                    newCpu
                | _ -> failwithf "add.l(dn->ea) not implemented for eamode %x" eamode
            | _ -> failwithf "add: not implemented for opmode %x" opmode

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucketE (instruction: int) : Cpu =
        match instruction with
        | ShiftRotate(countOrReg, direction, size, useRegisterCount, shiftType, register) ->
            // Logical right shift by 1. F#'s `>>>` on `int` is arithmetic (sign-propagating), so
            // for a .L operand with bit 31 set `v >>> 1` smears 1s down from the top - wrong for
            // LSR/ROR (fine for ASR, which wants the sign fill). Route the shift through uint32.
            // Byte/word operands are already masked non-negative, so this is a no-op for them.
            let lsr1 (v: int) = int (uint32 v >>> 1)
            match direction, size, useRegisterCount, shiftType with
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b00uy -> //ASL.B/W/L #imm,Dn
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                let mutable overflow = false
                for _ in 1 .. amount do
                    let beforeSign = v &&& signBit <> 0
                    carryOut <- beforeSign
                    v <- (v <<< 1) &&& bitMask
                    if (v &&& signBit <> 0) <> beforeSign then overflow <- true
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s
                ccr <- ccr &&& ~~~0x4s
                ccr <- ccr &&& ~~~0x2s
                ccr <- ccr &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if overflow then ccr <- ccr ||| 0x2s //V
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "asl.%s #%u,D%u" sizeChar amount register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b01uy -> //LSL.B/W/L #imm,Dn
                //Logical shift: same bit motion as ASL, but V is always cleared (no sign-change check).
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    carryOut <- v &&& signBit <> 0
                    v <- (v <<< 1) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "lsl.%s #%u,D%u" sizeChar amount register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b00uy -> //ASL.B/W/L Dn,Dn - shift count taken from a register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                let mutable overflow = false
                for _ in 1 .. amount do
                    let beforeSign = v &&& signBit <> 0
                    carryOut <- beforeSign
                    v <- (v <<< 1) &&& bitMask
                    if (v &&& signBit <> 0) <> beforeSign then overflow <- true
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if overflow then ccr <- ccr ||| 0x2s //V
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "asl.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b00uy -> //ASR.B/W/L Dn,Dn - shift count taken from a register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let width  = match size with 0b00uy -> 8   | 0b01uy -> 16     | _ -> 32
                let mutable v = x.DataRegister register &&& bitMask
                let originalSignSet = v &&& signBit <> 0
                let mutable carryOut = false
                for _ in 1 .. amount do
                    carryOut <- v &&& 1 <> 0
                    v <- ((v >>> 1) ||| (if originalSignSet then signBit else 0)) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > width then
                    // Real 68000: once the count exceeds the operand width the value has saturated
                    // to all sign bits and C / X both come out 0, even for a negative operand (the
                    // 680x0 vectors are explicit - X is cleared, not just left unchanged).
                    ccr <- ccr &&& ~~~0x1s &&& ~~~0x10s
                elif amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "asr.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b00uy -> //ASR.B/W/L #imm,Dn
                //Arithmetic shift right: sign-fills from the top (V always cleared - never overflows).
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let originalSignSet = v &&& signBit <> 0
                let mutable carryOut = false
                for _ in 1 .. amount do
                    carryOut <- v &&& 1 <> 0
                    v <- ((v >>> 1) ||| (if originalSignSet then signBit else 0)) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "asr.%s #%u,D%u" sizeChar amount register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b01uy -> //LSR.B/W/L #imm,Dn
                //Logical shift right: zero-fills from the top, carry/X take the last bit shifted out, V always cleared.
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    carryOut <- v &&& 1 <> 0
                    v <- (lsr1 v) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "lsr.%s #%u,D%u" sizeChar amount register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b01uy -> //LSR.B/W/L Dn,Dn - shift count taken from a register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    carryOut <- v &&& 1 <> 0
                    v <- (lsr1 v) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "lsr.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b01uy -> //LSL.B/W/L Dn,Dn - shift count taken from a register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    carryOut <- v &&& signBit <> 0
                    v <- (v <<< 1) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 then
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                    else ccr <- ccr &&& ~~~0x10s //X follows C
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "lsl.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b10uy -> //ROXL.B/W/L #imm,Dn - rotates through the X flag
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable xFlag = x.X
                for _ in 1 .. amount do
                    let newX = v &&& signBit <> 0
                    v <- ((v <<< 1) ||| (if xFlag then 1 else 0)) &&& bitMask
                    xFlag <- newX
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s &&& ~~~0x10s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if xFlag then ccr <- ccr ||| 0x1s ||| 0x10s //C mirrors the resulting X, even at amount=0 - a real ROXd quirk
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "roxl.%s #%u,D%u" sizeChar amount register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b10uy -> //ROXR.B/W/L #imm,Dn - rotate right through the X flag
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable xFlag = x.X
                for _ in 1 .. amount do
                    let newX = v &&& 1 <> 0
                    v <- ((lsr1 v) ||| (if xFlag then signBit else 0)) &&& bitMask
                    xFlag <- newX
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s &&& ~~~0x10s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if xFlag then ccr <- ccr ||| 0x1s ||| 0x10s //C mirrors the resulting X (true even at amount=0)
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "roxr.%s #%u,D%u" sizeChar amount register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b10uy -> //ROXL.B/W/L Dn,Dn - count from register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable xFlag = x.X
                for _ in 1 .. amount do
                    let newX = v &&& signBit <> 0
                    v <- ((v <<< 1) ||| (if xFlag then 1 else 0)) &&& bitMask
                    xFlag <- newX
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s &&& ~~~0x10s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if xFlag then ccr <- ccr ||| 0x1s ||| 0x10s //C mirrors the resulting X (true even at amount=0)
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "roxl.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b10uy -> //ROXR.B/W/L Dn,Dn - count from register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable xFlag = x.X
                for _ in 1 .. amount do
                    let newX = v &&& 1 <> 0
                    v <- ((lsr1 v) ||| (if xFlag then signBit else 0)) &&& bitMask
                    xFlag <- newX
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s &&& ~~~0x10s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if xFlag then ccr <- ccr ||| 0x1s ||| 0x10s //C mirrors the resulting X (true even at amount=0)
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "roxr.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b11uy -> //ROL.B/W/L Dn,Dn - rotate count from register, mod 64. Plain rotate: X unaffected, C mirrors the bit rotated out.
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    let topBit = v &&& signBit <> 0
                    carryOut <- topBit
                    v <- ((v <<< 1) ||| (if topBit then 1 else 0)) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 && carryOut then ccr <- ccr ||| 0x1s //C only - X is unaffected by plain rotate
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "rol.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 1uy, 0b11uy -> //ROR.B/W/L Dn,Dn - rotate count from register, mod 64
                let amount = (x.DataRegister countOrReg) &&& 0x3F
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    let bottomBit = v &&& 1 <> 0
                    carryOut <- bottomBit
                    v <- ((lsr1 v) ||| (if bottomBit then signBit else 0)) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 && carryOut then ccr <- ccr ||| 0x1s //C only - X is unaffected by plain rotate
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "ror.%s D%u,D%u" sizeChar countOrReg register
                newCpu
            | 0uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b11uy -> //ROR.B/W/L #imm,Dn
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    let bottomBit = v &&& 1 <> 0
                    carryOut <- bottomBit
                    v <- ((lsr1 v) ||| (if bottomBit then signBit else 0)) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 && carryOut then ccr <- ccr ||| 0x1s //C only - X is unaffected by plain rotate
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "ror.%s #%u,D%u" sizeChar amount register
                newCpu
            | 1uy, (0b00uy | 0b01uy | 0b10uy), 0uy, 0b11uy -> //ROL.B/W/L #imm,Dn - mirror of ROR #imm just above, rotating left like ROL Dn,Dn
                let amount = if countOrReg = 0uy then 8 else int countOrReg
                let bitMask = match size with 0b00uy -> 0xff | 0b01uy -> 0xffff | _ -> -1
                let signBit = match size with 0b00uy -> 0x80 | 0b01uy -> 0x8000 | _ -> 1 <<< 31
                let mutable v = x.DataRegister register &&& bitMask
                let mutable carryOut = false
                for _ in 1 .. amount do
                    let topBit = v &&& signBit <> 0
                    carryOut <- topBit
                    v <- ((v <<< 1) ||| (if topBit then 1 else 0)) &&& bitMask
                let newValue = (x.DataRegister register &&& ~~~bitMask) ||| v
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                if v &&& signBit <> 0 then ccr <- ccr ||| 0x8s //N
                if v = 0 then ccr <- ccr ||| 0x4s //Z
                if amount > 0 && carryOut then ccr <- ccr ||| 0x1s //C only - X is unaffected by plain rotate
                let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                let sizeChar = match size with 0b00uy -> "b" | 0b01uy -> "w" | _ -> "l"
                printfn "rol.%s #%u,D%u" sizeChar amount register
                newCpu
            | _ -> failwithf "shift/rotate not implemented for direction %x size %x useRegCount %x type %x" direction size useRegisterCount shiftType

        | MemoryShiftRotate(shiftType, direction, eamode, eareg) ->
            //Always word-size, always exactly 1 bit - the count/register-size variation only
            //applies to the Dn-direct ShiftRotate form above. EA is a memory-alterable mode, so
            //ResolveEa yields EaMem; `regUpdate` carries any (An)+/-(An) writeback, `extBytes` the
            //PC advance. shiftType: 000=AS 001=LS 010=ROX 011=RO; direction: 0=right 1=left.
            let left = direction = 1uy
            let loc, extBytes, desc, regUpdate = x.ResolveEa OperandSize.Word eamode eareg (x.PC + 2)
            let v = x.ReadEa OperandSize.Word loc &&& 0xffff
            let msb = v &&& 0x8000 <> 0
            let lsb = v &&& 1 <> 0
            let xIn = if x.X then 1 else 0
            let result, carry, affectX, mnem =
                match shiftType, left with
                | 0b000uy, true  -> (v <<< 1) &&& 0xffff, msb, true, "asl"                     // ASL
                | 0b000uy, false -> (v >>> 1) ||| (if msb then 0x8000 else 0), lsb, true, "asr" // ASR (sign fill)
                | 0b001uy, true  -> (v <<< 1) &&& 0xffff, msb, true, "lsl"                     // LSL
                | 0b001uy, false -> v >>> 1, lsb, true, "lsr"                                  // LSR
                | 0b010uy, true  -> ((v <<< 1) ||| xIn) &&& 0xffff, msb, true, "roxl"          // ROXL
                | 0b010uy, false -> (v >>> 1) ||| (xIn <<< 15), lsb, true, "roxr"              // ROXR
                | 0b011uy, true  -> ((v <<< 1) ||| (if msb then 1 else 0)) &&& 0xffff, msb, false, "rol" // ROL
                | 0b011uy, false -> (v >>> 1) ||| (if lsb then 0x8000 else 0), lsb, false, "ror"         // ROR
                | _ -> failwithf "memory shift/rotate: bad type %x" shiftType
            //V is only ever set by ASL (MSB changed during the shift); for a 1-bit shift that is
            //bit15 != bit14 of the original. Every other form clears V.
            let overflow = shiftType = 0b000uy && left && (msb <> (v &&& 0x4000 <> 0))
            let after = x.WriteEa OperandSize.Word loc result (regUpdate x)
            let mutable ccr = x.CCR &&& ~~~0xFs
            if int16 result < 0s then ccr <- ccr ||| 0x8s //N
            if result = 0 then ccr <- ccr ||| 0x4s //Z
            if overflow then ccr <- ccr ||| 0x2s //V
            if carry then ccr <- ccr ||| 0x1s //C
            if affectX then (if carry then ccr <- ccr ||| 0x10s else ccr <- ccr &&& ~~~0x10s) //X follows C (not for plain rotate)
            printfn "%s.w %s" mnem desc
            { after with PC = x.PC + 2 + extBytes; CCR = ccr }

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.Run(cycles: int) =
        //TODO
        //while cycles left
        //get instruction
        //execute
        ()
    member x.DisplayRegisters =
        sprintf """
D0:%08x D1:%08x D2:%08x D3:%08x
D4:%08x D5:%08x D6:%08x D7:%08x
A0:%08x A1:%08x A2:%08x A3:%08x
A4:%08x A5:%08x A6:%08x A7:%08x
USP:%08x SSP:%08x
     TTSM IPM   XNZVC
CCR: %s
PC: %08x""" x.D0 x.D1 x.D2 x.D3 x.D4 x.D5 x.D6 x.D7
            x.A0 x.A1 x.A2 x.A3 x.A4 x.A5 x.A6 x.A7
            x.USP x.SSP
            x.CCR.toBits (*x.TraceMode x.ActiveStack*) x.PC
