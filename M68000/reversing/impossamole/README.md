# impossamole — booted through a Replicants crack menu into real Amazon-world gameplay

First pass. *Impossamole* — Gremlin Graphics / Core Design, 1990. The opening-description
"isometric platformer" was an unverified guess; the first gameplay screen actually reached
(`amazon_gameplay.png`, below) is a plain side-view platform scene (terraced hillside, a ruined
pillar, a walking hero sprite) with no isometric projection visible. Leave the genre unlabelled
until a room with an actual diamond/2.5D grid turns up, rather than repeating the guess.
The copy in hand is a cracked scene release: a "Replicants"-badged boot menu leading into an
"E-Motion"/"R.AL" trained-and-packed version. No `\AUTO\` folder; the disk boots directly
(executable boot sector, checksum `$1234`) into the crack's own menu code, not straight into the
game.

## The disk image

**Commercial and not committed here.** To reproduce:

```
unzip "impossamole_emotion.zip"   # -> "impossamole cr replicants - emotion cr replicants.st"
#   impossamole_emotion.zip                                    (from the mac-st-sources Dropbox folder)
#   impossamole cr replicants - emotion cr replicants.st       sha256 f7e358080d17022f03c9d7b4c86e63998164597aea73f7e4f10aafcae9a9f6f5   (819200 bytes)
```

Standard 80-track double-sided FAT12 image (BPB: 512 bytes/sector, 2 sectors/cluster, 1 reserved
sector, 112 root-dir entries, 1600 total sectors, 10 sectors/track, 2 sides — `1*80*2*10*512 =
819200`). Root directory (28 files; the BPB's own claimed `nFATs=1` byte undercounts what's
actually mastered on the disk — the real root directory only resolves if a reader assumes 2 FAT
copies, i.e. trust the disk's physical layout over the BPB field when parsing it by hand):

| file | what |
|------|------|
| `EMOTION+.PRG` | 7094 bytes, magic `$601a` — a small GEMDOS loader, part of the crack menu |
| `MINDBOMB.PRG` | 19840 bytes, magic `$601a`, only file with `attr=$20` (archive) — the crack's own loader/menu binary |
| `E_MOTION` | 309398 bytes, no extension, starts `$6000` (`bra.w`) not `$601a` — not GEMDOS-loadable by name; raw code/data the crack loads directly, likely the "E-Motion" demo/utility behind the boot menu's F2 option |
| `CHARS11.DAT`, `SPRTS22.DAT`, `SPRTS33.DAT` | font + two sprite banks |
| `BRMUDA{22,33}.DAT`, `ICELND{22,33}.DAT`, `JUNGLE{22,33}.DAT`, `MINES{22,33}.DAT`, `ORIENT{22,33}.DAT` | per-level (Bermuda / Iceland / Jungle / Mines / Orient) data pairs — the game's 5 worlds |
| `SELECT44.DAT` | world-select screen data |
| `MDATA1.DCH`…`MDATA5.DCH`, `PICTURES.DCH` | more level/graphics data |
| `MST.IMG` | 56457 bytes, likely a Degas-family picture (title/loading art) |
| `E_MOTION.PC1`, `PRES_ST.PC1` | Degas PC1-compressed pictures — crack-intro art |
| `DISK.ID` | 4 bytes, `00 ff 00 ff` — a protection-check magic value the crack's loader reads back and compares (see below) |
| `DESKTOP.INF` | GEM desktop config; defines the "REPLICANTS" menu group, no auto-run entry |

## How it was run

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1 \
  dotnet exec bin/Debug/net8.0/M68000.dll 800000 --disk-a "impossamole cr replicants - emotion cr replicants.st"
```

The boot sector prints a Replicants banner (`Cconws`) with a `=`-by-`=` loading-bar animation
(one `Bconout` per disk block probed, `Bconstat` polled for an abort key between each), then blocks
on `Crawcin`/`Bconin` at step 724388 — the boot menu itself:

```
========================================
=       THE REPLICANTS PRESENTS        =
=---------------------------------------
=  PRESS F1 FOR IMPOSSAMOLE+++          =
=--------------------------------------=
=  PRESS F2 FOR E-MOTION+(EXIT DESKTOP)=
=--------------------------------------=
=     THE REPLICANTS RULES FOREVER     =
========================================
```

**F1** (scancode `$3B` make / `$BB` break) selects the game and lands on a second, trainer, menu
(`trainer_menu.png`):

```
THE REPLICANTS PRESENTS
IMPOSSAMOLE+++
CRACKED TRAINED 'N' PACKED BY R.AL
PRESS 'T' FOR TRAINER
UNLMT LIVE, MONEY & AMMO
NGS TO: AVB & THOR, ZAE, MCA, HOWDY,...
```

Any other key (tried: Space, `$39`/`$B9`) skips the trainer and proceeds — past this point the loader
switches from its own banner code to real GEMDOS file I/O (`Fopen`/`Fread`/`Fclose`, funcs
`$3d`/`$3f`/`$3e`) to pull in the game's data files, and ~20–30M steps later reaches the real title
screen (`title_logo.png`): the IMPOSSAMOLE logo, Gremlin Graphics' hero character, and the "Core
Design" / "Gremlin" publisher logos. No instruction wall, no crash, both crack-menu keypresses and
the game's own GEMDOS-driven loading path work end to end.

**Keyboard discipline** followed the pattern from prior games (Super Sprint, Cadaver): each key is
two separate `kbd` REPL calls (make, then break) with a real `s <n>` step count between them, not
one `kbd <make> <break>` call — see CLAUDE.md.

## Past the title screen: the attract loop waits on joystick-1 fire, not on VBL

The title screen's PC spends nearly all its time in a tight busy-poll at `$1ab8a`:

```
$01ab8a: move.b $1a2e9.l,D0      ; D0 = counter value at entry
$01ab90: move.b $1a2e9.l,D1      ; poll current counter
$01ab96: cmp.b  $1ab88.l,D1
$01ab9c: blt    $1ab90
$01aba0: cmp.b  $1a2e9.l,D0      ; has it changed since entry?
$01aba6: beq    $1ab90           ; no -> keep polling
$01abaa: clr.b  $1a2e9.l         ; yes -> consume the tick, return
$01abb0: rts
```

An earlier pass read two snapshots 30M steps apart, both caught with PC inside this loop and
`$1a2e9 = $00`, and concluded the counter was stuck (never VBL-driven, or the VBL handler never
invoked). **Both wrong — proven live:**

- `$1a2e9`'s only writer is the installed VBL handler itself (`find_field_writers.py <snap> 1a2e9`:
  31 hits, exactly one `addi.b #$1,$1a2e9.l` at `$1a2c0`, everywhere else is a `clr.b`/`cmpi.b`
  reader/consumer). The handler is genuinely installed (`$70.l = $1a2c0` in both snapshots) and
  genuinely firing: `hits 500000 1a2c0 1f950` from `after_retry3.snap` landed 42 hits on the VBL
  entry — 500000/12000 (`instructionsPerFrame`) ≈ 42, i.e. once a frame, exactly as expected.
- `watch 1a2e9` over the same run shows why it still reads `$00` almost always: `WriteByte
  $1a2e9 <- $1` at step 59808001 (the VBL tick), then `WriteByte $1a2e9 <- $0` only 233 steps later
  at `$1abaa` — this **same** wait-for-next-vbl routine consuming its own tick and clearing the
  counter, by design (`$1ab88`'s threshold byte happens to be `$00`, so the first `blt` never loops;
  the routine's real wait is the second check, spinning until the VBL handler's `addi.b` changes the
  byte at all). Between ticks the routine is doing nothing but re-reading a `$00` byte for ~12000
  steps out of every ~12233-step call — so a snapshot taken at a random moment during an idle
  attract screen lands inside this narrow spin >97% of the time. Two snapshots agreeing on that is
  the expected outcome of an idle loop, not proof of a hang.
- The actual gate on progress is in the attract loop's caller (`$017ac0` onward, one of 5 copies of a
  shared per-frame template at `$b1b6`/`$17ac0`/`$17dd0`/`$18110`/`$18450` — **not all 5 are attract-
  mode animation pages**: they share the VBL-wait/render calls, but `$17dd0` turns out to be the
  world-select screen's own selection logic, not a demo page; see "Confirming a world" below): after
  each `$1ab8a` VBL wait it checks `btst #7,$1c4c1.l; bne <exit>`. `$1c4c1` is written
  from exactly one place, `$1c5ac`, inside the game's own ACIA-receive interrupt handler
  (`$1c51a`, installed at vector `$118` — this game reads raw IKBD bytes itself rather than going
  through TOS's keyboard/IKBD driver): a `$FF` header selects "joystick 1", and the next byte is
  stored verbatim as its status (bit 7 = fire, matching the standard ST joystick-report format).
- **Proven live**: from `after_retry3.snap`, `kbd ff` / `s 30` / `kbd 80` (fire down) sets
  `$1c4c1 = $80` (`watch 1c4c1` confirms the write at `$1c5ac`); stepping one more frame (~15000
  steps) moves PC out of the attract loop's `$1ab8a` spin into new code (`$1c3d0`) and, a few
  hundred thousand steps later, renders the world-select screen (`world_select.png`): IMPOSSAMOLE
  logo over five level icons — Klondike Mine, The Orient, The Amazon, Ice Land, Bermuda Triangle
  (`SELECT44.DAT` plus the `BRMUDA/ICELND/JUNGLE/MINES/ORIENT` `.DAT` pairs) — with a walking hero
  cursor sprite. A second `kbd ff`/`kbd 80` fire (after a `kbd ff`/`kbd 00` release) drew a gold
  highlight border around the Klondike Mine icon the cursor was standing on, so the same joystick-1
  packet also drives the select-screen's own input, but repeating it did not visibly proceed further
  within another 5M steps — the actual "confirm and load a world" input is not yet identified (see
  "Not yet exercised", below).

**Technique for future games:** to exercise raw-IKBD (non-GEMDOS) joystick input, use the same `kbd`
REPL command as keyboard scancodes, with the same "two separate calls with a real step gap"
discipline: `kbd <header>` (`$FE`=joystick 0, `$FF`=joystick 1) then, after a few steps, `kbd
<status>` (bit 7 = fire; bits 0-3 = direction, `find_field_writers.py` on the status address tells
you which). Confirm the target address and header byte first (`find_ram_callers.py`/
`find_field_writers.py` on the game's own ACIA-receive handler, installed at MFP vector `$118`),
rather than guessing the packet format.

## Confirming a world needs a held fire, not a pulse

The engine's per-frame body (VBL-wait, then render, then input) is a small template duplicated as 5
near-identical copies in RAM (`find_ram_callers.py <snap> 1ab8a 1abb2 1ac34` each return exactly 5
JSR sites, clustered at `$b1b6`/`$17ac0`/`$17dd0`/`$18110`/`$18450`); `hits <n> <addr>...` against
those 5 JSR sites is how to tell which copy is actually driving the current screen (`hits 200000
b1bc 17ad4 17df4 1813c 1847e` from `after_select3.snap`: all hits land on `$17df4` — the copy at
`$17dd0` runs the world-select screen).

That copy's body, read at `$17dd0`-`$17f96`, is the actual selection state machine:

- **Object 0** (the 108-byte struct at `$1a2ea`, `find_ram_callers.py`'s "shared object-update loop"
  table) is the cursor/selection object: byte `78(A0)` is the highlighted icon index (0=Klondike
  Mine … 4=Bermuda Triangle), byte `$227f3` is a "settled" flag set once the cursor's live screen
  position (`2(A0)`) matches the expected slot position looked up from a table at `$17fb6`, and
  `$bb79` is a bitmask of locked icons (live value `$10` = bit 4 set = only Bermuda Triangle locked
  in this session).
- Only on a frame where the cursor is settled *and* the highlighted icon isn't locked does the loop
  test `btst #7,$1c4c1.l` (joystick-1 fire) at `$017e9e`. On fire it sets `$bb76` to
  `index+1` and falls into `$017f96` → `jsr $1c3c8` (sound) → `jmp $b0ee`, which uses `$bb76-1` to
  index a jump table at `$2166e` and hand off to the selected world's loader — proven live, this
  chain lands PC inside TOS ROM (`$00fc1bea`, a GEMDOS call) within a few hundred thousand steps.
- **The catch**: `$1c4c1` is a raw level, not an edge-latched event — it holds whatever byte the last
  `kbd` packet wrote until the next one changes it. A press-then-release pulse shorter than one VBL
  frame (~12000-15000 steps) can land entirely between two polls of this loop and never be seen as
  "pressed" on the one frame that actually runs the `$017e9e` check. The prior handoff's press/release
  attempts used a real gap only *inside* each two-byte IKBD packet (`kbd ff` / `s 30` / `kbd 80`) with
  essentially no hold before the very next packet released it — plausible enough to draw the
  highlight (a side effect of merely being settled, independent of fire) but not to win the race
  against `$017e9e`'s poll. Holding fire down for several frames before releasing
  (`kbd ff`/`s 30`/`kbd 80`/`s 60000`/`kbd ff`/`kbd 00`) is what actually reaches the ROM call;
  a same-packet-timing pulse (`s 30` between down and up) does not, confirmed by repeating both on
  `after_select3.snap`.

Past that ROM call, PC returns to low memory and settles into another idle wait loop — but running
through the *other* template copy, `$17ac0` (backtrace return address `$17b30` confirms it), showing
a plain "IMPOSSAMOLE" logo on a blue field (`after_confirm_screen.png`) — visually distinct from
`title_logo.png` (which also has the hero sprite and publisher logos). `ATARI_TRACE_FDC=1` over
500k steps here shows **no disk activity**, so this isn't a background load-progress wait; it's an
idle animation (a counter at `$22806` counting `0..$fa` then toggling `$22805`).

**This screen is Klondike Mine's data failing to load, not an unidentified transition.** Reading
`$17ac0`'s fire path (`$017b4c`-`$017b58`) in full — the prior pass stopped at `jsr $bb7e` (the
password/cheat-word lookup, keyed off `$bb7d` which stays 0 here so nothing fires) and inferred
"nothing happens" from that call's own irrelevance, but missed the instruction right after it:
`$017b58: jmp $17c9c`, **unconditional**, taken regardless of what `$bb7e` did. `$17c9c` is the
world-select screen's own re-entry setup — it copies image data `$25000`→`$53000`, repoints the
live screen buffer (`$1a2e4`) at `$53000`, and reinitializes the cursor object at `$1a2ea` from the
per-icon table at `$17fa2` exactly the way `$17dd0`'s selection loop expects — and falls straight
into that loop's own body. **Proven live**: from `after_confirm_screen.snap`, holding fire a full
VBL frame (`kbd ff`/`s 30`/`kbd 80`/`s 60000`/`kbd ff`/`kbd 00`) drives PC to `$1c3d8` — inside the
same title→select transition routine used the first time (`$1c3d0`, see above) — and `hits 400000
b1bc 17ad4 17df4 1813c 1847e` afterwards lands all 4 hits on `$17df4`, i.e. back on the world-select
copy. The rendered frame is pixel-identical to `world_select.png` (cursor sprite absent only because
the snapshot lands mid-settle). **So firing on this screen returns you to world-select — Klondike
Mine's confirm doesn't advance into a level, it bounces.**

**A different world loads for real.** Moving the world-select cursor to The Orient/Amazon/Ice
Land/Bermuda Triangle (joystick-1 bit 3 = increment `78(A0)`, bit 2 = decrement, wrapping checked
against the `$bb79` locked mask) and confirming The Amazon (icon index 2) with the same held-fire
technique lands PC at `$3b4` — a byte-copy depacker loop (`move.b -(A2),-(A1); dbf D1,#-4`) executing
out of the low, otherwise-unused vector-table RAM — and `ATARI_TRACE_FDC=1` over the same window
shows real raw-sector activity: 30+ `FDC read` lines across tracks 0/7/8, both sides, unlike
Klondike Mine's zero disk reads. A few million steps later PC settles at `$1ab96` (the shared
VBL-wait idle body) but now driven by a **fourth, previously uncharacterized template copy**,
`$b1b6` (`hits 300000 b1bc 17ad4 17df4 1813c 1847e`: 12 hits, all on `$b1bc`), and the live screen
(`amazon_gameplay.png`) is a real level frame: hero sprite standing on a terraced, vegetation-
covered hillside next to a ruined stone pillar under a cloudy sky — not the select/logo screen
template's blue field. This confirms the earlier handoff's hypothesis: **Klondike Mine's own data
is broken/missing in this crack; the engine's confirm→load path itself works, proven by a different
world.**

## Gameplay input: same joystick-1 bit layout as world-select, gated by a per-frame busy flag

The `$b1b6` template's per-frame body calls `$c2fa` once every frame; that routine is the hero's
input/movement dispatcher, and it uses the *same* `$1c4c1` raw joystick-1 byte and bit layout the
title/select screens use (bit 7 = fire, bits 0-3 = direction) — not a different mapping as the prior
handoff guessed:

- `$00c2fa: lea $1a572.l,A0` / `tst.b 101(A0); bne $c486` — the hero's 108-byte object (base
  `$1a572`, one slot of the same shared object array `$17dd0` uses for the cursor at `$1a2ea`) has a
  busy flag at offset 101 (`$1a5d7`); **while it's set, this routine skips reading `$1c4c1` for the
  entire frame** and falls straight to the tail (render/physics only, no input). A single-frame test
  that happens to land on a busy frame reads as "input does nothing" even though the mapping is
  correct — the prior handoff's one-packet test didn't check this flag before concluding the
  direction bits didn't work.
- When not busy: `move.b $1c4c1.l,$227f5.l` caches the byte, then, indexed by the hero's state
  byte `$227f3` (0 = idle, 1 = walking, 2/4 = other in-progress moves), a jump table at `$c488`
  dispatches to a per-state handler that tests `$227f5`'s bits directly:
  - **bit 0** (`$00c49c`): up — checks a ladder-above sensor byte (`$227ea`, classified through
    `$be96`) and climbs (`$227f3 := 4`) if it reads as ladder, otherwise falls into a jump/attack
    state (`$c742`).
  - **bit 1** (`$00c4d0`): down — same shape against a ladder-below sensor (`$227eb`).
  - **bit 2** (`$00c4ee`/`$c65e`): left — sets `$227f3 := 1` (walking), and (once settled) the
    idle/walk collision routine at `$c3a6` decrements the object's position word `2(A0)`
    (`$1a574`) by 1 px/frame while three forward-sensor bytes (`$227e0`/`$227e1`/`$227e2`, via
    `$be96`) all read as walkable. Whether `2(A0)` is the hero sprite's own screen X or a
    world/camera-scroll value applied to the whole frame is not yet settled — see below.
  - **bit 3** (`$00c4fa`/`$c6d0`): right — the mirror image, incrementing `2(A0)` while
    `$227e4`/`$227e5`/`$227e6` are walkable.
  - If no direction bit is set and the hero isn't airborne, ground sensors `$227e8`/`$227e9` decide
    between staying idle (`$227f3 := 0`, `$caba`) and falling (`$227f3 := 3`, `$cb2e`).

  **Proven live** from `after_amazon_load2.snap` (busy flag `$1a5d7 = $00`, state `$227f3 = $00`,
  position `2(A0) = $0080`): `kbd ff` / `kbd 08` (bit 3, right) then 2,000,000 steps moved
  `$227f3` to `$01` then back to `$00` (a completed walk cycle) and `2(A0)` from `$0080` to `$00c0`
  (+64, i.e. 4 discrete 16px steps); `kbd ff` / `kbd 04` (bit 2, left) over the same window moved
  `2(A0)` from `$0080` to `$0076` (-10). A same-length **no-input control** run from the same
  snapshot (2,000,000 steps, no `kbd` at all) leaves both fields unchanged (`$227f3` stays `$00`,
  `2(A0)` stays `$0080`) — the state-machine proof above isolates the input as the cause, not just
  elapsed steps. `snap_render.py` on the bit-3 run against that same-length no-input control (not
  against the original 0-step frame, which would conflate input effects with ordinary per-frame
  animation) shows most of the visible terrain redrawn, and a stone pillar that was off-screen right
  in the no-input frame is now well inside the visible area on the left — a real, isolated scroll of
  the scene under held input, not background animation (the no-input control's own diff against the
  0-step frame is a single small idle-animation blob, confirming the terrain doesn't otherwise move
  on its own).

  **`2(A0)`/`4(A0)` is genuinely the hero's own on-screen pixel coordinate, not a world/camera-scroll
  value — proven live, resolving the prior handoff's open question.** Diffing the full 20-slot,
  108-byte object array (`$1a2ea`) between `test_noinput_2M.snap` and `test_dirbit3_B.snap` shows the
  hero's slot (index 6, base `$1a572`, `type=2` at offset 0) is the *only* slot whose position moves
  with the held input (`+64,+8`); every other active slot (`type=1`, e.g. the green creature prop at
  base `$1a5de`) moves the opposite way (`-44,0`) — a background/parallax shift, not the hero. The
  render dispatcher that walks this array once a frame (`$00bada`, called from the `$b1b6` gameplay
  template) runs *two* type-gated draw stubs per slot every iteration — `$1b25a` (`type==1`) and
  `$1b3ec` (`type==2`) — each falling through to its own copy of the same generic masked blitter body
  (`$1ac34`'s type-1 body has a third, older copy of this same stub cluster, used by the non-gameplay
  per-frame templates at `$17dd0` etc. for the cursor). **Proven live** (`bpc 1b47a`, the point right
  before the final `adda.w D0,A1` address install): for the hero (`A0=$1a572`), the body computes
  `D0 = 4(A0)*160 + (2(A0)&$fff0)/2` and adds it to `A1` (the screen base from `$1a2e4`) — from
  `after_amazon_load2.snap`'s `X=$80`/`Y=$90`, that's exactly `$5a40`, matching `Y*160+X/2` by hand.
  This is the *same* formula the type-1 body uses (`$1acb6`-`$1acd0`), just with different left/right
  edge-clip thresholds (type-1 clips near byte-offset 0/`$90`/`$98`; type-2 clips near 0/`$8`/`$10` on
  the left and `$78`/`$80`/`$88` on the right — a narrower on-screen window, not yet explained).
  So the hero draws through the *same* screen-space mechanism as background props; the retracted
  "hero sprite" guess from two handoffs ago was still wrong (that visible humanoid was background
  art, most likely the green creature prop, which does track the parallax shift), but not because
  the hero's own field is camera-relative — it draws at a literal screen X/Y like everything else.

  **Why no hero sprite is visible in any screenshot taken so far, corrected**: the type-2 body reads
  its own, separate sprite table from the type-1 body's `$3b600` (128 bytes/entry) — `$1b4de`-`$1b4f8`
  computes `A2 = $3b600 + $7800 + 6(A0)*384` (384 bytes/entry: 24 rows x 16 bytes, matching the
  object's own 24px height at 2 words/32px wide), i.e. a dedicated hero-sprite bank at `$42e00`.
  **Live-driven the hero into an actual walk** (`kbd ff`/`kbd 08` then ~70,000 steps — well short of a
  full ~200,000-step cycle — catches `$227f3=1`, mid-stride, with `6(A0)` reading a real non-zero
  frame index, `7` and `9` seen across two separate drives) and checked the *exact* table entry the
  live code was about to read (`bpc 1b4f8`, right before the final `adda.l D4,A2`; `A2` matched the
  hand-computed address exactly both times): **every entry checked so far — index 0, 7 and 9 — is
  128 or 384 bytes of zero**, and a raw 4000-byte scan from `$42e00` found no non-zero byte at all.
  The hero's draw call is real (confirmed live: it computes the correct screen address and, per the
  no-op-blit hypothesis, an OR-mask write of an all-zero source leaves the destination's pre-existing
  background pixels untouched — matches every rendered comparison exactly, no distinct sprite ever
  appears no matter the frame index). **This isn't a per-frame "idle selects a blank pose" behaviour
  as first guessed — the entire hero sprite bank at `$42e00` is unpopulated throughout this whole
  play session**, idle or walking alike. The `$b1b6` per-frame template's own setup code has a block
  (`$b2b8`-`$b326`) that unpacks exactly `$9600` bytes into `$42e00` via a custom unpacker (`$1c6de`)
  — matching the table's address and size closely enough to be the same resource — but whether that
  block actually runs anywhere on the path this crack takes into Amazon gameplay hasn't been checked
  live yet. Until it's confirmed to run (or found not to), the honest reading is: the hero is
  invisible throughout everything driven so far because its graphic bank was never loaded, not
  because of anything state-dependent.

  A live double-buffer alternation caught mid-investigation, now folded into "Known traps" below:
  `$1a2e4` (the screen base the draw loop targets) is not a fixed address — it reads `$70000` in both
  `test_noinput_2M.snap`/`test_dirbit3_B.snap` but `$78000` a few thousand steps into a *fresh* resume
  of `after_amazon_load2.snap`, and the shifter's own displayed base (what `snap_render.py` picks)
  flips between the two on its own cadence. A screenshot taken from the "currently displayed" buffer
  does not necessarily show what a draw call *just* computed into the other one; `snap_render.py`'s
  own header comment already warns about exactly this (see Cadaver's `ScreenBufferA/B` precedent) —
  this cost real time here re-deriving it before finding the note already applied elsewhere.

  The earlier "a single right packet produced no visible change" reading in the prior handoff was a
  false negative from not holding the packet long enough past a possibly-busy frame and not running
  far enough afterward to see the (multi-frame) walk cycle complete, not evidence the mapping differs
  from world-select's.

**`$be96`'s tile classification, proven**: `$c0d4` (called every frame right before `$c2fa`'s input
dispatch) samples up to 11 probe points around the hero's own `(2(A0),4(A0))` — offsets `+8/+8`,
`+8,+16`, `+20/+8`, `+20,+16`, `+10,+24`/`+16,+16` and `+16,+16`/`+16,+24` pairs, matching the
`$227e0`-`$227eb` sensor bytes `$c488`'s handlers already read — through `$be2c`, which converts a
world position to a raw tile-map lookup: `tile_x = ((2(A0)-$20) + $227b6) >> 3` (8px tiles, `$227b6`
the level's own horizontal scroll counter — a *different* variable from the hero's own position, and
the actual camera-scroll value the type-1 background objects' apparent `-44` shift comes from),
`tile_y = clamp((4(A0)-8)>>3, 0, 23)`, indexing a raw byte map at `$31800` (1680 columns x 24 rows,
row stride `$690` — ends around `$3b540`, just before the `$3b600` sprite-graphics table). `$be96`
then maps that raw tile-map byte through a 256-byte classification table at `$25000` to the
walkable/ladder/etc category the sensor byte actually stores. Not yet live-tested: which raw tile IDs
classify as which category (the table's actual contents), and the ladder-climb (`$c812`/`$227f3:=4`)
and jump/attack (`$c742`/`$227f3:=2`) states these sensors gate — both still read statically only.

## Known traps

- `resume <snap> repl` does **not** reattach a disk image mounted with `--disk-a` on an earlier
  cold-boot run — `diskA` lives outside `MmuSnapshot` (see `MMU.fs` `tryReadSector`'s doc comment on
  `dmaSectorCount`, the same "not in MmuSnapshot" note applies to the disk mount itself). Forgetting
  `--disk-a` on a `resume ... repl` silently drops every floppy read from that point on
  (`ATARI_TRACE_FDC=1` shows `-> no data` for every request, indistinguishable at a glance from a
  real protection/geometry failure) — cost a live pass on this workstream a wrong "the emulator
  can't read sector 11" diagnosis before the missing flag was spotted. **Always pass `--disk-a` on
  every `resume ... repl` invocation for a disk-booted game, not just the first cold boot.**
- A game-specific busy-poll "wait for next VBL and consume it" utility (see above) will read as
  "stuck" if you only sample the field it polls at rest (it's `$00` >97% of the time by
  construction) — confirm with `hits`/`watch` against the actual VBL vector target before concluding
  a counter is dead, not just a raw byte read from one or two snapshots.
- `kbd`-injected IKBD status bytes (joystick/mouse) are a raw level in RAM, not an edge-latched
  event — a press-then-release pulse timed only by the couple of `s <n>` steps between the two bytes
  of one packet can land entirely between two of the game's per-frame polls and never register as
  "pressed" on the one frame that actually checks it (see "Confirming a world needs a held fire"
  above: this cost the prior handoff a "fire doesn't confirm" false negative). Hold the pressed state
  for at least one full VBL frame (~12000-15000 steps for this game — check `instructionsPerFrame`)
  before sending the release packet, when testing whether *any* input is being read at all.
- The object-render loop's screen base (`$1a2e4`) alternates between `$70000` and `$78000` — a real
  double buffer, not a fixed address. `snap_render.py` always renders whichever one the shifter
  currently displays, which is not necessarily the one a draw call *just* wrote into a few thousand
  steps earlier in the same snapshot's history; confirm which buffer a specific write landed in
  (read `$1a2e4` live, or force-render both addresses) before concluding a computed draw target
  produced no visible pixels (see "Gameplay input" above).

## Files

| file | what |
|------|------|
| `README.md` | this file |
| `trainer_menu.png` | crack trainer-menu screen, reached via F1 from the boot menu |
| `title_logo.png` | the real game's title screen, reached by skipping the trainer |
| `world_select.png` | the world-select screen, reached by sending a joystick-1 fire packet at the title screen (see above) |
| `after_confirm_screen.png` | the plain "IMPOSSAMOLE" logo screen reached after confirming Klondike Mine — this crack's Klondike data fails to load; firing here loops back to `world_select.png` (see "Confirming a world" above) |
| `amazon_gameplay.png` | first real gameplay frame, reached by confirming The Amazon instead of Klondike Mine — hero sprite, terraced hillside, ruined pillar (see "Confirming a world" above) |
| `amazon_noinput_2M.png` | control frame: `after_amazon_load2.snap` run 2M steps with no input at all — terrain unchanged from `amazon_gameplay.png` except one small idle-animation blob (see "Gameplay input" above) |
| `amazon_walk_right.png` | the same 2M-step window as `amazon_noinput_2M.png` but with joystick-1 bit 3 (right) held throughout — pillar and terrain visibly scrolled against the control frame, proving the movement mapping drives a real scene scroll. The visible green creature in both frames is a `type=1` background prop (it shifts with the scroll), not the hero — the hero itself is proven to draw at its own screen X/Y through the same mechanism, but its entire sprite bank (`$42e00`) is unpopulated throughout this playthrough, so it paints nothing visible (see "Gameplay input" above) |

## Not yet exercised

Past the gameplay movement mapping and the object-render/tile-classification mechanisms (see above):
the ladder-climb and jump/attack states (`$227f3 := 4`/`2`) are read statically only, not yet driven
live; what the `$25000` tile-classification table's 256 entries actually map to; whether the `$b2b8`-
`$b326` unpacker block that targets `$42e00` (the hero's sprite bank, confirmed empty every time
checked) ever actually runs on the path into Amazon gameplay — live-checking this (a `bpc`/`hits` on
that block during a fresh boot-to-gameplay drive) would settle whether the hero graphic is simply not
loaded yet at this point, or never loads in this crack at all; whether any enemy/AI-controlled object
exists at all — every object seen in this single screen of the Amazon level so far is either the
hero, a static background prop, or a dormant (`type=0`) slot, no hostile behaviour has been observed
because gameplay hasn't been driven past this one screen; why Klondike Mine's own data specifically
fails to load (worth diffing its `.DAT` pair against a working world's, or checking for a disk-read
error the engine silently swallows) and whether Orient/Ice Land/Bermuda Triangle load correctly too;
sprite/tile formats beyond the collision map now proven; level data (`MDATA*.DCH`, `BRMUDA*.DAT`
etc.); and control flow / CFG extraction.
