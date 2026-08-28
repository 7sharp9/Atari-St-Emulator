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
      DmaAddrHigh: byte; DmaAddrMid: byte; DmaAddrLow: byte
      MemConfig: byte
      KbdAciaControl: byte; IkbdRxFifo: byte[] }

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

    ///The MMU bank-size configuration register (real hardware: byte-wide, only the odd address
    ///$FF8001 is wired up - see stMemory.c's STMemory_MMU_Config_ReadByte/WriteByte, fetched from
    ///github.com/hatari/hatari for a ground-truth check since the local progref.txt's table for
    ///this register is column-garbled). Bits 2-3 = bank 0 size, bits 0-1 = bank 1 size, each 2 bits
    ///decoding 00=128KB 01=512KB 10=2048KB 11=reserved. TOS's own cold-boot RAM-sizing routine
    ///writes a candidate value here and probes real RAM to see what actually holds - previously
    ///unmapped (fell through to BusError, added in the twentieth pass), which crashed cold boot
    ///almost immediately at `$fc00e2: move.b #$a,$ffff8001.l` (confirmed via `tools/disassemble.py`)
    ///before TOS could even begin that probe - see [[atari-st-emulator-next-instructions]].
    let memConfig = 0xFF8001u

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
    ///Pending-interrupt line, modeling the CPU's IPL2-0 input pins: 0 = no interrupt asserted.
    ///Raised by a peripheral-timing source (currently just the VBL trigger in Program.fs's step
    ///loop - see [[atari-st-emulator-next-instructions]]'s twenty-eighth pass). Real, necessary
    ///infrastructure on its own merits (any future keyboard/IKBD work needs real interrupt
    ///delivery to reach TOS's own ISRs at all) - but NOT, on its own, the fix for the IPL=7 lock
    ///that motivated adding it: level 4 (VBL) and level 6 (MFP) requests are mechanically incapable
    ///of preempting an IPL=7 mask (only a genuine level-7/NMI request could, and none exists on
    ///this hardware), confirmed directly by instrumenting this exact mechanism - interrupts fire
    ///and get taken correctly right up until the mask locks to 7, then sit pending forever exactly
    ///as real 68000 semantics require. The real recovery mechanism, found via a Hatari instruction
    ///trace of the same ROM, is an ordinary (non-exception) instruction TOS itself executes shortly
    ///after the point where this project's own emulation currently diverges - see the twenty-eighth
    ///pass's final entry for the precise divergence point and next step. `Cpu.Step()` checks this
    ///each step against the live interrupt mask and, if unmasked, consumes it via
    ///AcknowledgeInterrupt and enters it as a real autovectored exception (`Cpu.EnterInterrupt`).
    ///Real hardware would let a higher-priority request preempt a lower still-pending one and hold multiple sources
    ///independently (per-source pending bits with priority arbitration) - this collapses to "the
    ///single highest level asserted right now, whatever raised it last," a deliberate
    ///simplification since only one source (VBL) exists yet; revisit if/when the MFP's own
    ///independent interrupt sources (timers, ACIA) are added.
    ///Two independent pending-interrupt slots, replacing the earlier single "highest level
    ///asserted" scalar (per that comment's own TODO). Real hardware holds a pending bit per
    ///source with priority arbitration; the two sources that actually exist here are the VBL
    ///(autovectored level 4, vector 28) and the MFP (vectored level 6 - currently only the
    ///keyboard ACIA on channel 6, vector $46). One slot each is enough and, crucially, keeps a
    ///periodic VBL from silently displacing a still-pending keystroke interrupt (the single-slot
    ///model dropped whichever was lower). `PendingInterruptLevel`/`Vector` report the higher of
    ///whatever is asserted; `AcknowledgeInterrupt` clears only that one.
    let mutable vblPending = false
    let mutable mfpPending = false
    let mutable mfpVector = 0

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
            0xFFFC04u, 0x02uy //MIDI ACIA control/status - no receive path (nothing generates MIDI in)
        ]

    ///Keyboard ACIA (MC6850) receive path - see [[atari-st-emulator-next-instructions]] pass 34
    ///step 2. Real ST wiring: the IKBD's 7812.5-baud serial output feeds the keyboard ACIA at
    ///$FFFC00 (control/status) / $FFFC02 (data). A received byte sets RDRF (status bit 0); with
    ///the RX interrupt enabled (control bit 7, which TOS sets via its `move.b #$96,$fffc00`
    ///write) that also drives the ACIA IRQ output (status bit 7) low, which is MFP GPIP bit 4,
    ///which is MFP interrupt channel 6, which is 68000 IPL 6, vectored through address $118
    ///(vector $46 = MFP VR base $40 | channel 6). TOS's ISR at $fc281c reads status then data
    ///and loops while GPIP bit 4 stays low, so RDRF / the GPIP bit / the pending interrupt must
    ///all track this FIFO or the ISR spins or drops bytes. This models only the ACIA end; there
    ///is no emulated 6301 IKBD MCU, so nothing here synthesises the power-on $F1 reset reply
    ///(TOS doesn't block waiting for it - the diskless boot already reaches the desktop without
    ///one). Callers inject real make/break scancodes and 3-byte mouse packets via EnqueueIkbd.
    let ikbdRxFifo = System.Collections.Generic.Queue<byte>()
    let mutable kbdAciaControl = 0uy //last value written to $FFFC00; bit 7 = RX interrupt enable

    ///Status byte the CPU reads at $FFFC00. TDRE (bit 1) is always set - nothing holds the
    ///transmitter here. RDRF (bit 0) tracks the FIFO. IRQ (bit 7) = RDRF AND RX-interrupt-enabled,
    ///matching the real 6850's IRQ output, and is what GPIP bit 4 and the ISR's `btst #7` test.
    let keyboardAciaStatus () =
        let mutable sr = 0x02uy
        if ikbdRxFifo.Count > 0 then
            sr <- sr ||| 0x01uy
            if kbdAciaControl &&& 0x80uy <> 0uy then sr <- sr ||| 0x80uy
        sr

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

    ///Real disk image mounted in drive A, if any - see LoadDiskA (set from Program.fs's
    ///ATARI_DISK_A env var, mirroring ATARI_ROM_PATH). `None` (the default) preserves every
    ///existing "no disk" behavior documented on fdcCommandStatus/tryReadSector below - this is
    ///purely additive. Real hardware selects side 0/1 via a PSG port A bit (Hatari's
    ///FDC_SetDriveSide, src/fdc.c) that this emulator's YM2149 handling doesn't model with real
    ///register-select semantics yet, so only single-sided images are supported for now (confirmed
    ///a valid single-sided image is sufficient to exercise real GEMDOS boot-time sector reads via
    ///a live Hatari trace - see [[atari-st-emulator-next-instructions]]).
    let mutable diskA : byte[] option = None
    let mutable diskASectorsPerTrack = 9

    ///Real hardware resets this to 0 on cold boot (stMemory.c: "0xFF8001 is set to 0 on cold reset
    ///but keep its value on warm reset") - this emulator only ever cold-boots, so 0 is always the
    ///right starting value, matching real hardware rather than the project's actual installed RAM.
    let mutable memConfigByte = 0uy

    ///Monitor type reported through MFP GPIP bit 7 ($FFFFFA01). `true` = colour monitor (bit 7
    ///set), `false` = monochrome (bit 7 clear). The boot ROM at $fc0366 does
    ///`move.b $fffffa01.l,D0 / bmi $fc0386`: bit 7 set keeps the power-on rez, bit 7 clear falls
    ///through to $fc0376 which forces rez 2 (640x400 mono). Real hardware drives this line purely
    ///from which monitor is physically plugged in; nothing ever writes GPIP, so it can't be
    ///storage-backed - the ReadByte GPIP case synthesises it. Set from Program.fs's ATARI_MONITOR
    ///env var (default colour), mirroring LoadDiskA. Hatari also defaults to colour here.
    let mutable colourMonitor = true

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

    ///Real STF hardware's MMU decodes RAM addresses using the *configured* bank sizes from
    ///`memConfigByte` ($FF8001), not a flat modulus - each bank's CAS/RAS address lines are reused
    ///differently depending on whether the MMU is told the bank is 128KB/512KB/2048KB, so a bank
    ///that's physically smaller than configured genuinely shows address-line aliasing at its real
    ///boundary. That aliasing is exactly the signal TOS's own cold-boot RAM-sizing probe depends on
    ///to discover the real installed size - the previous flat `address &&& ramMask` scheme masked
    ///identically regardless of `memConfigByte`, so that probe could never observe a real mismatch
    ///and TOS ended up believing whatever the largest candidate it tried ($0A = 2048KB+2048KB) was
    ///correct - see [[atari-st-emulator-next-instructions]]'s twenty-third pass.
    ///Ported directly from Hatari's `STMemory_MMU_Translate_Addr`/`_STF` (github.com/hatari/hatari,
    ///src/stMemory.c) - this project only ever has 512KB physical RAM per bank (`ram.Length` = 1MB
    ///total), so only the "RAM bank = 512KB" row of Hatari's full 128/512/2048-by-128/512/2048
    ///table is ported; the other two physical-size rows don't apply to any RAM size this project
    ///models.
    let ramBankPhysicalSize = uint32 (ram.Length / 2)

    let mmuBankSizeBytes (code: int) =
        match code with
        | 0 -> 0x20000u  //128KB
        | 1 -> 0x80000u  //512KB
        | _ -> 0x200000u //2048KB ($FF8001 code 2; code 3/"11" is real hardware's documented-reserved value, never written by this ROM, folded in here rather than left as a dead branch

    ///STF address-line remapping for one bank, given the bank's real physical size (always 512KB
    ///in this project) and the size the MMU is currently configured to believe it is.
    let stfTranslateWithinBank (addrInBank: uint32) (mmuBankSize: uint32) =
        let remapped =
            if mmuBankSize = 0x200000u then //MMU thinks 2048KB, bank is really 512KB: C9/R9 don't exist
                ((addrInBank &&& 0xff800u) >>> 1) ||| (addrInBank &&& 0x3ffu)
            elif mmuBankSize = 0x80000u then //MMU config matches the real 512KB bank exactly
                addrInBank
            else //MMU thinks 128KB, bank is really 512KB: C8/R8 get folded back in too
                ((addrInBank &&& 0x3fe00u) <<< 1) ||| (addrInBank &&& 0x3ffu)
        remapped &&& (ramBankPhysicalSize - 1u)

    ///Full bank0/bank1 routing, mirroring Hatari's `STMemory_MMU_Translate_Addr` wrapper: which
    ///bank an address falls in depends on the *configured* (not physical) bank sizes, but where
    ///that bank actually starts inside the real `ram` array depends on the *physical* size instead.
    ///Returns `None` for addresses beyond the MMU's configured total - genuinely open bus, no
    ///device backs them - rather than the old flat mirror.
    ///
    ///Traced (twenty-third pass) exactly how TOS's own cold-boot phystop probe works, and it's
    ///simpler than first guessed: `$fc0166`-`$fc0186` writes a 43-word evolving pattern at the
    ///current candidate top-of-RAM address, then immediately reads it back and compares - a plain,
    ///in-band software self-consistency check, NOT a CPU-level Bus Error trap (the vector-2 handler
    ///it installs a few instructions earlier is for something else; this loop never faults on real
    ///hardware, it just needs writes to genuinely open bus to not read back what was written). It
    ///climbs in fixed $20000 steps, so the first block that actually probes past a real 1MB machine
    ///starts at `$120000` (`$100000+$20000`) - well below the `$1E0100`-ish region the raw
    ///reset-vector SSP still uses as scratch stack at this point in boot (confirmed via a fresh
    ///trace: no instruction writes `A7` anywhere in the first 200,000 steps), so making this
    ///specific range open-bus doesn't collide with that stack use, unlike the earlier same-pass
    ///attempt that raised a real `BusError` here (which regressed cold boot - see
    ///[[atari-st-emulator-next-instructions]] - because the CPU's OWN exception-frame push for that
    ///fault used the same not-yet-relocated stack, a genuine fault-during-fault-handling case this
    ///emulator doesn't model). No exception needed this time: open-bus reads just return a fixed
    ///value that can never match an evolving write pattern, and open-bus writes are no-ops.
    let translateRamAddress (address: uint32) =
        let conf = int memConfigByte
        let bank0Mmu = mmuBankSizeBytes ((conf >>> 2) &&& 3)
        let bank1Mmu = mmuBankSizeBytes (conf &&& 3)
        if address < bank0Mmu then
            Some (stfTranslateWithinBank address bank0Mmu)
        elif address < bank0Mmu + bank1Mmu then
            Some (ramBankPhysicalSize + stfTranslateWithinBank (address - bank0Mmu) bank1Mmu)
        else
            None

    ///Copies a real 512-byte sector from the mounted disk-A image into RAM at `dmaAddr` (the DMA
    ///Address Counter's current value), if a disk is loaded and (track,sector) is a valid location
    ///on it (`sector` is the WD1772's real 1-based sector number). Returns whether the copy
    ///happened, so the caller can choose the FDC status byte accordingly - success, or fall back to
    ///the existing Record Not Found stub for anything a real drive couldn't find either (no disk,
    ///or a request past the image's own geometry). Writes go straight through translateRamAddress
    ///rather than the full WriteByte dispatch, matching WriteByte's own "aliasIntoRam" fallback -
    ///real DMA transfers only ever target RAM, never memory-mapped I/O.
    let tryReadSector (track: byte) (sector: byte) (dmaAddr: uint32) =
        match diskA with
        | None -> false
        | Some bytes ->
            let s = int sector
            if s < 1 || s > diskASectorsPerTrack then false
            else
                let offset = (int track * diskASectorsPerTrack + (s - 1)) * 512
                if offset < 0 || offset + 512 > bytes.Length then false
                else
                    for i in 0 .. 511 do
                        match translateRamAddress (dmaAddr + uint32 i) with
                        | Some idx -> store ram (int idx) bytes.[offset + i]
                        | None -> ()
                    true

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
        | a when a = 0xFFFA01u ->
            //MFP GPIP - eight read-only hardware input lines, not a writable register. Two bits
            //matter to boot and are synthesised here rather than read from stored zeros:
            //  bit 7 = monochrome-monitor-detect, INVERTED: 1 = colour monitor attached, 0 = mono
            //          (ROM $fc036c `bmi` forces rez 2 when this is clear). Driven by `colourMonitor`.
            //  bit 4 = keyboard/MIDI ACIA interrupt request, active-LOW: 0 = an ACIA IRQ is
            //          pending, 1 = none. Driven from keyboardAciaStatus; TOS's ISR at $fc281c
            //          loops (`btst #4 / beq`) while this bit is 0, servicing the ACIA until drained.
            //Every other GPIP bit (0 centronics busy, 1 RS232 DCD, 2 RS232 CTS, 3 blitter done,
            //5 FDC/HDC IRQ, 6 RS232 ring) still comes from stored mfpRegisters unchanged.
            let stored = mfpRegisters.[int (address - mpf68901)]
            let stored = if colourMonitor then stored ||| 0x80uy else stored &&& 0x7Fuy
            if keyboardAciaStatus() &&& 0x80uy <> 0uy then stored &&& 0xEFuy else stored ||| 0x10uy
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
        | a when a = memConfig -> memConfigByte
        | a when a = 0xFFFC00u -> keyboardAciaStatus () //keyboard ACIA control/status
        | a when a = 0xFFFC02u -> //keyboard ACIA receive data - pop one byte from the IKBD FIFO
            if ikbdRxFifo.Count > 0 then
                let b = ikbdRxFifo.Dequeue()
                mutations <- mutations + 1UL
                b
            else 0uy
        | Acia ->
            //MIDI ACIA (and any other address in range) - see ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> v
            | None -> 0uy
        | _ ->
            if aliasIntoRam address then
                match translateRamAddress address with
                | Some idx -> ram.[int idx]
                | None -> 0uy //open bus, no device backs this address
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
        | a when a = 0xFFFC00u || a = 0xFFFC02u ->
            //Keyboard ACIA - an 8-bit device on the upper data-bus byte (even address). TOS only
            //ever byte-accesses it; a word read still needs to not bus-error, so put the register
            //in the high byte with the unmapped low byte reading as 1s.
            (int (x.ReadByte address) <<< 8) ||| 0xFF
        | Acia ->
            //MIDI ACIA / rest of range - see ioStubs above.
            match ioStubs.TryFind address with
            | Some v -> int v
            | None -> 0
        | a ->
            if aliasIntoRam a then
                let byteAt addr = match translateRamAddress addr with Some idx -> ram.[int idx] | None -> 0uy
                ((int (byteAt a)) <<< 8) ||| (int (byteAt (a+1u)))
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
                let storeAt addr v = match translateRamAddress addr with Some idx -> store ram (int idx) v | None -> ()
                storeAt address (byte (input >>> 8))
                storeAt (address+1u) (byte (input &&& 0xffs))
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
                //Type II Read Sector: top 3 bits "100", bottom 2 bits "00" (FD-HD_Programming.pdf's
                //FDC Command Summary table - the m/h/e flag bits 4/3/2 don't affect this
                //classification). With a disk image mounted, copy the real requested sector
                //straight into RAM at the already-programmed DMA address counter (real boot-ROM
                //sequences always set Track/Sector/DMA-address before issuing the command - FD-HD
                //Programming.pdf's own DMA programming tips) and report success, instead of the
                //always-Record-Not-Found stub every other command still uses. This project has no
                //command timing or real WD1772 seek/settle modeling, so - matching every other FDC
                //command here - the whole operation completes synchronously on this one write.
                let isReadSector = (input &&& 0xE3uy) = 0x80uy
                let dmaAddr =
                    (uint32 dmaAddrHighByte <<< 16) ||| (uint32 dmaAddrMidByte <<< 8) ||| uint32 dmaAddrLowByte
                let status =
                    if isReadSector && tryReadSector fdcTrack fdcSector dmaAddr then 0uy
                    else fdcCommandStatus input
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
        | a when a = memConfig ->
            if input <> memConfigByte then mutations <- mutations + 1UL
            memConfigByte <- input
        | a when a = 0xFFFC00u ->
            //Keyboard ACIA control register. Bits 1-0 = 11 is a master reset (flush the receiver);
            //bit 7 is the RX interrupt enable that keyboardAciaStatus / GPIP bit 4 depend on. TOS
            //writes $03 (reset) then $96 (÷64, 8N1, RX interrupt on) at boot. The transmit side is
            //still a no-op - nothing here consumes bytes TOS sends to the IKBD.
            if input &&& 0x03uy = 0x03uy then ikbdRxFifo.Clear()
            if input <> kbdAciaControl then mutations <- mutations + 1UL
            kbdAciaControl <- input
        | Acia ->
            //MIDI ACIA control / transmit, keyboard ACIA transmit ($FFFC02) - no-ops, see
            //WriteWord's matching case just above.
            ()
        | _ ->
            if aliasIntoRam address then
                match translateRamAddress address with
                | Some idx -> store ram (int idx) input
                | None -> () //open bus, no device backs this address
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

    ///Mounts (or unmounts, on `None`) a real disk image in drive A - see `diskA`'s own comment
    ///above for the single-sided-only caveat. Reads the image's own boot-sector BPB for its real
    ///sectors-per-track (offset 24-25, little-endian - Hatari's src/floppy.c
    ///Floppy_FindDiskDetails and src/createBlankImage.c both use this exact offset), falling back
    ///to the standard 9 if the image is too short or the field looks invalid, rather than trusting
    ///arbitrary image content. Deliberately NOT part of MmuSnapshot/SaveState - like `rom` itself,
    ///which disk is in a drive is external, physical-world state, not something a state save
    ///should capture or a state load should disturb.
    member x.LoadDiskA (data: byte[] option) =
        diskA <- data
        diskASectorsPerTrack <-
            match data with
            | Some bytes when bytes.Length >= 26 ->
                let spt = int bytes.[24] ||| (int bytes.[25] <<< 8)
                if spt >= 1 && spt <= 48 then spt else 9
            | _ -> 9

    ///Selects the monitor type reported through MFP GPIP bit 7 - see `colourMonitor`. `true` =
    ///colour (the default and Hatari's default), `false` = monochrome. Like LoadDiskA this is
    ///external physical-world state, deliberately not part of MmuSnapshot.
    member x.SetMonitor (isColour: bool) = colourMonitor <- isColour

    ///Asserts an interrupt line - see the `vblPending`/`mfpPending` comment. Level 4 = VBL,
    ///level 6 = MFP (the `vector` is the MFP channel's own vector number, e.g. $46 for the
    ///keyboard ACIA on channel 6); any other level is ignored, as no other source exists.
    member x.RaiseInterrupt (level: int) (vector: int) =
        match level with
        | 4 ->
            if not vblPending then
                vblPending <- true
                mutations <- mutations + 1UL
        | 6 ->
            if not mfpPending || mfpVector <> vector then
                mfpPending <- true
                mfpVector <- vector
                mutations <- mutations + 1UL
        | _ -> () //no other interrupt source on this hardware
    member x.PendingInterruptLevel = if mfpPending then 6 elif vblPending then 4 else 0
    member x.PendingInterruptVector = if mfpPending then mfpVector elif vblPending then 28 else 0
    ///Called by `Cpu.Step()` once it has decided to actually take the pending interrupt (i.e. it
    ///cleared the current IPL mask) - clears only the slot being taken (the higher one), so a
    ///lower still-pending source stays pending, matching real interrupt-acknowledge behaviour.
    member x.AcknowledgeInterrupt() =
        if mfpPending then mfpPending <- false
        elif vblPending then vblPending <- false
        mutations <- mutations + 1UL

    ///Injects raw IKBD serial bytes into the keyboard ACIA receive FIFO - real make/break
    ///scancodes (make = scancode, break = scancode ||| $80) and 3-byte relative mouse packets
    ///(header $F8-$FB, then signed dx, dy). See `ikbdRxFifo`. Raises the MFP channel-6 interrupt
    ///(IPL 6, vector $46) so TOS's ACIA ISR runs and drains what was queued. Used by the REPL
    ///`kbd` command and, later, the live window's real keyboard/mouse handler.
    member x.EnqueueIkbd (bytes: byte seq) =
        let mutable added = false
        for b in bytes do
            ikbdRxFifo.Enqueue b
            added <- true
        if added then
            mutations <- mutations + 1UL
            x.RaiseInterrupt 6 0x46

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
          DmaAddrHigh = dmaAddrHighByte; DmaAddrMid = dmaAddrMidByte; DmaAddrLow = dmaAddrLowByte
          MemConfig = memConfigByte
          KbdAciaControl = kbdAciaControl; IkbdRxFifo = ikbdRxFifo.ToArray() }

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
        memConfigByte <- snapshot.MemConfig
        kbdAciaControl <- snapshot.KbdAciaControl
        ikbdRxFifo.Clear()
        for b in snapshot.IkbdRxFifo do ikbdRxFifo.Enqueue b
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
                let byteAt addr = match translateRamAddress addr with Some idx -> ram.[int idx] | None -> 0uy
                (int (byteAt address)      <<< 24) |||
                (int (byteAt (address+1u)) <<< 16) |||
                (int (byteAt (address+2u)) <<<  8) |||
                (int (byteAt (address+3u)))
            else raise (BusError address)
