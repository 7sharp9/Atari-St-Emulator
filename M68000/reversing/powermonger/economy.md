# PowerMonger ST — the economy: manpower, livestock, settlements, invention

Reverse-engineered 74th pass (pass 1 of 2), continuing `ai.md` / `strategy.md`.
Those two files cover the autonomous military layer and confirm it has **no**
economic reasoning; this file covers what the economy actually is and where its
numbers live. Same method: disassembly of `scratchpad/pm70_iso.ram` (game image
at its absolute addresses, base `$1050`), block traces, and field `watch`es
driven from `scratchpad/pm71_run1.snap` / `pm74_late.snap` ("Between Pages 1-5",
the procedurally-generated tutorial mission).

## Headline

**PowerMonger has no single "economy tick".** There is no routine that, once per
period, grows a population number and checks a food balance the way a 4X game
does. The economy is a set of loosely-coupled mechanisms, most of them driven at
the entity level by the same `$14b62` FSM that runs everything else:

| subsystem | where the number lives | how it moves | status |
|-----------|------------------------|--------------|--------|
| **manpower** (a town's available men) | `pm_leader.troops_reserve` = `$4e514`+6, `.troops_field` = +8 | soldiers walking home add 2–4; recruiting an army subtracts a discipline-scaled fraction; a battlefield/garrison loss subtracts 1 | **traced** |
| **livestock / food gathering** | `$4d252` herd array + `$57f68` herding-operation array + `$4c5f4` herd-marker array | shepherd units drive animals to towns; `$4342` animates the delivery once per sim tick | structure traced, delivery payoff **static-only** |
| **settlements** | `$4f916`, 18-byte records, ≤240, chained per nation | created at world-build from the mission stream; ownership changes on capture (`$1d70`/`$25d6`) | **static** |
| **weapon grade** ("invention" as the player sees it) | object record byte 44 | set once at unit spawn from a mission-setup constant; feeds melee damage and projectile type | **traced (effect), static (source)** |
| **passive population growth** | — | **not found** — see "What is not here" | — |

Over a **400M-instruction** (~1670-tick, ~10 game-minutes) traced settle from
`pm71_run1.snap`, the only writes to any `troops_reserve` were `+2`/`+4` at unit
arrivals. Nothing grew a town on its own. Either passive growth is gated on the
livestock-delivery payoff (untested — no herd completed a delivery in the quiet
view), needs a far longer timescale, or only a scripted campaign mission enables
it. Pass 2's job is to settle that.

## 1. The manpower ledger — `pm_leader.troops_reserve` / `.troops_field`

This is the closest thing PM has to a population number, and it is the one the
strategic layer actually reads (`$d322` sums both fields per side into
`$57fba`; `$68fe`/`$69b4` score enemy leaders on `troops_field`).

```c
// $4e514, 32-byte records (ai.md / strategy.md: pm_leader). Economy-relevant fields:
/* 4*/  u16  cell;             // packed {x:6,y:7}
/* 6*/  u16  troops_reserve;   // <<< the town's men-at-home pool
/* 8*/  u16  troops_field;     // <<< men currently in an army / garrison
/*14*/  u16  nation_off;       // -> $4f916 home-settlement record
/*22*/  u16  nearest_herd;     // $2906: byte offset into $57f68 of the closest herding op
```

### The flows (all traced, `watch $4e51a` / `$4e53a` over 80–400M steps)

| PC | handler / mode | effect on the pool |
|----|----------------|--------------------|
| `$1507c` | `$15042`, entity **mode `$16`** ("disband — go home") | `troops_reserve += 2` (`+= 2` again if `order_class == 8`) |
| `$15e18` | `$15ddc`, entity **mode `$60`** ("register with settlement") | `troops_reserve += 4` |
| `$150f2` | `$150c0`, entity **mode `$1a`** ("group absorbs reinforcements") | `slice = troops_reserve >> (group.discipline-2)`; `troops_reserve -= slice`; the slice goes to the group lead's marching pool (`14(lead)`) and the group total (`36(group)`) |
| `$2644` | `$25d6` (capture consequence) | old owner's `troops_field -= 1` (the fallen garrison) |
| `$42be` | `$3e06` tail, courier/arrow array | a `$51b66` object died and credited a leader: `troops_field += 1` |
| — | `$d322` per tick | reads both, never writes; totals into `$57fba` |

So a PM "population" is a bucket that fills when soldiers walk home
(`$16`/`$60`) and empties when a captain recruits (`$1a`). In the tutorial the
enemy's two sub-leaders (`$4e514[0]`, `[1]`, both side 2) sat with
`troops_reserve` ramping `$46 → $84` purely from returning patrol detachments;
the player's manpower is held the same way in the player's own leader record.

**Mode `$16` disband** (`$15042`, the "go home" path):

```c
void h_disband(pm_object *A1) {                 // entity mode $16
    jsr_16848(A1);                              // detach from group bookkeeping
    if (g_world_phase /*$57fd0*/ != 0) {        // world still animating in
        A1->dwell = -99; A1->prev_mode = A1->mode; A1->mode = 0x7c; return;
    }
    leader *L = &leader_of(A1->nation_off);     // $4f916[nation_off].nation_off -> $4e514
    L->troops_reserve += 2;
    if (A1->order_class == 8) L->troops_reserve += 2;   // "veteran" bonus?
    A1->target = unpack_cell(A1->group_off_lobyte);     // head to the packed muster cell
    A1->prev_mode = 0x18;  A1->mode = 0x10;             // walk there, then vanish
}
```

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

What `$4342` does **not** contain: any add to `troops_reserve`, any food
counter, any population maths. The delivery payoff (what a completed herd-drive
gives the town) was not observed — no `$4c5f4` marker reached `byte15 == 0` in
the quiet view, so this is the top item for pass 2: `watch` a marker's `byte15`
and the leader pools across a run where a herd actually completes, or force one.

`$5ec6` is the matching entity mode: it assigns a unit (`20(herd_op)` ← the
shepherd) to a specific animal and gives it a patrol path (`$16964`-relative)
and a target from `$580a6[side]+8`. The shepherd/hunter behaviour proper is
another mode chain not yet walked.

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
does **not** transfer a stored population — the settlement's future production
follows the ownership byte.

### The `$163ea` aliasing observation (needs verification, pass 2)

`watch $4f916 240` over 90M steps showed a steady stream of writes at PC
`$01643c` / `$016482` / `$01645c` landing on `$4f916 + i*$12 + {2, 20}` for many
`i`. Those PCs are inside **`$163ea` (`pm_relink_bucket`)** — the `$47970`
doubly-linked-cell-bucket maintenance — writing `bucket_prev` (`2(A3)`, A3 =
`$51b66 + link`) and the bucket head (`0(A2,D7.w)`, A2 = `$47970`). For those
writes to reach `$4f916` the link word or the cell index must be far out of the
legal range (`$47970` is only ~4–5 KB of buckets; object links are byte offsets
into a ~$63CE-byte array, so bit 15 is never legitimately set).

Reading: a set of **dead / never-initialised object slots** with stale large
`world_x/world_y` or link words are being relinked into out-of-bounds bucket
positions that alias the `$4f916`/`$4e514`/`$4d252` block. It is very likely
benign (those slots have `owner == 0`, never render, and the garbage they write
into the settlement tail is `_w0`/`_w2`/`_w16` — fields nothing reads), but it
should be confirmed against a real-Hatari trace before it is trusted as
harmless, and it means **the 73rd pass's `pm_nation.chain_next` at +2 was
wrong** (the real chain link is +8; +2 is scratch that `$163ea` scribbles).

## 4. Weapon grade — "invention" as the game surfaces it

The player-facing "your men have invented pikes / bows / cannon" is represented
as **object record byte 44** (`pm_object`, wrongly named `msg_code` in the 70th
pass — it is dual-purpose: a transient message code in the `$16260` notify path,
and, for a combat unit, its weapon tier).

| site | reads byte 44 as | effect |
|------|------------------|--------|
| `$1533c` (melee, mode `$32`) | weapon tier | `damage = (min(grade, 6) >> 1) + 1` per tick → 1..4; the `min(.,6)` caps the melee benefit at tier 6 |
| `$52fc` / `$5318` (`$5188`/`$532e` projectile spawn) | weapon tier | projectile **type** `D1`: default `$12` (the area-effect arrow), `$28` when `byte44 == $6` |
| `$3ffc` (`$3e06` speed calc) | `byte44 >= $e` → `+$10` force bonus | tilts the objective-unit speed term |
| `$9846` / `$9dc6` (`$a242` string table) | index | the "carrying …" clause in the on-screen unit description |

Where it is **set**: only at unit creation.
- `$245c` (`$238c` setup): every group **lead** gets `byte44 := 6` unconditionally
  (the `move.b 21(A2),44(A1)` one instruction earlier is immediately clobbered).
- `$2500` (`$238c` setup): every **follower** gets `byte44 := 23($580a6 + side*$20)`
  — and `$10d1e` clears assessment bytes 16..23 to zero, so tutorial followers
  start at grade **0**.

No routine was found that *advances* byte 44 over time — there is no research
counter, no per-town invention percentage in the mapped structures, and the
`$67d0` campaign hook (`strategy.md`) is the only path by which a scripted
mission could bump it. So in the procedural tutorial, weapon grade is a fixed
per-unit stamp (`6` for leads, `0` for followers) and never improves. Whether a
real campaign mission carries an invention-progression subsystem, or whether
grade is re-stamped from the home settlement at recruit time (mode `$1a`), is a
pass-2 question — the recruit path (`$150c0`) does **not** touch byte 44 today.

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
clamps every cell `>= 0`. This is the fertility / carrying-capacity field the
livestock system and (presumably) any growth payoff read. `$4672` then scatters
10 clusters of animals (`$4788`) and herd markers across buildable cells.

## What is not here (pass-2 targets, in priority order)

1. **The livestock-delivery payoff.** Force a `$4c5f4` herd marker to `byte15
   == 0` (or watch one that completes over a very long run) and capture what it
   adds — to `troops_reserve`? to a food counter? Watch the leader pools and the
   `$3f86c` fertility cells around the destination town at the moment of
   arrival. This is the missing link between "sheep" and "population".
2. **Passive population growth.** Run 1–2 **billion** instructions from a settled
   snapshot with `watch $4e514 64` and `watch` on any settlement scalar, and see
   whether `troops_reserve` ever moves without a unit-return event. If it never
   does, PM has no free growth and manpower is purely a conservation-of-soldiers
   system — a real finding worth stating.
3. **Invention progression.** Confirm byte 44 is never advanced (billion-step
   watch on a combat unit's `+44`), then check whether a *campaign* mission
   (`$580a0 != 0`, a real byte script) seeds `$67d0` with an invention order, or
   whether `$2984` (still not disassembled) stamps a per-nation tech level that
   recruits inherit.
4. **`$2984` / `$3338` / `$3528` / `$37f6`** — the un-mapped `$4f916` readers in
   the `$2200`–`$3500` cluster. `$2984` runs at world-build alongside `$238c`;
   the others may be the periodic settlement update this pass failed to find.
5. **Verify the `$163ea` aliasing** against a real-Hatari `cpu_disasm` trace of
   `$163ea` — rule it in or out as an emulator bug.

## Traces / artefacts (74th pass)

- `scratchpad/pm74_quiet.evt` (352 MB, 150M steps from `pm71_run1`), processed to
  `pm74_blocks.txt` / `pm74_cg.dot` with `pm74.names`. Confirms `$4342` is a
  per-tick child of `$3e06`; no economy-shaped routine outside the known tick.
- `scratchpad/pm74_late.snap` (`pm71_run1` + 400M steps, PC `$000124c0`) and
  `pm74_run1.ram` / `pm74_late.ram` — the settle-diff (biggest movers: `$4c5f4`
  151 B, `$4d252` breed bytes → `$0d`, `$4e514` leader pools).
- `scratchpad/pm74_watch{1,4}.err` — the `watch` hit logs (`$1507c`/`$15e18`
  reserve growth; `$163ea` settlement-tail writes).
- `scratchpad/pm74_disasm.txt` — linear disassembly `$1000`..~`$45000` of
  `pm70_iso.ram`, for grepping.
