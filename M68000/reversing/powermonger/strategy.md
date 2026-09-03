# PowerMonger ST — the strategic layer (the commander AI)

Reverse-engineered 71st pass, continuing `ai.md`. `ai.md` covers the per-entity
state machine (`$14b62`, ~2.4 Hz); this file covers the layer above it: how a
captain decides to march an army at an enemy, and how that decision reaches the
entity loop. Same method — disassembly of `scratchpad/pm70_iso.ram` (game image
at its absolute addresses), block traces, and field watches — driven from
`scratchpad/pm68_isoview.snap` / `pm71_run1.snap` (first mission, "Between
Pages 1-5").

## Where it runs

Five routines run **once per simulation tick** — the same ~2.4 Hz tick that
drives `$14b62` (measured: ~13 calls per 250 VBLs). They are the tail of the
sim-tick body `$13000` (which is *not* per-VBL — the per-VBL camera/renderer is
a separate path, see `graphics.md`), gated by `$57ff2 == 0` (not paused) and
`$14e4e != 0` (a game is running, set by the briefing OK click — `README.md`):

```
$13040  jsr $127e6   ; on-screen event-marker / notification-ticker feed
$13046  jsr $6522    ; per-commander order pipeline   <-- the commander AI
$1304c  jsr $d322    ; per-side troop accounting        -> $57fba
$13052  jsr $3e06    ; flag-health UI + per-objective budget decay + $57fba objective term
 ...
$130c8  jsr $6a3a    ; order executor: consumes $58016, drives group state + lead-man mode
 ...
$130f6  jsr $d23a    ; $57fba -> $57fce relative-strength ratio (UI mood indicator)
```

The 70th-pass note "called every sim tick from `$13040`" is right; `$13000`
itself is the tick.

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
`$6522`).

## Open threads

- **Trace the AI from a live enemy.** Needs a later campaign mission (or a
  provoked mission 1) where the enemy captain's command slot naturally reaches
  `byte4 == 4`. Only then can `$68fe`'s target choice, `$68ee`'s budget maths,
  and the `$08` besiege path be measured rather than single-shot forced.
- `$67d0` / the campaign-order hook: who writes it, and the mission-file format
  that seeds `268()` (the per-objective campaign id) and `$67d0`.
- `$580a6` per-side assessment block: the `$2200`–`$3500` writers, what `+16`
  (the targeting weight) means, and whether diplomacy ever changes the sign of
  the commander id `$3154` uses for friend/foe.
- `$3c08` (order `$08` besiege setup) and `$30fe`/`$39d4` (order `$10` regroup).
- `$5778` combat resolution — still open from `ai.md`.
