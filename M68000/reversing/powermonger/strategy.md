# PowerMonger ST — the strategic layer (the commander AI)

Reverse-engineered 71st pass, continuing `ai.md`. `ai.md` covers the per-entity
state machine (`$14b62`, ~2.4 Hz); this file covers the layer above it: how a
captain decides to march an army at an enemy, and how that decision reaches the
entity loop. Same method — disassembly of `scratchpad/pm70_iso.ram` (game image
at its absolute addresses), block traces, and field watches — driven from
`scratchpad/pm68_isoview.snap` / `pm71_run1.snap` (first mission, "Between
Pages 1-5").

## Where it runs — the sim tick `$13000`, disassembled (72nd pass)

`$13000` **is** the simulation tick. The 70th/71st passes had the call order and
the gating slightly wrong; here is the routine as it actually reads, with the
72nd-pass measured cadence.

```
$13000  ...clamp $4bb3a/$4bb3c (camera bounds)...
$13026  tst.w $57ff2 ; bne $13058        ; PAUSED -> skip the AI + accounting block
$1302e  addq.l #1,$2df70                 ; sim clock ++
$13034  addq.l #1,$4bb3e                 ; master tick ++
$1303a  tst.l 46($14e20) ; beq $13058    ; no running game -> skip
$13040  jsr $127e6   ; event-marker / "Lord X under attack" ticker feed
$13046  jsr $6522    ; << the commander AI (order pipeline)
$1304c  jsr $d322    ; per-side troop totals -> $57fba
$13052  jsr $3e06    ; flag-health UI + per-objective budget decay + $57fba objective term
$13058  clr.w $12f58
 ...set up $e3e2 / $e0d4 pointers...
$13074  subi.w #$1,$57ff0 ; bne $130b0   ; tick-subdivision gate (see below)
$1307e  move.w $57fee,$57ff0             ; reload the subdivision counter
$13088  move.w #$1,$12f58
$13090  jsr $1870    ; per-frame VBL sync / present
$13096  jsr $12ce0   ; offscreen buffer -> shifter (double-buffer flush)
$1309c  tst.w $57ff2 ; bne $130c8        ; paused -> skip the two heavy renderers
$130a4  jsr $178ae   ; render setup A (group $4c exec sub-record)
$130aa  jsr $f898    ; terrain raster
$130b0  jsr $1abaa   ; seasons: fade the grass 16 px ($57ff6 LCG), $57fec++; weather ($1ad2a)
$130b6  jsr $17878   ; render setup B (rotation row-table select)
$130bc  jsr $165b2   ; water / terrain animation for the selected group
$130c2  jsr $14b62   ; << the entity iterator (ai.md)
$130c8  jsr $6a3a    ; << order executor: consume $58016, drive group state + lead mode
$130ce  jsr $7a56    ; sprite / HUD compositor
$130d4  $ff9a += $12f56 ; ...andi #$3f... clr $12f56 when it wraps  ; AUTO-ROTATE hook
$130f6  jsr $d23a    ; $57fba -> $57fce UI mood ratio
$130fc  jsr $7202 ; text panels, then the minimap / compass / captain boxes / icon floor ("The player's commands")
```

**Correction to the 70th/71st passes.** `$6522`, `$d322`, `$3e06` and the
executor `$6a3a` are **not** all in one "tail" block. `$6522`/`$d322`/`$3e06`
run near the *top* of the tick (right after the pause + running gates);
`$14b62` and `$6a3a` run near the *bottom*, after the renderers. Only `$1870`,
`$12ce0`, `$178ae` and `$f898` sit behind the `$57ff0`/`$57fee` subdivision
gate — everything else (`$6522`, `$14b62`, `$6a3a`, `$1abaa`, `$165b2`,
`$7a56`) runs on **every** `$13000` call. The `$57ff0`/`$57fee` counter is the
*present-rate* divider (how often the frame is pushed to the shifter and the
terrain re-rastered), not a sim-rate divider; at normal game speed `$57fee`
observed at 1, so it reloads every tick and the two rates coincide.

**Auto-rotate.** `$130d4` unconditionally adds `$12f56` to the camera rotation
`$ff9a` every tick. `$12f56` is normally 0; it is set non-zero by the
"rotate the view" mouse command so a rotation glides over several ticks rather
than snapping. This is the reader for `$ff9a` that `graphics.md`'s 69th-pass
camera decode was missing.

### Measured cadence (72nd pass)

3M-instruction traced resume from `pm71_run1.snap` (`ATARI_TRACE_EVENTS`,
`trace_cfg.py --blocks`):

| block | hits | per |
|-------|-----:|-----|
| `$1270` VBL IRQ            | 250 | once per displayed frame (3M / 12000) |
| `$13040` tick-running body | 13  | **once per ~19 VBLs ≈ 2.6 Hz** |
| `$6522` / `$d322` / `$3e06` / `$6a3a` | 13 each | once per tick |
| `$14b62` entity iter      | 14  | once per tick |
| `$1307e` subdivision-reload path | 13 | every tick (so `$57fee` = 1 here) |
| `$1870` VBL-sync spin body | 7803 | ~600 spin iterations per tick |

The tick is **compute-bound** in this instruction-counted emulator: one full
`$13000` body (entity FSM + strategy + both renderers) costs ~19 VBLs of
instructions, and `$1870` only waits for a single VBL edge, so the sim
free-runs at whatever rate the frame takes to build (~2.6 Hz on the sparse
first map). On real hardware the same structure yields a similarly coarse tick
(PM's sim is famously slow); the exact ST rate depends on frame cost and is not
independently pinned here. **Every behavioural rate below is quoted in *ticks*,
which is the unit the game logic actually counts in.**

## The two tables the AI reads and writes

### `$58016` — command buffer

5 slots of 6 bytes (`$58016`..`$58033`), one per commander/side:

| off | type | meaning |
|-----|------|---------|
| 0 | byte | commander index — `× $13c` → the `$51538` record |
| 1 | byte | **order type** (even, `$00`..`$32`; `$00` = none). Cleared every tick by `$6a3a` after the executor reads it |
| 2 | word | **order parameter** — a packed cell `{x: bits 0-5, y: bits 6-12}` for movement orders |
| 4 | byte | **slot state** `0/2/4/6/8/$0a`. `$6a3a` dispatches on it each tick; `$6522` issues a new order only when it is `4` |

### `$51538` — group-order table

5 records of `$13c` (316) bytes. Header: long +0 = pending-order flag
(player/script channel), byte +1 = queued type, word +2 = queued param. The
rest is ~15 parallel **6-word arrays** — six "objective slots" per group. The
`$6564` loop walks slot `i = 0..5` with `A1 = base + 10 - 2i`, so field
`n(A1)` for slot `i` lives at `base + (n) - 2i`:

| `n(A1)` | array span | meaning |
|---------|-----------|---------|
| `4(A1)`   | +4..+14   | slot-index / link, written back by `$6822` |
| `28(A1)`  | +28..+38  | objective **active** gate (`ble` → skip the slot) |
| `52(A1)`  | +52..+62  | objective **force** — troops committed to it |
| `76(A1)`  | +76..+86  | objective **state** (`$6` idle/patrol, `$9`, `$d` support) |
| `112(A1)` | +112..+122| objective **range / patience budget** (drained by `$3e06`) |
| `136(A1)` | +136..+146| AI sub-state scratch |
| `256(A1)` | +256..+266| wait-until timestamp, compared to `$2df72` |
| `268(A1)` | +268..+278| campaign-order id, matched against `$67d0[0]` |
| `280(A1)` | +280..+290| campaign phase / sub-order |
| `292(A1)` | +292..+302| escort-target object offset |

Plus the group's **execution sub-records**: state word at `base+$4c`, target
cell word at `base+$64` — written by `$4b80` (below).

## Data structures (C)

Offsets confirmed by disassembly of `scratchpad/pm70_iso.ram`; `// ??` marks a
field seen referenced but not proven. The object record and the effect slot are
in `ai.md`.

```c
// ---- command buffer : $58016, 5 slots x 6 bytes -------------------------
typedef struct pm_cmd_slot {          // one per side; $6a3a walks slots 1..4
/* 0*/  u8   commander;               // x $13c -> the $51538 record. Sign: <0 attack |id|, 0 neutral, >0 own
/* 1*/  u8   order_type;              // even $00..$32; $00 = none. Cleared by $6a3a after the executor reads it
/* 2*/  u16  param;                   // packed cell {x: bits 0-5, y: bits 6-12} for a movement order
/* 4*/  u8   slot_state;              // 0/2/4/6/8/$a. $6a3a advances it each tick; $6522 issues only when == 4
/* 5*/  u8   _pad5;
} pm_cmd_slot;

// ---- group-order record : $51538, 5 x $13c bytes ----------------------
// The AI ($6564) walks it as SIX interleaved objective slots: for slot i (0..5)
// the field logically at n(A1) lives at  base + n - 2*i  (A1 = base + 10 - 2i).
// So each "field" below is really a 6-entry s16 array packed backwards from a
// base offset. Header + execution sub-records are plain (not interleaved).
typedef struct pm_group {             // base = $51538 + group_id
/* +0*/   u32  queued_flag;           // player / script order channel: nonzero -> a queued order in +1/+2
/* +1*/   u8   queued_type;
/* +2*/   u16  queued_param;
          // --- exec sub-record (written by $4b80 / $6a3a) ---
/* +$4c*/ u16  exec_state;            // 2/3/8/9/$a/$c ... the live group state; entity modes key off this
/* +$64*/ u16  exec_target_cell;
          // --- the six interleaved objective-slot arrays (index [i], i=0..5) ---
/* +4 */  s16  obj_link   [6];        // slot-index / link, written back by $6822
/* +28*/  s16  obj_active  [6];       // <= 0 -> skip this objective
/* +52*/  s16  obj_force   [6];       // troops committed to the objective
/* +76*/  s16  obj_state   [6];       // $6 idle/patrol, $9, $d support
/* +100*/ s16  obj_unit    [6];       // $68fe/$6762: the object-record offset assigned to the objective
/* +112*/ s16  obj_budget  [6];       // range / patience; drained by $3e06; underflow -> objective expires
/* +136*/ s16  obj_substate[6];       // AI scratch (campaign sub-mode lands here)
/* +256*/ s16  obj_wait_at [6];       // timestamp vs $2df72
/* +268*/ s16  obj_camp_id [6];       // matched against $67d0.campaignId
/* +280*/ s16  obj_camp_ph [6];       // campaign phase / sub-order
/* +292*/ s16  obj_escort  [6];       // escort-target object offset
          // ... $13c total; other parallel arrays (waypoint cursor $40-equiv, field60
          //     discipline used by $30fe, running-total +36-equiv) not fully mapped
} pm_group;
// $30fe returns  group.field_60 - 2  as the kill/rout + reinforcement-slice shift.
//   field_60 == 4 (mission 1) -> always "2" -> rout, never kill.

// ---- leader / lord record : $4e514, 32 x 32 bytes -------------------
// Full field list: economy.md §1 (pm_leader). The fields this file uses:
typedef struct pm_leader {
/* 0*/  u8   nation;                  // side id 1..5; 0 = empty slot (loop terminator, array ends $4f914); $550e rewrites it
/* 2*/  u16  chain_head;              // -> $4f916 first settlement of the lord (walk via +8)
/* 4*/  u16  cell;                    // packed {x: bits 0-5, y: bits 6-12} of the lord's position
/* 6*/  u16  troops_reserve;          // $d322: += into $57fba[side].word2 ; $15e18/$15760: += 4 on arrival
/* 8*/  u16  troops_field;            // $d322: += into $57fba[side].word0 ; sieges/$5bd2 decrement it; $68fe scores vs it
/*12*/  u16  gather_kind;             // $5cde: the lord's current work order
/*14*/  s16  loyalty_pressure;        // >= 600 -> $550e revolt, reset to 300
/*16*/  u16  herd_throttle;           // $5cde / $60dc
/*18*/  u16  build_site;              // $5cde: $4f916 offset of the settlement under construction
/*20*/  u16  herd_op;                 // $5cde: the nearest $57f68 herd op
/*24*/  u8   goods[8];                // pike, sword, bow, plough, boat, pot, catapult, cannon ($159a4/$16376 index 23 + code/2)
} pm_leader;                          // sizeof 32

// ---- settlement record : $4f916, 18 bytes (economy.md §3) ----------
typedef struct pm_settlement {        // object.34 and leader.chain_head index this
/* 0*/  u16  bucket_next;             // a settlement is also a $47970 bucket node ($5cde links new sites with $16808)
/* 2*/  u16  bucket_prev;
/* 5*/  u8   owner;                   // commander colour holding the settlement; $550e rewrites it
/* 6*/  u8   category;                // render byte6 ($1e = a site being built)
/* 7*/  u8   kind;                    // 7 = capital ($5cde looks for it)
/* 8*/  u16  chain_next;              // the lord's next settlement
/*10*/  u16  unit_head;               // first unit of the settlement (next at 24(unit))
/*12*/  u16  cell;                    // packed cell (mode $52 destination)
/*14*/  u16  leader_off;              // byte offset into $4e514 for this settlement's lord
} pm_settlement;                      // sizeof 18

// ---- per-side assessment block : $580a6, 5 x $20 bytes -------------
typedef struct pm_assess {            // index by side id: $580a6 + side*$20
/* 0*/  u16  decay_period;            // $3e06: objective budget decays every this-many ticks
/* 2*/  u16  march_speed;             // $3fac: the lead's base speed (30; 32 for side 0), before weather/winter/load
/* 4*/  u8   _b4[2];
/* 6*/  u8   peace_bits;              // bit t = at peace / allied with side t ("Diplomacy"): $2458 sets the own bit at build, $34a8 sets, $4c2a clears
/* 7*/  u8   _b7[8];
/*15*/  s8   rel[5];                  // +15+t: attitude toward side t (campaign table layout); $311a READS here (unsigned) ...
                                      // ... and WRITES +16+t (one byte higher, clamped -100..100): a game bug, "Diplomacy"
                                      // $33b0 reads +16+proposer; $68fe reads byte 15 of block[me+t] instead (weight 0 or garbage)
/*17*/  u8   _b17[3];
/*20*/  u8   start_equip[4];          // $238c world build: 20/21 -> the side's first unit's 33/44 ($244c/$2452; $245c then forces 44 := 6), 22/23 -> the followers' ($24fa/$2500)
/*24*/  u8   _b24[8];
} pm_assess;                          // sizeof $20; $2200-$3500 cluster owns the rest
// Also read: word 8 (+4 = the herd-throttle reload, $5cde), word 12 (the RNG
// mask for a new group's 72(sub), $25d6). The whole block is part of the
// campaign table entry each land loads ("The campaign").

## `$6522` — the commander AI

Outer loop over the 5 command slots. A slot with `4(A0) != 4` is skipped
(scan only). For `4(A0) == 4` ("engine has consumed the last order, ready for
the next"):

- **`$51538[cmd]` long +0 nonzero** → a **queued** order (player click, or a
  mission script): copy type→`1(A0)`, param→`2(A0)`, clear the flag, next slot.
  This is the player's order channel.

- **else `$6564`** — **synthesise** an order. Walk the 6 objective slots; for an
  active one (`28() > 0`, `4() == 0`):

  1. state `$6` and past its wait timer (`256() + $14 <= $2df72`) → **`$6762`**:
     if the global campaign slot `$67d0` holds an order whose id matches this
     objective's `268()`, obey it (order `$06`, or a random sub-mode `2..5`
     seeded from `$57fec`). `$67d0` = `{campaignId, orderType, subMode}`, static
     in the binary in mission 1 — **no writer found**; it is the campaign-script
     hook.
  2. `52() >= $16` (≥ 22 troops) → **`$69b4`** scans `$4e514` for the nearest
     enemy leader (skip own/empty sides; cost = `max(|dx|,|dy|)` weighted by the
     leader's troop count; already-adjacent leaders excluded) → issue order
     **`$08`** (→ group state 3 = besiege) toward it.
  3. objective slot `i > 0` whose predecessor is state `$d` / `280() == 4` →
     issue order **`$0c`** to **escort** `292()`'s object.
  4. primary slot (`i == 0`), `52() - 4 > 0` → **`$68fe`** scans `$4e514` for
     the nearest enemy leader (cost weighted by the per-side assessment byte
     `16($580a6 + side*$20)`); **`$68ee`** scores it `≈ (d/2)·(force/8 + 1)`;
     if `score <= 112()` (within budget) → set group state 4 and issue order
     **`$0c`** (→ group state 8 = march & engage) toward that leader's cell.

Order writes go through `$67ee` → `$6822`: `$67ee` re-packs the found leader's
cell `4(A3)` into `{x:6, y:7}`, `$6822` stores `{type, param}` into
`$58016[cmd]` bytes 1/2 and stamps `4(A1)` / the `$58042` cross-index.

**This layer has no economy, build or recruit reasoning** *(Observed — the
`$6522`/`$6564` handler was fully disassembled and traced in mission 1; no
economy/build branch was seen, but `$6564` is one of several `$6522` sub-cases
and the campaign hook `$67d0` was never live. Evidence taxonomy: `ai.md`.)*. The
autonomous decision is: *"march the army at the nearest enemy leader, if I have
more than ~4–22 men and the target is inside a range budget that scales with my
army size."* Reinforcement is handled at the entity level (mode `$1a`, `ai.md`);
build/invention orders, if the AI issues them at all, come through the `$67d0`
campaign hook, not from `$6564`.

## `$6a3a` / `$6ac6` / `$6b38` — the order executor

Per tick, `$6a3a` dispatches command slots 1..4 on `byte4` through the table at
`$6a80` (states 2/4/6/8 → `$6ac6`; 6 and 8 additionally poke a UI effect via
`$1c390` / `$1c340`), **then clears `byte1`/`word2`**. `$6ac6` → `$6b38` reads
`byte1` (order type), clears it, and dispatches types below `$34` through the
table at `$6b5a` (`move.w 6(PC,D0.w)` at `$6b52`, `jmp 2(PC,D0.w)` at `$6b56`:
handler = `$6b5a + word[$6b5a + type]`). Handlers read the slot as A0
(`0(A0)` commander, `2(A0)`/`3(A0)` target cell x/y) and the commander's group
offset as D2. Who posts each type is in "The player's commands" below.

| type | handler | calls | posted by |
|------|---------|-------|-----------|
| `$02` | `$6b8e` | `$3888(x,y)`, D6 = `$ea` | icon, targeted |
| `$04` | `$6ba8` | `$1c18(cmd,x,y)` | captain-select mode (icon `$04`, then a captain click) |
| `$06` | `$6bbe` | `$3154` D3=2 D4=`$1a`, then `$38ce` | icon, targeted; AI (`$6762`) |
| `$08` | `$6bea` | `$3154` D3=3 D4=`$1c`, then `$3248` | icon, targeted; AI (`$69b4`, besiege) |
| `$0a` | `$6c16` | `$3c08` (regroup, the lead `-12(A3)`) | HOME icon |
| `$0c` | `$6c32` | `$4a7a(x,y)` → `$4b80` (group state 8) | sword icon, targeted; AI (`$68fe`) — **march & engage** |
| `$0e` | `$6c48` | `$3154` D3=9 D4=`$22` | bulb icon, targeted |
| `$10` | `$6c6a` | `$3154` D3=`$a` D4=`$6e`, then `$6128` | icon, targeted |
| `$12` | `$6c96` | `$30fe`, `$39d4` D7=1 | icon, immediate |
| `$14` | `$6cbc` | `$1cc4` | icon, immediate |
| `$16` | `$6cc6` | `$35a0(cmd, param)` | the three posture icons, param 2/3/4 |
| `$18` | `$6cda` | `$30fe`, `$39d4` D7=2 | icon, immediate |
| `$1a` | `$6d00` | `$390e(x,y)` | icon, targeted |
| `$1c` | `$6d12` | `$3154` D3=`$f` D4=`$78` D5=0 (neutral) | icon, targeted |
| `$1e` | `$6d32` | `$3154` D3=`$e` D4=`$76` D5=−cmd | icon, targeted — **offer an alliance** ("Diplomacy") |
| `$20` | `$6d56` | `$3154` D3=`$10` D4=`$7a` D5=−cmd, then `$1d36` | icon, targeted |
| `$22` | `$6d90` | `$3ce8(D1=cmd, D2=param)` | captain-portrait click (`$134a4`); AI |
| `$24` | `$6dbc` | `not.w $57ff2` (pause) | PAUSE button |
| `$26` | `$6dd0` | `$d0dc(param)` when cmd ≠ local side: one character into the message line (panel `$16`) | linked play: the local side posts it at `$d14c` (inferred: chat) |
| `$28` | `$6dc6` | `$13d1a` (rebuild the land) | REPLAY MAP button |
| `$2a` | `$6dea` | `$34a8(D0=cmd, A3=$51538+param)`: accept an alliance | alliance panel YES; `$33b0` (`$3458`) for an AI lord |
| `$2c` | `$6e04` | `$71fe := 1` | MULTI PLAY button |
| `$2e` | `$6e10` | `$71ae`, `$d2c8` (end of land) | RETIRE button; `$d23a` on captain loss |
| `$30` | `$6e36` | `$580a0/$580a2 := param`, `$13d1a` | RANDOM MAP button (param `$2df84`) |
| `$32` | `$6e56` | `$cada` (refusal message) when cmd ≠ local side | alliance panel NO (into the local slot, so locally a no-op; inferred: for a linked proposer) |

The 121st-pass version of this table read the base as `$6b5c` and was one
entry off (`$06` → `$6bec`, `$08` → `$6c18` are mid-instruction). Checked on
the real CPU: 12 dispatches at `$6b56` over 6 handlers on `pm121/run/k60_s2`
all landed at `$6b5a + word` (`scratchpad/pm123/disp.txt`).

`$6888` is a word table indexed by order type: `$02`→5, `$06`→2, `$08`→3,
`$0a`→7, `$0c`→8, `$0e`→9, `$10`→`$a`, `$1a`→`$c`, `$1c`→`$f`, `$1e`→`$10`,
the rest 0. `$6822` (the AI's order write) compares the entry with the
objective's state `76(A1)` and does not re-issue an order whose state the
objective is already in (except `$0c` with D7 = 0). The states line up with the
group-state → entity-mode table in `ai.md` (state 3 ⇔ besiege modes
`$28`/`$2a`; state `$c` ⇔ mode `$1a` absorb-reinforcements).

`$3154` is the common order dispatcher: it turns the packed target cell into a
word offset `(cellY*64 + cellX)*2`, looks up the `$47970` bucket for that cell
to find the entity/settlement standing there, checks friend/foe by the **sign
of the commander id** (`<0` attack side `|id|`, `0` neutral, `>0` own), and
commits through **`$4b80`**:

```
$4b80  worldX = cellX*256 + 128 ;  worldY = cellY*256 + 128     ; cell centre
       jsr $37c2                                                 ; validate / path setup
       move.w #$8, 0(A3)         ; group execution sub-record state = 8
       move.w D1, 24(A3)         ; target link
       A1 = $51b66 + -12(A3)     ; <- the group's LEAD MAN object
       move.b #$30, 30(A1)       ; lead prev-mode
       move.b #$10, 31(A1)       ; lead CURRENT MODE = $10  (advance-to-target, ai.md)
       movem.w #$0018, 20(A1)    ; lead target (words 20/22) = (worldX, worldY)
```

From here `ai.md` takes over: `$14b62` walks the lead man in mode `$10` every
tick (velocity integration toward `20/22`, terrain probe, obstacle divert to
mode `$48`); the formation followers (mode `$68`) are stamped from the lead;
bucket proximity flips men to combat (`$32` → `$56a6` → `$5778`).

## The player's commands (123rd pass)

The player's orders do not go through the `$51538` queue: every UI path writes
the local side's command slot directly (`movea.l $58034,A0` then
`1(A0)` = type, `2(A0)`/`3(A0)` = target cell), and the executor consumes it on
the next tick. The tick's UI tail (`$130fc`) runs in this order, on the pointer
`$2df92`, the click position `$2df8e` and the click flags `$2df96`/`$2df98`:

1. **`$7202`, the text panels.** Up to four draggable panels, 8-byte entries
   at `$7a36` (word: template offset from `$7a36`; bytes: x/16, y); `$7a3c` is
   the id of the open panel. A panel is a character grid built from a template
   by `$a91a` (bytes with bit 7 set remapped through the list at `$a99c`, `@`
   runs filled by the panel's formatter table in A6). Cells are 4 × 6 px; a
   click on the row under a button's top edge (`$81`) walks left to the `$80`
   corner, whose grid offset is the button code D3, and `$76f6` dispatches on
   `$7a3c` (table base `$76fe`, id 4 = entry 0). Every panel, decoded by
   `reversing/powermonger/py/panels.py`:

   | id | template | opened by | buttons (D3) → effect |
   |----|----------|-----------|------------------------|
   | 2 | `$921a` | `$9036` (captain info) | none: name, job, aggression, loyalty, strength, speed, food, troops, carrying |
   | 4 | `$b03a` | options icon `$2e` (`$af6c`) | game speed slider; `$31` "@@@@" (`$aeac`, only when the local slot state is 2); `$39` GAME → panel 8 (`$af52`) |
   | 6 | `$b0ad` | `$aeac` | FILE: `$17` LOAD (`$3f768` → `$3f2a0` OR-merge, `$e29c`); `$47` save (`$3f2a0` → `$3f768`, `$e288`, only when `$14e4e == $2c`); `$77` (`$1ba72`) |
   | 8 | `$b160` | GAME | `$11` RETIRE → order `$2e`; `$41` REPLAY MAP → `$28`; `$71` SELECT MAP (`$abcc`, `$13ce8`); `$a1` MULTI PLAY → `$2c`; `$d1` RANDOM MAP → `$30`, param `$2df84`; `$101` PAUSE → `$24`; `$131` SEND MESSAGE → panel `$14` (`$d194`) |
   | `$a` | `$b510` | briefing | "Between Pages": `$2a3`/`$2b1` OK → `$b814` |
   | `$c` | `$bb66` | multiplayer | `$1ba` CONNECT (`$2df6c := 1`), `$1d6` CANCEL |
   | `$e` | `$bfda` | main menu `$13de8` | `$92`/`$da`/`$122`/`$16a` → `$2df6e := 2/4/6/8` (Start New / Continue Conquest / Play Random Land / Load Data Disk) |
   | `$10` | `$cd82` | disk requester | `$e2` OK, `$f6` CANCEL |
   | `$12` | `$c332` | modem connect | `$68` CANCEL |
   | `$14`/`$16` | `$d048` | SEND MESSAGE / `$d0dc` | none (a message line) |
   | `$18` | `$c512` | Start New Conquest with lands conquered | `$7a` YES clears `$3f2a0` (196 bytes), `$8a` NO |
   | `$1a` | `$c820` | `$c706`, from `$33b0`, when an envoy reaches a lord of the local side | `$146` YES → order `$2a`, param `$5809e` (only if that group's `-48(A3) != 0`, `192(A3) == $e` and its lead is on the local side); `$162` NO → `$32` |

2. **The minimap** (x < `$40`, 6 ≤ y < `$86`; cells 1:1, `(x, y−6)`). With a
   command armed (`$57fd4 != 0`), `$13892` draws the line from the selected
   captain's lead to the pointer, and a click posts `type = $57fd4`, target
   `(x, y−6)` (`$131be..$131cc`). Without one, a click recentres the view
   (`$4bb3a`/`$4bb3c`). Clicks in the strip above the map (y < 6) set
   `$58098 := x/16` and redraw the minimap (`$107d6`; inferred: the minimap
   overlay selector).
3. **`$13212`**: four rectangles by the compass (`$13250`). The first two turn
   the view by ∓4 (`$ff9a`); one entry path (`$13270`, taken when `$2df96` is
   set) also sets the auto-rotate `$12f56` to ∓4, the other (`$13278`) clears
   it. The other two zoom through `$13f60`: `$57ffc` ∓1 clamped 1..7, or
   straight to 2 / 7 on the second path.
4. **The compass rose** (x < `$20`, y > `$a7`): an 8-way camera pan
   (`$1420c` angle minus the yaw `$ff9a`, table `$132ca`).
5. **The captain boxes** (twelve rectangles at `$138ec`, each live only while
   the local side's `$51538` record has a non-zero word for it): the first six
   open the captain panel 2 (`$9036`, A3 = that captain's group). On the second
   six, the other button (`$2df98`) recentres the view on that group's lead;
   with the captain-select mode on (`$57fd6`, icon `$04`) a click posts order
   `$04` with the selected group (`$57fd2`) and the box index; otherwise it
   posts `$22`, param = box index.
6. **The icon floor** (`$13506`): the icon grid is the perspective floor under
   the view. Column edges `$12e6a` and row edges `$12ee4` are lines
   `(x0,y0,x1,y1)`; the icon id is `columns crossed + 16 × rows crossed`, each
   loop counting the edge it stops at. The id is looked up in `$19bde` (24
   words, `-1` terminated); the slot index D1 dispatches through `$135cc`:

   | slot D1 | id | screen (320 × 200) | glyph | handler → effect |
   |---------|----|--------------------|-------|------------------|
   | `$02` | `$ea` | (299,182) | figure | `$135fe`: arm `$57fd4 := $02` |
   | `$04` | `$c4` | (103,186) | two men | `$13620`: toggle captain-select `$57fd6` |
   | `$06` | `$d7` | (201,181) | sphere | arm `$06` |
   | `$08` | `$da` | (275,162) | arrow into men | arm `$08` (besiege) |
   | `$0a` | `$b4` | (100,170) | HOME | `$13652`: post `$0a` now |
   | `$0c` | `$e8` | (243,190) | sword | arm `$0c` (march & engage) |
   | `$0e` | `$e9` | (274,187) | light bulb | arm `$0e` |
   | `$10` | `$db` | (297,156) | – | arm `$10` |
   | `$12` | `$d5` | (142,193) | – | post `$12` now |
   | `$14` | `$d9` | (252,168) | four arrows | post `$14` now |
   | `$18` | `$d6` | (173,188) | – | post `$18` now |
   | `$1a` | `$d8` | (227,174) | chain | arm `$1a` |
   | `$1c` | `$b3` | (74,175) | – | arm `$1c` (neutral target) |
   | `$1e` | `$a3` | (73,161) | eye with arrows | arm `$1e`: offer an alliance to the clicked settlement's lord |
   | `$20` | `$93` | (72,149) | eye | arm `$20` (enemy target) |
   | `$26`/`$28`/`$2a` | `$a4`/`$94`/`$84` | (97,156)/(94,145)/(92,135) | posture | `$13678`: post `$16`, param 2/3/4 |
   | `$2c` | `$c3` | (75,191) | – | `$136b2`: toggle `$57fea`, disarm `$57fd4` |
   | `$2e` | `$83` | (71,138) | – | `$13716`: options panel 4 (`$af6c`) |

   Arming the icon that is already armed disarms it (`$1898e`). Screen
   positions are centroids from the game's own hit-test
   (`reversing/powermonger/py/iconmap.py`); the sword `$0c` and the options
   `$2e` were clicked and behaved as listed. The other glyph names are read off
   a rainy frame and the effects of `$3888`, `$1c18`, `$38ce`, `$6128`,
   `$1cc4`, `$35a0`, `$390e`, `$1d36` are not decoded: the manual's names
   (food, supplies, invent, spy, ...) are **inferred** until each is followed.

**Driving it headless** (`reversing/powermonger/py/clicks.py`): the pointer
moves 1:1 with `mouse move` and clamps at 0, so home it with a large negative
move and click at absolute (x, y). `reversing/powermonger/py/drive_win.sh`
plays mission 1 to a natural victory this way (next section, "How a land
ends").

## `$d322` + `$3e06` → `$57fba` → `$d23a` → `$57fce`

`$57fba` = 5 × 4-byte per-side force totals, rebuilt from scratch every tick:

- **`$d322`** zeroes all five, then for each leader in `$4e514` (32-byte
  records) adds `+0 += 8(leader)`, `+2 += 6(leader)` (its two troop-count
  fields). It also walks the `$47970` buckets around each leader via the
  neighbour-offset ring `$d49e`, and where an enemy category-0 entity whose
  group is strong enough (`8(leader) >> 1 > -24(groupRecord)`) is in contact it
  calls `$4bc8` — troop-count / ownership reconciliation. That is bookkeeping,
  **not an order.**
- **`$3e06`** — larger than the 69th-pass "morale→UI" reading. Its head is the
  flag-health indicator (morale byte 45 of the selected group's lead,
  `divu #$14`, → `$58056`). Then it walks **every** group's 6 objective slots:
  adds `52(objective)` into `$57fba[side].word0`, and runs the **per-objective
  budget decay** — every `$580a6[side].word0` ticks (doubled while the objective
  is in state 6), `112(objective) -= 52()/8 + 1`. When `112()` underflows the
  objective expires and the group re-picks a patrol waypoint (`$12c9a` / field
  `40()`). A big army spends its patience budget fast (commits), a small one
  slowly.

`$d23a` (at `$130f6`) is the **only consumer** of `$57fba`. For the local side
`$57ffe`:

```
enemy = Σ (other four sides' .word0) + 1
ratio = min(4, (2*myForce + enemy/4) / enemy)      ; clamp 0..4
$57fce = ratio ; jsr $16bb8                         ; captain's mood / fist indicator
```

`$6522` never reads `$57fce`; besides the fist indicator (`$16bb8`, `$188dc`)
its one consumer is the end-of-land verdict `$d2c8`: **ratio 4 at the moment
the land ends is a win, anything less a defeat** ("How a land ends", below).
Before the ratio, `$d23a` checks the local side's captain group: if
`word[$51538 + side*$13c + 28]` (the owner-side word of that side's exec
sub-record 0) is `<= 0`, it posts command `$2e` itself and clears `$57fce`,
which ends the land as a defeat. The knob the autonomous AI actually turns is
the per-objective budget `112()` and the per-side assessment weight in
`$580a6`, not this global ratio.

`$580a6` — 5 × `$20`-byte per-side assessment blocks — is written all over the
`$2200`–`$3500` cluster and from `$139dc`/`$13a3e`/`$13b20` in the sim tick.
The relation and peace-bit fields are the diplomacy layer ("Diplomacy",
below); `$68fe` reads one wrong byte of it as a targeting weight.

## `$127e6`

Min-of-2 selector over a 59-entry / 58-byte table at `$12952` keyed on
`10(entry)`, emitting the two smallest into `$58058`. It feeds the on-screen
event markers / the "Lord X's men are under attack" ticker. Not a decision
routine — listed only because it shares the `$13040` call site.

## The campaign-order hook — `$6762` / `$67d0` (72nd pass, static)

`$6762` is the first thing `$6564` tries for an objective in state `$6` past its
wait timer. `$67d0` is a 6-byte global: `{word0 campaignId, word2 orderType,
word4 subMode}`. The routine, decoded:

```c
// A1 = objective slot base ($51538 record + 10 - 2*i)
int pm_campaign_hook(obj *A1) {
    if (g_campaign_order.campaignId == 0)          return 0;   // no scripted order
    if (g_campaign_order.campaignId != A1->camp_id_268) return 0; // not for this objective
    if (g_campaign_order.campaignId == 0x0d && A1->camp_phase_280 != 2) return 0;
    obj *leader = &g_object_records[A1->field_100];            // the objective's assigned unit
    if (leader->byte0 != A1->expect_nation_29)     return 0;   // wrong nation holds it
    int sub = g_campaign_order.subMode;
    if (sub == 0) sub = (g_tick_rng & 3) + 2;                  // 2..5, "random"
    A1->ai_substate_136 = sub;
    pm_order_pack(A1);                                          // -> $67ee -> issue the order
    return 1;                                                   // handled
}
```

`$67d0` has **no writer anywhere in the loaded game image** (verified: the only
reference to the address `$67d0` is the `lea $67d0,A4` inside `$6762` itself),
and it lies in the code segment, outside the `$580a6..$581f1` block the
campaign loads per land ("The campaign", below). No path that loads a land
writes it, so the hook is inert in every land, campaign or random: `$6762`
always returns 0. It is dead code in this build (its original writer, if there
was one, is gone).

The AI therefore has no path other than "march at the nearest enemy leader":
there is **no build / recruit / invention reasoning** in the strategic layer.

## Combat (73rd pass — mechanism closed, rout is the real outcome)

The 70th/71st passes flagged "`$5778` combat resolution" as the biggest open
gap and assumed it was a battle resolver with odds and casualty rolls.
**It is not.** PowerMonger has no discrete battle resolver. Combat is a set of
loosely-coupled mechanisms, all running at the entity level in `ai.md`'s
`$14b62` tick. The 73rd pass traced the first real field fight (`$5590` fired
ten times) and found the decisive one is a **morale grind ending in a rout**,
not the wear-attrition path the 72nd pass focused on.

### 0. The melee grind (`$1533c`, mode `$32`) — the primary mechanic

Once two units are in mode `$32` (locked in contact via `$15302` → `$56a6`),
`$1533c` runs every tick for the attacker:

```c
void h_melee(obj *A1 /*attacker*/) {              // $1533c
    obj *T = &obj[A1->link_target_48];
    if (T->owner <= 0 || T->prev_mode == 0x3c) {  // target already a corpse/routed
        A1->mode = A1->prev_mode = 0x2c; return;  // fighting-hold
    }
    T->heading = A1->heading + 0x80;              // face the attacker
    if (T->mode != 0x32) pm_engage(T /*A3*/, A1); // drag the target into the fight
    int dmg = min((u8)A1->msg_code, 6) >> 1;      // 0..3
    dmg += 1;                                     // 1..4 per tick
    T->morale -= dmg;                             // <<< byte 45 is the melee HP
    if (T->morale <= 0) { pm_kill_or_rout(A1, T); return; }  // -> $5590
    A1->link_into(T);  T->mode = 0x32;            // keep grinding
}
```

`$5590` — reached when a unit's `morale` is ground to `<= 0`:

```c
void pm_kill_or_rout(obj *A1 /*attacker*/, obj *A3 /*loser*/) {
    A3->morale = 0;
    int roll = 0;
    if ((A1->flags & BIT4) ? A1->group_off != 0 : (A1->flags & BIT6)) {
        obj *lead = A1->link_related ? &obj[A1->link_related] : A1;
        if (lead->owner > 0) roll = pm_30fe(lead);   // = lead's group.field_60 - 2
    }
    bool kill;
    if      (roll == 0) kill = true;
    else if (roll == 2) kill = false;                // <-- mission 1: field_60 == 4 -> roll 2 -> always rout
    else kill = ((g_tick_rng + A1->anim_phase) & 2) == 0;
    if (A3->flags & BIT5) kill = true;               // encircled: no escape

    if (kill) {                                      // $55f2
        A3->owner = -A3->owner;                      // negative owner = dying
        A3->anim_sub = 0;  A3->category = 0x0c;      // corpse
        A3->dwell = 0xa0;                            // 160-tick decay to a free slot
    } else {                                         // $560a  ROUT
        pm_3c08(&group[A3->group_off]);              // restructure/scatter the loser's group
        A3->prev_mode = 0x3c;  A3->category = 0;     // survives, disorganised
    }
    // then: adjust the loser's group committed-force counter (42/-24) either way
}
```

The `group.field_60` term is a per-group **discipline / cohesion** value.
Mission 1's groups all carry `field_60 == 4`, so `pm_30fe` returns `2` and the
roll is pinned to **rout** — ten routs, zero kills in the 73rd-pass fight.
A disciplined attacking group (`field_60 != 4`) or an encircled loser
(`flags.bit5`) gets kills.

### 1. Contact → engage (`$56a6`, from mode `$32`)

`$15302` (an entity reached the record it was chasing, `48(A1)`) snaps to the
target's cell, sets both mode bytes to `$32`, and if the target is "engageable"
(`31(target) > $2c` and `30(target) >= $3c`) calls **`$56a6`**:

```c
void pm_engage(obj *A3 /*me*/, obj *A1 /*enemy*/) {
    if (A3->flags & BIT6) {                       // "can fight"
        obj *e = &g_object_records[A3->link_28];
        int d = max(|e->x - A3->x|, |e->y - A3->y|);   // Manhattan-max distance
        if (d < 0xfff) pm_engage_bookkeep(e);          // -> $5778
    }
    if (A3->flags & BIT4) pm_engage_bookkeep(A3);      // -> $5778
    A3->mode = A3->prevmode = 0x32;                    // fighting
    A3->attacker_link_48 = offset_of(A1);
    ... link A3 into A1->target fields (46/38) ...
}
```

### 2. `$5778` — contact bookkeeping, **not** casualties

```c
void pm_engage_bookkeep(obj *A3) {
    group *g = &g_group_orders[A3->group_42];
    if (g->state == 6) {                          // besiege in progress
        obj *garr = &g_object_records[A3->link_46];
        if (garr in [$4cff8,$4d250)) garr->flags = 0x11;   // mark garrison "engaged"
    }
    if (g->state == 0x0d)                         // support objective
        g->field_204 = offset_of(attacker);       // record who is attacking
    else
        pm_contact_reconcile(target=A1, attacker=A3);  // -> $4bc8
}
```

`$4bc8` walks both parties' nation bytes (`$4de2`), and when two different
nations touch it drops into `$4c2a` → clears the "at peace" relationship bits in
both sides' `$580a6` assessment blocks (`bclr D3,6(A5)`), frees a group slot if
one side's group was in state 8 (`$35f4`), calls `$c5ee` ("war declared"
player message) if the player is one of the two nations, and writes a `-8`
assessment delta via `$311a`. **This is the diplomatic consequence of contact,
not attrition.**

### 3. Projectiles — `$57f0`

`$5bd2`/`$56a6` and the mode handlers spawn projectiles into the effect array
`$4bdf0` (`$30` slots × `$10` bytes):

```c
effect *pm_spawn_projectile(obj *shooter, int type /*D1*/, int tx, int ty) {
    effect *e = first slot with life==0;         // 14(slot); dbeq scan, $30 slots
    if (!e) return NULL;
    e->shooter_12 = offset_of(shooter);
    e->x = shooter->x; e->y = shooter->y;        // movem.w 8(shooter) -> 8(e)
    e->life_14 = 0x14;                            // 20 ticks
    shooter->countdown_18 = e->reload_15;         // shooter's reload delay
    e->type_6 = type;                             // arrow / spear / musket by invention level
    resolve target cell ($16808);
    // normalised velocity toward (tx,ty): divu #$78 (speed denominator 120),
    // dx/dy then dy/dx, same fixed-point trick as $164bc
}
```

The projectile then flies as its own object record for 20 ticks; on arrival at
an enemy cell it flips that entity toward removal (mechanism 4). The `type`
byte selects the sprite and, indirectly, the lethality — higher invention
levels issue faster / deadlier projectile types.

### 4. Attrition — `$5c80` upkeep → `$5bd2` removal (the slow second channel)

`$5c80` runs once per tick for every moving or garrison entity:

```c
int pm_upkeep(obj *A1) {                                // $5c80, exactly
    int surv = t_survivability[A1->flags & 0x1f];       // inline table at $5ccc
    int wear = (u8)A1->anim_wear - 0x3c;
    if (wear >= 0) {                                    // bmi skips otherwise
        surv -= wear * 4;
        if (surv < 0) { pm_unit_remove(A1); }           // -> $5bd2
    }
    int morale = (s8)A1->morale;
    if (morale < 0) { A1->morale = 0; return 1; }
    if (surv > morale) { A1->morale += (g_tick_rng & 1); return 1; }  // creep up
    return 0;                                           // surv <= morale: spent, no recovery
}
```

`t_survivability` (`$5ccc`) is a sparse **17-byte** table indexed by
`flags & $1f` (a small enum, not a bitfield): index `0/1/2/4/8/$10` →
`90/82/69/79/72/95`; every other index is `0` (and `>= 17` reads into the next
routine's code — never happens, the enum only takes those six values plus
`$11`). `$5778` stamps an engaged garrison's flags to `$11` → survivability `0`,
so it stops recovering morale and is removed once `anim_wear` crosses `$3c`.

`anim_wear` (object byte 14) is only ever **incremented** — by the iterator's
animation-advance at `$14b9a`, roughly once per animation cycle for a
moving/animating unit — and **never reset** by any handler. It is a lifetime
counter: a unit that has been continuously active for ~`$3c` animation cycles
becomes attrition-vulnerable. This is why the wear path is a long-campaign
mechanic and fired **zero** times in the 73rd-pass 276-tick fight.

`$5bd2` (removal) decrements the parent's strength — a **group follower**
(`flags & BIT6`) decrements the group's committed-force counter
`-24($51538+grp)` via `$1b8c`; a **garrison / lone unit** decrements its
leader's troop count `8($4e514 + 14($4f916 + 34(A1)))`. Then `$5c10` turns the
record into a 160-tick corpse (`byte5` negated, category `$c`).

### 5. Settlement capture / regroup — `$1d70`

The besiege modes (`$28`/`$2a`, `ai.md`) grind a settlement's garrison count
down while the group stays in state 3; at 0 they call **`$1d70`** (ownership
itself is transferred by the besiege caller — `$25d6`/`$2644`, `economy.md`).

**`$1d70` proven (99th, via `$3c08`'s bit-4 teardown — `ai.md`):** it is a
**route-string expander**, not the ownership writer. It picks a terrain route
string from the `'C'`(`$43`)-delimited table at `$1e9e` (indexed by the highest
set bit of `word[grouprec−24]`), then for every roster member (chain via
`word[+26]`) does a two-way scan of that string — a 1-D slice of terrain codes,
`'P'`/`'S'`/`'B'` passable, `$ba` blocked — for the nearest cell matching the
member's preferred terrain (`word[$1e8c + 44(member)]`), marks it taken so the
next member picks a different one, and writes the member a step vector
(`20/22 := (dx,dy) << 6`), mode `$08`, `dwell 0`, `category 0`. Net effect: the
group is dispersed / sent home along a terrain-following path.

### Measured — the re-armed mission-1 fight (73rd pass)

66M-instruction traced resume from `pm71_slot4.snap`, re-arming slot 1's
`byte4 := 4` every ~4M steps (16 pokes; `scratchpad/pm73_fight.evt`,
`trace_cfg.py --blocks`), ~276 sim ticks. (The 72nd pass ran 40M / 166 ticks
with a single poke; the counts that overlap match.)

| routine | hits | reading |
|---------|-----:|---------|
| `$6522` decide | 276 | once/tick |
| `$661a` primary-slot decide | **2** | re-arming `byte4` mostly does *not* re-trip `$661a` — the objective slot's `obj_active`/`obj_force` stop qualifying after the first order issues. Only 2 autonomous primary decisions in 276 ticks |
| `$68fe` / `$68ee` | 2 / 2 | both decisions scored inside budget |
| `$15302` reached-enemy | 41 | men closing on enemy positions |
| `$56a6` engage | 9 | contacts made |
| `$5778` bookkeep | 2 | gated hard on `flags.bit6` + `d < $fff` |
| **`$5590` kill-or-rout** | **10** | first field-combat resolutions ever traced |
| — KILL (`$55f2`) | **0** | |
| — ROUT (`$560a`) | **10** | `$30fe` → `2` every time (`group.field_60 == 4`) |
| `$5bd2` wear removal | **0** | `anim_wear` never crossed `$3c` in 276 ticks |
| `$57f0` spawn projectile | 3 | |
| `$1d70` group route-expand | **15** | fires on capture *and* regroup; the route/disperse step, not the ownership write (99th) |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5c80` upkeep | 2136 | ~8 entities/tick |

**Reading.** A forced attack in mission 1 produces engagement, a handful of
projectiles, ten **routs** (units scattered by `$3c08`, none killed), and
fifteen **captures**. So territory changes hands and armies get broken up, but
almost nobody dies on the field — because mission 1's group discipline
(`field_60 == 4`) pins the `$5590` roll to "rout", and the wear channel is far
too slow for a 276-tick fight. The 72nd pass's "no casualties" verdict was right
about deaths and wrong about outcome: **routing is what combat does here**, and
it fired ten times.

On later lands the same pipeline runs by itself (`ai.md` "Natural runs on later
lands"): over 200M steps each, lands 5, 60, 0 and 25 made 4-8 `$661a` primary
decisions (each scored by `$68fe`/`$68ee`), killed 7-59 men through `$55f2`, and
the enemy lords' pigeons carried the orders. The `$5bd2` wear path still never
fired. Histogramming `$68fe`/`$68ee` over those decisions is still to do.

## RNG and determinism (72nd pass)

There are **three** "random" sources; none is a seeded PRNG in the *AI* path:

- **`$57fec`** — a free-running 16-bit counter, `addi.w #$1,$57fec` in `$1abc0`
  (reached from `$1abaa`, once per tick, gated by a phase accumulator so it
  advances a little under once per tick). Every AI use takes low bits only:
  `& 1` (morale creep, `$5c80`), `& 3` (campaign sub-mode, `$6762`), `& 7`
  (a speech-line pick, `$3e06`/`$3f08`). Because it is just the low bits of the
  tick count, **the AI is fully deterministic** given the tick number — there is
  no seeding, no entropy, and a save/restore at the same tick replays
  identically.
- **`$57ff6`** — a genuine 13-bit LCG, `x = (x * $24a1 + $24df) & $1fff`,
  stepped 16× per housekeeping pass in `$1abc0`. It feeds the **sound** driver
  (`$ff9e`-relative table lookups); its **wrap** to 0 also drives the `$57fd0`
  rotation + the `$4d252` wildlife poke (see "What `$1abaa` actually is"). Never
  the AI or combat directly.
- **`$12c9a` / `$2df84`** — a 32-bit LCG (`state = state * $bb40e62d + …`,
  default seed `$bc614e`), used **only at world-build** (`$10d1e` reseeds
  `$2df84` from `$580a0`, then draws map size / lord count / placement). Makes
  the generated map a pure deterministic function of `$580a0` (97th).

A modern reimplementation that wants PM's feel can keep the tick-counter trick
for the coarse AI jitter and add a real PRNG only where it wants
non-determinism (casualty rolls, if it makes combat a resolver).

## What actually fired, and what didn't

In "Between Pages 1-5" (`$57ffe` = player = side 1; enemy = side 2 with two
sub-leaders in `$4e514`), across a **250M-step** watched resume (~1000 sim
ticks) the only writes to `$58016`..`$58033` were `$6a3a`'s per-tick clear of
`byte1`/`word2`. **No command slot's `byte4` ever reached 4; no order was ever
issued.** The lone enemy captain sat on its standing patrol objective the whole
time. Mission 1 is a tutorial and its enemy AI is near-dormant.

The `$6564` path above was read statically and then **confirmed by force**:
poking `$58020` (slot 1 `byte4`) = 4, `$6522` took `$6564` → primary-slot
`$661a` → `$68fe` (picked the nearer enemy leader) → `$68ee` (in budget) →
`$67ee`/`$6822`, which wrote `{type $0c, cell $1d3e}` into the command buffer.
The next tick `$6a3a` → `$6ac6` → `$6b38` → `$6c4a` → `$3154` → `$4b80` set the
group's execution sub-record to state 8 and stamped the group lead into mode
`$10` with the target cell's centre world coordinates. The pipeline works end to
end; mission 1's enemy just never trips the "needs a new order" state on its
own.

Snapshots: `scratchpad/pm71_run1.snap` (settled, ~677M), `pm71_run2.snap`
(~927M, still quiet), `pm71_slot4.snap` (slot 1 forced to `byte4`=4, PC at
`$6522`). 72nd-pass traces: `scratchpad/pm72_sched.evt` (3M, cadence),
`scratchpad/pm72_fight2.evt` (40M from `pm71_slot4`, the forced fight).

## Mission / world setup (73rd pass)

The briefing OK click (`$b814`, README) copies the saved game-state block
`$584c4..` over `$580a0..$58367` (`$b860`; it includes the world parameters at
`$58146`) and calls **`$13b9a`**, the world-build dispatcher:

```
$13b9a  ff9c := $15 ; jsr $fe04 (zoom index 4)      ; render geometry
        $51536 := $12                               ; group-order table live count
        $57fd0 := (byte[$58146] & 3) * 2            ; tile-set / mode-$7c gate ($1abaa rotates it later)
        if ($580a0 != 0)       jsr $10d1e ; jsr $2266 / $ac20  ; re-roll the parameters from the seed
        elif ($58148 < $100)   jsr $df52(7) / $10a46 / $10410  ; fixed map from resource 7
        else                   jsr $ffa6 / $2266 / $ac20       ; stored parameters (mission 1)
        jsr $1073c / $10058 / $4672                   ; terrain init + scatter
        jsr $2984 / $238c / $2906                    ; objective-slot + assessment seeding
        ...
        $57fee := 1 ; $57ff0 := 1 ; ff9a := $fff0    ; speed = normal, camera reset
        rts   ($13ce6)
```

For mission 1 the saved block holds `$580a0 = 0` and the parameters `1e19 0750
0008 0023 0031 0004` (at `$5856a` in `pm67_ok_pre`; a write-watch on
`$58146` sees no write during `$13b9a`), so `$10d1e` is skipped and the map is
built from those stored parameters. `$580a0 = $45e` is the briefing *preview*:
`$b2dc` picks a land index `k` from entropy, sets `$580a0 = k*$b + $3fb` and
`$5809c = k*$96 + $672`, and rolls a preview through `$b394 → $10d1e`
(`$45e` is `k = 9`). That preview is a different map from the one the OK path
builds.

`$10d1e` is **not** a byte-script parser: it **reseeds the RNG from `$580a0`**
(`$10d22: move.l $580a0,$2df84`) and fills the parameter block from `$12c9a`
draws. `$12c9a` is a **32-bit LCG** (`state = state * $bb40e62d + …`, seed
`$bc614e` when zero), so a seeded map is a **deterministic function of
`$580a0`** (and `$5809c`). Poking both at `$13b9a` builds any of the 144 lands
for real (README "Driving a later land").

| addr | filled with (`$10d1e`, 97th disasm) | meaning |
|------|-------------|---------|
| `$58146` | 1st `$12c9a` draw | world RNG seed; `byte[$58146] & 3` picks the initial `$57fd0` |
| `$58148` | `$5809c` override (else `(2nd draw & $7fff) + $1500`) | map size; `< $2000` ⇒ "small" preset (`D1 := $a`, `D2 := 3`); `$b85a` clears `$5809c` before the OK path's block copy (which starts at `$580a0`, so it stays 0); an unseeded build uses the stored `$58148` from the copied block |
| `$5814a` | `(draw & 7) + (small ? $a : 2)` | lord count |
| `$5814c` / `$5814e` | `draw & $3f` / `draw & $7f` | seed cell coords |
| `$58150` | `(draw & 3) + 2 + (small ? $a : 2)` | settlement count knob |
| `$58152…` | a stream of 4-byte `{x, y, id, kind}` placement records built by `$111e2` + a loop | the "unit list" |

`$2266` then consumes the `$58152` stream: a record with `kind == $10` is a
**lord** — it writes `id` into `$58016[id].commander` and, if the slot isn't
already armed, sets `slot_state := 4`. **This is where the enemy command slots
are armed at mission start** (and why a fresh procedural mission's enemy has a
slot ready but — per "What actually fired" — its objective fields never
re-qualify `$661a` after the opening move). Records with `kind < $10` seed the
player start position; `kind == 0` ends the stream. `$2266` then appends
procedurally-placed settlements (`kind $10`, random cells `rand%$30+8`,
`rand%$70+8`).

Neither branch is a byte-script mission, and there is no mission-file grammar:
a campaign land is a stored parameter block from a fixed 195-entry table
(mission 1 is entry 0), and a random land re-rolls the parameters from a seed.
None of the 195 table entries has `$58148 < $100` (their range is
`$400..$7f20`; 67 are below `$2000`, the "small" preset), so the campaign never
takes the fixed-map `$df52(7)` branch; that branch is unreached by every route
found (campaign, random land, briefing preview).

## How a land ends (122nd pass)

A land ends only through command **`$2e`** in the local side's command slot
(`[$58034]`, the `$58016` slot of side `$57ffe`). The order executor
`$6a3a` → `$6b38` dispatches `$2e` to `$6e10`: if the slot's state byte
`4(slot)` is 2 it calls `$d2c8` at once; otherwise it calls `$71ae` (re-arms
every command slot: state 2 or 6 → 2, any other non-zero → 4) and then `$d2c8`
when the slot belongs to the local side. Two writers post `$2e`:

- **Retire**: the in-game options button that the panel handler `$7202`
  decodes as `D3 == $11` (`$77c2`: `move.b #$2e,1(slot)`).
- **The captain's group dissolves**: `$2776`, run on the side's exec
  sub-record 0 (the captain's group), clears its owner-side word
  `-48(sub)` = `word[$51538 + side*$13c + 28]`; the next tick `$d23a` sees it
  `<= 0`, clears `$57fce` and posts `$2e`.

`$d2c8` is the verdict:

```c
void end_of_land_d2c8(void) {
    if (ratio_57fce == 4) {                         // (2*mine + enemy/4)/enemy clamped 0..4
        victory_screen_1a4da();                     // resource $f; the last land ($580a4 == $c2, mode 4) -> $1a486
        conquered_3f2a0[land_580a4] = 1;            // guarded by tst.w $1120e, which reads the code word $48e7: always taken
    } else {
        defeat_screen_1a5b2();                      // resource $e
    }
    main_menu_13de8();                              // Start New Conquest / Continue Conquest / Play Random Land / Load Data Disk
    menu_dispatch_13e8e();                          // on $2df6e
    rebuild_world_13d1a();                          // -> $13b9a
}
```

With `enemy = Σ other sides' $57fba.word0 + 1` and `mine` the local side's
`word0`, ratio 4 needs `2*mine + enemy/4 >= 4*enemy`, i.e. about
`mine >= 15/8 * enemy`. Nothing ends a land on a winning ratio by itself: the
player must retire while the scale is full. A land is lost either by retiring
early or by losing the captain.

Evidence (`scratchpad/pm122/end/`, from `pm121/run/k25_s4.snap`, ratio 0):
posting `$2e` (the retire button's own write) reaches `$d2c8` in 136,275 steps
and `$1a5b2` 790 steps later: "You have been defeated" (`lose_screen.png`),
then the main menu at 28.4M steps (`lose_after.png`). The same state with
`$57fce` poked to 4 at `$d2c8` takes `$1a4da`: "After a glorious victory you
must go on to conquer the whole world" (`win_screen.png`), and
`$3f2a0[0]` goes 0 → 1.

**A natural defeat.** Land 60 run on from `pm121/run/k60_s4.snap` (where the
player's force total is already 0) dissolves the player's captain group
through `$2776` at step 94,725,510 (`A3 = $516c0`, side 1's sub-record 0, no
members left; `scratchpad/pm122/agents/dissolve/nat2/k60_x1.snap`). With no
input from there, `$d23a` posts `$2e` (+605,283 steps), `$6e10` +780,340,
`$d2c8` +780,343 with `word[$51690] = 0` and `$57fce = 0`, and the defeat
screen `$1a5b2` +781,229 (`scratchpad/pm122/end/k60_natloss.png`). The other
three run lands did not end in 300M steps.
**A natural victory (123rd).** Mission 1 (campaign land 0; player side 1
with 26 men in the field, side 2 with two lords of 10 garrison men each, ratio
2), played with clicks only (`reversing/powermonger/py/drive_win.sh`, from
`scratchpad/pm67_ok_pre.snap` through the briefing OK and 30M steps of
settling). Sword icon, then the minimap at enemy lord 0's cell (22,45): `$131c4`
writes `$0c` / (22,45) into the local slot `$5801c`, and the executor clears
it at `$6b46` on the next tick. Over the next 25M steps `$56a6` (engage) fires
8 times and lord 0's `troops_field` falls 10 → 7. In the next 25M, one
`$550e` defection moves lord 0 to side 1 (loyalty 608 → 300), and the totals
become 31 : 10, ratio 4. Options icon → GAME → RETIRE: `$d2c8` takes the
victory branch, `$d304` writes `$3f2a0[0] := 1`, and the main menu follows.
Continue Conquest (`$1120e` in 216,752 steps), then land 1 on the map:
`$11414` with `$580a4 = 1`, and land 1 builds and runs at `$f898`.
Control, the same settled state with no order for 50M steps: `$56a6`,
`$1623c` and `$550e` 0 hits, both lords stay on side 2 at loyalty 608, and the
ratio stays at 2. So the attack caused the defection (both runs are
deterministic, one run each). Loyalty 608 is already over the 600 threshold
at the start and no defection happens without the attack, so the threshold
alone does not trigger `$550e` (inferred: it is reached from the conquest arm
`$539a` of mode `$2c`, open item). Snapshots `scratchpad/pm123/win/`.

*Rule: Proven from the code. Defeat observed both ways (retire and the natural
captain loss); victory observed naturally (mission 1, clicks only).*

## Diplomacy (123rd pass)

An alliance is a pair of peace bits: bit `t` of `+6` in side `s`'s `$580a6`
block means `s` is at peace with `t`. Outside the bulk copies of the whole
block (`$1140e` campaign pick, `$b86c`/`$716c` restore, `$10d1e` random land)
the complete writer set is `$2458` (world build: the side's own bit), `$34a8`
(two `bset`, alliance forged), `$4c2a` (`$4c64`/`$4c7a`, two `bclr`, alliance
broken) and `$311a` (the relation bytes). Found by searching the image for
every absolute longword in `$580a0..$58145` (74 sites, the same set as the
listing); the table with each site is in `scratchpad/pm123/diplo/` (the
subagent report, saved as `REPORT.md`).

**Proposing.** Order `$1e` (icon `$1e`, then a settlement): `$3154` (D3 = `$e`,
D4 = `$76`, D5 = −commander) takes a settlement that is not the proposer's,
stores its lord in `24(group)`, and walks the group's lead to it (mode `$10`,
prev-mode `$76`). On arrival mode `$76` runs `$15754` → `$33b0`:

```c
void envoy_arrives_33b0(group *g, leader *L) {
    if (L->side == local) open_panel_1a(g);          // $c706: the player decides (YES $2a / NO $32)
    int tribute = 0;
    for (i = 0; i < 8; i++) { tribute += g->supply_acc[i] * W_3498[i]; g->supply_acc[i] = 0; }
                                                     // W = {4,4,8,4,6,2,20,40}, per carried goods type
    slot *s = &cmd_slot[L->side];
    if (s->state == 4 || s->state == 0) {            // an AI (or unlinked) side
        int v = (s8)assess[L->side].rel_byte[16 + g->side] + tribute - 2;
        if (v >= 0) {                                // accept
            if (s->state == 0) accept_alliance_34a8(L->side, g);
            else { s->order = 0x2a; s->param = g - $51538; }   // $3458; the executor runs $34a8
        } else if (g->side == local) refusal_message_cada(L->side);
    }
    free_group_35f4(g);                              // the envoy group is always disbanded
}
void accept_alliance_34a8(int a, group *g) {         // order $2a
    bset(g->side, &assess[a].peace_bits);  bset(a, &assess[g->side].peace_bits);
    if (g->side == local || a == local) message_c9f8();   // "An Alliance has been forged ..."
}
```

Checked (`scratchpad/pm123/diplo/`, from `offer_a_end.snap`, the player's
envoy dispatched with `w 5801c 011e2d15` toward side 3's settlement (45,21) on
land 60, its lead's mode then set to `$76`): with no goods carried, `v = −2`,
`$cada` and `$35f4` run once and nothing is written; with one unit of goods 0,
`v = 2`, `$3458` posts `$2a` into side 3's slot, and the executor's `$34a8`
writes `$5810c := $0a` and `$580cc := $0a` (sides 3 and 1 allied), then
`$c9f8`. Re-run this session: byte-identical `t2_end.snap`. The unforced walk
never arrived: after 180M steps the envoy touched side 3's men first, which
breaks the approach (below).

**What an alliance changes.** Only the two readers of `+6`:

- `$3154`'s friendly-target test (`$3172`/`$31a6`). Order `$06` (recruit,
  group state 2) on side 3's settlement (45,21): before the alliance
  `$31a6` → `$31c8` → fallback `$38ce` (refused, 1/1); after it `$31a6` →
  `$31b2` → `$31cc` (accepted, 1/1). Orders `$06` and `$10` accept an ally's
  settlements like one's own.
- The pointer test `$1394c`, run while a command is armed (`$57fd4` = `$06`,
  `$10`, `$1e`): `$139da`/`$13a3c` accept a settlement whose owner's bit is set,
  `$13b1e` (for `$1e`) one whose bit is clear. These three are the addresses the
  122nd pass listed as "per-tick writers": they are reads.

Combat does not look at `+6`. Any contact between two sides' units runs
`$4bc8` → `$4c2a`, which clears both peace bits, calls `$c5ee` ("The alliance
between ... is broken") when the player is one of them, and applies a −8
relation delta both ways through `$311a`. Replaying the envoy run with the
1 ↔ 3 bits set, the first contact did exactly that (`$4c64`, `$4c7a`, `$c5ee`
1 hit each). An alliance with no contact persists (60M steps, bits unchanged).

**Who proposes.** Order `$1e` is posted only by the UI (`$131c4`, `$1365e`);
the AI's order writer `$6822` posts only `$02/$04/$06/$08/$0c/$22`. In 150M
natural steps over three lands `$6d32` and `$15754` had 0 hits, and
`$34a8`/`$33b0`/`$c706` never ran. So only the player offers alliances, and
panel `$1a` (an envoy arriving at the player) needs a linked opponent
(inferred; its branch is read statically only).

**Relations and their bugs.** The campaign table stores side `s`'s attitude to
side `t` at `+15+t` (3 non-zero self-entries under that layout, 77 under
`+16+t`; 96 of 195 lands have a non-zero pair, values mostly −128, −2, +16,
+112; no land pre-sets `+6`). Three code paths disagree with it:

1. `$311a` reads `+15+t` **unsigned** and writes `+16+t`: a stored negative
   reads as ≥ 128 and clamps to +100, and for `t = 4` the write lands on `+20`,
   the side's starting equipment (13 of 26 writes on land 60's first 50M
   steps).
2. `$33b0` reads `+16+proposer`, i.e. the designed attitude toward side
   proposer + 1 (inferred intent: `+15+proposer`).
3. `$68fe` reads byte 15 of `block[me + t]` instead of `+15+t` of `block[me]`:
   the low byte of word `+14` (2, weight 0) or bytes past the table
   (`$58155` = 3, `$58175` = 2, `$58195` = `$10`); 13/13 reads at `$6968` were
   those values. The relation never reaches targeting.

Also: `$c5ee` clobbers D2, so when an alliance with the player breaks, the two
−8 deltas go to `$580bd` and `$57d97` (bp at `$311a`: D2 = `$e7`). Natural
writes to the block in 50M-step runs from a land's start: land 60, `$4c64`
13 and `$314a` 26; land 25, 78 and 156 (77 of the 78 contacts between sides 2
and 3); all contact-driven.

## The campaign (122nd pass)

The main menu's four buttons set `$2df6e` (`$78d2..$7908`): 2 Start New
Conquest, 4 Continue Conquest, 6 Play Random Land, 8 Load Data Disk. `$13e8e`
dispatches it:

- **2 / 4 → the conquest map `$1120e`**. Start New Conquest first asks for
  confirmation (`$c48e`) when any land is already conquered. Continue Conquest
  first calls `$aeac` (inferred: the load-campaign dialog) when the protection
  flag `$14e4e` is not `$2c`, and goes straight to the map when it is.
- **6 → a random land** (`$13ece`): `$580a0 := video counter + mouse + RNG`,
  OR `$71010101`, so `$13b9a` re-rolls it through `$10d1e`.

**The conquest map** is a 13 × 15 grid of 195 lands; `byte[$3f2a0 + land]` is
the campaign state (0 = free, > 0 = conquered, < 0 = not selectable). A cell
is 24 × 40 px (`$11252`: `col = (x-8)/24`, `row = (y+scroll-8)/40`,
`land = row*13 + col`, with the pointer in the cell's left 16 / top 32 px).
The pointer may pick a free land when it is land 0 or when one of its four
neighbours (N/S/W/E) is conquered (`$112ba..$112ec`). The pick (`$113a8`) sets
`$580a4 := land`, loads resource `$b` over `$3f364..` (it reuses the map
bitmap's buffer), and copies **`$14c` bytes from `$3f428 + land*$14c` over
`$580a6..$581f1`**: the per-side assessment blocks and the world parameters
at `$58146`. `$13ec6` clears `$580a0`, so `$13b9a` takes the stored-parameter
branch (`$ffa6`/`$2266`/`$ac20`) and builds that land exactly.

Evidence (`scratchpad/pm122/end/`): after the forced win, Continue Conquest
reaches `$1120e` in 271,702 steps (`map_cont.png`). Clicking land 1 runs
`$113a8`, `$10768`, `$13ec6`, `$13d1a`, `$13b9a`, `$ffa6`, `$2266`, `$ac20`,
`$1073c`, `$2984`, `$238c`, `$2906`, `$13ce6` once each, not `$10d1e`, and the
iso view starts at `$f898` (`land1_built.png`). At `$11414` the live
`$580a6..$581f1` equals table entry 1 byte for byte, and the built land's
`$58146` params are entry 1's `2310 0400 0007 0010 0060 0003`. **Table
entry 0 is mission 1's `1e19 0750 0008 0023 0031 0004`**: mission 1 is
campaign land 0. Clicking land 5 (not adjacent to a conquered land) with land 0
conquered sets `$1141a = 5` but never reaches `$113a8`.

**What the campaign keeps between lands**: only the conquest map
`$3f2a0..$3f362`. The land parameters are reloaded from the table on every
pick, and the stored block `$584c4..` is identical before the win and after
land 1 is built. The options panel's save/load buttons move the same 195 bytes:
`D3 == $47` copies `$3f2a0` → `$3f768` and calls `$e288` (→ `$1bdfe`);
`D3 == $17` ORs `$3f768` into `$3f2a0` after `$e29c` (→ `$1bd70`). That these
are the disk save and load is inferred from the call shape, not traced.
`$b2dc`'s entropy pick of one of 144 lands (`k*$b + $3fb`) belongs to the
briefing preview and Play Random Land; it has no part in the campaign.

**The protection check.** The briefing dialog asks a manual-lookup question
("Between Pages 17-22 / How many People in this land?"). Its OK handler `$b814`
parses the answer (`$b940`), then in the original code
`$b842: sub.w 0(A0,D1.w),D0` subtracts the stored answer `$5878e[$57ff8]`
(`$57ff8` a random 0/1, set at `$b430`). A difference of 0 stores
`$14e4e := $2c` and copies `$584c4..` over `$580a0..` (`$b860`); anything else
shows "Your answer is wrong. You have been deemed unworthy to rule this fair
land. Demo mode now activated." (`$b9ac`). `$14e4e` is a long in the code
segment, cleared by the land build `$b436`, and it gates the whole AI block of
the tick (`$1303a`: `tst.l 46($14e20)`, which skips `$127e6`/`$6522`/`$d322`/`$3e06`)
as well as Save (`$7774`) and Continue Conquest (`$13ea6`). The Replicants
crack replaces the subtraction with `moveq #0,D0 / nop`, but the patch is
present only in the campaign route's image (`pm67_ok_pre.snap`). After Play
Random Land (`pm121/random_land2.snap`) `$b842` still holds the original
`sub.w`, so the "Please Wait For The Protection Check" dialog (`$bee0`, from
the start-up path `$12fd2`) is followed by the real question, and the land runs
with no AI (`$6522` 0 hits in 50M steps; `scratchpad/pm122/prot/`).
Answering OK without setting the digit wheels breaks at `$b846` with
`D0 = $feee` (0 − 274) and gives the demo-mode message. Poking `$14e4e := $2c`
restores the AI block (`$6522` and `$d322` 164 hits in 30M). Where the crack
applies its patch was not traced.

## What `$1abaa` actually is — seasons and weather, not economy

`$1abaa` (`$130b0` in the tick) was a candidate for the economy/growth engine.
It is not. Each tick it steps the 13-bit LCG `$57ff6` 16 times, copying one
pixel of the season's grass patterns into the live dither slots per step
(`port/SPEC.md` §4 "Seasons"), and runs the weather (`$1ad2a`: draws rain or snow
with `$1a856` and counts the spell `$4bb42`/`$4bb44` down, or starts one via
`$1ad74`; SPEC §7 "Weather"). **Once per LCG wrap** (`$1ac3c`, when `$57ff6`
reaches 0):
- pokes **one** random `$4d252` record — if its `byte7 == $d` it becomes
  `$e + (byte10 & 3)` (wildlife / ambient nudge);
- **rotates `$57fd0`** — `$57fd0 = ($57fd0 + 2) & 6`, cycling {0,2,4,6}
  (`$1ac5e..$1ac6a`, raw-verified 97th). `$57fd0` is the season *and* the
  mode-`$7c` settlement-heartbeat gate (economy.md §3a), so this rotation is
  what makes the heartbeat + loyalty/revolt system **transiently active in
  mission 1** despite its seed giving `$57fd0 = 4` at world-build. Observed
  rate: ~1 rotation per ~110M steps;
- clears `$57fec` / `$57ff6` and ends any weather (`$4bb42`/`$4bb44` := 0).

No population, food or invention maths anywhere in it.

## The AI as modern pseudocode (73rd pass)

Everything above, decoupled from the 68000 and from the 2.6 Hz tick, as one
loop. This is the whole autonomous AI — there is nothing else.

```python
# ---- once per simulation tick (~2.6 Hz on the ST; compute-bound) --------
def sim_tick(world):
    for side in world.sides:                       # $6522: the "commander AI"
        slot = world.cmd_buffer[side]
        if slot.state != READY:                    # 4
            continue
        group = world.groups[slot.commander]
        if group.queued_order:                     # player click / mission script
            slot.emit(group.queued_order); group.queued_order = None
            continue
        # --- synthesise one order ($6564) ---
        for i, obj in enumerate(group.objectives): # exactly 6 slots
            if not obj.active or obj.link != 0:
                continue
            # 1. scripted campaign order, if this mission has one ($6762)
            if obj.state == PATROL and world.clock >= obj.wait_at + 20:
                if world.campaign_order.id == obj.camp_id:
                    obj.substate = world.campaign_order.sub or (world.tick & 3) + 2
                    slot.emit(BESIEGE, obj.leader_cell); break
            # 2. strong enough to storm a keep ($69b4)
            if obj.force >= 22:
                tgt = nearest_enemy_leader(obj, weight=lambda L: L.troops)
                if tgt: slot.emit(BESIEGE, tgt.cell); break     # -> group state 3
            # 3. escort the objective ahead of me, if it's a support slot
            if i > 0 and group.objectives[i-1].state in (SUPPORT, CAMP4):
                slot.emit(MARCH, obj.escort_target.cell); break
            # 4. primary slot: march at the nearest enemy leader ($661a/$68fe/$68ee)
            if i == 0 and obj.force - 4 > 0:
                tgt = nearest_enemy_leader(obj,
                        weight=lambda L: assessment[side][L.side].out >> 2)
                if tgt:
                    score = (dist(obj, tgt) // 2) * (tgt.troops // 8 + 1)   # $68ee
                    if score <= obj.budget:                                  # patience
                        group.state = 4
                        slot.emit(MARCH, tgt.cell); break        # -> group state 8

    for side in world.sides:                       # $6a3a: order executor
        slot = world.cmd_buffer[side]
        handler = ORDER_TABLE[slot.order_type]     # 26-entry jump table
        handler(world.groups[slot.commander], slot.param)   # e.g. commit_group_target
        slot.order_type = NONE; slot.param = 0     # consumed

    # $d322 + $3e06: rebuild per-side force totals, decay objective budgets
    force = [0]*5
    for L in world.leaders:
        force[L.side] += L.troops_field + L.troops_reserve
    for group in world.groups:
        for obj in group.objectives:
            if not obj.active: continue
            force[group.side] += obj.force
            if world.tick % assessment[group.side].decay_period == 0:
                obj.budget -= obj.force // 8 + 1               # big army -> impatient
                if obj.budget < 0: obj.expire()                # re-pick a patrol waypoint

    # $d23a: UI-only mood ratio (the AI never reads it back)
    enemy = sum(force[s] for s in other_sides) + 1
    ui.mood = clamp(0, 4, (2*force[me] + enemy//4) // enemy)

    # $14b62: the entity FSM  (ai.md) -- one tick of every active object
    for obj in world.objects:
        if not obj.active: continue
        MODE_TABLE[obj.mode](obj)                  # 75-entry jump table; see ai.md FSM

    projectiles_update(world)                      # $596a
```

`commit_group_target` (the `MARCH`/`$0c` handler, via `$3154` → `$4b80`):

```python
def commit_group_target(group, packed_cell):
    x, y = packed_cell & 0x3f, (packed_cell >> 6) & 0x7f
    entity = world.cell_buckets[y*64 + x]          # who's standing there
    if sign(group.commander_id) < 0 and entity and entity.side == abs(...):
        pass                                       # foe: attack it
    group.exec_state = 8
    lead = group.lead_object
    lead.prev_mode, lead.mode = 0x30, 0x10         # advance-to-target
    lead.target = (x*256 + 128, y*256 + 128)       # cell centre, world coords
    # from here the entity FSM walks the lead there; followers (mode $68) are
    # stamped from the lead; bucket proximity flips men to melee (mode $32).
```

Combat, in full (`ai.md` + "Combat" above):

```python
def melee_tick(attacker):                          # entity mode $32 / $1533c
    T = attacker.target
    if T.dead: attacker.mode = FIGHT_HOLD; return
    dmg = (min(attacker.msg_code, 6) >> 1) + 1     # 1..4 per tick
    T.morale -= dmg
    if T.morale <= 0:                              # $5590
        roll = attacker.group.discipline - 2       # field_60 - 2
        kill = (roll == 0) or (roll not in (0,2) and (world.tick + attacker.phase) & 2 == 0)
        if attacker.target.encircled: kill = True
        if kill: T.to_corpse(decay=160)
        else:    T.rout()                          # scattered, survives
    # slow second channel, $5c80: survivability[flags] - (age-60)*4 < 0 -> removed
```

## What's crude, and what a modern version changes

Read against a contemporary RTS AI, PM's autonomous layer is deliberately thin —
it fits the "you are the influence, not the general" design, but several parts
are limitations rather than choices:

1. **Targeting is nearest-enemy-leader, full stop.** `$68fe` picks the smallest
   `max(|dx|,|dy|)` (weighted by a single relationship byte); `$68ee` scores it
   only on raw distance × a coarse troop bucket. No terrain cost, no
   choke-point awareness, no "is this the *valuable* target", no coordination
   between a side's own groups. A modern version would run an **influence /
   threat map** and score targets on expected gain vs. expected loss, and let a
   side's groups deconflict (one besieges, one screens).

2. **No economy in the decision loop at all.** The AI never reasons about
   population, food, invention or building — those orders can only come from a
   scripted campaign hook (`$67d0`), which mission 1 doesn't use. A modern
   version needs a real economic planner: grow settlements, tech up, *then*
   attack, with the military goal chosen to serve the economic one.

3. **The "patience budget" is the only pacing knob.** `obj.budget` drained by
   `force/8 + 1` per decay period is a neat trick — big armies commit fast,
   small ones dither — but it's a scalar with no situational input. Replace with
   a proper utility model: commit when `P(win) * value > opportunity_cost`.

4. **2.6 Hz, and compute-bound.** The whole sim — every entity, both renderers —
   runs in one thread at whatever rate a frame builds. Decisions land ~2.5 s
   apart and combat resolves in ~1–4 morale/tick. A modern port decouples the
   sim tick from the render, runs the AI on its own budget, and can afford
   per-frame steering while keeping the coarse "issue an order every few
   seconds" cadence that gives PM its feel.

5. **Deterministic tick-count "RNG".** `$57fec` is just the low bits of the tick
   counter (`ai.md`), so the AI and combat replay identically from a save.
   Fine for the kill/rout roll's *flavour*, but it means no genuine uncertainty
   — a human learns the exact outcome of a given engagement. Keep the trick for
   cosmetic jitter; use a real seeded PRNG for anything the player can exploit.

6. **Rout, not attrition, decides fights — and rout is pinned.** `group.field_60
   == 4` in mission 1 forces every morale-kill into a rout. Whether that's
   tuning or a bug in the procedural generator, the effect is that field combat
   almost never kills; territory changes hands by **capture** (`$1d70`) while
   armies just get scattered and re-form. A modern version would make the
   discipline value depend on training / leadership / recent losses so that
   fights have consequences.

## Open threads

- **Economy / population / invention — not started.** Confirmed *not* in the
  per-tick path (`$1abaa` is sound, `$3e06` is budget-decay + morale-UI,
  `$d322` is force-totalling). Initial population/settlement counts come from
  the `$10d1e`/`$2266` procedural generator. Growth and invention are either
  event-driven (a revolt, `$550e`, moves a lord and his settlements; economy.md §3) or live in the setup-time
  cluster `$2984`/`$238c`/`$2906`/`$ac20` which may also run periodically —
  none of that code is mapped. This is the largest remaining subsystem.
- **The AI on a live enemy (122nd).** All 25 natural `$661a` primary
  decisions in the four 200M-step runs (lands 0/5/25/60: 8/7/4/6) were
  captured at `$662a`/`$6632` (`scratchpad/pm122/dec/`, `parse.py`). `$68fe`
  found a target every time, and `$68ee`'s cost (4-66) was always far inside
  the objective budget `112(A1)` (24,218-24,671, i.e. the `$5fff` seed of
  `$26c4` barely decayed), so every decision issued the attack order
  (`136(A1) := 4`, `$67ee(12)`); the over-budget fallback `$69b4(6)` and the
  no-target path `$69b4(8)` never ran. Targets were leaders of every other
  side, the player's (side 1) in 6 of 25, usually with a small `troops_field`
  (0-18). The budget test does not bind at these values.
- **Combat — mechanism closed** (73rd, see "Combat" + `ai.md`). The `$5590` kill
  branch runs naturally on later lands (121st). Remainder: the `$5c80`/`$5bd2`
  wear path (never fired in 800M later-land steps). Projectile type is byte6:
  `$28` (40, an arrow, from a bow) is common; `$12` (18) never appeared.
- **Land setup**: there is no mission-file grammar (campaign lands are the
  195-entry `$3f428` table, "The campaign" above). Still unreached: the
  fixed-map branch (`$58148 < $100` → `$df52(7)`), which no campaign entry
  uses (possibly Load Data Disk), and the per-objective `obj_camp_id` fields,
  which only the dead `$67d0` hook reads.
- Diplomacy ("Diplomacy" above): an alliance offered naturally by clicks
  (icon `$1e` on a settlement, carrying goods, envoy reaching the lord without
  contact) is not yet observed; the panel-`$1a` branch (an envoy arriving at the
  player) is static only.
- `$3c08` (rout / besiege-fail group restructure; order `$0a`, the HOME icon)
  and `$39d4` (orders `$12`/`$18`, D7 = 1/2) — first-look only.
- The player's icon orders whose handlers are not decoded (`$02` `$3888`,
  `$04` `$1c18`, `$06` `$38ce`, `$10` `$6128`, `$14` `$1cc4`, `$16` `$35a0`,
  `$1a` `$390e`, `$20` `$1d36`): click each on `pm123/win/m1_s0.snap` with
  `py/clicks.py`, follow the group with `watch`/`hits`, and name them.
