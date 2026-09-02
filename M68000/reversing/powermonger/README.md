# powermonger — two emulator bugs the cracks exposed, and how far it runs now

PowerMonger (© 1990 Bullfrog / Electronic Arts). Driven from two scene cracks.
This folder documents three emulator bugs the cracks exposed and their fixes, not
a full control-flow reconstruction — the game now runs its title + credits +
intro sequence but has not been driven into gameplay (its map screen is
mouse-menu driven).

**The disks are not committed** (commercial). To reproduce:

```
unzip "Powermonger (1990)(Bullfrog)[cr Replicants].zip"
#   sha256 2099be892f49d779bbdf6f5d397b160c3048647c1d3c73d1fba2c0552cb02b31   819200 bytes
unzip "Powermonger (1990)(Bullfrog)[cr Empire].zip"
#   Powermonger (1990)(Bullfrog)[cr Empire].st                               829440 bytes
```

Replicants: 820 KB, double-sided 80/10/2, bootable (boot-sector word-sum
`$1234`), boot sector = TDT "ALTAIR ANTI VIRUS V3.00". Empire: 810 KB, `AUTO\`
`WARI.PRG` is the game, "SK Micro Intro 6.0 (C) 1990 YODA" cracktro.

### Drive recipes

```
# Replicants -> PowerMonger title/credits/intro
./run.ps1 -NoBuild repl 1 -DiskA "Powermonger (1990)(Bullfrog)[cr Replicants].st"
  s 15000000        # -> Replicants cracktro key-wait
  kbd 1c            # RETURN advances it (space misbehaves)
  s 55000000        # loads ~1 MB, depacks, runs -> "Powermonger" title + scrolling credits

# Empire -> PowerMonger title + "Pondering over the map..." intro
./run.ps1 -NoBuild repl 1 -DiskA "Powermonger (1990)(Bullfrog)[cr Empire].st"
  s 8000000         # -> Empire / YODA cracktro key-wait
  kbd 39 b9         # SPACE advances it (return does nothing)
  s 45000000        # -> title, then the pre-game narrative screen
```

---

## Bug 1 — FDC self-test hang (62nd pass diagnosis, 63rd pass fix)

Booted with the Replicants disk, TOS printed "TDT ALTAIR ANTI VIRUS V3.00:
CHECK OK:" forever. Root cause, traced against a real Hatari `cpu_disasm`:

After the primary autoboot, TOS runs an **FDC self-test loop at ROM `$fc04a8`** —
8 iterations, each firing one raw WD1772 command and polling
`$fc0580: btst #5,$fffffa01 / beq` for completion with a `_hz_200 + 10` (~50 ms)
deadline. It is a *presence* check: on real hardware those bare commands are
still running when the deadline expires, every poll times out, and the loop
exits after 8 tries without ever running its `$fc04cc: jsr (A0)`.

This emulator hardwired **MFP GPIP bit 5 (FDC IRQ, active-low) to 0** — "a
command is always complete" — so every poll succeeded instantly and
`$fc04cc: jsr (A0)` re-executed the still-valid `$1234` boot sector in
`_dskbufp` every iteration. The boot sector's own `move.w #$ff,d7` clobbered the
ROM loop's `add.b #$20,d7 / bne` counter, so the loop never terminated. (A plain
TOS boot survived only because its buffer didn't checksum to `$1234`; this
crack's boot sector does.)

**Fix:** `MMU`'s `fdcIrq` / `FdcTick`. GPIP bit 5 idle-high, re-raises INTRQ on a
coarse bucketed delay after a command (immediate for a Read/Write Sector that
moved data, ~4000 steps for a Seek/Step, ~40000+ for a Restore / failed search /
Read Address). The self-test's first polled command is a Restore, so it times
out and the loop exits. Diskless-boot `checkpoint.txt` re-baselined.

## Bugs 2 & 3 — the depacker derail (64th pass)

Past the cracktro, both cracks load ~1 MB of game data (hundreds of successful
double-sided FDC reads) and hand off to an **ICE depacker** ("Ice!" magic
`$49636521`, the plain-68000 self-decompressor at `$70880` in the Replicants
build). Depacking completed cleanly; execution then derailed — Replicants to
`PC=$20` (running the exception vector table as code → `WriteEa: immediate
operand is not a valid destination`), Empire to low RAM `$5a6`.

Traced the Replicants derail instruction-by-instruction from the depacker's
`rts`. The cracktro's installed VBL handler at `$660` does:

```
$660  move.l  D0,$2ca2
$666  move    usp,A0
$668  move.l  A0,$2c9c
$66e  movem.l $ffff8240,#$00ff        ; read the 16 palette words
$676  movem.l #$00ff,$2caa            ; stash them
$67e  move.l  #$00078000,$ffff8260.w  ; <-- long write to the shifter res register
```

The `move.l` to `$ffff8260` writes four bytes: `$ff8260`/`$ff8261` (the GLUE +
shifter resolution registers) and **`$ff8262`/`$ff8263`**. This emulator's
video-register region ended at `$ff8260`, so the second word hit the generic
`raise (BusError …)` fall-through. That bus error vectored through a cracktro
vector table that doesn't handle it → garbage PC → the vector-table-as-code
crash. Empire's `$5a6` derail is the same bus error landing on a different bogus
vector.

On a plain ST the shifter chip is selected for the whole `$ff8200`–`$ff827f`
page but decodes no register in `$ff8262`–`$ff827f`; accesses there are harmless.
Hatari's `IoMemTable_ST` marks exactly this: `{ 0xff8262, 30, IoMem_VoidRead,
IoMem_VoidWrite }` with the comment *"No bus errors here"* (`$ff8261` is also a
real register there, `Video_ResShifter`, which this emulator was also
bus-erroring on).

**Fix 2** (`MMU.fs`): `videoDisplayRegisterEnd` `$ff8260` → `$ff8261` (the
shifter-only res register is real), and a new `ShifterVoid` region
`$ff8262`–`$ff827f` — reads return open-bus `$ff`, writes are dropped, no bus
error. The `videoDisplayRegisterMemory` array is unchanged (98 bytes), so the
snapshot format and the byte-identical diskless boot are untouched.

**Fix 3** (`68k.fs` `DecodeBucket9`): with the bus error gone the Replicants
depacked code next hit `suba.l (d16,PC),A5` — the hand-coded SUBA.L handler only
covered `Dn` / `An` / `#imm.L` / `(xxx).L` and bus-errored on every other mode.
Replaced the whole `match eamode` block with the shared EA decoder
(`x.ResolveEa` / `x.ReadEa`), mirroring the CMPA.L / SUBA.W arms directly above
it. Selftest pass count rose ~3000 (previously-`unimpl` SUBA.L modes now correct)
with the wrong-answer lane still at 0.

## How far it runs now

1. Boots. ALTAIR / YODA boot runs, FDC self-test exits, TOS `Pexec`s the game.
2. Cracktro key-wait (`cracktro.png` = Replicants).
3. ~1 MB load + ICE depack, no wall.
4. **PowerMonger title** — "Powermonger" logo + Electronic Arts, then a scrolling
   credits sequence ("Special Thanks to…", "Designed by Bullfrog", "Programmed by
   Peter Molyneux / Glenn Corpes", …) — `title.png`, `credits.png`.
5. Empire runs on to the pre-game narrative screen — "Pondering over the map, you
   prepare plans for battle…" (`empire_intro.png`).
6. Not yet driven into gameplay: the map / plan screen is mouse-menu driven and
   the emulator does not interpret IKBD mouse-mode commands. A CFG / sym
   reconstruction is deferred until it can be driven that far.

## Files

| file | what |
|------|------|
| `cracktro.png` | Replicants cracktro key-wait (after the FDC self-test fix) |
| `title.png` | PowerMonger title, reached after the depacker-derail fixes |
| `credits.png` | the scrolling credits sequence |
| `empire_intro.png` | Empire build, the "Pondering over the map…" intro screen |
