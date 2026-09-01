# powermonger — the FDC self-test hang, and how far `[cr Replicants]` now gets

PowerMonger (© 1990 Bullfrog / Electronic Arts). Driven from the scene crack
`Powermonger (1990)(Bullfrog)[cr Replicants].zip` (Replicants / Illegal). This
folder documents an emulator bug the crack exposed and the fix, not a full
control-flow reconstruction — the game does not yet run to its title.

**The disk is not committed** (commercial). To reproduce:

```
unzip "Powermonger (1990)(Bullfrog)[cr Replicants].zip"
#   Powermonger (1990)(Bullfrog)[cr Replicants].st
#   sha256 2099be892f49d779bbdf6f5d397b160c3048647c1d3c73d1fba2c0552cb02b31   819200 bytes
```

820 KB, double-sided, 80 track / 10 sector / 2 head, **bootable** (boot-sector
word-sum `$1234`). Root: `MREP` + `WAR` markers, `AUTO\POWER.PRG`, `DATA\*.DAT`.
The boot sector is TDT's "ALTAIR ANTI VIRUS V3.00".

## The hang (62nd pass diagnosis, 63rd pass fix)

Booted with this disk, TOS printed "TDT ALTAIR ANTI VIRUS V3.00: CHECK OK:"
forever, filling the screen. Root cause, traced against a real Hatari
`cpu_disasm`:

After the primary autoboot, TOS runs an **FDC self-test loop at ROM `$fc04a8`** —
8 iterations, each calling `$fc04d6` to fire one raw WD1772 command type
(Restore / Step / Step-in / Step-out / ReadSector / WriteSector / ReadAddr /
ReadTrack) and poll `$fc0580: btst #5,$fffffa01 / beq` for completion, with a
`_hz_200 + 10` (~50 ms) deadline. The loop is a *presence* check: on real
hardware those bare commands are still running when the deadline expires, each
poll times out, `$fc04d6` returns failure, and the loop exits after 8 tries
without ever running its `$fc04cc: jsr (A0)`.

This emulator hardwired **MFP GPIP bit 5 (the FDC IRQ line, active-low) to 0** —
"a command is always complete". So every poll returned success instantly,
`$fc04d6` reported success, and `$fc04cc: jsr (A0)` re-executed the still-valid
`$1234` boot sector in `_dskbufp` on every iteration. The boot sector's own
`move.w #$ff,d7` then clobbered the ROM loop's `add.b #$20,d7 / bne` counter, so
the loop never terminated. (A plain TOS boot survived only because the buffer it
re-ran didn't checksum to `$1234`; this crack's boot sector does.)

Hatari for the same boot: `$fc04d6` called 8×, `$fc04cc` **0×**, clean exit.

### Fix

`MMU`'s `fdcIrq` / `FdcTick` (commit *"MMU: give WD1772 INTRQ / GPIP bit 5 real
completion timing"*). GPIP bit 5 is idle-high and re-raises INTRQ on a coarse
delay after a command, cleared on a status-register read or a new command. No
per-command WD1772 state machine (Hatari's `src/fdc.c` has one, ~2000 lines);
the delay is bucketed instead:

| command | INTRQ after | why |
|---------|-------------|-----|
| Read/Write Sector that moved data | immediately | bytes are already in RAM; a per-sector delay adds tens of millions of steps to a big load |
| Seek / Step (Type I `$1x`–`$7x`) | ~4000 steps | a real adjacent-track seek is a few ms; the real read path does one before most sector reads |
| Restore (`$0x`), failed search, Read Address/Track | ~40000 steps | above the self-test's ~30000-step deadline, far below the GEMDOS `$40000`-iteration poll budget |

The self-test's first polled command is a Restore, so it now times out and the
loop exits. The boot timeline moves ~1.4M steps later (spin instead of
short-circuit), so the diskless-boot `checkpoint.txt` was re-baselined.

## How far it gets now

1. Boots. The ALTAIR boot sector runs once, the self-test exits, TOS
   `Pexec`s `\AUTO\POWER.PRG`.
2. **Replicants / Illegal cracktro** — "The masters and The replicants /
   Savagely present Powermonger / Cracked by Illegal / … / hi to : …". A
   `Bconin(2)` key-wait (`cracktro.png`). This is the 62nd-pass success target.
3. A key advances to a second screen ("IMPORTED BY THE MASTERS / BROKEN BY
   ILLEGAL!").
4. Past that it loads **~1 MB of game data** — hundreds of successful
   double-sided FDC reads to `$04xxxx` — then its depacker **derails to
   `PC=$20`** (executes the exception vector table as code; the next opcode is
   an illegal write-to-immediate). All FDC reads succeeded, so this is not the
   floppy path. It is the same undiagnosed class as `[cr Empire]`'s WARI.PRG
   (62nd pass) and the 60th-pass HxC WAR.PRG self-decompressor — a bad control
   transfer out of a depacker, cause not yet found.

## Files

| file | what |
|------|------|
| `cracktro.png` | the Replicants cracktro key-wait reached after the self-test fix |
