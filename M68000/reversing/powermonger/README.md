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
15. The 77th pass **closes the projection** and **corrects the dither phase**
    (doc + tooling only; aligned re-disasm of `$fecc`/`$ff7c`/`$e3e6..$e4de`).
    The projection maths reproduces the game's own `$3f364` corner buffer
    **byte-exact** (81/81 vertices) — the 76th's "island 15-20 px low" was a bad
    diff against a live frame whose camera had drifted from the RAM snapshot
    (the consistent reference is the snapshot's back buffer `$24400`). The whole fill
    (`$e3e6`→`$e5a6`) + the 4 yaw-quadrant grid-walk handlers are disassembled.
    Exact dither phase: `A5(y) = [$ff9e] + colourByte*128 + (topY & 15)*8 +
    8*(y - topY)`; the whole span on one scanline is a single 16-px pattern
    (`long0` @ A5 = planes {0,1}, `long1` @ A5+4 = planes {2,3}) tiled
    screen-X-aligned. `dither.bin` 2 KB → 16 KB. `colourByte 0` → palette 14/15
    = how the open sea is drawn. `pm_render_ref.py`'s `dither_index()` is exact
    (exact-index 11.9 %→18.5 %).
    **`$11f82` decode corrected:** 8×11 four-bitplane, `[mask,p0,p1,p2,p3]` per
    row, opaque where mask bit 0 (not a 1bpp silhouette) — `sheet_contact.png`
    decodes as the men, 4 faction-colour blocks of 16.
16. The 78th pass **ports the quadrant-3 grid walk to a verifiable terrain
    layer** (`tools/pm_render_ref.py --ram <settled.ram>`: `$fccc` +
    `$ef62` + the **+64 px iso-window inset**, from the game's own `$3f364`
    corners). Trace findings: `$438ee` flag-plane bit 7 = **diagonal selector**,
    not a skip; `$ef62` **forces `colourByte 0x1c`** on the coast-side triangle
    (the dark front shading); `$e420` X accumulator = `2*screenX`, `$ece2`
    word-indexed → **`screen_x == corner_sx`**.
17. The 79th pass **kills the "sea fill" myth + fixes the dither phase** (doc +
    tooling only). Pixel analysis of the composed `$1c700` buffer vs the
    `$78000` master across three RAM images: they differ **only** in the island
    terrain blob (idx 6/7/11/12/13) + a few sprites — **the open sea (idx 14/15)
    is byte-identical, baked into the master**, which `$13b9a` builds once at
    mission load. There is no per-frame sea fill; the 78th's "unmapped sea fill,
    main blocker" was a misdiagnosis (`$f922`'s `jsr $11f82` frame `0x149` is the
    8×11 mini-sprite blitter, not a fill). `walk_q3` covers **96 %** of the
    game's real terrain layer. The `$e3e6` dither setup is verified byte-exact
    against the live `$f1e2` record (`[$ffa2]` = `$5c000` = doubled `$2e000`
    base, `(2·base + colourByte·256 + rowbits) >> 1` = `$2e000 + colourByte·128
    + (topY&15)·8`), but a uniform empirical `colourByte − 1`
    (`DITHER_COLOUR_BIAS`) was still needed — greens rendered one step too light;
    it lifts exact-index **65.8 % → ~78 %** (within-1 flat at ~93 %) on
    `pm78_settle` and +12-13 pts on `pm74_late` / `pm70_iso`. Still open for
    pixel-exact: `$e420`'s sub-pixel edge masks (`$ec62`/`$eca2`, the NE-edge
    diff band), the dither-phase root cause, the other 3 quadrant handlers
    (rotation). HUD glyphs, per-category sprite frame rip, minimap,
    `sprite_triggers.json` — **not started** (SPEC.md §9 3-5).
18. The 80th pass **ports the real `$e420` DDA span walker + closes the dither
    phase** (doc + tooling only). `_fixed_slope` (`$f000`) + `_dda_walk`
    (`$e420`) replace the float+`floor()`'d spans: two 16.16 edge X
    accumulators, the shorter edge bending to the far vertex at its own
    scanline; the `$ec62`/`$eca2` partial-word masks reduce exactly to
    "draw pixel x iff `ixL <= x <= ixR`". Live single-stepping `$e420` (cell
    topY 75, colour `0x26`: `A5 = 2f358 2f360 2f368 2f370 2f378 → 2f300 2f308
    2f310 2f318`) showed **`A5` wraps modulo 128 inside the colour's slot** —
    the `$e44a` roll's `addq.b #8` on `2*A5` byte-overflows at `A5&0x7f==124` —
    so the phase is `colourByte*128 + ((8*y) mod 128)`, the `topY` term
    dropping out entirely. That kills the 79th's empirical
    `DITHER_COLOUR_BIAS = -1` (it only happened to be right for 16-32 px-tall
    triangles). Exact-palette-index **78 % → 94 %** (within-1 93 % → 95 %) on
    `pm78_settle`; 93.9 % / 93.4 % on `pm74_late` / `pm70_iso`. Residual: unit
    sprites (`walk_q3` is terrain-only), the tall `0x1c` coast slopes (game
    dithers idx 1-7, port lands nearer flat), a ~1 px NE edge.
19. The 81st pass **folds the closed rasteriser into `port/godot/logic/Fill.fs`**
    (doc + tooling only — no emulator change). `port/godot/logic/Fill.fs` is a
    1:1 F# port of `pm_render_ref.py`'s `walk_q3` / `ef62_raster` /
    `_fixed_slope` / `_dda_walk` / `dither_index` — this was explicitly blocked
    on the 80th's DDA landing cleanly (no fudge or `floor()`'d span left to
    carry over). **Cross-verified byte-exact against `pm_render_ref.py`**: five
    synthetic triangles exercising every rasteriser path (general split,
    flat-top, the `$f134` reorder, the `0x1c` coast-force, the mid-vertex
    slope switch, water shimmer) plus a synthetic 9×9-corner/8×8-cell grid
    exercising both `walk_q3` diagonal-selector branches — F# and Python
    produce identical coverage counts and pixel-index hashes on every case
    (`dotnet fsi` against the same synthetic inputs; scripts not committed,
    throwaway). `Terrain.Map`'s flag-plane accessor renamed `SeaStatic` →
    `DiagonalSelector` to match the 78th's trace finding (it was still named
    for the stale "corners unmoved, skip fill" reading `Fill.fs` would have
    inherited); `SPEC.md` §2's flag-plane row corrected to match. Added a
    `Sprites.fs` decode stub (`$11f82`'s 8×11 four-bitplane frame format +
    `t_heading_frame`) so terrain and sprite compositing have a shared home;
    not wired into a blitter yet. **Not done this pass:** wiring `Fill.fs`
    into `TerrainView.cs` (a software layer into a `SubViewport`, or an
    `ArrayMesh` + shader) — Godot isn't installed in this environment, so any
    C#-side change would be unverified; left as the next step (`port/README.md`
    "Next steps"). `PmLogic.fsproj` builds clean (`dotnet build`, net8.0).

20. The 83rd pass **ports the other 3 yaw-quadrant grid-walk handlers**
    (doc + tooling + port only — no emulator change), unlocking real camera
    rotation in the live Godot view the 82nd pass wired up. `Fill.walkQ0`/
    `walkQ1`/`walkQ2` join `walkQ3` behind a new `Fill.walk` dispatcher
    (mirrors `$f97e`/`$f982`'s `((yaw+8)>>5)&6` handler select); `pm_render_ref
    .py` gets matching `walk_q0`/`walk_q1`/`walk_q2`/`walk_by_yaw`. **Found and
    fixed a stale-address bug along the way**: the 3 handlers' entry points
    were recorded as `$f98c`/`$fa98`/`$fbb2` by an earlier pass — the real
    jump table at `$f986` (`jmp 2(PC,D0.w)`, offsets `$8`/`$114`/`$22e`/`$346`)
    gives `$f98e`/`$fa9a`/`$fbb4`; the old addresses landed on the RTS of the
    *preceding* handler (or, for `$f98c`, a byte inside the table itself).
    **Trace-verified, not guessed**: rotated the live camera via the keypad-
    poke recipe to a yaw in each of q0/q1/q2's range, captured RAM, and dumped
    registers at the first `$ef62` call after resuming to the settled PC — the
    vertex assignment and colour-plane choice (type vs height) matched the
    disassembly-derived port exactly at every cell checked. **Cross-checked
    byte-exact against the F# port** on synthetic data exercising every
    CLEAR/SET branch and both comparison directions (`dotnet fsi`, same method
    as the 81st). **Re-verified live in Godot** with real GPU screenshots at
    two more yaw steps (quadrant 0 and quadrant 2), each a distinct island
    silhouette through the same `TerrainView.RenderFrame()` path; PageUp/
    PageDown now rotate the camera in the live scene. The already-documented
    residual rasteriser inaccuracy (tall coast-slope dither spread, `SPEC.md`
    §9 item 1) scores much lower against real captures at these new yaws
    (35-50% exact-index vs quadrant 3's 94%) — confirmed to be that same
    known, low-priority limitation showing up more at other camera angles,
    not a new geometry bug, via the live-trace check above.

21. The 85th pass **fixes a real right-edge clip/framing bug** (doc + tooling
    + port only — no emulator change) found while chasing the 84th's
    unexplained green-vs-black anomaly. `SPEC.md` §3 already documented that
    `$ef62`'s own `screenX <= 255` clip runs on the *raw* `$3f364` vertex,
    before the `+64` HUD-strip inset applied later via the `$e420` draw
    pointer — but `pm_render_ref.py --ram`'s scoring path baked the inset
    into the corners *before* rasterising and then applied that same `<=255`
    bound, truncating the true window's right ~64px on every score.
    `ef62_raster`/`_dda_walk` now take an `x_inset` parameter so the clip
    bound shifts with the coordinate space it's given. `TerrainView.cs` had
    the mirror bug at the opposite end of the port's pipeline — `Fill.fs`/
    `Projection.fs` stay in raw space throughout (matching `$ef62` itself),
    but the Godot blit read the buffer at `(x,y)` instead of `(x-64,y)`,
    rendering the whole terrain layer 64px too far left. Fixed the same way
    (shift at blit time) and **verified with a real GPU screenshot** at yaw
    step 11 — the island silhouette visibly shifts right by the expected
    amount. Cross-checked the two fixes are the same fix at different
    pipeline stages: a synthetic triangle straddling the raw X=255 boundary
    produces identical covered-pixel sets in raw mode and inset mode, up to
    the expected `+64` shift. **Exact-index score does not improve for
    q0/q1/q2** from this — it's a coverage fix, not an accuracy fix, and the
    newly-drawn strip is dominated by the still-open coast-slope dither
    residual — but the absolute count of correctly-matched pixels goes up for
    every capture. **Ruled out both of the 84th's candidate causes for the
    green-vs-black anomaly**: neither `$f202` nor this clip bug can be it —
    the affected cells' own vertices never approach either clip boundary in
    either direction. That anomaly's cause remains open (`SPEC.md` §9 item 1).

22. The 86th pass **proves the q0/q1/q2 terrain renderer is byte-exact** and
    reframes the "giant-blob residual" as a bad-capture artifact (doc +
    tooling only — no code change). Live single-stepped `pm83_q2c`: all
    128/128 `$ef62` calls per frame match the live game (vertices + colour),
    the dither `A5` phase is byte-exact every scanline on two traced
    triangles, the `$e420` DDA span endpoints are byte-exact every scanline
    of a traced 27-row triangle, and `_fixed_slope` + the fill's plane/tile
    model re-verify against fresh disasm. Since every rasteriser input is
    byte-exact, the port's per-triangle output equals the game's, so the
    35–50% exact-index against `pm83_q{0,1,2}c` measures the captured
    `$1c700`/`$24400` reference buffer, which for these synthetic-rotation
    captures does not match the state the frozen `$3f364` corners describe
    (`pm83_q2c`'s heuristic picks the worse buffer; it and `pm83_q1c` share a
    draw pointer but need opposite buffers). Large-error regions are
    coast/edge-shaped, not unit-shaped; ±1 errors are one frame-wide blob —
    both point at sub-step camera drift, not a triangle bug. `pm78_settle`
    (clean capture) still scores 94.4%, residual = real unit sprites. Next
    is a clean natural-rotation capture or Task 2 (sprite rip), not a 7th
    rasteriser hypothesis. Detail in `port/SPEC.md` §9 item 1.

23. The 87th pass **starts Task 2 (the sprite rip) and settles which blit path
    draws the iso-terrain entities** (doc + tooling only — no emulator or port
    code change). Live-traced one frame of `scratchpad/pm78_settle.snap`:
    **`$115e0` (`pm_draw_cell_entities`) is the iso path** — called inline per
    cell from the grid walk (`$fdbc`), after the cell's triangles, far→near, so
    painter's order is free. `$16738`→`$e6ee` is NOT it: in `pm78_settle` it
    fires only from `$165b2` (the selected-group marker — one glyph per record
    whose byte 5 == `[$57ffe]`, positioned by raw cell coord, blinking via
    `$4bb41` bit 0), plus HUD glyphs. Ripped from the RAM jump tables + a
    disasm of each prepare handler + the men-path trace: the dispatch is
    `$1162e` prepare / **`$1165c`** blit (SPEC said `$1165a`, 2 low); cat 0
    (men) blits via `$11f78`→`$11f82`, **not `$1187c`** (a melee/dying
    sub-case); position is a bilinear lerp of the 4 projected cell corners
    (`$11f1a`) by the entity's sub-cell fraction; and the frame-index formulas
    for **all of cats 0-15** (men use a **camera-yaw-relative**
    facing: `(faction−1)*16 + (((heading + [$ff9a] + 0x10) & 0xff) >> 5)*2`;
    the `+0x40` armed variant = `record[7]` bit 4). All in
    `port/assets/sprites/sprite_triggers.json`. **Four sprite sheets, all
    decoded**: `$33000` 8×11 (full 352-frame rip, was 64), `$312a0` 16×16
    (structures / siege engines), `$37c7c` 32×24 (buildings + trees). Still
    open (88th): per-category frame counts, the cat-2 offset table, the goods
    table, then the `pm_render_ref.py` + `Sprites.fs` compositing (Targets
    3–4). Detail in `port/SPEC.md` §6 / §9 item 3.

24. The 88th pass **finds that both of the 87th's "blockers" were one bug and
    composites the flag/marching-group sprites** (tooling + asset + doc +
    `Sprites.fs`; no emulator or port-runtime change). Live single-stepped
    `$115e0` from `scratchpad/pm78_settle.snap` (register probes at `$fdb2` /
    `$115f4` / `$11f88`): (a) `$115e0` walks the **`$47970` per-cell bucket
    array**, head into `adda.w D4,A3` with `A3 = $51b66` and **D4 SIGNED**, so
    scenery/animal records also live *below* `$51b66` (the 87th's stride-50
    `$51b66` scan missed them); (b) the dispatch is `word[$1162e + byte6]` with
    **`byte6` even, 0..30** — the 87th read it as `0..15` and keyed every frame
    formula (except the men's) on the wrong record byte. So the **26-record
    marching group is `byte6 == 14`** (87th "cat 7", flag/banner) and **is**
    drawn by `$115e0` → `$11bf4` → `$11f78` → `$11f82`, frame
    `record[5] + 0x13e == 0x13f`; `$11b0c` is `byte6 == 28`, never fired.
    Position (`fx = record[9]`, `fy = record[11]`, lerp of the 4 raw `$3f364`
    corners, `+0x3c`/`−8`) matches the live `$11f82` D0/D1 to ≤ 1 px.
    `pm_render_ref.py`'s entity parse is now the bucket walk; `_entity_frame`
    is re-keyed on `byte6`; `COMPOSITE_CATS = {14}` composites for real:
    `pm78_settle` **94.4 % → 94.9 %** exact-index (pm74_late 94.3→94.7,
    pm70_iso 93.8→94.3). `byte6 ∈ {4,8}` (buildings/trees, animals) parsed +
    positioned, not drawn (frame formulas incomplete). `$16738`→`$e6ee` uses
    `record[5] + blink` into `$1675a` and `record[8]` into a descriptor table
    at `$e762` — a roster/HUD path, not the terrain men. Detail in
    `port/SPEC.md` §6 / §9 item 3.

25. The 89th pass **pins the `byte6 == 4` building/tree frame formula and
    verifies the `$37c7c` sprite decode + position, all live** (tooling +
    asset + doc + `Sprites.fs`; no emulator or port-runtime change). Handler
    `$1168c` blits inline via `$12244`; frame `= (record[7] & 0x7f) + word[
    $11746 + word[$57fd0]]` (special-cases `record[7] ∈ {0x0d, 0x0e}`), table
    `$11746 = {0,3,6,9}`, `word[$57fd0] = ($58146 & 3)*2` = a per-mission
    tile-set selector (mission 1 → 4 → `+6`). Live-verified D2 at `$12288`;
    the 32 × 24 word-plane decode aligns byte-exact against `pm78_settle`'s
    `$24400` live tree pixels; the position is the `$11f1a` sub-cell lerp with
    an **address-jitter** `fx/fy` (from the record / bucket-slot / corner
    pointer values) then `$12272` `−4/−8`, byte-exact vs the live D0/D1.
    `byte6 == 8` (animal) also live-verified (D2 0x123/0x124 at `$11ab6`);
    `byte6 == 24` (territory marker, `record[7] + 0x100`, centroid) from
    disasm. `pm_render_ref.py` (`_entity_frame`/`load_ram`/`draw_entities`) and
    `Sprites.fs` (`frameForProp`/`propTileOffset`/`propJitter`/`propScreenPos`/
    `decodeFrameWord`) updated; `COMPOSITE_CATS` stays `{14}` — compositing
    `byte6 == 4` still lowers the score because `pm78_settle`'s two compose
    buffers disagree on the entity layer (`$115e0` redraws a *subset* per
    frame), not from a formula error. **Task 1 (a populated second
    reference):** established that the mission map is a pure function of the
    world RNG seed `$12c9a` + `$5809c`; mission 1's map has `byte6 ∈
    {0,2,4,8,14,16,24}` map-wide (only `{0,2,4,14}` in the default window); a
    camera poke exposes the rest but produces the 86th's giant-blob capture
    artifact. A town-dense map needs the full campaign — out of scope.
    **89th did not reach** Task 3 (minimap) or Task 4 (`Fill.fs`/
    `TerrainView.cs` wiring). Detail in `port/SPEC.md` §6 / §9 items 3-4.

26. The 90th pass **closes the HUD minimap's mapping + raster path (Task 3) and
    ports + byte-exact cross-checks the per-cell entity pass (Task 4)** (tooling
    + asset + doc + `Terrain.fs`/`Sprites.fs`/`pm_render_ref.py`/`TerrainView.cs`;
    no emulator or port-runtime behaviour change). **Task 3:** live-traced
    `pm67_ok_pre` through the briefing-OK click into `$13b9a` + a full-frame
    trace of `pm88_f1` — the minimap is **baked once into the `$78000` master by
    `$13b9a`, not per-frame** (a settled compose buffer's minimap region is
    byte-identical to the master). `$13b9a` builds a 64 × 128 byte per-cell
    source buffer at `$418ae` (≈ the terrain type plane) and `$e6ee`
    (`pm_blit_hud_sprite`) rasters it **1:1 at screen origin `(cellX+1,
    cellY+6)`** (98.8 % land/water agreement), LUT'ing the source byte to a
    palette-index elevation ramp. Ported: `pm_render_ref.draw_minimap`
    (100 % vs the master from `$418ae`, 94.5 % from the type plane) +
    `TerrainView.cs` minimap panel with a live camera-window box, verified with
    a real Godot screenshot. **Task 4:** `Sprites.fs` gains `EntityRec` /
    `EntityCtx` / `entityFrame` / `blitEntity` / `drawEntities`; a `dotnet fsi`
    harness vs a `pm_render_ref.draw_entities` import on identical synthetic
    data is **13/13 cases byte-exact** for `byte6 ∈ {0,4,8,14,24}`. Not wired
    into a live Godot frame (no object-record source in the port yet). **Still
    open:** the minimap's per-event ownership/dots overlay; per-category frame
    counts; the goods table. Detail in `port/SPEC.md` §6 / §9 item 6.

27. The 91st pass (continuation of the substrate-hardening commit `a91b311`)
    **wires the per-cell entity pass into a live Godot frame with a real record
    stream (Task 2), and refutes most of the minimap "per-event overlay"
    premise (Task 1)** (tooling + asset + doc + `Sprites.fs`/`TerrainView.cs`/
    `pm_export.py`; no emulator or port-runtime *behaviour* change → regression
    net skipped, selftest 807124/0/8 unchanged since the 67th). Baseline:
    `detcheck 500000` on `pm78_settle` clean (trace hash `$0a144adee7e92d99`).
    - **Task 2:** `pm_export.py` `export_entities` now also emits
      `entities.json → render_entities[]` (the `$47970` bucket walk, byte-exact
      vs `pm_render_ref.load_ram`) + `entity_ctx`. `Sprites.drawEntitiesArr`
      (array wrapper) is called from `TerrainView.cs` after `Fill.walk`, gated on
      the mission-1 start pose. F# output on the real 53-record stream +
      `$3f364` corners = **byte-identical to `pm_render_ref.draw_entities`,
      2881/2881 covered px** (`byte6 ∈ {0,4,6,8,14,24}`). Real Godot screenshot
      `port/assets/reference/godot_screenshot_entities_91st.png` — ~25 trees +
      the 26-record banner ring + the man on the hill.
    - **Task 1:** static-diffed the minimap sub-rect vs the `$78000` master
      across `pm78_settle`/`pm73_fight`/`pm74_late`/`pm89_pan_e` + a one-frame
      `watch` of `pm88_f1`. The master's minimap region + the `$3f86c` control
      plane are **byte-identical across all four** (no ownership change present
      → an ownership tint is unconfirmed); **the game draws no camera-viewport
      rectangle** (`TerrainView.cs`'s is a port addition); the only real
      per-frame delta is the `$11f82` selected-unit marker (`watch` PC ≈
      `$12002`) + a static top-left chrome mark, with faint idx-5 pixels at a
      lord's cell only during an event at that cell. Detail in `port/SPEC.md`
      §9 item 6.
    - **Methodology rider (3a):** an **evidence taxonomy**
      (Proven/Corroborated/Observed/Hypothesis) header added to `ai.md` and
      `port/SPEC.md` §9, with the load-bearing strong negatives in
      `ai.md`/`economy.md`/`strategy.md` re-tagged as **Observed** (bounded
      mission-1 traces, not exhaustive proofs).

28. The 92nd pass **builds the differential-test substrate (RIDER 3b) and proves
    the first PM routine against the real 68000** (2 emulator commits `f6d574f` +
    `df140df`; then tooling + doc). New emulator primitive **`callcap <addr>
    [maxSteps] [out|-] [Rn=hex ...]`** — calls a subroutine in isolation from a
    captured state (sentinel return address, IPL-masked, register presets),
    captures its full register + changed-memory delta + a per-step trace hash,
    then snapshot-restores through the 91st's verified-identity path so the REPL
    session is untouched (`detcheck` still replays byte-identically after two
    `callcap`s). Regression net for both commits: `verify 5M` PASS, 30M diskless
    boot snapshot byte-identical, selftest 807124/0/8 unchanged, build clean.
    - **Routine 1 — `$fecc` grid-corner projector: PROVEN vs the real 68000.**
      `callcap` surfaced the entry contract (`A3` = `&$13f8a` sine table; a bare
      `bsr` runs it on garbage — 158/162 corner bytes wrong). With `A3` set, the
      freshly recomputed `$3f364` is **byte-identical to the stored buffer**
      across `pm78_settle`/`pm88_f1`/`pm73_fight`/`pm74_late` — this **closes the
      "circular verification" concern** that passes 77–90 leaned on the in-RAM
      corner buffer (it *is* the projection output, reproducibly). A
      from-disassembly **integer** reconstruction (`scratchpad/pm92/proj_ref.py`
      — `$fecc` + `$fe8e` HBIAS + `$ff7c` divide, transcribed line-for-line, no
      float `sin`/`cos`, zero fudge) matches the real `$fecc` over **36 generated
      camera-cell states + 4 natural captures: 3240/3240 vertices exact**, full
      corner-buffer comparison (`scratchpad/pm92/diff_fecc.py`). Pre-registered
      falsifier (any vertex off by ≥1) / bar (100% over ≥30 states): PASS.
    - **`$14b62` (entity FSM tick), `$4342` / `$163b8` (economy servicers),
      `$fe8e` (HBIAS leaf):** `callcap`-clean and deterministic (identical trace
      hash on repeat), reconstructions deferred. **`$5590` (combat roll):** needs
      combatant-record pointers on entry — a bare call from `pm73_fight` throws
      after 1701 steps (deterministically). Per-routine entry-contract discovery
      is the gating step for each remaining differential test.
    - **Still open:** RIDER 3b routines 2–5 (full reconstruction diffs of
      `$14b62` / `$5590` / an economy servicer); RIDER 3c (14-byte group-0
      exception frame — own emulator pass); RIDER 3d (fault-corpus writeup);
      RIDER 3e (Diabolus / `geogeo28` / Ghidra); Task 1's territory-flip capture.

29. The 93rd pass (RIDER 3b routine 2, doc + tooling only — no emulator change,
    regression net skipped) **proves the dwell/upkeep core of the entity FSM
    tick `$14b62` byte-exact against the real 68000.** `$14b62` has **no entry
    contract** — it `lea`s its own base pointers (`$51b66`, `$47970`) and reads
    everything else from fixed memory, so `callcap 14b62` runs the whole
    iterator over all 511 records and returns cleanly (4554 steps, identical
    trace hash + 84-byte delta on repeat). The differential test
    (`scratchpad/pm93/fsm_ref.py` + `diff_fsm.py`) disables every record not in
    a target mode (owner byte `:= 0`), so `callcap 14b62` exercises exactly the
    reconstructed subset, and compares the **full changed-memory delta** over
    the object records + `$47970` buckets + leader table.
    - **Covered, PROVEN (675/675 tracked bytes over 22 states):** the iterator
      prologue (active gate `5(A1)`, the anim-frame advance `14(A1)++` and its
      `flags` bit-4 suppression, the `D6/D7` load); **mode `$12`** `$14ff8`
      (halt/cool-down — integrate `(step_x,step_y)`, `subq.w #1,18(A1)`,
      `> 0` → stay, `<= 0` → `mode := $10`); the epilogue `$161c4` (word clamps,
      `$1648e` terrain veto → `mode := $0` + no write-back on water, else
      `bclr #5,7(A1)` + relink); `$1648e` terrain sample; `$163ea` position
      write-back + `$47970` bucket relink (unlink-at-head, link-at-new-head, the
      `next.prev` fix-up, old-bucket clear — all exercised by the naturals);
      **mode `$68`** `$16048` (formation follower — `$5c80`, then `clr` step +
      heading, no write-back); **mode `$8a`** `$161b2` (garrison — `$5c80`);
      **`$5c80`** upkeep (morale creep `45(A1) += $57fec & 1` toward the
      `flags`-indexed survivability cap `$5ccc`; `morale < 0` → clear).
    - **Corpus:** `pm88_f1` / `pm78_settle` / `pm74_late` / `pm73_fight` naturals
      + poked variants driving each branch (dwell → mode flip, world-Y negative →
      water veto, forced anim trigger ± the freeze bit, morale below/at/under
      the cap, single-record isolation). Pre-registered falsifier (any tracked
      byte differing in any state) / bar (100% over ≥ 20 states): **PASS**. The
      `$5c80` wear/removal path (`$5bd2`) is asserted **OFF** — `anim_wear`
      maxes at 44 (`< $3c`) across all four captures — and is explicitly out of
      scope.
    - **Deferred (recorded, not covered):** the movement modes
      `$0e`/`$10`/`$06`/`$08`/`$48`/`$4a`, all combat (`$28`/`$2e`/`$32` →
      `$1533c`/`$5590`), the regroup/group modes (`$1a`/`$1c`/`$56`/`$5a`/`$5c`/
      `$60`), shepherd/porter (`$42`/`$46`/`$52`/`$54`), the dying-entity path
      `$1623c`, and `$5bd2`. Each needs its own leaf reconstruction
      (`$164bc` DIVU step-toward, `$14262` heading, `$12d56` rotate, the
      `$168ee` patrol spline).

30. The 94th pass (RIDER 3b routine 2 cont., doc + tooling only — no emulator
    change, regression net skipped) **proves the four movement modes of the
    entity FSM tick `$14b62` byte-exact against the real 68000.** Same
    isolate-by-disabling differential test as the 93rd
    (`scratchpad/pm94/fsm_ref.py` + `diff_fsm.py`), extended with the movement
    handlers and their leaves, all transcribed line-for-line from raw-byte-
    verified disassembly + the lookup tables (`tbl_heading_14360.bin` 2048 B,
    `tbl_trig_13f8a.bin`, `tbl_spline_168ee.bin`).
    - **Covered, PROVEN (1335/1335 tracked bytes over 32 states):**
      **mode `$06`** `$14d32` (walk until blocked — step, terrain, `dwell--` →
      `mode $08`, water → `mode $0` no write-back); **mode `$08`** `$14d7c`
      (escort/orbit — `$12d56`-rotate the orbit offset by the lead's heading,
      `$164bc`, arrival snap, then fall into the `$14d32` / `$14cfa` body);
      **mode `$0e`** `$14e70` (patrol — integrate, at dwell 0 advance the
      `$168ee` spline: recompute step `(nextpt−seg)>>3` + heading; the `$7d01`
      loop / `$7d02+n` jump-to-mode / `$7d00` end terminators); **mode `$10`**
      `$14f08` (advance / chase — `$164bc` step, `prev_mode $2e` chase tracking
      a live entity's position, dead-target → `$2c`, `dbeq` probe ahead →
      `$4a`, reached → snap onto target, else `mode := $12` + run the `$14ff8`
      body); the leaves **`$164bc`** (4-quadrant `divu`-steer + swap-dance;
      `dwell := count>>1`; `beq` = reached; `divu #0` → vector-5 trap → PM's
      handler resumes op-unchanged → a valid "reached"), **`$14262`**
      (shift-table octant fold → `dir_tbl`), **`$12d56`** (Q15 sin/cos rotate,
      same trig table as `$fecc`); the epilogue **`$16202`** (`$161c4`'s clamp
      minus the terrain veto).
    - **Corpus:** `pm73_fight`'s 26 `$06` + 5 `$08` + 4 `$0e` records, the `$10`
      records of all four captures (reached / not-reached / probe / the
      `divu #0` edge `pm74_late` slot 7), plus poked variants: `$0e` spline
      advance + all three terminators, `$10` chase + `$2c` conversion, `$06`
      dwell → `mode $08`. Pre-registered falsifier / bar (100 % over ≥ 20
      states): **PASS**. Negative controls (perturb heading / rotate / the
      swap-dance) all flip the result. **Asserted OFF:** the chase-reached
      `$15302` (→ `$56a6` engage) and the group-state-8 hand-off `$1518a`
      (→ `$4bc8`) — no corpus state reaches either.
    - **Still deferred:** combat (`$32` → `$1533c`/`$5590`), the economy
      servicer (`$4342`/`$163b8`), the regroup/group/shepherd modes, `$1623c`,
      `$5bd2`; RIDER 3c/3d/3e; Task 1's territory-flip capture.

31. The 95th pass (RIDER 3b routine 3, doc + tooling only — no emulator change,
    regression net skipped) **proves the combat path (mode `$32` melee) of the
    entity FSM tick `$14b62` against the real 68000.** Same isolate-by-disabling
    differential test (`scratchpad/pm95/fsm_ref.py` + `diff_fsm.py`), extended
    with `$1533c` (melee) and its leaves `$56a6` (engage), `$5590` (kill/rout
    roll) and `$30fe` — all transcribed line-for-line from raw-byte-verified
    disassembly.
    - **Corpus is a natural capture:** `pm73_fight` driven forward 10.6 M steps
      until `$1533c` first fires, snapshotted at the next frame start
      (`pm73_melee.snap`), then five more frames (`mel_g1..g5.snap`) as the
      battle escalates to 33 live mode-`$32` records — both armies in melee.
    - **Covered, PROVEN (413/413 tracked bytes over 48 states, 6 branch
      families):** `$1533c` every branch — target-loss (`5(A3) <= 0` /
      `30(A3) == $3c`) → `_melee_lost` (mode/prev `:= $2c`, epilogue `$161c4`);
      face-away `17(A3) := 17(A1) + $80`; `31(A3) != $32` → `$56a6`; the
      **morale drain `(s8(44(A1)) < 6 ? 44(A1) : 0) >> 1 + 1`** (`>= 6` is a
      hard `moveq #0`, *not* `min(44,6)` as the old docs said); mutual
      retaliation (`48(A3) := self`, `31(A3) := $32`, no epilogue);
      `morale <= 0` → `$5590` → `_melee_lost`. `$56a6`'s `$574a` leaf (skip
      `$5778`, set both mode bytes, `46(A3) := leader-entry offset`,
      `38(A3) := 2`). `$5590`'s no-lead KILL, the group-lead walk +
      `$30fe` + the `D0 == 2 → $560a` selector, the RNG-parity branch
      `($57fec + 24(A1)) & 2`, the `btst #5` KILL-force, the KILL body
      (`neg.b 5(A3)`, corpse `$c`, `dwell $a0`), and the tail
      `leader.population -= 1`.
    - Pre-registered falsifier / bar (100 % over ≥ 15 states, ≥ 1 per
      sub-branch): **PASS.** Negative control (drain `+1 → +2`) flips 66
      tracked bytes. Determinism re-checked (`detcheck 500000` clean; two
      consecutive `callcap` give byte-identical deltas).
    - **Asserted OFF** (no corpus/poked state reaches; `raise` guards it —
      these are the deferred regroup/group modes): `$5778 → $4bc8` (group
      hand-off), `$5590 → $560a → $3c08` (the true ROUT), the `$5590` tail
      calls `$2776` / `$1b8c`.
    - **Still deferred:** the economy servicer (`$4342`/`$163b8`), the
      regroup/group/shepherd modes (`$3c08`/`$4bc8`/`$2776`/`$1b8c`), `$1623c`,
      `$5bd2`, mode `$28`/`$2e` differential tests; RIDER 3c/3d/3e; Task 1's
      territory-flip capture.

32. The 96th pass (RIDER 3b routine 4, doc + tooling only — no emulator change,
    regression net skipped) **proves the settlement heartbeat (entity mode
    `$7c`) of the sim tick against the real 68000.** `scratchpad/pm96/fsm_ref.py`
    + `diff_pm96.py` extend the reconstruction with `$157e6` (the heartbeat body)
    and its leaves `$16848` (side ↔ settlement-owner reconcile) and `$163b8`
    (the `troops_reserve -= 1` manpower drain — economy.md §3a).
    - **Mode `$7c` cannot occur in mission 1.** `$157ba` routes to `$157e6` only
      when `word[$57fd0] == 0`; `$57fd0` is `g_tileset_sel = (seed & 3) * 2 = 4`
      there, and the same gate guards every instruction that writes mode `$7c`.
      No capture (pm74_late at 400M steps included) holds a `$7c` record. So
      **the whole per-settlement upkeep drain + loyalty/revolt system is dead in
      the tutorial**, and the corpus is *synthesised* (poke `$57fd0 := 0`,
      repurpose inert records into `$7c` markers on the real `$4f916` / `$4e514`
      data, isolate by disabling every other record).
    - **Covered, PROVEN (85/85 tracked bytes over 25 states, 12 branch
      families;** obj / `$4e514` / `$4f916` / `$47970` regions all compared): the
      `dwell` early-out, `$16848` (incl. the adopt-owner path), the `$580a6`
      pulse-period reload, `$163b8` (incl. the floor at 0), the construction
      timer (`nation_kind $a` → `16(settl)++`, at `$78` → `dest_cell % 10`,
      `== 7` → capital), and the loyalty accumulator — which **only moves on the
      first pulse after a `#$ff9d`-dwell park (`D5 == $ff9c`)**, not every pulse
      as the 75th pass said.
    - Pre-registered falsifier / bar (100 % over ≥ 15 states, ≥ 8 branches):
      **PASS.** Four negative controls (`$163b8` drain, `±` loyalty, dwell
      reload word) all bite. Determinism re-checked (`detcheck` clean on a poked
      state; two consecutive `callcap` byte-identical).
    - **Asserted OFF** (`raise` guards it): `$5cde` (settlement herd-op
      assessment), `$550e` (militarism revolt), `$5c2c` (owner reconcile).
    - **`$4342`** (the herd-drive servicer) is now disassembled and its
      reconstruction skeleton drafted, but **not differentially tested** — it is
      a no-op in every natural capture (all `breed`-bit-7 animals have
      `shepherd_obj == 0`; all `$4c5f4` markers have `progress == 0`) and needs
      its own synthesised-corpus pass.
    - **Corrections:** economy.md §1's `h_disband` pseudocode had the `$57fd0`
      test inverted (mission 1 *does* take the `troops_reserve += 2` path);
      §3a's loyalty accumulator was over-stated. Both fixed.
    - **Still deferred:** `$4342`, `$5cde`, the regroup/group modes
      (`$3c08`/`$4bc8`/`$2776`/`$1b8c`), `$1623c`, `$5bd2`, mode `$28`/`$2e`
      tests; RIDER 3c/3d/3e; Task 1's territory-flip capture.

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
| `port/` | **iso-renderer port precursor (76th pass).** `port/assets/` = every asset + constant the terrain renderer reads, extracted from a live RAM image (`tools/pm_export.py`), with `manifest.json` provenance. `port/SPEC.md` = the porting contract (coordinate systems, the `$fecc`/`$ff7c` projection with exact constants, the rolling-bitplane dither, sprites, zoom, frame pipeline). `port/godot/` = a Godot 4.x + F# skeleton (F# logic lib, C# node glue, one heightmap mesh). `tools/pm_render_ref.py` rebuilds a frame from `port/assets/` alone. **77th:** the projection now reproduces the game's `$3f364` corner buffer byte-exact and the dither phase is corrected (`colourByte*128 + (topY&15)*8`, rolling); the colour families match the reference, a pixel-exact fill needs the span walker ported (`SPEC.md` §9). |
