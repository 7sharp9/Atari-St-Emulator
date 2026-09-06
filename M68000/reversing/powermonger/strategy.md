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
$130b0  jsr $1abaa   ; housekeeping: phase accumulator; gates $57fec++ and the sound LCG
$130b6  jsr $17878   ; render setup B (rotation row-table select)
$130bc  jsr $165b2   ; water / terrain animation for the selected group
$130c2  jsr $14b62   ; << the entity iterator (ai.md)
$130c8  jsr $6a3a    ; << order executor: consume $58016, drive group state + lead mode
$130ce  jsr $7a56    ; sprite / HUD compositor
$130d4  $ff9a += $12f56 ; ...andi #$3f... clr $12f56 when it wraps  ; AUTO-ROTATE hook
$130f6  jsr $d23a    ; $57fba -> $57fce UI mood ratio
$130fc  jsr $7202 / mouse-command dispatch ($13212 world, $13892 hit-test, ...)
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
typedef struct pm_leader {
/* 0*/  u8   nation;                  // side id 1..5; 0 = empty slot (loop terminator, array ends $4f914)
/* 1*/  u8   _b1;                     // ?? (== 3 for both mission-1 sub-leaders)
/* 2*/  u16  _w2;                     // ??
/* 4*/  u16  cell;                    // packed {x: bits 0-5, y: bits 6-12} of the lord's position
/* 6*/  u16  troops_reserve;          // $d322: += into $57fba[side].word2 ; $15e18/$15760: += 4 on arrival
/* 8*/  u16  troops_field;            // $d322: += into $57fba[side].word0 ; sieges/$5bd2 decrement it; $68fe scores vs it
/*10*/  u8   _b10[4];                 // ??
/*14*/  u16  nation_off;              // back-link: byte offset into $4f916 for this lord's home settlement
/*16*/  u8   _b16[7];                 // ??
/*23*/  u8   msg_count [1];           // $16376/$159a4: "under attack" / order message counters (indexed run)
/*24*/  u8   speech_ctr[8];           // $159de: divu #6 index -> speech-line countdown table
} pm_leader;                          // sizeof 32

// ---- nation / settlement record : $4f916, 18 bytes ------------------
typedef struct pm_nation {            // object.nation_off and leader.nation_off index this
/* 0*/  u16  _w0;                     // ??
/* 2*/  u16  chain_next;              // $5cde: settlement chain (walk while byte7 != 7)
/* 4*/  u8   _b4;
/* 5*/  u8   owner;                   // commander colour holding the settlement; copied into object.owner ($1501a,$5c2c)
/* 6*/  u8   _b6;
/* 7*/  u8   kind;                    // $5cde: == 7 terminates the settlement walk (capital?)
/* 8*/  u16  linked_obj;              // object-record offset of the settlement's own marker
/*10*/  u8   _b10[2];
/*12*/  u16  dest_cell;               // mode $52: the nation's ordered destination (packed cell)
/*14*/  u16  leader_off;              // byte offset into $4e514 for this settlement's lord
/*16*/  u16  _w16;
} pm_nation;                          // sizeof 18

// ---- per-side assessment block : $580a6, 5 x $20 bytes -------------
typedef struct pm_assess {            // index by side id: $580a6 + side*$20
/* 0*/  u16  decay_period;            // $3e06: objective budget decays every this-many ticks
/* 2*/  u8   _b2[4];
/* 6*/  u8   relation_bits;           // $4c2a: bclr peace bit per other side; $3154 friend/foe sign source
/* 7*/  u8   _b7[8];
/*15*/  u8   assess_in [1];           // $311a writes here: clamped 15(A5,other*$20) + delta, range $ff9c..$64
/*16*/  u8   assess_out;              // $68fe reads (16(A4, target*$20 - 1)) >> 2 as the targeting weight
/*17*/  u8   _b17[15];
} pm_assess;                          // sizeof $20; $2200-$3500 cluster owns the rest

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
`byte1` (order type), clears it, and `jmp`s a 26-entry table at `$6b5c`:

| type | handler | reaches | effect |
|------|---------|---------|--------|
| `$06` | `$6bec` | `$3154` (D3=3), then `$3248` | scripted move |
| `$08` | `$6c18` | `$3c08` | besiege — group state 3 |
| `$0c` | `$6c4a` | `$3154` (D3=9) | **march & engage** |
| `$10` | `$6c98` | `$30fe` + `$39d4` | regroup / muster |

`$6888` maps order type → the group state it produces: `$06`→2, `$08`→3,
`$0c`→8, `$0e`→9, `$10`→10, `$1a`→`$c`, `$1c`→`$f`, `$1e`→`$10`. These line up
with the group-state → entity-mode table in `ai.md` (state 3 ⇔ besiege modes
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

`$57fce` is **UI only** everywhere it was traced (`$16bb8`, `$188dc`, and
`$d2c8`'s `jsr $1a5b2` when ratio ≠ 4). `$6522` never reads it. The knob the
autonomous AI actually turns is the per-objective budget `112()` and the
per-side assessment weight in `$580a6`, not this global ratio.

`$580a6` — 5 × `$20`-byte per-side assessment blocks — is written all over the
`$2200`–`$3500` cluster and from `$139dc`/`$13a3e`/`$13b20` in the sim tick.
That is a further subsystem (the spy-report / relationship layer); `$68fe` only
reads one byte of it (`+16`, `>> 2`) as a targeting weight. Not decoded here.

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
reference to the address `$67d0` is the `lea $67d0,A4` inside `$6762` itself).
It is the slot the **mission-file loader** (`$13b9a` / `$10d1e`, run on the
briefing OK click) writes when a mission script wants to force a specific
lord's move at a specific phase — a besiege (`orderType` even, → `$6b5c`
dispatch) with an optional deterministic sub-mode. In "Between Pages 1-5" it
stays zero, so the tutorial's enemy never receives a scripted order and the
hook is inert. The per-objective `camp_id_268` field that it matches against is
also seeded by the same loader from the mission file's objective list.

This is the only path by which the AI can issue anything other than "march at
the nearest enemy leader" — there is still **no build / recruit / invention
reasoning** in the strategic layer; those orders, if a campaign uses them, come
through `$67d0`.

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

### 5. Settlement capture — `$1d70`

The besiege modes (`$28`/`$2a`, `ai.md`) grind a settlement's garrison count
down while the group stays in state 3; at 0 they call **`$1d70`**, which
transfers ownership *and* procedurally renames the territory (it walks a
`'C'`-delimited name-fragment table at `$1e9e`, indexed by the capturing
group's `44(lead)` field and the target's own name bytes).

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
| `$1d70` capture settlement | **15** | the decisive mechanic |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5c80` upkeep | 2136 | ~8 entities/tick |

**Reading.** A forced attack in mission 1 produces engagement, a handful of
projectiles, ten **routs** (units scattered by `$3c08`, none killed), and
fifteen **captures**. So territory changes hands and armies get broken up, but
almost nobody dies on the field — because mission 1's group discipline
(`field_60 == 4`) pins the `$5590` roll to "rout", and the wear channel is far
too slow for a 276-tick fight. The 72nd pass's "no casualties" verdict was right
about deaths and wrong about outcome: **routing is what combat does here**, and
it fired ten times. The kill branch of `$5590` and the whole `$5bd2` wear path
remain decoded-not-traced.

Re-arming the *primary objective slot* directly (rather than `byte4`) to force
repeated `$661a` decisions across a moving front, or reaching mission 2+ with a
disciplined enemy, is still what's needed to exercise the kill branch and to
histogram `$68fe`/`$68ee` across many decisions.

## RNG and determinism (72nd pass)

There are **two** "random" sources and neither is a seeded PRNG in the AI path:

- **`$57fec`** — a free-running 16-bit counter, `addi.w #$1,$57fec` in `$1abc0`
  (reached from `$1abaa`, once per tick, gated by a phase accumulator so it
  advances a little under once per tick). Every AI use takes low bits only:
  `& 1` (morale creep, `$5c80`), `& 3` (campaign sub-mode, `$6762`), `& 7`
  (a speech-line pick, `$3e06`/`$3f08`). Because it is just the low bits of the
  tick count, **the AI is fully deterministic** given the tick number — there is
  no seeding, no entropy, and a save/restore at the same tick replays
  identically.
- **`$57ff6`** — a genuine 13-bit LCG, `x = (x * $24a1 + $24df) & $1fff`,
  stepped 16× per housekeeping pass in `$1abc0`. It feeds only the **sound**
  driver (`$ff9e`-relative table lookups), never the AI or combat.

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

The briefing OK click (`$b814`, README) copies a mission descriptor
`$584c4 → $580a0` and calls **`$13b9a`**, the world-build dispatcher:

```
$13b9a  ff9c := $15 ; jsr $fe04 (zoom index 4)      ; render geometry
        $51536 := $12                               ; group-order table live count
        $57fd0 := ($58146 & 3) * 2                  ; a rotating sub-phase seed
        if ($580a0 != 0)  jsr $10d1e                 ; <- DEFINED mission -> parse it
        else              jsr $df52 / $10a46 / $10410 ; <- procedural fallback
        jsr $2266 / $ac20 / $1073c / $10058 / $4672  ; nation + placement + terrain init
        jsr $2984 / $238c / $2906                    ; objective-slot + assessment seeding
        ...
        $57fee := 1 ; $57ff0 := 1 ; ff9a := $fff0    ; speed = normal, camera reset
```

**"Between Pages 1-5" takes the procedural path** — `$580a0` is a small
descriptor, and `$10d1e` fills a parameter block from the RNG, not from a byte
script:

| addr | filled with | meaning |
|------|-------------|---------|
| `$58146` | `$12c9a` | world RNG seed |
| `$58148` | `$5809c` override, else `rand & $7fff + $1500` | map size / richness; `< $2000` ⇒ "small" preset |
| `$5814a` | `(rand & 7) + (small ? $a : 2)` | lord count (≈10–12 small, 2–9 large) |
| `$5814c` / `$5814e` | `rand & $3f` / `rand & $7f` | seed cell coords |
| `$58150` | `(rand&3) + 2 + (small ? $a : 2)` | settlement count knob |
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

A **defined campaign mission** would ship `$580a0` non-zero pointing at a real
byte script, `$10d1e` would parse that instead of rolling dice, and the
objective-setup calls (`$2984`/`$238c`/`$2906`) would seed `obj_camp_id` and the
global `$67d0` from it. That path is **not exercised by this entry point**, so
`$67d0` stays zero and the campaign hook stays inert — consistent with the 72nd
pass. Reversing the real mission-file grammar needs a mission that uses it (a
later "Between Pages" or the Conquest campaign proper), not mission 1.

## What `$1abaa` actually is — sound + ambient, not economy (73rd pass)

`$1abaa` (`$130b0` in the tick) was a candidate for the economy/growth engine.
It is not. It is a phase-gated block that: steps the 13-bit sound LCG `$57ff6`
16× and mixes `$ff9e`-relative sample tables into the audio buffers
(`$1ba3e`/`$1a856` are sound); and, once per LCG wrap, pokes **one** random
record in the `$4d252` array (stride 12, count `$4e512 / $c`) — if its `byte7 ==
$d` it becomes `$e + (byte10 & 3)`. `$4d252` is the **wildlife / ambient** array
(sheep, etc.); the poke is a cosmetic behaviour nudge, and the rest of the block
is a "sheep bleats / bird calls" ambient trigger. `$57fec` (the tick-count
"RNG") and the animation phase `$4bb42`/`$4bb44` are also serviced here. No
population, food or invention maths anywhere in it.

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
  event-driven (via `$1d70` capture → `$25d6`) or live in the setup-time
  cluster `$2984`/`$238c`/`$2906`/`$ac20` which may also run periodically —
  none of that code is mapped. This is the largest remaining subsystem.
- **Trace the AI from a live enemy.** Still needs a later campaign mission where
  the enemy captain's command slot reaches `byte4 == 4` on its own. The 72nd
  pass ran the forced fight *for 166 ticks* (not a single-shot poke) — that gave
  the engagement / projectile / capture pipeline but still no autonomous
  `$661a` re-decision and no `$5bd2` casualty. To measure `$68fe` target
  choice and `$68ee` budget maths across repeated decisions, either re-arm
  `byte4` every N ticks with a watch-poke, or reach mission 2+.
- **Combat — mechanism closed** (73rd, see "Combat" + `ai.md`). Static-only
  remainder: the kill branch of `$5590` (needs a disciplined attacker group),
  the `$5c80`/`$5bd2` wear path (needs a long fight), and the projectile
  `type` → invention-level mapping (only `type $12`, the area-effect one, seen).
- **Mission-file grammar** — the procedural generator (`$10d1e`/`$2266`) is
  sketched (above). The real byte-script path (`$580a0 != 0` → `$10d1e` parses
  it; objective setup `$2984`/`$238c`/`$2906` seeds `obj_camp_id` + `$67d0`) is
  unexercised by "Between Pages 1-5" and needs a mission that uses it.
- `$580a6` per-side assessment block: `$311a` writes `+15`/`+16` (clamp
  `$ff9c..$64`, a signed −100..+100 relationship), `$4c2a` clears `+6` peace
  bits, `$3154` reads the sign for friend/foe. The `$2200`–`$3500` seeders and
  the per-tick incremental writers (`$139dc`/`$13a3e`/`$13b20`) are still
  unmapped — this is the diplomacy/spy-report subsystem.
- `$3c08` (rout / besiege-fail group restructure) and `$39d4` (order `$10`
  regroup march) — first-look only.
