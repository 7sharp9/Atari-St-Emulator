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
| `graphics.md` | 7th-pass graphics writeup: live screen format + the packed sprite/object sheet found at `$029800`-`$02de08` |
| `ram_contact.png` | whole-RAM contact sheet (`gfxview.py --contact`), regenerated 7th pass |
| `gfxview.html` | interactive per-region viewer (`gfxview.py --html`), regenerated 7th pass |
| `spritesheet_29800.png` | the player's packed frame sheet, rendered as a struct-confirmed 32×42-cell grid (see `graphics.md`) |
| `player_frame_alt.png` | the player's alternate/gesture animation frame (`$2ca94`) |
| `sprites/` | the full 22-entry sprite-object-array catalog (player + every prop in the room), one PNG per slot + contact sheet + manifest — see `graphics.md` §3 |
| `movement_before.png` | 10th pass: base gameplay frame before any joystick-1 input |
| `movement_after_right.png` | 10th pass: same state after holding joystick-1 `right` — player visibly walked and picked up items, proving real movement |
| `movement_walk_to_chest_boundary.png` | 11th pass: held Right to its boundary (chest/mat area) |
| `movement_walk_to_upperwall_boundary.png` | 11th pass: held Up to its boundary (blocked almost immediately by a wall) |
| `movement_walk_to_barrel_boundary.png` | 11th pass: held Left to its boundary (the barrel, top-left) |
| `movement_walk_to_boat_boundary.png` | 11th pass: held Down to its boundary (water's edge by the boat prop) — a BOAT item enters inventory here |
| `movement_at_boat_boundary.snap` | 11th pass: live snapshot at the boat-boundary screenshot above — a ready resume point for the "how do you use the boat" open question |
| `room2_tunnel_entry.png` | 12th pass: the first frame of the second room, "TUNNEL", reached via the CAVERN door |
| `room2_tunnel_entry.snap` | 12th pass: live snapshot at the screenshot above — resume point for exploring past the first room |
| `room2_lever_boundary.png` | 13th pass: player flush against the TUNNEL lever, status bar reads "LEVER", icon panel shows its bracket/key icon pair |
| `room2_lever_boundary.snap` | 13th pass: live snapshot at the screenshot above — resume point for trying new inputs against the lever (all tried this pass were inert; see the 13th-pass entries) |
| `mechanics.md` | 14th pass: the collision/obstacle-check algorithm (`$008870`) and the TUNNEL lever's proximity-hotspot mechanism; 15th pass (§10): TUNNEL's live portal table fully decoded, settling "does the lever's door have an entry" as no; 17th pass (§13): CAVERN's own portal table decoded, a second real door found + live-triggered, closing the creature hunt as a fully-enumerated dead end; 18th pass (§15): found the type-8 room-registration table's only writer — the save-game restore deserializer (`$00c9ee`), gated behind a boot-menu branch this spike has never taken; 19th pass (§17): found the SAVE-serializer's real trigger — it's not a player hotkey, it fires automatically once at the very start of every boot on an always-empty type-8 table, retiring the planned save→restore live test; axe/pick navigation attempted, not reached; 20th pass (§18): found and fully disassembled the ring-304 queue's consumer — opcode `$8` is a name-banner/message-box display trigger, not a room loader, closing the "does `$defa` do real disk I/O" question as no; (§19) the axe/pickaxe reached and picked up live, closing the 16th pass's open item and opening a new "retest the lever with it held" lead; 21st pass (§20): the pickaxe-precondition reading retracted per user ground truth, replaced with a settled directional sweep — the player is hard-blocked with zero clearance toward the object and the "LEVER" hotspot itself is gone by 3 units in either free direction, closing the finer-position-sweep lead as a real negative, not an untested one; 22nd pass (§21): read the lever's own object-array entry in full and ran it through §4's own interactive/pickup classification test for the first time — it fails (byte24's top bit is set, but the linked `+10`→`+15` bit-2 flag isn't), so the object is plain scenery, not interactive; combined with §20's own "AABB overlap unreachable" finding, this is a double negative that closes the touch/opcode-`$9` pathway for the lever without needing to trace §18a's dispatcher against it; 23rd pass (§22): decoded action 101's own script (animation-only, confirmed) and finished the embedded debug-string scan past where §9 stopped — found a whole previously-undocumented "object verb" bytecode interpreter (LOCK/UNLOCK/MOVE/creature kill-wake-sleep/rucksack/chest ops, `$010000`-ish–`$011256`ish) whose LOCK/UNLOCK opcodes (`$0104a0`/`$0104ae`) write the *exact* `+15` bit-2 flag §21b found clear on the lever's linked struct, via an id-resolver using resource types 6/9 (unlike rooms' always-empty type 8); also disassembled the ring-304 queue's generic (non-`$8`) opcode path (`$00fe0c`-`$00fe70`) as a per-entity tagged-record dispatcher, and ruled the fire chain back out as still cosmetic-only — neither new mechanism is yet tied to the lever specifically, see `mechanics.md` §22g for the priority-ordered next steps; 24th pass (§23): found the verb interpreter's own top-level dispatch table (`$010000`-`$010075`, 59 word-relative entries) by raw byte-scan and confirmed LOCK's real numeric opcode id is 18 (exact address match, not a guess) — UNLOCK's own address isn't one of the 59 entries, still open; dumped resource types 6/8/9 live (no `kbd`/`mouse` needed, RAM-only against the already-known `A5=$18152`) and found type 6 (objects) fully populated (1000/1000) — then the headline result: **the lever is object id 144** in that exact table, triple-confirmed (id-resolve → `$06fa0e`, the lever's own sprite-array `+10` field → the same address, and `+15`/`+24` reading exactly as §21b originally found), settling that the LOCK/UNLOCK mechanism operates on the lever specifically, by a confirmed id and opcode — only "what script/event actually invokes opcode 18 with operand 144" is still open, see `mechanics.md` §23e; 25th pass (§24): four independent static searches for the dispatch table's caller (absolute-literal, PC-relative-`lea`, opcode-read-pattern, and an 18-site whole-block external-caller sweep) all came back negative — no static call site anywhere in the loaded image reaches the byte-opcode dispatcher — so ran the causal test directly on LOCK's own address instead of through it: `callcap $01049a A1=<scratch id-144 buffer>` from `room2_lever_boundary.snap` flips the lever's `+15` byte from `$01` to `$05` (bit 2 set), the first genuinely causal (not just structural) proof that LOCK-on-144 does what every prior pass inferred; whether anything in this game state actually calls it that way remains open, now backed by a much broader negative, see `mechanics.md` §24d; 26th pass (§25): decoded `$00fe84`'s jump table in full (29 entries, `$00fe84`-`$00febd`, same "table then code" shape as `$010000`) — every handler is a precondition gate (pass/fail against small state fields `1156`/`1157`/`1167(A5)`) or a minor unrelated mutation (actor-pointer swap, a bit-clear, a score+sound accumulator), and **none references the lever's record, object id 144, or anything in `$010000`-`$011256`** — a clean negative closing the standing "does the ring-304 queue reach LOCK/UNLOCK" question from §22e/§22g/§24d outright, see `mechanics.md` §25c for the resulting reframe (the caller may not be loaded into RAM at all, since room 3's own script/init data — as opposed to its graphics — has never been shown to load in any snapshot this spike has taken); 27th pass (§26): closed the whole lever-caller thread as a documented negative in one paragraph, not reopened by further searching, and (§27) added a consolidated schema-style room/level-encoding reference — room-extent test (§3), live object-array collision/classification (§4), portal-table format and both rooms' live examples (§10b/§10c/§13), and the type-6/8/9 master resource-table system (§15b/§23c/§23d) — pulling facts already found across those sections into one place rather than re-deriving anything; 28th pass (§28): tested the flag-poll hypothesis live for the first time — held object 144's own `+15` byte set with a real memory write (not `callcap`, which reverts) across 5,000,000 steps from `room2_lever_boundary.snap` — completely inert, `RoomLoadQueuedFlag`/`DoorFacingOrBlockedFlag`/TUNNEL's whole live portal table all stayed byte-identical (§28a); re-ran both of §25c's remaining fallbacks and found them already closed — the one literal write of `2142(A5)=2` is the display-register site the 18th pass's own §18c already named, not a room-load flag (§28b), and the "already resident" branch (`$69da`), disassembled in full for the first time, turns out to be the game's own main-loop re-entry point with no decompress/copy step hiding in it (§28c); **reframes the whole thread** (§28d) — combined with the 17th pass's user-supplied ground truth that the lever really does open the door in the real game, and the 22nd pass's double negative that genuine touch is unreachable by ordinary movement, LOCK(144) now reads as the wrong mechanism entirely, not a real-but-unreached one, and the next pass should look past it rather than continue the caller search; 29th pass (§29): re-examined whether the hard wall toward the object (§20b) is a Left-only route artefact — no: a genuinely different route (Down×3 then Left×3 from `room2_tunnel_entry.snap`, never using the original approach corridor) reaches a new boundary tile on the object's *south* side, still exactly 1 unit short (mirrored axis: x-overlapping, y off by 1, vs. the original y-touching, x off by 1), and true diagonal packets (not sequential moves) at both corners are also fully blocked — three independent approach vectors, one consistent wall (§29a/§29b); the save→restore lead was not re-run live since §17c already closed it analytically (no player-reachable SAVE trigger exists anywhere in the loaded image, and the auto-serialize-at-boot always writes an empty type-8 table regardless of which boot-menu branch runs after it) (§29c); the 6 alias action ids (`127/129/158/159/188/198`) were each driven through the real IKBD pipeline for the first time (not the 9th pass's own hand-write shortcut, which it had already shown isn't equivalent) at the lever boundary specifically — completely inert, closing this as a live negative rather than a structural inference (§29d); leaves the whole spike's input/route/action-id space exhausted against this specific puzzle (§29e), with only the never-attempted pickaxe-at-the-lever retest and the still-undecoded `$defa` room-load path open; 33rd pass (§32b): got the live register dump at `$014b28` the 32nd pass's `bp` runs couldn't reproduce (`bpc 014b28 1 <maxSteps>` proved reliable both directions) — `A0=$55b6` is **identical** across the TUNNEL→CAVERN and CAVERN→TUNNEL crossings, settling `$014a90`/`$014b28` as a fixed status/icon-panel redraw (matching §7's independently-known "icon panel switches on room entry" behaviour), not the still-unfound room-background painter — closes that lead and reframes the open search; 41st pass (§41): rebuilt `room2_lever_boundary.snap` (missing from this Mac checkout) from `room2_tunnel_entry.snap` via the 13th pass's own Left-hold recipe, this time with `bpc 014a90` armed for the whole approach rather than just the settled boundary — **zero hits** across the full proximity transition (status bar going blank→"LEVER", icon panel gaining its two icons, confirmed by render and pixel diff against the idle state), settling that `$014a90`/`$014b28` is room-crossing-only and never involved in a same-room proximity icon-panel change; the actual proximity-icon writer is now a distinct, still-unidentified open item |
| `cavern_east_door_matched.snap` | 17th pass: live snapshot at CAVERN's newly-found east door, at the "already resident" branch's post-resolution state (20th pass, §18d: live-checked and corrected — the ring-304 queue here is empty, this door never reaches `$defa` at all, contra this entry's original framing) — resume point for pushing further on `$de5e`/`$e854`/`$11256` without re-deriving the route |
| `ai.md` | 14th pass: the entity/action-script bytecode interpreter (`$15c70`), its 17-opcode instruction set, and the 3-slot structure it drives; 27th pass (§6): promoted the separate "object verb" bytecode interpreter (`$010000`-`$011256`, LOCK/UNLOCK/MOVE/creature/rucksack/chest ops, found 23rd-26th passes) out of `mechanics.md`'s narrative into its own proper writeup — dispatch table, opcode vocabulary, LOCK's confirmed id (18) and the lever's confirmed object id (144), with the caller search cross-referenced as a closed negative (`mechanics.md` §26) rather than re-argued here |
| `axe_touch.snap` | 20th pass: live snapshot with the pickaxe just picked up (status bar "PICKAXE", inventory count 22→23) — resume point for retesting TUNNEL's lever with it held, untracked like the other `.snap` resume points |
| `axe_touch.png` | 20th pass: screenshot at the snapshot above, status bar reading "PICKAXE" / "CAVERN" |
| `lever_sweep_down_clean.snap` | 21st pass: live snapshot 3 settled units below the lever hotspot — status bar "TUNNEL" only, no "LEVER"; the resume point behind `mechanics.md` §20c/§20d, untracked like the other `.snap` resume points |
| `lever_hotspot_gone_3units_down.png` | 21st pass: screenshot at the snapshot above, proving the "LEVER" name-hotspot is gone 3 units below the baseline tile |
| `room2_lever_south_boundary.snap` | 29th pass: live snapshot at the new south-approach hard-block tile (`x6-12,y16-22`), reached via Down×3 then Left×3 from `room2_tunnel_entry.snap` — a genuinely different route from the original Left-only approach; resume point behind `mechanics.md` §29a/§29b; untracked like the other `.snap` resume points |

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
- **Screen buffers**: the running game keeps a small struct at global `A5=$18152`. `(A5)+0` and
  `(A5)+$7d00` (32000) are the two halves of *one* 64000-byte double-buffer feeding the shifter
  directly (observed as `$19100`/`$20f00` in one snapshot) — **not** a two-way role-swap with
  `120(A5)` as previously written here (corrected 35th/36th pass, `mechanics.md` §34a-35;
  `CompositeBackBuffer` below is the old, wrong name for what `120(A5)` actually is). `120(A5)`
  (observed as `$2de08`) is a **separate, third resident buffer** — not the room's source art, but
  a *cache* of it (corrected again, 37th pass, `mechanics.md` §36: see below).
  `ScreenFlip_ScanlineCopy` (`$144b8`) is a fully-unrolled `movem.l` copy loop (571×56-byte chunks
  plus one 24-byte remainder chunk, `$5a99`-gated) with a `trap #4`-based mid-loop yield (`$90.w`
  vector) that splits the ~32KB copy across several VBLs so it never tears — but the copy is not a
  straight memcpy: forward-read/backward-write `movem` reverses **chunk order** end-to-end, so
  `120(A5)` stores its content byte-chunk-reversed relative to normal raster order (fully decoded,
  byte-exact, `mechanics.md` §35; `reversing/cadaver/py/decode_backbuffer.py`). **This same routine
  runs in *either* direction** (`mechanics.md` §36): normally `120(A5)` → the display buffer's
  inactive half, refreshing it each frame; on a room crossing, traced live with zero disk/FDC
  activity either way, it runs *backwards* — the display buffer's inactive half (freshly painted by
  some other, still-unidentified RAM-to-RAM writer) → `120(A5)`, banking the new room's art into the
  cache. `120(A5)` is therefore downstream of the real room-background painter, not the painter's
  target; every `watch` armed on `120(A5)` to find that painter (§33b/§34b and this session's first
  attempt) was watching one hop too late.
  `ScreenFlip_AndCompositeSprites` (`$14d64`) does the same kind of copy but with an
  `and.l (a1),Dn / or.l Dn,Dn / move.l Dn,(a1)+` masked-composite inner loop
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
- **4th pass — the "vanishing sprite" doesn't reproduce; it's a short interact/dig gesture, not a
  disappearance.** The 3rd pass's single 3M-step sample was misleading. Bisecting the same `kbd 50`
  (Down make) / `kbd d0` (Down break) sequence at 25k/50k/75k/100k/150k/200k/300k/400k/500k/1M/1.5M/
  2M/3M steps and rendering+diffing each checkpoint against the base frame (script:
  `scratchpad/cadaver_bisect.py` this session, not yet copied into `tools/` — reads a `.snap`'s live
  shifter video-base + palette directly, same ground truth `gfxview.py` uses, so it isn't fooled by
  the `ScreenBufferA`/`B` role-swap that caused earlier false negatives) shows: the character plays
  a ~5-6-frame animation peaking around 200k-300k steps — crouch, then an arm/implement raised
  overhead (screenshot-confirmed, not inferred) — then relaxes back down, and by **2,000,000 steps
  the frame is byte-identical to the pre-keypress base** (0 px diff, full 320×200 screen). Sending Up
  afterward in the 3rd pass therefore "did nothing" simply because there was nothing left to undo -
  the character was never gone; the 3rd pass's one coarse 3M sample apparently caught a genuinely
  bad frame (most likely a mid-flip buffer read, the same class of bug the 2nd pass's screen-buffer
  guess had already been burned by once). Given the isometric-dig framing of the rest of the game,
  this animation reads most plausibly as a "dig/interact with the tile below" or "duck" gesture
  rather than movement - consistent with no net screen-position change and the near-total lack of
  change to the main entity table already noted in the 3rd pass.
- **5th pass — the bitmask "open thread" above was a misreading; the real mechanism is a 3-way
  round-robin action-script allocator, and it self-clears fast.** Watching just `$162cc`-`$162cf`
  (4 bytes — cheap, unlike a broad screen-buffer watch) across the same `kbd 50`/`kbd d0` sequence
  gives the ground truth: `$162cc` (`ActiveEntitySlotBitmask`) is a single **byte**, bits 0-2 = slots
  0/1/2 "primary" active, bits 4-6 = the same slots' "secondary" flag (set when the action's second
  table entry has a specific tag byte `$82`) - there is no 4-byte-wide bitmask; the earlier "bit 16"
  reading came from treating an unrelated neighbour byte as part of the same word. `$162cd` is
  **not** a stuck completion flag - it's a persistent round-robin index (`IkbdKeyDispatch_ScanTable1616c`
  at `$015924`-`$015964`, reused by the key-release path at `$015986`-`$0159e8`): each new keyboard
  action increments it mod 3 and picks that slot if free, else tries the other two. Each slot's real
  control-block address comes from a small **PC-relative** pointer table at `$15c64` (3 entries only,
  confirming exactly 3 concurrent action slots exist): slot 0 → `$162d0` (what the isolated
  `callcap $15bf4 D1=0` test in the 3rd pass wrote to - explaining why it stayed zero for the real
  Down-key path), slot 1 → `$16306`, slot 2 → `$1633c`. The real Down-key press was dispatched onto
  **slot 1** (`$16306`), not slot 0. `EntityScript_StartAction_SlotD1_ActionD0` (`$15bf4`)
  unconditionally writes `ActionScriptPointerTable[actionId]` into the slot's control block (offsets
  0/4) and only conditionally re-*sets* the active bit (skipped if the pointer is null); a **second**
  call ~82,000 steps later (well before the animation even peaks around 200k-300k) writes a **null**
  pointer, clearing both the control block and the bit - i.e. the bookkeeping fully idles out on its
  own, fast. Confirmed by direct memory dump: `$16306` is completely zero at every checkpoint from
  50k through 500k, and the visual animation still has hundreds of screen pixels changing well after
  that. **So whatever drives the multi-hundred-thousand-step visible animation is not this slot-
  allocator system at all** - the player's animated pose must be tracked somewhere else entirely,
  consistent with the 3rd pass's finding that `EntityTable_Base` (`$16380`) is barely touched either.
- **5th pass, cont. — two concrete candidate regions for what actually drives it.** A/B RAM diff
  (`base` vs. a matched-length **idle** control run vs. the **Down**-key run, both 300k steps, video
  memory excluded) isolated 542 input-only changed bytes in 39 runs. Two stand out: **`$0180b6`-
  `$018ae9`** (small, scattered single/double-byte deltas, close to the global screen-buffer-pointer
  struct at `A5=$18152` - a plausible home for a per-character animation-frame-index or timer field)
  and **`$02ca83`-`$02cd63`** (~740 bytes, dense/structured change, sitting near
  `CompositeBackBuffer` at `$2de08` - a plausible unpacked sprite/work-buffer region for whichever
  frame is currently being composited). A third cluster, **`$03672b`-`$038378`** (regular ~48-byte-
  stride 2-byte deltas), is more likely a secondary lighting/shadow recompute triggered by the
  animation than the animation state itself.
- **5th pass, cont. — both candidates traced and downgraded; the real animation-state address is
  still unknown.** `watch 180b6 2612` across the full `kbd 50`/`kbd d0` sequence shows this region is
  the `TimerQueueService`/sound-command area already named in the 2nd pass (writers at `$0158e0`-
  `$015c92`, matching `2534(A5)`/`304(A5)` from that pass's notes) - it's rewritten constantly every
  VBL regardless of input, and the handful of bytes that come out different at 300k almost certainly
  reflect a sound effect the Down action queued (e.g. a grunt/thud), not the visible pose. `watch
  2ca83 738` shows a tight cluster of routines at `$00bf72`-`$00c242` (unnamed) running roughly once
  per VBL: `$00bf72` clears the ~369-word buffer, `$00c1a0`-`$00c242` then fill it - a per-frame
  recompute, not a static sprite-frame table, and also running whether or not Down was pressed. Both
  regions differ between the idle and Down runs only as a **downstream side effect** of the Down
  action (sound queued / whatever this buffer recomputes being sensitive to the character's current
  pose as an input), not because either address *is* the animation state. **Next step, more targeted
  than another RAM diff**: watch or trace what source address `ScreenFlip_AndCompositeSprites`
  (`$14d64`) / `SpriteCompositeInner_AndOrMaskLoop` (`$14f24`) reads the player sprite bitmap from on
  a gesture-frame vs. an idle-frame composite - that pointer (wherever it's stored) is the actual
  "current animation frame" state, and tracing it top-down from the known compositor is more direct
  than guessing from an undifferentiated RAM diff.
- **Graphics format — live screen only, not the source data.** The live screen (`ScreenBufferA` at
  `$19100`) is plain standard-ST `st-interleaved` 320×200×4bpp — no unusual packing — using the
  palette table at `$5a9c` (16 big-endian `$0RGB` words, the same one `$015302` copies to
  `$ffff8240` at boot). Rendering it directly (`tools/gfxview.py` "st-interleaved" layout, or the
  a-priori-simplest guess) reproduces the `gameplay.png` milestone screenshot exactly. This is the
  *composited output*, not the room's source data — the 7th pass (below) found and decoded the
  actual packed sprite/object sheet that gets composited into it.

- **7th pass — found and decoded the packed sprite/object sheet: `$029800`-`$02de08`.**
  Full derivation in `graphics.md` (new this pass). Summary: the 6th pass's own "7 candidate data
  spans" from `gfxview.py --contact`/`--html` were regenerated and logged as real addresses for the
  first time (previously eyeballed once and dropped); the most plausible-looking one by proximity
  to two adjacent room-sized palette tables (`$04d21c`-`$06b000`) turned out to be a dead end (no
  tile structure at any width). The actual sheet was found the way the 6th pass's own method says
  to — top-down from the compositor, not another RAM diff: disassembling the "per-frame recompute"
  routine the 5th pass had flagged and downgraded (`$00bf72`-`$00c242`) shows it's a **second,
  more general sub-pixel (arbitrary-shift) masked blitter**, distinct from
  `SpriteCompositeInner_AndOrMaskLoop` (`$14f24`), reading its source bitmap from a wide packed
  region via a 3-word per-entry header. Rendering that region (32×32-cell grid, live palette) shows
  17,928 bytes of coherent, distinct art bounded cleanly by `CompositeBackBuffer` (`$2de08`) on one
  side and noise on the other; the 6th pass's own `$2ca84`/`$2ca94` player-frame pointers land
  inside it, at byte offsets that are **not** aligned to the 32×32 grid — the real per-entry format
  is a variable-size, header-prefixed pack, not a uniform tile grid (the grid was a diagnostic
  rendering choice, not the true stride). Exported as `spritesheet_29800.png`. This also produced a
  corrected read on what kind of asset this is: it looks like a **sprite/prop/object catalog**, not
  a floor/wall tile sheet — `gameplay.png`'s cave walls are one irregular hand-painted texture with
  no visible tile seams, and a cold-boot `ATARI_TRACE_GEMDOS=1` run showed only 2 GEMDOS calls
  total before stalling at the restore-game prompt, meaning room/level data isn't loaded via TOS
  `Fread` at all (consistent with the Medway Boys section's existing finding that this game reads
  raw disk sectors directly). Whether "room layout" is a tile-index grid or just a pointer to one
  pre-rendered per-room background bitmap is still open — see Next steps.

- **7th pass, cont. — the 32×32 grid render was wrong; width/height are struct fields, confirmed and
  fixed.** Flagged on review (the exported PNGs repeated the same silhouette in nearly every cell,
  and the two prop crops had a second unrelated shape bleeding in below the real object — both
  classic symptoms of decoding at the wrong stride). Root cause found and fixed rather than
  re-guessed: `$00bf72`'s own caller (`$00bef0`-`$00bf6e`, disassembled this pass) computes a
  per-call row-bytes constant at global `1246(A5)`, read live off the snapshot as `16` (= 32 px) —
  but the routine that actually **draws** every sprite-object-array entry (player included) is
  `SpriteList_ClipAndCompositeOne` (`$00d856`, via `jsr $14d64`), which reads **struct offset `+50`
  (width in 16-px groups) and `+51` (height in rows) directly per-object** — no guessing needed, it
  was sitting in the already-captured 22-entry array dump the whole time. Player (slot 0): 32×42.
  Slot 1: 32×28. Slot 16: 32×23. Re-rendering at these exact sizes fixed both symptoms cleanly:
  the player's frames (`$2ca84`/`$2ca94`, 32×42, `player_frame_alt.png`) now render as an
  unambiguous armoured-knight character sprite, and individual prop renders end cleanly in black
  with no bleed. `spritesheet_29800.png` regenerated at the correct 32×42 stride — the recurring
  "roof" motif across frames turned out to be real (a shared isometric bounding-cell silhouette
  every frame sits in), not a decode artifact. `$00bf72`'s actual purpose is now open again — it
  isn't what draws the sprite array after all (see `graphics.md` §2).

- **7th pass, cont. — extracted the full 22-entry sprite-object-array catalog.** Since width/height
  turned out to be plain struct fields, extracting every entry (not just the two spot-checked
  above) became mechanical — written up as a reusable tool rather than repeated one-off renders:
  `tools/sprite_array_export.py` (new, game-agnostic — batch-exports any struct-driven
  sprite/object array given its base, stride, count, and width/height/pointer field offsets).
  Run against `gameplay_empire.snap`, all 22 entries decode cleanly with no bleed and most are
  immediately identifiable against `gameplay.png`'s room dressing: the player, two torches, a
  barrel, an axe, two flowers, two stools, a goblet (the one `state=4` outlier), a **boat** (64×33,
  the only entry wider than 32px), a **chest**, and several woven mats — the boat and chest both
  visibly match `gameplay.png`. Output committed under `reversing/cadaver/sprites/` (one PNG per
  slot, `contact_sheet.png`, `manifest.csv`). Confirms the "no monster in this array" finding above
  more thoroughly — all 20 non-goblet prop slots read as ordinary static dressing. Full writeup in
  `graphics.md` §3.

- **6th pass — found the "current animation frame" pointer the 5th pass was chasing.** Top-down
  from the compositor, not another RAM diff, as the 5th pass's next-step said. Disassembling
  `ScreenFlip_AndCompositeSprites` (`$14d64`) and `SpriteCompositeInner_AndOrMaskLoop` (`$14f24`)
  directly shows the masked-composite inner loop reads its source bitmap from **`A0`**
  (`move.l (A0)+,D2` / `move.l (A0)+,D3`, twice per 16-byte group, `subq.b #1,(A6)` / `bne` driving
  the row count) and writes through `A1` (the screen destination). Tracing callers up the chain
  (`$00d792` `SpriteList_BuildAndDispatch` → `$00d856` `SpriteList_ClipAndCompositeOne`, both now in
  `cadaver.sym`) to the single-sprite (no-overlap) path shows the exact setup before
  `jsr $14d64.l` at `$00d8e8`: `A0` is loaded from **offset `+52`** of a per-sprite descriptor
  struct (`A3`), and `A3` comes from a fixed-stride (`$46` = 70 bytes) array of these structs whose
  base pointer lives at **`(A5)+56`** (`$1818a`, new `SpriteObjectArrayPtr_A5Plus56` in
  `cadaver.sym`) with a count word at **`(A5)+1152`** (`$185d2`,
  `SpriteObjectArrayCount_A5Plus1152` — 22 entries live in `gameplay_empire.snap`). The player
  character is always **slot 0** of that array (only slot whose state byte at struct-offset `+42`
  is `0`; every monster/prop slot seen so far is `5`), so its descriptor sits at a fixed offset from
  the array base (`+52` within slot 0 = struct-relative bitmap pointer, `+20`/`+23` = a shared
  animation-phase counter/derived screen-row-bob byte — `+23 = +20 + ~0x2b`, i.e. the same counter
  drives both, see below).
- **6th pass, cont. — confirmed live, with an exact step window.** Snapshotting
  `gameplay_empire.snap`, sending `kbd 50`/`kbd d0` (Down make/break), then dumping slot 0's 70-byte
  descriptor (`m <arrayBase> 70`, decimal-step checkpoints) across the whole gesture: the `+20`
  phase byte counts down smoothly from its idle value `$22` to `$00` by ~step 220,000, holds at
  `$00` through ~step 240,000-260,000, then counts back up to `$22` (idle) by ~step 400,000-450,000
  — matching the 4th pass's render-confirmed "crouch, arm/implement raised, relax" timeline almost
  exactly. The struct-`+52` bitmap pointer itself is `$0002ca84` (the same region the 5th pass had
  found and provisionally downgraded to "a per-frame recompute buffer, not a static sprite-frame
  table" — it's actually *both*: a live-recomputed buffer that also happens to be exactly where the
  frame pointer points) for the entire gesture **except** a narrow window bisected to **steps
  ~250,000-260,000** (10,000-step checkpoints; `$00` immediately before and after), where it flips
  to `$0002ca94` — exactly `+$10` (16 bytes, one composite-loop row-group) — before reverting. That
  16-byte-offset alternate frame, active only at the phase counter's trough, is the "arm/implement
  raised overhead" pose frame from the 4th pass's screenshot. This closes the "next steps 1" item
  below: the real "current animation frame" state is struct-offset `+52` of the player's
  slot-0 descriptor (a pointer into the `$2ca84`-based per-frame buffer), gated by the phase counter
  at `+20`.
- **What this doesn't yet explain**: only one alternate frame (`+$10`) was seen in this bisection —
  the visually smoother 5-6-frame appearance from the 4th pass may be the `+20`/`+23` counter
  driving a continuous vertical draw offset (the "bob") layered on top of a coarser 2-frame bitmap
  swap, rather than 5-6 distinct bitmaps; not confirmed, would need denser bisection (every VBL,
  not every 10k steps) around the `$00` plateau to see if `+52` visits more than one alternate
  value.

- **7th pass, cont. — the `$00` plateau has exactly one alternate frame, confirmed at 2,000-step
  granularity, closing the 6th pass's open question.** Re-ran the same `kbd 50`/`kbd d0` gesture,
  dumping slot 0's `+20`/`+52` every 2,000 steps (not 10,000) from step 210,000 through 300,000.
  Result is completely clean, no intermediate values ever seen: `+52` is `$2ca84` through step
  218,000, `$00` the phase byte from 220,000, `$2ca94` from **244,000** through **266,000** (a solid
  22,000-step hold, not a narrow blip), then back to `$2ca84` from 268,000, with `+20` itself only
  ever observed as `$02` or `$00` at this sampling rate. So the "5-6 frame" visual impression from
  the 4th pass is **not** additional bitmap frames — it's the `+20`/`+23` phase counter driving a
  continuous bob/position offset over this same 2-bitmap swap, exactly the alternative the 6th pass
  flagged as unconfirmed. Settles next-step item 2 from the 6th pass; no further bisection needed
  here.

- **7th pass, cont. — checked whether non-player slots use the same `+52`/`+20` mechanism: yes, and
  it revealed what the other 21 array entries actually are.** Dumped the full 22×70-byte sprite
  object array (`m 38338 1540` off the live snapshot; array base `$038338`, read from the `(A5)+56`
  pointer field, count `22` from `(A5)+1152` — both match the 6th pass). All 22 entries use the
  identical struct shape. State byte (`+42`): slot 0 (player) is `0`; slots 1-15 and 17-21 are `5`;
  slot 16 alone is `4`. Their `+52` bitmap pointers are **not** in the `$029800`-`$02de08` sheet
  found above — they cluster at `$056fc2`-`$06975f`, inside the span-3 candidate (`$051000`-
  `$06b000`) that the whole-span 320px-wide render had already written off as a dead end. Rendering
  directly at the actual per-slot pointers (not at the span's start address) instead of guessing a
  screen-width bitmap shows why that dismissal was wrong: `decode_span.py` at slot 1's pointer
  (`$056fc2`, 32px wide) renders a small, clean, recognisable object — a grey/green torch bracket
  with a gold flame tip — in the first ~30 rows before the data runs out into the next entry. Slot
  16's pointer (`$05fbaa`) renders a different, more elaborate grey/gold vessel-like shape over a
  woven basket base. Both match static room-decoration silhouettes plausible for `gameplay.png`'s
  furniture (torches, containers), not creatures. **So the 21 `state=5` entries read as static room
  props sharing the player's animation-slot struct, not monsters** — item 3 below (checking a
  monster slot) doesn't yet have a confirmed monster to check; state `4` (slot 16, the one outlier)
  is the best current candidate for "something other than a static prop" but wasn't chased further.
  This means there's a **second packed sprite region** (`$056fc2`-`~$06975f`, inside the wider
  `$051000`-`$06b000` span) alongside the player-only one at `$029800`-`$02de08` — `graphics.md`
  updated with both.

- **7th pass, cont. — Right (`kbd 4d`/`kbd cd`), tried with the exact same make/break discipline
  that worked for Down, activates nothing.** `ActiveEntitySlotBitmask` (`$162cc`) sampled at steps
  20,000/40,000/100,000/200,000/400,000 after the gesture stays `$00` throughout — no action slot
  ever goes active, unlike Down's immediate, clean activation. Inconclusive rather than negative:
  either Right genuinely needs a different trigger (held rather than tapped, a different scancode
  than the `$4d`/`$4c` pair the table dump found, or gated behind some precondition Down isn't), or
  it really is a menu/UI-layer binding as the 2nd pass originally suspected. Not chased further this
  pass — see next-step 5.

- **8th pass — the player animation sheet's "672 B/frame, ~27 frames" stride is not real; corrected
  to unknown/open.** Added `sprite_array_export.py --sequence BASE STRIDE COUNT W H` (uniform-stride
  batch export, distinct from the existing struct-driven `--base`/array mode) and ran it over
  `$029800`-`$02de08` at the graphics.md-stated 672-byte stride. Caught on review, not asserted: the
  one already-confirmed-good frame pointer, `$2ca84` (the idle pose, struct-verified via slot 0's
  live `+52` field), sits at byte offset 12932 from `$029800` — **not** a multiple of 672 (remainder
  164). A uniform stride from that base cannot be the real per-frame layout; the visually-plausible
  contact sheet the naive export produced is coincidence, not ground truth, past frame 0. This
  downgrades the README's own prior "confirmed ... ~27 frames at 672 B/frame" line (graphics.md §2)
  to unverified — real per-frame boundaries are still unknown and need either a header/pointer table
  (not yet found) or more live gesture-bisection data (blocked on finding more triggerable actions,
  i.e. this pass's real focus, below). The export tool itself is fine and reusable; its output for
  this specific region isn't — not committed, kept in scratchpad only.
- **8th pass, cont. — the game's custom IKBD ISR does not parse standard mouse-motion packets;
  confirmed by disassembly and by a live `watch`, not assumed.** Full disassembly of `IkbdIsr`
  (`$1535a`-`$1539c`): it reads one byte at a time from the ACIA data register (`$fc02.w`) into a
  1-byte cell at `A5_isr` (a *different* base than the main-loop's `A5=$18152` — the ISR does
  `movea.l $5abc.l,A5; adda.w #$9e2,A5`, landing at `$018b34`, confirmed live). Two header bytes,
  `$ff`/`$fe`, are recognised as "the next byte is an extended 2-byte report" and get written to
  `A5_isr + sign_extend(header)` (i.e. `$018b33`/`$018b32` — a fixed joystick-0/-1 state byte each,
  not a sparse table, since `$fe`/`$ff` sign-extend to `-2`/`-1`). **Any other byte with the top bit
  set (`>=$80`), arriving when the ISR is idle, gets written to the current-key cell (`$018b34`) and
  then immediately cleared** (`move.b D0,(A5) / bpl skip-clear / clr.b (A5)` — `bpl` isn't taken for
  a negative/high-bit byte, so the clear executes). A standard 3-byte relative-mouse packet
  (`$F8`-`$FB`-headed) is exactly this case: the header byte is written-then-cleared, and the
  following `dx`/`dy` payload bytes (top bit clear, ordinary small integers) fall through to the
  **normal single-scancode path** and get treated as if they were real keyboard scancodes. Verified
  live with `watch 18b30 8` across a `mouse move 20 20`: the trace shows exactly `$f8` written then
  cleared, then `$14` (=20 decimal, the dx/dy byte) written and **held** — i.e. a `mouse move 20 20`
  literally forges a fake keypress of scancode `$14` (which happens to itself be one of the
  `KeyDispatchTable` entries — see below). This is a real mechanism finding, not merely "mouse
  doesn't work": relative-mouse packets don't get silently ignored, they get *misinterpreted as
  spurious key data*, which is worse for testing (a `mouse move` in an earlier pass could have been
  quietly forging an unrelated keypress rather than doing nothing).
- **8th pass, cont. — despite the mechanism above, `mouse move` produces zero net, lasting effect in
  practice; ruled out empirically as well as mechanically.** Idle-vs-mouse-move A/B render diffs at
  matched step counts (3,000 and 30,000 steps) show **0 changed pixels** on both screen buffers, and
  `ActiveEntitySlotBitmask` (`$162cc`-`$162cf`) stays `$00 00 00 00` through a `mouse move 20 20` +
  23,000-step window. The forged-scancode byte is present only for a handful of steps before an
  already-queued, unrelated stray `$00` byte in the ACIA FIFO (present before the mouse packet was
  even sent — a pre-existing harness/boot artifact, not caused by the mouse command) drains behind
  it in the same interrupt burst and clears it again — a narrow, unreliable race, not a usable
  signal either way. **Directly contradicts the 3rd pass's claim** ("`mouse move 40 20` moves a
  visible ~29×24px cursor icon to exactly the predicted screen position") — that claim was not
  re-verified this pass and does not reproduce; treat it as retracted pending re-derivation (see
  `verify-visual-claims-with-frame-diffs` in project memory — this is exactly that failure mode).
- **8th pass, cont. — mouse clicks currently send *zero bytes* at all, a separate, harder gap.**
  `mouse down l` / `mouse up l` only synthesize a keycode-style byte (`$74`/`$75`) when the IKBD is
  in "buttons report as keys" mode (`MouseButtonsReportAsKeys`, gated on `ikbdMouseButtonAction`
  bit 2, set only by a `$07` IKBD command the *game* would have to send). Checked live: this mode is
  `false` in `gameplay_empire.snap`'s state, and the REPL confirms it (`mouse down left
  (buttons-as-keys=false)`), so a `mouse down`/`up` pair enqueues nothing — no bytes, no interrupt,
  no memory change at all. Whether the game ever sends that `$07` command (at some other point in
  its lifecycle) is unknown — needs an `ATARI_TRACE_IKBD` cold-boot trace (see next steps).
- **8th pass, cont. — joystick `$FE` (port 0) direction packets: byte-write mechanism verified, but
  zero downstream effect.** Sent `kbd fe 08` (header `$FE` + direction byte, bit3="right" in
  standard IKBD joystick encoding) and confirmed via direct memory dump that it lands exactly where
  the ISR disassembly predicts, `$018b32 = 08`, and **persists unmodified** through 25,500 steps (no
  auto-clear the way scancodes get cleared on a break code — there was no break code sent). Held the
  same "right" state for 400,000+ steps (`ActiveEntitySlotBitmask` sampled at each step multiple):
  stays `$00 00 00 00` throughout, and a full-screen A/B render diff against a matched-length idle
  control is 0 pixels. Inconclusive on encoding (wrong bit convention, wrong port, or the game simply
  never polls this cell in this room/state) rather than a clean negative, but the byte-delivery
  mechanism itself is now confirmed working, which narrows any future retry to "try different bit
  patterns/the other port" rather than re-deriving the address.
- **8th pass, cont. — Right, *held* (not tapped), settles the 7th pass's open question: still
  nothing.** `kbd 4d` (make only, no break) held for 400,000+ steps, `ActiveEntitySlotBitmask`
  sampled throughout: `$00 00 00 00` at every checkpoint, identical to the 7th pass's tap result.
  Rules out "needs to be held" as the explanation — Right (or at least the `$4c`/`$4d` scancode
  pair) does not drive any action-slot activity under either discipline.
- **8th pass, cont. — re-dumped and correctly parsed the full `KeyDispatchTable`; corrects the base
  address by one byte and settles "is this a movement table?" as no.** The raw dump at `$1616c`
  parses cleanly as 61 fixed 5-byte entries (`[type][sc1][sc2][sc3][actionId]`, type=1/2/3 selects
  how many scancode slots are populated) starting at `$1616d`, **one byte past** the address
  `cadaver.sym`/earlier passes recorded (`$1616c` itself, value `$01`, is unaccounted for — likely a
  count/flag byte, not part of the first entry; the old base produced entries with implausible
  `type` bytes like `55`/`127`/`198` and is simply mis-aligned). At the corrected alignment every
  entry is a well-formed `[1-3][real scancode(s)][action id]`. The scancode set spans nearly the
  entire keyboard — Esc, digit row, most letters, all ten function keys, space, shift (`$2a`),
  alt (`$38`), the three confirmed arrow keys, and more — which reads as a general UI/menu hotkey
  dispatcher (save/load, pause, inventory shortcuts, etc.), not a movement-specific table, backing up
  the standing suspicion from the 2nd/7th passes. **`$4b` (Left) still has no entry anywhere in the
  61**, confirmed at the corrected alignment. One concrete new data point: the Down-key entry
  (`sc=[$50,$51]`) and a separate three-way entry (`sc=[$0c,$0d,$1c]` — minus/equals/**Return**)
  share the **same action id, `$65`** — independent evidence that the Down gesture (already known,
  4th-7th passes, to be a crouch/dig/interact animation with no net position change) is a generic
  "confirm/interact with the current square," triggerable by either Down or Return, not a directional
  move.

- **9th pass — decoded `ActionScriptPointerTable` ($163aa) directly, which redirected the whole
  approach: the planned callcap sweep is uninformative, but exhaustively testing every real
  keyboard action confirms nothing in this room moves the player.** Dumped 1024 bytes (256 4-byte
  entries) from `$163aa` (`m 163aa 1024`) and parsed it as the pointer table `$15bf4` indexes with
  `D0*4`: only **entries 0-116 are distinct** (monotonically increasing pointers `$16864`-`$16fe4`,
  one exception at id 27→28 which goes slightly backward, not investigated further); **every entry
  117-255 aliases to the same terminal pointer, `$16fe4`** — a shared "no real script" placeholder,
  not 256 independent actions as the 8th-pass next-steps assumed. Entry 0 alone is a true null
  (`$00000000`), which `$15bf4`'s own `beq` skips setting the active bit for. This mechanically
  **confirms** (not just empirically re-confirms) the 7th/8th-pass finding that Right's bound action
  (`$c6` = 198 decimal) is a no-op: 198 ≥ 117, so it aliases straight to the shared placeholder —
  there was never a real script to run.
- **9th pass, cont. — ran the priority-1 callcap sweep exactly as scoped (`callcap 15bf4 <n> - D1=0
  D0=<id>` for all 256 ids) and it is a methodological dead end, not a source of new movement
  candidates.** Every non-null id (1-254; 255 untested, off-by-one in the sweep script, inconsequential
  given the finding below) produces the **identical ~20-byte footprint** — `$15bf4` only *installs*
  the pointer into a control-slot struct (`(A4)`/`4(A4)`, clears 46 scratch bytes at `+8`); the
  bytecode interpreter that actually *executes* the installed script runs elsewhere (driven by
  `MainLoop`/`EntityScriptDispatch` over real, unmasked VBLs) and never runs inside a `callcap` call,
  since `callcap` masks IPL 7 for the call's whole duration by design (see its own doc comment in
  `Program.fs`) and returns the instant `$15bf4`'s `rts` fires. A pure install-then-restore call
  cannot show a script's effect, no matter which id is passed — confirmed by the sweep's own data
  (byte count uniform at 20 regardless of id, `D0` end value scaling cleanly as `id*4`, `A4` landing
  on the same control-slot address every time).
- **9th pass, cont. — replicating `$15bf4`'s writes by hand (bypassing `callcap` entirely) also
  produces zero effect, even for Down's own known-good id and pointer; validated against a control.**
  Hand-wrote the exact same install `$15bf4` does — `w`-ing the table pointer into a control-slot's
  offset `0`/`4`, clearing offset `8`-`53` (46 bytes), setting the slot's `ActiveEntitySlotBitmask`
  bit — for **both** slot 0 (`$162d0`) and slot 1 (`$16306`, the slot the 5th pass found the real
  Down keypress actually lands on), using Down's own action id (101, pointer `$16f07`), then ran
  400,000-1,000,000 real (unmasked) steps. **Zero byte change** in the player's sprite descriptor
  (`$038338`) either way — extends, rather than contradicts, the 5th pass's own conclusion
  ("whatever drives the visible animation is not this slot-allocator system at all"): the real IKBD
  key-dispatch path (`IkbdKeyDispatch_ScanTable1616c`/`GuardedCall_15bf4_Single`) does something
  beyond calling `$15bf4` that a hand-replicated memory write doesn't reproduce, and that something
  is what actually matters. **Verified this isn't a harness bug**: the identical script structure
  (settle → dump → `kbd 50`/`kbd d0` → dump → dump) reproduces Down's known effect exactly (phase
  byte and the `+52` `$2ca84`→`$2ca94` frame-pointer swap both visible) when driven through the real
  `kbd` REPL path instead of hand-written memory pokes — see `control_down.txt` in this pass's
  scratchpad (not committed). So the install-by-hand shortcut is out; only the real input pipeline
  reproduces real effects, for reasons not fully traced (not chased further this pass — see Next
  steps).
- **9th pass, cont. — exhaustively drove every remaining real, keyboard-reachable action id through
  the genuine input pipeline; all of them are inert.** Cross-referencing the corrected 61-entry
  `KeyDispatchTable` dump (8th pass) against the newly-decoded `ActionScriptPointerTable` gives
  exactly **12 distinct non-null real action ids** reachable from any key on the whole keyboard:
  `{10, 30, 50, 55, 64, 70, 79, 90, 100, 101, 110, 120}` — everything else bound to a key (`127,
  129, 158, 159, 188, 198`) aliases into the shared no-op placeholder established above. `101`
  (Down/Return) and `110` (Up) were already characterized (crouch/interact gesture; no independent
  effect respectively). Drove the other **10**, each via its own real scancode make+break through
  `kbd` (1,000,000 real steps per id, 500,000-step idle settle beforehand to clear any residual
  animation from the previous id in the same session — no snapshot-reload command exists in this
  REPL, see `Program.fs`'s command list): `55`←Esc(`$01`), `90`←'2'(`$03`), `64`←'4'(`$05`),
  `50`←Ctrl(`$1d`), `100`←'A'(`$1e`), `10`←'6'(`$07`), `79`←Keypad-`(`(`$65`), `120`←Alt(`$38`),
  `70`←F5(`$3f`), `30`←Keypad-Enter(`$6e`). **Every one of the 10 produces zero byte change** in the
  player's 70-byte sprite descriptor and zero `ActiveEntitySlotBitmask` activity across the full
  window. This is a clean, harness-validated negative (same script shape reproduces Down's real
  effect in the same session, see above) — not an inconclusive one. **Every keyboard action this
  game's own dispatch table can reach has now been tested; only `101` touches the player sprite at
  all.** Combined with the already-ruled-out mouse (8th pass) and joystick-`$FE` (8th pass) paths,
  no input mechanism tested across this whole spike moves the player or changes rooms from this
  snapshot. Scripts/data used this pass (parsing/generation only, not committed):
  `gen_action_sweep.py`, `gen_key_sweep.py`, `parse_table.py`, `parse_keytable.py` in this session's
  scratchpad.

- **10th pass — SOLVED: movement is real joystick port 1 (`$FF` header), not port 0 and not the
  keyboard at all. The 8th pass tested the wrong port.** User-supplied ground truth (playing the
  real disk in Hatari, reaching a different room) prompted re-checking the joystick encoding
  against Hatari's own source (`hatari/src/ikbd.c`/`joy.h`) rather than continuing to search the
  keyboard/callcap space the 9th pass had just exhausted. Two things fell out of that: (1) the
  direction-bit encoding used in the 8th pass (`ATARIJOY_BITMASK_UP/DOWN/LEFT/RIGHT` = `0x01/0x02/
  0x04/0x08`) was already correct; (2) the **port** was wrong — on real ST hardware, joystick port 0
  (IKBD header `$FE`) is electrically shared with the mouse, so any game wanting a dedicated
  joystick reads **port 1** (`$FF`) instead, which the 8th pass never tried. Sending `kbd ff 08`
  (port 1, right) from `gameplay_empire.snap` and stepping forward produces immediate, large,
  non-reverting changes across most of the player's 70-byte descriptor — unlike every keyboard
  action tested in the 8th/9th passes, which either did nothing or fully self-reverted. **Confirmed
  visually, not just from byte deltas** (per the `verify-visual-claims-with-frame-diffs` discipline):
  rendered checkpoint snapshots at 0/500k/1M/2M steps plus a release checkpoint using a new
  `snap_render.py` helper (this session's scratchpad — reads the live shifter video-base/palette
  straight from a `.snap`'s `VideoDisplayRegisters` bank via `tools/gfxview.py`'s own
  `load_ram`/`load_video_regs`, so it's immune to the `ScreenBufferA`/`B` role-swap trap that burned
  earlier passes). The player visibly walks from its start position to the chest/mat area on the
  right, **picks up a coin and other items along the way** (inventory boxes fill in, "SILVER COIN"
  appears in the status line), and the walk completes by ~500,000 steps then holds position exactly
  once the direction byte is released (`kbd ff 00`) — a real, controllable, continuous walk, not a
  one-shot animation. All **four directions tested and confirmed** (`kbd ff 01/02/04/08` = up/down/
  left/right), each producing a distinct, visually-clean displacement in a different isometric
  screen direction (Down even picks up a "BOAT" item near the boat prop). Screenshots committed:
  `movement_before.png` (base) / `movement_after_right.png` (after a sustained right-hold — visibly
  moved, inventory populated). This also **retroactively explains** two standing open questions:
  the 8th pass's "Right held produces zero effect" was correctly measuring port 0 (genuinely inert,
  since Right's keyboard-bound action id is the aliased no-op established in the 9th pass) and is
  not contradicted by this; and the "no `$4b` Left entry anywhere in `KeyDispatchTable`" mystery
  (2nd-8th passes) is now explained rather than just unresolved — **movement was never meant to be
  reachable through that table at all**, it's a completely separate, always-on joystick-port-1 poll,
  wholly outside the `$15bf4`/`ActionScriptPointerTable`/`KeyDispatchTable` system this whole spike
  had been investigating for movement. That system is real and does something (Down's crouch/
  interact gesture proves it), it's just not how the player walks.
- **10th pass, cont. — what's still open, plus one lead checked and ruled out.** The routine that
  *reads* `$018b33` (joystick-1 state, `A5_isr - 1`, confirmed live in the 8th pass's ISR
  disassembly) every frame and turns it into a position delta hasn't been located yet — `watch` only
  reports writes, not reads, so it can't find a reader directly. **Ruled out**: an
  `ATARI_TRACE_EVENTS` diff between a matched-length idle run and a joystick-right-held run (both
  600,000 steps from `gameplay_empire.snap`) showed `$15bf4`/`$15c70` (`EntityScript_
  StartAction_SlotD1_ActionD0`/`EntityScriptDispatch`) and their neighbourhood (`$1535a`-`$15ff6`)
  newly exercised during the held-right run — looked promising, but a direct check (dump
  `$162cc`/`$162d0`/`$16306`/`$1633c`, all three known control-slots, 20,000 steps into the same
  `kbd ff 08` hold) found **no pointer installed anywhere** — all three stayed zero. So the extra
  coverage in that address range during movement is most likely incidental (ambient entity
  processing shifted by the walk's different per-frame timing, or the composite/clipping path doing
  more work because the moving sprite overlaps more of the screen — `SpriteList_
  ClipAndCompositeOne`'s clipped-path block hit 1320 times vs. idle's 1100), **not** evidence that
  movement goes through the known 3-slot action system. Don't re-chase that lead without new
  information. The real reader is still unlocated — next pass should disassemble `MainLoop`
  (`$014496`)'s per-frame fan-out directly for a `-1(A5)`-relative or `$018b33`-literal memory access
  (the ISR computes `A5_isr` as `$5abc.l + $9e2` at runtime, so a reader doing the same computation
  won't show up as a literal `$018b33` operand in disassembly — match the *pattern*, not the
  constant). Also still open: whether the player's world-position lives in this room's `$038338`
  descriptor at all (candidate fields `+8`/`+16-19` flagged 8th pass, never confirmed) or is tracked
  in some other global — the raw before/after descriptor dumps from the 9th pass's key-sweep script
  output (scratchpad, not committed) are a starting point for that mapping, not yet done.

- **11th pass — found the real per-frame joystick-1 reader and the movement-application routine,
  closing the 10th pass's open item 1.** Not at the literal `$018b33` operand (the ISR computes
  that address at runtime from `$5abc.l + $9e2`, so no static disassembly shows it as a literal),
  and not by re-chasing the `$15bf4`/`ActiveEntitySlotBitmask` lead the 10th pass had already ruled
  out. Instead: an idle-vs-joystick-held `ATARI_TRACE_EVENTS` diff (300k steps each, both from
  `gameplay_empire.snap`, this pass's own regenerated event logs — the committed `cadaver_events.bin`/
  `blocks.txt`/`cg.dot` are stale 2nd-pass artefacts, left alone) restricted to `--range 6000 40000`
  surfaced a large cluster of blocks executed only in the joystick run, at addresses below the
  `$9000` floor every previous pass's static disassembly happened to start from. A full linear
  disassembly of that floor (`$6000`-`$9000`) found the actual mechanism directly:
  **`$006ac0` (`Joystick1_LatchRawByteToField2243`)**: `move.b 2529(A5),2243(A5)` — once per VBL,
  inside the *real* main per-frame fan-out block (`$006a26`-`$006b60`, which calls
  `TimerQueueService`/`SpriteList_BuildAndDispatch`/the screen-composite chain — the README's
  existing "`MainLoop` fans out to..." description was written from `$014496`, which is a
  *sub-helper* this block calls into for the screen-flip, not the true per-VBL top level; not
  corrected further this pass, just noted so a future pass doesn't re-derive `$006a26` from
  scratch). Gated on bit 0 of `2477(A5)` (an "input frozen" flag) and additionally masked
  (`andi #$83`, dropping the left/right bits) when bit 2 of `2499(A5)` (a shift/modifier flag) is
  set — a directional-lock behaviour, not chased further. **`$006e50`
  (`MovementPathFollow_Field2243Bit7Gate`)**: gates entry on bit 7 of the *latched* byte at
  `2243(A5)` (not the raw joystick cell), then repeatedly calls **`$008870`
  (`MovementStep_ObstacleCheck`)** and applies the actual per-step displacement,
  `sub.w D6,D0` / `sub.w D7,D1` at `$006efe`/`$006f00` — a real position update, looping via
  `bra $6e78` until the obstacle check or a distance threshold ends it. D6/D7 (the per-step
  velocity) come from **`$00737a`/`$005bea`** (`DirectionVectorTable_Lookup_ByField2273` /
  `DirectionVectorTable_16Entries_DxDyPairs`): a 16-entry `(dx,dy)` table indexed by
  `2273(A5) & $f` (a direction-code field, presumably 0-7 used twice for a sign variant), negated
  when `2340(A5)` is set. All five addresses added to `cadaver.sym`. **Not chased further**: what
  sets `2273(A5)` from `2243(A5)`'s bit pattern (the direction-code translation step itself),
  what `$008870`'s obstacle check actually tests, and the still-open "where does the player's
  world position live" question from the 9th pass (D0/D1 here are *candidates*, not yet confirmed
  against a known field on the slot-0 descriptor).
- **11th pass, cont. — drove the confirmed joystick controls to each direction's boundary; no room
  transition or creature found on this room's single screen, but one new interaction surfaced.**
  New tool this pass, promoted straight to `tools/snap_render.py` (this is the second session to
  independently need "render a `.snap`'s live screen via `gfxview.load_video_regs`, immune to the
  `ScreenBufferA`/`B` swap" — the 10th pass's own version stayed in scratchpad and is gone; this
  one is committed so a third pass doesn't reinvent it again). Held each of the four directions
  for 3.5-5M steps from `gameplay_empire.snap`: **Right** walks to the chest/mat area and stops
  (blocked by room furniture) — `movement_walk_to_chest_boundary.png`. **Up** is blocked almost
  immediately by a rock wall directly above the start position — `movement_walk_to_upperwall_boundary.png`
  (small, real displacement — a distinct animation-frame pose, not a bug; the wall is just close
  from this exact starting tile). **Left** walks to the barrel at the top-left of the room and
  stops — `movement_walk_to_barrel_boundary.png`. **Down** walks to the water's edge next to the
  boat prop, stops, and **picks up a "BOAT" inventory item** (a small collectible, not the visible
  boat prop, which stays rendered in the water) — `movement_walk_to_boat_boundary.png`,
  `movement_at_boat_boundary.snap`. Sending the known interact gesture (`kbd 50`/`kbd d0`, the
  crouch/interact action characterized in the 4th-9th passes) while standing at the water's edge
  plays the same generic animation and does nothing room-specific — not a "board the boat" verb,
  at least not through that input. **This maps the joystick's four screen directions to isometric
  diagonals** (Right≈NE toward the chest, Down≈SW toward the boat, Left≈NW toward the barrel,
  matching the 10th pass's "Down picks up a BOAT item" note), consistent with a typical isometric
  control scheme. No monster and no transition anywhere reachable by a single held direction from
  the start tile — the room's exits (if any, beyond the water crossing hinted at by the BOAT
  pickup) are not simply "walk to the edge of this screen," matching the 7th pass's finding that
  this is one hand-painted background, not a tile grid with obvious door tiles.

- **12th pass — REAL ROOM TRANSITION reached: CAVERN → TUNNEL.** User-supplied ground truth ("the
  black door shaped area to the right of the first room leads to the next room") pointed at the
  black notch in the upper-right rock wall the 11th pass's single-direction holds never reached —
  a single held direction (including the Up+Right and Down+Right diagonals) always stopped against
  a rock/chest obstacle short of it, because the movement mechanism found in the 11th pass
  (`$006e50`) walks a straight line into whatever's in front of it and stops, it doesn't route
  around corners. Reaching the door needed a short, human-style zigzag from
  `gameplay_empire.snap`: **Right 1.2M steps → Up 0.5M steps → Right 1.2M steps → Up 1.2M steps**
  (`kbd ff 08` / `kbd ff 00` / `kbd ff 01` between each leg, matching the make/break discipline
  documented above). The screen changes completely on entry — a vertical rock shaft, a
  ladder/tool prop leaning on the wall, a green pool at the bottom — and the status-bar room-name
  field (already known from the "CAVERN" label) now reads **"TUNNEL"**, i.e. this is a real,
  distinct second room, not a scripted animation. `room2_tunnel_entry.png` /
  `room2_tunnel_entry.snap` (untracked, like `gameplay_empire.snap` — a resume point for continuing
  from inside the tunnel). Checked the sprite-object array here the same way the 7th pass did in
  CAVERN: base pointer `(A5)+56` is still `$038338` (the struct memory is reused per room, not a
  fresh allocation) but count `(A5)+1152` is now **2**, not 22 — slot 0 is the player as always,
  slot 1 is a single ordinary static prop (`state=5`, `16×24`, bitmap pointer `$059956` — almost
  certainly the ladder/tool visible in the screenshot). **No monster in this room either** — the
  creature-search item from the 10th/11th passes is still open, now one room further in.

- **13th pass — found the TUNNEL lever's proximity hotspot and its per-object UI, but no tested
  input opens the door behind it.** User-supplied ground truth ("there's a lever on the left that
  opens a door in front of it, leading to a third room") pointed at a riveted wall panel with a
  round dial/valve-wheel, mounted on the right-hand wall of the shaft from the player's entry
  angle. Holding Left (`kbd ff 04`) ~1.2M steps from `room2_tunnel_entry.snap` walks the player
  flush against it: the status-bar name field, blank in the plain "TUNNEL" idle state, now reads
  **"LEVER"**, and the icon panel gains two object-specific icons (a bracket/hook icon + a key
  icon) — `room2_lever_boundary.png`/`.snap`. This is the same UI class as CAVERN's boat
  (`?` + hand-arrow icons when named "BOAT", 11th pass) — **per-object display icons, not a verb
  selector** — confirmed by cross-referencing the two screenshots side by side (different icon
  pairs per object). The sprite-object array is unchanged at **count 2** (`$185d2`, player + the
  12th pass's ladder/tool prop) — **the lever has no discrete `EntityScriptDispatch`-tracked
  entity**; it's background art with a proximity name-hotspot, not a game-object.
- **13th pass, cont. — every input mechanism tried at the boundary is inert; the door never opens
  and the object-array count never changes.** Tested from `room2_lever_boundary.snap` (re-render +
  pixel-diff confirms no persistent change after each):
  1. The known keyboard interact gesture (`kbd 50`/`kbd d0`, Down arrow, action 101, characterized
     4th-9th passes) — same generic no-op as at CAVERN's boat (11th pass).
  2. **Joystick-1 fire alone** (`kbd ff 80`, bit `$80` per Hatari's `ATARIJOY_BITMASK_FIRE`,
     `hatari/src/includes/joy.h`) — genuinely untested by any prior pass (8th-9th only tried
     movement bits and the wrong port; the keyboard sweep never touched the joystick byte at all).
     A tap flashes an orange highlight border onto the bracket-icon slot for a few frames, then it
     clears on its own — reproduced identically with a 20,000,000-step hold (`scratch_fire_5m`/
     `10m`/`20m`, not committed), so it's edge-triggered/one-shot, not something a longer hold
     advances further.
  3. Fire combined with Left in one joystick packet (`kbd ff 84`) — same highlight-flash, no
     different outcome.
  4. **Space bar** (`kbd 39`/`kbd b9`) — tested because Wikipedia's Cadaver page (unverified for
     this specific ST release, not the game's own source) describes Space as opening a "rucksack"
     inventory screen. No visible effect at any wait length up to 10,000,000 steps post-break. Then
     checked directly: freshly dumped the full 61-entry `KeyDispatchTable` (`$1616d`, corrected
     base per the 8th pass) and parsed all 5-byte entries — the 12 real + 6 alias action ids match
     the 9th pass's list exactly, and **no entry anywhere contains scancode `$39`**. Space is not
     wired into this pipeline on this release at all; the negative result is real, not a timing
     miss.
  5. Held Left for 1.5M more steps from the boundary — zero pixel diff (`ImageChops.difference`
     bbox `None`) — confirms the player is genuinely flush-blocked against the panel, not stopped
     short by an unrelated rock the way single-direction holds stopped short of CAVERN's door.
  6. Up and Down nudges (500K steps) from the boundary both walk the player **off** the "LEVER"
     zone entirely (name field goes blank, icon panel reverts to empty) rather than closer to
     anything — the hotspot is narrow and only reachable via the Left approach used here.
- **13th pass, cont. — fire does have a real, traced effect, just not on the door.** `watch 38338
  46` (the player's 70-byte descriptor, `$038338`) across one fire tap shows genuine writes at
  offsets `+$0e`/`+$10`/`+$12`/`+$14`/`+$15`/`+$16`/`+$17` from code at `$00afb2`→`$00db4a`→
  `$00db54`→`$00db58`→`$00db5e`→`$00db68` — new addresses, not yet named or disassembled — on top
  of the already-known idle-loop writes to `+$16`/`+$2d` from `$00f72a`/`$00f740`/`$00fd1c`/
  `$007472`. This is a genuine action/animation-state update (matches the visible icon-highlight
  flash) but it never touches the sprite-object count or produces any pixel change in the room's
  door area. **Net: the lever is real (named, has its own icon pair) but nothing tried this pass
  opens the door behind it.** Its trigger logic isn't in the `EntityScriptDispatch` or
  `KeyDispatchTable` systems already mapped, so it's bespoke room-specific code — `$00afb2`/
  `$00db4a` (this pass's new fire-driven lead) is the concrete place to start disassembling next,
  rather than trying more input combinations blind.

- **14th pass — systems survey: collision, graphics compositing, and the entity-script bytecode
  interpreter, all reversed statically (no new input-guessing).** Scope change from the 13th pass:
  the lever's door is a genuine dead end for now (see its own next-step item below), so this pass
  covered three algorithms that don't need it or a live creature. Full detail in `mechanics.md`
  (new), `graphics.md` (extended), and `ai.md` (new) respectively; summary:
  1. **Collision (`$008870`, `mechanics.md`)**: not a pixel probe and not a static per-room mask —
     a live bounding-box test against the sprite-object array plus a second, separate "portal" table
     (same 70-byte stride, different base), refined by an optional per-room quadrant-cutout selector
     (`(A5)+140`) that approximates an irregular room shape from a handful of rectangles, and a
     direction-dependent diagonal-corner allowance at doorways. A dedup'd "touch" event cache
     (`$00e614`) queues a one-shot opcode into the same VBL-serviced command ring
     `TimerQueueService` drains, plausibly how pickups trigger.
  2. **Graphics compositing (`graphics.md` §4)**: the full back-buffer→screen pipeline is a
     `trap #4`-yielded, fully-unrolled block copy (`$0144b8`) spread across VBLs to avoid tearing;
     sprite compositing (`$14d64` family, `$14f24`) and the previously-unknown `$00bf72` blitter
     turn out to be **the same underlying sub-pixel AND/OR shift-mask primitive**, `$00bf72` settled
     as a multi-item window/panel compositor (into scratch RAM, not the live screen) rather than a
     room-tile painter. Also re-checked, per a direct user challenge to the 7th pass's "one
     hand-painted background" claim, for real tile periodicity in the rendered room: none found
     (two independent checks, aligned-grid and arbitrary-offset) — narrows rather than reverses the
     earlier finding (nothing tile-*blits* the visible room at runtime; whether the source art was
     tile-*authored* and baked to one bitmap per room is still the README's own next-step #2).
  3. **AI/entity logic (`$15c70`, `ai.md`)**: fully decoded as a 17-opcode (`$80`-`$90`) bytecode
     interpreter with literal bytes (`<$80`) as frame/pose values. **It is the same interpreter
     already driving the player's own 3-slot keyboard-action system** (5th-9th passes) — not a
     separate, still-dormant monster-AI VM — so this closes the interpreter side of the "reverse the
     AI once a creature exists" next-step in advance; only the data (a creature's own script
     content) would remain to reverse later. Also found, as a side effect of tracing the dispatcher's
     epilogue: it flushes 11 PSG sound-chip registers once per dispatch pass, not
     `TimerQueueService`'s command queue as previously assumed for sound.
  4. **Bounded look at the lever's fire chain** (`mechanics.md` §8, timeboxed as scoped): traced
     `$00afb2`'s per-object rescan loop and `$00db4a`'s field-packaging into a `state==5`-gated queue
     push, consistent with a generic "select the nearest interactable prop" pipeline (matches the
     highlight-flash seen at other props too, not lever-specific) — not chased to `$b1a2`/`$ddb6`,
     still doesn't explain the door.
  5. **Bonus, found via embedded debug strings rather than more disassembly** (`mechanics.md` §9): a
     developer error-string table sits right after the AI opcode `$89` table (`$1729d`+`$2a`
     onward) — `"DOOR ERROR"`, `"BOTH ROOMS BLOCKED"`, and a dozen other engine diagnostics. A raw
     scan for code referencing those two strings' addresses landed directly on the **real
     room-transition executor** (`$007104`-`$007364`), previously untouched: it resolves a portal's
     target room id, gates entry through two undisassembled checks (`$de5e` = "DOOR ERROR" on
     failure, `$e84a` = "BOTH ROOMS BLOCKED" on failure), and either treats the target room as
     already resident or calls an undisassembled `$defa` to load it. This reframes the lever
     question from "what input opens it" to "does its portal-table entry exist and pass these two
     gates" — three concrete disassembly-only next steps in `mechanics.md` §9, no more input
     guessing needed.

  **Update, 39th pass**: `$de5e` (left undisassembled here since the 14th pass) is now fully
  decoded, `mechanics.md` §38d — it's not a portal-table lookup at all, it's a **spatial
  point-in-rectangle scan over every room record** (type 3, §38a), testing a world coordinate
  against each room's bounding box (record fields `+1`/`+3`/`+4`/`+5` = x0/y0/width/height) until
  one contains the point; `D7<0` (the "DOOR ERROR" case this section already named) means no room's
  rectangle contains it. Proven live end to end for the TUNNEL→CAVERN crossing: the resolver's
  input coordinate `(20,17)` sits exactly on the shared edge between TUNNEL's rect
  `[19,12]`-`[22,17]` and CAVERN's rect `[12,18]`-`[22,28]`, and the actual current-room commit
  (`$0000727c`) writes slot 0 (CAVERN). This also answers item 2 of "Next steps" below and the
  room-connectivity half of item 7 — rooms connect by geometric adjacency on a shared coordinate
  grid, not an explicit exit graph; see `mechanics.md` §38 for the full writeup.

- **15th pass — settled: TUNNEL's portal table has no entry for the lever's door at all; the "no
  input opens it" finding is now explained, not just re-confirmed.** Ran the 14th pass's own
  three-step plan (`mechanics.md` §10, new): dumped TUNNEL's portal table directly from
  `room2_lever_boundary.snap` (2 live entries, both non-degenerate — `$8ac8`'s bbox bytes turned out
  to be a direction-dependent threshold test, not min/max containment, correcting §5's
  oversimplified analogy to §4), then dereferenced both entries' door descriptors to read the actual
  target-room-id word `$007104` branches on. **Both are the two special-cased "not a real room"
  values, `$0000` and `$ffff`** — meaning neither of TUNNEL's live portals ever reaches
  `$de5e`/`$e84a`/`$defa` in the general case at all. Traced both special-case paths to their end:
  the `$ffff` entry is a self-contained sound/event-cue queue-push with no door semantics
  whatsoever; the `$0000` entry *does* run the full `$de5e`→`$e854`/`$e84a`→`$defa` chain, and its
  geometry (sitting at the room's `RoomMaxY` edge) matches the already-proven CAVERN exit, not
  anything new. `$defa` itself also turned out not to be the sector-level loader — it's one more
  ring-304 queue push (opcode `$8`), deferring the real load to an as-yet-unlocated opcode-`$8`
  consumer. **Conclusion, with disassembly behind it rather than exhausted input-guessing**: no
  portal-table entry for the lever's door exists yet in this game state — not a disk/data-residency
  gap, but game state that some other mechanism (most plausibly the still-undisassembled
  `$00b1a2`/`$00ddb6` fire-chain tail from §8) must write before `$008870` can ever route there.
  Driving `$007104` directly via `callcap` (the 14th pass's fallback suggestion) would not help,
  since the blocker is upstream of the executor, in the portal table itself. Full derivation and all
  raw addresses/bytes in `mechanics.md` §10.
- **15th pass, cont. — the fire chain's last two unknowns disassembled, and the whole pipeline ruled
  out both statically and live: fire cannot open this door under any tested input.** `$00b1a2` (§8's
  remaining unknown) is a generic even-alignment assert on an animation-frame pointer (prints
  `"ANI PIC HAS GONE ODD"` on failure); `$00ddb6` is a generic spatial-overlap/selection-list builder
  for whatever candidates `$00db8a` feeds it — neither writes anywhere near the portal table, a door
  descriptor, or any room-transition global. Confirmed live too: `watch`ed the portal table's pointer
  (`(A5)+88`), count (`(A5)+1162`), and full 140-byte body across fire-tap/release, the known
  interact gesture, and fire+Left combined from `room2_lever_boundary.snap` — zero hits, byte-
  identical before/after. **New lead, not chased**: the lever's icon panel shows a bracket/hook icon
  *and a key icon* (13th pass) — read at the time as generic per-object UI, but in hindsight a
  plausible hint this needs an inventory item clicked onto the object (a mouse-icon-click action),
  a whole input class this spike has never properly exercised (the 8th pass found mouse-motion
  packets get misinterpreted as spurious keystrokes, and no pass has tried clicking a specific
  inventory/UI icon slot). Full writeup `mechanics.md` §11.
- **16th pass — both of the 15th pass's remaining leads closed; the lever's door is now this
  one-disk spike's confirmed boundary.** Two disassembly/trace-only checks, no new input-guessing:
  1. **The icon panel is not UI-driven at all.** `$00bef0`/`$00bf72` has exactly two callers in the
     whole loaded image (found by brute-force-scanning the snapshot's RAM for BSR displacements,
     since `--callers` only scans the TOS ROM — a standing tool gap). Both are internal per-object
     loops, not input handlers: `$00af6a` (inside the fire-rescan loop from §8) passes `D0` = the
     byte at `(A5)+2455`, and `$00cea8` (an unrelated construction loop) hardcodes `D0=0`. Tracing
     `(A5)+2455`'s one and only writer (`$0007590`) leads to a small byte-stream interpreter fed by
     `$007480`'s move/turn-state dispatcher — **`(A5)+2455` is the player's own current
     movement-animation frame byte**, not an icon-selection index. There is no keyboard
     cycle-icon-then-confirm mechanism anywhere in this call graph; the bracket/key icon pair is
     drawn automatically, without any user selection to trace.
  2. **Mouse buttons-as-keys is conclusively, not just currently, off.** `mouse down l` against
     `room2_lever_boundary.snap` still reports `buttons-as-keys=false` (matching the 8th pass at
     `gameplay_empire.snap`), and a fresh cold-boot `ATARI_TRACE_IKBD=1` run (15,000,000 steps,
     boot → gameplay) logs exactly three IKBD commands total — `$80 $01` reset, `$12` mouse
     disabled, `$1A` joystick auto-report disabled — **`$07` (the buttons-as-keys command) is never
     sent**. The game turns the mouse off at boot and never turns buttons-as-keys on anywhere in the
     traced boot path or the live session that reached the lever.
  Both of the 15th pass's own leads are now dead ends, disassembly- and trace-grounded rather than
  input-guessed. Combined with §§7-11 (no portal entry, fire chain proven inert, keyboard/joystick/
  interact exhausted), **every currently-identifiable input path to the lever's door is closed** —
  this spike is switching scope to next-steps item 7 (find a creature/monster in either room) rather
  than continuing to chase the door. Full writeup `mechanics.md` §12.

## Next steps

1. ~~Decode the sprite sheet's per-entry width/height~~ — **done, 7th pass**: they're struct fields
   (`+50`/`+51` on the sprite-object array, `$038338`), not a header inside `$00bf72`'s data. What's
   still open is `$00bf72` itself — it isn't the routine that draws the sprite-object array
   (`$00d856`→`$14d64` is), so what it *does* draw is unknown. `callcap` differential testing against
   it (vary `D0`-`D2` register presets, diff the write footprint) is the concrete way to find out.
2. ~~Settle "tile-indexed room vs. one pre-rendered background per room"~~ — **done, 39th pass,
   `mechanics.md` §37: neither.** A room's "background" is its full set of static objects (walls,
   props, terrain pieces), instantiated from the current room record (`(A5)+164`, a new field this
   pass identifies) into the same shared object array real entities live in (`56(A5)`), then drawn
   once via the ordinary entity masked-blit renderer (§33b/34b) — not a tile grid, not a pre-rendered
   bitmap, and no disk/FDC read is needed at crossing time because every room's objects are already
   resident (matching the "self-contained, no swap needed" milestone and the 12th pass's own
   no-`Fread`/no-FDC finding). Room record byte `+29` = object count, byte-exact confirmed against
   both TUNNEL (2) and CAVERN (22).
3. ~~Check whether a non-player slot uses the same `+52`/`+20` mechanism~~ — **done, 7th pass**: yes,
   but all 21 non-player slots read as static room props (torches/containers), not monsters (state
   `4` on slot 16 alone is the one outlier worth a second look). No monster/creature has actually
   been found in this room yet — that's the open item, not the mechanism check.
4. ~~Denser per-VBL bisection of the `+20 = $00` plateau~~ — **done, 7th pass**, at 2,000-step
   granularity: exactly one alternate frame (`$2ca94`), no third value at any sampled point. The
   4th pass's "5-6 frame" look is the phase counter's continuous bob on top of this one 2-frame
   swap, not additional bitmaps.
5. ~~Try Right the same way~~ / ~~try mouse/joystick~~ / ~~callcap-sweep `$15bf4` for the real
   movement trigger~~ — **SOLVED, 10th pass: real joystick port 1 (`kbd ff 01/02/04/08` =
   up/down/left/right), not the keyboard/callcap system this whole item was chasing.** The 8th pass
   tested joystick port **0** (`$FE`), which is electrically shared with the mouse on real ST
   hardware — port **1** (`$FF`) is the dedicated joystick port and was never tried. All four
   directions confirmed both by descriptor-byte deltas and by rendered before/after screenshots
   (`movement_before.png`/`movement_after_right.png`) — the player visibly walks and picks up items
   along the way. The keyboard/`ActionScriptPointerTable`/`callcap` investigation (9th pass) was not
   wasted — it correctly proved that system handles UI/interact actions only (Down's crouch gesture),
   not movement; the two are unrelated mechanisms. See the 10th-pass README entries for full detail
   and the still-open "where's the per-frame joystick-poll routine" question.
6. ~~Locate the per-frame routine that reads `$018b33` and turns it into a position delta~~ —
   **done, 11th pass**: `$006ac0` latches it into `2243(A5)` every VBL, `$006e50` gates the actual
   `sub.w`-based position update on that latch's bit 7, `$008870` does a per-step obstacle check,
   and `$00737a`/`$005bea` supply the per-direction `(dx,dy)` vector. See the 11th-pass README entry
   for the full chain and what's still unconfirmed within it (the `2243(A5)`→`2273(A5)`
   direction-code translation, what `$008870` actually tests, whether D0/D1 here *are* the
   player's world position or just this loop's locals).
7. ~~Walk to a room edge and find a real transition~~ — **done, 12th pass: CAVERN → TUNNEL**; a
   second, self-looping CAVERN door found the 17th pass (`mechanics.md` §13). **Find a creature in
   either room — STILL OPEN, and confirmed to exist just past TUNNEL's lever.** The 17th pass briefly
   claimed this was a closed, no-creature search after enumerating both rooms' *current* portal
   tables; that was wrong and got retracted the same pass. Ground truth (the game's own published
   walkthrough, and the user's own prior playthrough of this exact one-disk file): pulling TUNNEL's
   lever opens a door to a room 3 with a "spiky floater" enemy, and later rooms have maggots and
   worse. **What's actually confirmed exhausted**: a bare keypress at the lever writing directly to
   TUNNEL's portal table — the 9th/13th passes' keyboard-action sweep plus a 17th-pass sweep of every
   remaining real action id and every direction/fire combo, done specifically at the lever's position,
   produced zero portal-table change every time. **What's not yet tried**: whatever the lever's real
   trigger condition actually is (not necessarily a `KeyDispatchTable`-bound action at all), and —
   more promising — finding room 3's data directly rather than triggering it via play. A 17th-pass
   `gfxview.py --contact` scan of `room2_lever_boundary.snap` found **9 distinct palette tables** (this
   spike had only accounted for 2) and confirmed a **104KB span (`$51000`-`$6b000`)** only ever sampled
   at 2-3 pointers so far (torch/goblet/boat) — real evidence more rooms' assets are already resident
   in this one-disk image, matching its own "self-contained, no swap needed" milestone note (top of
   this file). That resource table was found and fully traced (`mechanics.md` §14): **all 64 slots
   are still empty** — `callcap`-verified, three different target ids all miss — so CAVERN/TUNNEL were
   linked directly at boot, not through this generic system, and nothing has registered a new room
   into it yet. A from-scratch, descriptor-level re-sweep of every keyboard/joystick/fire input at the
   lever (not just the live portal table, the actual door descriptor bytes) also came up empty, as did
   a full disassembly of `TimerQueueService` (a sound-queue producer, not the interaction-script
   consumer the 14th pass had guessed). **Concrete next steps, in order**: (1) find what *writes* into
   the empty resource table (untried — the same static-scan technique that found every other writer
   this pass would work here too); (2) check whether the lever needs an inventory precondition (the
   walkthrough lists collecting a pick before it, though not explicitly *for* the lever — verify
   whether CAVERN's axe/pick prop has ever actually been picked up in any snapshot); (3) try a finer
   position sweep right at the lever, since only the one position reached by the 13th pass's original
   held-Left approach has ever been tested. **Update, 18th/19th pass**: item (1)'s writer was found —
   `$00c9ee`, the save-game *restore* deserializer, gated behind a boot-menu branch this spike has
   never taken (`mechanics.md` §15) — and the 19th pass traced the *serialize* side's own trigger all
   the way up: it's not a player action at all, it fires automatically once at the very start of every
   boot on an always-empty table (`mechanics.md` §17), which retires the previously-planned
   save→reboot→restore live test as uninformative (the buffer it would produce is always empty by
   construction). Item (2), the axe/pick check, was attempted the 19th pass but not completed —
   navigation to the prop stalled against what reads as real room geometry, not a mechanism finding;
   see `mechanics.md` §17d for the concrete resume options. **Update, 21st pass**: item (3), the finer
   position sweep, is now also closed (`mechanics.md` §20) — retracting the pickaxe-precondition
   reading per direct user ground truth ("the lever needs no item, just the action") reopened item (3)
   as the live next step, but a careful, settled (not short-nudge — see §20a's own methodology note)
   directional sweep from `room2_lever_boundary.snap` found the player **hard-blocked with zero
   clearance** on the two sides facing the interactive object (Up, Left — 300,000+ held steps, no bbox
   change) and the "LEVER" name-hotspot itself **gone by 3 settled units** in either direction that
   *is* free (Down, Right — screenshot-confirmed via `tools/snap_render.py`). There is no second
   reachable tile both inside the hotspot and different from the one the 13th pass already tested;
   interact retried at every position reached along the way, watching TUNNEL's live portal table
   directly rather than guessing from a screenshot, produced zero effect every time. **Update, 22nd
   pass**: the standing "is the lever object even flagged interactive" question (never actually
   checked despite `mechanics.md` §4 documenting the classification mechanism since the 4th pass) is
   now answered — it isn't (`mechanics.md` §21). The object's own `byte24` top bit is set, but the
   linked `+10`→`+15` bit-2 flag §4 requires alongside it is clear, so the AND fails and the object is
   plain scenery, not "interactive/pickup." Combined with §20's own "AABB overlap unreachable"
   finding, the touch/opcode-`$9`/ring-304-queue pathway (§4a/§18a) is now a double negative for this
   object, closed without needing to trace §18a's generic per-entity dispatcher against it at all. The
   two leads left standing are a genuinely different, uncharacterized input verb (outside the 9th
   pass's action-id sweep), or a whole-image caller-graph scan (`find_ram_callers.py`/
   `find_field_writers.py`) for whatever actually gates this door, since neither the portal table
   (§10) nor the touch/interactive pathway (§21) turned out to be it — §21d recommends the
   caller-graph scan as the next concrete step, matching this spike's own pattern of static techniques
   outperforming live input-guessing from §9 onward. **Update, 23rd pass**: following §21d's own
   recommendation, finished the embedded debug-string scan (`mechanics.md` §9) past where it had
   stopped, and found something bigger than expected — a whole previously-undocumented "object verb"
   bytecode interpreter (LOCK/UNLOCK, MOVE/GOMOVE/STOPMOVE, GOANI/STOPANI, creature KILL/WAKE/SLEEP,
   rucksack add, chest UNLOCK/UNTRAP/CLEAR, a potion op), found via the same unique-debug-string
   address-reference technique that cracked `"DOOR ERROR"` in §9. Its LOCK (`$0104a0`) and UNLOCK
   (`$0104ae`) opcodes `bset`/`bclr` bit 2 of struct offset `+15` on an object resolved by numeric id —
   the exact bit the 22nd pass's own §21b found clear on the lever's `+10`-linked struct, via a
   resource-table lookup (types 6/9, not rooms' always-empty type 8) that's plausibly populated where
   type 8 wasn't. Also disassembled the ring-304 queue's generic (non-`$8`) opcode path as a genuinely
   new per-entity tagged-record event dispatcher (`mechanics.md` §22e), and confirmed the fire chain
   still doesn't reach any of this (§22f — §11's "cosmetic only" finding stands). Neither new
   mechanism is yet tied to the lever specifically — the LOCK/UNLOCK opcodes have zero direct
   `bsr`/`jsr` callers (reached only through an unlocated computed-jump dispatch table), so the
   concrete next steps (`mechanics.md` §22g) are finding that dispatch table (to get LOCK/UNLOCK's
   real opcode numbers), dumping resource types 6/9 live to check whether they're populated, and
   decoding the ring-304 tagged-record jump table (`$00fe84`) to see whether it can reach the verb
   interpreter from some entity other than the lever's own inert scenery object. **Update, 24th
   pass**: found the dispatch table (`mechanics.md` §23a, `$010000`-`$010075`, 59 word-relative
   entries) and confirmed LOCK's real opcode id is 18 by an exact address match, not a guess —
   UNLOCK's own address isn't one of the 59 entries, still open (§23b). Dumped resource types 6/8/9
   live (§23c): type 6 (objects) is fully populated, 1000/1000. Then the actual headline result:
   **the lever is object id 144** in that exact table (§23d), triple-confirmed — the id-resolve path
   lands on `$06fa0e`, the lever's own sprite-array `+10` field points to that same address, and its
   `+15`/`+24` bytes read exactly as the 22nd pass's §21b originally found. This is the first time
   this spike has tied the LOCK/UNLOCK mechanism to the lever by a confirmed numeric id and opcode,
   not just "a mechanism that writes the right bit somewhere." What's still missing is purely "who
   calls it" — no script byte sequence invoking opcode 18 with operand 144 has been found, and the
   interpreter's own top-level "read a script opcode byte, dispatch" entry point wasn't located this
   pass either (§23e has the concrete next steps: find that caller, then `callcap` the opcode-18/
   id-144 path directly and diff the lever's `+15` byte — cheaper than any further static search).
   **Update, 25th pass**: item (1), finding the caller, is now a broad negative rather than an
   unfound one — four independent static techniques (absolute-literal scan, PC-relative-`lea` scan,
   opcode-read-pattern scan, and an 18-site whole-verb-block external-caller sweep) all found no
   static call site anywhere in the loaded image that reaches the byte-opcode dispatcher
   (`mechanics.md` §24a/§24b). Item (2) was done anyway, directly on LOCK's own already-known address
   rather than waiting on (1): `callcap $01049a` with `A1` pointing at a scratch buffer holding id
   144, from `room2_lever_boundary.snap`, flips the lever's `+15` byte from `$01` to `$05` (bit 2
   set) exactly as LOCK's own `bset` instruction would (`mechanics.md` §24c) — the first causal, not
   merely structural, confirmation in this whole spike that the mechanism works. Whether anything in
   this game state actually invokes it that way is still open, and now a stronger negative than
   before — see `mechanics.md` §24d for the one remaining lead (`$00fe84`'s still-undecoded jump
   table).
   **Update, 26th pass**: that lead is now closed too - `$00fe84`'s 29 handlers (`mechanics.md` §25)
   are all precondition gates or minor unrelated mutations, none reaching LOCK/UNLOCK or referencing
   the lever's own record or id 144 anywhere. Both concrete next steps standing after the 25th pass
   are now clean negatives, not unfound leads. The most coherent reading left (§25c): the code that
   calls LOCK with id 144 for real may not be loaded into RAM at all in any snapshot this spike has
   produced, since room 3's own script/init data (as opposed to its graphics, confirmed resident by
   the 17th pass's palette-table find) has never been shown to load. The concrete next step, if this
   spike is picked up again, is broader than the lever itself: what would register a freshly-loaded
   room during ordinary play, and why has it never fired even at CAVERN's own second door (§13)?
   Once room 3 (or any room with a creature) is located/
   reached, snapshot there and differential-test `EntityScriptDispatch`/its
   opcode handlers with `callcap`, following the PowerMonger FSM methodology (`tools/pm_fsm_diff.py`'s
   `Harness`/`State`/`run_corpus`, game-agnostic; write a Cadaver-specific reconstruction module).
   Action 101's script (pointer `$16f07`) remains a usable second seed regardless, for the interact/UI
   side of the interpreter.
   **Update, 27th pass**: closed the whole lever-caller thread as a documented negative
   (`mechanics.md` §26) — not reopened, the reading above stands as the final word on "who calls
   LOCK with id 144." Also consolidated the room/object/portal/resource-table facts scattered across
   §§3/4/10/13/15/23 into one schema-style reference (`mechanics.md` §27).
   **Update, 28th pass**: tested the flag-poll hypothesis live for the first time — held object
   144's own `+15` byte set (a real memory write, not `callcap`, which reverts after reporting)
   across 5,000,000 steps from `room2_lever_boundary.snap` — and nothing reacted: `RoomLoadQueuedFlag`,
   `DoorFacingOrBlockedFlag`, and TUNNEL's whole live portal table all stayed byte-identical
   (`mechanics.md` §28a). Also re-ran both of §25c's own remaining fallbacks and found them already
   closed by earlier passes: `find_field_writers.py` filtered to literal writes of `2142(A5)=2` finds
   exactly one site, already named and correctly read as a display-register write by the 18th pass's
   own §18c, not a room-load flag (§28b); and the "already resident" branch (`$69da`), previously only
   characterized from register behavior, turns out on full disassembly to be the game's own main-loop
   re-entry point (confirmed: `room2_lever_boundary.snap`'s own resume PC sits inside it) with no
   decompress/copy step hiding in it (§28c). **This pass's own conclusion reframes the whole thread**:
   combined with the 17th pass's own user-supplied ground truth that pulling the lever really does
   open the door in the real game, and the 22nd pass's double negative that genuine touch is
   unreachable by ordinary movement in the first place, the balance of evidence now points toward
   LOCK(144) being the wrong mechanism entirely, not a real-but-unreached one — a hypothesis this
   spike backed into via the 23rd pass's opcode-ID match, not evidence the door's actual trigger uses
   it. See `mechanics.md` §28d for the concrete reframe and what the next pass should try instead of
   more LOCK-specific searching.
8. `tools/snap_render.py` (**promoted to the repo, 11th pass** — was scratchpad-only twice in a row,
   10th and 11th pass, before this) renders a `.snap`'s live screen straight to PNG via
   `gfxview.load_video_regs`, immune to the `ScreenBufferA`/`B` swap trap. `decode_span.py`/
   `decode_grid.py` (still scratchpad-only, render an arbitrary RAM span at a chosen palette/stride)
   remain candidates for a future promotion if a third pass needs them.
9. Player descriptor struct (slot 0, `$038338`, 70 bytes) dumped in full this pass (8th) but not yet
   interpreted beyond the already-known offsets (`+20`/`+23` phase, `+42` state, `+50`/`+51`/`+52`
   dims/pointer). The remaining ~50 bytes (notably a plausible world-position pair around `+8`/`+16`-
   `+19`, not screen pixels — no value in 0-320/0-199 range stood out except one coincidental byte)
   are unmapped; worth a targeted diff against the 11th pass's `sub.w D6,D0`/`sub.w D7,D1` values
   (single-step through `$006e50`'s loop with `callcap` or dense bisection) rather than guessing
   field semantics from one static dump.
10. ~~Open the TUNNEL lever~~ — **CLOSED, dead end (13th-16th passes), boundary of this spike.** Found
    its proximity hotspot (13th, `room2_lever_boundary.snap`, named "LEVER", own icon pair); no tested
    input opens the door (13th); explained by the 15th pass (`mechanics.md` §10-11): TUNNEL's live
    portal table has exactly 2 entries and neither is the lever's door (one is the already-working
    CAVERN exit, the other a sound/event cue with no room-transition semantics), and the entire
    fire-driven pipeline (`$00afb2`→...→`$00b1a2`/`$00ddb6`) never writes to it under any tested
    input. The 15th pass's one remaining lead — the icon panel's bracket/key icon pair hinting at a
    mouse-driven inventory-item click — is now also closed by the **16th pass** (`mechanics.md` §12):
    the icon-panel draw (`$00bef0`/`$00bf72`) takes its icon argument from the player's own
    movement-animation-frame byte, not any UI-selection state, so there is no icon-cycling input to
    find; and a cold-boot `ATARI_TRACE_IKBD` trace plus a live check at `room2_lever_boundary.snap`
    both confirm the game never sends the IKBD `$07` command that would make mouse clicks report at
    all. Keyboard interact, joystick movement, fire, Space, and now mouse clicks are all exhausted.
    **This is the spike's confirmed boundary for the lever's door** — no further input-guessing
    planned; see item 7 for the active next step.
- **17th pass — found and live-triggered a genuinely new CAVERN door, wrongly concluded from it that
  the game's connectivity was fully closed, then retracted that same pass on direct outside evidence.**
  Dumped **CAVERN's own portal table for the first time** (`mechanics.md` §13): 2 entries, entry 0 the
  known shared CAVERN↔TUNNEL door descriptor, **entry 1 a new descriptor (`$6d532`) with a real,
  positive target room id (`$49`=73)** — the first non-special-case target seen anywhere in this
  spike. Mapped all 22 CAVERN prop bboxes to find a walkable lane around the chest that blocked the
  11th pass's Right-hold, and live-triggered the match (`PendingRoomTargetWord_A5Plus1184` flipped
  from its idle `$ffff` to the entry's own `$3b`) — but the transition stalls at the "already
  resident" branch (`RoomLoadQueuedFlag_A5Plus2142` never sets to `2`), unchanged across 36.5M total
  steps of real per-VBL gameplay (confirmed the CPU wasn't hung — the VBL handler and its `$568e`
  tick counter keep cycling normally throughout; a `cmp.l $568e.l,D0`/`beq` spin at `$011360` that
  looked alarming turned out to be an ordinary once-per-frame "wait for vsync" primitive, not a stuck
  disk read). **From this, the pass wrongly concluded the whole game was just these two rooms with no
  creature anywhere** — the user, who has actually played this exact one-disk file, immediately
  corrected this: TUNNEL's lever really does open a door to a room 3 with a "spiky floater" enemy
  (confirmed against the game's own published walkthrough), and later rooms have maggots and worse.
  The error was scope, not the CAVERN-door finding itself: "both portal tables are fully enumerated"
  only covers what those two tables reference *right now*, not whatever the lever changes, and not
  whatever's sitting in RAM unreferenced by either. A follow-up `gfxview.py --contact` scan (prompted
  by a direct question about whether other rooms' tile/sprite data is even resident) found **9
  distinct palette tables** (up from the 2 this spike had accounted for) and confirmed a **104KB span
  (`$51000`-`$6b000`)** this spike had only ever sampled 2-3 pointers out of — real evidence more
  rooms' assets are already loaded in this one-disk image, matching its own "self-contained, no swap
  needed" milestone note. A systematic sweep of all 12 real keyboard action ids plus every
  direction/fire combo, done *at the lever specifically*, still produced zero portal-table change —
  so the lever's mechanism, whatever it is, isn't a bare keypress written straight to TUNNEL's portal
  table the way this pass was checking for. **Concrete next step, corrected**: find the master
  room/resource table that `$011256` (`RoomIdLookup_ByD2_LinearScan`) and its `$c628`/`$c52c` helpers
  walk — it resolved CAVERN's own east-door target id `$49` to something (not a lookup failure),
  meaning that id names a real entry in whatever table `$c628` scans. Locating that table directly
  would enumerate every room's descriptor without more input-guessing. Full writeup (including the
  retraction) in `mechanics.md` §13. `cavern_east_door_matched.snap` remains a valid resume point.
  **Same-pass follow-up (`mechanics.md` §14)**: found and fully traced the resource table — 64 slots
  reserved for rooms, **every single one still empty**, confirmed via `callcap`-testing `$011256`
  with three different target ids (all miss). Decoded the room-record format from CAVERN/TUNNEL's two
  known-good records (7-slot door-id list + floor-clamp bytes, matching live globals exactly) and
  directly refuted the standing "lever rewrites the descriptor in place" hypothesis (checked the real
  descriptor bytes, not just the live table, across all 18 previously-tried inputs — zero change).
  Also found the player sits almost exactly adjacent to TUNNEL's one non-player sprite (off by 1 unit)
  and is physically blocked from a true collision-overlap with it, and disassembled `TimerQueueService`
  fully — it's a sound-queue producer, not a script-trigger consumer, retracting the 14th pass's own
  "opcode `$9` triggers scripts" speculation. **The lever's real trigger is still unsolved** after this
  much more thorough sweep; the next concrete lead is finding what writes into the empty resource
  table (untried), not more input-guessing (now genuinely exhausted at both the live-table and
  descriptor level).
- **18th pass — found the type-8 index table's only writer in the whole loaded image: the
  save-game restore deserializer, gated behind a boot-menu branch never taken this spike.** Per the
  17th pass's own priority-1 next step, static-only (`mechanics.md` §15). A literal-address sweep
  for `$4c536`-`$4c636` (the same technique that found `$568e`/`88(A5)`) came back with zero hits —
  a real negative: unlike those targets, the table is only ever reached through a pointer loaded
  from the resource-table row, never as a literal operand, so that technique structurally cannot
  find this writer. Switched to a whole-image BSR/JSR caller sweep instead (new
  `scratchpad/cadaver18/find_callers_ram.py`), fully disassembling all three consumer primitives
  (`$c52c` row-resolve, `$c628`/`$c660` forward/backward populated-slot scan) and the table
  allocator/clearer (`$c696`/`$c6d0`) plus all 14 of their real call sites in the whole image —
  every one is read-only (enumerate/ID-match/iterate), none write a new entry. Separately found
  `$00b1e0`, a level-asset bulk loader that reloads resource types 2-7 from an in-memory stream on
  every load — **type 8 (rooms) is structurally excluded from it**, and `$00b1e0` itself has zero
  callers anywhere in the loaded image (dead code this playthrough). The actual writer:
  **`$00c9ee`**, a save-buffer deserializer, called with `D0=8` (`$00b962`) from the boot-time
  restore-game menu handler, gated on a `"CAD "` magic-header match at `$00b8fc`/`$00b906` — the
  exact mirror of a `$00c9c2`-based in-game SAVE routine that writes the same header. **This is the
  only place in the whole image that ever writes a real entry into the type-8 table** — and this
  entire spike's boot path has always taken "ESC: start fresh" (never "place a disk"/restore), so
  it has never run. Caveat stated plainly rather than overclaimed: this explains *why* the table has
  always been observed empty, but a restore-deserializer can't be the mechanism that populates a
  room's entry for the *first* time within one playthrough — either the table is orthogonal to the
  lever entirely (the real per-room-discovery path, if any, still hides in `$defa`'s undecoded
  body), or type 8 only ever gets populated via an actual save/restore round-trip. Concrete
  untried next step: trigger a real in-game SAVE, reboot, choose restore instead of ESC, and check
  live whether type 8 picks up a non-zero slot — settles which of the two readings is right.
  Secondary check (`mechanics.md` §16): CAVERN's axe/pick prop (sprite-array slot 4) is still an
  untouched static prop (state `5`) in every existing CAVERN snapshot — never picked up this whole
  spike, still untried live.
