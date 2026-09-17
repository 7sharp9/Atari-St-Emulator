# Cadaver — entity/action-script bytecode interpreter (14th pass)

Grounded in a full linear disassembly of `EntityScriptDispatch` (`$15c70`-`$16056`) and its helper
routines against `room2_lever_boundary.snap`. Static analysis only — no live creature has been found
in either room explored so far (CAVERN's 22-entry sprite array, TUNNEL's 2-entry one; both all
static props, per `graphics.md` §3), so this is the dispatcher and opcode set read directly off the
code, not yet exercised with `callcap` against a real monster. **Key finding up front**: this is
**not a separate, still-unused "monster AI" system waiting for a creature to appear — it is the same
interpreter that already runs the player's own interact/crouch action** (the 3-slot
`ActionScriptPointerTable`/`$162d0`/`$16306`/`$1633c` system fully characterized in the 5th-9th
passes). `EntityScriptDispatch` *is* what executes an installed action script every VBL; the 5th-9th
passes only ever watched its *inputs and outputs* (slot control blocks, `ActiveEntitySlotBitmask`),
never the interpreter itself. So whenever a real creature turns up, this opcode table already
applies — no new interpreter reversing needed, only new data (which script pointers a creature's own
`ActionScriptPointerTable` entries resolve to).

## 1. What it iterates: the 3 action slots, not the sprite-object array

`$15c70` initializes `A6 = EntityTable_Base` ($16380, a small header/output block — **not** the
22-entry sprite-object array `graphics.md` describes, a same-numbered but different structure) and
`A4 = ActionSlot0_ControlBlock` ($162d0). It then loops exactly **3 times** (`cmpi.w #$3,12(A6)`),
advancing `A4` by **54 bytes** each iteration — landing on `$162d0`, `$16306`=`$162d0+54`... actually
the confirmed slot bases (`$162d0`/`$16306`/`$1633c`, 5th pass) are 54 bytes apart, matching this
loop's own stride exactly. **This confirms the entity-script interpreter processes the same 3
control-slot structs the keyboard/`$15bf4` install path writes to, once per VBL, regardless of
whether a slot has a real script installed** (an idle/null slot just runs the shared no-op script at
`ActionScriptPointerTable[0]`, per the 9th pass's own finding that entry 0 is a true null pointer,
guarded by a `beq` at `$15c9a`).

Per slot, in order:
1. If the slot's countdown field (`+8`) is nonzero, skip straight to advancing the shared output byte
   (§4) — the slot is "resting" between ticks and doesn't re-run its script this VBL.
2. Otherwise (countdown expired): reload the script cursor from the slot's persisted pointer
   (`+4`); if null, skip to the output stage. Else read one byte from the script stream and dispatch:
   **byte `< $80`** is a literal frame/pose value (§3); **byte `>= $80`** indexes a 17-entry jump
   table (§2) of dedicated opcode handlers.
3. Most opcode handlers end by branching back to `$15ca0` (re-enter the byte-dispatch loop
   immediately — i.e. **most opcodes execute in the same tick with no yield**, so a script can chain
   several instructions before the frame it actually displays); a few (the loop/duration/frame path)
   fall through to §3/§4 instead, which is what actually advances the script cursor forward for next
   time and ends the tick.

## 2. Opcode table (`$80`-`$90`, all 17 real jump-table entries — confirmed exhaustive: entries `$91`
   and above decode as garbage/code bytes, not valid pointers, so the table is exactly 17 wide,
   ending where the handler bodies themselves begin at `$15d22`)

| Op | Addr | What it does | Reading |
|---|---|---|---|
| `$80` | `$15f38` | `field+25 = *script++` | Set a per-entity "frame-group" byte, later combined with `field+50` (§3) to pick the displayed frame |
| `$81` | `$15f40` | `field+24 = (*script++) << slotIndex` | Set this slot's bit-lane of a shared per-tick flag byte (own slot's contribution shifted into its own bit position; combined for all 3 slots by `EntityFrameFlagsCombine`, `$16042`, into `25(A6)`) |
| `$82` | `$15f50` | `field+4 = field+0` | **Restart**: rewind the live script cursor back to the slot's original installed pointer (loops the whole script) |
| `$83` | `$15f5a` | `field+10 = (*script++) * TickScale(14(A6))` | Set the post-tick countdown duration, in scaled ticks |
| `$84` | `$15d22` | `field+4 = A2; field+8 = field+10` | **Yield/end-of-tick**: commit the current read position as the resume point and reload the countdown from `field+10` — the normal way a script suspends until its next scheduled tick (also the natural fallthrough after a literal frame byte, §3) |
| `$85` | `$15f8a` | `TickScale(14(A6)) = 0xBB8 / ((*script++) * 4)` | Set the shared tick-scale divisor (`0xBB8` = 3000 = 50 Hz × 60 — reads as a BPM-style tempo-to-VBL-ticks conversion, plausibly synced to the PSG flush in §5) |
| `$86` | `$15f6a` | `field+10 = Σ (*script++) * TickScale`, for `N+1` literals (`N` read first) | Compound/summed duration — same effect as `$83` but built from several literal terms in one instruction |
| `$87` | `$15fb0` | clears `field+51` bits 0-1; copies a 12-byte record from table `$16fe5[byte*8]` into `field+34..45`; clears `field+26/27/30/31/32/50/14..15` | **Load preset**: select behavior/animation parameter block `byte` from a shared table into this entity's own working fields — the closest thing to a genuine "pick a behavior" instruction in this set |
| `$88` | `$15ff6` | peeks byte, `global $1637d = byte & $1f`; calls the ring-rotate helper `$16090`; re-reads and consumes the same byte; if its sign bit is set, ends the entity's turn, else falls into the literal-frame path (§3) reusing the byte | Sets a shared 5-bit global mode/cue value, with the byte's own top bit choosing whether to also treat it as a frame index this same tick |
| `$89` | `$16010` | clears bit 2 of `$1637c`; copies a 6-byte record (indexed by `*script++`) from table `$1729d` into the shared ring `$16372+4`; clears `$16372` and `$1637e` | Load a *global* (not per-entity) secondary table entry — same shape as `$87` but scoped to the shared scene-state globals rather than one entity |
| `$8a` | `$15fa0` | `field+51 |= byte; $1637c |= byte` | Set flag bits, both locally and in the shared global copy |
| `$8b` | `$15f18` | `bsr $15bf4` with `D1=currentSlot, D0=0`; reload cursor from `field+4`; `field+8 = 1` | **Force-idle**: re-installs action id `0` (the confirmed null/no-op action, 9th pass) onto this slot via the exact same install path the keyboard dispatch uses — an explicit "abandon this script, go idle next tick" instruction |
| `$8c` | `$15ef8` | `field+16 = ActionScriptPointerTable[*script++]` | **Stage** an action id's script pointer (doesn't jump yet) |
| `$8d` | `$15f10` | `A2 = field+16` (cursor jumps here) | **Call**: jump execution into the pointer `$8c` staged — the `$8c`/`$8d` pair together is the closest thing to a subroutine-call construct in this bytecode |
| `$8e` | `$15ee4` | `byte = *script++`; if `0`: `field+52 = 0`, else `field+52 += byte` | Reset-or-accumulate a per-entity counter (`field+52` here is a *different* struct from the sprite-object array's own `+52` bitmap pointer in `graphics.md` — same offset number, unrelated field, on a different struct; noted to avoid confusion) |
| `$8f` | `$15eb6` | `byte = *script++`; if `0`, skip (no-op); else `field+53 = byte; field+20 = A2` | **Loop-start**: mark the current cursor as a loop body's entry point and set an iteration count |
| `$90` | `$15ec8` | if `field+20 == 0`, skip; else `A2 = field+20`; `field+53 -= 1`; if nonzero, loop back (re-enter the marked body); else clear `field+20` and fall through | **Loop-test**: the `$8f`/`$90` pair is a bounded-repeat (`for`) loop construct — mark-and-count, then decrement-and-branch |

## 3. Literal bytes (`< $80`) — the frame/pose value, not a jump opcode

`field+52` (accumulated by `$8e`) is added to the literal byte, masked to 12 bits, doubled, and used
to index a 4096-entry-ish word table at `$160ac` (`EntityFrameFlagsCombine`'s neighbour,
`EntityFieldCopy_2629_3435` in `cadaver.sym` is a *different*, unrelated helper — this table itself
isn't separately named yet); the low byte and high byte of the looked-up word are written
consecutively to a small per-call output cursor (`38(A6)`, advanced 2 bytes per slot) — i.e. **each
of the 3 slots contributes one 16-bit "compound frame code" per tick to a 3-entry-wide output
array**, computed from `(literalFrame + accumulator) & $FFF`, then the normal `$84`-style yield
(commit cursor, reload countdown) runs. This output array's consumer (presumably whatever decides
what to actually draw/play for each active slot) hasn't been traced this pass — a concrete next step
if a differential test becomes worthwhile once a live creature exists.

## 4. Shared helper subroutines (not opcodes themselves)

- **`EntityFrameFlagsCombine`** (`$16042`): `AND`s/`OR`s a 3-entry bit table (indexed by the current
  slot number, `12(A6)`) into shared byte `25(A6)` — accumulates which of the 3 slots set their
  `$81`-flag this tick into one combined byte, called once per slot.
- **`$1605c`/`$16076`** (unnamed): each copies two entity fields into two others (`44→30`, `45→31`,
  `36→32`, `37→33` / `42→26`, `43→27`, `34→28`, `35→29`) — a snapshot/restore pair for two 4-byte
  parameter groups, called conditionally from the per-slot advance logic (§1) when specific flag
  bits (`field+51` bit 0/1) are set. Reads as "swap in an alternate parameter set for one tick" —
  not chased further; the exact trigger condition and what the two parameter groups represent
  (an alternate pose/timing pair, most likely) is open.
- **`$16090`** (unnamed): rotates a small 4-byte ring buffer at `$16372` (`8,9,4,5 → 0,1,2,3`),
  called from opcode `$88`'s peek and from the per-slot advance path (§1, guarded by `field+10` bit
  2) — a shift-register-style history buffer, purpose not traced further.
- **`$15ea4`** (`cadaver.sym`'s `EntityScriptOp_07_SetBitAndAdvance` — **this name is misleading,
  corrected here**: it is not one of the 17 real opcode handlers, and it is not reached through the
  jump table at all). It's a small helper called **exactly 11 times in a row**, unconditionally,
  once per full `EntityScriptDispatch` call (after all 3 slots are processed, IPL raised to 7 first,
  `$15e5e`-`$15ea2`), each call writing one incrementing register-select byte (`D0 = 0..10`) to
  `$ff8800` (the PSG/YM2149 register-select port) and one byte from a per-dispatch table (`18(A6)`,
  advancing) to `$ff8802` (the PSG data port) — i.e. **this is a full flush of 11 sound-chip
  registers (tone/noise/mixer/volume — registers 0-10, not the envelope registers 11-13) once per
  entity-dispatch pass**, not an entity opcode. Register 7 (the PSG mixer register) gets one extra
  bit forced (`bset #6`) on the *source* table byte before the write. This ties the interpreter to
  real-time sound output directly — worth remembering if a later pass wants to reverse the sound
  driver, since this is where PSG registers actually get written, not `TimerQueueService`'s command
  queue (which only schedules callbacks, per the 2nd-pass finding).

## 5. What's not chased this pass

- The `$160ac` frame-lookup table's actual contents/meaning (what a "compound frame code" controls),
  and where the 3-entry output array (`38(A6)` onward) is read by anything else.
- `$16fe5`'s (opcode `$87`) and `$1729d`'s (opcode `$89`) actual preset contents — dumping and
  decoding either table is mechanical (`sprite_array_export.py`'s approach doesn't directly apply,
  since these are flat records, not sprite descriptors, but the method transfers) and would show
  what concrete presets/behaviors exist, without needing a live creature.
- Whether any creature, if one is ever found, is driven through this same 3-slot system (reusing a
  slot the player might also use) or has its own independent slot pool elsewhere — nothing in this
  pass's disassembly suggests more than 3 concurrent slots exist anywhere in the game, which would be
  a real design constraint worth confirming (e.g. can only 3 things — including the player — ever be
  "acting" at once?).
- A `callcap`/differential-test pass proper (per the PowerMonger methodology): now that the opcode
  table is decoded structurally, the concrete next step is writing a Python reconstruction of one
  slot's tick (mirroring `tools/pm_fsm_ref.py`'s shape) and diffing it against `callcap $15c70`
  output over a corpus of captured slot states, once there's a reason to (e.g. a creature script to
  verify, or doubt about one of the opcode readings above).

## 6. The object-verb bytecode interpreter (`$010000`-`$011256`) — a separate room/level-scripting
   system, distinct from §1-5's entity/action-script interpreter (23rd-26th passes)

Found via the embedded debug-string table (`mechanics.md` §22b), not via the same top-down
compositor trace that found §1-5's interpreter — this is a genuinely different mechanism, driving
room/level object state (locks, movement, chests, creatures) rather than a per-entity animation
tick. Full derivation: `mechanics.md` §22-25.

### 6a. Dispatch table and calling convention

Same idiom as §2's own jump table and `mechanics.md`'s `$00fe84`/`$011728`
(`add.w D0,D0; adda.w 0(A2,D0.w),A2; jmp (A2)`): a 59-entry word-relative offset table at
`$010000`-`$010075`, real handler code resuming exactly at `$010076` (`mechanics.md` §23a). Handlers
read their operand — typically a big-endian 16-bit object id — from a script-stream cursor in `A1`
via `(A1)+`. Most handlers resolve that id through a shared id-resolver, `$010738` → `$00c542`/
`$00c56e` (`mechanics.md` §22d), which reuses the *same* generic `(A5)+96` resource-type-descriptor
system §15b describes for rooms (type 8), but against **types 6 (objects) and 9 (creatures)** —
`tst.w D1; bpl` → type 6 for a positive id, a negative sentinel → type 9 with the id replaced by a
global, and `$ffff` → the current "self/current actor" slot (`348(A5)`) directly, bypassing the
resource system entirely.

### 6b. Opcode vocabulary (from the debug-string error table, `mechanics.md` §22b)

Only **LOCK**'s numeric id is confirmed by an exact address match (below); the rest of this list is
the full verb vocabulary the engine's own debug strings name, not yet each individually pinned to a
table entry:

LOCK, UNLOCK, MOVE, GOMOVE, STOPMOVE, GOANI, STOPANI, creature KILL, creature UNINVENT (uninvent),
creature WAKE, creature SLEEP, rucksack ADD, FLAG ops, chest UNLOCK, chest UNTRAP, chest CLEAR, a
potion op (DIRTY). (`GOACTI`/`STOPACTI` and a generic object MOVE also appear in the string table but
weren't individually chased.)

### 6c. LOCK and UNLOCK, disassembled exactly (`mechanics.md` §22c)

```
$01049a: bsr  $10738        ; resolve object by 16-bit id operand
$01049e: beq  $104b6        ; not found -> "LOCKING NON-EXISTANT OBJECT"
$0104a0: bset #2,15(A0)     ; LOCK: set bit 2 of the resolved object's +15 byte
$0104a6: rts

$0104a8: bsr  $10738        ; same resolve
$0104ac: beq  $104cc        ; not found -> "UNLOCKING NON-EXISTANT OBJECT"
$0104ae: bclr #2,15(A0)     ; UNLOCK: clear bit 2 of the same +15 byte
$0104b4: rts
```

`+15` bit 2 on the resolved type-6 record is the exact flag the live object array's own classification
test reads via its `+10` link (§4's "interactive/pickup" `AND` test in `mechanics.md`, and this file's
own struct-shape note in §1 that entity structs and sprite-array structs are numbered similarly but
distinct — this is a third, separate struct again, the type-6 resource record). **LOCK's real
dispatch-table id is 18** — `$010000`'s entry 18 resolves to exactly `$01049a`, an exact match on a
specific two-word instruction among ~3,400 possible values, not a coincidence (`mechanics.md` §23a).
**UNLOCK's own address is *not* one of the 59 table entries** — the "LOCK=18, UNLOCK=19" adjacency
guess is directly refuted (entry 19 lands on an unrelated `rts`); UNLOCK is reached some other way,
genuinely unresolved (`mechanics.md` §23b).

### 6d. Tied to a real object: the lever is id 144

Object id 144 resolves (type-6 index table → `$0006fa0e`) to the exact same address the live sprite-
array entry's own `+10` field points to for TUNNEL's lever, cross-confirmed three independent ways
(`mechanics.md` §23d). `callcap $01049a` with `A1` pointing at a scratch buffer holding id 144 flips
that record's `+15` byte from `$01` to `$05` (bit 2 set) exactly as LOCK's own `bset` predicts — a
causal, not just structural, proof that LOCK-on-144 does what every static reading inferred
(`mechanics.md` §24c). **What calls LOCK with id 144 during ordinary play is closed as a documented
negative — not resident in RAM in any snapshot this spike has taken** (`mechanics.md` §26); this
file's job is the mechanism, not the caller search, and that thread is not reopened here.

### 6e. Not chased

- Every opcode besides LOCK/UNLOCK (§6b's vocabulary) — none individually mapped to a table id.
- `$010076`'s own alternate entry point into the id-resolver (`mechanics.md` §24a) — a real routine,
  zero found callers.
- The verb interpreter's own top-level "read a room's init script, dispatch opcode bytes" entry
  point — not the reusable generic-jump-table stubs at `$011700`-`$01172e` (confirmed via
  `find_ram_callers.py`, `mechanics.md` §23d/§24b), and not a bridge through `$00fe84`
  (`mechanics.md` §25, a clean negative) — still unlocated.

## Files

| File | What |
|---|---|
| `ai.md` | this file |
