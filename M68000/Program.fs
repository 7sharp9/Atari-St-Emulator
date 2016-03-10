open System
[<AutoOpen>]
module Bits =
    let setbit  index (value:int)=
        value ||| (1 <<< index)
    
    let setbits  indices (value)=
        indices |> List.fold (fun state index -> setbit index state) value
        
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
    let romStart = 0xfa0000
    let romEnd = 0xff8800
    
    let (|Rom|_|) address =
        if address >= romStart && address <= romEnd then Some() else None
    

        
    member x.ReadByte address =
        match address with
        | a when a <= 7 ->
            //Read from roms first 8 bytes
            rom.[a]
        | Rom ->
            //read from from
            0uy
        | _ -> 
            //otherwise read from mem area
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
        | a when a >= romStart && a <= romEnd ->
            readBigEndianLWord rom (a &&& 0x3ffff)
        | _ -> 
            //TODO check memory extents
            0

            
        
type TraceMode =
    | No_Trace
    | Trace_On_Any_Instruction
    | Trace_On_Change_of_Flow
    | Undefined
        
type ActiveStack =
    | USP | ISP | MSP
    
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
        
    let (|CMPZ|_|) data =
        if (data &&& 0b1111111100000000) = 0b0000110000000000 then
            let zz =  (data &&& 0b0000000011000000) >>> 6
            printfn "data : %s" data.toBits
            printfn "mask : %s" (data &&& 0b0000000011000000).toBits
            printfn "shift: %s" ((data &&& 0b0000000011000000) >>> 6).toBits
            let ddd = (data &&& 0b0000000000111000) >>> 3
            let DDD = (data &&& 0b0000000000000111)
            Some(zz,ddd,DDD)
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
          
    member x.C = not (x.CCR &&& 0x0001s = 0s)
    member x.V = not (x.CCR &&& 0x0002s = 0s)
    member x.Z = not (x.CCR &&& 0x0004s = 0s)
    member x.N = not (x.CCR &&& 0x0008s = 0s)
    member x.X = not (x.CCR &&& 0x0010s = 0s)
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
        printfn "instruction: %x" instruction
        match instruction with
        | Move2SR(mode, register) ->
            printfn "move2sr mode: %0x register: %0x" mode register
            //Hack, not sure about this
            if mode = 0b111 && register = 0b100 then
                //load data
                let register = int16 <| x.MMU.ReadWord (x.PC + 2)
                printfn "register: %0x %s" register register.toBits
                {x with PC = x.PC + 4; CCR = register}
            else {x with PC = x.PC + 4}
            //TODO run instruction
        | Reset ->
            if x.S then
                printfn "RESET"
                //Asserted for 124 cycles
            else
                printfn "TRAP Not supervisor"
            {x with PC = x.PC + 2}
        | CMPZ(zz,ddd,DDD) -> 
            printfn "CMP.Z zz: %s ddd: %x DDD: %x" zz.toBits ddd DDD
            //TODO run instruction
            {x with PC = x.PC + 4}
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
CCR: %s PC: %08x Trace: %A ActiveStack: %A""" 
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
    
    member x.Debug =
       sprintf "CPU:\n\t%A" cpu
        
let st = AtartSt("/Users/dave/Desktop/100uk.img")
st.Reset()
st.Step()
st.Step()
st.Step()