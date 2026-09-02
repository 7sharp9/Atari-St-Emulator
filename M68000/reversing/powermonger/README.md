# powermonger — the emulator bugs the cracks exposed, and how far it runs now

PowerMonger (© 1990 Bullfrog / Electronic Arts). Driven from two scene cracks.
This folder documents the emulator bugs the cracks exposed and their fixes.

**66th pass: [cr Replicants] now runs all the way into the game.** credits →
`SPACE` → "What Is Thy Name Oh Lord" name entry → type a name + `RETURN` →
"Welcome to the World of PowerMonger / select option" menu → click **START NEW
CONQUEST** → the campaign **world map** (green landmasses on blue sea, cursor
tracks the mouse). See "66th pass — reached the game" below. The isometric battle
view is one world-map territory-click further and has not been pinned down yet
(the click target needs the cursor exactly on a land pixel, PM validating
land-vs-sea).

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

## 66th pass — reached the game ([cr Replicants])

The 65th-pass "post-credits derail to `PC=$240000fc`" turned out to be **a
resume-without-`-DiskA` artefact plus the wrong key** (`RETURN`, which the credits
VBL handler at `$2c8a` ignores — it tests `cmpi.b #$39,$fffc02` = **SPACE**).
With the disk mounted and `SPACE`, PM's post-credits loader (`$12e8` → `$57032`
path parses `data\sprite40.dat` and issues its own raw multi-sector FDC reads,
which our WD1772 model already serves — `transferred=10 status=$00`) relocates
the game to `$1050` and runs on with no derail.

The one real emulator gap was input: PM's menus poll the IKBD every frame with
`$0D` "interrogate mouse position" and `$16` "interrogate joystick" and never
touch the relative `$F8` packets. The interpreter had no reply path, so the mouse
froze. Fixed in commit `MMU: answer the IKBD $0D / $16 interrogation commands`
(66th pass) — the interpreter now maintains the 6301's internal absolute mouse
position + button state and replies `$F7`/`$FD` packets.

Drive recipe (Replicants, 66th pass):

```
./run.ps1 -NoBuild repl 1 -DiskA "Powermonger (1990)(Bullfrog)[cr Replicants].st"
  s 15000000                     # -> Replicants cracktro key-wait
  kbd 1c                         # RETURN advances the cracktro
  s 55000000                     # -> "Powermonger" title + scrolling credits ($12aa loop)
  kbd 39                         # SPACE  -> past the credits (RETURN is ignored here)
  s 80000000                     # loads data\*.dat, relocates -> "What Is Thy Name Oh Lord"
  kbd 20 <settle> a0 <settle> …  # type a name SLOWLY (one make/break per s ~800000 - the
                                 #   handler drops bytes that arrive back-to-back), then
  kbd 1c 9c                      # RETURN -> "Welcome to the World of PowerMonger" menu
  mouse move 100 50 / 55 35      # cursor onto START NEW CONQUEST (~155,85 in 320-space)
  mouse down l / mouse up l      # -> the campaign world map
```

Snapshots this pass: `pm66_credits` / `pm66_name2` ("dave" typed) / `pm66_map`
(menu) / `pm66_newconq` (world map). Screens: `name_entry.png`, `menu.png`,
`world_map.png`.

### Graphics pipeline — what is visible so far (Q2)

The **isometric zoomable battle view** — the thing Dave's Q2 is about — is a
separate code overlay PM loads when you enter a territory, and it was not reached
live this pass (see the world-map click note above), so its rasteriser could not
be profiled with real hit counts. What *is* observable:

- **Credits / name-dialog / menu compositor** — heavy time in `$88ac`–`$8960`,
  a 4-bitplane word compositor: `move.w (A0)+,D4 / rol.w Dn,D4 / andi.w #$f000,D4`
  for each of 4 planes, OR-combined, `move.w D4,(A5)+`, unrolled ×6 with a
  `lea 152(A5),A5` row stride and a `dbf D6` outer loop, driven by a command
  stream at `A4`. A chunky/indexed → 4-plane blit.
- **World-map frame refresh** — `$11422`: `lea $3f364,A0` (an off-screen composed
  buffer) → `mulu #$a0,D0` (row = index × 160) → `movem.l (A0)+,#$7cf8` /
  `movem.l #$7cf8,(A1)` (44 bytes/`movem`), 58 inner × 3 outer. A straight
  register-blit of the composed viewport strip to the shifter buffer each VBL.
  On the static world map PM does this once/frame then idles in the `$1870`
  VBL-wait spin (~1.9 M of ~2 M sampled steps).
- **Screen output** is direct-to-shifter: the displayed base is read from
  `$FFFF8201/8203` (`$024400` at the menus, `$01c700` after transitions), not
  `_v_bas_ad` at `$44E` — screendump / the frame recorder must use the shifter
  base for PM.

A profile of the isometric terrain renderer (vertex projection MULS/DIVS, terrain
fill, sprite painter's-sort, per-zoom LOD) needs PM one territory-click deeper —
carried to the next pass. See `graphics.md` for the "what a modern port would do"
notes, which stand on the design regardless.

## Files

| file | what |
|------|------|
| `cracktro.png` | Replicants cracktro key-wait (after the FDC self-test fix) |
| `title.png` | PowerMonger title, reached after the depacker-derail fixes |
| `credits.png` | the scrolling credits sequence |
| `empire_intro.png` | Empire build, the "Pondering over the map…" intro screen |
| `name_entry.png` | "What Is Thy Name Oh Lord" — keyboard dialog (66th pass) |
| `menu.png` | "Welcome to the World of PowerMonger" option menu (66th pass) |
| `world_map.png` | the campaign world map — PM in-game (66th pass) |
