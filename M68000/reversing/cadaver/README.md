# Cadaver (Bitmap Brothers / Image Works, 1990) — reversing spike

Isometric adventure/puzzle game. This is a spike (bounded exploratory pass), not the full
milestone ladder used for PowerMonger/Super Sprint — it exists to get the game running and
establish a known-good boot path, since that alone took three real emulator fixes. AI/UI content
reversing (the actual goal) has not started yet; see "Next steps".

## Disk images

Two separate releases were tried, both under `Atari-St-Emulator/Cadaver/` and
`Atari-St-Emulator/The Medway Boys #88{A,B}.zip` (kept untracked, copyrighted — never `git add`).

**"The Medway Boys #88" compilation (ZIPPY crack), disks A+B, MSA format** — dead end, see below.
- `The Medway Boys #88A.zip` sha256 `13a3491686bbf37290325aabdc857402e92a6996683f7b776f4b8af437498f77`
- `The Medway Boys #88B.zip` sha256 `192cada5350806a9503b77aa49d84226332b98a932948eac7736e0685e0e4f18`
- Contains `TMB08{8A,8B}.MSA`, converted to raw `.ST` with the new `tools/msa2st.py` (no MSA
  support existed in this repo before — MSA is a simple per-track RLE format, see the script).
- Disk A is a normal FAT12 volume (double-sided, 10 spt) holding a menu (`MENU88.PRG`) plus four
  games (Cadaver, Magic Fly, Helter Skelter) and docs. Disk B is a **non-filesystem, self-booting**
  raw disk (executable code at sector 0) — Cadaver's own loader reads it by absolute sector number.

**Cadaver (1990)(Image Works)\[cr Empire\]\[one disk\].st** — the one that works end to end.
- `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].zip` sha256
  `5df6ccafafbcd6fdcd8c3865979576d75bf4d24a85884e95ff8a6c4bb131d882`
- Extracted `.st` sha256 `7d4641dd5346a0367e7086bc1bb480c60ccd67c840947041d04f0f816180ad5c`
- Already a raw `.ST` image (819,200 bytes) — no MSA conversion needed.
- Self-contained: despite the "place levels disk" prompt, no swap is actually needed — pressing a
  key with the *same* disk still mounted goes straight into gameplay.
- The `Atari-St-Emulator/Cadaver/` directory also has the two-disk Image Works release under
  several crack groups (Empire, Replicants — ST Amigos) and a `[!]` (verified-dump, likely
  original/uncracked) pair, untried.

## Milestones reached

1. **Cold boot → GEM desktop → AUTO-launch**, clean on both releases, no instruction walls.
2. **Medway Boys menu screen** renders correctly (`menu_medwayboys.png`) — a "Medway Boys #88"
   cracktro menu (Cadaver+ / Magic Fly / Helter Skelter+ / Docs).
3. **ZIPPY crack intro** (`crack_intro_zippy.png`) — plain-text screen that documents the exact
   protection scheme in its own words: five Rob Northen Copylock checks (one per level) with a
   "trace-decoded sub-routine" anti-debug check, and states that a failed check leaves that
   level's data corrupted, crashing the game on a later room. This turned out to be exactly what
   happened (see "Dead end" below).
4. Full **five-part Rob Northen protection check** (polls all four MFP timer data registers in
   sequence as a hardware-timing fingerprint) — needed two of the three emulator fixes below.
5. **Bitmap Brothers logo** (`crack_intro_empire.png` shows the Empire variant) with a genuine
   multi-second animated colour-cycle hold, driven by real VBL interrupts.
6. **Language select** ("1 ENGLISH / 2 FRANCAIS / 3 DEUTSCH") and **restore-game prompt** ("place a
   disk... or ESC to start at the beginning") — both keyboard-driven through the game's own custom
   IKBD ISR (installed at vector `$118`), not TOS's Bconin.
7. **Full gameplay** (`gameplay.png`, Empire release only) — isometric dungeon view, "DAY 1",
   room name "CAVERN", inventory UI. `gameplay_empire.snap` is a live snapshot sitting at this
   state, ready to resume from (`resume <path> repl --disk-a "Cadaver...[cr Empire][one disk].st"`).

### Dead end: Medway Boys / ZIPPY crack corrupts on level load

With disk B swapped in at the "place levels disk" prompt, the loader reads real data (confirmed
via `ATARI_TRACE_FDC=1`) but shortly after hits `$4E7A` (`MOVEC`, a 68010+-only instruction — see
the ILLEGAL fix below) followed almost immediately by clearly-garbage instruction decode (`ori
#$a71f,SR`, nonsensical `btst`/`swap` chains) — i.e. the CPU has run off into data, not code. This
lines up with the crack's own documented failure mode: an anti-debug timing check failing and
leaving level data "corrupted, making the game crash". Not an emulator bug — the Empire one-disk
crack (different crack group, same underlying game) sails through the equivalent point with zero
new instruction walls, confirming the CPU core is fine; it's this specific crack's own incomplete
patch. **Use the Empire release, not Medway Boys, for anything past the title screens.**

## What it needed from the emulator (commit-table style)

| Wall | Fix |
|---|---|
| MFP Timer A (`$fffffa1f`) never modelled as a live counter — only Timer B had been (added for an earlier game) — so a busy-poll on it never converges | Gave Timer A the same read-driven decrement Timer B has (`MMU.fs`) |
| Timer B/A stuck at 0 forever once a reload of literal `0` was written | Real MC68901: a `0` reload means a count of 256, not "stays 0" — fixed for all four timers (verified bit layout against Hatari's `mfp.c`: `TCDCR & 0x70` = Timer C armed, `& 0x07` = Timer D) |
| MFP Timer C/D (`$fffffa23`/`$fffffa25`) same gap as Timer A, needed for the same 4-timer protection poll | Same read-driven decrement pattern, gated on the shared `TCDCR` control register |
| `$4AFC` (real 68000 `ILLEGAL` opcode, vector 4) not decoded at all | Added `Illegal` pattern + `EnterVector 4 x.PC` (pushes the *faulting* instruction's own address, unlike TRAP/TRAPV which push the next one — confirmed against Hatari's `op_illg`) |
| `$4E7A`/`$4E7B` (`MOVEC`) — a 68010+ instruction that doesn't exist on the ST's real 68000 — hit as an apparent CPU-detection probe | Folded into the same `Illegal` pattern (narrow, explicit — not a catch-all for genuinely-unimplemented-but-valid opcodes, which must keep failing loudly) |
| No way to hot-swap the mounted disk image mid-run (needed for "insert disk 2" flows) | New REPL `disk <path>` command (`Program.fs`) |
| No MSA disk image support at all | New `tools/msa2st.py` (RLE per-track decoder) |

Snapshot format bumped to v11 (adds Timer A/C/D live-decrement state; old snapshots still load,
defaulting that state to the chip's power-on value). All four changes are regression-clean:
`verify` passes, `selftest tests/680x0` stays at 973696 pass / 0 wrong-answer / 8 skip.

## How it was run

```
# one-time: convert MSA -> ST (Medway Boys disks only; Empire's .st needs no conversion)
python tools/msa2st.py TMB088A.MSA TMB088A.ST
python tools/msa2st.py TMB088B.MSA TMB088B.ST

# boot
dotnet exec bin/Debug/net8.0/M68000.dll 15000000 --disk-a "Cadaver...[cr Empire][one disk].st"

# drive it with the REPL (kbd <make> then, separately, kbd <break> - injecting both bytes in one
# `kbd` call fires the whole burst inside a single interrupt, so a real polling main loop never
# observes the transient "key is down" state; see the make/break discipline note below)
dotnet exec bin/Debug/net8.0/M68000.dll resume <snap> repl --disk-a "...st"
> kbd 39        # space, make code only
> s 3000000
> kbd b9        # space, break code, sent later
> s 20000000
```

**Keyboard discipline this game needs**: its own IKBD ISR (vector `$118`) stores raw scancodes into
a game-internal cell that the main loop polls; sending make+break in one `kbd` call lets the ISR
drain both before the main loop ever sees the intermediate "key down" value. Always separate them
with real step counts in between, mirroring a human's press/release timing.

**Disk swap**: `disk <path>` in the REPL re-mounts drive A from a different `.ST` file
mid-session — added specifically for this game's "insert disk 2" flow, though the Empire release
turned out not to need it.

## Files

| File | What |
|---|---|
| `README.md` | this file |
| `menu_medwayboys.png` | Medway Boys #88 cracktro menu |
| `crack_intro_zippy.png` | ZIPPY crack-intro text (documents the protection scheme) |
| `crack_intro_empire.png` | Empire crack-intro screen |
| `gameplay.png` | Empire release, in actual gameplay (Day 1, Cavern room) |
| `gameplay_empire.snap` | live snapshot at the gameplay screenshot above (untracked — regenerate via the resume command above, or re-drive a fresh boot) |
| `cadaver.sym` | `addr<TAB>name` sidecar for the routines/tables identified so far (main loop, entity script interpreter, input dispatch, screen buffers) |

## Control flow (2nd pass, from `gameplay_empire.snap`)

Grounded via `ATARI_TRACE_EVENTS` + `tools/trace_cfg.py` over a REPL session that drove mouse
clicks and cursor-key presses from the gameplay snapshot (`resume ... repl`, `watch` on candidate
buffers, `snap`-diff before/after) — not read off static disassembly alone. Symbols in
`cadaver.sym`.

- **`$014496` `MainLoop`** — the per-VBL game loop. Self-recursive in the call graph (called once
  from `entry`, then calls itself every iteration); 61 hits across a ~1.45M-step window against a
  ~12000-24000-step VBL period, i.e. it runs once per video frame, not once per VBL-interrupt tick.
  Fans out every frame to: `TimerQueueService` (`$9006`, a countdown-timer/callback scheduler —
  `$9052` `jsr`s through a vector table at `2534(A5)`, capped-ring command queue at `304(A5)` sized
  200 (`$c8`) that looks like the sound/music driver's command buffer), `EntityScriptDispatch`
  (`$15c70`, see below), and the screen-flip chain (`$d792`→`$d856`→`ScreenFlip_AndCompositeSprites`
  `$14d64`).
- **Screen buffers**: the running game keeps a small struct at global `A5=$18152` whose field 0 and
  field +120 are two 320×200×4bpp (32000-byte) buffer pointers that swap roles across frames —
  observed as `$19100`/`$20f00`/`$2de08` in different snapshots (`ScreenBufferA/B`,
  `CompositeBackBuffer`). `ScreenFlip_ScanlineCopy` (`$144b8`) is a fully-unrolled `movem.l`
  copy loop with a `trap #4`-based mid-loop yield (`$90.w` vector) — splits the ~32KB copy across
  several VBLs so it never tears. `ScreenFlip_AndCompositeSprites` (`$14d64`) does the same kind of
  copy but with an `and.l (a1),Dn / or.l Dn,Dn / move.l Dn,(a1)+` masked-composite inner loop
  (`SpriteCompositeInner_AndOrMaskLoop` at `$14f24`, 4361 word-writes across 141 calls) — sprites
  (cursor, held object, and presumably creatures once one exists) are masked onto the frame as part
  of the flip, not baked into the room background buffer.
- **Entity/animation bytecode interpreter**: `EntityScriptDispatch` (`$15c70`) walks an entity
  table at `$16380`, each entity a struct with a script byte-pointer (offset 4), a per-opcode jump
  table read from a 1-byte opcode stream (opcode ≥ `$80` → indexed `jmp` through a table at
  `$15cae`; else it's a frame-table lookup into `$160ac`). Individual opcodes (`$15ea4`..`$15f18`
  in `cadaver.sym`) set/countdown small per-entity fields (`52`/`53`), re-point the script cursor
  from a per-entity table at `+16`, or jump the whole entity to a new script via
  `ActionScriptPointerTable` (`$163aa`). This is the same shape as PowerMonger's regroup FSM
  (see `[[atari-st-emulator-next-instructions]]`, 92nd–99th passes) and is the right target for a
  `callcap` differential-test pass once a creature entity exists in the table.
- **Input → action pipeline**: the custom IKBD ISR (`$1535a`, vector `$118`) stores raw scancodes
  into a cell polled elsewhere; `IkbdKeyDispatch_ScanTable1616c` (`$158f6`) scans
  `KeyDispatchTable` (`$1616c`, 5 bytes/entry: type `01`/`02`/`03` = 1/2/3 alternate scancodes for
  the same action, then the scancode(s), then a 1-byte action id) and calls through
  `GuardedCall_15bf4_Single`/`_Loop` (`$15a5c`/`$15a7e`, which set the reentrancy flag `$158da`
  around the call) into `EntityScript_StartAction_SlotD1_ActionD0` (`$15bf4`) — this loads
  `ActionScriptPointerTable[actionId]` as a new script onto control-slot `D1`, tracked in the
  bitmask `ActiveEntitySlotBitmask` (`$162cc`). Confirmed table entries: Up (`$48`) alone → action
  `$6e`; Down (`$50`, paired with `$51`) → `$65`; Right (`$4d`, paired with `$4c`) → `$c6`; no `$4b`
  (left-arrow) entry was found in the table dumped so far — worth re-checking, since Cadaver is
  reportedly mouse/icon driven for movement (per the "inventory UI" already seen) rather than
  cursor-key walking; the arrow-key entries found may be a UI/menu-navigation layer instead of
  player movement.
- **What didn't pan out in the 2nd pass, corrected in the 3rd**: the 2nd pass concluded mouse/kbd
  input produced no visible effect. That conclusion was an artefact of two mistakes, both now
  fixed: (a) the REPL's `watch <addr> <len>` takes `<len>` in **decimal**, not hex — passing a hex
  length (e.g. `e63` for a 0xe63-byte span) either throws or silently watches the wrong range, so
  the earlier "0 watch hits" results were watching garbage; (b) the three screen-buffer addresses
  guessed from one static pointer read are not stable — `ScreenBufferA`/`B` swap roles across
  frames, so a `watch` fixed at one of them before driving input can legitimately miss everything.
  The fix that worked: snapshot before/after a matched-length **idle control run** and an
  **input-driven run** from the same base state, diff both against the base, and keep only the
  bytes that changed in the input run but *not* the idle one (idle-only changes turned out to be
  real — ambient torch/water animation flips ~1800 bytes over 1.5M steps regardless of input; see
  `verify-visual-claims-with-frame-diffs` in project memory). That isolated a real, reproducible,
  input-only signature: a repeating ~160-byte-stride (one scanline) run of ~15-23 changed bytes,
  17 rows tall — the mouse cursor sprite. **Rendering the live screen directly and diffing the
  actual images confirms it pixel-for-pixel**: `mouse move 40 20` moves a visible ~29×24px cursor
  icon to exactly the predicted screen position; the player-character sprite's own pixels are
  **byte-identical** before/after (confirmed over a 45×50px crop around it) despite the same run
  also sending `mouse down/up` (a click) and all four cursor keys. So input reaches the game and
  visibly acts (the cursor moves, and the earlier `callcap $15bf4 D0=$6e D1=0` experiment cleanly
  set `ActiveEntitySlotBitmask` bit 0 and wrote a script pointer into the slot-0 control block at
  `$162d0` — the same region the real-input A/B diff also flagged) — but **nothing this pass made
  the character walk or spawned a creature**. The click may need to land on a specific room tile
  (screen-space room/tile mapping still unknown), need to be held rather than a tap, or the
  confirmed key-table entries (Up/Down/Right) may genuinely be a UI/menu layer rather than
  movement, as suspected in the 2nd pass.
- **3rd pass, cont. — the Down key does something real, not yet understood.** `kbd 50`+`kbd d0`
  (Down make+break) alone, run forward 3M steps and rendered: **the player-character sprite
  disappears from its starting position entirely** (pixel-diff confirmed — byte-identical rock
  texture fills where it stood, and the diff bbox against the base frame contains no new
  character-shaped blob anywhere else on screen, so it isn't simply repositioned in view).
  Sending Up (`kbd 48`+`kbd c8`) afterward and running another 3M steps does **not** bring it back
  (identical resulting frame) — either Up isn't the semantic opposite of Down, the walk/whatever-
  it-is needs more than 3M steps to complete or reverse, or it's a one-way state (an item-use /
  death / room-exit animation) rather than ordinary movement. `ActiveEntitySlotBitmask` (`$162cc`)
  bit 0 sets after Down and **stays set** through the subsequent Up (doesn't self-clear the way
  the `callcap $15bf4` single-shot experiment's cleared-scratch-then-idle pattern suggested it
  should once a script finishes) — but the slot-0 control block itself (`$162d0`+) stays entirely
  zero this time, unlike the earlier isolated `callcap` test, so the real in-game call path is
  doing something other than what was assumed from that one experiment. The main entity table
  (`$16380`, 0x800 bytes scanned) shows only **1 byte** different between base and post-Down — the
  character is almost certainly not tracked as a normal entity in that table at all (or its
  relevant field lies outside the 0x800-byte window scanned). Not chased further this pass —
  next step 1 below is the concrete way to pin it down (bisect on step count to find the exact
  VBL where the sprite stops compositing, then trace what runs in that window specifically, rather
  than wading through the routine per-VBL screen-copy noise that dominates any broad `watch` here).
- **Graphics format: not actually an open question.** The live screen (`ScreenBufferA` at
  `$19100`) is plain standard-ST `st-interleaved` 320×200×4bpp — no unusual tile/sprite packing —
  using the palette table at `$5a9c` (16 big-endian `$0RGB` words, the same one `$015302` copies to
  `$ffff8240` at boot). Rendering it directly (`tools/gfxview.py` "st-interleaved" layout, or the
  a-priori-simplest guess) reproduces the `gameplay.png` milestone screenshot exactly. The earlier
  "decode the isometric tile/sprite format" framing assumed room art must be built from a packed
  tile sheet found somewhere in RAM (the `ram_contact.png` data spans); that search never found a
  match because there was no need to look past the screen buffer itself for what's already on
  screen. A *packed* per-tile sheet (for other rooms not yet visited) may still exist in one of the
  7 candidate spans, but isn't needed to view the current room.

## Next steps

1. Pin down what the Down key actually did (see above — the character vanished and 3M steps of Up
   didn't bring it back). Bisect on step count from the known-good `kbd 50`/`kbd d0` sequence
   (e.g. render+diff at 200k/500k/1M/1.5M/2M/3M steps) to find the specific VBL window where the
   sprite stops compositing, then trace *just that window* (`ATARI_TRACE_EVENTS` scoped tight, or
   a full `-Trace` dump — cheap once the window is a few thousand steps instead of 3M) to see which
   routine actually removes it — a real walk-off-screen, a death/room-exit, or something else.
   `EntityScriptDispatch`/`$15c70` and the control-slot area (`$162cc`+) are candidates but the 3rd
   pass found the main entity table (`$16380`) and the slot-0 control block essentially untouched
   by the real in-game Down-key path, unlike the isolated `callcap $15bf4` experiment — so the real
   path may go through a different mechanism than that one test assumed. Once understood, try
   Right (`$c6`) the same way, and try clicking with the cursor positioned directly over the
   character or adjacent floor tiles (cursor positioning is now confirmed working via render+diff).
2. Once movement or a room transition can be triggered on demand, `watch` (with a **decimal**
   length!) on `ScreenBufferA`/`B` and A/B-diff against an idle control the way this pass did, to
   find the actual room-tile draw routine — far more reliable than guessing.
3. Once a creature is on screen, snapshot at that point and differential-test
   `EntityScriptDispatch`/its opcode handlers with `callcap`, following the PowerMonger FSM
   methodology (`tools/pm_fsm_diff.py`'s `Harness`/`State`/`run_corpus`, game-agnostic; write a
   Cadaver-specific reconstruction module).
