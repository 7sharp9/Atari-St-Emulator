namespace Atari
open Bits
type MMU(rom:byte array, ram: byte array) =
    
    let ym2149IO = Array.create 4 0uy
    let ym2149Start = 0xFF8800u
    let ym2149End = 0xFF8804u
       
    let romStart = 0xfc0000u
    let romEnd = 0xff0000u
    let cartStart = 0xfa0000u
    let cartEnd = 0xfc0000u
    let maxMemory = 0xffffffu
    
    let (|YM2149|_|) address =
        if address >= ym2149Start && address <= ym2149End then Some()
        else None
    
    let (|Rom|_|) address =
        if address >= romStart && address <= romEnd then Some()
        else None
        
    let (|Cart|_|) address =
        if address >= cartStart && address <= cartEnd then Some()
        else None
        
    member x.ReadByte (address:uint32) =
        match address with
        | a when a <= 7u ->
            //Read from roms first 8 bytes
            rom.[int a]
        | Rom ->
            rom.[int (address &&& 0x3ffffu)]
        | _ -> 
            //TODO: otherwise read from mem area
            0uy 
    
    member x.ReadWord (address:uint32) =
        match address with
        | a when a < 7u -> 
            ((int rom.[int a]) <<< 8) |||
            (int rom.[int a+1])
        | a when a >= romStart && a <= romEnd ->
            readBigEndianWord rom (a &&& 0x3ffffu)
            
        | _ -> failwith "Dont care"
        
    member x.WriteWord (addr:uint32) input =
        //TODO: defensive coding around resricted ram/rom
        let address = addr &&& maxMemory //clip to max mem
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> failwithf "Attempt to write to Rom: $%08x" address
        | Cart -> failwithf "Attempt to write to Cart: $%08x" address
        | YM2149 -> ym2149IO.[int (address-ym2149Start)] <- byte (input >>> 8)
                    ym2149IO.[int (address-ym2149Start+1u)] <- byte input
        | _ ->
            ram.[int address]   <- byte (input >>> 8)
            ram.[int (address+1u)] <- byte (input &&& 0xffs)
               
    member x.ReadLong (address:uint32) =
        match address with
        //The first 8 bytes (2 long Words) are mirrored from the rom area
        | a when a = 0u || a = 4u ->
           //read from rom as first 8 bytes mirrored
           ((int rom.[int a])   <<< 24) |||
           ((int rom.[int a+1]) <<< 16) |||
           ((int rom.[int a+2]) <<<  8) |||
           ( int rom.[int a+3])
        | Rom ->
            readBigEndianLWord rom (address &&& 0x3ffffu)
        | Cart -> 
            //TODO support cart
            0xffffffff
        | _ -> 
            //TODO read normal ram, check memory extents
            0
