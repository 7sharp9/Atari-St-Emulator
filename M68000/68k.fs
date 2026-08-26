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

    let Add_IgnoringX currentCCR (dest: int) (source: int) =
        //unset all flag bits apart from x
        let mutable ccr = currentCCR &&& ~~~0xFs
        let result = dest + source
        let dm = dest < 0
        let sm = source < 0
        let rm = result < 0
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0 then ccr <- ccr ||| 0x4s //Z
        if (dm && sm && not rm) || (not dm && not sm && rm) then ccr <- ccr ||| 0x2s //V
        if (dm && sm) || (not rm && sm) || (dm && not rm) then ccr <- ccr ||| 0x1s //C
        ccr

    let Add_IgnoringX_Word currentCCR (dest: int16) (source: int16) =
        //unset all flag bits apart from x
        let mutable ccr = currentCCR &&& ~~~0xFs
        let result = int16 (int dest + int source)
        let dm = dest < 0s
        let sm = source < 0s
        let rm = result < 0s
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0s then ccr <- ccr ||| 0x4s //Z
        if (dm && sm && not rm) || (not dm && not sm && rm) then ccr <- ccr ||| 0x2s //V
        if (dm && sm) || (not rm && sm) || (dm && not rm) then ccr <- ccr ||| 0x1s //C
        ccr

    let Add_IgnoringX_Byte currentCCR (dest: byte) (source: byte) =
        //unset all flag bits apart from x
        let mutable ccr = currentCCR &&& ~~~0xFs
        let result = byte (int dest + int source)
        let dm = dest &&& 0x80uy <> 0uy
        let sm = source &&& 0x80uy <> 0uy
        let rm = result &&& 0x80uy <> 0uy
        if rm then ccr <- ccr ||| 0x8s //N
        if result = 0uy then ccr <- ccr ||| 0x4s //Z
        if (dm && sm && not rm) || (not dm && not sm && rm) then ccr <- ccr ||| 0x2s //V
        if (dm && sm) || (not rm && sm) || (dm && not rm) then ccr <- ccr ||| 0x1s //C
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
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
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

        | ORI(size, mode, register) ->
            match size with
            | 0b00uy -> //byte
                match mode with
                | 0b000uy -> //Dn
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let result = dest ||| immediate
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "ori.b #$%x,D%u" immediate register
                    newCpu
                | _ -> failwithf "ori.b not implemented for mode %x" mode
            | 0b01uy -> //word
                match mode with
                | 0b000uy -> //Dn
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let result = dest ||| immediate
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "ori.w #$%x,D%u" immediate register
                    newCpu
                | 0b101uy -> //(d16,An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                    let addr = x.AddressRegister register + int displacement
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = dest ||| immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    x.MMU.WriteWord (uint32 addr) result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "ori.w #$%x,%i(a%u)" immediate displacement register
                    newCpu
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest ||| immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+8; CCR = ccr}
                    printfn "ori.w #$%x,$%x.l" immediate addr
                    newCpu
                | 0b010uy -> //(An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest ||| immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "ori.w #$%x,(a%u)" immediate register
                    newCpu
                | _ -> failwithf "ori.w not implemented for mode %x" mode
            | 0b10uy -> //long
                match mode with
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+6)))
                    let dest = x.MMU.ReadLong addr
                    let result = dest ||| immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+10; CCR = ccr}
                    printfn "ori.l #$%x,$%x.l" immediate addr
                    newCpu
                | _ -> failwithf "ori.l not implemented for mode %x" mode
            | _ -> failwithf "ori: not implemented for size %x" size

        | ANDI(size, mode, register) ->
            match size with
            | 0b00uy -> //byte
                match mode with
                | 0b000uy -> //Dn
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let result = dest &&& immediate
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "andi.b #$%x,D%u" immediate register
                    newCpu
                | _ -> failwithf "andi.b not implemented for mode %x" mode
            | 0b01uy -> //word
                match mode with
                | 0b000uy -> //Dn
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let result = dest &&& immediate
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "andi.w #$%x,D%u" immediate register
                    newCpu
                | 0b101uy -> //(d16,An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                    let addr = x.AddressRegister register + int displacement
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = dest &&& immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    x.MMU.WriteWord (uint32 addr) result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "andi.w #$%x,%i(a%u)" immediate displacement register
                    newCpu
                | 0b010uy -> //(An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest &&& immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "andi.w #$%x,(a%u)" immediate register
                    newCpu
                | _ -> failwithf "andi.w not implemented for mode %x" mode
            | _ -> failwithf "andi: not implemented for size %x" size

        | EoriToCcr ->
            //Opcode-space alias: mode=111/reg=100 in EORI's general EA encoding is reserved for
            //this dedicated "EORI to CCR" form - see [[68k-opcode-space-aliasing]]. Byte operation:
            //only the low byte of the word immediate is used (matches the flag bits in CCR).
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
            let newCcr = x.CCR ^^^ immediate
            printfn "eori #$%x,CCR" immediate
            {x with PC = x.PC+4; CCR = newCcr}

        | EORI(size, mode, register) ->
            match size with
            | 0b00uy -> //byte
                match mode with
                | 0b000uy -> //Dn
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let result = dest ^^^ immediate
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "eori.b #$%x,D%u" immediate register
                    newCpu
                | _ -> failwithf "eori.b not implemented for mode %x" mode
            | 0b01uy -> //word
                match mode with
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest ^^^ immediate
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+8; CCR = ccr}
                    printfn "eori.w #$%x,$%x.l" immediate addr
                    newCpu
                | _ -> failwithf "eori.w not implemented for mode %x" mode
            | _ -> failwithf "eori: not implemented for size %x" size

        | ADDI(size, mode, register) ->
            match size with
            | 0b00uy -> //byte
                match mode with
                | 0b000uy -> //Dn
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX_Byte x.CCR dest immediate
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "addi.b #$%x,D%u" immediate register
                    newCpu
                | _ -> failwithf "addi.b not implemented for mode %x" mode
            | 0b01uy -> //word
                match mode with
                | 0b000uy -> //Dn
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest immediate
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "addi.w #$%x,D%u" immediate register
                    newCpu
                | 0b010uy -> //(An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest immediate
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "addi.w #$%x,(a%u)" immediate register
                    newCpu
                | _ -> failwithf "addi.w not implemented for mode %x" mode
            | 0b10uy -> //long
                match mode with
                | 0b000uy -> //Dn
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let dest = x.DataRegister register
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX x.CCR dest immediate
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+6; CCR = ccr}
                    printfn "addi.l #$%x,D%u" immediate register
                    newCpu
                | 0b010uy -> //(An)
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let addr = uint32 (x.AddressRegister register)
                    let dest = x.MMU.ReadLong addr
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX x.CCR dest immediate
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "addi.l #$%x,(a%u)" immediate register
                    newCpu
                | 0b101uy -> //(d16,An)
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+6)))
                    let addr = uint32 (x.AddressRegister register + int displacement)
                    let dest = x.MMU.ReadLong addr
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX x.CCR dest immediate
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+8; CCR = ccr}
                    printfn "addi.l #$%x,%i(a%u)" immediate displacement register
                    newCpu
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+6)))
                    let dest = x.MMU.ReadLong addr
                    let result = dest + immediate
                    let ccr = CCR.Add_IgnoringX x.CCR dest immediate
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+10; CCR = ccr}
                    printfn "addi.l #$%x,$%x.l" immediate addr
                    newCpu
                | _ -> failwithf "addi.l not implemented for mode %x" mode
            | _ -> failwithf "addi: not implemented for size %x" size

        | CMPI(size, mode , register) ->
            match size with
            | 0b000uy ->
                match mode with
                | 0b000uy -> //Dn
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest immediate
                    printfn "cmpi.b #$%x,D%u" immediate register
                    {x with PC = x.PC + 4; CCR = ccr}
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                    let dest = x.MMU.ReadByte addr
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest immediate
                    printfn "cmpi.b #$%x,$%x.l" immediate addr
                    {x with PC = x.PC + 8; CCR = ccr}
                | 0b010uy -> //(An)
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let addr = uint32 (x.AddressRegister register)
                    let dest = x.MMU.ReadByte addr
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest immediate
                    printfn "cmpi.b #$%x,(a%u) == $%x" immediate register dest
                    {x with PC = x.PC + 4; CCR = ccr}
                | 0b101uy -> //(d16,An)
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                    let addr = uint32 (x.AddressRegister register + int displacement)
                    let dest = x.MMU.ReadByte addr
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest immediate
                    printfn "cmpi.b #$%x,%i(a%u) == $%x" immediate displacement register dest
                    {x with PC = x.PC + 6; CCR = ccr}
                | 0b011uy -> //(An)+ - A7 postincrements by 2 (word-aligned stack), others by 1
                    let immediate = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let addr = x.AddressRegister register
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest immediate
                    let step = if register = 0b111uy then 2 else 1
                    let newCpu = {x.WithAddressRegister register (addr+step) with PC = x.PC + 4; CCR = ccr}
                    printfn "cmpi.b #$%x,(a%u)+" immediate register
                    newCpu
                | _ -> failwithf "cmpi.b mode %u not implemented" mode
            | 0b001uy ->
                match mode with
                | 0b000uy -> //Dn
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest immediate
                    printfn "cmpi.w #$%x,D%u" immediate register
                    {x with PC = x.PC + 4; CCR = ccr}
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                    let dest = int16 (x.MMU.ReadWord addr)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest immediate
                    printfn "cmpi.w #$%x,$%x.l" immediate addr
                    {x with PC = x.PC + 8; CCR = ccr}
                | 0b101uy -> //(d16,An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                    let addr = uint32 (x.AddressRegister register + int displacement)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest immediate
                    printfn "cmpi.w #$%x,%i(a%u) == $%x" immediate displacement register dest
                    {x with PC = x.PC + 6; CCR = ccr}
                | 0b010uy -> //(An)
                    let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest immediate
                    printfn "cmpi.w #$%x,(a%u) == $%x" immediate register dest
                    {x with PC = x.PC + 4; CCR = ccr}
                | _ -> failwithf "cmpi.w mode %u not implemented" mode
            | 0b010uy ->
                match mode with
                //| 0b000uy -> //Dn
                | 0b010uy -> //(An)
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let dest = x.MMU.ReadLong(uint32 (x.AddressRegister register))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    printfn "cmpi.l #$%x,(a%u) == $%x" immediate register dest
                    {x with PC = x.PC + 6; CCR = ccr}
                | 0b011uy -> //(An)+
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let addr = x.AddressRegister register
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    let newCpu = {x.WithAddressRegister register (addr+4) with PC = x.PC+6; CCR = ccr}
                    printfn "cmpi.l #$%x,(a%u)+ == $%x" immediate register dest
                    newCpu
                //| 0b100uy -> //-(An)
                //| 0b110uy -> //(d8,An,Xn)
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let destreg = x.MMU.ReadLong(uint32 (x.PC+6))
                    let dest = x.MMU.ReadLong(uint32 destreg)
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpi.l #$%x,$%x" source destreg
                    {x with PC = x.PC + 10; CCR = ccr }
                  //mode 5
                | 0b101uy -> // (d16, An)
                    let immediate = x.MMU.ReadLong(uint32 (x.PC+2))
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+6)))
                    let addr = uint32 (x.AddressRegister register + int displacement)
                    let dest = x.MMU.ReadLong addr
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    printfn "cmpi.l #$%x,(A%u,$%x) == $%x" immediate register displacement dest
                    {x with PC = x.PC + 8; CCR = ccr }
                | _ -> failwithf "cmpi Unknown mode: %x" mode
            | _ -> failwithf "Inknown size: %x" size
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
            let bitnum = int (x.DataRegister register) &&& 7 //memory destination: byte-sized, bit number mod 8
            match eamode with
            | 0b000uy -> //Dn - long-sized destination, bit number mod 32
                let bitnum32 = int (x.DataRegister register) &&& 31
                let current = x.DataRegister eareg
                let mask = 1 <<< bitnum32
                let bitWasSet = (current &&& mask) <> 0
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                let newCpu =
                    match opmode with
                    | 0b00uy -> //BTST
                        printfn "btst D%u,D%u" register eareg
                        {x with PC = x.PC+2; CCR = ccr}
                    | 0b01uy -> //BCHG
                        let newCpu = x.WithDataRegister eareg (current ^^^ mask)
                        printfn "bchg D%u,D%u" register eareg
                        {newCpu with PC = x.PC+2; CCR = ccr}
                    | 0b10uy -> //BCLR
                        let newCpu = x.WithDataRegister eareg (current &&& ~~~mask)
                        printfn "bclr D%u,D%u" register eareg
                        {newCpu with PC = x.PC+2; CCR = ccr}
                    | _ -> //BSET
                        let newCpu = x.WithDataRegister eareg (current ||| mask)
                        printfn "bset D%u,D%u" register eareg
                        {newCpu with PC = x.PC+2; CCR = ccr}
                newCpu
            | 0b010uy -> //(An)
                let addr = uint32 (x.AddressRegister eareg)
                let current = x.MMU.ReadByte addr
                let mask = byte (1 <<< bitnum)
                let bitWasSet = (current &&& mask) <> 0uy
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                let newCpu =
                    match opmode with
                    | 0b00uy -> //BTST
                        printfn "btst D%u,(a%u)" register eareg
                        {x with PC = x.PC+2; CCR = ccr}
                    | 0b01uy -> //BCHG
                        x.MMU.WriteByte addr (current ^^^ mask)
                        printfn "bchg D%u,(a%u)" register eareg
                        {x with PC = x.PC+2; CCR = ccr}
                    | 0b10uy -> //BCLR
                        x.MMU.WriteByte addr (current &&& ~~~mask)
                        printfn "bclr D%u,(a%u)" register eareg
                        {x with PC = x.PC+2; CCR = ccr}
                    | _ -> //BSET
                        x.MMU.WriteByte addr (current ||| mask)
                        printfn "bset D%u,(a%u)" register eareg
                        {x with PC = x.PC+2; CCR = ccr}
                newCpu
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = uint32 (x.AddressRegister eareg + int displacement)
                let current = x.MMU.ReadByte addr
                let mask = byte (1 <<< bitnum)
                let bitWasSet = (current &&& mask) <> 0uy
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                let newCpu =
                    match opmode with
                    | 0b00uy -> //BTST
                        printfn "btst D%u,%i(a%u)" register displacement eareg
                        {x with PC = x.PC+4; CCR = ccr}
                    | 0b01uy -> //BCHG
                        x.MMU.WriteByte addr (current ^^^ mask)
                        printfn "bchg D%u,%i(a%u)" register displacement eareg
                        {x with PC = x.PC+4; CCR = ccr}
                    | 0b10uy -> //BCLR
                        x.MMU.WriteByte addr (current &&& ~~~mask)
                        printfn "bclr D%u,%i(a%u)" register displacement eareg
                        {x with PC = x.PC+4; CCR = ccr}
                    | _ -> //BSET
                        x.MMU.WriteByte addr (current ||| mask)
                        printfn "bset D%u,%i(a%u)" register displacement eareg
                        {x with PC = x.PC+4; CCR = ccr}
                newCpu
            | _ -> failwithf "bit op not implemented for eamode %x" eamode

        | BitOpImmediate(opmode, eamode, eareg) ->
            //Static-bit-number BCHG/BCLR/BSET - same op table as BitOpDynamic above, but the bit
            //number is a literal extension word (at PC+2) instead of a data register.
            let bitnumber = x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff
            match eamode with
            | 0b000uy -> //Dn - long-sized destination, bit number mod 32
                let bitnum32 = bitnumber % 32
                let current = x.DataRegister eareg
                let mask = 1 <<< bitnum32
                let bitWasSet = (current &&& mask) <> 0
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                match opmode with
                | 0b01uy -> //BCHG
                    let newCpu = x.WithDataRegister eareg (current ^^^ mask)
                    printfn "bchg #$%x,D%u" bitnumber eareg
                    {newCpu with PC = x.PC+4; CCR = ccr}
                | 0b10uy -> //BCLR
                    let newCpu = x.WithDataRegister eareg (current &&& ~~~mask)
                    printfn "bclr #$%x,D%u" bitnumber eareg
                    {newCpu with PC = x.PC+4; CCR = ccr}
                | _ -> //BSET
                    let newCpu = x.WithDataRegister eareg (current ||| mask)
                    printfn "bset #$%x,D%u" bitnumber eareg
                    {newCpu with PC = x.PC+4; CCR = ccr}
            | 0b010uy -> //(An) - byte-sized destination, bit number mod 8
                let addr = uint32 (x.AddressRegister eareg)
                let current = x.MMU.ReadByte addr
                let mask = byte (1 <<< (bitnumber % 8))
                let bitWasSet = (current &&& mask) <> 0uy
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                match opmode with
                | 0b01uy -> //BCHG
                    x.MMU.WriteByte addr (current ^^^ mask)
                    printfn "bchg #$%x,(a%u)" bitnumber eareg
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b10uy -> //BCLR
                    x.MMU.WriteByte addr (current &&& ~~~mask)
                    printfn "bclr #$%x,(a%u)" bitnumber eareg
                    {x with PC = x.PC+4; CCR = ccr}
                | _ -> //BSET
                    x.MMU.WriteByte addr (current ||| mask)
                    printfn "bset #$%x,(a%u)" bitnumber eareg
                    {x with PC = x.PC+4; CCR = ccr}
            | 0b101uy -> //(d16,An) - byte-sized destination, bit number mod 8
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                let addr = uint32 (x.AddressRegister eareg + int displacement)
                let current = x.MMU.ReadByte addr
                let mask = byte (1 <<< (bitnumber % 8))
                let bitWasSet = (current &&& mask) <> 0uy
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                match opmode with
                | 0b01uy -> //BCHG
                    x.MMU.WriteByte addr (current ^^^ mask)
                    printfn "bchg #$%x,%i(a%u)" bitnumber displacement eareg
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b10uy -> //BCLR
                    x.MMU.WriteByte addr (current &&& ~~~mask)
                    printfn "bclr #$%x,%i(a%u)" bitnumber displacement eareg
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> //BSET
                    x.MMU.WriteByte addr (current ||| mask)
                    printfn "bset #$%x,%i(a%u)" bitnumber displacement eareg
                    {x with PC = x.PC+6; CCR = ccr}
            | 0b111uy when eareg = 0b001uy -> //(xxx).L, byte-sized destination, bit number mod 8
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                let current = x.MMU.ReadByte addr
                let mask = byte (1 <<< (bitnumber % 8))
                let bitWasSet = (current &&& mask) <> 0uy
                let ccr = if bitWasSet then CCR.ClearZero x.CCR else CCR.SetZero x.CCR
                match opmode with
                | 0b01uy -> //BCHG
                    x.MMU.WriteByte addr (current ^^^ mask)
                    printfn "bchg #$%x,$%x.l" bitnumber addr
                    {x with PC = x.PC+8; CCR = ccr}
                | 0b10uy -> //BCLR
                    x.MMU.WriteByte addr (current &&& ~~~mask)
                    printfn "bclr #$%x,$%x.l" bitnumber addr
                    {x with PC = x.PC+8; CCR = ccr}
                | _ -> //BSET
                    x.MMU.WriteByte addr (current ||| mask)
                    printfn "bset #$%x,$%x.l" bitnumber addr
                    {x with PC = x.PC+8; CCR = ccr}
            | _ -> failwithf "static bit op not implemented for eamode %x" eamode

        | BTSTImmediate(eamode, eareg) ->
            let bitnumber = x.MMU.ReadWord (uint32 (x.PC+2)) &&& 0xFF
            //ccr z flag is set if zero, no others
            match eamode with
            | 0b000uy -> //Dn - bit number taken modulo 32, tests the whole long register
                let bit = bitnumber % 32
                let regValue = x.DataRegister eareg
                let bitZeroSet = not (regValue.isset bit)
                printfn "BTST.B #$%x,D%u" bitnumber eareg
                {x with PC=x.PC+4; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }
            | 0b010uy -> //(An) - byte-only, bit number taken modulo 8
                let ea = uint32 (x.AddressRegister eareg)
                let eaVal = x.MMU.ReadByte ea
                let bitZeroSet = eaVal.isnotset (bitnumber % 8)
                printfn "BTST.B #$%x,(a%u)" bitnumber eareg
                {x with PC=x.PC+4; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }
            | 0b101uy -> //(d16,An) - byte-only, bit number taken modulo 8
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                let ea = uint32 (x.AddressRegister eareg + int displacement)
                let eaVal = x.MMU.ReadByte ea
                let bitZeroSet = eaVal.isnotset (bitnumber % 8)
                printfn "BTST.B #$%x,%i(a%u)" bitnumber displacement eareg
                {x with PC=x.PC+6; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }
            | 0b111uy ->
                match eareg with
                | 0b010uy -> //d16, PC
                    let displacement = int16 (x.MMU.ReadWord (uint32 (x.PC+4)))
                    let ea = (x.PC+4) + int displacement

                    printfn "BTST.B #$%04x,(PC,$%x) == $%08x" bitnumber displacement ea
                    // Data register direct can be used for long only; all others are byte only.
                    let eaVal = x.MMU.ReadByte (uint32 ea)
                    let bitZeroSet = eaVal.isnotset (bitnumber % 8)

                    {x with PC=x.PC+6; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }

                | 0b001uy -> //(xxx).L
                    let ea = uint32 (x.MMU.ReadLong (uint32 (x.PC+4)))
                    let eaVal = x.MMU.ReadByte ea
                    let bitZeroSet = eaVal.isnotset (bitnumber % 8)
                    printfn "BTST.B #$%04x,$%x.l" bitnumber ea
                    {x with PC=x.PC+8; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }

                | other -> failwithf "BTST.b EA reg %u not supported" other
            | other -> failwithf "BTST.b EA mode %u not supported" other

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucketMove (instruction: int) : Cpu =
        match instruction with
        | Move(size, dReg, dMode, sMode, sReg) ->

                
            //Note CCR: N,Z are set as appropriate.  V and C set to 0. X =N/A
            match size with
            //For immediate data, byte size operations
            //only use the byte portion of the "extension word"
            | OperandSize.Byte ->
                //sourceExtWords: number of extension words the source addressing mode consumes,
                //needed to locate the destination's own extension words (e.g. (xxx).L, d16(An))
                let source, sourceExtWords, sourceDesc, sourceUpdate =
                    match sMode, sReg with
                    | 0b111uy, 0b100uy -> //#imm
                        let v = int16 (x.MMU.ReadWord(uint32 (x.PC+2) ) &&& 0xff)
                        v, 1, sprintf "#$%x" v, id
                    | 0b111uy, 0b001uy -> //(xxx).L
                        let addr = x.MMU.ReadLong(uint32 (x.PC+2))
                        let v = int16 (x.MMU.ReadByte(uint32 addr))
                        v, 2, sprintf "$%x.l" addr, id
                    | 0b111uy, 0b011uy -> //(d8,PC,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = (x.PC+2) + ext.Offset
                        let v = int16 (x.MMU.ReadByte(uint32 addr))
                        v, 1, sprintf "%i(pc,%s%u.%s)" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w"), id
                    | 0b000uy, reg -> //Dn
                        let v = int16 (x.DataRegister reg)
                        v, 0, sprintf "D%u" reg, id
                    | 0b010uy, reg -> //(An)
                        let v = int16 (x.MMU.ReadByte(uint32 (x.AddressRegister reg)))
                        v, 0, sprintf "(a%u)" reg, id
                    | 0b011uy, reg -> //(An)+ - A7 postincrements by 2 (word-aligned stack), others by 1
                        let addr = x.AddressRegister reg
                        let v = int16 (x.MMU.ReadByte(uint32 addr))
                        let step = if reg = 0b111uy then 2 else 1
                        v, 0, sprintf "(a%u)+" reg, (fun (cpu: Cpu) -> cpu.WithAddressRegister reg (addr + step))
                    | 0b101uy, reg -> //(d16,An)
                        let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = x.AddressRegister reg + int displacement
                        let v = int16 (x.MMU.ReadByte(uint32 addr))
                        v, 1, sprintf "%i(a%u)" displacement reg, id
                    | 0b110uy, reg -> //(d8,An,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = x.AddressRegister reg + ext.Offset
                        let v = int16 (x.MMU.ReadByte(uint32 addr))
                        v, 1, x.DescribeIndexed reg ext, id
                    | 0b100uy, reg -> //-(An) - A7 predecrements by 2 (word-aligned stack), others by 1
                        let step = if reg = 0b111uy then 2 else 1
                        let addr = x.AddressRegister reg - step
                        let v = int16 (x.MMU.ReadByte(uint32 addr))
                        v, 0, sprintf "-(a%u)" reg, (fun (cpu: Cpu) -> cpu.WithAddressRegister reg addr)
                    | otherMode, otherReg ->
                        failwithf  "Move address mode %u, reg %u not implemented"
                            otherMode otherReg

                let destBase = x.PC + 2 + sourceExtWords * 2
                let x = sourceUpdate x

                match dMode with
                | 0b000uy -> //Dn
                    let currentValue = x.DataRegister dReg
                    let newValue = (currentValue &&& ~~~0xff) ||| (int source &&& 0xff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    let newCpu = {x.WithDataRegister dReg newValue with PC = destBase; CCR = ccr}
                    printfn "move.b %s,D%u" sourceDesc dReg
                    newCpu
                | 0b010uy ->
                    let destEA = uint32 (x.AddressRegister dReg)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase; CCR=ccr}
                    printfn "move.b %s,(a%u)" sourceDesc dReg
                    newCpu
                | 0b011uy -> //(An)+ - A7 postincrements by 2 (word-aligned stack), others by 1
                    let destEA = x.AddressRegister dReg
                    x.MMU.WriteByte (uint32 destEA) (byte source)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    let step = if dReg = 0b111uy then 2 else 1
                    let newCpu = x.WithAddressRegister dReg (destEA + step)
                    let newCpu = {newCpu with PC=destBase; CCR=ccr}
                    printfn "move.b %s,(a%u)+" sourceDesc dReg
                    newCpu
                | 0b101uy ->
                    let displacement = int16 (x.MMU.ReadWord(uint32 destBase))
                    let destEA = uint32 (x.AddressRegister dReg + int displacement)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase+2; CCR=ccr}
                    printfn "move.b %s,%i(a%i) == $%x" sourceDesc displacement dReg destEA
                    newCpu
                | 0b100uy -> //-(An) - A7 predecrements by 2 (word-aligned stack), others by 1
                    let step = if dReg = 0b111uy then 2 else 1
                    let destEA = x.AddressRegister dReg - step
                    x.MMU.WriteByte (uint32 destEA) (byte source)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    let newCpu = x.WithAddressRegister dReg destEA
                    let newCpu = {newCpu with PC=destBase; CCR=ccr}
                    printfn "move.b %s,-(a%u)" sourceDesc dReg
                    newCpu
                | 0b111uy when dReg = 0b001uy -> //(xxx).L
                    let destEA = uint32 (x.MMU.ReadLong(uint32 destBase))
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase+4; CCR=ccr}
                    printfn "move.b %s,$%x.l" sourceDesc destEA
                    newCpu
                | 0b110uy -> //(d8,An,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 destBase))
                    let destEA = uint32 (x.AddressRegister dReg + ext.Offset)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR (byte source)
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase+2; CCR=ccr}
                    printfn "move.b %s,%s" sourceDesc (x.DescribeIndexed dReg ext)
                    newCpu
                | _ -> failwithf "Move with dest mode %u dest reg %u not implemented" dMode dReg
                    
            | OperandSize.Word ->
                match sMode with
                | 0b111uy ->
                    match sReg with
                    | 0b100uy ->
                        //#imm
                        let immediate = (x.MMU.ReadWord(uint32 (x.PC+2)))
                        match dMode with
                        | 0b000uy -> //D
                            let currentValue = x.DataRegister dReg
                            let newValue = (currentValue &&& ~~~0xffff) ||| (immediate &&& 0xffff)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 immediate)
                            let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+4; CCR = ccr}
                            printfn "move.w #$%04x,D%i" immediate dReg
                            newCpu
                        | 0b001uy -> //MOVEA.W An, sign-extended, CCR unaffected
                            let signExtended = int (int16 immediate)
                            let newCpu = {x.WithAddressRegister dReg signExtended with PC = x.PC+4}
                            printfn "movea.w #$%04x,A%i" immediate dReg
                            newCpu
                        | 0b010uy -> //(An)
                            let destEA = uint32 (x.AddressRegister dReg)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 immediate)
                            x.MMU.WriteWord destEA (int16 immediate)
                            let newCpu = {x with PC = x.PC+4; CCR = ccr}
                            printfn "move.w #$%04x,(a%u)" immediate dReg
                            newCpu
                        | 0b100uy -> //-(An)
                            let destEA = x.AddressRegister dReg - 2
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 immediate)
                            x.MMU.WriteWord (uint32 destEA) (int16 immediate)
                            let newCpu = {x.WithAddressRegister dReg destEA with PC = x.PC+4; CCR = ccr}
                            printfn "move.w #$%04x,-(a%u)" immediate dReg
                            newCpu
                        | 0b101uy -> //(d16,An)
                            let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                            let destEA = uint32 (x.AddressRegister dReg + int displacement)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 immediate)
                            x.MMU.WriteWord destEA (int16 immediate)
                            let newCpu = {x with PC = x.PC+6; CCR = ccr}
                            printfn "move.w #$%04x,%i(a%u) == $%x" immediate displacement dReg destEA
                            newCpu
                        | 0b111uy when dReg = 0b001uy -> //(xxx).L
                            let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 immediate)
                            x.MMU.WriteWord destEA (int16 immediate)
                            let newCpu = {x with PC = x.PC+8; CCR = ccr}
                            printfn "move.w #$%04x,$%x.l" immediate destEA
                            newCpu
                        | _ -> failwith "Not implemented"
                    | 0b001uy -> //(xxx).L
                        let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                        let value = x.MMU.ReadWord addr
                        match dMode with
                        | 0b000uy -> //Dn
                            let currentValue = x.DataRegister dReg
                            let newValue = (currentValue &&& ~~~0xffff) ||| (value &&& 0xffff)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+6; CCR = ccr}
                            printfn "move.w $%x.l,D%u" addr dReg
                            newCpu
                        | 0b001uy -> //MOVEA.W An, sign-extended, CCR unaffected
                            let signExtended = int (int16 value)
                            let newCpu = {x.WithAddressRegister dReg signExtended with PC = x.PC+6}
                            printfn "movea.w $%x.l,A%u" addr dReg
                            newCpu
                        | 0b111uy when dReg = 0b001uy -> //(xxx).L
                            let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+6)))
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            x.MMU.WriteWord destEA (int16 value)
                            let newCpu = {x with PC = x.PC+10; CCR = ccr}
                            printfn "move.w $%x.l,$%x.l" addr destEA
                            newCpu
                        | 0b010uy -> //(An)
                            let destEA = uint32 (x.AddressRegister dReg)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            x.MMU.WriteWord destEA (int16 value)
                            let newCpu = {x with PC = x.PC+6; CCR = ccr}
                            printfn "move.w $%x.l,(a%u)" addr dReg
                            newCpu
                        | 0b100uy -> //-(An)
                            let destEA = x.AddressRegister dReg - 2
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            x.MMU.WriteWord (uint32 destEA) (int16 value)
                            let newCpu = {x.WithAddressRegister dReg destEA with PC = x.PC+6; CCR = ccr}
                            printfn "move.w $%x.l,-(a%u)" addr dReg
                            newCpu
                        | 0b101uy -> //(d16,An)
                            let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+6)))
                            let destEA = uint32 (x.AddressRegister dReg + int displacement)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            x.MMU.WriteWord destEA (int16 value)
                            let newCpu = {x with PC = x.PC+8; CCR = ccr}
                            printfn "move.w $%x.l,%i(a%u)" addr displacement dReg
                            newCpu
                        | 0b011uy -> //(An)+
                            let destAddress = x.AddressRegister dReg
                            x.MMU.WriteWord (uint32 destAddress) (int16 value)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            let newCpu = {x.WithAddressRegister dReg (destAddress + 2) with PC = x.PC+6; CCR = ccr}
                            printfn "move.w $%x.l,(a%u)+" addr dReg
                            newCpu
                        | _ -> failwith "Not implemented"
                    | 0b011uy -> //(d8,PC,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = (x.PC+2) + ext.Offset
                        let value = x.MMU.ReadWord(uint32 addr)
                        match dMode with
                        | 0b000uy -> //Dn
                            let currentValue = x.DataRegister dReg
                            let newValue = (currentValue &&& ~~~0xffff) ||| (value &&& 0xffff)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+4; CCR = ccr}
                            printfn "move.w %i(pc,%s%u.%s),D%u" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w") dReg
                            newCpu
                        | 0b001uy -> //MOVEA.W An, sign-extended, CCR unaffected
                            let signExtended = int (int16 value)
                            let newCpu = {x.WithAddressRegister dReg signExtended with PC = x.PC+4}
                            printfn "movea.w %i(pc,%s%u.%s),A%u" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w") dReg
                            newCpu
                        | 0b101uy -> //(d16,An)
                            let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                            let destEA = uint32 (x.AddressRegister dReg + int displacement)
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            x.MMU.WriteWord destEA (int16 value)
                            let newCpu = {x with PC = x.PC+6; CCR = ccr}
                            printfn "move.w %i(pc,%s%u.%s),%i(a%u)" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w") displacement dReg
                            newCpu
                        | _ -> failwith "Not implemented"
                    | _ -> failwith "Not implemented"
                | 0b001uy -> //An - a legal MOVE source (unlike MOVEA, which cares about the dest
                             //side only; reading an address register's low word is ordinary here)
                    let sourceContents = int16 (x.AddressRegister sReg)

                    match dMode with
                    | 0b000uy -> //Dn
                        let currentValue = x.DataRegister dReg
                        let newValue = (currentValue &&& ~~~0xffff) ||| (int sourceContents &&& 0xffff)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+2; CCR = ccr}
                        printfn "move.w A%u,D%u" sReg dReg
                        newCpu

                    | 0b010uy -> //(An)
                        let destEA = uint32 (x.AddressRegister dReg)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+2; CCR = ccr}
                        printfn "move.w A%u,(a%u)" sReg dReg
                        newCpu

                    | 0b111uy when dReg = 0b001uy -> //(xxx).L
                        let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+6; CCR = ccr}
                        printfn "move.w A%u,$%x.l" sReg destEA
                        newCpu

                    | 0b101uy -> //(d16,An)
                        let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let destEA = uint32 (x.AddressRegister dReg + int displacement)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+4; CCR = ccr}
                        printfn "move.w A%u,%i(a%u)" sReg displacement dReg
                        newCpu

                    | _ -> failwith "Not implemented"
                | 0b011uy -> //(AN)+
                    let sourceAddress = x.AddressRegister sReg
                    let sourceContents = int16 (x.MMU.ReadWord (uint32 sourceAddress))

                    match dMode with
                    | 0b011uy -> //(AN)+
                        let destAddress = x.AddressRegister dReg
                        x.MMU.WriteWord (uint32 destAddress) sourceContents

                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu =
                            (x.WithAddressRegister sReg (sourceAddress + 2))
                                .WithAddressRegister dReg (destAddress + 2)
                        let newCpu = {newCpu with PC = newCpu.PC + 2; CCR = ccr}
                        printfn "move.w (a%u)+,(a%u)+" sReg dReg
                        newCpu

                    | 0b000uy -> //Dn
                        let currentValue = x.DataRegister dReg
                        let newValue = (currentValue &&& ~~~0xffff) ||| (int sourceContents &&& 0xffff)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = (x.WithAddressRegister sReg (sourceAddress + 2)).WithDataRegister dReg newValue
                        let newCpu = {newCpu with PC = newCpu.PC + 2; CCR = ccr}
                        printfn "move.w (a%u)+,D%u" sReg dReg
                        newCpu

                    | 0b100uy -> //-(An)
                        let destAddress = x.AddressRegister dReg - 2
                        x.MMU.WriteWord (uint32 destAddress) sourceContents

                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu =
                            (x.WithAddressRegister sReg (sourceAddress + 2))
                                .WithAddressRegister dReg destAddress
                        let newCpu = {newCpu with PC = newCpu.PC + 2; CCR = ccr}
                        printfn "move.w (a%u)+,-(a%u)" sReg dReg
                        newCpu

                    | 0b010uy -> //(An)
                        let destAddress = x.AddressRegister dReg
                        x.MMU.WriteWord (uint32 destAddress) sourceContents

                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = x.WithAddressRegister sReg (sourceAddress + 2)
                        let newCpu = {newCpu with PC = newCpu.PC + 2; CCR = ccr}
                        printfn "move.w (a%u)+,(a%u)" sReg dReg
                        newCpu

                    | 0b111uy when dReg = 0b001uy -> //(xxx).L
                        let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister sReg (sourceAddress + 2) with PC = x.PC+6; CCR = ccr}
                        printfn "move.w (a%u)+,$%x.l" sReg destEA
                        newCpu

                    | 0b101uy -> //(d16,An)
                        let destDisplacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let destEA = uint32 (x.AddressRegister dReg + int destDisplacement)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister sReg (sourceAddress + 2) with PC = x.PC+4; CCR = ccr}
                        printfn "move.w (a%u)+,%i(a%u)" sReg destDisplacement dReg
                        newCpu

                    | _ -> failwith "Not implemented"
                | 0b000uy -> //Dn
                    let sourceContents = int16 (x.DataRegister sReg)

                    match dMode with
                    | 0b000uy -> //Dn
                        let currentValue = x.DataRegister dReg
                        let newValue = (currentValue &&& ~~~0xffff) ||| (int sourceContents &&& 0xffff)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+2; CCR = ccr}
                        printfn "move.w D%u,D%u" sReg dReg
                        newCpu

                    | 0b001uy -> //MOVEA.W An, sign-extended, CCR unaffected
                        let signExtended = int sourceContents
                        let newCpu = {x.WithAddressRegister dReg signExtended with PC = x.PC+2}
                        printfn "movea.w D%u,A%u" sReg dReg
                        newCpu

                    | 0b010uy -> //(An)
                        let destAddress = x.AddressRegister dReg
                        x.MMU.WriteWord (uint32 destAddress) sourceContents

                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC + 2; CCR = ccr}
                        printfn "move.w D%u,(a%u)" sReg dReg
                        newCpu

                    | 0b011uy -> //(AN)+
                        let destAddress = x.AddressRegister dReg
                        x.MMU.WriteWord (uint32 destAddress) sourceContents

                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = x.WithAddressRegister dReg (destAddress + 2)
                        let newCpu = {newCpu with PC = newCpu.PC + 2; CCR = ccr}
                        printfn "move.w D%u,(a%u)+" sReg dReg
                        newCpu

                    | 0b100uy -> //-(An)
                        let destAddress = x.AddressRegister dReg - 2
                        x.MMU.WriteWord (uint32 destAddress) sourceContents

                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = x.WithAddressRegister dReg destAddress
                        let newCpu = {newCpu with PC = newCpu.PC + 2; CCR = ccr}
                        printfn "move.w D%u,-(a%u)" sReg dReg
                        newCpu

                    | 0b111uy when dReg = 0b001uy -> //(xxx).L
                        let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+6; CCR = ccr}
                        printfn "move.w D%u,$%x.l" sReg destEA
                        newCpu

                    | 0b101uy -> //(d16,An)
                        let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let destEA = uint32 (x.AddressRegister dReg + int displacement)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+4; CCR = ccr}
                        printfn "move.w D%u,%i(a%u)" sReg displacement dReg
                        newCpu

                    | 0b110uy -> //(d8,An,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let destEA = uint32 (x.AddressRegister dReg + ext.Offset)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+4; CCR = ccr}
                        printfn "move.w D%u,%s" sReg (x.DescribeIndexed dReg ext)
                        newCpu

                    | _ -> failwith "Not implemented"
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister sReg + int displacement
                    let sourceContents = int16 (x.MMU.ReadWord(uint32 addr))

                    match dMode with
                    | 0b000uy -> //Dn
                        let currentValue = x.DataRegister dReg
                        let newValue = (currentValue &&& ~~~0xffff) ||| (int sourceContents &&& 0xffff)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %i(a%u),D%u" displacement sReg dReg
                        newCpu

                    | 0b001uy -> //MOVEA.W An, sign-extended, CCR unaffected
                        let signExtended = int sourceContents
                        let newCpu = {x.WithAddressRegister dReg signExtended with PC = x.PC+4}
                        printfn "movea.w %i(a%u),A%u" displacement sReg dReg
                        newCpu

                    | 0b111uy when dReg = 0b001uy -> //(xxx).L
                        let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+8; CCR = ccr}
                        printfn "move.w %i(a%u),$%x.l" displacement sReg destEA
                        newCpu

                    | 0b100uy -> //-(An)
                        let destEA = x.AddressRegister dReg - 2
                        x.MMU.WriteWord (uint32 destEA) sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister dReg destEA with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %i(a%u),-(a%u)" displacement sReg dReg
                        newCpu

                    | 0b101uy -> //(d16,An)
                        let destDisplacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                        let destEA = uint32 (x.AddressRegister dReg + int destDisplacement)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+6; CCR = ccr}
                        printfn "move.w %i(a%u),%i(a%u)" displacement sReg destDisplacement dReg
                        newCpu

                    | 0b010uy -> //(An)
                        let destEA = uint32 (x.AddressRegister dReg)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %i(a%u),(a%u)" displacement sReg dReg
                        newCpu

                    | 0b011uy -> //(An)+
                        let destAddress = x.AddressRegister dReg
                        x.MMU.WriteWord (uint32 destAddress) sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister dReg (destAddress + 2) with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %i(a%u),(a%u)+" displacement sReg dReg
                        newCpu

                    | _ -> failwith "Not implemented"
                | 0b010uy -> //(An)
                    let sourceContents = int16 (x.MMU.ReadWord(uint32 (x.AddressRegister sReg)))

                    match dMode with
                    | 0b000uy -> //Dn
                        let currentValue = x.DataRegister dReg
                        let newValue = (currentValue &&& ~~~0xffff) ||| (int sourceContents &&& 0xffff)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+2; CCR = ccr}
                        printfn "move.w (a%u),D%u" sReg dReg
                        newCpu

                    | 0b101uy -> //(d16,An)
                        let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let destEA = uint32 (x.AddressRegister dReg + int displacement)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        x.MMU.WriteWord destEA sourceContents
                        let newCpu = {x with PC = x.PC+4; CCR = ccr}
                        printfn "move.w (a%u),%i(a%u)" sReg displacement dReg
                        newCpu

                    | 0b011uy -> //(An)+
                        let destAddress = x.AddressRegister dReg
                        x.MMU.WriteWord (uint32 destAddress) sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister dReg (destAddress + 2) with PC = x.PC+2; CCR = ccr}
                        printfn "move.w (a%u),(a%u)+" sReg dReg
                        newCpu

                    | 0b010uy -> //(An)
                        let destEA = uint32 (x.AddressRegister dReg)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+2; CCR = ccr}
                        printfn "move.w (a%u),(a%u)" sReg dReg
                        newCpu

                    | 0b100uy -> //-(An)
                        let destEA = x.AddressRegister dReg - 2
                        x.MMU.WriteWord (uint32 destEA) sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister dReg destEA with PC = x.PC+2; CCR = ccr}
                        printfn "move.w (a%u),-(a%u)" sReg dReg
                        newCpu

                    | 0b111uy when dReg = 0b001uy -> //(xxx).L
                        let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+6; CCR = ccr}
                        printfn "move.w (a%u),$%x.l" sReg destEA
                        newCpu

                    | _ -> failwith "Not implemented"
                | 0b110uy -> //(d8,An,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister sReg + ext.Offset)
                    let sourceContents = int16 (x.MMU.ReadWord addr)
                    let srcDesc = x.DescribeIndexed sReg ext

                    match dMode with
                    | 0b000uy -> //Dn
                        let currentValue = x.DataRegister dReg
                        let newValue = (currentValue &&& ~~~0xffff) ||| (int sourceContents &&& 0xffff)
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithDataRegister dReg newValue with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %s,D%u" srcDesc dReg
                        newCpu

                    | 0b001uy -> //MOVEA.W An, sign-extended, CCR unaffected
                        let signExtended = int sourceContents
                        let newCpu = {x.WithAddressRegister dReg signExtended with PC = x.PC+4}
                        printfn "movea.w %s,A%u" srcDesc dReg
                        newCpu

                    | 0b111uy when dReg = 0b001uy -> //(xxx).L
                        let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+8; CCR = ccr}
                        printfn "move.w %s,$%x.l" srcDesc destEA
                        newCpu

                    | 0b100uy -> //-(An)
                        let destEA = x.AddressRegister dReg - 2
                        x.MMU.WriteWord (uint32 destEA) sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x.WithAddressRegister dReg destEA with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %s,-(a%u)" srcDesc dReg
                        newCpu

                    | 0b101uy -> //(d16,An)
                        let destDisplacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                        let destEA = uint32 (x.AddressRegister dReg + int destDisplacement)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+6; CCR = ccr}
                        printfn "move.w %s,%i(a%u)" srcDesc destDisplacement dReg
                        newCpu

                    | 0b010uy -> //(An)
                        let destEA = uint32 (x.AddressRegister dReg)
                        x.MMU.WriteWord destEA sourceContents
                        let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR sourceContents
                        let newCpu = {x with PC = x.PC+4; CCR = ccr}
                        printfn "move.w %s,(a%u)" srcDesc dReg
                        newCpu

                    | _ -> failwith "Not implemented"
                | _ ->    failwith "Not implemented"
            | OperandSize.Long ->
                let source, sourceExtWords, sourceDesc, sourceUpdate =
                    match sMode, sReg with
                    | 0b111uy, 0b100uy -> //#imm
                        let v = x.MMU.ReadLong(uint32 (x.PC+2))
                        v, 2, sprintf "#$%x" v, id
                    | 0b111uy, 0b010uy -> //(d16,PC)
                        let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = (x.PC+2) + int displacement
                        let v = x.MMU.ReadLong(uint32 addr)
                        v, 1, sprintf "%i(pc)" displacement, id
                    | 0b111uy, 0b001uy -> //(xxx).L
                        let addr = x.MMU.ReadLong(uint32 (x.PC+2))
                        let v = x.MMU.ReadLong(uint32 addr)
                        v, 2, sprintf "$%x.l" addr, id
                    | 0b111uy, 0b011uy -> //(d8,PC,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = (x.PC+2) + ext.Offset
                        let v = x.MMU.ReadLong(uint32 addr)
                        v, 1, sprintf "%i(pc,%s%u.%s)" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w"), id
                    | 0b000uy, reg -> //Dn
                        x.DataRegister reg, 0, sprintf "D%u" reg, id
                    | 0b001uy, reg -> //An
                        x.AddressRegister reg, 0, sprintf "A%u" reg, id
                    | 0b010uy, reg -> //(An)
                        let v = x.MMU.ReadLong(uint32 (x.AddressRegister reg))
                        v, 0, sprintf "(a%u)" reg, id
                    | 0b011uy, reg -> //(An)+
                        let addr = x.AddressRegister reg
                        let v = x.MMU.ReadLong(uint32 addr)
                        v, 0, sprintf "(a%u)+" reg, (fun (cpu: Cpu) -> cpu.WithAddressRegister reg (addr + 4))
                    | 0b101uy, reg -> //(d16,An)
                        let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = x.AddressRegister reg + int displacement
                        let v = x.MMU.ReadLong(uint32 addr)
                        v, 1, sprintf "%i(a%u)" displacement reg, id
                    | 0b110uy, reg -> //(d8,An,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = x.AddressRegister reg + ext.Offset
                        let v = x.MMU.ReadLong(uint32 addr)
                        v, 1, x.DescribeIndexed reg ext, id
                    | otherMode, otherReg ->
                        failwithf "Move.l address mode %u, reg %u not implemented"
                            otherMode otherReg

                let destBase = x.PC + 2 + sourceExtWords * 2
                let x = sourceUpdate x

                match dMode with
                | 0b000uy -> //Dn
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    let newCpu = {x.WithDataRegister dReg source with PC = destBase; CCR = ccr}
                    printfn "move.l %s,D%u" sourceDesc dReg
                    newCpu
                | 0b001uy -> //MOVEA.L An, CCR unaffected
                    let newCpu = {x.WithAddressRegister dReg source with PC = destBase}
                    printfn "movea.l %s,A%u" sourceDesc dReg
                    newCpu
                | 0b010uy -> //(An)
                    let destEA = uint32 (x.AddressRegister dReg)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    x.MMU.WriteLong destEA source
                    let newCpu = {x with PC=destBase; CCR=ccr}
                    printfn "move.l %s,(a%u)" sourceDesc dReg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 destBase))
                    let destEA = uint32 (x.AddressRegister dReg + int displacement)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    x.MMU.WriteLong destEA source
                    let newCpu = {x with PC=destBase+2; CCR=ccr}
                    printfn "move.l %s,%i(a%i) == $%x" sourceDesc displacement dReg destEA
                    newCpu
                | 0b011uy -> //(An)+
                    let destEA = x.AddressRegister dReg
                    x.MMU.WriteLong (uint32 destEA) source
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    let newCpu = x.WithAddressRegister dReg (destEA + 4)
                    let newCpu = {newCpu with PC=destBase; CCR=ccr}
                    printfn "move.l %s,(a%u)+" sourceDesc dReg
                    newCpu
                | 0b100uy -> //-(An)
                    let destEA = x.AddressRegister dReg - 4
                    x.MMU.WriteLong (uint32 destEA) source
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    let newCpu = {x.WithAddressRegister dReg destEA with PC=destBase; CCR=ccr}
                    printfn "move.l %s,-(a%u)" sourceDesc dReg
                    newCpu
                | 0b111uy when dReg = 0b001uy -> //(xxx).L
                    let destEA = uint32 (x.MMU.ReadLong(uint32 destBase))
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    x.MMU.WriteLong destEA source
                    let newCpu = {x with PC=destBase+4; CCR=ccr}
                    printfn "move.l %s,$%x.l" sourceDesc destEA
                    newCpu
                | 0b110uy -> //(d8,An,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 destBase))
                    let destEA = uint32 (x.AddressRegister dReg + ext.Offset)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR source
                    x.MMU.WriteLong destEA source
                    let newCpu = {x with PC=destBase+2; CCR=ccr}
                    printfn "move.l %s,%s" sourceDesc (x.DescribeIndexed dReg ext)
                    newCpu
                | _ -> failwithf "Move.l dest mode %u dest reg %u not implemented" dMode dReg
            | other -> failwithf "Move invalid operand size %A" other

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
                let newCcr = (x.CCR &&& ~~~0xffs) ||| (source &&& 0xffs)
                printfn "move D%u,ccr" register
                {x with PC = x.PC+2; CCR = newCcr}
            | 0b111uy when register = 0b100uy -> //#imm
                let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let newCcr = (x.CCR &&& ~~~0xffs) ||| (source &&& 0xffs)
                printfn "move #$%x,ccr" source
                {x with PC = x.PC+4; CCR = newCcr}
            | _ -> failwithf "move2ccr not implemented for mode %x" mode

        | Move2SR(mode, register) ->
            //Hack, not sure about this
            //Goes through WithSR (not a plain `CCR = newCcr`) because this instruction can change
            //the S bit directly, without going through TRAP/RTE - real TOS's own boot code does
            //exactly this as its very first instruction (`move #$2700,sr`), which must swap A7
            //over to the supervisor stack same as a trap would (see USP/SSP field comment).
            if mode = 0x7 && register = 0b100 then
                //load data
                let register = int16 (x.MMU.ReadWord (uint32 (x.PC+2)))
                printfn "move #%0x, sr" register
                {x.WithSR register with PC = x.PC + 4}
            elif mode = 0x0 then //Dn
                let reg = byte register
                let newCcr = int16 (x.DataRegister reg)
                printfn "move D%u,sr" reg
                {x.WithSR newCcr with PC = x.PC + 2}
            elif mode = 0x3 then //(An)+
                let reg = byte register
                let addr = x.AddressRegister reg
                let newCcr = int16 (x.MMU.ReadWord(uint32 addr))
                let newCpu = {(x.WithSR newCcr).WithAddressRegister reg (addr + 2) with PC = x.PC + 2}
                printfn "move (a%u)+,sr" reg
                newCpu
            elif mode = 0x7 && register = 0b001 then //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let newCcr = int16 (x.MMU.ReadWord addr)
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

        | NEG(size, eamode, eareg) ->
            //Two's complement negation (0 - operand). Reuses the existing Subtract_IgnoringX_*
            //helpers for N/Z/V/C (dest=0), then sets X to match C - the one real difference from
            //a plain CMP/SUB-style subtract: X isn't ignored here, it mirrors the result's carry.
            match eamode, size with
            | 0b000uy, 0b10uy -> //Dn, long
                let source = x.DataRegister eareg
                let result = 0 - source
                let ccr = CCR.Subtract_IgnoringX x.CCR 0 source
                let ccr = if ccr &&& 0x1s <> 0s then ccr ||| 0x10s else ccr &&& ~~~0x10s
                let newCpu = {x.WithDataRegister eareg result with PC = x.PC+2; CCR = ccr}
                printfn "neg.l D%u" eareg
                newCpu
            | 0b000uy, 0b01uy -> //Dn, word
                let source = int16 (x.DataRegister eareg)
                let result = int16 (0 - int source)
                let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (int result &&& 0xffff)
                let ccr = CCR.Subtract_IgnoringX_Word x.CCR 0s source
                let ccr = if ccr &&& 0x1s <> 0s then ccr ||| 0x10s else ccr &&& ~~~0x10s
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                printfn "neg.w D%u" eareg
                newCpu
            | 0b000uy, 0b00uy -> //Dn, byte
                let source = byte (x.DataRegister eareg)
                let result = byte (0 - int source)
                let newValue = (x.DataRegister eareg &&& ~~~0xff) ||| int result
                let ccr = CCR.Subtract_IgnoringX_Byte x.CCR 0uy source
                let ccr = if ccr &&& 0x1s <> 0s then ccr ||| 0x10s else ccr &&& ~~~0x10s
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                printfn "neg.b D%u" eareg
                newCpu
            | 0b101uy, 0b01uy -> //(d16,An), word
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = uint32 (x.AddressRegister eareg + int displacement)
                let source = int16 (x.MMU.ReadWord addr)
                let result = int16 (0 - int source)
                let ccr = CCR.Subtract_IgnoringX_Word x.CCR 0s source
                let ccr = if ccr &&& 0x1s <> 0s then ccr ||| 0x10s else ccr &&& ~~~0x10s
                x.MMU.WriteWord addr result
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "neg.w %i(a%u)" displacement eareg
                newCpu
            | _ -> failwithf "neg: not implemented for mode %x size %x" eamode size

        | NOT(size, eamode, eareg) ->
            //One's complement. CCR: N/Z from result, V/C cleared, X unaffected - same helper
            //shape as CLR uses, just complementing instead of zeroing.
            match eamode, size with
            | 0b000uy, 0b10uy -> //Dn, long
                let result = ~~~(x.DataRegister eareg)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                let newCpu = {x.WithDataRegister eareg result with PC = x.PC+2; CCR = ccr}
                printfn "not.l D%u" eareg
                newCpu
            | 0b000uy, 0b01uy -> //Dn, word
                let currentValue = x.DataRegister eareg
                let result = ~~~(int16 currentValue)
                let newValue = (currentValue &&& ~~~0xffff) ||| (int result &&& 0xffff)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                printfn "not.w D%u" eareg
                newCpu
            | 0b000uy, 0b00uy -> //Dn, byte
                let currentValue = x.DataRegister eareg
                let result = ~~~(byte currentValue)
                let newValue = (currentValue &&& ~~~0xff) ||| int result
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                printfn "not.b D%u" eareg
                newCpu
            | _ -> failwithf "not: not implemented for mode %x size %x" eamode size

        | CLR(size, eamode, eareg) ->
            match eamode, size with
            | 0b011uy, 0b10uy -> //(An)+, long
                let addr = x.AddressRegister eareg
                x.MMU.WriteLong (uint32 addr) 0
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x.WithAddressRegister eareg (addr+4) with PC = x.PC+2; CCR = ccr}
                printfn "clr.l (a%u)+" eareg
                newCpu
            | 0b000uy, 0b10uy -> //Dn, long
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x.WithDataRegister eareg 0 with PC = x.PC+2; CCR = ccr}
                printfn "clr.l D%u" eareg
                newCpu
            | 0b000uy, 0b01uy -> //Dn, word
                let currentValue = x.DataRegister eareg
                let newValue = currentValue &&& ~~~0xffff
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                printfn "clr.w D%u" eareg
                newCpu
            | 0b010uy, 0b00uy -> //(An), byte
                let addr = x.AddressRegister eareg
                x.MMU.WriteByte (uint32 addr) 0uy
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR 0uy
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "clr.b (a%u)" eareg
                newCpu
            | 0b010uy, 0b01uy -> //(An), word
                let addr = x.AddressRegister eareg
                x.MMU.WriteWord (uint32 addr) 0s
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "clr.w (a%u)" eareg
                newCpu
            | 0b010uy, 0b10uy -> //(An), long
                let addr = x.AddressRegister eareg
                x.MMU.WriteLong (uint32 addr) 0
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "clr.l (a%u)" eareg
                newCpu
            | 0b100uy, 0b01uy -> //-(An), word
                let addr = x.AddressRegister eareg - 2
                x.MMU.WriteWord (uint32 addr) 0s
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                let newCpu = {x.WithAddressRegister eareg addr with PC = x.PC+2; CCR = ccr}
                printfn "clr.w -(a%u)" eareg
                newCpu
            | 0b100uy, 0b10uy -> //-(An), long
                let addr = x.AddressRegister eareg - 4
                x.MMU.WriteLong (uint32 addr) 0
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x.WithAddressRegister eareg addr with PC = x.PC+2; CCR = ccr}
                printfn "clr.l -(a%u)" eareg
                newCpu
            | 0b101uy, 0b01uy -> //(d16,An), word
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                x.MMU.WriteWord (uint32 addr) 0s
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "clr.w %i(a%u)" displacement eareg
                newCpu
            | 0b101uy, 0b10uy -> //(d16,An), long
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                x.MMU.WriteLong (uint32 addr) 0
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "clr.l %i(a%u)" displacement eareg
                newCpu
            | 0b101uy, 0b00uy -> //(d16,An), byte
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                x.MMU.WriteByte (uint32 addr) 0uy
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR 0uy
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "clr.b %i(a%u)" displacement eareg
                newCpu
            | 0b111uy, 0b01uy when eareg = 0b001uy -> //(xxx).L, word
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                x.MMU.WriteWord addr 0s
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                let newCpu = {x with PC = x.PC+6; CCR = ccr}
                printfn "clr.w $%x.l" addr
                newCpu
            | 0b111uy, 0b10uy when eareg = 0b001uy -> //(xxx).L, long
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                x.MMU.WriteLong addr 0
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x with PC = x.PC+6; CCR = ccr}
                printfn "clr.l $%x.l" addr
                newCpu
            | 0b111uy, 0b00uy when eareg = 0b001uy -> //(xxx).L, byte
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                x.MMU.WriteByte addr 0uy
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR 0uy
                let newCpu = {x with PC = x.PC+6; CCR = ccr}
                printfn "clr.b $%x.l" addr
                newCpu
            | _ -> failwithf "clr: not implemented for mode %x size %x" eamode size

        | TST(size, eamode, eareg) ->
            //TST: sets N/Z from the operand, clears V/C, X unaffected. CCR-only, no write-back.
            match eamode, size with
            | 0b000uy, 0b10uy -> //Dn, long
                let value = x.DataRegister eareg
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR value
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "tst.l D%u" eareg
                newCpu
            | 0b000uy, 0b01uy -> //Dn, word
                let value = int16 (x.DataRegister eareg)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR value
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "tst.w D%u" eareg
                newCpu
            | 0b000uy, 0b00uy -> //Dn, byte
                let value = byte (x.DataRegister eareg)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR value
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "tst.b D%u" eareg
                newCpu
            | 0b010uy, 0b10uy -> //(An), long
                let addr = x.AddressRegister eareg
                let value = x.MMU.ReadLong(uint32 addr)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR value
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "tst.l (a%u)" eareg
                newCpu
            | 0b010uy, 0b01uy -> //(An), word
                let addr = x.AddressRegister eareg
                let value = int16 (x.MMU.ReadWord(uint32 addr))
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR value
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "tst.w (a%u)" eareg
                newCpu
            | 0b010uy, 0b00uy -> //(An), byte
                let addr = x.AddressRegister eareg
                let value = x.MMU.ReadByte(uint32 addr)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR value
                let newCpu = {x with PC = x.PC+2; CCR = ccr}
                printfn "tst.b (a%u)" eareg
                newCpu
            | 0b011uy, 0b10uy -> //(An)+, long
                let addr = x.AddressRegister eareg
                let value = x.MMU.ReadLong(uint32 addr)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR value
                let newCpu = {x.WithAddressRegister eareg (addr+4) with PC = x.PC+2; CCR = ccr}
                printfn "tst.l (a%u)+" eareg
                newCpu
            | 0b011uy, 0b01uy -> //(An)+, word
                let addr = x.AddressRegister eareg
                let value = int16 (x.MMU.ReadWord(uint32 addr))
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR value
                let newCpu = {x.WithAddressRegister eareg (addr+2) with PC = x.PC+2; CCR = ccr}
                printfn "tst.w (a%u)+" eareg
                newCpu
            | 0b101uy, 0b01uy -> //(d16,An), word
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let value = int16 (x.MMU.ReadWord(uint32 addr))
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR value
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "tst.w %i(a%u)" displacement eareg
                newCpu
            | 0b101uy, 0b10uy -> //(d16,An), long
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let value = x.MMU.ReadLong(uint32 addr)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR value
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "tst.l %i(a%u)" displacement eareg
                newCpu
            | 0b111uy, 0b01uy when eareg = 0b001uy -> //(xxx).L, word
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let value = int16 (x.MMU.ReadWord addr)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR value
                let newCpu = {x with PC = x.PC+6; CCR = ccr}
                printfn "tst.w $%x.l" addr
                newCpu
            | 0b111uy, 0b00uy when eareg = 0b001uy -> //(xxx).L, byte
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let value = x.MMU.ReadByte addr
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR value
                let newCpu = {x with PC = x.PC+6; CCR = ccr}
                printfn "tst.b $%x.l" addr
                newCpu
            | 0b111uy, 0b10uy when eareg = 0b001uy -> //(xxx).L, long
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let value = x.MMU.ReadLong addr
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR value
                let newCpu = {x with PC = x.PC+6; CCR = ccr}
                printfn "tst.l $%x.l" addr
                newCpu
            | 0b110uy, 0b10uy -> //(d8,An,Xn), long
                let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + ext.Offset
                let value = x.MMU.ReadLong(uint32 addr)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR value
                let newCpu = {x with PC = x.PC+4; CCR = ccr}
                printfn "tst.l %s" (x.DescribeIndexed eareg ext)
                newCpu
            | _ -> failwithf "tst: not implemented for mode %x size %x" eamode size

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
            match eamode with
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = x.MMU.ReadLong(uint32 (x.PC+2))
                let newSP = x.A7 - 4
                x.MMU.WriteLong (uint32 newSP) addr
                printfn "pea $%x.l" addr
                {x with PC = x.PC+6; A7 = newSP}
            | 0b111uy when eareg = 0b010uy -> //(d16,PC)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = uint32 ((x.PC+2) + int displacement)
                let newSP = x.A7 - 4
                x.MMU.WriteLong (uint32 newSP) (int addr)
                printfn "pea %i(pc) == $%x" displacement addr
                {x with PC = x.PC+4; A7 = newSP}
            | _ -> failwithf "pea not implemented for eamode %x" eamode

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
            let sr = int16 (x.MMU.ReadWord(uint32 x.A7))
            let pc = x.MMU.ReadLong(uint32 (x.A7+2))
            let poppedCpu = {x with A7 = x.A7 + 6}
            let newCpu = {poppedCpu.WithSR sr with PC = pc}
            printfn "rte"
            newCpu

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
            x.MMU.WriteLong (uint32 newSP) (x.AddressRegister register)
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
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest (int16 amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "addq.w #%u,D%u" amount eareg
                    newCpu
                | 0b00uy -> //byte
                    let dest = byte (x.DataRegister eareg)
                    let result = dest + byte amount
                    let ccr = CCR.Add_IgnoringX_Byte x.CCR dest (byte amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xff) ||| int result
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "addq.b #%u,D%u" amount eareg
                    newCpu
                | _ -> //long
                    let dest = x.DataRegister eareg
                    let result = dest + amount
                    let ccr = CCR.Add_IgnoringX x.CCR dest amount
                    let newCpu = {x.WithDataRegister eareg result with PC = x.PC+2; CCR = ccr}
                    printfn "addq.l #%u,D%u" amount eareg
                    newCpu
            | 0b010uy -> //(An)
                let addr = x.AddressRegister eareg
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord(uint32 addr))
                    let result = dest + int16 amount
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord (uint32 addr) result
                    printfn "addq.w #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let result = dest + byte amount
                    let ccr = CCR.Add_IgnoringX_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte (uint32 addr) result
                    printfn "addq.b #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let result = dest + amount
                    let ccr = CCR.Add_IgnoringX x.CCR dest amount
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
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord (uint32 addr) result
                    printfn "addq.w #%u,%i(a%u)" amount displacement eareg
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let result = dest + byte amount
                    let ccr = CCR.Add_IgnoringX_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte (uint32 addr) result
                    printfn "addq.b #%u,%i(a%u)" amount displacement eareg
                    {x with PC = x.PC+4; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let result = dest + amount
                    let ccr = CCR.Add_IgnoringX x.CCR dest amount
                    x.MMU.WriteLong (uint32 addr) result
                    printfn "addq.l #%u,%i(a%u)" amount displacement eareg
                    {x with PC = x.PC+4; CCR = ccr}
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + int16 amount
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord addr result
                    printfn "addq.w #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte addr
                    let result = dest + byte amount
                    let ccr = CCR.Add_IgnoringX_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte addr result
                    printfn "addq.b #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong addr
                    let result = dest + amount
                    let ccr = CCR.Add_IgnoringX x.CCR dest amount
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest (int16 amount)
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                    printfn "subq.w #%u,D%u" amount eareg
                    newCpu
                | 0b10uy -> //long
                    let dest = x.DataRegister eareg
                    let result = dest - amount
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest amount
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord (uint32 addr) result
                    printfn "subq.w #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte(uint32 addr)
                    let result = dest - byte amount
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte (uint32 addr) result
                    printfn "subq.b #%u,(a%u)" amount eareg
                    {x with PC = x.PC+2; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong(uint32 addr)
                    let result = dest - amount
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest amount
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "subq.w #%u,%i(a%u)" amount displacement eareg
                    newCpu
                | 0b10uy -> //long
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = x.MMU.ReadLong addr
                    let result = dest - amount
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest amount
                    x.MMU.WriteLong addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "subq.l #%u,%i(a%u)" amount displacement eareg
                    newCpu
                | _ -> failwithf "subq not implemented for size %x on (d16,An)" size
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                match size with
                | 0b01uy -> //word
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - int16 amount
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest (int16 amount)
                    x.MMU.WriteWord addr result
                    printfn "subq.w #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b00uy -> //byte
                    let dest = x.MMU.ReadByte addr
                    let result = dest - byte amount
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest (byte amount)
                    x.MMU.WriteByte addr result
                    printfn "subq.b #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> //long
                    let dest = x.MMU.ReadLong addr
                    let result = dest - amount
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest amount
                    x.MMU.WriteLong addr result
                    printfn "subq.l #%u,$%x.l" amount addr
                    {x with PC = x.PC+6; CCR = ccr}
            | _ -> failwithf "subq not implemented for eamode %x" eamode

        | Scc(cond, eamode, eareg) ->
            //Scc: sets the byte at <ea> to $FF if cond is true, $00 otherwise. CCR unaffected.
            let value = if x.EvaluateCondition cond then 0xffuy else 0x00uy
            match eamode with
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let destEA = uint32 (x.AddressRegister eareg + int displacement)
                x.MMU.WriteByte destEA value
                printfn "s%s %i(a%u)" (conditionName cond) displacement eareg
                {x with PC = x.PC+4}
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                x.MMU.WriteByte destEA value
                printfn "s%s $%x.l" (conditionName cond) destEA
                {x with PC = x.PC+6}
            | 0b100uy -> //-(An) - A7 predecrements by 2 (word-aligned stack), others by 1
                let step = if eareg = 0b111uy then 2 else 1
                let destEA = x.AddressRegister eareg - step
                x.MMU.WriteByte (uint32 destEA) value
                let newCpu = x.WithAddressRegister eareg destEA
                printfn "s%s -(a%u)" (conditionName cond) eareg
                {newCpu with PC = x.PC+2}
            | 0b010uy -> //(An)
                let destEA = uint32 (x.AddressRegister eareg)
                x.MMU.WriteByte destEA value
                printfn "s%s (a%u)" (conditionName cond) eareg
                {x with PC = x.PC+2}
            | 0b000uy -> //Dn - only the low byte is affected
                let newValue = (x.DataRegister eareg &&& ~~~0xff) ||| int value
                let newCpu = x.WithDataRegister eareg newValue
                printfn "s%s D%u" (conditionName cond) eareg
                {newCpu with PC = x.PC+2}
            | _ -> failwithf "Scc eamode %u not implemented" eamode

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
            let doDivide divisor pcAdvance desc =
                if divisor = 0u then failwith "DIVU: divide by zero (trap not implemented)"
                let dividend = uint32 (x.DataRegister register)
                let quotient = dividend / divisor
                let remainder = dividend % divisor
                if quotient > 0xffffu then failwith "DIVU: quotient overflow (V flag not implemented)"
                let result = int ((remainder <<< 16) ||| quotient)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 quotient)
                let newCpu = {x.WithDataRegister register result with PC = x.PC + pcAdvance; CCR = ccr}
                printfn "divu.w %s,D%u" desc register
                newCpu
            match eamode with
            | 0b000uy -> //Dn
                doDivide (uint32 (uint16 (x.DataRegister eareg))) 2 (sprintf "D%u" eareg)
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let divisor = uint32 (uint16 (x.MMU.ReadWord(uint32 addr)))
                doDivide divisor 4 (sprintf "%i(a%u)" displacement eareg)
            | _ -> failwithf "divu.w not implemented for eamode %x" eamode

        | DIVS(register, eamode, eareg) ->
            //Truncating division/remainder (F#'s / and % on signed ints truncate toward zero) is
            //exactly real 68000 DIVS.W semantics: quotient truncates toward zero, remainder takes
            //the dividend's sign - so no extra sign-fixup is needed beyond what DIVU already does.
            let doDivide (divisor: int16) pcAdvance desc =
                if divisor = 0s then failwith "DIVS: divide by zero (trap not implemented)"
                let dividend = x.DataRegister register
                let quotient = dividend / int divisor
                let remainder = dividend % int divisor
                if quotient > 32767 || quotient < -32768 then failwith "DIVS: quotient overflow (V flag not implemented)"
                let result = ((remainder &&& 0xffff) <<< 16) ||| (quotient &&& 0xffff)
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 quotient)
                let newCpu = {x.WithDataRegister register result with PC = x.PC + pcAdvance; CCR = ccr}
                printfn "divs.w %s,D%u" desc register
                newCpu
            match eamode with
            | 0b000uy -> //Dn
                doDivide (int16 (x.DataRegister eareg)) 2 (sprintf "D%u" eareg)
            | 0b111uy when eareg = 0b100uy -> //#imm
                let divisor = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                doDivide divisor 4 (sprintf "#$%x" divisor)
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let addr = x.AddressRegister eareg + int displacement
                let divisor = int16 (x.MMU.ReadWord(uint32 addr))
                doDivide divisor 4 (sprintf "%i(a%u)" displacement eareg)
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                let divisor = int16 (x.MMU.ReadWord addr)
                doDivide divisor 6 (sprintf "$%x.l" addr)
            | _ -> failwithf "divs.w not implemented for eamode %x" eamode

        | OR(register, opmode, eamode, eareg) ->
            match opmode with
            | 0b000uy -> //OR.B ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = byte (x.DataRegister eareg)
                    let dest = byte (x.DataRegister register)
                    let result = source ||| dest
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                    printfn "or.b D%u,D%u" eareg register
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister register)
                    let result = source ||| dest
                    let newValue = (x.DataRegister register &&& ~~~0xff) ||| int result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "or.b #$%x,D%u" source register
                    newCpu
                | _ -> failwithf "or.b(ea->dn) not implemented for eamode %x" eamode
            | 0b001uy -> //OR.W ea+Dn->Dn
                match eamode with
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister register)
                    let result = source ||| dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "or.w %i(a%u),D%u" displacement eareg register
                    newCpu
                | 0b000uy -> //Dn
                    let source = int16 (x.DataRegister eareg)
                    let dest = int16 (x.DataRegister register)
                    let result = source ||| dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+2; CCR = ccr}
                    printfn "or.w D%u,D%u" eareg register
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister register)
                    let result = source ||| dest
                    let newValue = (x.DataRegister register &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x.WithDataRegister register newValue with PC = x.PC+4; CCR = ccr}
                    printfn "or.w #$%x,D%u" source register
                    newCpu
                | _ -> failwithf "or.w(ea->dn) not implemented for eamode %x" eamode
            | 0b100uy -> //OR.B Dn,ea -> ea
                match eamode with
                | 0b010uy -> //(An)
                    let source = byte (x.DataRegister register)
                    let addr = uint32 (x.AddressRegister eareg)
                    let dest = x.MMU.ReadByte addr
                    let result = source ||| dest
                    x.MMU.WriteByte addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Byte x.CCR result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "or.b D%u,(a%u)" register eareg
                    newCpu
                | _ -> failwithf "or.b not implemented for eamode %x" eamode
            | 0b101uy -> //OR.W Dn,ea -> ea
                match eamode with
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source ||| dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "or.w D%u,(a%u)" register eareg
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = int16 (x.DataRegister register)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = source ||| dest
                    x.MMU.WriteWord addr result
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "or.w D%u,%i(a%u)" register displacement eareg
                    newCpu
                | _ -> failwithf "or.w(dn->ea) not implemented for eamode %x" eamode
            | 0b010uy -> //OR.L ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = x.DataRegister eareg
                    let dest = x.DataRegister register
                    let result = source ||| dest
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+2; CCR = ccr}
                    printfn "or.l D%u,D%u" eareg register
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let dest = x.DataRegister register
                    let result = source ||| dest
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR result
                    let newCpu = {x.WithDataRegister register result with PC = x.PC+6; CCR = ccr}
                    printfn "or.l #$%x,D%u" source register
                    newCpu
                | _ -> failwithf "or.l(ea->dn) not implemented for eamode %x" eamode
            | _ -> failwithf "or: not implemented for opmode %x" opmode

        | _ -> failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x

    member x.DecodeBucket9 (instruction: int) : Cpu =
        match instruction with
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
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "sub.b %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b000uy -> //Dn
                    let source = byte (x.DataRegister eareg)
                    let dest = byte (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Subtract_IgnoringX_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "sub.b D%u,D%u" eareg address
                    newCpu
                | _ -> failwithf "sub.b(ea->dn) not implemented for eamode %x" eamode
            | 0b010uy -> //SUB.L Dn-ea->Dn
                match eamode with
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let result = dest - source
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "sub.l #$%x,D%u" source address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 addr)
                    let result = dest - source
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+4; CCR = ccr}
                    printfn "sub.l %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest - source
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "sub.w %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "sub.w #$%x,D%u" source address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.MMU.ReadWord addr)
                    let dest = int16 (x.DataRegister address)
                    let result = dest - source
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+6; CCR = ccr}
                    printfn "sub.w D%u,$%x.l" address addr
                    newCpu
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest - source
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
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
                    let ccr = CCR.Subtract_IgnoringX_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "sub.w D%u,%i(a%u)" address displacement eareg
                    newCpu
                | _ -> failwithf "sub.w(dn->ea) not implemented for eamode %x" eamode
            | 0b011uy -> //SUBA.W (source sign-extended to 32 bits before subtracting)
                match eamode with
                | 0b000uy -> //Dn
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.DataRegister eareg))
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "suba.w D%u,A%u" eareg address
                    newCpu
                | 0b001uy -> //An
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.AddressRegister eareg))
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "suba.w A%u,A%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm.W
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))
                    let result = dest - source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+4}
                    printfn "suba.w #$%x,A%u" source address
                    newCpu
                | _ -> failwithf "suba.w not implemented for eamode %x" eamode
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
                | _ -> failwithf "cmp.l eamode %u not implemented" eamode
            | 0b111uy -> //CMPA.L An,<ea>
                match eamode with
                | 0b000uy -> //Dn
                    let dest = x.AddressRegister register
                    let source = x.DataRegister eareg
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpa.l D%u,A%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b001uy -> //An
                    let dest = x.AddressRegister register
                    let source = x.AddressRegister eareg
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpa.l A%u,A%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.AddressRegister register
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpa.l #$%x,A%u" source register
                    {x with PC = x.PC+6; CCR = ccr}
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = x.AddressRegister register
                    let source = x.MMU.ReadLong(uint32 addr)
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpa.l %i(a%u),A%u" displacement eareg register
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.AddressRegister register
                    let source = x.MMU.ReadLong addr
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpa.l $%x.l,A%u" addr register
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> failwithf "cmpa.l eamode %u not implemented" eamode
            | 0b011uy -> //CMPA.W <ea>,An - source is word-sized, sign-extended to long before the compare
                match eamode with
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.AddressRegister register
                    let source = int (int16 (x.MMU.ReadWord addr))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmpa.w $%x.l,A%u" addr register
                    {x with PC = x.PC+6; CCR = ccr}
                | _ -> failwithf "cmpa.w eamode %u not implemented" eamode
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
                    let destAddr = x.AddressRegister register
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
            //Extend-aware add, used for multi-precision arithmetic: adds the X flag into the sum,
            //and - the real 68000 quirk that distinguishes ADDX from plain ADD - Z is only ever
            //CLEARED on a nonzero result, never SET on a zero one, so a chain of ADDX calls across
            //a multi-word value can tell whether the WHOLE value came out zero, not just this word.
            if usePredecrement then failwith "ADDX -(An),-(An) (memory form) not implemented"
            let extend = if x.X then 1 else 0
            match size with
            | 0b01uy -> //word
                let dest = int16 (x.DataRegister registerX)
                let source = int16 (x.DataRegister registerY)
                let wide = int dest + int source + extend
                let result = int16 wide
                let newValue = (x.DataRegister registerX &&& ~~~0xffff) ||| (int result &&& 0xffff)
                let carryOut = (uint32 (uint16 dest) + uint32 (uint16 source) + uint32 extend) > 0xffffu
                let overflow = ((dest >= 0s) = (source >= 0s)) && ((result >= 0s) <> (dest >= 0s))
                let mutable ccr = x.CCR
                ccr <- ccr &&& ~~~0x8s &&& ~~~0x2s &&& ~~~0x1s &&& ~~~0x10s
                if result < 0s then ccr <- ccr ||| 0x8s //N
                if result <> 0s then ccr <- ccr &&& ~~~0x4s //Z: clear on nonzero, leave alone otherwise
                if overflow then ccr <- ccr ||| 0x2s //V
                if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s //C and X
                let newCpu = {x.WithDataRegister registerX newValue with PC = x.PC+2; CCR = ccr}
                printfn "addx.w D%u,D%u" registerY registerX
                newCpu
            | _ -> failwithf "addx not implemented for size %x" size

        | ADD(address, opmode, eamode, eareg) ->
            match opmode with
            | 0b000uy -> //ADD.B ea+Dn->Dn
                match eamode with
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = byte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff)
                    let dest = byte (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xff) ||| int result
                    let ccr = CCR.Add_IgnoringX_Byte x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.b #$%x,D%u" source address
                    newCpu
                | _ -> failwithf "add.b(ea->dn) not implemented for eamode %x" eamode
            | 0b001uy -> //ADD.W ea+Dn->Dn
                match eamode with
                | 0b000uy -> //Dn
                    let source = int16 (x.DataRegister eareg)
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+2; CCR = ccr}
                    printfn "add.w D%u,D%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let source = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.w #$%x,D%u" source address
                    newCpu
                | 0b011uy -> //(An)+
                    let addr = x.AddressRegister eareg
                    let source = int16 (x.MMU.ReadWord(uint32 addr))
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
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
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
                    let newCpu = {x.WithDataRegister address newValue with PC = x.PC+4; CCR = ccr}
                    printfn "add.w %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let source = int16 (x.MMU.ReadWord addr)
                    let dest = int16 (x.DataRegister address)
                    let result = source + dest
                    let newValue = (x.DataRegister address &&& ~~~0xffff) ||| (int result &&& 0xffff)
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
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
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+2; CCR = ccr}
                    printfn "add.l D%u,D%u" eareg address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + int displacement
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 addr)
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+4; CCR = ccr}
                    printfn "add.l %i(a%u),D%u" displacement eareg address
                    newCpu
                | 0b001uy -> //An
                    let dest = x.DataRegister address
                    let source = x.AddressRegister eareg
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+2; CCR = ccr}
                    printfn "add.l A%u,D%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong(uint32 (x.PC+2))
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "add.l #$%x,D%u" source address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.DataRegister address
                    let source = x.MMU.ReadLong addr
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+6; CCR = ccr}
                    printfn "add.l $%x.l,D%u" addr address
                    newCpu
                | _ -> failwithf "add.l not implemented for eamode %x" eamode
            | 0b011uy -> //ADDA.W
                match eamode with
                | 0b000uy -> //Dn
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.DataRegister eareg))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "adda.w D%u,A%u" eareg address
                    newCpu
                | 0b001uy -> //An
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.AddressRegister eareg))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+2}
                    printfn "adda.w A%u,A%u" eareg address
                    newCpu
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+4}
                    printfn "adda.w #$%x,A%u" source address
                    newCpu
                | 0b111uy when eareg = 0b011uy -> //(d8,PC,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = (x.PC+2) + ext.Offset
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.MMU.ReadWord(uint32 addr)))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+4}
                    printfn "adda.w %i(pc,%s%u.%s),A%u" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w") address
                    newCpu
                | 0b111uy when eareg = 0b001uy -> //(xxx).L
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.MMU.ReadWord addr))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+6}
                    printfn "adda.w $%x.l,A%u" addr address
                    newCpu
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = x.AddressRegister address
                    let source = int (int16 (x.MMU.ReadWord addr))
                    let result = dest + source
                    let newCpu = {x.WithAddressRegister address result with PC = x.PC+4}
                    printfn "adda.w %i(a%u),A%u" displacement eareg address
                    newCpu
                | _ -> failwithf "adda.w not implemented for eamode %x" eamode
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
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
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
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "add.w D%u,%i(a%u)" address displacement eareg
                    newCpu
                | 0b010uy -> //(An)
                    let addr = uint32 (x.AddressRegister eareg)
                    let source = int16 (x.DataRegister address)
                    let dest = int16 (x.MMU.ReadWord addr)
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX_Word x.CCR dest source
                    x.MMU.WriteWord addr result
                    let newCpu = {x with PC = x.PC+2; CCR = ccr}
                    printfn "add.w D%u,(a%u)" address eareg
                    newCpu
                | _ -> failwithf "add.w(dn->ea) not implemented for eamode %x" eamode
            | 0b110uy -> //ADD.L Dn,<ea> (ea+Dn->ea, result written to memory)
                match eamode with
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let source = x.DataRegister address
                    let dest = x.MMU.ReadLong addr
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
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
                    v <- (v >>> 1) &&& bitMask
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
                    v <- (v >>> 1) &&& bitMask
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
                    v <- ((v >>> 1) ||| (if bottomBit then signBit else 0)) &&& bitMask
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
                    v <- ((v >>> 1) ||| (if bottomBit then signBit else 0)) &&& bitMask
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
            | _ -> failwithf "shift/rotate not implemented for direction %x size %x useRegCount %x type %x" direction size useRegisterCount shiftType

        | MemoryShiftRotate(shiftType, direction, eamode, eareg) ->
            //Always word-size, always exactly 1 bit - the count/register-size variation only
            //applies to the Dn-direct ShiftRotate form above.
            match shiftType, direction with
            | 0b001uy, 0uy -> //LSR.W <ea>
                match eamode with
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let v = uint16 (x.MMU.ReadWord addr)
                    let carryOut = v &&& 1us <> 0us
                    let result = int16 (v >>> 1)
                    x.MMU.WriteWord addr result
                    let mutable ccr = x.CCR
                    ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                    if result < 0s then ccr <- ccr ||| 0x8s //N
                    if result = 0s then ccr <- ccr ||| 0x4s //Z
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s else ccr <- ccr &&& ~~~0x10s //C and X
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "lsr.w %i(a%u)" displacement eareg
                    newCpu
                | _ -> failwithf "lsr.w(memory) not implemented for eamode %x" eamode
            | 0b001uy, 1uy -> //LSL.W <ea>
                match eamode with
                | 0b101uy -> //(d16,An)
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let v = uint16 (x.MMU.ReadWord addr)
                    let carryOut = v &&& 0x8000us <> 0us
                    let result = int16 (v <<< 1)
                    x.MMU.WriteWord addr result
                    let mutable ccr = x.CCR
                    ccr <- ccr &&& ~~~0x8s &&& ~~~0x4s &&& ~~~0x2s &&& ~~~0x1s
                    if result < 0s then ccr <- ccr ||| 0x8s //N
                    if result = 0s then ccr <- ccr ||| 0x4s //Z
                    if carryOut then ccr <- ccr ||| 0x1s ||| 0x10s else ccr <- ccr &&& ~~~0x10s //C and X
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "lsl.w %i(a%u)" displacement eareg
                    newCpu
                | _ -> failwithf "lsl.w(memory) not implemented for eamode %x" eamode
            | _ -> failwithf "memory shift/rotate not implemented for type %x direction %x" shiftType direction

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
