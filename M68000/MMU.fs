namespace Atari
open Bits

///Everything SnapshotRam/RestoreRam need to roll back a speculative run exactly - previously just
///the three byte arrays, which silently missed the MFP's register bank and Timer B's scalar state
///(tbcr/tbdr/tbdrReload/tbdrReadCount). A Preview that touched the MFP would permanently corrupt
///the real run's timer state on "rollback", contradicting Preview's own "state restored" claim.
type MmuSnapshot =
    { Ram: byte[]; VideoDisplayRegisters: byte[]; Ym2149: byte[]; MfpRegisters: byte[]
      Tbcr: byte; Tbdr: byte; TbdrReload: byte; TbdrReadCount: uint32 }

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
    let mfpEnd = 0xFFFA2Fu //last of the MC68901's byte-wide registers (base+$00 to base+$2F)
    let mfpTbcr = 0xFFFA1Bu //Timer B control register
    let mfpTbdr = 0xFFFA21u //Timer B data register
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
    let (|Mfp|_|) = between mpf68901 mfpEnd

    ///Counts every actual emulator-visible state change (a byte store that changes a value, or an
    ///internal side effect - like the TBDR poll's read-triggered countdown - that could change
    ///future behavior even though it isn't itself directly readable). Consumed by the loop
    ///detector in Program.fs: if this hasn't moved between two points where the full CPU state is
    ///identical, the machine is PROVABLY stuck (Step() is a pure function of Cpu + this MMU's
    ///state, and nothing else in the interpreter holds any other mutable state - verified by
    ///inspection of 68k.fs/Instructions.fs/Extensions.fs), not just "probably" stuck from having
    ///revisited a state many times. See the loop-detection comment in Program.fs for the full
    ///reasoning. Soundness of that proof depends on every real state change in this file bumping
    ///this counter - route new mutable peripheral state through `store` (byte arrays) or bump
    ///explicitly (scalar fields like tbcr/tbdr) rather than writing around it.
    let mutable mutations = 0UL
    let store (arr: byte[]) (i: int) (v: byte) =
        if arr.[i] <> v then
            arr.[i] <- v
            mutations <- mutations + 1UL

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

    ///Minimal MFP Timer B stub: real hardware decrements TBDR on each external clock event
    ///(HBLANK in event-count mode, much slower than CPU instruction execution) and reloads it from
    ///the last-armed value on underflow. We have no real clock source, so instead decrement TBDR
    ///once every `tbdrDecrementPeriod` CPU reads of it while armed (tbcr <> 0uy), rather than on
    ///every read - this reproduces both properties ROM code depends on: a poll spinning on TBDR
    ///eventually observes it count down to any given terminal value, AND two back-to-back reads a
    ///few instructions apart (a "has it changed" debounce idiom the boot ROM also uses) normally
    ///see the same value, matching real hardware where a tick is rare relative to instruction
    ///execution. The period is an arbitrary tuning constant, not a real HBLANK-accurate rate (this
    ///emulator has no cycle counting to derive one from) - picked only to comfortably exceed the
    ///longest known back-to-back read run in the boot ROM's debounce loop (~617 reads). Every
    ///other MFP register (GPIP, AER, DDR, interrupt enable/pending/in-service/mask, vector
    ///register, Timer A/C/D control and data, USART control/status/data, etc.) is backed by plain
    ///read/write storage instead - accurate for what the CPU sees on a bare register access (their
    ///special behavior - interrupts actually firing, the USART actually shifting bits, timers
    ///actually counting - is not modeled, but nothing in the boot ROM so far depends on that, only
    ///on writes to these registers being readable back). Confirmed necessary, not speculative: the
    ///ROM write/read-verifies several MFP registers in a loop (TADR/TBDR/TCDR/TDDR among them) as
    ///part of its own hardware-presence check, and got stuck forever on any of them that still
    ///silently dropped writes.
    let tbdrDecrementPeriod = 700u
    let mfpRegisters = Array.create (int (mfpEnd - mpf68901) + 1) 0uy
    let mutable tbcr = 0uy
    let mutable tbdr = 0uy
    let mutable tbdrReload = 0uy
    let mutable tbdrReadCount = 0u

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

    member x.ReadByte (address: uint32) =
        let address = address &&& maxMemory
        match address with
        | a when a <= 7u ->
            //Read from roms first 8 bytes
            rom.[int a]
        | Rom ->
            rom.[int (address &&& 0x3ffffu)]
        | Cart ->
            0xffuy //no cartridge present
        | VideoDisplayRegister ->
            videoDisplayRegisterMemory.[int (address - videoDisplayRegisterStart)]
        | a when a = mfpTbdr ->
            let v = tbdr
            if tbcr <> 0uy then
                //tbdrReadCount always changes on every armed read, even on passes where tbdr
                //itself doesn't - that's still a real change to state that affects when the next
                //visible decrement happens, so it must count as a mutation for the loop detector
                //to stay sound (see the field's comment above).
                mutations <- mutations + 1UL
                tbdrReadCount <- tbdrReadCount + 1u
                if tbdrReadCount >= tbdrDecrementPeriod then
                    tbdrReadCount <- 0u
                    tbdr <- (if tbdr = 0uy then tbdrReload else tbdr - 1uy)
            v
        | a when a = mfpTbcr -> tbcr
        | Mfp -> mfpRegisters.[int (address - mpf68901)]
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
        | a when a < 7u ->
            ((int rom.[int a]) <<< 8) |||
            (int rom.[int a+1])
        | Rom ->
            BigEndian.readWord rom (address &&& 0x3ffffu)
        | Cart -> 0xffff //no cartridge present
        | VideoDisplayRegister ->
            let indexIntoVReg = address - videoDisplayRegisterStart
            BigEndian.readWord videoDisplayRegisterMemory indexIntoVReg
        | Mfp ->
            //Same asymmetry bug as WriteWord had (see its comment): word/long access to the MFP's
            //byte-wide registers used to fall through to the generic 0/unmapped default instead of
            //actually reading TBDR/TBCR/mfpRegisters. Delegate byte-by-byte to ReadByte so any
            //address-specific side effect (TBDR's countdown) fires exactly once, at the right byte.
            (int (x.ReadByte address) <<< 8) ||| int (x.ReadByte (address+1u))
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
        | Rom -> () //real ROM chips can't be written; ignored rather than a bus error
        | Cart -> () //no cartridge present; writes go nowhere, matching the read side's fixed $ff(ff) stub
        | VideoDisplayRegister ->
            let i = int (address - videoDisplayRegisterStart)
            store videoDisplayRegisterMemory i (byte (input >>> 8))
            store videoDisplayRegisterMemory (i+1) (byte (input &&& 0xffs))
        | YM2149 ->
            store ym2149IOMemory (int (address-ym2149Start)) (byte (input >>> 8))
            store ym2149IOMemory (int (address-ym2149Start+1u)) (byte input)
        | Mfp ->
            //Bug fix: this case didn't exist before, so word writes to any MFP register (TBDR/
            //TBCR included) were silently dropped while byte writes worked - a real asymmetry, not
            //just a missing feature, since ROM code that happened to use a word-sized MOVE here
            //would have looked "stuck" for no visible reason. Delegate byte-by-byte to WriteByte
            //so TBDR/TBCR's arm/reload semantics and mutation-bumping stay in one place.
            x.WriteByte address (byte (input >>> 8))
            x.WriteByte (address+1u) (byte input)
        | _ ->
            if aliasIntoRam address then
                let masked = address &&& ramMask
                store ram (int masked) (byte (input >>> 8))
                store ram (int ((masked+1u) &&& ramMask)) (byte (input &&& 0xffs))
            //else: genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap) - write ignored

    member x.WriteByte (addr: uint32) (input: byte) =
        let address = addr &&& maxMemory //clip to the 24-bit address bus
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> () //real ROM chips can't be written; ignored rather than a bus error
        | Cart -> () //no cartridge present; writes go nowhere, matching the read side's fixed $ff(ff) stub
        | VideoDisplayRegister ->
            store videoDisplayRegisterMemory (int (address - videoDisplayRegisterStart)) input
        | YM2149 ->
            store ym2149IOMemory (int (address-ym2149Start)) input
        | a when a = mfpTbdr ->
            //Writing the *same* value still resets tbdrReadCount, which is a real state change
            //(it re-phases the next visible decrement) even when tbdr/tbdrReload don't move - so
            //this can't be a plain `store`-style value compare, it needs the count folded in too.
            if tbdr <> input || tbdrReload <> input || tbdrReadCount <> 0u then
                mutations <- mutations + 1UL
            tbdr <- input
            tbdrReload <- input
            tbdrReadCount <- 0u
        | a when a = mfpTbcr ->
            if tbcr <> input || tbdrReadCount <> 0u then
                mutations <- mutations + 1UL
            tbcr <- input
            tbdrReadCount <- 0u
        | Mfp -> store mfpRegisters (int (address - mpf68901)) input
        | _ ->
            if aliasIntoRam address then store ram (int (address &&& ramMask)) input
            //else: genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap) - write ignored

    member x.WriteLong (addr: uint32) (input: int) =
        x.WriteWord addr (int16 (input >>> 16))
        x.WriteWord (addr+2u) (int16 input)

    ///How many emulator-visible state changes have happened so far - see the field's own comment
    ///above. Consumed by Program.fs's loop detector.
    member x.Mutations = mutations

    ///Deep-copies every mutable memory-backed and scalar peripheral region (not `rom`, which is
    ///never written) - see `MmuSnapshot`. Used to roll back side effects after a speculative
    ///preview run - see `AtartSt.Preview`.
    member x.SnapshotRam() : MmuSnapshot =
        { Ram = Array.copy ram
          VideoDisplayRegisters = Array.copy videoDisplayRegisterMemory
          Ym2149 = Array.copy ym2149IOMemory
          MfpRegisters = Array.copy mfpRegisters
          Tbcr = tbcr; Tbdr = tbdr; TbdrReload = tbdrReload; TbdrReadCount = tbdrReadCount }

    member x.RestoreRam(snapshot: MmuSnapshot) =
        Array.blit snapshot.Ram 0 ram 0 snapshot.Ram.Length
        Array.blit snapshot.VideoDisplayRegisters 0 videoDisplayRegisterMemory 0 snapshot.VideoDisplayRegisters.Length
        Array.blit snapshot.Ym2149 0 ym2149IOMemory 0 snapshot.Ym2149.Length
        Array.blit snapshot.MfpRegisters 0 mfpRegisters 0 snapshot.MfpRegisters.Length
        tbcr <- snapshot.Tbcr
        tbdr <- snapshot.Tbdr
        tbdrReload <- snapshot.TbdrReload
        tbdrReadCount <- snapshot.TbdrReadCount
        //Restoring bypasses every write path above, so none of it bumped `mutations` on the way in
        //- that's correct (a rollback isn't itself a "real" forward mutation to prove anything
        //against), but it does mean the loop detector's anchor may now describe a state from the
        //just-reverted speculative branch. AtartSt.Preview resets the detector's epoch right after
        //calling this, for exactly that reason.

    member x.ReadLong (address: uint32) =
        let address = address &&& maxMemory //clip to the 24-bit address bus, matching Read/WriteByte/Word
        match address with
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
        | Mfp -> //same reasoning as ReadWord's Mfp case above
            (int (x.ReadByte address) <<< 24) |||
            (int (x.ReadByte (address+1u)) <<< 16) |||
            (int (x.ReadByte (address+2u)) <<< 8) |||
            (int (x.ReadByte (address+3u)))
        | _ ->
            if aliasIntoRam address then
                let masked = address &&& ramMask
                (int ram.[int masked]           <<< 24) |||
                (int ram.[int ((masked+1u) &&& ramMask)] <<< 16) |||
                (int ram.[int ((masked+2u) &&& ramMask)] <<<  8) |||
                (int ram.[int ((masked+3u) &&& ramMask)])
            else 0 //genuinely unmapped bus (beyond ROM/cart, e.g. an unemulated peripheral gap)
