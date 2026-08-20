namespace Atari
open Bits
type MMU(rom: byte array) =

    let memoryConfiguration = 0xFF8000u

    let videoDisplayRegisterStart = 0xFF8200u
    let videoDisplayRegisterEnd =  0xFF8260u
    let videoDisplayRegisterMemory = Array.create 96 0uy

    let reserved = 0xFF8400u
    let dma_diskcontroller = 0xFF8600u

    let ym2149IOMemory = Array.create 4 0uy
    let ym2149Start = 0xFF8800u
    let ym2149End =  0xFF8804u

    let mpf68901 = 0xFFFA00u
    let aciaStart = 0xFFFC00u
    let aciaEnd = 0xFFFC07u //keyboard ACIA (FC00 ctrl/status, FC02 data) + MIDI ACIA (FC04 ctrl/status, FC06 data)

    let romStart = 0xfc0000u
    let romEnd = 0xff0000u
    let cartStart = 0xfa0000u
    let cartEnd =  0xfc0000u

    let maxMemory = 0xffffffu

    let between (startAddress:uint32) (endAddress:uint32) (address:uint32) =
        if address >= startAddress && address <= endAddress then Some() else None

    let (|YM2149|_|) = between ym2149Start ym2149End
    let (|Rom|_|) = between romStart romEnd
    let (|Cart|_|) = between cartStart cartEnd
    let (|VideoDisplayRegister|_|) = between videoDisplayRegisterStart videoDisplayRegisterEnd
    let (|Acia|_|) = between aciaStart aciaEnd

    ///Minimal peripheral stub table, keyed by exact address: no real ACIA emulation, just enough
    ///for ROM code polling "can I send a byte" to not spin forever. Control/status registers
    ///report transmitter-ready (TDRE, bit1); anything else in the Acia range (data registers)
    ///falls through to the 0 default below since there's never real data waiting. If future ROM
    ///code waits to *receive* a byte (keyboard input, MIDI data) this needs real ACIA emulation,
    ///not more table entries - see [[atari-st-emulator-next-instructions]] memory for the note.
    let ioStubs : Map<uint32, byte> =
        Map.ofList [
            0xFFFC00u, 0x02uy //keyboard ACIA control/status
            0xFFFC04u, 0x02uy //MIDI ACIA control/status
        ]

    let ram = Array.create 1048576 0uy
        
    member x.ReadByte (address: uint32) =
        let address = address &&& maxMemory
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
        | Acia ->
            //See ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> v
            | None -> 0uy
        | _ ->
            //TODO: otherwise read from mem area
            0uy
    
    member x.ReadWord (address: uint32) =
        let address = address &&& maxMemory
        match address with
        | a when a < 7u -> 
            ((int rom.[int a]) <<< 8) |||
            (int rom.[int a+1])
        | Rom ->
            BigEndian.readWord rom (address &&& 0x3ffffu)
        | Cart -> failwithf "not implemented read from cart: %x" address
        | VideoDisplayRegister ->
            let indexIntoVReg = address - videoDisplayRegisterStart
            BigEndian.readWord videoDisplayRegisterMemory indexIntoVReg
        | Acia ->
            //See ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> int v
            | None -> 0
        | a -> BigEndian.readWord ram (a &&& 0xffffffu)
        
    member x.WriteWord (addr: uint32) (input: int16) =
        let address = uint32 (uint16 (addr &&& maxMemory)) //clip to max mem
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> failwithf "Attempt to write to Rom: $%08x" address
        | Cart -> failwithf "Attempt to write to Cart: $%08x" address
        | VideoDisplayRegister ->
            failwithf "not implemented write to Video Display Register: %x" address
        | YM2149 ->
            ym2149IOMemory.[int (address-ym2149Start)] <- byte (input >>> 8)
            ym2149IOMemory.[int (address-ym2149Start+1u)] <- byte input
        | _ ->
            ram.[int address]   <- byte (input >>> 8)
            ram.[int (address+1u)] <- byte (input &&& 0xffs)
               
    member x.WriteByte (addr: uint32) (input: byte) =
        let address = uint32 (uint16 (addr &&& maxMemory)) //clip to max mem
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> failwithf "Attempt to write to Rom: $%08x" address
        | Cart -> failwithf "Attempt to write to Cart: $%08x" address
        | VideoDisplayRegister ->
            failwithf "not implemented write to Video Display Register: %x" address
        | YM2149 ->
            ym2149IOMemory.[int (address-ym2149Start)] <- input
        | _ ->
            ram.[int address] <- input

    member x.WriteLong (addr: uint32) (input: int) =
        x.WriteWord addr (int16 (input >>> 16))
        x.WriteWord (addr+2u) (int16 input)

    ///Deep-copies the mutable memory-backed regions (not `rom`, which is never written).
    ///Used to roll back side effects after a speculative preview run - see `AtartSt.Preview`.
    member x.SnapshotRam() : byte[] * byte[] * byte[] =
        (Array.copy ram, Array.copy videoDisplayRegisterMemory, Array.copy ym2149IOMemory)

    member x.RestoreRam((ramSnapshot, videoSnapshot, ym2149Snapshot): byte[] * byte[] * byte[]) =
        Array.blit ramSnapshot 0 ram 0 ramSnapshot.Length
        Array.blit videoSnapshot 0 videoDisplayRegisterMemory 0 videoSnapshot.Length
        Array.blit ym2149Snapshot 0 ym2149IOMemory 0 ym2149Snapshot.Length

    member x.ReadLong (address: uint32) =
        match address with
        //The first 8 bytes (2 long Words) are mirrored from the rom area
        | a when a = 0u || a = 4u ->
           //read from rom as first 8 bytes mirrored
           ((int rom.[int a])   <<< 24) |||
           ((int rom.[int a+1]) <<< 16) |||
           ((int rom.[int a+2]) <<<  8) |||
           ( int rom.[int a+3])
        | Rom ->
            BigEndian.readLongWord rom (address &&& 0x3ffffu)
        | Cart ->  0xffffffff
          //failwithf "Not implemented read long from cart: %x" address
        | YM2149 ->
            let test = int (address-ym2149Start)
            let _ = sprintf "%x" test
            BigEndian.readLongWord ym2149IOMemory (uint32 (int (address-ym2149Start)))
        | _ -> BigEndian.readLongWord ram (address &&& 0xffffffu)
