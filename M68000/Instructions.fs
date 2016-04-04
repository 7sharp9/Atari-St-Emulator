namespace Atari
open System
open Bits

[<RequireQualifiedAccess>] 
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
    
[<RequireQualifiedAccess>] 
type OperandSize =
    | Byte | Word | Long | Single | Double | Extended | Packed
    
type AddressingModes =
    | Dn of byte
    | An of byte
    | An_Indirect of byte
    | An_PostIncrement of byte
    | An_PreDecrement of byte
    | An_Displacement of byte
    | An_ByteDisplacement of byte
    | PC_Indirect_Word_Displacement of int16
    | PC_Indirect_Byte_Displacement of byte
    | Absolute_Short of int16
    | Absolute_Long of int
    | Immediate of OperandSize
    //| An_BaseDisplacement of byte * byte //68020+
    //| MemoryIndirect_PostIndexed ////68020+
    //| MemoryIndirect_PreIndexed ////68020+
    //| PC_Indirect_Base_Displacement ////68020+
    //| PC_Indirect_PostIndexed ////68020+
    //| PC_Indirect_PreIndexed ////68020+
    
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
        
    let (|BCC|_|) data =
        //sample:
        //0110000000000000
        //0110conddisp----
        
        if data &&& 0b1111000000000000 = 0b0110000000000000 then
            let condition : Condition = enum (data &&& 0b0000111100000000) >>> 8
            match data &&& 0b0000000011111111 with
            | 0x00 -> Some(condition, OperandSize.Word)//16bit disp
            | 0xFF -> Some(condition, OperandSize.Long)//32bit disp
            | _ ->    Some(condition, OperandSize.Byte)//8bit disp
        else None
        
    let (|SUB|_|) data =
        //1001101111001101
        //----reg
        //-------opm
        //----------EAm
        //-------------EAr
        if data &&& 0b1111000000000000 = 0b1001000000000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let opmode = byte (data >>> 6) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            printfn "%s" data.toBits
            Some(register, opmode, eamode, eareg)
        else None
        
    let (|JMP|_|) data =
        //0100111011sssSSS
        //sample: 0100111011 010 110 = An Mode, register A6
        //sss = effective address mode
        //SSS = effective address register
        if data &&& 0b1111111111000000 = 0b0100111011000000 then
            let eaMode = byte (data >>> 3) &&& 0b111uy
            let eaReg = byte (data &&& 0b111)
            Some(eaMode, eaReg)
        else None
    
    ///Represents the move instuction
    ///size, dest_reg, dest_mode, source_mode, source_reg 
    let (|Move|_|) data = 
        //00ssdddDDDsssSSS
        if data &&& 0b1100000000000000 = 0b0000000000000000 then
            let size =
              match (byte (data >>> 12) &&& 0b11uy) with
              | 0b01uy -> OperandSize.Byte
              | 0b11uy -> OperandSize.Word
              | 0b10uy -> OperandSize.Long
              | other -> failwithf "Invalid operand size %u" other
              
            let dest_reg    = byte (data >>> 9) &&& 0b111uy
            let dest_mode   = byte (data >>> 6) &&& 0b111uy
            let destEA =
                match dest_mode with
                | 0b000uy -> AddressingModes.Dn(dest_mode)
                | 0b010uy -> AddressingModes.An_Indirect(dest_reg)
                | 0b011uy -> AddressingModes.An_PostIncrement(dest_reg)
                | 0b100uy -> AddressingModes.An_PreDecrement(dest_reg)
                | 0b101uy -> AddressingModes.An_Displacement(dest_reg)
                | 0b110uy -> AddressingModes.An_ByteDisplacement(dest_reg)
                | 0b111uy when dest_reg = 0b0uy -> Immediate(OperandSize.Word)
                | 0b111uy when dest_reg = 0b1uy -> Immediate(OperandSize.Long)
                | _ -> failwithf "Invalid destination effective address: mode: %u, reg: %u"  dest_mode dest_reg
            
            let source_mode = byte (data >>> 3) &&& 0b111uy
            let source_reg = byte (data &&& 0b111)
            
            Some(size, dest_reg, dest_mode, source_mode, source_reg)
        else None