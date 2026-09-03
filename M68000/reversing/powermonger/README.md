# powermonger — the emulator bugs the cracks exposed, and how far it runs now

PowerMonger (© 1990 Bullfrog / Electronic Arts), driven from two scene cracks.
As of the 68th pass, [cr Replicants] runs cold-boot all the way into the
**isometric battle view**: cracktro, ICE depack, title + credits, name entry,
option menu, campaign world map, "Between Pages 1-5" mission briefing, and past
the briefing's OK button into the height-mapped terrain view (`iso_view.png`).
The four emulator bugs the cracks exposed on the way are documented below; the
graphics pipeline is analysed in `graphics.md`.

**Disks are not committed** (commercial). Reproduce:

```
unzip "Powermonger (1990)(Bullfrog)[cr Replicants].zip"
#   sha256 2099be892f49d779bbdf6f5d397b160c3048647c1d3c73d1fba2c0552cb02b31   819200 bytes  (820 KB, DS 80/10/2, bootable $1234, TDT "ALTAIR ANTI VIRUS V3.00" boot sector)
unzip "Powermonger (1990)(Bullfrog)[cr Empire].zip"
#   829440 bytes  (810 KB, AUTO\WARI.PRG, "SK Micro Intro 6.0 (C) 1990 YODA" cracktro)
```

## Drive recipe: cold boot to the isometric view ([cr Replicants])

```
./run.ps1 -NoBuild repl 1 -DiskA "<replicants>.st"     # -DiskA on EVERY rrepl/resume (mount is not snapshotted)
  s 15000000 ; kbd 1c ; s 55000000                     # RETURN -> "Powermonger" title + scrolling credits
  kbd 39 ; s 80000000                                  # SPACE (RETURN ignored here) -> "What Is Thy Name" name entry
  kbd 20 <settle ~800k> a0 <settle> … ; kbd 1c 9c      # type a name SLOWLY (handler drops back-to-back bytes), RETURN
                                                        #   -> "Welcome to the World of PowerMonger" option menu
  mouse move onto ~(155,85) in 320-space ; mouse down l ; mouse up l   # START NEW CONQUEST -> campaign world map
  mouse move onto ~(18,18) in 320-space  ; mouse down l ; mouse up l   # top-left scroll icon -> "Between Pages 1-5" briefing
  w 2df92 001400b1 ; w 2df8e 001400b1 ; w 2df96 00010001 ; s 12000000  # left OK button (cursor 20,177) -> ISOMETRIC VIEW
```

The final `w` pokes stand in for a click delivered through PM's mouse state
machine; `mouse move` / `mouse down l` to screen (20,177) works too. PM screen
is direct-to-shifter, `scratchpad/pmshot.sh <snap> <png>` reads `$FFFF8201/8203`
(`$024400` menus, `$01c700` iso view), not `_v_bas_ad $44E`.

Empire build: `s 8000000` / `kbd 39 b9` (SPACE) / `s 45000000` → title, then the
"Pondering over the map…" narrative screen. Not driven further.

---

## Bug 1 — FDC self-test hang (62nd pass diagnosis, 63rd pass fix)

Booted with the Replicants disk, TOS printed "TDT ALTAIR ANTI VIRUS V3.00:
CHECK OK:" forever. Traced against a real Hatari `cpu_disasm`:

After the primary autoboot, TOS runs an **FDC self-test loop at ROM `$fc04a8`**:
8 iterations, each firing one raw WD1772 command and polling
`$fc0580: btst #5,$fffffa01 / beq` with a `_hz_200 + 10` (~50 ms) deadline. It is
a *presence* check: on real hardware those bare commands are still running when
the deadline expires, every poll times out, and the loop exits after 8 tries
without ever running its `$fc04cc: jsr (A0)`.

This emulator hardwired **MFP GPIP bit 5 (FDC IRQ, active-low) to 0** ("a command
is always complete"), so every poll succeeded instantly and `$fc04cc: jsr (A0)`
re-executed the still-valid `$1234` boot sector in `_dskbufp` every iteration.
The boot sector's own `move.w #$ff,d7` clobbered the ROM loop's
`add.b #$20,d7 / bne` counter, so the loop never terminated. (A plain TOS boot
survived only because its buffer didn't checksum to `$1234`; this crack's does.)

**Fix** (`MMU` `fdcIrq` / `FdcTick`): GPIP bit 5 idle-high, re-raises INTRQ on a
coarse bucketed delay after a command (immediate for a Read/Write Sector that
moved data, ~4000 steps Seek/Step, ~40000+ Restore / failed search / Read
Address). The self-test's first polled command is a Restore, so it times out and
the loop exits. Diskless-boot `checkpoint.txt` re-baselined.

## Bugs 2 & 3 — the depacker derail (64th pass)

Past the cracktro, both cracks load ~1 MB of game data and hand off to an **ICE
depacker** ("Ice!" magic `$49636521`, plain-68000 at `$70880` in Replicants).
Depacking completed cleanly; execution then derailed (Replicants to `PC=$20`,
Empire to `$5a6`).

Traced instruction-by-instruction from the depacker's `rts`. The cracktro's VBL
handler at `$660` ends with `move.l #$00078000,$ffff8260.w`. That long write's
low word lands on **`$ff8262`/`$ff8263`**. This emulator's video-register region
ended at `$ff8260`, so the second word hit the generic `raise (BusError …)`
fall-through, which vectored through a cracktro table that doesn't handle bus
errors → garbage PC → vector-table-as-code crash. On a plain ST the shifter is
selected for the whole `$ff8200`–`$ff827f` page but decodes no register in
`$ff8262`–`$ff827f`; Hatari's `IoMemTable_ST`: `{ 0xff8262, 30, IoMem_VoidRead,
IoMem_VoidWrite }` "No bus errors here".

**Fix 2** (`MMU.fs`): `videoDisplayRegisterEnd` `$ff8260` → `$ff8261`
(`Video_ResShifter` is real), plus a new `ShifterVoid` region `$ff8262`–`$ff827f`
(reads open-bus `$ff`, writes dropped, no bus error). `videoDisplayRegisterMemory`
unchanged (98 bytes), snapshot format and diskless boot untouched.

**Fix 3** (`68k.fs` `DecodeBucket9`): with the bus error gone the depacked code
hit `suba.l (d16,PC),A5`; the hand-coded SUBA.L handler only covered
`Dn`/`An`/`#imm.L`/`(xxx).L`. Replaced the `match eamode` block with the shared
EA decoder (`x.ResolveEa` / `x.ReadEa`). Selftest +~3000 pass, wrong-answer lane
still 0.

## Bug 4 — the isometric-view setup code needs real 68000 DIVU/DIVS (67th pass)

Clicking the world-map scroll icon loads the mission-setup overlay above `$1050`,
which does projection with `DIVU` / `DIVS`. Two `failwith`s in `68k.fs`
`DecodeBucket8`:

- **Quotient overflow** was `failwith`. On overflow the 68000 sets **V=1, C=0**
  and leaves **N, Z, X and the destination untouched**, PC advancing (no trap).
  Verified against the SingleStepTests 68000 vectors, every overflow vector
  there touches only V and C (Hatari's `setdivuflags` forces `N=1/Z=0`, a
  different chip revision). DIVS fit-check runs in `int64` so `Int32.MinValue /
  -1` is caught as overflow, not a CLR exception.
- **Divide by zero** was `failwith`. Now traps to **vector 5** with the standard
  group-2 frame via `EnterVector`, same shape as CHK/TRAPV. No zero-divisor
  vectors in the suite so selftest can't check the trap path.

Selftest after: DIVU 2494→4963, DIVS ~2500→4992, **0 wrong / 0 unimpl** for both.
30M diskless boot byte-identical.

## PM's mouse dialog state machine (67th pass RE, completed 68th)

PM's own IKBD ISR is at `$18be` (vector `$46`). It parses the `$F7`
absolute-position reply (the emulator's `$0D` interrogation answer):

| RAM addr | holds |
|----------|-------|
| `$1c48f` | `$F7` button-edge byte (`%0000dcba`: c=left-down, d=left-up) |
| `$2df92` / `$2df94` | live cursor X / Y (words) |
| `$2df8e` | cursor position **latched at the click** (long) |
| `$2df96` | **left-click pending** flag, set 1 on left-down, cleared by whichever dialog consumes the click |
| `$2df9c` / `$2df98` / `$2df9e` | left level / right pending / right level |

VBL handler `$1270` dispatches on `$1c48f` through a jump table at `$12ac`
(index = `button_byte * 2`): button `4` (left-down) → `$1330`, which sets
`$2df96=1` and latches `$2df8e`.

### The briefing dialog hit-test (`$7298`), decoded

`$7298` runs when `$2df96 != 0`. It loads D0=X, D1=Y from the latched click and
walks the four 8-byte entries of the dialog descriptor at `$7a36`:

| entry word | meaning |
|------------|---------|
| word 0 (`D2`) | offset from `$7a36` to this panel's `{widthCells:b, heightCells:b}` pair + its cell grid; `0` = inactive |
| word 1 (`D3`) | packed rect origin: `left = ((D3>>8) & $1f) * 16`, `top = D3 & $ff` |

The briefing has one active entry (`$7a36` = `0176 0000 …`): panel at screen
`(0,0)`, `$7a36+$176` = `{06, 20}`, so a **24×32 grid of 4×6-pixel cells** over
screen x 0-95, y 0-191. A hit computes `col = (X-left) >> 2`, `row = (Y-top) / 6`,
fetches `grid[row*24 + col]`:

- cell `>= $20` (text / button glyphs `$80`-`$87`) → handler `$7658`
- cell `$01`-`$1f` → jump table `$735e` (`$01`-`$0b` border → `$739e`
  "click-anywhere confirm"; `$10`/`$11` → `$73d4`/`$740e` population digit up/down)

```
r28 y168:  . .  80 81 81 82  . . .  10 10 10 10  . . .  80 81 81 82  . .   ($10 = population up-arrows)
r29 y174:  . .  83 4f 4b 84  . . .  30 30 30 30  . . .  83 4f 4b 84  . .   ("OK" text, "0000" digits)
r30 y180:  . .  85 86 86 87  . . .  11 11 11 11  . . .  85 86 86 87  . .   ($11 = population down-arrows)
```

`$7658` re-walks from the clicked cell to the enclosing `$80` cell, gets its grid
offset in D3 (left OK = `$2a3`, right OK = `$2b1`), plays a click sound, then
jumps through a **per-dialog** table: `D0 = word[$76fa + $7a3c]`,
`jmp $76fe + D0`. `$7a3c` is the dialog id; the briefing's is `$0a`, and
`word[$7704] = $0186` → `jmp $7884`:

```
$7884  cmpi.w #$2a3,D3 ; beq $7890     ; left OK
$788a  cmpi.w #$2b1,D3 ; bne $7896     ; right OK
$7890  jsr $b814
```

`$b814` parses the population digit string, then **unconditionally** (the crack
nopped the "must enter a value" check at `$b842`: `moveq #0,D0 / nop / bne`)
writes `population + $2c` to `$14e4e` (the gate `$739e` and `$7774` test), copies
the game-state seed table `$584c4` → `$580a0`, `jsr $13b9a` (world generation /
`$10d1e` load path), and `move.w #$1,$1c48a` to advance the state machine. One
frame later PM composites the isometric view.

The 67th-pass "no click accepted" was two mistakes: click positions outside the
`(0,0)`-anchored grid, and reading the per-dialog OK table with the base four
bytes low so `$7a3c=$0a` looked like it routed to a handler that ignores OK.

## How far it runs now

1. Boots, ALTAIR / YODA boot, FDC self-test exits, TOS `Pexec`s the game.
2. Cracktro key-wait (`cracktro.png`).
3. ~1 MB load + ICE depack, no wall.
4. **Title** + scrolling credits (`title.png`, `credits.png`).
5. Empire: on to the "Pondering over the map…" narrative screen (`empire_intro.png`).
6. Replicants: name entry (`name_entry.png`) → option menu (`menu.png`) → world
   map (`world_map.png`) → mission briefing (`briefing.png`) → **isometric battle
   view** (`iso_view.png`). The 69th pass reversed PM's in-game key handling (ISR
   `$18be`, the `$2de6c` key array, the right-shift gate at `$13762`), drove the
   camera (rotation re-projects the whole terrain — `iso_rotated.png`), and
   **closed Q2**: the renderer is profiled at both zoom extremes
   (`iso_zoom_in.png` / `iso_zoom_out.png`) in `graphics.md`. Keypad scroll and
   keypad zoom write their variables but have no effect (scroll is cursor-driven,
   keypad zoom never calls the `$fe04` geometry rebuild — the real zoom path is
   `$13f60` → `$fe04`).
7. The 70th pass reversed the **entity / commander decision loop** — the
   per-entity behaviour state machine driven once per ~2.4 Hz simulation tick by
   the iterator `$14b62` and its 75-entry mode table `$14bb4` (`ai.md`). Object
   records at `$51b66`, spatial buckets at `$47970`, group orders at `$51538`,
   nations at `$4f916`. Target selection is local: bucket-proximity contact,
   adjacent-settlement siege, and a group-order destination cell.
8. The 71st pass reversed the **strategic layer** (`strategy.md`): the
   per-commander order pipeline `$6522` (decide) → `$58016` command buffer →
   `$6a3a` (execute) → `$4b80` (stamp the group lead into mode `$10`). The
   autonomous decision (`$6522`'s `$6564` branch) is "march at the nearest enemy
   leader if strong enough and it's within a force-scaled budget" — no economy
   or build reasoning. `$d322` + `$3e06` build the per-side force totals
   `$57fba`, reduced by `$d23a` to a UI-only strength ratio `$57fce`. Mission
   1's enemy captain never issues an autonomous order in ~1000 traced ticks; the
   `$6564` path was confirmed by forcing a command slot ready.
9. The 72nd pass tightened the **scheduler** (the sim tick `$13000`
   disassembled and its cadence measured — 13 ticks / 250 VBLs ≈ 2.6 Hz,
   compute-bound; corrected the 70th/71st call-order), reclassified **combat**
   (`$5778` is contact bookkeeping, *not* a battle resolver — casualties are
   attrition via `$5c80`/`$5bd2`, projectiles via `$57f0`, and capture via
   `$1d70`; a 166-tick forced mission-1 fight produced engagement + 5 captures
   + 0 field deaths), decoded the **campaign hook** `$6762`/`$67d0`, and settled
   the **RNG** question (`$57fec` is the low bits of a tick counter — the AI is
   deterministic; `$57ff6` is a sound-only LCG). All in `strategy.md`; a
   `powermonger.sym` symbol table was added for `trace_cfg.py --names`.
10. The 73rd pass finished the **AI** deliverable: every object-record field and
    the command-slot / group-order / leader / nation / assessment / effect
    structures as C structs, the entity FSM as a state diagram, per-handler
    pseudocode for the load-bearing modes, and a re-armed 276-tick mission-1
    fight that traced the **melee casualty mechanic** for the first time.
    Combat is a **morale grind**: mode `$32` drains the enemy's morale byte 1–4
    per tick; at zero `$5590` rolls kill-vs-rout off the group's discipline
    value, which in mission 1 pins every result to **rout** — ten routs, zero
    kills, fifteen captures over the fight. It also sketched **mission setup**
    (`$13b9a` → `$10d1e`/`$2266`: "Between Pages 1-5" is procedurally generated,
    which arms the enemy command slots and explains the inert `$67d0` hook),
    ruled `$1abaa` out as the economy engine (it is sound + ambient wildlife),
    and added an **AI reconstruction** section — the whole autonomous layer as
    modern pseudocode plus what a modern version changes. `ai.md` /
    `strategy.md`.
11. The 73rd pass also finished the **rendering mechanism** (`graphics.md` had a
    profile, not the mechanism). PM's iso view is a **software heightmap-grid
    rasteriser**: `$fec6` rotates + perspective-projects the grid corners,
    `$f898` walks the grid far→near drawing **two flat, 2-line-dithered
    triangles per cell** (colour index = the terrain byte itself), and cell
    sprites (1bpp masked, `$33000` sheet) are blitted inline in the same walk so
    the painter's order is free — no mesh, no texture, no light model, no
    palette cycling (frame-diff confirmed). Frame pipeline: terrain master →
    per-present `$12ce0` copy → dirty-cell re-fill → sprite overlay → VBL buffer
    flip. A renderer-as-pseudocode reconstruction is in `graphics.md`.
12. The 74th pass opened the **economy** (`economy.md`, pass 1 of 2). PM has no
    single "economy tick"; the subsystems are diffuse. A town's manpower is
    `pm_leader.troops_reserve` / `.troops_field` (`$4e514` +6/+8) — it fills when
    soldiers walk home (entity modes `$16`/`$60`, +2/+4) and empties when a
    captain recruits (mode `$1a`); nothing grew it passively in 400M traced
    steps. Food is **sheep herded to towns**: the `$4d252` herd array, the
    `$57f68` herding-operation array, the `$4c5f4` moving markers, and the
    per-tick servicer `$4342` (a child of `$3e06`) that animates the delivery —
    but the delivery *payoff* was not observed and is pass 2's first target.
    "Invention" as the player sees it is object byte 44 (weapon grade): it drives
    melee damage (`min(grade,6)`) and projectile type, is stamped once at unit
    spawn (`6` for leads, `0` for tutorial followers), and **no routine advances
    it**. Settlements are `$4f916` (18-byte, ≤240, chained per nation, built by
    `$2fc0`). Also flagged: `$163ea` bucket-relink writes landing in the `$4f916`
    region for some dead object slots — needs verification.
13. The 75th pass closed the **economy** (`economy.md` is now complete). The
    "livestock payoff" is `+1` to one of `pm_leader.goods[0..7]` (`$4e514` +24) —
    eight per-lord counters, one for each item type (Pike, Sword, Bow, Plough,
    Boat, Pot, Catapult, Cannon), heavily throttled (`$60dc`). They are shown in
    the lord panel (`$9bae`), shuffled between a nation's lords by porter units
    (`$159de`/`$159a4`), and spent by the army-supply subsystem (`$6352`/`$638c`)
    to equip and **upgrade** field units — which is the whole of "invention":
    `if unit_tier < delivered_item: unit_tier := delivered_item`, no research
    timer. All of that is in the strategic layer that is dormant in mission 1, so
    the tutorial never exercises it. **Manpower is a completely separate ledger
    with no growth term** — strict conservation of soldiers minus a per-settlement
    upkeep drain (`$163b8`, one man per settlement per `$580a6[side].word0`
    ticks). The "periodic settlement update" turned out to be entity **mode `$7c`**
    (`$157e6`), which also runs a loyalty accumulator (`pm_leader` +14): at ≥ 600
    (army too big for the manpower base, sustained) the lord and all its
    settlements **defect** (`$550e`). `$2984` is world-build garrison spawn; the
    `$163ea` write aliasing is characterised (a corrupt object forward-link, not a
    fault in `$163ea`) and benign (`pm_settlement._w2`, which nothing reads).
14. The 76th pass is a **port precursor** (`port/`, doc + tooling only, no
    emulator change). `tools/pm_export.py` extracts the iso renderer's whole
    input set from a live RAM image into `port/assets/` (terrain heightmap +
    type + flag + control planes, the single 16-colour palette, the 2 KB dither
    table, 64 mini-sprite frames + the heading→frame table, the projection /
    zoom / rotation constants, one frame of entity state, the reference frame).
    `port/SPEC.md` writes the projection as exact fixed-point maths: rotate by
    `yaw * 1.40625 deg` (the `$13f8a` table is a plain sine table — verified),
    then `sx = x*EYE/(EYE-depth)`, `sy = (z-HORIZON)*EYE/(EYE-depth) + HORIZON`
    with `EYE=320, HORIZON=130`; the fill is a rolling-bitplane stipple (a
    modern port replaces it with a height-ramp shader). `tools/pm_render_ref.py`
    rebuilds the frame from `port/assets/` alone — the island silhouette,
    orientation and shading reproduce (proving the export is complete); the
    exact vertical calibration and the dither phase are left open (`SPEC.md` §9).
    `port/godot/` stands up a Godot 4.x + F# skeleton (F# = terrain decode +
    projection, C# = the thin node layer; the F# lib builds clean).

## Files

| file | what |
|------|------|
| `cracktro.png` | Replicants cracktro key-wait |
| `title.png` / `credits.png` | PowerMonger title, scrolling credits |
| `empire_intro.png` | Empire "Pondering over the map…" intro |
| `name_entry.png` / `menu.png` / `world_map.png` | name dialog, option menu, campaign world map (66th) |
| `briefing.png` | "Between Pages 1-5" mission briefing (67th) |
| `iso_view.png` | isometric battle view, past the briefing OK button (68th) |
| `iso_rotated.png` | iso view after ~5 keypad rotation steps (`$ff9a` $f0→$a0), 69th |
| `iso_zoom_in.png` / `iso_zoom_out.png` | iso view at zoom index 1 / 7 (69th, `$fe04` patched via `$13bbe`) |
| `graphics.md` | the graphics pipeline + measured renderer profile + camera control + zoom comparison + modern-port notes |
| `ai.md` | the entity / commander decision loop: the `$14b62` iterator, the 50-byte object record, the 75-entry `$14bb4` mode table, the spatial primitives, the mode catalogue, target selection, and the tables it reads |
| `strategy.md` | the strategic layer: the sim tick `$13000` (call order + measured cadence), the `$6522` commander AI, the `$58016` command buffer + `$51538` group-order table, the `$6a3a`/`$6b38`/`$4b80` order executor, `$d322`+`$3e06` force accounting → `$57fba` → `$57fce`, the campaign hook `$6762`/`$67d0`, the combat pipeline (`$56a6`/`$5778`/`$57f0`/`$5c80`/`$5bd2`/`$1d70`), RNG/determinism, and what fired vs didn't in mission 1 |
| `economy.md` | the economy (complete, 74th-75th): the **goods** ledger — `pm_leader.goods[0..7]` (`$4e514` +24), fed by the shepherd FSM (`$5ec6`→modes `$3e`/`$44`/`$42`→`$60dc`), circulated by porters (`$159de`/`$159a4`), spent on unit equipment tiers by the army-supply subsystem (`$6352`/`$638c` = "invention"); the **separate** manpower ledger (`$4e514` +6/+8) and its full flow table incl. the per-settlement upkeep drain (`$163b8`); the per-settlement heartbeat (mode `$7c`, `$157e6`) and the loyalty/defection accumulator (`$4e514` +14 → `$550e`); the `$4f916` settlement records + builders `$2fc0`/`$2984`; world-gen (`$10d1e` / `$ffa6` / `$4592f`); and the characterised-benign `$163ea` write aliasing |
| `powermonger.sym` | `addr<TAB>name` symbol table for `trace_cfg.py --names` (routines + data tables named across all five docs) |
| `port/` | **iso-renderer port precursor (76th pass).** `port/assets/` = every asset + constant the terrain renderer reads, extracted from a live RAM image (`tools/pm_export.py`), with `manifest.json` provenance. `port/SPEC.md` = the porting contract (coordinate systems, the `$fecc`/`$ff7c` projection with exact constants, the rolling-bitplane dither, sprites, zoom, frame pipeline). `port/godot/` = a Godot 4.x + F# skeleton (F# logic lib, C# node glue, one heightmap mesh). `tools/pm_render_ref.py` rebuilds a frame from `port/assets/` alone: the island silhouette + shading reproduce (`port/assets/reference/render_compare.png`); the exact perspective calibration + dither phase are open (`SPEC.md` §9). |
