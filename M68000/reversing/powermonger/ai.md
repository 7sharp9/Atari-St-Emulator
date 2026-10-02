# PowerMonger ST — the entity / commander decision loop

**Scope.** This file documents the per-entity behaviour state machine that drives every man and boat (the
50-byte object records), and the pools updated beside it (animals, arrows, carrier pigeons): the iterator
`$14b62`, the object record at `$51b66`,
the 75-entry mode table `$14bb4` and its handlers, the group-order handlers that connect the entities to the
commander AI, and the differential proofs of those routines against the real 68000. The commander AI that
issues the orders (`$6522`), the order executor and the combat design are in `strategy.md`; the economy
numbers the handlers touch (food, goods, settlements, the gatherer cycle) are in `economy.md`; rendering is in
`graphics.md`; sound, save disks and the serial link are in `system.md`.

Contents (section titles, in file order):

- Evidence taxonomy; What the loop actually is (with "The simulation tick").
- The iterator `$14b62`; then "Proofs against the real 68000: the iterator and its handlers": the Proven blocks
  for the dwell/upkeep core, the movement modes, melee, the settlement heartbeat, the forest animator `$4342`,
  the regroup dispatcher `$3c08`, `$4bc8` and the flag-bit-4 group teardown.
- The object record (table and C struct); Spatial primitives (`$1648e`, `$164bc`, `$14262`, `$12d56`,
  `$163ea`, `$16260`).
- The behaviour modes (move/path, combat, group orders, static/upkeep/boats/effects); The entity FSM
  (state diagram); Load-bearing handlers, pseudocode.
- Where target selection happens, and what it reads; What each entity decides per tick.
- Measured: the quiet view, the re-armed fight, natural runs on later lands; then "Proofs against the real 68000:
  dying entities, groups, orders, animals and the `$15000` page": the Proven blocks for the dying-entity path
  `$1623c`, the group dissolve `$2776`, the lord's work order `$5cde`, the revolt chain, shepherds / animals /
  carrier pigeons, arrows and carrier pigeons, and the `$15000` page of mode bodies.
- Open threads.

**Method and sources.** First reverse-engineered from the live isometric battle view, driven from
`scratchpad/pm68_isoview.snap` (first mission, "Between Pages 1-5": one player island plus neutral villages).
Every address is a RAM address in the relocated game image (base `$1050`), disassembled from the snapshot RAM
(`scratchpad/pm70_iso.ram`, via `scratchpad/extract_ram.py`). Method: a 25M-step traced resume
(`ATARI_TRACE_EVENTS`), `trace_cfg.py --blocks`, and `watch` on individual object-record fields to catch the
writing PC; later sections add differential tests of the routines against `callcap` of the real 68000
(`tools/pm_fsm_ref.py` is the from-disassembly model, `tools/pm_fsm_diff.py` the harness). The developers'
own symbol names (`powermonger_orig.sym`, 8-character truncations; `strategy.md` "Original names") are quoted
as "original `name`" where a routine's role was checked against them.

## Evidence taxonomy

Claims in this file (and `strategy.md` / `economy.md` / `graphics.md` /
`port/SPEC.md`) carry one of four confidence levels. The load-bearing ones are
tagged inline as **[Proven]** / **[Corroborated]** / **[Observed]** /
**[Hypothesis]**; untagged prose is Corroborated-or-better.

- **Proven** — exhaustive binary/dataflow reasoning, or differential equivalence
  against the real 68000 over many states (the `detcheck`/Musashi standard). Each
  `[Proven]` section below states its gate, state count and byte count. The renderer's
  `$ef62`/`$e420` path (graphics.md) meets the same standard: 128/128 triangle inputs + every
  scanline's DDA span + dither phase byte-exact vs a live single-step.
- **Corroborated** — an independent static read (disassembly of the handler)
  **and** a dynamic check (a `watch` on the written field catching the PC, or a
  register probe at the handler, or a frame diff) agree. The record layout, the
  mode-table groupings, the sprite frame formulas and every mode not named in a
  `[Proven]` section.
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
state machine**. Every man and boat, and the building and marker records the
people interact with, is a 50-byte **object record** in the array at `$51b66`
(original `_sprites` / `_peeps`: 512 slots, slot 0 never walked, so records
1..511). Animals (`$4ccd6`), arrows (`$4be00`), carrier pigeons (`$4c112`), trees
(`$4d252`) and forest markers (`$4c5f4`) are separate pools updated by `$3e06` and
`$4342`, not by this iterator. Each object record carries a one-byte **mode opcode**
at offset 31. Once per **simulation tick** the iterator `$14b62` walks records
1..511 and, for each active one, `jmp`s through a 75-entry table at `$14bb4` to
that mode's handler.
A handler integrates one tick of motion, tests the world, and usually rewrites
its own mode byte to advance the state machine. Mode transitions *are* the AI;
there is no separate planner.

The "commander AI" (whether the Red/Green/Blue lords attack, recruit, or build)
is a thin layer on top: it is expressed as **group records** in the table
at `$51538` (one per captain's group, six per side; strategy.md "`$51538`"), holding
a state enum and a link to the group's lead object record. The group-order state drives which mode the lead man is put into
(`$10` march-to-cell, `$28` wait for recruits (get men), `$1a` take food from a town); the
individual men then follow their own state machines toward the goal.

### The simulation tick

`$14b62` runs once per pass through the sim-tick body `$13000` — see
`strategy.md` "Where it runs — the sim tick `$13000`, disassembled" for the full
call order. In short: `$13000` **is** the tick;
`$14b62` (at `$130c2`) and the executor `$6a3a` (at `$130c8`) run on *every*
`$13000` call, not behind the `$57ff0`/`$57fee` gate (that gate is only the
present-rate divider — `$1870` / `$12ce0` / the two renderers).

Measured (3M-instruction trace): the tick body runs **13× per 250
VBLs** — about once per 19 displayed frames, ≈ **2.6 Hz**. The tick is
compute-bound in this instruction-counted emulator (one full body ≈ 19 VBLs of
instructions; `$1870` only waits one VBL edge). The 97 iterator passes in the 25M-step
quiet view ("Measured" below, ~2.4 Hz) are consistent. `$4bb3e` (long) is the master tick counter, bumped at
`$013034`; its low word `$4bb40` is the wrapping animation-phase value the
iterator uses. `$14e4e` (original `_test_en...`: the protection check's result word, set to `$2c`
by a correct answer, or to `population + $2c` by the cracked briefing OK handler, `README.md`
and strategy.md "The campaign") non-zero is the "a game is running" gate at `$1303a`; `$57ff2`
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
| `$1623c` | dying-entity path (owner < 0, Proven below, "the dying-entity path `$1623c`"): count `18(A1)` down from `$a0`, stepping the flap phase `32(A1)`; at 0 stamp `$4bb3e` into `20(A1)`, credit the dead man's goods codes to a settlement/base leader in the same cell, then `byte6 := $0a` (equipment left lying) or `$20` + unlink |

Active-record count in this settled first-mission view: **~50 of 511 slots**,
of which ~26 reach a handler each tick (the rest are `byte 5 == 0`).

## Proofs against the real 68000: the iterator and its handlers

Method shared by the `[Proven]` blocks that follow: the routine is transcribed line by line from disassembly
into `tools/pm_fsm_ref.py`, and the model is compared against `callcap` of the real routine over a corpus of
natural and poked states, "isolate-by-disabling" (every record other than the one under test is disabled, so
only the routine under test changes memory); a gate passes when every changed byte matches ("tracked bytes
identical"). Branches the corpus cannot reach are asserted off with a `raise` and listed per block. The gate drivers
of the earliest blocks (dwell/upkeep through the group teardown, the forest animator and `$4bc8`) are in `py/fsm/` (`repro93.py`..`repro97.py`,
`diff_pm98.py`, `diff_pm99.py`, `diff_4342.py`, `diff_4bc8.py`, `diff_4bc8_kind2.py`; run from `M68000/`; the `repro*` scripts reuse the earlier
passes' cached callcap deltas only with the argument `reuse`), their anchor snapshots indexed in `scratchpad/ANCHORS.md`; the later gates are in `py/` (`py/README.md`).

### [Proven] — the dwell/upkeep core, vs the real 68000

`$14b62` has **no entry contract**: it `lea`s its own `$51b66` / `$47970` bases
and reads everything else from fixed memory, so `callcap 14b62` runs the whole
iterator over all 511 records and returns cleanly (4554 steps; identical trace
hash + 84-byte delta on repeat = deterministic). A from-disassembly integer
reconstruction (`scratchpad/pm93/fsm_ref.py`) of the **prologue**, **modes
`$12` / `$68` / `$8a`**, **`$5c80`**, the epilogue **`$161c4`**, **`$1648e`**
and **`$163ea`** (+ the `$16778` unlink-at-head branch) matches the real 68000
**byte-for-byte over the full changed-memory delta**: **675/675 tracked bytes
across 22 differential-test states** (`diff_fsm.py` — `pm88_f1` / `pm78_settle`
/ `pm74_late` / `pm73_fight` naturals with every non-target record disabled,
plus poked variants forcing each branch: dwell → `mode := $10`, world-Y
negative → the `$1648e` water veto → `mode := $0`, forced anim trigger ± the
`flags` bit-4 freeze, health below/at/under the job's cap). The
`$5c80` wear-death path (`$5bd2`) is asserted **off** — `anim_wear` maxes at 44
(`< $3c`) in all four captures.

### [Proven] — the movement modes, vs the real 68000

`scratchpad/pm94/fsm_ref.py` extends the reconstruction with the four movement
modes **`$06`** (`$14d32` walk-until-blocked), **`$08`** (`$14d7c` escort/orbit),
**`$0e`** (`$14e70` farmer path spline) and **`$10`** (`$14f08` advance/chase), plus
their leaves **`$164bc`** (step-toward — the DIVU steerer), **`$14262`**
(heading), **`$12d56`** (rotate) and the epilogue **`$16202`**. All transcribed
line-for-line from raw-byte-verified disassembly + the lookup tables
(`tbl_heading_14360.bin` 2048 B, `tbl_trig_13f8a.bin`, `tbl_spline_168ee.bin`).
Same isolate-by-disabling differential test (`diff_fsm.py`): **1335/1335 tracked
bytes identical over 32 states** — `pm73_fight`'s 26 `$06` + 5 `$08` + 4 `$0e`
records, the `$10` records of all four captures (reached / not-reached / probe),
plus poked variants: `$0e` spline advance and all three terminators (`$7d01`
loop, `$7d02+n` jump-to-mode, `$7d00` end→`$92`), `$10` chase (`prev_mode := $2e`
tracking a live entity), the `$2c` dead-target conversion, `$06` dwell→`mode $08`.

- **`$164bc`**: `sub.w` dx/dy → 4-quadrant fold → `divu speed` on the major axis,
  `divu` the quotient on the minor, then a swap-dance that leaves `D0.w`=step_x,
  `D1.w`=step_y, `D2.w`=count; `dwell := count>>1`; **`beq` on return = reached
  = `count>>1 == 0`** (confirmed byte-exact via `pm78_settle` slot 5, which snaps
  onto the target). `divu #0` (target == current, or a speed-0 entity) traps
  vector 5; PM's handler resumes with the operand unchanged, so `$164bc` still
  returns a well-formed "reached" (confirmed: `pm74_late` slot 7).
- **`$14262`**: octant fold, `shift = shift_tbl[max(|dx|,|dy|) >> 5]`, normalise
  both `>> shift`, `dir_tbl[(dx<<5)+dy]`, per-quadrant fixup (`0x80-d` / `-d` /
  `d+0x80`).
- **`$12d56`**: `cos = word[$1400a + 2h]`, `sin = word[$13f8a + 2h]` (the *same*
  trig table as the renderer's `$fecc` `A3`); `x' = ((x·cos − y·sin)<<1)>>16` (Q15).
- Asserted **off** (out of scope, same discipline as `$5bd2`): the chase-reached
  edge `$15302` (→ `$56a6` engage) and the group-state-8 hand-off `$1518a`
  (→ `$4bc8`) — no natural or poked state in the corpus reaches either.

### [Proven] — the combat path (mode `$32` melee), vs the real 68000

`scratchpad/pm95/fsm_ref.py` extends the reconstruction with **mode `$32`**
(`$1533c` melee) and its leaves **`$56a6`** (engage bookkeeping), **`$5590`**
(kill/rout roll) and **`$30fe`** (`word[group + 60] − 2`). Transcribed
line-for-line from raw-byte-verified disassembly. Same isolate-by-disabling
differential test (`diff_fsm.py`): **413/413 tracked bytes identical over 48
states, 6 branch families.**

Corpus is a **natural** capture: `pm73_fight` driven forward 10.6 M steps until
`$1533c` first fires, snapshotted at the next frame start (`pm73_melee.snap`),
then five more frames (`mel_g1..g5.snap`) as the battle escalates to 33 live
mode-`$32` records — both armies in melee. Poked variants drive each branch.

- **`$1533c`** — every branch: target-loss (`5(A3) <= 0`, or `30(A3) == $3c`, a routed man) →
  `$153a2` (self mode/prev `:= $2c`, epilogue `$161c4`); face-away
  (`17(A3) := 17(A1) + $80`); `31(A3) != $32` → `jsr $56a6`; **health drain =
  `(s8(44(A1)) < 6 ? 44(A1) : 0) >> 1 + 1`** applied `sub.b D0,45(A3)`
  (the `>= 6` arm is a **hard `moveq #0`**, not `min(44,6)`); `> 0` → mutual retaliation (`48(A3) := self`, `31(A3) := $32`,
  `bra $1622c`, no epilogue); `<= 0` → `jsr $5590` then fall into `$153a2`.
- **`$56a6`** — the `btst #6/#4,7(A3)` gates that skip `$5778` when the target's
  flags are clear; `31/30(A3) := $32`; `48(A3) := attacker`; the `$5730` vs
  `$574a` selector on the *attacker's* flags; the `$574a` leaf
  (`46(A3) := (roster→leader entry) − $51b66`, `38(A3) := 2`).
- **`$5590`** — `45(A3) := 0`; the no-group-lead path (`D0 = 0` → KILL); the
  group-lead walk (`A4 = obj[28(A1)]`, `tst.b 5(A4)`), `jsr $30fe`, `D0 == 2`
  → `$560a`; the RNG-parity selector `($57fec + 24(A1)) & 2` when
  `$30fe ∉ {0,2}` (deterministic — the master tick is fixed across a `callcap`);
  `btst #5,7(A3)` forces KILL over ROUT; the KILL body (`neg.b 5(A3)`,
  `32(A3) := 0`, `6(A3) := $c`, `18(A3) := $a0`); the `$5628` tail →
  `$567e` → leader-population decrement `word[leader + 8] -= 1`.

Asserted **off** (no corpus/poked state reaches; `raise` guards it — these are
the deferred *regroup/group modes*): `$5778 → $4bc8` (group hand-off, group
state `!= $d`); `$5590 → $560a → $3c08` (the true ROUT, unit survives — the
`$3c08` dispatcher itself is Proven below, but the ROUT wrapper that
overrides `prev_mode := $3c` and the `$5628` group cleanup around it is not);
the `$5590` tail calls `$2776` / `$1b8c`.

### [Proven] — the settlement heartbeat (mode `$7c`), vs the real 68000 (synthesised corpus, then a natural one)

`scratchpad/pm96/fsm_ref.py` extends the reconstruction with **mode `$7c`**
(`$157e6`, the per-settlement heartbeat) and its leaves **`$16848`** (side ↔
settlement-owner reconcile) and **`$163b8`** (the manpower drain — economy.md
§3a). Isolate-by-disabling differential test:
- **Natural corpus (`py/fsm/repro97.py`): 99/99 tracked bytes
  identical over 27 states, all 12 branch families.**
- Synthesised corpus (`py/fsm/repro96.py`): 85/85 over 25 states.
(obj / `$4e514` leader / `$4f916` settlement / `$47970` bucket regions compared.)

Mode `$7c` requires `word[$57fd0] == 0`. `$57fd0` (original `_season`) starts at
`g_tileset_sel = (byte[$58146] & 3) * 2` (= 4 for mission 1) — but it is **not
static**: `$1abaa` (`$130b0` in the tick) rotates it `($57fd0 + 2) & 6`, cycling
{0,2,4,6}, once per 512 `$1abaa` calls (one wrap of its pixel-order LCG; 118.4M steps measured). So mode `$7c`, and the three same-gated
entries into it (`$1505e` in the mode-`$16` farmer-home handler, `$15a46` in the mode-`$4e` merchant arrival,
`$15b7a` in the mode-`$5e` fisher arrival), run
in mission 1 during the brief `$57fd0 == 0` phases, **transiently, not never**.
No ordinary capture froze a `$7c` record because the windows are short.
The natural corpus **`pm97_map0`** is a real mission-1 world with `$57fd0` pinned to 0 at
world-build (the value the game visits anyway — just pinned so the phase
persists): 80M steps later, 19 natural `$7c` markers on 10 real `$4f916`
settlements (2 under construction), entered by the game's own `$1505e` / `$15a46`
/ `$15b7a`, leaders at `loyalty_pressure` 316 / 318. The synthesised corpus poked
`$57fd0 := 0` on pm78_settle and repurposed inert `$68` records into fake `$7c`
markers.

- **`$157e6`** — `dwell` decrement (`> 0` → next record, no epilogue);
  `jsr $16848` + `jsr $5c80` (twice); `D5 := post-decrement dwell`; reload
  `18(A1) := $580a6[side·$20].word0`; `jsr $163b8`; `btst #4,7(A1)` →
  straight to the epilogue; construction (`7(settl) == $a`, a Ruin → `16(settl)++`, at
  `>= $78` → building kind (`7(settl)`) `:= dest_cell % 10` via `divu #$a`/`swap`, `== 7` (a WorkShop) →
  `6(settl) := $10` (its render category), `16 := 0`); `troops_field·4` vs `food`
  (`== 0` → skip; `>= food` and `D5 == $ff9c` → `loyalty += 2`;
  `< food` and `D5 == $ff9c` → `loyalty −= 1`); epilogue `$161c4`.
- **The loyalty accumulator only moves when `D5 == $ff9c`** — i.e. on the first
  `$7c` tick after the marker is parked with dwell `#$ff9d` (`−99` → `−100`).
  On an ordinary steady-state pulse `D5 == 0` and neither `±` branch runs, so the accumulator does not
  move one step per settlement pulse.
- **`$163b8`** — `settlement.leader.food −= 1`, floored at 0. This is
  the entire per-settlement upkeep drain; in mission 1 it fires only during the
  intermittent `$57fd0 == 0` phases (above).

Asserted **off** (`raise` guards it): **`$5cde`** (the lord's work-order
choice — a whole routine; every `field·4 < food` state is arranged with
`(14(A1) & 3) == 3` so it is skipped), **`$550e`** (hunger revolt, loyalty
kept `< 600`), **`$5c2c`** (owner reconcile inside `$16848`).

`$5cde` is Proven on its own (below, "the lord's work order `$5cde`"); the heartbeat proof still keeps it
off. The dying-entity path `$1623c` is Proven below too.
Modes `$28` and `$2e` (`$15302`) are covered by the `$15000`-page gate (the last
Proven block; `$2e` calls the same `$56a6`).

### [Proven, 8/9 branches] — the forest animator `$4342` (original `_do_fore...`), vs the real 68000

`$4342` (called from `$3e06`, once per sim tick) animates the on-screen forest markers. It is a no-op in every
*natural* capture, including `pm97_map0` (every `tree_state`-bit-7 tree has `worker_obj == 0`; every `$4c5f4`
marker has `progress == 0`), so its gate uses a synthesised corpus built on `pm97_map0` (8 live forest ops,
68 markers). It has no entry contract (it `lea`s all three of its own tables: `$57f68` forest ops, `$4d252`
trees, `$4c5f4` markers). Structure and field meanings: economy.md §2.

The model is `tools/pm_fsm_ref.py` `call_4342` plus a leaf `call_16808` (bucket-chain insert, the CLAIM
path's screen-record spawn; `bucket_unlink`/`$16778` was already Proven from the entity FSM). Differential test
`py/fsm/diff_4342.py`: **110/110 tracked bytes identical over 9 states, 8 branch families**
(natural idle; the CLAIM mechanism itself, its precondition-guard failure, and its "no empty op slot"
fallback; both ramp-in sub-cases, unclamped and clamping to `+$30`; the dwell-not-yet-expired skip; a real
`$164bc` step that doesn't arrive; and the owner-sync byte-14 write). Pre-registered bar (100% over >= 9
states, >= 7 families): PASS.

Two bugs in the model's leaf machinery (not in `$4342`) are general 68000-semantics traps, so they are
recorded here:
1. **Missing full-skip guard.** The first model routed `byte15 == 0` into the "moving" branch instead of
   skipping the marker entirely (`beq $452a` in the real asm). The **natural** state (zero pokes) showed 235
   spurious recon-only changes against a real hardware delta of zero, so the simplest possible state caught it.
2. **Unsigned vs. sign-extended address arithmetic.** `bucket_unlink`/`call_16808` computed `OBJ + rec_off`
   as a plain unsigned add. Every other caller passes a positive `rec_off` (a `$51b66`-table entity lives above
   `OBJ`), but `$4342`'s markers live at `$4c5f4`, *below* `OBJ`, and a real `adda.w D0,An` sign-extends the
   16-bit word first, so their `rec_off` is genuinely negative. The shared helper
   `_objaddr(rec_off) = OBJ + s16(rec_off)` fixes both functions and is a no-op for positive offsets.

**Not closed: the "arrived" branch** (bset the tree's bit 7 back on and `$16778`-unlink the marker). It reuses
the proven `bucket_unlink`/`_objaddr` machinery in the remove direction (the claim path proves the insert
direction extensively), so it is Corroborated rather than untested, but every synthesised poke that reaches
it (an exact-target degenerate `$164bc` divide by zero, and a 1-unit-off normal division) reproducibly hangs
the real emulator within ~3000 steps, parked in a timer-interrupt `rte` (`$14e4`) per the loop detector. Not
root-caused: `bucket_unlink` alone cannot loop forever on these inputs (it is a bounded walk with no cycle
risk from what was poked), so this is either a separate real-68000/game-state interaction that the synthetic
state exposes, or a missing precondition (a marker that was never actually `$16808`-inserted at that cell,
unlike a naturally claimed one). The repro is left in `py/fsm/diff_4342.py`, excluded from the pass
bar.

**Tracked-region note.** The forest tables (`$4c5f4`/`$4d252`/`$57f68`; `HERD_REGIONS` in the code, a name
kept from the first reading of `$4d252`) are deliberately not folded into `pm_fsm_ref.REGIONS`: doing so
widens the tracked window of every `$14b62` (`reconstruct()`) test and surfaced a real, separately owned gap (a
live write into the tree table's unknown `_w4` field, `$4d819`, that `reconstruct()` does not model) which broke
the established 675/675 and 1335/1335 bars. `pm_fsm_ref.HERD_REGIONS` holds them instead; a `$4342` test adds
`pm_fsm_ref.REGIONS = pm_fsm_ref.REGIONS + pm_fsm_ref.HERD_REGIONS` itself (process-local, never mutates the
module for anyone else; see the top of `diff_4342.py`).

### [Proven] — the regroup / return-home dispatcher `$3c08`, vs the real 68000

`$3c08` is the `word[$57fd0] != 0` branch of the mode-`$7c` dispatch `$157ba`,
and a leaf `jsr`'d from 17 sites across the entity FSM and the group-order
system (the mode-`$16`/`$4e`/`$5e` handlers, the `$5590` ROUT path `$560a`, …).
Entry contract: **just `A1`** (the object record) — it `lea`s its own
`$51538`/`$4f916`/`$4e514` bases, like every other `$14b62` handler.

`tools/pm_fsm_ref.py` `call_3c08` + `call_16892` + `h_mode7c_regroup`.
Differential test `py/fsm/diff_pm98.py`: **71/71 tracked bytes identical
over 22 states, 11 branch families** (`callcap 3c08` direct with `A1` preset for
16, `callcap 14b62` end-to-end through the `$157ba` dispatch for 5). Pre-registered
falsifier / bar (100% over ≥ 15 states, ≥ 8 families): PASS. `hostile.py`'s 5
negative controls (prev-mode table entry, `w22` low byte, the byte-6 guard, the
`$4c` bit-4 prev-mode, the `$16892` gate) all bite; two `callcap 3c08` byte-identical.

- **`$157ba` dispatch:** `word[$57fd0] == 0` → `$157e6` (the heartbeat, above);
  else `jsr $12c9a` (RNG — reseeds `$580a0`, outside every tracked region),
  `jsr $16892`, `bne $1622c` (skip), else `jsr $3c08`; `bra $1622c` (no epilogue).
- **`$16892` — equipment pickup gate (tried first):** if any of
  `owner_leader.goods[3..0]` (`$4e514 + 24 + i`) is non-zero → retarget the
  record to the leader's cell (`4($4e514+idx)`: `20 := cell & $3f`, `21 := $80`,
  `22 := ((cell & $1fc0) << 2) + $80`), `prev_mode(30) := D2`, `mode(31) := $10`,
  return 1 (caller skips `$3c08`). All goods zero → return 0. **D2 is the caller's**: `$157d2` (this dispatch, non-winter) passes `$90`
  (arrival runs `$160f2`: `$3c08`, then the swap), `$4f82` (inside the `$4f68` target picker, for a man with byte 7 bit 6 clear and byte 44 == 0) passes `$8e`
  (arrival runs `$160e4`: the swap, then mode `$2c`; the picker skips target choice when the gate returns 1). The gate tests goods[0..3] non-zero, not
  "usable by this man": a lord holding only Ploughs sends every unarmed soldier and merchant on a pointless walk to him every ~3 ticks (`k5/s10`, 67 retargets in
  10M steps). The swap itself (weapon bow > sword > pike, farmer's Plough, the stale-D0 misdirection for lord index >= 8) is in economy.md §2c.
- **`$3c08` — flag-driven regroup:** pick `prev_mode` (byte 30) from the record's
  flag bits, in order: bit 7 → `$7e`, bit 0 → `$16`, bit 1 → `$4e`, bit 2 → `$5e`,
  bit 3 → `$80`, bit 4 → (group teardown, then `$4c`), none set → `$7e`. Then the
  shared tail `$3ca2`: retarget to the **settlement's** cell (`12($4f916+34)`:
  `20 := cell & $3f`, `21 := $80`, `22 := ((cell & $1fc0) << 2) | $80`),
  `mode(31) := $10`, and `iff owner > 0` clear category byte `6 := 0`. The units
  then walk home under the already-Proven mode-`$10` handler.
- **The flag-bit-4 group-teardown sub-path** (Proven, see the teardown block below). `$3c46`: `D2 := 42(A1)` (group offset); `!= 0` → `jsr $37c2` ;
  `group.state($51538+D2) := 7` ; `jsr $17a46` ; `prev_mode(30) := $4c` ; fall
  into the `$3ca2` tail. See the sub-section below.
- **`$4bc8`** is Proven for all three real call sites (`$5778`, `$1518a`, `$5c2c`): see the next block.
- **`$2776`** (the `$5590`-tail and `$25d6` group dissolve): Proven (below, "the group dissolve `$2776`"). **Still Corroborated:** `$1b8c`-via-`$5778`, a *different* `$1b8c`
  call site from the one proven here.

### [Proven] — `$4bc8` contact reconcile (nation-pair peace-break + player notify), vs the real 68000

(Original `_setup_f...`, inferred to be "set up fight": it decides what a contact between two sides does. The
role above is read from the body, not from the name.)


`tools/pm_fsm_ref.py` `call_4bc8` (+ leaves `_classify`/`$4de2`, `call_4dae`/
`$4dae`, `call_35f4`/`$35f4`, `call_3744`/`$3744`). Entry: `A0`/`A1` = the two
`$51b66` object records in contact. Differential test
`py/fsm/diff_4bc8.py`: **51/51 tracked bytes identical over 8
states, 6 branch families** — both sides classified via `$4de2` into a
`(byte_class, kind)` pair (kind ∈ `{4,6,8,10,12}` covered; kind 6 is the
settlement-distance fallback, kind 4 is the bit4-direct-group-check-on-self
path, 8/10/12 are bare `rts`); a byte-class mismatch dispatches each side
through `$4cb8`'s per-kind table (`$4d40` group-disband-via-`$4dae` for kind
4, `$4d9a` single-`$4dae`-reset for kind 6, no-op otherwise) and clears a
side-relation bit in `$580a6` (untracked, not in `REGIONS` — modelled for
fidelity, inert for the diff); a byte-class match instead ends either side's
group order via `$35f4` (the camp) iff that side is kind 4 and its own group is in state `8`
(both the `D6==4` and the mirrored `D7==4` arm covered). `$35f4`'s own ring-
scatter (up to 4 rings, `$12d56`-rotated radial placement) and lead-to-
formation-follower (`$68`) conversion are fully exercised; its `$4cff8`
GARRISON-table marker-placement sub-path (`$3744`) is bypassed by
construction in every test state (lead's bit5 flag set) since that table
isn't in `REGIONS` — a diff there would be invisible regardless, so it's
flagged as a followup rather than silently assumed correct. `$c5ee`
(player-notify) / `$311a` (relation-event) are asserted, not verified, to
write only outside every tracked region (same precedent as `$17a46`, in the
teardown block below) — never differential-tested directly.

**Kind 2 (leader/settlement).** Reached via `$5c2c`'s own
call (`A0` = a `$4e514` leader record, always kind 2) or `$4de2`'s "close to
home settlement" redirect; drives `$4ee8` + `_case_4cd0`. `$4ee8`: `self_side`'s
own `$13c`-stride `$51538` record carries 6 word arrays (bases 28/76/64/40),
one entry per *other* side — an active order (`28+i·2 != 0`) whose own group
state isn't already `$d` (`76+i·2`) and whose military lead (`64+i·2`) sits
within Manhattan-max 15 of the leader's home cell (`4(leader)`) recursively
re-enters `$4bc8` against that lead (real `$4bc8`'s `movem.l #$fffe` prologue
saves/restores nearly every register, so the recursion is transparent to the
caller's own D5/D7 bookkeeping — `tools/pm_fsm_ref.py` mirrors this by
save/restoring its `_NOTIFY_OTHER_*` globals around the recursive call, a real
bug the first model missed). `_case_4cd0`'s tail then walks every settlement
this leader owns (`2(leader)` chain) and every resident man at each (`10(settl)`,
then the `24(man)` chain), `$4dae`-resetting any that isn't already
group-linked-active (bit4 + `42 != 0`), bit6-flagged, or in a regroup mode
(`$5c`/`$60`/`$62`). Differential test `py/fsm/diff_4bc8_kind2.py`:
**20/20 tracked bytes identical over 2 states, 2 branch families** — one
exercising the `$4ee8` recursion landing on a real nested mismatch/notify
(verified the recursion's register-restore fix actually matters, not just
theoretical), one exercising a 2-settlement chain with a 2-man sub-chain
covering all three skip conditions plus the normal reset (spot-checked
per-record: the reset and both skips landed on exactly the intended slots,
not a "both sides happen to agree on doing nothing" false pass). `$4bc8` is
Proven end-to-end for all three real call sites.

### [Proven] — the flag-bit-4 group teardown behind `$3c08` (`$37c2` / `$1d70` / `$1b8c` / `$17a46`), vs the real 68000

`tools/pm_fsm_ref.py` `call_37c2` / `call_1d70` / `call_1b8c` / `call_17a46`;
the `raise` in `call_3c08`'s bit-4 arm is gone. Differential test
`py/fsm/diff_pm99.py`: **1847/1847 tracked bytes identical over 13
states, 10 branch families** — `callcap 37c2` (entry contract: `D2` = group
offset), `callcap 1d70` (`A3` = group record), `callcap 1b8c` (`A0`/`A1`/`D1`),
`callcap 3c08` (the whole arm), and `callcap 14b62` end-to-end. Anchor
`scratchpad/pm97/pm97_map1` — its one natural grouped record, slot 21 (flags
`$10`, group 392, `group.state 6`), drives `$3c08` bit-4 → `$37c2` (bit-7 clear)
→ `$1d70` over all 26 roster members (slots 22..47). Pre-registered falsifier /
bar (100% over ≥ 12 states, ≥ 7 families): PASS. `scratchpad/pm99/hostile.py` —
5 negative controls (`$382a` `troops_field −= 1`, `$1d70` member mode, `$1d70`
`asl.w #6` target, `$37c2` owner re-parent, `$1b8c` `troops_field += 1`) all
bite; per-family delta address classes are exactly the disasm's fields; two
`callcap 37c2` byte-identical (`$05ad26002a549747`); `detcheck 1000000` clean.

- **`$37c2` — tear the group lead out of its group.** `D2` = group offset; `A1'
  := $51538 + D2` (group record), lead entity `A0' := $51b66 + word[grouprec−12]`.
  `iff lead.owner > 0` clear `lead.category(6) := 0`. Then branch on
  `lead.flags` bit 7:
  - **bit 7 set** (re-parent / hand-off): `lead.owner(5) := byte[grouprec−47]`;
    `lead.settlement.word10 := lead.word24`; `lead.word34 := grouprec.word24`;
    clear flag bit 7, set flag bit 4. Then on `lead.flags` bit 6: **clear** →
    `owner_leader.troops_field(8) −= 1` (the `$382a` economy row, Proven here);
    **set** → `jsr $1b8c` (`A0 := $51b66 + lead.word28`, `D1 := 0`).
  - **bit 7 clear** (the natural slot-21 case): if `grouprec.state == 6` and
    `lead.word46` resolves into `[$4cff8, $4d250)` → that record's `flags(7) :=
    $11`; then `jsr $1d70` (`A3 := grouprec`).
- **`$1d70` — the rank former, the developers' `_rerank`: it places each man of a group in a formation slot by weapon class** (also run on every successful join, strategy.md "What each order does", so it is a rank former and neither a "send everyone home" step nor a capture routine; the rank-shape strings are weapon-class layouts, not terrain: `word[$1e8c + byte44]` maps the carried weapon code to a class letter, 2 Pike `'P'`, 4 Sword `'S'`, 6 Bow `'B'`, else `'N'`, read from RAM and shown live by a `callcap` with 4 swords, 4 bows and 18 pikes poked into the 26-man group: swords placed on row 0, bows on row -2, pikes on rows -1 and 1..3, `scratchpad/pm134/audit/live/cc1d70.json`). Selects a
  rank-shape string (`rank_sha...`) from a table at `$1e9e`, whose head is the signed column table 0..10, -10..-1 (21 columns), indexed by the highest set bit of
  `word[grouprec−24]` (`D1 := 2·(15 − highbit)`); the string is a row layout of
  weapon-class letters (`'C'`=`$43` the lead's slot, `$00` boundaries, `$ba` an unusable slot). For each roster member (chain via `word[+26]` from
  `word[grouprec−36]`): read its weapon-class char `word[$1e8c +
  byte44]`; do a two-way scan outward from the `$43` marker for the nearest slot
  of that class (falling back to the first *passable* cell via the `D3` latch);
  `bset #7` that cell so the next member picks a different one (this is what
  spreads the group out along the route); convert the found offset to a step
  `(dx,dy)` via `divu(dist, len)` + a lookup into the route data, then write
  `20/22 := (dx,dy) << 6` (world units), `mode/prev(30,31) := $08`, `dwell(18)
  := 0`, `category(6) := 0`. A cleanup pass clears the `bset` marks afterward.
- **`$1b8c` — roster unlink.** `A3 := $51538 + word[A0+42]`; `iff group.word[−24]
  != 0`: decrement it; unlink `A1` from the `word[+26]` roster chain (head or
  mid); `bclr #6` `A1.flags`; `A1.word28 := 0`; `iff A1.owner > 0` → `jsr $3c08`
  recursively on `A1` then `owner_leader.troops_field += 1` (inverse of `$382a`);
  `iff D1 != 0` → `jsr $1d70`.
- **`$17a46` — minimap redraw.** Copies group-state glyphs into `*($e0d4)` (the
  HUD minimap buffer). **A tracked-region no-op** — `callcap` touches 0 bytes in
  any tracked region.

## The object record (50 bytes, stride `$32`, array `$51b66`, slots 1..511)

Fields are **overloaded by entity category** — a marching soldier and a spell
effect reuse the same bytes for different things. This is the common layout:

| off | type | meaning |
|-----|------|---------|
| 0 | word | **next** in this cell's entity bucket (offset into `$51b66`, 0 = tail) |
| 2 | word | **prev** in the bucket |
| 5 | byte | **owner / strength**. 0 = slot free (skip). `>0` = live, value is the owning commander colour (1..4) or a small count. `<0` = dying, `18(A1)` counts down to removal |
| 6 | byte | **category** (the render/click tag; `$115e0`'s draw dispatch and the click table `cjt`, strategy.md "The game's own text"): `$00` man, `$02` house, `$04` tree frame, `$0a` loose equipment, `$0c` corpse in decay, `$0e` a sitting man (the camp), `$10` house (WorkShop), `$18` catch marker or boat, `$1e` building going up, `$20` never drawn (free), `$2c` goods pile, `$3c`… (checked by the neighbour scans) |
| 7 | byte | **flags** (overloaded): bits 0..3 the job (farmer, merchant, fisher, shepherd; `$3c08` maps them to the home modes `$16` / `$4e` / `$5e` / `$80`, economy.md §5a); bit 4 the leader flag (a lord's captain, a group lead; the iterator does not advance the animation frame while it is set; also "stamped by the lead" in `$d322` / `$14f08`); bit 5 afloat (a Boat carrier) / "blocked, needs repath"; bit 6 member of a group roster (`$1b2a` sets it, `$1b8c` clears it; also the "can fight" test of `$56a6`); bit 7 render-cull / hand-off marker (`$d322`, `$37c2`) |
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
| 33 | byte | **carried item code** `2 * (slot + 1)` (`$0a` = Boat, 8 = Plough, `$0c` Pot ...; porters pick it up and drop it at `$159de`/`$159a4`, economy.md §3); a man carrying a Boat is `$02`/`$8c` afloat with flag bit 5 (71 of 71 and 17 of 17 live) |
| 34 | word | byte offset into the **building table `$4f916`** (original `_houses`; the 18-byte settlement records; this is the man's home settlement, `nation_off` in the code); the iterator also compares it with the animation phase (`cmp.w 34(A1),D0` at `$14b8c`) as the frame-advance trigger |
| 36 | word | saved origin X, or a packed destination cell |
| 38 | word | saved origin Y |
| 40 | word | cursor into the **patrol-path table `$168ee`** (or the obstacle-sweep angle for mode `$48`) |
| 42 | word | **packed muster cell** {x = bits 0-5, y = bits 6-12}, *and* the group id: byte offset into the **group-order table `$51538`** |
| 44 | byte | **weapon item code** `2 * (slot + 1)` (pike 2, sword 4, bow 6; catapult and cannon only for a man with flag bit 4, never written in practice; economy.md §2c and §4: byte 44 is the weapon tier, byte 33 the tool tier); also a transient notify code (consumed + cleared by `$16260`) and the carried-item tag of a merchant |
| 45 | byte | **health**: the captain panel prints `(45 >> 4) & 7` through `healthnames` (`$a2dc`, "Very Sickly" ... "Very Strong"; "Dead" when byte 5 < 0). Drained by melee (`$1533c`), recovered by `$5c80` up to the job's cap |
| 46 | word | offset into `$4e514` (leader table), or a lead's recruit quota (order `$08`, `$15122`) |
| 48 | word | link to the **target** object record (the entity being chased / attacked) |

### As a C struct

Every offset below is confirmed by disassembly of a handler that touches it.
The comment says which handler / routine pins it. `//` = decoded; `// ??` = seen
referenced but purpose not proven. The record is a tagged union on `category`
(byte 6): a man, a boat, a building or marker record and equipment lying on the
ground share the 50 bytes and reinterpret the tail.

```c
typedef struct pm_object {           // array $51b66, stride 50, slots 1..511 (512 slots, slot 0 never walked)
/* 0*/  u16  bucket_next;            // $163ea: next in this cell's $47970 chain (byte offset into $51b66, 0 = tail)
/* 2*/  u16  bucket_prev;            // $163ea / $16778: prev in chain
/* 4*/  u8   _pad4;                  // ?? (never read in the traced handlers)
/* 5*/  s8   owner;                  // $14b72: 0 = free slot, >0 = live (commander colour 1..4 / small count), <0 = dying
/* 6*/  u8   category;               // render/click tag: $00 man, $02 house, $04 tree frame, $0a loose equipment, $0c corpse in decay
                                     //   (dwell $a0), $0e sitting man (camp), $10 WorkShop house, $18 catch marker / boat,
                                     //   $1e building going up, $20 never drawn (free), $2c goods pile, $3c ??
/* 7*/  u8   flags;                  // bits 0..3 job (farmer, merchant, fisher, shepherd); bit4 = leader flag / stamped by lead
                                     //   ($d322,$14f08); bit5 = afloat / blocked-needs-repath; bit6 = in a group roster, can-fight
                                     //   ($56a6); bit7 = render-cull / don't-count ($d322), hand-off marker ($37c2)
/* 8*/  s16  world_x;                // 0..$3fff   (movem.w 8(A1),D6/D7 at the top of every handler)
/*10*/  s16  world_y;                // 0..$1f40
/*12*/  s8   step_x;                 // signed per-tick velocity, added to world_x by nearly every handler
/*13*/  s8   step_y;
/*14*/  u8   anim_wear;              // $14b9a: ++ once per animation cycle. Doubles as the $5c80 wear counter
                                     //   (the health cap collapses once anim_wear-$3c > 0). Not reset by the handlers seen.
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
/*33*/  u8   carried;                // item code 2*(slot+1); $0a = a Boat: special-cased in $14c92,$14d32,$14f08,... (afloat, flag bit 5)
/*34*/  u16  nation_off;             // byte offset into the building (settlement) table $4f916: the man's home settlement
/*36*/  u16  origin_x;               // $14e56: saved (x,y) at the start of a patrol; also a packed dest cell
/*38*/  u16  origin_y;
/*40*/  u16  path_cursor;            // $14e70: byte cursor into the patrol-path table $168ee.
                                     //   $158da ($48): the obstacle-sweep angle instead.
/*42*/  u16  group_off;              // byte offset into the group-order table $51538 (== the group id).
                                     //   Low 6 bits + next 7 bits also decode as a packed muster cell {x:6,y:7}.
/*44*/  u8   weapon;                 // item code 2*(slot+1), the weapon tier ($1533c, $52fc); also a transient "under attack"
                                     //   notify code (consumed + cleared by $16260 / $159a4) and a merchant's carried item
/*45*/  s8   health;                 // melee HP (panel: healthnames): $1533c drains it, <=0 -> $5590 (kill/rout). $5c80 recovers it, 1 per tick at random, up to the job's cap $5ccc.
/*46*/  u16  leader_or_quota;        // $15122: a lead's recruit quota (order $08); $34f2 sets a townsman's to the lead's offset, read by $15282; $5bd2: offset into $4e514 for the kill credit
/*48*/  u16  link_target;            // the entity being chased / attacked ($14f08 mode $10, $15302, $56a6)
} pm_object;                         // sizeof == 50
```

Arrows have their own 16-byte slots (`pm_effect`, after the mode table's Combat rows below); animals and carrier
pigeons have their own pools (the "Shepherds, animals and carrier pigeons" block below).

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
tst.b 8257(A4)     ; the flag plane (bit 7 = the cell's diagonal, graphics.md)
...
D0 = byte[A4]      ; colour byte of the triangle the point lies in (A4 -= 8257 for the second one)
rts               ; Z set  <=>  colour == 0
```

Callers `beq` on **colour 0** = open sea (all four corner altitudes 0) / off-map. Used both as a
"can I stand here" test after a move and, probed in a `dbeq` loop, as a
short-range "is the path ahead clear" test.

### `$164bc` — one step toward (D0, D1)   *[Proven, see the movement-modes block above]*

`dx = D0-D6`, `dy = D1-D7`, `sub.w`; the sign of each picks one of four
quadrants (each folds to magnitudes with `neg.w`). Within a quadrant,
`cmp.w D0,D1 ; bgt` picks the **major** axis (`|dy| > |dx|` → Y). `divu speed`
(`16(A1)`) on the major axis gives `count`; `divu count` on the minor gives its
per-tick increment; a swap-dance rebuilds `D0.w = step_x`, `D1.w = step_y`,
`D2.w = count`. The shared tail (`$16596`) writes `step_x/step_y` (12,13),
`heading` (17, via `$14262`), and **`dwell` (18) := `count >> 1`**;
**`beq` on return ⇔ `count>>1 == 0` ⇔ reached**. `divu #0` (target == current,
or `speed == 0`) traps vector 5 — PM's handler resumes with the operand
unchanged, so the routine still returns a well-formed "reached" rather than
crashing. This is the routine the emulator's DIVU fix unblocked (`README.md`, "Bug 4").

### `$14262` — (dx, dy) → heading 0..255   *[Proven, movement-modes block]*

Octant fold on `sign(dx)/sign(dy)`; `shift = shift_tbl[$14360 + (max(|dx|,|dy|)
>> 5)]` (a `bit_length`-style ramp); `dx >>= shift`, `dy >>= shift` (both now
< 32); `dir_tbl[$14760 + ((dx << 5) + dy)]`; per-quadrant fixup
(`0x80 - d` / `-d` / `d + 0x80`). Returns 0..255 in D0. Written to `17(A1)`; the
sprite blit and `$12d56` read it.

### `$12d56` — rotate (D0, D1) by heading D2   *[Proven, movement-modes block]*

`cos = word[$1400a + 2·h]`, `sin = word[$13f8a + 2·h]` — the **same trig table**
as the renderer's `$fecc` `A3` contract. `x' = ((x·cos − y·sin) << 1) >> 16`,
`y' = ((x·sin + y·cos) << 1) >> 16` (`muls`, 32-bit, `add.l` for the `<<1`,
`swap` for the `>>16` — a Q15 rotate). Turns a heading back into a unit velocity
vector — used by mode `$08` (escort) and the obstacle-avoidance mode `$48`.

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
| `$00` | `$14c92` | – | **idle** (original `out_of_b...`). If `33(A1)==$a` (carrying a Boat) → bit 5 set, become `$8c` (afloat, holding course). Else `$14caa`: set dwell 20, face a direction from `17(A1)` + flags, small fidget |
| `$02` | `$14cfa` | – | **afloat step** (original `in_fleet`): step by (12,13); sample terrain; on hitting an obstacle clear bit5 and drop to mode `$06` *(Proven, movement-modes block; reached from mode `$08`)* |
| `$04`/`$06` | `$14d32` | – | *(Proven, movement-modes block)* step by (12,13); `$1648e`; **land** → `subq.w #1,18(A1)` (`==0` → mode `$08`) → epilogue `$16202`; **water** → carrying a Boat (`33 == $a`): `bset #5` (afloat) + mode `$02`, else mode `$00` + `bra $1622c` (no write-back) |
| `$08` | `$14d7c` | – | *(Proven, movement-modes block; original `lost`)* **orbit the lead `28(A1)`**: `$12d56`-rotate the orbit offset `(20,22)` by the lead's heading, `+` lead position `8/10`, `speed := lead.speed + 4`, `$164bc`; on arrival copy the lead's step `12` + dwell `$a`; then `$1648e` at the new spot → land: mode `$06` + fall into the `$14d32` body / water: mode `$02` (`$14cfa`) or `$00` |
| `$0a` | `$14e1e` | – | dwell `18`; at 0 → mode `$08`, or mode `$10` if no linked entity |
| `$0c` | `$14e56` | 6 | save (D6,D7) → (36,38), load the `farm` path (original `start_fl...`; the `$168ee` table's `farm` entry, cursor `$50..$73`), → mode `$0e` |
| `$0e` | `$14e70` | **445** | *(Proven, movement-modes block)* **the farmer's walk along the `farm` path of the spline table `$168ee`** (original `in_fligh...`; 275 of 281 live men in the mode are farmers over 11 snapshots, so it is not a "patrol"): integrate step + `subq.w #1,18(A1)` (`!=0` → epilogue `$16202`); at 0 snap to origin+segment, read the next point, recompute step `(nextpt−seg)>>3` + heading, dwell 8; segment word ≥ `$7d00` = terminator (`$7d01` loop: `D2 -= D1`; `$7d02+n`: `mode := n`; `$7d00`: `mode := $92`) |
| `$10` | `$14f08` | **180** | *(Proven, movement-modes block; original `home_in`)* **advance to the target** `20/22` (or, `prev_mode == $2e`, chase entity `48(A1)` copying its live position; target gone → mode/prev `:= $2c`). `$164bc` for the step; **reached** → `$15302` (chase) / `$14fdc` (fixed — snap onto target); else probe up to `dwell` cells ahead along (12,13) with `$1648e` (`dbeq`) — blocked → mode `$4a`; else mode `:= $12` + run the `$14ff8` body. `$15302` + the group-state-8 hand-off `$1518a` asserted off |
| `$12` | `$14ff8` | **774** | **the moving leg between `$10` re-plans** (original `on_route`) *(Proven, dwell/upkeep block; the man moves every tick, it is not a halt)*: add the step `(12,13)` to the position, `subq.w #1,18(A1)`; at `<= 0` → mode `$10`. Its prev byte is the job mode that planned the leg (`$58` for the fishermen in the mission-1 snapshots, `$42`/`$44` for 33 of 33 men in `k5_s4`, `py/mode_census.py`; on the Play Random Land roll, 473 men in 20 snapshots: `$20` 122, `$4e` 54, `$16` 41, `$2e` 41, `$50` 30, `$44` 30, then `$1c`, `$18`, `$5e`, `$42`, `$86` and others, so the previous mode is whatever job or order step planned the leg, not a fixed set) |
| `$48` | `$158da` | 13 | **obstacle avoidance**: `12(A1)/13(A1)` from heading via `$12d56`; probe ahead (`dbeq` on `$1648e`); if blocked, add a growing ± sweep (`40(A1)` += 4, negate) to `17(A1)` and retry — turn by ever-wider angles until a lane opens |
| `$4a` | `$1597a` | 3 | set up mode `$48`: copy target from `28(A1)`, sweep = 8, clear low 2 bits of heading |

### Combat

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$28` | `$15264` | – | **wait for recruits** (arrival of order `$08`, via `$1c`): `subq 18(A1)` each tick; at 0 `$35f4` ends the order and makes the camp (group state 6, men ringed round the lead; live: 22 entries in 6M steps on the player's lead) |
| `$2a` | `$15282` | – | **a recruit joins** (the original name is `wait_mee`, strategy.md "Original names"; *proven live*, strategy.md "What each order does": 4 runs, 5 first-tick tests each, `$1b2a`/`$1d70` hits = the quota): on the first tick (dwell `$32`) the man's `46(A1)` names the group lead `A0`; if the lead is alive and its group is in state 3, `46(A0)` (the quota `$15122` set) is decremented, **by every arrival, so refused ones push it negative**, and while it stays non-negative `$1b2a` adds the man to the group (head of the roster, flag bit 6, `28` = the lead), his home lord's `troops_field` (`8(A4,D0)`) drops by one and `$1d70` re-forms the ranks (the man goes mode `$08` → `$06` → `$68`); a refused man runs his 50-tick dwell out (about 200k steps per tick) into `$3c08`, which sends him back to a civilian mode |
| `$2c` | `$152f8` | – | **pick a target** (`jsr $4f68`). `$4f68` dispatches on `38(A1)` unmasked through `$4fa2` (handler = `$4fa2 + word[$4fa2 + 38]`): 0/2/`$18`..`$1e` `$4fc4` hunt a lord (`46` = `$4e514` record): every man of his settlements that can fight, within `$fff`; 4 `$503c` hunt a group (roster of `obj[46]`'s group); 6 `$50b2` one target `obj[46]`; 8 `$50da` follow it (mode `$36`, prev `$66`); `$a` `$5150` shoot it (mode `$34`, `$57f0` type `$28`); `$c` `$519a` walk to its cell (mode `$10`, prev `$3a`); `$e`/`$10` `$51dc` help allies of my lord, else `$5402` sends my lord's idle men home (`$3c08`); `$12`/`$14`/`$16` `$5240` group done: nobody engaged → `$539a` (conquest: `38 == $12` → `$550e`, economy.md §3), else `$3c08`. Each candidate is weighed by `$548a` (Chebyshev distance; stronger weapon or health, or a third retry; the best key stored is D0, not the distance: a game bug that changes 48 of 169 natural picks). No candidate: `38 += $10` (flag bit 6, or bit 4 with a group) else `+= $c` (`$538a`/`$5392`). *Proven: `py/diff_4f68.py`, 1804/1804 over 192 states, 170 natural (`scratchpad/pm124/conquest/`)* |
| `$2e` | `$15302` | – | **reached the target** `48(A1)`: snap `(D6,D7)` onto it, set both mode bytes `$32`; `jsr $56a6` iff `s8(mode(target)) <= $2c` **or** `s8(prev_mode(target)) >= $3c` (signed byte tests; a target in a combat or order mode with an old prev mode below `$3c` is not engaged). *Proven, `py/fsm15/gate_fsm15.py`: 49 states over seven target mode/prev pairs; the engage fired in 6 of 7 for ($10,$10), 7 of 7 for ($68,$68)* |
| `$32` | `$1533c` | – | *(Proven, see the combat block above)* **melee**: `tst.b 5(A3) <= 0` or `30(A3) == $3c` (target dead, or routed: the ROUT roll stamps `prev_mode := $3c`, original `run_away`) → mode/prev `:= $2c`, epilogue `$161c4`. Else face away (`17(A3) := 17(A1) + $80`); if target `31 != $32` → `jsr $56a6`. **Drain health `45(A3)` by `(s8(44(A1)) < 6 ? 44(A1) : 0) >> 1 + 1`** via `sub.b` (the `>= 6` arm is a hard `moveq #0`, *not* `min`). `> 0` → mutual retaliation (`48(A3) := self`, `31(A3) := $32`, `bra $1622c` — no epilogue). `<= 0` → `jsr $5590`, then mode/prev `:= $2c` + `$161c4` |
| `$34` | `$153b2` | – | **shot cool-down** (*counted*: 400 snapshots hold men in it with the dwell high byte 5..20; bytes 30 and 31 both `$34`, `48(A1)` a live man of another side, shooters all byte 7 `$10`): set by `$5150` after its `$57f0` call, which seeds the dwell high byte with `$14` (`move.b 15(A0),18(A1)`); `subi.b #1,18(A1)` per tick (a byte, the low byte 19 is untouched; `watch` over 900k steps: five byte writes `$0f`..`$0b`, one per ~216k steps), then at negative mode/prev `:= $2c`, so 21 ticks |
| `$36` | `$153cc` | – | **chase the entity `48(A1)`** (original `goto_ani`, "go to animal"; 0 men in mode `$36` or `$38` in 400 snapshots and in 20 Play Random Land snapshots, so never seen naturally). Set only by `$5100` in `$50da`, the `38(A1) == 8` arm of the `$4f68` picker (one `move.b #$36,31(A1)` in the whole image, fresh `0..$1d000` listing), when `5(target) > 0`; `38 := 8` comes from `$4dae` with the class `D7 = 8` of a category-8 (animal) record that engages the party, so the natural target is an animal (inferred; no live animal contact seen). Target dead (`5(A3) <= 0`) → `6(A1) := $e`, mode `$68`; else `$164bc` steps toward its position; on contact (the block at `$15428..$1545c` is unreachable) dwell `18 := $a`, mode `$38` (`$1547e`, the slaughter: `subi.w #1,18`), the target's byte 7 `:= $10`; at 0 the target becomes category `$1c` (carcass) with its side byte negated, and the chaser either adds `$b4` food to its home lord and calls `$3c08` (no byte-7 bit 4/6) or adds `$b4` to the group's food and calls `$35f4`. *Poke-driven, 3 of 3* (`k5_s4`, chaser `30/31 = $66 $36`, `48` = a man: target byte 7 -> `$10`, side negated, category `$1c`; the lord's food `+$b2` against the code's `+$b4`, 2 unattributed; the group branch left the lord's food unchanged); `scratchpad/pm137/C_modes/drive36.py` |
| — | `$56a6` | – | *(Proven on the `$574a` path, combat block)* **engage**: if `flags.bit6(target)` and the linked enemy `28(A3)` is within `$fff` (Manhattan-max) → `jsr $5778`; then set both mode bytes `$32`, link attacker into `48(A3)`, and pick `46(A3)` — from `28(A1)` / self (`$5730`, if the attacker has a group) or the attacker's leader-table entry (`$574a`, `38(A3) := 2`) |
| — | `$5778` | – | **contact bookkeeping, not a resolver** — see `strategy.md` "Combat". Marks an engaged garrison `flags = $11`, records the attacker for a support objective, else `$4bc8` (nation peace-break + player notify; Proven, its own block) when group state `!= $d`. |
| — | `$5590` | – | *(Proven on the KILL branches, combat block)* **kill-or-rout roll** (from mode `$32` when `health <= 0`): `45(A3) := 0`; `D0 := $30fe = group.field60 − 2` (attacker in a group with a live lead), else `D0 := 0`. `D0 == 0` → **KILL**; `D0 == 2` → `$560a`; else `($57fec + 24(A1)) & 2` parity → KILL / `$560a`. **KILL**: `neg.b 5(A3)`, `32(A3) := 0`, `category $6 := $c` corpse, `dwell := $a0` (160-tick decay), then the `$5628` tail (`$567e` → `leader.population -= 1`). **`$560a`**: `flags.bit5(target)` set → KILL anyway; else `jsr $3c08` (**ROUT** — restructure the group, `prev_mode := $3c`, unit survives; *asserted off in the combat-block proof*) |
| — | `$30fe` | – | *(Proven, combat block; original `_get_agg...`)* `word[$51538 + 42(A1) + 60] − 2` — the `$5590` roll selector; `2` for the pm73_fight attack group |
| — | `$57f0` | – | **spawn a projectile** into the first free slot (life word 0) of the 49 effect slots `$4be00..$4c110` (16 B each; D2 = 0 when none is free): copy the shooter's position, `life := $14` (20 ticks; a type `$12` gets its flight time + 1), `type := D1`, `shooter := A1-$51b66`, per-axis velocity bytes 4/5 toward the target via `divu #$78`, link it into its cell (`$16808`), and set the shooter's dwell high byte 18 := `$14`, the low byte of the life word just written (there is no per-weapon reload table) |
| — | `$596a` | – | **projectile update loop** (every tick, from `$3e06`; *Proven*, section "Arrows and carrier pigeons" below: `py/gate_proj.py`, 456 states, 4210/4210 bytes): an arrow (type `$28`, the only type anything creates) flies by its velocity bytes for 20 ticks and ends on the first man, pigeon or marker of another side within 15 × 21 units in its cell (a man loses `$52` health, the `$5590` roll when that leaves 0 or less; a pigeon is shot down, `$4624`); the end of its life or a hit unlinks it and ends the shooter's `$34` cool-down. The type-`$12` area effect (stamp categories in the arrow's cell) is unreachable |

The effect slots are 49 records of 16 bytes at `$4be00..$4c110` (the spawn searches
them from `$4bdf0 + $10`; there is no header or template slot):

```c
typedef struct pm_effect {           // $4be00, stride 16, 49 slots
/* 0*/  u16  bucket_next;             // shares the $47970 chain machinery
/* 2*/  u16  bucket_prev;
/* 4*/  s8   vx, vy;                  // per-tick velocity in map units, from $57f0
/* 6*/  u8   type;                    // D1 at spawn: $28 for a bow. $12 = area effect on expiry (never created)
/* 7*/  u8   _pad7;
/* 8*/  s16  world_x;                 // copied from the shooter at spawn
/*10*/  s16  world_y;
/*12*/  u16  shooter_off;             // offset into $51b66 of the firing unit
/*14*/  s16  life;                    // $14 at spawn (the low byte, 15, is what $57f0 copies into the shooter's dwell); --/tick in $596a; 0 = free; 1 -> impact; -4..-1 = a spent area effect counting up
} pm_effect;
```

### Group-order arrivals, merchants and fishermen

The first rows read/write the **group table `$51538`** (indexed by `42(A1)`, so `A3 = $51538 + 42(A1)`; group
field `0(A3)` = the state enum, seen values 3 / 8 / `$c` (the game's own names: 3 Get Men, 8 Attack, 12 Supply;
strategy.md "The game's own text"); `-12(A3)` links the group's lead object record, `24(A3)` the target (a lord,
settlement or object); `36(A3)` is the army's food, the captain panel's "Food" line). The rest of the table is
the merchant (`$4e`..`$54`) and fisherman (`$56`..`$62`) job cycles, which have no group.

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$18` | `$150b0` | 6 | → mode `$0c` (begin the field path). Original `at_farme...`: a farmer who reached his field cell (`42/43`); `prevmode $18` on every mode-`$0e` record (the villagers' farm cycle, not a garrison) |
| `$1a` | `$150c0` | – | **take food from a town** (arrival mode of order `$06`, and of the `$1a` supply line): A5 = the target lord (`$51b66 + 24(A3)`, set by `$3154`); `loyalty_pressure 14(A5) += 16 >> $30fe`; `slice = food 6(A5) >> $30fe` moves into the army's food `36(A3)`; group state `$c` → mode `$26` (back to the supply-line cell), else `$35f4`. Live: 22 → 11, army +11 vs control, `scratchpad/pm124/o06` |
| `$1c` | `$15122` | – | arrival of order `$08` (**get men**): the quota `46(A1) = lord.troops_field(8(A5)) >> shift` (aggressive all, neutral half, passive a quarter); `$34f2` sends every able man of the town's house chain to the cell (`20/22 := the lord's cell`, `31 := $10`, `30 := $14`, `46 :=` the lead offset when the group is in state 3: callcap on lord 0's town sends 4 men); the lead → mode `$28`, dwell `$32` |
| `$1e` | `$1515c` | – | arrival mode of order `$02` (go to): `$35f4`, the group camps there |
| `$26` | `$15200` | – | if group state == `$c`, unpack `36(A1)` as a target cell → mode `$10` (march there), prevmode `$74` (the `$1a` supply line's return leg) |
| `$22` | `$151a8` | – | arrival of order `$0e`: `$5fa0` hands the lord's work order (`$5cde`) to every man of the group, then mode `$92`. `$5cde` refuses a lord without a WorkShop (building kind 7), so the player's single mission-1 building (a Tower, kind 11) refuses it |
| `$6e` | `$15740` | – | arrival of order `$10`: `$61f8`, take `goods >> $30fe` from the town lord and equip the men (economy.md §2c) |
| `$72` | `$1605a` | – | arrival of order `$06` on a cell with no friendly town: pick up the food of a `$2c` pile there into `36(A3)`, free the pile when empty |
| `$74` | `$160d6` | – | the `$1a` supply line (`$3956`): drop food at the cell (`$39d4` D7=1), find the own lord with the most food (`$3bc8`, field `+6`), march there with arrival `$1a` |
| `$78` | `$15772` | – | arrival of order `$1c`: `$63f4` trade (strategy.md "The player's commands"), then mode `$92` |
| `$7a` | `$1578c` | – | arrival of order `$20` (spy): `$3da4` links the lone captain into the target settlement's unit chain, takes its owner's side, `bset #7`, mode `$7e`; the lord's `troops_field += 1` |
| `$4e` | `$15a0e` | – | **merchant arrives at the home lord** (original `merch_ar...`; `init_mer` starts every merchant here, economy.md §5a): deposits the carried good at the home lord (`$159a4`), dwell `$32`, then mode `$54`; also one of the three same-gated entries into the `$7c` park (`$15a46`, economy.md §3a) |
| `$50` | `$15a60` | – | **merchant arrives at the far lord** (original `merch_st...`): after the `$10` leg with previous mode `$50`, deposits into lord `46(A1)`, then mode `$52` |
| `$52` | `$15a80` | 51 | **merchant, wait at the far lord** (after `$50`'s deposit into lord `46(A1)`, a 50-tick dwell; 404 of 404 men in `$52/$50` have `46 ==` the home lord offset, and 165 of 165 plus 9 of 9 in `$50/$50` on the Play Random Land roll; the `$54/$4e` returners hold it for 104 of 120, `py/merch_census.py`): at `< 0` target := the home settlement's cell `12($4f916+34)`, prev := `$4e`, mode `$10`, and `$159de` picks up one good from the lord at `46(A1)`; arrival `$4e` deposits it at the home lord. There is no order message |
| `$54` | `$15ad2` | 29 | **merchant, start of a trip** (after `$4e`'s deposit, dwell `$32`; one merchant followed live through four identical 16M-step cycles `$4e` → `$54` → `$10` (prev `$50`) → `$50` → `$52` → `$10` (prev `$4e`) → `$4e`; `$54/$4e` 639 and `$52/$50` 404 of 1156 men in `$4e..$54`, all job 2): at dwell `< 0` choose a lord by walking `14(A1) & 7` steps along the leader table, target := his cell, prev := `$50`, mode `$10`, `$159de` picks up one good. *Proven, `py/fsm15/gate_fsm15.py` (119 states of mode `$54`, 884 tracked bytes): the walk register A3 never advances (`lea 32(A3),A0` at `$15b0c` loads A0, and the loop tests A3) except that A3 wraps to leader 0 when the home lord is the last record, so `46(A1)` is the home lord; and `$159de` at `$15b54` runs with that stale A0, i.e. the record after A3 (`A3 + 32`) whenever `14(A1) & 7 >= 2` (A3 itself for 0 and 1): 48 of 48 states with goods only on the next record took the good from it. A game defect: `$159de` at `$15abe` (mode `$52`) reloads A0 from `46(A1)`, this one does not*. The earlier "speech generation" label is wrong |
| `$5e` | `$15b5e` | – | **fisherman arrives** (original `fish_arr...`; `init_fis` starts every fisherman here and `$3c08`'s flag-bit-2 case sends a man home to it): the other `$7c` park entry (`$15b7a`, economy.md §3a); the `$15000`-page gate covers it (11 states) |
| `$56` | `$15b94` | **168** | **fisherman: go to the fishing cell** (every man seen in modes `$56`..`$62` is job 4, fisher: 93 of 93 over seven states, `py/job_census.py`; original labels `fish_*`): unpack `42(A1)` → target (20/21/22), read the altitude `$3f86c[42]` (and its `+1`/`+64` neighbours) to choose sprite `$70` (open sea) / `$90` (land adjacent), prevmode `$58`, mode → `$10` |
| `$58` | `$15bec` | 11 | fisherman: arrived at the cell — settle |
| `$5a` | `$15c46` | **119** | fisherman: **look for the catch** (not a "proximity gate"): dwell; scan the cell bucket `$47970[42]` for a neighbour of category `$18` (flags `$10`) or `$20`; found → mode `$62`; timeout → mode `$62`, dwell `$64` |
| `$5c` | `$15d66` | **152** | fisherman: **head home**: move; `$15fa8` clamps (D6,D7) to the map and tests the four altitude-plane bytes of the cell for collision (original `check_co...`, see the `$15000`-page block); on arrival set up target from the altitude `$3f86c[42]` / `$4f916`, mode → `$60` |
| `$60` | `$15ddc` | 86 | fisherman: **deliver the catch**: move to (20,22); on `$164bc` arrival `addi.w #$4,6($4e514+idx)` (`+6` is the lord's food store, economy.md §1: **+4 food per trip**), mode → `$62` |
| `$62` | `$15bfc` | 3 | fisherman: idle between trips (original `fish_get`) |

### Static / upkeep / boats / effects

| mode | handler | tick | behaviour |
|------|---------|-----:|-----------|
| `$68` | `$16048` | **2559** | **resting in camp** (original `rest_in_...`; 118 of 123 live `$68` men are byte6 14, the sitting category; marching men are `$06`/`$08`, not `$68`; the camp is made by `$35f4`, read from the code) *(Proven, dwell/upkeep block)*: `jsr $5c80` (upkeep), zero velocity + heading, next. The dominant mode: the bulk of an army sits in it, and the handler never moves the man (the camp positions are set by `$35f4` and the rank former `$1d70`) |
| `$8a` | `$161b2` | 99 | **captain resting at his town** (original `captain_...`; not a garrison: job 9, 29 of 29 men in it; byte 7 `== $10` in 660 of 661 men in the mode over 400 snapshots and 41 of 41 in 20 Play Random Land snapshots, `py/census_8a.py`; `$5c80` is the per-job health regeneration toward the `$5ccc` cap, 95 for bit 4) *(Proven, dwell/upkeep block)*: `jsr $5c80` only |
| `$8c` | `$14c48` | – | afloat with a Boat (flag bit 5): re-add the last step, re-test terrain, drop to `$10`/`$06` if pushed off |
| `$80` | `$15f80` | 5 | **shepherd at his town** (original `shep_arr...`; job 8; *Proven*, section "Shepherds, animals and carrier pigeons"): `jsr $16848` (owner reconcile and upkeep), dwell := `$32`, mode `$84` |
| `$84` | `$15f96` | 76 | shepherd waits: dwell − 1; at 0 mode `$86` *(Proven)* |
| `$86` | `$15e30` | 20 | **shepherd rounds up the herd** (original `shep_fin...`): the first free (`$11`) animal of his chain (word 42, then each animal's word 16) becomes the target, at the midpoint between man and animal; walking there is mode `$10` with previous mode `$86`; on arrival the animal becomes herded (`$12`, both velocity bytes `|= $40`). No free animal left (or no chain): mode `$88` *(Proven)* |
| `$88` | `$15eb0` | – | **shepherd goes home** (original `shep_go_...`): target the cell just south of his town (`+$100` in y), previous mode `$82`, mode `$10` *(Proven)* |
| `$82` | `$15eee` | 1 | **shepherd at the gate** (original `shep_go_...`): target the town cell, previous mode `$80`, mode `$10`; releases the herd: every `$12` animal of the chain becomes `$11` again with a fresh speed (`rng & 7 + 2`) and heading and the velocity of `(0, -speed)` rotated by it *(Proven)* |
| `$14` | `$1501a` | – | **arrive at the meeting** (original `at_meeti...`; arrival mode of the order-`$08` recruits `$34f2` sends, 5 hits live): copy the settlement's owner byte `5(A3)` (record `$4f916+34`) into the man's owner byte `5(A1)` unless its bit7 is set, mode `$2a`, dwell `$32` |
| `$16` | `$15042` | 6 | **a farmer home from his field** (original `at_farme...`; not a "disband"): `jsr $16848`; then **iff `$57fd0 == 0`** (winter): save mode → 30, mode `$7c`, dwell `-99` (park as a settlement heartbeat marker): the dwell-park write, Proven live (economy.md §3a: 0 of 28 natural entries parked with `$57fd0` non-zero; poking it to 0 made the next entry park). **Else** (`$57fd0 != 0`): `owner_leader.food += 2` (`+= 2` again if `33(A1) == 8`, a Plough), then mode `$10` prev `$18` (walk to the field cell, bytes `42/43`). `$57fd0` rotates {0,2,4,6} (economy.md §3a), so mission 1 takes both branches over time (economy.md §1's first pseudocode had this branch inverted). Entered at the end of the farmer cycle (`$0e` → `$24` walk home → `$16`, strategy.md "Original names") and by `$3c08`'s flag-bit-0 case; bit 0 of byte 7 is the farmer flag, set at build by `init_far` (`$2cd0` inside `$2c5a`, economy.md §5a), not by any player action |
| `$7e` | `$157e6` | – | **idle at home** (original `stay_at_...`; 23 live men, all soldiers): the winter-pulse body, like `$7c` but with no `$57fd0` gate. A man dismissed home or a spy (`$3da4`) sits here, so each pulses his lord's loyalty check (economy.md §3; the spy run revolted lord 0) — but arrives with whatever stale `dwell` the record already had, never freshly parked at `$ff9d`, so the `D5 == $ff9c` "just parked" edge cannot fire for it (economy.md §3a; traced live for one starvation deserter, entity `$52462`) |
| `$7c` | `$157ba`→`$157e6` | – | **winter state of a parked civilian: the "settlement heartbeat"** (original `in_winte...`; the live men in it are jobs 1, 2 and 4, 19 over 11 snapshots: the pulse belongs to each parked man, so `$163b8`'s upkeep, original `_eat_tow...`, is one food per man per pulse, not per settlement) *(Proven, heartbeat block)* — runs when `$57fd0 == 0`; `$57fd0` rotates {0,2,4,6} via `$1abaa` (1 per 118.4M steps) so mission 1 sees it in intermittent bursts. `dwell--` (`>0` → next); `jsr $16848`; `jsr $5c80` (×2); reload `dwell := $580a6[side·$20].word0`; **`jsr $163b8`** (`owner_leader.food -= 1`, floored); construction progress (building kind `$a`, a Ruin → `16(settl)++`, at `$78` → kind `:= dest_cell % 10`, `== 7` → a WorkShop, `settl.category := $10`); loyalty accumulator (`field·4` vs `food`, `±` only on the first post-park tick where `D5 == $ff9c`); `>= 600` → `$550e` revolt; epilogue `$161c4`. `$5cde` / `$550e` / `$5c2c` asserted off. `$57fd0 != 0` at `$157ba` → `jsr $16892` (goods-driven regroup) then `jsr $3c08` (flag-driven regroup) — ***Proven*** (regroup block: 71/71 over 22 states); its **flag-bit-4 group-teardown** sub-path (`$37c2` → `$1d70`/`$1b8c`, `$17a46`) — ***Proven*** (teardown block: 1847/1847 over 13 states) |
| `$4c` | `$16176` | – | **captain back at his town** (original `captain_...`; the handler stores `$8a` in both mode bytes): adjust the owning commander's troop count (`$5c2c` → `$4bc8` when the settlement's owner no longer matches; Proven end-to-end, see the `$4bc8` block), end the group's order and make its camp (`$35f4`), `$5c80`, zero velocity, mode `$8a` |
| — | `$16848` | – | *(Proven, heartbeat block)* **side ↔ owner reconcile**: `A3 = $4f916 + 34(A1)`; `settlement.owner == marker.side` → skip; else `btst #7` clear + `btst #4` clear → `5(A1) := owner` (adopt), `btst #4` set → `jsr $5c2c`. Then `24(A1) != 0 && == 0(A1)` → `$57ff4 := 24(A1)`. Tail `jsr $5c80`. Also called from the mode-`$16` prologue |
| — | `$5c80` | 2600+ | **per-entity upkeep**: job-indexed cap table `$5ccc` + byte14 age + byte45 health; `byte45 += ($57fec & 1)` while below the cap (recovery with a 1-bit random term; 203 of 225 live persons sit on their cap, `py/health_check.py`); past age `$3c` the cap falls by 4 per unit and `jsr $5bd2` removes the man when it reaches 0 |

Modes with no row here (`$20`, `$24`, `$30`, `$38`, `$3a`, `$3c`, `$3e`..`$46`, `$64`..`$66`, `$6a`..`$72`, `$76`..`$7a`, `$8e`, `$90`
and the other sparse entries) are modelled, with their handler addresses, in the `$15000`-page block (the last
Proven section below); the gatherer modes `$3e`..`$46` and `$6a` are in economy.md §2a. Indices > `$94` alias into
following code and are never selected.

The full table (`$14bb4`, `handler = $14bb4 + (s16)word[$14bb4 + mode]`) was
dumped from RAM; every valid entry `$00`..`$94` resolves inside the handler
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
    state "8C afloat with a Boat" as S8C
    state "0A pre-move dwell" as S0A
    state "08 orbit / rejoin the linked lead" as S08
    state "06 walk until blocked" as S06
    state "02 step until blocked (afloat)" as S02
    state "0C load the farm path" as S0C
    state "0E farmer walk along the spline" as S0E
    state "24 farmer walks home" as S24
    state "10 advance to the target" as S10
    state "12 the moving leg between re-plans" as S12
    state "48 obstacle-avoidance sweep" as S48
    state "4A set up the sweep" as S4A
    state "2E reached the target" as S2E
    state "32 melee" as S32
    state "2C pick a target" as S2C
    state "34 shot cool-down" as S34
    state "36 chase an animal" as S36
    state "28 get men: wait for recruits" as S28
    state "68 resting in camp" as S68
    state "8A captain resting at his town" as S8A
    state "18 farmer at his field: begin path" as S18
    state "1A group: take food from a town" as S1A
    state "1C group: get men, summon the town" as S1C
    state "26 group: unpack dest -> march" as S26
    state "56 fisher: go to the fishing cell" as S56
    state "58 fisher: settle" as S58
    state "5A fisher: look for the catch" as S5A
    state "5C fisher: head home" as S5C
    state "60 fisher: deliver, food += 4" as S60
    state "62 fisher: idle between trips" as S62
    state "92 do nothing (zero velocity)" as S92
    state "$15302 reached (routine)" as S15302
    state "$1518a $4bc8 reconcile" as S18A
    state "$5590 kill / rout" as S5590
    state "$35f4 make camp (group state 6)" as S35F4

    S00 --> S8C : carried == 0A (Boat)
    S00 --> S0A : else (face + fidget, dwell 20)
    S8C --> S10 : pushed off terrain
    S8C --> S06 : pushed, blocked
    S0A --> S08 : dwell 0 && link_related != 0
    S0A --> S10 : dwell 0 && no link
    S08 --> S06 : arrived at linked entity
    S02 --> S06 : hit obstacle
    S06 --> S00 : water, carried != 0A (no write-back)
    S06 --> S02 : water, carried == 0A (afloat)
    S06 --> S08 : land, dwell 0 (rejoin the lead)
    S0C --> S0E : always (saves origin, loads path)
    S0E --> S0E : segment end word == $7D01 (loop)
    S0E --> S24 : segment end word == $7D26 (mode := n = $24)
    S0E --> S92 : segment end word == $7D00 (end)
    S0E --> S0E : dwell > 0 (integrate step)
    S10 --> S15302 : $164bc says target reached (chase)
    S10 --> S4A : terrain probe blocked ahead
    S10 --> S12 : path ahead clear (mode := $12)
    S10 --> S18A : group state 8 && dwell <= $12 (hand to $1518a)
    S12 --> S10 : dwell expired
    S4A --> S48 : copies target, sweep = 8
    S48 --> S48 : still blocked -> widen sweep angle
    S48 --> S4A : sweep exhausted one way
    S48 --> S12 : gave up (D2 < 0)
    S2E --> S32 : snap to target; engageable -> $56a6
    S32 --> S32 : target alive & not routed; drain 45(A3); health > 0 -> target retaliates (mutual $32)
    S32 --> S2C : target dead (5(A3)<=0) or routed (30(A3)==$3c)
    S32 --> S5590 : drained target health <= 0 (kill-or-rout roll)
    S5590 --> S2C : after the roll, self -> mode $2c
    S2C --> S34 : picker shoots (via $5150 / $57f0)
    S34 --> S2C : cool-down over (dwell byte < 0)
    S2C --> S36 : picker follows an animal (via $50da)
    S36 --> S68 : target dead (6(A1) := $e)
    S28 --> S35F4 : dwell 0 (order slot freed)
    S18 --> S0C : always (40 := $50)
    S1A --> S26 : group state == $C, dwell $23
    S1A --> S35F4 : group state != $C (free slot)
    S1C --> S28 : always (quota := lord troops >> roll, dwell $32)
    S26 --> S10 : group state $C -> unpack origin as dest cell
    S56 --> S10 : always, prev_mode := $58, target := the fishing cell
    S58 --> S5A : dwell $A
    S5A --> S62 : neighbour of category $18/$20 found, or timeout
    S5C --> S60 : $164bc arrival at settlement
    S60 --> S62 : arrival; leader.food += 4
    S62 --> S62 : dwell > 0
    S68 --> S68 : always (upkeep only; handler never moves the man)
    S8A --> S8A : always (upkeep only)
```

`$92` is the do-nothing mode (handler `$161bc`, original `do_nothi...`; code read of the table word and the body:
`clr.w 12(A1)` / `clr.b 17(A1)`, then the epilogue `$161c4`, and the mode byte is not rewritten): the farm path's
`$7d00` terminator and the arrival handlers `$22` and `$78` leave a man in it. (Do not confuse it with `$1615c`, which lies inside the
equipment-exchange tail `$160f8`, or with the `$35f4` call at `$16190..$1619e`, which belongs to mode `$4c`, `$16176`.) `$1518a` is `$4bc8` (contact reconcile) then epilogue.
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
    if (A1->carried == 0x0a) {                     // carrying a Boat
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

// ---- $14e70  mode $0E : the farmer's walk along the spline $168ee -----------
void h_farm_walk(pm_object *A1) {
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
    A1->mode = 0x92;                                // $7d00 : end -> mode $92 (do nothing)
    goto epilogue_161c4;
}

// ---- $14f08  mode $10 : advance to the target ----------------------------
void h_advance(pm_object *A1) {
    if (A1->prev_mode == 0x2e) {                    // chasing a live entity, not a fixed cell
        pm_object *e = &obj[A1->link_target];
        if (e->owner <= 0 || e->prev_mode == 0x3c) {// target gone / already routed
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
    if (A1->carried != 0x0a) {
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
    A1->mode = 0x12;                                // -> the moving leg (original on_route)
    goto tail_of_$14ff8;
  arrived_$14fdc:
    A1->mode = A1->prev_mode;                       // resume the previous state
    D6 = A1->target_x;  D7 = A1->target_y;          // snap exactly onto it
    goto (A1->flags & BIT5 ? epilogue_16202 : epilogue_161c4);
}

// ---- $14ff8  mode $12 : the moving leg between $10 re-plans ----------------
void h_on_route(pm_object *A1) {
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (--A1->dwell > 0) goto epilogue_161c4;
    A1->mode = 0x10;                                // re-plan: advance again
    goto epilogue_161c4;
}

// ---- $14d32  mode $06 : walk until blocked ------------------------------
void h_walk(pm_object *A1) {                        // Proven, movement-modes block
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (terrain_ok($1648e, D6, D7)) {               // land
        if (--A1->dwell == 0) A1->mode = 0x08;      // ($14d6a / $14d20)
        goto epilogue_16202;
    }
    if (A1->carried == 0x0a) {                      // water, carrying a Boat
        A1->flags |= BIT5;  A1->mode = 0x02;
        if (--A1->dwell == 0) A1->mode = 0x08;
        goto epilogue_16202;
    }
    A1->mode = 0x00;  goto next_record;             // water -> idle, no write-back
}

// ---- $14d7c  mode $08 : escort / orbit the lead ------------------------
void h_escort(pm_object *A1) {                      // Proven, movement-modes block
    pm_object *L = &obj[A1->link_related];          // 28(A1)
    s16 x = A1->target_x, y = A1->target_y;         // orbit offset (20,22)
    jsr_12d56(&x, &y, L->heading);                  // rotate by the lead's heading
    x += L->world_x;  y += L->world_y;              // desired point
    A1->speed = L->speed + 4;
    if (jsr_164bc(A1, x, y) == REACHED) {           // recompute + snap on arrival
        s16 ox = A1->target_x, oy = A1->target_y;
        A1->heading = L->heading;
        jsr_12d56(&ox, &oy, L->heading);
        D6 = ox + L->world_x;  D7 = oy + L->world_y;
        A1->step_x = L->step_x;  A1->step_y = L->step_y;   // move.w 12(A4),12(A1)
        A1->dwell = 0x0a;
    }
    if (terrain_ok($1648e, D6, D7)) {               // land
        A1->mode = 0x06;  A1->flags &= ~BIT5;
        h_walk(A1);  return;                        // bra $14d32 : run the $06 body
    }
    if (A1->carried == 0x0a) {                      // water
        A1->mode = 0x02;  A1->flags |= BIT5;  h_step_02(A1);  return;  // bra $14cfa
    }
    A1->mode = 0x00;  goto next_record;
}

// ---- $150c0  mode $1A : the army takes food from a town -------------------
void h_take_food(pm_object *A1) {
    (*(u16*)0x12a24)++;                             // a UI/stat counter
    group *g   = &group[A1->group_off];
    pm_leader *L = (pm_leader *)&obj[g->target_24]; // $3154 stored the target LORD as a $51b66-relative offset
    int roll = jsr_30fe(A1);                        // = posture - 2  (a shift amount)
    L->loyalty_pressure += (0x10 >> roll);          // taking food angers the town
    u16 slice = L->food >> roll;
    L->food  -= slice;
    g->food_36 += slice;                            // the captain panel's "Food:" line
    jsr_34f2();                                     // recompute derived group totals
    if (g->exec_state == 0x0c) { A1->mode = 0x26; A1->dwell = 0x23; }
    else jsr_35f4();                                // group order done -> make the camp
    goto epilogue_161c4;
}

// ---- $15122  mode $1C : arrival of order $08, get men ---------------------
void h_get_men(pm_object *A1) {                      // A5 = the target lord ($3154 stored it in group[+24])
    group *g   = &group[A1->group_off];
    int roll = jsr_30fe(A1);                         // posture - 2
    A1->recruit_quota = lord_of(g)->troops_8 >> roll;   // 46(A1)
    jsr_34f2();                                      // send the town's men to the lord's cell (31 := $10, 30 := $14)
    A1->mode  = 0x28;                                // wait
    A1->dwell = 0x32;
    goto epilogue_161c4;
}

// ---- $15264  mode $28 : wait for the recruits ---------------------------
void h_wait_men(pm_object *A1) {
    if (--A1->dwell != 0) goto next_tick;            // $161bc
    jsr_35f4(&group[A1->group_off]);                 // order done -> camp
    goto epilogue_161c4;
}

// ---- $15282  mode $2A : one recruit joins (proven live, see the $2a row) ----
void h_recruit_joins(pm_object *A1) {                // A1 is the townsman; 46(A1) = the group lead
    if (A1->dwell == 0x32 && A1->link_46 != 0) {
        pm_object *lead = &obj[A1->link_46];
        if (lead->owner <= 0 || group[lead->group_off].exec_state != 3) goto restructure;   // $152ee
        if (--lead->recruit_quota >= 0 && jsr_1b2a(A1)) {                                   // add the man to the group
            home_lord(A1)->troops_8 -= 1;
            jsr_1d70(A1);                            // re-form the ranks
            goto epilogue_161c4;
        }
    }
    if (--A1->dwell > 0) goto epilogue_161c4;
restructure:
    jsr_3c08(&group[A1->group_off]);
    goto epilogue_161c4;
}

// ---- $1533c  mode $32 : melee ------------------------------- Proven, combat block
void h_melee(pm_object *A1) {
    pm_object *T = &obj_at_off(A1->link_target);         // A3 = $51b66 + 48(A1)
    if (T->owner <= 0 || T->prev_mode == 0x3c) {       // dead / routed
        A1->mode = A1->prev_mode = 0x2c;
        goto epilogue_161c4;                             // $153a2
    }
    T->heading = A1->heading + 0x80;                     // face the target away
    if (T->mode != 0x32) jsr_56a6(A1, T);               // enrol it into melee

    u8 d = (s8)A1->field44 < 6 ? A1->field44 : 0;        // NB: hard 0, not min(,6)
    d = (u8)(d >> 1) + 1;                                // 1..64
    if ((s8)(T->health -= d) <= 0) {                     // sub.b ; ble
        jsr_5590(A1, T);                                 // kill / rout roll
        A1->mode = A1->prev_mode = 0x2c;
        goto epilogue_161c4;                             // falls into $153a2
    }
    T->link_target = off(A1);  T->mode = 0x32;           // mutual: target retaliates
    goto next_record;                                    // $1622c -- no epilogue
}

// ---- $56a6  engage bookkeeping ------------------------ Proven ($574a), combat block
void jsr_56a6(pm_object *A1 /*attacker*/, pm_object *T /*target*/) {
    if ((T->flags & BIT6) && T->group_lead_off) {
        pm_object *L = &obj_at_off(T->group_lead_off);
        if (manhattan_max(L, T) < 0xfff) jsr_5778(A1, L);
    }
    if (T->flags & BIT4) jsr_5778(A1, T);
    T->mode = T->prev_mode = 0x32;
    T->link_target = off(A1);
    if ((A1->flags & BIT6) || ((A1->flags & BIT4) && A1->group_off)) {   // $5730
        T->field46 = A1->group_lead_off ? A1->group_lead_off : off(A1);
        T->field38 = 4;
    } else {                                                             // $574a
        leader *L = &leader[roster[A1->roster_off].leader_byte_off];
        T->field46 = (u16)((u8*)L - (u8*)obj);   T->field38 = 2;
    }
}

// ---- $5590  kill / rout roll ------------------- Proven (KILL paths), combat block
void jsr_5590(pm_object *A1 /*attacker*/, pm_object *T /*loser*/) {
    T->health = 0;
    int sel = 0;
    pm_object *A4 = A1->group_off ? &obj_at_off(A1->group_lead_off) : A1;
    if (((A1->flags & BIT4) && A1->group_off) || ((A1->flags & BIT6) && !(A1->flags & BIT4)))
        if (A4->owner > 0) sel = call_30fe(A4);          // group[42].field60 - 2
    bool kill;
    if      (sel == 0) kill = true;                      // -> $55f2
    else if (sel == 2) kill = false;                     // -> $560a
    else               kill = (($57fec + A1->anim_phase) & 2) != 0;  // parity
    if (!kill) {                                         // $560a
        if (T->flags & BIT5) kill = true;               // forced KILL
        else { jsr_3c08(T); /* ROUT: unit survives, group restructured */
               T->prev_mode = 0x3c; T->cat6 = 0; goto tail; }
    }
    T->owner = -T->owner;  T->field32 = 0;               // KILL
    T->cat6  = 0x0c;       T->dwell   = 0xa0;            // corpse, 160-tick decay
tail:                                                    // $5628 -- flag-routed cleanup
    // owner <= 0 && BIT7|BIT4 set && group -> $2776 ; BIT6 && group_lead -> $1b8c ;
    // else (the common case) -> $567e :
    leader[roster[T->roster_off].leader_byte_off].population -= 1;
}

// ---- $16048  mode $68 : resting in camp (original rest_in_...) ---------
void h_camp_rest(pm_object *A1) {
    jsr_5c80(A1);                                    // upkeep only
    A1->step_x = 0;  A1->heading = 0;                // never moves itself
    goto next_record;                               // the camp position was set by $35f4 / $1d70
}

// ---- $161b2  mode $8A : captain resting at his town ---------------------
void h_captain_rest(pm_object *A1) { jsr_5c80(A1); goto next_record; }

// ---- $15b94  mode $56 : fisherman -- unpack the fishing cell ----------
void h_fisher_go(pm_object *A1) {
    if (--A1->dwell >= 0) goto epilogue_161c4;
    A1->target_x_lo = A1->group_off & 0x3f;          // {x:6} of the packed fishing cell (42(A1))
    A1->b21 = 0x70;                                  // sprite tag (0x70 / 0x90 by the cell's altitude)
    u8 *alt = &alts[A1->group_off];                  // altitude plane, $3f86c
    if (alt[1] || alt[65]) A1->b21 = 0x90;           // a neighbour is above sea level
    A1->target_y = ((A1->group_off & 0x1fc0) << 2) + 0x80;   // {y:7} -> world_y centre
    A1->prev_mode = 0x58;
    A1->mode      = 0x10;                            // march to the cell
    goto epilogue_161c4;
}

// ---- $15c46  mode $5A : fisherman -- look for the catch --------------
void h_fisher_scan(pm_object *A1) {
    if (--A1->dwell >= 0) goto next_record;
    for (pm_object *p = bucket_head($47970, A1->group_off); p; p = &obj[p->bucket_next]) {
        if (p->category == 0x18 && (p->flags == 0x10)) goto found;
        if (p->category == 0x20) goto found;
    }
    A1->dwell = 0x64;  A1->mode = 0x62;  goto next_record;   // timeout -> idle
  found:
    p->category = 0x20;                              // claim it
    A1->flags |= BIT5;
    // then a $12c9a-driven random nudge of (D6,D7) by $20, $15fa8 collision test ...
    ...
}

// ---- $15d66 / $15ddc  mode $5C -> $60 : fisherman heads home & delivers
void h_fisher_home(pm_object *A1) {                 // $15d66
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (cell_collision($15fa8) == 0 && --A1->dwell >= 0) goto epilogue_16202;
    A1->mode = 0x60;
    // re-derive target from the packed cell + $3f86c altitude (same as $56):
    A1->target_x_lo = A1->group_off & 0x3f;
    A1->b21 = (alts[A1->group_off + 1] || alts[A1->group_off + 65]) ? 0x90 : 0x70;
    A1->target_y = ((A1->group_off & 0x1fc0) << 2) + 0x80;
    jsr_164bc(A1, A1->target_x, A1->target_y);
    goto epilogue_16202;
}
void h_fisher_deliver(pm_object *A1) {              // $15ddc  mode $60
    D6 += (s8)A1->step_x;  D7 += (s8)A1->step_y;
    if (--A1->dwell >= 0) goto epilogue_16202;
    if (jsr_164bc(A1, A1->target_x, A1->target_y) != REACHED) goto epilogue_16202;
    nation *n = &nation[A1->nation_off];
    leader[n->leader_off].field6 += 4;               // the catch: +4 food
    A1->mode = 0x62;
    D6 = A1->target_x;  D7 = A1->target_y;
    goto epilogue_16202;
}
```

## Where target selection happens, and what it reads

There is **no global "pick the best target" pass**. Targeting is local and
event-driven, in three places:

1. **Group order → destination cell.** When a lord (or the player) orders an army to move, the group
   record `$51538` takes the order's state (the game's own names: 8 Attack, 5 Going To, 2 Get Food, 3 Get Men, 12 Supply;
   strategy.md "The game's own text") and the destination is handed to the lead as a packed cell: through the order
   executor `$6a3a` → `$4b80` for a march, or into the lead man's `36(A1)` for the supply line's return leg
   (mode `$26`). The lead unpacks it and marches in mode `$10`. Two other reads of a packed cell are not group
   orders: mode `$52`'s read of the settlement record's `12($4f916+34)` is a merchant's walk home to the settlement's
   cell (see the `$52` row), and the fisherman's trip (`$56`) is his own. Which cell the lord chooses is decided by
   the higher-level strategy code reached from `$13040`'s `jsr $6522` / `$d322` / `$3e06`, which runs every
   tick and owns the `$51538` / `$4f916` tables; it is decoded in `strategy.md`, not here.

2. **Contact → engage.** While marching, mode `$10` probes `$1648e` a few cells
   ahead; the fisher modes (`$5a`, `$5c`) and the notify scan (`$16260`) walk
   the current cell's `$47970` bucket. A neighbour of an enemy category within
   range flips the record to mode `$32` and calls `$56a6`, which re-checks the
   linked enemy `28(A3)` is within `$fff` world units before `$5778` records the contact
   (the casualties come from the melee grind of `$1533c`, strategy.md "Combat"). So "attack" is decided by
   **bucket proximity at ~2.4 Hz**, using the Manhattan-max distance, not by any threat evaluation.

3. **Own settlement → recruits.** Order `$08` (modes `$1c`, `$28`, `$2a`, above) summons a town's men to the lead
   and moves them into the group, counting the lord's `troops_field` down; it never targets another side. Ownership
   is reconciled by `$5c2c` (the revolt chain block below): it compares the
   settlement's stored owner (`$4e514[14($4f916+34)]`) against the entity's
   `5(A1)` and calls `$4bc8` on a mismatch (or defects a man who leads no group).

Inputs read by the loop, in order of how often:

| table | base | stride | holds |
|-------|------|--------|-------|
| object records | `$51b66` | 50 | the entities (above) |
| spatial buckets | `$47970` | 2 | per-cell linked-list heads (broad phase) |
| terrain | `$438ee` | — | four 8 KB planes: altitude `-16514` (`$3f86c`), colour B `-8257`, colour A `0`, flags `+8257` (graphics.md) |
| building (settlement) | `$4f916` | 18 | `+5` owner colour, `+6` render category, `+7` building kind, `+8` chain to the lord's next settlement, `+10` first unit (the unit chain runs through `24(unit)`), `+12` destination cell, `+14` byte offset of the lord in `$4e514` (economy.md §3) |
| group records | `$51538` | `$13c` per side | 5 side records of six-word arrays, one word per captain's group (group field `x` at `$4c + x + 2k`): `0` state enum, `-12` lead object link, `24` target link, `36` the army's food (strategy.md "`$51538`") |
| altitude plane (`_alts`) | `$3f86c` | 1 | terrain height per map cell, 64 x 128; the renderer projects it (`py/alts_render_check.py`) |
| leader / message | `$4e514` | 32 | per-lord food and men at home, goods counters, loyalty, message counters, name index (economy.md §1) |
| patrol paths | `$168ee` | var | {dx,dy} word lists (the `_flights` spline table: `farm`, `pots`, `eyes`), terminated by a word ≥ `$7d00` |

## What each entity decides per tick (the answer)

For a **man** (category `$00`): integrate one step of velocity `(12,13)`;
check the destination cell is land (`$1648e`); if in mode `$10`, additionally
probe a few cells ahead and divert to mode `$48` (turn around the obstacle) if
blocked; if a bucket neighbour is an enemy, switch to fighting (`$32` →
`$56a6`); recover health (`$5c80`). It does **not** choose where to go — that
came from its group order.

For a man **resting in camp** (mode `$68`, the bulk of an army): nothing but
upkeep; the handler never moves him.

For a **captain resting at his town** (mode `$8a`): upkeep only, until a group order
or the `$4c` return handler (`$16176`) changes his mode.

For a **group lead** carrying a live order (`$51538` state 8 Attack, 5 Going To, 2 Get Food, 3 Get Men, ...): walk to the
destination cell in mode `$10`; on arrival the order's arrival mode runs: take food from a town (`$1a`), get men
from one (`$1c` → `$28`), camp (`$1e`), and so on.

The lords' strategic choices — *declare* an attack, *pick* which village,
*decide* to recruit or build — live one level up, in `$6522` / `$d322` /
`$3e06` (called from `$13040` every tick, operating on `$51538` and `$4f916`).
**That layer is decoded in `strategy.md`:** `$6522`'s `$6564`
branch is the commander AI — it picks the nearest enemy leader (`$68fe`),
scores the trip's food against the group's food (`$68ee` vs `112()`, the
group's `36`; strategy.md "`$6522`"), and issues order `$0c` → group state 8 → the group lead enters mode
`$10` toward that cell (via `$6a3a` → `$4b80`). No economy or build planning
at that layer; the one economic sequence is the follow-up table `$6762`/`$67d0` (food, men,
equipment, invention orders chained after each finished state, `strategy.md` "The follow-up table"). `$d322` + `$3e06` only build the per-side force totals `$57fba`,
which `$d23a` reduces to the 0..4 force ratio `$57fce` (a fist indicator, and the victory test `== 4` at `$d2c8`); the AI does not read it.

## Measured

25M-step traced resume from `pm68_isoview.snap`, settled first-mission view
(one player army of ~20 men near a neutral village, a few loose animals):

- `$14b62` iterator: 97 passes (one per ~254k instr / ~21 VBLs).
- ~50 of 511 slots active; ~26 reach a handler per pass; ~4850 handler
  dispatches total.
- Mode histogram (handler entries): `$68` 2559, `$12` 774, `$0e` 445, `$56`
  168, `$5c` 152, `$5a` 119, `$8a` 99, `$60` 86, `$52` 51, `$84` 30, `$54` 29,
  `$48` 13, `$58` 11, `$86` 10 — everything else in single digits. In a quiet
  view the loop is almost entirely camp rest + farm walks + regroup dwell;
  combat modes (`$32`, `$5778`) did not fire.
- `$5c80` upkeep: ~2600 calls (once per moving or resting entity per pass).
- Instruction weight of the whole `$14b62` subtree: small next to the renderer
  — `$163ea` relink 1806 calls, `$1648e` 1979, `$164bc` 213. Consistent with
  `graphics.md`: the sim tick is cheap, the per-VBL fill is not.

### The re-armed fight — the melee casualty mechanic seen

66M-step traced resume from `pm71_slot4.snap` re-arming slot 1's `byte4 := 4`
every ~4M steps (16 pokes; `scratchpad/pm73_fight.evt`, `trace_cfg.py --blocks`).
~276 sim ticks.

| routine | hits | reading |
|---------|-----:|---------|
| `$6522` decide | 276 | once/tick |
| `$661a` the attack arm of the decide chain | **2** | re-arming `byte4` mostly does *not* re-trip `$661a` — the objective slot's `active`/`force` fields stop qualifying after the first order. Only 2 autonomous primary decisions in 276 ticks |
| `$68fe` / `$68ee` | 2 / 2 | the two decisions; both scored in budget |
| `$15302` reached-enemy | 41 | men closing on enemy positions |
| `$56a6` engage | 9 | contacts made |
| `$5778` bookkeep | 2 | gated hard on `flags.bit6` + `d < $fff` |
| `$1533c` melee (mode `$32`) | present | health-drain rounds |
| **`$5590` kill-or-rout** | **10** | first field-combat resolutions ever traced |
| — of those, KILL (`$55f2`) | **0** | |
| — of those, ROUT (`$560a`) | **10** | `$30fe` returned `2` every time (`group.field60 == 4`) → always rout |
| `$5bd2` wear removal | **0** | `anim_wear` never crossed `$3c` in ~276 ticks |
| `$57f0` projectile | 3 | |
| `$1d70` re-rank | **15** | runs on every roster change (it re-forms the ranks and writes no ownership) |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5c80` upkeep | 2136 | ~8 entities/tick |

**Finding.** PowerMonger's battlefield death is a **health-grind**, not an odds
roll: mode `$32` (`$1533c`) subtracts `(field44 >> 1) + 1` (`field44 >= 6` → just
`1`) from the enemy's `health` byte every tick a unit stays in contact; at
`health <= 0` `$5590` rolls **kill vs rout** off `$30fe = group.field60 − 2` (the
group's posture 2/3/4, strategy.md "What each order does") and, when that is neither 0 nor 2, the
`($57fec + anim_phase)` parity. In this fight the attack group's `field60 == 4` (the AI's attack stamp, `$6638`)
→ `$30fe == 2` → the roll is pinned to `$560a`; a unit there dies only if
`flags.bit5` is set (afloat: bit 5 men are drawn as boats, `$1174e`), otherwise it *routs* — survives, scattered by
`$3c08`. *(`$1533c` + the `$5590` KILL branches + `$30fe` + `$56a6`'s
`$574a` leaf are Proven vs the real 68000 — 413/413 tracked bytes over 48
differential states; the `$3c08` regroup dispatcher that scatters the
routed unit is Proven too — 71/71 over 22 states; the `$5778` group plumbing stays asserted off in the
combat proof, while `$2776`, `$1b8c` and `$3c08`'s bit-4 group teardown are Proven in their own blocks below.)* The `$5c80`/`$5bd2` **wear** path
(`anim_wear - $3c`, health-cap table `$5ccc`) is a slow second channel that a
short fight never reaches — `anim_wear` is only bumped by the iterator's
animation-advance (`$14b9a`, ~once per animation cycle) and is not reset by any
handler, so it is a lifetime-exhaustion counter, relevant only over a long
campaign. So the quiet view's "no casualties" is right about *deaths*, but
**routing is the real outcome** of a short fight and it fired ten times. Kills need either a
disciplined attacker group (`field60 != 4`) or `flags.bit5` (a man in a boat).

### Natural runs on later lands

Four lands built through the briefing-OK poke (`README.md` "Driving a later
land"; the briefing preview's roll, `$5809c` non-zero, not the Play Random Land roll, whose lands are denser and were not run this long) and run 200M steps each with no pokes, in four 50M stretches, counting PC
hits with the REPL's `hits` command (`reversing/powermonger/py/runland.sh`; snapshots
`scratchpad/pm121/run/<land>_s1..s4.snap`). Totals over the 200M steps:

| routine | land 5 | land 60 | land 0 | land 25 |
|---------|-------:|--------:|-------:|--------:|
| `$6522` commander decide | 1153 | 1110 | 1321 | 1135 |
| `$661a` the attack arm of the decide chain | 7 | 6 | 8 | 4 |
| `$56a6` engage | 19 | 27 | 36 | 135 |
| `$5590` kill-or-rout | 17 | 26 | 29 | 78 |
| — KILL `$55f2` | 9 | 7 | 18 | 59 |
| — ROUT `$560a` | 8 | 19 | 12 | 17 |
| `$5bd2` wear removal | 0 | 0 | 0 | 0 |
| `$57f0` projectile | 8 | 15 | 23 | 61 |
| `$1623c` dying-entity ticks | 21896 | 5361 | 9756 | 40945 |
| `$2776` / `$1b8c` | 3 / 74 | 2 / 26 | 2 / 27 | 3 / 52 |
| `$3c08` regroup | 237 | 155 | 86 | 213 |
| `$4bc8` contact reconcile | 9 | 16 | 10 | 92 |
| `$5cde` work-order choice | 336 | 59 | 309 | 707 |
| `$550e` revolt | 6 | 6 | 6 | 6 |
| `$25d6` (a captain defects, via `$5c2c`; land 25's from the `$1618a` removal path, land 60's from a revolt) | 0 | 1 | 0 | 1 |
| `$45f2` pigeon launched | 17 | 13 | 19 | 25 |

A later land fights without being prompted: every land killed men (`$55f2`),
the first kills seen anywhere (mission 1's forced fight: 0), and `$2776` fires
17-37 steps after a kill (two instances checked), from the `$5628` tail when the
dead man was in a group (12 of the 13 hits; the thirteenth comes from a
captain's defection, `$25d6`). The
enemy lords' pigeons (byte6 20, owners 2 and 4 on land 5) fly to their groups
over and over, the visible side of `$661a` issuing orders. `$5bd2` never fired.
`$550e` (called from the `$7c`/`$7e` heartbeat at `$158cc` and from mode `$2c` at
`$53f6`, the conquest arm `$539a`; gate `py/diff_4f68.py`) is how land changes hands (economy.md §3 and the revolt-chain proof below). Re-running two lands from the same snapshot
reproduced every count exactly. Land 5's run started at step 0 of
`scratchpad/pm121/k5.snap`; the first kill is at step 27,732,607 of stretch 1.

The same census on the Play Random Land roll (`$5809c = 0`, `PAGES0=1 build_land.sh`, the same four seeds plus a land the game itself rolled, `scratchpad/pm142/rand1.snap`;
`runland.sh`, four 50M stretches each, `scratchpad/pm143/run/`), totals over the 200M steps. These lands are denser (more men, buildings and trees) and the counts move,
the picture does not:

| routine | seed 5 | seed 60 | seed 0 | seed 25 | `rand1` |
|---------|-------:|--------:|-------:|--------:|--------:|
| `$6522` commander decide | 482 | 1140 | 1097 | 1044 | 1198 |
| `$661a` the attack arm | 8 | 9 | 12 | 12 | 8 |
| `$56a6` engage | 51 | 83 | 142 | 46 | 88 |
| `$5590` kill-or-rout | 53 | 64 | 130 | 61 | 107 |
| — KILL `$55f2` / ROUT `$560a` | 27 / 26 | 60 / 4 | 89 / 41 | 55 / 5 | 55 / 52 |
| `$5bd2` wear removal | 0 | 0 | 0 | 0 | 0 |
| `$57f0` projectile | 15 | 37 | 25 | 41 | 35 |
| `$2776` / `$1b8c` | 3 / 28 | 4 / 85 | 4 / 92 | 3 / 82 | 4 / 78 |
| `$3c08` regroup | 116 | 139 | 133 | 84 | 151 |
| `$4bc8` contact reconcile | 11 | 19 | 26 | 10 | 22 |
| `$5cde` work-order choice | 7 | 401 | 79 | 209 | 46 |
| `$550e` revolt | 5 | 8 | 14 | 4 | 6 |
| `$25d6` | 0 | 0 | 0 | 0 | 1 |
| `$45f2` pigeon launched | 24 | 37 | 29 | 36 | 26 |
| `$60dc` | 0 | 0 | 0 | 11 | 56 |
| `$163b8` | 6 | 1132 | 111 | 403 | 118 |

Every land kills men, `$5bd2` never fires, and `$2776` and `$1b8c` follow kills as before. Two differences matter for the gates: `$60dc` has natural entries (11 on seed 25, 56 on `rand1`; the preview-roll table above does not list it) and `$5e3a` (a building going up, byte6 30) fired once each on seeds 60, 0 and 25. The 200M-step counts are not repeated per roll for the rest of this document;
the preview-roll table above is the one the later sections quote unless they say otherwise.

## Proofs against the real 68000: dying entities, groups, orders, animals and the `$15000` page

The same method and bar as above, for the routines around the entity loop.

### [Proven] — the dying-entity path `$1623c`, vs the real 68000

`tools/pm_fsm_ref.py` `call_1623c` (+ `$16376` goods credit, `$16392` unlink,
`$45ee` pigeon launch); `reconstruct()` runs it for every record with a
negative owner. Differential test
`reversing/powermonger/py/diff_1623c.py`: **275/275 tracked bytes identical over 23
states, 9 branch families**, on dead men the game made itself on lands 0, 5, 25
and 60 (8 natural states with every dead record live, plus pokes of one field on
a natural record). Tracked: `REGIONS` + the player's pigeon record `$4c112`
(26 B) + `$57ff4`. Every other byte the real routine wrote is stack (entry SP
`$2c920`).

- `word[18]` counts down from `$a0`; while it is non-zero `32(A1)` steps 0-3
  (the rising figure's flap, SPEC §6 byte6 12).
- At 0: `20(A1) := [$4bb3e]`; the first record in the same cell with byte6 2,
  `$10` or `$1e` (settlement building, leader's base, building going up) gives a
  leader, `$4e514 + word[rec + 14]`, and each goods code in `33(A1)`/`44(A1)`
  (`code 0` = none) adds 1 to `goods[(code − 2) >> 1]` unless it is `$ff`; the
  codes are cleared. Then flags bit 5 clear → `byte6 := $0a` (the equipment
  stays on the ground, drawn by `$11772`) if any code is left, else (or with
  bit 5) `byte6 := $20` (never drawn) and `$16778` unlinks it. `$16778` ends on
  `clr.l`, so `beq $1622c` at `$162ea` skips the flap step.
- Once `word[18]` is 0, a pending pigeon request `[$57ff4]` (an object offset)
  is served by the first such record the iterator meets: it clears the request
  and, if the player's pigeon (`$4c112`) is free (`byte6 == 0`), launches it
  (`owner := 1`, `22(A0) :=` the requested object's position, `8(A0) := $01800180`,
  `$45ee`, `20(A0) :=` this record) and unlinks the record if it is byte6 `$0a`. The launching record is the pigeon's rider: when the pigeon lands, `$4244` (in `$3e06`) revives that
  same dead record as a live man of its home settlement at the landing point and adds one to the home lord's `troops_field` (`$42be`; counted live, 6 of 6, `economy.md` section 1).
  The `cmp.l #$3e8` at `$16322` has no branch after it.

Branches exercised: natural countdown (8), countdown reaching 0 with no base in
the cell (3), with a base (4), with a base and no goods (1), flags bit 5 (2),
goods counter already `$ff` (1), pigeon launched (2), pigeon busy (1), pigeon
launched from byte6 `$0a` remains (1).

### [Proven] — the group dissolve `$2776`, vs the real 68000

`tools/pm_fsm_ref.py` `call_2776` (+ `$39d4` goods handover, `$1d36` roster
unlink, `$3ce8` current-group select, the tracked parts of `$187d8` and
`$71ae`). Differential test `reversing/powermonger/py/diff_2776.py`: **4119/4119
tracked bytes identical over 28 states** (15 natural, 13 poked), 21 branch
combinations. Callcap runs at IPL 7, so states where the sound driver's busy
flag `$2c993` is set get `$2c993 := 0` first, or `$1ae40` never returns.

Entry: `A3 = $51538 + group_off`, a group exec sub-record
(`side*$13c + $4c + 2k`). Two callers: the `$5590` kill tail at `$564e`
(`A3 = $51538 + 42(victim)`), which runs only when the victim's owner byte is
`<= 0` (`$563e: tst.b 5(A3); bgt $56a0`, so a routed survivor skips it), and
the captain defection `$25d6` at `$262a` (1 of the 13 natural census hits,
land 25; the other 12 come from kills).

- **Captain group** (sub-record 0 of its side, `(A3-$51584) mod $13c == 0`):
  every record of the order-pigeon pool (26-byte records, `$4c12c..$4c5f2`; slot 0 at `$4c112` is the player's pigeon) owned by that side
  is unlinked (`$16778`) and cleared. **Other groups**: the effect records whose
  `20(rec)` is the group's lead are cleared (and the local side's `$57fd8`
  entry for that sub-record).
- Then: `36(A3) &= $3ff`; `$39d4` hands the group's goods to whatever lies on
  the lead's cell (an existing goods pile `$2c`, a settlement or building,
  crediting its leader's goods and `food`, or a new `$4bb4e` pile);
  `$1d36` unlinks every member through `$1b8c`; a live lead loses its group
  offset; **`-48(A3)`, the sub-record's owner side, is cleared**; `$3ce8` makes
  sub-record 0 the side's current group; `$187d8` redraws the local side's
  panel.
- For a captain group whose side's command-slot state is 8 or 6, `$71ae`
  tears the link down and demotes every command slot (6 to 2, 8 and the rest to 4, 0 and 2 unchanged; strategy.md "Serial-link states"). The state is read at `$58016 + 3*side + 4`
  (`$28e4: mulu #$3`), not `6*side`, so side 2 reads side 1's slot and side 1
  reads its own order byte (confirmed on the real CPU by `k5_s1_1_cmd8`). That
  this is a bug is inferred.

Clearing `-48` of the local side's sub-record 0 is how the player loses a land
(`strategy.md` "How a land ends"); one natural corpus state is exactly that
(`k60_x1`, land 60, step 94,725,510 after `run/k60_s4.snap`).

### [Proven] — the lord's work order `$5cde`, vs the real 68000

`tools/pm_fsm_ref.py` `call_5cde`. Differential test
`reversing/powermonger/py/diff_5cde.py`: **768/768 tracked bytes identical over
47 states** (32 natural, 15 poked or with a register preset), 15 branch tags,
and the returned `D2`/`D3`/`D4` low words 85/85. `$5cde` chooses the lord's whole work order (original `_set_tow...`, a prefix shared with `$2eac` and `$550e`).
Callers: the settlement heartbeat (`$1589a`, `D1 = 14(marker) & 3`) and the
group-order handler (`$5fc0`, `D1` = the `$30fe` result). `A0` = the leader.

1. Walk the lord's settlement chain (`2(L)`, next `+8`) for a WorkShop
   (`+7 == 7`). No buildings or no WorkShop: return 0 (27 of 32 natural hits).
2. Find the nearest live forest op in `$57f68..$57fb8` by `max(|dx|,|dy|)` from
   the lord's cell `4(L)`, and read the cell's altitude `$3f86c[4(L)]`.
3. **Build** (`D2 = $40`) when a site is already under way (`18(L) != 0`), or
   the altitude is `>= $10` and either no forest op is within 20 cells or
   `$57fed` bit 0 is set. A new site allocates a `$4f916` record
   (`$51536 += 18`, capped at `$1c20`) on the cell of the first unit with flags
   bit 0, owner = the lord's side, byte6 `$1e`, and links it into the `$47970`
   bucket through `$16808` with a negative offset from `$51b66`; `18(L)` keeps
   it. **Fell trees** (`D2 = $3e`) when a forest op is within 20 cells: `12(L)` from
   `D1` and the OR of the units' flags (`$e`/6, `$a`/8, 2) and `20(L) :=` that
   forest op (the gather kind and its goods counter: economy.md §2a). **Fallback** (`D2 = $6a`, `12(L) := $c`) otherwise, including a
   wanted build with no flagged unit or a full table.
4. Every non-zero path reloads `16(L) := $580a6[side].word8 + 4` (`+$2000` if
   `12(L) >= $e` and the reload is not below the old value) and stamps
   `31 := D2`, `46 := the WorkShop`, `36 := D4` (and `39 := 4` when `D4 == 0`) on
   every eligible unit of every settlement in the chain (owner `> 0`, flags
   bits 6 and 4 clear, mode not `$5c`/`$60`/`$62`). The unit loop has no
   empty-chain test, so a settlement with no units stamps object slot 0.

Natural states: 27 no-WorkShop exits, 4 tree-felling, 1 fallback. No natural state took
the build side (the control byte was 1..6 and `18(L)` 0 in all of them), so the
build arms are proven on poked states only and how often lords build in play
is not measured. Not reached: the `31 == $62` filter, and the `12 := 6` /
`12 := 8` arms.

### [Proven] — the revolt chain `$550e` → `$5c2c` → `$25d6`, vs the real 68000

`tools/pm_fsm_ref.py` `call_550e`, `call_5c2c`, `call_25d6` (+ `rng_12c9a`,
and the `$2776` family above). Differential test
`reversing/powermonger/py/diff_revolt.py`: **1778/1778 tracked bytes identical
over 49 states, 24 branch families**: all 27 natural `$550e` calls on lands 0,
5 (two runs), 25 and 60, the 4 natural `$5c2c`/`$25d6` calls, and 18 pokes.
The corpus runs `$25d6` into `$2776`, so it also checks the `$2776` family
against a second, independent corpus.

- `$550e` (A0 = leader, A1 = the object whose side byte is the new side): the
  mechanics are in `economy.md` §3. Of the 27 natural calls, 11 come from the
  heartbeat (loyalty 600-608) and 16 from mode `$2c` (`$53f6`, loyalty 0-292).
- `$5c2c` (A1 = the man): nothing if his settlement's leader is on his side;
  `$4bc8` if he leads a group that still has members or the leader has no
  `troops_field`; otherwise he defects and `$25d6` runs.
- `$25d6` (A1 = the man, D3 = mode): dissolves his old group (`$2776`) or takes
  one off his old leader's `troops_field`; takes his new side's first free
  sub-record (none: returns 0); makes him its lead (`42(man)`, flags bit 4,
  `-12(sub)`), `0(sub) := 6`, `36(sub) := $5fff` if the side's command slot is
  in state 4 (else 0), `-48(sub) :=` the side, `72(sub) := rng & $580a6[side].w12`,
  `60(sub) := 3`, then `$3c08`. D3 = 2 would bump `$12abe`/`$12acc`, but
  `$5c2c` sets D2, not D3.

Not reached: `$187d8` from `$25d6` on the player's side with D3 ≠ 0 (asserted
off in the transcription), and the RNG's zero-seed reload.

### [Proven] — shepherds, animals and carrier pigeons

`tools/pm_fsm_ref.py` `h_mode80/82/84/86/88` (wired into `reconstruct`), `call_animals`, `call_pigeons`; `economy.md` section 5a for how the shepherds and animals come to exist.
Differential tests: `py/gate_shepherd.py` **1043/1043 tracked bytes identical over 198 states** (`callcap 14b62` with one record live: natural shepherds of two land builds run
forward, `$80` 5, `$84` 76, `$86` 20, `$82` 1, plus 16 each of synthetic `$88`, `$82`, `$86` arrival, `$86` one step short, `$86` with the whole chain herded and `$86` without a chain);
`py/gate_animals.py` **45094/45094 compared values identical over 55 snapshots** (`callcap 3e06`, see below for what is compared; free walk 1073, free turn 820, herded 187, pigeon
flights 81, pigeon re-steers 5, two natural pigeon arrivals).
Both gates were rerun on the Play Random Land roll (`$5809c = 0`, `build_series.py` with `PAGES0=1`, lands 0 and 5, 30 snapshots each): shepherds **1010/1010 over 215 states** (natural `$80` 27, `$84` 70, `$86` 21, `$88` 1, plus the same 96 synthetic ones) and animals **49178/49178 over 60 snapshots** (free walk 1640, free turn 384, herded 346, pigeon flights 126, re-steers 11, two pigeon arrivals; no live projectile, nothing excluded), so neither depends on the roll.

**The animals** (sheep: the panel names category 8 "Sheep"; the 8-character symbol `init_she` is shared by `$2b08`, the shepherd, and `$2d0e`, which by the panel text is presumably `init_sheep`) live in a pool of 40 records of 20 bytes at `$4ccd6..$4cff6`; the word at `$4cff6` is the bytes used. The pool is filled once, by the shepherds' world-build pick (`$2d0e`
is called from one place, `$2b32`; the count word is only ever added to), no animal is born or freed afterwards, and the count stayed at 720 and 800 bytes over 30 snapshots on two
lands. They are a pool of their own: separate from the tree array `$4d252` (economy.md §2) and from arrows (`$4be00`).

```c
typedef struct pm_animal {            // $4ccd6, stride 20, 40 slots
/* 0*/ u16 bucket_next;               // the $47970 cell chains, offsets from $51b66 (negative: the pool lies below the man table)
/* 2*/ u16 bucket_prev;
/* 5*/ u8  owner;                     // the shepherd's side + 4 (> 0 = alive for $15e30 and the statistics routine $b8f4)
/* 6*/ u8  category;                  // 8 = Sheep (the game's own panel text, strategy.md "The game's own text"); the slaughter (mode $38) makes it $1c, a carcass; the loop below also takes $22 = Cow, which nothing writes
/* 7*/ u8  state;                     // $11 free, $12 herded, $10 dead or still (skipped)
/* 8*/ s16 x;   /*10*/ s16 y;         // world position
/*12*/ s8  vx;  /*13*/ s8  vy;        // velocity per tick; a herded animal's are the fixed offset from the shepherd (both |= $40)
/*14*/ u8  heading;
/*15*/ u8  speed;                     // 2..9
/*16*/ u16 prev_animal;               // the shepherd's chain, 0 at its end (offset from $4ccd6)
/*18*/ u16 shepherd;                  // the man's offset from $51b66
} pm_animal;
```

**The update** is the loop `$4044..$4166` inside `$3e06`, once per tick for all 40 slots: a slot with category 8 (or `$22`) and state other than `$10` is
- **free** (`$11`): the new position is the position plus `(vx, vy)`, clamped (`x >= 0`, `y < $6000`); if all four corners of the cell it falls in (`$3f86c`, `+1`, `+64`, `+65`) are above sea level
  the animal moves there and is relinked (`$163ea`); otherwise it stays, its heading goes up by one and the velocity becomes `(0, ~speed)` rotated by the new heading, so an animal that meets
  the shore turns by 1/256 of a circle a tick until it points inland, then walks straight on (820 turns against 1073 steps in the 55 snapshots);
- **herded** (any other state, in practice `$12`): it stands at the shepherd's position plus `(vx, vy)` (clamped like a man), its heading copied from his byte 17, and is relinked.

**The shepherd cycle**: `$80` (at the town) → `$84` (wait 50 ticks) → `$86` (round up the chain's free animals one by one: walk to the midpoint, mark it herded) → `$88` (walk to the cell
south of the town) → `$82` (walk onto the town and let the herd go) → `$80`. Nothing in the cycle touches food, goods or `troops_field`; the one economy-relevant call is `$16848` at the
town, the same arrival upkeep every job uses. Animals matter to the rest of the game only as targets: the objective class of category 8 (`$4dae`, picked by `$50da` into mode `$36` and then the slaughter mode `$38`), which nothing a shepherd
does triggers and which was never seen naturally (the `$36` row above). Natural coverage: of 210 shepherd samples (ten snapshots of each of two lands), 102 were in `$84` (the 50-tick wait dominates), 21 in `$80` and 11 in `$86`; `$88` and `$82` last a single walk each and were not caught.

**The carrier-pigeon pool `$4c112..$4c5f2`** (48 records of 26 bytes; `$416e..$4326` of `$3e06`, after the animals): slot 0 is the player's pigeon (launched through `$45ee`, which falls into `$45f2`, from the request served in `$1623c`; landing `$4244`, the
revival of a dead man described in `economy.md` section 1), the other 47 are the order pigeons launched by `$4562` (through `$45ee`, category `$14`; section "Arrows and carrier pigeons" below). Per tick a live record (owner byte > 0, category
byte non-zero) counts word 18 down; above 0 it flies on by its velocity bytes 12/13 and relinks; at 0 it re-steers with `$164bc` toward its target (the player's own word 22/24; any other pigeon
the position of its rider, the man at its word 20), the new flight time is `min(2 * dwell, $30)` into byte 15, and a time of 0 is the arrival. An **arrival of another lord's pigeon** (`$41dc`,
natural in two of the 55 compared snapshots) hands the rider's group the order packet `{the group's side, byte 23, word 24}` through `$6b38` (the order executor, `strategy.md`) when the rider is still alive,
decrements the local side's pending-pigeon counter `$57fd8[2k]` when the group is the local one, then unlinks the pigeon from its cell and frees it (category 0). So the 47 other records of the pool are the order pigeons that deliver a commander's orders to his other captains (the visible side of `$661a` issuing orders), and `$41dc` never touches `troops_field` (code read).

What the gates compare and leave out: `gate_animals.py` compares the 40 animal records (links included) and, for every cell an animal left or entered, the whole bucket chain with forward
and backward links, because `$3e06` also moves the pigeons (modelled: flights, re-steers, the `$41dc` bucket effect) and runs `$596a` (projectiles; the 5 snapshots with a live projectile are
excluded), `$4342` (Proven above), the army food and health indicator (not compared). Not modelled: the effect of `$6b38` on the arrival, and the player's landing `$4244`
(asserted off; counted live separately, `economy.md` section 1). The projectile loop `$596a`, once excluded, is modelled and proven below. `py/gate_shepherd.py` needs a time series of snapshots after a land build (the recipe is in `py/README.md`).

### [Proven] — arrows and carrier pigeons: `$596a`, `$4562`, `$4624`

`tools/pm_fsm_ref.py` `call_596a` (with `_proj_end`, `_proj_area`, `call_4624`) and `call_4562`; gates `py/gate_proj.py` and `py/gate_pigeon_send.py`, each against `callcap` of the whole routine,
comparing every byte the real call wrote against every byte the model wrote (the stack excluded). Corpora: the entries of `$596a` and `$4562` in the 21 stretches of lands 0, 5 (also in winter), 25 and 60 that hold a live arrow or a
launch (`py/proj_scan.py`, `py/proj_corpus.py`, `tools/capture_hits.py`; recipes in the docstrings), plus synthetic states poked from them.

**`$596a` — the arrow loop** (once per tick; 49 slots of the effect array above). Per slot with life ≠ 0:

- life < 0: counts up one a tick and the slot is unlinked when it reaches 0.
- life > 1: **flight**. Position += (vx, vy), clamped to x in 0..`$3fff` and y ≥ 0 (the upper clamp on y is dead: `cmpi.w #$8000` is followed by `bmi`, which is always taken); relinked into its new cell (`$163ea`). A type `$12` flies on
  unhindered. Any other type then walks the chain of its new cell for the first record of category 0 (man), `$14` (pigeon) or `$16` (marker) whose owner byte is positive, differs from the shooter's byte 5 and lies within |dx| < `$10`,
  |dy| < `$16` of the arrow. **No flags are tested** (the flag bits 6 and 4, group member and leader, that `$32c6` honours do not exempt anyone). A man's health byte 45 loses `$52`; when the signed `subi.b` result is not positive
  (zero, negative, or an overflow: byte 45 is 0..`$7f` in play, so a value of `$80` or more would misfire) the `$5590` roll runs with the shooter as the attacker. A pigeon goes to `$4624`. A marker's owner byte is negated. The arrow is then spent (`$599e`).
- life == 1: the **end of life**, the same `$599e`. The slot's life := 0; if the shooter's byte 31 is `$34` (the shot cool-down, `$153b2`) and it is alive, its dwell byte 18 := 0, so **the archer's cool-down ends with the arrow**, after the full 20 ticks or at the hit; a type other than `$12` is unlinked.
  A type `$12` instead becomes an area effect (life −4) on every record in its cell: category 2 gets flags `$a`, category `$10` becomes 2 with flags `$a` and the lord's eight goods bytes `$4e514 + 24 + word 14` cleared, a man
  of another side than the shooter's goes to `$5590`, category 4 gets flags `$d`. Nothing creates a type `$12` (the port SPEC's "Why 18 and 28 are missing"), so this is covered by synthetic states only.

The gate: 364 natural entries (354 with an arrow flying with nothing in its path, 86 impacts, and one hit that is excluded below) plus 92 synthetic states, **4210/4210 changed bytes identical over 456 states**. The synthetic ones place a target at the arrow's position
(a man with health `$60/$30/$90/$52/$53/$00/$7f/$80`, at the edges of the 15 × 21 box, of the shooter's own side and dead; a pigeon with and without a rider, with a rider of the local side and a group; a marker; moving arrows; the type-`$12` flight, fade and area
cases on a building, a building going up, a tree and a man). 8 states are excluded because the roll `$5590` reaches its group cleanup tail (`$1b8c`), which `kill_rout_5590` asserts off. Natural firing over 21 stretches of 50M steps: 6195 `$596a` ticks, 91 `$57f0` shots,
127 `$5590` rolls of every cause and **no pigeon ever shot down** (`$4624` 0 hits). The shipped example of a natural kill by an arrow is `k0_s1_202` (excluded, for the same tail).

**`$4624` — a pigeon shot down.** The pigeon's owner byte is negated (dead) and nothing frees it: the pool loop of `$3e06` and the free-record search of `$4562` both skip a record with a non-zero category, and the only code that clears a pigeon's category is the
arrival `$41dc`, the landing `$4244` and the group dissolve `$2776` (code read of every reference to `$4c112`/`$4c12c`/`$4c5f2` in the whole image). `$2776` frees it when its rider (word 20) is the dissolved group's lead. If the rider is a man of the local side with a group, the
group slot's counter `$57fd8 + 2j` is decremented when non-zero (the offset is the rider's word 42, `(w − $4c) mod $13c`: word 42 is a group offset only for a lead, a farmer's is its field cell, and an odd remainder is an address error).

**`$4562` — how an order reaches a subordinate captain.** `$6ac6` (per tick, once per command slot 1..4 with a type byte): types `$22` and above (chat, the alliance reply, the link commands) and groups without a lead run `$6b38` at once; otherwise D2 = the side's group offset (`$58042[2 × side]`, 0 = nothing; the group the executor acts for: `$6822` writes an order straight into the slot only when its group is that one, otherwise it stores it in the group's pending record `1(group − D7)` and posts `$22`, a captain select (`$3ce8`), code read) and the group's **word 48 is the sender**: the lead of the side's first group, 0 for that group itself. No sender: the order runs at once (`$6b2e`). So the commander's own group, the player's first captain and an AI lord's own army, acts directly (live: order `$12` from `m1_s0`,
`$6ac6` → `$6b2e` → `$6b38` → `$39d4` with `$4562` 0 hits). Any other group is reached by a **carrier pigeon**: `$4562` takes the first free record of `$4c12c..$4c5f2` (47; slot 0 is the player's), copies the sender's owner and position (`$51b66 + word 48`), the order's type
(byte 23) and target word (24), sets the rider (word 20) to the group's lead (`-12`), launches it (`$45ee`, then flight time byte 16 = `$78`) and clears the order's type byte. The pigeon flies to the lead (`$3e06`, above); its arrival `$41dc` hands `{side, type, target}` to `$6b38`.
With no free record nothing is launched and the order is lost (`$6a3a` clears the slot's type byte anyway). For the local side's group `$4562` first counts the pigeon in `$57fd8 + 2j` (j = the group's slot, 0..4), and `$3e06` (`$3ee8`) draws a flapping pigeon (frame `$127 + (tick & 7)`, positions from the table `$4548`) over captain box j
while the counter is non-zero (code read, not seen on screen). The direct branch is dead in practice: the test `$6b06..$6b1e` was meant to compare the sender's cell with the target lead's, but it loads its second record from `$51b66 + word[$51b5a]` (`-12` of the wrong base: word 0, record 0, all zero),
so it is taken only for a sender at cell (0, 0) (code read; the `$6b20` branch has no hit in 21 stretches). Group census, two snapshots (`m1_s0`, `k5_s4`): the first group of each side has word 48 = 0 (3 of 3 live first groups); 3 of the 4 other live groups carry the first group's lead, and the fourth (side 3 in `k5_s4`, whose first group is gone) a stale record offset of a man of side 4. Routing proven (`py/cmdai/exec_census.py`, `hits` on 44 poked slots: 44/44 against `py/cmdai/cmdai_ref.py` `call_6ac6`): no sender or type `$22` and above runs `$6b38` at once, a sender with a different cell goes by pigeon (`$4562`, 5/5), and with `$51b5a` poked to the sender's own offset (cell equal) the direct branch runs (5/5; the `clr.w -72(A1)` it does first is a code read); a side with no `$58042` entry does nothing. The executor loop and routing are also `callcap`-proven against the model on natural and synthetic states (`py/cmdai/gate_exec.py`, `strategy.md` "The order executor").

`py/gate_pigeon_send.py`: **1567/1567 changed bytes identical over 125 states**: 95 natural launches (all by AI groups, `$4562` 48 times and `$6b38` 171 in the 21 stretches), 12 synthetic states with the pool full (no launch), 12 with the group's side made the local side (the counter), and the pool with only its first
or last record free. The player's own order to a second captain is therefore a code read plus the synthetic local-side states, not a natural run.

### [Proven] — the `$15000` page of mode bodies, vs the real 68000 (`py/fsm15/gate_fsm15.py`)

`py/fsm15/fsm15_ref.py` models the mode bodies from `$1501a` to `$16176` that the earlier blocks above do not cover, and plugs them into
`pm_fsm_ref.reconstruct` through its `SHEP_MODES` dispatch table. `gate_fsm15.py` runs each state as one RAM image with every other live record
disabled, the record under test in its mode, `callcap 14b62`, and compares the whole real delta byte for byte with the model over the entity table,
buckets, leaders, settlements, the group table `$51538..$51b66`, the tree array `$4d252..$4e514`, the stat counters `$12a24`/`$12a32`, the RNG seed and
`$57ff4`: **18452/18452 tracked bytes identical over 1889 states** (117 natural: records caught in the mode in 44 snapshots; 1772 synthetic: the mode
and the fields it reads poked on real records). Five synthetic states are unrun: one asserts the model's out-of-scope `$5cde` arm (`$7e` in winter),
four make the emulator itself throw at `$35f4` on a group I built (`$3a` x2, `$1c`, `$72`). 611 of 621 model statements are executed; the rest are
the `$155ac` no-tree exit with flag bit 6, three edge-fail statements of `$15c46`, the empty-pile unlink of `$1605a` (`$16778`, asserted out) and a
`break` of `$15bfc` (a trace artifact). Handler entries per 60M steps over 44 snapshots (`py/fsm15/census.sh`): `$14` 781, `$16` 4005, `$18` 3933,
`$1a` 26, `$1c` 96, `$1e` 110, `$20` 4971, `$24` 3832, `$28` 2895, `$2a` 3809, `$2e` 1442, `$30` 40, `$34` 3324, `$3c` 7956, `$3e` 314, `$40` 153,
`$44` 158, `$6a` 475, `$46` 8777, `$48` 59227, `$4a` 3303, `$4c` 8, `$4e` 1598, `$50` 1554, `$52` 76324, `$54` 80235, `$5e` 1294, `$56` 64836,
`$58` 1166, `$62` 1099, `$5a` 12675, `$5c` 21976, `$60` 20563; `$26`, `$36`, `$66`, `$38`, `$3a`, `$72` never.

| mode | entry | states | tracked bytes | notes |
|---|---|---|---|---|
| `$14` | `$1501a` | 8 | 16/16 | |
| `$16` `$18` `$24` | `$15042` `$150b0` `$151c2` | 14, 8, 8 | 70, 16, 44 (all identical) | `$16`: summer and winter, plough |
| `$1a` `$1c` | `$150c0` `$15122` | 24, 25 | 1716, 602 | town chain men kept live so `$34f2` really sends them; group states 3, `$c`, 6; bit-7 men |
| `$1e` `$20` `$26` `$28` | `$1515c` `$15170` `$15200` `$15264` | 5, 9, 8, 10 | 370, 15, 273, 262 | `$26` synthetic only |
| `$2a` | `$15282` | 37 | 209 | join, quota 0, negative quota, side mismatch, refused, first-tick dwell, lead not in state 3 |
| `$2c` `$30` `$34` | `$152f8` `$1518a` `$153b2` | 5, 4, 8 | 5, 309, 12 | `$2c` glue only; `$4f68` is `diff_4f68.py` |
| `$2e` | `$15302` | 49 | 1088 | seven target mode/prev pairs |
| `$36` `$66` `$38` `$3a` | `$153cc` `$1540c` `$1547e` `$15518` | 49, 7, 12, 26 | 392, 21, 208, 552 | all four synthetic only; `$3a` indexes the bucket array with `2 * y(target)` (y up to `$7fff`, so it reads outside the array: a defect), proven for in-range y only |
| `$3c` `$3e` `$40` `$44` `$46` `$6a` | `$15598` `$155ac` `$15680` `$156be` `$15724` `$156e0` | 9, 53, 3, 5, 9, 3 | 20, 258, 14, 35, 11, 19 | |
| `$48` `$4a` | `$158da` `$1597a` | 277, 9 | 1046, 32 | incl. map-edge probes and the `$80` sweep word |
| `$4c` | `$16176` | 12 | 453 | `$5c2c` side reconcile (the callcap needs the sound flag `$2c993` poked to 0) |
| `$4e` `$50` `$52` `$54` | `$15a0e` `$15a60` `$15a80` `$15ad2` | 17, 3, 57, 119 | 97, 6, 387, 884 | merchants; `$54` stale-A0 pickup (row above) |
| `$5e` `$56` `$58` `$62` `$5a` `$5c` `$60` | `$15b5e` `$15b94` `$15bec` `$15bfc` `$15c46` `$15d66` `$15ddc` | 11, 13, 2, 45, 633, 237, 29 | 34, 50, 4, 242, 6292, 1448, 148 | fishers; `$5a` with 18 RNG seeds and map edges, `$5c` with all 16 corner combinations of the altitude cell |
| `$72` | `$1605a` | 12 | 767 | synthetic only; non-empty pile only |
| `$64` `$70` `$7e` `$8e` `$90` | `$16044` `$160e0` `$157e6` `$160e4` `$160f2` | 2, 1, 6, 3, 3 | 0, 0, 6, 6, 13 | glue; `$7e` is the heartbeat body (heartbeat block), `$8e`/`$90` call `$160f8` (`gate_equip.py`) |

Not modelled (their callees belong to the orders executors): `$22` (`$5fa0`), `$42` (`$600a`), `$6c` (`$32c6`), `$6e` (`$61f8`), `$74` (`$3956`),
`$76` (`$33b0`), `$78` (`$63f4`), `$7a` (`$3da4`).

New leaves modelled and proven through the states above: `$34f2` (the town summons: every able man of the lord's settlements, bit 6 clear, bit 7 or
(bit 4 clear and mode not `$5c`/`$60`/`$62`, gets `20/22` = the lord's cell, advancing the x word by `$50000` per man, mode `$10`, prev `$14`, `46` = the
lead offset in group state 3), `$1b2a` (join: the lead and the man must have the same owner, or the man's settlement the lead's owner, which the man then
adopts; the man heads the roster chain `26`, `28` = the lead, flag bit 6), `$159a4`/`$159de` (item code `2 * (slot + 1)` banked into / taken from the
lord's goods byte `23(A0 + code / 2)`; the pickup kind is `word[$57fec] mod 6`, code into byte 33 when `>= 8` else 44), `$15fa8` (fishing-cell
collision: the four altitude-plane bytes at `+0/+1/+64/+65` of cell `(D7 >> 8) * 64 + (D6 >> 8)`, with the carry/borrow of the low bytes deciding
the diagonal). Two model details the gate forced: a bucket chain also links markers and buildings as negative offsets (`adda.w` sign-extends: fixed in
`pm_fsm_ref.call_35f4`), and `bge`/`blt`/`bgt` after `add.w`/`subi.w` test N xor V, the mathematical sign of the result, not the wrapped word's
sign (`$15c46`'s scaled target is not clamped to 0 when the sum is positive but wraps).

## Open threads

- **The strategic layer** — decoded in `strategy.md`, including the natural
  `$661a` decisions and how a land ends. Still open there: the `$580a6`
  per-side assessment / diplomacy subsystem (`$2200`–`$3500`).
- **`$5778` / combat** — the mechanism is closed (this file's combat block plus `strategy.md`
  "Combat"). `field44` is written only by the world build (`$2452`/`$2500`,
  from the side block) and the equip paths `$16124`/`$159de` (codes 2/4/6);
  the projectile type is `$28` for a bow (6) and `$12` for `$e`/`$10`, a value
  no writer produces, so `$12` is unreachable (`port/SPEC.md` "Why 18 and 28
  are missing"). `group.field60` is the posture: the player's
  posture icons (order `$16`) and the AI's `$6638`/`$6762` set it.
- `$51538` group record: `strategy.md` has the stride (`$13c`), the header
  (pending long / type / param) and the six groups' parallel arrays (the old
  "objective slots" and "execution sub-records" are the side's groups; field table in
  strategy.md "`$51538`"). The least explained array is `+280` (campaign phase / sub-order).
- The mouse "move / attack / fully engage" commands reach the group state through the order-to-state table `$6888`
  (strategy.md "The player's commands" and "`$6822`: issuing an order"); the order table's remaining handlers
  are in strategy.md, not here.
