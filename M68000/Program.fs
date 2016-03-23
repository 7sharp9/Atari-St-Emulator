open System
[<AutoOpen>]
module Bits =
    let setbit  index (value:int)=
        value ||| (1 <<< index)
    
    let setbits  indices (value)=
        indices |> List.fold (fun state index -> setbit index state) value
        
    type Byte with
        member x.toBits = Convert.ToString(x,2).PadLeft(8, '0')
        
    type Int32 with
        member x.setBit i = x ||| (1 <<< i)
        member x.toBits = Convert.ToString(x, 2).PadLeft(32, '0') 
        
    type Int16 with
        member x.setBit i = x ||| (1s <<< i)
        member x.toBits = Convert.ToString(x, 2).PadLeft(16, '0')
        
    let tobits (tw:IO.TextWriter) (i:int16) =
        tw.Write(Convert.ToString(i,2).PadLeft(16, '0'))
        
    let readBigEndianWord (bytes: _ array) a =
        ((int bytes.[a]) <<< 8) |||
        (int  bytes.[a+1])
            
    let readBigEndianLWord (bytes: _ array) a =
        ((int bytes.[a])   <<< 24) |||
        ((int bytes.[a+1]) <<< 16) |||
        ((int bytes.[a+2]) <<<  8) |||
        ( int bytes.[a+3])
        
type MMU(rom:byte array, ram: byte array) =
    let romStart = 0xfc0000
    let romEnd = 0xff0000
    let cartStart = 0xfa0000
    let cartEnd = 0xfc0000
    
    let (|Rom|_|) address =
        if address >= romStart && address <= romEnd
        then Some()
        else None
        
    let (|Cart|_|) address =
        if address >= cartStart && address <= cartEnd
        then Some()
        else None
        
    member x.ReadByte address =
        match address with
        | a when a <= 7 ->
            //Read from roms first 8 bytes
            rom.[a]
        | Rom ->
            rom.[address &&& 0x3ffff]
        | _ -> 
            //TODO: otherwise read from mem area
            0uy 
    
    member x.ReadWord address =
        match address with
        | a when a < 7 -> 
            ((int rom.[a]) <<< 8) |||
            (int rom.[a+1])
        | a when a >= romStart && a <= romEnd ->
            readBigEndianWord rom (a &&& 0x3ffff)
            
        | _ -> failwith "Dont care"
        
    member x.ReadLong address =
        match address with
        //The first 8 bytes (2 long Words) are mirrored from the rom area
        | a when a = 0 || a = 4 ->
           //read from rom as first 8 bytes mirrored
           ((int rom.[a])   <<< 24) |||
           ((int rom.[a+1]) <<< 16) |||
           ((int rom.[a+2]) <<<  8) |||
           ( int rom.[a+3])
        | Rom ->
            readBigEndianLWord rom (address &&& 0x3ffff)
        | Cart -> 
            //TODO support cart
            0xffffffff
        | _ -> 
            //TODO read normal ram, check memory extents
            0

            
        
type TraceMode =
    | No_Trace
    | Trace_On_Any_Instruction
    | Trace_On_Change_of_Flow
    | Undefined
        
type ActiveStack =
    | USP | ISP | MSP
    
type Condition =
    | T =     0b0000
    | F =     0b0001
    | H =     0b0010
    | LS =    0b0011
    | CC_HI = 0b0100
    | CC_LO = 0b0101
    | NE =    0b0110
    | EQ =    0b0111
    | VC =    0b1000
    | VS =    0b1001
    | PL =    0b1010
    | MI =    0b1011
    | GE =    0b1100
    | LT =    0b1101
    | GT =    0b1110
    | LE =    0b1111
    
    
[<AutoOpen>]
module Instructions =
    let (|Move2SR|_|) data =
        if ((data >>> 6) = 0b0100011011) then
            let mode = (data &&& 0b0000000000111000) >>> 3
            let reg  = (data &&& 0b0000000000000111)
            Some(mode,reg)
        else None
    
    let (|Reset|_|) data =
        if data = 0b0100111001110000 then Some()
        else None
        
    let (|CMPI|_|) data =
        if (data &&& 0b1111111100000000) = 0b0000110000000000 then
            let size = byte (data &&& 0b0000000011000000) >>> 6
            let mode = byte (data &&& 0b0000000000111000) >>> 3
            let register = byte (data &&& 0b0000000000000111)
            Some(size, mode, register)
        else None
        
    //0110 <4:cond> <8:displacement>  Bcc.B   #I
    let (|BNES|_|) data =
        if data >>> 12 = 0b0000000000000110 then
            let displacement = data &&& 0b0000000011111111
            let condition : Condition = enum (data &&& 0b0000111100000000) >>> 8  
            if condition = Condition.NE && displacement <> 0x0 then
                Some(displacement)
            else None
        else None
        
    let (|LEA|_|) data =
        //0100 rrr1 11ss sSSS
        if data &&& 0b1111000111000000 = 0b0100000111000000 then
            printfn "read %x" data
            let register = byte (data >>> 9) &&& 0b111uy
            let mode = byte (data >>> 3) &&& 0b111uy
            let register2 = byte data &&& 0b111uy
            Some(register, mode, register2)
        else None
        

    
[<StructuredFormatDisplay("{DisplayRegisters}")>]
type Cpu =
    {D0:int; D1:int; D2:int; D3:int; D4:int; D5:int; D6:int; D7:int
     A0:int; A1:int; A2:int; A3:int; A4:int; A5:int; A6:int; A7:int //USP
     PC : int
     CCR : int16
     MMU: MMU }
     
     //CCR
     //T1 T2 S M 0 IPM 0 0 0 X N Z V C
     //0  0  0 0 0 000 0 0 0 0 0 0 0 0

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
      
    member x.TraceMode =
        match (x.T1, x.T0) with
        |    false, false -> No_Trace
        |    true, false -> Trace_On_Any_Instruction
        |    false, true -> Trace_On_Change_of_Flow
        |    true, true -> Undefined
        
    member x.ActiveStack =
        match x.S, x.M with
        | false, _ -> USP
        | true, false -> ISP
        | true, tru -> MSP
        
    member x.Reset() =
        //SSP is loaded form $0
        //PC is loaded from $4
        //reset and CCR setup should come from rom (first 8 bytes copied to $0-$8)
        { x with A7= x.MMU.ReadLong 0 ; PC= x.MMU.ReadLong 4 }
    
    member x.Step() =
    //TODO implement prefetch ops
        let instruction = x.MMU.ReadWord x.PC
        match instruction with
        | Move2SR(mode, register) ->
            //Hack, not sure about this
            if mode = 0b111 && register = 0b100 then
                //load data
                let register = int16 <| x.MMU.ReadWord (x.PC + 2)
                printfn "move #%0x, sr" register
                
                {x with PC = x.PC + 4
                        CCR = register }
            else
                failwithf "mode %A, register %A not implemented for move2sr" mode register
        | Reset ->
            if x.S then
                printfn "reset"
                //Asserted for 124 cycles
            else
                printfn "TRAP: Not supervisor"
            {x with PC = x.PC + 2}
        | CMPI(size, mode , register) -> 
            match size with
            | 0b00000000uy ->
                failwith "Not implemented"
                //TODO byte op 
            | 0b00000001uy ->
                failwith "Not implemented"
                //TODO word op
            | 0b00000010uy ->
                match mode with
                //| 0b00000000uy -> //Dn
                //| 0b00000010uy -> //(An)
                //| 0b00000011uy -> //(AN)+
                //| 0b00000100uy -> //-(An)
                //| 0b00000101uy -> // (d16, An)
                //| 0b00000110uy -> //(d8,An,Xn)
                | 0b00000111uy ->
                    //(xxx).W
                    let source = x.MMU.ReadLong(x.PC+2)
                    let destreg = x.MMU.ReadLong(x.PC+6)
                    let dest = x.MMU.ReadLong(destreg)
                    printfn "cmpi.l #$%x,$%x" source destreg
                    //subtract 
                    let result = dest - source
                    
                    //unset all flag bits apart from x
                    let mutable ccr = x.CCR &&& (~~~0x31s ||| 0x16s)

                    if (result &&& 0x80000000) <> 0 then ccr <- ccr ||| 0x8s //N
                    if result = 0 then ccr <- ccr ||| 0x4s //Z
                    if ((dest^^^source) < 0 && (source^^^result) >= 0) then ccr <- ccr ||| 0x2s //V
                    if ((result&&&source) < 0 || (~~~dest &&& (result ||| source)) < 0) then ccr <- ccr ||| 0x1s //C

                    {x with PC = x.PC + 10
                            CCR = ccr }
                | _ -> failwithf "Unknown mode: %x" mode
            | _ -> failwithf "Inknown size: %x" size
        | BNES(disp) ->
            let condition = not x.Z
            let newPC = if condition then (x.PC + 2) + disp else x.PC + 2
            printfn "bne.s #$%x (%A)" ((x.PC + 2) + disp) (condition)
            {x with PC = newPC}
            
        | LEA(a_reg,mode,reg2) ->
            match mode with
            | 0b010uy -> failwith "not implemented" //reg. number:An
            | 0b101uy -> failwith "not implemented" //reg. number:An
            | 0b110uy -> failwith "not implemented"//reg. number:An
            | 0b111uy -> 
                match reg2 with
                | 0b000uy -> failwith "not implemented" //(xxx).W
                | 0b001uy -> failwith "not implemented" //(xxx).L
                | 0b010uy -> //(d16,PC)
                    //PC + displacement
                    //TODO: ensure sign extended
                    let displacedPC =
                        let disp = x.MMU.ReadWord(x.PC+2)
                        x.PC + 2 + disp //pc+2 because thats the point we finished reading the first part
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
                | _ -> failwithf "unknown Register %x for mode %x" reg2 mode
            | _ -> failwithf "unknown mode %x" mode

        | other ->
            printfn "unknown instruction %x %s" instruction instruction.toBits
            {x with PC = x.PC + 2}
            
    member x.Run(cycles) =
        //TODO
        //while cycles left
        //get instruction
        //execute
        ()
    member x.DisplayRegisters =
        sprintf """
D0:%x A0: %x
D1:%x A1: %x
D2:%x A2: %x
D3:%x A3: %x
D4:%x A4: %x
D5:%x A5: %x
D6:%x A6: %x
D7:%x A7: %x
     TTSM IPM   XNZVC
CCR: %s PC: %x Trace: %A ActiveStack: %A""" 
                  x.D0 x.A0
                  x.D1 x.A1
                  x.D2 x.A2
                  x.D3 x.A3
                  x.D4 x.A4
                  x.D5 x.A5
                  x.D6 x.A6
                  x.D7 x.A7
                  x.CCR.toBits x.PC x.TraceMode x.ActiveStack
            
[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mmu = MMU(rom, [||])
    let mutable cpu = Cpu.Create(mmu)
    
    member x.Reset() = cpu <- cpu.Reset()
    member x.Rom = rom
    
    member x.Step() =
        cpu <- cpu.Step()
        printfn "CPU:\n\t%A" cpu
    
    member x.Debug =
       sprintf "CPU:\n\t%A" cpu
        
let st = AtartSt("/Users/dave/Desktop/100uk.img")
st.Reset()
st.Step()
st.Step()
st.Step()
st.Step()
st.Step()