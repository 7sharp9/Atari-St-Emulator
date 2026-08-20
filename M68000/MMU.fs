namespace Atari
open Bits
type MMU(rom: byte array) =

    let memoryConfiguration = 0xFF8000u

    let videoDisplayRegisterStart = 0xFF8200u
    let videoDisplayRegisterEnd =  0xFF8260u
    let videoDisplayRegisterMemory = Array.create 98 0uy

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

    ///Real ST hardware only has `ram.Length` bytes of RAM physically installed, but the GLUE/MMU's
    ///address decoding for that bank doesn't stop at the installed size - addresses between the top
    ///of RAM and the start of cartridge/ROM space (cartStart) alias back into the same RAM chips
    ///rather than going to an unmapped/bus-error bus. This is why TOS's own boot ROM can safely use
    ///the raw reset-vector SSP ($601E0100, masked to $1E0100 - well above `ram.Length`) as scratch
    ///stack space for early hardware-probe code, before it sets up a real stack: on real hardware
    ///that address mirrors back into installed RAM. Only applies below cartStart - genuinely
    ///unmapped/unemulated peripheral gaps above ROM (e.g. mpf68901) still fall through to the 0/drop
    ///default further down, since aliasing those into RAM would be a worse stub than a flat 0.
    let ramMask = uint32 (ram.Length - 1)
    let aliasIntoRam (address: uint32) = address < cartStart

    ///Real ST hardware mirrors only the CPU's own 8-byte reset-vector fetch (SSP at $0, PC at $4)
    ///at low memory - see [[atari-st-emulator-next-instructions]]. But TOS's own ROM header is
    ///deliberately crafted so those 8 bytes double as valid code (the first word decodes as a
    ///branch into real early-boot init code a little further along), and a critical error raised
    ///before TOS installs the real exception-vector table (still early boot - `etv_critic` at $404
    ///reads as 0) jumps through that uninitialized vector to address 0, relying on this trick as a
    ///soft-restart. Extending the mirror just far enough to cover that short init snippet (through
    ///the point it jumps back to a real high ROM address) lets that path play out like real
    ///hardware, without shadowing the wider low-memory range TOS later writes real vector-table
    ///data into - deliberately narrow, not a general ROM/RAM overlay bank-switch.
    let lowRomMirrorEnd = 0x100u

    member x.ReadByte (address: uint32) =
        let address = address &&& maxMemory
        match address with
        | a when a < lowRomMirrorEnd ->
            //Mirror ROM at low memory - see lowRomMirrorEnd's comment above.
            rom.[int a]
        | Rom ->
            rom.[int (address &&& 0x3ffffu)]
        | Cart ->
            0xffuy //no cartridge present
        | VideoDisplayRegister ->
            videoDisplayRegisterMemory.[int (address - videoDisplayRegisterStart)]
        | Acia ->
            //See ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> v
            | None -> 0uy
        | _ ->
            if aliasIntoRam address then ram.[int (address &&& ramMask)]
            else 0uy //genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap)

    member x.ReadWord (address: uint32) =
        let address = address &&& maxMemory
        match address with
        | a when a < lowRomMirrorEnd ->
            ((int rom.[int a]) <<< 8) |||
            (int rom.[int a+1])
        | Rom ->
            BigEndian.readWord rom (address &&& 0x3ffffu)
        | Cart -> 0xffff //no cartridge present
        | VideoDisplayRegister ->
            let indexIntoVReg = address - videoDisplayRegisterStart
            BigEndian.readWord videoDisplayRegisterMemory indexIntoVReg
        | Acia ->
            //See ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> int v
            | None -> 0
        | a ->
            if aliasIntoRam a then
                let masked = a &&& ramMask
                ((int ram.[int masked]) <<< 8) ||| (int ram.[int ((masked+1u) &&& ramMask)])
            else 0 //genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap)

    member x.WriteWord (addr: uint32) (input: int16) =
        let address = addr &&& maxMemory //clip to the 24-bit address bus
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | a when a < lowRomMirrorEnd -> () //mirrors ROM at low memory - see lowRomMirrorEnd's comment
        | Rom -> () //real ROM chips can't be written; ignored rather than a bus error
        | Cart -> failwithf "Attempt to write to Cart: $%08x" address
        | VideoDisplayRegister ->
            let i = int (address - videoDisplayRegisterStart)
            videoDisplayRegisterMemory.[i]   <- byte (input >>> 8)
            videoDisplayRegisterMemory.[i+1] <- byte (input &&& 0xffs)
        | YM2149 ->
            ym2149IOMemory.[int (address-ym2149Start)] <- byte (input >>> 8)
            ym2149IOMemory.[int (address-ym2149Start+1u)] <- byte input
        | _ ->
            if aliasIntoRam address then
                let masked = address &&& ramMask
                ram.[int masked] <- byte (input >>> 8)
                ram.[int ((masked+1u) &&& ramMask)] <- byte (input &&& 0xffs)
            //else: genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap) - write ignored

    member x.WriteByte (addr: uint32) (input: byte) =
        let address = addr &&& maxMemory //clip to the 24-bit address bus
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | a when a < lowRomMirrorEnd -> () //mirrors ROM at low memory - see lowRomMirrorEnd's comment
        | Rom -> () //real ROM chips can't be written; ignored rather than a bus error
        | Cart -> failwithf "Attempt to write to Cart: $%08x" address
        | VideoDisplayRegister ->
            videoDisplayRegisterMemory.[int (address - videoDisplayRegisterStart)] <- input
        | YM2149 ->
            ym2149IOMemory.[int (address-ym2149Start)] <- input
        | _ ->
            if aliasIntoRam address then ram.[int (address &&& ramMask)] <- input
            //else: genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap) - write ignored

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
        let address = address &&& maxMemory //clip to the 24-bit address bus, matching Read/WriteByte/Word
        match address with
        | a when a < lowRomMirrorEnd ->
            //Mirror ROM at low memory - see lowRomMirrorEnd's comment above.
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
        | _ ->
            if aliasIntoRam address then
                let masked = address &&& ramMask
                (int ram.[int masked]           <<< 24) |||
                (int ram.[int ((masked+1u) &&& ramMask)] <<< 16) |||
                (int ram.[int ((masked+2u) &&& ramMask)] <<<  8) |||
                (int ram.[int ((masked+3u) &&& ramMask)])
            else 0 //genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap)
