namespace Atari
open System
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
        
    let readBigEndianWord (bytes: byte array) a =
        ((int bytes.[a]) <<< 8) |||
        (int  bytes.[a+1])
            
    let readBigEndianLWord (bytes: byte array) a =
        ((int bytes.[a])   <<< 24) |||
        ((int bytes.[a+1]) <<< 16) |||
        ((int bytes.[a+2]) <<<  8) |||
        ( int bytes.[a+3])
