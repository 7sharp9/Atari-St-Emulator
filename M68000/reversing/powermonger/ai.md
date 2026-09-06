# PowerMonger ST — the entity / commander decision loop

Reverse-engineered from the live isometric battle view (70th pass), driven from
`scratchpad/pm68_isoview.snap` (first mission, "Between Pages 1-5", one player
island plus neutral villages). Every address is a RAM address in the relocated
game image (base `$1050`); disassembled from the snapshot RAM
(`scratchpad/pm70_iso.ram`, via `scratchpad/extract_ram.py`). Method: 25M-step
traced resume (`ATARI_TRACE_EVENTS`), `trace_cfg.py --blocks`, plus `watch` on
individual object-record fields to catch the writing PC.

## Evidence taxonomy (91st pass)

Claims in this file (and `strategy.md` / `economy.md` / `graphics.md` /
`port/SPEC.md`) carry one of four confidence levels. The load-bearing ones are
tagged inline as **[Proven]** / **[Corroborated]** / **[Observed]** /
**[Hypothesis]**; untagged prose is Corroborated-or-better.

- **Proven** — exhaustive binary/dataflow reasoning, or differential equivalence
  against the real 68000 over many states (the `detcheck`/Musashi standard).
  Very little here is Proven yet; the renderer's `$ef62`/`$e420` path is the
  closest (86th: 128/128 triangle inputs + every scanline's DDA span + dither
  phase byte-exact vs a live single-step).
- **Corroborated** — an independent static read (disassembly of the handler)
  **and** a dynamic check (a `watch` on the written field catching the PC, or a
  register probe at the handler, or a frame diff) agree. Most of the FSM,
  the record layout, the order pipeline, and the sprite frame formulas.
- **Observed** — true in the missions / traces actually run (mission 1
  "Between Pages 1-5", the `pm67`–`pm90` snapshots), not shown to hold in
  general. **Every strong negative below is at most Observed** unless it also
  carries a static-exhaustiveness argument: "no per-unit-type AI", "no research
  timer", "no passive town growth", "enemy AI dormant in mission 1", "invention
  = weapon grade, never advanced" were each checked by tracing a specific
  scenario for a bounded step budget, not by proving the absence of a code path.
- **Hypothesis** — a plausible reading from disassembly alone, not yet traced.

## What the loop actually is

PowerMonger has **no per-unit-type AI** *(Observed — mission-1 traces; the
dispatch through `$14bb4` is by mode opcode, not unit type, across every record
seen, but a type-keyed branch elsewhere has not been exhaustively ruled out)*. It runs one **per-entity behaviour
state machine**. Every man, boat, animal, projectile, spell effect and
"pending order" in the world is a 50-byte **object record** in the array at
`$51b66`. Each record carries a one-byte **mode opcode** at offset 31. Once per
**simulation tick** the iterator `$14b62` walks all 511 records and, for each
active one, `jmp`s through a 75-entry table at `$14bb4` to that mode's handler.
A handler integrates one tick of motion, tests the world, and usually rewrites
its own mode byte to advance the state machine. Mode transitions *are* the AI;
there is no separate planner.

The "commander AI" (whether the Red/Green/Blue lords attack, recruit, or build)
is a thin layer on top: it is expressed as **group-order records** in the table
at `$51538`, one per army, holding a state enum and a link to the group's lead
object record. The group-order state drives which mode the lead man is put into
(`$10` march-to-cell, `$28` besiege, `$1a` absorb reinforcements); the
individual men then follow their own state machines toward the goal.

### The simulation tick

`$14b62` runs once per pass through the sim-tick body `$13000` — see
`strategy.md` "Where it runs — the sim tick `$13000`, disassembled" for the full
call order and the 72nd-pass correction. In short: `$13000` **is** the tick;
`$14b62` (at `$130c2`) and the executor `$6a3a` (at `$130c8`) run on *every*
`$13000` call, not behind the `$57ff0`/`$57fee` gate (that gate is only the
present-rate divider — `$1870` / `$12ce0` / the two renderers).

Measured (72nd pass, 3M-instruction trace): the tick body runs **13× per 250
VBLs** — about once per 19 displayed frames, ≈ **2.6 Hz**. The tick is
compute-bound in this instruction-counted emulator (one full body ≈ 19 VBLs of
instructions; `$1870` only waits one VBL edge). The 70th-pass "97 in 25M / ~2.4
Hz" is consistent. `$4bb3e` (long) is the master tick counter, bumped at
`$013034`; its low word `$4bb40` is the wrapping animation-phase value the
iterator uses. `$14e4e` (population, written by the briefing OK click — see
`README.md`) non-zero is the "a game is running" gate at `$1303a`; `$57ff2`
non-zero (paused) skips the AI + accounting + renderers but **not** the
executor `$6a3a` or the entity iterator.

## The iterator — `$14b62`

```
$14b62  lea $51b66,A1                 ; object record array
$14b68  lea $47970,A2                 ; parallel spatial-grid array
$14b6e  adda.w #$32,A1                ; skip slot 0; first real record = $51b98
$14b72  tst.b 5(A1)                   ; active gate:
$14b76  beq $1622c                    ;   byte 5 == 0  -> inactive, skip to next
$14b7a  blt $1623c                    ;   byte 5 <  0  -> dying entity, death path
        ; -- byte 5 > 0: live entity --
$14b7e  move.w $4bb40,D0
$14b84  add.w  24(A1),D0              ; + this record's animation phase
$14b88  andi.w #$3ff,D0
$14b8c  cmp.w  34(A1),D0              ; == its anim-trigger threshold?
$14b90  bne    $14ba0
$14b92  btst   #4,7(A1)               ; and bit4 of the flags clear?
$14b98  bne    $14ba0
$14b9a  addi.b #$1,14(A1)             ;   -> advance the animation frame
$14ba0  movem.w 8(A1),D6/D7           ; D6 = worldX, D7 = worldY  (signed words)
$14ba6  moveq  #0,D0
$14ba8  move.b 31(A1),D0              ; D0 = mode opcode
$14bac  move.w 6(PC,D0.w),D0          ; D0 = word[$14bb4 + mode]
$14bb0  jmp    2(PC,D0.w)             ; jmp $14bb4 + that offset
```

The loop tail:

| epilogue | what it does |
|----------|--------------|
| `$1622c` | `lea 50(A1),A1 / cmpa.l #$57f66,A1 / bne $14b72` — next record; `rts` at `$57f66` |
| `$16228` | `bsr $163ea` (relink spatial buckets, write back position) then fall into `$1622c` |
| `$16202` | clamp D6 to `[0,$3fff]`, D7 to `[0,$1f40]`, then `$163ea` + next |
| `$161c4` | same clamp, then re-sample terrain (`$1648e`): if the new cell is impassable, **revert to mode `$00`** and skip the position write; else clear the "blocked" flag (bit 5 of byte 7) and relink |
| `$1623c` | dying-entity path: count down `18(A1)`; at 0 stamp `$4bb3e` into `20(A1)` and run the neighbour-notify scan `$16260` |

Active-record count in this settled first-mission view: **~50 of 511 slots**,
of which ~26 reach a handler each tick (the rest are `byte 5 == 0`).

## The object record (50 bytes, stride `$32`, array `$51b66`, slots 1..511)

Fields are **overloaded by entity category** — a marching soldier and a spell
effect reuse the same bytes for different things. This is the common layout:

| off | type | meaning |
|-----|------|---------|
| 0 | word | **next** in this cell's entity bucket (offset into `$51b66`, 0 = tail) |
| 2 | word | **prev** in the bucket |
| 5 | byte | **owner / strength**. 0 = slot free (skip). `>0` = live, value is the owning commander colour (1..4) or a small count. `<0` = dying, `18(A1)` counts down to removal |
| 6 | byte | **category**: `$00` man/troop, `$04`, `$0e` formation node, `$10`, `$18`, `$1e`, `$20`, `$3c`… (checked by the neighbour scans) |
| 7 | byte | **flags**: bit4 = freeze animation, bit5 = "blocked / needs repath", bit6/bit7 = render-cull + "can fight" |
| 8 | word | **worldX** (0..`$3fff`) |
| 10 | word | **worldY** (0..`$1f40`) |
| 12 | byte | signed **X step** this tick (velocity) |
| 13 | byte | signed **Y step** this tick |
| 14 | byte | animation frame counter |
| 16 | byte | **speed / step magnitude** (divisor in the steer routine `$164bc`) |
| 17 | byte | **heading** 0..15 (from `$14262`, feeds the sprite pick and `$12d56`) |
| 18 | word | **countdown timer** (`subq.w #1,18(A1) / bge|bgt|bne`) — the dwell in the current mode |
| 20 | long | **target position** (word 20 = X, word 22 = Y). Bytes 20/21 also reused as a packed cell {x:6, hi:$70/$80/$90} by the regroup modes |
| 24 | word | animation phase offset (added to `$4bb40`) |
| 28 | word | link to a **related** object record (group leader, or the boat being boarded) |
| 30 | byte | **previous mode** (saved before a transition; several handlers branch on it) |
| 31 | byte | **current mode opcode** — the state-machine dispatch key |
| 33 | byte | **order class** — `$0a` ("hold / defensive") is special-cased in ~6 handlers |
| 34 | word | byte offset into the **nation/settlement table `$4f916`** (18-byte records) |
| 36 | word | saved origin X, or a packed destination cell |
| 38 | word | saved origin Y |
| 40 | word | cursor into the **patrol-path table `$168ee`** (or the obstacle-sweep angle for mode `$48`) |
| 42 | word | **packed muster cell** {x = bits 0-5, y = bits 6-12}, *and* the group id: byte offset into the **group-order table `$51538`** |
| 44 | byte | pending message code (consumed + cleared by `$16260`) |
| 45 | byte | morale / food counter (drained by `$5c80`) |
| 46 | word | offset into `$4e514` (leader table), or a siege garrison count |
| 48 | word | link to the **target** object record (the entity being chased / attacked) |

### As a C struct

Every offset below is confirmed by disassembly of a handler that touches it.
The comment says which handler / routine pins it. `//` = decoded; `// ??` = seen
referenced but purpose not proven. The record is a tagged union on `category`
(byte 6): a man, a boat, a projectile and a "pending group order" all share the
50 bytes and reinterpret the tail.

```c
typedef struct pm_object {           // array $51b66, stride 50, slots 1..510
/* 0*/  u16  bucket_next;            // $163ea: next in this cell's $47970 chain (byte offset into $51b66, 0 = tail)
/* 2*/  u16  bucket_prev;            // $163ea / $16778: prev in chain
/* 4*/  u8   _pad4;                  // ?? (never read in the traced handlers)
/* 5*/  s8   owner;                  // $14b72: 0 = free slot, >0 = live (commander colour 1..4 / small count), <0 = dying
/* 6*/  u8   category;               // dispatch tag: $00 man, $02 tree/obstacle, $04, $0a loose, $0e army node,
                                     //   $10, $18, $1e, $20, $2c corpse-in-decay, $3c
/* 7*/  u8   flags;                  // bit4 = in-formation / stamped by lead ($d322,$14f08); bit5 = blocked-needs-repath;
                                     //   bit6 = can-fight ($56a6); bit7 = render-cull / don't-count ($d322)
/* 8*/  s16  world_x;                // 0..$3fff   (movem.w 8(A1),D6/D7 at the top of every handler)
/*10*/  s16  world_y;                // 0..$1f40
/*12*/  s8   step_x;                 // signed per-tick velocity, added to world_x by nearly every handler
/*13*/  s8   step_y;
/*14*/  u8   anim_wear;              // $14b9a: ++ once per animation cycle. Doubles as the $5c80 wear counter
                                     //   (survivability collapses once anim_wear-$3c > 0). Not reset by the handlers seen.
/*15*/  u8   _pad15;                 // ??
/*16*/  u8   speed;                  // $164bc divisor (step magnitude); 0 for a stationary entity
/*17*/  u8   heading;                // 0..15, from $14262; picks the sprite and feeds $12d56
/*18*/  s16  dwell;                  // mode dwell timer: subq #1 / bge|bgt|bne at the head of the timed modes
/*20*/  s16  target_x;               // movement goal. Also reused as {packed cell x:6, hi $70/$80/$90} by $56/$5c
/*22*/  s16  target_y;
/*24*/  u16  anim_phase;             // $14b84: added to $4bb40 before the animation-trigger compare
/*28*/  u16  link_related;           // group lead / boat being boarded / obstacle-avoid target ($14d7c,$1597a)
/*30*/  u8   prev_mode;              // saved before a transition; $14f08 branches on ==$2e, $15302 sets $32
/*31*/  u8   mode;                   // <<< the FSM dispatch key: jmp $14bb4 + word[$14bb4 + mode]
/*32*/  u8   anim_sub;               // $1623c / $16260: 0..3 rotating animation phase
/*33*/  u8   order_class;            // $0a = "hold / defensive" — special-cased in $14c92,$14d32,$14f08,...
/*34*/  u16  nation_off;             // byte offset into the nation/settlement table $4f916
/*36*/  u16  origin_x;               // $14e56: saved (x,y) at the start of a patrol; also a packed dest cell
/*38*/  u16  origin_y;
/*40*/  u16  path_cursor;            // $14e70: byte cursor into the patrol-path table $168ee.
                                     //   $158da ($48): the obstacle-sweep angle instead.
/*42*/  u16  group_off;              // byte offset into the group-order table $51538 (== the group id).
                                     //   Low 6 bits + next 7 bits also decode as a packed muster cell {x:6,y:7}.
/*44*/  u8   msg_code;               // pending "under attack" message, consumed + cleared by $16260 / $159a4
/*45*/  s8   morale;                 // combat HP in melee: $1533c drains it, <=0 -> $5590 (kill/rout). $5c80 creeps it up.
/*46*/  u16  garrison_or_leader;     // $15282: besiege garrison count; $5bd2: offset into $4e514 for the kill credit
/*48*/  u16  link_target;            // the entity being chased / attacked ($14f08 mode $10, $15302, $56a6)
} pm_object;                         // sizeof == 50
```

The projectile / effect reinterpretation of the same slot is in `## Combat`
below (`pm_effect`).

## Spatial primitives

The handlers share five routines. None of the movement math uses the isometric
projection — that is baked into the world-coordinate encoding (see
`graphics.md` `$163ea`).

### `$1648e` — terrain sample at (D6, D7)

```
A4 = $438ee
D5 = worldX >> 6
D0 = (worldY & $ff00) | (worldX>>6 & $ff), then >> 2      ; cell index
A4 += D0
tst.b 8257(A4)     ; the height/flag plane (graphics.md's +8257)
...
D0 = byte[A4]      ; terrain TYPE byte
rts               ; Z set  <=>  type == 0
```

Callers `beq` on **type 0** = water / off-map / impassable. Used both as a
"can I stand here" test after a move and, probed in a `dbeq` loop, as a
short-range "is the path ahead clear" test.

### `$164bc` — one step toward (D0, D1)

`dx = D0-D6`, `dy = D1-D7`; if either goes negative the target plane is already
crossed on that axis. Otherwise `ext.l` both, `divu 16(A1)` (the entity's speed)
to get a normalised per-tick increment, `divu` again for the minor axis, and
return the step. **`beq` on return = target reached** (the dominant axis
underflowed). This is the routine the 67th-pass DIVU overflow / divide-by-zero
fix unblocked; `16(A1)` can be 0 for a stationary entity.

### `$14262` — (dx, dy) → 16-direction heading

Octant fold + a shift table at `$14360`; returns 0..15 in D0. Written to
`17(A1)`; the sprite blit and `$12d56` read it.

### `$12d56` — rotate (D0, D1) by heading D2

Sin/cos tables at `$1400a` / `$1400a-128`, `muls`, fixed-point (`add.l / swap`).
Turns a heading index back into a unit velocity vector — used by the
obstacle-avoidance mode to swing the probe direction.

### `$163ea` — maintain the per-cell entity buckets

Projects the entity to a screen cell (`((worldY&$ff00)>>2) + worldX_lo`); if the
cell changed since last tick, unlink the record from its old bucket (words 0/2)
and relink at the head of the new one. The bucket heads live in the array at
**`$47970`**, indexed by a coarser `f(worldX_hi, worldY)` (`$16260`,
`$15c46`, `$15518` all recompute the same index). This is PowerMonger's
**broad-phase**: every "is there an enemy / village / boat near me" query is a
walk of one bucket chain, never a scan of all 511 records.

### `$16260` — neighbour-notify scan

From the dying-entity path and the "process interactions" step: walk this
entity's cell bucket, and for each neighbour whose category is `$02` / `$10` /
`$1e`, bump a message counter in the `$4e514` leader table (`$16376` /
`$159de`) so the UI can print "Lord Matthew's men are under attack", then
clear bytes 33/44 and rotate the 0..3 animation phase in byte 32.

## The behaviour modes

75 table entries (`$14bb4` + mode → handler). Grouped by function; the
"tick" column is how many times that handler entered in the 25M-step trace of
the settled first-mission view.

### Move / path

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$00` | `$14c92` | – | **idle**. If `33(A1)==$a` → become `$8c` (hold position). Else `$14caa`: set dwell 20, face a direction from `17(A1)` + flags, small fidget |
| `$02` | `$14cfa` | – | step by (12,13); sample terrain; on hitting an obstacle clear bit5 and drop to mode `$06` |
| `$04`/`$06` | `$14d32` | – | step + terrain test; if clear and `33!=$a` → mode `$00`; if blocked → `$14d6a` (repath) |
| `$08` | `$14d7c` | – | **walk toward the linked entity `28(A1)`**: read its heading `17`, `$12d56` to a vector, add its position offset `8/10`, `$164bc` line test, copy step from `12(A4)`, set dwell `$a`. On arrival → mode `$06` |
| `$0a` | `$14e1e` | – | dwell `18`; at 0 → mode `$08`, or mode `$10` if no linked entity |
| `$0c` | `$14e56` | 6 | save (D6,D7) → (36,38), load patrol path, → mode `$0e` |
| `$0e` | `$14e70` | **445** | **patrol / march along the spline `$168ee`**: cursor `40(A1)` walks {dx,dy} word pairs; segment end (word ≥ `$7d00`) ends the path; recompute step (12,13) and heading (17) each segment, dwell 8 |
| `$10` | `$14f08` | **180** | **advance to the target** `20/22` (or chase entity `48(A1)`, copying its live position). `$164bc` for the step; then probe up to D2 cells ahead along (12,13) with `$1648e` (`dbeq`). Path blocked → mode `$4a`. Target reached → `$15302` / `$14fdc` |
| `$12` | `$14ff8` | **774** | **halt / cool-down**: step, dwell `18`; at 0 → mode `$10` (resume advancing) |
| `$48` | `$158da` | 13 | **obstacle avoidance**: `12(A1)/13(A1)` from heading via `$12d56`; probe ahead (`dbeq` on `$1648e`); if blocked, add a growing ± sweep (`40(A1)` += 4, negate) to `17(A1)` and retry — turn by ever-wider angles until a lane opens |
| `$4a` | `$1597a` | 3 | set up mode `$48`: copy target from `28(A1)`, sweep = 8, clear low 2 bits of heading |

### Combat

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$28`/`$2a` | `$15282` | – | **besiege** the target record `46(A1)`: while its group state (`$51538`) is 3, decrement its garrison `46(A0)` each tick; at 0, decrement the settlement's troop count in `$4e514` and `jsr $1d70` (capture) |
| `$2c` | – (`$153b2`→) | – | fighting hold; mode `$36` counts down back to `$2c` |
| `$2e` | `$15302` | – | **reached the target** `48(A1)`: snap `(D6,D7)` onto it, set both mode bytes `$32`; if engageable (`mode(target) > $2c`, `prev_mode(target) >= $3c`) `jsr $56a6` |
| `$32` | `$1533c` | – | **melee**: face the target (`heading + $80`); if it isn't already in `$32`, `jsr $56a6`. Then **drain the target's `morale` (byte 45)** by `(min(msg_code,6) >> 1) + 1` per tick (1..4). At `morale <= 0` → `jsr $5590` (kill-or-rout). Target dead first → mode `$2c` for both |
| `$34`/`$36` | `$153b2`/`$153cc` | – | fight recoil / hold; `$36` counts `dwell` back down to `$2c` |
| — | `$56a6` | – | **engage**: if `flags.bit6` and the linked enemy `28(A3)` is within `$fff` (Manhattan-max) → `jsr $5778`; then set both mode bytes `$32`, link attacker into `48(A3)`, and pick the attacker's `garrison_or_leader` (`46`) either from `28(A1)` or the target's leader record |
| — | `$5778` | – | **contact bookkeeping, not a resolver** — see `strategy.md` "Combat". Marks an engaged garrison `flags = $11`, records the attacker for a support objective, else `$4bc8` (nation peace-break + player notify) |
| — | `$5590` | – | **kill-or-rout roll** (from mode `$32` when `morale <= 0`): `morale := 0`; `D0 := $30fe(group) = group.field60 - 2` (or `$57fec`-parity if the attacker isn't in a group). `D0==0` → **KILL** (`owner` negated, `category := $c` corpse, `dwell := $a0` 160-tick decay); `D0==2` or the parity fails → **ROUT** (`$3c08` restructures the unit's group, `prev_mode := $3c`, `category := 0`, unit survives scattered). `flags.bit5` set forces KILL |
| — | `$57f0` | – | **spawn a projectile** into the `$4bdf0` effect array (slot 0 is a header; 48 slots × 16 B from `$4be00`): copy position, `life := $14` (20 ticks), `type := D1` (weapon / invention tier), `shooter := A1-$51b66`, velocity toward the resolved target cell via `divu #$78`. Shooter's `dwell` set from the slot's reload byte |
| — | `$596a` | – | **projectile update loop** (every tick): `life--`; at 0, if `type == $12` the projectile does an **area hit** on whatever entity stands in its cell (stamp `category := $2`, `flags := $a`, `speed := 0` — i.e. disable/rout it) then lingers 4 more ticks; other types just unlink (`$16778`) and free the slot |

The effect slot reinterprets the first 16 bytes of an object-record-sized area
(array `$4bdf0`, but the loop iterates `$4be00`..`$4c110` = 48 usable slots of
16 B; slot 0 is a template holding the per-weapon `reload` byte at +15):

```c
typedef struct pm_effect {           // $4be00, stride 16, 48 slots
/* 0*/  u16  bucket_next;             // shares the $47970 chain machinery
/* 2*/  u16  bucket_prev;
/* 4*/  u8   _pad4[2];
/* 6*/  u8   type;                    // D1 at spawn: weapon / invention tier. $12 = area-effect on expiry
/* 7*/  u8   _pad7;
/* 8*/  s16  world_x;                 // copied from the shooter at spawn
/*10*/  s16  world_y;
/*12*/  u16  shooter_off;             // offset into $51b66 of the firing unit
/*14*/  s16  life;                    // $14 at spawn; --/tick in $596a; 0 -> impact; -4 = "area lingering"; <0 fade
/*15*/  u8   reload;                  // (template slot only) ticks written back into shooter->dwell
} pm_effect;
```

### Group orders (the "commander AI")

These read/write the **group-order table `$51538`** (indexed by `42(A1)`; word
0 = state enum, seen values 3 / 8 / `$c`; `24(A3)` links the group's lead
object record; `36(A3)` a running total).

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$18` | `$150b0` | 6 | → mode `$0c` (begin the patrol route). This is the state the neutral-village garrisons sit in (`prevmode $18` on every mode-`$0e` record) |
| `$1a` | `$150c0` | – | **absorb reinforcements**: move a fraction (`16 >> $30fe`) of the reserve pool `6(A5)` into the marching pool `14(A5)`, add to the group total `36(A3)`; if group state `!= $c` recompute (`$35f4`) |
| `$1c` | `$15122` | – | **detach a raiding party**: `46(A1) = 8(A5) >> shift`; → mode `$28` (siege), dwell `$32` |
| `$1e`/`$26` | `$15200` | – | if group state == `$c`, unpack `36(A1)` as a target cell → mode `$10` (march there), prevmode `$74` |
| `$52` | `$15a80` | 51 | read the nation's destination cell `12($4f916+34)` → target, mode `$10`; issue an order message via `$4e514+46` (`$159de`) |
| `$54` | `$15ad2` | 29 | walk the `$4e514` leader records selecting the text for a status message (speech generation, not movement) |
| `$56` | `$15b94` | **168** | **regroup at the muster cell**: unpack `42(A1)` → target (20/21/22), consult the per-cell control byte `$3f86c[42]` to choose sprite `$70`/`$90`, prevmode `$58`, mode → `$10` |
| `$58` | `$15bec` | 11 | arrived at muster — settle |
| `$5a` | `$15c46` | **119** | **proximity gate**: dwell; scan the cell bucket `$47970[42]` for a neighbour of category `$18` (flags `$10`) or `$20`; found → mode `$62`; timeout → mode `$62`, dwell `$64` |
| `$5c` | `$15d66` | **152** | move; `$15fa8` on-screen test; on arrival set up target from `$3f86c[42]` / `$4f916`, mode → `$60` |
| `$60` | `$15ddc` | 86 | move to (20,22); on `$164bc` arrival `addi.w #$4,6($4e514+idx)` (register the arriving detachment with the settlement), mode → `$62` |
| `$62` | `$15bfc` | 3 | group idle / wait for the next order |

### Static / upkeep / boats / effects

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$68` | `$16048` | **2559** | **in formation**: `jsr $5c80` (upkeep), zero velocity, next. The dominant mode — the men drawn in an army's marching column. Their position is written by the lead record, not by themselves |
| `$8a` | `$161b2` | 99 | **garrison**: `jsr $5c80` only. A settlement's stationed troop |
| `$8c` | `$14c48` | – | hold position: re-add the last step, re-test terrain, drop to `$10`/`$06` if pushed off |
| `$84` | `$15f96` | 30 | dwell → mode `$86` |
| `$86` | `$15e30` | 10 | (chain to `$88`) |
| `$14` | `$1501a` | – | **board / transfer**: copy `5(A3)` (strength) from the `$4f916+34` record into `5(A1)` unless its bit7 is set, mode `$2a`, dwell `$32` |
| `$16` | `$15042` | 6 | `jsr $16848`; if `$57fd0 == 0` save mode → 30, mode `$7c`, dwell `-99` |
| `$8a8a` write | `$16176` | – | **removal**: adjust the owning commander's troop count (`$5c2c` → `$4bc8` when the settlement's owner no longer matches), free the group slot (`$35f4`), `$5c80`, zero velocity, mode `$8a` |
| — | `$5c80` | 2600+ | **per-entity upkeep**: flags-indexed table + byte14 age + byte45 morale; `byte45 += ($57fec & 1)` (a food/desertion drain with a 1-bit random term); `jsr $5bd2` past a threshold |

Modes not listed (`$1f`…`$92` sparse entries, indices > `$94` alias into
following code and are never selected) were catalogued by address only.

The full table (`$14bb4`, `handler = $14bb4 + (s16)word[$14bb4 + mode]`) was
re-dumped this pass; every valid entry `$00`..`$94` resolves inside the handler
block `$14c48`..`$1620e`. Entries `$96`+ point back into the dispatch prologue
or into `$19434`/`$1acb4`/`$1b2b4` (unrelated code) and are dead — `mode` is
never written a value above `$92` by any handler.

## The entity FSM

The transitions below are exactly what the handlers write to `mode` (byte 31),
with the branch condition that selects each edge. Only the load-bearing modes
and their reachable neighbours are drawn; `$5c80` upkeep and the `$163ea`
relink happen on the epilogue of *every* state and are not edges.

```mermaid
stateDiagram-v2
    [*] --> S00 : slot spawned

    state "00 idle" as S00
    state "8C hold-position" as S8C
    state "0A pre-move dwell" as S0A
    state "08 walk-to-linked-entity" as S08
    state "06 step+repath" as S06
    state "02 step-until-blocked" as S02
    state "0C load-patrol" as S0C
    state "0E patrol / march spline" as S0E
    state "10 advance-to-target" as S10
    state "12 halt / cool-down" as S12
    state "48 obstacle-avoidance sweep" as S48
    state "4A set-up sweep" as S4A
    state "2E reached-target" as S2E
    state "32 melee" as S32
    state "2C fighting-hold" as S2C
    state "36 fight recoil" as S36
    state "28 besiege settlement" as S28
    state "68 in-formation (follower)" as S68
    state "8A garrison" as S8A
    state "18 group: begin route" as S18
    state "1A group: absorb reinforcements" as S1A
    state "1C group: detach raiding party" as S1C
    state "26 group: unpack dest -> march" as S26
    state "56 regroup: unpack muster cell" as S56
    state "58 regroup: settle" as S58
    state "5A regroup: proximity gate" as S5A
    state "5C regroup: move to settlement" as S5C
    state "60 regroup: register w/ settlement" as S60
    state "62 group idle" as S62
    state "92 -> free slot, mode 00" as S92
    state "$15302 reached (routine)" as S15302
    state "$1518a $4bc8 reconcile" as S18A
    state "$5590 kill / rout" as S5590
    state "$1d70 capture" as S1D70
    state "$3c08 restructure" as S3C08
    state "$35f4 free group slot" as S35F4

    S00 --> S8C : order_class == 0A
    S00 --> S0A : else (face + fidget, dwell 20)
    S8C --> S10 : pushed off terrain
    S8C --> S06 : pushed, blocked
    S0A --> S08 : dwell 0 && link_related != 0
    S0A --> S10 : dwell 0 && no link
    S08 --> S06 : arrived at linked entity
    S02 --> S06 : hit obstacle
    S06 --> S00 : path clear && order_class != 0A
    S06 --> S02 : path clear && order_class == 0A
    S06 --> S08 : blocked, dwell 0 (repath)
    S0C --> S0E : always (saves origin, loads path)
    S0E --> S0E : segment end word == $7D01 (loop)
    S0E --> S92 : segment end word == $7D02+n, n>0
    S0E --> S0E : dwell > 0 (integrate step)
    S10 --> S15302 : $164bc says target reached
    S10 --> S4A : terrain probe blocked ahead
    S10 --> S12 : arrived, order_class 0A / group not state 8
    S10 --> S18A : group state 8 && dwell <= $12 (hand to $1518a)
    S12 --> S10 : dwell expired
    S4A --> S48 : copies target, sweep = 8
    S48 --> S48 : still blocked -> widen sweep angle
    S48 --> S4A : sweep exhausted one way
    S48 --> S12 : gave up (D2 < 0)
    S2E --> S32 : snap to target; engageable -> $56a6
    S32 --> S32 : target still alive, morale > 0 (drain it)
    S32 --> S2C : target dead / not engageable
    S32 --> S5590 : target morale <= 0 (kill-or-rout roll)
    S2C --> S36 : (via $153b2)
    S36 --> S2C : recoil dwell 0
    S28 --> S1D70 : garrison count hits 0 -> capture
    S28 --> S3C08 : group left besiege state
    S18 --> S0C : always (40 := $50)
    S1A --> S26 : group state == $C, dwell $23
    S1A --> S35F4 : group state != $C (free slot)
    S1C --> S28 : always (garrison := reserve >> roll, dwell $32)
    S26 --> S10 : group state $C -> unpack origin as dest cell
    S56 --> S10 : always, prev_mode := $58, target := muster cell
    S58 --> S5A : dwell $A
    S5A --> S62 : neighbour of category $18/$20 found, or timeout
    S5C --> S60 : $164bc arrival at settlement
    S60 --> S62 : arrival; leader.field6 += 4
    S62 --> S62 : dwell > 0
    S68 --> S68 : always (upkeep only; position stamped by lead)
    S8A --> S8A : always (upkeep only)
```

`$92` (`$1615c`) frees the group slot (`$35f4`) and drops to mode `$0` — the
terminal patrol state. `$1518a` is `$4bc8` (contact reconcile) then epilogue.
`$5590`, `$1d70`, `$3c08`, `$35f4`, `$15302` are routines, not modes, but sit
on FSM edges and are listed in the symbol table.

## Load-bearing handlers — pseudocode

Faithful to the disassembly of `scratchpad/pm70_iso.ram`. `A1` = the current
object record; `D6/D7` = its `world_x/world_y` (loaded at `$14ba0`, written back
by the epilogue). "epilogue X" = `bra $161c4` (clamp + terrain-test + relink,
revert to mode `$0` if the new cell is impassable) or `bra $16202` (clamp +
relink, no terrain veto) or `bra $1622c` (straight to next record).

```c
// ---- $14c92  mode $00 : idle ----------------------------------------------
void h_idle(pm_object *A1) {
    if (A1->order_class == 0x0a) {                 // player "hold" order
        A1->mode = 0x8c;  A1->flags |= BIT5;
        goto epilogue_16202;
    }
    A1->mode  = 0x0a;                              // -> pre-move dwell
    A1->dwell = 0x14;
    int d;
    if (A1->flags & BIT6)                          // "can fight": face a fixed way
        d = A1->heading + (A1->target_x < 0 ? +7 : -7);
    else
        d = jsr_12c9a();                           // else a pseudo-random-ish heading
    A1->heading = d;
    D2 = d;  D1 = -(u8)A1->speed;  D0 = 0;
    jsr_12d56(&D0,&D1, D2);                        // heading -> velocity vector
    A1->step_x = D0;  A1->step_y = D1;
    goto epilogue_161c4;
}

// ---- $14e70  mode $0E : patrol / march along the spline $168ee -------------
void h_patrol(pm_object *A1) {
    D6 += (s8)A1->step_x;   D7 += (s8)A1->step_y;   // integrate one tick
    if (--A1->dwell != 0) goto epilogue_16202;      // still walking this segment

    s16 *path = (s16*)0x168ee;
    int c = A1->path_cursor;
    D6 += path[c/2 + 0] ... ;                       // (movem.w 0(A0,D2),D6/D7): snap to segment start
    D7 += ...;
    c += 4;
  next_seg:
    s16 sx = path[c/2], sy = path[c/2 + 1];         // (movem.w 0(A0,D2),D0/D1)
    if ((u16)sx >= 0x7d00) goto seg_terminator;
    A1->path_cursor = c;
    // step toward (origin + seg) from here, /8, and a heading:
    s16 dx = (A1->origin_x + sx - D6) >> 3;
    s16 dy = (A1->origin_y + sy - D7) >> 3;
    A1->step_x = dx;  A1->step_y = dy;
    A1->heading = jsr_14262(dx, -dy);
    A1->dwell = 8;
    goto epilogue_16202;
  seg_terminator:
    if (sx == 0x7d01) { c -= sy; goto next_seg; }   // loop the path
    if (sx >= 0x7d02) { A1->mode = sx - 0x7d02; goto epilogue_161c4; }  // jump to an explicit mode
    A1->mode = 0x92;                                // $7d00 : end -> free the group slot
    goto epilogue_161c4;
}

// ---- $14f08  mode $10 : advance to the target ----------------------------
void h_advance(pm_object *A1) {
    if (A1->prev_mode == 0x2e) {                    // chasing a live entity, not a fixed cell
        pm_object *e = &obj[A1->link_target];
        if (e->owner <= 0 || e->prev_mode == 0x3c) {// target gone / already a corpse
            A1->mode = A1->prev_mode = 0x2c;        // -> fighting-hold
            goto epilogue_161c4;
        }
        *(u32*)&A1->target_x = *(u32*)&e->world_x;  // track its live position
        if (jsr_164bc(A1, e->world_x, e->world_y) == REACHED) goto reached_$15302;
        A1->dwell = 3;                              // D2 = probe depth
        goto move_body;
    }
    if (jsr_164bc(A1, A1->target_x, A1->target_y) == REACHED) goto arrived_$14fdc;
  move_body:
    if (A1->order_class != 0x0a) {
        int probe = A1->dwell - 1;                  // look 2..3 cells ahead along (step_x,step_y)
        int x=D6,y=D7;
        do { x += A1->step_x; y += A1->step_y; } while (--probe >= 0 && terrain_ok($1648e,x,y));
        if (probe >= 0) { A1->mode = 0x4a; goto next_record; }   // blocked -> obstacle avoidance
    }
    // arrival bookkeeping when this lead man belongs to a live group order:
    if ((A1->flags & BIT4) && A1->group_off != 0
        && group[A1->group_off].exec_state == 8) {
        if (A1->dwell <= 0x12) { jsr_1518a(); return; }         // $4bc8 reconcile
        A1->dwell >>= 1;
    }
    A1->mode = 0x12;                                // -> halt / cool-down
    goto tail_of_$14ff8;
  arrived_$14fdc:
    A1->mode = A1->prev_mode;                       // resume the previous state
    D6 = A1->target_x;  D7 = A1->target_y;          // snap exactly onto it
    goto (A1->flags & BIT5 ? epilogue_16202 : epilogue_161c4);
}

// ---- $14ff8  mode $12 : halt / cool-down --------------------------------
void h_halt(pm_object *A1) {
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (--A1->dwell > 0) goto epilogue_161c4;
    A1->mode = 0x10;                                // resume advancing
    goto epilogue_161c4;
}

// ---- $150c0  mode $1A : group absorbs reinforcements ---------------------
void h_absorb(pm_object *A1) {
    (*(u16*)0x12a24)++;                             // a UI/stat counter
    group *g   = &group[A1->group_off];
    pm_object *lead = &obj[g->lead_off];
    int roll = jsr_30fe(A1);                        // = group.field60 - 2  (a shift amount)
    lead->reinf_march_14 += (0x10 >> roll);         // move a slice of the reserve...
    u16 slice = lead->reinf_reserve_6 >> roll;
    lead->reinf_reserve_6 -= slice;
    g->running_total_36  += slice;
    jsr_34f2();                                     // recompute derived group totals
    if (g->exec_state == 0x0c) { A1->mode = 0x26; A1->dwell = 0x23; }
    else jsr_35f4();                                // group order done -> free the slot
    goto epilogue_161c4;
}

// ---- $15122  mode $1C : group detaches a raiding party -------------------
void h_detach(pm_object *A1) {
    group *g   = &group[A1->group_off];
    pm_object *lead = &obj[g->lead_off];
    int roll = jsr_30fe(A1);
    A1->garrison_or_leader = lead->troops_8 >> roll; // size the raiding party
    jsr_34f2();
    A1->mode  = 0x28;                                // -> besiege
    A1->dwell = 0x32;
    goto epilogue_161c4;
}

// ---- $15264 / $15282  mode $28/$2A : besiege a settlement ---------------
void h_besiege(pm_object *A1) {                      // handler = $15282 for $2a
    if (A1->dwell == 0x32) {                         // one "assault pulse" per 50 ticks
        pm_object *garr = &obj[A1->garrison_or_leader];
        if (garr->owner > 0 && group[garr->group_off].exec_state == 3) {
            if (--garr->garrison_or_leader >= 0) {   // still defenders left
                nation *n   = &nation[A1->nation_off];
                leader *L   = &leader_by_off(n->leader_off);   // via $1b2a
                if (found) { L->troops_8 -= 1; jsr_1d70(A1); } // capture
            }
        }
    }
    if (--A1->dwell > 0) goto epilogue_161c4;
    jsr_3c08(&group[A1->group_off]);                 // pulse over -> restructure group
    goto epilogue_161c4;
}

// ---- $16048  mode $68 : formation follower -----------------------------
void h_formation(pm_object *A1) {
    jsr_5c80(A1);                                    // upkeep only
    A1->step_x = 0;  A1->heading = 0;                // never moves itself
    goto next_record;                               // position is stamped by the group lead
}

// ---- $161b2  mode $8A : garrison -------------------------------------
void h_garrison(pm_object *A1) { jsr_5c80(A1); goto next_record; }

// ---- $15b94  mode $56 : regroup -- unpack the muster cell ------------
void h_regroup_unpack(pm_object *A1) {
    if (--A1->dwell >= 0) goto epilogue_161c4;
    A1->target_x_lo = A1->group_off & 0x3f;          // {x:6} of the packed muster cell
    A1->b21 = 0x70;                                  // sprite tag "friendly muster"
    cellctrl *cc = &cellctrl[A1->group_off];         // per-cell control byte, $3f86c
    if (cc->byte1 || cc->byte65) A1->b21 = 0x90;     // "contested muster"
    A1->target_y = ((A1->group_off & 0x1fc0) << 2) + 0x80;   // {y:7} -> world_y centre
    A1->prev_mode = 0x58;
    A1->mode      = 0x10;                            // march to the muster cell
    goto epilogue_161c4;
}

// ---- $15c46  mode $5A : regroup -- proximity gate -------------------
void h_regroup_gate(pm_object *A1) {
    if (--A1->dwell >= 0) goto next_record;
    for (pm_object *p = bucket_head($47970, A1->group_off); p; p = &obj[p->bucket_next]) {
        if (p->category == 0x18 && (p->flags == 0x10)) goto found;
        if (p->category == 0x20) goto found;
    }
    A1->dwell = 0x64;  A1->mode = 0x62;  goto next_record;   // timeout -> idle
  found:
    p->category = 0x20;                              // claim it
    A1->flags |= BIT5;
    // then a $12c9a-driven random nudge of (D6,D7) by $20, $15fa8 on-screen test ...
    ...
}

// ---- $15d66 / $15ddc  mode $5C -> $60 : move to & register with a settlement
void h_regroup_move(pm_object *A1) {                 // $15d66
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (on_screen_test($15fa8) == 0 && --A1->dwell >= 0) goto epilogue_16202;
    A1->mode = 0x60;
    // re-derive target from the packed cell + $3f86c control byte (same as $56):
    A1->target_x_lo = A1->group_off & 0x3f;
    A1->b21 = (cellctrl[A1->group_off].byte1 || cellctrl[...].byte65) ? 0x90 : 0x70;
    A1->target_y = ((A1->group_off & 0x1fc0) << 2) + 0x80;
    jsr_164bc(A1, A1->target_x, A1->target_y);
    goto epilogue_16202;
}
void h_regroup_register(pm_object *A1) {             // $15ddc  mode $60
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (--A1->dwell >= 0) goto epilogue_16202;
    if (jsr_164bc(A1, A1->target_x, A1->target_y) != REACHED) goto epilogue_16202;
    nation *n = &nation[A1->nation_off];
    leader[n->leader_off].field6 += 4;               // "a detachment has arrived"
    A1->mode = 0x62;
    D6 = A1->target_x;  D7 = A1->target_y;
    goto epilogue_16202;
}
```

## Where target selection happens, and what it reads

There is **no global "pick the best target" pass**. Targeting is local and
event-driven, in three places:

1. **Group order → destination cell.** When a lord decides to move an army, the
   group-order record `$51538` is set to state `$c` and the destination is
   written as a packed cell into either the lead man's `36(A1)` (mode `$1e`) or
   the nation record `12($4f916+34)` (mode `$52`). The men unpack that cell and
   march (`$56` → `$10`). The decision itself (which cell) is made by the
   higher-level strategy code reached from `$13040`'s `jsr $6522` / `$d322` /
   `$3e06` — **not decoded this pass**; those run every tick and own the
   `$51538` / `$4f916` tables.

2. **Contact → engage.** While marching, mode `$10` probes `$1648e` a few cells
   ahead; the regroup modes (`$5a`, `$5c`) and the notify scan (`$16260`) walk
   the current cell's `$47970` bucket. A neighbour of an enemy category within
   range flips the record to mode `$32` and calls `$56a6`, which re-checks the
   linked enemy `28(A3)` is within `$fff` world units before `$5778` resolves a
   round. So "attack" is decided by **bucket proximity at ~2.4 Hz**, using the
   Manhattan-max distance, not by any threat evaluation.

3. **Adjacent settlement → capture.** Mode `$28`/`$2a` sits on a village record
   (`46(A1)`), counts its garrison `46(A0)` down while the group state stays 3,
   and on 0 decrements the settlement's troop count in `$4e514` and calls the
   capture routine `$1d70`. Ownership is reconciled by `$5c2c`: it compares the
   settlement's stored owner (`$4e514[14($4f916+34)]`) against the entity's
   `5(A1)` and calls `$4bc8` on a mismatch.

Inputs read by the loop, in order of how often:

| table | base | stride | holds |
|-------|------|--------|-------|
| object records | `$51b66` | 50 | the entities (above) |
| spatial buckets | `$47970` | 2 | per-cell linked-list heads (broad phase) |
| terrain | `$438ee` | — | type plane at `0`, height/flag plane at `+8257` (dual 8 KB planes) |
| nation / settlement | `$4f916` | 18 | `+5` owner colour, `+8` linked object, `+12` destination cell, `+14` leader index |
| group orders | `$51538` | ~`$13c` | `+0` state enum, `+24` lead object link, `+36` running total |
| per-cell control | `$3f86c` | 1 | influence / ownership byte per map cell |
| leader / message | `$4e514` | 32 | per-lord troop counts + message counters + name index |
| patrol paths | `$168ee` | var | {dx,dy} word lists, terminated by a word ≥ `$7d00` |

## What each entity decides per tick (the answer)

For a **man** (category `$00`): integrate one step of velocity `(12,13)`;
check the destination cell is land (`$1648e`); if in mode `$10`, additionally
probe a few cells ahead and divert to mode `$48` (turn around the obstacle) if
blocked; if a bucket neighbour is an enemy, switch to fighting (`$32` →
`$56a6`); tick morale/food (`$5c80`). It does **not** choose where to go — that
came from its group order.

For a **formation follower** (mode `$68`, the bulk of an army): nothing but
upkeep; its position is stamped by the group lead.

For a **garrison** (mode `$8a`): upkeep only, until a `$8a8a` removal or a
group order pulls it out.

For a **group lead** carrying a live order (`$51538` state `$c`): unpack the
destination cell and enter mode `$10`; on arrival register with the settlement
(`$60`) or begin a siege (`$1c` → `$28`); absorb reinforcements each tick
(`$1a`).

The lords' strategic choices — *declare* an attack, *pick* which village,
*decide* to recruit or build — live one level up, in `$6522` / `$d322` /
`$3e06` (called from `$13040` every tick, operating on `$51538` and `$4f916`).
**That layer is decoded in `strategy.md` (71st pass):** `$6522`'s `$6564`
branch is the commander AI — it picks the nearest enemy leader (`$68fe`),
scores it against a force-scaled patience budget (`$68ee` vs objective field
`112()`), and issues order `$0c` → group state 8 → the group lead enters mode
`$10` toward that cell (via `$6a3a` → `$4b80`). No economy or build reasoning
at that layer. `$d322` + `$3e06` only build the per-side force totals `$57fba`,
which feed a UI mood indicator (`$57fce`), not the AI.

## Measured

25M-step traced resume from `pm68_isoview.snap`, settled first-mission view
(one player army of ~20 men near a neutral village, a few loose animals):

- `$14b62` iterator: 97 passes (one per ~254k instr / ~21 VBLs).
- ~50 of 511 slots active; ~26 reach a handler per pass; ~4850 handler
  dispatches total.
- Mode histogram (handler entries): `$68` 2559, `$12` 774, `$0e` 445, `$56`
  168, `$5c` 152, `$5a` 119, `$8a` 99, `$60` 86, `$52` 51, `$84` 30, `$54` 29,
  `$48` 13, `$58` 11, `$86` 10 — everything else in single digits. In a quiet
  view the loop is almost entirely formation-hold + patrol + regroup dwell;
  combat modes (`$32`, `$5778`) did not fire.
- `$5c80` upkeep: ~2600 calls (once per moving/garrison entity per pass).
- Instruction weight of the whole `$14b62` subtree: small next to the renderer
  — `$163ea` relink 1806 calls, `$1648e` 1979, `$164bc` 213. Consistent with
  `graphics.md`: the sim tick is cheap, the per-VBL fill is not.

### The re-armed fight (73rd pass) — the melee casualty mechanic seen

66M-step traced resume from `pm71_slot4.snap` re-arming slot 1's `byte4 := 4`
every ~4M steps (16 pokes; `scratchpad/pm73_fight.evt`, `trace_cfg.py --blocks`).
~276 sim ticks.

| routine | hits | reading |
|---------|-----:|---------|
| `$6522` decide | 276 | once/tick |
| `$661a` primary-slot decide | **2** | re-arming `byte4` mostly does *not* re-trip `$661a` — the objective slot's `active`/`force` fields stop qualifying after the first order. Only 2 autonomous primary decisions in 276 ticks |
| `$68fe` / `$68ee` | 2 / 2 | the two decisions; both scored in budget |
| `$15302` reached-enemy | 41 | men closing on enemy positions |
| `$56a6` engage | 9 | contacts made |
| `$5778` bookkeep | 2 | gated hard on `flags.bit6` + `d < $fff` |
| `$1533c` melee (mode `$32`) | present | morale-drain rounds |
| **`$5590` kill-or-rout** | **10** | first field-combat resolutions ever traced |
| — of those, KILL (`$55f2`) | **0** | |
| — of those, ROUT (`$560a`) | **10** | `$30fe` returned `2` every time (`group.field60 == 4`) → always rout |
| `$5bd2` wear removal | **0** | `anim_wear` never crossed `$3c` in ~276 ticks |
| `$57f0` projectile | 3 | |
| `$1d70` capture | **15** | the decisive mechanic |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5c80` upkeep | 2136 | ~8 entities/tick |

**Finding.** PowerMonger's battlefield death is a **morale-grind**, not an odds
roll: mode `$32` (`$1533c`) subtracts 1–4 from the enemy's `morale` byte every
tick a unit stays in contact; at `morale <= 0` `$5590` rolls **kill vs rout**
off `group.field60` (a per-group discipline/cohesion value) and the tick-counter
parity. In mission 1 every routed unit *survived* (`field60 == 4` → the roll is
pinned to "rout"), scattered by `$3c08`. The `$5c80`/`$5bd2` **wear** path
(`anim_wear - $3c`, survivability table `$5ccc`) is a slow second channel that a
short fight never reaches — `anim_wear` is only bumped by the iterator's
animation-advance (`$14b9a`, ~once per animation cycle) and is not reset by any
handler, so it is a lifetime-exhaustion counter, relevant only over a long
campaign. So the 72nd pass's "no casualties" was right about *deaths* but missed
that **routing is the real outcome** and it fired ten times. Kills need either a
disciplined attacker group (`field60 != 4`) or `flags.bit5` (encircled).

## Open threads

- **The strategic layer** — decoded in `strategy.md`. Still open there: tracing
  the AI from a *live* enemy captain, the `$67d0` campaign hook mission-file
  format, and the `$580a6` per-side assessment / diplomacy subsystem
  (`$2200`–`$3500`).
- **`$5778` / combat — mechanism now closed** (73rd pass, above + `strategy.md`
  "Combat"). Remaining static-only: the `msg_code`→damage mapping range (why
  `min(.,6)`), the `group.field60` discipline value's own source, and the
  invention level → projectile `type` byte (only `type $12` was seen; it is the
  one type that does an area hit on expiry).
- `$51538` group-order record: `strategy.md` has the stride (`$13c`), the header
  (pending long / type / param), the six interleaved objective slots and the
  `base+$4c` / `base+$64` execution sub-records. Still open: the full field set.
- `$3f86c` per-cell control byte: how influence spreads and what `bit0` / `65`
  mean to the regroup modes.
- Whether byte 33 `== $a` ("hold") is the player's "defend" order or an AI
  disposition, and how the mouse "move / attack / fully engage" commands map to
  the group-order state.
