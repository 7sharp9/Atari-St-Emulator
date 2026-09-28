# impossamole — booted through a Replicants crack menu into real Amazon-world gameplay

First pass. *Impossamole* — Gremlin Graphics / Core Design, 1990. The opening-description
"isometric platformer" was an unverified guess; the first gameplay screen actually reached
(`coldboot_amazon_gameplay.png`, below) is a plain side-view platform scene (terraced hillside, a
ruined pillar) with no isometric projection visible. Leave the genre unlabelled until a room with an
actual diamond/2.5D grid turns up, rather than repeating the guess. (Passes 79-81 reported no hero
sprite visible in this emulator's own render of that scene, and framed it as a confirm→load bug in
this repo's F# core; the 82nd pass retracted that — the hero renders fine here too, matching real
Hatari exactly, from a fresh cold boot. The negative result was specific to one long-lived, reused
snapshot lineage whose own original boot (undocumented, now lost) evidently skipped a one-time
resource load early in the crack's own loading sequence — see "Real-hardware cross-check" and "Why no
hero sprite is visible" below.)
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

**Why `$b288` sometimes never runs (82nd-pass open item — largely resolved, one part still open)**:
it is not gated by keypress *timing* in the sense the 81st pass suspected (an FDC/DMA-level race). A
cold-boot bisection (varying every `kbd`/`s` gap independently, then a `hits` census on `b288` and
the surrounding block) found instead that it is gated by whether **both** crack-menu keys were sent
at all, and in the right order: F1 alone (tested holding it 0-500,000 steps, then waiting a full
35,000,000 steps with no second key) never reaches `b288` — PC parks permanently at `$00fc0732`,
TOS's own `Crawcin`/`Bconin` wait loop, exactly where "waiting on the trainer menu" should sit; a
second key alone (no F1) or no key at all behave the same. Sending the second key before F1 also
never fires it (F1 is what leaves the boot-menu screen at all, so anything sent first has nothing to
act on). Once F1 *and* a second key are both sent, in order, `$b288` fires reliably regardless of how
long either key is held or how long the gap between them is (tested F1 holds 0-500,000 steps,
F1-to-second-key gaps 100-500,000 steps, second-key holds 100-500,000 steps, all pairwise) — and
regardless of *which* second key: Space (`$39`), Return (`$1C`), and T (`$14`, "PRESS 'T' FOR
TRAINER" — the cheat-enable path, not just the plain skip) all fire it at the same step, so this
isn't a "which path through the crack" distinction either. The only timing effect found at all is
minor and cosmetic: a second-key hold under one VBL frame (~100 steps) fires `$b288` about 11,988
steps *earlier* than a many-frame hold (500,000 steps) — some poll-window artifact of press+break
landing in the same IKBD cycle or not — but it never prevents the fire either way.

**What this does not yet explain**: the old `after_select3.snap` lineage reached world-select,
confirm and gameplay just fine — it did not hang the way an incomplete keypress does above — so
whatever its lost original boot script did was not simply "F1 with no second key" or any other gap
this bisection covers; every combination that gets *past* the boot/trainer menus at all, in this
emulator, also runs `$b288`. The most likely remaining explanation is that lineage's root snapshot
was never produced by this same live-keyboard cold-boot path in the first place (a hand-edited
state, a different/older build, or a since-changed tool) rather than a reachable-but-untested keypress
timing on today's path — but that is inferred from absence, not shown directly, since the script that
made it no longer exists to compare against. Treat any future finding of "this emulator skips a
resource load" as suspect until reproduced from today's known-good cold-boot script, per "Known
traps" below, rather than re-opening this specific timing search.

**Keyboard discipline** followed the pattern from prior games (Super Sprint, Cadaver): each key is
two separate `kbd` REPL calls (make, then break) with a real `s <n>` step count between them, not
one `kbd <make> <break>` call — see CLAUDE.md.

## Program classification: hand-written 68000 assembly, not compiled C (89th pass)

The loaded game image (post-crack-unpack, read from any gameplay snapshot) has **zero `4e56` (LINK
A6) words across the entire ~260KB span this workstream has explored** (`$2000`-`$42e00`, covering
the main-loop/dispatch code at `$b000`-`$1d000` and the tables/object-array region up to the sprite
bank), against the skill's own classification heuristic (§0): a compiled-C program from this era's
Atari ST toolchains emits one `LINK A6,#n` per function with locals, hundreds to thousands across a
program this size, where a hand-assembled game typically has none at all, using a handful of fixed
global scratch variables instead of per-call stack frames — every routine read so far in this
workstream (`$00c2fa`, `$00eafa`, `$00ec50`, the whole hero dispatch/hit/death chain) bears this out,
addressing everything through absolute globals and `An`-based struct offsets, never a frame-relative
local. This settles item 9 from the 88th-pass handoff: the decompile route (§3b) does not apply here,
same as PowerMonger and Super Sprint; `disassemble.py --all` plus live `watch`/`bpc`/`callcap` proof
(§3/§5) is the only path, which is what every pass on this workstream has already been doing.

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

**Retracted below (see the real-Hatari cross-check after this section): Klondike Mine's data is not
actually broken in this crack — it's this emulator that fails to load it.** The description of what
*this emulator* does when confirming Klondike Mine (bounces to a blank logo screen, zero disk reads)
is accurate and left as-is below, but the conclusion drawn from it — "the data is broken/missing in
this crack" — was wrong. Reading
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
template's blue field. At the time this read as confirming Klondike Mine's own data is broken and
the engine's confirm→load path works fine, proven by Amazon loading. **A real-Hatari cross-check
(below) disproves the "Klondike is broken" half of that**: this emulator's specific behavior (bounce
to blank logo, zero disk reads) is real and reproducible, but it does not mean Klondike Mine's data
is actually broken in the crack — it's this emulator that fails to load it. The "Amazon loads fully
in this emulator" half still stands on its own, though real Hatari's Amazon run additionally shows a
visible hero sprite this pass's snapshot lineage never rendered (see below) — **both retracted by the
82nd pass, see immediately below.**

**Real-hardware cross-check (Hatari v2.6.1, run 2026-09-27): both "broken" readings above were
wrong — and the 82nd pass has since found the readings were not even divergent from real hardware,
just from a fresh cold boot.** Driven live in the actual Hatari emulator (not this repo's F# core)
from the same disk image, with the same crack-menu → title-fire → world-select → confirm sequence:
confirming **Klondike Mine reaches genuine gameplay** — a real mine-cavern level, HUD
(score/lives/ammo), a clearly visible hero sprite, ending in an actual "GAME OVER" death screen
(`scratchpad/impossamole/hatari_crosscheck/hatari_klondike_gameover.png`) — not the blank-logo bounce
the *stale snapshot lineage described below* had shown. Confirming **The Amazon** also shows a
clearly visible hero sprite (`hatari_crosscheck/hatari_amazon_gameplay.png`, zoomed in
`hatari_amazon_hero_zoom.png`): a small mole-themed character (grey head, red scarf, blue suit,
matching the title screen's mascot) standing in the grass. The hero's object struct in real Hatari
(`$1a572`) matches this workstream's reverse-engineered layout exactly (`type=2`, `2(A0)`/`4(A0)`
position, `6(A0)` frame index) — the addressing and struct work stands.

**Retracted (82nd pass): this was never a genuine bug in this repo's F# core.** Every claim below
about Klondike bouncing to a blank logo and about the hero's sprite bank (`$42e00`) never being
populated was measured against `after_select3.snap` and its long chain of descendants — the same
snapshot lineage nearly every pass of this workstream has reused since very early on. A fresh cold
boot run this pass (own script, not a reused snapshot) through the identical crack-menu →
title-fire → world-select → confirm sequence reaches full parity with real Hatari for *both* worlds:
Klondike Mine loads into a genuine mine-cavern level (`coldboot_klondike_gameplay.png` — same rock
texture, gallows-post and hanging lantern as `hatari_klondike_gameover.png`) and Amazon's hero sprite
renders correctly (`coldboot_amazon_gameplay.png`, zoomed in `coldboot_amazon_hero_zoom.png` — grey
head, red scarf, blue suit, pixel-for-pixel the same mascot as Hatari's). Reproduced twice,
byte-for-byte identical, from an independent cold boot each time. Directly checked against the old
lineage: resuming the long-lived `after_select3.snap` itself (upstream of any confirm/gameplay code)
and dumping `$42e00` shows it is *already* all-zero there — so the divergence from real hardware was
introduced during that lineage's own original cold boot, not by anything the confirm→load path does.
That original boot's exact keypress timing was never recorded (no `.repl` script was saved from
whichever early pass first produced it) and cannot be reconstructed; what's proven is that at least
one specific, reproducible F1/skip-trainer timing (`kbd 3b`/`s 100000`/`kbd bb`/`s 500000`/`kbd
39`/`s 500000`/`kbd b9`, from the boot-menu wait point) executes the common-resource loader
correctly, and it is likely the old lineage's boot used different-enough timing to miss it — a real
timing-sensitivity in the crack's own loading code (or in how this emulator models FDC/DMA timing)
that is now the interesting open question, not a rendering or confirm→load bug. See "Why no hero
sprite is visible" below for the mechanism, and the handoff for the new top open item.

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

  **Why no hero sprite was visible in the old snapshot-lineage screenshots, and why it renders fine
  from a fresh cold boot (corrected, 82nd pass)**: the type-2 body reads its own, separate sprite
  table from the type-1 body's `$3b600` (128 bytes/entry) — `$1b4de`-`$1b4f8` computes `A2 = $3b600 +
  $7800 + 6(A0)*384` (384 bytes/entry: 24 rows x 16 bytes, matching the object's own 24px height at 2
  words/32px wide), i.e. a dedicated hero-sprite bank at `$42e00`. Passes 79-81 checked this table
  live (`bpc 1b4f8`, right before the final `adda.l D4,A2`) from the `after_select3.snap`/
  `after_confirm_amazon.snap` lineage and consistently found it zero — 0/384 bytes at every entry
  checked, in both Klondike and Amazon, and a `watch 42e00 9600` held across that lineage's entire
  confirm→load→gameplay transition recorded zero writes there. That negative was real *for that
  lineage*: a `hits` census on the block that should populate it (`b288`-`b326`, unpacking
  `CHARS11.DAT`/`SPRTS22.DAT`/`SPRTS33.DAT` to `$24000`/`$3b600`/`$42e00` via the shared unpacker
  `$1c6de`) landed zero hits on `b288`/`b2ca`/`b328` across that whole run, and a static whole-RAM
  scan (`find_ram_callers.py`) found no caller for it either — consistent with the block never running
  at all *in that lineage*, not with a read/render bug.

  **What actually happened: `$b288` runs once, very early, before any of that lineage's snapshots
  were ever taken — but it didn't run during whichever original boot produced `after_select3.snap`.**
  A fresh cold boot this pass (`kbd 3b`/`s 100000`/`kbd bb`/`s 500000`/`kbd 39`/`s 500000`/`kbd b9`
  from the boot-menu wait point, then a `hits` census run straight through to world-select) lands a
  single hit on `b288` at step 1,057,153 — inside the crack's own loading sequence, tens of millions of
  steps before the title screen even renders — with `$1c6de` firing 6 times in the following ~4M
  steps (unpacking all three common resources). Reproduced byte-for-byte across two independent cold
  boots. The live-breakpoint check (`bpc 1b4f8`) against this run's own confirm→gameplay state
  resolves the identical `A2=$00042e00` as every prior pass, but the full 384-byte dump is now real
  sprite-mask data throughout, not zero, and the on-screen result is the mole hero, clearly visible,
  rendering exactly where the object's coordinates place it (`coldboot_amazon_gameplay.png`, zoomed
  `coldboot_amazon_hero_zoom.png` — grey head, red scarf, blue suit, matching Hatari's
  `hatari_amazon_hero_zoom.png` pixel-for-pixel). Directly checked against the old lineage to confirm
  the divergence is upstream of confirm, not downstream: resuming `after_select3.snap` itself (already
  sitting at world-select, before any world is even chosen) and dumping `$42e00` shows it is *already*
  all-zero — so whatever caused `$b288` to be skipped happened during that lineage's own original cold
  boot, before world-select was ever reached. That original boot's exact keypress timing is lost (no
  `.repl` script survives from whichever early pass first produced it); the working hypothesis is that
  `$b288`'s execution is timing-sensitive to the F1/skip-trainer keypress gaps in a way not yet
  characterized — a real question worth answering on its own, but not a rendering or confirm→load bug.
  The hero's draw call itself was never broken: it always computed the right screen address and read
  the right table entry, exactly as passes 79-81 proved: the only thing missing was the data at that
  address, and that turned out to be a fact about which cold boot produced the RAM state under test, not
  about this emulator's confirm→load path.

  **The same fix applies to Klondike Mine — it was never a confirm→load bounce, either.** Passes 80-81
  found Klondike's confirm bounces straight to a blank "IMPOSSAMOLE" logo screen with zero disk reads,
  from the same `after_select3.snap` lineage. A fresh cold boot confirming Klondike Mine instead of
  Amazon (identical F1/skip-trainer prefix, so `$b288` fires at the same step) runs the per-world
  loader (`$b328`, real FDC activity), drives the `$b1b6` gameplay template (`hits` census: `b1bc`
  hits starting ~6.4M steps after confirm), and around 9M steps in renders a genuine mine-cavern level
  (`coldboot_klondike_gameplay.png`) — same rock texture, gallows-post and hanging lantern as Hatari's
  own `hatari_klondike_gameover.png`, with both the hero and what looks like a second (enemy or NPC)
  sprite on screen. Left running with no player input at all, the level ends within another few
  million steps (screen goes black, then PC moves to the shared title/select transition routine
  `$1c3d8`) — consistent with an unattended hero dying quickly to a hazard, though the exact death/
  Game-Over screen hasn't been rendered yet (see "Not yet exercised"). The old "Klondike bounces,
  zero disk reads" description was accurate for the snapshot lineage it was measured against, but that
  lineage's own early boot is now the known-bad reference, not this emulator's confirm→load path.

  A grey humanoid figure an earlier pass found and reported as "Klondike's hero rendering" in the old
  lineage does **not** survive a precise position check and should be treated as retracted: a crop
  taken exactly at the hero object's own declared coordinates (`$40`,`$90`) does not contain it — the
  figure sits roughly 20-30px further right, cut off at the edge of that crop. It's some other,
  unidentified graphical element (most likely background/tile art), not proof the hero object itself is
  drawing anything. See "Known traps" below for the general lesson.

  **Item 5 (the `$b328` block's "missing first call") is resolved, not a bug — it was a trace-window
  artifact.** A full `ATARI_TRACE_FDC=1`/`ATARI_TRACE_GEMDOS=1` trace from the *actual confirm
  keypress* (not from a downstream snapshot already past the depacker, which is what the original
  census used) shows all three of `$b328`'s straight-line calls firing, in order, for *both* Klondike
  and Amazon: target `$53000`/`$c800` (the one previously reported missing), then `$40600`/`$2800`,
  then `$4c400`/`$6c00` — each a real Fopen/Fread/Fclose triple with genuine FDC sector activity. The
  earlier census's window started at `after_confirm_amazon.snap` (PC=`$3b4`, already inside the
  depacker loop), which is *after* the first call already completed — the same class of mistake as the
  "zero disk reads" reading of Klondike above, not a second real bug. `$4c400`'s content is real,
  comparable non-garbage data in both worlds (verified across the full `$6c00`-byte extent, not a
  leading sample) — this per-world loader block is not where the actual hero-invisibility bug lives.

  **Ruled out via a full hardware-register comparison: not a stubbed/unimplemented peripheral** — this
  finding stands even after the correction above, just repointed: it confirms the *emulated hardware*
  was never the problem. Watching the *entire* `$FF8000`-`$FFFC10` I/O space across the whole
  confirm-to-gameplay run for both worlds shows an identical set of touched registers (video/palette,
  FDC, DMA address, YM2149, MFP) — no divergence at the hardware level at all. Neither world ever
  touches the Blitter register range (`$FF8A00`+, confirmed genuinely unmapped in this emulator: falls
  through to a real 68000 `BusError`, matching real STF hardware with no blitter fitted rather than
  being a silent stub — but moot here since the game never accesses it either way).

  **The static whole-RAM scan's "no caller found" result is now explained, not a mystery**: `$b288`-
  `$b326` (loads the common `CHARS11.DAT`/`SPRTS22.DAT`/`SPRTS33.DAT` resources to
  `$24000`/`$3b600`/`$42e00`) is called exactly once, from the crack's own early loading code, ~330k
  steps after the trainer-skip keypress and tens of millions of steps before the title screen —
  nowhere near either world's post-confirm snapshot, and that caller is almost certainly overwritten by
  later loads long before confirm. A whole-RAM scan of a post-confirm snapshot was always going to miss
  it; see "Why no hero sprite is visible" above for the live-traced proof it does run, from a cold boot.

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

## Past the first screen: a hazard/death-reload cycle, and jumping over it (82nd pass, item 6)

Driving from the fresh cold-boot `at_gameplay_final.snap` (the lineage above, hero sprite bank
populated) with plain held-right (`kbd ff`/`kbd 08`, no release) for the first time past the single
screen every prior pass stopped at:

- **Proven live, reproduced byte-for-byte on a second independent re-run of the identical script**
  (identical PC at all 8 one-million-step checkpoints both times): the hero walks from `2(A0)=$0080`
  to `$00c0` over the first ~2,000,000 steps, then **freezes there** — position unchanged from step
  2,000,000 through step 4,000,000 despite the input staying held throughout. At step 4,000,000 the
  hero's own struct gains a nonzero value (`$5f`) at offset `+6` (`$1a578`, a field not otherwise
  described above) that reads `$00` at every earlier checkpoint. Sometime in the following ~1,000,000
  steps the *entire* object-array region containing the hero zeroes out and PC lands at `$0000039a`,
  then `$0001c68e` — inside the same early common-resource unpacker region the initial boot-time load
  uses (see "Why `$b288` sometimes never runs" above) — i.e. the game performs a full resource reload,
  the same shape as a level-restart/retry sequence, not an ordinary screen transition.
- **The green `type=1` object at `$1a5de`, previously characterized as a fixed-rate parallax
  background prop from a single before/after diff, has genuine autonomous motion independent of the
  hero**: a same-length **16,000,000-step no-input control** (no `kbd` at all, hero stays parked at
  `$0080`) shows this object's own position still drifting (`+8,+16`) over that window even though
  nothing forced a parallax shift — proof it moves on its own timer, not only in lockstep with
  hero-driven scroll. During the held-right run its position swings much further (`$00ce` to `$0042`
  and back, `1a5de` dump) as the hero approaches, consistent with (not yet proven as) a proximity- or
  contact-reactive object rather than pure ambient animation.
- **The hazard/collision mechanism, resolved (proven from disassembly, cross-checked live) — item 1**:
  the earlier "inferred from timing+visual correlation only" framing is retracted. The mechanism is a
  generic, reusable hero-contact check, not something specific to the green object:
  - **`$00b71a` is the generic proximity/"bounding-box" test**, called `A0`=some other object,
    `A1`=hero (or any two objects — dozens of per-type handlers between `$013fe8` and `$017922`
    call it the same way). It is **not** a standard AABB-overlap test (sum of both radii); it's an
    *asymmetric single-radius* test per axis:
    ```
    if 36(A0) != 0: rts (fail)              ; A0 already locked onto a partner this frame, skip
    if 0(A1) == 0: fail                     ; A1 (hero) must be an active object
    dx = (2(A0)+8(A0)) - (2(A1)+8(A1))      ; signed gap between each object's (pos + offset-8 field)
    threshold = dx>=0 ? 12(A1) : 12(A0)     ; radius byte taken from whichever side dx points at
    if |dx| >= threshold: fail
    dy = (4(A0)+10(A0)) - (4(A1)+10(A1))    ; same shape on Y, offsets 10/13 instead of 8/12
    threshold = dy>=0 ? 13(A1) : 13(A0)
    if |dy| >= threshold: fail
    on success: 36(A0):=A1, 36(A1):=A0 (mutual lock), and each object's own 16/18/20/21 word/word/
    byte/byte fields (velocity/facing) are copied into its own 40/42/44/45 (a cached pre-contact
    velocity snapshot, zeroed instead if that object's own byte 100 is set) — success is signalled
    to the caller via CCR (`move #$4,CCR`, i.e. Z set); the fail path's `rts` leaves Z clear, so
    every caller reads the test with a plain `bne <fail-label>` immediately after the `jsr`.
    ```
  - **`$00e80e` is the hero-damage application, called after `$b71a` succeeds**: `A0` = the other
    (hazard/enemy) object, `A1` implicitly `$1a572` (hero, hardcoded via `lea $1a572,A1`). It
    immediately clears both `36(A0)`/`36(A1)` locks `$b71a` just set (this caller is one-shot, not
    frame-persistent), skips if the hero's own hit-cooldown byte `102(A1)` (`$1a5d8`) is still
    counting down, then does the actual damage transfer: `move.b 104(A0),$227f6.l` — **copies the
    *contacting object's own* per-type damage value (its struct offset `+104`) into the global
    pending-damage cell `$227f6`**. Live-checked: the green `type=1` object at `$1a5de` has
    `104(A0) = $1a5de+104 = $1a646 = 1` (one contact = 1 damage point).
  - **`$00eafa` (called once per frame from the `$b1b6` gameplay template, right after `$c0d4`'s
    sensor sample) applies the pending damage to the hero's health, `$bb74`**: gated the same way as
    `$c2fa`'s input read (skips entirely while the hero's busy flag `101(A0)` is set), it also has its
    *own* ground-hazard path independent of `$e80e`/object contact — reading the same forward-ground
    sensor bytes `$227e8`/`$227e9` through `$be96`'s tile-classifier and treating tile category `$9`
    as a second hazard source (`cmp.b #$9,D0; beq $eba2`). Either source (a category-9 tile, or a
    nonzero `$227f6` from an object contact) leads to the same hit-reaction: play a sound effect
    (`jsr $1c840` with D0=`$9`/`$a`/`$21`), arm the hit-cooldown (`102(A0):=3` or `7`), subtract the
    damage from `$bb74`, and if `$bb74` drops to ≤0, jump to the death handler `$ec50`; otherwise set
    `$227f3:=2` (the same "jump/hit-reaction" state `$c488`'s dispatcher uses for airborne moves) and
    a knockback-direction byte (`$227f4`) away from whichever way the hero was facing.
  - **`$00ec50` is the death/respawn handler**: if a "continue" flag `$bb78` is set, it clears the
    flag, flashes the screen (`bsr $fd8e`), and **respawns in place with half health** (`$bb74 :=
    $bb75 >> 1`, `$bb75` being a fixed max-health constant, `$18` = 18 in this run) — no reload. If
    `$bb78` is clear (the case exercised by this run), it zeroes `$bb74`, sets the hero's busy flag
    `101(A0):=1` (disabling `$c2fa`'s input read, matching the observed freeze) and installs a
    death-animation descriptor pointer at `22(A0)` (`$21892`, or `$218a0` if the hero was left-facing).
    **Not yet identified**: the routine that, once that death animation finishes, actually triggers
    the full resource reload through `$1c6de` observed at PC `$0000039a`→`$0001c68e` — `$ec50` itself
    only starts the animation, it doesn't reload anything directly. This remains open (see item 3
    below).
  - **Live cross-check, from the `right_hold_fine.txt` checkpoints** (`gameplay_explore/step2M.snap`
    .. `step5M.snap`): `$bb74` reads `$09` at step 2,000,000, `$05` at step 3,000,000, `$00` at step
    4,000,000 (the same checkpoint the `+6` field `$1a578` turns nonzero — part of the death-anim
    descriptor `$ec50` installs, not itself a distinct mechanism), and the whole object array is
    zeroed with PC inside the unpacker by step 5,000,000 — health hitting zero and the reload
    coincide exactly as the mechanism above predicts. The hero's own hit-cooldown byte `$1a5d8`
    (`102(A0)`) is never idle for long across these checkpoints (`$05`/`$07`/`$01`/`$02`), i.e. it is
    being continually re-armed — proof the hero is taking repeated hits during the "freeze", not
    stuck for an unrelated reason. A direct `callcap eafa` at a `102(A0)==0` moment (`step3M.snap` +
    20,000 steps) returned a clean 0-byte no-op with `regdelta A0` only, matching the busy-flag gate
    (`101(A0)` was set at that instant) rather than the damage-application branch — a negative result
    consistent with, not contradicting, the mechanism (busy-gated frames are common; catching the
    exact damage-application step needs finer-grained stepping than attempted this pass, see item 1b
    below).
  - **Item 1b resolved: `callcap eafa` pinned directly on the damage-application branch.** Scanning
    20 consecutive per-frame arrivals at `$eafa` (`bpc eafa 1` repeated, dumping `102(A0)`/`$227f6`/
    `$bb74` at each) from `step3M.snap` shows the exact frame-by-frame shape: a contact sets
    `$227f6=1` while `102(A0)=0` (hit 2 of the scan); the *next* `eafa` call (hit 3) is where health
    actually drops (`$bb74` `$05`→`$04`) and the cooldown arms to `7`; cooldown then ticks down one
    per frame for 7 frames (`6,5,4,3,2,1,0`) before the next contact (hit 13) repeats the cycle. Firing
    `callcap eafa` from the primed state at hit 13 (`102(A0)=0`, `$227f6=1`, `$bb74=4`) gives the
    direct memory delta: `mem $00bb74 $04->$03`, `mem $01a5d8 $00->$07` (cooldown armed), `mem
    $0227f6 $01->$00` (pending damage consumed), plus a HUD/status-bar redraw on both screen buffers
    (`$070xxx`/`$078xxx`) — the hit-reaction visibly updates an on-screen indicator, not identified
    further. This is the direct, non-inferred proof of the damage-application branch the mechanism
    above predicted from static disassembly alone.
  - **Item 3 resolved: the reload is a genuine death → Game Over transition, not a per-level retry.**
    `$eafa`'s call site in the `$b1b6` per-frame template is `jsr $eafa` / `bcs $b058` — `$ec50`
    (entered from `eafa` when `$bb74` hits zero) returns with the carry flag set, so the *very next*
    instruction in the frame template branches straight to `$00b058`, the same target `$df4a`'s
    parallel `bcs` reaches. `$b058` tears down the gameplay template (`$1c3c8`, `$22784`, `$1ab5a`/
    `$1ab6e`, `$1f972`), calls `$b2d8` (which re-unpacks `$53000`/`$fa00` and `$4c400`/`$5000` via the
    shared `$1c6de` depacker — the same "resource reload" symptom seen as the object array zeroing
    and PC transiting `$1c6de`), then `jmp $17fe8`. `$17fe8` prints text and builds a 3-entry object
    array (the same generic object-init shape `$17dd0`/world-select's cursor setup uses) — **live
    render, not just code-shape inference, confirms this is the actual Game Over screen**: resuming
    the reload 10,000,000 steps past `step5M.snap` and rendering shows a tombstone graphic and the
    text `GAME OVER` / `YOUR SCORE 000000` / `FINAL SCENE THE AMAZON`
    (`coldboot_amazon_game_over.png`). So: ground-truth confirmed as death → Game Over, structurally
    the same *outcome* as Klondike's unattended death (documented above as reaching `$1c3d8`), but
    reached through a different code path (`$b058`/`$b2d8`/`$17fe8`) — the two deaths were never
    proven to funnel through the identical `$1c3d8` address, only to the same category of screen.
  - **The `$25000` classification table is now fully mapped (83rd pass), read directly out of RAM
    rather than probed tile-by-tile**: `$00be96` (`lea $25000,A0; andi.w #$ff,D0; move.b
    0(A0,D0.w),D0`) confirms the table is a flat 256-byte array indexed by the raw tile ID (masked to
    8 bits), one category byte per ID — dumping all 256 entries from `ru_step8M.snap` gives exactly
    six distinct category values: `$0` (138 entries, the large majority — off-map/background, never
    walked on), `$4` (79 entries, walkable, matching the two IDs already confirmed underfoot), `$9`
    (6 entries: IDs `$4f`-`$52` and `$f6`-`$f7` — every ground-hazard ID, not just the two seen live),
    and three still-uncharacterized categories `$1`/`$2`/`$3` (10/10/13 entries respectively) that
    `$be96`'s callers never compare against — only `$4` (walkable/climbable-adjacent) and `$9`
    (hazard) gate any code path found so far, so `$1`/`$2`/`$3` may be inert or feed a not-yet-found
    caller. This resolves the "map the rest of the table" open item outright; what remains open is
    only the semantic identity of `$1`/`$2`/`$3` (e.g. ladder vs. water vs. decoration), not the
    table's contents.
  - **The HUD/status-bar routine is identified: `$00fdc4`, a health-pip bar renderer**, called from
    every hit/death/respawn branch in `$eafa`/`$ec50` right after `$bb74` changes. It builds a
    17-character tile string in a scratch buffer at `$fe74` (initialised to blank tile `$20`,
    terminated `$ff`): `$bb74/2` "full pip" tiles (byte pulled from a 2-entry template at `$fe86`,
    plus one more if `$bb74` is odd — the half-pip case) followed by `($bb75-$bb74)/2` "empty pip"
    tiles (`$07`), where `$bb75` is the max-health constant. It then blits that string via the shared
    tile-string drawer `$1c0aa` (font base `$24000`, column `$13`, row `$0`) to *both* screen buffers
    (`$70000` and `$78000`) in turn — exactly the double write the `callcap eafa` memory delta showed.
    So the on-screen indicator the hit-reaction updates is the health bar itself, not a separate
    lives counter (`M68000/reversing/impossamole/coldboot_amazon_gameplay.png`'s top-left pip row).
- **Holding right *and* up together (`kbd 09`, bits 3+0) instead of right alone avoids the reload
  entirely** — proven live: the hero's Y oscillates (a jump arc, `$0090`→`$0080`→`$0074`) while X
  holds near `$00c0`-`$00c2`, and PC never leaves normal gameplay code through the same step counts
  that reset the plain-right run. The screen genuinely scrolls into terrain never seen in this
  workstream before: at 4,000,000 steps a ladder/tree structure and a row of ground spikes appear on
  the right (`coldboot_amazon_jump_ladder.png`); continuing to 8,000,000 steps reveals tribal
  totem-pole decorations, a water pool, and more spikes, with the hero (struct still `type=2`, alive)
  standing on a ledge at the far side (`coldboot_amazon_jump_totems.png`). This is the first time any
  pass has driven this game past its single starting screen.
- **Continuing the same held right+up another 8,000,000 steps (83rd pass) reaches a second, distinct
  screen and a second death** (`gameplay_explore/ru_continue.txt`, `ru_step12M.snap`). At 4,000,000
  steps further (12,000,000 total from `at_gameplay_final.snap`) the scene has scrolled into a
  twin-tree/hanging-vine area with a totem-and-ladder structure on the right, and a second `type=2`
  slot has appeared (object-array index 8, base `$1a64a`, `x=$24`, `y=$90`) — proof that `type=2`
  denotes a shared rendering/behaviour class (hero *and* enemy animated characters use the same draw
  body `$1b3ec`, not "the hero" specifically; this generalises the observation the README already made
  about `type=1` background props). Holding right+up straight through the screen (no dodge) reproduces
  the same death→reload cycle documented above: health `$bb74` drops `3→2→1→0` over the following
  ~2,900,000 steps (three separate hits, not one continuous drop — re-measured precisely this pass by
  checkpointing every 200,000-500,000 steps, correcting the original "~2,500,000/one drop" estimate)
  while the hero's Y climbs from `$28` to `$70`+ (falling into or through terrain near the new object),
  then PC lands back inside the shared `$1c6de` depacker (confirmed at `$0001882e`, mid-unpack-loop
  `move.b D3,(A1)+`/`subq.l #1,D0`/`bne`), the same signature as the first death. **A same-position
  retry with the fire button held throughout (`kbd 89`, bits 0+3+7) does not avoid this death**
  (`ru12_fire_probe.txt`) — a *held* fire byte only fires once (rising-edge detected), so this was
  never a sustained-fire test.
  - **Correction (84th pass): the `$1a64a` type=2 slot was never actually the thing dealing the
    damage above — a live breakpoint on the exact `$e80e` write site pins the real culprit as a
    different, static `type=1` prop.** The original write above inferred the new type=2 object was
    the hazard from screen-area proximity alone (the same "sprite in roughly the right area" trap
    CLAUDE.md already warns about from the 81st pass). Re-running the straight-through drive with
    `bpc e82e 1` (the `move.b 104(A0),$227f6.l` instruction inside `$e80e`) catches the actual first
    hit at step 1,596,247 past `ru_step12M.snap` with `A0=$0001a722` — object-array slot 10, `type=1`,
    static (`+8`/`+10` offsets both `0`, matching the existing `type=1` background-prop convention,
    not the moving `type=2` characters), at `x=190,y=151` with radius bytes `12(A0)=13(A0)=14(A0)=
    $10`, damage field `104(A0)=1`. At that instant the hero (`x=196,y=128`, `+8=8`) gives
    `dx=(190+0)-(196+8)=-14` (within hero's own `12(A1)=$10=16` threshold) and
    `dy=(151+0)-(128+0)=23` (within hero's `13(A1)=$18=24` threshold) — both axes inside range,
    exactly reproducing the `$b71a` proximity test the mechanism above already proves, just with a
    different, previously-unexamined slot as `A0`. The `$1a64a` type=2 object may still be a hazard in
    its own right (its `+104` damage field does read `1`), but nothing in this pass's data shows it
    ever being the one in contact — it should be treated as unconfirmed, not as the screen's hazard,
    until its own slot is caught the same way.
  - **Dropping "right" and holding up-only delays the hits but does not avoid them, and the hero never
    reaches the ladder-climb state either way (84th pass, bears on item 6).** From `ru_step12M.snap`,
    `kbd ff`/`kbd 01` (bit 0, up only, no right) takes two hits (health `3→2→1`) over 4,800,000 steps —
    slower than the right+up run's three hits to death by ~2,900,000, but not a fix. In both runs
    `$227f3` (the hero's movement state) stays at `2` (jump/attack) throughout every checkpoint taken;
    it never reaches `4`, the ladder-climb state `$00c49c`'s up-handler sets when its ladder-above
    sensor (`$227ea`) classifies the tile above as climbable. So neither input combination ever gets
    read as "there is a ladder here" at any point tested — the on-screen "totem-and-ladder structure"
    is not proven climbable from this resume point/approach; item 6 needs a different horizontal
    position (aligned to the ladder's own tile column) before `$227ea` will plausibly classify as
    ladder, not just an up-heavy hold from here.
  - **A dodge that survives the crossing is proven (85th pass), though the screen isn't cleared
    yet.** From `ru_step12M.snap`, held right+up up to the point the hero's own state (`$227f3`)
    transitions from `2` (jump/attack) to `3` (natural fall, first seen at `x=196,y=96`→`112` around
    step 1,400,000-1,500,000), then **switching to right-only (dropping the up bit) right at that
    transition** lets the hero fall straight through the hazard's contact band in one pass instead of
    bouncing back up into it repeatedly: exactly one hit (`3→2`, at `y=128`, matching the culprit's
    proven geometry) instead of the original run's three, and the hero lands and settles (state `0`,
    idle) at `x=192,y=144` with `2/18` health, alive (`pass85_dodge1_end.snap`,
    `coldboot_amazon_twintree_dodge_landed.png` — a green round object and a real ladder, visible on
    the left tree trunk, are both on screen from here). **The landing spot is still boxed in**: held
    right goes nowhere from there for 1,500,000 steps (forward ground sensors read non-walkable, a
    wall) and any further jump — held or a brief 30,000-step tap — arcs back up into a second contact
    band around `y=96-118` and is fatal at `2/18` health (`pass85_jump2_end.snap`,
    `pass85_shorthop_end.snap`, both die).
  - **The left-retreat lead is a dead end: the hero cannot reach the ladder from ground level here,
    and the earlier `x=142` reading was a mid-walk snapshot, not a stop (86th pass; settles with a
    proven no the open question of whether `$227ea` classifies as ladder from further left).** Holding
    left
    from `pass85_dodge1_1_5M_more.snap` does not stop at `x=142` as the 85th pass's fixed-600000-step
    snapshot suggested — that was still mid-walk (`$227f3=1`). Continuing the hold, the hero keeps
    walking left through `x=160→144→128→110→94→78` and only actually settles (state `0`, idle,
    unmoving for 2,200,000+ steps) at **`x=74,y=152`**, right against the tree trunk's own solid
    pixels (`pass86_left_settled.snap`/`.png`). The real ladder-up check at `$00c49c` reads
    `$227ea` (the tile directly above the hero's head) through `$be96` (`$25000`-table lookup) and
    only climbs (`$227f3:=4`) on category `1`/`2`; at the settled `x=74` position `$227ea`'s raw id
    (`$2b`) classifies as category `0` every time, live-confirmed by holding up for 2,700,000 steps
    (`$227f3` goes to `2`, jump/attack, and stays there — never `4` — while `y` just bobs
    `112↔120` in place and `x` never moves, `pass86_settled_up_end.snap`). The reason the hero can't
    walk further left to get under the visible ladder rungs is proven, not inferred: `$00c3a6`'s
    forward-sensor gate (`$227e0`/`$227e1`/`$227e2`, each through `$be96`, blocking on category
    `>=4`) reads `$227e2`'s raw id `$26` as category `4` at `x=74` — the tree trunk itself is the
    blocking tile, one column short of wherever the rungs' own column would put `$227ea` overhead.
    So this ground-level approach cannot reach the ladder; the zoomed screenshot
    (`pass86_left_settled_zoom.png`) shows a horizontal branch/platform jutting right from the trunk
    above the hero's head, at roughly the trunk's mid-height, that was the next visual lead — reached
    by a real controlled jump, proven the next pass (below). `pass85_dodge1_1_5M_more.snap` (the safe,
    landed, pre-retreat state, `x=192,y=144`, `2/18` health) is the resume point for anything not
    starting from the trunk-blocked spot.
  - **A real, table-driven jump exists and clears the trunk (87th pass), resolving the "no jump
    mechanism proven" gap the 86th pass left open.** `$00c742` — the jump/attack state entry the
    up-handler `$00c49c` falls into whenever `$227ea` does *not* classify as ladder — is not itself
    the per-frame jump logic; it is one-shot setup (play a sound, latch facing from `$227f5` bits
    2/3 into `$227f4`, pick a weapon/attack animation descriptor, and — if a weapon is equipped
    (`98(A0) != 0`) — fire once through `$bef4`) that falls straight into `$00cbbc`, which *is* the
    real per-frame jump handler and is what a live `hits` run actually shows executing repeatedly
    (not `$c742` itself, which only fires once per jump trigger). `$cbbc` first applies a fixed
    facing-locked horizontal push (`98(A0)`, 1-2 px/frame, snapshotted at jump entry — it does not
    re-read `$227f5` each frame, so the horizontal component of a jump is committed at takeoff and
    is unaffected by releasing or changing direction mid-air), then indexes a signed-word velocity
    table at `$cd54` with the jump's own frame counter (`82(A0)`, advanced by 1 each call) and adds
    the value straight into `4(A0)` — genuine vertical displacement, not the stationary bob the two
    static tests in the 86th pass read (those held up alone, from a resting spot with no horizontal
    component, so the arc's real shape wasn't visible against the noise of `y` bobbing at the resting
    boundary). The table's terminal sentinel (`$7fff`) forces a transition to state `3` (fall,
    `$cb2e`) if reached before landing; landing on a walkable ground sensor (`$227e8`/`$227e9`,
    category `>=2`) instead returns straight to idle (`$227f3 := 0`, `$caba`), skipping state 3
    entirely — both exits proven live, not inferred.
    **Live-confirmed from `pass86_left_settled.snap`** (`x=74,y=152`, idle, trunk-blocked): `kbd
    ff`/`kbd 09` (up+right together, bits 0+3) drives three separate jumps over 1,000,000 steps
    (`$c742` retriggers each time the hero returns to idle with up still held; `$cbbc` runs every
    frame in between) — `hits` shows `$c742` at 3 hits, `$cbbc` at 42, `$caba` (a clean landing) at
    2, `$cb2e`/`$cd84`/`$c812` all at 0. Position moves `x=74→124, y=152→108` after the first
    600,000 steps (`pass87_jump_right_600k.snap`, `coldboot_amazon_twintree_jump_midair.png` — the
    hero is visibly past the trunk, level with the fence-post/ladder structure and the green item
    beside it) and settles idle at `x=152,y=144` after a further 400,000 steps with no input held
    (`pass87_jump_right_1M_settled.snap`, `coldboot_amazon_twintree_jump_landed.png` — the hero
    stands past the trunk, at the base of that fence-post structure). A same-shape `kbd ff`/`kbd 01`
    (up-only, no right) test from
    `pass85_dodge1_1_5M_more.snap` (`x=192,y=144`) over 1,000,000 steps confirms the horizontal
    component really is direction-gated, not automatic: `x` never moves (stays `$00c0`) while `y`
    cycles `144→105→...` through three up-only bounces in place. This is the controlled jump the 86th
    pass found no evidence for. **The 88th pass read this landing spot as a soft-lock; the 89th pass
    found the real cause is a third, previously-uncatalogued hazard object the jump arc itself clips
    twice — see below.**
  - **The `pass87_jump_right_1M_settled.snap` landing spot is not a soft-lock: it is the ordinary
    hazard-death sequence, reached because the jump itself takes two fatal hits from an uncatalogued
    hazard object, and gated to only start its animation once the hero lands (89th pass, correcting
    the 88th).** The 88th pass found `$1a5d7` (`=$1a572+101`, tested by `$00c2fa`'s `tst.b 101(A0);
    bne $c486` busy-branch) reads `$01` at this landing spot and stays `$01` for ~500,000-600,000
    steps while the whole movement-dispatch chain shows zero hits, then the game reloads through the
    hazard-death fade chain (`$00b058`/`$0001c3d8`) — all still true and reproduced again this pass —
    but its "health (`$bb74`) unchanged at 18/18 the whole time" claim is wrong: a direct read of
    `pass87_jump_right_600k.snap` (600,000 steps into the *same* up+right jump that was written up as
    clearing the trunk cleanly, before the 88th pass's own observation window even starts) shows
    `$bb74 = $00` already. `$bb75` (the max-health constant) reads `$12` = 18; the 88th pass's "18/18"
    evidently came from that field, not from live health.
    A `watch $bb74` from `pass86_left_settled.snap` (`x=74,y=152`, `2/18` health) through the same
    `kbd ff`/`kbd 09` jump shows exactly two writes, both at `$00eb8c` (`sub.b D0,$bb74.l`, the
    already-proven generic contact-damage path: `$00b71a` proximity → `$00e80e` copies the contacting
    object's own `+104` field into `$227f6` → `$00eafa`'s fall-through applies it here) — the hero
    takes 1 damage twice during the jump's ascent, `2/18 → 1/18 → 0/18`, well before landing. A `bpc
    e80e` breakpoint on the same run names the contact: object base `$1a6b6` — slot 9 of the
    established 20-slot, 108-byte-stride array (`$1a2ea + N·108`; `($1a6b6-$1a2ea)/108 = 9` exactly),
    sitting numerically between the twin-tree screen's two already-documented hazards (slot 8 `$1a64a`,
    slot 10 `$1a722`) — a third member of the same hazard cluster, missed because prior passes never
    checked health during this jump, only position. Its fields match the established static-hazard
    shape: `type=1`, position `x=66,y=98`, radius bytes `12/13/14(A0) = 16/16/16`, damage `104(A0)=1`,
    velocity `+8/+10 = 0` (stationary). The hero's own arc passes from `x=74,y=152` up through
    `x=124,y=108` by the 600,000-step mark, close enough to `(66,98)` with a 16px radius to register
    two separate contacts on the way.
    With that established, `$1a5d7`'s own write is no longer a mystery: `watch 1a5d7` over the same
    run shows one write, `$00ecce: move.b #$1,101(A0)`, inside `$00ec50` — the death-animation entry,
    reached only when `$00eafa`'s own entry check (`tst.b $bb74; beq $ec50`) finds health already
    zero. `$00ec50` itself gates on the hero being grounded (`cmpi.b #$1,$227f3; bgt $ecfe`, i.e. state
    `<=1`) before it will start the animation (play a sound, pick a facing-dependent death-animation
    script pointer into `22(A0)`, set `101(A0)`), which is exactly why the "stuck" state only becomes
    visible after the hero lands — the fatal hit happens mid-jump (state `2`), but the game holds off
    entering the death animation until the state machine returns to idle. `$00eafa` is called from the
    main loop at `$00b238` (`jsr $eafa.l`), a separate call site from `$00c2fa`'s own `jsr` at
    `$00b20e` — both are gated by the same `101(A0)` flag but branch differently when it is set:
    `$00c2fa` just returns (`bne $c486`, bare `rts`), while `$00eafa` takes a different internal path
    (`bne $ed04`) that still runs every frame. Continuing past `watch_1M.snap` (busy still `$01`,
    health `$00`) another 2,000,000 steps shows `$1a5d7` clear again: `$01ab66: WriteByte $1a5d7 <-
    $0`, inside the already-documented `$b058`/`$1c3d8` reload chain, with PC ending the run at
    `$0001c686`, the same reload region the 88th pass's own force-reload landed in. So item 3 (find the
    main loop's own separate reload trigger) does not need a third `bcs $b058` exit: the whole
    sequence — mid-air hit → grounded death-animation entry → reload — is the single, already-proven
    hazard-death cycle from "Items 1, 1b, 2 and 3" below, just triggered by this newly-found slot-9
    hazard instead of the slot-8/10 pair. Exploring past the trunk needs either a jump that avoids
    `(x=66,y=98)`'s 16px radius (a lower arc, or releasing "right" earlier) or enough health margin to
    survive two more hits — `pass86_left_settled.snap`'s `2/18` was already too low for this exact jump
    to be safe.
**The fire button is a real weapon system, not decorative — proven from disassembly (83rd pass),
resolving the "type=3, never observed live" open item.** `$00c308`/`$00c31e` cache the raw joystick
byte into `$227f5` each frame and edge-detect fire specifically: `$227ef` holds the *previous*
frame's raw byte, and bit 7 of `$227f5` is cleared (`bclr #7,$227f5`) whenever `$227ef`'s own bit 7
was already set — so `$227f5`'s fire bit is true for exactly one frame per press, not for the whole
hold (this is why the held-fire death-avoidance attempt above only ever fired once). Two real
consumers of that bit exist in the gameplay code (`$00d37c`, `$00ea2c`) plus one seen but not yet
read (`$012cd8`):
- **`$00d37c`** is the primary weapon-fire handler, called from the movement-state code with
  `A0=$1a572` (hero). It fires only while grounded/walking (`$227f3 < 3`, i.e. not mid-jump/knockback)
  and only once every 6 frames (`$227fd`, set to `6` on a successful shot and presumably ticked down
  elsewhere, the same shape as the hero's own hit-cooldown `102(A0)`). On a real edge it plays a sound
  (`jsr $1c840` D0=`3`) and dispatches through a 4-entry jump table at `$d3bc` indexed by `$227fa`
  (an as-yet-unidentified "current fire mode" selector) to `$d3cc`.
- **`$00d3cc` spawns the actual projectile(s)**: a 64-byte-per-entry descriptor table at `$d4be`,
  indexed by the equipped-weapon byte `$bb72` (`(weapon-1)*64`), is copied into **four consecutive
  object-array slots starting at `$1a9aa`** — `($1a9aa-$1a2ea)/108 = 16`, i.e. **slots 16-19 of the
  same 20-slot, 108-byte-stride array** (`$1a2ea`+N·108) documented above as the hero/enemy/prop
  array, not a separate table. Each slot gets `type := 3` (the literal `moveq #3,D0` proves the
  "type=3" ID the README's item 7 named but never traced to a writer), position = hero's own
  `2(A0)`/`4(A0)` plus a per-slot `(dx,dy)` offset from the descriptor, radius bytes `12(A1)`/`13(A1)`
  and anim-descriptor pointer `$21822` from the same descriptor, and **damage field `104(A1) :=
  $bb72`** — a fired projectile's own damage equals the equipped-weapon index, the same struct field
  `$e80e` already reads generically for enemy-contact damage, so a projectile hitting *anything* that
  runs the same generic contact check would use the identical mechanism, just in the other direction.
  A second, mirrored 2-byte-per-entry offset table at `$d57e` is substituted when the hero is
  left-facing (`$227f4 != 0`), giving the projectile spawn the correct muzzle offset for either
  direction.
- **`$00bafc` is a small, separate type-3 draw-dispatch scan**: it walks only 5 array slots starting
  at `$1a5de` (indices 7-11, *not* the projectile slots 16-19) and calls the generic draw stub
  `$1b3f8` for any of them that reads `type==3` at the time — i.e. some of the ordinary prop/enemy
  slots can themselves *become* type 3 (most likely on death/destruction, turning into rubble/debris
  rendered through the same stub), a distinct mechanism from weapon projectiles despite sharing the
  same type ID. Not yet proven which prop/enemy this applies to or what triggers the transition.
- **Not yet found**: the routine (if any) that checks a projectile slot for contact against an enemy
  and applies damage the other way — `$0147ec`/`$014d5c`, the two `$b71a` call sites found in the
  `$13fe8`-`$17922` per-type-handler range this pass, are both enemy-vs-**hero** checks (`A1 :=
  $1a572` hardcoded, immediately followed by `bsr $e80e`), the same mechanism already proven, not a
  projectile-vs-enemy path. A per-type dispatch entry for `type==3` itself (parallel to how enemy
  types run their own hero-contact handler) is the most likely place to find one; not yet located.
  `$014d3a`'s `cmpa.l #$1a9aa,A1` loop bound (found while reading `$014d56`'s handler) is independent
  confirmation that `$1a9aa` — slot 16 — is a real, code-recognised boundary between the general
  object slots and the dedicated projectile block, not just an address this pass computed by
  arithmetic.

Items 1, 1b, 2 and 3 are now all resolved: the hazard/collision mechanism is proven end to end
(`$b71a` proximity test → `$e80e` damage-field copy → `$eafa` health decrement, pinned live with a
`callcap` showing the `$bb74`/`$1a5d8`/`$227f6` delta directly → `$ec50` death handling →
`$b058`/`$b2d8`/`$17fe8` reload into a real Game Over screen, confirmed by render), the full
`$25000` tile table is read out (six categories, three still semantically unidentified), and the
HUD write is `$00fdc4`'s health-pip bar. The 83rd pass's own new finding — the weapon/projectile
system (`$00d37c`/`$00d3cc`/`$d4be`, type-3 slots 16-19) — is proven from disassembly (table
contents, slot writes, damage-field assignment) but not yet cross-checked live with a `callcap` or a
confirmed on-screen hit. The 84th pass corrected the twin-tree screen's hazard attribution (the real
contact is a static `type=1` prop at slot 10, `$1a722`, not the `type=2` slot 8 object at `$1a64a`)
and ruled out plain up-holding as a ladder-climb (state never leaves `2`/jump). The 85th pass found a
dodge that survives the crossing (drop "up" right as the fall state begins: one hit instead of three,
lands alive at `2/18` health) and a safe leftward retreat from the landing spot toward the screen's
visible ladder, but the landing spot itself is still boxed in (right blocked, any further jump fatal).
The 86th pass proved the leftward retreat is a dead end (the hero settles at `x=74`, trunk-blocked,
one column short of the ladder) and identified a branch/platform visible above that spot as the next
lead. The 87th pass found and proved the real jump mechanism (`$c742` one-shot entry → `$cbbc`
per-frame table-driven vertical displacement plus a facing-locked horizontal push) and used it
(up+right from the trunk-blocked spot) to clear the trunk entirely, landing past it near a
fence-post/ladder structure with a visible item. The 88th pass read that exact landing spot as a
soft-lock: the hero's busy flag (`$1a5d7`) stays set there for ~500,000-600,000 steps while the whole
movement-dispatch chain shows zero hits, then the game force-reloads through the hazard-death screen's
own fade/reload chain — and wrote up health as unchanged at `18/18` throughout. The 89th pass found
that last claim was wrong and, correcting it, closed out `$1a5d7`, the reload trigger, and the "why
here" question together: `pass87_jump_right_600k.snap` already shows `$bb74=$00`, and a live `watch`
of the same jump pins two hits at `$00eb8c` from a third, previously-uncatalogued static hazard at
slot 9 (`$1a6b6`, `x=66,y=98`, between the twin-tree screen's known slot-8/slot-10 pair) that the
jump's own arc clips on the way up. `$1a5d7` is simply the death-animation lock (`$00ecce`, inside
`$00ec50`, entered once `$bb74` hits zero and the hero is grounded — which is why the visible "stuck"
state only starts after landing, though the fatal hit lands mid-air) and it does clear again, at
`$01ab66`, inside the same `$b058`/`$1c3d8` reload chain the 82nd pass already proved for ordinary
hazard deaths. No new mechanism, no unresolved reload trigger: this is that same cycle, reached via a
hazard this jump was never checked against. "Does a fired shot damage an enemy" is still open too,
unchanged from the 83rd pass.

**A jump that clears slot 9's hazard entirely is proven (90th pass), closing item 1: walk right to
`x=96` first, then jump.** From `pass86_left_settled.snap` (`x=74,y=152`, trunk-blocked, `2/18`
health), plain held-right (`kbd ff`/`kbd 08`, no up) advances the hero to `x=96,y=152` and stops there
on its own (a second, closer forward-sensor block, distinct from the trunk tile that stops further
*left* movement) — this stretch was never walked in any prior pass, which always jumped straight from
`x=74`. Triggering the up+right jump from `x=96` instead of `x=74` (`kbd ff`/`kbd 09`) reproduces the
same `$c742`/`$cbbc` mechanism but 22px closer to the far side, so the same table-driven arc clears
`(x=66,y=98)`'s 16px radius by a comfortable margin — `watch bb74` across the whole maneuver shows
**zero** writes, confirmed twice (an exploratory run to `x=192` and a second, checkpointed-every-frame
run used to find the exact landing step). The jump's own velocity table returns the hero to a brief
idle frame (`$227f3=0`, one VBL frame wide) at `x=130,y=144` around relative step 430,000 into the
jump before `$c742` would otherwise retrigger a second jump (up is still held); releasing up right at
that idle frame (a fresh `kbd ff`/`kbd 08` packet, right-only) stops the retrigger and settles the
hero there for good — `pass90_x96jump_land_130.snap`, health still `2/18`, zero damage across the full
900,000+430,000+1,000,000-step maneuver. `snap_render.py` on that snapshot
(`pass90_x96jump_land_130.png`) shows the hero standing well past the trunk, at the base of the first
of *two* fence-post/crossbar structures, with a green pot-shaped item sitting on the crossbar between
them and a second, purple creature near the base of the second post. From there, plain held-right at
ground level (no jump) is safe all the way to `x=192` — the same wall previous passes found from the
dodge-landing route, now reached hazard-free (`watch bb74` clean the whole way, `pass90_wall_192.snap`,
`pass90_wall_192.png` — the hero stands directly under the crossbar and item, with the purple creature
just ahead). **The item is still guarded, and the guarding object is now identified (91st pass).** A
`kbd ff`/`kbd 09` jump straight up+right from `x=192` takes a hit (`$bb74` `2`→`1`) at step 490,926
relative to the jump, at `$00eb8c` (`sub.b D0,$bb74.l`) — but that site's own `A0` is the *hero*
(`lea $1a572,A0` a few instructions earlier), not the attacker: the contact was already recorded into
`$227f6` upstream, at `$00e82e` (`move.b 104(A0),$227f6.l`, inside the `$e80e` proximity-scan block),
where `A0` is the object under test that frame. Breaking on `$e82e` (not `$eb8c`) pins the real
contact at step 490,587: object-array index 12 (base `$1a7fa` — the proven 108-byte stride off array
base `$1a2ea` places it exactly six slots past the hero's own index 6, the same formula that locates
slots 7/8/9/10 at `$1a5de`/`$1a64a`/`$1a6b6`/`$1a722`), `type=1`, hit radius `4/4/4(A0)` (far tighter
than slot 9's 16px), damage `104(A0)=1`. The 89th pass's `bpc e82e 1 400000` found nothing only
because the real hit lands well past that pass's 400,000-step cap, not because this hazard's contact
routes through a different instruction than slot 9's. Unlike the other `type=1` props, this one's
position isn't fixed: pinning the same jump from two different takeoff points read `x/y=(217,115)`
(from `x=192`) and `(211,119)` (from `x=130`) — a few pixels of drift despite zero velocity fields
(`8`-`11(A0)` all zero). The 93rd pass proved this is real, continuous motion, not noise or
per-pin measurement error: see "Slot 12 is a moving flying creature" below. **The slot-9 playbook —
take off further back so the arc clears the hazard — does not
generalize here**: jumping from `x=130` instead of `x=192` still takes the hit (same `A0=$1a7fa` via
the same `e82e` pin), so this hazard's tight, near-the-item radius can't simply be out-run the way
slot 9's wider, off-path one was; clearing it will need a different arc shape or timing, or the route
may just cost the one hit. `pass90_wall_192.snap` (`2/18` health, safe, right at the wall) is still
the best resume point for chasing the item (open item 2).

**Continuing `pass91_from130_end.snap`'s arc is fatal, and the jump is fully committed once
triggered — releasing "up" mid-arc does not abort or shorten it (92nd pass).** Two live trials, both
confirmed dead ends: (1) continuing `pass91_from130_end.snap` (`1/18`, mid-air at `(192,112)`) another
900,000 steps with "up" still held re-triggers `$c742` a second time (since up never released at an
idle-landing frame) and lands a second hit — `$bb74` reaches `0` and the death-animation marker
`$1a578` goes nonzero (`$5f`, the same value the 82nd pass's freeze investigation found), the ordinary
hazard-death cycle, not a new mechanism. (2) A fresh jump from `pass90_wall_192.snap` (`kbd ff`/`kbd
09`), sampled every 50,000 steps: the arc peaks (`y≈104`) around relative step 250,000-300,000, then
descends, taking the first hit (`$bb74` `2→1`) around step 450,000 at `y≈109-112` — consistent with
the 91st pass's `step 490,926` figure for the same maneuver. Releasing "up" right at the peak (step
300,000, well before any idle-landing frame, ruling out the "still holding through a retrigger" cause)
does **not** change this outcome: the hero continues through the same downward trajectory regardless,
still takes the first hit near `y≈109`, and a second hit at `$bb74` `1→0` follows shortly after while
still descending — proof the "horizontal push committed at takeoff" framing (87th pass) extends to the
whole arc, not just the horizontal component: once `$c742` triggers, input changes only affect whether
a *new* jump re-triggers at the idle-landing frame, they don't reshape or truncate the current one.
This rules out an early-release dodge as a way to shorten exposure to slot 12's hazard band.

**Slot 12 is a moving flying creature, not the "purple creature" ground prop or the mechanical
saw-wheel structure — proven and closing item 2 (93rd pass).** A fresh `bp e82e 491000` pin from
`pass90_wall_192.snap` reproduces the 91st pass's contact exactly (step 490,587, `A0=$1a7fa`,
`x=217,y=115`, `type=1`, radius `4/4/4`, damage `1`), confirming the whole maneuver is deterministic.
Rendering that exact snapshot and marking `(217,115)` lands the crosshair on the crossbar's own
saw-wheel graphic (`pass93_e82e_pin_tight.png`) — but this is a coincidence of that one instant, not
proof of identity: a struct read taken at two later points during total hero idle (`s 750000`/`s
1750000` from `pass90_wall_192.snap`, no input at all) shows `(x,y)` moving from `(188,161)` to
`(62,240)` — off the bottom of the visible screen — a continuous, near-linear drift of roughly
`-0.126px/step` in `x` and `+0.079px/step` in `y`, confirmed by a live `watch 1a7fc 4` over the same
window (214 writes, all from `$019aba`/`$019abe`, not the velocity-integration fields at `8`/`10(A0)`,
which read `0` at every struct snapshot taken). This single rate also reconciles the 91st pass's
"a few pixels of drift" between its two takeoff points: at this rate the two pins (close together in
real elapsed steps, not in takeoff `x`) land only a few pixels apart, exactly as observed. A **same
fixed screen region** compared between the two idle snapshots (`pass93_drift_a.png`/`pass93_drift_b.png`,
crop `(0,80)-(320,200)`, `pass93_drift_compare_fixedcrop.png`) shows every other sprite pixel-identical
across the full 1,000,000-step idle gap — the saw-wheel structure, the crossbar, the item, the hero,
and the "purple creature" near the second post (a separate, genuinely static prop) — except one small,
thin, brown/tan winged sprite that shifts from near the top of the frame to lower-left, matching the
struct's measured drift direction and magnitude. That sprite is slot 12; the 92nd pass's "black winged
creature" guess (`pass92_arc600k.png`) was the right identification, now proven by tracked position
rather than a single-frame visual guess. Open sub-question, not yet resolved: both idle-drift struct
reads show `type=0` where the live contact pin reads `type=1` — possibly an activation/danger-range
flag rather than a fixed type tag, unconfirmed.

**A safe, zero-damage timing dodge past slot 12 is proven (94th pass), and every contact below is
identified by its own live `A0`, not assumed from which hazard the trial was aimed at.** The arc
itself is fixed in absolute time from trigger (92nd pass) while slot 12 keeps drifting, so an idle
wait before the same `kbd ff`/`kbd 09` up+right trigger shifts where the drifting hazard is relative
to that fixed arc. From `pass90_wall_192.snap`, holding the trigger 15,000 steps (a genuine hold is
required: a 1-step tap never reaches `$00c742` at all, the hero stays grounded) then releasing to
`kbd ff`/`kbd 08` (right-only — prevents the idle-landing-frame retrigger the 92nd pass identified,
though it does not reshape the current arc) was tried at nine idle delays, 50,000 steps apart.

Delays `0`-`150,000` take a hit from slot 12 itself (`A0=$1a7fa`, confirmed live at each): the exact
`$b71a` margin closes as delay grows — at delay `0` (contact step `475,454`) `x/y=(217,115)` against
hero `(194,112)` gives `dx=15` (threshold `16`), `dy=3` (threshold `24`); at delay `150,000` (contact
step `361,433`) `x/y=(214,130)` against hero `(194,108)` gives `dx=12`, `dy=22` — both axes still
inside range, but the `dy` margin has shrunk from `21` px of headroom to `2`. **Delays `250,000`-
`450,000` (five values) clear slot 12 outright**: `bp e82e` gave up (zero hits, from any object)
across the whole post-trigger window, re-checked out to 1,300,000-1,615,000 steps, with the hero
settled idle, grounded, at the exact takeoff spot `x=192,y=144`, health still `2/18`.

**Delays `200,000`, `500,000`-`550,000` and `600,000` also clear slot 12 — the hit they take is a
different, previously-unconfirmed hazard, slot 8 (`$1a64a`).** The first write-up of this pass read
these as slot 12 catching up late, on the strength of the "prove a static-looking value live"
caution (below) applied to *timing*: a short post-trigger check (`bp e82e` giving up within 700,000
steps, hero resting idle at `y=112` — on the crossbar itself, not the ground) looked clean, and a
longer check (400,000 more steps, or a direct hit within 655,193 steps for delay `600,000`) caught a
hit at each. Reading `A0` at that hit (not just the hex dump at slot 12's own fixed address, which
was silently stale for these three) shows `$0001a64a` every time — the `type=2` object the 83rd pass
first spotted on this same twin-tree screen and the 84th pass explicitly flagged as unconfirmed:
"the `$1a64a` type=2 object may still be a hazard in its own right..., but nothing in this pass's
data shows it ever being the one in contact." **This closes that flag**: at the delay-`200,000`
contact (step `839,032`), slot 8 reads `x/y=(214,112)`, velocity `(+2,0)`, radius `20/24/24`, damage
`1`, against the hero resting at `(194,112)` — `dx=(214+2)-(194+8)=14` (threshold `16`), `dy=(112)-
(112)=0` (threshold `24`), the identical generic `$b71a` test, genuinely triggered. Unlike the
84th pass's slot-10 culprit, slot 8's own velocity field reads nonzero here (`+2` in `x`) — the
"static" classification given to slot 8 on sight in the 83rd/84th passes is now itself suspect and
unconfirmed either way, not yet re-checked live.

The five genuinely clean delays (`250,000`-`450,000`) share a trait the caught ones don't: the arc's
own landing height. The hero settles at the crossbar height `y=112` for `200,000`/`500,000`-
`550,000`/`600,000` (where slot 8's danger band sits) but continues fully through to the ground
`y=144` for `250,000`-`450,000`, clearing slot 8's height entirely — inferred from this data as *why*
the wider window is genuinely safe rather than merely unluckied-into, not yet mechanized: what
decides which landing height a given delay produces (the same one-shot arc, by the 92nd pass's own
"fixed in time from trigger" finding) is still open, see below. No route or arc-shape change was
needed to solve the original problem, only takeoff timing within the `250,000`-`450,000` window;
`pass94_dodge_item_landed.snap` (delay `300,000`, dead centre of that range) is the settled resume
point. Still open: this dodge lands the hero back on the ground, not confirmed to have collected the
item itself — no address or mechanism for the item's own pickup/inventory state is known yet.

## Known traps

- **Proving a jump/maneuver reaches a target position is not proof it was safe — check health and
  other hidden state too, not just position.** The 87th pass wrote up `kbd ff`/`kbd 09` from
  `pass86_left_settled.snap` as clearing the trunk cleanly, checking only `x`/`y` and the jump state
  machine; the 88th pass then spent a full pass on an apparent "soft-lock" at the landing spot. The
  89th pass found the jump itself took two hits from an uncatalogued hazard mid-arc, killing the hero
  to `0/18` before it ever landed — invisible to a position-only check, and the "soft-lock" was just
  the ordinary death sequence waiting for the hero to be grounded before it could start. When proving
  a movement input reaches a place, also snapshot/watch health (`$bb74`) and any other per-object
  status field (busy/cooldown flags) across the whole maneuver, not only at the end.
- **A `bp`/`watch` check that finds nothing within its own step budget is not proof the maneuver is
  safe past that budget, and a hit inside a wider budget is not proof it's the hazard you were
  aiming at — read `A0`/the contact site, don't assume it from which trial you were running.** The
  94th pass's timing-dodge search found three delays (`200,000`, `500,000`-`550,000`, `600,000`)
  where a `bp e82e` capped at 700,000 steps gave up clean (or, for `600,000`, hit inside the cap) and
  the hero looked settled (idle, resting on the crossbar at `y=112`) — a wider budget (out to
  1,300,000+ steps) caught a hit at all three, health reaching `0`, first written up as slot 12
  catching up late. Reading the stopped breakpoint's own `A0` register (not the hex dump at slot
  12's fixed address, which was silently stale) showed it was a *different* object, slot 8
  (`$1a64a`) — all three delays had already cleared slot 12 outright, same as the five genuinely
  clean ones; slot 8 was the actual, previously-unconfirmed second hazard. Two separate mistakes
  compound here: trusting a short check window, and trusting an assumed contact identity instead of
  reading it. Re-running with a materially longer budget than the maneuver's own known duration
  (here, well past where the genuinely-safe delays had settled grounded and idle) catches the delayed
  hit; reading `A0` (or the exact contact address) at that hit is what tells you which hazard it was.
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
- **A visual match "in roughly the right screen area" is not proof of an object's identity.** The
  81st pass spotted a grey humanoid figure in this emulator's Klondike Mine render near where the
  hero object's coordinates would place it, and reported it as "the hero rendering" without checking
  the object's own declared position precisely — a tight crop at the object's *exact* `(X,Y)` later
  showed the figure sits 20-30px away, outside that crop entirely. Before attributing a visible sprite
  to a specific object, crop tightly at that object's own coordinates (or better, breakpoint the draw
  call itself and read the address it resolves, the way the `$42e00` hero-bank proof above does) —
  don't eyeball proximity on a full-screen thumbnail.
- **Checking only a small prefix of a memory region is not the same as checking the region.** The same
  pass twice drew a wrong "empty"/"non-empty" conclusion from the first 64 bytes of a buffer whose
  real content only differs later (an object struct's type field is a 16-bit word, not the first
  byte alone; a loaded file's first 64 bytes were a legitimate zero-padded header, not proof the
  whole `$6c00`-byte buffer was blank). Dump the field's actual declared width, and the buffer's full
  extent, before concluding "populated" or "empty" from a byte count.
- **`bt` (backtrace) can crash the whole REPL session with an unhandled `AddressError`** if the
  A6 link-chain it walks reaches an address that isn't a valid link frame — hit when backtracing
  from a snapshot frozen mid-unpacker-loop (the depacker temporarily runs at a low, non-`LINK`-framed
  address and repurposes registers freely). `bt`'s *first* frame (return address straight off `A7`)
  is reliable even then; when the chain past it looks suspect, fall back to a raw `m <A7> <len>`
  stack dump, or set a breakpoint at the routine's real entry point (where a caller's `jsr`/`bsr` just
  pushed a clean return address) rather than backtracing from an arbitrary mid-execution snapshot.

## Files

| file | what |
|------|------|
| `README.md` | this file |
| `trainer_menu.png` | crack trainer-menu screen, reached via F1 from the boot menu |
| `title_logo.png` | the real game's title screen, reached by skipping the trainer |
| `world_select.png` | the world-select screen, reached by sending a joystick-1 fire packet at the title screen (see above) |
| `after_confirm_screen.png` | the plain "IMPOSSAMOLE" logo screen the `after_select3.snap` lineage reaches after confirming Klondike Mine, bouncing back to `world_select.png` — **retracted as a general confirm→load bug (82nd pass)**: specific to that stale snapshot lineage's own early boot, which skipped the `$b288` common-resource load; a fresh cold boot reaches genuine gameplay instead (`coldboot_klondike_gameplay.png`) — see "Confirming a world" above |
| `amazon_gameplay.png` | first real gameplay frame from the `after_select3.snap` lineage, reached by confirming The Amazon instead of Klondike Mine — terraced hillside, ruined pillar; no hero sprite visible in this render. **Retracted as a rendering/confirm-path bug (82nd pass)** — same stale-lineage cause as `after_confirm_screen.png` above; kept for reference as "what the old lineage looked like", superseded by `coldboot_amazon_gameplay.png` |
| `amazon_noinput_2M.png` | control frame: `after_amazon_load2.snap` (same stale lineage) run 2M steps with no input at all — terrain unchanged from `amazon_gameplay.png` except one small idle-animation blob (see "Gameplay input" above) |
| `amazon_walk_right.png` | the same 2M-step window as `amazon_noinput_2M.png` but with joystick-1 bit 3 (right) held throughout — pillar and terrain visibly scrolled against the control frame, proving the movement mapping drives a real scene scroll. The visible green creature in both frames is a `type=1` object (it shifts with the scroll), not the hero — **note (82nd pass continued): it also has its own autonomous motion independent of the hero/scroll, see "Past the first screen" below, so "background prop" was only ever proven for this one short window, not in general** |
| `coldboot_amazon_gameplay.png` | **82nd pass, fresh cold boot** (not the stale lineage above) — the identical Amazon scene as `amazon_gameplay.png`, but with the mole hero clearly visible standing at the pillar's base, matching Hatari's `hatari_amazon_gameplay.png` — see "Why no hero sprite is visible" above |
| `coldboot_amazon_hero_zoom.png` | zoomed crop of the hero from `coldboot_amazon_gameplay.png` — grey head, red scarf, blue suit, pixel-for-pixel the same mascot as Hatari's `hatari_amazon_hero_zoom.png` |
| `coldboot_klondike_gameplay.png` | **82nd pass, fresh cold boot**, confirming Klondike Mine instead of Amazon — a genuine mine-cavern level (rock texture, gallows-post, hanging lantern), same layout as Hatari's `hatari_klondike_gameover.png`, not the blank-logo bounce `after_confirm_screen.png` shows |
| `coldboot_amazon_hazard_contact.png` | **82nd pass continued, item 6**: 4,000,000 steps into a held-right run from `at_gameplay_final.snap` — a white contact/hit-effect sprite appears where the green `type=1` object has drifted next to the hero, one checkpoint before the run resets through the resource loader. Visual support for, not proof of, "this object is a hazard" — see "Past the first screen" above |
| `coldboot_amazon_jump_ladder.png` | **82nd pass continued, item 6**: holding right+up instead of right alone, 4,000,000 steps in — genuinely new terrain (a ladder/tree structure, ground spikes) never seen by this workstream before, the reload from the plain-right run avoided |
| `coldboot_amazon_jump_totems.png` | **82nd pass continued, item 6**: the same right+up run, 8,000,000 steps in — tribal totem-pole decorations, a water pool and more spikes, hero (`type=2`, alive) standing on a ledge |
| `coldboot_amazon_game_over.png` | **82nd pass continued, items 1/1b/3**: rendered 10,000,000 steps past the plain-right death's reload snapshot — a tombstone and `GAME OVER` / `YOUR SCORE 000000` / `FINAL SCENE THE AMAZON`, proving the reload is a genuine death transition (`$b058`/`$b2d8`/`$17fe8`), not a per-level retry |
| `coldboot_amazon_twintree_ladder.png` | **83rd pass**: the same held right+up run continued another 4,000,000 steps (12,000,000 total) — a genuinely new screen, twin trees with hanging vine curtains and a totem/ladder structure, with a second `type=2` hazard object (object-array slot 8, base `$1a64a`) visible bottom-centre; holding straight through it reproduces the death→reload cycle by ~14,500,000-15,000,000 steps |
| `hatari_crosscheck/hatari_title.png`, `hatari_klondike_gameover.png`, `hatari_amazon_gameplay.png`, `hatari_amazon_hero_zoom.png` | real Hatari v2.6.1, same disk image, driven live 2026-09-27 — title screen, Klondike Mine played to a genuine Game Over, Amazon gameplay with the hero sprite clearly visible, and a zoomed crop of it. Originally run to check this emulator for bugs; the 82nd pass found the divergence was in one stale snapshot lineage, not this emulator generally — see "Real-hardware cross-check" above |
| `coldboot_amazon_twintree_dodge_landed.png` | **85th pass**: the hero alive at `x=192,y=144`, `2/18` health, right after surviving the twin-tree hazard crossing (one hit instead of three) by dropping "up" as the fall state begins — a real ladder is visible on the left tree trunk, not yet reached from this landing spot |
| `coldboot_amazon_twintree_dodge_left.png` | **85th pass**: the same run continued with left held from the landing spot — hero walks to `x=142` with health unchanged, the first safe horizontal move off the hazard's danger corridor found so far, closer to the visible ladder |
| `coldboot_amazon_twintree_jump_midair.png` | **87th pass**: `kbd ff`/`kbd 09` (up+right) from the trunk-blocked `x=74,y=152` spot, 600,000 steps in — the hero mid-jump (`$227f3=2`), now at `x=124,y=108`, visibly past the tree trunk and level with the fence-post/ladder structure and green item |
| `coldboot_amazon_twintree_jump_landed.png` | **87th pass**: the same run continued a further 400,000 steps with no input — the hero lands idle at `x=152,y=144`, standing at the base of the fence-post structure past the trunk, proving the real jump mechanism (`$c742`/`$cbbc`) clears the obstacle the 86th pass's ground-level approach couldn't. **Superseded as a "safe" reference by `coldboot_amazon_twintree_jump_landed_safe.png` below — this exact jump was later proven to take two fatal hits from slot 9 mid-arc (89th pass)** |
| `coldboot_amazon_twintree_jump_landed_safe.png` | **90th pass**: the hero idle at `x=130,y=144`, `2/18` health unchanged, after a jump triggered from `x=96` instead of `x=74` — clears slot 9's hazard with zero damage (`watch bb74`: no writes), proving item 1. Two fence-post/crossbar structures are visible, a green item on the first crossbar, a purple creature near the second post's base |
| `coldboot_amazon_twintree_item_crossbar.png` | **90th pass**: the hero at `x=192,y=144`, `2/18` health, reached by plain ground-level right-walking from the safe landing above — the same wall previous passes found from the dodge-landing route, now reached hazard-free. Hero stands directly under the item's crossbar; a `kbd ff`/`kbd 09` jump straight up from here takes a hit, the guarding object not yet pinned to a slot (open item 2) |
| `coldboot_amazon_twintree_guard_hit.png` | **92nd pass**: rendered just after the jump from `x=192` takes its first hit — shows a black winged creature circling near the top of the crossbar/item area; the 93rd pass confirmed this is slot 12 (see next row) |
| `coldboot_amazon_twintree_slot12_drift.png` | **93rd pass**: the same fixed screen region (`(0,80)-(320,200)`) rendered from two idle snapshots 1,000,000 steps apart, no input held — every sprite is pixel-identical except one small winged creature, which shifts from near the top of the frame to lower-left, proving slot 12 is that creature (not the static saw-wheel structure its coordinates happened to overlap at the original contact pin, and not the separate, genuinely static "purple creature" prop near the second post) |

## Not yet exercised

**`$b288` keypress-timing bisection is done (82nd pass, continued)** — see "Why `$b288` sometimes
never runs" above: it needs F1 then any second recognized key, in order, and is insensitive to hold
duration and gap length once both are present; no combination was found that reaches gameplay while
skipping it. The old lineage's exact failure mode is not reproduced and is now suspected to predate
today's cold-boot path entirely (its script no longer exists to check) rather than being a live,
re-triggerable timing race — not worth further bisection time unless a *new* instance of the same
symptom turns up on a fresh cold boot.

**Item 6 (drive Amazon gameplay past this one screen) is well underway but still open** — see "Past
the first screen" above: the hazard/collision mechanism itself is now `callcap`-proven end to end
(not just visually correlated), the full tile-classification table is read out, the HUD routine is
named, and a real weapon/projectile system is proven from disassembly. Held right+up (jumping) gets
past the first screen's ground hazard into new terrain (ladder, spikes, totems, water), and
12,000,000 steps in reaches a second new screen (twin trees, vine curtains, a totem/ladder structure)
with a second hazard creature that the same held input has not yet been driven past alive. **Open
now**: get past that second-screen creature (a different dodge timing, or actually landing a weapon
shot on it); confirm live whether a fired projectile damages an enemy at all (the write side —
`$00d3cc` spawning a `type=3` slot — is proven, the read/damage side is not); and continue mapping
Amazon's content beyond that point.

Also open: the Klondike cold-boot run past ~9M steps with no player input goes black and PC moves to
the shared title/select transition routine (`$1c3d8`) — consistent with an unattended death, but not
yet confirmed or rendered (the screen may be on the buffer `snap_render.py` isn't currently displaying;
see "Known traps"). Driving Klondike with real movement input from the fresh-cold-boot lineage (instead
of leaving it running untouched) would both dodge this and give a proper look at mine-cavern gameplay
mechanics, which have not been examined at all yet (only Amazon's `$c2fa`/`$be96`/`$c0d4` mechanics
have been proven live, all from the old lineage — worth spot-checking they still hold from a fresh
Amazon cold boot too, though there's no reason to expect the RAM contents relevant to those mechanics
differ between the two lineages downstream of world-select).

Past the gameplay movement mapping and the object-render/tile-classification mechanisms (see above):
the ladder-climb and jump/attack states (`$227f3 := 4`/`2`) are read statically only, not yet driven
live; what the `$25000` tile-classification table's 256 entries actually map to; whether any
enemy/AI-controlled object exists at all — every object seen in this single screen of the Amazon
level so far (in this emulator) is either the hero, a static background prop, or a dormant (`type=0`)
slot, no hostile behaviour has been observed because gameplay hasn't been driven past this one screen
in this emulator (Klondike Mine's cavern screen has an unidentified second figure worth checking, see
`coldboot_klondike_gameplay.png`); whether Orient/Ice Land/Bermuda Triangle load correctly in this
emulator too; sprite/tile formats beyond the collision map now proven; level data (`MDATA*.DCH`,
`BRMUDA*.DAT` etc.); and control flow / CFG extraction.
