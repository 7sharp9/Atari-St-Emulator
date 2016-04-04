namespace Atari
open Bits
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
