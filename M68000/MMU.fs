namespace Atari
open Bits

///Everything SnapshotRam/RestoreRam need to roll back a speculative run exactly - previously just
///the three byte arrays, which silently missed the MFP's register bank and Timer B's scalar state
///(tbcr/tbdr/tbdrReload/tbdrReadCount). A Preview that touched the MFP would permanently corrupt
///the real run's timer state on "rollback", contradicting Preview's own "state restored" claim.
type MmuSnapshot =
    { Ram: byte[]; VideoDisplayRegisters: byte[]; Ym2149: byte[]; MfpRegisters: byte[]
      Tbcr: byte; Tbdr: byte; TbdrReload: byte; TbdrReadCount: uint32
      FdcSelectedReg: byte; FdcStatus: byte; FdcTrack: byte; FdcSector: byte; FdcData: byte
      DmaAddrHigh: byte; DmaAddrMid: byte; DmaAddrLow: byte }

///Real 68000 hardware cannot perform a word/long-sized bus access to an odd address - it traps
///to the Address Error vector (vector 3) instead of completing the access. Raised by
///ReadWord/WriteWord/ReadLong (WriteLong composes from two WriteWord calls, so it's covered
///for free) so Cpu.Step() can catch it and push an exception frame the way TRAP does, instead of
///the previous behavior of silently performing the misaligned access and continuing with
///corrupted state - see [[atari-st-emulator-next-instructions]]'s nineteenth pass, found via a
///differential comparison against a real 68000 core (dmcoles/estyjs).
exception AddressError of address: uint32

///Real 68000 hardware bus-errors (vector 2) on any access to an address no device claims -
///DTACK never asserts, so the bus controller aborts the cycle rather than letting it complete.
///Raised by the genuinely-unmapped fallback case in ReadByte/ReadWord/ReadLong/WriteByte/WriteWord
///(previously: reads silently returned 0 and writes were silently dropped, both explicitly
///commented "genuinely unmapped bus" - a real gap, not a typo, dating back to the earliest
///out-of-range-RAM-aliasing work) - see [[atari-st-emulator-next-instructions]]'s twentieth pass,
///found by tracing a garbage `rte` target ($56780000, well outside ROM/RAM/cart/peripheral space)
///straight into an opcode-decode failure instead of a hardware fault.
exception BusError of address: uint32

type MMU(rom: byte array) =

    let memoryConfiguration = 0xFF8000u

    let videoDisplayRegisterStart = 0xFF8200u
    let videoDisplayRegisterEnd =  0xFF8260u
    let videoDisplayRegisterMemory = Array.create 98 0uy

    let reserved = 0xFF8400u
    let dma_diskcontroller = 0xFF8600u
    let fdcAccess = 0xFF8604u //WD1772 register access byte - which of its 4 registers this hits is selected via fdcModeSelect
    let fdcModeSelect = 0xFF8606u //DMA mode register; bits 1-2 select status/cmd, track, sector, or data register
    let dmaAddrHigh = 0xFF8609u //DMA Address Counter, high byte - real, documented, byte-wide-only (odd address) register
    let dmaAddrMid = 0xFF860Bu //DMA Address Counter, middle byte
    let dmaAddrLow = 0xFF860Du //DMA Address Counter, low byte

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

    ///Ad-hoc debug watchpoint (REPL `watch`/`unwatch`, see Program.fs) - prints via eprintfn (so it
    ///survives ATARI_NOTRACE) whenever a write touches [lo,hi]. Added after repeatedly hand-editing
    ///WriteByte/WriteWord with a temporary eprintfn to answer "does anything ever write $4C2" -
    ///style questions (see [[atari-st-emulator-next-instructions]]'s seventeenth-pass finding) -
    ///promoted to a permanent, always-available tool instead of re-adding and reverting the same
    ///throwaway edit next time the same kind of question comes up.
    let mutable watchRange : (uint32 * uint32) option = None
    let checkWatch (address: uint32) (label: string) (value: uint32) =
        match watchRange with
        | Some(lo, hi) when address >= lo && address <= hi ->
            eprintfn "WATCH: %s $%08x <- $%x" label address value
        | _ -> ()

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

    ///WD1772 FDC + DMA mode-select emulation. Real hardware accesses all 4 FDC registers (status-
    ///or-command, track, sector, data) through the single access byte at $FFFF8604; the DMA mode
    ///register at $FFFF8606 selects which one a subsequent $FFFF8604 access hits, via its bits 1-2
    ///(see FD-HD_Programming.pdf, "Accessing FDC Registers": $x80=status/command, $x82=track,
    ///$x84=sector, $x86=data). Previously neither address had any emulation at all - both fell
    ///through to the generic "genuinely unmapped, return 0" default in Read/WriteByte, so every
    ///status read always came back 0. On a real WD1772, a status register of 0 means "not busy, no
    ///errors" - i.e. success - which is backwards for "no disk present": this emulator has no
    ///disk-image support, so every floppy command should report the failure real hardware would
    ///report with an empty drive, not silent success. NOTE: an earlier version of this comment
    ///claimed this always-0 status was the cause of the boot-reset loop (via a bogus disk-present
    ///bit reaching TOS's boot-device check) - that was the initial hypothesis, but a later same-session
    ///trace comparison (with this fix in place vs without) showed the reset-cycle boundaries were
    ///byte-for-byte identical either way, disproving it. This fix is still correct and worth keeping
    ///(a status of 0 is genuinely wrong for an empty drive), just not the explanation for that bug -
    ///see [[atari-st-emulator-next-instructions]]'s fifteenth-pass section for the actual finding.
    let mutable fdcSelectedReg = 0uy //bits 1-2 of the last fdcModeSelect write: 0=status/cmd, 1=track, 2=sector, 3=data
    let mutable fdcStatus = 0uy
    let mutable fdcTrack = 0uy
    let mutable fdcSector = 0uy
    let mutable fdcData = 0uy

    ///The DMA Address Counter's three bytes (FD-HD_Programming.pdf: "DMA Registers Address Map") -
    ///a real, 22-bits-used-of-24 internal address register the DMA chip uses to know where in RAM
    ///to read/write during a floppy transfer. Boot ROM routinely writes this (in the documented
    ///Low/Mid/High order) before starting any FDC command, even though this emulator has no actual
    ///DMA-driven memory transfer to point it at (FDC completion is an instant, always-computed
    ///status byte - see fdcCommandStatus's comment) - so these three bytes just need to exist as
    ///real, addressable storage rather than falling through to "genuinely unmapped bus".
    let mutable dmaAddrHighByte = 0uy
    let mutable dmaAddrMidByte = 0uy
    let mutable dmaAddrLowByte = 0uy

    ///Per FD-HD_Programming.pdf's "Status Register Summary": Type I commands (Restore/Seek/Step -
    ///opcode top bit clear) only need the mechanical track-00 sensor, which works with no disk
    ///present, so real hardware reports success (TR00 set, bit 2) regardless of whether a disk is
    ///in the drive. Type II/III commands (Read/Write Sector, Read Address/Track, Write Track -
    ///opcode top bit set, excluding Force Interrupt $D0-$DF) need to find a real ID field on the
    ///media; with no disk image loaded there is nothing to find, so real hardware reports Record
    ///Not Found (bit 4) after searching. Force Interrupt just goes idle. Busy (bit 0) is always
    ///clear on read-back - this emulator has no command timing, every command completes instantly.
    let fdcCommandStatus (command: byte) =
        if command < 0x80uy then 0x04uy //Type I: TR00 set, no seek error, not busy
        elif command >= 0xd0uy && command < 0xe0uy then 0uy //Force Interrupt: idle
        else 0x10uy //Type II/III: Record Not Found, not busy

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
        | YM2149 ->
            //Real device, just missing from this one access-width's match arms - previously fell
            //through to the generic "genuinely unmapped" default (silently 0), which happened to
            //read back the chip's real reset-state value here but only by coincidence, not because
            //this was actually unmapped bus. Surfaced as a false BusError once that default started
            //raising instead of returning 0 - see [[atari-st-emulator-next-instructions]]'s
            //twentieth pass.
            ym2149IOMemory.[int (address-ym2149Start)]
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
        | a when a = fdcAccess ->
            match fdcSelectedReg with
            | 0uy -> fdcStatus
            | 1uy -> fdcTrack
            | 2uy -> fdcSector
            | _ -> fdcData
        | a when a = fdcModeSelect -> fdcSelectedReg <<< 1
        | a when a = dmaAddrHigh -> dmaAddrHighByte
        | a when a = dmaAddrMid -> dmaAddrMidByte
        | a when a = dmaAddrLow -> dmaAddrLowByte
        | Acia ->
            //See ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> v
            | None -> 0uy
        | _ ->
            if aliasIntoRam address then ram.[int (address &&& ramMask)]
            else raise (BusError address)

    member x.ReadWord (address: uint32) =
        let address = address &&& maxMemory
        if address % 2u <> 0u then raise (AddressError address)
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
        | YM2149 ->
            //Same gap as ReadByte's YM2149 case - see its comment.
            BigEndian.readWord ym2149IOMemory (address-ym2149Start)
        | Mfp ->
            //Same asymmetry bug as WriteWord had (see its comment): word/long access to the MFP's
            //byte-wide registers used to fall through to the generic 0/unmapped default instead of
            //actually reading TBDR/TBCR/mfpRegisters. Delegate byte-by-byte to ReadByte so any
            //address-specific side effect (TBDR's countdown) fires exactly once, at the right byte.
            (int (x.ReadByte address) <<< 8) ||| int (x.ReadByte (address+1u))
        | a when a = fdcAccess ->
            //FD-HD_Programming.pdf, "$FF8604 R/W (16 bits)": "The DMA interface only uses 8 bits
            //when writing and therefore the upper byte is ignored and when reading the 8 upper
            //bits consistently reads 1." - a genuine 8-bit device on the low data-bus byte, not
            //two independently byte-addressable registers at `address`/`address+1` like the Mfp
            //case above. The old byte-by-byte split put the real status byte in the HIGH half of
            //the word instead, so every ROM `move.w $ffff8604.l,Dn` / `btst #n,Dn` check (which
            //only ever tests the low byte) always saw zero - see [[atari-st-emulator-next-instructions]]'s
            //seventeenth-pass finding for the full trace-verified diagnosis.
            0xFF00 ||| int (x.ReadByte address)
        | a when a = fdcModeSelect ->
            //Same low-byte-device reasoning as fdcAccess above, minus the "upper bits read as 1"
            //quirk (not documented for this register - FD-HD_Programming.pdf only states real
            //content, status bits 0-2, in the low byte).
            int (x.ReadByte address)
        | Acia ->
            //See ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> int v
            | None -> 0
        | a ->
            if aliasIntoRam a then
                let masked = a &&& ramMask
                ((int ram.[int masked]) <<< 8) ||| (int ram.[int ((masked+1u) &&& ramMask)])
            else raise (BusError a)

    member x.WriteWord (addr: uint32) (input: int16) =
        let address = addr &&& maxMemory //clip to the 24-bit address bus
        if address % 2u <> 0u then raise (AddressError address)
        checkWatch address "WriteWord" (uint32 (uint16 input))
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
        | a when a = fdcAccess || a = fdcModeSelect ->
            //See ReadWord's matching case just above - a single 8-bit device on the low
            //data-bus byte, per FD-HD_Programming.pdf's explicit "the upper byte is ignored"
            //for $FF8604 (applied to $FF8606 too, on the same low-byte-device reasoning). The
            //old code wrote the word's HIGH byte to `address` (the only byte that has any
            //effect, since `address+1u` doesn't match anything) - exactly backwards from what
            //its own comment claimed, and from what the ROM's low-byte-only writes actually need.
            x.WriteByte address (byte input)
        | Acia ->
            //No real ACIA write emulation (see ioStubs' comment on the read side) - a real, mapped
            //device, so writes are accepted and ignored rather than bus-erroring. Previously this
            //fell through to the generic "genuinely unmapped, write ignored" default, which had the
            //same observable effect (silently ignored) but for the wrong reason - now raises
            //BusError instead, so it needs its own case. See [[atari-st-emulator-next-instructions]]'s
            //twentieth pass.
            ()
        | _ ->
            if aliasIntoRam address then
                let masked = address &&& ramMask
                store ram (int masked) (byte (input >>> 8))
                store ram (int ((masked+1u) &&& ramMask)) (byte (input &&& 0xffs))
            else raise (BusError address)

    member x.WriteByte (addr: uint32) (input: byte) =
        let address = addr &&& maxMemory //clip to the 24-bit address bus
        checkWatch address "WriteByte" (uint32 input)
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
        | a when a = fdcModeSelect ->
            let selected = (input >>> 1) &&& 0x3uy
            if selected <> fdcSelectedReg then mutations <- mutations + 1UL
            fdcSelectedReg <- selected
        | a when a = fdcAccess ->
            match fdcSelectedReg with
            | 0uy ->
                let status = fdcCommandStatus input
                if status <> fdcStatus then mutations <- mutations + 1UL
                fdcStatus <- status
            | 1uy -> if input <> fdcTrack then mutations <- mutations + 1UL
                     fdcTrack <- input
            | 2uy -> if input <> fdcSector then mutations <- mutations + 1UL
                     fdcSector <- input
            | _ -> if input <> fdcData then mutations <- mutations + 1UL
                   fdcData <- input
        | a when a = dmaAddrHigh ->
            if input <> dmaAddrHighByte then mutations <- mutations + 1UL
            dmaAddrHighByte <- input
        | a when a = dmaAddrMid ->
            if input <> dmaAddrMidByte then mutations <- mutations + 1UL
            dmaAddrMidByte <- input
        | a when a = dmaAddrLow ->
            if input <> dmaAddrLowByte then mutations <- mutations + 1UL
            dmaAddrLowByte <- input
        | Acia ->
            //See WriteWord's matching case just above.
            ()
        | _ ->
            if aliasIntoRam address then store ram (int (address &&& ramMask)) input
            else raise (BusError address)

    member x.WriteLong (addr: uint32) (input: int) =
        x.WriteWord addr (int16 (input >>> 16))
        x.WriteWord (addr+2u) (int16 input)

    ///How many emulator-visible state changes have happened so far - see the field's own comment
    ///above. Consumed by Program.fs's loop detector.
    member x.Mutations = mutations

    ///REPL `watch <hexaddr> [len]` - see `checkWatch` above. `hi` is inclusive.
    member x.SetWatch (lo: uint32) (hi: uint32) = watchRange <- Some(lo, hi)
    member x.ClearWatch() = watchRange <- None

    ///Read-only peeks at Timer B's registers, for the CPU-level busy-wait fast-forward (see
    ///Cpu.TryFastForwardTbdrPoll) - unlike ReadByte's TBDR case, these have no side effects, so
    ///they're safe to use to *check* whether a poll would resolve without also advancing state.
    member x.PeekTbcr = tbcr
    member x.PeekTbdr = tbdr
    member x.TbdrAddress = mfpTbdr

    ///Resolves a TBDR busy-wait in one step instead of interpreting every intervening read. Real
    ///Timer B ticks on actual elapsed time (external HBLANK pulses); this model only advances on
    ///demand, once per `tbdrDecrementPeriod` reads (see that field's comment), so a tight poll has
    ///no way to "skip ahead" through its own artificial read-count clock on its own. Called only
    ///after the CPU has confirmed the exact "read TBDR / compare against a fixed target / branch
    ///back if unequal" instruction shape, so this is equivalent to letting that specific loop run
    ///to completion: its only externally-visible effect is TBDR eventually reading as `target`, so
    ///jump straight there instead of counting through every intervening read.
    member x.FastForwardTbdrTo (target: byte) =
        if tbcr <> 0uy && tbdr <> target then
            tbdr <- target
            tbdrReadCount <- 0u
            mutations <- mutations + 1UL

    ///Deep-copies every mutable memory-backed and scalar peripheral region (not `rom`, which is
    ///never written) - see `MmuSnapshot`. Used to roll back side effects after a speculative
    ///preview run - see `AtartSt.Preview`.
    member x.SnapshotRam() : MmuSnapshot =
        { Ram = Array.copy ram
          VideoDisplayRegisters = Array.copy videoDisplayRegisterMemory
          Ym2149 = Array.copy ym2149IOMemory
          MfpRegisters = Array.copy mfpRegisters
          Tbcr = tbcr; Tbdr = tbdr; TbdrReload = tbdrReload; TbdrReadCount = tbdrReadCount
          FdcSelectedReg = fdcSelectedReg; FdcStatus = fdcStatus; FdcTrack = fdcTrack
          FdcSector = fdcSector; FdcData = fdcData
          DmaAddrHigh = dmaAddrHighByte; DmaAddrMid = dmaAddrMidByte; DmaAddrLow = dmaAddrLowByte }

    member x.RestoreRam(snapshot: MmuSnapshot) =
        Array.blit snapshot.Ram 0 ram 0 snapshot.Ram.Length
        Array.blit snapshot.VideoDisplayRegisters 0 videoDisplayRegisterMemory 0 snapshot.VideoDisplayRegisters.Length
        Array.blit snapshot.Ym2149 0 ym2149IOMemory 0 snapshot.Ym2149.Length
        Array.blit snapshot.MfpRegisters 0 mfpRegisters 0 snapshot.MfpRegisters.Length
        tbcr <- snapshot.Tbcr
        tbdr <- snapshot.Tbdr
        tbdrReload <- snapshot.TbdrReload
        tbdrReadCount <- snapshot.TbdrReadCount
        fdcSelectedReg <- snapshot.FdcSelectedReg
        fdcStatus <- snapshot.FdcStatus
        fdcTrack <- snapshot.FdcTrack
        fdcSector <- snapshot.FdcSector
        fdcData <- snapshot.FdcData
        dmaAddrHighByte <- snapshot.DmaAddrHigh
        dmaAddrMidByte <- snapshot.DmaAddrMid
        dmaAddrLowByte <- snapshot.DmaAddrLow
        //Restoring bypasses every write path above, so none of it bumped `mutations` on the way in
        //- that's correct (a rollback isn't itself a "real" forward mutation to prove anything
        //against), but it does mean the loop detector's anchor may now describe a state from the
        //just-reverted speculative branch. AtartSt.Preview resets the detector's epoch right after
        //calling this, for exactly that reason.

    member x.ReadLong (address: uint32) =
        let address = address &&& maxMemory //clip to the 24-bit address bus, matching Read/WriteByte/Word
        if address % 2u <> 0u then raise (AddressError address)
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
        | a when a = fdcAccess -> //same low-byte-device reasoning as ReadWord's Fdc case above
            0xFFFFFF00 ||| int (x.ReadByte address)
        | a when a = fdcModeSelect -> //same reasoning, minus fdcAccess's documented "reads as 1" quirk
            int (x.ReadByte address)
        | _ ->
            if aliasIntoRam address then
                let masked = address &&& ramMask
                (int ram.[int masked]           <<< 24) |||
                (int ram.[int ((masked+1u) &&& ramMask)] <<< 16) |||
                (int ram.[int ((masked+2u) &&& ramMask)] <<<  8) |||
                (int ram.[int ((masked+3u) &&& ramMask)])
            else raise (BusError address)
