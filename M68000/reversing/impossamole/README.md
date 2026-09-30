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

## Topic documents

| document | what it covers |
|---|---|
| this README | boot and input, the Amazon level, route, boss, shop, spawn types, level end, known traps, file index |
| `graphics.md` | the asset formats (level, tiles, sprite banks, palettes, font, collision categories) with match counts |
| `worlds.md` | the five worlds: loader, per-world files and banks, categories 5-8, rooms and routes, bosses, per-world tables |
| `secrets.md` | cheats and their effects, the Space smart bomb and other keys, the crack's trainer and protection, dead content, the LSD!/Huffman packers, the random number generator, the two sound engines |
| `py/README.md` | every script, its start snapshot and expected output |

## Design digest

The game's rules restated for re-use in another design, without addresses. Each line names the section that proves it (R = this README,
G = `graphics.md`, W = `worlds.md`; "route" = R "The route to the boss room on real input", "spawn" = R "Spawn types"); anything not proven there is
labelled inferred or read (from code, not run). `/handoff` re-checks this list against every session's changes.

### What carries the game

- **One long map per world, played one room at a time.** A level is a 420-block-wide tile map with a separate collision layer at 8 px, cut into
  overlapping block ranges (rooms). Only one room is live; leaving through the top or bottom of the screen looks up the hero's block in the world's
  exit list, clears the objects and installs the destination. Overlap lets the same blocks be a corridor in one room and a cave in another.
  (R "The level is one tile map of connected rooms"; W "Rooms and routes")
- **Terrain is a small vocabulary of categories, and the art does not decide it.** Air, ladder, ledge, one-way log or stair, solid, hazard, plus
  conveyors left and right, ice slide and slow ground in the later worlds. Changing the art changes nothing about what is solid. (G "Pipeline", W
  "Collision categories")
- **One object record does every job.** Hero, enemy, pickup, shop keeper, weapon swipe and spawned projectile are the same 108-byte record in a
  20-slot array, told apart by slot range and handler. Contact, shot hits, triggers and platform riding all use one box overlap test. (R "Spawn
  types", "Common machinery")
- **Levels populate from a list.** A column-sorted list of (column, row, type) records is walked as the camera advances; each type is a descriptor
  (hit points, damage, speeds, art, score, handler) plus a handler routine, and the same handlers serve several worlds. Fruit comes from invisible
  containers the level places. (R "Spawn types"; W "Other `$bb76`-indexed tables")
- **Health is the only resource, and it is small.** 18 points, no regeneration, 1-point hits, a 7-frame invulnerability window after a touch and a knockback
  jump. Heal pickups are rare (five records in the Amazon, each `4 + world number`) and one shop item heals the same amount. (R "Boss", "The shop")
- **The weapon is a short-range swipe, not a projectile.** A fire press makes a static hit box in front of the hero for 5 frames with a 6-frame
  cooldown; damage is the weapon level (1-3, raised by an upgrade pickup, reset each level); a swipe hits at most once. (R "Boss", "Natural aim")
- **Enemies are killable or immune by their hit points.** 1-127 dies to swipes; 128-255 absorbs them, so an immune enemy has to be avoided or
  outlasted. About a dozen reusable behaviours (ambusher on a proximity box, perched thrower, patroller that spits, chaser, wanderer, scripted
  flier, falling trap, rideable platform, tongue) make up each world's roster. (R "Spawn types")
- **Movement is a fixed-shape jump.** Up starts a jump with a table-driven arc of 40 px apex and a horizontal push locked at take-off; a plain
  jump covers about 43 px. Obstacles are built in 32 px units (one hop) and 8 px lips that stall a walker. (R "Past the first screen", route)
- **Water costs health by contact.** Standing or landing on a hazard tile takes 1 point and throws the hero into the same hit-reaction jump; the
  four pits of the Amazon route cost an unpoked hero that just walks on 8 water hits, and 0 when each jump is timed to land on a crocodile with its jaws
  shut (crocodiles are platforms only then). (R "What the route costs in health", "Unpoked, hop 3 is playable")
- **The level's shape is a health budget.** Measured on the Amazon route from room `188..285` to the boss: 92 contact decrements and 9 water hits with a
  refilled hero, against 18 points. Walking it and swiping what is ahead dies in the fourth pit; with a guard that snipes perched monkeys, timed pit
  crossings and a few waits, hop 3 reaches its exit with 11 of 18 points and no poke; hop 4 costs 2 more, one shop purchase (75 of the 100 coins held there) gives 7 back, and the
  boss then has to be beaten from 16 points against a 7-damage lob and 1-damage shots. (R "What the route costs in health", "Unpoked, hop 3 is playable",
  "Unpoked, the whole Amazon")
- **A boss ends the level.** One 60-hit-point boss per world in a dead-end room; a flag, a 125-frame count, a fade and reload lead to world select
  with the world crossed out. The Amazon boss is vulnerable only in an open-mouth phase and only to a jumping hero; other worlds add a
  hit-ignoring flag (Klondike) or a shielded phase (Bermuda). The Amazon boss answers with an aimed 1-damage shot and a 7-damage lob that flies toward the
  hero's side, so a 16-point hero that dodges only the lob beat it in one start timing of twelve. (R "Boss", "Unpoked, the whole Amazon", "How a level ends"; W "Bosses")
- **Progress is one run.** Death goes Game Over, title, and all progress and score are lost; Bermuda unlocks when the other four are won; the fifth
  world's win goes to the ending and high-score entry. (R "How a level ends")
- **One hidden shop per level**, entered by finding the mole in a pit and pressing down on it; coins (dropped by monkeys, 25 each) buy heals (proven for the worm can),
  weapon upgrades and special fire (read). (R "The shop")
- **Two extras with no on-screen hint.** Space is a once-per-level smart bomb (kills every enemy slot except hit points `$fe`, freezes the hero for its
  animation), and six names typed into the Game Over or ending high-score entry (score of 2000 or more; `HEINZ...` needs its three full stops) switch on one run of
  bigger health, weapon 3, endless special fire, an extra life, harmless water or double heals. Ctrl pauses, Esc quits to the title. (R "Unpoked, the whole Amazon";
  `secrets.md` "Cheats", "Keys the game reads")
- **Randomness is a function of time.** One 16-bit generator fed by four VBL counters that are zeroed at every title, death and level start, so the same input timing gives
  the same enemies, drops and boss shots: a route recorded as packets replays exactly. (`secrets.md` "The random number generator")
- **Everything is frame-counted and deterministic**, so a run replays byte for byte from a snapshot and a route can be recorded as joystick
  packets. (route)

### Limits that became features

- **Hit points as a flag.** One byte does both jobs: the low range counts damage and the high range means immune, which spends no extra state on
  "this enemy cannot be killed". (R "Spawn types")
- **The camera pins the hero at one screen column** while the level scrolls, so the hero's own position hardly changes on a long walk; progress lives
  in the scroll counter. (route)
- **One-way platforms and 8 px lips** stand in for enemy blocking: the player has to hop rather than walk through the dangerous stretch. (route)
- **A 20-slot array, cleared on every room change,** bounds memory and makes rooms cheap; objects leaving the window (x outside 0..304, y outside
  -16..200) are freed. (R "The level is one tile map of connected rooms", "Spawn types")
- **Bank overwrite per world.** The common sprite frames stay and each world's files replace the tail of each bank, so five art sets fit one
  loader and one engine. (W "Sprite banks")

### Bugs and accidents a new design should drop

- Every world's ambient sound is silent (five sound slots use an empty record) and the digitised-sample and song paths of the effect engine are unreachable: the release
  drops what an earlier build seems to have had (`secrets.md` "Dead and unreferenced content").
- The joystick fire bit is edge-detected once per frame, so a press shorter than a frame is lost; on the world-select screen a fire pressed while
  the cursor is still moving is lost. (R "Confirming a world needs a held fire"; W "Ice Land and Bermuda Triangle")
- The hero's sensor scan writes probe offsets into its own position for a few instructions each frame, so a reader that samples mid-frame sees a
  jump (found while driving, handled in `py/route/route_driver.py` `read_stable`; inferred to be harmless to the game).
- Water damage is tested only in hero states 0 and 1, so a hero already in a jump or fall is not hit by the tile until it lands (read, from the tile
  test's state check; not tested). (R "What the route costs in health")
- Klondike's boss ignores hits while a state byte is non-zero, which stretched its kill from 60 to 223 pulses (W "Bosses"; possibly intended).

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
| `EMOTION+.PRG` | 7094 bytes, magic `$601a`: the E-Motion crack's launcher, packed with a second packer (JEK PACKER V1.2), "PRESS 'T' FOR TRAINER / PRESS 'N' FOR NORMAL" (`secrets.md`) |
| `MINDBOMB.PRG` | 19840 bytes, magic `$601a`, a third packer; unpacks to 63,068 bytes, the "Mind Bomb" demo screen (Chrispy Noodle music, Manikin code): a filler nothing in the game refers to (`secrets.md`) |
| `E_MOTION` | 309398 bytes, no extension, starts `$6000` (`bra.w`): the E-Motion game itself (US Gold / Assembly Line 1990), the other half of the crack disk; not analysed |
| `CHARS11.DAT`, `SPRTS22.DAT`, `SPRTS33.DAT` | font + two sprite banks |
| `BRMUDA{22,33}.DAT`, `ICELND{22,33}.DAT`, `JUNGLE{22,33}.DAT`, `MINES{22,33}.DAT`, `ORIENT{22,33}.DAT` | per-level (Bermuda / Iceland / Jungle / Mines / Orient) data pairs — the game's 5 worlds |
| `SELECT44.DAT` | bank-2 frames 100-152 (32x24): red X, selection frame, walking cursor hero, Game Over art (`secrets.md`) |
| `MDATA1.DCH`…`MDATA5.DCH` | per-world level block (`$25000`-`$31800`), LSD! then Huffman packed |
| `PICTURES.DCH` | the world-select and title screens, two 32,000-byte ST low-res pictures, LSD! then Huffman packed |
| `MST.IMG` | 56457 bytes: the game itself, a 484-byte stub ("AUTOMATION PACKER V2.2f") plus an LSD!-packed 98,148-byte image (F1 in the boot menu loads it to `$50000`) |
| `E_MOTION.PC1`, `PRES_ST.PC1` | LSD!-packed Degas PC1 pictures: the E-Motion title and the Replicants intro |
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
  `CHARS11.DAT`/`SPRTS22.DAT`/`SPRTS33.DAT` to `$24000`/`$3b600`/`$42e00` via the shared file loader
  `$1c6de`, whose `Fread` the crack's trap #1 hook depacks in place, `secrets.md`) landed zero hits on `b288`/`b2ca`/`b328` across that whole run, and a static whole-RAM
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
  then `$0001c68e` — inside the same early common-resource loader region (`$1c686` is the VBL wait loop, `$1c68e` its tail) the initial boot-time load
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
    zeroed with PC inside the loader by step 5,000,000 — health hitting zero and the reload
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
    `$1ab6e`, `$1f972`), calls `$b2d8` (which reloads `$53000`/`$fa00` and `$4c400`/`$5000` via the
    shared `$1c6de` file loader — the same "resource reload" symptom seen as the object array zeroing
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
  then PC lands back inside `$18812`, the Huffman expander that follows the `$1c6de` load (confirmed at `$0001882e`, mid-expand-loop
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
- **The projectile-vs-enemy check is `$0013a9c` (found by the 99th pass, see "The level is one tile map
  of connected rooms", "Boss").** The two `$b71a` call sites in `$0147ec`/`$014d5c` are enemy-vs-hero
  checks, as found here; the enemy-side check is a separate routine that an enemy's own per-frame handler
  calls, and it loops over the four projectile slots (`$1a9aa`, slots 16-19).
  `$014d3a`'s `cmpa.l #$1a9aa,A1` loop bound is independent confirmation that slot 16 is a real,
  code-recognised boundary between the general object slots and the dedicated projectile block.

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

**Retraction (95th pass): the "safe, zero-damage timing dodge past slot 12" the 94th pass reported is
not a dodge at all — for five of its nine trial delays, the jump never fired.** The 94th pass held the
`kbd ff`/`kbd 09` up+right trigger for 15,000 steps before releasing to `kbd ff`/`kbd 08`, tried at
nine idle delays 50,000 steps apart, and read "zero `$e82e` hits, hero still at the takeoff spot" as a
clean dodge. A direct `watch` on the jump's own frame counter (`82(A0)`, `$0001a5c4` — "advanced by 1
each call", 87th pass) shows why that reading was wrong: for delays `0`, `100,000`, `150,000`,
`200,000`, `500,000`, `550,000` and `600,000` the counter is written 17 times (a real jump runs); for
every one of the five delays the 94th pass called "genuinely clean" (`250,000`-`450,000`) it is written
**zero** times — the jump never entered `$00c742` at all, and "hero still at `x=192,y=144`, health
`2/18`" is simply the hero never having moved, not a completed round-trip arc. The cause is an
input-timing bug in the *test*, not the game: the up+right packet is enqueued instantly (no delay
between `kbd ff` and `kbd 09`), and the game only samples it on its own ~24,000-step joystick poll
cycle (twice the `$c6d0`/`$caba` idle-flicker toggle period visible in a `watch 227e0 26` trace); a
15,000-step hold is shorter than that full cycle, so whether the poll falls inside the hold window
depends on the idle delay's phase (`delay mod 24000`). The five delays that "cleared" outright all
land in the same `10,000`-`18,000` dead band of that cycle (`250,000 mod 24000 = 10,000`
... `450,000 mod 24000 = 18,000`) where the poll never lands inside the 15,000-step window; every
delay confirmed to fire (`0, 100000, 150000, 200000, 500000, 550000, 600000`) sits outside that band.
Holding for 30,000 steps instead (more than one full poll cycle, so the packet is guaranteed to be
seen regardless of phase) makes the jump fire reliably even at delay `300,000` — but the result is
**not** a lasting safe landing either: the hero lands at `x=194,y=112` with zero hits in the first
700,000 post-release steps, but a second `bp e82e 700000` window catches a hit from slot 8 (`A0=
$1a64a`) after a further `360,435` steps, and a third window catches a second hit `251,999` steps
after that (`pass95_realdodge_300k_30khold.snap`, paused at the second hit) — the same trap already on
this list (a clean window is not proof past its own budget), now confirmed against a genuine jump
rather than a mistimed one.

This also answers the "what decides landing height" question the 94th pass left open, but not the way
it assumed: **there is no variable landing height** — when the packet registers, the arc always lands
at the same spot, the crossbar height `y=112` (confirmed for delays `0`/`100,000`/`150,000` — cut
short by a mid-air hit from slot 12 before landing — and `200,000`/`500,000`/`550,000`/`600,000`,
which do land there); `y=144` only ever means the hero never left the ground because the trigger
packet was missed. **Delays `0`-`150,000` take a hit from slot 12 itself** (`A0=$1a7fa`, confirmed
live at each) before ever landing: the exact `$b71a` margin closes as delay grows — at delay `0`
(contact step `475,454`) `x/y=(217,115)` against hero `(194,112)` gives `dx=15` (threshold `16`),
`dy=3` (threshold `24`); at delay `150,000` (contact step `361,433`) `x/y=(214,130)` against hero
`(194,108)` gives `dx=12`, `dy=22` — both axes still inside range, but the `dy` margin has shrunk
from `21`px of headroom to `2`. **Delays `200,000`, `500,000`-`550,000` and `600,000` land clean at
`y=112` but are then caught at rest by slot 8** (`$1a64a`), a previously-unconfirmed hazard the 83rd
pass first spotted and the 84th pass explicitly flagged as unresolved ("the `$1a64a` type=2 object may
still be a hazard in its own right..., but nothing in this pass's data shows it ever being the one in
contact"). **This closes that flag**: at the delay-`200,000` contact (step `839,032`), slot 8 reads
`x/y=(214,112)`, velocity `(+2,0)`, radius `20/24/24`, damage `1`, against the hero resting at
`(194,112)` — `dx=(214+2)-(194+8)=14` (threshold `16`), `dy=(112)-(112)=0` (threshold `24`), the
identical generic `$b71a` test, genuinely triggered. Unlike the 84th pass's slot-10 culprit, slot 8's
own velocity field reads nonzero here (`+2` in `x`) — the "static" classification given to slot 8 on
sight in the 83rd/84th passes is now confirmed wrong: it patrols the crossbar rest spot on its own
schedule, and the 30,000-step-hold retest above shows it catches *every* landing there eventually, not
just the four delays first flagged.

**Item 3 (dodge the guard's hazard) is reopened, not closed.** No delay or hold duration tried so far
produces a genuinely, indefinitely safe rest position at the crossbar — every real jump (mistimed
"escapes" excepted, since those never happened) either takes a hit from slot 12 mid-air or eventually
takes one from slot 8 at rest. `pass94_dodge_item_landed.snap` is **not** a dodge result: it is
state-for-state the same as `pass90_wall_192.snap`, because the packet that was supposed to trigger it
never registered. The next lever is probably to not rest at the crossbar height at all — e.g. continue
moving past it immediately after landing rather than settling, or find an approach that never stops in
either hazard's drift path — not a further search over takeoff timing alone.

**Escape attempts from the crossbar rest spot (96th pass) all "landed at the same place" because the
camera moved, not the hero.** (1) Holding right through a genuine (30,000-step-hold) landing leaves
`x` at `192`-`194` for 400,000+ steps, only `y` wobbling (`112`→`105`→`112`). (2) A second
`kbd ff`/`kbd 09` only 50,000 steps after the first landing is ignored: `$227f3` still reads `2`
(jump) and `$00c742` requires idle `0`. (3) Waiting 500,000 steps for idle before the second trigger
fires a real second jump (frame counter: 18 more writes, 35 total), ending at the same on-screen
`x=192,y=112`, undamaged. Those results were read as "the hop nets zero horizontal progress". The 98th
pass showed that reading was wrong: every one of those hops scrolled the level (see below), so the
same on-screen spot was a different world position each time (`$227b6`: `$46c` at
`pass90_wall_192.snap`, `$49e` at `pass96_doublejump_v2.snap`, `$4b4` at
`pass95_realdodge_300k_30khold.snap`).

**`x=192` is the camera-follow trigger, not a wall: airborne pushes past it scroll the level, and that
is how the item is reached (97th pass disassembly, 98th pass live proof).** Three routines:

```
$00c450: clr.b   $227f1.l          ; clear the trigger flag
$00c456: cmpi.w  #$c0,2(A0)        ; A0 = hero: is x > 192 ($c0)?
$00c45c: ble     $c486             ; no -> done, nothing to correct
$00c460: bset    #3,$227f1.l       ; yes -> arm the scroll gate
$00c468: move.w  2(A0),D0
$00c46c: subi.w  #$c0,D0           ; D0 = x - 192 (how far over)
$00c470: move.b  D0,$1883c.l       ; shared shift delta := that excess
$00c476: cmp.b   #$2,D0
$00c47a: ble     $c486
$00c47e: move.b  #$2,$1883c.l      ; clamped to at most 2 px/frame
$00c486: rts

$018f7e: bclr    #0,$227f2.l       ; scroll routine, called once per main-loop pass from $00b254
$018f86: btst    #3,$227f1.l       ; gate armed by $c460?
$018f8e: beq     $18ffc
$018f92: move.w  $227b6.l,D0
$018f98: cmp.w   $227b8.l,D0       ; camera vs. level scroll limit ($227b8 = $1020 here)
$018f9e: bge     $18ffc
$018fa2: addq.w  #2,$227b6.l       ; camera += 2 (the only increment of $227b6)
$018fa8: bset    #0,$227f2.l       ; "scrolled this frame"
   ...                             ; redraw the strip of new tile columns ($18ebe, $1923c, $192d2)
$018ffc: move.b  #$2,$1883c.l      ; delta reset to 2
$019004: rts

$00bb22: btst    #3,$227f1.l       ; per-frame object shift, only if the gate is armed ...
$00bb2a: beq     $bb6c
$00bb2e: btst    #0,$227f2.l       ; ... and the camera actually scrolled this frame
$00bb36: beq     $bb6c
$00bb3a: lea     $1a2ea.l,A0       ; A0 = object array base (all 20 slots)
$00bb40: moveq   #19,D0
$00bb42: tst.w   0(A0)             ; skip inactive slots (type==0)
$00bb46: beq     $bb64
$00bb4a: cmpi.w  #$ff,30(A0)       ; only objects flagged 30(A0)=$00ff (hero and every hazard/item read $00ff)
$00bb50: bne     $bb64
$00bb54: moveq   #0,D1
$00bb56: move.b  $1883c.l,D1       ; D1 = this frame's shared delta
$00bb5c: sub.w   D1,2(A0)          ; x -= delta
$00bb60: sub.w   D1,48(A0)         ; (and a second, parallel x-like field)
$00bb64: lea     108(A0),A0        ; next slot
$00bb68: dbf     D0,#-40 == $bb42
```

So when the hero's `x` exceeds `192`, the camera `$227b6` advances 2px and every flagged object,
hero included, is shifted left by the same amount: the hero stays pinned at `192` on screen while the
world moves under it. The level's own scroll limit is `$227b8 = $1020`, far from the current `$46c`,
so this screen is not at a scroll stop. The 97th pass saw only the `$bb5c` half (the hero's tile-legal
`+2` push reverted to `192`) and read it as a per-frame position correction that no input could beat;
it never looked at `$227b6`.

Two things gate the scroll in practice:

- **Ground-level walking never scrolls.** `watch 227b6` over 400,000 steps of held right from
  `pass90_wall_192.snap` shows zero writes: the forward-sensor tile block (90th pass, category `>=4`)
  stops the hero at `x=192` before any push reaches `x>192`. The camera only advances when a push past
  `192` gets through, which the jump arc's own horizontal add (`$00ccc4`, gated only on the arc's
  tile-forward check `$00cc60`-`$00ccc4`) does.
- **Each hop scrolls a few pixels.** From `pass90_wall_192.snap`, `kbd ff`/`kbd 09` (30,000-step hold)
  then release: `watch 227b6` shows 4 writes (`$46e`,`$470`,`$472`,`$474`), i.e. the camera moved 8px
  and `$227b4` (the tile column counter) stayed `$23`. The two hops behind `pass96_doublejump_v2.snap`
  moved it 50px in total.

**The item on the twin-tree crossbar is collected (98th pass; reproduced byte-for-byte on a second run
of `py/twintree_item_route.repl`).** After the hops the world has scrolled so the crossbar's item
(object-array slot 0, `$1a2ea`, `type=1`, `(138,88)`, radius `16/16`, flag `$00ff`) sits 50-70px to the
left of the hero, who is standing on the raised ground step on the right. From
`pass96_doublejump_v2.snap` (camera `$49e`, hero `x=192,y=112`, `2/18`):

1. Hold left (`kbd ff`/`kbd 04`) 700,000 steps: the hero walks off the step and to the foot of the
   ledge at `x=142,y=144`. **Health drops `2`→`1`** on the way (slot 12's drift path); the route is not
   hazard-free.
2. Jump straight up from `x=132`-`142`: the arc peaks at `y=106`, `18` short of the item's `y=88`. The
   proximity test at `$00b71a` needs `|dy| < 16` (threshold `13(A0)=16`), so `y` must be `<=104` at
   `|dx| < 16`. A straight-up hop from ground level misses the item by 2px of margin and was tried
   first.
3. Up+right hop (`kbd 09`, 30,000-step hold) from the ledge foot lands on the step at `x=158,y=112`,
   idle, `1/18`.
4. Up+left hop (`kbd 05`, 30,000-step hold) from the step: the arc runs from `x=152,y=109` through
   `x=148,y=97` to `x=144,y=91` at 150,000 steps (`y` is `<=104`, and `|dx|=6` against the item's `x=138`), and slot 0's `type`
   word reads `1` at 50,000 and 100,000 steps and **`0` from 150,000 on**. The HUD score reads `000000`
   before (`pass98_onledge.snap`) and `003200` after (`pass98_item_try.snap`); health stays `1/18`
   throughout the hop. The item sprite is gone from the render
   (`coldboot_amazon_twintree_item_collected.png`).

What that proves and what it leaves inferred: the pickup is object slot 0 deactivating on hero
proximity with the score gaining 3,200 (one observation each, deterministic on replay). Not yet checked:
that the deactivation is the generic `$00b71a` test rather than a dedicated pickup handler (a `bpc` on
its write of slot 0's `type` would pin the handler), and what the item is (a `+3200` score bonus versus a
pickup that also changes health, weapon or inventory: health did not change).

**Correction to the 90th-97th pass framing.** "Jump/walk shape can never pass `x=192`" is true only of
the hero's on-screen `x`. "Nets to the same spot" was measured on screen coordinates. Any pass that
compares positions of a pinned camera-follow hero across trials has to read the scroll counter
(`$227b6`) too, or compare against a scroll-independent landmark.

**The dodge does not collect the item (95th pass) — though not for the reason first given.** A
whole-frame pixel diff between `pass90_wall_192.snap` and `pass94_dodge_item_landed.snap` shows
`63,454`/`64,000` pixels identical, with every one of the `546` differing pixels inside the drifting
hazard sprites' own band and the item's own on-screen region byte-identical between the two frames —
that empirical result stands. The *explanation* first given for it (a completed round-trip jump that
happens to land back at its takeoff spot) does not: the frame-counter check above shows no jump ran at
all for this snapshot's delay (`300,000`, in the dead band), so the render match is simply because
nothing moved, not because an arc returned the hero to the same place. Reaching the item still needs a
maneuver that gets the hero up onto the crossbar top and, per the retraction above, off it again before
slot 8 arrives — not yet found by any trial in this pass.

## The level is one tile map of connected rooms (99th pass)

The scroll limit `$227b8 = $1020` is not the end of the level, it is the end of the *first room*. The
Amazon (world index `$bb76 = 3`) is a single 1680-column x 24-row tile map at `$31800` (`amazon_level_map.png`,
rendered by `py/level_map.py`; categories: gold walkable `4`, red hazard `9`, and `1`/`2`/`3` drawn green/blue/magenta, which
line up with the ladders, small ledges and crossbars/diagonal stairs seen on screen; the real-tile overlay in
`graphics.md` confirms `1` ladder, `2` branch-stub ledge, `3` log walkway/stair/bridge and `9` spikes and water, as a
visual correlation) holding many *rooms*. A room is a block
range `[start,end)` of that map (a block is 32px = 4 tile columns; the map has 420 blocks) and only one room is
live at a time:

- `$00c028` (8 bytes per world, indexed by `$bb76-1`) gives the start room: words 2 and 3 are the start
  and end block (world 3: `0`, `137`). `$00018ed4` (called from `$c01a`, `$e04c`, `$e918`) installs a room:
  `$227b4 = start` (afterwards it tracks `camera >> 5` as the room scrolls: `$81` at camera `$1020`), camera
  `$227b6 = start*32`, limit `$227b8 = end*32 - 256` (world 3: `137*32-256 = $1020`),
  and rebuilds the screen from the block map at `$27600` (6 bytes per block column, each byte a 2x2 tile block
  from `$29000`).
- `$00df4a` (per frame) fires when the hero leaves the screen through the top (`4(A0) <= $fff0`, state
  `$227f3 = 2`, direction `D7 = 0`) or the bottom (`4(A0) >= $c8`, `$227f3 = 3`, `D7 = 1`). It searches the
  world's list (`$e0aa` is a 5-entry pointer table; each list is 10-byte records `dir, trigger block,
  dest start, dest end, dest hero block-x`, terminated by `$ffff`) for a record whose `dir` equals `D7` and
  whose trigger equals the hero's block `(x - $20 + camera + 16) >> 5`. On a match it clears object slots
  0-5 and 7-19, sets hero `y = -16` (bottom exit) or `$c8` (top exit), calls `$18ed4` with the destination,
  and puts the hero at `x = (dest block-x << 5) + $20`.
- `py/level_rooms.py <snap>` prints the whole graph. World 3 has 21 exits over rooms such as `0..137`
  (start), `139..156`, `156..161`, `160..173`, `188..285`, `328..378`, `378..409`; room ranges may overlap
  because a sub-room reuses part of a larger room's blocks. The start room has three exits: up at block
  112 (col 448, the gap in the cave ceiling) and down at blocks 131 and 135 (cols 524, 540).
- **Checked live, both directions (two records, forced by poking the hero, not reached by playing).** From
  `cyc5.snap` with the hero poked to camera `$1020`, `x=80`, `y=$d4`, `$227f3 = 3`: after the transition
  `$227b4=$9c`, camera `$1380`, limit `$1320`, hero `x=$60`, `y=-16` -- all five fields the table record
  `(1,131,156,161,2)` predicts, and the render is a rocky cave room (`amazon_room_after_bottom_exit_131.png`).
  With camera `$e00`, `x=40`, `y=-24`, `$227f3 = 2`: `$227b4=$8b`, camera `$1160`, limit `$1280`, hero `x=$80`,
  matching `(0,112,139,156,3)`. The transition's fade routine `$1c3c8` takes several hundred thousand steps before
  the new room is live, so sample well after the trigger. Three exits were later reached with real input (next
  bullet); the block-112 ceiling gap was not.
- **Three exits fired from positions reached by real joystick input (103rd pass, `py/start_room_route.repl`).**
  Staging is poked and labelled: `warp_up112.snap` (room `139..156`) has the hero poked onto the block-151 bottom
  exit, which installs `118..137` (the start room's tail: camera `$ec0`, hero `x=$80`); health is poked to full
  (`w bb74 12120300`) at each segment start because two bees and a frog chase the hero. Everything after that is
  input only. In `118..137`: right along the upper ledge, off its end, right along the floor over a plank bridge,
  up the ladder (world x about 4100), right along the rock top, a hop across the block-131 shaft, right along the
  box top, then off its end into the block-135 shaft. Falling straight down the block-131 shaft instead fired
  `(1,131,156,161,2)` with all five fields matching (hero `x=$c0` at camera `$fc2`, so `x + camera - 16 = 4210`,
  block 131). The block-135 fall began at hero `x=$d8` and drifted to `$e0` at camera `$1020` (`x + camera - 16` =
  4328..4336, block 135): `$227b4=$a0`, camera `$1400`, limit `$14a0`, hero `x=$60`, `y=$90` landed, exactly
  `(1,135,160,173,2)`. In `160..173` the block-168 ladder, a hop right across the block-169 shaft onto the `y=$30`
  ledge and a hop back left onto the block-168 ledge (`y=$10`), then a straight up jump: `y` went `$02`, `$fffc`,
  `$fff0`, and after the fade `$227b4=$bc`, camera `$1780`, limit `$22a0`, hero `x=$60`, `(0,168,188,285,2)`. The
  script replays the whole chain from `warp_up112.snap` and its `room160.snap`/`room188.snap` are byte-identical
  (`cmp`) to the interactively driven runs. What the walk showed about the controls:
  - A 32 px shaft with a 32-33 px rise is crossed by holding up+right (`kbd ff` / `kbd 09`) for 30,000-90,000
    steps from the platform edge, then right only; 60,000 landed at the block-131 shaft, 15,000 fell in. At the
    block-169 shaft all six tries (at the edge and one nudge before it, 30k/60k/90k) landed, and all six mirrored
    left hops (`05` then `04`) landed on the block-168 ledge. The jump peaks 40 px above take-off, so a 33 px rise
    has a 7 px margin.
  - The ladder climb starts when `$227ea` classifies as category 1 (tile ids `$63`/`$64`), but state 4 moves up
    only while `$227ec` and `$227ed` are both category < 4 (`$00cf78..$00cfa0`), and the sensors are recomputed
    only when `y & 7 == 0` (`$00cfe0`). At the first ladder `x=$a6` stalled at `y=$84` with `$227ec` = tile `$d7`
    (category 4, rock beside the rungs); steering right on the ladder to `x=$b0`, stepping down once so `y`
    realigns, then up climbed to the top. At the block-168 ladder `x=$7e`, `$82` and `$86` all climbed unaided.
  - The climb tops out into state 0 when `y` reaches a multiple of 8 with `$227eb` category >= 2 (`$00cffa`, at
    `y=$50` here); holding up past that starts a jump, so release up at the top.
  - Where the hero is pinned at `x=192` only the camera (`$227b6`) shows progress; a nudge of `s 25000` moves
    about 4 px.
- The object spawner reads a 4-byte-record list at `$27200` (sorted, `$7fff` sentinel at `$275fc`; record =
  tile column word, row byte, type byte), walked by `$fe9e`/`$fed6` as the camera advances and calling
  `$10006` (type byte indexes the descriptor pointer table at `$10474`; the descriptor's first byte
  picks one of four slot allocators through `$10046`: `$10056` slots 0-5, `$100ec` slots 7-11). The list's
  columns run to 1664, covering every room of the map. Decoding which type is which enemy or item is open.
- **How a level ends (104th pass; every step below is live-checked, scripts in `py/level_end/`).**
  `$00b1f6` calls `$00fb98`, which watches `$22803`; when bit 7 is set it counts `$22804` up to `$7d` (125 frames). On the
  next frame `$fbcc` writes `$fe`, clears the hero's `105(A0)` and slots 7-11, runs `$f050`, then `jmp $f0ee`. `$f0ee` returns
  early each frame while the hero's `66(A0)` flag is `$c1` (set by `$b704` at `$f15e`), a wait of about 21 frames, then
  `$22800` counts to `$19`; at `$f17e` the routine sets bit (world index - 1) of `$bb79` and returns Z=1, so the main loop's
  `beq $b0b2` fires: 46 `$f0ee` calls and about 1.08M steps from `$fbcc` to `$f188`. `$b0b2` calls `$1c3c8` (a fade of 8 VBL
  ticks), `$1ab5a`, `$1ab6e` and `$b2d8`, which reloads `PICTURES.DCH` (`$fa00` bytes to `$53000`) and `SELECT44.DAT` (`$5000` to
  `$4c400`) and waits 150 ticks at `$1c680`; fade plus reload take 4.26M steps, so from `pass99/boss_kill_end.snap` `$b0ca` is
  hit at step 8,244,047 and `$17c9c` at 8,244,050 (`$fbcc` 2,905,652, `$b0b2` 3,985,684; `agents/wsel/win_amazon.repl`).
  `$b0ca` compares `$bb76` with 5: worlds 1-4 jump to the world-select setup `$17c9c`, world 5 goes `$b0dc -> $b0e8 -> $183c0`.
  - **`$bb79` is a "done or unavailable" mask** (a set bit makes the icon unselectable, and the world-select screen draws a red X
    over it): it starts at `$10` (Bermuda only, set by `$bb7e` at a new game) and the Amazon win gave `$14`. After the `bset`,
    `$f18e` masks `$bb79` with `$f`; if all four low bits are set it does `bclr #4`, which unlocks Bermuda (`$f1a0`, live with
    the mask poked to stand in for three earlier wins: `$bb79` became `$0f`, the cursor moved to icon 4 and fire loaded Bermuda by
    real input). `$17c9c` sets the cursor `78(A0)` to 0 (Klondike); if that icon is locked the loop at `$17f52` steps the cursor
    one icon per frame to the first free one, and `$bb76` is rewritten to cursor+1 every frame. Score `$bb6e` carries over; weapon
    and health reset only when the next level installs (`$b15e` calls `$bbc8`: weapon 1, health := max).
  - **World 5 (Bermuda)**: `$183c0` copies `$25000` to `$53000`, prints the 14-line "CONGRATULATIONS MONTY / YOU HAVE SUCCESSFULLY
    DEFEATED THE FIVE GUARDIANS AND OBTAINED THE SCROLLS OF ETERNAL LIFE ... NOW I WONDER WHAT MY NEXT ADVENTURE WILL BE ?" text
    from `$185e1` (`ending_screen.png`), and loops at `$1847e` until fire, then `$182bc`, the high-score entry (`$19f5a`; name entry
    reached live at `$19dfc`), else `$183b4`, `jmp $b088` and the title (`$17a9e`). No file is opened. The world-5 run poked
    `$bb76` to 5 and the flag, so the ending is proven, the full natural chain (kill Bermuda's boss for real) is not.
  - **Death** is a different path: `$b058` (via `$b2d8`) goes to `$17fe8`, the Game Over screen; fire, or 250 idle frames
    (`$22806 == $fa`), goes `$182bc`, `$19f5a`, `$183b4`, `$b088`, `$b2d8`, then the title, and fire at the title reaches `$17b52`,
    `jsr $bb7e`, `jmp $17c9c`. `$bb7e` zeroes the score, sets max health `$12` (`$22` with cheat code `$bb7d = 1`), `$bb78 := 0`
    and `$bb79 := $10`: all progress is lost on death, and death never returns directly to world-select.
  - **Cheat names**: the high-score name entry compares the typed name with 8-byte names at `$1837e` (`LUMBAJAK`, `HEINZ...` with three full stops,
    `COMMANDO`, `ANNFRANK`, `OOCHOUCH`, `JUGGLERS`) and stores the code 1-6 in `$bb7d`; all six work through the real joystick entry and each effect is
    measured (`secrets.md`: extra health, weapon 3, endless special fire, an extra life, harmless water, double heals).
  - **Boss deaths**: `$22803 := $ff` is written at five sites, one per world (`$014ad6` Klondike, `$015752` Orient, `$01602e`
    Amazon, `$016958` Ice Land, `$0176a6` Bermuda; all five bosses have 60 hit points, `worlds.md` lists the records), each in a
    death block of the same shape (sound `$1c`, write `$22803`, clear `$22804`, `addi.l #$4e20,$bb6e` = +20,000 points, start the death
    animation, `$fc26` HUD redraw) reached by `bsr $13a9c; bcs <block>` from the boss's own handler. All five bosses were killed
    live (the Amazon by real swipes, "Boss" below; the other four with a poked shot position). The level-end chain after the flag was
    run for the Amazon boss's own kill, and from a poked flag for Ice Land (back to `$17c9c`) and Bermuda (`$183c0`); for Klondike
    and Orient only the kill was done, so that their boss deaths end the level is inferred.
- Object slots are live-spawned: at camera `$5ac` the array holds different objects than at `$46c`, so the
  slot numbers used for the twin-tree screen do not carry over.

### The route to the boss room on real input (104th pass)

From `pass103/room188.snap` (room `188..285`, reached by real input) to the boss room, every input is a joystick packet; the driver reads the hero
state each tick (`py/route/route_driver.py`: per tick about 8000 steps it reads x, y, busy flag, `$227f3`, `$227b4/6/8`, health and the
`$227e*` sensors, sends a `kbd` packet only when the wanted bits change, and logs the state-changing commands to a replayable `.repl`).
Health is poked full (`w bb74 12120300`, labelled in the logs) at the start of each of the 17 segments and refilled at 4 or below (three
times in room `188..285`); nothing else is poked. Every segment replays byte-identically (`cmp`), the whole 7397-command chain replays in one
process to the same snapshot, and the live route was run twice from scratch with identical end snapshots
(`py/route/verify_route.py`, `py/route/route_full_real.repl`). The routes, with `wx = x - 32 + $227b6` (map px):

- **Room `188..285` to the block-283 top exit (11 segments, 51.7M steps; hop 3).** Walking is about 2 px per game update (about 25k
  steps), so 20k steps per pixel is a safe budget. (1) Start pillar and totem: a hop right from `wx` 6112 onto pillar 2 (top `y=112`), a second hop
  from `wx` 6154 onto the solid 32 px totem on it (`y=80`), then walk off. (2) A hop right from 6400 onto the dirt plateau (cols 804-811).
  (3) First water pit (cols 812-823, 96 px; a plain jump covers about 43 px): a hop from 6488 lands on a crocodile (spawn type 130, contact damage
  byte 0, effectively a platform); holding right walks the hero across it and it bounces up onto the plateau. (4) Two 8 px deep, 32 px wide floor
  notches with an 8 px lip (cols 848-851, 860-863) stall the hero for good while it is bitten: hop each from the edge (take-off at `wx` <= 6775 and
  <= 6871), the first lands on the crossbar above. (5) Stone-pillar pair: onto pillar 1 from `wx` 7044, walk to 7120, hop the 32 px hole (cols
  892-895, the block-223 bottom exit; falling in leaves the room) onto pillar 2. (6) Four water pits (64, 128, 32, 128 px, cols 908-975): holding
  right is enough, crocodiles at each surface bounce the hero on. (7) Second pillar pair: hop up at 7908, hop the plank gap from 7982. (8) Temple
  stairs: the floor at `wx` 8336-8364 ends in the block-261 bottom exit (cols 1044-1047), so two hops right from 8296 climb the one-way
  log staircase (category 3) to `y=112` then `y=80`, onto the stone roof (cols 1048-1059), and off it to the floor at 8562. (9) Ladder (cols
  1080-1081): stand at `wx` 8634, hold up, release at `y <= 48`; it tops out in state 0 on the `y=64` ledge (`$227eb` not read here). Walk the
  slab top (cols 1084-1107), drop through the gap (cols 1108-1111), land at 8898. (10) From 9036 hop up+left (`kbd 05`, then `04`) onto the
  `y=128` bead platform (cols 1124-1127), walk left to 8988 to align on the second ladder (cols 1124-1125) and climb to `y <= 48`; the camera has
  stopped at its limit `$22a0` here so the hero's own `x` moves. (11) Along the `y=64` ledge to 9012, hop right over the 32 px gap (cols
  1128-1131) onto the `y=64` bead, hop straight up (`kbd 01`) onto the `y=32` bead, jump straight up again: `y` runs 9, 2, -4, -10, -16, the exit fires
  and the fade starts about 130k steps later. Record `(0,283,299,318,3)`: after the fade `$227b4 = $12b`, camera `$2560`, limit `$26c0`, hero
  `x=$80`, `y=$90`, all four predicted fields.
- **Room `299..318` to the block-317 bottom exit into the boss room (5 segments plus a settle, about 9.9M steps; hop 4).** Right along the low tunnel
  (rows 128-159) to the block-304 ladder, which climbs only with hero world x 9718..9722 (at 9714 it stalls at `y=132` with `$227ec = $d7`:
  walk right on the ground to 9720 first) to the row-64 ledge, tops out at `y=48` (release up on that tick or the next input jumps), right over the
  block-305 wall top, down the block-306 ladder (down on the ledge starts the descent, landing `y=144`) back to the tunnel, right to the tunnel wall
  at world x 9900, up+right onto the 32 px ledge (`y=112`) and again onto the rock top (`y=80`), right down the stair tiles onto the grass, and
  right into the pit at block 317: the exit fires when the hero falls at world x about 10148, `(x - 32 + camera + 16) >> 5 = 317`, and the camera
  stops at its limit `$26c0` so the hero walks freely to about x=250. `bp $18ed4` on the replay hits with `D0 = $13e`, `D7 = 1` (bottom exit) and
  `A0 = $1a572`; after the fade `$227b4 = $13e`, camera and limit `$27c0`, hero `x=$20`. The chained arrival matches `pass99/boss_room.snap` in the
  boss (`x=224`, `y=96`, 60 hit points, `$22803 = 1`, handler `$15e9a`) and the room fields; weapon (3, carried) and coins (25) and health differ,
  and the boss animation phase is one tick off.
- **What the route costs in health** (poked run; `py/route/hazard_census.py` runs each step as `bp e82e n` and reads `A0` at every damaging contact,
  `py/route/contact_census.py <snap> <repl>...` does the same for any recorded segment and adds the handler pointer, record byte 86; both leave the run's
  final snapshot byte-identical). There are two decrement sites of `$bb74`: `$eb8c` applies an object contact (`$e82e` writes the contact's damage byte
  to `$227f6`, `$eb86` clears it) and `$ebca` is the category-9 tile path (`$eb42`/`$eb56` branch on `$227e8/9 == 9` with the hero in state 0 or 1, cooldown
  `102(A0) = 3`, subtract 1, force the hit-reaction jump `$227f3 := 2`, which is the "bounce" at the water line). `hits <n> $eb8c $ebca` over the whole
  recorded route (`route_full_real.repl`, 7397 commands, final snapshot identical): **`$eb8c` 96, `$ebca` 9**; up to the block-283 exit 92 and 9, room `299..318` 4 and 0. Contacts in `188..285` (99 at `$e82e`, 98 of damage 1): the chasing bee
  (types 114/115, hp 1) 71, because a poked hero idles in the pits for 12M steps with a bee on it (about one bite per 150-200k steps); killable walkers
  and hoppers (`$015934` monkey hp 8, `$015ac8` plant hp 4, `$01415e/7c` bees) and immune ones (`$015a38` tentacle hp 255, `$0142be` fliers hp 255);
  the crocodile once, damage 0. Room `299..318`'s four decrements are all object contacts while the hero hops at the tunnel wall (wx 9900-9954):
  three from the ping-pong fliers `$0142be` (anims `$22046`, `$22050`, hp 255) and one from `$015c7a` (hp 4, anim `$2205a`). Water costs 1 hp per
  entry at the surface, with no object involved.
- **Unpoked, hop 3 is playable to the block-283 exit** (`py/route/unpoked_hop3.py`; `room188.snap` already holds weapon 3, 25 coins and `$bb74` = `12120300`,
  so the `w bb74 12120300` at the head of the recording changes no byte). A guard that only swipes killable enemies ahead and hops immune ones
  (`natural_hop3.py`) reaches health 18, 15, 14, 12, 10 at the ends of segments 1-5 and dies in the segment-6 pits (eight water hits, two contacts): the
  chaser bee is not the cause (one swipe kills it for good, hp 1 goes to 254, the dying value), but walkers and hoppers that approach diagonally from
  above (`$015934` hp 8 needs three swipes at one per 6 frames and reaches the hero first) cost 8 hp in segments 2-5, and holding right through the pits
  costs one water hit per 43 px arc. Three things fix that, and the result is one recorded input file replayed in a single process (7720 commands,
  final snapshot identical to the live one), with health 11 at the exit:
  - **Segments 1-5 under the `BEST` guard** (`py/route/policy.py`, 2 hp lost: 0, 0, 1, 0, 1). Bee within dx -30..50, dy -40..40 gets a fire pulse with the
    stick turned toward it (the swipe box never reaches above head height, and the bee bites from above and behind: segment 1 goes 3 to 0). A monkey perched
    32-56 px above head height is hit only from the air: stop, jump straight up and fire every 150k steps in flight (three swipes per jump; hp 8, 5, 2,
    dead). A monkey higher still is lured: walk until its dx <= 26 (it triggers and drops), stand and fire up to six pulses. Ablation from the chained
    run: without the bee rule 6 hp are lost, without the snipe 5, without lure-and-kill 3, with all three 2. Not fixed: the segment-3 crocodile drop (1 hp; the
    jaws open about four frames after the landing and the hero falls onto the water tile; two hops via the croc do not fit the 96 px pit) and the
    segment-5 tentacle (`$015a38`, hp 255, triggers at about 32 px, 24-frame cycle with the hit box up from frame 3 to 21; every hop distance tried
    costs 1 or 2 hp).
  - **The four pits at 0 hp** (`py/route/pits.py`, `auto_pits.py`). A pit's crocodile is a platform only while its jaws are shut (entries 10-13, 18-19 and 30-44
    of the 45-entry cycle, tick 3), patrols 1 px per frame between two turn points (pit 1: wx 7261..7298 left edge, 74 frames per round trip, so the
    jaw and patrol phases drift against each other with a 135-frame cycle) and carries the hero at its speed while shut; the hero's left edge
    stays on the back for offsets 5 to about 22 and falls off at 23. The jump's horizontal speed is latched at take-off (`UP` alone jumps straight up, steering
    in the air does nothing), so a crossing is: hop right from 20 px before the pit, land on the croc, walk to offset 17, stand until the croc turns
    (or the jaws have five frames left), hop again. Pit 3 has no croc (32 px, cols 948-951; a take-off from `wx` 7550-7574 clears it, from 7576 the hero has already walked off the last stair step and takes 1 hp). The take-off
    delay is searched by rollout: from a snapshot at the take-off spot, idle W frames (24,000 steps each), cross, and read the hp lost, for W in steps of 6
    over one 135-frame period; the zero-loss windows are pit 1 W 48-78, pit 2 72-84, pit 4 66-84 (chosen middle 66, 78, 78), pit 3 take-offs `wx` 7562-7574 (chosen 7568). The delay
    is a property of the arrival time (the croc's phase runs from when it spawned), so a different arrival needs a new search. The result is recorded input,
    not a policy that reads the croc before it decides.
  - **Segments 7-11 by search** (`segsweep.py`, `wait_opt.py`; guard `natural_hop3.py`). Enemies that spawn as the camera reaches them meet the hero with the
    same phase whatever it did before, so a start delay changes nothing (segments 8-10: every delay loses the same); patrolling ones do change. `wait_opt.py`
    finds the first hurt, then tries standing still for W frames at `hurt_wx - D` (D 32 or 64 px) and keeps the best total. Results: segment 7 0 hp
    (start delay 24 frames, the only zero in the sweep), segment 8 5 hp (waits: one at wx 8526; the monkey `$015934`, leaf bush `$015d9c`, rock `$01439e` and two
    fliers remain), segment 9 0 hp (waits at wx 8600 x18 frames and 8812 x24; the fliers `$0142be`), segment 10 0 hp (wait at wx 8996 x24; `$015b3c`), segment 11
    0 hp. Health at the ends of segments 5-11: 16, 16, 16, 11, 11, 11, 11.
- **Unpoked, the whole Amazon from room `188..285` to the dead boss** (`py/route/route_hop4.py`, `py/boss/boss_unpoked.py`): one recorded file of 12,032
  commands (`agents/unpoked/amazon_unpoked_room188_to_boss_dead.repl`: hop 3, hop 4 with the shop, the boss fight) replays in one process from
  `pass103/room188.snap` in 3 min 19 s to a snapshot byte-identical with the live one (`agents/unpoked/boss/kill_d900000_end.snap`; the only `w` is hop 3's
  no-op `w bb74 12120300`). At the end the boss is at 0 hit points, `$22803 = $ff`, health 10, weapon 3, coins 25.
  - **Hop 4 costs 2 hp** (`route_hop4.py --guard none`, 1237 commands from `s11/seg11_shaft_exit.snap`, replay identical): health 11 at the room start, 9 in the
    boss room. The two contacts are during the hops at the tunnel wall: a flier `$0142be` at wx 9900 (onto the 32 px ledge) and a flier plus `$015c7a` at wx 9932
    (onto the rock top); the poked run's four contacts (above) become two here, presumably because the fliers' phase differs with the different arrival time. The heal pickup of
    block 302 (spawn column 1208, object `(128, 88)` on the `y=96` log ledge over the start) is not taken: a straight jump peaks at hero `y=104`, one row short of the
    pickup box (health unchanged), the ledge is reached by the left ladder (cols 1200-1201), and the two `$015b3c` fliers (hp 255) beside the start cost 3 hp on the
    way there in the one trial run (11 to 8), so a search over their timing would be needed for a gain of at most 7.
  - **The shop heals what hop 4 cost** (`route_hop4.py --shop`: seg1-4, then seg6-10, then seg5, all no poke, chain replay identical). The natural coins (25 in `room188.snap`, 100 after hop 3) buy one worm can (75): `$bb72..75` `03 64 09 12` to `03 19 10 12` (weapon 3, coins 100 to 25, health 9 to 16 of 18). The mole climbs out for
    about 1.1M steps, `DOWN` on it installs blocks `410..418`, the can is at hero `x=158`, fire once (45,000 steps), leave at the keeper by fire; the return room
    is `308..318` at wx 10080, and seg5 walks on to the pit. Boss room with health 16.
  - **The damage-7 shot is a lob that flies toward the hero's side** (`$016184`, verified by a live probe of 400 samples, `py/boss/shot140_probe.py`).
    At its first call the handler takes `rand & 1 + 1` as the horizontal speed `16(A0)` (1 or 2 px per frame, `jsr $bef4`) and sets the direction `20(A0)` to
    the hero's side of the shot. The shot spawns at the boss's mouth (x 231 for the boss at 224, y 121), rises to y 108 in 8 frames, then falls 1, 1, 1, 1, 2,
    2, 2, 3, 3, 4 px per frame to y 164 on frame 27 (the earlier "(-2, +4) per frame" is only the tail of the fall). Speed 1 was measured; speed 2 is read from the code and matches
    the hits (hero x 172 to 192, boss at 224): a shot of speed 2 crosses the hero's row at x about 187 on frame 22. So the hero on the platform is inside the
    sweep when the boss stands at 224, and outside it (x >= 176 against a sweep ending at x 125) when the boss stands at 64. Hero hit box `(x+8, y, 16, 24)`.
  - **The fight** (`boss_unpoked.py` on `boss_fight.py`'s `Fight`): when the boss is at 224 the hero fights from the platform as before (hop over the step,
    straight jumps, swipes only while the boss is open and the hero is in the swipe model's window); a grounded hero within 80 px of a live 140's spawn point
    walks away from it until it is gone (walks are cut short the moment a 140 appears); when the boss is at 64 the hero waits on the platform out of the sweep.
    Twelve start delays (0 to 1,100,000 steps, the boss's random phase) from health 16: one kill (delay 900,000: 20 hits, 25 pulses, 14 jumps, 3 retreats,
    15.65M steps), the other eleven die with the boss at 30, 3, 27, 18, 48, 18, 12, 42, 30, 60 and 30 hit points. From health 9 (no shop) the same policy
    never killed in 18 runs (best: 9 hit points left; without the retreat, 36 to 39 in all six delays, dead within 3.7M steps). The 140 costs 7; the
    aimed 139 and the boss's contact cost 1 each, roughly one per 1.5M steps (read from the damage logs) that this policy does not dodge. The fight is therefore feasible unpoked and
    marginal, as the earlier "2 of 12" with a poked weapon and full health suggested; a controller that also dodges the 139 (a flat shot aimed at the hero's
    position at spawn, 3 px per frame) and fights the boss's left position from the right side would raise the rate.
- **Controls learned.** The jump starts on the game's next joystick poll, 24-30k steps after up is pressed, so the driver holds up+direction until
  the state reads jump and then the direction only (apex is always 40 px); a full jump and fall takes about 1M steps; stairs and bead platforms
  are one-way (a hop from below lands on top); holding up+right on stairs re-jumps at every landing, so use single hops; read an obstacle's height
  from the `$25000` map first (totems and pillars are 32 px, one hop; the temple slab leaves 8 px); `x` reads jitter by 2 px while the camera scrolls,
  so use `wx` progress with a tolerance for stall detection.

### Boss (99th pass)

- **The Amazon boss is the only kind-2 spawn record of its level** (every world has one, `worlds.md`): type byte `138`, column 1296 (block 324), `y=120`, in
  the dead-end room `318..326` (8 blocks, 256px, no exit of its own). `py/spawn_list.py <snap>` prints the whole
  list (256 records: 119 kind-0 allocations, 135 kind-1 and this one kind-2; world 3's own types are 105-132,
  types 0-9 are small props and 63 records are type 251, all kind 0). The route from the start room is four exits, from
  `py/level_rooms.py <snap> --route 318 326`: fall through the bottom at block 135 (`0..137` to `160..173`),
  leave through the top at block 168 (to `188..285`), leave through the top at block 283 (to `299..318`), fall
  through the bottom at block 317 (to `318..326`). The last hop was forced live: `$227b4=$13e`, camera `$27c0`,
  hero `x=$20`, exactly the record `(1,317,318,326,0)`. The whole route was later played with real input from the
  start room's tail (see "Three exits fired..." above and "The route to the boss room on real input" below).
- **Spawning it**: descriptor kind 2 selects allocator `$01021a`, which plays sound `$1f`, sets `$22803 := 1`
  ("boss alive"), and builds the boss in slot 7 (`$1a5de`; type word from the per-world table at `$10370`,
  world 3: `3`) plus up to four extra parts in the following slots. Its per-frame handler is
  `$00015e9a` (`hits` 125 over 3M steps). Render: a giant tree face on a trunk (`amazon_boss_room.png`).
- **Boss data (descriptor `$11aee`, bytes 5/6 to `103`/`104`)**: `103(A0)` = hit points = `$3c` (60, read
  live at `$1a645`), `104(A0)` = contact damage 1. Its hit box is 12-14(A0) = `$20`/`$30`/`$18`.
- **The projectile-vs-enemy damage path exists and is `$0013a9c`.** An enemy handler calls it each frame
  (`bsr $13a9c`, boss at `$15eae`); it loops over projectile slots 16-19 (`$1a9aa`, skipping any whose
  flag word `30(A1)` is not `$ff`), runs the `$b71a` proximity test against each, and on contact does
  `103(A0) -= 104(A1)` at `$013b20`, where `104(A1)` is the projectile's damage, the equipped-weapon index
  `$bb72` (README, weapon system). It then sets a short invulnerability count in `102(A0)` and, at
  `HP <= 0`, sets `101(A0) := 1` (`$13b4c`) and returns carry. **Live**: with `$bb72 = 2`, one projectile
  placed on the boss dropped `$1a645` from `$3c` to `$3a` (write PC `$13b20`, 1 write, watch); further hits
  gave `$32`, `$26`, `$16`, `$10`, and `py/boss_kill.py` took it to `0`.
  That first proof placed the shot on the boss by a poke; natural aim is proven separately, next bullet.
- **Natural aim (104th pass, `py/boss/`).** There is no flying projectile: the "shot" is a static melee swipe. The fire handler
  `$d37c` (per frame from `$d2be`) fires on the fire-bit rising edge if `$227f3 < 3` and the cooldown `$227fd` is 0; `$d3cc` copies
  the weapon row `(weapon-1)*64` of the table at `$d4be` (weapons 1-3 only; `$d4be+192` is the mirror-x word table `$d57e`) into
  slots 16-19. Only slot 16 is a hit box (`30(A1) = $ff`, `104(A1) = $bb72`); slots 17-19 are decoration. The swipe never moves: its
  position is the hero's x/y plus the row offset at the moment of firing (plus the mirror word when `$227f4 != 0`), it is cleared when
  `$227fd` (set to 6, one count per frame) reaches 0, so it lives 5.0 frames, and it hits at most once (`101(A1) := $ff`). One frame
  is 24,000 steps in this room. Rows for slot 16 (dx, dy, w x h; mirror dx facing right): weapon 1 `-6, 8, 16x16; 28`, weapon 2
  `-12, 4, 24x24; 32`, weapon 3 `-20, 0, 32x32; 40` (`py/boss/swipe_check.py`: 108/108 predicted positions, weapons 1-3, both facings,
  standing and airborne). The test is `$b71a`, an AABB on `x+8(A)`, `y+10(A)` with widths `12(A)`, `13(A)`; the boss box is
  `x=bx, y=96, w=32, h=48`, so the swipe overlaps when `shot.y + h > 96` and `shot.y < 144`: hero `y` in (72, 136) for weapon 1,
  (68, 140) for weapon 2, (64, 144) for weapon 3. A standing hero has `y` 144 or 152 and misses (weapon 3 from the raised platform
  by exactly one row), so **only a jumping hero hits the boss**, from the first rise step. In x the hero must be beyond 186 (weapon 1),
  180 (2) or 172 (3) when the boss is at `bx = 224`; a walking hero stops at x=172 against an 8 px step (the platform, `y=144`, runs
  from about x=176 to 260), so the hero hops it with up+right (`kbd 09`, ballistic, x 172 to about 206, peak about `y=112`) or stands on
  the platform at x 176-200 and jumps straight up. At `bx = 64` a straight jump works from the left zone (hero x in (20, 76) for weapon 2).
  Controls: grounded at x=172, straight jump at x=172 and standing on the platform gave 0 hits in 30 real pulses; a hop onto the
  platform gave 8 hits in 8 pulses for weapons 2 and 3. **Kills with real fire input and no shot poke**: weapon 1 in 60 hits,
  weapon 2 in 30 (37 pulses, 22 jumps, 24.4M steps), weapon 3 in 20 (`py/boss/boss_fight.py`, `watch 1a645` shows each hit as one
  `$13b20` write); after the kill `$22803 = $fe`, `$22804 = $7d` and the level-end chain runs as above (`$b0b2` at 3,946,651). Damage per
  hit is `$bb72`, which only takes 1-3 (`$bbc8` resets it to 1, the upgrade pickup `$12e50` adds one, capped at 3; spawn type 4, two
  records in the Amazon at blocks 27 and 134); there is no ammo (`$bb73` is a separate item counter, `$13044` adds 25, `$fd4c`
  subtracts 5). Weapon and health pokes were used in most runs; with health unpoked and the weapon poked to 3, 2 of 12
  phase-varied runs killed the boss (finishing at health 1), with weapon 2 none of 6. With no poke at all and a retreat from the 140 the fight was won
  in 1 of 12 timings ("Unpoked, the whole Amazon", below), so it is feasible and marginal.
  The boss attacks with contact damage 1 while open (`104(A0)`; measured 18 to 17 with no shot alive) and two projectiles from its script:
  byte 3 spawns type 139 (`$15f5a`, handler `$14790`, 12x12, damage 1, aimed at the hero's position at spawn, about (-3, +1) per
  frame) and byte 4 type 140 (`$15f76`, handler `$16184`, 16x12, damage 7, a lob toward the hero's side, path in "Unpoked, the whole Amazon"). An idle hero at x=32 dies
  in about 9.2M steps. Heal pickups (type 5, heal `4 + $bb76`) sit at blocks 46, 140, 244, 302, 413 (two records).
- **The boss cycles between two animations**: `22(A0) = $221f6` (mouth closed; `$15ea2` skips the hit check
  entirely, so it is shielded) and `$221d0` (open, vulnerable), each a script step (`94(A0)` script pointer,
  a step every 10 frames; script byte 5 selects `$221f6`, byte `$ff` ends a script, `$15fd0` then moves the
  boss `x` by `table[rand&1]*8` from `$16132` (bytes `00 14`: 0 or +160, minus 320 when the result is `>= $120`, so `x` is only ever
  `224` or `64`) and picks one of four scripts from `$16134`).
  A fixed aim point therefore stalls (60 to 16 hit points, then nothing for ten million steps in the first
  attempt); `py/boss_kill.py` reads the boss's `x`,`y` and animation each pulse and only places the shot
  while the animation is `$221d0`; the real-input driver `py/boss/boss_fight.py` does the same with hero position instead of a poke.
- **Death**: `bcs $16024` (`$15eb2`) plays sound `$1c`, sets `$22803 := $ff` at `$01602e` and starts the
  death animation `22(A0) = $22306` (set only by `$016040`). Live: after `boss_kill.py` HP `0`, `$22803 = $ff`,
  anim `$22306`, `$22804` counting (`boss_kill_end.snap`). The 125-frame count, `$f0ee` and the jump to `$b0b2`
  were checked separately with the flag poked to `$ff` (`$22804` counted `1`..`$7d` at `$fbb4`, `$fbcc` wrote
  `$fe` at step 137,916,201, `$f050` 1 hit, `$f0ee` 46 hits, `$b0b2` 1 hit at 4,081,686); the world-5 branch
  and the return to world-select (`$17c9c`) were reached later (the fade plus reload take 4.26M steps after `$b0b2`, "How a level
  ends" above).
- **The other four `$22803 = $ff` writers** (`$014ad6`, `$015752`, `$016958`, `$0176a6`) sit in the other worlds' boss handlers
  (Klondike, Orient, Ice Land, Bermuda; `worlds.md`), each killed live with a poked shot position.

### Spawn types (103rd pass)

`py/spawn_types.py <snap> [--sheet out.png] [--check]` decodes the descriptor of every type in the spawn list and
draws its frames (`graphics/amazon_spawn_types.png`, one row per type). A type byte indexes `$10474`; the
descriptor's first byte is the allocator kind (`$10046`), and the two allocators that matter read it as follows
(read off `$10056` and `$100ec`, and matching the live objects they build):

- **kind 0** (`$10056`, object slots 0-5, object type word 1 so bank 1): `+1` height, `+2` animation tick count,
  `+3` to `79(A0)`, `+4` long = animation list. Pickups and props; no hit points.
- **kind 1** (`$100ec`, slots 7-11): `+1`/`+2` to `12`/`13(A0)` (the hit-box radii), `+3` to `20(A0)` (the initial horizontal direction byte,
  which also selects the entry pointer in the table at `+24`, 4 bytes each, zero-ended: entry 0 faces left, entry 1 right), `+4` to `21(A0)` (the
  initial vertical direction byte, 0 = up, 1 = down; not an animation pointer), `+5` tick count, `+6` hit points to `103(A0)`, `+7` contact damage to
  `104(A0)`, `+8` word = the object's type word (1: bank 1, 16x16; 2: bank 2, 32x24), `+10`/`+12` words to `8`/`10(A0)` (the hit-box offsets; `+12`
  plus `+2` is also the row count `14(A0)`), `+14`/`+16` words to `16`/`18(A0)` (speeds in pixels per frame, x and y), `+18` word to `106(A0)` (the score
  awarded on a kill), `+20` long = per-frame handler to `86(A0)`, `+32` the entry pointer that some handlers read as a period (low word) or a byte-script
  pointer. An animation pointer addresses a run of sub-animations, each a list of frame words ended by `$fffe` (loop), `$fffd` (hold the last frame),
  `$fffc` (jump, long follows) or `$ffff` (end and free the slot), so a frame list is read up to its first control word and the lists that follow in memory
  belong to other objects. Kind 2 is the boss (`$1021a`). **Kind 3** (`$1037a`, slots 12-15) is the allocator of objects that handlers spawn
  (`$01366e`, type in `D3`): `+1`/`+2` radii, `+3`/`+4` to `20`/`21(A0)`, `+5` tick, `+6` contact damage, hit points `103(A0) := $ff` (immune), `+8`
  type word, `+10`/`+12` hit-box offsets, `+14`/`+16` speeds, `+18` long = handler; the Amazon spawns types 52 (monkey drop, `$0147e6`), 135/136
  (chameleon tongues, `$015e54`), 137 (plant spit, `$014790`) and 141 (coconut, `$016210`), and none appears in the spawn list.

What each Amazon type is (`hp` and `dmg` are the descriptor bytes; the picture is the decoded first frames, checked against the live screen where a
live object existed; `py/spawn/` proves each behaviour with a match count, listed below the table):

| types (count in the level) | kind | picture | hp / dmg | handler | live check |
|---|---|---|---|---|---|
| 105, 106, 107, 108 (10, 10, 6, 8) | 0 | fruit: watermelon slice (175), banana (176), grapes (177), green apple (178); scores 400, 800, 1600, 3200 (`$130f2`) | none | none | slot 0 frame 175 144/144 (`pass103/live_c3.snap`) |
| 1-8 (4, 3, 3, 2, 6, 2, 1, 1) | 0 | small items: bomb (132), two grey pipe/boot pieces (130, 131), barrel (129), tin with an S (134), pot (135-140), spinning gold coin (141-146), book (133); items 1, 3, 5, 7 are the shop's goods | none | none | frames only |
| 251 (63) | 0 | invisible fruit container: a blank frame (list `$2270a` = `[0]` hold); a shot releases a fruit | none | `$017982` | live, see below |
| 0, 9 (1, 1) | 1 | the mole climbing out of the ground (bank 2 frames 62-70), at block 416 and block 313 (the room before the boss room): the shop keeper and the shop's entrance, see "The shop" | 0 / 0 | `$00e842` | live (`shop_mole_in_shaft.png`, `shop_room.png`) |
| 109 (7) | 1 | stone slab piston (frame 137, its only animation is `[137]` hold); a solid child block in slots 12-15 absorbs shots | 254 unused / 0 direct | `$013cb4` | frame 137 192/192 (`live_c20`); 130-frame cycle, crush 18 to 16 to 14 |
| 110 (11) | 1 | monkey (131-136, 159) | 8 / 1, score 200 | `$015934` | trigger, fall and throws at frames 26, 42, 58 |
| 111 (10) | 1 | tentacle rising from the ground (100-104) | 255 / 1 | `$015a38` | trigger 12/12 |
| 112 (7) | 1 | walking, spitting plant (115-128) | 4 / 1, score 800 | `$015ac8` | frame 121 308/339 (`pass99/cyc4`); patrol and spit |
| 113 (12) | 1 | falling rock trap that crumbles (107-114) | 255 / 2 | `$01439e` | frame 107 566/566 (`live_c1`); fall and crumble |
| 114, 115 (8, 6) | 1 | bee facing left (129, 130) or right (170, 171), wanders (114) or chases (115); score 100 | 1 / 1 | `$01415e`, `$01417c` | type 114 frame 171 415/415 (`box_edge`); type 115 frame 130 491/491 (`live_c13`); 20/20 picks, 160/160 chase calls |
| 116-125 (3+6+1+1+1+5+6+5) | 1 | brown winged flier (bank 1 frames 168-173) on a scripted or ping-pong path | 255 / 1 | `$015b3c` (116, 117), `$0142be` (118-125) | 1,364/1,364 per-frame positions of six live fliers |
| 126, 127 (18, 10) | 1 | green snake (bank 1 frames 164-167): 126 falls off ledges (score 400), 127 patrols (score 200) | 4 / 1 | `$015c7a`, `$015c82` | type 127 frame 166 188/188 and frame 164 173/173 (`live_e2`), frame 167 173/173 (`live_c22`); type 126 best 67/173 (`pass99/cyc6`) |
| 128, 129 (6, 2) | 1 | chameleon (146-149, 153-156) that shoots a tongue (150-152, 157, 158) | 255 / 1 | `$015ca6` | type 128 frame 147 389/389 (`live_c22`); type 129 frame 153 389/389 (`room160`), frame 155 389/389 (`live_e2`); trigger 17/17 |
| 130 (5) | 1 | crocodile in a water line (138-145), a rideable platform | 254 / 0 | `$015d26` | hero landed on the shut back twice |
| 131, 132 (1, 2) | 1 | leaf bush (105, 106) that walks (131) or ambushes (132); score 1600 | 10 / 1 | `$015d82`, `$015d9c` | handler swap only (no live object exists) |
| 138 (1) | 2 | the boss: eyes (160-165) and mouth shapes (166-169) | 60 / 1 | `$015e9a` | the boss room render, 99th pass; killed by real swipes |

**Hit points 254/255 mean immune.** `$013a9c` (`A0` = the enemy) returns at once if the enemy is dead (`101`) or invulnerable (`102`); otherwise it
tests each shot in slots 16-19 (`30(A1) = $ff`; a spent shot, `101(A1) != 0`, is skipped unless `79(A1) = 1`, the special-fire shots) with `$b71a`. On
contact it clears both contact links, marks an ordinary shot spent (`$013b0e`), and then `tst.b 103(A0)` / `bmi $013b3e` skips everything below when bit 7 is
set (hit points 128 to 255): the shot is absorbed and does nothing, no invulnerability count starts. Otherwise `$013b20 sub.b D1,103(A0)` (`D1 = 104(A1)`,
the weapon index) and `ble $013b4c` on a kill. A non-lethal hit sets `102(A0) = max(3, $227fd)`; the lethal path `$013b4c` sets `101 := 1`, zeroes `16/18`, loads
the death animation from entry 3, plays sound `$1c` (list `$2195a` or `$21b6c`) or `$013be6[world-1]`, adds `106(A0)` to the score `$bb6e` (bee +100, plant
+800) and redraws the HUD (`$fc26`). Live (`py/spawn/immune_shot.py`): 8 immune objects (types 116, 117, 125, 113, 111, 129 at hp 255, 130 at 254, and 109's child
block) reached the hp test with 0 subtracts and the shot still consumed; controls: a bee (hp 1) dies with 1 subtract, a plant (hp 4) goes to 3. An immune
enemy is removed only by its own script (the rock crumbles when it lands or touches the hero) or by leaving the screen window (`$012bba`: x outside 0..`$130` or
y outside -16..`$c8` clears the slot).

**Common machinery** (read off the code, most checked live). Handlers of slots 7-11 run from `$012ba8` while `101 = 0`; the generic pass `$0b4de`, once per
frame after every handler, moves each object (x by `16(A0)` in the direction of bit 0 of `20(A0)`, 0 = left; y by `18(A0)` by bit 0 of `21(A0)`, 0 = up) and
animates it, skipping both while `100(A0) != 0` (a freeze counter). `$e80e` is hero contact (`$227f6 := 104(A0)`; the hero loses that much at `$eb80` and is
invulnerable for 7 frames). `$e5a0(D0,D1,D2,D3)` is the proximity trigger: the object is shifted by (D2, D3), the hero gets a virtual box (centre offset
(-D0, -D1), half sizes `2*D0+$20` and `2*D1+$18`) and `$b71a` runs; `$b71a` passes an axis when `d = centre(A0) - centre(A1)` satisfies `0 <= d < half(A1)` or
`-d < half(A0)` (36/36 live results for tentacle, chameleon and rock, `trigger_scan.py`). `$136a8` turns the object at a solid tile (category >= 4) at the leading
edge, `$139ae` flips `21(A0)` at solid tiles (category >= 2) above or below, `$131c8` = `$013870` (turn at x < `$20` or > `$108`) + `$136a8` + a turn when the tile under
the leading edge is not ground, `$013270` = `$136a8` + falling off ledges (no ground under the box centre: `21 := 1`, `18 := 2 x 16`, `16 := 0`, landing snaps y to a
multiple of 8). One frame is about 23,400 steps here.

Behaviour of each type (frames, offsets and scripts are read from the descriptor and handler; the live column of the table gives the proof):

- **109, stone slab piston (`$013cb4`).** Rests 25 frames (`$013f88[world-1]`: 25 for worlds 1-4, 15 for world 5), creates a solid child block in slots 12-15
  (hp `$ff`, absorbs shots), then moves down by 1,1,1,1,2,2,2,3,3,4.. per frame (`$013f5c`) until its y is a multiple of 8 with a solid tile below (observed y 40
  to 64 in 11 frames), retracts along the same table (11 frames) and rests again: period 47 frames. When the thrust ends (sound `$1d`) a hero touching it takes 2
  damage (`$227f6 := 2`, hurt animation `$218ae`); while it moves it also pushes the hero sideways (`$b804`, static reading only). Live: the cycle over 130
  frames and the crush at two consecutive thrust ends (`slab_crush.py`, health 18 to 16 to 14).
- **110, monkey (`$015934`).** State 0 perched (entry 0 `$21fd6`, frames `[131,132,133,132]`), waiting for the hero in the box dx (-30, 22), dy (-24, 152).
  State 1 (frame 134, `$21fe0`) falls along the script `$15a22` until `$01359c` finds ground; state 2 (`$21fe4`, frames 135, 136) stands and throws: when `82 & 15 = 0`
  and `$15a14[82>>4]` is 1 (82 = 16, 32, 48, 128, 176, 192 of a 224-frame cycle) it freezes 7 frames on frame 159 and spawns type 141 (coconut, `$016210`, damage 1,
  lobs toward the hero's side at 1-2 px per frame until a wall, ground or hero hit). Death (entry 3 `$21b6c`) drops type 52 (`$0147e6`), a pickup that adds 25 to
  `$bb73` (max 250, sound `$19`). Live: throws at 82 = 16, 32, 48, the seven-shot kill and `$bb73` 0 to `$19`; later throws are static readings.
- **111, tentacle (`$015a38`).** One animation `$21fee` (tick 3): `[62,62,100,101,102,103,104,103,102,101,100,62..]`, frame 62 blank. At the second blank frame it
  freezes until the hero is in the box dx (-34, 26), dy (-40, 24) (`$e5a0(8,8,0,-8)`), then rises; blank it does nothing (no shot test, no contact); up, its hit box
  grows upward (y offset 13, 10, 6, 4, 0, half height 11, 14, 18, 20, 24 for frames 100-104), damage 1, sound `$0c` at frame 100.
- **112, plant (`$015ac8`).** Walks at 2 px per frame with `$0131c8` (`$22010` frames 115-120 left, `$2201e` 122-127 right, tick 2); each frame with probability 1/64
  (`rand & $3f = 0`) it stops for 30 frames on frame 121 or 128; at freeze count 15 it spawns type 137 at (x + 16 x dir + 2, y + 4), aimed at the hero's position at that
  moment, 3 px per frame along a straight line (`$b704`), removed on arrival or at a wall (`$13a46`). Live: patrol x 112..190, a spit from (140, 116) to (201, 121).
- **113, rock trap (`$01439e`).** Waits for the hero in the box dx (-32, 24), dy (-24, 88), shakes by 2 px (left, right, right, left, left, right, script `$143e2`), falls
  with speeds 1,1,2,2,3,3,4,4..; `$013544` kills it at a solid tile under its bottom edge; touching an unhurt hero does damage 2 and kills it at once (`bsr $13b4c`).
  Death `$22036` frames 108-114, sound `$2b` in world 3. Live: fall y 16 to 36 then the crumble, slot freed 14 frames later; a hero in its path 14 to 12.
- **114, 115, bees (`$01415e`, `$01417c`).** 114 wanders: `$0138dc` mode 2 picks one of eight compass headings (`$00ba8e`) every 24, 32, 40 or 48 frames at speed 2; 115
  chases: `$013602` -> `$b932` every fourth frame, speed 2 toward the hero on each axis where the centre distance exceeds 2. Both flip `20/21(A0)` at walls; the animation
  entry is `20(A0)` (`$22194` frames 129/130 left, `$2219a` 170/171 right); hit box 26 x 20. Live: 20/20 picks against the table, 160/160 `$b932` calls and 40 recomputes.
- **116-125, fliers.** All ten: hp 255, damage 1, hit box 16 x 16, score 0; animation entry `20(A0)` (`$22046` frames 168-170 left, `$22050` 171-173 right). 118-125
  (`$0142be`: `bsr $13a9c; addq 82(A0)`; at `82 == +34` word, `82 := 0`, `eori.w #$101,20(A0)`, reload the animation; `bsr $e80e`) ping-pong along their speed vector for P
  frames each way (the +34 word is the low half of the entry slot +32): 118 left/down (0,1) P 30 (1 record); 119, 120 no records; 121 left/up (1,0) P 30 (1); 122 left/down
  (0,3) P 20 (1); 123 left/down (2,2) P 30 (5); 124 left/up (2,2) P 30 (6); 125 left/up (3,0) P 20 (5). 116, 117 (`$015b3c`: `bsr $13a9c; bsr $013308; bsr $e80e`) follow byte
  scripts: entry +32 points to a speed script (indexed by `82(A0)`) and a direction script (by `84(A0)`), one entry per frame, `$fe` restarts, `$fc` replays backwards with
  the direction bits mirrored; direction code bits 0-1 vertical (1 up, 2 down), bits 2-3 horizontal (4 left, 8 right), the speed byte applying to every axis it moves
  (`$013508`). 116 (`$15b4e`) is a clockwise rectangle 30 x 45 px, period 90 frames (speed 3 x15, 0 x10, 3 x10, 0 x10, 3 x15 ...; down, left, up, right); 117 (`$15c0c`) goes down
  three 30 px steps with pauses and back up, period 100. Live (`py/spawn/verify_fliers.py`, synchronised at `$b4de`, camera delta subtracted): 125 418/418, 123 92/92, 124
  36/36, 116 418/418, 117 (slots 9 and 11) 418/418 each; 118, 121, 122 share the handler 118-125 (inferred).
- **126, 127, snakes.** `$015c7a` (126) is `$013270`: walks at 2 px per frame, turns at walls only and drops off ledges; `$015c82` (127) is `$0131c8`: turns at walls, ledges and
  the screen edges. Frames `$2205a` 164/165 left, `$22060` 166/167 right; death `$2195a`. 127 live (turns at 266 and at a wall at 64); 126 by a handler swap only.
- **128, 129, chameleons (`$015ca6`).** Idle entry 0 (`$22066` for 128, `$2208c` for 129: frames 146-148 and 153-155); while `78(A0) = 0` and the hero is in front (129: dx 0..64,
  dy -32..24; 128: dx -64..0, dy -32..24; `$e5a0(8,8,+-32,-8)`) it starts the tongue: `78 := 25` (cooldown per frame), entry 1 (`$220b2` / `$220c4`, six ticks of frame 149 / 156,
  then `$fffc` back), and spawns type 135 (left) / 136 (right) (`$015e54`, frames 150-152 / 157, 158, 152, damage 1, hit box by frame from `$015e76`) 32 px in front. Body contact
  also does 1 damage. Live for 129: the tongue in the first frame, cooldown 25, a second tongue after a 37-frame period; 128's rule is the mirror (inferred).
- **130, crocodile (`$015d26`).** Walks 1 px per frame in a water line (`$013870`, `$136a8`) between two turn points (the pit-1 croc: left edge wx 7261..7298), jaw animation entries
  `$220d6` (left) / `$22132` (right; 45 entries, tick 3, the entry index carries across a turn); frames 140/144 (jaws shut) are entries 10-13, 18-19 and 30-44, the rest are 138/139,
  141/142 or 143/145. Spawn records sit at cols 910, 932 and 968, one in each of pits 1, 2 and 4. Only on frames 140/144
  (jaws shut) does it call `$e5fe`, the moving-platform routine (a hero falling onto it with the feet 0..8 px above its top gets `$227f9 = 1`, `$227a0` = the object and is carried at
  its speed); on other frames a riding hero is dropped (`clr.w 16(A1)`, `$cb2e`, static). Damage 0.
- **131, 132, leaf bushes.** `$015d82` walks at 1 px per frame with `$0131c8` and pauses 48-96 frames with probability 1/64 (`$13988`); `$015d9c` is frozen until the hero is in the box
  dx (-78, 38), dy (-24, 24) (`$e5a0($20,0,-16,0)`), then walks at 3 px per frame. Their only animation is `$2218e` (frames 105, 106); nothing turns into a bee.
- **251, fruit containers (`$017982`, called for every slot 0-5 at `$012e0e`).** A kind-0 object with descriptor `+3 = 9` (`79(A0) = 9`), blank, list `$2270a`. Touching it does nothing (entry 9 of
  `$012e22` is `$012e4a`, `move #1,CCR; rts`; 26 contact passes, unchanged). `bsr $013bec` is the shot test (slots 16-19, `$b71a`; carry on a hit, the shot marked spent); on a hit `clr.w
  0(A0)` removes the marker and `bsr $01366e` (D1 = D2 = 0) spawns type `$0179d8[(world-1)*4 + (rand & 3)]` (10-13, 59-62, 105-108, 146-149, 198-201; the Amazon's four are the fruit)
  at the marker's x, y with `78(A0) := 1`; such a fruit (`79 = 8`) hops (`$017a72`: up 8,4,4,3,3,2,2,2,1,1,1,1 then down 1,1,2,3,4) until it lands (`$0179ec`), then `78 := 0` and it is a
  normal pickup. Records sharing a column and y are stacks (3 at col 904, y 168): an ordinary shot pops one marker (the shot is spent), the special-fire shot (`$227fa` = 1, `79(A1) = 1`,
  `cmpi.b #1,79(A1)` in `$013bec`) pops the whole stack in one frame. Nothing creates markers at run time (no code spawns type 251; `$0179d8` does not contain it), so they are placed by the
  level. Live: three markers, one pulse each (shot position poked), 3/3 replaced by fruit with `hits` `$01799c` x1 and `$01366e` x1 each and a control shot 0 and 0; natural shots
  (hero position only poked): 5 pulses removed 3 markers; a stack of 3 in mode 1: one shot, 3 to 0 markers; mode 0: 3 to 2 to 1 to 0.

Not proven: 118, 121, 122 (and 119, 120) have no live object, 131 and 132 none at all; 128's trigger was not fired live; 109's sideways push, the crocodile dropping a rider on open jaws and the
monkey throws after the third are static readings; the coconut script `$0161e8` and the plant spit's stepper (`$0199d2`/`$019a50`) were characterised by observed positions; special-fire shots
(fire modes `$227fa` 1-3 from the pickups at `$012ec8`, `$012f2c`, `$012f90`; `$013ae2`) were exercised only for the marker stack. The first spawn-type pass read bank 2 as ending at frame 139 and
took chameleons and bees for other things (`graphics.md`), and read `spawn_types.py` frame lists ("reach") as belonging to one object although the lists are not delimited, which
produced the monkey, leaf-bush and marker misreadings above.

### The shop (104th pass)

`$00e842` is one routine for two objects, and the mole is the shop keeper (`py/shop/route_driver.py --shop`, segments `seg5b`-`seg11b`, all
replaying byte-identically; images `shop_mole_in_shaft.png`, `shop_room.png`, `shop_bubble_too_much.png`,
`graphics/bank2_shop_frames_62_79.png`). The staging up to the block-313 ledge is the poked start of the hop-4 route, so the shop branch
has not been re-run from the chained real-input snapshot.

- **Outside (`$bb77 == 0`)**: the type 9 mole (spawn record col 1253, y 184, descriptor `$108a8`, live slot 11) sits at the bottom of a 32 px
  pit under the stair in room `299..318` (world col 1252-1255). It stays dormant (animation 0, frame 62) until the hero is inside the box `$e5a0`
  builds around it (about 24 px each side), then climbs out over 13 animation steps (frames 62, 63, 64, 66, 65, 66, 65, 66, 65, 67, 68, hold
  word `$fffd`). It is reached by walking off the ground to its left and falling in (the hero lands at `y=160`). When the hero touches it
  (`$b71a`) with the animation at `$fffd`, hero state 0 and `$227f5` bit 1 (down) set, the handler sets `$bb77 := 1`, fades (`$1c3c8`)
  and installs a record of `$ea92` (16 bytes per world, an "enter" and a "return" record of four words: start block, end block, hero block-x,
  block-y for `$c050`). World 3: enter `(410, 418, 5, 4)` (`$227b4 = $19a`, camera `$3340` = limit, hero `x=$c0`, `y=$90`), return
  `(308, 318, 7, 4)` (`$227b4 = $134`, camera `$2680`, hero `x=$100`, world x 10080). The entry needs about 1M steps of holding down after the fall
  (a control holding down from step 0 sets `$bb77` at step 1,100,000).
- **Inside (`$bb77 == 1`)**: an 8-block shelf-and-ladder cave. The shopkeeper is slot 7 (the type 0 record at block 416, same `$e842`, frames
  69/70), the price bubble slot 8 (`$21822`, a no-op handler `$13cb2`) and the goods slots 0-4 (spawn types 1, 3, 5, 5, 7 at blocks 411-414; kind-0
  pickups whose item code `$79(A0)` comes from descriptor byte +3). The pickup loop `$012c8e..$012e20` walks slots 0-5 and tests contact with
  `$b71a`. With `$bb77 == 1`: touching only shows the price (the mole frame `$46`, the bubble from table `$eae2` by item code); fire pressed with the
  hero idle compares the price byte (table `$eaf2`) with the coins `$bb73` (`bge`): enough coins, the mole plays `$21b3c`, the bubble `$21b4c`
  (THANK YOU, frame `$4e`), the price goes to `$22801`, the item routine runs through the jump table `$12e22` and the item is cleared; too few, the bubble
  plays `$21b5c` (TOO MUCH, frame `$4f`) and nothing is charged. `$fd0e` counts `$22801` down by 5 per call taking 5 coins per step (255 to 180 =
  75 for the worm can). Item codes: 0 SOUP CAN 250 (frame `$48`), 1 WORM CAN 75 (`$4b`), 2 BOMB 125 (`$49`), 3 LASER GUN 175 (`$47`), 4 BIG GUN 150
  (`$4c`), 5 EXT'D BAR 200 (`$4a`); frame `$4d` is EXIT?. The Amazon shop stocks codes 2, 3, 1, 1, 5 only. Effects: code 1 (`$12e7e`) heals `4 + $bb76`
  capped at `$bb75` (live 5 to 12), code 0 (`$12e50`) is the weapon upgrade (`$bb72++`, wrapping at 4 to 3), code 2 (`$12ec8`) sets `$227fa = 1`; the
  others are unread.
- **Leaving**: touching the mole shows EXIT? (bubble `$4d`, mole `$46`); fire (`$227f5` bit 7) plays sound `$22`, sets `$bb77 := $fe` and installs the
  return record. When the room's animation is done `$ea66` sets `$bb77 := $ff` and clears the mole's slot, so the shop is usable once (`$bb77` is
  cleared at `$bbe2`: once per life or level, inferred). `$d2cc` and `$12ccc` also test `$bb77`, so gameplay changes while it is 1. The other worlds
  carry the same structure (`worlds.md`: Ice Land shop records `(411, 419, 3, 4)` / `(318, 331, 2, 4)`, Bermuda `(411, 419, 5, 4)` / `(352, 400, 4, 3)`,
  read from the table, not entered).
- The purchase and health effect of the worm can were driven with coins and health poked (`w bb72 03ff0512`); the too-much refusal used the natural 25
  coins. A health poke `w bb74 12120300` zeroes `$bb77`, which turned every item into a free pickup until found.

## Known traps

Added by the 104th pass (parallel route, boss, shop, level-end and world passes):

- **The health poke writes more than health.** `w bb74 12120300` writes `$bb74..$bb77`: it sets `$bb76` (the world index) to 3 and zeroes `$bb77`, the
  shop flag (inside the shop every item became a free pickup). In another world write `1212<world>00`, and in the shop `w bb72 <weapon><coins>1212`.
  `w bb72 XX000000` zeroes `$bb73-$bb75` and so health. `$227b6` and `$227b8` are adjacent words: `w 227b6` also writes the limit, so pass the current
  limit as the low word, and check `$227b4` after every warp.
- **A frame is about 24,000 steps in gameplay rooms** (12-15k on idle screens): a `kbd` jump key held less than one frame is missed (1/8 at 6,000
  steps, 4/8 at 12,000, 8/8 at 24,000 and 30,000); walk 20k steps per pixel; a jump and fall takes about 1M steps, so a landing budget under 1M ends
  mid-air; releasing up before the game polls the pad means the jump never starts and reads as an instant landing.
- **Floor dips, holes and shafts.** An 8 px dip with a lip stalls the hero for good and it is bitten to death; walking into a bottom-exit hole is silent
  until `y` reaches 192, then the room is left; a camera-follow hero pulled toward x=192 adds -2 px per iteration to any drift test above x=192.
- **Take a sprite bank's extent from the LSD! header, not from the last non-zero frame:** Klondike's bank 2 ends at frame 159 and frames 160-171 are noise.
  Bank 1 frames 0-159 and bank 2 frames 0-99 are common to all worlds; the rest is per world (`worlds.md`).
- **`spawn_list.py` prints garbage on a snapshot that is not mid-level** (world-select, Game Over, `klondike_plus_30M.snap`): `$27200` is not a spawn list
  there, and a "kind-2 record" printed from it is nothing. Use a mid-level snapshot such as `klondike_p9M.snap`, or `agents/wsel/py/spawn_kind2.py`.
- **World-select**: once the cursor has settled (`$227f3 = 1`) the lock test at `$17e2c` is skipped, so poking `$bb79` afterwards does not move it; fire pressed
  while the cursor is still travelling (`$227f3 = 0`) is lost (Bermuda's icon needs about 4M steps).
- **`hits` output piped through `tail` lost its first lines** and made `$b0ca` look unhit: read the whole output. `bt` at `$17c9c` raises an unhandled
  `AddressError` and ends the REPL. `watch` reports go to stderr. `ATARI_TRACE_GEMDOS=1` logs function numbers only: take file names from A0 at `$1c6de`.
- **A "no hit on natural aim" reading needs the geometry:** the Amazon boss's "shot" is a static swipe that only a jumping hero overlaps, so 30 standing pulses
  hitting nothing said nothing about the mechanism until the overlap window was computed.

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
- **A fixed-length input hold shorter than the game's own poll cycle can silently never register at
  all, and "the expected outcome happened" is not proof it did.** The 94th pass held `kbd ff`/`kbd 09`
  for 15,000 steps before releasing, tried at nine idle delays, and read the five delays that left the
  hero exactly where it started (`x=192,y=144`, undamaged) as a successful zero-damage dodge. The 95th
  pass found (via a direct `watch` on the jump's own frame counter, `$1a5c4`) that the jump's entry
  point was never reached at all for those five delays — the up+right packet is enqueued instantly
  with no gap before it, so whether the game's own ~24,000-step joystick poll falls inside a
  15,000-step hold depends on the idle delay's phase mod that period, and those five delays all landed
  in the ~8,000-step dead band where it doesn't. "The hero ended up somewhere consistent with the
  maneuver having worked" is not evidence the maneuver ran — when a test can plausibly do nothing, add
  a direct signal that something in the mechanism actually fired (a counter, a one-shot flag, a state
  transition), not just a position/damage check that a no-op would also pass. Holding for longer than
  one full poll cycle (here, 30,000 steps) makes the input register regardless of phase.
- **A raw memory dump of a position field can catch it mid-scratch, showing a bogus probe offset
  instead of the true value.** The environment-sensor scan (`$00c0d0`-`c204`) walks a lookahead probe
  by repeatedly overwriting the hero's own `2(A0)`/`4(A0)` (x/y) with candidate offsets, reading a tile
  at each, and correctly restoring the true position from cached `D0`/`D1` afterward — it always
  round-trips correctly, so it isn't itself a bug. But an `m`/`watch` read taken at an arbitrary moment
  while this scan is mid-flight (not synchronized to its own start/end) can report one of those
  transient probe offsets (e.g. `204` instead of the real `194`) as if it were the current position.
  When exact position values matter (not just "did it change eventually"), single-step past a known
  instruction (a `bpc` on the actual write you care about) rather than trusting a bare `m` dump taken at
  a guessed moment (97th pass, tracing the `x=192` correction).
- **A camera-follow hero pinned at one screen `x` makes every on-screen position comparison blind to
  progress.** The 90th-97th passes spent eight passes on "the hero cannot get past `x=192`" and "each
  hop nets to the same resting spot", both measured in screen coordinates, while `$227b6` (the camera
  counter) advanced 8px per hop and had never been read. The 97th pass disassembled the `$00bb5c` shift
  and still read it as a wall correction, because it didn't ask what advanced the shared delta. Before
  calling a screen position "stuck", read the scroll counter across the trial (`watch` it), and look for
  its writer (`find_field_writers.py`), which here was one `addq.w #2,$227b6` at `$018fa2`
  (98th pass).
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
  from a snapshot frozen mid-depack loop (the crack's trap hook or `$18812` temporarily runs at a low, non-`LINK`-framed
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
| `coldboot_amazon_twintree_slot12dodge_landed.png` | **94th pass, retracted by the 95th**: `pass94_dodge_item_landed.snap` rendered — pixel-identical to `coldboot_amazon_twintree_item_crossbar.png` (the pre-jump frame) outside the drifting-hazard sprites (`63,454`/`64,000` px match). Originally captioned as a jump-dodge's landing spot; the 95th pass found the frame-counter watch shows no jump ever ran for this snapshot's trigger (a mistimed 15,000-step hold), so this is just the pre-jump frame with the independently-drifting hazards in a different position — kept as the proof image for that retraction, not for a dodge |
| `coldboot_amazon_twintree_item_collected.png` | **98th pass**: `pass98_item_try.snap` rendered right after the up+left hop from the ledge picks up the crossbar item: score `003200`, the item gone from the crossbar, hero at `x=114,y=144` (`1/18`) |
| `amazon_level_map.png` | **99th pass**: the whole Amazon tile map (1680 columns x 24 rows, 2px per tile) from `py/level_map.py --rooms`: category colours, blue lines = room boundaries, cyan/orange ticks = top/bottom exit triggers, white lines = camera window and first-room limit |
| `amazon_room_after_bottom_exit_131.png` | **99th pass**: the cave room `156..161` right after the poked bottom-exit transition at block 131 (see "The level is one tile map of connected rooms") |
| `amazon_boss_room.png` | **99th pass**: the boss room `318..326` right after the transition, the boss tree face on the right trunk |
| `py/level_map.py`, `py/level_rooms.py`, `py/spawn_list.py`, `py/boss_kill.py` | **99th pass**: render the tile map / print the room graph from any snapshot (usage in `py/README.md`) |
| `graphics.md` | **102nd pass**: the graphics pipeline (level, block map, block definitions, tile bank, scroll cache), sprite banks, palettes, font, collision categories, with match counts |
| `graphics/amazon_tileset.png`, `graphics/amazon_level_tiles.png`, `graphics/amazon_categories_start.png` | **102nd pass**: the 256-tile Amazon bank, the whole level from real tiles (13440x192), and the first 80 blocks with the collision categories tinted over the art |
| `graphics/sprites_bank1.png`, `graphics/sprites_bank2.png`, `graphics/hud_font.png`, `graphics/world_palettes.png` | **102nd pass**: sprite bank 1 (`$3b600`, 16x16), bank 2 (`$42e00`, 32x24, hero and shop art), the 8x8 font and the five world palettes |
| `graphics/amazon_spawn_types.png`, `py/spawn_types.py` | **103rd pass**: every Amazon spawn type's descriptor decoded and its frames drawn, one row per type (README "Spawn types"); `graphics/sprites_bank2.png` was regenerated with all 172 frames |
| `py/start_room_route.repl` | **103rd pass**: real-input replay of the route's first two hops, from `pass99/warp_up112.snap` to room `188..285` (usage in `py/README.md`) |
| `py/tiles.py`, `py/sprites.py` | **102nd pass**: render the tileset, level, category overlay, palettes, sprite banks and font from any snapshot, and `--check` them against the live screen (usage in `py/README.md`) |
| `py/twintree_item_route.repl` | **98th pass**: REPL script for the whole item route from `pass96_doublejump_v2.snap` (usage and expected output in `py/README.md`) |
| `worlds.md`, `graphics/<world>_*.png` (`klondike`, `orient`, `ice`, `bermuda`) | **104th pass**: the four other worlds: tile banks, whole-level renders, category overlays, level maps with rooms, sprite banks, spawn-type sheets, gameplay and boss-room screenshots (`worlds.md` "Files"); `graphics/klondike_conveyors_room93.png` |
| `ending_screen.png`, `world_select_after_win.png`, `world_select_four_done.png` | **104th pass**: the Bermuda ending ("CONGRATULATIONS MONTY", `$183c0`), world-select after an Amazon win (red X on the Amazon, `$bb79 = $14`) and after four wins (Bermuda unlocked) |
| `shop_mole_in_shaft.png`, `shop_room.png`, `shop_bubble_too_much.png`, `graphics/bank2_shop_frames_62_79.png` | **104th pass**: the type-9 mole in its shaft with the hero above it, the shop cave (goods, bubble, shopkeeper), the TOO MUCH bubble, and bank 2 frames 62-79 (mole and bubbles) |
| `py/route/`, `py/shop/`, `py/boss/`, `py/level_end/`, `py/worlds/`, `py/spawn/` | **104th pass**: the event-driven route driver and replays, the shop branch, the real-input boss fight, the level-end scripts, the per-world pipeline and census scripts, the spawn-type proofs (`py/README.md`, "Subdirectories") |

## Not yet exercised

Current open items, in the order `sessions/impossamole.md` ranks them (everything else this README once listed here has been done):

- **Natural play, unpoked.** From `pass103/room188.snap` (weapon 3, 25 coins) the Amazon is played with no health, weapon or shot poke: hop 3, hop 4 with
  the shop's worm can, and the boss (previous section, one recorded file of 12,032 commands). Still poked or staged: hops 1 and 2 (`118..137`, `160..173`) and
  the start room (a labelled poke into `118..137`, health refilled per segment), plus the two type-4 upgrades (blocks 27 and 134) that `room188.snap` already
  carries; the boss kill is 1 of 12 timings and needs a controller that also dodges the aimed 139. The other four worlds have cold-boot, warp and boss-kill
  proofs only, no played route.
- **Damage sources:** the water tiles and room `299..318`'s drain are pinned (previous section); the type-2 enemies met in segments 2-5 are identified by handler
  but their approach paths are not modelled.
- **Shop items:** only the worm can (code 1) was bought; codes 0, 2, 3, 4, 5 and the shop ladder are undriven.
- **Level-end chain for Klondike and Orient** (their boss kills were done, the flag chain only for the Amazon, Ice Land and Bermuda). Name entry
  and the cheat names are done (`secrets.md`).
- **Per-world code:** `$ee16` (death dispatch), `$ea92` (shop records) and `$c028` words 0-1 are located, not decoded; Orient's category 5/8
  behaviour, Bermuda's 17-hop chain on real input, Klondike bank-2 residue's source.
- **Graphics:** the title, world-select and ending art formats, animation order per action, the `$216e2` flash palette.
