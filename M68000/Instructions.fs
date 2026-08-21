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
    
    /// 0100 0000 11 mmm rrr : MOVE SR,<ea>
    let (|MoveFromSR|_|) data =
        if data &&& 0b1111111111000000 = 0b0100000011000000 then
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(eamode, eareg)
        else None

    /// 0000 0000 0111 1100 : ORI #<data>,SR
    let (|OriToSR|_|) data =
        if data = 0b0000000001111100 then Some()
        else None

    /// 0000 1010 0011 1100 : EORI #<data>,CCR
    let (|EoriToCcr|_|) data =
        if data = 0b0000101000111100 then Some()
        else None

    let (|Reset|_|) data =
        if data = 0b0100111001110000 then Some()
        else None

    let (|RTS|_|) data =
        if data = 0b0100111001110101 then Some()
        else None

    let (|RTE|_|) data =
        if data = 0b0100111001110011 then Some()
        else None

    /// 0100 1110 0100 nnnn : TRAP #<vector>
    let (|TRAP|_|) data =
        if data &&& 0b1111111111110000 = 0b0100111001000000 then
            let vector = byte data &&& 0b1111uy
            Some(vector)
        else None

    /// 0100 1110 0110 d rrr : MOVE An,USP (d=0) / MOVE USP,An (d=1)
    let (|MoveUsp|_|) data =
        if data &&& 0b1111111111110000 = 0b0100111001100000 then
            let direction = byte (data >>> 3) &&& 0b1uy
            let register = byte data &&& 0b111uy
            Some(direction, register)
        else None

    /// 0100 1110 0101 0 rrr : LINK An,#<displacement>
    let (|LINK|_|) data =
        if data &&& 0b1111111111111000 = 0b0100111001010000 then
            let register = byte data &&& 0b111uy
            Some(register)
        else None

    /// 0100 1110 0101 1 rrr : UNLK An
    let (|UNLK|_|) data =
        if data &&& 0b1111111111111000 = 0b0100111001011000 then
            let register = byte data &&& 0b111uy
            Some(register)
        else None
        
    let (|CMPI|_|) data =
        if (data &&& 0b1111111100000000) = 0b0000110000000000 then
            let size = byte (data &&& 0b0000000011000000) >>> 6
            let mode = byte (data &&& 0b0000000000111000) >>> 3
            let register = byte (data &&& 0b0000000000000111)
            Some(size, mode, register)
        else None
        
    /// 0000 0010 ss mmm rrr : ANDI #<data>,<ea>
    let (|ANDI|_|) data =
        if data &&& 0b1111111100000000 = 0b0000001000000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            let mode = byte (data >>> 3) &&& 0b111uy
            let register = byte data &&& 0b111uy
            Some(size, mode, register)
        else None

    /// 0000 0110 ss mmm rrr : ADDI #<data>,<ea>
    let (|ADDI|_|) data =
        if data &&& 0b1111111100000000 = 0b0000011000000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            let mode = byte (data >>> 3) &&& 0b111uy
            let register = byte data &&& 0b111uy
            Some(size, mode, register)
        else None

    /// 0000 1010 ss mmm rrr : EORI #<data>,<ea>
    let (|EORI|_|) data =
        if data &&& 0b1111111100000000 = 0b0000101000000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            let mode = byte (data >>> 3) &&& 0b111uy
            let register = byte data &&& 0b111uy
            Some(size, mode, register)
        else None

    let (|LEA|_|) data =
        //0100 rrr1 11ss sSSS
        if data &&& 0b1111000111000000 = 0b0100000111000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let mode = byte (data >>> 3) &&& 0b111uy
            let register2 = byte data &&& 0b111uy
            Some(register, mode, register2)
        else None
        
    let (|BCC|_|) data =
        //sample:
        //0110000000000000
        //0110CondDisp----
        
        if data &&& 0b1111000000000000 = 0b0110000000000000 then
            let condition : Condition = enum (data &&& 0b0000111100000000) >>> 8
            Some(condition, byte (data &&& 0b0000000011111111))
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
            //printfn "%s" data.toBits
            Some(register, opmode, eamode, eareg)
        else None
        
    /// 1100 xxx1 ooooo yyy : EXG (mode: 01000=Dx,Dy 01001=Ax,Ay 10001=Dx,Ay)
    /// Shares AND's top nibble but occupies EA-mode values that are otherwise illegal for AND,
    /// so this must be tried before the generic AND pattern.
    /// 1110 ccc d ss i TT rrr : Shift/Rotate register
    /// (d: 0=right,1=left; i: 0=immediate count,1=register count; TT: 00=AS,01=LS,10=ROX,11=RO)
    /// size=11 is the memory-shift form (different EA-based layout) and is excluded here.
    let (|ShiftRotate|_|) data =
        if data &&& 0b1111000000000000 = 0b1110000000000000 && (byte (data >>> 6) &&& 0b11uy) <> 0b11uy then
            let countOrReg = byte (data >>> 9) &&& 0b111uy
            let direction = byte (data >>> 8) &&& 0b1uy
            let size = byte (data >>> 6) &&& 0b11uy
            let useRegisterCount = byte (data >>> 5) &&& 0b1uy
            let shiftType = byte (data >>> 3) &&& 0b11uy
            let register = byte data &&& 0b111uy
            Some(countOrReg, direction, size, useRegisterCount, shiftType, register)
        else None

    /// 0000 rrr1 oo mmm rrr : BTST/BCHG/BCLR/BSET Dn,<ea>  (oo: 00=BTST,01=BCHG,10=BCLR,11=BSET)
    /// EAmode=001 (An) is illegal for bit ops and is reserved for MOVEP instead - excluded here.
    let (|BitOpDynamic|_|) data =
        if data &&& 0b1111000100000000 = 0b0000000100000000 then
            let eamode = byte (data >>> 3) &&& 0b111uy
            if eamode <> 0b001uy then
                let register = byte (data >>> 9) &&& 0b111uy
                let opmode = byte (data >>> 6) &&& 0b11uy
                let eareg = byte data &&& 0b111uy
                Some(register, opmode, eamode, eareg)
            else None
        else None

    /// 0101 ddd0 ssmmmrrr : ADDQ #<data>,<ea>  (size 11 is reserved for Scc/DBcc, excluded here)
    let (|ADDQ|_|) data =
        if data &&& 0b1111000100000000 = 0b0101000000000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            if size <> 0b11uy then
                let quickData = byte (data >>> 9) &&& 0b111uy
                let eamode = byte (data >>> 3) &&& 0b111uy
                let eareg = byte data &&& 0b111uy
                Some(quickData, size, eamode, eareg)
            else None
        else None

    /// 0101 ddd1 ssmmmrrr : SUBQ #<data>,<ea>  (size 11 is reserved for Scc/DBcc, excluded here)
    let (|SUBQ|_|) data =
        if data &&& 0b1111000100000000 = 0b0101000100000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            if size <> 0b11uy then
                let quickData = byte (data >>> 9) &&& 0b111uy
                let eamode = byte (data >>> 3) &&& 0b111uy
                let eareg = byte data &&& 0b111uy
                Some(quickData, size, eamode, eareg)
            else None
        else None

    let (|OR|_|) data =
        //1000 reg opm EAm EAr : OR/DIVU/DIVS
        //----reg
        //-------opm
        //----------EAm
        //-------------EAr
        //opmode 011 and 111 are reserved for DIVU/DIVS, not OR - see (|DIVU|_|)
        if data &&& 0b1111000000000000 = 0b1000000000000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let opmode = byte (data >>> 6) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            if opmode = 0b011uy || opmode = 0b111uy then None
            else Some(register, opmode, eamode, eareg)
        else None

    let (|DIVU|_|) data =
        //1000 reg 011 EAm EAr : DIVU.W <ea>,Dn
        if data &&& 0b1111000111000000 = 0b1000000011000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(register, eamode, eareg)
        else None

    let (|EXG|_|) data =
        if data &&& 0b1111000100000000 = 0b1100000100000000 then
            let mode = byte (data >>> 3) &&& 0b11111uy
            if mode = 0b01000uy || mode = 0b01001uy || mode = 0b10001uy then
                let rx = byte (data >>> 9) &&& 0b111uy
                let ry = byte data &&& 0b111uy
                Some(rx, mode, ry)
            else None
        else None

    let (|AND|_|) data =
        //1100 reg opm EAm EAr : AND/MULU/MULS
        //----reg
        //-------opm
        //----------EAm
        //-------------EAr
        //opmode 011 and 111 are reserved for MULU/MULS, not AND - see (|MULU|_|)
        if data &&& 0b1111000000000000 = 0b1100000000000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let opmode = byte (data >>> 6) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            if opmode = 0b011uy || opmode = 0b111uy then None
            else Some(register, opmode, eamode, eareg)
        else None

    let (|MULU|_|) data =
        //1100 reg 011 EAm EAr : MULU.W <ea>,Dn
        if data &&& 0b1111000111000000 = 0b1100000011000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(register, eamode, eareg)
        else None

    let (|MULS|_|) data =
        //1100 reg 111 EAm EAr : MULS.W <ea>,Dn
        if data &&& 0b1111000111000000 = 0b1100000111000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(register, eamode, eareg)
        else None

    let (|ADD|_|) data =
        //1101 reg opm EAm EAr : ADD/ADDA/ADDX
        //----reg
        //-------opm
        //----------EAm
        //-------------EAr
        if data &&& 0b1111000000000000 = 0b1101000000000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let opmode = byte (data >>> 6) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(register, opmode, eamode, eareg)
        else None

    /// 0101 cccc 11001 rrr : DBcc Dr,<disp>
    let (|DBcc|_|) data =
        if data &&& 0b1111000011111000 = 0b0101000011001000 then
            let condition : Condition = enum (data &&& 0b0000111100000000) >>> 8
            let register = byte data &&& 0b111uy
            Some(condition, register)
        else None

    /// 0101 cccc 11 EEE eee : Scc <ea> (EAmode=001 is DBcc instead, not Scc)
    let (|Scc|_|) data =
        if data &&& 0b1111000011000000 = 0b0101000011000000 then
            let eamode = byte (data >>> 3) &&& 0b111uy
            if eamode <> 0b001uy then
                let condition : Condition = enum (data &&& 0b0000111100000000) >>> 8
                let eareg = byte data &&& 0b111uy
                Some(condition, eamode, eareg)
            else None
        else None

    let (|CMP|_|) data =
        //1011 rrr opm EAmEAr : CMP/CMPA/EOR
        //----reg
        //-------opm
        //----------EAm
        //-------------EAr
        if data &&& 0b1111000000000000 = 0b1011000000000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let opmode = byte (data >>> 6) &&& 0b111uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(register, opmode, eamode, eareg)
        else None

    let (|JSR|_|) data =
        //0100111010sssSSS
        //sss = effective address mode, SSS = effective address register
        if data &&& 0b1111111111000000 = 0b0100111010000000 then
            let eaMode = byte (data >>> 3) &&& 0b111uy
            let eaReg = byte (data &&& 0b111)
            Some(eaMode, eaReg)
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
    ///00zzdddDDDsssSSS
    let (|Move|_|) (data: int) = 
        let inline byteWordOrLong b =
            match b with 0b01 | 0b11 | 0b10 -> true | _ -> false
            
        if data &&& 0b1100000000000000 = 0 && byteWordOrLong (data >>> 12) then
            let size =
                let s = data >>> 12 &&& 0b11
                match s with
                | 0b01 -> OperandSize.Byte
                | 0b11 -> OperandSize.Word
                | 0b10 -> OperandSize.Long
                | other -> failwithf "Invalid operand size %u" other
              
            let dest_reg    = byte (data >>> 9) &&& 0b111uy
            let dest_mode   = byte (data >>> 6) &&& 0b111uy
            let destEA =
                match dest_mode with
                | 0b000uy -> Dn(dest_reg)
                | 0b001uy -> An(dest_reg) //MOVEA
                | 0b010uy -> An_Indirect(dest_reg)
                | 0b011uy -> An_PostIncrement(dest_reg)
                | 0b100uy -> An_PreDecrement(dest_reg)
                | 0b101uy -> An_Displacement(dest_reg)
                | 0b110uy -> An_ByteDisplacement(dest_reg)
                | 0b111uy when dest_reg = 0b0uy -> Immediate(OperandSize.Word)
                | 0b111uy when dest_reg = 0b1uy -> Immediate(OperandSize.Long)
                | _ -> failwithf "Invalid destination effective address: mode: %u, reg: %u"  dest_mode dest_reg
            
            let source_mode = byte (data >>> 3) &&& 0b111uy
            let source_reg = byte (data &&& 0b111)
            
            Some(size, dest_reg, dest_mode, source_mode, source_reg)
        else None
        
    /// 0000 1000 00ss sSSS:00: BTST    #1,s[!Areg]
    ///return EA mode, EA register
    let (|BTSTImmediate|_|) data =
        if data &&& 0b1111111111000000 = 0b0000100000000000 then
            let mode = byte (data >>> 3) &&& 0b111uy
            let register = byte data &&& 0b111uy
            Some(mode,register)
        else None

    /// 0111 rrr0 dddddddd: MOVEQ #<data>,Dr
    ///return dest register, 8-bit signed data
    let (|MOVEQ|_|) data =
        if data &&& 0b1111000100000000 = 0b0111000000000000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let data8 = sbyte (data &&& 0xff)
            Some(register, data8)
        else None
    
    
    /// 0100 0010 ss mmm rrr : CLR
    let (|CLR|_|) data =
        if data &&& 0b1111111100000000 = 0b0100001000000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(size, eamode, eareg)
        else None

    /// 0100 1010 ss mmm rrr : TST
    let (|TST|_|) data =
        if data &&& 0b1111111100000000 = 0b0100101000000000 then
            let size = byte (data >>> 6) &&& 0b11uy
            let eamode = byte (data >>> 3) &&& 0b111uy
            let eareg = byte data &&& 0b111uy
            Some(size, eamode, eareg)
        else None

    /// 0000 ddd1 oo 001 aaa : MOVEP
    let (|MOVEP|_|) data =
        if data &&& 0b1111000100111000 = 0b0000000100001000 then
            let register = byte (data >>> 9) &&& 0b111uy
            let opmode = byte (data >>> 6) &&& 0b111uy
            let addressReg = byte data &&& 0b111uy
            Some(register, opmode, addressReg)
        else None

    /// 0100 1d00 1s mmm rrr : MOVEM  (d: 0=reg->mem, 1=mem->reg; s: 0=word, 1=long)
    /// EAmode=000 (Dn direct) is illegal for MOVEM's memory-list operand and is reserved for EXT
    /// instead - see [[68k-opcode-space-aliasing]]. Excluded here so the two patterns are
    /// mutually exclusive by construction.
    let (|MOVEM|_|) data =
        if data &&& 0b1111101110000000 = 0b0100100010000000 then
            let eamode = byte (data >>> 3) &&& 0b111uy
            if eamode <> 0b000uy then
                let direction = byte (data >>> 10) &&& 0b1uy
                let size = byte (data >>> 6) &&& 0b1uy
                let eareg = byte data &&& 0b111uy
                Some(direction, size, eamode, eareg)
            else None
        else None

    /// 0100 1000 1s 000 rrr : EXT (s: 0=EXT.W byte->word, 1=EXT.L word->long, sign-extend Dn in place)
    let (|EXT|_|) data =
        if data &&& 0b1111111110111000 = 0b0100100010000000 then
            let size = byte (data >>> 6) &&& 0b1uy
            let register = byte data &&& 0b111uy
            Some(size, register)
        else None

    /// 0100 1000 0100 0 rrr : SWAP Dn (swap the two 16-bit halves of a data register)
    let (|SWAP|_|) data =
        if data &&& 0b1111111111111000 = 0b0100100001000000 then
            let register = byte data &&& 0b111uy
            Some register
        else None

    /// 0100 1000 01 mmm rrr : PEA <ea> (push the effective address, not its contents, onto the stack)
    /// EAmode=000 (Dn direct) is illegal for PEA (control addressing modes only) and is reserved
    /// for SWAP instead - see [[68k-opcode-space-aliasing]]. Excluded here so the two patterns are
    /// mutually exclusive by construction.
    let (|PEA|_|) data =
        if data &&& 0b1111111111000000 = 0b0100100001000000 then
            let eamode = byte (data >>> 3) &&& 0b111uy
            if eamode <> 0b000uy then
                let eareg = byte data &&& 0b111uy
                Some(eamode, eareg)
            else None
        else None

    /// 0000 rrr1 00ss sSSS:00: BTST    Dr,s[!Areg]
