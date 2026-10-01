# PowerMonger ST — the economy: food, manpower, timber gathering, settlements, invention

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

**75th-pass summary.** All five pass-2 questions closed. The gathering payoff is
`+1` to one of `pm_leader.goods[0..7]` (§2a) — eight per-lord counters, one for
each of Pike/Sword/Bow/Plough/Boat/Pot/Catapult/Cannon, shown in the lord panel,
shuffled between lords by porter units (§2b), and spent to equip and upgrade
field units (§2c). "Invention" is that upgrade step (`$638c`), not a research
timer. Men are a **separate** ledger with **no growth term** (§6): conservation
of soldiers. A lord's `+6` is his food store (124th), drained by a
per-settlement upkeep (`$163b8`) and filled by the fishermen's catches and returning men. The
"periodic settlement update" is entity mode `$7c` (§3a). The `$163ea` write
aliasing is characterised and benign (§3b).

## Headline

**PowerMonger has no single "economy tick".** There is no routine that, once per
period, grows a population number and checks a food balance the way a 4X game
does. The economy is a set of loosely-coupled mechanisms, most of them driven at
the entity level by the same `$14b62` FSM that runs everything else:

| subsystem | where the number lives | how it moves | status |
|-----------|------------------------|--------------|--------|
| **food** (a lord's store) and **manpower** (his men at home, not in an army) | `pm_leader.food` = `$4e514`+6; `.troops_field` = +8 | food: a fisherman delivering a catch adds 4, a disbanded man arriving home 2; an army takes a posture-scaled slice (order `$06`) or drops one (`$12`, teardown); each settlement pulse eats one (`$163b8`). Men: `troops_field` moves by ±1 as men join, leave or change hands | **Proven (124th: orders `$06`/`$12` move exactly `food >> shift` between `+6` and the army's food `36(group)`, which the captain panel labels "Food")** |
| **goods** ("invention" and the granary line the player sees) | `pm_leader` bytes **24..31** — 8 counters, one per item type (Pike, Sword, Bow, Plough, Boat, Pot, Catapult, Cannon) | a completed gathering trip credits `+1` to one counter (`$60dc`), heavily throttled; porter units shuttle counters between a nation's lords (`$159de`/`$159a4`); the army-supply subsystem spends them to equip/upgrade field units (`$6352`/`$638c`) | **traced** |
| **timber gathering** (what feeds the goods counters) | `$4d252` tree array (`_trees`) + `$57f68` forest ops (`_forests`) + `$4c5f4` markers (`_birds`) | the gatherer chain (modes `$3e`→`$44`→`$42`, run by men of every job) walks to an unfelled tree of the lord's nearest forest, fells it (`tree_state := $0d`), carries it to the lord's workshop and credits the goods counter; `$4342` (`_do_forest`) only animates the on-screen markers | **traced; live 134th (below)** |
| **settlements** | `$4f916`, 18-byte records, ≤240, chained per nation (+8) | built at world-build (`$2fc0`/`$2984`); a per-settlement heartbeat is entity **mode `$7c`** (`$157e6`); ownership changes when a lord revolts (`$550e`, §3): the lord and all his settlements change side, then `$5c2c`/`$25d6` turn his garrison men over | **Proven (122nd, `diff_revolt.py` 1778/1778 over 49 states, all 27 natural revolts)** |
| **weapon grade** ("invention") | `pm_object` byte 44 (items 1–6) / byte 33 (items 7–8) | stamped at spawn (`6` for leads, `0` for tutorial followers); **advanced by the army-supply subsystem** (`$638c`: `if slot < delivered_item: slot := delivered_item`) — no research timer | **traced; observed on later lands (121st): `$63e8` equipped 22 empty slots on land 25 and 14 on land 0 in 200M steps; `$63be` (replacing a lower item) never fired** |
| **passive population growth** | — | **does not exist** — men are strict conservation-of-soldiers (see §6) | **traced negative** |

Men and goods are **two separate ledgers**. Goods never become soldiers and
soldiers never become goods. Food and goods meet only in a trade (order `$1c`,
`$63f4`: the army's food is part of its buying credit, strategy.md "The player's
commands"). Over a ~1-billion-instruction watched resume from
`pm74_late.snap` (`pm75_big.err`) plus a 135M cross-check (`pm75_w1.err`), every
`food` / `troops_field` write came from the fixed set in §6; no counter
grew a lord's manpower on its own, and **no lord's side byte was written once**.
The 74th pass's "delivery payoff not observed" is resolved:
the payoff is a `+1` to a goods counter, and in the tutorial the food-tier gather
throttle (`$580a6[side].word8 + $2000` ≈ 8200 ticks, ~1 game-hour) is why the
400M window saw none complete.

## 1. The food and manpower ledger — `pm_leader.food` / `.troops_field`

`+6` is the lord's **food store** and `+8` his men at home (not in an army). Passes before the
124th read `+6` as `troops_reserve` (men at home). It is food: order `$06` at the
player's own town moves `food >> shift` (22 → 11) into the army's `36(group)`
(247 → 258 against a no-order control's 247, `scratchpad/pm124/o06`, `ctl`), order
`$12` moves `36(group) >> shift` back (town 22 → 147), and the captain panel
(`$921a`, formatter `$917c`) prints `36(group)` on its "Food:" line
(strategy.md "The player's commands"). The strategic layer reads both fields
(`$d322` sums them per side into `$57fba`, the ratio uses only `troops_field`;
`$68fe`/`$69b4` score enemy leaders on `troops_field`).

```c
// $4e514, 32-byte records (ai.md / strategy.md: pm_leader). Economy fields (75th):
/* 0*/  u8   side;             // owning commander (1..4); $550e rewrites it on a defection
/* 1*/  u8   order_class;
/* 2*/  u16  chain_head;       // -> $4f916 first settlement of this lord's nation (walk via +8)
/* 4*/  u16  cell;             // packed {x:6,y:7}
/* 6*/  u16  food;             // <<< the lord's food store (124th; was read as troops_reserve)
/* 8*/  u16  troops_field;     // <<< men at home: this lord's men (home settlement `34(man)` → `$4f916 + 14`) whose byte-7 bit 6 is clear, i.e. not in a group roster, and, for the one leader-flag man (byte-7 bit 4) a lord may have, only while `42(man) == 0` (leads no group; counted 144 of 144, and the leader-flag men with `42 != 0` are not counted in 874 of 879, the 5 others in pre-game map snapshots; whole-corpus rule 2280 of 2280 exact over the game snapshots, `py/troops_rule.py`, instances rather than independent lords; why the count follows the group link is inferred); joining an army (`$152d4`) takes one off, leaving it (`$1b8c`) puts one back
/*12*/  u16  gather_kind;      // $5cde: {2,6,8,$a,$e} fell trees, 4 workshop loop, $c field path -- the lord's current work order ($5cde, read by $600a)
/*14*/  s16  loyalty_pressure; // ramps +2 (field*4 >= food: hunger) / -1 per settlement pulse; +16>>shift when an army takes food, -8 when one drops food or goods; >=600 -> $550e defection, reset 300
/*16*/  u16  herd_throttle;    // $60dc countdown; $5cde reloads $580a6[side].word8 + 4 (+$2000 if gather_kind >= $e and the reload >= the old value)
/*18*/  u16  build_site;       // $5cde: $4f916 offset of the settlement being built (0 = none)
/*20*/  u16  herd_op;          // $5cde: $51b66-relative offset of the nearest $57f68 forest op (written on the work order)
/*22*/  u16  nearest_herd;     // $2906: byte offset into $57f68 of the closest forest op ($5cde recomputes it, never reads this)
/*24*/  u8   goods[8];         // <<< Pike,Sword,Bow,Plough,Boat,Pot,Catapult,Cannon counts (0..255)
```

The 74th pass's `pm_leader` guesses at +14 (`nation_off`) were wrong: the
settlement chain head is at **+2**, and **+14 is the loyalty / recruitment-pressure
accumulator** (§6). +24..31 are the goods counters (§2a).

### The flows (all traced, `watch $4e51a` / `$4e53a` over 80–400M steps)

| PC | handler / mode | effect on the pool |
|----|----------------|--------------------|
| `$1507c` | `$15042`, entity **mode `$16`** (a farmer home from his field; non-winter only) | `food += 2` (`+= 2` again at `$1508a`, behind the `$15082` compare, when he carries a Plough, byte 33 `== 8`; 2 of 73 returns doubled in 40M steps of land 5, and only 1 farmer in ~73 carries a Plough, 136th) |
| `$15e18` | `$15ddc`, entity **mode `$60`** (the fisherman delivering his catch: every man in modes `$56`..`$62` is job 4, fisher, 93 of 93 over seven states, `py/job_census.py`, ai.md) | `food += 4` per trip |
| `$150f2` | `$150c0`, entity **mode `$1a`** (an army takes food from a town: order `$06`) | `slice = food >> (posture-2)`; `food -= slice`; `36(group) += slice` (the army's food); `loyalty_pressure += 16 >> (posture-2)` (the `14(A5)` write, A5 = the lord). 124th, 1 run: 22 → 11, loyalty 0 → 8 |
| `$3bc0` | `$39d4`/`$3b32` (order `$12` drop food at a settlement; also the `$35f4` camp-making family) | `food += 36(group) >> (posture-2)`, `36(group) -= that`; `loyalty_pressure -= 8` when the town is the army's side. 124th, 1 run: town 22 → 147, army 247 → 122. *(Corroborated. Note: `$3c08` — the flag-driven regroup dispatcher, **Proven 98th** — does NOT itself write the ledger on the common non-grouped path; its bit-4 group-teardown sub-path calls `$37c2`, which is the `$382a` row below, not `$3bc0`.)* |
| `$163b8` | entity **mode `$7c`** settlement heartbeat (§3a) | `owner_leader.food -= 1`, floored at 0 — **per-settlement upkeep / desertion**, once per `$580a6[side].word0` ticks. **Proven (97th).** Mode `$7c` needs `$57fd0 == 0`; `$57fd0` rotates {0,2,4,6} via `$1abaa` (1 rotation per 118.4M steps), so in mission 1 this drain runs only in brief bursts during the `== 0` phases — a small, intermittent leak, not a steady term of the ledger |
| `$603e` | `$600a` (mode `$42`, no `flags.bit6`) | `leader.food -= 2`, floored — a detached gatherer costs the lord (75th) |
| `$382a` | `$37c2` (marker re-parent) | `leader.troops_field -= 1` when a settlement marker changes group (bit-7-set, bit-6-clear arm). *(**Proven, 99th** — `$37c2` + its `$1d70`/`$1b8c`/`$17a46` leaves differential-tested vs the real 68000, 1847/1847 over 13 states; reached via `$3c08`'s flag-bit-4 teardown sub-path. The inverse `+= 1` on the bit-6-set arm is `$1b8c`'s `$1c04`.)* |
| `$1c04` | `$1bf0` (capture consequence) | **new** owner's `troops_field += 1` — pairs with `$2644` (old owner `-1`); a captured garrison changes hands, it is not created |
| `$2644` | `$25d6`, from `$5c2c` after a revolt | the garrison man's old leader: `troops_field -= 1`, only when the man led no group (land 60: leader 4, 18 → 17, `scratchpad/pm121/flip/`). *(Proven, 122nd, `diff_revolt.py`.)* |
| `$42be` | `$4244`, the player's-pigeon landing arm of `$3e06`'s effect-array loop (sole caller `$13052`; only the first record `$4c112` takes the arm) | **a dead man's record revived (137th, counted 6 of 6 hits, `scratchpad/pm137/B_42be/probe42be.py`)**: the record at `20(pigeon)` is the dead man whose `$1623c` countdown served the pigeon request (side byte negative, byte 6 `$0a` or `$20`, 6 of 6 launches); on landing `$4244` makes it live again (`neg.b 5`, byte-7 bits 4..6 cleared, byte 14 `:= $c`, repositioned to the pigeon's landing point, mode by `$3c08`), `5(A0) :=` its home settlement's side, then `$42be` adds 1 to that settlement's lord. Live persons +1 and one entity record changed at every hit. Neither a kill credit nor a settlement birth. The `+1` restores a count the death had already removed: the KILL tail `$567e` takes an ungrouped man off the home lord's `troops_field` (section 6), and in all 5 landings captured on `k5_s4` and `m1_ready` every lord's `troops_field` equals the live-man rule count both before and after, the home lord's `+1` the only change (`py/pigeon_ledger.py`), so the pigeon is not a manpower leak |
| — | `$d322` per tick | reads both, never writes; totals into `$57fba` |

So a lord's food store fills when his fishermen deliver a catch (`$60`), when disbanded men
arrive home (`$16`) or an army drops food (`$3bc0`), and empties when an army takes food (`$1a`), through
detached gatherers (`$603e`), and through a slow per-settlement drain
(`$163b8`, intermittent in mission 1, see §3a). Men are a separate count
(`troops_field`), which is **strict conservation of soldiers**: nothing
manufactures a man from nothing (§6). In the tutorial the enemy's two sub-leaders
(`$4e514[0]`, `[1]`, both side 2) sat with `food` between 0 and `$a6`. In
mission 1 the enemy's store rises by 4 per fisherman's delivery (28 → 40 in 3M steps,
56 in 25M, `scratchpad/pm124/ctl25`); an army eats its own food `36(group)` in `$3e06`
(`$3f6a`: `-= men/8 + 1` every `$580a6[side].word0` ticks, doubled while idle;
at zero each man deserts with chance 1/8; strategy.md "`$d322` + `$3e06`").
Mission 1, 26 men: 251 → 247 → 243 in 25M steps, both writes at `$3f6a`.

**Mode `$16`, a farmer home from his field** (`$15042`; the first reading called it "disband"):

```c
// $15042 -- CORRECTED 96th: the $57fd0 test was written backwards below, and the
// "veteran" test is on byte 33, not order_class (byte 1).
void h_farm_home(pm_object *A1) {               // entity mode $16
    jsr_16848(A1);                              // side<->owner reconcile + $5c80
    if (g_tileset_sel /*$57fd0*/ == 0) {        // <- == 0, NOT != 0
        A1->dwell = -99; A1->prev_mode = A1->mode; A1->mode = 0x7c; return;
    }                                          // (park as a $157e6 heartbeat marker)
    leader *L = &leader_of(A1->nation_off);
    L->food += 2;                     // the mission-1 path: DOES credit +2
    if (A1->byte33 == 8) L->food += 2;       // carrying a Plough
    A1->target = unpack_cell(A1->group_off_lobyte);
    A1->prev_mode = 0x18;  A1->mode = 0x10;             // walk to the muster cell
}
```

`$57fd0` (`g_tileset_sel`, initialised to `(byte[$58146] & 3) * 2` at
world-build) is not a "world still animating" flag. It starts at `4` in mission
1, so a disbanding unit *usually* takes the **`food += 2`** path — but
`$57fd0` rotates {0,2,4,6} via `$1abaa` (1 rotation per 118.4M steps, §3a), and
whenever it is `0` the disbanding unit parks as a mode-`$7c` heartbeat marker
instead. Mode `$7c` and the whole loyalty/revolt system therefore run in mission
1 in brief intermittent bursts, not never.

## 2. Timber gathering: trees, forests and the goods payoff

The goods counters are fed by men felling trees and carrying them home; food is a different
thing (the fishermen, §1). The arrays keep the `herd_*`/`shepherd_*` field names of the first reading
(`$4d252` as sheep and wild animals) in `tools/pm_fsm_ref.py` and the older proof scripts, but the
developer symbols (`$4d252` `_trees`, `$57f68` `_forests`, `$4c5f4` `_birds`, `$4342` `_do_fore...`,
modes `$44` `at_fores...`, `$42` `at_works`) and a live check say trees (strategy.md "Original names"):

- all 203 live `$4d252` entries of `pm123/win/m1_s0` (154 of 154 in `pm129/env5_12M`) sit on a
  byte6 == 4 record, the building/tree frame category of graphics.md, and that is the whole byte6 == 4
  population; none sits on a byte6 == 8 record (the animals, drawn by `$11a86`, a different set:
  3 in `m1_s0`, 40 in `env5_12M`; `py/tree_census.py`);
- from land 5 (`pm121/run/k5_s4.snap`, 10M steps, `hits` on the chain): `$3e` (`$155ac`) 28 hits, `$44`
  (`$156be`) 24, `$42` (`$15736`/`$600a`) 25, `$60dc` 25, **`$5ec6` 0**; the trees in state `$0d` went 2 → 5 while
  the live `$0e..$11` trees went 100 → 97 (3 felled), and the one goods credit among the 25 `$60dc` calls (lord 8's Plough 2 → 3)
  is the throttle at work;
- the men found in modes `$3e/$40/$42/$44/$46/$6a` over every `pm*` snapshot are of every job (fisher, farmer,
  shepherd, merchant, plus soldiers in `$46`/`$6a`), not shepherds (shepherds are `$80..$88`; `py/tree_census.py --chain`).

Three arrays and one per-tick animator implement it.

### `$4d252` — the tree array (stride 12, count in `$4e512`)

```c
typedef struct pm_tree {           // $4d252 .. $4d252 + $4e512, stride 12
/* 0*/  u16  _w0;                   // ?? (dead slots hold stale large values -> see "$163ea aliasing")
/* 2*/  u16  worker_obj;            // $51b66 offset of a unit working this tree (0 = none); the 97th: nothing natural sets it
/* 4*/  u16  _w4;                   // ??
/* 6*/  u8   category;              // $4672/$4788 seeder writes $04 for every tree (= the byte6 4 render category)
/* 7*/  u8   tree_state;            // $0e..$11 = one of four tree kinds (rand&3 + $e at spawn);
                                    //   $0d = felled (set by mode $44, $156d0); bit7 = "handled this tick" flag
/* 8*/  u16  next_in_forest;        // next tree of the same forest ($155f8 walks it; 0 = the walk restarts at the op's first tree)
/*10*/  u16  cell;                  // packed {x:6,y:7}; nonzero == a live tree ($b8f4 counts these)
} pm_tree;                          // sizeof 12
```

`$4e512` holds the live byte-length, initialised to `$c` (one reserved slot) by
`$4672` and grown `+= $c` per tree by `$47fa`. Hard cap `$12c0` → 400 trees.

`$4788` (the tree seeder, `place_tr...`, reached from `$4672` `_setup_f...` at world-build) picks a buildable land
cell (`$438ee` type byte `>= $1f` on both planes, `$47970` bucket free), writes
`category := $4`, `breed_state := $e + (rand & 3)`, `cell := packed`, and links
the tree both ways into a `$57f68` forest-operation entry.

### `$57f68` — forest operations (`_forests`; stride 8, live length in `$57fb8`, ≤10)

```c
typedef struct pm_forest_op {         // $57f68 .. $57fb8, stride 8
/* 0*/  u16  target_cell;           // the settlement cell the forest serves
/* 2*/  u16  _w2;
/* 4*/  u16  herd_off;              // -> $4d252 (the forest's first tree; `$155ac` reads it as 4(op))
/* 6*/  u16  marker_off;            // -> $4c5f4 (the on-screen marker chain)
} pm_forest_op;                       // sizeof 8
```

Each leader caches the nearest forest in `pm_leader.nearest_herd` (`+22`), computed
by `$2906` (`pm_place_nations`-adjacent) at setup and, per its caller, refreshed.

### `$4c5f4` — forest markers (`_birds`; stride 22, ≤80, live length in `$4ccd4`)

Seeded by `$4672` (`$46e8`): `byte5 := 1` (active), `byte6 := $16`, `byte8/9` =
packed x + `$80`, `byte10` = worldY, `byte15 := 0`, `byte16 := $40`, `word20` =
link to the previous marker in the chain. `$4342` animates it: `byte15` is a
signed progress counter that ramps from `$d0` (−48) up toward `$30` while the
marker walks (via `$164bc`) from the tree's cell to the destination cell; when
it reaches `$30` the delivery completes and the op unlinks.

### `$4342` — the per-tick forest animator (`_do_fore...`; from `$3e06` / `pm_flag_health`)

Confirmed once per sim tick in the 74th-pass callgraph (`pm_flag_health ->
ram_004342  x651` over 651 ticks). Structure:

```c
void pm_forest_service(void) {                    // $4342
  for (herd_op *op = $57f68; op->target_cell; op++) {   // <= 10 ops
    pm_tree *h = &$4d252[op->herd_off];
    if ((h->tree_state & 0x80) && h->category && h->worker_obj) {
      // walk the worker object's bucket chain; find the op's $4c5f4 marker;
      // if the marker is idle (byte15 == 0) claim it: byte15 := $d0, snap it to
      // the tree's cell, spawn its screen record ($16808).
      ...
    }
    // then, for each $4c5f4 marker in this op's chain (word20 link):
    for (marker *m = &$4c5f4[op->marker_off]; m; m = &$4c5f4[m->link20]) {
      if (m->byte15 < 0) {                       // ramp-in: -48 -> +48, +1..+2/tick
          m->byte15 = min(0x30, m->byte15 + 1 + slot_index);
      } else {                                   // moving: step toward the tree
          if (--m->dwell18 <= 0) {
              int d2 = 2 * step_toward($164bc, m, tree_cell);
              m->byte15 = min(0x30, d2);
              if (m->byte15 == 0) { h->tree_state |= 0x80; unlink(m); }  // arrived
          }
      }
      m->byte14 -= 4;                             // trail/animation decay
      integrate m by (byte12,byte13); $163ea relink;
    }
  }
}
```

What `$4342` does **not** contain: any add to `food`, any goods
counter, any population maths. `$4342` is **only the animation** — it walks the
`$4c5f4` marker sprite from the tree's cell toward the destination cell
(`$164bc` one step per `18(marker)` dwell), and at arrival (`$44c6`: `$164bc`
returns 0) it does exactly two things — `bset #7, tree_state` of the tree and
`jsr $16778` to unlink the marker's screen object. The economic credit is
elsewhere, in the gatherer's own FSM (§2a). What a `$4c5f4` marker is on screen is not established: the label `_birds` suggests flocks over the forests, but that is the label, not a check.

**96th.** Fully disassembled (`scratchpad/pm96/disasm/herd_4342.txt` (file name from the old reading)): the
marker-CLAIM head (`$437e`..`$4422`, gated on `tree.worker_obj != 0` +
`$16808` bucket link-at-head) and the animate loop (`$4436`.., `$164bc` step +
`$163ea` relink, or `$16778` unlink at arrival). All three non-trivial leaves
(`$164bc` / `$163ea` / `$16778`) are already Proven (93rd/94th) and `$16808` is
transcribed. But `$4342` is a **no-op in every natural capture** — every
`tree_state`-bit-7 tree has `worker_obj == 0` (claim path skipped) and every
`$4c5f4` marker has `progress (byte15) == 0` (animate loop skipped). The 97th's
`pm97_map0` (mode `$7c` live, 8 forest ops, 68 markers, ~40 trees with a worker)
did **not** unblock it — markers still seed `byte15 := 0` and only `$4342`'s own
claim head writes `byte15 := $d0`, and that head needs a bit-7 tree *with* a
worker, which no natural state reaches. So, like mode `$7c` before the 97th, a
real differential test needs a synthesised corpus (poke a marker's `byte15` +
a tree's `worker_obj`, wire the `$57f68`/`$4c5f4`/`$4d252` chains).

**113th, Proven for 8/9 branches** (`tools/pm_fsm_ref.py` `call_4342`,
`scratchpad/pm113/diff_4342.py`): the CLAIM mechanism is genuinely more
involved than the pseudocode above lets on — it does NOT reuse the triggering
op's *own* marker chain. It clears the op's own `marker_off`, scans the whole
`$57f68` array from the start for the first OTHER op whose `marker_off` is
still 0, and transplants the triggering op's chain into that op instead (a
fallback keeps the triggering op's original chain if no empty slot exists
anywhere). Every `byte5 > 0` marker in the transplanted chain then gets
(re)initialised via `$16808`. 110/110 tracked bytes identical over 9 states
(claim + guard-fail + no-empty-op fallback, both ramp-in cases, the dwell-skip,
a real step, and the owner-sync write) — see `ai.md`'s own entry for full
detail, including the two real bugs the pass caught in the bucket-link
machinery and the one branch (arrival/unlink) still only Corroborated because
it reproducibly hangs the real emulator under every synthesised poke tried so
far.

### 2a. The gatherer FSM and the delivery payoff

`$5ec6` (the tail of the work-order setup `$5cde`, `_set_tow...`) hands the lord's work to every living
non-leader man of every settlement in his chain (it skips a man with flag bit 6 or bit 4 set and one
already in a fisherman's mode `$5c`/`$60`/`$62`): it writes the man's mode `31`, a deposit object `46` and a
start value `36`, and stores the forest op's offset in the lord's `20`. The kind **`pm_leader.gather_kind` (`$4e514`+12)** is chosen in `$5cde` (ai.md, proven 768/768) from `D1` and the OR of the
men's flags, and the forest is the nearest `$57f68` op within 20 cells. `$600a` dispatches on that kind (table `$6062`, read from RAM):

| `gather_kind` | what the men run after each delivery | goods counter `(kind>>1)-1` |
|---|---|---|
| `$2`, `$6`, `$8`, `$a`, `$e` | `$60dc`, then mode `$3e`: fell the next tree | Pike, Bow, Plough, Boat, Catapult |
| `$4` | the building loop: count `8(house)` down by `10(house)`, `$60dc` when it reaches 0, then mode `$40` | Sword |
| `$c` | `$60dc`, then the `$16964`-relative path in `40(man)` and mode `$c` (the field-path walk, §3a) | Pot |

The kinds 4 and `$c` rows are read from the code and were not run live. The tree cycle was observed live (land 5, 10M steps, counts above):

| mode | handler | what it does |
|------|---------|--------------|
| `$3e` | `$155ac` | take the lord's forest op (`$51b66 + 20(lord)`, its `4` is the first tree); walk the trees' `next_in_forest` chain (word `+8`), skipping `14(man) & 3` of them so the men of a group pick different trees, to the first tree whose `tree_state != $d` (not felled); no tree left → `$35f4` on his lead's group for a man with flag bit 6 (a group follower), else `$3c08`. Otherwise `36(man) :=` that tree, target := its cell (`+10`), mode `$10` (walk), `prev_mode := $44` |
| `$44` | `$156be` | on arrival: 4-tick countdown (`byte 39`), then `tree_state := $0d` (**felled**); re-target the deposit object `46(man)`'s cell, dwell 10, mode `$46`, `prev_mode := $42` |
| `$46` | `$15724` | dwell `18(man)` ticks, then mode `$10` (walk to the deposit object) |
| `$42` | `$15736` → `$600a` | arrival at the deposit object: mode `$46`, dwell 10; for a man without flag bit 6 the lord's `food -= 2` (floored; at 0, `$3c08` sends him home, §1); then the dispatch above, which calls **`$60dc`** and re-arms the cycle |
| `$40` | `$15680` | the kind-4 variant: target the house `36(man)` in `$4f916` (`+12` its cell), mode `$10`, `prev_mode := $6a` |

**`$60dc` is the payoff:**

```c
void pm_deliver_goods(pm_leader *L) {           // $60dc, from $600a (mode $42)
    if (--L->herd_throttle /*+16*/ != 0) return;         // one delivery per throttle window
    L->herd_throttle = side_assess(L->side)->word8 + 4;  // $580a6[side].word8 + 4
    int kind = L->gather_kind;                           // +12
    if (kind >= 0x0e) L->herd_throttle += 0x2000;        // the `$e` tier is ~4x rarer
    int r = (kind >> 1) - 1;                             // 0..6
    if (L->goods[r] /*byte 24+r*/ != 0xff) L->goods[r] += 1;   // <<< the credit
}
```

So a completed delivery is worth **exactly +1 to one of `pm_leader.goods[0..7]`**,
and the throttle (`+16`, reload `$580a6[side].word8 + 4`, `+$2000` for `gather_kind
≥ $e`) is why deliveries are so rare in the settled view. In `pm75_big.err` the
`$6120` credit fired 3 times in the first ~40M instructions; `$4e544` (a lord's
`+16` throttle) reloads to `~$1fc9`, i.e. ~8100 ticks (~1 game-hour) between
deliveries.

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

Goods are meant to move: a separate carrier FSM (modes `$4e`/`$50`/`$52`/`$54`, the merchants) picks up one good from a lord and deposits it at another.
**Not observed to move anything (136th):** 0 of 136 merchants in transit carried a code, and `$54`'s lord-selection loop, as encoded, never leaves the
home lord (`lea 32(A3),A0` at `$15b0c`, A3 never advances; inferred from the encoding and the census, not a differential test), so the destination equals the
home lord in 404 of 404 men in `$52/$50` and the net transfer is zero. The merchants are also not a designed trade class: they are the men left over when the world-build job pick
could place neither a farmer nor a fisherman (281 of 281 merchants in eight builds, §5a: 59 gave up on a 1-in-32 roll, 222 failed five rounds, mostly through a stale register). The "biased toward the capital" reading is unsupported:

| routine | direction | effect |
|---------|-----------|--------|
| `$159de` | pick up | `r = $57fec % 6`; if `src_leader.goods[r] != 0`: `goods[r] -= 1`, stamp the carried code `(r+1)*2` onto the porter's byte 44 (r<3) or byte 33 (r≥3) |
| `$159a4` | drop off | read the carried code off byte 33 / byte 44, `dst_leader.goods[(code>>1)-1] += 1` (cap `$ff`), clear the byte |

`$57fec` (the count of `$1abaa` calls since the last season change, ~231k steps each) round-robins the resource, so over time
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
  `- 2`; if `≥ 0` the target lord **accepts an alliance** (order `$2a` → `$34a8`,
  peace bits; strategy.md "Diplomacy"), else a refusal message; the envoy group is
  freed either way. The carried goods are the tribute: this is how the economy
  feeds diplomacy (123rd; the 75th pass read `$2a` as an attack order).

All of `$61f8` / `$638c` / modes `$76`–`$78` sit in the strategic layer that
`strategy.md` measured as **near-dormant in "Between Pages 1-5"** (the enemy
captain issues no autonomous orders in ~1000 ticks). So in the tutorial, tier
byte 44 keeps its spawn value and the 74th pass's "no routine advances byte 44"
is *practically* true there — but the mechanism is fully present and would fire
in a live campaign.

There is no salvage of a fallen unit's weapon. `$1611a`'s `goods[(byte44>>1)-1] += 1` (earlier read as a unit-removal handler) is the
return half of the **equipment exchange** (136th): a *living* man at his lord's cell, in mode `$90` (`townee_g`, `$160f2`: `$3c08` regroup, then the swap) or
mode `$8e` (`fight_ge`, `$160e4`: swap, then back to `$2c`), runs the shared tail `$160f8`: (a) a weapon in byte 44 goes back into the lord's
`goods`, (b) the first non-zero of `goods[2]`, `[1]`, `[0]` (bow, sword, pike) is taken into byte 44, (c) a farmer (byte 7 bit 0) with `goods[3]` non-zero
returns his carried item and takes a Plough (byte 33 `:= 8`, `goods[3] -= 1`). It never compares the lord's weapon with the man's own, so he
ends with the best in stock. The tail has a stale-register bug: D0.w still holds the lord's record offset `14(A0)` when `move.b 44(A1),D0` / `move.b 33(A1),D0`
run, so a returned item is credited `128 * (D0.w >> 8)` bytes further on, i.e. into leader record `lord + 4*(lord>>3)` for lord >= 8 (lord 8's Plough went to
lord 12's `goods[3]`, captured live twice; lords 0..7 are unaffected), which breaks goods conservation. The rule is exact only with D0 tracked through the whole
tail (137th, `tools/pm_fsm_ref.py` `call_160f8`, gate `py/gate_equip.py`: 201 states, 385/385 bytes and D0.w/D1.w 201/201, 41 misdirected weapon returns and
8 misdirected item returns among them): a weapon returned is always misdirected for lord >= 8; the farmer's item return reuses whatever D0.w is left, so it is credited
correctly if a weapon was taken in the same call (D0.w = 2*(slot+1) <= 6), misdirected if nothing was taken and no weapon returned, and credited correctly for lords 8..15 but
misdirected from lord 16 up after a weapon return without a take. The take follows the return, so a weapon returned to a higher slot can be re-taken in the same call
(code read; seen in the synthetic states). Of 48 natural men in `k5_s4`, `k25_s3` and the `pm136` e1/e2 snapshots, 3 carry a weapon and belong to a lord >= 8 (the model and the 68000 agree
their weapon is credited past the lord). Natural counts, `k5_s4` run in 12 stretches of 10M steps
(`scratchpad/pm136/equip/run1.sh`): `$16892` 3, 61, 66, 81, 41, 15, 51, 5, 82, 6 hits per stretch, `$160f2` 1, `$1616c` 1 and 2; `m1_s0` 0 (every lord's goods are zero).
The earlier "`pm75_big.err` caught this, 7×" was the `$1611a` instruction, not a dead unit's weapon.

The port has it as `port/godot/logic/Equipment.fs` (`tail`, `arriveFight`, `arriveGoods`, `goodsRegroup`) with a `CreditMode`: `Original` keeps the stale D0 and is identical to the
68000 on all 202 corpus cases (the 201 gate states plus the native exchange, 1451038 compared bytes, `py/equip_check.fsx`); `Corrected` clears the high byte so the item goes to the
man's own lord, equals `Original` for every lord < 8 (89 of 89 cases), and for every case keeps all bytes outside the own lord's goods and conserves goods plus items held
(192 of 192). The `Corrected` mode has no oracle in the game, only those properties. The port has no game simulation yet (the stepper replays the draw order of one frame),
so nothing calls these; `$3c08`, which `arriveGoods` runs first, is a parameter, not ported.

`$b8f4` is a **statistics collector** for the UI/score screen: it counts the live animals (the 40 records of `$4ccd6` with an owner byte and byte 7 `$11` or
`$12`, free or herded; `ai.md` "Shepherds, animals and carrier pigeons", not projectiles, which live in `$4be00`) and live trees (`$4d252`, `cell != 0`) into a caller buffer.
Confirms `pm_tree.cell` is the liveness key.

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
owner/kind/cell/leader. A site is refused when the four corner altitudes of its cell
(`-16514(A3)`, `-16513`, `-16450`, `-16449`: the `$3f86c` plane, A3 being the `$438ee` cell pointer; `$2f72`, static) sum to 0,
that is open sea; otherwise it sets bit 1 in four cells of the flag plane (`ori.b #$2,8257(A3)` + `bset #1` on
three neighbours). Bit 1 pins a cell's altitude against the `$10410` smoothing pass (`btst #1`), and `$10458`/`$10b3e` set it too, so it is not
a settlement-only mark: in `m1_s0` all 28 bit-1 cells lie in the 11 settlements' four-cell claims, in `k5_s4` 232 of 506 do not (136th `planes/flag_census.py`).

**How a settlement changes hands: the revolt `$550e`** (Proven, 122nd:
`reversing/powermonger/py/diff_revolt.py`, 1778/1778 over 49 states, 27 of
them every natural `$550e` call on the four run lands). `$550e` has two
callers, and they are the only two ways land changes side (124th,
`reversing/powermonger/py/diff_4f68.py`, 1804/1804 over 192 states, 170 natural):

- **Revolt, the settlement heartbeat** (`$157e6`, entered from mode `$7c` while
  `$57fd0 == 0` and from mode `$7e`, a man idling at home, with no such gate).
  A pulse with `field·4 < food` (fed) takes 1 off `word[14]` on a man's first
  pulse and then checks `>= 600` every pulse; a pulse with `field·4 >= food`
  (hungry) adds 2 and checks only on the first pulse (`$158a2 bne $158d6`). At
  600 the caller sets the pulsing man's side to `(x cell mod 4) + 1`, calls
  `$550e` at `$158cc` and restores it (`$158d2`): the new side is effectively
  arbitrary (11 natural calls on the run lands, loyalty 600-608). Hunger builds
  the pressure; a pulse, hungry or not, cashes it. In mission 1 the lords start
  at 608 and nothing pulses for them (`$57fd0` stays 4 and none of their men is in
  `$7e`), so they never revolt on their own. The spy order (`$20`) puts our
  captain into lord 0's town in mode `$7e`: his first pulse (field 11 × 4 = 44 <
  food 55) sent lord 0 to side `(22 mod 4) + 1 = 3` (`scratchpad/pm124/o20`,
  `conquest/spy`; the 25M control: `$157e6` 0 hits).
- **Conquest in the field** (`$53f6`). Mode `$2c` (`$152f8: jsr $4f68`) picks a
  target through the `38(A1)` table at `$4fa2` (handler = `$4fa2 + word[$4fa2 +
  38]`, ai.md mode `$2c`). A man told to hunt a lord (`38 = 2`, `46` = the
  lord record, set by `$4dd6`/`$576c` when contact is made) looks over every man
  of that lord's settlements within `$fff`; when none is left that can fight
  (dead or routed), `38` becomes `$12` (`$538a`), and on the next tick `$5240`
  checks that nobody in his group is still engaged and runs `$539a`, which calls
  `$550e` with the lord and makes the lord's side the attacker's `5(A1)`, then
  ends the group's order and makes its camp (`$35f4`). It made 16 of the 27 natural calls (loyalty 0 to
  292), and the mission-1 win: 5 kills + 5 routs of lord 0's 10 men, then
  `$539a` once at +26,268,828 steps after `m1_atk.snap`, lord 0 → side 1 with
  `troops_field` still 5. The lord's field count is not the test; his
  settlements' men are. `$550e` makes
`5(A1)` the leader's side, resets `word[14]` to 300, and walks the leader's
settlement chain (`2(leader)`, next at `8(settlement)`): each settlement not
already on the new side gets owner byte 5 rewritten, and its unit chain
(`10(settlement)`, next at `24(unit)`) is scanned for a garrison man (owner
`> 0`, flags bit 4, mode `$8a` or `$3c`); the last one found is reconciled by
`$5c2c`. If his settlement's leader is now on another side, `$5c2c` either
hands the contact to `$4bc8` (he leads a group that still has members, or the
leader has no `troops_field`) or defects him (`5(man) := leader side`) and
`$25d6` makes him the lead of a new group in his new side's first free
sub-record. `$25d6` takes one off his old leader's `troops_field` only when he
had no group (`$2644`); a group lead's old group is dissolved by `$2776`
instead. `$5c2c` loads `D2 := 2` but `$25d6` tests `D3` for its "defected"
counters `$12abe`/`$12acc`, so those never count a defection (a game bug,
inferred). Lords defect both to and from the player's side. Observed on land 60 (`scratchpad/pm121/flip/k60_flip_pre.snap`
/ `_post.snap`, from `run/k60_s3.snap`: `$550e` at step 4,509,545, the owner
byte of settlement `$4fa90` written 2 → 3 at `$5538`, `$25d6` at 4,509,837); all
four later lands ran `$550e` six times in 200M steps. Nothing moves stored
population or goods: the settlement's future production follows the owner
byte, and the goods sit on the lord record (`$4e514`). `$1d70` is the
route expander that sends men home, not an ownership writer (`ai.md`).

### 3a. The per-settlement heartbeat — entity mode `$7c` (75th; **Proven — natural corpus, 97th**)

There is no global "settlement update" routine. A settlement marker in **entity
mode `$7c`** (`t_mode_handlers[$7c]` → `$157ba`, body `$157e6`) pulses once every
`$580a6[side·$20].word0` ticks and runs the drain + construction + loyalty
logic below.

**Mode `$7c` requires `word[$57fd0] == 0`.** `$157ba` branches on it (`== 0` →
`$157e6`, else `jsr $16892` then `jsr $3c08` regroup — **Proven, 98th**), and so
does every instruction that *enters* mode `$7c` — `$1505e` (mode `$16` disband), `$15a46` and `$15b7a` (porter /
regroup). `$57fd0` is set at world-build to `g_tileset_sel = (byte[$58146] & 3)
* 2` (= 4 for mission 1's seed) — **but it is not static**: the seasons
routine `$1abaa` (`_seasons`, `$130b0` in the sim tick) **rotates it**, `$1ac5e..$1ac6a` =
`$57fd0 = ($57fd0 + 2) & 6`, cycling {0 winter, 2 spring, 4 summer, 6 autumn}, once per full 8192-iteration cycle of its 13-bit
pixel-order LCG `$57ff6` (512 calls of 16 pixels; Hull-Dobell full period). Measured: writes at steps 789,032,489 (4 → 6),
907,448,489 (6 → 0) and 1,025,912,489 (0 → 2), a period of 118.44M steps = 512 calls × ~231k (`watch 57fd0`, 136th `scratchpad/pm136/season/`; 2 writes
over a 220M-step mission-1 drive earlier; 0 over 40M of pm78_settle). The word is the *target* season: the live tileset then dissolves pixel by pixel
into the new art over the following 512 calls. So the per-settlement
heartbeat — the `$163b8` food drain, the construction timer, the
loyalty/revolt accumulator — **is transiently reachable in mission 1**, during
the brief `$57fd0 == 0` phases of that rotation, not permanently dead. It is
*dormant*, not absent: none of pm78_settle / pm88_f1 / pm73_fight / pm74_late
(400M steps) happened to freeze a `$7c` record because those windows are short
and rare, and when `$57fd0` rotates off 0 any live `$7c` markers convert to mode
`$56`/`$3c08` and `food` refills through the mission-1 `$1507c` path.
(This also refines the 89th's "`$57fd0` static per mission" for the `byte6 == 4`
building/tree tile-set — it shifts once per rotation too.) The 75th pass's "each
settlement's marker sits in mode `$7c`" was static + a `$163b8` `watch` that
actually caught a same-address routine in TOS.

**Weather and the season art.** PowerMonger has weather: rain in spring and
autumn and snow in winter, started by `$1ad74` from `word[$1ad9c + word[$57fd0]]`
and drawn over the iso window by `$1a856` (`port/SPEC.md` §7 "Weather"; the
port's `Weather.fs` matches the game's frames). Weather and winter slow
marching groups through the lead's speed byte `16(lead)`, which `$3e06` sets
every tick for each active group exec sub-record (`$3fac..$401c`):

```
speed = $580a6[side*$20].word2          ; 30 for sides 1-4, 32 for side 0, on all four run lands
if (word[$4bb44] > 0) speed -= 16       ; a rain/snow spell is running
if (word[$57fd0] == 0) speed -= 8       ; winter
load  = Σ words at 160(sub)+{0,12,24,36,48,72,84} (the last two x16; inferred: goods carried)
        + 16 if 44(lead) >= $e
excess = load - 52(sub)                 ; group force
if (excess > 0) { speed -= excess; if (speed <= 0) speed = 2; }
16(lead) := speed                       ; and 18(lead) := 0 if 31(lead) == $12
```

The FSM turns it into the per-step velocity at `$14cda` (`$12d56` rotates
`(0, -speed)` by the heading into `12/13(lead)`, added to the position each
movement step), in world units where a cell is 256. An unloaded group so moves
30 units a step in fair weather, 14 in rain, 22 in a dry winter and 6 in snow:
a spell cuts the speed by about half, snow on top of winter by four-fifths.
*Decoded from the disassembly; the base values are read from the four run
lands' RAM, the reductions were not measured in motion.* On lands 0 and 25 `$1a856` drew weather on 131-132 frames in
200M steps. The water shimmer (`graphics.md`'s `colour(h) += masterTick & 3` for
`h < 0x0c`) is a separate 4-phase dither cycle. The season also picks the tree
and building frames (`g_tileset_sel`, below); the sprite art itself is the same
in every season.

The `$37c7c` prop sheet (28 × 480 B, `32×24` word-plane, decode already pinned
89th) was pulled from a live RAM snapshot (`scratchpad/pm114_rand2.snap` —
world-build had run; the sheet is **not** resident before that, confirmed by
diffing against a pre-world-build snapshot where all 480×28 bytes at `$37c7c`
are zero) and every frame rendered against `port/assets/palette.json`
(`pm114_prop_contact.png`, contact sheet; `pm114_tileset_families.png`, the
four `{r7, r7+3, r7+6, r7+9}` families for `r7 = 0, 1, 2, 12` side by side).
Findings, from the actual pixels:

- **`r7 = 0` and `r7 = 1` (both cottages): the first three variants
  (`tsel = 0, 2, 4` → offset `0, 3, 6`) are the *same building*, redrawn with
  progressively fewer wall gaps / more intact masonry** — a damage-state
  gradient, not a colour or architecture swap. The fourth variant
  (`tsel = 6` → offset `9`) is a small unrelated flower/shrub sprite for both
  families, breaking the gradient.
- **`r7 = 12` (a tree-ish base): `offset 3/6/9` run bare-branches →
  more-branches → full green leaf** — a believable growth/season gradient,
  but `offset 0` (frame 12 itself) is a gallows/frame-like structure unrelated
  to the other three.
- **`r7 = 2` does not fit either pattern**: its four frames (checkered-roof
  house, a narrower house, a tower ruin, a different ruin) look like four
  distinct structures, not stages of one.

**Reading.** The four slots of each family are the four seasons' versions of
one tile (`port/SPEC.md` §4 "Seasons": tree frames 15-17, 18-20, 21-23 and 24-26
are bare, blossoming, leafy and autumn brown), and `$57fd0` steps through them
once per season fade (118.4M steps). Families whose four slots look unrelated are
tiles the sheet packs into the same stride-3 layout, not stages of one object.
The four prop slots are four distinct pictures (`py/family_distinct.py`: 12 of 12 families `r7 = 0..11` have four different
frames on `k5_s4`), so "four" is right for the prop sheet; the terrain colour tables are the ones with only three distinct sets
(`graphics.md` "Seasons": spring and autumn share one table, `py/season_tilediff.py`), and the two counts are not the same thing.

**Aside — driving the menus: click timing and the Timer A hang.** Getting to
`pm114_rand2.snap` needed a click-timing fix: `mouse down`/`mouse up` alone
enqueue no IKBD packet at all in relative-report mode (`MMU.fs`
`EnqueueMouseButton` only emits a byte when `MouseButtonsReportAsKeys` is
true) — the button state only reaches the game embedded in a *subsequent*
`mouse move` packet's header, so a bare `down;up` with no flush is silently
dropped. Fix: `down`, `mouse move 0 0` (flush), hold ~300k steps, `up`,
`mouse move 0 0` (flush) — confirmed working for the Welcome-menu →
world-map transition. But driving *from* the world map (both the top-left
compass icon at `~(18,18)` — the README's documented "scroll icon" — and
"PLAY RANDOM LAND" from the Welcome menu) lands in the identical
`$1ae40: tst.b $2c993.l / bne $1ae40` busy-wait. `$2c993` is a busy flag
that the MFP Timer A handler (`$134` → `$1af32`) clears (`sf $2c993` at
`$1af72`); it is not an FDC poll. The same wait hung the briefing-OK world build until an emulator
regression was fixed: `RaiseTimerA` read TACR from a register array that TACR
writes no longer reached, so Timer A never fired (README "Bug 5"). The build
now completes. PLAY RANDOM LAND, re-driven from `pm114_postclick2.snap` (cursor
`mouse move 0 35`, then down / `move 0 0` / up / `move 0 0`), now builds a world
(`$13b9a` 2.5M steps after the click, a winter land;
`scratchpad/pm121/random_land2.snap`), shows "Please Wait For The Protection
Check" while the build finishes, then asks the manual-lookup question. The AI
block does not run on that land because the uncracked answer check leaves the
flag `$14e4e` at 0 (strategy.md "The campaign", protection check). The
top-left "scroll icon" at `~(18,18)` of the world map is land 0's cell on the
13 × 15 conquest map (`$1120e`), and land 0 is mission 1 (inferred from the
cell geometry; the pick itself is traced for land 1 in strategy.md).
`pm114_rand2.snap` was taken mid-hang; its RAM already had a fully populated
`$37c7c` sheet (used above).

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
    settlement_upkeep_163b8(S);                    // $163b8: S->leader->food -= 1, floored
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
        if (f4 >= L->food) {
            if (D5 == (short)0xff9c) L->loyalty_pressure += 2;   // <<< only on the
        } else {                                                //     first post-park
            if (D5 == (short)0xff9c) L->loyalty_pressure -= 1;   //     tick (dwell was
            if ((M->anim /*+14*/ & 3) != 3) settlement_workorder_5cde(L);  // -99 -> -100)
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
work-order assignment — a whole routine), `$550e` (revolt — economy.md §6: never
observed), `$5c2c` (owner reconcile in `$16848`).

**What sets `dwell := $ff9d` (Proven, 126th pass, live).** The write is
`$015052`, inside mode `$16`'s handler (`$015042`, ai.md's "disband" row),
gated on `word[$57fd0] == 0`: `jsr $16848`; if `$57fd0 == 0`, `18(A1) := $ff9d`
(dwell), `30(A1) := 31(A1)` (save the entering mode as `prev_mode`),
`31(A1) := $7c` (park as the settlement heartbeat marker); else the record
instead credits the owner leader's food and re-musters (`mode := $10`,
`prevmode := $18`). Isolated live from `scratchpad/pm125b/`: `$015042` fired
naturally 28 times over 100M steps with `$57fd0` nonzero throughout (0/28 hit
`$015052`); forcing `word[$57fd0] := 0` (`w 57fd0 00000188`, the neighbouring
field untouched) on the same state made the very next mode-`$16` entry take
the park branch — 1/3 over a further 150M steps, at the one step `$57fd0` read
0. 1/1 dwell-writes land exactly where the disassembly predicts, 0 elsewhere.

**Mode `$16` belongs to garrison/neutral markers, not to player-dismissed
troops (126th, live-traced).** `$3c08`'s flag-bit dispatch only picks
`prev_mode := $16` for a record whose flags byte `7(A1)` has **bit 0 set**;
the sole site in the whole image that sets that bit is `$002cd0`, inside a
grid site-scan that also stamps mode `$18`/`$0c` (the neutral-village-garrison
patrol setup, ai.md's `$18` row) — a world-build-time placement, not anything
a player action reaches. Captured live: the mode-`$16` entity at a natural
`$015042` hit (`A1 = $51bfc`, 15.3M steps into `m1_s0` with no input at all)
carries flags byte `$01`. By contrast, tracing one *player* desertion end to
end (starvation via `$3f6a` → `$1b8c` → its own recursive `$1bea: jsr $3c08`
call, entity `$52462`) hit `$3c08`'s **"no flag bits set" default** at `$3c3c`
(`prev_mode := $7e`), walked home under mode `$10` (five probe/blocked
`$10`↔`$12` cycles), and arrived in mode `$7e` (`$014fdc: mode := prev_mode`)
— never touching `$16`. Mode `$7e` runs the same heartbeat body (`$157e6`) as
`$7c` but **ungated and without ever having its own dwell reset to `$ff9d`**,
so the `D5 == $ff9c` "just parked" edge structurally cannot fire for a unit
that arrives this way. This is why the 125th's dismiss/starve test saw zero
loyalty pulses over 104 settlement beats: player-triggered troop movement
never reaches the one instruction that arms the loyalty edge. **The
"hunger revolt by clicks" framing is very likely wrong as stated** — the
loyalty park-tick looks like a periodic self-cycle of the settlement's own
garrison marker (`$7c` ⇄ `$16`, gated purely by the global `$57fd0` season word,
1 rotation per 118.4M steps), independent of what the player does with troops or
food on that settlement. What order `$06` moves (`loyalty_pressure` 0 → 16,
corroborated 125th) is that order's own `+16 >> (posture−2)` formula, a
completely separate write path from the parked-marker pulse.

**"Does a settlement ever revolt on its own?" is already answered, and yes**
(127th: this framing had gone stale — §6/`ai.md`'s `$550e` proof already
settled it four passes before the 125th/126th re-opened it as a fresh
question). The 122nd pass's `diff_revolt.py` (1778/1778 tracked bytes over 49
states, `ai.md` "The revolt chain") ran on the four `pm121/run/<land>_s1..s4`
corpora — 200M steps per land, **no player input at all**. Of the 27 natural
`$550e` calls it captured, **11 fired from the settlement heartbeat at loyalty
600-608** (the other 16 from mode `$2c`'s conquest arm, loyalty 0-292; §6).
That is exactly the `$7c`/`$16` self-cycle described above crossing 600
unassisted, differential-tested against the real 68000 rather than merely
observed. What is still genuinely open is narrower: whether the settlement's
own `$7c` marker is itself the bit-0-flagged record feeding the mode-`$16`
traffic, or some other garrison entity — the `$51bfc` record above was caught
already inside `$16`, not followed backward to its own prior `$3c08` call.
`scratchpad/pm125b/` (gitignored; `ANCHORS.md`).

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

Conclusion: **these are real bucket links, not corruption.** `$5cde` builds a
new settlement by allocating a `$4f916` record and inserting it into the
`$47970` cell bucket with `$16808`, passing its offset from `$51b66`, which is
negative (`$5e62..$5e70`; Proven, 122nd, `scratchpad/pm122/agents/herdop/`,
state `p_newsettl`: the new record's `+0` becomes the old bucket head). So a
settlement record is also a bucket node: `+0` is its forward link and `+2` its
back link, and an object whose forward link is negative points at such a
record (byte6 `$1e`, the building going up). The occasional values `$b184` /
`$af48` were not investigated. The chain link of the lord's settlements is `+8`,
as the 73rd pass's `pm_nation.chain_next @ +2` had wrong.

## 4. Weapon grade — "invention" as the game surfaces it

**`pm_object` byte 44 is triple-purpose** (70th "msg_code", 74th "weapon tier",
and now a third role): a transient notify code in `$16260`; the equipment tier
for item types 1..6 on a combat unit; and a transient *carried-item* tag on a
porter unit (§2b). Bytes 44 and 33 both hold an item code `2 * (goods slot + 1)`: 44 a
weapon (2 pike, 4 sword, 6 bow; `$e` catapult and `$10` cannon are never
written), byte **33** a tool (8 plough, `$a` boat, `$c` pot: `$159de` for goods
slots 3-5, `$1616c` for the plough: the lord's `goods[3]` is decremented there, the only live Plough source seen).

| site | reads byte 44 as | effect |
|------|------------------|--------|
| `$1533c` (melee, mode `$32`) | tier | `damage = (min(grade, 6) >> 1) + 1` per tick → 1..4 |
| `$52fc` / `$5318` (projectile spawn) | tier | projectile **type** (its byte6): `$12` when `byte44` is `$e` or `$10`, `$28` when it is `$6` (a bow: the arrows the renderer draws as one pixel); any other value takes the melee branch `$5334` and fires nothing. No writer ever stores `$e`/`$10` in byte 44 (the build forces a lead's to 6, followers get 0/2/4/6, the equip paths 2/4/6), so type `$12` is unreachable (`port/SPEC.md` "Why 18 and 28 are missing") |
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
  reaches its lord's stockpile and the supply subsystem runs. It is dormant in
  mission 1; on later lands `$63e8` (an empty slot takes the item) fired 22 times
  on land 25 and 14 on land 0 in 200M steps, and `$63be` (a better item replaces
  a worse one) never did.

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
| `$5814b` | low byte of the lord-count word `$5814a` | the height step `$ffa6` adds per random-walk step to the altitude plane `$3f86c` |

`$ffa6` (original `_fill_al...`) builds the **altitude plane `$3f86c`** (`$2000` bytes, 64 columns by 128 rows, cell
`y*64 + x`; original `_alts`): `$58148` random-walk steps (the point starts at (`$5814c`, `$5814e`) and moves -1..+1 per axis,
wrapped to 64 x 128) each add `$5814b` to the cell under the point unless bit 1 of that cell's `$4592f` flag is set,
then every cell is clamped `>= 0` and `$10410` (neighbour averaging) runs `$58150` times (`$ffa6`..`$10056`, static).
That the renderer projects this plane as the terrain height is proven by poking it: a block of 39 longwords of `$3c`
under the camera raises a plateau, 10938 pixels differ against the same forced redraw without the poke
(`py/alts_render_check.py`). Altitude 0 is sea level: settlements are refused on a cell whose four corners are 0 (`$2f72`), and a
fisherman picks his sprite `$70` or `$90` by whether the cell's `+1` and `+64` neighbours are nonzero (`$15bae`, static,
not seen live); `$5d80` (the build decision, ai.md "Build") reads the altitude at the lord's cell, `>= $10` meaning high
ground. It is not an influence, ownership or carrying-capacity field, and not read by any manpower or goods maths. `$4672` scatters
10 forests, clusters of trees (`$4788`), and their markers across buildable cells.

### 5a. The starting population: who each man is (139th)

`$2984` (the developers' `_set_peo...`) runs once per land build, after the map is made and before `$238c`, which builds each side's army (the only other
caller of the man allocator `$2e1e`). It is not a periodic pass and not a garrison. For each lord that has a settlement chain and each settlement of the chain
it creates `word[$580a6 + side*32 + 14]` men, which is 2 on every side of every build seen (so 70 men on land 0, 35 settlements, and 210 on land 25).
Each man is allocated by `$2e1e` (the first free record from slot 1; the high-water word `$57f66` grows by 50 per man and the routine stops for good at `$5460`,
432 men, never reached), chained into his settlement (word 10 is the head, word 24 the next man), counted into his lord (`troops_field += 1`), and given a job by `$2a98`.
Only the first man of a lord of kind > 3 carries the leader flag (the flag survives across that lord's settlements and is cleared after one use), so a land has one
captain per such lord (8 of 8 builds: 31 captains for 31 lords of kind 4 or 5, 2 to 6 a land). The health byte follows the job: farmer `$52`, fisher `$4f`, merchant `$45`, shepherd `$48`, captain `$5f`.

The job pick `$2a98` (developers' `_its_my_`; `reversing/powermonger/py/gate_jobs.py`):

```c
int job_pick(man *m, int d1_from_caller) {
    if (m->flags & LEADER) { m->mode = 0x8a; return CAPTAIN; }            // captain at rest
    retry = 5;                                                           // a word inside the code, $2b06
    do {
        r = rng() & 0x1f;
        if (r == 0) break;                                               // 1 in 32: give up
        if ((r & 7) == 0 && init_shepherd(m)) return SHEPHERD;           // 3 in 32 (r = 8, 16, 24)
        if ((r & 1) && init_fisher(m)) return FISHER;                    // 16 in 32, odd draws
        if (init_farmer(m, d1)) return FARMER;                           // the rest, and the fall-through of both arms above
    } while (--retry);
    m->mode = 0x4e; m->flags |= MERCHANT; return MERCHANT;
}
```

- **Shepherd `$2b08`** (`init_she`): refused only when the animal pool is already past `$2f8` bytes (38 animals). Otherwise 2 to 5 animals are created by `$2d0e`
  (`(rng & 3) + 1` passes of a `dbf` loop), chained through the animals' words 16 (the previous animal, 0 for the first) and 18 (the shepherd); the man's word 42
  is the last animal made, his mode is `$80` and his flag bit 3 is set. Animals are described in `ai.md` "Shepherds, animals and carrier pigeons".
- **Fisherman `$2b68`** (`init_fis`): scans squares of radius 1 to 9 around the man for the first cell with altitude 0 where exactly one of the two colour planes is
  non-zero (read as a shore cell, inferred from the plane meanings) and whose bucket holds no category-`$18` record, and plants a catch marker there (category `$18`, flags `$10`, the man's side) in the pool
  `[$4cff8, $4d250)` (10-byte records; `$4d250` counts bytes used). The man's word 42 is that cell, his mode `$5e`, his flag bit 2. Refused when `$4d250 >= $12c`,
  so at most 30 markers are made by this arm (the pool has room for 60: `$3744` puts the category-6 camp and garrison markers in the same pool).
- **Farmer `$2c5a`** (`init_far`): scans squares of radius 1 to 9 for the first cell whose flag byte (`$4592f` plane) has bit 4 set, clears the bit, sets both colour
  planes (`$418ad`, `$438ee`) of that cell to `$1e` (the field), makes the cell his target (bytes 42/43 the cell, words 20/22 the position) and sets mode `$10`, previous
  mode `$18` (the farmer cycle, `ai.md`), flag bit 0. Altitude is never tested. Every farmer takes one site: free sites fell by exactly the farmer count in all eight builds.
- **Merchant / captain** (`$2ce8`, `$2cf8`): mode `$4e` with flag bit 1; mode `$8a`, no flag change.

**A stale-register bug decides the job mix.** `$2c5a` bounds the row of the cell it examines with `cmpi.w #$80,D1`, which tests D1, not the row (D0). D1 is the caller's
register: `$2984`'s remaining-men counter on entry, but the fisher arm leaves in it the cell index of the last cell it visited whenever it fails (no shore cell within nine, or
the 30-marker pool full), normally above `$80`. From then on every farmer attempt of that man fails at once, in all five rounds, so a man whose fisher arm fails once can no
longer become a farmer. Counted over eight builds: 1234 of 1234 farmer-arm failures were this stale bound and none was a genuine "no free site within nine cells"
(every merchant has a free site within nine cells in the final state, on lands 0, 25 and 142 checked). The merchant class is therefore mostly this bug's output:

| land | men | captains | farmers | fishers | shepherds | merchants: gave up / five rounds failed | animals | catch markers |
|---|--:|--:|--:|--:|--:|---|--:|--:|
| 0 | 70 | 3 | 32 | 17 | 10 | 3 / 5 | 36 | 17 |
| 1 | 168 | 3 | 71 | 30 | 10 | 9 / 45 | 40 | 30 |
| 5 | 176 | 6 | 73 | 30 | 11 | 12 / 44 | 40 | 30 |
| 10 | 128 | 4 | 56 | 30 | 10 | 7 / 21 | 39 | 30 |
| 25 | 210 | 6 | 91 | 30 | 11 | 12 / 60 | 40 | 30 |
| 60 | 132 | 4 | 56 | 30 | 10 | 8 / 24 | 38 | 30 |
| 100 | 84 | 3 | 34 | 18 | 11 | 4 / 14 | 38 | 18 |
| 142 | 58 | 2 | 23 | 9 | 11 | 4 / 9 | 40 | 9 |

Fishermen stop at 30 because of the marker cap, shepherds at 10 or 11 once the animal pool is past 38 (seven of the eight builds end at 38 to 40 animals; land 0 ends at 36 and its 70 men are
simply too few to reach the cap), and the 59 + 222 merchants are the overflow. Whether a clean D1 would be the intended behaviour is not decidable from the code; the port, which does not simulate the entity loop, keeps no choice to make.

Proof: `py/gate_jobs.py` runs `$2a98` against the real 68000 (`callcap 2a98`) on 146 states: the 70 natural entries of land 0's build plus synthetic RNG seeds (each arm drawn),
full animal and marker pools, a leader, and an incoming D1 over `$80`: 3310 of 3310 tracked bytes and returned D0 identical (men, buckets, planes, both pools, the RNG seed, the
retry word). `py/gate_pop.py` runs the whole `$2984` (`callcap 2984`) on the build of eight lands (0, 1, 5, 10, 25, 60, 100, 142): 29860 of 29860 tracked bytes identical over 1026 men.
The model is `call_2984`, `call_2a98`, `call_2b08`, `call_2b68`, `call_2c5a`, `call_2d0e`, `call_2e1e` in `tools/pm_fsm_ref.py`. The per-round probabilities (1, 3, 16 and 12 in 32) are read from
the masks in `$2a98` and agree with the counts; `$2984` itself takes 1.4 to 8.7 M steps a build. That the farmer arm never fails for lack of a site is counted on the final states of eight builds only.

## 6. Men are conserved, food is not grown by any counter (75th, task 2; 124th: `+6` is food)

Combining §1's flow table with the `pm75_big.err` (~1B steps) / `pm75_w1.err`
(135M steps) watches from `pm74_late.snap` (`watch $4e514 160` / `128`):

**Every** write to any lord's `food` / `troops_field` came from this
closed set. Food: `$1507c` (`+2`, mode `$16`), `$15e18` (`+4`, mode `$60`), `$3bc0`
(`+= 36(group)>>shift`, an army drops food), `$150f2` (`-=`, an army takes food),
`$603e` (`-2`, mode `$42`), `$163b8` (`-1`, settlement pulse). Men
(`troops_field`): `$1c04` (`+1`, capture, new owner), `$42be` (`+1`, a pigeon
landing revives a dead man's record), `$382a` / `$2644` (`-1`, re-parent / old owner on capture),
`$567e` (`-1`, the KILL tail of `$5590` for a man in no group roster: the dead man leaves the home lord's count, `ai.md` `$5590`, proven by the 95th gate; the watches behind this list ran on AI-only play without kills, which is why it was missing). The 124th
pass adds the player's order paths, which the AI-only watches could not see:
order `$14` (`$1cc4` → `$1b8c`) returns dismissed men to `troops_field`, and
order `$20` (`$3da4`) adds the spy to the target lord's `troops_field`. `$1b8c`
is also the starvation-desertion sink (strategy.md "`$d322` + `$3e06`"): driven
live (125th) by dropping an army's food at posture 2 and marching it to 0, the
roster fell 26 → 13 over 50M steps and the local lord's `troops_field` rose
0 → 13 by the same amount — a starving man leaves by the identical `$1b8c` path
as a dismissed one, just LCG-triggered instead of player-triggered.
There is **no accumulator, no per-tick `+n`, no birth rate**. A nation's men can
only be redistributed among its lords; they grow only by winning battles (men
who would have died walk home instead) and shrink by losing them.

**96th/97th refinement.** In mission 1 the drain side of that ledger is
thinner than the flow table suggests: `$163b8` (the settlement pulse) fires only
**intermittently** — mode `$7c` is `$57fd0`-gated, and `$57fd0` rotates {0,2,4,6}
via `$1abaa` (1 rotation per 118.4M steps, §3a), so the drain runs in brief
bursts during the `$57fd0 == 0` phases and is off the rest of the time. The
steady sinks in the tutorial are `$150f2` (recruit), `$603e` (besiege) and the
capture pair. The conservation observation stands.

The one thing that *looks* like a growth counter — `pm_leader.loyalty_pressure`
(`+14`) — is the opposite. It moves `+2` when `troops_field*4 >= food`
(the town holds at most 4 food per man in the field: hunger) and `-1` otherwise —
but only on the *first* settlement pulse after a marker is parked
(`D5 == $ff9c`, the `#$ff9d` dwell decrementing to `-100`); on ordinary
steady-state pulses `D5 == 0` and neither arm runs (96th correction, §3a).
At `loyalty_pressure` **≥ 600** the pulse sets the marker's side to
`(marker.field8 % 4) + 1` (`$158b6`) and calls `$550e`: the lord and every one
of his settlements not already on that side defect, `loyalty_pressure` resets
to 300, and one garrison man is reconciled (§3 "How a settlement changes
hands", Proven 122nd). On the four later lands this fired naturally 11 times
in 800M steps, at loyalty 600-608. In the plain tutorial `loyalty_pressure` only
oscillated 296–306 (the settlement pulse is intermittent); in `pm97_map0` (a
mission-1 world with `$57fd0` pinned to 0) both AI lords climbed to 316 / 318
within 80M steps with `troops_field·4 = 40 > food = 0`. Read as a
mechanic it is a **hunger revolt**: a lord whose store stays below 4 food per
man for long enough changes side. The player's orders push the same counter:
taking food adds `16 >> (posture-2)` (`$150e8`), dropping food or goods at an
own town takes 8 off (`$3b48`), and a trade (`$63f4`) takes 8 off at an own town
and adds 8 at a foreign one. That fits the manual's "the people will turn
against a cruel ruler".

## Complete picture

```
   TREES ($4d252)                                    ARMIES (groups, $51538)
      │  gatherer FSM  $3e→$44→$42                       │
      ▼                                                  │ group end   $3c08/$35f4 
   pm_leader.goods[0..7]  ($4e514 +24)  ◄───────────────┤ ($3b5a deposit remainder)
      │  ▲                                               │
      │  │ porters (modes $4e/$50/$52/$54/$5e)           │ army-supply $61f8 / $6352
      │  │ $159de pick up  /  $159a4 drop off            ▼
      │  └──────────────────────────────────►  $638c  equip / UPGRADE unit tier
      │                                          (pm_object byte 44 / byte 33)
      │  displayed:  $9bae  "n Swords" in the lord panel
      ▼
   $33b0 (mode $76): envoy's goods as tribute + attitude  ─►  alliance accepted ($2a → $34a8) or refused


   pm_leader.food  ($4e514 +6)                       ── SEPARATE LEDGER ──
      +2  mode $16 disband-home ($1507c)          -1  settlement pulse upkeep ($163b8, mode $7c)
      +4  mode $60 fisher's catch ($15e18)        -2  mode $42 gatherers      ($603e)
      +f  army drops food       ($3bc0, order $12) -n army takes food        ($150f2, order $06)
   pm_leader.troops_field  ($4e514 +8)
      +1  pigeon revives a dead man ($42be)     -1  capture / re-parent     ($2644/$382a)
      +n  dismissed men / spy   ($1b8c, $3da4)
                                (no birth term — §6; the one path that raises the live count without a capture or a dismissal is `$42be`,
                                 which recycles a dead record)
```

## Traces / artefacts

75th pass:
- `scratchpad/pm75_big.err` — `watch $4e514 160`, ~1B steps from `pm74_late.snap`
  (the §6 conservation evidence; `$6120` goods credit fires ~3×/40M).
- `scratchpad/pm75_w1.err` — `watch $4e514 128`, 135M steps (`$163b8` food
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
