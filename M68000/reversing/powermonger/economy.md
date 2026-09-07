# PowerMonger ST — the economy: manpower, livestock, settlements, invention

Reverse-engineered 74th–75th pass, continuing `ai.md` / `strategy.md`. Those two
files cover the autonomous military layer and confirm it has **no** economic
reasoning; this file covers what the economy actually is and where its numbers
live. Same method: disassembly of `scratchpad/pm70_iso.ram` (game image at its
absolute addresses, base `$1050`), block traces, and field `watch`es driven from
`scratchpad/pm71_run1.snap` / `pm74_late.snap` ("Between Pages 1-5", the
procedurally-generated tutorial mission).

**Evidence level (91st).** See `ai.md` "Evidence taxonomy". The **negatives in
this file are Observed, not Proven**: "no growth term", "no research counter",
"strict conservation of soldiers", "invention never advances" were each checked
by tracing mission 1 for a bounded step budget (≤400M) with field `watch`es on
the relevant counters and finding zero unexplained increments — not by proving
no such code path exists. The army-supply *mechanism* (`$61f8`/`$638c`) is
Corroborated (static + a forced-delivery trace); its dormancy in mission 1 is
Observed.

**75th-pass summary.** All five pass-2 questions closed. The livestock payoff is
`+1` to one of `pm_leader.goods[0..7]` (§2a) — eight per-lord counters, one for
each of Pike/Sword/Bow/Plough/Boat/Pot/Catapult/Cannon, shown in the lord panel,
shuffled between lords by porter units (§2b), and spent to equip and upgrade
field units (§2c). "Invention" is that upgrade step (`$638c`), not a research
timer. Manpower is a **separate** ledger with **no growth term** (§6) — it is
conservation of soldiers minus a per-settlement upkeep drain (`$163b8`). The
"periodic settlement update" is entity mode `$7c` (§3a). The `$163ea` write
aliasing is characterised and benign (§3b).

## Headline

**PowerMonger has no single "economy tick".** There is no routine that, once per
period, grows a population number and checks a food balance the way a 4X game
does. The economy is a set of loosely-coupled mechanisms, most of them driven at
the entity level by the same `$14b62` FSM that runs everything else:

| subsystem | where the number lives | how it moves | status |
|-----------|------------------------|--------------|--------|
| **manpower** (a lord's available men) | `pm_leader.troops_reserve` = `$4e514`+6, `.troops_field` = +8 | soldiers walking home add 2–4; a disbanding group returns a discipline-scaled slice; recruiting subtracts one; each settlement pulse drains one (`$163b8`); a battlefield/garrison loss subtracts 1 | **traced** |
| **goods** ("livestock", "invention" and the granary line the player sees) | `pm_leader` bytes **24..31** — 8 counters, one per item type (Pike, Sword, Bow, Plough, Boat, Pot, Catapult, Cannon) | a completed herd-drive credits `+1` to one counter (`$60dc`), heavily throttled; porter units shuttle counters between a nation's lords (`$159de`/`$159a4`); the army-supply subsystem spends them to equip/upgrade field units (`$6352`/`$638c`) | **traced** |
| **livestock** (the herds that feed the goods counters) | `$4d252` herd array + `$57f68` herding ops + `$4c5f4` markers | shepherd FSM (modes `$3e`→`$44`→`$42`) drives an animal home, marks it consumed (`breed:=$d`), credits the goods counter; `$4342` only animates the on-screen marker | **traced** |
| **settlements** | `$4f916`, 18-byte records, ≤240, chained per nation (+8) | built at world-build (`$2fc0`/`$2984`); a per-settlement heartbeat is entity **mode `$7c`** (`$157e6`); ownership changes on capture (`$1d70`/`$25d6`) | **traced** |
| **weapon grade** ("invention") | `pm_object` byte 44 (items 1–6) / byte 33 (items 7–8) | stamped at spawn (`6` for leads, `0` for tutorial followers); **advanced by the army-supply subsystem** (`$638c`: `if slot < delivered_item: slot := delivered_item`) — no research timer | **traced (mechanism); dormant in mission 1** |
| **passive population growth** | — | **does not exist** — manpower is strict conservation-of-soldiers (see §6) | **traced negative** |

Manpower and goods are **two separate ledgers**. Goods never become soldiers and
soldiers never become goods. Over a ~1-billion-instruction watched resume from
`pm74_late.snap` (`pm75_big.err`) plus a 135M cross-check (`pm75_w1.err`), every
`troops_reserve` / `troops_field` write came from the fixed set in §6; no counter
grew a lord's manpower on its own, and **no lord's side byte was written once**.
The 74th pass's "delivery payoff not observed" is resolved:
the payoff is a `+1` to a goods counter, and in the tutorial the food-tier herd
throttle (`$580a6[side].word8 + $2000` ≈ 8200 ticks, ~1 game-hour) is why the
400M window saw none complete.

## 1. The manpower ledger — `pm_leader.troops_reserve` / `.troops_field`

This is the closest thing PM has to a population number, and it is the one the
strategic layer actually reads (`$d322` sums both fields per side into
`$57fba`; `$68fe`/`$69b4` score enemy leaders on `troops_field`).

```c
// $4e514, 32-byte records (ai.md / strategy.md: pm_leader). Economy fields (75th):
/* 0*/  u8   side;             // owning commander (1..4); $550e rewrites it on a defection
/* 1*/  u8   order_class;
/* 2*/  u16  chain_head;       // -> $4f916 first settlement of this lord's nation (walk via +8)
/* 4*/  u16  cell;             // packed {x:6,y:7}
/* 6*/  u16  troops_reserve;   // <<< the lord's men-at-home pool
/* 8*/  u16  troops_field;     // <<< men currently in an army / garrison
/*12*/  u16  gather_kind;      // $5ec6: $2/$4/../$e -- which of goods[] this lord's herds yield now
/*14*/  s16  loyalty_pressure; // ramps +2 (field*4 >= reserve) / -1 per settlement pulse; >=600 -> $550e defection, reset 300
/*16*/  u16  herd_throttle;    // $60dc countdown; reload $580a6[side].word8 + 4 (+$2000 if gather_kind>=$e)
/*20*/  u16  shepherd_obj;     // $5ec6: $51b66 offset of the unit assigned to gather
/*22*/  u16  nearest_herd;     // $2906: byte offset into $57f68 of the closest herding op
/*24*/  u8   goods[8];         // <<< Pike,Sword,Bow,Plough,Boat,Pot,Catapult,Cannon counts (0..255)
```

The 74th pass's `pm_leader` guesses at +14 (`nation_off`) were wrong: the
settlement chain head is at **+2**, and **+14 is the loyalty / recruitment-pressure
accumulator** (§6). +24..31 are the goods counters (§2a).

### The flows (all traced, `watch $4e51a` / `$4e53a` over 80–400M steps)

| PC | handler / mode | effect on the pool |
|----|----------------|--------------------|
| `$1507c` | `$15042`, entity **mode `$16`** ("disband — go home") | `troops_reserve += 2` (`+= 2` again if `order_class == 8`) |
| `$15e18` | `$15ddc`, entity **mode `$60`** ("register with settlement") | `troops_reserve += 4` |
| `$150f2` | `$150c0`, entity **mode `$1a`** ("group absorbs reinforcements") | `slice = troops_reserve >> (group.discipline-2)`; `troops_reserve -= slice`; the slice goes to the group lead's marching pool (`14(lead)`) and the group total (`36(group)`) |
| `$3bc0` | `$35f4` group teardown | `troops_reserve += group.force >> discipline` — a disbanding army returns a slice of its men (75th). *(Corroborated. Note: `$3c08` — the flag-driven regroup dispatcher, **Proven 98th** — does NOT itself write the ledger on the common non-grouped path; its bit-4 group-teardown sub-path calls `$37c2`, which is the `$382a` row below, not `$3bc0`.)* |
| `$163b8` | entity **mode `$7c`** settlement heartbeat (§3a) | `owner_leader.troops_reserve -= 1`, floored at 0 — **per-settlement upkeep / desertion**, once per `$580a6[side].word0` ticks. **Proven (97th).** Mode `$7c` needs `$57fd0 == 0`; `$57fd0` rotates {0,2,4,6} via `$1abaa` (~1/110M steps), so in mission 1 this drain runs only in brief bursts during the `== 0` phases — a small, intermittent leak, not a steady term of the ledger |
| `$603e` | `$600a` (mode `$42`, no `flags.bit6`) | `leader.troops_reserve -= 2`, floored — besieging/detached shepherds cost the lord (75th) |
| `$382a` | `$37c2` (marker re-parent) | `leader.troops_field -= 1` when a settlement marker changes group (bit-6-clear arm). *(98th: `$37c2` disassembled — reached only via `$3c08`'s flag-bit-4 teardown sub-path; asserted off in the `$3c08` proof, its `$1d70`/`$1b8c` leaves deferred, so still Corroborated.)* |
| `$1c04` | `$1bf0` (capture consequence) | **new** owner's `troops_field += 1` — pairs with `$2644` (old owner `-1`); a captured garrison changes hands, it is not created |
| `$2644` | `$25d6` (capture consequence) | old owner's `troops_field -= 1` (the fallen garrison) |
| `$42be` | `$3e06` tail, courier/arrow array | a `$51b66` object died and credited a leader: `troops_field += 1` |
| — | `$d322` per tick | reads both, never writes; totals into `$57fba` |

So a PM "population" is a bucket that fills when soldiers walk home
(`$16`/`$60`) or an army disbands (`$3bc0`), and empties through recruiting
(`$1a`), besieging (`$603e`), and a slow per-settlement drain
(`$163b8` — intermittent in mission 1, see §3a). It is **strict conservation of
soldiers** — nothing manufactures a man from nothing (§6). In the tutorial the
enemy's two sub-leaders
(`$4e514[0]`, `[1]`, both side 2) sat with `troops_reserve` between 0 and `$a6`,
each unit return nudging it up and each settlement pulse nudging it down; the
player's manpower is held the same way in the player's own leader record.

**Mode `$16` disband** (`$15042`, the "go home" path):

```c
// $15042 -- CORRECTED 96th: the $57fd0 test was written backwards below, and the
// "veteran" test is on byte 33, not order_class (byte 1).
void h_disband(pm_object *A1) {                 // entity mode $16
    jsr_16848(A1);                              // side<->owner reconcile + $5c80
    if (g_tileset_sel /*$57fd0*/ == 0) {        // <- == 0, NOT != 0
        A1->dwell = -99; A1->prev_mode = A1->mode; A1->mode = 0x7c; return;
    }                                          // (park as a $157e6 heartbeat marker)
    leader *L = &leader_of(A1->nation_off);
    L->troops_reserve += 2;                     // the mission-1 path: DOES credit +2
    if (A1->byte33 == 8) L->troops_reserve += 2;
    A1->target = unpack_cell(A1->group_off_lobyte);
    A1->prev_mode = 0x18;  A1->mode = 0x10;             // walk to the muster cell
}
```

`$57fd0` (`g_tileset_sel`, initialised to `(byte[$58146] & 3) * 2` at
world-build) is not a "world still animating" flag. It starts at `4` in mission
1, so a disbanding unit *usually* takes the **`troops_reserve += 2`** path — but
`$57fd0` rotates {0,2,4,6} via `$1abaa` (~1 rotation per ~110M steps, §3a), and
whenever it is `0` the disbanding unit parks as a mode-`$7c` heartbeat marker
instead. Mode `$7c` and the whole loyalty/revolt system therefore run in mission
1 in brief intermittent bursts, not never.

## 2. The livestock / food-gathering system

PowerMonger's food supply is **sheep and wild animals herded to towns**. Three
arrays and one per-tick servicer implement it.

### `$4d252` — the herd / wildlife array (stride 12, count in `$4e512`)

```c
typedef struct pm_herd {           // $4d252 .. $4d252 + $4e512, stride 12
/* 0*/  u16  _w0;                   // ?? (dead slots hold stale large values -> see "$163ea aliasing")
/* 2*/  u16  shepherd_obj;          // $51b66 offset of the unit herding this animal (0 = free-roaming)
/* 4*/  u16  _w4;                   // ??
/* 6*/  u8   category;              // $4672/$4788 seeder writes $04 for every animal
/* 7*/  u8   breed_state;           // $0e..$11 = one of four live breeds (rand&3 + $e at spawn);
                                    //   $0d = claimed/consumed (all animals drifted $0e-$11 -> $0d
                                    //   over the 400M settle); bit7 = "handled this tick" flag
/* 8*/  u16  _w8;                   // ??  (worldY?)
/*10*/  u16  cell;                  // packed {x:6,y:7}; nonzero == a live animal ($b8f4 counts these)
} pm_herd;                          // sizeof 12
```

`$4e512` holds the live byte-length, initialised to `$c` (one reserved slot) by
`$4672` and grown `+= $c` per animal by `$47fa`. Hard cap `$12c0` → 400 animals.

`$4788` (the seeder, reached from `$4672` at world-build) picks a buildable land
cell (`$438ee` type byte `>= $1f` on both planes, `$47970` bucket free), writes
`category := $4`, `breed_state := $e + (rand & 3)`, `cell := packed`, and links
the animal both ways into a `$57f68` herding-operation entry.

### `$57f68` — herding operations (stride 8, live length in `$57fb8`, ≤10)

```c
typedef struct pm_herd_op {         // $57f68 .. $57fb8, stride 8
/* 0*/  u16  target_cell;           // where the herd is being driven (a settlement cell)
/* 2*/  u16  _w2;
/* 4*/  u16  herd_off;              // -> $4d252 (the animal)
/* 6*/  u16  marker_off;            // -> $4c5f4 (the moving on-screen herd marker)
} pm_herd_op;                       // sizeof 8
```

Each leader caches the nearest op in `pm_leader.nearest_herd` (`+22`), computed
by `$2906` (`pm_place_nations`-adjacent) at setup and, per its caller, refreshed.

### `$4c5f4` — herd-drive markers (stride 22, ≤80, live length in `$4ccd4`)

Seeded by `$4672` (`$46e8`): `byte5 := 1` (active), `byte6 := $16`, `byte8/9` =
packed x + `$80`, `byte10` = worldY, `byte15 := 0`, `byte16 := $40`, `word20` =
link to the previous marker in the chain. `$4342` animates it: `byte15` is a
signed progress counter that ramps from `$d0` (−48) up toward `$30` while the
marker walks (via `$164bc`) from the animal's cell to the destination town; when
it reaches `$30` the delivery completes and the op unlinks.

### `$4342` — the per-tick herding servicer (from `$3e06` / `pm_flag_health`)

Confirmed once per sim tick in the 74th-pass callgraph (`pm_flag_health ->
ram_004342  x651` over 651 ticks). Structure:

```c
void pm_herd_service(void) {                    // $4342
  for (herd_op *op = $57f68; op->target_cell; op++) {   // <= 10 ops
    pm_herd *h = &$4d252[op->herd_off];
    if ((h->breed_state & 0x80) && h->category && h->shepherd_obj) {
      // walk the shepherd object's bucket chain; find the op's $4c5f4 marker;
      // if the marker is idle (byte15 == 0) claim it: byte15 := $d0, snap it to
      // the animal's cell, spawn its screen record ($16808).
      ...
    }
    // then, for each $4c5f4 marker in this op's chain (word20 link):
    for (marker *m = &$4c5f4[op->marker_off]; m; m = &$4c5f4[m->link20]) {
      if (m->byte15 < 0) {                       // ramp-in: -48 -> +48, +1..+2/tick
          m->byte15 = min(0x30, m->byte15 + 1 + slot_index);
      } else {                                   // moving: step toward the animal
          if (--m->dwell18 <= 0) {
              int d2 = 2 * step_toward($164bc, m, animal_cell);
              m->byte15 = min(0x30, d2);
              if (m->byte15 == 0) { h->breed_state |= 0x80; unlink(m); }  // arrived
          }
      }
      m->byte14 -= 4;                             // trail/animation decay
      integrate m by (byte12,byte13); $163ea relink;
    }
  }
}
```

What `$4342` does **not** contain: any add to `troops_reserve`, any goods
counter, any population maths. `$4342` is **only the animation** — it walks the
`$4c5f4` marker sprite from the animal's cell toward the destination town
(`$164bc` one step per `18(marker)` dwell), and at arrival (`$44c6`: `$164bc`
returns 0) it does exactly two things — `bset #7, breed_state` of the animal and
`jsr $16778` to unlink the marker's screen object. The economic credit is
elsewhere, in the shepherd unit's own FSM (§2a).

**96th.** Fully disassembled (`scratchpad/pm96/disasm/herd_4342.txt`): the
marker-CLAIM head (`$437e`..`$4422`, gated on `animal.shepherd_obj != 0` +
`$16808` bucket link-at-head) and the animate loop (`$4436`.., `$164bc` step +
`$163ea` relink, or `$16778` unlink at arrival). All three non-trivial leaves
(`$164bc` / `$163ea` / `$16778`) are already Proven (93rd/94th) and `$16808` is
transcribed. But `$4342` is a **no-op in every natural capture** — every
`breed`-bit-7 animal has `shepherd_obj == 0` (claim path skipped) and every
`$4c5f4` marker has `progress (byte15) == 0` (animate loop skipped). The 97th's
`pm97_map0` (mode `$7c` live, 8 herd ops, 68 markers, ~40 shepherded animals)
did **not** unblock it — markers still seed `byte15 := 0` and only `$4342`'s own
claim head writes `byte15 := $d0`, and that head needs a bit-7 animal *with* a
shepherd, which no natural state reaches. So, like mode `$7c` before the 97th, a
real differential test needs a synthesised corpus (poke a marker's `byte15` +
an animal's `shepherd_obj`, wire the `$57f68`/`$4c5f4`/`$4d252` chains). Deferred
to its own pass; the skeleton is in `scratchpad/pm96/`, the anchor is
`scratchpad/pm97/pm97_map0`.

### 2a. The shepherd FSM and the real delivery payoff (75th pass)

The unit that herds an animal runs a four-mode chain. `$5ec6` (`pm_shepherd_assign`)
kicks it off: it binds the unit to an animal (`20(herd_op)` ← shepherd object),
gives it a `$16964`-relative patrol path, and — the part that matters — sets
**`pm_leader.gather_kind` (`$4e514`+12)** to one of `$2/$4/$6/$8/$a/$c/$e` from
the `$3f86c` terrain-control byte at the lord's cell plus the animal's flags.
That value picks which of the eight goods the lord's herds currently yield.

| mode | handler | what it does |
|------|---------|--------------|
| `$3e` | `$155ac` | scan `$4d252` for a live animal near the lord's herd cell (`breed_state` in `$0e..$11`); set it as `target`, → mode `$10` (walk), `prev_mode := $44` |
| `$44` | `$156be` | on arrival: 4-tick countdown (`byte 39`), then `animal.breed_state := $0d` (**consumed**); re-target the deposit object (`46(A1)`), → mode `$6a` body → mode `$46` → mode `$10`, `prev_mode := $42` |
| `$42` | `$15736` → `$600a` | dispatch on `pm_leader.gather_kind`; every non-idle case calls **`$60dc`** then re-arms the chain (`prev_mode := $3e`/`$40`/`$c`) |
| `$46` | `$15724` | short dwell (`18(A1)`) then → mode `$10` |

**`$60dc` is the payoff:**

```c
void pm_deliver_goods(pm_leader *L) {           // $60dc, from $600a (mode $42)
    if (--L->herd_throttle /*+16*/ != 0) return;         // one delivery per throttle window
    L->herd_throttle = side_assess(L->side)->word8 + 4;  // $580a6[side].word8 + 4
    int kind = L->gather_kind;                           // +12
    if (kind >= 0x0e) L->herd_throttle += 0x2000;        // "food"-tier herds are ~4x rarer
    int r = (kind >> 1) - 1;                             // 0..6
    if (L->goods[r] /*byte 24+r*/ != 0xff) L->goods[r] += 1;   // <<< the credit
}
```

So a completed herd-drive is worth **exactly +1 to one of `pm_leader.goods[0..7]`**,
and the throttle (`+16`, reload `$580a6[side].word8 + 4`, `+$2000` for `gather_kind
≥ $e`) is why deliveries are so rare in the settled view. In `pm75_big.err` the
`$6120` credit fired 3 times in the first ~40M instructions; `$4e544` (a lord's
`+16` throttle) reloads to `~$1fc9`, i.e. ~8100 ticks (~1 game-hour) between
food deliveries.

The eight `goods[]` slots map 1:1 to the `$a242` string table used for the unit
"carrying …" clause, and are read straight back out for the player in the lord /
settlement info panel:

```c
// $9bae  --  the granary line of the lord info panel
for (int i = 0; i < 8; i++)
    if (L->goods[i]) emit("%d %s%s", L->goods[i], a242[i+1], L->goods[i]==1 ? "" : "s");
// a242[1..8] = Pike, Sword, Bow, Plough, Boat, Pot, Catapult, Cannon
```

### 2b. Goods circulation — porter units

Goods do not stay where they are produced. A separate carrier FSM (modes
`$4e`/`$50`/`$52`/`$54`/`$5e`) moves counts between a nation's lords, biasing the
flow toward the capital:

| routine | direction | effect |
|---------|-----------|--------|
| `$159de` | pick up | `r = $57fec % 6`; if `src_leader.goods[r] != 0`: `goods[r] -= 1`, stamp the carried code `(r+1)*2` onto the porter's byte 44 (r<3) or byte 33 (r≥3) |
| `$159a4` | drop off | read the carried code off byte 33 / byte 44, `dst_leader.goods[(code>>1)-1] += 1` (cap `$ff`), clear the byte |

`$57fec` (the deterministic tick counter) round-robins the resource, so over time
every counter is sampled. This is what makes a lord's `goods[]` oscillate ±1 in a
long trace (`pm75_big.err`: `$0159f0`/`$0159ba` on `$4e530`) rather than ramp.

### 2c. Goods → equipment — the army-supply subsystem and "invention"

The player-facing "your men have invented Swords / Bows / Cannon" is **not** a
research timer. It is the moment a higher-tier item first reaches a lord's
`goods[]` and its field units get re-equipped from it.

`pm_object` carries the unit's equipment in **byte 44** (tier for items 1..6 —
Pike/Sword/Bow/Plough/Boat/Pot) and **byte 33** (tier for items 7..8 —
Catapult/Cannon). `$1533c` (melee) reads byte 44 as `damage = (min(v,6) >> 1) + 1`;
`$52fc` reads it for the projectile type.

The distribution runs from the commander-AI group-supply routine (`$61f8`, ahead
of `$6522`) and from the group-teardown family (`$3a66`/`$3aee`/`$3b32`, reached
via `$3c08`/`$35f4`):

```c
// per group-order record, D0 = shift from group discipline ($30fe)
for (int i = 0; i < 8; i++) {
    int take = L->goods[i] >> D0;      L->goods[i] -= take;      // spend a discipline-scaled slice
    grp->supply_acc[i] /*word[84 + i*12]*/ += push_to_units(i+1, take);   // $6352
}
// $638c, per candidate field unit, slot = (item <= 6 ? byte44 : byte33):
//   if unit.slot == 0      -> unit.slot = item          (equip)
//   else if unit.slot < item -> unit.slot = item; recycle the displaced lower item   (UPGRADE)
//   else                    -> no change
```

Two more modes close the loop:

* **mode `$78`** (`$15772` → `$63f4`): deposit a group's `supply_acc[]` back into
  `L->goods[]` (cap `$ff`), then → mode `$92` (free the group slot).
* **mode `$76`** (`$15754` → `$33b0`): weighted sum of *this-tick* deliveries
  (`supply_acc[i] × weight[$3498]`) `+` the assessment byte toward a target side
  `- 2`; if `≥ 0` issue **attack order `$2a`** (or `$34a8` = declare war); if `< 0`
  free the group. **This is the game's only economy → strategy coupling**: a lord
  that is being kept well-supplied turns aggressive.

All of `$61f8` / `$638c` / modes `$76`–`$78` sit in the strategic layer that
`strategy.md` measured as **near-dormant in "Between Pages 1-5"** (the enemy
captain issues no autonomous orders in ~1000 ticks). So in the tutorial, tier
byte 44 keeps its spawn value and the 74th pass's "no routine advances byte 44"
is *practically* true there — but the mechanism is fully present and would fire
in a live campaign.

One salvage path *does* fire in the tutorial: mode `$90` (`$160f2`, a
unit-removal handler) does `owner_leader.goods[(byte44>>1)-1] += 1` at `$1611a`
before clearing the dead unit's byte 44 — a fallen unit's weapon returns to the
lord's stockpile. `pm75_big.err` caught this (`$01611a`, 7×).

`$b8f4` is a **statistics collector** for the UI/score screen: it counts live
projectiles (`$4ccd6`, type `$11`/`$12`) and live animals (`$4d252`,
`cell != 0`) into a caller buffer. Confirms `pm_herd.cell` is the liveness key.

## 3. Settlements — `$4f916`

```c
typedef struct pm_settlement {      // $4f916, stride $12 (18), count in $51536, <= 240
/* 0*/  u16  _w0;
/* 2*/  u16  _w2;                    // written by $163ea bucket-relink for some records -- see below.
                                    //   NOT a population field (it is cleared/rewritten as a link word)
/* 4*/  u8   _b4;
/* 5*/  u8   owner;                  // $2fc0/$3018: commander colour holding the settlement (0 = free slot)
/* 6*/  u8   kind;                   // $3020: $02 normal, $10 if seeded kind == $7 (capital)
/* 7*/  u8   nation_kind;            // $2fc0: stream byte 2(A2); $7 == capital; read by the UI text gen ($9ccc)
/* 8*/  u16  chain_next;             // $3014: byte offset into $4f916 of the next settlement in this nation
/*10*/  u16  linked_obj;             // $51b66 offset of the settlement's own map marker
/*12*/  u16  dest_cell;              // $3034: packed {x:6,y:7} of the settlement
/*14*/  u16  leader_off;             // $3046: byte offset into $4e514 of this settlement's lord
/*16*/  u16  _w16;
} pm_settlement;                     // sizeof 18
```

Built by the routine at `$2fc0` (world-build, from `$13b9a`'s cluster): it walks
a 3-byte-per-record mission stream, allocates `$4f916` slots, chains them per
nation (`chain_next` at +8, head stored in `2(leader)`), and stamps
owner/kind/cell/leader. On the terrain plane it also sets influence bits
(`ori.b #$2,8257(A3)` + `bset #1` on three neighbours) so the settlement claims
its cells in `$3f86c`.

Capture (`$1d70` → `$25d6`, `ai.md`/`strategy.md`) flips `owner`, decrements the
loser's `troops_field`, and spins up a garrison objective for the new owner. It
does **not** transfer a stored population or goods — the settlement's future
production follows the ownership byte, and the goods sit on the *lord* record
(`$4e514`), not the settlement.

### 3a. The per-settlement heartbeat — entity mode `$7c` (75th; **Proven — natural corpus, 97th**)

There is no global "settlement update" routine. A settlement marker in **entity
mode `$7c`** (`t_mode_handlers[$7c]` → `$157ba`, body `$157e6`) pulses once every
`$580a6[side·$20].word0` ticks and runs the drain + construction + loyalty
logic below.

**Mode `$7c` requires `word[$57fd0] == 0`.** `$157ba` branches on it (`== 0` →
`$157e6`, else `jsr $16892` then `jsr $3c08` regroup — **Proven, 98th**), and so
does every instruction that *enters* mode `$7c` — `$1505e` (mode `$16` disband), `$15a46` and `$15b7a` (porter /
regroup). `$57fd0` is set at world-build to `g_tileset_sel = (byte[$58146] & 3)
* 2` (= 4 for mission 1's seed) — **but it is not static**: the sound/ambient
routine `$1abaa` (`$130b0` in the sim tick) **rotates it**, `$1ac5e..$1ac6a` =
`$57fd0 = ($57fd0 + 2) & 6`, cycling {0,2,4,6}, once per 13-bit sound-LCG
(`$57ff6`) wrap. Observed rate: ~1 rotation per ~110M steps (2 writes over a
220M-step mission-1 drive; 0 over 40M of pm78_settle). So the per-settlement
heartbeat — the `$163b8` manpower drain, the construction timer, the
loyalty/revolt accumulator — **is transiently reachable in mission 1**, during
the brief `$57fd0 == 0` phases of that rotation, not permanently dead. It is
*dormant*, not absent: none of pm78_settle / pm88_f1 / pm73_fight / pm74_late
(400M steps) happened to freeze a `$7c` record because those windows are short
and rare, and when `$57fd0` rotates off 0 any live `$7c` markers convert to mode
`$56`/`$3c08` and `troops_reserve` refills through the mission-1 `$1507c` path.
(This also refines the 89th's "`$57fd0` static per mission" for the `byte6 == 4`
building/tree tile-set — it shifts once per rotation too.) The 75th pass's "each
settlement's marker sits in mode `$7c`" was static + a `$163b8` `watch` that
actually caught a same-address routine in TOS.

**Proven — natural corpus (97th).** `pm97_map0` (`scratchpad/pm97/`) is a real
mission-1 world with `word[$57fd0]` forced to 0 at world-build (the single
intervention — it only *pins* the value the game visits transiently) and driven
80M steps: disbanding / regrouping / porter units then park as `$7c` heartbeat
markers through the game's own `$1505e` / `$15a46` / `$15b7a`, giving **19
natural mode-`$7c` records** on 10 real `$4f916` settlements (2 under
construction), leaders at `loyalty_pressure` 316 / 318. The 96th's
reconstruction (unchanged) differential-tested against the real 68000 via
`callcap 14b62` on this corpus: **99/99 tracked bytes over 27 states, all 12
branch families** — construction exercised naturally, `hostile.py` 5 negative
controls all bite. (The 96th first proved it on a *synthesised* corpus — poke
`$57fd0 := 0` on pm78_settle, repurpose inert records into fake `$7c` markers —
85/85 over 25 states; `scratchpad/pm96/`.)

```c
void h_mode7c_settlement(pm_object *M) {           // $157e6
    int D5 = --M->dwell;                           // subi.w #1 ; bgt -> next (no epilogue)
    if (D5 > 0) return;
    reconcile_16848(M);  upkeep_5c80(M);           // $16848 (which also calls $5c80) + $5c80
    M->dwell = side_assess(M->side)->word0;        // reload
    pm_settlement *S = &settlement_at(M->off34);   // $4f916 + 34(M)
    settlement_upkeep_163b8(S);                    // $163b8: S->leader->troops_reserve -= 1, floored
    if (M->flags & 0x10) goto epilogue;            // btst #4
    if (S->nation_kind == 0x0a) {                  // "under construction"
        if (++S->build_progress /*+16*/ >= 0x78) {
            S->nation_kind = S->dest_cell % 10;    // divu #$a ; swap  (remainder)
            if (S->nation_kind == 7) S->kind = 0x10;
            S->build_progress = 0;
        }
    }
    pm_leader *L = S->leader;                      // $4e514 + word[S+14]
    int f4 = L->troops_field * 4;
    if (f4 != 0) {
        if (f4 >= L->troops_reserve) {
            if (D5 == (short)0xff9c) L->loyalty_pressure += 2;   // <<< only on the
        } else {                                                //     first post-park
            if (D5 == (short)0xff9c) L->loyalty_pressure -= 1;   //     tick (dwell was
            if ((M->anim /*+14*/ & 3) != 3) settlement_herdop_5cde(L);  // -99 -> -100)
        }
        if (L->loyalty_pressure >= 0x258) revolt_550e(L, M);     // >= 600
    }
epilogue:
    epilogue_161c4(M);
}
```

**Corrections to the 75th-pass reading.** (1) The loyalty accumulator moves
**only when `D5 == $ff9c`** — the pulse immediately after the marker was parked
with dwell `#$ff9d` (`-99`), which decrements to `-100` on that first tick. On
every ordinary steady-state pulse `D5 == 0` and neither `±` branch runs (the
`-1` branch's `$5cde` call still does, gated on `(anim & 3) != 3`). (2) The
`$163b8` drain and construction run *before* the `btst #4` / `field·4 == 0`
early-outs. (3) `$16848` itself ends in a `jsr $5c80`, so upkeep runs twice per
pulse.

Asserted **off** in the proof (`raise` guards each): `$5cde` (settlement
herd-op assessment — a whole routine), `$550e` (revolt — economy.md §6: never
observed), `$5c2c` (owner reconcile in `$16848`).

### 3b. The `$163ea` aliasing — characterised, benign (75th pass, task 5)

`watch $4f916 240` (`pm75_w2.err`) confirms the writes land on
**`$4f916 + i*$12 + 2`** (i.e. `pm_settlement._w2`) for i ≈ 1..11, from PCs
`$1643c` / `$16482` / `$1645c` inside **`$163ea`**. Disassembly resolves it
cleanly: `$163ea` is a textbook doubly-linked-list relink of the `$47970` cell
buckets —

```
$1643c  move.w 2(A1),2(A3)     ; A3 = $51b66 + word[A1+0]   ; next->prev = my prev
$16482  move.w D0,2(A3)        ; A3 = $51b66 + new-head-link ; old head->prev = me
$1645c  clr.w  2(A3)           ; A3 = $51b66 + word[A1+0]   ; new head->prev = 0
```

Every one is `node.prev := …` at `$51b66 + link`. It reaches `$4f916` only when
the source object's forward-link word (`word[A1+0]`) is **sign-extended
negative** (`adda.w D5,A3` with `D5 ≈ $DDC2`): `$51b66 - $223E = $4F928`. The
values written are legitimate small link offsets (multiples of 50, the object
stride: `$32 $64 $fa $12c $190 $1f4 $258`) with occasional garbage
(`$b184`, `$af48`).

Conclusion: **`$163ea` is not at fault** — it only propagates links. The fault
is *upstream*: one or more object slots hold a corrupt bit-15 forward link, and
because the emulator zero-inits RAM that link was *written* by some instruction
(a bad `$2e1e` allocation index, or a stale link on a freed slot re-walked).
The damage is confined to `pm_settlement._w2`, which **nothing reads** (the chain
link is `+8`, cell is `+12`, owner `+5`). A real-Hatari cross-check is blocked by
the same limitation as all PM analysis — PM cannot be driven to the iso view
headlessly in Hatari — so this is downgraded from "needs verification" to
**characterised, benign, low priority**. It does confirm the 73rd pass's
`pm_nation.chain_next @ +2` was wrong (real link `+8`; `+2` is scratch).

## 4. Weapon grade — "invention" as the game surfaces it

**`pm_object` byte 44 is triple-purpose** (70th "msg_code", 74th "weapon tier",
and now a third role): a transient notify code in `$16260`; the equipment tier
for item types 1..6 on a combat unit; and a transient *carried-item* tag on a
porter unit (§2b). Byte **33** is the tier for item types 7..8 (Catapult, Cannon).

| site | reads byte 44 as | effect |
|------|------------------|--------|
| `$1533c` (melee, mode `$32`) | tier | `damage = (min(grade, 6) >> 1) + 1` per tick → 1..4 |
| `$52fc` / `$5318` (projectile spawn) | tier | projectile **type**: default `$12`, `$28` when `byte44 == $6` |
| `$3ffc` (`$3e06` speed calc) | `byte44 >= $e` → `+$10` force bonus | speed term |
| `$9846` / `$9dc6` (`$a242`) | index | the "carrying …" clause in the unit description |

Where it is **set**:
- **at spawn** — `$245c` stamps `6` on every group lead; `$2500` gives followers
  `byte44 := $580a6[side].byte23`, which `$10d1e` zeroes in the tutorial, so
  tutorial followers start at **0**.
- **advanced by supply** — `$638c` (§2c): when a lord's `goods[]` gets spent on
  its field units, `if unit.tier < delivered_item: unit.tier := delivered_item`.
  This is the whole of "invention" — there is **no research counter and no
  per-town invention percentage**. A unit improves iff a higher-tier item
  reaches its lord's stockpile and the supply subsystem runs (dormant in mission
  1, so pass 1's "never advances" holds *for the tutorial*).

The recruit path (mode `$1a`, `$150c0`) does not touch byte 44 — a fresh recruit
keeps whatever tier the group lead's supply run has given the group.

## 5. World-generation of the initial economy

`$13b9a` → `$10d1e` fills `$58146..$58150` from the RNG (`strategy.md` has the
table). The economy-relevant ones:

| addr | value | meaning |
|------|-------|---------|
| `$58148` | `$5809c` override else `rand & $7fff + $1500` | map size / richness; `< $2000` ⇒ "small" preset (more lords, more settlements) |
| `$5814a` | `rand & 7 + (small ? $a : 2)` | lord count |
| `$58150` | `(rand & 3) + 2 + (small ? $a : 2)` | settlement-count knob |
| `$5814b` | (byte of `$58148`) | **land richness / fertility byte** — added to every cell's `$3f86c` control value by `$ffa6` |

`$ffa6` seeds the per-cell control plane `$3f86c` ($1fff cells) from a base map
at `$4592f`, offset by `$5814b`, gated by `bit 1` of `$4592f`-plane flags, then
clamps every cell `>= 0`. The 75th pass corrects the pass-1 guess: `$3f86c` is
the **influence / carrying-capacity** field, not a fertility input to a growth
payoff (there is no growth payoff). It is read by `$5ec6` to pick `gather_kind`,
by the regroup modes (`$15b94`) for sprite selection, and by the strategy layer
for territory ownership — not by any manpower or goods maths. `$4672` scatters
10 clusters of animals (`$4788`) and herd markers across buildable cells.

`$2984` (task 4, now disassembled) is **world-build settlement-garrison spawn**,
not a periodic pass: per lord it walks the settlement chain, allocates a `$51b66`
marker per settlement (guarded by the object high-water `$57f66 < $5460`),
`owner_leader.troops_field += 1`, and seeds the marker's morale byte 45. It runs
once, alongside `$238c`.

## 6. Manpower is conservation-of-soldiers — there is no growth (75th, task 2)

Combining §1's flow table with the `pm75_big.err` (~1B steps) / `pm75_w1.err`
(135M steps) watches from `pm74_late.snap` (`watch $4e514 160` / `128`):

**Every** write to any lord's `troops_reserve` / `troops_field` came from this
closed set — `$1507c` (`+2`, mode `$16`), `$15e18` (`+4`, mode `$60`), `$3bc0`
(`+= force>>disc`, group teardown), `$1c04` (`+1`, capture — new owner), `$42be`
(`+1`, kill credit); `$150f2` (`-=`, recruit), `$603e` (`-2`, besiege), `$163b8`
(`-1`, settlement pulse), `$382a` / `$2644` (`-1`, re-parent / old owner on
capture). There is **no accumulator, no per-tick `+n`, no birth rate**. A
nation's total manpower can only be redistributed among its lords and slowly bled
by garrison upkeep; it grows only by winning battles (men who would have died
walk home instead) and shrinks by losing them.

**96th/97th refinement.** In mission 1 the drain side of that ledger is
thinner than the flow table suggests: `$163b8` (the settlement pulse) fires only
**intermittently** — mode `$7c` is `$57fd0`-gated, and `$57fd0` rotates {0,2,4,6}
via `$1abaa` (~1 rotation per ~110M steps, §3a), so the drain runs in brief
bursts during the `$57fd0 == 0` phases and is off the rest of the time. The
steady sinks in the tutorial are `$150f2` (recruit), `$603e` (besiege) and the
capture pair. The conservation observation stands.

The one thing that *looks* like a growth counter — `pm_leader.loyalty_pressure`
(`+14`) — is the opposite. It moves `+2` when `troops_field*4 >= troops_reserve`
(the lord's standing army has outgrown its manpower base) and `-1` otherwise —
but only on the *first* settlement pulse after a marker is parked
(`D5 == $ff9c`, the `#$ff9d` dwell decrementing to `-100`); on ordinary
steady-state pulses `D5 == 0` and neither arm runs (96th correction, §3a).
At `loyalty_pressure` **≥ 600** the pulse calls `$550e` — still **not observed
firing** (asserted off in the mode-`$7c` proof, loyalty kept < 600), but no
longer out of reach: see the caveat below the code:

```c
void revolt(pm_leader *L, pm_object *marker) {     // $550e
    u8 new_side = (marker->field8 % 4) + 1;        // pseudo-random 1..4
    L->side = new_side;                            // the lord defects
    L->loyalty_pressure = 300;                     // reset, half-way
    for (pm_settlement *s = chain(L); s; s = next(s))
        s->owner = new_side;                       // and every settlement with him
    reconcile_owner(...);                          // $5c2c
}
```

Read statically, this is a **rebellion-from-militarism** mechanic: over-militarise
a territory (big army, empty coffers, sustained) and the lord and all his
settlements switch allegiance. Caveat: `$550e` writes `leader.side` and every
`settlement.owner` in the chain to `(marker.field8 % 4) + 1` and resets
`loyalty_pressure` to 300 — the `≥ 600` path and the exact `new_side` formula
are inferred from the disassembly, not observed firing. In the plain tutorial
`loyalty_pressure` only oscillated 296–306 (the settlement pulse is
intermittent). But in `pm97_map0` — a mission-1 world with `$57fd0` pinned to 0
so the heartbeat runs continuously (§3a, 97th) — both AI lords' `loyalty_pressure`
climbed to 316 / 318 within 80M steps and was still rising (`troops_field·4` = 40
vs `troops_reserve` = 0, so the `+2` arm every pulse), which puts the `≥ 600`
revolt within reach of a long game whenever the `$1abaa` rotation favours `$7c`.
It fits PowerMonger's theme (the manual's "the people will turn against a cruel
ruler").

## Complete picture

```
   HERDS ($4d252)                                    ARMIES (groups, $51538)
      │  shepherd FSM  $3e→$44→$42                       │
      ▼                                                  │ group teardown $3c08/$35f4
   pm_leader.goods[0..7]  ($4e514 +24)  ◄───────────────┤ ($3b5a deposit remainder)
      │  ▲                                               │
      │  │ porters (modes $4e/$50/$52/$54/$5e)           │ army-supply $61f8 / $6352
      │  │ $159de pick up  /  $159a4 drop off            ▼
      │  └──────────────────────────────────►  $638c  equip / UPGRADE unit tier
      │                                          (pm_object byte 44 / byte 33)
      │  displayed:  $9bae  "n Swords" in the lord panel
      ▼
   $33b0 (mode $76): weighted delivery total + hostility  ─►  attack order $2a / declare war


   pm_leader.troops_reserve / .troops_field  ($4e514 +6/+8)   ── SEPARATE LEDGER ──
      +2  mode $16 disband-home ($1507c)          -1  settlement pulse upkeep ($163b8, mode $7c)
      +4  mode $60 register     ($15e18)          -2  mode $42 besiege        ($603e)
      +f  group teardown        ($3bc0)           -n  mode $1a recruit        ($150f2)
      +1  kill credit           ($42be)           -1  capture / re-parent     ($2644/$382a)
                                (no birth term — §6)
```

## Traces / artefacts

75th pass:
- `scratchpad/pm75_big.err` — `watch $4e514 160`, ~1B steps from `pm74_late.snap`
  (the §6 conservation evidence; `$6120` goods credit fires ~3×/40M).
- `scratchpad/pm75_w1.err` — `watch $4e514 128`, 135M steps (`$163b8` reserve
  drain 273×, `$60dc` throttle, mode `$16`/`$60` returns).
- `scratchpad/pm75_w2.err` — `watch $4f916 240` (the §3b `$163ea`→`_w2` writes,
  refined to `+2` only + the multiples-of-50 link values). NOTE: the double-`watch`
  form (two regions) suppressed the `$4e514` events in that run — **`watch` is
  reliable for one region at a time**; use separate runs.
- `scratchpad/pm75_w3.out` — `m 4e514 128` dumps (leader field map verification).

74th pass:
- `scratchpad/pm74_quiet.evt` (352 MB, 150M steps from `pm71_run1`) →
  `pm74_blocks.txt` / `pm74_cg.dot` / `pm74.names`. `$4342` per-tick child of `$3e06`.
- `scratchpad/pm74_late.snap` (`pm71_run1` + 400M, PC `$000124c0`),
  `pm74_run1.ram` / `pm74_late.ram`.
- `scratchpad/pm74_disasm.txt` — linear disasm `$1000`..~`$45000` of `pm70_iso.ram`.
