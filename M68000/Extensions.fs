namespace Atari
open System
open System.Numerics

module Bits =
    
    ///Logical shift to the right
    let inline (>>>&)  (x:int) (y:int)  = int32 (uint32 x >>> y)

    let setbit  index (value:int)=
        value ||| (1 <<< index)
    
    let setbits  indices (value)=
        indices |> List.fold (fun state index -> setbit index state) value
        
    type Byte with
        member x.toBits = Convert.ToString(x,2).PadLeft(8, '0')
        member x.isset i = x &&& (1uy <<< i) <> 0uy
        member x.isnotset i = (x &&& (1uy <<< i)) <> 1uy
        
    type Int32 with
        member x.setBit i = x ||| (1 <<< i)
        member x.toBits = Convert.ToString(x, 2).PadLeft(32, '0')
        member x.isset i = x &&& (1 <<< i) <> 0

    type UInt32 with
        member x.setBit i = x ||| (1u <<< i)
        member x.toBits = Convert.ToString(int64 x, 2).PadLeft(32, '0')
        member x.isSet i = x &&& (1u <<< i) <> 0u
        
    type Int16 with
        member x.setBit i = x ||| (1s <<< i)
        member x.toBits = Convert.ToString(x, 2).PadLeft(16, '0')
        member x.isset i = x &&& (1s <<< i) <> 0s
        member x.isset_be i = x &&& (1s >>> i) <> 0s
        
    type UInt16 with
        member x.setBit i = x ||| (1us <<< i)
        member x.toBits = Convert.ToString(int64 x, 2).PadLeft(16, '0')
        member x.isset i = x &&& (1us <<< i) <> 0us
        
    let tobits (tw:IO.TextWriter) (i:int16) =
        tw.Write(Convert.ToString(i,2).PadLeft(16, '0'))
        
    let readBigEndianWord (bytes: byte array) (a:uint32) =
        ((int bytes.[int a]) <<< 8) |||
        (int  bytes.[int a+1])
            
    let readBigEndianLWord (bytes: byte array) (a:uint32) =
        ((int bytes.[int a])   <<< 24) |||
        ((int bytes.[int a+1]) <<< 16) |||
        ((int bytes.[int a+2]) <<<  8) |||
        ( int bytes.[int a+3])
