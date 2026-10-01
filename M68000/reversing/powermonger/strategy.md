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
$13040  jsr $127e6   ; sound-event dispatcher (original _do_soun...): plays the 2 highest-priority pending sounds
$13046  jsr $6522    ; << the commander AI (order pipeline)
$1304c  jsr $d322    ; per-side troop totals -> $57fba
$13052  jsr $3e06    ; flag-health UI + the armies eat (food decay) + $57fba group term
$13058  clr.w $12f58
 ...set up $e3e2 / $e0d4 pointers...
$13074  subi.w #$1,$57ff0 ; bne $130b0   ; tick-subdivision gate (see below)
$1307e  move.w $57fee,$57ff0             ; reload the subdivision counter
$13088  move.w #$1,$12f58
$13090  jsr $1870    ; per-frame VBL sync / present
$13096  jsr $12ce0   ; offscreen buffer -> shifter (double-buffer flush)
$1309c  tst.w $57ff2 ; bne $130c8        ; paused -> skip the two heavy renderers
$130a4  jsr $178ae   ; HUD group bars (food 112, men 52, the lead's health 45; callcap: 138 bytes written)
$130aa  jsr $f898    ; terrain raster
$130b0  jsr $1abaa   ; _seasons: dissolve the live tileset 16 px per call ($57ff6 LCG), $57fec++; weather ($1ad2a)
$130b6  jsr $17878   ; compass (callcap: 51 bytes written)
$130bc  jsr $165b2   ; water / terrain animation for the selected group
$130c2  jsr $14b62   ; << the entity iterator (ai.md)
$130c8  jsr $6a3a    ; << order executor: consume $58016, drive group state + lead mode
$130ce  jsr $7a56    ; sprite / HUD compositor
$130d4  $ff9a += $12f56 ; ...andi #$3f... clr $12f56 when it wraps  ; AUTO-ROTATE hook
$130f6  jsr $d23a    ; $57fba -> $57fce force ratio (0..4; 4 = victory at $d2c8)
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
| 4 | byte | **slot state** `0/2/4/6/8/$0a`. `$6a3a` dispatches on it each tick through the word table at `$6a80` (state 0 no work, 2 and 4 execute the order locally, 6 and 8 are the serial-link states below, `$0a` is a bare `rts`); `$6522` issues a new order only when it is `4` |

`$6a3a` walks slots 1..4 only (`$5801c..$58033`); slot 0 (`$58016`) is never dispatched.

**Serial-link states (6 and 8).** State 2 is a local human, state 4 an AI side. State 6 is a human whose
orders are mirrored to a peer: `$6a9e` calls `$1c390` to write the slot's first 4 bytes (commander, order,
parameter) to the MFP USART data register (`$fffffa2f`), then executes the order. State 8 is the remote
human: `$6ab2` calls `$1c340` to read 4 bytes from the receive ring buffer `$58368` into the slot
(read index word `$58368`, write index word `$5836a` advanced by the receive interrupt, wrap limit word `$58372`, baud code `$5836e` = 1200 here, data from `$58374`), then executes them. Both loops spin
until the byte moves, so a slot in state 6 or 8 with no peer stops the whole game. The aborts differ:
the receive loop (`$1c34e`) leaves on ESC alone (`$2de6d`); the send loop (`$1c39e`) needs ESC plus a
non-zero `$2dea2` or `$2de96`, the key-array cells of the right and left shift scancodes `$36`/`$2a`.
The key ISR (`$1962`) never stores those two scancodes in the array (it only sets and clears the shift
flag `$2df8a` and returns), so the send-side abort cannot fire from the keyboard. Abort calls the
link teardown `$71ae`: it flushes the receive ring (`$1c328` clears both indices), calls `$c3f6` (not read) and demotes each slot
(0 stays 0, 2 stays 2, 6 becomes 2, everything else including 8 becomes 4), so a remote human falls
back to an AI side and the game continues. Proven on `pm123/win/m1_s0.snap` with the slot states
poked (`scratchpad/pm132/`, "Serial-link roles" in "Hidden features audit"): the state-6 send loop
entered once from `$6a9e` and spun 571,668 times in 3M steps; the state-8 receive loop spun 122,257
times in 1M steps, ESC reached `$71ae` 41 steps later (1/1), slot 2 went 8 to 4 and `$6a3a` ran 11 more
times in the next 3M steps. The spin in state 6 is the emulator's MFP never setting the transmitter-empty
bit that `btst #7,44(A1)` (`$fffffa2d`) polls; there is no peer to test the protocol against.

### `$51538` — group-order table

5 records of `$13c` (316) bytes, **one per side**. Header: long +0 =
pending-order flag (player/script channel), byte +1 = queued type, word +2 =
queued param. The rest is ~15 parallel **6-word arrays**, one word per
**group** (captain) of the side: group `k` (0..5) is the word at `base + n + 2k`,
and the group offset `D2` that the executor, the entity modes (`42(obj)`) and
`$57fd2` use is `side*$13c + $4c + 2k`, so a field at `x(A3)` of a group is the
array at `base + $4c + x`. The captain panel (`$9090`: `A3 - $51538` divided by
`$13c` gives side and `2k`) prints four of these arrays as Food, Troops and
aggression. Passes before the 124th called the six entries "objective slots";
they are the side's six captains' groups ("What each order does"). The
`$6564` AI loop sets `A1 = base + D7` with `D7 = 10, 8, ..., 0`, so `n(A1)` is
group `k = D7/2`'s word, walked from group 5 down to group 0 (the captain's):

| `n(A1)` | array span | meaning |
|---------|-----------|---------|
| `4(A1)`   | +4..+14   | slot-index / link, written back by `$6822` |
| `28(A1)`  | +28..+38  | the group's **owner side** (group `-48`; `<= 0`: no group, skip) |
| `52(A1)`  | +52..+62  | the group's **men** (group `-24`, captain panel "Troops") |
| `76(A1)`  | +76..+86  | the group **state** (group `0`: `$6` camp, `$9`, `$d` support, ...) |
| `112(A1)` | +112..+122| the group's **food** (group `36`, captain panel "Food"; eaten by `$3e06`, AI groups seeded `$5fff`) |
| `136(A1)` | +136..+146| the group's **posture** (group `60`: 2 Aggressive, 3 Neutral, 4 Passive; the second half of the captain panel's "Aggression" line; `$90fe`) |
| `148(A1)` | +148..+158| the group's **aggression** rank (group `72`: 0 PowerMonger .. 7 Wimp, the first half of that line; `$90de`; group 0 holds `$580a6[side].word12`, 7 in every land seen, the others `rng & word12`) |
| `256(A1)` | +256..+266| wait-until timestamp, compared to `$2df72` |
| `268(A1)` | +268..+278| campaign-order id, matched against `$67d0[0]` |
| `280(A1)` | +280..+290| campaign phase / sub-order |
| `292(A1)` | +292..+302| escort-target object offset |

The "execution sub-record" older passes described at `base+$4c` / `base+$64`
is group 0's state word and its `24` target link (`$4b80`, below).

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
// One record per SIDE. Each field below is a 6-entry s16 array, one word per
// group (captain) k of the side, at base + off + 2k. A group's offset D2 is
// side*$13c + $4c + 2k, so group field x = array at $4c + x (x = -48 .. +$84).
// The AI ($6564) walks the same arrays with A1 = base + D7, D7 = 10..0 (group k = D7/2).
typedef struct pm_side_groups {       // base = $51538 + side*$13c
/* +0*/   u32  queued_flag;           // player / script order channel: nonzero -> a queued order in +1/+2
/* +1*/   u8   queued_type;
/* +2*/   u16  queued_param;
          // --- six-word arrays, [k] = group k (group field in brackets) ---
/* +4 */  s16  link       [6];        // slot-index / link, written back by $6822
/* +28*/  s16  owner_side [6];        // [-48] <= 0 -> no group
/* +40*/  s16  first_man  [6];        // [-36] roster head (next via 26(man))
/* +52*/  s16  men        [6];        // [-24] captain panel "Troops"
/* +64*/  s16  lead       [6];        // [-12] lead object offset
/* +76*/  s16  state      [6];        // [0]   $6 camp, 2/3/5/8/9/$a/$c/$e/$f/$10 per order, $d support
/* +88*/  s16  eat_timer  [6];        // [12]  $3e06: counts to $580a6[side].word0 (doubled in state 6)
/* +100*/ s16  target     [6];        // [24]  target link: a lord, settlement or object ($3154, $68fe/$6762)
/* +112*/ s16  food       [6];        // [36]  captain panel "Food"; -= men/8+1 per eat tick; AI groups seeded $5fff
/* +136*/ s16  posture    [6];        // [60]  2/3/4 aggressive/neutral/passive; also AI sub-state scratch (campaign sub-mode lands here)
/* +160*/ s16  carrying   [6][8];     // [84+12i] goods carried, i = pike..cannon (interleaved: stride 12 per item)
/* +256*/ s16  obj_wait_at [6];       // timestamp vs $2df72
/* +268*/ s16  obj_camp_id [6];       // matched against $67d0.campaignId
/* +280*/ s16  obj_camp_ph [6];       // campaign phase / sub-order
/* +292*/ s16  obj_escort  [6];       // escort-target object offset
          // ... $13c total
} pm_side_groups;
// $30fe returns  group.field_60 - 2  (posture - 2) as the kill/rout shift and the slice shift of every player order.
//   posture 4 (the AI stamps it on every attack group, $6638) -> always "2" -> rout, never kill.

// ---- leader / lord record : $4e514, 32 x 32 bytes -------------------
// Full field list: economy.md §1 (pm_leader). The fields this file uses:
typedef struct pm_leader {
/* 0*/  u8   nation;                  // side id 1..5; 0 = empty slot (loop terminator, array ends $4f914); $550e rewrites it
/* 2*/  u16  chain_head;              // -> $4f916 first settlement of the lord (walk via +8)
/* 4*/  u16  cell;                    // packed {x: bits 0-5, y: bits 6-12} of the lord's position
/* 6*/  u16  food;                    // the lord's food store (124th; was troops_reserve). $d322: += into $57fba[side].word2 ; $15e18/$15760: += 4 on arrival
/* 8*/  u16  troops_field;            // the lord's men at home (not in an army roster); $d322: += into $57fba[side].word0 ; $152d4 (join) / sieges/$5bd2 decrement it, $1b8c (leave) increments; $68fe scores vs it
/*12*/  u16  gather_kind;             // $5cde: the lord's current work order
/*14*/  s16  loyalty_pressure;        // >= 600 -> $550e revolt, reset to 300
/*16*/  u16  herd_throttle;           // $5cde / $60dc
/*18*/  u16  build_site;              // $5cde: $4f916 offset of the settlement under construction
/*20*/  u16  herd_op;                 // $5cde: the nearest $57f68 forest op
/*24*/  u8   goods[8];                // pike, sword, bow, plough, boat, pot, catapult, cannon ($159a4/$16376 index 23 + code/2)
} pm_leader;                          // sizeof 32

// ---- settlement record : $4f916, 18 bytes (economy.md §3) ----------
typedef struct pm_settlement {        // object.34 and leader.chain_head index this
/* 0*/  u16  bucket_next;             // a settlement is also a $47970 bucket node ($5cde links new sites with $16808)
/* 2*/  u16  bucket_prev;
/* 5*/  u8   owner;                   // commander colour holding the settlement; $550e rewrites it
/* 6*/  u8   category;                // render byte6 ($1e = a site being built)
/* 7*/  u8   kind;                    // the building: 7 = WorkShop ($5cde looks for it), names in economy.md "Buildings and town layouts"
/* 8*/  u16  chain_next;              // the lord's next settlement
/*10*/  u16  unit_head;               // first unit of the settlement (next at 24(unit))
/*12*/  u16  cell;                    // packed cell (the settlement's own cell; a merchant's mode $52 walks home to it)
/*14*/  u16  leader_off;              // byte offset into $4e514 for this settlement's lord
} pm_settlement;                      // sizeof 18

// ---- per-side assessment block : $580a6, 5 x $20 bytes -------------
typedef struct pm_assess {            // index by side id: $580a6 + side*$20
/* 0*/  u16  eat_period;              // $3e06: each army eats (food -= men/8+1) every this-many ticks, doubled while idle
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
// The word at +14 is the men per settlement that $2984 creates (economy.md 5a): 2 on every side of eight builds, so +15 is its low byte and
// overlaps rel[0] above; the layout of +14..+20 is not settled (rel[] may start at +16, which would make the +15+t reads one byte early).
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

- **else `$6564`** — **synthesise** an order. Walk the side's 6 groups; for a
  live one (`28() > 0`, `4() == 0`):

  1. state `$6` and past its wait timer (`256() + $14 <= $2df72`) → **`$6762`**:
     if the global campaign slot `$67d0` holds an order whose id matches this
     group's `268()`, obey it: order type = the entry's word 2, and the group's
     posture `136()` := the entry's word 4, or `($57fec & 3) + 2` when that is 0. `$67d0` = `{campaignId, orderType, subMode}`, static
     in the binary in mission 1 — **no writer found**; it is the campaign-script
     hook.
  Steps 2-4 run only for a group in state `$9`, or in state `$6` once `$6762`
  declines (`$6584`/`$658e`; any other state → next group).
  2. `52() < $16` (**fewer** than 22 men: `cmpi.w #$16,52(A1); bge $65dc` skips
     it at 22 or more; passes before the 124th had this inverted) → **`$69b4(8)`** scans `$4e514` for the
     nearest **own-side** lord that has more than one man in his `troops_field` (`cmp.b 5(A2),D0` skips
     every other side; the selector `D1` is the word offset read, 8 here and 6 for food; cost = that word `<< 3`
     over `max(|dx|,|dy|)`, a lord on the group's own cell scoring `$7fff`) → issue order
     **`$08`** (**get men**, group state 3) toward his town. Live, `callcap $69b4` with the
     player's lead as `A2` on `m1_s0`: `D1 = 6` returned the player's own lord 2 (enemy lords 0 and 1, food 28 and 32, skipped),
     `D1 = 8` found nobody while lord 2's field troops were 0 and returned lord 2 once they were poked to 10
     (3/3, `scratchpad/pm133/cc69b4.cmds`). The same routine with `D1 = 6` is the AI's food fallback (order `$06`).
  3. groups 1..5 (`D7 != 0`), when group 0 (`A3 = A1 − D7`) is in state `$d`
     with `280(A3) == 4` → issue order **`$0c`** to **escort** group 0's
     `292(A3)` object.
  4. group 0 (`D7 == 0`, the captain's), `52() - 4 > 0` → **`$68fe`** scans
     `$4e514` for the nearest enemy leader (cost weighted by the per-side
     assessment byte `16($580a6 + side*$20)`); **`$68ee`** scores it
     `(d/2)·((men−4)/8 + 1) + d/2` (D1 = own men − 4 survives `$68fe`); if
     `score <= 112()` (the trip's food at the eating rate `men/8 + 1`, against the
     group's food) → set group state 4 and issue order
     **`$0c`** (→ group state 8 = march & engage) toward that leader's cell.

Order writes go through `$67ee` → `$6822`: `$67ee` re-packs the found leader's
cell `4(A3)` into `{x:6, y:7}`, `$6822` stores `{type, param}` into
`$58016[cmd]` bytes 1/2 and stamps `4(A1)` / the `$58042` cross-index.

**This layer has no economy, build or recruit reasoning** *(Observed — the
`$6522`/`$6564` handler was fully disassembled and traced in mission 1; no
economy/build branch was seen, but `$6564` is one of several `$6522` sub-cases
and the campaign hook `$67d0` was never live. Evidence taxonomy: `ai.md`.)*. The
autonomous decision is: *"march the army at the nearest enemy leader, if I have
more than ~4–22 men and my army has the food to get there."* AI groups start
with `$5fff` food (`$26c4`), so the test never binds in practice ("Open threads"). Food is taken from towns at the entity level (mode `$1a`, `ai.md`);
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
| `$08` | `$6bea` | `$3154` D3=3 D4=`$1c`, then `$3248` | icon, targeted; AI (`$69b4(8)`, "get men") |
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
| `$26` | `$6dd0` | `$d0dc(param)` when cmd ≠ local side: one character into the message line (panel `$16`) | chat: SEND MESSAGE (`$131`) sets `$d03e := $fe`; `$d13e` posts each typed key at `$d14c` (live, "Hidden features audit") |
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
group-state → entity-mode table in `ai.md` (state 3 ⇔ order `$08`, get men: the modes `$1c`/`$28`/`$2a`;
state `$c` ⇔ the `$1a` food supply line).

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
   | 2 | `$921a` | `$9036` (captain info) | none: name, job, aggression, loyalty, health (the row is labelled "Strength:" but `$912a` prints the `healthnames` string from byte 45), speed, food, troops, carrying |
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
   | `$02` | `$ea` | (299,182) | figure | `$135fe`: arm `$57fd4 := $02`: **go to** |
   | `$04` | `$c4` | (103,186) | two men | `$13620`: toggle captain-select `$57fd6`: **transfer men** to another captain |
   | `$06` | `$d7` | (201,181) | sphere | arm `$06`: **take food** |
   | `$08` | `$da` | (275,162) | arrow into men | arm `$08`: **get men** (recruit) |
   | `$0a` | `$b4` | (100,170) | HOME | `$13652`: post `$0a` now |
   | `$0c` | `$e8` | (243,190) | sword | arm `$0c` (march & engage) |
   | `$0e` | `$e9` | (274,187) | light bulb | arm `$0e`: **set the men to work** (invent) |
   | `$10` | `$db` | (297,156) | – | arm `$10`: **take equipment** |
   | `$12` | `$d5` | (142,193) | – | post `$12` now: **drop food** |
   | `$14` | `$d9` | (252,168) | four arrows | post `$14` now: **dismiss men** |
   | `$18` | `$d6` | (173,188) | – | post `$18` now: **drop equipment** |
   | `$1a` | `$d8` | (227,174) | chain | arm `$1a`: **food supply line** |
   | `$1c` | `$b3` | (74,175) | – | arm `$1c`: **trade** (any settlement) |
   | `$1e` | `$a3` | (73,161) | eye with arrows | arm `$1e`: offer an alliance to the clicked settlement's lord |
   | `$20` | `$93` | (72,149) | eye | arm `$20`: **spy** (a settlement not ours) |
   | `$26`/`$28`/`$2a` | `$a4`/`$94`/`$84` | (97,156)/(94,145)/(92,135) | posture | `$13678`: post `$16`, param 2/3/4: **aggressive / neutral / passive** |
   | `$2c` | `$c3` | (75,191) | – | `$136b2`: toggle `$57fea`, disarm `$57fd4` |
   | `$2e` | `$83` | (71,138) | – | `$13716`: options panel 4 (`$af6c`) |

   Arming the icon that is already armed disarms it (`$1898e`). Screen
   positions are centroids from the game's own hit-test
   (`reversing/powermonger/py/iconmap.py`); the sword `$0c` and the options
   `$2e` were clicked and behaved as listed, and every other order was clicked
   in the 124th pass ("What each order does", below). The glyph names are read
   off a rainy frame; the order names are the effects, with the manual's words
   where they fit.

**Driving it headless** (`reversing/powermonger/py/clicks.py`): the pointer
moves 1:1 with `mouse move` and clamps at 0, so home it with a large negative
move and click at absolute (x, y). `reversing/powermonger/py/drive_win.sh`
plays mission 1 to a natural victory this way (next section, "How a land
ends").

### What each order does (124th pass)

A targeted order marches the group's lead to the target with `31 := $10`
(advance) and `30 :=` an **arrival mode**; the order's meaning is that mode.
`$3154` (orders `$06`/`$08`/`$0e`/`$10`/`$1c`/`$1e`/`$20`) only accepts a cell
holding a settlement (object byte6 `$2` or `$10`) whose owner passes a filter
set by D5: own side (D5 > 0; for D3 = 2 or `$a` also a side whose peace bit is
set, "Diplomacy"), any side (D5 = 0), not the local side (D5 < 0). It then
targets the settlement's lord's cell (`4(lord)`; order `$20` the settlement's
own cell `12(settl)`) and stores the lord as the group's target link `24(group)`.
Every amount an order moves is `x >> (posture − 2)` (`$30fe`): aggressive
(posture 2) moves all, neutral (3) half, passive (4) a quarter.

The group record fields the orders use (offsets from the group exec record
`$51538 + D2`; the captain panel `$921a` prints four of them):

| field | meaning | captain panel |
|-------|---------|---------------|
| `-12` | lead object offset | |
| `-24` | men in the group | "Troops:" (`$9192`) |
| `-36` | first man (roster via `26(man)`) | |
| `-48` | owner side (0 = the group is dissolved) | |
| `0` | group state (= D3 of the order) | |
| `24` | target link (a lord, a settlement or an object, `$51b66`-relative) | |
| `36` | **the army's food** | "Food:" (`$917c`) |
| `60` | posture 2/3/4 | |
| `84 + 12i`, i = 0..7 | goods carried (pike, sword, bow, plough, boat, pot, catapult, cannon) | "Carrying:" (`$91a8`) |

A lord's `+6` (`$4e514`) is his town's **food store** (economy.md §1).

| order | handler | target | arrival mode | effect |
|-------|---------|--------|--------------|--------|
| `$02` go to | `$3888` | any cell | `$1e` (`$1515c` → `$35f4`) | state 5, march there, go idle |
| `$04` transfer men | `$1c18` (D0 side, D1 from, D2 to group) | a captain box, with captain-select on | – | `men >> shift` move from one captain's group to the other (`$1b8c` out, `$1b2a` in); static only (mission 1 has one captain) |
| `$06` take food | `$3154` D3=2 D4=`$1a`; else `$38ce` | own or allied town; else a cell | `$1a` (`$150c0`); `$72` (`$1605a`) | from a town: `food >> shift` into `36(group)`, `loyalty_pressure += 16 >> shift`; on a cell: pick up a food pile (`$2c`) there |
| `$08` get men | `$3154` D3=3 D4=`$1c`, else `$3248` | an own settlement, else an own man standing on the cell (byte6 0) | `$1c` (`$15122`: quota `lord.troops_field >> shift` into `46(lead)`, `$34f2` sends the town's men to the cell), `$6c` for a lone man | the town's able men step to the lord's cell, where the lead waits, and the first `quota` of them join (`$1b2a`), cost the lord one `troops_field` each and trigger `$1d70`'s re-forming of the ranks; later arrivals are refused (proven live, below; ai.md `$2a`); the executor's original name is `get_men` ("Original names") |
| `$0c` march & engage | `$4a7a` | any cell holding a tracked entity (a settlement, tested; not empty ground, which never commits — "Diplomacy") | – | "How a land ends" |
| `$0e` set men to work | `$3154` D3=9 D4=`$22` | own town | `$22` (`$151a8` → `$5fa0`) | the town lord's work order `$5cde` goes to every man; `$5cde` refuses a lord without a WorkShop (building kind 7) |
| `$10` take equipment | `$3154` D3=`$a` D4=`$6e`; else `$6128` | own or allied town; else a pile / object byte6 `$0a`, `$18`+`$10` | `$6e` (`$15740` → `$61f8`) | `goods >> shift` from the lord, handed to the men (`$6352`/`$638c`) |
| `$12` drop food | `$39d4` D7=1 | the lead's cell, now | – | `36(group) >> shift` to the town's food (`loyalty_pressure −= 8` if own town) or to a new or existing pile (byte6 `$2c`, `$4bb4e`) |
| `$14` dismiss men | `$1cc4` | now | – | `men >> shift` leave, least equipped first (lowest `44 + 33`), back to the lord's `troops_field` |
| `$16` posture | `$35a0` | now | – | `60(group) := param` and the icon highlight |
| `$18` drop equipment | `$39d4` D7=2 | the lead's cell, now | – | carried goods `>> shift` (and a lead's byte44 ≥ `$e`) to the town lord's goods, or to a pile |
| `$1a` food supply line | `$390e` | any cell | `$74` (`$160d6` → `$3956`) | state `$c`: at the cell drop food (`$39d4` D7=1), go to the own lord with the most food (`$3bc8`), take food (`$1a`), return (`$26`), repeat |
| `$1c` trade | `$3154` D3=`$f` D4=`$78`, D5=0 | any town | `$78` (`$15772` → `$63f4`) | sell the carried goods to the lord; credit = army food + Σ sold × 2 × price (`$6502`: 5,10,20,4,6,2,100,200); buy in the posture's order (`$650a`: aggressive cannon, catapult, bow, sword, pike, boat; passive plough, boat, pot, ...); the credit left is the army's food, the food spent goes to the town; `loyalty_pressure` −8 own town / +8 foreign; `$311a` relation +2 |
| `$1e` offer alliance | `$3154` D3=`$e` D4=`$76` | a town not ours | `$76` | "Diplomacy" |
| `$20` spy | `$3154` D3=`$10` D4=`$7a`, then `$1d36` | a town not ours | `$7a` (`$1578c` → `$3da4`) | every man is dismissed; the captain walks alone into the town and joins its unit chain with its owner's side (`5(lead)`), `bset #7`, mode `$7e`; the lord's `troops_field += 1` |

Evidence: each order clicked from `scratchpad/pm123/win/m1_s0.snap` (mission 1,
posture 3) and compared with a no-order run over the same steps
(`scratchpad/pm124/<order>/`; reproduce with `reversing/powermonger/py/order_run.sh`,
for example `order_run.sh o12 3000000 home 142,193`, byte-identical). 1 run each:

- `$06` on the own town (3M steps): town food 22 → 11, `loyalty_pressure` 0 → 8, army food 258 vs 247.
- `$02` to (35,51): state 5, lead heading for the cell, arrival `$1e`.
- `$0e`: refused (`$5cde` 1 hit, 0 return, the `$5ffe` exit); with the town poked to kind 7, all 26 men
  switch to mode `$46` and the lord gains 2 pots within 2M steps.
- `$10` with the lord's goods poked to 10,10,10: goods 5,5,5; 5 men get bows, 5 swords.
- `$12`: army food 247 → 122, town food 22 → 147, `loyalty_pressure` −8.
- `$14`: men 26 → 13, the lord's `troops_field` 0 → 13.
- `$16` param 2: posture 3 → 2.
- `$18` with carried goods poked to 10,6: carried 5,3, the lord's goods 5,3, `loyalty_pressure` −8.
- `$1a` to (35,51), 25M steps: a food pile of 123 at (35,51), town food 22 → 11, state `$c`, the
  lead on its way back.
- `$1c` on lord 0's town, carried goods poked to 10,6: 6 men get swords, army food 235.
- `$08` is **get men**, not besiege (133rd; the executor's own name in the developer symbols is `get_men`,
  "Original names"). Both of its target routines, `$3154` and `$3248`, take D5 = the commander's side and
  accept only a target of that side (`$3154`: `D5 > 0` branch; `$3248`: `cmp.b 5(A1),D5`, byte6 0). Live on `m1_s0`: the
  armed icon clicked on enemy lord 0's town (minimap `(22,51)`) posted nothing (`$57fd4` stayed `8`, 0 `$6bea`
  and 0 `$3154` hits in 60M steps); clicked on the own town (lord 2's field troops poked to 10 so the quota is
  non-zero) it ran `$15122` once and left the lead in mode `$28` (a 50-tick wait, then `$35f4` makes the camp),
  group state 3, 22 `$15264` entries in 6M steps. `callcap $34f2` (the summons `$15122` makes) on lord 0's town
  sends 4 men (object records 2, 3, 5, 7: target cell `20/22`, mode byte `31 := $10`, `30 := $14`) and on the
  player's own town none: its house chain holds no inhabitants in mission 1, so no join happens there
  (`$15282`, `$1b2a`, `$1d70` 0 hits). `scratchpad/pm133/o08*/cmds`, `cc34f2*.json`.
- **A man joins live (134th, `py/join08_run.sh`).** `pm123/win/m1_ready.snap` is mission 1 after the natural
  conquest: lord 0's town is side 1 with `troops_field` 5 and 5 able side-1 men in its houses (the corpses
  carry side byte 254 and are skipped), the player's lead idles at (28,47). Armed icon `(275,162)`, click on
  the town on the minimap `(22,51)`: `$6bea` and `$3154` 1 hit each, `$57fd4` back to 0, `$3248` 0 (the town path), the
  lead reaches the cell and `$15122` fires 6,604,819 steps after the click. `$34f2` (1 hit) gives all 5 men
  mode `$3c` → `$10`/`$14`, `46(man)` = the lead's offset `$41a`; the men reach mode `$2a` (`$15282`, 5 first-tick tests)
  between 0.4M and 1.9M steps later. The quota `46(lead) = troops_field >> (posture - 2)` is decremented by
  every arrival *before* `$1b2a`, so the first `quota` men join and the rest are refused (their `46(lead)` goes
  negative), wait out the 50-tick dwell in `$2a` and fall into `$3c08` (back to civilian modes). Measured, one run per row
  (all four rerun-identical; the posture and the `troops_field` 7 row are pokes, `w 516fc 000p0000` and `w 4e51c 00070000`):

  | posture | `troops_field` | quota set | `$1501a` arrivals | `$1b2a` / `$1d70` hits | group men | `troops_field` after |
  |---|---|---|---|---|---|---|
  | 3 neutral | 5 | 2 | 5 | 2 / 2 | 26 → 28 | 3 |
  | 2 aggressive | 5 | 5 | 5 | 5 / 5 | 26 → 31 | 0 |
  | 4 passive | 5 | 1 | 5 | 1 / 1 | 26 → 27 | 4 |
  | 3 neutral | 7 (poke) | 3 | 5 | 3 / 3 | 26 → 29 | 4 |

  A joined man is pushed at the head of the roster (`-36`) with flag bit 6 set and `28(man)` = the lead; `$1d70` gives him mode
  `$08` → `$06` → `$68` (idle in the group). The lead stays in `$28` for the 50 `$15264` ticks (about 200k steps each, ten
  million in all), then `$35f4` ends the order and makes the camp: the group goes from state 3 to 6. `py/townmen.py`, `scratchpad/pm134/join/`.
  Not run: `$1b2a`'s rule for a man of another side (read from the code: he joins only when his home settlement's owner is the lead's side).
- `$20` on lord 0's town, 25M steps: men 0, the captain inside (22,45) with side byte 2. Lord 0
  then defected to side 3 (loyalty reset to 300); the 25M control keeps him on side 2 at 608. The
  spy idles in the town in mode `$7e`, which runs the settlement heartbeat with no `$57fd0` gate;
  his first pulse checked lord 0's 608 and revolted him to `(x cell 22 mod 4) + 1 = 3` (economy.md §3).

## `$d322` + `$3e06` → `$57fba` → `$d23a` → `$57fce`

`$57fba` = 5 × 4-byte per-side force totals, rebuilt from scratch every tick:

- **`$d322`** zeroes all five, then for each leader in `$4e514` (32-byte
  records) adds `+0 += 8(leader)`, `+2 += 6(leader)` (its two troop-count
  fields). It also walks the `$47970` buckets around each leader via the
  neighbour-offset ring `$d49e`, and where an enemy category-0 entity whose
  group is strong enough (`8(leader) >> 1 > -24(groupRecord)`) is in contact it
  calls `$4bc8` — troop-count / ownership reconciliation. That is bookkeeping,
  **not an order.**
- **`$3e06`** — more than a UI routine. Its head is the
  flag-health indicator (health byte 45 of the selected group's lead,
  `divu #$14`, → `$58056`). Then it walks **every** side's 6 groups (A2 =
  side base + 2k): adds the group's men `52(A2)` into `$57fba[side].word0`, and
  **the army eats** (`$3f44..$3faa`): `88(A2)` counts ticks to
  `$580a6[side].word0` (twice that while the group is idle, state 6); then
  `food 112(A2) -= men/8 + 1` (`$3f6a`). At below zero the food is cleared and
  every man of the roster (`40(A2)`, next `26(man)`) leaves with chance 1/8
  (`$12c9a` LCG `& 7 == 0` → `$1b8c`, D1 = 0 in state `$d`, else 1): **a
  starving army deserts**. Observed (124th): our 26-man group on mission 1,
  `watch $516e4` over 25M steps, 2 writes, both at `$3f6a`, 251 → 247 → 243
  (`26/8 + 1 = 4`). A big army eats fast; the AI's march test `$68ee` charges
  the same rate per cell of distance.

  **Driven live and proven (125th).** From `m1_s0` (26 men, food 251), posture
  set to 2 (`$26`, so the next order moves the full amount), then `$12` drop
  food (empties `36(group)` to the town) and `$02` go-to (35,51) so the group
  keeps marching. Food hit 0 and stayed clamped there for the rest of the run:
  four `$3f6a`/`$3f72` eat-and-clear ticks over 50M steps (`scratchpad/pm125/starve/`,
  `watch $516e4`, `hits ... 3f6a 1b8c 12c9a`). `$1b8c` fired 13 times and the
  roster (`group.py`) dropped from 26 to exactly 13 — an exact match, confirming
  `$1b8c` is the desertion action, not just a candidate. Bracketing each tick
  with `bpc 3f72 1` and dumping `516a8` (`scratchpad/pm125/starve2/`) gives the
  per-tick roll: 3/26, 5/23, 4/18, 1/14 — 13/81 total (16.0%) against the 1/8
  (12.5%) rule, inside one standard deviation (σ ≈ 3.0 on an expectation of
  10.1) for four trials this small. The deserters are not lost: our lord's
  `troops_field` (`sides.py` "field") went 0 → 13, the same destination as an
  order-`$14` dismiss (`$1cc4` → `$1b8c`) — starvation desertion is mechanically
  a forced dismiss, just triggered by the LCG roll instead of the player.

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
`word[$51538 + side*$13c + 28]` (the owner-side word of that side's group 0,
the captain's) is `<= 0`, it posts command `$2e` itself and clears `$57fce`,
which ends the land as a defeat. The knob the autonomous AI actually turns is
the groups' food `112()` (through `$68ee`) and the per-side assessment weight in
`$580a6`, not this global ratio.

`$580a6` — 5 × `$20`-byte per-side assessment blocks — is written all over the
`$2200`–`$3500` cluster and from `$139dc`/`$13a3e`/`$13b20` in the sim tick.
The relation and peace-bit fields are the diplomacy layer ("Diplomacy",
below); `$68fe` reads one wrong byte of it as a targeting weight.

## `$127e6`

The **sound-event dispatcher** (original `_do_soun...`). A min-of-2 selector over the `$3b`-entry table at `$12952`
(14-byte entries, pending when word 0 is nonzero, keyed on the priority word `10(entry)`) picks the two best pending
events, clears them, and `$1283c` hands each to `$1ba3e`, the sound player (`move.w 6(A1),-(A7)` = the sound id,
`jsr $1ba3e` at `$128d2`), unless the same id is already playing on the channel. Live: from `pm123/win/m1_atk` over
6M steps `$127e6` runs 24 times and one run reaches `$128d2` and `$1ba3e` (the other 23 find nothing pending). It is not
an event-marker or "under attack" ticker feed, and not a decision routine.

## The campaign-order hook — `$6762` / `$67d0` (72nd pass, static)

`$6762` is the first thing `$6564` tries for a group in state `$6` past its
wait timer. `$67d0` is a 6-byte global: `{word0 campaignId, word2 orderType,
word4 subMode}`. The routine, decoded:

```c
// A1 = side base + 2k (group k)
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
ten times) and found the decisive one is a **health grind ending in a rout**,
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
    T->health -= dmg;                             // <<< byte 45 is the melee HP (the panel's healthnames)
    if (T->health <= 0) { pm_kill_or_rout(A1, T); return; }  // -> $5590
    A1->link_into(T);  T->mode = 0x32;            // keep grinding
}
```

`$5590` — reached when a unit's `health` is ground to `<= 0`:

```c
void pm_kill_or_rout(obj *A1 /*attacker*/, obj *A3 /*loser*/) {
    A3->health = 0;
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

The `group.field_60` term is the group's **posture** (2 aggressive, 3 neutral,
4 passive; the player's three posture icons, "What each order does"; passes
before the 124th called it discipline). The AI stamps posture 4 on every group
it sends to attack (`$6638`), so `pm_30fe` returns `2` and the roll is pinned to
**rout**: ten routs, zero kills in the 73rd-pass fight. Posture 2 always kills;
posture 3 rolls (the player's mission-1 army: 5 kills, 5 routs in the win run,
`scratchpad/pm124/conquest/REPORT.md`); an encircled loser (`flags.bit5`) is
killed whatever the posture.

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
    int cap = t_health_cap[A1->flags & 0x1f];           // inline table at $5ccc, indexed by the job byte 7
    int wear = (u8)A1->anim_wear - 0x3c;
    if (wear >= 0) {                                    // bmi skips otherwise
        cap -= wear * 4;
        if (cap < 0) { pm_unit_remove(A1); }            // -> $5bd2
    }
    int health = (s8)A1->health;
    if (health < 0) { A1->health = 0; return 1; }
    if (cap > health) { A1->health += (g_tick_rng & 1); return 1; }  // recover
    return 0;                                           // cap <= health: at the cap, nothing to do
}
```

`t_health_cap` (`$5ccc`, the health a man of that job recovers to; byte 45 sits on it in 203 of 225 live persons over three snapshots, `py/health_check.py`) is a sparse **17-byte** table indexed by
`flags & $1f` (a small enum, not a bitfield): index `0/1/2/4/8/$10` →
`90/82/69/79/72/95`; every other index is `0` (and `>= 17` reads into the next
routine's code — never happens, the enum only takes those six values plus
`$11`). `$5778` stamps an engaged garrison's flags to `$11` → health cap `0`,
so it stops recovering health and is removed once `anim_wear` crosses `$3c`.

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

The get-men modes (`$28`/`$2a`, `ai.md`; order `$08`) are not a siege: `$28` waits 50 ticks and `$2a` (`$15282`)
moves one recruit into the group, counts down the lead's quota and calls **`$1d70`** (`_rerank`) to re-form
the ranks (observed live, "What each order does"; settlement ownership is transferred elsewhere — `$25d6`/`$2644`, `economy.md`).

**`$1d70` proven (99th, via `$3c08`'s bit-4 teardown — `ai.md`):** it is the
**rank former** (`_rerank`), not the ownership writer. It picks a rank-shape
string from the `'C'`(`$43`)-delimited table at `$1e9e` (indexed by the highest
set bit of `word[grouprec−24]`), then for every roster member (chain via
`word[+26]`) does a two-way scan of that string — a row layout of weapon-class
letters, `'P'` pike, `'S'` sword, `'B'` bow, `$ba` unusable — for the nearest slot matching the
member's weapon class (`word[$1e8c + 44(member)]`; ai.md `$1d70`), marks it taken so the
next member picks a different one, and writes the member a step vector
(`20/22 := (dx,dy) << 6`), mode `$08`, `dwell 0`, `category 0`. Net effect: the
roster is re-ranked, each man stepping to his preferred-terrain slot along the route (the developers' name is `_rerank`); a
member then settles in mode `$06` → `$68`, idle in the group (live on a join, "What each order does"). The earlier
"dispersed / sent home" reading came from the teardown call sites, where the same steps run before the men are released.

### Measured — the re-armed mission-1 fight (73rd pass)

66M-instruction traced resume from `pm71_slot4.snap`, re-arming slot 1's
`byte4 := 4` every ~4M steps (16 pokes; `scratchpad/pm73_fight.evt`,
`trace_cfg.py --blocks`), ~276 sim ticks. (The 72nd pass ran 40M / 166 ticks
with a single poke; the counts that overlap match.)

| routine | hits | reading |
|---------|-----:|---------|
| `$6522` decide | 276 | once/tick |
| `$661a` primary-slot decide | **2** | re-arming `byte4` mostly does *not* re-trip `$661a` — the objective slot's `obj_active`/`obj_force` stop qualifying after the first order issues. Only 2 autonomous primary decisions in 276 ticks |
| `$68fe` / `$68ee` | 2 / 2 | both decisions: food enough for the trip |
| `$15302` reached-enemy | 41 | men closing on enemy positions |
| `$56a6` engage | 9 | contacts made |
| `$5778` bookkeep | 2 | gated hard on `flags.bit6` + `d < $fff` |
| **`$5590` kill-or-rout** | **10** | first field-combat resolutions ever traced |
| — KILL (`$55f2`) | **0** | |
| — ROUT (`$560a`) | **10** | `$30fe` → `2` every time (`group.field_60 == 4`) |
| `$5bd2` wear removal | **0** | `anim_wear` never crossed `$3c` in 276 ticks |
| `$57f0` spawn projectile | 3 | |
| `$1d70` group route-expand (`_rerank`) | **15** | fires whenever a roster changes (a join `$15282`, an unlink `$1b8c`, a teardown `$37c2`); the re-rank step, not the ownership write (99th, 134th) |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5c80` upkeep | 2136 | ~8 entities/tick |

**Reading.** A forced attack in mission 1 produces engagement, a handful of
projectiles, ten **routs** (units scattered by `$3c08`, none killed), and
fifteen **captures**. So territory changes hands and armies get broken up, but
almost nobody dies on the field — because the attack group's posture
(`field_60 == 4`, the AI's attack stamp) pins the `$5590` roll to "rout", and the wear channel is far
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
  `& 1` (health recovery, `$5c80`), `& 3` (campaign sub-mode, `$6762`), `& 7`
  (a speech-line pick, `$3e06`/`$3f08`). Because it is just the low bits of the
  tick count, **the AI is fully deterministic** given the tick number — there is
  no seeding, no entropy, and a save/restore at the same tick replays
  identically.
- **`$57ff6`** — a genuine 13-bit LCG, `x = (x * $24a1 + $24df) & $1fff`,
  stepped 16× per `$1abaa` call (`$1abc0`). It is the **pixel-order generator of the season tileset
  dissolve** (each step copies one pixel of the new season's art into the live tileset at `[$ff9e]+3712`; 136th, `scratchpad/pm136/season/tilediff.py`:
  half summer and half autumn art at count 255, 98% the new art at 496); full period 8192 = 512 calls, and its **wrap** to 0 rotates `$57fd0`, plays a season
  sound and nudges one `$4d252` tree record (see "What `$1abaa` actually is"). Never the AI or combat.
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
issued.** The lone enemy captain stayed in its standing state (inferred idle, group state 6: the
player's own group is in state 6 in 6 of 6 snapshots of `py/group_states.py`; no snapshot holds side 2's group) the whole
time. Mission 1 is a tutorial and its enemy AI is near-dormant.

The `$6564` path above was read statically and then **confirmed by force**:
poking `$58020` (slot 1 `byte4`) = 4, `$6522` took `$6564` → primary-slot
`$661a` → `$68fe` (picked the nearer enemy leader) → `$68ee` (food enough) →
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
at the start and no defection happens without the attack: in mission 1 nothing
pulses the heartbeat for lord 0, so 608 is never checked. The defection is the
field conquest `$539a` (124th: `$53f6` 1 hit, `$158cc` 0; lord 0's 10 men all
dead or routed; economy.md §3 "How a settlement changes hands", gate
`py/diff_4f68.py`). Snapshots `scratchpad/pm123/win/`.

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
    make_camp_35f4(g);                               // the envoy group's order always ends (camp, state 6)
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

**A fully organic attempt corroborates this (127th pass, no pokes anywhere in
the chain).** Land 25's side-1 captain group (8 men, `scratchpad/pm121/run/k25_s4.snap`)
was sent with order `$10` to its own lord 7's town (24,21) — a real `take
equipment` click, no register pokes — and came back carrying 3 pots pulled
from lord 7's actual stockpile (confirms economy.md §2c: `$61f8`/`$6352` really
does fill a group's `carrying[]`/`supply_acc[]`, not just equip individual
men). Still carrying those 3 pots, the same group was then sent with order
`$1e` toward the nearest foreign lord (side 3's lord 4, capital at (28,14),
7 cells away) to offer an alliance. It never arrived: within 13M steps it hit
a hostile unit at (26,17), `$4c2a` fired (contact reconciliation, not
diplomacy), and the whole group was wiped out in the melee — its 3 pots
dropped as a ground pile where it died (`scratchpad/pm127/diplo3/`). Between
this and the 123rd's forced-goods run on land 60, two independent natural
corpora showed the same failure mode: by the time a settled world has
accumulated enough goods economy for a natural tribute, its territory is also
contested enough that an unescorted envoy rarely completes the walk.

**Neither of the two obvious fixes works on land 25 (128th pass, two parallel
agents).** An earlier snapshot does not help: the same envoy, zero goods, sent
on the identical route to side 3's lord 4 (28,14) from `pm121/k25.snap` (0
ticks) and `pm121/run/k25_s1.snap` (50M ticks) died at the *same* cell (31,13)
in both runs — the death is a structural feature of the corridor (a garrison
cluster of 18+ side-3 entities sits right around the capital, confirmed by a
spatial object-table scan), not something that accumulates over the land's
runtime. An escort cannot be built either: land 25's side 1 has exactly one
captain slot, always (censused across the whole `k25`/`k25b` corpus) — there
is no second group to send ahead, and no player order grows a group or spawns
a new captain (order `$04` transfer needs two captains that don't exist here
either). A hypothetical escort couldn't pre-position on open ground ahead of
the envoy regardless: order `$0c` (march & engage) aimed at an empty cell
never commits at all (`$57fd4` stays armed, the group never leaves home,
tested at the 127th's own death cell); it only commits against a cell holding
something the game already tracks, such as a settlement (confirmed: the same
click against lord 4's town at (28,14) committed within 5M steps). This
corrects "any cell" in the `$0c` row of the order table below — read it as
"no friend/foe filter", not "arbitrary ground". Details, commands and
snapshots: `scratchpad/pm128a/REPORT.md`, `scratchpad/pm128b/REPORT.md`
(indexed in `ANCHORS.md`).

Those failures (123rd, 127th, and the 128th's two land-25 probes) were all
against garrisoned lords, and all ended in `$4c2a` before `$33b0` ran. **Land
5's apparent second/third captain slots are not usable as an escort, checked
at the land's start (`pm121/k5.snap`) and 50M/100M ticks in
(`pm121/run/k5_s1.snap`/`k5_s2.snap`) with `scratchpad/pm128a/census_groups.py`:
groups 1 and 2 are `owner 1` but `men 0` from the very first snapshot,
dead captain records.** An escort is not needed if the target is not
garrisoned, which the next paragraph shows.

**A natural alliance completes end to end (129th pass, land 25, no pokes).**
Start: `pm127/diplo3/equip_probe.snap` (the organic take-equipment state);
the only inputs are three `clicks.py` click sequences
(`scratchpad/pm129/`, commands `run5/6/9.cmds`, outputs beside them).

1. *Target.* `census_lords.py` counts live entities by owner around each
   foreign lord and along the corridor from the group's lead at (24,21). Lord 4
   (side 3, the dead route): 18 side-3 entities at the lord and 18 on the
   corridor. Lord 15 (side 4, (39,31)) is a lone kind-11 town, 0 side-4
   entities at it and 0 non-own entities in the box x23..41, y17..35
   (`scan_objects.py`). Lord 9 (side 3, (50,50)) has 2 entities but is 29
   cells away, too far for the group's food.
2. *Tribute.* Order `$10` on own lord 7's town (`clicks.py home 297,156
   24,27`): `carrying[]` pots 3 to 5, lord 7's pots 2 to 0 at 3M steps
   (`$61f8` 1 hit, `$6352` 8 hits; `eq_3M.snap`).
3. *Waypoint.* Order `$1e` straight at lord 15 fails, and it is terrain, not
   a garrison: the lead reaches (38,29), then sits in mode `$48` (obstacle
   avoidance) at (37..38,29) for 60M steps, starves (food 0, men 8 to 3) and
   `$33b0`/`$34a8`/`$4c2a` have 0 hits. `terrain.py` prints the `$438ee` type
   plane (`y*64+x`, type 0 = water per ai.md `$1648e`): a type-0 strip at
   (38..39,29) lies between the straight-line path and the town. An order
   `$02` to (40,28) first (`clicks.py home 299,182 40,34`) gets round it:
   after 45M steps the lead is at (40,28), state 6, 6 men, food 0, 5 pots
   (`wp5_45M.snap`). Food is 0 from about 38M steps and one man deserts per
   5-10M steps, so 6 of 8 arrive.
4. *Offer.* Order `$1e` on lord 15's town from `wp5_45M.snap`
   (`clicks.py home 73,161 39,37`, `run9.cmds`). Hits counted from the click
   over 6M steps: `$15754` 1 (step 5,331,749), `$33b0` 1 (5,331,754), `$3458` 1
   (5,331,847, posts `$2a`), `$34a8` 1 (5,337,916), `$c9f8` 1 (5,337,931, the
   "alliance forged" message); `$c706`, `$cada`, `$4c2a` 0 (`$15754` and `$3458` from
   `run7`, which `run9` reproduces step for step; `run9` itself counted
   `$33b0/$34a8/$c9f8/$c706/$cada/$4c2a`). Peace bits: side 1
   (`$580cc`) `$02` to `$12`, side 4 (`$5812c`) `$10` to `$12`, re-read
   from the snapshots (`wp5_45M`, `env5_8M`, `env5_12M`, `env5_42M`). The
   envoy group is freed with `carrying[]` zeroed; 5 men are still at (39,31).
   30M further steps (`run8.cmds`, from `env5_12M.snap`) leave the bits at
   `$12/$12` with `$4c2a`, `$4c64`, `$4c7a`, `$c5ee`, `$c9f8`, `$33b0`, `$34a8` at 0 hits.
   (`$4c2a` did fire once, 2.07M steps into `run7`'s third chunk, a contact
   elsewhere, inferred to be sides 3 against 4; it did not touch the 1/4 bits.)

*The tribute bar is exact.* `$33b0`'s `v = rel[16+g->side] + Σ supply_acc·W − 2`
with side 4's byte `$58137` = −8 (`rel.py`). Control, same route with the
organic 3 pots (`run4.cmds`, from `wp_45M.snap`, 8 men at arrival): `$15754`
1, `$33b0` 1 (295,648), `$cada` 1 (295,745, the refusal), `$34a8` 0:
`v = −8 + 6 − 2 = −4`. With 5 pots the tribute is 10 and `v = 0`, accepted. Only the outcomes at 3 and 5 pots were
observed, so "the bar for this lord is exactly 5 pots" and
`carrying[] == supply_acc[]` at the offer are inferred from those two runs.
Side 3's byte is 0 (`rel.py`), so 3 pots would give `v = 4` there (not run:
lord 4's garrison still kills the envoy).

Caveats: the ally is side 4, not side 3; the walk survived because lord 15
is an ungarrisoned lone town, not because of an escort; the route needs the
`$02` waypoint and the tribute needs the second `$10`. The earlier
reading that an unescorted envoy inevitably dies to contact is wrong: the
death is specific to a garrisoned target.

*The alliance's effects, checked from the natural state.* From `pm129/env5_12M.snap`
(peace bits `$12`/`$12`, group `$188` alive at lord 15's town (39,31), 5 men), the
icon is armed and lord 15's town clicked on the minimap (`scratchpad/pm131/o06|o10|o1e.cmds`,
`hits` started before the click, 3M steps each):

| armed order | `$3154` | `$31a6` → | pointer test | result |
|---|---|---|---|---|
| `$06` take food | 1 | `$31b2` 6, `$31cc` 1, `$31c8` 0, `$38ce` 0 | `$139da` 1, `$131be` 1 | accepted as an own town: lord 15's food 36 to 0, group food 0 to 35, loyalty 0 to 16 |
| `$10` take equipment | 1 | `$31b2` 6, `$31cc` 1, `$31c8` 0, `$38ce` 0 | `$13a3c` 1, `$131be` 1 | accepted (lord 15 holds no goods, so nothing moves) |
| `$1e` offer alliance | 0 | not reached | `$1394c` 14, `$13b1e` 14, `$131be` 0 | refused: nothing posted, `$57fd4` stays `$1e` |

So `+6` is read exactly as documented above: an ally's town passes the friendly filter of
`$06`/`$10` and fails the foe filter of `$1e`. The same click on the same town before the
alliance posted `$1e` and ran to `$34a8` (129th, `run9.cmds`), which is the unallied control.
The `$1e` row proves the refusal at the pointer test only (no `$131be` in 14 passes over 3M
steps); the group lost one to two men to starvation in each run (food 0), unrelated to the order.

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
- pokes **one** random `$4d252` (tree array) record — if its `byte7 == $d` it becomes
  `$e + (byte10 & 3)` (a tree-state nudge; 0 of 204 records changed over one watched wrap, the array holds no type-`$d` record: effectively dormant, inferred);
- **rotates `$57fd0`** — `$57fd0 = ($57fd0 + 2) & 6`, cycling {0,2,4,6}
  (`$1ac5e..$1ac6a`, raw-verified 97th). `$57fd0` is the season *and* the
  mode-`$7c` settlement-heartbeat gate (economy.md §3a), so this rotation is
  what makes the heartbeat + loyalty/revolt system **transiently active in
  mission 1** despite its seed giving `$57fd0 = 4` at world-build. Observed
  rate: 118.44M steps per rotation (512 calls × ~231k, three writes watched);
- clears `$57fec` (the call count since the last change, 0..512) / `$57ff6` and ends any weather (`$4bb42`/`$4bb44` := 0).

No population, food or invention maths anywhere in it.

## The AI as modern pseudocode (73rd pass)

Everything above, decoupled from the 68000 and from the 2.6 Hz tick, as one
loop. This is the whole autonomous AI — there is nothing else.

```python
IDLE = 6                                           # group state 6: idle (the player's group sits in it, 6 of 6 snapshots)
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
        for k in (5, 4, 3, 2, 1, 0):               # the side's 6 groups, captain's last
            obj = group.groups[k]
            if obj.owner_side <= 0 or obj.link != 0:
                continue
            # 1. scripted campaign order, if this mission has one ($6762)
            if obj.state == IDLE and world.clock >= obj.wait_at + 20:
                if world.campaign_order.id == obj.camp_id:
                    obj.posture = world.campaign_order.sub or (world.tick & 3) + 2
                    slot.emit(world.campaign_order.type, obj.target.cell); break
            if obj.state not in (IDLE, 9): continue
            # 2. a small group goes to its own best town for men ($69b4(8))
            if obj.men < 22:
                tgt = nearest_own_lord(obj, word=FIELD_TROOPS, weight=lambda L: L.troops_field)   # troops_field > 1
                if tgt: slot.emit(GET_MEN, tgt.cell); break     # order $08, group state 3
            # 3. escort the captain's group when it is in support state $d
            g0 = group.groups[0]
            if k > 0 and g0.state == SUPPORT and g0.camp_phase == 4:
                slot.emit(MARCH, g0.escort_target.cell); break
            # 4. the captain's group: march at the nearest enemy leader ($661a/$68fe/$68ee)
            if k == 0 and obj.men - 4 > 0:
                tgt = nearest_enemy_leader(obj,
                        weight=lambda L: assessment[side][L.side].out >> 2)
                if tgt:
                    d = dist(obj, tgt)                                       # $68ee: D1 = own men - 4 (kept through $68fe)
                    score = (d // 2) * ((obj.men - 4) // 8 + 1) + d // 2      # the trip's food at the eating rate
                    if score <= obj.food:                                    # enough food to get there
                        group.state = 4
                        slot.emit(MARCH, tgt.cell); break        # -> group state 8

    for side in world.sides:                       # $6a3a: order executor
        slot = world.cmd_buffer[side]
        handler = ORDER_TABLE[slot.order_type]     # 26-entry jump table
        handler(world.groups[slot.commander], slot.param)   # e.g. commit_group_target
        slot.order_type = NONE; slot.param = 0     # consumed

    # $d322 + $3e06: rebuild per-side force totals, the armies eat
    force = [0]*5
    for L in world.leaders:
        force[L.side] += L.troops_field            # L.food goes to a second word ($57fba+2) the ratio never reads
    for side_groups in world.groups:
        for obj in side_groups.groups:
            if obj.owner_side <= 0: continue
            force[side_groups.side] += obj.men
            if eat_timer_elapsed(obj, assessment[group.side].eat_period):   # doubled while idle
                obj.food -= obj.men // 8 + 1                   # big army eats fast
                if obj.food < 0:
                    obj.food = 0
                    for man in obj.roster:                     # a starving army deserts
                        if rng() & 7 == 0: man.leave_group()

    # $d23a: force ratio $57fce (the AI never reads it back; $d2c8 tests it == 4 for victory)
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
    T.health -= dmg
    if T.health <= 0:                              # $5590
        roll = attacker.group.discipline - 2       # field_60 - 2
        kill = (roll == 0) or (roll not in (0,2) and (world.tick + attacker.phase) & 2 == 0)
        if attacker.target.encircled: kill = True
        if kill: T.to_corpse(decay=160)
        else:    T.rout()                          # scattered, survives
    # slow second channel, $5c80: health_cap[job] - (age-60)*4 < 0 -> removed
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

3. **Food is the only pacing knob, and the AI does not manage it.** An army
   eats `men/8 + 1` per period and the AI marches only if the trip's food fits,
   but AI groups are seeded with `$5fff` food and never take more, so the test
   does not bind. The player's armies start with a few hundred and must take
   food from towns ("What each order does"). A modern version would give the AI
   the same food economy and a utility model: commit when
   `P(win) * value > food and opportunity cost`.

4. **2.6 Hz, and compute-bound.** The whole sim — every entity, both renderers —
   runs in one thread at whatever rate a frame builds. Decisions land ~2.5 s
   apart and combat resolves in ~1–4 health/tick. A modern port decouples the
   sim tick from the render, runs the AI on its own budget, and can afford
   per-frame steering while keeping the coarse "issue an order every few
   seconds" cadence that gives PM its feel.

5. **Deterministic tick-count "RNG".** `$57fec` is just the low bits of the tick
   counter (`ai.md`), so the AI and combat replay identically from a save.
   Fine for the kill/rout roll's *flavour*, but it means no genuine uncertainty
   — a human learns the exact outcome of a given engagement. Keep the trick for
   cosmetic jitter; use a real seeded PRNG for anything the player can exploit.

6. **Rout, not attrition, decides the AI's fights — and rout is pinned.** The AI
   attacks at posture 4, which forces every kill into a rout, so its
   field combat almost never kills (the player chooses: aggressive kills); territory changes hands by **conquest** (`$539a` → `$550e`, economy.md §3) while
   armies just get scattered and re-form. A modern version would let the AI
   choose its posture from the situation so that its fights have consequences.

## Original names: the developer symbol table (133rd)

`DATA\SPRITE40.DAT` on the disk is not sprite data (the loader table `$e0c4` never names it, and nothing
in the image or on the disk does). It is a self-extracting GEMDOS program, 137,652 bytes once unpacked, and the
same game build as the loaded image: every one of the 28,942 unique 16-byte windows of its text except 6 sits in
the running RAM at the constant offset `$10a6`, and 2,855 absolute operands differ by exactly that offset. It still
carries the linker's symbol table (1,639 entries, 1,196 unique, 978 distinct routine starts), with each name cut
to 8 characters. `py/s40_symbols.py` unpacks it from the disk image (a port of the stub at file `$1c..$ba`) and writes
`powermonger_orig.sym`: a text symbol is at (text offset + `$10a6`); a bss symbol's value is bss-relative, so its
address is value + `$1c48e`. Rebuilt from the disk, no other input but one RAM snapshot to find the offset.

The names are the developers' own labels, so they answer "what did the authors call this", not "what does it do":
a label can be reused by neighbouring code, and 8 characters drop the tail (`wait_mee` is `wait_meet...`). Checked
against everything already proven, they agree almost everywhere (the exceptions are listed below): all 25 order executors, the group-order
table `$51538` (`_kings`), the object table `$51b66` (`_sprites`, 512 records of 50 bytes), the lords `$4e514`
(`_towns`) and houses `$4f916` (`_houses`), the cell buckets `$47970` (`_map_who`), the command slots `$58016`
(`_packets`), the key array `$2de6c` (`_key_on`) and shift flag `$2df8a` (`_shift`), the selected group `$57fd2` (`_the_cap`),
the armed order `$57fd4` (`_mouse_m`), `$57fd0` (`_season`, so the settlement heartbeat is the winter state `in_winte`
at `$157ba`), the conquest save `$3f2a0` (`_conques`), the control plane `$3f86c` (`_alts`), `$438ee` (`_block2`),
`$4be00` (`_shots`), `$4d252` (`_trees`), `$12d88` (`_command`, the startup parser), `$1962` (`its_a_ke`, the keyboard ISR's
key writer), `$df52` (`_load_co`), `$e2b8` (`decrunch`) and `$f898` (`_draw_it`). The order executors, in table order
from `$02`: `send_cap`, `xfer_men`, `get_food`, `get_men`, `go_home`, `send_att`, `send_inv`, `send_equ`, `drop_foo`,
`derank`, `set_leve`, `drop_equ`, `supply_f`, `send_tra`, `send_all`, `send_spy`, `select_c`, `pause`, `message`,
`restart`, `do_accep`, `do_seria`, `do_retir`, `do_rando`, `do_rejec`.

What the names changed:

- **Order `$08` is `get_men`, not besiege**; `$69b4` finds the best *own* lord for `D1` = 8 (men) or 6 (food)
  (live, "What each order does"). The `$28`/`$2a` modes are `wait_men` and `wait_mee(t)`.
- **`$14e4e` is `_test_en...`**, the word the protection check sets to `$2c` (the gate of the AI block, Save and
  Continue Conquest, "The campaign"): the label reads as the test's result, not as an AI switch. `$5809a` is `_show_de...`
  (show debug?), the dormant switch of the audit below.
- The debug monitor was stripped, not hidden: `_debug_m`, `_setup_d`, `_reset_d` and `_debug_s` at `$1ba62..$1ba70` are
  one-instruction stubs (`rts`), and nothing calls them.
- `$123c` is the label `shitpiss` (the startup string `_command` parses); the unhandled-exception labels are `fuckup`/`none` at
  `$1378` and mode `$0a` is `fucking_`. The linker's whole source file list is not recoverable (no module names).
- **`$4d252` is the tree array, not animals** (134th): the labels are `_trees` (`$4d252`), `_forests` (`$57f68`), `_birds` (`$4c5f4`),
  `_do_fore...` (`$4342`), `at_fores...` (mode `$44`), `at_works` (`$42`), and the census agrees (203 of 203 live entries on byte6 4 tree
  records, none on byte6 8 animals, `py/tree_census.py`; 10M live steps: 28 `$3e`, 24 `$44`, 25 `$42`/`$60dc` hits, 0 `$5ec6`, 3 trees
  felled). The gather modes `$3e..$46`/`$6a` are run by men of every job, not shepherds (shepherds are `$80..$88`); economy.md §2.
- `$1d70` is `_rerank`: it re-forms a group's ranks on every join and roster change (live, "What each order does"), not a
  "send everyone home" step.
- **The farmer cycle is modes `$0c`/`$0e`/`$16`/`$18`/`$24`** (labels `start_fl...`, `in_fligh...`, `at_farme...`, `at_farme...`,
  `farmer_f...`; 134th audit): `init_far` → walk `$10` → `$18` at the field cell (`42/43`) → `$0c` loads the `farm` entry of the
  spline table `$168ee` (`_flights`: `fp1..fp3`, `farm` at cursor `$50`, `pots` at `$76`, `eyes`) → `$0e` walks it (terminator `$7d26`
  = mode `$24`, walk home) → `$16` at home. Census: 275 of 281 live `$0e` men are farmers (11 snapshots); live from
  `m1_s0`, 40M steps: `$15042` 10, `$1507c` (the `food += 2`) 10, `$150b0` 11, `$14e56` 11, `$151c2` 11. So `$0e` is not a
  "patrol", `$18` not a "neutral garrison" and `$16` not a "disband"; `$2984` (`_set_peo...`) builds the village population, two men
  per settlement with a random job (`init_she/fis/far/mer`; one captain per lord of kind > 3), not garrisons (`economy.md` 5a, Proven).
  The farmer job is bit 0 of byte 7 (`$3c08` maps bits 0..3 to `$16`/`$4e`/`$5e`/`$80`), so the 126th's "one site sets flag
  bit 0" is `init_far` at `$2cd0`.
- **Mode `$68` is camp rest, not a marching column** (`rest_in_...`, `a_sitting`, `at_camp`, `in_camp`): 118 of 123 live `$68` men are
  byte6 14, the sitting category; marching men are `$06`/`$08`. `$35f4` (`_make_ca...`) is read to set group state 6 and ring the
  men around the lead in mode `$10`, prev `$20`, which settles into `$68` (static, one positive live match on `m1_ready`: the
  state-6 group's lead is `$68` at its camp marker). `$7c` is the winter state of a parked civilian (`in_winte...`), `$7e` a soldier
  staying at home, `$8a` a captain resting at his town (29 of 29 job 9).
- **Byte 33 is a carried item code** (`2 * (slot + 1)` for a boat or tool: `$0a` Boat, 8 Plough, 12 Pot ...; modes `$02` and `$8c`
  are 71 of 71 and 17 of 17 with bit 5 set and 33 = `$0a`: `boating`, not "hold position") and **byte 45 is health** (the captain
  panel prints `(45 >> 4) & 7` through `healthnames` at `$a2dc`, "Very Sickly" ... "Dead": 11 of 11 `callcap $912a` calls with a poked
  byte return the table's string, and 203 of 225 live persons sit exactly on their `$5ccc` cap, `py/health_check.py`;
  `$5c80` is `_add_str...`, which recovers it to the job's cap).
- **`$3f86c` is `_alts`, the altitude plane**, not a "control byte" or influence field: `$ffa6` (`_fill_al...`) accumulates a random
  walk into it, `$10410` (`_smooth_`) averages neighbours, `$10458` lays the rivers; graphics.md already reads it as the height
  source: poking a block of it raises a plateau in the redrawn terrain, 10938 pixels differ (`py/alts_render_check.py`). Likewise `$127e6` is the sound-event dispatcher (`_do_soun...`), `$178ae` the HUD group bars (food
  `112`, men `52`, the lead's health `45`; `callcap` 138 bytes written) and `$17878` the compass (51 bytes), not "render setup A/B".
- Modes `$56..$62` are labelled `fish_*`, `$80..$88` `shep_*`, `$4e..$54` `merch_*`: the job state machines of the people
  the panel calls farmer, merchant, fisher and shepherd (`jobnames` at `$a200`; a man's job is `7(obj) & $f`, 9 with bit 4
  set, as the panel routine `$9d6e` reads it). Census over seven snapshots (`py/job_census.py`, live persons only): every man
  in `$56..$62` is a fisher (93 of 93), every man in `$4e..$54` a merchant (115 of 115), `$80..$88` shepherds,
  `$0e` farmers (202 of 208), `$8a` leaders; `$10` and `$12` are shared by all jobs. So **`$60`'s `food += 4` is the
  fisherman's catch**, the lord's regular food income, and the old "regroup" labels of `$56`..`$60` named a fishing trip
  (ai.md: to the cell `42(A1)`, a gate scan for the catch, home, deliver); the group-order "muster" cell is
  unrelated to them.

The entity mode names (table `$14bb4`, mode `$xx` is the table offset, so it matches the documented mode numbers):

`$00` `out_of_b`, `$02` `in_fleet`, `$04` `in_rank`, `$06` `in_rank`, `$08` `lost`, `$0a` `fucking_`,
`$0c` `start_fl`, `$0e` `in_fligh`, `$10` `home_in`, `$12` `on_route`, `$14` `at_meeti`, `$16` `at_farme`,
`$18` `at_farme`, `$1a` `at_town_`, `$1c` `at_town_`, `$1e` `at_camp`, `$20` `in_camp`, `$22` `at_inven`,
`$24` `farmer_f`, `$26` `wait_foo`, `$28` `wait_men`, `$2a` `wait_mee`, `$2c` `set_figh`, `$2e` `at_goto_`,
`$30` `at_attac`, `$32` `fighting`, `$34` `shooting`, `$36` `goto_ani`, `$38` `fighting`, `$3a` `fighting`,
`$3c` `run_away`, `$3e` `head_for`, `$40` `head_for`, `$42` `at_works`, `$44` `at_fores`, `$46` `wait_at_`,
`$48` `scanning`, `$4a` `blocked`, `$4c` `captain_`, `$4e` `merch_ar`, `$50` `merch_st`, `$52` `merch_se`,
`$54` `merch_at`, `$56` `fish_at_`, `$58` `fish_at_`, `$5a` `fish_get`, `$5c` `fish_hea`, `$5e` `fish_arr`,
`$60` `fish_hea`, `$62` `fish_get`, `$64` `i_am_sha`, `$66` `at_goto_`, `$68` `rest_in_`, `$6a` `workshop`,
`$6c` `get_man`, `$6e` `at_equip`, `$70` `retreat_`, `$72` `pickup_f`, `$74` `pickup_f+7c`, `$76` `at_allia`,
`$78` `at_trade`, `$7a` `at_spy`, `$7c` `in_winte`, `$7e` `stay_at_`, `$80` `shep_arr`, `$82` `shep_go_`,
`$84` `shep_at_`, `$86` `shep_fin`, `$88` `shep_go_`, `$8a` `captain_`, `$8c` `boating`, `$8e` `fight_ge`, `$90` `townee_g`, `$92` `do_nothi`.

Unreferenced routines (`scratchpad/pm133/orphans.py`): of the 978 starts, 97 have no direct operand, literal pointer or
`jsr`/`bsr` target; reading every word within `$120` bytes of any symbol as a table offset leaves 14. Thirteen of those
are explained: four data labels (`qcom`, `com`, `x0`, `y0`), the fall-through label `xfer_com` (`$668c`, inside `_compute`),
the grid-walk quadrants `$fbb4`/`$fccc` (reached through the table at `$f986`) and six mode handlers (`shooting`, `run_away`,
`at_allia`, `at_spy`, `get_man`, `shep_arr`; the table `$14bb4`). One is left, `_how_far` (`$10cae`), a line-sampling
helper beside `_pospos`/`_mapline`/`_distanc`: 0 entries in 60M steps from each of two states, and its neighbours were not
entered in 120M either, so it is probably dead. The image has essentially no dead code; the earlier count of 117 orphans
came from a walker blind to the dispatch tables.

## The game's own text: names for the fields (139th)

The UI text tables name the fields the panel code reads, so each name is the developers' word for what the byte means (code read at the selector, plus the live check noted). The text sits in `$9000..$b000`; a
selector returns a string pointer in A5.

| field | selector | the game's names |
|---|---|---|
| group state, `76(A3)` = `0(sub)` | `$90ca`, 9-byte entries from `$9497` | 1 Waiting, 2 Get Food, 3 Get Men, 4 Meeting, 5 Going To, 6 In Camp, 7 Go Home, 8 Attack, 9 Invent, 10 Equip, 11 Pickup, 12 Supply, 13 Fighting, 14 Alliance, 15 Trading, 16 Spying (0 blank). Seen in 5 snapshots: 3, 6, 7, 8, 13; 6 is the player's resting group, 3 and 8 the AI's "get men" and "march and engage" |
| lord kind, byte 1 of the `$4e514` record | `$9c80`, words at `$a128` | 1 Village, 2 Hamlet, 3 Town, 4 City, 5 Capital, 6 Base (the layouts of `economy.md` "Buildings and town layouts": a Village is a single FarmHouse, a Hamlet a single FishHut, a Town 5 buildings, a City 9, the Capital 17 round a Tower, a Base a single Tower, mission 1's own lord) |
| building kind, byte 7 of the `$4f916` record | `$9ccc`, words at `$a15a` | 0 TownHall .. 12 Mine (`economy.md`) |
| group posture, `136(A3)` | `$90fe`, from `$9580` | 2 Aggressive, 3 Neutral, 4 Passive (value minus 2) |
| group aggression, `148(A3)` | `$90de`, from `$9530` | 0 PowerMonger, 1 Bellicose, 2 Domineering, 3 Aggressive, 4 Firm, 5 Quite Firm, 6 Weak, 7 Wimp; the panel shows PowerMonger instead when the flag word `$9218` is set (the panel opens with it set and clears it for any group that is not the side's first) |
| loyalty line | `$9116` | an unconditional `move.w #3,D0`: the line always reads "trusting" (`$95c1`; `callcap $9116` on `m1_s0` and `k5_s4` returns A5 = `$95c1` both times). The lord's loyalty is never displayed |
| speed word | `$9d52` | `(byte16 >> 4) & 3`: 0 hardly, 1 slowly, 2 tirelessly, 3 endlessly (a march speed of 30 reads "slowly", 32 "tirelessly") |
| job | `$9d6e` | `jobnames` `$a200`: 0 soldier, 1 farmer, 2 merchant, 4 fisher, 8 shepherd, 9 leader (bit 4 of byte 7 forces 9) |
| health | `$912a`, `$9e2c` | `healthnames` `$a2dc`, `(byte45 >> 4) & 7`: Very Sickly, Sickly, Very Weak, Weak, Well, Strong, Very Strong; Dead for a negative owner byte |
| age class, byte 14 | `$a4ae`, words at `$a508` | `(age - 12) / 20` capped at 4: Tender, Young, Mature, Ripe, Great; byte 14 is the man's age in years (`$2e1e` starts every man at 12 to 43), shown as a number by `$a4d6` |
| carried item, byte 33 / 44 | `$9da8` | Nothing, a Pike, a Sword, a Bow, a Plough, a Boat, a Pot, a Catapult, a Cannon (`$a242`) |
| side names | `$9e04`, `$a4ee`, 16 bytes each from `$582f9` | side 1 is the name typed at "What Is Thy Name Oh Lord" ("dave" in `m1_s0`), sides 2 to 4 are Jayne III, Jos XVIII, Harold II (live in `m1_s0` and `k5_s4`); "Philip II", the first of the four stored names, is the default for side 1 (inferred); the multi-player menu lists the four sides as White, Blue, Red, Yellow |

Other panels read the same way: the **house panel** (`$9ea1`: House, Town, People and Kingdom names, Food, Men "who are" a job, Near Forest, Stock), the **person panel** (`$a353`: name, rank and
kingdom, health, "lives in a <building> with <n>", job, the carried item, age and years old, "obeys <captain>"; the death line `$a50d` "has died at the Tender age of N, whilst faithfully in the service of ..."),
the mine panel (`$a677`, a Mine's metal "makes the <weapon>s"), the tree panel (`$a827`: A Stump, A Pine, An Oak, An Elm, An Ash, the season, "There are birds in the tree"), the animal panel
(`$a095`, selector `$9a12`: category 8 and the carcass category `$1c` read "Sheep", any other category "Cow": the animals of `ai.md` "Shepherds, animals and carrier pigeons" are sheep, and the category `$22` that their update loop also accepts is the cow, which nothing creates) and the pigeon panel ("Pigeon Flying to" a name).
Names of people, houses and towns are made by `$a9ce` (`_getname`) from a syllable table at `$aa5b` (`br ih ea pa rr op sc rv om br it o g fi ...`) keyed by the record offset: the same record always gets the same name.
The panel text is the place to look first when a field's meaning is in doubt: the 133rd pass's group-state and mode labels, the 134th's "Strength" row and this pass's building kinds all agree with it, and
it is what retired the "capital (kind 7)" reading.

## Hidden features audit (130th)

No cheat keys, debug commands or developer hooks found in the loaded game image. Evidence:

- **Keys.** The only code touching the key array `$2de6c` is the ISR writer (`$1962`), the camera loop `$13762`, the
  serial-link loops (`$1c34e`, `$1c39e..$1c3ae`) and the clear at `$10a6` (scan of the whole image for pointers into
  `$2de00..$2df6b`: 10 hits). There is no "any key" scan and no Ctrl/Alt/CapsLock/Help/Undo/F-key test; the only
  modifier state is the shift flag `$2df8a`, which only selects the shifted ASCII table in the getkey routine
  (`$19c2`, tables `$19e8`/`$1a7a`, UK layout). A live sweep of scancodes `$01..$72` (500,000-step holds in
  `pm78_settle`, reader hits counted with `hits`, RAM diffed against F1): only the four arrow keys change state
  (`$13824` block, each reader body 2 hits; left moved camera X 40 to 38, re-checked 130th). ESC reaches the link
  receive loop (`$1c34e`), which calls `$71ae` (link teardown): exercised, see "Serial-link states" under the command
  buffer. The send loop's ESC-plus-shift abort cannot fire, because `$1962` never stores the shift scancodes in the
  array. Name entry
  (`$cf46`, only entered while `$d03e` is set) treats only CR and BS specially and compares the name against nothing.
- **Joystick.** Polled every frame; joystick 1 lands in `$2c1b8`, which nothing reads (8 injected values per stick:
  RAM identical to the control).
- **Startup command line.** `$11b2` passes the string at `$123c` (one space) to `$12d88`. Called through `callcap`
  with A0 pointing at `S`, `M` and the static string on `pm123/win/m1_s0.snap` (local side 1; 3/3 as the code reads),
  it picks a side (`$57ffe`, a `$b940` draw, 0 becoming 1), fills the side table `$58038` with 6, 12, 18, 24,
  and sets the local command slot `$58016 + 6*side` to state 2 with its commander byte. `S` or `s` then makes the
  *previous* slot state 8 and the local slot 6 (`$5801a := 8`, `$58020 := 6`); `M` or `m` makes the local slot 6
  and the *next* slot 8 (`$58026 := 8`); anything else changes nothing. Slot 0 is never dispatched, so `S` with
  side 1 leaves a send-only local side. These are the serial-link roles of "Serial-link states": the string is the
  command-line twin of the MULTI PLAY button (order `$2c` sets `$71fe`, `$6a3a` then calls `$6eb6`, panel `$c`
  CONNECT sets `$2df6c`; `$6eb6` and the handshake were not read). With the static string neither role is set. Patching `$123c` in a running
  snapshot is useless (the routine runs once, before the game loads); to test a role, write the slot states.
- **Dormant word `$5809a`** (`_show_de...`, "Original names"; read at `$16640` in a loop over the entity table, written nowhere by an absolute
  operand; 0 in both snapshots). Poking it to 1 raised that loop's `$16738` calls from 54 to 94 per 500k steps and
  `$e6ee` marker draws from 27 to 47, and on 4 of 8 samples added 24-26 bytes of extra dots to the minimap: a
  "draw all sides' markers" switch. Nothing in the image sets it (131st, static; no live write was attempted):
  the only absolute operand of `$5809a` is the read at `$16640`; a byte scan of the RAM image finds the longword
  `$0005809a` once (that read) and no pointer to `$58094..$58098` other than the six `$58098` word accesses; every
  bulk copy or clear that could sweep it starts higher (link/save blocks `$580a0..$58368` at `$6fa2`, `$7150`,
  `$b866`; the campaign pick `$1140e` copies 333 bytes to `$580a6`) or lower and stops short (`$58058` clears 16
  words, `$58042` is a 12-entry word table, `$5801c`/`$58016` are the 6-byte command slots, side 0..5). The save
  game (`$3f2a0`, 196 bytes of conquered lands) is not RAM-block data. Treat it as an unset debug flag: reachable only
  by a patch, like `$123c`.
- **Developer leftovers.** `d:\samples\ste.tos` (`$123e`) and `d:\samples\qaz.spl` (`$1251`), no code references; the
  live save-disk header at `$1bb0e` (checked by `$1bd64` against `POWE`) carries the text "PLEASE STOP HACKING THIS GAME
  OR IT MAY BE THE LAST ST PRODUCT FROM BULLFROG"; three MFP vectors (`$120`, `$138`, `$13c`) set the palette to
  `$700`/`$770`/`$007` (stray-interrupt flashes, never fired in 2M steps); vector 5 (divide by zero) points at an
  `rte`, so a zero divide is ignored.
- **Data loads** (`$e0c4`, "Original names"). The table holds 16 resources (`TEXTURES`, `QAZ`, `SPRITE16`, `SPRITE8`,
  `SPRITE24`, `SPRITE32`, `CAP_SPR`, `BITMAP`, `CAPGRAPH`, `FX`, `MAP`, `MAPDATA`, `END_PIC1`, `END`, `LOSE`, `WIN`, index 0..15) and
  the loader `$df52(index)` copies a resource from its cache slot (`$e040`, filled by `$dff8`) or reads the file (`$def0`,
  `$d4d2`, `$e2b8` decrunch). Its 17 call sites push literal indices: startup loads 9 (`$11c0`) and the sprite sets 0, 2, 3, 4, 5 (`$12f70..$12fa0`),
  the briefing 10 and 11 (`$11224`, `$113d0`), the land build 1 and 8 (`$187e8`, `$13d0a`, `$18804`), the end screens
  15, 14, 12, 13 (`$1a524..$1a66e`). Indices 6 (`CAP_SPR.DAT`) and 7
  (`BITMAP.DAT`) are not on the disk; 6 has no caller and 7 only the fixed-map branch (`$13c0e`, `$58148 < $100`, which
  no land takes). Live, `hits` from the build's `$13b9a` on `pm67_ok_pre`: `$df52` 2 hits (indices 1 and 8, both from the
  cache, `$def0` 0), `$13c0e` 0; 30M further steps load nothing (`scratchpad/pm133/land0.cmds`). `DATA\SPRITE40.DAT` is the
  developer-symbol build above. `NuDATA/MAP0000.DAT` (`$e38a`) and `B_FLOOD.ECH` (`$1adaa`) have no reference of any kind (no
  literal, no PC-relative `lea`, none in the whole-image listing): leftovers of the fixed-map and sound code. `DATA\SPRITE8.DAT`
  at `$1bafc` is a probe file: `$1bd0e(index)` opens it (`$d574`) when the resource is not cached and `$1bec8` asks
  for "PLEASE INSERT THE POWERMONGER DISK" until the open succeeds (read from the code, not run).
- **Link chat (`$26`).** Reachable in a normal game: GAME panel button `$131` SEND MESSAGE (`$7878`) calls `$d194`,
  which sets `$d03e := $fe`; the main loop (`$13750`) then hands every frame to `$cf46`, which branches at `$cf4e`
  to `$d13e`: `jsr $19c2` (getkey), and for a key posts order `$26` with the character as the slot parameter into
  the local slot (`$d14c`, `$d152`) and echoes it into the edit buffer through `$d162` (CR and BS only). Held `a`
  (`kbd 1e`, held past the main-loop poll: a make and break sent together are erased by the ISR before getkey
  sees them) left the local slot `01 26 00 61 02 00` (1/1). The receiving half `$6dd0`, for a slot whose
  commander is not the local side, calls `$d0dc` and opens panel `$16`, "message from <lord name>" with the
  character on its second row: a slot `02 26 00 58` in state 4 gave 1 `$6dd0`, 1 `$d0dc`, 1 `$affe` and an `X` on
  the panel (`scratchpad/pm132/chat.cmds`; `chat_message.png`). A character from the local side is not shown on
  its own message line (`$6dd0` tests `cmd == $57ffe` first). How the mode is left was not traced (`$d03e` is cleared at `$78a0`/`$78be` by the panel `$c` buttons and at `$6f04`, `$73c4`, `$abf6`, `$ccf0`, `$cffc`).
- **The developer symbols add no hidden command.** The only labels that read as debug are the four `rts` stubs at
  `$1ba62..$1ba70`; the `_test_*` words belong to the protection check (`_test_en...` `$14e4e`, `_test_wh...` `$57ff8`, the random
  question index set at `$b430`; `_test_se...` at `$2df9a` has no reference), `_protect` is `$5809c`, the page number the briefing asks about.
- **Not covered:** the link handshake (`$6eb6`, panel `$c`/`$12`); the crack's own title/intro screens and `MREP`; indirect
  writers of any flag. Scripts and raw output: `scratchpad/pm130/audit/` (`keysweep.py`, `sweep_diff.py`, `rw_census.py`);
  the reachability walk `reach_scan.py` there misses dispatch tables (it called `$b892` unreferenced although `$b3d0` calls
  it), which is why "Original names" counts unreferenced routines from the symbol starts instead.

## Open threads

- **Economy / population / invention — see economy.md.** Not in the per-tick path: `$1abaa` is sound, `$3e06` is the armies eating, the health indicator, the
  animals and the carrier pigeons (`ai.md` "Shepherds, animals and carrier pigeons"), `$d322` is force-totalling. The land is made by `$10d1e`/`$ffa6`/`$2266`/`$ac20`;
  `$2984` then gives every settlement its two men and each man a job, once per build (`economy.md` 5a, Proven: a build runs it once, 8 of 8). Growth after that does not exist
  (a revolt, `$550e`, only moves a lord and his settlements). Still unmapped: `$238c`, which builds each side's army (leader, captain group, soldiers; read, not differentially
  tested) and `$2906`, the assessment seeding.
- **The AI on a live enemy (122nd).** All 25 natural `$661a` primary
  decisions in the four 200M-step runs (lands 0/5/25/60: 8/7/4/6) were
  captured at `$662a`/`$6632` (`scratchpad/pm122/dec/`, `parse.py`). `$68fe`
  found a target every time, and `$68ee`'s cost (4-66) was always far inside
  the group's food `112(A1)` (24,218-24,671, i.e. the `$5fff` seed of
  `$26c4` barely eaten), so every decision issued the attack order
  (posture `136(A1) := 4`, `$67ee(12)`); the not-enough-food fallback `$69b4(6)` and the
  no-target path `$69b4(8)` never ran. Targets were leaders of every other
  side, the player's (side 1) in 6 of 25, usually with a small `troops_field`
  (0-18). The food test does not bind at these values: AI armies never go hungry.
- **Combat — mechanism closed** (73rd, see "Combat" + `ai.md`). The `$5590` kill
  branch runs naturally on later lands (121st). Remainder: the `$5c80`/`$5bd2`
  wear path (never fired in 800M later-land steps). Projectile type is byte6:
  `$28` (40, an arrow, from a bow) is common; `$12` (18) never appeared.
- **Land setup**: there is no mission-file grammar (campaign lands are the
  195-entry `$3f428` table, "The campaign" above). Still unreached: the
  fixed-map branch (`$58148 < $100` → `$df52(7)`), which no campaign entry
  uses (possibly Load Data Disk), and the per-objective `obj_camp_id` fields,
  which only the dead `$67d0` hook reads.
- Diplomacy ("Diplomacy" above): an alliance offered naturally by clicks with
  organically-earned goods (no register pokes at all) is proven up through the
  tribute forming — order `$10` genuinely fills a group's `carrying[]` from a
  real stockpile (127th) — but the envoy reaching its target without
  interception is not yet observed: two independent natural corpora (123rd
  forced-goods, 127th fully organic) both had it die in unrelated combat
  first. Try an escorted envoy (a second group clearing the corridor first) or
  a land snapshot early enough that territory hasn't solidified. The panel-`$1a`
  branch (an envoy arriving at the player) is static only.
- `$3c08` (rout / besiege-fail group restructure; order `$0a`, the HOME icon)
  — first-look only.
- The player's orders ("What each order does"): each is named from 1 run. Not
  yet seen: `$04` (needs two captains), `$0e` on a lord with a WorkShop (a campaign land
  whose player lord is of kind 3 or 4, `economy.md` "Buildings and town layouts"), `$10`/`$1c` on a pile. Driving a revolt
  on purpose: take a lord's food (order `$06` on his town is refused, it is not
  ours; a trade adds +8) and then plant a spy to pulse him.
