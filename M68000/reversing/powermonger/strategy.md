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

**This layer has no economy, build or recruit reasoning.** The autonomous
decision is: *"march the army at the nearest enemy leader, if I have more than
~4–22 men and the target is inside a range budget that scales with my army
size."* Reinforcement is handled at the entity level (mode `$1a`, `ai.md`);
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

## Combat (72nd pass — pipeline traced, casualty maths static)

The 70th/71st passes flagged "`$5778` combat resolution" as the biggest open
gap and assumed it was a battle resolver with odds and casualty rolls.
**It is not.** PowerMonger has no discrete battle resolver. Combat is four
loosely-coupled mechanisms, all running at the entity level in `ai.md`'s
`$14b62` tick:

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

### 4. Attrition — `$5c80` upkeep → `$5bd2` removal

`$5c80` runs once per tick for every moving or garrison entity:

```c
int pm_upkeep(obj *A1) {
    int surv = t_survivability[A1->flags & 0x1f];       // table at $5ccc, 18 bytes
    int wear = A1->byte14 - 0x3c;                        // byte14 doubles as a wear counter
    if (wear >= 0) {
        surv -= wear * 4;
        if (surv < 0) pm_unit_remove(A1);               // -> $5bd2, the unit is spent
    }
    int morale = (int8)A1->byte45;
    if (morale >= 0 && surv > morale)
        A1->byte45 += (g_tick_rng & 1);                  // morale creeps up, 1-bit "random"
    return surv > morale;
}
```

`t_survivability` (`$5ccc`, indexed by `flags & $1f`): the flag low bits are a
small enum, not a bitfield — values `0/1/2/4/8/16` map to `90/82/69/79/72/95`.
`$5778` stamps an engaged garrison's flags to `$11` (17) → `t_survivability[17]
= 0`, so an engaged unit has zero survivability and stops recovering morale;
it is removed the moment its wear counter (`byte14`) crosses `$3c`.

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

### Measured — the forced mission-1 fight (72nd pass)

40M-instruction traced resume from `pm71_slot4.snap` (slot 1 `byte4` forced to
4 once; ~166 sim ticks):

| routine | hits | reading |
|---------|-----:|---------|
| `$6522` decide | 166 | once/tick |
| `$661a` primary-slot decide | **1** | the one forced decision; never re-armed |
| `$68fe` find enemy leader | 1 | picked the nearer of the two `$4e514` sub-leaders |
| `$6a3a` executor | 166 | once/tick |
| `$56a6` engage | 9 | the armies did make contact |
| `$5778` bookkeep | 2 | gated hard on `flags & BIT6` + `d < $fff` |
| `$15302` reached-enemy | 41 | men repeatedly closing on enemy positions |
| `$57f0` spawn projectile | 3 | three shots fired |
| `$1d70` capture settlement | **5** | five territories changed hands |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5bd2` unit removal | **0** | **no field casualty in 166 ticks** |
| `$5c80` upkeep | 1015 | ~6 entities/tick |

So a forced attack in mission 1 produces engagement, a few projectiles, and
territory capture — but **zero battlefield deaths** over ~166 ticks. Field
attrition in PowerMonger is genuinely slow: it needs an engaged unit's `byte14`
wear counter to climb past `$3c` while `t_survivability[flags]` stays low, and
in a brief skirmish that threshold is never reached. The decisive mechanic in a
short fight is **capture** (`$1d70`), not casualties. The casualty formula in
mechanism 4 is decoded from the disassembly only — **not trace-confirmed**,
because no `$5bd2` fired.

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

## Open threads

- **Trace the AI from a live enemy.** Still needs a later campaign mission where
  the enemy captain's command slot reaches `byte4 == 4` on its own. The 72nd
  pass ran the forced fight *for 166 ticks* (not a single-shot poke) — that gave
  the engagement / projectile / capture pipeline but still no autonomous
  `$661a` re-decision and no `$5bd2` casualty. To measure `$68fe` target
  choice and `$68ee` budget maths across repeated decisions, either re-arm
  `byte4` every N ticks with a watch-poke, or reach mission 2+.
- **`$5778` combat — reclassified, not closed.** Pipeline (contact → `$56a6` →
  projectile `$57f0` → attrition `$5c80`/`$5bd2` → capture `$1d70`) is decoded
  and mostly traced. Still static-only: the `byte14` wear-counter increment
  during combat (what raises it, how fast), the projectile-impact → removal
  link, the `t_survivability` enum meaning (terrain? posture? weapon tier?),
  and the role of invention level in the projectile `type` byte.
- `$67d0` campaign hook: decoded (above). Open: the mission-file byte layout
  that `$13b9a` / `$10d1e` parse to seed `$67d0` and the per-objective
  `camp_id_268`.
- `$580a6` per-side assessment block: the `$2200`–`$3500` writers, what `+16`
  (the targeting weight) and `+6` (the relationship bits `$4c2a` clears) mean,
  and whether diplomacy ever flips the friend/foe sign `$3154` uses.
- `$3c08` (order `$08` besiege setup) and `$30fe`/`$39d4` (order `$10` regroup)
  — first-look only.
- Economy: settlement population / food / sheep growth, where invention is
  modelled and unlocked, the muster/regroup group modes `$56`/`$5a`/`$5c`/`$60`
  (`ai.md`). None of this is in the strategic layer — it must be in the
  `$3e06`-adjacent or `$2200`–`$3500` code, still unmapped.
