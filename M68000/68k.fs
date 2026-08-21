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
     A0: int; A1: int; A2: int; A3: int; A4: int; A5: int; A6: int; A7: int //USP
     PC: int
     CCR: int16
     MMU: MMU }

    static member Create(mmu: MMU) =
        //TODO review MMU creation / ownership
        { D0=0; D1=0; D2=0; D3=0; D4=0; D5=0; D6=0; D7=0
          A0=0; A1=0; A2=0; A3=0; A4=0; A5=0; A6=0; A7=0
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
        { x with A7 = x.MMU.ReadLong 0u
                 PC = x.MMU.ReadLong 4u }
    
    member x.Step() =
    //TODO implement prefetch ops
        let instruction = x.MMU.ReadWord (uint32 x.PC)
        //printfn "instruction: %x" instruction
        match instruction with
        | Move2SR(mode, register) ->
            //Hack, not sure about this
            if mode = 0x7 && register = 0b100 then
                //load data
                let register = int16 (x.MMU.ReadWord (uint32 (x.PC+2)))
                printfn "move #%0x, sr" register
                {x with PC = x.PC + 4; CCR = register }
            elif mode = 0x3 then //(An)+
                let reg = byte register
                let addr = x.AddressRegister reg
                let newCcr = int16 (x.MMU.ReadWord(uint32 addr))
                let newCpu = {x.WithAddressRegister reg (addr + 2) with PC = x.PC + 2; CCR = newCcr}
                printfn "move (a%u)+,sr" reg
                newCpu
            else
                failwithf "mode %A, register %A not implemented for move2sr" mode register
        | MoveFromSR(eamode, eareg) ->
            match eamode with
            | 0b100uy -> //-(An)
                let newAddr = x.AddressRegister eareg - 2
                x.MMU.WriteWord (uint32 newAddr) x.CCR
                let newCpu = {x.WithAddressRegister eareg newAddr with PC = x.PC+2}
                printfn "move sr,-(a%u)" eareg
                newCpu
            | _ -> failwithf "move sr not implemented for eamode %x" eamode

        | OriToSR ->
            let immediate = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
            let newCcr = x.CCR ||| immediate
            printfn "ori #$%x,SR" immediate
            {x with PC = x.PC+4; CCR = newCcr}

        | Reset ->
            if x.S then printfn "reset"
                //Asserted for 124 cycles
            else printfn "TRAP: Not supervisor"
            {x with PC = x.PC + 2}
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
                | _ -> failwithf "addi.l not implemented for mode %x" mode
            | _ -> failwithf "addi: not implemented for size %x" size

        | CMPI(size, mode , register) ->
            match size with
            | 0b000uy ->
                match mode with
                | 0b000uy -> //Dn
                    let immediate = int (sbyte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff))
                    let dest = int (sbyte (x.DataRegister register))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    printfn "cmpi.b #$%x,D%u" immediate register
                    {x with PC = x.PC + 4; CCR = ccr}
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = int (sbyte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                    let dest = int (sbyte (x.MMU.ReadByte addr))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    printfn "cmpi.b #$%x,$%x.l" immediate addr
                    {x with PC = x.PC + 8; CCR = ccr}
                | _ -> failwithf "cmpi.b mode %u not implemented" mode
            | 0b001uy ->
                match mode with
                | 0b111uy when register = 0b001uy -> //(xxx).L
                    let immediate = int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))
                    let addr = uint32 (x.MMU.ReadLong(uint32 (x.PC+4)))
                    let dest = int (int16 (x.MMU.ReadWord addr))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    printfn "cmpi.w #$%x,$%x.l" immediate addr
                    {x with PC = x.PC + 8; CCR = ccr}
                | 0b101uy -> //(d16,An)
                    let immediate = int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                    let addr = uint32 (x.AddressRegister register + int displacement)
                    let dest = int (int16 (x.MMU.ReadWord addr))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    printfn "cmpi.w #$%x,%i(a%u) == $%x" immediate displacement register addr
                    {x with PC = x.PC + 6; CCR = ccr}
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
                | 0b111uy -> //(xxx).W
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
                    let dest = x.AddressRegister register + int displacement
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest immediate
                    
                    printfn "cmpi.l #$%x,(A%u,$%x) == $%x" immediate register displacement dest
                    {x with PC = x.PC + 8; CCR = ccr }
                | _ -> failwithf "cmpi Unknown mode: %x" mode
            | _ -> failwithf "Inknown size: %x" size
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
            | 0b110uy -> failwith "not implemented" //reg. number:An
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

        | CLR(size, eamode, eareg) ->
            match eamode, size with
            | 0b011uy, 0b10uy -> //(An)+, long
                let addr = x.AddressRegister eareg
                x.MMU.WriteLong (uint32 addr) 0
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC_Long x.CCR 0
                let newCpu = {x.WithAddressRegister eareg (addr+4) with PC = x.PC+2; CCR = ccr}
                printfn "clr.l (a%u)+" eareg
                newCpu
            | 0b000uy, 0b01uy -> //Dn, word
                let currentValue = x.DataRegister eareg
                let newValue = currentValue &&& ~~~0xffff
                let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR 0s
                let newCpu = {x.WithDataRegister eareg newValue with PC = x.PC+2; CCR = ccr}
                printfn "clr.w D%u" eareg
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
            | _ -> failwithf "clr: not implemented for mode %x size %x" eamode size

        | TST(size, eamode, eareg) ->
            //TST: sets N/Z from the operand, clears V/C, X unaffected. CCR-only, no write-back.
            match eamode, size with
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
            | _ -> failwithf "tst: not implemented for mode %x size %x" eamode size

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
            | _ -> failwithf "shift/rotate not implemented for direction %x size %x useRegCount %x type %x" direction size useRegisterCount shiftType

        | BitOpDynamic(register, opmode, eamode, eareg) ->
            let bitnum = int (x.DataRegister register) &&& 7 //memory destination: byte-sized, bit number mod 8
            match eamode with
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

        | RTS ->
            let returnAddr = x.MMU.ReadLong(uint32 x.A7)
            let newCpu = {x with PC = returnAddr; A7 = x.A7 + 4}
            printfn "rts"
            newCpu

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
                    printfn "b%A.w $%x (%b)" cond newPC takeBranch
                    {x with PC = newPC}
                | 0xFFuy -> failwith "Not yet supprted" //32-bit displacement (68020+)
                | byteDisp ->
                    let newPC = if takeBranch then (x.PC+2) + int (sbyte byteDisp) else x.PC + 2
                    printfn "b%A.s $%x (%b)" cond newPC takeBranch
                    {x with PC = newPC}
        
        | SUB(address, opmode, eamode, eareg) ->
            //1001regopmEAmEAr
            //----reg
            //-------opm 
            //----------EAm
            //-------------EAr

            match opmode with
            | 0b111uy -> //long op mode
                //
                match eamode with
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
                | _ -> failwithf "Not implmented eamode %uy, eareg %uy" eamode eareg
            | _ -> failwithf "Not implemented op mode %uy" opmode //word operation

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
                    let dest = int (int16 (x.DataRegister eareg))
                    let result = dest + amount
                    let ccr = CCR.Add_IgnoringX x.CCR dest amount
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (result &&& 0xffff)
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
                | _ -> failwithf "addq not implemented for size %x on Dn" size
            | _ -> failwithf "addq not implemented for eamode %x" eamode

        | SUBQ(quickData, size, eamode, eareg) ->
            let amount = if quickData = 0uy then 8 else int quickData
            match eamode with
            | 0b000uy -> //Dn
                match size with
                | 0b01uy -> //word
                    let dest = int (int16 (x.DataRegister eareg))
                    let result = dest - amount
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest amount
                    let newValue = (x.DataRegister eareg &&& ~~~0xffff) ||| (result &&& 0xffff)
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
            | 0b101uy -> //(d16,An)
                match size with
                | 0b01uy -> //word
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = uint32 (x.AddressRegister eareg + int displacement)
                    let dest = int (int16 (x.MMU.ReadWord addr))
                    let result = dest - amount
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest amount
                    x.MMU.WriteWord addr (int16 result)
                    let newCpu = {x with PC = x.PC+4; CCR = ccr}
                    printfn "subq.w #%u,%i(a%u)" amount displacement eareg
                    newCpu
                | _ -> failwithf "subq not implemented for size %x on (d16,An)" size
            | _ -> failwithf "subq not implemented for eamode %x" eamode

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
            | _ -> failwithf "or: not implemented for opmode %x" opmode

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
            | _ -> failwithf "mulu.w not implemented for eamode %x" eamode

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
                | _ -> failwithf "and.w(ea->dn) not implemented for eamode %x" eamode
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
            | _ -> failwithf "and: not implemented for opmode %x" opmode

        | ADD(address, opmode, eamode, eareg) ->
            match opmode with
            | 0b010uy -> //ADD.L ea+Dn->Dn
                match eamode with
                | 0b001uy -> //An
                    let dest = x.DataRegister address
                    let source = x.AddressRegister eareg
                    let result = dest + source
                    let ccr = CCR.Add_IgnoringX x.CCR dest source
                    let newCpu = {x.WithDataRegister address result with PC = x.PC+2; CCR = ccr}
                    printfn "add.l A%u,D%u" eareg address
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
                | _ -> failwithf "adda.l not implemented for eamode %x" eamode
            | _ -> failwithf "add: not implemented for opmode %x" opmode

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
            | _ -> failwithf "JSR not implemented for eamode %u reg %u" eamode eareg

        | JMP(eamode, eareg) ->
            match eamode with
            | 0b010uy ->
                let jump = x.AddressRegister eareg
                let newCpu = {x with PC = jump}
                printfn "jmp.l A%u" eareg
                newCpu
            | _ -> failwithf "JMP not implemented for mode %u reg %u" eamode eareg  
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
                    | otherMode, otherReg ->
                        failwithf  "Move address mode %u, reg %u not implemented"
                            otherMode otherReg

                let destBase = x.PC + 2 + sourceExtWords * 2
                let x = sourceUpdate x

                match dMode with
                | 0b000uy -> //Dn
                    let currentValue = x.DataRegister dReg
                    let newValue = (currentValue &&& ~~~0xff) ||| (int source &&& 0xff)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    let newCpu = {x.WithDataRegister dReg newValue with PC = destBase; CCR = ccr}
                    printfn "move.b %s,D%u" sourceDesc dReg
                    newCpu
                | 0b010uy ->
                    let destEA = uint32 (x.AddressRegister dReg)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase; CCR=ccr}
                    printfn "move.b %s,(a%u)" sourceDesc dReg
                    newCpu
                | 0b011uy -> //(An)+ - A7 postincrements by 2 (word-aligned stack), others by 1
                    let destEA = x.AddressRegister dReg
                    x.MMU.WriteByte (uint32 destEA) (byte source)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    let step = if dReg = 0b111uy then 2 else 1
                    let newCpu = x.WithAddressRegister dReg (destEA + step)
                    let newCpu = {newCpu with PC=destBase; CCR=ccr}
                    printfn "move.b %s,(a%u)+" sourceDesc dReg
                    newCpu
                | 0b101uy ->
                    let displacement = int16 (x.MMU.ReadWord(uint32 destBase))
                    let destEA = uint32 (x.AddressRegister dReg + int displacement)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase+2; CCR=ccr}
                    printfn "move.b %s,%i(a%i) == $%x" sourceDesc displacement dReg destEA
                    newCpu
                | 0b100uy -> //-(An) - A7 predecrements by 2 (word-aligned stack), others by 1
                    let step = if dReg = 0b111uy then 2 else 1
                    let destEA = x.AddressRegister dReg - step
                    x.MMU.WriteByte (uint32 destEA) (byte source)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    let newCpu = x.WithAddressRegister dReg destEA
                    let newCpu = {newCpu with PC=destBase; CCR=ccr}
                    printfn "move.b %s,-(a%u)" sourceDesc dReg
                    newCpu
                | 0b111uy when dReg = 0b001uy -> //(xxx).L
                    let destEA = uint32 (x.MMU.ReadLong(uint32 destBase))
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    x.MMU.WriteByte destEA (byte source)
                    let newCpu = {x with PC=destBase+4; CCR=ccr}
                    printfn "move.b %s,$%x.l" sourceDesc destEA
                    newCpu
                | 0b110uy -> //(d8,An,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 destBase))
                    let destEA = uint32 (x.AddressRegister dReg + ext.Offset)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
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
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 immediate)
                            let newCpu = {x.WithDataRegister dReg immediate with PC = x.PC+4; CCR = ccr}
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
                        | 0b111uy when dReg = 0b001uy -> //(xxx).L
                            let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+6)))
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            x.MMU.WriteWord destEA (int16 value)
                            let newCpu = {x with PC = x.PC+10; CCR = ccr}
                            printfn "move.w $%x.l,$%x.l" addr destEA
                            newCpu
                        | _ -> failwith "Not implemented"
                    | 0b011uy -> //(d8,PC,Xn)
                        let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                        let addr = (x.PC+2) + ext.Offset
                        let value = x.MMU.ReadWord(uint32 addr)
                        match dMode with
                        | 0b000uy -> //Dn
                            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
                            let newCpu = {x.WithDataRegister dReg value with PC = x.PC+4; CCR = ccr}
                            printfn "move.w %i(pc,%s%u.%s),D%u" ext.Disp (if ext.IndexIsAddress then "a" else "d") ext.IndexReg (if ext.UseLong then "l" else "w") dReg
                            newCpu
                        | _ -> failwith "Not implemented"
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

                    | _ -> failwith "Not implemented"
                | 0b000uy -> //Dn
                    let sourceContents = int16 (x.DataRegister sReg)

                    match dMode with
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
            | 0b111uy ->
                match eareg with
                | 0b010uy -> //d16, PC
                    let displacement = int16 (x.MMU.ReadWord (uint32 (x.PC+4)))
                    let ea = (x.PC+4) + int displacement

                    printfn "BTST.B #$%04x,(PC,$%x) == $%08x" bitnumber displacement ea
                    // Data register direct can be used for long only; all others are byte only.
                    let eaVal = x.MMU.ReadByte (uint32 ea)
                    let bitZeroSet = eaVal.isnotset bitnumber

                    {x with PC=x.PC+6; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }

                | 0b001uy -> //(xxx).L
                    let ea = uint32 (x.MMU.ReadLong (uint32 (x.PC+4)))
                    let eaVal = x.MMU.ReadByte ea
                    let bitZeroSet = eaVal.isnotset bitnumber
                    printfn "BTST.B #$%04x,$%x.l" bitnumber ea
                    {x with PC=x.PC+8; CCR= if bitZeroSet then CCR.SetZero x.CCR else CCR.ClearZero x.CCR }

                | other -> failwithf "BTST.b EA reg %u not supported" other
            | other -> failwithf "BTST.b EA mode %u not supported" other

        | MOVEQ(register, data) ->
            let value = int data
            let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR (int16 value)
            let newCpu = {x.WithDataRegister register value with PC = x.PC+2; CCR = ccr}
            printfn "moveq #$%x,D%u" value register
            newCpu

        | Scc(cond, eamode, eareg) ->
            //Scc: sets the byte at <ea> to $FF if cond is true, $00 otherwise. CCR unaffected.
            let value = if x.EvaluateCondition cond then 0xffuy else 0x00uy
            match eamode with
            | 0b101uy -> //(d16,An)
                let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                let destEA = uint32 (x.AddressRegister eareg + int displacement)
                x.MMU.WriteByte destEA value
                printfn "s%A %i(a%u)" cond displacement eareg
                {x with PC = x.PC+4}
            | 0b111uy when eareg = 0b001uy -> //(xxx).L
                let destEA = uint32 (x.MMU.ReadLong(uint32 (x.PC+2)))
                x.MMU.WriteByte destEA value
                printfn "s%A $%x.l" cond destEA
                {x with PC = x.PC+6}
            | _ -> failwithf "Scc eamode %u not implemented" eamode

        | CMP(register, opmode, eamode, eareg) ->
            match opmode with
            | 0b000uy -> //CMP.B <ea>,Dn
                match eamode with
                | 0b000uy -> //Dn
                    let dest = int (sbyte (x.DataRegister register))
                    let source = int (sbyte (x.DataRegister eareg))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.b D%u,D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b010uy -> //(An)
                    let dest = int (sbyte (x.DataRegister register))
                    let source = int (sbyte (x.MMU.ReadByte(uint32 (x.AddressRegister eareg))))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.b (a%u),D%u" eareg register
                    {x with PC = x.PC+2; CCR = ccr}
                | 0b110uy -> //(d8,An,Xn)
                    let ext = x.DecodeBriefExtension (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let addr = x.AddressRegister eareg + ext.Offset
                    let dest = int (sbyte (x.DataRegister register))
                    let source = int (sbyte (x.MMU.ReadByte(uint32 addr)))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.b %s,D%u" (x.DescribeIndexed eareg ext) register
                    {x with PC = x.PC+4; CCR = ccr}
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = int (sbyte (x.DataRegister register))
                    let source = int (sbyte (x.MMU.ReadWord(uint32 (x.PC+2)) &&& 0xff))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.b #$%x,D%u" source register
                    {x with PC = x.PC+4; CCR = ccr}
                | _ -> failwithf "cmp.b eamode %u not implemented" eamode
            | 0b001uy -> //CMP.W <ea>,Dn
                match eamode with
                | 0b111uy when eareg = 0b100uy -> //#imm
                    let dest = int (int16 (x.DataRegister register))
                    let source = int (int16 (x.MMU.ReadWord(uint32 (x.PC+2))))
                    let ccr = CCR.Subtract_IgnoringX x.CCR dest source
                    printfn "cmp.w #$%x,D%u" source register
                    {x with PC = x.PC+4; CCR = ccr}
                | _ -> failwithf "cmp.w eamode %u not implemented" eamode
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
                | _ -> failwithf "cmpa.l eamode %u not implemented" eamode
            | _ -> failwithf "cmp opmode %u not implemented" opmode

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
                printfn "db%A D%u,$%x" cond register newPC
                newCpu

        | other ->
            failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x
            
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
     TTSM IPM   XNZVC
CCR: %s
PC: %08x""" x.D0 x.D1 x.D2 x.D3 x.D4 x.D5 x.D6 x.D7
            x.A0 x.A1 x.A2 x.A3 x.A4 x.A5 x.A6 x.A7
            x.CCR.toBits (*x.TraceMode x.ActiveStack*) x.PC
