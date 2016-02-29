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
        
type TraceMode =
    | No_Trace
    | Trace_On_Any_Instruction
    | Trace_On_Change_of_Flow
    | Undefined
        
type ActiveStack =
    | USP | ISP | MSP
    
[<StructuredFormatDisplay("{DisplayRegisters}")>]
type Cpu =
    {D0:int; D1:int; D2:int; D3:int; D4:int; D5:int; D6:int; D7:int
     A0:int; A1:int; A2:int; A3:int; A4:int; A5:int; A6:int; A7:int //USP
     PC : int
     CCR : int16 }
     
     //CCR
     //T1 T2 S M 0 IPM 0 0 0 X N Z V C
     //0  0  0 0 0 000 0 0 0 0 0 0 0 0
   
    static member Create() = 
        { D0=0; D1=0; D2=0; D3=0; D4=0; D5=0; D6=0; D7=0
          A0=0; A1=0; A2=0; A3=0; A4=0; A5=0; A6=0; A7=0
          PC=0; CCR=0s}
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
        { x with CCR = 0x2700s; A7=0; PC=0 }
        
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
                  
type MMU(romData:byte array) =
    let romStart = 0xfa0000
    let romEnd = 0xff8800
    
    let (|Rom|_|) address =
        if address >= romStart && address <= romEnd then Some() else None
        
    member x.ReadByte address =
        match address with
        | a when a <= 8 ->
            //Read from roms first 8 bytes
            0y
        | Rom ->
            //read from from
            0y
        | _ -> 
            //otherwise read from mem area
            0y 
    
    member x.ReadWord address =
        0s 

type AtartSt(romPath) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mutable cpu = Cpu.Create()
    
    member x.Reset() =
        cpu <- cpu.Reset()
        

