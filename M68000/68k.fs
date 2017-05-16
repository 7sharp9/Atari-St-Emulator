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
        let mutable ccr = currentCCR &&& (~~~0x31s ||| 0x16s)
        let result = dest - source
        if (result &&& 0x80000000) <> 0 then ccr <- ccr ||| 0x8s //N
        if result = 0 then ccr <- ccr ||| 0x4s //Z
        if ((dest^^^source) < 0 && (source^^^result) >= 0) then ccr <- ccr ||| 0x2s //V
        if ((result&&&source) < 0 || (~~~dest &&& (result ||| source)) < 0) then ccr <- ccr ||| 0x1s //C
        ccr
        
    ///Calculate CCR
    let IgnoreX_ZeroV_And_ZeroC currentCCR (input:int16) =
        //TODO: Expand logic as more variations of flag ignorance is needed
        let mutable ccr = currentCCR &&& (~~~0x31s ||| 0x16s)
        //set N,Z 
        if (input &&& 0x8000s) <> 0s then ccr <- ccr ||| 0x8s //N
        if input = 0s then ccr <- ccr ||| 0x4s //Z
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
           
[<StructuredFormatDisplay("{DisplayRegisters}")>]
type Cpu =
    {D0:int; D1:int; D2:int; D3:int; D4:int; D5:int; D6:int; D7:int
     A0:int; A1:int; A2:int; A3:int; A4:int; A5:int; A6:int; A7:int //USP
     PC : int
     CCR : int16
     MMU: MMU }

    static member Create(mmu:MMU) =
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
    member x.AddressRegister register =
        match register with
        | 0uy -> x.A0 | 1uy -> x.A1 | 2uy -> x.A2 | 3uy -> x.A3
        | 4uy -> x.A4 | 5uy -> x.A5 | 6uy -> x.A6 | 7uy -> x.A7
        | _ -> failwithf "Invalid register %uy" register
        
    member x.DataRegister register =
        match register with
        | 0uy -> x.D0 | 1uy -> x.D1 | 2uy -> x.D2 | 3uy -> x.D3
        | 4uy -> x.D4 | 5uy -> x.D5 | 6uy -> x.D6 | 7uy -> x.D7
        | _ -> failwithf "Invalid register %uy" register
      
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
            else
                failwithf "mode %A, register %A not implemented for move2sr" mode register
        | Reset ->
            if x.S then printfn "reset"
                //Asserted for 124 cycles
            else printfn "TRAP: Not supervisor"
            {x with PC = x.PC + 2}
        | CMPI(size, mode , register) ->
            match size with
            | 0b000uy ->
                failwith "Not implemented"
                //TODO byte op 
            | 0b001uy ->
                failwith "Not implemented"
                //TODO word op
            | 0b010uy ->
                match mode with
                //| 0b000uy -> //Dn
                //| 0b010uy -> //(An)
                //| 0b011uy -> //(AN)+
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
        | BNES(disp) ->
            let condition = not x.Z
            let newPC = if condition then (x.PC + 2) + disp else x.PC + 2
            printfn "bne.s #$%x (%A)" ((x.PC + 2) + disp) (condition)
            {x with PC = newPC}
            
        | LEA(a_reg,eamode,eareg) ->
            match eamode with
            | 0b010uy -> failwith "not implemented" //reg. number:An
            | 0b101uy -> failwith "not implemented" //reg. number:An
            | 0b110uy -> failwith "not implemented"//reg. number:An
            | 0b111uy -> 
                match eareg with
                | 0b000uy -> failwith "not implemented" //(xxx).W
                | 0b001uy -> //(xxx).L
                    //load the next long into a_reg
                    let addr = x.MMU.ReadLong(uint32 (x.PC+2))
                    let newCpu =
                        match a_reg with
                        | 0b000uy -> {x with PC = x.PC+6; A0 = addr}
                        | 0b001uy -> {x with PC = x.PC+6; A1 = addr}
                        | 0b010uy -> {x with PC = x.PC+6; A2 = addr}
                        | 0b011uy -> {x with PC = x.PC+6; A3 = addr}
                        | 0b100uy -> {x with PC = x.PC+6; A4 = addr}
                        | 0b101uy -> {x with PC = x.PC+6; A5 = addr}
                        | 0b110uy -> {x with PC = x.PC+6; A6 = addr}
                        | 0b111uy -> {x with PC = x.PC+6; A7 = addr}
                        | _ -> failwithf "Unknown address register %uy" a_reg
                    printfn "lea %x, A%i" addr a_reg
                    newCpu
                    
                | 0b010uy -> //(d16,PC)
                    let displacedPC =
                        let disp = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                        (x.PC+2) + int disp
                    let newCpu =
                        match a_reg with
                        | 0b000uy -> {x with PC = x.PC + 4; A0 = displacedPC}
                        | 0b001uy -> {x with PC = x.PC + 4; A1 = displacedPC}
                        | 0b010uy -> {x with PC = x.PC + 4; A2 = displacedPC}
                        | 0b011uy -> {x with PC = x.PC + 4; A3 = displacedPC}
                        | 0b100uy -> {x with PC = x.PC + 4; A4 = displacedPC}
                        | 0b101uy -> {x with PC = x.PC + 4; A5 = displacedPC}
                        | 0b110uy -> {x with PC = x.PC + 4; A6 = displacedPC}
                        | 0b111uy -> {x with PC = x.PC + 4; A7 = displacedPC}
                        | _ -> failwithf "Unknown address register %uy" a_reg
                    printfn "lea $%x,a%i" displacedPC a_reg
                    newCpu
                    
                | 0b011uy -> failwith "not implemented" //(d8,PC,Xn)
                | _ -> failwithf "unknown Register %x for mode %x" eareg eamode
            | _ -> failwithf "lea: unknown mode %x" eamode
            
        | BCC(cond,disp) ->
            match disp with
            | 0x00uy ->
                match cond with
                | Condition.T ->   
                    let disp = int16 (x.MMU.ReadWord(uint32 (x.PC+2)))
                    let displacedPC = (x.PC+2) + int disp
                    printfn "bra.w $%x" displacedPC
                    {x with PC = displacedPC }
                | _ -> failwith "Not implemented"
            | 0xFFuy -> failwith "Not yet supprted"
            | byteDisp ->
                match cond with
                | Condition.EQ ->
                    let newPc = if x.Z then x.PC+2 + int byteDisp else x.PC + 2
                    printfn "beq.s #$%08x == #$%08x" byteDisp newPc
                    //printfn "%s" byteDisp.toBits

                    {x with PC = newPc}
                | _ -> failwithf "Not supported: instruction:\n0x%x\n%s\n%A" instruction (int16 instruction).toBits x
        
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
                    //TODO update target address better than this!
                    let newCpu = 
                        match address with
                        | 0x0uy -> {x with PC = x.PC+2; A0 = result}
                        | 0x1uy -> {x with PC = x.PC+2; A1 = result}
                        | 0x2uy -> {x with PC = x.PC+2; A2 = result}
                        | 0x3uy -> {x with PC = x.PC+2; A3 = result}
                        | 0x4uy -> {x with PC = x.PC+2; A4 = result}
                        | 0x5uy -> {x with PC = x.PC+2; A5 = result}
                        | 0x6uy -> {x with PC = x.PC+2; A6 = result}
                        | 0x7uy -> {x with PC = x.PC+2; A7 = result}
                        | _ -> failwithf "Invalid destination register %uy" address
                    printfn "suba.%s A%u, A%u" (if opmode = 0x7uy then "l" else "w" ) address eareg
                    newCpu
                | _ -> failwithf "Not implmented eamode %uy, eareg %uy" eamode eareg 
            | _ -> failwithf "Not implemented op mode %uy" opmode //word operation
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
                let source = 
                    match sMode, sReg with
                    | 0b111uy, 0b100uy -> int16 (x.MMU.ReadWord(uint32 (x.PC+2) ) &&& 0xff)
                    | otherMode, otherReg ->
                        failwithf  "Move address mode %u, reg %u not implemented"
                            otherMode otherReg

                match dMode with
                | 0b010uy ->
                    let destEA = uint32 (x.AddressRegister dReg)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    x.MMU.WriteWord destEA source
                    let newCpu = {x with PC=x.PC+4; CCR=ccr}
                    printfn "move.b #%u A%u" source dReg
                    newCpu
                | 0b101uy -> 
                    let displacement = int16 (x.MMU.ReadWord(uint32 (x.PC+4)))
                    let destEA = uint32 (x.AddressRegister dReg + int displacement)
                    let ccr = CCR.IgnoreX_ZeroV_And_ZeroC x.CCR source
                    x.MMU.WriteWord destEA source
                    let newCpu = {x with PC=x.PC+6; CCR=ccr}
                    printfn "move.b #$%x,%i(a%i) == $%x" source displacement dReg destEA
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
                            let newCpu = 
                                match dReg with
                                | 0x0uy -> {x with PC = x.PC+4; D0 = immediate}
                                | 0x1uy -> {x with PC = x.PC+4; D1 = immediate}
                                | 0x2uy -> {x with PC = x.PC+4; D2 = immediate}
                                | 0x3uy -> {x with PC = x.PC+4; D3 = immediate}
                                | 0x4uy -> {x with PC = x.PC+4; D4 = immediate}
                                | 0x5uy -> {x with PC = x.PC+4; D5 = immediate}
                                | 0x6uy -> {x with PC = x.PC+4; D6 = immediate}
                                | 0x7uy -> {x with PC = x.PC+4; D7 = immediate}
                                | _ -> failwithf "Invalid destination register %uy" dReg
                            printfn "move.w #$%04x,D%i" immediate dReg
                            newCpu
                        | _ -> failwith "Not implemented"
                    | _ -> failwith "Not implemented"
                | 0b011uy -> //(AN)+
                    let sourceAddress =  (x.AddressRegister sReg)
                    let sourceContents = int16 (x.MMU.ReadWord (uint32 sourceAddress))

                    match dMode with
                    | 0b011uy -> //(AN)+
                        let destAddress = uint32 (x.AddressRegister dReg)
                        x.MMU.WriteWord destAddress sourceContents

                        let xxx = x.MMU.ReadWord destAddress
                        printfn "dest: %x %s" xxx xxx.toBits
                        failwith "Not implemented"

                    | _ -> failwith "Not implemented"
                | _ ->    failwith "Not implemented"
            | OperandSize.Long -> failwith "Move.l not implemented"
            | other -> failwithf "Move invalid operand size %A" other

        | ``BTST Immediate``(eamode,eareg) ->
            let bitnumber = x.MMU.ReadWord (uint32 (x.PC+2)) &&& 0xFF
            //ccr z flag is set if zero, no others
            match eamode with
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

                | other -> failwithf "BTST.b EA reg %u not supported" other
            | other -> failwithf "BTST.b EA mode %u not supported" other
            
        | other ->
            failwithf "unknown instruction:\n0x%x\n%s\n%A" instruction instruction.toBits x
            
    member x.Run(cycles) =
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