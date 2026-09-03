# PowerMonger ST — the entity / commander decision loop

Reverse-engineered from the live isometric battle view (70th pass), driven from
`scratchpad/pm68_isoview.snap` (first mission, "Between Pages 1-5", one player
island plus neutral villages). Every address is a RAM address in the relocated
game image (base `$1050`); disassembled from the snapshot RAM
(`scratchpad/pm70_iso.ram`, via `scratchpad/extract_ram.py`). Method: 25M-step
traced resume (`ATARI_TRACE_EVENTS`), `trace_cfg.py --blocks`, plus `watch` on
individual object-record fields to catch the writing PC.

## What the loop actually is

PowerMonger has **no per-unit-type AI**. It runs one **per-entity behaviour
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
| `$32` | `$15302`+ | – | reached an enemy: snap to its position, mode → `$32`, and if it is engageable (`31(A3) > $2c`, `30(A3) >= $3c`) `jsr $56a6` |
| — | `$56a6` | – | **engagement**: if flag bit6 + a linked enemy `28(A3)` within `$fff` world units → `jsr $5778`; set both mode bytes to `$32`, link the attacker into `48(A3)` |
| — | `$5778` | – | **contact bookkeeping, not a battle resolver** — see `strategy.md` "Combat". Marks an engaged garrison's flags `$11`, records the attacker for a support objective, else `$4bc8` (nation peace-break + player notify). Casualties happen elsewhere: attrition in `$5c80`/`$5bd2`, capture in `$1d70` |
| — | `$57f0` | – | **spawn a projectile** into the `$4bdf0` effect array (`$30`×`$10`): copy position, life `$14` ticks, `type = D1` (weapon/invention tier), velocity toward target via `divu #$78`. Flies as its own object record |

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

## Open threads

- **The strategic layer** — decoded in `strategy.md` (71st pass). Still open
  there: tracing the AI from a *live* enemy captain (mission 1's never issues an
  autonomous order), the `$67d0` campaign-order hook, and the `$580a6` per-side
  assessment / diplomacy subsystem (`$2200`–`$3500`).
- `$5778` — **reclassified** (72nd pass, `strategy.md` "Combat"): it is contact
  bookkeeping, not a resolver. The casualty mechanic (`$5c80` survivability
  table `$5ccc` minus a `byte14` wear counter, → `$5bd2` removal → leader /
  group troop-count decrement) is decoded statically but **no field death fired
  in 166 traced ticks** of a forced mission-1 fight — captures (`$1d70` ×5)
  carried it instead. Still open: what raises `byte14` during combat, the
  projectile-impact link, and the invention-level → projectile-`type` mapping.
- `$51538` group-order record: `strategy.md` has the stride (`$13c`), the header
  (pending long / type / param), the six interleaved objective slots and the
  `base+$4c` / `base+$64` execution sub-records. Still open: the full field set.
- `$3f86c` per-cell control byte: how influence spreads and what `bit0` / `65`
  mean to the regroup modes.
- Whether byte 33 `== $a` ("hold") is the player's "defend" order or an AI
  disposition, and how the mouse "move / attack / fully engage" commands map to
  the group-order state.
