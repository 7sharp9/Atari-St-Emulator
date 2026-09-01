namespace Atari
open Bits

///Everything SnapshotRam/RestoreRam need to roll back a speculative run exactly - previously just
///the three byte arrays, which silently missed the MFP's register bank and Timer B's scalar state
///(tbcr/tbdr/tbdrReload/tbdrReadCount). A Preview that touched the MFP would permanently corrupt
///the real run's timer state on "rollback", contradicting Preview's own "state restored" claim.
type MmuSnapshot =
    { Ram: byte[]; VideoDisplayRegisters: byte[]; Ym2149: byte[]; MfpRegisters: byte[]
      PsgSelectedReg: byte; PsgReadData: byte
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

/// `flatTestBus` (default false) turns the MMU into a plain big-endian 24-bit RAM (sparse -
/// unwritten addresses read 0) with no I/O regions, no ROM, no address aliasing and no bus errors
/// - ONLY for the `selftest` harness, whose 680x0 ProcessorTests vectors place operands anywhere
/// in the 24-bit space and test pure CPU semantics, not the ST memory map. Address errors (odd
/// word/long access) are still raised, since the vectors do test those. Sparse (a Dictionary, not
/// a 16 MB array) so a fresh MMU per case is cheap and GC-friendly under `Array.Parallel`.
/// Nothing in the real emulator passes this flag.
type MMU(rom: byte array, ?flatTestBus: bool) =

    let flatBus = defaultArg flatTestBus false
    let flatMem = System.Collections.Generic.Dictionary<uint32, byte>()
    let flatGet (a: uint32) = match flatMem.TryGetValue a with | true, v -> v | _ -> 0uy

    ///`ATARI_TRACE_FDC=1` logs every FDC register/command write and every sector-read attempt to
    ///stderr (so it survives ATARI_NOTRACE), the way `ATARI_TRACE_GEMDOS` does for GEMDOS traps -
    ///the tool for watching the disk-load path against a Hatari `--trace fdc` ground truth.
    let traceFdc = not (isNull (System.Environment.GetEnvironmentVariable "ATARI_TRACE_FDC"))
    let fdcLog (s: string) = if traceFdc then eprintfn "FDC %s" s

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

    ///YM2149 PSG. Real chip: a write to $FF8800 selects one of the 16 registers, a write to
    ///$FF8802 sets the selected register's value, and a read of $FF8800 returns the last value
    ///latched into the read port (the selected register's contents at select time, or a data
    ///write's raw value - mirrors Hatari's `PSGRegisterReadData`, src/psg.c). The address vs data
    ///port is picked by address bit 1 ($FF8800 = select, $FF8802 = data); the chip sits on the
    ///upper data-bus byte so only even-address byte accesses are real. Previously modelled as a
    ///raw 4-byte array indexed by `address - $FF8800`, so a read of $FF8800 returned the last
    ///*register number* written, not the register's contents - which broke TOS's `giaccess`
    ///read-modify-write of port A ($fc1c60: `move.b #$e,$ff8800; move.b $ff8800,D1; and.b #$f8,D1;
    ///or.b D0,D1; move.b D1,$ff8802`) for bits 3-7. Only register 14 (I/O port A) matters past
    ///sound: bit 0 = floppy side-select (side = ~portA & 1, per hatari FDC_SetDriveSide), bits 1-2
    ///= drive-select, active low (bit 1 clear = drive 0, else bit 2 clear = drive 1, else none).
    let psgRegs = Array.create 16 0uy
    let mutable psgSelectedReg = 0uy       //0..15 selects a register; >=16 is invalid (reads 0xFF)
    let mutable psgReadData = 0xFFuy       //value returned by a read of $FF8800
    let mutable fdcSide = 0                //PSG port-A bit 0: floppy head side 0 or 1
    let mutable fdcDrive = -1              //PSG port-A bits 1-2: selected drive (0, 1, or -1 = none)
    ///Recompute the derived side/drive-select signals from PSG register 14 (I/O port A).
    let updateDriveSide () =
        let portA = psgRegs.[14]
        fdcSide <- int ((~~~portA) &&& 1uy)
        fdcDrive <-
            if portA &&& 0x02uy = 0uy then 0
            elif portA &&& 0x04uy = 0uy then 1
            else -1
    do psgRegs.[14] <- 0xFFuy; updateDriveSide ()   //cold-reset port A: no drive selected, side 0
    let ym2149Start = 0xFF8800u
    //Only bits 0-1 of $FF88xx reach the YM2149, so $FF8804-$FF88FF mirror $FF8800-$FF8803
    //(Hatari psg.c, same note). Bit 1 selects address-register ($FF8800) vs data ($FF8802);
    //bit 0 is the shadow. Games use this: Super Hang-On's music ISR does `movep.l Dn,$ff8800`
    //to poke $8800/$8802/$8804/$8806 = select/data/select/data in one instruction. Without the
    //mirror the $8806 access bus-errored and the ISR looped on vector 2 forever.
    let ym2149End =  0xFF88FFu

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
    ///See `InterruptAcks` - count of interrupts actually taken, for the loop detector.
    let mutable interruptAcks = 0UL

    ///Write to a PSG port. `sel` picks the address ($FF8800) vs data ($FF8802) register. See the
    ///psgRegs comment above.
    let psgWrite (sel: bool) (input: byte) =
        if sel then
            if psgSelectedReg <> input then mutations <- mutations + 1UL
            psgSelectedReg <- input
            psgReadData <- if input < 16uy then psgRegs.[int input] else 0xFFuy
        elif psgSelectedReg < 16uy then
            let reg = int psgSelectedReg
            let masked =
                match reg with
                | 1 | 3 | 5 | 13 -> input &&& 0x0Fuy       //channel A/B/C coarse tune, envelope shape
                | 6 | 8 | 9 | 10 -> input &&& 0x1Fuy       //noise period, channel A/B/C amplitude
                | _ -> input
            if psgRegs.[reg] <> masked || psgReadData <> input then mutations <- mutations + 1UL
            psgRegs.[reg] <- masked
            psgReadData <- input                            //raw value, like hatari's PSGRegisterReadData
            if reg = 14 then updateDriveSide ()

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
    ///Three independent pending-interrupt slots, replacing the earlier single "highest level
    ///asserted" scalar (per that comment's own TODO). Real hardware holds a pending bit per
    ///source with priority arbitration; the sources that exist here are the VBL (autovectored
    ///level 4, vector 28), the keyboard ACIA (MFP channel 6, level 6, vector $46) and MFP Timer C
    ///(channel 5, level 6, vector $45 -> the 200Hz system tick that drives etv_timer and, through
    ///it, the AES's double-click / click-release timeout countdown). A separate slot each is
    ///needed so a periodic tick never silently displaces a still-pending keystroke: when both MFP
    ///channels are asserted the ACIA (higher channel number) is taken first, matching the 68901's
    ///own priority order. `PendingInterruptLevel`/`Vector` report the highest asserted;
    ///`AcknowledgeInterrupt` clears only that one.
    let mutable vblPending = false
    let mutable mfpPending = false
    let mutable mfpVector = 0
    let mutable timerCPending = false
    let mutable timerBPending = false
    let mutable timerAPending = false

    let mutable watchRange : (uint32 * uint32) option = None
    ///PC of the instruction currently executing, pushed in from Program.fs's Step() before each
    ///cpu.Step(). Only used to annotate WATCH lines with the offending instruction address - the
    ///MMU has no other need to know the PC, so this stays a plain debug aid.
    let mutable watchPc = 0
    let mutable watchStep = 0UL
    let checkWatch (address: uint32) (label: string) (value: uint32) =
        match watchRange with
        | Some(lo, hi) when address >= lo && address <= hi ->
            eprintfn "WATCH: step=%d pc=$%06x %s $%08x <- $%x" watchStep watchPc label address value
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
    ///Live down-counter for MFP Timer B in EVENT-COUNT mode ($08), advanced one tick per emulated
    ///scanline by HblTick - the HBLANK clock source the coarse read-driven `tbdr`/`tbdrReadCount`
    ///pair (kept for the ROM's MFP-presence check) can't model. 0 = "not seeded yet"; the first
    ///HblTick after Timer B is armed loads it from `tbdrReload`, and each underflow reloads and
    ///raises the Timer B interrupt. Deliberately NOT in MmuSnapshot: TOS never arms event-count
    ///Timer B so it stays 0 on the diskless path (keeps that snapshot byte-identical), and a
    ///mid-split resume losing one scanline of counter phase is immaterial.
    let mutable tbCounter = 0

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

    ///The DMA status register read at $FF8606 (write = DMA mode/control - see fdcModeSelect). Only
    ///the low 3 bits are real (hatari src/fdc.c FDC_DmaStatus_ReadWord): bit 0 = 1 when the last
    ///DMA transfer had no error (real reset value is 1 = "no error"), bit 1 = 1 when the DMA
    ///sector-count register is non-zero, bit 2 = FDC DRQ (always 0 on the ST, the 16-byte DMA FIFO
    ///hides it). Previously $FF8606 read echoed the mode-select bits (`fdcSelectedReg <<< 1`), so
    ///bit 0 was always 0 - which TOS's floppy read completion check at $fc1628 (`move.w $ff8606,D0
    //// btst #0,D0 / beq retry`) reads as a permanent DMA error, retrying every sector read ~25
    ///times then giving up. That is the real cause of the "this disk may be damaged" alert on any
    ///disk access past the boot sector.
    let mutable dmaNoError = true

    ///WD1772 INTRQ, seen by the CPU as MFP GPIP bit 5 (active-LOW: line low = interrupt asserted).
    ///Real hardware pulses INTRQ when a command finishes; it is cleared by reading the status
    ///register or writing a new command. TOS polls `btst #5,$fffffa01` in two very different ways:
    ///  - the boot-time FDC self-test at ROM $fc04a8 (via $fc04d6) polls with a ~10-tick `_hz_200`
    ///    deadline (~30000 steps here) and EXPECTS the commands to still be running when it expires,
    ///    so it can prove the FDC is merely present without a formatted disk;
    ///  - the real GEMDOS read/write paths ($fc15e6 / $fc16d4 / $fc1be2) poll a bare `$40000`+
    ///    software loop, which on real hardware easily outlasts a real command.
    ///Before the 63rd pass GPIP bit 5 was hardwired 0 ("INTRQ always pending"): the self-test's
    ///polls returned success instantly, its `jsr (A0)` re-ran the boot sector, and a crack whose
    ///boot sector checksums to $1234 (PowerMonger `[cr Replicants]`) looped forever. Now INTRQ is
    ///idle-high and re-raises on a coarse delay after a command (FdcTick counts it down). This
    ///emulator has no per-command WD1772 state machine (Hatari's src/fdc.c does; that is the
    ///re-architecture this project has not built), so the delay is bucketed by command:
    ///  - a Read/Write Sector that actually moved data: INTRQ immediately - the bytes are already
    ///    in RAM, and a real WD1772 asserts INTRQ the moment the DMA transfer ends. Keeps disk
    ///    loading fast (a per-sector delay here would make a 200 KB file take tens of millions of
    ///    extra steps).
    ///  - a Seek / Step (Type I $1x-$7x): `fdcIrqFastSteps` - a real adjacent-track seek is a few
    ///    ms, well inside the self-test deadline, and the real read path does one before most
    ///    sector reads so this must stay cheap.
    ///  - anything else - Restore (Type I $0x), a sector command that found nothing, Read Address/
    ///    Track: `fdcIrqSlowSteps`. `$fc04d6` issues a hardcoded Restore ($01) as its first command
    ///    every self-test iteration (the following `move.l D0,(A5)` lands in the DMA sector-count
    ///    register, not the command register - `$fc0518` set `$8606` bit 4 first), so that Restore's
    ///    slow bucket is what times the self-test out every iteration. Verified: `$fc04cc` (the
    ///    boot-sector re-exec) is reached 0 times, the loop exits at `$fc04d4`.
    ///Not in MmuSnapshot: a settled machine read its status register (INTRQ cleared) long ago, like
    ///Timer B's tbCounter.
    let mutable fdcIrq = false            //true = INTRQ asserted = GPIP bit 5 reads 0
    let mutable fdcIrqPending = 0         //steps until INTRQ asserts; 0 = not counting
    //The slow bucket must exceed the self-test's per-poll deadline (`_hz_200`+10 ticks, ~30000
    //steps at the fixed timerCPeriod=3000) and stay well under the GEMDOS sector poll's
    //`$40000`-iteration budget (~1.5M steps). 120000 is ~4x the deadline and ~1/12 the budget -
    //wide enough that a slower Timer C ISR path can't close the gap, cheap enough that the two
    //Restores a real disk load issues cost ~0.24M steps total.
    let fdcIrqSlowSteps = 120000
    let fdcIrqFastSteps = 4000            //a real adjacent-track seek, well inside the self-test deadline

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

    ///The DMA sector-count register. On real hardware $FF8606 bit 4 (`$x90` vs `$x80`) switches the
    ///$FF8604 access between "an FDC/HDC register" and "the DMA sector-count register"; the boot ROM
    ///and GEMDOS write the count here (verified against a live Hatari `--trace fdc` run - see
    ///[[atari-st-emulator-reversing-goal]]) before every Read/Write Sector command, then the WD1772
    ///transfers that many consecutive sectors when the command's multi-record (`m`) bit is set.
    ///Not in MmuSnapshot: it is re-written before every command, so a resumed snapshot re-derives it.
    ///`dmaScSelected` tracks the last $FF8606 bit-4 state so the next $FF8604 write is routed right.
    let mutable dmaSectorCount = 0uy
    let mutable dmaScSelected = false

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
    let mutable diskASides = 1

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

    let ram = Array.create 0x100000 0uy

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
        let r =
            match diskA with
            | None -> false
            | Some _ when fdcDrive <> 0 -> false     //only drive A is backed by an image
            | Some _ when fdcSide >= diskASides -> false
            | Some bytes ->
                let s = int sector
                if s < 1 || s > diskASectorsPerTrack then false
                else
                    //Interleave the two sides for a double-sided image: track 0 side 0, track 0
                    //side 1, track 1 side 0, ... - the standard .ST layout (hatari src/floppy.c).
                    let logicalSector = (int track * diskASides + fdcSide) * diskASectorsPerTrack + (s - 1)
                    let offset = logicalSector * 512
                    if offset < 0 || offset + 512 > bytes.Length then false
                    else
                        for i in 0 .. 511 do
                            match translateRamAddress (dmaAddr + uint32 i) with
                            | Some idx -> store ram (int idx) bytes.[offset + i]
                            | None -> ()
                        true
        fdcLog (sprintf "read  drive=%d track=%d side=%d sector=%d dma=$%06x -> %s"
                    fdcDrive (int track) fdcSide (int sector) dmaAddr (if r then "OK" else "no data"))
        r

    ///Symmetric to tryReadSector: copies a real 512-byte sector *out* of RAM (at the DMA Address
    ///Counter's current value) *into* the mounted disk-A image - the RAM->media direction of a
    ///WD1772 Write Sector ($Ax) command. Same geometry (1-based sector, .ST side interleave) and
    ///the same synchronous FAT12-only model as the read path; mirrors Hatari's
    ///FDC_WriteSector_ST -> Floppy_WriteSectors (src/fdc.c).
    ///
    ///Deliberately in-memory only: it mutates the `diskA` byte array (so a read-back later in the
    ///same run sees the write), but nothing ever writes the host .ST file. That keeps every run
    ///deterministic - a run can't silently rewrite its own input - and keeps the committed
    ///reversing/*/*.st CFG artefacts byte-stable. GEMDOS test programs (Dcreate/Fwrite/Fseek/...)
    ///and control-flow reconstruction only need within-run persistence, which this gives. A
    ///persistent write-through to the host file would be a separate, explicit feature.
    let tryWriteSector (track: byte) (sector: byte) (dmaAddr: uint32) =
        let r =
            match diskA with
            | None -> false
            | Some _ when fdcDrive <> 0 -> false     //only drive A is backed by an image
            | Some _ when fdcSide >= diskASides -> false
            | Some bytes ->
                let s = int sector
                if s < 1 || s > diskASectorsPerTrack then false
                else
                    let logicalSector = (int track * diskASides + fdcSide) * diskASectorsPerTrack + (s - 1)
                    let offset = logicalSector * 512
                    if offset < 0 || offset + 512 > bytes.Length then false
                    else
                        for i in 0 .. 511 do
                            match translateRamAddress (dmaAddr + uint32 i) with
                            | Some idx -> bytes.[offset + i] <- ram.[int idx]
                            | None -> ()
                        true
        fdcLog (sprintf "write drive=%d track=%d side=%d sector=%d dma=$%06x -> %s"
                    fdcDrive (int track) fdcSide (int sector) dmaAddr (if r then "OK" else "no data"))
        r

    member x.ReadByte (address: uint32) =
        let address = address &&& maxMemory
        if flatBus then flatGet address else
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
            //Both the address port ($FF8800) and the data port ($FF8802) read back the last
            //latched read-data value - see the psgRegs comment. (Real hardware only truly drives
            //data on a read of $FF8800; $FF8802 reads are undefined. TOS only ever reads $FF8800.)
            psgReadData
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
            //  bit 5 = FDC/HDC interrupt request, active-LOW: 0 = INTRQ asserted (command done),
            //          1 = idle. Driven by `fdcIrq` - see its comment. HDC is not modelled.
            //Every other GPIP bit (0 centronics busy, 1 RS232 DCD, 2 RS232 CTS, 3 blitter done,
            //6 RS232 ring) still comes from stored mfpRegisters unchanged.
            let stored = mfpRegisters.[int (address - mpf68901)]
            let stored = if colourMonitor then stored ||| 0x80uy else stored &&& 0x7Fuy
            let stored = if fdcIrq then stored &&& 0xDFuy else stored ||| 0x20uy
            if keyboardAciaStatus() &&& 0x80uy <> 0uy then stored &&& 0xEFuy else stored ||| 0x10uy
        | Mfp -> mfpRegisters.[int (address - mpf68901)]
        | a when a = fdcAccess ->
            match fdcSelectedReg with
            | 0uy ->
                //Reading the WD1772 status register clears INTRQ (GPIP bit 5 back to idle-high),
                //exactly like issuing a new command - see fdcIrq. A pending assertion is cancelled.
                if fdcIrq || fdcIrqPending <> 0 then
                    fdcIrq <- false
                    fdcIrqPending <- 0
                    mutations <- mutations + 1UL
                fdcStatus
            | 1uy -> fdcTrack
            | 2uy -> fdcSector
            | _ -> fdcData
        | a when a = fdcModeSelect ->
            //DMA status: bit 0 = no DMA error, bit 1 = DMA sector count non-zero, bit 2 = DRQ
            //(always 0 on the ST). See dmaNoError.
            (if dmaNoError then 0x01uy else 0uy) ||| (if dmaSectorCount <> 0uy then 0x02uy else 0uy)
        | a when a = dmaAddrHigh -> dmaAddrHighByte
        | a when a = dmaAddrMid -> dmaAddrMidByte
        | a when a = dmaAddrLow -> dmaAddrLowByte
        | a when a = memConfig -> memConfigByte
        | a when a = 0xFFFC00u -> keyboardAciaStatus () //keyboard ACIA control/status
        | a when a = 0xFFFC02u -> //keyboard ACIA receive data - pop one byte from the IKBD FIFO
            if ikbdRxFifo.Count > 0 then
                let b = ikbdRxFifo.Dequeue()
                mutations <- mutations + 1UL
                //The 6850 keeps its IRQ line asserted while RDRF stays set. On real hardware IKBD
                //bytes arrive ~1.28 ms apart so each is its own MFP channel-6 edge; EnqueueIkbd
                //instead delivers a whole packet at once. Re-raise the interrupt while bytes
                //remain so a handler that reads exactly one byte per interrupt - Super Sprint's own
                //IKBD ISR at $104b6, which does not loop like TOS's - still sees every byte of a
                //multi-byte packet ($FE/$FF + joystick state, 3-byte mouse packets). The final
                //byte leaves the FIFO empty, so at most one extra interrupt follows a burst and it
                //hits the handler's "no data" guard.
                if ikbdRxFifo.Count > 0 && kbdAciaControl &&& 0x80uy <> 0uy then
                    x.RaiseInterrupt 6 0x46
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
        if flatBus then (int (flatGet address) <<< 8) ||| int (flatGet ((address + 1u) &&& maxMemory)) else
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
            //Byte-wide device on the upper data-bus byte - compose from ReadByte, register in the
            //high half. TOS only ever byte-accesses the PSG.
            (int (x.ReadByte address) <<< 8) ||| int (x.ReadByte (address+1u))
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
        if flatBus then
            flatMem.[address] <- byte (int input >>> 8)
            flatMem.[(address + 1u) &&& maxMemory] <- byte input
        else
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> () //real ROM chips can't be written; ignored rather than a bus error
        | Cart -> () //no cartridge present; writes go nowhere, matching the read side's fixed $ff(ff) stub
        | VideoDisplayRegister ->
            let i = int (address - videoDisplayRegisterStart)
            store videoDisplayRegisterMemory i (byte (input >>> 8))
            store videoDisplayRegisterMemory (i+1) (byte (input &&& 0xffs))
        | YM2149 ->
            //Byte-wide device on the upper data-bus byte - only the high byte reaches the chip.
            x.WriteByte address (byte (input >>> 8))
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
        if flatBus then flatMem.[address] <- input else
        match address with
        | a when a < 8u -> failwithf "Memory error:$%08x, %i, %s" address address address.toBits
        | Rom -> () //real ROM chips can't be written; ignored rather than a bus error
        | Cart -> () //no cartridge present; writes go nowhere, matching the read side's fixed $ff(ff) stub
        | VideoDisplayRegister ->
            store videoDisplayRegisterMemory (int (address - videoDisplayRegisterStart)) input
        | YM2149 ->
            psgWrite (address &&& 0x2u = 0u) input
        | a when a = mfpTbdr ->
            //Writing the *same* value still resets tbdrReadCount, which is a real state change
            //(it re-phases the next visible decrement) even when tbdr/tbdrReload don't move - so
            //this can't be a plain `store`-style value compare, it needs the count folded in too.
            if tbdr <> input || tbdrReload <> input || tbdrReadCount <> 0u then
                mutations <- mutations + 1UL
            tbdr <- input
            tbdrReload <- input
            tbdrReadCount <- 0u
            //Do NOT touch tbCounter here: real MFP leaves a running timer's main counter alone on a
            //TxDR write and only loads the new value at the next time-out (HblTick's underflow branch
            //already reloads from tbdrReload). Only a TCR write from stop->run reloads immediately.
        | a when a = mfpTbcr ->
            if tbcr <> input || tbdrReadCount <> 0u || tbCounter <> 0 then
                mutations <- mutations + 1UL
            tbcr <- input
            tbdrReadCount <- 0u
            tbCounter <- 0 //arming/re-arming Timer B restarts the HBL event count
        | Mfp -> store mfpRegisters (int (address - mpf68901)) input
        | a when a = fdcModeSelect ->
            let selected = (input >>> 1) &&& 0x3uy
            let scSelected = input &&& 0x10uy <> 0uy
            if selected <> fdcSelectedReg || scSelected <> dmaScSelected then mutations <- mutations + 1UL
            fdcSelectedReg <- selected
            dmaScSelected <- scSelected
            fdcLog (sprintf "mode  $8606<-$%02x  reg=%d sectorCount=%b" input selected scSelected)
        | a when a = fdcAccess && dmaScSelected ->
            //$FF8606 bit 4 is set: this $FF8604 write is the DMA sector-count register, not an FDC
            //register. See dmaSectorCount's comment.
            if input <> dmaSectorCount then mutations <- mutations + 1UL
            dmaSectorCount <- input
            fdcLog (sprintf "count $8604<-$%02x" input)
        | a when a = fdcAccess ->
            match fdcSelectedReg with
            | 0uy when input < 0x80uy ->
                //Type I commands (Restore/Seek/Step/Step-in/Step-out) move the head and, when done,
                //leave the Track register holding the new physical track. TOS's floppy driver
                //($fc1c14/$fc1b7a) writes the *current* head position to the Track register and the
                //*target* track to the Data register, then issues a Seek - so without modelling
                //this a later Read Sector reads the stale Track register (usually 0), not the track
                //TOS sought to. Step-rate / settle / verify flags don't matter to this synchronous
                //model; every command reports "not busy, TR00" like the other stub commands.
                let newTrack =
                    match input &&& 0xF0uy with
                    | 0x00uy -> 0uy                                          //Restore -> track 0
                    | 0x10uy -> fdcData                                      //Seek -> Data register
                    | 0x40uy when input &&& 0x10uy <> 0uy -> fdcTrack + 1uy  //Step-in with update
                    | 0x60uy when input &&& 0x10uy <> 0uy && fdcTrack > 0uy -> fdcTrack - 1uy
                    | _ -> fdcTrack
                let newStatus = fdcCommandStatus input
                //Restore ($0x) takes the slow bucket the boot FDC self-test relies on timing out;
                //a Seek/Step is a cheap adjacent move. See fdcIrq.
                let delay = if input &&& 0xF0uy = 0uy then fdcIrqSlowSteps else fdcIrqFastSteps
                if newTrack <> fdcTrack || newStatus <> fdcStatus || fdcIrq || fdcIrqPending <> delay then
                    mutations <- mutations + 1UL
                fdcLog (sprintf "cmd   type I $%02x -> track %d" input (int newTrack))
                fdcTrack <- newTrack
                fdcStatus <- newStatus
                fdcIrq <- false
                fdcIrqPending <- delay
            | 0uy ->
                //Type II sector transfer: Read Sector ($8x, media -> RAM) or Write Sector ($Ax,
                //RAM -> media). Top 3 bits "100"/"101", bottom 2 bits "00" (FD-HD_Programming.pdf's
                //FDC Command Summary table - the m/h/e flag bits 4/3/2 don't affect this
                //classification). With a disk image mounted, the transfer runs against the
                //already-programmed DMA address counter (real boot-ROM / GEMDOS sequences always
                //set Track/Sector/DMA-address before issuing the command - FD-HD Programming.pdf's
                //own DMA programming tips) and reports success, instead of the always-Record-Not-
                //Found stub every other command still uses. This project has no command timing or
                //real WD1772 seek/settle modeling, so - matching every other FDC command here - the
                //whole operation completes synchronously on this one write. See tryReadSector /
                //tryWriteSector and Hatari FDC_Update{Read,Write}SectorsCmd (src/fdc.c).
                let isReadSector = (input &&& 0xE3uy) = 0x80uy
                let isWriteSector = (input &&& 0xE0uy) = 0xA0uy   //Hatari src/fdc.c: (Command & 0xe0) == 0xa0
                let multiRecord = input &&& 0x10uy <> 0uy
                let dmaAddr =
                    (uint32 dmaAddrHighByte <<< 16) ||| (uint32 dmaAddrMidByte <<< 8) ||| uint32 dmaAddrLowByte
                //With the multi-record (`m`) bit set the WD1772 keeps reading consecutive sectors
                //on the same track until the DMA sector-count register is exhausted (GEMDOS issues
                //a fresh command per track boundary). Without it, exactly one sector. Any sector the
                //drive couldn't find stops the run and reports that sector's error status, matching
                //real hardware - see fdcCommandStatus.
                let count = if multiRecord then max 1 (int dmaSectorCount) else 1
                let xfer t s a = if isWriteSector then tryWriteSector t s a else tryReadSector t s a
                let mutable ok = isReadSector || isWriteSector
                let mutable transferred = 0
                while ok && transferred < count do
                    ok <- xfer fdcTrack (fdcSector + byte transferred) (dmaAddr + uint32 (transferred * 512))
                    if ok then transferred <- transferred + 1
                //Real hardware advances the DMA address counter ($FF8609/B/D) by one per byte
                //actually transferred and decrements the DMA sector-count register; GEMDOS reads
                //both back after a transfer to see where it ended (FD-HD_Programming.pdf, "DMA
                //Registers Address Map" + hatari FDC_WriteDMAAddress). The counter is word-aligned
                //(low bit forced to 0). No-op when nothing transferred (Record Not Found).
                if transferred > 0 then
                    let advanced = (dmaAddr + uint32 (transferred * 512)) &&& 0xFFFFFEu
                    dmaAddrHighByte <- byte (advanced >>> 16)
                    dmaAddrMidByte <- byte (advanced >>> 8)
                    dmaAddrLowByte <- byte advanced
                    dmaSectorCount <- byte (max 0 (int dmaSectorCount - transferred))
                    mutations <- mutations + 1UL
                let status = if ok then 0uy else fdcCommandStatus input
                if status <> fdcStatus then mutations <- mutations + 1UL
                fdcStatus <- status
                //Read Sector and Write Sector both run a DMA transfer, so both move the $FF8606
                //DMA-error bit; other Type II/III commands (Read Address, Force Interrupt) leave it
                //where the last transfer left it.
                if (isReadSector || isWriteSector) && dmaNoError <> ok then
                    dmaNoError <- ok
                    mutations <- mutations + 1UL
                fdcLog (sprintf "cmd   $8604<-$%02x  %s multi=%b count=%d transferred=%d status=$%02x"
                            input
                            (if isReadSector then "READ-SECTOR" elif isWriteSector then "WRITE-SECTOR" else "(other)")
                            multiRecord count transferred status)
                //INTRQ. Force Interrupt ($D0-$DF): $D8-$DF assert immediately, $D0-$D7 terminate with
                //none. A Read/Write Sector that moved data asserts INTRQ now (bytes are already in
                //RAM). Everything else - a sector command that found nothing, Read Address/Track -
                //takes the slow bucket that makes the boot FDC self-test time out. See fdcIrq.
                if input >= 0xD0uy && input < 0xE0uy then
                    fdcIrq <- input &&& 0x08uy <> 0uy
                    fdcIrqPending <- 0
                elif (isReadSector || isWriteSector) && transferred > 0 then
                    fdcIrq <- true
                    fdcIrqPending <- 0
                else
                    fdcIrq <- false
                    fdcIrqPending <- fdcIrqSlowSteps
            | 1uy -> if input <> fdcTrack then mutations <- mutations + 1UL
                     fdcTrack <- input
                     fdcLog (sprintf "track $8604<-%d" (int input))
            | 2uy -> if input <> fdcSector then mutations <- mutations + 1UL
                     fdcSector <- input
                     fdcLog (sprintf "sector $8604<-%d" (int input))
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
    ///See `watchPc` - Program.fs pushes the executing instruction's PC here so WATCH lines can name it.
    member x.WatchPc with get () = watchPc and set v = watchPc <- v
    ///See `watchStep` - Program.fs pushes the current emulated step count here for WATCH lines.
    member x.WatchStep with get () = watchStep and set v = watchStep <- v

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
        diskASides <-
            match data with
            | Some bytes when bytes.Length >= 28 ->
                let heads = int bytes.[26] ||| (int bytes.[27] <<< 8)   //BPB "number of heads", offset 26
                if heads = 1 || heads = 2 then heads else 1
            | _ -> 1

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
    ///Asserts MFP Timer C (channel 5, level 6, vector $45). Gated on the same enable/mask the real
    ///68901 checks: Timer C's channel bit in IERB (bit 5) and IMRB (bit 5) - TOS programs both
    ///during MFP init, so before that a stray tick is simply not raised (its vector at $114 may
    ///not be installed yet). The ACIA still wins arbitration when both are pending - see
    ///`vblPending`/`mfpPending`/`timerCPending`.
    member x.RaiseTimerC() =
        let ierb = mfpRegisters.[int (0xFFFA09u - mpf68901)]
        let imrb = mfpRegisters.[int (0xFFFA15u - mpf68901)]
        if ierb &&& 0x20uy <> 0uy && imrb &&& 0x20uy <> 0uy && not timerCPending then
            timerCPending <- true
            mutations <- mutations + 1UL
    ///Asserts MFP Timer B (channel 8, level 6, vector $48 -> $120) for the TBCR DELAY / PULSE modes
    ///($01-$07, $09-$0F) only - a COARSE tick delivered on an instruction count (Program.fs's
    ///`timerBPeriod`), enough for an ISR that just advances a counter. EVENT-COUNT mode ($08),
    ///which every raster-split game uses, is handled scanline-accurately in HblTick instead, so it
    ///is excluded here. Gated like the others on IERA/IMRA bit 0; TOS leaves Timer B off entirely.
    member x.RaiseTimerB() =
        let iera = mfpRegisters.[int (0xFFFA07u - mpf68901)]
        let imra = mfpRegisters.[int (0xFFFA13u - mpf68901)]
        let mode = tbcr &&& 0x0Fuy
        if mode <> 0uy && mode <> 0x08uy && iera &&& 0x01uy <> 0uy && imra &&& 0x01uy <> 0uy && not timerBPending then
            timerBPending <- true
            mutations <- mutations + 1UL
    ///Called once per emulated scanline (~313x/frame) from Program.fs's Step loop - the HBLANK
    ///granularity the coarse instruction-count ticks lack. Drives MFP Timer B in EVENT-COUNT mode
    ///(TBCR low nibble = $08), where each HBLANK pulse is one count event: seed the live counter
    ///from the programmed TBDR on the first tick after arming, decrement it every scanline, and on
    ///underflow reload it and raise the Timer B interrupt - so a game's raster ISR fires at the
    ///scanline it programmed (Super Sprint's in-race palette ISR, Super Hang-On's post-title split,
    ///Impossamole's attract animation all use TBCR=$08). Gated identically to RaiseTimerB (mode +
    ///IERA/IMRA bit 0), so TOS - Timer B off - never sees a tick and the diskless boot stays
    ///byte-identical.
    member x.HblTick() =
        if tbcr &&& 0x0Fuy = 0x08uy then
            let iera = mfpRegisters.[int (0xFFFA07u - mpf68901)]
            let imra = mfpRegisters.[int (0xFFFA13u - mpf68901)]
            if iera &&& 0x01uy <> 0uy && imra &&& 0x01uy <> 0uy then
                if tbCounter <= 0 then
                    tbCounter <- (if tbdrReload = 0uy then 256 else int tbdrReload)
                tbCounter <- tbCounter - 1
                if tbCounter <= 0 then
                    tbCounter <- (if tbdrReload = 0uy then 256 else int tbdrReload)
                    //Bump `mutations` only on the pending false->true edge, exactly like
                    //RaiseTimerA/B/C - a bare counter decrement is not a CPU-visible change, and
                    //bumping it every scanline would re-anchor the loop detector (Program.fs) each
                    //tick and stop it ever proving a genuine IPL-masked spin is stuck.
                    if not timerBPending then
                        timerBPending <- true
                        mutations <- mutations + 1UL
    ///Counts down a pending WD1772 INTRQ. Called from Program.fs's Step loop at the same cadence as
    ///HblTick (`steps` = instructionsPerLine), so a CPU polling `btst #5,$fffffa01` sees the line
    ///drop after the command's fast/slow bucket has elapsed. See fdcIrq for why the delay exists.
    member x.FdcTick(steps: int) =
        if fdcIrqPending > 0 then
            fdcIrqPending <- fdcIrqPending - steps
            if fdcIrqPending <= 0 then
                fdcIrqPending <- 0
                if not fdcIrq then
                    fdcIrq <- true
                    mutations <- mutations + 1UL
    ///Asserts MFP Timer A (channel 13, level 6, vector $4D -> $134). Gated on Timer A being armed
    ///(TACR mode bits non-zero) and its channel enabled+unmasked in IERA/IMRA bit 5 - TOS leaves
    ///Timer A off (the classic "free" application timer), games turn it on. Super Hang-On's intro
    ///drives a software-synth music player off Timer A and busy-waits on the tick counter its ISR
    ///increments. COARSE like RaiseTimerB/C: delivered on an instruction count, so the music tempo
    ///is wrong but the intro sequence advances instead of hanging. Vector $4D = VR($40) | channel 13.
    member x.RaiseTimerA() =
        let tacr = mfpRegisters.[int (0xFFFA19u - mpf68901)]
        let iera = mfpRegisters.[int (0xFFFA07u - mpf68901)]
        let imra = mfpRegisters.[int (0xFFFA13u - mpf68901)]
        if tacr &&& 0x0Fuy <> 0uy && iera &&& 0x20uy <> 0uy && imra &&& 0x20uy <> 0uy && not timerAPending then
            timerAPending <- true
            mutations <- mutations + 1UL
    ///The single place the interrupt-source priority order is written down. Highest-priority
    ///currently-asserted source: 0 = Timer A, 1 = MFP/ACIA, 2 = Timer B, 3 = Timer C, 4 = VBL,
    ///5 = none. `PendingInterruptLevel` / `PendingInterruptVector` / `AcknowledgeInterrupt` all
    ///dispatch on this so the three can never drift out of sync. Allocation-free (checked every
    ///`Cpu.Step()`).
    member private x.TopPendingInterrupt =
        if timerAPending then 0
        elif mfpPending then 1
        elif timerBPending then 2
        elif timerCPending then 3
        elif vblPending then 4
        else 5
    member x.PendingInterruptLevel =
        match x.TopPendingInterrupt with
        | 5 -> 0    // nothing asserted
        | 4 -> 4    // VBL is autovector level 4
        | _ -> 6    // every MFP source is level 6
    member x.PendingInterruptVector =
        match x.TopPendingInterrupt with
        | 0 -> 0x4D
        | 1 -> mfpVector
        | 2 -> 0x48
        | 3 -> 0x45
        | 4 -> 28
        | _ -> 0
    ///Called by `Cpu.Step()` once it has decided to actually take the pending interrupt (i.e. it
    ///cleared the current IPL mask) - clears only the slot being taken (the highest one), so a
    ///lower still-pending source stays pending, matching real interrupt-acknowledge behaviour.
    member x.AcknowledgeInterrupt() =
        (match x.TopPendingInterrupt with
         | 0 -> timerAPending <- false
         | 1 -> mfpPending <- false
         | 2 -> timerBPending <- false
         | 3 -> timerCPending <- false
         | 4 -> vblPending <- false
         | _ -> ())
        mutations <- mutations + 1UL
        interruptAcks <- interruptAcks + 1UL

    ///Count of interrupts actually taken (autovector VBL, MFP ACIA/Timer C). Distinct from
    ///`Mutations`: the loop detector uses this to tell "spinning until a scheduled interrupt
    ///arrives" (e.g. TOS's `vsync` waiting on the VBL to bump `frclock`) apart from a genuine
    ///stuck loop - a spin that an interrupt keeps rescuing is not provably stuck.
    member x.InterruptAcks = interruptAcks

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
          Ym2149 = Array.copy psgRegs
          PsgSelectedReg = psgSelectedReg; PsgReadData = psgReadData
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
        Array.blit snapshot.Ym2149 0 psgRegs 0 (min snapshot.Ym2149.Length psgRegs.Length)
        psgSelectedReg <- snapshot.PsgSelectedReg
        psgReadData <- snapshot.PsgReadData
        updateDriveSide ()
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
        if flatBus then
            (int (flatGet address) <<< 24) ||| (int (flatGet ((address + 1u) &&& maxMemory)) <<< 16)
            ||| (int (flatGet ((address + 2u) &&& maxMemory)) <<< 8) ||| int (flatGet ((address + 3u) &&& maxMemory))
        else
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
        | VideoDisplayRegister ->
            //ReadWord/WriteWord/WriteLong all handle the shifter register block; ReadLong was the
            //one gap, so `move.l $ffff8244,Dn` (Super Hang-On's raster palette handler reads two
            //palette words at once) bus-errored into vector 2. Compose byte-wise like YM2149/MFP.
            (int (x.ReadByte address) <<< 24) |||
            (int (x.ReadByte (address+1u)) <<< 16) |||
            (int (x.ReadByte (address+2u)) <<< 8) |||
            (int (x.ReadByte (address+3u)))
        | YM2149 ->
            (int (x.ReadByte address) <<< 24) |||
            (int (x.ReadByte (address+1u)) <<< 16) |||
            (int (x.ReadByte (address+2u)) <<< 8) |||
            (int (x.ReadByte (address+3u)))
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
