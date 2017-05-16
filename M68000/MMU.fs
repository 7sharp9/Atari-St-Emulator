namespace Atari
open Bits
type MMU(rom:byte array, ram: byte array) =

    let memoryConfiguration = 0xFF8000u

    let videoDisplayRegisterStart, videoDisplayRegisterEnd = 0xFF8200u, 0xFF8260u
    let videoDisplayRegisterMemory = Array.create 96 0uy

    let reserved = 0xFF8400u
    let dma_diskcontroller = 0xFF8600u

    let ym2149IOMemory = Array.create 4 0uy
    let ym2149Start, ym2149End = 0xFF8800u, 0xFF8804u

    let mpf68901 = 0xFFFA00u
    let midi = 0xFFFC00u

    let romStart, romEnd = 0xfc0000u, 0xff0000u
    let cartStart, cartEnd = 0xfa0000u, 0xfc0000u

    let maxMemory = 0xffffffu

    let between (starta:uint32) (enda:uint32) (address:uint32) =
        if address >= starta && address <= enda then Some() else None

    let (|YM2149|_|) = between ym2149Start ym2149End
    let (|Rom|_|) = between romStart romEnd
    let (|Cart|_|) = between cartStart cartEnd
    let (|VideoDisplayRegister|_|) = between videoDisplayRegisterStart videoDisplayRegisterEnd
        
    member x.ReadByte (address:uint32) =
        match address with
        | a when a <= 7u ->
            //Read from roms first 8 bytes
            rom.[int a]
        | Rom ->
            rom.[int (address &&& 0x3ffffu)]
        | Cart ->
            failwith "not implemented"
        | VideoDisplayRegister ->
            failwith "not implemented"
        | _ -> 
            //TODO: otherwise read from mem area
            0uy 
    
    member x.ReadWord (address:uint32) =
        let address = address &&& maxMemory
        match address with
        | a when a < 7u -> 
            ((int rom.[int a]) <<< 8) |||
            (int rom.[int a+1])
        | Rom ->
            readBigEndianWord rom (address &&& 0x3ffffu)
        | Cart -> failwithf "not implemented read from cart: %x" address
        | VideoDisplayRegister ->
            let indexIntoVReg = address - videoDisplayRegisterStart
            readBigEndianWord videoDisplayRegisterMemory indexIntoVReg
        | a -> readBigEndianWord ram (a &&& 0xffffffu)
        
    member x.WriteWord (addr:uint32) input =
        let address = uint32 (uint16 (addr &&& maxMemory)) //clip to max mem
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> failwithf "Attempt to write to Rom: $%08x" address
        | Cart -> failwithf "Attempt to write to Cart: $%08x" address
        | VideoDisplayRegister ->
            failwithf "not implemented write to %x" address
        | YM2149 -> ym2149IOMemory.[int (address-ym2149Start)] <- byte (input >>> 8)
                    ym2149IOMemory.[int (address-ym2149Start+1u)] <- byte input
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
        | Cart ->  0xffffffff
          //failwithf "Not implemented read long from cart: %x" address
        | YM2149 ->
            let ttt = int (address-ym2149Start)
            let tttt = sprintf "%x" ttt
            readBigEndianLWord ym2149IOMemory (uint32 (int (address-ym2149Start)))
        | _ -> readBigEndianLWord ram (address &&& 0xffffffu)
