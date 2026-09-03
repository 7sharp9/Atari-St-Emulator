# powermonger — the emulator bugs the cracks exposed, and how far it runs now

PowerMonger (© 1990 Bullfrog / Electronic Arts). Driven from two scene cracks.
This folder documents the emulator bugs the cracks exposed and their fixes.

**66th pass: [cr Replicants] now runs all the way into the game.** credits →
`SPACE` → "What Is Thy Name Oh Lord" name entry → type a name + `RETURN` →
"Welcome to the World of PowerMonger / select option" menu → click **START NEW
CONQUEST** → the campaign **world map** (green landmasses on blue sea, cursor
tracks the mouse). See "66th pass — reached the game" below.

**67th pass: past the world map into the mission-briefing screen.** Clicking the
scroll icon at the world map's top-left corner (~18,18 in 320-space) advances to
the "Between Pages 1-5" briefing (three commanders behind a stone table, a
territory preview, "How many People in this land?" with two OK buttons). Getting
there needed two 68000 divide fixes the isometric-view setup code exercises:
DIVU/DIVS quotient-overflow, and DIVU/DIVS divide-by-zero to vector 5 (see
"Bug 4" below). `briefing.png`.

**68th pass: clicking OK on the briefing drops PM into the isometric battle
view.** `iso_view.png`: the height-mapped terrain on the stone table, the
commander portrait, the mini-map, the full command UI. No emulator code change:
the 67th pass had the dialog hit-test decoded correctly but the OK-button
click positions tried were outside the panel's grid and the jump-table base
used to read the per-dialog OK handler was mis-computed by four bytes. The
briefing panel is a 24x32 grid of 4x6-pixel cells anchored at screen (0,0);
the left OK button's clickable cells sit at grid col 3-6 / row 28-29, i.e.
screen x 16-24, y 174-180. A left click there runs `$b814`, which commits the
population and sets `$1c48a=1` to advance the state machine. See "PM's mouse
dialog state machine" below for the full decode.

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

## Bug 4 — the isometric-view setup code needs real 68000 DIVU/DIVS (67th pass)

Clicking the world-map scroll icon loads the mission-setup overlay above `$1050`,
which does isometric vertex projection with `DIVU` / `DIVS`. Two `failwith`s in
`68k.fs` `DecodeBucket8` stopped it dead:

- **Quotient overflow.** `DIVU D0,D1` with `D1/D0 > 0xffff` (and the DIVS
  equivalent) was `failwith "quotient overflow (V flag not implemented)"`. The
  SingleStepTests 68000 vectors are unambiguous: on overflow the 68000 sets
  **V=1, C=0** and leaves **N, Z, X and the destination register untouched**, PC
  still advancing past the instruction (no trap; this is not divide-by-zero).
  That is what the fix does. (Hatari's `setdivuflags`/`setdivsflags` force
  `N=1/Z=0` for its "68000" branch, a different chip revision from the one
  TomHarte captured; every overflow vector in the suite only touches V and C.)
  The DIVS check runs in `int64` so `Int32.MinValue / -1` is caught as overflow
  instead of raising a CLR exception.

- **Divide by zero.** `DIVU D0,D1` with `D0.w = 0` was
  `failwith "divide by zero (trap not implemented)"`. Now traps to **vector 5**
  with the standard 68000 group-2 frame (SR + PC-of-next-instruction) via
  `EnterVector`, same shape as CHK/TRAPV. The SingleStepTests carry no
  zero-divisor vectors so this path is unchecked by selftest, but it matches the
  68000 manual and PM's renderer hits it for real.

Selftest after the fix: DIVU 2494→4963 pass, DIVS ~2500→4992 pass, **0 wrong,
0 unimplemented** for both (the residual `frame` fails are the pre-existing
odd-address address-error cases, unchanged). 30M diskless boot byte-identical.

### Drive recipe (68th pass, briefing to isometric view)

```
# from the "Between Pages 1-5" briefing (scratchpad/pm67_p4c.snap, PC $e450):
./run.ps1 -NoBuild rrepl scratchpad/pm67_p4c.snap -DiskA scratchpad/pm63/pm_replicants.st
  w 2df92 001400b1      # cursor X=$14 (20), Y=$b1 (177) - inside the left OK button
  w 2df8e 001400b1      # latched click position (same)
  w 2df96 00010001      # left-click-pending edge flag
  s 12000000            # -> the isometric battle view (iso_view.png), $14e4e = $2c
```

The `w` pokes stand in for a real click delivered through PM's mouse state
machine; a live `mouse move` / `mouse down l` to the same screen position does
the same thing. `snap` at the end for `pm68_isoview.snap`.

## PM's mouse dialog state machine (67th pass RE, completed 68th)

PM's own IKBD ISR is at `$18be` (vector `$46`, i.e. `[$118]`). It parses the
`$F7` absolute-position reply (our `$0D` interrogation answer):

| RAM addr | holds |
|----------|-------|
| `$1c48f` | the `$F7` button-edge byte (`%0000dcba`: c=left-down, d=left-up) |
| `$2df92` | cursor **X** (word) |
| `$2df94` | cursor **Y** (word) |
| `$2df8e` | cursor position **latched at the moment of a click** (long, = `$2df92`) |
| `$2df96` | **left-click pending** edge flag, set 1 on a left-down, consumed and cleared by whichever dialog owns the click |
| `$2df9c` | left-button level (1 while held) |
| `$2df98` / `$2df9e` | the right-button pending / level pair |

The VBL handler `$1270` dispatches on `$1c48f` through a jump table at `$12ac`
(word offsets, index = `button_byte * 2`): button `4` (left-down) → `$1330`,
which sets `$2df96=1` and latches `$2df8e`.

### The briefing dialog hit-test (`$7298`), decoded

`$7298` runs when `$2df96 != 0`. It loads D0=X, D1=Y from the latched click
(`movem.w $2df8e,#$0003`) and walks the four 8-byte entries of the dialog
descriptor at `$7a36`:

| entry word | meaning |
|------------|---------|
| word 0 (`D2`) | offset from `$7a36` to this panel's `{widthCells:b, heightCells:b}` pair, then its cell grid; `0` = inactive entry |
| word 1 (`D3`) | packed rectangle origin: `left = ((D3>>8) & 0x1f) * 16`, `top = D3 & 0xff` |

The briefing has one active entry (`$7a36` = `0176 0000 ...`): panel at screen
`(0,0)`, `descriptor+$176` = `{06, 20}` so the grid is **24 cols x 32 rows of
4x6-pixel cells**, covering screen x 0-95, y 0-191. A hit computes
`col = (X-left) >> 2`, `row = (Y-top) / 6`, fetches `grid[row*24 + col]`:

- cell `>= $20` (text / button glyphs incl. `$80`-`$87`) -> handler `$7658`
- cell `$01`-`$1f` -> small jump table at `$735e` (border cells `$01`-`$0b` ->
  `$739e` "click-anywhere confirm"; `$10`/`$11` -> `$73d4`/`$740e` digit
  up/down on the population counter)

Grid layout (row : screen-y):

```
r28 y168:  . .   80 81 81 82 . . .   10 10 10 10 . . .   80 81 81 82 . .   ($10 = population up-arrows)
r29 y174:  . .   83 4f 4b 84 . . .   30 30 30 30 . . .   83 4f 4b 84 . .   ("OK" text, "0000" digits)
r30 y180:  . .   85 86 86 87 . . .   11 11 11 11 . . .   85 86 86 87 . .   ($11 = population down-arrows)
```

`$7658` re-walks from the clicked cell to the enclosing `$80` cell (top-left of
a button widget), gets its grid offset in D3 (left OK = `$2a3`, right OK =
`$2b1`), plays a click sound, then `jmp` through a **per-dialog** table:
`D0 = word[$76fa + $7a3c]`, `jmp $76fe + D0`. `$7a3c` is the dialog id; the
briefing's is `$0a`, and `word[$76fa + $0a] = word[$7704] = $0186` ->
`jmp $7884`:

```
$7884  cmpi.w #$2a3,D3 ; beq $7890     ; left OK
$788a  cmpi.w #$2b1,D3 ; bne $7896     ; right OK
$7890  jsr $b814
```

`$b814` parses the population digit string, then **unconditionally** (the crack
nopped the "must enter a value" check at `$b842`: `moveq #0,D0 / nop / bne`)
writes `population + $2c` to `$14e4e` (the gate the `$739e` handler and `$7774`
test), copies the game-state seed table `$584c4` -> `$580a0`, `jsr $13b9a`
(world generation / `$10d1e` load path), and `move.w #$1,$1c48a` to advance the
main state machine. One frame later PM is compositing the isometric view.

The 67th-pass "no click accepted" was two mistakes: click positions outside the
`(0,0)`-anchored grid, and reading the per-dialog OK table with the base four
bytes low so `$7a3c=$0a` appeared to route to a handler that ignores OK.

## How far it runs now

1. Boots. ALTAIR / YODA boot runs, FDC self-test exits, TOS `Pexec`s the game.
2. Cracktro key-wait (`cracktro.png` = Replicants).
3. ~1 MB load + ICE depack, no wall.
4. **PowerMonger title** — "Powermonger" logo + Electronic Arts, then a scrolling
   credits sequence ("Special Thanks to…", "Designed by Bullfrog", "Programmed by
   Peter Molyneux / Glenn Corpes", …) — `title.png`, `credits.png`.
5. Empire runs on to the pre-game narrative screen — "Pondering over the map, you
   prepare plans for battle…" (`empire_intro.png`).
6. Replicants: name entry -> option menu -> world map -> mission briefing ->
   **isometric battle view** (`iso_view.png`) with the height-mapped terrain,
   commander portrait, mini-map and command UI. The view is static while no
   input is given (PM only recomposites the terrain on scroll / rotate / zoom /
   unit movement); driving it further needs PM's in-game key handling reversed,
   which is a separate job.

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

The isometric terrain renderer was reached and profiled in the 68th pass, see
`graphics.md` for the grounded routine-by-routine breakdown (`$14b62` entity /
projection loop, `$163ea` shift-add iso projection, `$1648e` terrain sampler,
`$164bc` DIVU edge-slope, `$16738` sprite blit, `$12ce0` bulk buffer -> screen
copy).

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
| `briefing.png` | "Between Pages 1-5" mission-briefing screen, reached past the world map (67th pass) |
| `iso_view.png` | the isometric battle view, reached by clicking OK on the briefing (68th pass) |
