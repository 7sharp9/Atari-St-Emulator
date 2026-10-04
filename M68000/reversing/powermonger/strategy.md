# PowerMonger ST — the strategic layer (the commander AI)

This file covers the layer above the per-entity state machine of `ai.md` (`$14b62`, ~2.4 Hz): how a captain decides to march an army at an enemy, how that decision reaches the entity loop, and the machinery around it that shapes a land's life. It holds the sim tick `$13000` and its measured cadence, the two tables the AI reads and writes (`$58016` command buffer, `$51538` group orders), the commander AI `$6522`, the order executor and every order the player can post, the per-side force totals and the armies' food, combat as a mechanism, the RNG, the world build and the starting armies, how a land ends, diplomacy, the campaign map, and the developers' own names for routines and fields (their symbol table and the game's UI text). A hidden-feature audit and the open threads close it.

Method: disassembly of `scratchpad/pm70_iso.ram` (the game image at its absolute addresses), block traces, field watches and `callcap` gates against Python models, driven from snapshots such as `scratchpad/pm68_isoview.snap`, `pm71_run1.snap` and `pm123/win/m1_s0.snap` (the first mission, "Between Pages 1-5"). Claims are labelled **proven** (a gate script with a match count), **live** (an emulator run), **code read** (disassembly only) or **inferred** (the code supports it, nothing ran it); an unlabelled claim carries the evidence stated beside it. The other docs cite sections of this file by title, so keep the titles when editing.

## Contents

- Tick and tables: "Where it runs", "The two tables the AI reads and writes" (`$58016` with the serial-link states, `$51538`), "Data structures (C)".
- The AI and its orders: "The commander AI `$6522`" (lord scans, target recheck, "The follow-up table `$6762` / `$67d0`" with the routine as C, issuing an order, proof), "`$6a3a` / `$6ac6` / `$6b38` — the order executor" (with "The executor, proven"), "The player's commands" (panels, minimap, icon floor, "What each order does", "The order senders and arrival executors, proven").
- Per-tick accounting: "`$d322` + `$3e06`", "`$127e6` — the sound-event dispatcher".
- Mechanics: "Combat", "RNG and determinism", "What actually fired, and what didn't".
- Lands: "Mission / world setup" (including "The starting armies" and "The world build, proven"), "How a land ends", "Diplomacy", "The campaign", "What `$1abaa` actually is".
- Synthesis: "The AI as modern pseudocode", "What's crude, and what a modern version changes".
- Names and audits: "Original names: the developer symbol table", "The game's own text: names for the fields", "Hidden features audit".
- "Open threads".

## Where it runs — the sim tick `$13000`, disassembled

`$13000` **is** the simulation tick. The routine as it reads, with its measured cadence:

```
$13000  ...clamp $4bb3a/$4bb3c (camera bounds)...
$13026  tst.w $57ff2 ; bne $13058        ; PAUSED -> skip the AI + accounting block
$1302e  addq.l #1,$2df70                 ; sim clock ++
$13034  addq.l #1,$4bb3e                 ; master tick ++
$1303a  tst.l 46($14e20) ; beq $13058    ; no running game -> skip
$13040  jsr $127e6   ; sound-event dispatcher (original _do_soun...): plays the 2 highest-priority pending sounds
$13046  jsr $6522    ; << the commander AI (order pipeline)
$1304c  jsr $d322    ; per-side troop totals -> $57fba
$13052  jsr $3e06    ; flag-health UI + the armies eat (food decay) + $57fba group term; also animals, pigeons, projectiles ($596a)
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
$130ce  jsr $7a56    ; dialog / info-panel renderer (the four `$7a36` slots, via `$8838`)
$130d4  $ff9a += $12f56 ; ...andi #$3f... clr $12f56 when it wraps  ; AUTO-ROTATE hook
$130f6  jsr $d23a    ; $57fba -> $57fce force ratio (0..4; 4 = victory at $d2c8)
$130fc  jsr $7202 ; text panels, then the minimap / compass / captain boxes / icon floor ("The player's commands")
```

**Where the calls sit.** The AI calls are not one "tail" block. `$6522`, `$d322` and `$3e06`
run near the *top* of the tick (right after the pause + running gates);
`$14b62` and `$6a3a` run near the *bottom*, after the renderers. Only `$1870`,
`$12ce0`, `$178ae` and `$f898` sit behind the `$57ff0`/`$57fee` subdivision
gate; everything else (`$6522`, `$14b62`, `$6a3a`, `$1abaa`, `$165b2`,
`$7a56`) runs on **every** `$13000` call. The `$57ff0`/`$57fee` counter is the
*present-rate* divider (how often the frame is pushed to the shifter and the
terrain re-rastered), not a sim-rate divider; at normal game speed `$57fee`
observed at 1, so it reloads every tick and the two rates coincide.

**Auto-rotate.** `$130d4` unconditionally adds `$12f56` to the camera rotation
`$ff9a` every tick. `$12f56` is normally 0; it is set non-zero by the
"rotate the view" mouse command so a rotation glides over several ticks rather
than snapping. It is the tick's reader of `$ff9a`; the writers (keys, compass, mouse) are in
`graphics.md` "In-game camera control".

### Measured cadence

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

#### Serial-link states (6 and 8)

State 2 is a local human, state 4 an AI side. State 6 is a human whose
orders are mirrored to a peer: `$6a9e` calls `$1c390` to write the slot's first 4 bytes (commander, order,
parameter) to the MFP USART data register (`$fffffa2f`), then executes the order. State 8 is the remote
human: `$6ab2` calls `$1c340` to read 4 bytes from the receive ring buffer `$58368` into the slot
(read index word `$58368`, write index word `$5836a` advanced by the receive interrupt, wrap limit word `$58372`, baud code `$5836e` = 1200 here, data from `$58374`), then executes them. Both loops spin
until the byte moves, so a slot in state 6 or 8 with no peer stops the whole game. The aborts differ:
the receive loop (`$1c34e`) leaves on ESC alone (`$2de6d`); the send loop (`$1c39e`) needs ESC plus a
non-zero `$2dea2` or `$2de96`, the key-array cells of the right and left shift scancodes `$36`/`$2a`.
The key ISR (`$1962`) never stores those two scancodes in the array (it only sets and clears the shift
flag `$2df8a` and returns), so the send-side abort cannot fire from the keyboard. Abort calls the
link teardown `$71ae`: it flushes the receive ring (`$1c328` clears both indices), calls `$c3f6` (the "Multi Player Game is now ended returning to Single Player." notice dialog, template `$c412`, no id word set; code read, never run live) and demotes each slot
(0 stays 0, 2 stays 2, 6 becomes 2, everything else including 8 becomes 4), so a remote human falls
back to an AI side and the game continues. Proven on `pm123/win/m1_s0.snap` with the slot states
poked (`scratchpad/pm132/`, "Startup command line" in "Hidden features audit"): the state-6 send loop
entered once from `$6a9e` and spun 571,668 times in 3M steps; the state-8 receive loop spun 122,257
times in 1M steps, ESC reached `$71ae` 41 steps later (1/1), slot 2 went 8 to 4 and `$6a3a` ran 11 more
times in the next 3M steps. The spin in state 6 is the emulator's MFP never setting the transmitter-empty
bit that `btst #7,44(A1)` (`$fffffa2d`) polls; there is no peer to test the protocol against.
The emulator's MFP is a plain byte array (no USART, no TBE/RBF interrupts), so the first real `$1c390` call spins at `$1c39e` for good (live: PC `$1c39e` after 2M steps, `$1c390` 1 hit).

#### The link handshake `$6eb6`

`$6eb6` (`_serial_`, to `$71ac`; `$71ae` is the separate teardown) is the whole connection set-up of the MULTI PLAY button. `$6a3a` runs it after the slot loop when `$71fe` is non-zero (order `$2c` sets it). `$7102`, the `dick` symbol, is not a routine but a label inside it (the `jsr $12e34` of the merge). Live from `m1_ready` with `$71fe` poked: `$6eb6` 1, `$12726` (stop sound) 1, `$12e10` (copy the own lord's name to `$58339`) 1, `$ba74` 1, and the login dialog is up (`$7a36` word 3 = `$c`). The protocol is symmetric: both machines run the same code, there is no master.

1. **Login dialog.** `$582f2 := $57ffe` (own side), flush the ring, zero the 712-byte buffer `$584c4`, `$ba74` opens panel `$c` (below), then `$cee6` is pumped until the dialog closes (`$cee6` returns Z when `$7a36` is 0). CANCEL leaves `$2df6c` at 0 and returns through `$71a2` (`$abcc`). CONNECT sets `$2df6c := 1` (live: the click gives `$7658` 1, then `$6f28` 1).
2. **Find the peer** (`$6f28`..). Each round bumps the try counter `$2df6c`, redraws the status dialog `$c1be`, pumps `$cee6` (closed dialog: abort) and sends the one byte `$71fc` (`'?'`, `$3f`) with `$1c390`. When `$71fd == '?'` the peer is found; otherwise, if the ring is non-empty (`$1c30a`), one received byte goes to `$71fd` (`$1c340`) and the round repeats. Live: after the CONNECT click `$c1be` 1, `$1c390` 1, `$2df6c` = 2 and the dialog id `$12` ("TRYING FOR CONNECT").
3. **Block exchange** (`$6f74`..). The status text changes to "Sending Game Info." (`$c1be` with `$71fd == '?'`), `$2df6c := 90`. The ring is flushed for 50 ticks of the long counter `$6f304`, then 50 ticks of plain delay (the tick source was not identified; code read). Then the 712-byte block `$580a0..$58367` (the setup block `$b2d4` saves into `$584c4`: seed, land numbers, side names, `$582f2` the own side word, `$582f4` five "Computer Is" flags) is exchanged in lockstep: send own byte i (`$1c390`), wait for the peer's byte i, store it at `$584c4 + i`; D2 sums the sent bytes, D3 the received ones (8-bit). Every 8th byte `$c1be`/`$cee6` redraw the dialog and `$2df6c` counts down; a closed dialog aborts to `$71a2`. Between redraws the loop just spins on the ring (so a cancel is noticed only on a redraw byte; inferred from the code, not run).
4. **Checksum.** D2 is sent as one byte and the peer's is read into `$71fd`; it must equal D3 (what was received). A mismatch sets `$71fd := $62` (`'b'`, message "Error, Try Again"), redraws until the dialog is closed, then restarts at `$6ed0`.
5. **Merge** (`$706c`..`$7198`). If the peer's side word equals the own side, `$71fd := $74` (`'t'`, "You Are Both <side>"), same wait and restart. Otherwise, for the five flag bytes at `$582f4`: own |= peer, the merged byte goes back into the received copy, and slot `$58016 + 6i` gets state 4 when the merged flag is non-zero, else 0. Then the own slot is set to 6 and the peer's slot to 8 (the serial states above; the pairing is by the side numbers in the two blocks), `$57ffe := $582f2`, `$12e34` restores the four default names from `$a29c` (D1 = `$3f` from the caller) and the own saved name from `$58339` goes into the own side's slot, the peer's saved name (from its block) into the peer's. **The lower side's block wins**: when the peer's side number is below the own one, the 64 name bytes of the merged table are patched into the received copy and the whole 712-byte copy replaces `$580a0..$58368`, so both machines build the same land from the same seed; otherwise the own block stays. Last: `$58034 := $58016 + 6*side`, `$2df84 := 0`, `$13d1a` (the land rebuild), `$71a2`.

Differential gate (`py/link/link_gate.py`): the real routine run in `m1_ready` with a scripted peer, because there is no USART: at every stop after the UDR write the script clears the busy flag `$5836c` and appends one peer byte to the ring. Four scenarios, all PASS: the sent stream is `'?'`, `'?'`, the 712 block bytes, the checksum (715 of 715 bytes, four times); peer side 2 against own 1 and own 2 against peer 1 (adopt) leave `$57ff0..$58367` identical to the Python model (0 differing bytes of 888); equal sides give `$71fd = $74` and a bad checksum `$71fd = $62`. Not run: the delays' real length, `$13d1a` after the merge, a cancel mid-exchange.

### `$51538` — group-order table

5 records of `$13c` (316) bytes, **one per side**. Header: long +0 =
pending-order flag (player/script channel), byte +1 = queued type, word +2 =
queued param. The rest is ~15 parallel **6-word arrays**, one word per
**group** (captain) of the side: group `k` (0..5) is the word at `base + n + 2k`,
and the group offset `D2` that the executor, the entity modes (`42(obj)`) and
`$57fd2` use is `side*$13c + $4c + 2k`, so a field at `x(A3)` of a group is the
array at `base + $4c + x`. The captain panel (`$9090`: `A3 - $51538` divided by
`$13c` gives side and `2k`) prints four of these arrays as Food, Troops and
aggression. The six entries are the side's six captains' groups ("What each order
does"), not objective slots. The
`$6564` AI loop sets `A1 = base + D7` with `D7 = 10, 8, ..., 0`, so `n(A1)` is
group `k = D7/2`'s word, walked from group 5 down to group 0 (the captain's):

| `n(A1)` | array span | meaning |
|---------|-----------|---------|
| `4(A1)`   | +4..+14   | slot-index / link, written back by `$6822` |
| `28(A1)`  | +28..+38  | the group's **owner side** (group `-48`; `<= 0`: no group, skip) |
| `52(A1)`  | +52..+62  | the group's **men** (group `-24`, captain panel "Troops") |
| `76(A1)`  | +76..+86  | the group **state** (group `0`: `$6` camp, `$9` invent, `$d` fighting; the game's names are in "The game's own text") |
| `112(A1)` | +112..+122| the group's **food** (group `36`, captain panel "Food"; eaten by `$3e06`, AI groups seeded `$5fff`) |
| `136(A1)` | +136..+146| the group's **posture** (group `60`: 2 Aggressive, 3 Neutral, 4 Passive; the second half of the captain panel's "Aggression" line; `$90fe`) |
| `148(A1)` | +148..+158| the group's **aggression** rank (group `72`: 0 PowerMonger .. 7 Wimp, the first half of that line; `$90de`; group 0 holds `$580a6[side].word12`, 7 in every land seen, the others `rng & word12`) |
| `256(A1)` | +256..+266| the tick the group went back to camp (state 6), stamped by `$3720`; `$6522` waits `$14` ticks after it |
| `268(A1)` | +268..+278| the group's **previous state**: `$3728` copies the state word into it as the group goes back to camp (live: state `$d` copied, state := 6, `256` := the tick, 1/1); `$6762` matches it against the table `$67d0` |
| `280(A1)` | +280..+290| campaign phase / sub-order |
| `292(A1)` | +292..+302| escort-target object offset |

The "execution sub-record" that `$4b80` writes (state at `base+$4c`, target link at `base+$64`)
is group 0's state word and its `24` target link (below).

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
/* +76*/  s16  state      [6];        // [0]   $6 camp, 2/3/5/8/9/$a/$c/$e/$f/$10 per order, $d fighting
/* +88*/  s16  eat_timer  [6];        // [12]  $3e06: counts to $580a6[side].word0 (doubled in state 6)
/* +100*/ s16  target     [6];        // [24]  target link: a lord, settlement or object ($3154, $68fe/$6762)
/* +112*/ s16  food       [6];        // [36]  captain panel "Food"; -= men/8+1 per eat tick; AI groups seeded $5fff
/* +136*/ s16  posture    [6];        // [60]  2/3/4 aggressive/neutral/passive; the AI writes it per decision (`$6522`: 2, 4, or the `$67d0` entry's posture)
/* +160*/ s16  carrying   [6][8];     // [84+12i] goods carried, i = pike..cannon (interleaved: stride 12 per item)
/* +256*/ s16  camp_since  [6];       // tick the group went back to camp ($3720); $6522 waits $14 ticks past it
/* +268*/ s16  prev_state  [6];       // the state before that ($3728); $6762 looks it up in the table $67d0
/* +280*/ s16  obj_camp_ph [6];       // campaign phase / sub-order
/* +292*/ s16  obj_escort  [6];       // escort-target object offset
          // ... $13c total
} pm_side_groups;
// $30fe returns  group.field_60 - 2  (posture - 2) as the kill/rout shift and the slice shift of every player order.
//   posture 4 (the AI stamps it on every attack group, $6638) -> always "2" -> rout, never kill.

// ---- leader / lord record : $4e514, 160 slots x 32 bytes ($4e514..$4f914; ~16 used, the rest zero) -------------------
// Full field list: economy.md §1 (pm_leader). The fields this file uses:
typedef struct pm_leader {
/* 0*/  u8   nation;                  // side id 1..5; 0 = empty slot (not a terminator: `$3bc8` walks all 160 slots to the array end $4f914); $550e rewrites it
/* 2*/  u16  chain_head;              // -> $4f916 first settlement of the lord (walk via +8)
/* 4*/  u16  cell;                    // packed {x: bits 0-5, y: bits 6-12} of the lord's position
/* 6*/  u16  food;                    // the lord's food store (the town's food, economy.md §1). $d322: += into $57fba[side].word2 ; $15e18/$15760: += 4 on arrival
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
/*20*/  u8   start_equip[4];          // $238c world build: 20/21 -> the side's first unit's byte 33 (tool tier) and 44 (weapon tier) ($244c/$2452; $245c then forces 44 := 6), 22/23 -> the followers' ($24fa/$2500)
/*24*/  u8   _b24[8];
} pm_assess;                          // sizeof $20; $2200-$3500 cluster owns the rest
// The word at +14 is the men per settlement that $2984 creates (economy.md 5a): 2 on every side of eight builds, so +15 is its low byte and
// overlaps rel[0] above; the layout of +14..+20 is not settled (rel[] may start at +16, which would make the +15+t reads one byte early).
// Also read: word 8 (word 8 + 4 is the herd-throttle reload, $5cde), word 12 (the RNG
// mask for a new group's 72(sub), $25d6). The whole block is part of the
// campaign table entry each land loads ("The campaign").
```

## The commander AI `$6522`

Outer loop over the 5 command slots. A slot with `4(A0) != 4` is skipped
(scan only). For `4(A0) == 4` ("engine has consumed the last order, ready for
the next"):

- **`$51538[cmd]` long +0 nonzero** → a **queued** order (player click, or a
  mission script): copy type→`1(A0)`, param→`2(A0)`, clear the flag, next slot.
  This is the player's order channel.

- **else `$6564`** — **synthesise** an order. Walk the side's 6 groups from group 5
  down to group 0 (`D7 = 10, 8, ..., 0`, `A1 = base + D7`). A group with `28() <= 0`
  (no group) or `4() != 0` (an order already pending: `$6822` sets it to `D7`;
  group 0's stays 0) is skipped. At most one order is issued per slot per tick. By
  the group's state `76()`:

  - state `$9`: decide (below);
  - state `$6` (camp): wait while `256() + $14 > $2df72` (signed), then **`$6762`**
    (the follow-up table, "The follow-up table" below); when it returns 1 the slot
    is done, otherwise decide;
  - any other state: **`$66e8`** (the target recheck, below); when it returns nonzero
    the slot is done.

  Decide, first match wins (`$65b4`):
  1. `52() < $16` (**fewer** than 22 men, signed: `cmpi.w #$16,52(A1); bge $65dc`
     skips it at 22 or more) → **`$69b4(8)`**
     scans `$4e514` for the best **own-side** lord that has more than one man in his
     `troops_field` (`cmp.b 5(A2),D0` skips every other side; the selector `D1` is
     the word offset read, 8 here and 6 for food) → posture `136()` := 2 and order
     **`$08`** (**get men**, group state 3) toward his town. The score is not
     a clean `(word << 3) / max(|dx|,|dy|)`: see "The lord scans". Live, `callcap $69b4` with the
     player's lead as `A2` on `m1_s0`: `D1 = 6` returned the player's own lord 2 (enemy lords 0 and 1, food 28 and 32, skipped),
     `D1 = 8` found nobody while lord 2's field troops were 0 and returned lord 2 once they were poked to 10
     (3/3, `scratchpad/pm133/cc69b4.cmds`).
  2. groups 1..5 (`D7 != 0`), when group 0 (`A3 = A1 − D7`) is in state `$d`
     with `280(A3) == 4` → posture := 2 and order **`$0c`** to **escort** group 0's
     `292(A3)` object. The packed parameter is `(word 10 & $ff00) | byte 8` of that
     record, i.e. `{y_hi, x_hi}`, where every other order packs `{x, y}` (`$67ee`,
     `$66e8`) and the `$0c` handler reads byte 2 as x: the escort target is transposed
     (the bytes are proven, 119 escort states; the handler's reading is a code read, so a
     transposed march is **inferred**). Natural: 2 hits in a 150M-step census of 29
     start snapshots.
  3. `52() - 4 > 0` (any group; this arm is the code at `$661a`, whose posture stamp is `$6638`) → **`$68fe(D1 = men − 4)`** scans
     `$4e514` for the nearest enemy leader whose men at home are below `men − 4` (cost
     weighted by the per-side assessment byte `16($580a6 + side*$20)`); **`$68ee`** scores it
     `(d/2)·((men−4)/8 + 1) + d/2` (word arithmetic, `d` the score `$68fe` returned); if
     `score <= 112()` (signed: the trip's food at the eating rate `men/8 + 1`, against the
     group's food) → posture `136()` := **4** and order
     **`$0c`** (→ group state 8 = march & engage) toward that leader's cell. If the score
     exceeds the food: **`$69b4(6)`** (own lord by food) → order **`$06`** (get food,
     no posture write), none → next group. `$68fe` reports "none" also, for a group in
     state `$d` or 8, when the best lord already is its target `100()`.
  4. no attack (men ≤ 4, or `$68fe` found none): **`$69b4(8)`** finds an own lord with men
     at home, then **`$68fe(D1 = men + that lord's troops_field)`** must find an enemy
     lord → posture := 2 and order **`$08`** toward the own lord.
  5. otherwise, for a group `D7 != 0` with men: posture := 2 and order **`$04`** with the
     parameter `D7 << 8` (this goes through `$6822`'s pending-record route: the slot
     gets `$22`, below); group 0 or an empty group: next group.

  Natural coverage (`py/cmdai/census.py`, `hits` over 150M steps from 29 start snapshots): arm 1's
  `$69b4` call (95; whether it found a lord is not counted), arm 2 (2 issues), arm 3's attack (77),
  `$6762` (179 issues) and `$66e8` (137 re-issues) occur; arm 3's food fallback, arms 4 and 5
  and `$6822`'s refusal never did (synthetic states only).
  The same census on the Play Random Land roll (59 start snapshots, 60M steps each, 3.5G steps, `PM_CENSUS_GLOB`) reaches the same arms more often (`$661a` 193, `$6762` 698, `$66e8` 64729)
  and again never reaches `$66a4` (the food fallback), `$664c`, `$668c` (the xfer fall-through, order `$04`) or `$6884` (`$6822`'s refusal): 0 hits each. The real code takes all but the last of them, and none can be reached by a run of any length that has been tried (`py/cmdai/arm_census.py`, `py/cmdai/arm_pokes.py`; the model's `_decide` on every AI group of 159 snapshots, then pokes on the real 68000 from `pm143/run/p0k0_s1.snap`):

- Only state 6 (after the wait and an empty follow-up table) or state 9 decides. In 159 snapshots 65 AI groups are deciding (39 attack, 26 get men); decided as a camped group, all 636 groups take arm 1, the escort (6 times) or the attack, never the three arms below.
- **Food fallback `$66a4`**: needs the march cost `$68ee` (about 450 for 40 men and a target 150 cells away) above the group's food. AI groups start at `$5fff` (`$26c4`) and `$3f6a` takes `men/8 + 1` a period, about 96 over 50M steps (24523, 24427, 24331, 24239 in four snapshots of one run), so the arm is about 12G steps away, sixty times the longest run. Live: food `112(A1)` := 0 at the decision point (17.7M steps into `p0k0_s1`) takes `$66a4`, `$66b0`, `$67ee`, `$6822` where the control takes `$6638`.
- **Transfer `$664c`, `$668c`**: a deciding group with `D7 != 0` and 1 to 4 men (or no enemy lord with fewer than `men - 4` at home), on a side where no lord has more than one man at home (else arm 1 or `$6680`'s get-men fires). Live: state := 9, men := 3 and the home troops of side 3's six lords := 0 reach `$664c`, `$6680`, `$668c`, `$6822` and leave order `$22`, parameter 4 in the slot with `4(A1) = 4` (the pending-record route); without the lord pokes arm 1 (`$65c8`) takes the group.
- **Refusal `$6884` cannot hold from any caller** (code read of the five `$6822` call sites, `$6610`, `$669a`, `$674a` and the two inside `$67ee`, and the goal table `$6888`, not a live miss). It refuses only when the group's state equals `$6888[type]`. The call sites issue `$0c` (goal 8, from state 6 or 9), `$04` (goal 0, which never refuses), `$02` from `$66e8` (goal 5; `$66e8` acts only for the states 2, 3, 8, 9, 10, 13, 14, 16, whose flag byte at `$6750 + state` is non-zero, and 5 is not among them), `$08` (3), `$06` (2), and the follow-up table's `$06`, `$08`, `$10`, `$0e` (goals 2, 3, 10, 9) from state 6. No goal is 6 and no deciding state is a goal of an order issued from it. The refusal itself stays gated by the synthetic states.

Order writes go through `$67ee` → `$6822`: `$67ee` re-packs the found leader's
cell `4(A3)` into `{x:6, y:7}` (`x << 8 | y`), `$6822` stores `{type, param}` into
`$58016[cmd]` bytes 1/2 or into the side's pending record (below).

**What the layer decides.** Apart from the follow-up chain of `$6762`, `$6522` has
no economy or build reasoning (*code read of the whole tree, proven arm by arm below*): its autonomous decisions
are "fetch men from an own lord", "escort", "march the army at the nearest enemy
leader, if I have more than ~4–22 men and my army has the food to get there" and "fetch food". AI groups start
with `$5fff` food (`$26c4`), so the food test never binds in practice ("Open threads"). Food is taken from towns at the entity level (mode `$1a`, `ai.md`).
Food, men, equipment and invention orders come in sequence from the follow-up table
below. The invention order does reach its arrival for an AI side (26 of 30 natural orders, "What an AI invention order does" below).

### The lord scans: `$68fe`, `$69b4`, `$68ee`

- `$68fe` (`closest_`): for every lord (`$4e514..$4f914`, 32 bytes; a nation byte 0 is
  **skipped**, the loop runs to the end) of another side than the lead `A2`'s
  whose men at home (word 8) are below `D1` (signed): `score = max(|dx|,|dy|) +
  (asr.b #2 of byte $580a6 + own*$20 + 15 + nation*$20 - 1)`; the lowest wins,
  ties go to the **later** lord (`cmp.w D6,D3; blt skip`). Returns `D3` (`$7fff` =
  none), `A3`, and Z for none (or, for state `$d`/8, for "already the target").
  **Proven** by `py/cmdai/gate_cmdai.py leaves`: 80/80 register sets (D3 and A3).
- `$69b4` (`closest_`): the lords of the lead's **own** side with the word at `D1` (6 food,
  8 men at home) above 1 (signed); the best is the **highest** `(word << 3) / dist`, a
  lord on the lead's own cell scoring `$7fff` and taken without comparison, ties to the
  later lord, none → `D3 = $ffff`. The divide is `divu D6,D0` on the whole longword
  and only the low word is reloaded per lord, so the **previous lord's remainder is in
  the high word of D0**: a lord's score is `((prev remainder << 16) | word << 3) / dist`; when
  that overflows 16 bits `divu` leaves D0 alone and the score is the raw `word << 3`.
  The first candidate is a clean quotient (D0's high word is 0 at every call site).
  **Proven** by `leaves`: 60/60 register sets, and the whole-call gate (a model with a
  clean quotient failed 10 of 84 fuzz states, with the remainder 0 of 84).
- `$68ee`: `D0 = D3 >> 1; D1 = ((D1 >> 3) + 1) * D0 + D0`, low word. **Proven** 40/40
  register sets (`leaves`, including 16-bit overflow of the product).

### The target recheck `$66e8`

For a group in a state other than 6 and 9, `$6750[state]` (a byte table indexed by the
state word; its first two bytes are `$66e8`'s own `rts`) selects tests on the group's
target `OBJ + 100()`:
bit 0 byte 0 (the nation of a lord) differs from the group's owner, bit 1 byte 0 equals
it, bit 2 word 8 (the men at home) is at most 1, bit 3 (state `$d`): posture := 2 when
`280() == 4`, and fires when `40()` (the first man) is 0. The masks: state 2 bit 0, state 3
bits 0 and 2, state 8 bit 1, state `$a` bit 0, state `$d` bit 3, states `$e` and `$10` bit 1,
the others none. A test that fires re-issues order **`$02`** toward the group's own lead
(`x_hi << 8 | y_hi` of the lead's record): a group whose target stopped being a suitable lord
is sent to its lead's cell (what `$3888` does with it is the order table's business; the
reading of the states is from the order-to-state table `$6888`, not from the UI). **Proven**: `py/cmdai/gate_cmdai.py leaves` 40 states (22 firing), and 137 natural re-issues in the census.

### The follow-up table `$6762` / `$67d0`

A group that has been in camp (state 6) for `$14` ticks gets its next order from `$6762`.
`$67d0` is a read-only table in the code segment of 6-byte entries `{previous
state, order type, posture}` ending at id 0:

| previous state (`268()`) | order | posture |
|---|---|---|
| `$d` (fighting), with `280() == 2` | `$06` get food | 4 |
| 2 (the state of order `$06`) | `$08` get men | 3 |
| 3 (get men) | `$10` equipment (`$6128`) | 2 |
| `$a` (equipment) | `$0e` (the bulb icon's order) | 0 → `($57fec & 3) + 2` |

`268()` is the state the group was in before it went back to camp (`$3728`, above), so
the table chains one finished order to the next: food, men, equipment, invention. The
target `OBJ + 100()` must have byte 0 equal to the group's owner (the nation of a lord);
the scan stops at the first id match, a failed test does not look further, and `$6762`
returns 1 even when `$6822` refused the order. **Proven**: `py/cmdai/gate_cmdai.py` (3 natural
follow-up states in the whole-call gate, 28 active synthetic leaf states). **Live**: `py/cmdai/campaign_census.py`, 34 natural
issues over 4 start snapshots, every one a table pair (`$d`→6 ×15, 2→8 ×9, 3→`$10` ×6, `$a`→`$e` ×4);
179 `$67b4` hits in the 29-snapshot census.

The routine as C (transcribed in `py/cmdai/cmdai_ref.py` `call_6762`, proven there):

```c
// A1 = side base + 2k (group k); table = $67d0, entries {prev_state, order, posture}, prev_state 0 ends
int pm_followup(group *A1) {
    for (e = table; e->prev_state != 0; e++) {
        if (e->prev_state != A1->prev_state_268) continue;          // the state the group came back to camp from
        if (e->prev_state == 0x0d && A1->phase_280 != 2) return 0;
        obj *t = &g_object_records[A1->target_100];                 // the group's target (a lord)
        if (t->byte0 != A1->owner_28_low_byte)       return 0;      // no longer the group's own nation: stop scanning
        A1->posture_136 = e->posture ? e->posture : (g_rng_bits_57fec & 3) + 2;
        pm_issue_at_cell_of(t, e->order);                           // -> $67ee -> $6822
        return 1;                                                   // even when $6822 refused
    }
    return 0;
}
```

The table is read-only data in the code segment (nothing writes it; it is a constant).
`268()` is the group's previous state, written by `$3728`, so the hook fires in ordinary play.

### What an AI invention order does

The chain's last link is the only one whose effect had not been followed. Live, one `$a` → `$0e` issue at a time (`capture_hits.py` on `$67b4`, then `watch` on the group's state `76(A1)` and the lead's mode byte `31(lead)`, `scratchpad/pm145/inv/`):

- `$6822` posts `$0e` into the side's slot; the executor `$6c48` runs it about 157k to 181k steps later (156,748, 175,881, 180,634, 174,401 in four issues) and its `$3154` (D3 = 9, D4 = `$22`) writes **group state 9** (`$3202`), stamps the lead's mode `$10` and previous mode `$22`, and aims the lead at the lord's cell (`$3218..$323a`).
- State 9 is a deciding state, and `$6522` runs about every 168k steps (`$6522` hits at 172,586 and 340,841 in the first issue), so a state-9 group is offered to the arms at the next pass with no wait. The lead walks to the cell centre (mode `$10`, ending in `$14fdc`, which writes the arrival mode `$22`); the arrival handler `$151a8` → `$5fa0` runs on the lead's next entity tick, so an uninterrupted order arrives 295k to 525k steps after `$6c48` (22 of 22 measured arrivals on the Play Random Land roll) and the state is held for two or three passes.
- **Outcome over 39 Play Random Land lands of 60M steps (`py/cmdai/invent_census.py`): 30 executed `$0e` orders, 26 reach `$5fa0`, 4 do not.** The four were replaced by a later order of the commander AI before the arrival tick: `$0c` three times (`k4`, `k5`, `k60`: `$6c32` at +209,719, +271,524, +190,622) and `$08` once (`k143`: `$6bea` at +185,771); each of those hits `$4b80` or `$3154` and rewrites the lead's mode and previous mode, so the pending `$22` never runs. On the preview-roll land 25 (`pm121/run/k25_s2`, `k25_s4`) all four natural orders were replaced that way (two `$0c`, two `$08`), because that land's AI group always had a target at the next pass. `$5cde` hits are not an invention count: the winter heartbeat `$157ba` calls it too (`k4` shows two with no `$5fa0`).
- The Play Random Land natural `$5fa0` states the order gate reads (`py/orders/gate_orders.py`, `nat/n5fa0_p0k*.json`) are these arrivals: all 26 have group state 9, previous state `$a` and a lead of side 2, 3 or 4 in mode `$22`, so every natural entry of `$5fa0` is an AI invention order. The arrival hands the lord's work order `$5cde` to the men, which does something only for a lord with a WorkShop (11 of the gate's 27 natural entries take that arm, `economy.md` 3). The chain stops here: `$67d0` has no entry for previous state 9, so an AI group that finished inventing stays in camp until the commander decides again.
- Why no snapshot ever showed a group in state 9 (159 snapshots, 0 groups): the state lasts about 0.3M to 0.5M steps and 30 orders in 2.3G steps cover about 0.5% of the time.

### `$6822`: issuing an order

`$6888[type]` (the word table under "The order executor") is the group state the order creates. A group already in it
refuses (D0 := 0), except group 0 with `$0c`. Otherwise `4(A1) := D7` and `D2 = side*$13c +
$4c + D7` is compared with `$58042[2*side]`: the side's own group (group 0 in every
snapshot) gets the order straight into the slot (byte 1 type, word 2 parameter); any other
group has the order written to the side's **record header** (`base + 1`, `base + 2`, the
queued-order bytes above, not the group's own entry) and the slot gets type `$22` with
parameter `D7`, which the executor hands to `$3ce8` (`$6d90`; code read). **Proven**
(`leaves`: 160 states, 666 changed bytes and the returned D0, 38 issuing). The refusal path is
synthetic only.

### Proof of the commander AI

`py/cmdai/gate_cmdai.py` (model `py/cmdai/cmdai_ref.py`, every changed byte of `callcap 6522`
against the model over RAM except the stack): **323/323 natural states** (298 `$6522` entries
of 35 lands at ticks 1, 2, 4, ..., 256 plus the 25 `$661a` captures of `scratchpad/pm122/dec`, 226 changed bytes: 7 queued,
29 attack, 5 re-issue, 3 follow-up) and **280/280 synthetic states** (seeded rewrites of the groups, lords and
slots: 3749 changed bytes, every arm above, the escort, fetch-men-behind-an-enemy, transfer, food
and refused arms among them), plus the leaf gates quoted above.

## `$6a3a` / `$6ac6` / `$6b38` — the order executor

Per tick, `$6a3a` dispatches command slots 1..4 on `byte4` through the table at
`$6a80` (states 2/4/6/8 → `$6ac6`; 6 and 8 additionally poke a UI effect via
`$1c390` / `$1c340`), **then clears `byte1`/`word2`**. `$6ac6` → `$6b38` reads
`byte1` (order type), clears it, and dispatches types below `$34` through the
table at `$6b5a` (`move.w 6(PC,D0.w)` at `$6b52`, `jmp 2(PC,D0.w)` at `$6b56`:
handler = `$6b5a + word[$6b5a + type]`). `$6ac6` runs `$6b38` at once for the commander's own group, but an order for any other captain's group travels by carrier pigeon (`$4562`) and
reaches `$6b38` when the pigeon lands (`ai.md` "Arrows and carrier pigeons"). Handlers read the slot as A0
(`0(A0)` commander, `2(A0)`/`3(A0)` target cell x/y) and the commander's group
offset as D2. Who posts each type is in "The player's commands" below.

| type | handler | calls | posted by |
|------|---------|-------|-----------|
| `$02` | `$6b8e` | `$3888(x,y)`, D6 = `$ea` | icon, targeted |
| `$04` | `$6ba8` | `$1c18(cmd,x,y)` | captain-select mode (icon `$04`, then a captain click); AI (`$6522`'s transfer arm: param `D7 << 8`, never natural) |
| `$06` | `$6bbe` | `$3154` D3=2 D4=`$1a`, then `$38ce` | icon, targeted; AI (`$6762` after state `$d`; `$69b4(6)` food fallback) |
| `$08` | `$6bea` | `$3154` D3=3 D4=`$1c`, then `$3248` | icon, targeted; AI (`$69b4(8)`, "get men"; `$6762` after get food) |
| `$0a` | `$6c16` | `$3c08` (regroup, the lead `-12(A3)`) | HOME icon |
| `$0c` | `$6c32` | `$4a7a(x,y)` → `$4b80` (group state 8) | sword icon, targeted; AI (`$68fe`) — **march & engage** |
| `$0e` | `$6c48` | `$3154` D3=9 D4=`$22` | bulb icon, targeted; AI (`$6762` after equipment) |
| `$10` | `$6c6a` | `$3154` D3=`$a` D4=`$6e`, then `$6128` | icon, targeted; AI (`$6762` after get men) |
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

The table base is `$6b5a`, not `$6b5c` (`$06` → `$6bec` and `$08` → `$6c18` would land
mid-instruction). Checked on the real CPU: 12 dispatches at `$6b56` over 6 handlers on
`pm121/run/k60_s2` all landed at `$6b5a + word` (`scratchpad/pm123/disp.txt`).

### The executor, proven

`$6a3a` walks slots 1..4 only (`$5801c..$58033`; slot 0 is never
dispatched), reads the state byte as an index into the word table at `$6a80` (offsets from
`$6a80`: 0 and `$a` do nothing, 2 and 4 `$6ac6`, 6 and 8 the serial write/read first, `$1c390` /
`$1c340`), clears the slot's type byte and parameter word afterwards, and after the loop
clears `$71fe` and runs the link handshake `$6eb6` when order `$2c` set it ("The link handshake `$6eb6`" under "Serial-link states").
`$6ac6` takes the slot's type `T`: 0 does nothing; a signed byte `>= $22` runs `$6b38` at once;
otherwise `$58042[2 * side]` (0: nothing), the group's sender word 48 (0: `$6b38` at once) and
the sender's cell against that of `OBJ + word[$51b5a]` (equal: `$6b38`; different: the pigeon
`$4562`, `ai.md`). `$6b38` clears the type byte, sends types `>= $34` to `$6eb0` (a bare exit),
and every handler leaves through `$6e6e`: when byte 0 of the slot is the local side `$57ffe` it
calls `$17a46` (role not read; with the word counter at `$12abe + 14 * ((group state + word -36)
mod 6)`, a code read), otherwise nothing (live: `$6e7e` reached 1/1 for the local side, 0/1 for
another).
- `py/cmdai/gate_exec.py` (model `call_6a3a` / `call_6ac6`, with `call_4562` from `pm_fsm_ref`, every
  changed byte of `callcap 6a3a`): **80/80 synthetic states, 2393/2393 bytes** (random slot states
  0/2/4/`$a`, sides, types, senders; routes: 90 pigeons, 30 no-`$58042`-entry, 36 empty) and
  **288 natural states, 157/157 bytes** (9 natural pigeon launches); a further 35 of the 323 natural states run a handler
  (`$3888`, `$4a7a`, ...), which is the orders area's and not compared.
- `py/cmdai/exec_census.py` (`hits` on 44 poked slots): routing 44/44 against the model and, for
  the 32 cases that run `$6b38`, **handler 32/32**: type `T` enters exactly the handler the table
  `$6b5a` names (the table above), with `$6eb0` as the common tail of `$6d90..$6e56`. Types 4 and `$2a`
  run wild with the poked parameter (the emulator stops with an exception) and were checked with `bp`.
- `py/cmdai/wrapper_check.py` (`bp` on the callee, 36 cases): `$6b8e` hands `$3888` D0.w, D1.w =
  x, y sign-extended and D6 = `$ea`; `$6ba8` hands `$1c18` D0.b = side, D1.b = x, D2.b = y; `$6bbe` /
  `$6bea` hand `$3154` D0, D1 = x, y (zero-extended), D5.b = side and D3/D4 = 2/`$1a` and 3/`$1c`,
  then `$38ce` / `$3248` when `$3154` returns zero (17 of 18 cases): **36/36** register sets.

`$6888` is a word table indexed by order type: `$02`→5, `$06`→2, `$08`→3,
`$0a`→7, `$0c`→8, `$0e`→9, `$10`→`$a`, `$1a`→`$c`, `$1c`→`$f`, `$1e`→`$10`,
the rest 0 (the table ends at `$1e`; its `$1e` entry, `$10`, is not the state the `$1e` handler sets, `$e`,
because the AI never posts `$1e` or `$20`; read from the code segment of `pm74_late.ram`). `$6822` (the AI's order write) compares the entry with the
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

## The player's commands

The player's orders do not go through the `$51538` queue: every UI path writes
the local side's command slot directly (`movea.l $58034,A0` then
`1(A0)` = type, `2(A0)`/`3(A0)` = target cell), and the executor consumes it on
the next tick. The tick's UI tail (`$130fc`) runs in this order, on the pointer
`$2df92`, the click position `$2df8e` and the click flags `$2df96`/`$2df98`. The level
bytes `$2df9c` (left) and `$2df9e` (right) stay set while a button is held. Items 2 to 6 are
consecutive sections of one function, the main per-tick loop `_again` `$12fd8` ... `bra $12fd8`
(`$13888`), not separate routines: `$1310e` (sym `do_the_m`) is the fall-through after `$7202`
returns zero (and `$3039` is not in D0), `$133ba` begins the captain boxes, `$134f4` the icon floor,
and `$1373c` is the per-tick tail (below). Position choice: with a left or right press pending
(`$2df96`/`$2df98`) the section tests the latched click `$2df8e`, otherwise the live pointer
`$2df92` (so a held button is acted on at the pointer's current position each tick):

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
   | `$c` | `$bb66` | `$ba74`, from `$6eb6` | "Multiplayer Login": a "Modem Message:" line (no hook), Baud Rate radios 300/1200/2400/4800/9600/19200 (word table `$bb5a`), "You Are" and "Computer Is" radios White/Blue/Red/Yellow. `$ba74` flips the radio glyph `$be,$b7` to selected `$ab,$bb` for the baud equal to `$5836e`, the side equal to `$582f2` and every non-zero flag of `$582f4`; default render 1200 and White (live, `m1_ready`). `$1ba` CONNECT (`$2df6c := 1`, live), `$1d6` CANCEL. The radio click handlers (what writes `$5836e`/`$582f2`/`$582f4`, whether `$1c3e6` is called) were not read |
   | `$e` | `$bfda` | main menu `$13de8`; the dialog is opened by `$bf5a` (`$7b10` + `$a91a` with the callback `$bf94`, which pads the name line to centre it; called from the menu loop `$13e18`; code read, 0 live hits because the snapshots are past it) | `$92`/`$da`/`$122`/`$16a` → `$2df6e := 2/4/6/8` (Start New / Continue Conquest / Play Random Land / Load Data Disk) |
   | `$10` | `$cd82` | disk requester | `$e2` OK, `$f6` CANCEL |
   | `$12` | `$c332` | `$c1be`, from `$6eb6` each round | "TRYING FOR CONNECT" status dialog with three `@` runs and a hook table at `$c1f8` (words `$6`, `$72`, `$80`): hook 0 the message chosen by `$71fd` (0 "Looking For Player", `'?'` "Sending Game Info.", `'b'` "Error, Try Again", `'t'` "You Are Both" plus the side name from the 7-byte table `$c2f5`), hook 1 the label "Try Number:" or "To Send:", hook 2 the counter `$2df6c` as a decimal (`$e39e`). `$68` CANCEL. Live: after CONNECT `$7a36` word 3 = `$12`, `$2df6c` = 2 |
   | `$14`/`$16` | `$d048` | SEND MESSAGE / `$d0dc` | none (a message line) |
   | `$18` | `$c512` | Start New Conquest with lands conquered | `$7a` YES clears **62** bytes of `$3f2a0` (the loop at `$7986` is `move.w #$c3,D0` then `neg.b D0`, which leaves the word `$003d`; live from `m1_win`: 240 bytes poked to 1, then Start New Conquest and YES left `$3f2a0..$3f2dd` zero and the rest untouched), not the 195 of the conquest map: a game bug, so a new conquest keeps the conquered flags of lands 62 and up, `$8a` NO |
   | `$1a` | `$c820` | `$c706`, from `$33b0`, when an envoy reaches a lord of the local side | `$146` YES → order `$2a`, param `$5809e` (only if that group's `-48(A3) != 0`, `192(A3) == $e` and its lead is on the local side); `$162` NO → `$32` |

2. **The minimap** (x < `$40`, 6 ≤ y < `$86`; cells 1:1, `(x, y−6)`). With a
   command armed (`$57fd4 != 0`), `$13892` draws the line from the selected
   captain's lead to the pointer, and a click posts `type = $57fd4`, target
   `(x, y−6)` (`$131be..$131cc`), but only if the target passes `$1394c` (below): `$13892`
   returns Z, and the click does nothing, when no captain is selected (`$57fd2 = 0`) or the
   cell is not a valid target for that order (live: `$0c` armed, click on an empty cell,
   `$13892`/`$1394c` once, `$1898e` 0 hits, `$57fd4` stays `$0c`). Without an order, a click
   recentres the view (`$4bb3a`/`$4bb3c`) and so does holding either button: the live-pointer
   branch (`$1311e`) sets the cell from the pointer every tick while `$2df9c`/`$2df9e` is
   non-zero, a drag (live, pm142/rand1: left held at (20,40) gives cell (20,34), then
   `mouse move 10 0` gives (30,34)). Clicks in the strip above the map (y < 6) set
   `$58098 := x/16` (`_show_ma`) and redraw the minimap (`$107d6`): mode 0 contour
   colours, 1 terrain with trees, buildings and bases marked, 2 terrain (the default),
   3 terrain with each lord's food margin as a dot (`graphics.md` "The minimap and the
   conquest map"; 16 of 16 renders pixel-exact).
3. **`$13212`**: four rectangles by the compass (`$13250`). The first two turn
   the view by ∓4 (`$ff9a`); one entry path (`$13270`, taken when `$2df96` is
   set) also sets the auto-rotate `$12f56` to ∓4, the other (`$13278`) clears
   it. The other two zoom through `$13f60`: `$57ffc` ∓1 clamped 1..7, or
   straight to 2 / 7 on the second path. The rectangles (x0,y0,x1,y1) are (24,155,32,161) rotate
   −4, (34,161,40,169) rotate +4, (45,159,61,174) zoom in, (45,178,61,193) zoom out. The first
   path is the **left click** (`$13362`, `$13374`, `$1338e`, `$133a0`; one step, plus the
   auto-rotate for the two rotate rectangles); the second is the **right button held**
   (`$2df9e`; `$13342`, `$13352`, `$13386`, `$1338a`), which repeats every tick: live, a held right
   button on the first rectangle gives `$13342` 6 hits in 6 ticks, `$ff9a` `$f0` to `$d8` and
   `$12f56` 0; a left click gives `$ff9a` −4 once and leaves `$12f56` = −4, so the view keeps
   turning; a held right button on the zoom-in rectangle sets `$57ffc` = 2.
4. **The compass rose** (x < `$20`, y > `$a7`): an 8-way camera pan
   (`$1420c` angle minus the yaw `$ff9a`, table `$132ca`; sectors are 32 angle units wide with a +8 bias, code read). Each handler moves
   the cell by one in the screen direction. A left click moves one cell; the right button held
   moves one cell per tick (live, yaw `$f0`: clicks at (18,172), (30,181), (18,195), (6,181) hit
   `$132da`, `$132f4`, `$1330e`, `$13328` once each; right held on the north point, `$132da` 6 hits
   and cell y 119 to 113). Only `$2df96` and `$2df9e` are tested here, so a held left button does
   not repeat.
5. **The captain boxes** (twelve rectangles at `$138ec`, each live only while
   the local side's `$51538` record has a non-zero word for it): the first six
   open the captain panel 2 (`$9036`, A3 = that captain's group). On the second
   six, the other button (`$2df98`) recentres the view on that group's lead;
   with the captain-select mode on (`$57fd6`, icon `$04`) a click posts order
   `$04` with the selected group (`$57fd2`) and the box index; otherwise it
   posts `$22`, param = box index. Code read only: no click on a box has been run. Rectangles
   `$138ec` (x0,y0,x1,y1): the first six (102,56,114,68) (157,49,169,61) (201,46,213,57)
   (237,49,249,61) (263,54,275,66) (306,62,318,74); the second six (65,21,118,86) (119,16,177,82)
   (178,10,232,78) (224,17,250,77) (250,19,281,92) (282,27,319,109).
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
   | `$2c` | `$c3` | (75,191) | – | `$136b2`: toggle `$57fea`, disarm `$57fd4`: the **examine tool**: while it is on, a click on a drawn sprite opens that record's info panel ("The game's own text", "How a panel opens") |
   | `$2e` | `$83` | (71,138) | – | `$13716`: options panel 4 (`$af6c`) |

   Arming the icon that is already armed disarms it (`$1898e`). Screen
   positions are centroids from the game's own hit-test
   (`reversing/powermonger/py/iconmap.py`); the sword `$0c` and the options
   `$2e` were clicked and behaved as listed, and every other order but `$04` and `$0a` was
   clicked ("What each order does", below). The glyph names are read
   off a rainy frame; the order names are the effects, with the manual's words
   where they fit.

**The order-target test `$1394c`** (sym `_check_l`; D7 = x<<16 | map row, `$57fd4` = the armed
order; returns D2 = 1 and D3 = 8 for a valid target, D2 = 0 and D3 = `$10` otherwise, and bumps
the counters `$12bc8` / `$12be4`). It reads the cell list `$47970[(row·64 + x)·2]`, a **signed**
word offset into the `$51b66` records (`adda.w` sign-extends, so offsets from `$8000` are
below the base), and follows each record's link word (+0) until a record passes. Per record,
with kind = byte 6, owner = byte 5, ally = the owner's bit in byte 6 of `$580a6 + side·$20`:
`$02` and `$1a` accept every cell (no lookup); `$1c` kind 2 or `$10`; `$06` kind `$2c`, or kind
2/`$10` with the ally bit; `$10` kind `$0a` or `$2c`, kind `$18` with byte 7 = `$10`, or kind 2/`$10`
with the ally bit; `$0c` owner not the local side and kind in {2, `$10`, 0, `$0e`, 8, 4}; `$08`
owner the local side and kind 2/`$10`, or kind 0/`$0e` with bits 6 and 4 of byte 7 clear; `$1e`
kind 2/`$10` with the ally bit clear; any other order (`$0e` invent, `$20` spy): kind 2/`$10`, with
owner = local side for `$0e` and owner ≠ local side otherwise. Gate: `py/input/validity.py`
callcaps `$1394c` for 10 orders over 61 cell classes of `pm142/rand1.snap`, 610 of 610 match
the transcription above.

**The tick tail `$1373c`**: when the sim clock `$2df70` differs from `$2df74` it clears both click
flags (`clr.l $2df96`); while name entry is on (`$d03e`) it calls `$cf46`; then the key rows
(`graphics.md` "Per-frame camera loop"), `$13864` (panels, fades) and the jump back to `$12fd8`.
On `pm142/rand1.snap` the loop runs every 187k steps (16 ticks in 3M idle steps).

**Driving it headless** (`reversing/powermonger/py/clicks.py`): the pointer
moves 1:1 with `mouse move` and clamps at 0, so home it with a large negative
move and click at absolute (x, y). Do not poke the live pointer `$2df92`/`$2df94`: the
IKBD `$0D` answer rewrites them every frame, so a poked position tests nothing (held-button
tests with a poked pointer matched no rectangle, the same tests with `mouse move` and
`mouse down r` did). To test a click without the settle, poke the latched click and the
pending flag instead (`w 2df8e <x><y>` and `w 2df96 00010000`), or hold a real button and
count `hits` (`py/input/seg.py`, `py/input/hold.py`). `reversing/powermonger/py/drive_win.sh`
plays mission 1 to a natural victory this way (next section, "How a land
ends").

### What each order does

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
| `$10` take equipment | `$3154` D3=`$a` D4=`$6e`; else `$6128` | own or allied town; else the first record on the cell of byte6 `$0a` (a dropped kit), `$2c` (a goods pile) or `$18` with byte7 `$10` | `$6e` (`$15740` → `$61f8`) | `goods >> shift` from the lord, handed to the men (`$6352`/`$638c`) |
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
- `$08` is **get men**, not besiege (the executor's own name in the developer symbols is `get_men`,
  "Original names"). Both of its target routines, `$3154` and `$3248`, take D5 = the commander's side and
  accept only a target of that side (`$3154`: `D5 > 0` branch; `$3248`: `cmp.b 5(A1),D5`, byte6 0). Live on `m1_s0`: the
  armed icon clicked on enemy lord 0's town (minimap `(22,51)`) posted nothing (`$57fd4` stayed `8`, 0 `$6bea`
  and 0 `$3154` hits in 60M steps); clicked on the own town (lord 2's field troops poked to 10 so the quota is
  non-zero) it ran `$15122` once and left the lead in mode `$28` (a 50-tick wait, then `$35f4` makes the camp),
  group state 3, 22 `$15264` entries in 6M steps. `callcap $34f2` (the summons `$15122` makes) on lord 0's town
  sends 4 men (object records 2, 3, 5, 7: target cell `20/22`, mode byte `31 := $10`, `30 := $14`) and on the
  player's own town none: its house chain holds no inhabitants in mission 1, so no join happens there
  (`$15282`, `$1b2a`, `$1d70` 0 hits). `scratchpad/pm133/o08*/cmds`, `cc34f2*.json`.
- **A man joins live (`py/join08_run.sh`).** `pm123/win/m1_ready.snap` is mission 1 after the natural
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

### The order senders and arrival executors, proven

The routines that start and finish the player's targeted orders are proven against the real 68000 by `py/orders/gate_orders.py` (models in `py/orders/orders_ref.py`,
which imports `tools/pm_fsm_ref.py`): every byte the real `callcap` changed against every byte the model changed over the whole of RAM except the stack and the screen
(`$78000..$7fcff`: `$17a46` redraws the selected group's panel icons, which the model leaves untracked), plus the returned registers. **61143/61143 over 2273 states, 0
mismatches**: the states are real groups of `m1_ready`, `k25_s4` and `k5_s4` with planted cell contents and poked fields, and 72 natural entries (player clicks from
`m1_s0` captured with `py/orders/nat_capture.sh`; `$600a`/`$35f4` from land runs on the preview roll; `$3248`, `$38ce`, `$6128` and `$5fa0` from Play Random Land lands, below). Per routine (states, bytes + registers, natural entries): `$3248` 52, 1793/1793, 10;
`$3888` 8, 916/916, 1; `$38ce` 9, 980/980, 2; `$390e` 8, 932/932, 1; `$3956` 36, 1195/1195, 1; `$39d4` 344, 1292/1292, 8; `$3bc8` 72, 216/216, 0; `$3da4` 15, 178/178, 1;
`$4a7a` 58, 5079/5079, 1; `$5fa0` 161, 21008/21008, 27; `$6128` 25, 1763/1763, 1; `$311a` 72, 65/65, 0; `$35f4` (with `$3744`) 57, 6505/6505, 1. `$600a`, `$60dc`, `$61f8`,
`$6352`, `$638c` and `$63f4` are in economy.md §2a/§2c.

`$3248`, `$38ce`, `$6128` and `$5fa0` have no natural entry from a player click (they are the fallbacks after `$3154`, and no click tried on an own man or empty ground reached them) and
none on the preview-roll lands, but the AI reaches them on the Play Random Land roll: a `hits` census over 59 start snapshots of 60M steps (`py/cmdai/census.py` with `PM_CENSUS_GLOB`: 39 freshly built lands plus the 20
stretch snapshots of five `runland.sh` runs) counts `$3154` 532, `$3248` 101 (83 of them on one land, seed 5), `$38ce` 3, `$6128` 1 and `$5fa0` 28 (counts overlap where a run snapshot follows its own land snapshot;
the preview-roll census of `$3154` and those four was not made, so "none" there means not looked for). `capture_hits.py` took natural entries of 23 lands into `nat/` (`$3248` 10 from three lands,
`$38ce` 2, `$6128` 1, `$5fa0` 26 from 21 lands): all pass the gate. `$38ce` and `$3248` are entered with return addresses `$6be6` and `$6c12`, `$6128` with `$6c92`, `$5fa0` with `$151b8`; 11 of the 27 natural `$5fa0` entries take the success arm and 16 the refusal, and 3 of the 10 `$3248` entries find a target.

All cell senders first call `$37c2` (detach the lead from its old group) and stamp the target into the lead as `x, $80, y, $80` (bytes 20..23); the arrival mode goes in byte 30
and `31 := $10` (advance).

| sender | group state | lead arrival mode | other effect |
|---|---|---|---|
| `$3888` (`_send_ca`, order `$02`) | 5 | `$1e` | `$1d70` re-routes the roster |
| `$38ce` (`_pickup_`, order `$06` fallback) | 2 | `$72` | |
| `$390e` (`_supply_`, order `$1a`) | `$c` | `$74` | `36(lead)` = y*64 + x |
| `$6128` (`_send_eq`, order `$10` fallback) | `$a` | `$6e` | `24(group)` = 2*cell; byte 21 = `$70` for a `$18` record, `$90` when cell control byte 1 or 65 (`$3f86c`) is set; `$1d70`; D0 = 1, or 0 and nothing changed when the cell holds none of the kinds below |

- **`$3248`** (`_send_ge`, order `$08` fallback): the first record on the cell's bucket chain with `5 == side`, byte6 0 and flag bit 6 clear (a man not in a group). The group goes to
  state 3 with `24(group)` = the cell, and the lead walks to the man's x/y in mode `$6c`. Nothing else matches (no man: it returns without a write). It does not exclude the lead
  itself, which is on its own cell's chain (**inferred**, not run).
- **`$6128` kinds**: byte6 `$0a` (a dropped kit, graphics/SPEC category 10), `$2c` (a goods pile) or `$18` with byte7 `$10` (a marker record; the arrival executor `$61f8` turns it into one boat).
  The first match on the chain wins.
- **`$4a7a`** (`_send_at`, order `$0c`) picks its target by scanning the cell's whole chain: a building (byte6 2 or `$10`) of another side ends the scan at once and the target is its
  leader's cell (`204(A3) := 2`); otherwise the **last** enemy man (byte6 0 or `$e`, owner > 0 and not ours) wins (`204 := 6`), else the last byte6 `8`/`$14`/`$16` record
  (`204 := 8`), else the last byte6 4 record, whose `10(rec)` is its cell (`204 := $c`); nothing: no change. `204(A3)` is the campaign phase array (`+280`). The group goes to state 8
  with `24(A3)` = the target's offset, the lead to mode `$30` heading for the target's x/y. Natural: sword icon on lord 0's town, `m1_s0`.
- **`$3bc8`** (`_get_lar...`): scans the 160 leader slots `$4e514..$4f914` (the slot test is byte0 == side, `$3bc8` does not stop at an empty slot). `A0` is the matching slot with the strictly
  largest signed word at `D3`, the first on a tie; while the best is 0 `A0` follows every match, so an all-zero side returns its last leader; no match: `A0 = 0`; it leaves `D4 = $20`.
- **`$3956`** (`_at_supp...`, mode `$74` arrival of order `$1a`): `$39d4` with `D7 = 1` (drop only the army's food, `D0` = posture - 2), then `$3bc8(side, 6)` (the own leader with the most
  food, wherever he is) becomes `24(A3)` and the lead's target (its cell, arrival mode `$1a`, take food; the return leg is in ai.md); no own leader: `$35f4`.
- **`$39d4` and the stale D5.** For `D7 = 1` the routine never clears D5 (the clear at `$3a6a` is in the goods half), so its "nothing to hand over" test (`$3abe`, D5 + shifted food == 0)
  uses whatever D5 the caller holds. With a stale D5 low word `<> 0` and `food >> shift == 0` it still creates an **empty `$2c` record** on an open cell (byte6 `$2c`, food 0, a free slot of
  `$4bb4e..$4bdee` used up). **Live**: at the natural entry of the drop-food icon `$12` (`m1_s0`, D5 = `$31009d`, D0 = 1) with the lead moved to a free cell and the army's food poked to 0
  or 1 the real call writes the empty record and the model with D5 = 0 does not (`nat_n39d4_1_open_food0/1`). The `$3956` caller held D5 low word 0 in its one sample, so there it did not
  fire; one sample each. Every other arm (a pile, a settlement, bit 5, no free slot, `D7` 0 or 2) is independent of D5.
- **`$3da4`** (`_at_spy`, mode `$7a` arrival of order `$20`): with `A0` = the settlement record named by `24(A3)` and `L` its leader: `L.troops_field += 1`; `24(A3) := 34(lead)`;
  the lead takes mode `$7e`, flags `|= $80`, `&= ~$10`, side `:= 5(A0)`, `34(lead) := A0 - $4f916`, `24(lead) := 10(A0)` and `10(A0) := lead` (head of the unit chain).
- **`$5fa0`** (`_start_i...`, mode `$22` arrival of order `$0e`): `24(A3)` is a leader record; if its side is not the lead's: `$35f4`. Else `$5cde(shift = posture - 2)` (the lord's work order,
  ai.md); refused (D2 = 0): `$35f4`; accepted: every roster man with owner > 0 gets mode D2, `46` = D3, `36` = D4 (and byte 39 := 4 when D4 = 0), the lead mode `$92`. `A5` at entry reaches
  `$5cde` (stored as the forest op when no herd op is found), so the gate runs A5 = 0 and a record address. The success arm needs a lord with a kind-7 building and is only synthetic
  (14 states); the natural entry (the player's single Tower) is the refusal.
- **`$311a`** (`_set_hat...`, "set hate": the original name) bumps the relation byte `16 + b` of `$580a6[a*$20]` by `D1`, clamped to 100, but **reads** `15 + b` (unsigned): 72/72.
- **`$35f4`/`$3744`**: the marker placement and its table-full, free-slot and evict arms are proven (57 direct states); the bucket-chain walk sign-extends the record offsets, so a building or effect
  slot (offset >= `$8000`, below `$51b66`) in the lead's cell blocks the marker. A model that reads them as `OBJ + d0` misjudges exactly those cells.

## `$d322` + `$3e06` → `$57fba` → `$d23a` → `$57fce`

`$57fba` = 5 × 4-byte per-side force totals, rebuilt from scratch every tick:

- **`$d322`** zeroes all five, then for each leader in `$4e514` (32-byte
  records) adds `+0 += 8(leader)`, `+2 += 6(leader)` (its two troop-count
  fields). It also walks the `$47970` buckets around each leader via the
  neighbour-offset ring `$d49e`, and where an enemy category-0 entity whose
  group is strong enough (`8(leader) >> 1 > -24(groupRecord)`) is in contact it
  calls `$4bc8` — troop-count / ownership reconciliation. That is bookkeeping,
  **not an order.**
- **`$3e06`** — more than a UI routine; besides what follows it also runs the forest animator `$4342`
  (`economy.md`), the animals and carrier pigeons and the projectile update `$596a` (`ai.md`). Its head is the
  flag-health indicator (health byte 45 of the selected group's lead,
  `divu #$14`, → `$58056`). Then it walks **every** side's 6 groups (A2 =
  side base + 2k): adds the group's men `52(A2)` into `$57fba[side].word0`, and
  **the army eats** (`$3f44..$3faa`): `88(A2)` counts ticks to
  `$580a6[side].word0` (twice that while the group is idle, state 6); then
  `food 112(A2) -= men/8 + 1` (`$3f6a`). At below zero the food is cleared and
  every man of the roster (`40(A2)`, next `26(man)`) leaves with chance 1/8
  (`$12c9a` LCG `& 7 == 0` → `$1b8c`, D1 = 0 in state `$d`, else 1): **a
  starving army deserts**. Observed: our 26-man group on mission 1,
  `watch $516e4` over 25M steps, 2 writes, both at `$3f6a`, 251 → 247 → 243
  (`26/8 + 1 = 4`). A big army eats fast; the AI's march test `$68ee` charges
  the same rate per cell of distance.

  **Driven live and proven.** From `m1_s0` (26 men, food 251), posture
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

`$6522` never reads `$57fce`; besides the fist indicator (`$16bb8`, called from `$d2be` and `$188e0`)
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

## `$127e6` — the sound-event dispatcher

The **sound-event dispatcher** (original `_do_soun...`). A min-of-2 selector over the table at `$1290c` (entry 0 is a sentinel, then 59 entries of 14 bytes: pending count word 0, cooldown long 2 (50 ticks), sound id word 6 = the entry's index,
channel word 8 or −1, priority word 10 (99, 9 or 7), flags word 12 `$a0`) picks the two best pending events, clears them, and `$1283c` hands each to `$1ba3e`, the sound player (`move.w 6(A1),-(A7)` = the sound id, `jsr $1ba3e` at `$128d2`),
unless the same id is already playing on the channel. **The renderer posts the events**: the sprite preparers of `$115e0` add one to word 0 of an entry (the man preparer at `$11d2c` does `addi.w #1,$129d0` for a man whose mode byte 31 is 6 and indexes the table by class for mode `$46`; `$129fa`, `$12a16`, `$12a6a`, `$12a78`, `$12b3c`,
`$12b58`, `$12bf2`, `$12c2a` are word 0 of entries 17, 19, 25, 26, 40, 42, 53 and 57, counting the sentinel as entry 0, bumped by the other preparers; the pigeon preparers `a_pigeon`/`a_flight` raise `$12a78`/`$12b58`), so only drawn objects make a sound and the count is a number of visible objects, not a flag (live: `watch $129d0` over `pm123/win/m1_atk`, the only writer is `$11d34`, values 1, 2, 3 ...).
From `pm123/win/m1_atk` over 6M steps `$127e6` runs 24 times and one run reaches `$128d2` and `$1ba3e` (the other 23 find nothing pending). `$1ba3e` ignores its second argument and plays sequence id − 1; the driver is in `system.md`. It is not
an event-marker or "under attack" ticker feed, and not a decision routine.

## Combat

PowerMonger has no discrete battle resolver with odds and casualty rolls. Combat is a set
of loosely-coupled mechanisms, all running at the entity level in `ai.md`'s `$14b62` tick,
and the routine once suspected of being the resolver, `$5778`, is contact bookkeeping
(mechanism 2). The decisive mechanism is a **health grind ending in a rout** (mechanism 0;
the first real field fight traced fired `$5590` ten times, "Measured" below); the
wear-attrition path (mechanism 4) is a slow second channel that never fired in it. Rout,
not death, is what an AI attack produces.

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
    else kill = ((g_tick_rng + A1->anim_phase) & 2) != 0;   // bit 1 set: kill (btst #1 / beq $560a at $55ec)
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
4 passive; the player's three posture icons, "What each order does"). The AI stamps posture 4 on every group
it sends to attack (`$6638`), so `pm_30fe` returns `2` and the roll is pinned to
**rout**: ten routs, zero kills in the re-armed fight. Posture 2 always kills;
posture 3 rolls (the player's mission-1 army: 5 kills, 5 routs in the win run,
`scratchpad/pm124/conquest/REPORT.md`); an encircled loser (`flags.bit5`) is
killed whatever the posture.

### 1. Contact → engage (`$56a6`, from mode `$32`)

`$15302` (an entity reached the record it was chasing, `48(A1)`) snaps to the
target's cell, sets both mode bytes to `$32`, and if the target is "engageable"
(`s8(31(target)) <= $2c` **or** `s8(30(target)) >= $3c`; signed byte tests, proven in `ai.md` for `$15302`)
calls **`$56a6`**:

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
    if (g->state == 6) {                          // In Camp
        obj *garr = &g_object_records[A3->link_46];
        if (garr in [$4cff8,$4d250)) garr->flags = 0x11;   // mark garrison "engaged"
    }
    if (g->state == 0x0d)                         // Fighting
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
`$4be00` (49 slots × `$10` bytes, `ai.md`):

```c
effect *pm_spawn_projectile(obj *shooter, int type /*D1*/, int tx, int ty) {
    effect *e = first slot with life==0;         // 14(slot); dbeq scan, counter $30 = 49 slots
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
`90/82/69/79/72/95`; every other index is `0` (index `$11`, which `$5778` stamps on an engaged garrison, reads the pad byte
after the table, also `0`; the next routine's code starts at index 18 and the enum only takes those six
values plus `$11`; table bytes read from `pm74_late.ram`). `$5778` stamps an engaged garrison's flags to `$11` → health cap `0`,
so it stops recovering health and is removed once `anim_wear` crosses `$3c`.

`anim_wear` (object byte 14) is only ever **incremented** — by the iterator's
animation-advance at `$14b9a`, roughly once per animation cycle for a
moving/animating unit — and **never reset** by any handler. It is a lifetime
counter: a unit that has been continuously active for ~`$3c` animation cycles
becomes attrition-vulnerable. This is why the wear path is a long-campaign
mechanic and fired **zero** times in the 276-tick re-armed fight.

`$5bd2` (removal) decrements the parent's strength — a **group follower**
(`flags & BIT6`) decrements the group's committed-force counter
`-24($51538+grp)` via `$1b8c`; a **garrison / lone unit** decrements its
leader's troop count `8($4e514 + 14($4f916 + 34(A1)))`. Then `$5c10` turns the
record into a 160-tick corpse (`byte5` negated, category `$c`).

### 5. Get men and rank re-forming — `$1d70`

The get-men modes (`$28`/`$2a`, `ai.md`; order `$08`) are not a siege: `$28` waits 50 ticks and `$2a` (`$15282`)
moves one recruit into the group, counts down the lead's quota and calls **`$1d70`** (`_rerank`) to re-form
the ranks (observed live, "What each order does"; settlement ownership is transferred elsewhere — `$25d6`/`$2644`, `economy.md`).

**`$1d70` proven (via `$3c08`'s bit-4 teardown, `ai.md`):** it is the
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

### Measured: the re-armed mission-1 fight

66M-instruction traced resume from `pm71_slot4.snap`, re-arming slot 1's
`byte4 := 4` every ~4M steps (16 pokes; `scratchpad/pm73_fight.evt`,
`trace_cfg.py --blocks`), ~276 sim ticks. (An earlier 40M-step / 166-tick run with a single poke,
`scratchpad/pm72_fight2.evt`, gave matching counts where they overlap.)

| routine | hits | reading |
|---------|-----:|---------|
| `$6522` decide | 276 | once/tick |
| `$661a` attack arm (decide arm 3) | **2** | re-arming `byte4` mostly does *not* re-trip it: after the first order the groups are skipped or go to the `$66e8` recheck (inferred). Only 2 autonomous attack decisions in 276 ticks |
| `$68fe` / `$68ee` | 2 / 2 | both decisions: food enough for the trip |
| `$15302` reached-enemy | 41 | men closing on enemy positions |
| `$56a6` engage | 9 | contacts made |
| `$5778` bookkeep | 2 | gated hard on `flags.bit6` + `d < $fff` |
| **`$5590` kill-or-rout** | **10** | first field-combat resolutions ever traced |
| — KILL (`$55f2`) | **0** | |
| — ROUT (`$560a`) | **10** | `$30fe` → `2` every time (`group.field_60 == 4`) |
| `$5bd2` wear removal | **0** | `anim_wear` never crossed `$3c` in 276 ticks |
| `$57f0` spawn projectile | 3 | |
| `$1d70` group route-expand (`_rerank`) | **15** | fires whenever a roster changes (a join `$15282`, an unlink `$1b8c`, a teardown `$37c2`); the re-rank step, not the ownership write |
| `$4bc8` contact reconcile | 1 | one nation-pair peace break |
| `$5c80` upkeep | 2136 | ~8 entities/tick |

**Reading.** A forced attack in mission 1 produces engagement, a handful of
projectiles, ten **routs** (units scattered by `$3c08`, none killed), and
fifteen **captures**. So territory changes hands and armies get broken up, but
almost nobody dies on the field — because the attack group's posture
(`field_60 == 4`, the AI's attack stamp) pins the `$5590` roll to "rout", and the wear channel is far
too slow for a 276-tick fight. A "no casualties" reading would be right
about deaths and wrong about outcome: **routing is what combat does here**, and
it fired ten times.

On later lands the same pipeline runs by itself (`ai.md` "Natural runs on later
lands"): over 200M steps each, lands 5, 60, 0 and 25 made 4-8 attack decisions (`$661a`,
each scored by `$68fe`/`$68ee`), killed 7-59 men through `$55f2`, and the enemy lords'
pigeons carried the orders. The `$5bd2` wear path still never fired. The 25 natural
decisions and their costs are in "Open threads".

## RNG and determinism

There are **three** "random" sources. The commander AI (`$6522`) and the combat roll draw
only low bits of a counter; the one genuine PRNG serves the world build and a few per-tick
rolls elsewhere.

- **`$57fec`** (`_season_`) — the count of `$1abaa` calls since the last season change:
  `addi.w #$1,$57fec` in `$1abc0`, once per `$13000` call, cleared when the season LCG
  wraps, so it runs 0..512 ("What `$1abaa` actually is"; the port's `Season.fading`
  reproduces the live tileset from steps = 16 × `$57fec`, `port/SPEC.md` §4). Every AI use
  takes low bits only: `& 1` (health recovery, `$5c80`), `& 3` (campaign sub-mode,
  `$6762`), `& 7` (a speech-line pick, `$3e06`/`$3f08`; the flapping-bird frame,
  `graphics.md`), `($57fec + anim_phase) & 2` (the kill/rout roll), `mod 6` (a porter's
  pickup kind, `economy.md` 2b). Because it is a counter that advances once per tick,
  **the commander AI and the combat roll are fully deterministic** given the tick number:
  no seeding, no entropy, and a save/restore at the same tick replays identically.
- **`$57ff6`** — a genuine 13-bit LCG, `x = (x * $24a1 + $24df) & $1fff`,
  stepped 16× per `$1abaa` call (`$1abc0`). It is the **pixel-order generator of the season tileset
  dissolve** (each step copies one pixel of the new season's art into the live tileset at `[$ff9e]+3712`; `scratchpad/pm136/season/tilediff.py`:
  half summer and half autumn art at count 255, 98% the new art at 496); full period 8192 = 512 calls, and its **wrap** to 0 rotates `$57fd0`, plays a season
  sound and nudges one `$4d252` tree record (see "What `$1abaa` actually is"). Never the AI or combat.
- **`$12c9a` / `$2df84`** (`_newrand`, `_seed`) — a 32-bit LCG (`state = state * $bb40e62d + …`,
  default seed `$bc614e`). The world build is its main user: `$10d1e` reseeds `$2df84` from
  `$580a0`, then draws map size / lord count / placement, which makes the generated map a
  pure deterministic function of `$580a0` (and of `$5809c`, "Mission / world setup"). In
  play it feeds a few rolls outside the commander AI: the starvation-desertion roll of
  `$3e06` (`& 7`, "`$d322` + `$3e06`") and a new captain group's aggression (`rng & word 12`,
  `$275c`); `ai.md` lists its other draws. The state is part of the RAM image, so a snapshot
  replays identically.

A modern reimplementation that wants PM's feel can keep the tick-counter trick
for the coarse AI jitter and add a real PRNG only where it wants
non-determinism (casualty rolls, if it makes combat a resolver).

## What actually fired, and what didn't

In "Between Pages 1-5" (`$57ffe` = player = side 1; enemy = side 2 with two
sub-leaders in `$4e514`), across a **250M-step** watched resume (~1000 sim
ticks) the only writes to `$58016`..`$58033` were `$6a3a`'s per-tick clear of
`byte1`/`word2`. **No command slot's `byte4` ever reached 4; no order was ever
issued.** The lone enemy captain stayed in its standing state (its group state is not recorded for this snapshot: the player's own group is in state 6 in 6 of 6 snapshots of
`py/group_states.py`, but the AI sides' first groups sit in state 3 or `$d` in the four builds counted under "The
starting armies", so a state-6 camp is not to be assumed) the whole
time. Mission 1 is a tutorial and its enemy AI is near-dormant.

The `$6564` path above was read statically and then **confirmed by force**:
poking `$58020` (slot 1 `byte4`) = 4, `$6522` took `$6564` → the attack arm
`$661a` → `$68fe` (picked the nearer enemy leader) → `$68ee` (food enough) →
`$67ee`/`$6822`, which wrote `{type $0c, cell $1d3e}` into the command buffer.
The next tick `$6a3a` → `$6ac6` → `$6b38` → `$6c4a` → `$3154` → `$4b80` set the
group's execution sub-record to state 8 and stamped the group lead into mode
`$10` with the target cell's centre world coordinates. The pipeline works end to
end; mission 1's enemy just never trips the "needs a new order" state on its
own.

Snapshots: `scratchpad/pm71_run1.snap` (settled, ~677M), `pm71_run2.snap`
(~927M, still quiet), `pm71_slot4.snap` (slot 1 forced to `byte4`=4, PC at
`$6522`). Traces: `scratchpad/pm72_sched.evt` (3M, cadence),
`scratchpad/pm72_fight2.evt` (40M from `pm71_slot4`, the forced fight).

## Mission / world setup

The briefing OK click (`$b814`, README) copies the saved game-state block
`$584c4..` over `$580a0..$58367` (`$b860`; it includes the world parameters at
`$58146`) and calls **`$13b9a`**, the world-build dispatcher:

```
$13b9a  ff9c := $15 ; jsr $fe04 (zoom index 4)      ; render geometry
        $51536 := $12                               ; settlement array live byte length (one 18-byte record: slot 0 is reserved)
        $57fd0 := (byte[$58146] & 3) * 2            ; tile-set / mode-$7c gate ($1abaa rotates it later)
        if ($580a0 != 0)       jsr $10d1e ; jsr $2266 / $ac20  ; re-roll the parameters from the seed
        elif ($58148 < $100)   jsr $df52(7) / $10a46 / $10410  ; fixed map from resource 7
        else                   jsr $ffa6 / $2266 / $ac20       ; stored parameters (mission 1)
        jsr $1073c / $10058 / $4672                   ; terrain init + scatter
        jsr $2984 / $238c / $2906                    ; the men (economy.md 5a), each side's base and army, each lord's nearest forest op
        ...
        $57fee := 1 ; $57ff0 := 1 ; ff9a := $fff0    ; speed = normal, camera reset
        rts   ($13ce6)
```

For mission 1 the saved block holds `$580a0 = 0` and the parameters `1e19 0750
0008 0023 0031 0004` (at `$5856a` in `pm67_ok_pre`; a write-watch on
`$58146` sees no write during `$13b9a`), so `$10d1e` is skipped and the map is
built from those stored parameters. `$580a0 = $45e` is the briefing *preview*:
`$b2dc` first copies the live block `$580a0..$58367` to `$584c4`, then picks a land index `k` from entropy, sets `$580a0 = k*$b + $3fb` and
`$5809c = k*$96 + $672`, and rolls a preview through `$b394 → $10d1e`
(`$45e` is `k = 9`). The OK path (`$b85a`) clears `$5809c` and copies `$584c4` back over `$580a0..`: the block of
*before* the preview, so the preview's map is discarded. `$5809c` is therefore non-zero only between a preview and its OK, and every
land the game really builds runs with `$5809c == 0` (`pm123/win/m1_s0` has it 0 after the OK, `pm67_ok_pre` has `$0bb8`).

Which builds reach `$10d1e` was counted live (`hits` from the end of the click; `scratchpad/pm142/`):

| route | `$13b9a` | `$10d1e` | `$5809c` | `$580a0` |
|---|---|---|---|---|
| mission 1, briefing OK (`pm67_ok_pre`, the click pokes) | yes | no (`tst.l $580a0` is 0) | 0 (`$b85a` ran) | 0, restored from `$584c4` |
| campaign pick of land 1 (`m1_map`, click (40,20)) | step 678 | 0 hits (`$4788` 927) | 0 | cleared by `$13ec6` |
| Play Random Land (`m1_win`, click (160,120) in 320-space) | `$13e8e` at 264686, `$13ece` 264689, `$13b9a` 265397 | 330184, branch A (side states 2, 0, 0, 0; `$4788` 810, `$111e2` 14) | 0 | `$f9abdbf1` (entropy OR `$71010101`) |

`$b85a` and `$b2dc` are not reached from Play Random Land. A settled real random land is `scratchpad/pm142/rand1.snap`
(size `$3ae1`, 4 lords, 263 tree records, 18 catch markers). The `build_land.sh` lands are the preview's rolls; `PAGES0=1`
(`build_land.sh`, `cap_land.sh`) builds the Play Random Land roll. The population model `call_2984` passes on both:
`gate_pop.py` 29860/29860 over 8 preview-roll lands and 41760/41760 over the same 8 with `$5809c = 0`
(`PM_POP_CORPUS=scratchpad/pm142/corpus_2984a`).

`$10d1e` is **not** a byte-script parser: it **reseeds the RNG from `$580a0`**
(`$10d22: move.l $580a0,$2df84`) and fills the parameter block from `$12c9a`
draws. `$12c9a` is a **32-bit LCG** (`state = state * $bb40e62d + …`, seed
`$bc614e` when zero), so a seeded map is a **deterministic function of
`$580a0`** (and `$5809c`). Poking both at `$13b9a` builds any of the 144 lands
for real (README "Driving a later land").

| addr | filled with (`$10d1e`, from its disassembly) | meaning |
|------|-------------|---------|
| `$58146` | 1st `$12c9a` draw | world RNG seed; `byte[$58146] & 3` picks the initial `$57fd0` |
| `$58148` | `$5809c` override (else `(2nd draw & $7fff) + $1500`) | map size; `< $2000` ⇒ "small" preset (`D1 := $a`, `D2 := 3`); the only builds that roll `$58148` run with `$5809c == 0` (Play Random Land, branch A below); the briefing preview and every `build_land.sh` land (without `PAGES0=1`) roll with it non-zero (branch C), so their sizes are `$672 + k*$96` (44 of the 144 are below `$2000`, "small") against `$1500..$94ff` for a real random land; an unseeded build (`$580a0 == 0`: mission 1's OK, every campaign pick) uses the stored `$58148` and never reaches `$10d1e` |
| `$5814a` | `(draw & 7) + (small ? $a : 2)` | lord count |
| `$5814c` / `$5814e` | `draw & $3f` / `draw & $7f` | seed cell coords |
| `$58150` | `(draw & 3) + 2 + (small ? $a : 2)` | settlement count knob |
| `$58152…` | a stream of 4-byte `{x, y, side, kind}` records built by `$111e2` + a loop: side 1 to 4, lord kind 1 to 5 (`$ac20`'s `d0` and radius, `$2eac`'s D1 and D4); start sites `{x, y, side, $10}` are appended | the "unit list"; see "The world build, proven" |

`$2266` then consumes the `$58152` stream: a record with `kind == $10` is a
**lord** — it writes `id` into `$58016[id].commander` and, if the slot isn't
already armed, sets `slot_state := 4`. **This is where the enemy command slots
are armed at mission start** (and why a fresh procedural mission's enemy has a
slot ready to issue orders, while mission 1's enemy never trips it, "What actually fired"). Records with `kind < $10` seed the
player start position; `kind == 0` ends the stream. `$2266` then appends
procedurally-placed settlements (`kind $10`, random cells `rand%$30+8`,
`rand%$70+8`). `$ac20` reads the same stream for the group start cells (`graphics.md` "`$ac20` — the land script").

Neither branch is a byte-script mission, and there is no mission-file grammar:
a campaign land is a stored parameter block from a fixed 195-entry table
(mission 1 is entry 0), and a random land re-rolls the parameters from a seed.
None of the 195 table entries has `$58148 < $100` (their range is
`$400..$7f20`; 67 are below `$2000`, the "small" preset), so the campaign never
takes the fixed-map `$df52(7)` branch; that branch is unreached by every route
found (campaign, random land, briefing preview).

### The starting armies (`$238c`, proven; counts checked)

`$238c` (the developers' `_setup_k...`, kings) runs once per build after `$2984`, for each side's group block of `$51538` whose word 100 holds a start cell (`$ac20` writes it from the `$58152` stream, `graphics.md`):
it makes the side's **Base** with `$2eac` (lord kind 6, a single Tower; `$10638` then levels its ground), a **leader** man (age 21, leader flag, health `$5f`, mode `$4c`) who becomes
the group's lead (`64(A3)`) and the first man put in the Base's chain, and `word[$580a6 + side*32 + 10]` **followers** (each `$2e1e`, pushed at the head of the Base's chain `10(settlement)`, so the leader ends as its tail; carried-item bytes from the side block's 20 to 23, joined to the group
with `$1b2a`, health `$5a`), then re-forms the ranks (`$1d70`). The group gets its food from the side block's word 4 (`$5fff` for a side whose command slot is in state 4, the AI sides, which also
carry a Boat), posture 3, aggression `word 12`, and the side's peace bit for itself; the local side's group becomes the selected group `$57fd2`. Finally every man of the side's *other* lords
who has the leader flag (the captains `$2984` made for lords of kind 4 and 5) is made the lead of a new group of his own through `$25d6` (Proven, `diff_revolt.py`), which is where the side's
groups 1 to 5 come from. Counted, 30 M steps after the build: the first group's men equal the side block's word 10 on every side that still has one (10 sides in four snapshots: 26, 12, 7, 8, 8, 8, 14, 13, 14, 8; the 26 is
mission 1's player), and that group is in state 6 "In Camp" for side 1 and 3 "Get Men" or 13 "Fighting" for the AI sides. Proven: `py/worldbuild/gate_build.py kings`, 44963/44963 bytes over 54 states (24 natural builds, 30 poked: every command state, another
local side, a sea Base, a full and a nearly full man table, full group slots), including `$2eac`, `$2e1e`, `$1b2a`, `$1d70`, `$25d6`, `$3c08`
and the levelling `$10638` (`maps_ref`); only the panel redraw `$187d8` writes (screen, icon buffer, a few UI words) are masked, its group
selection (`$3ce8`) is compared. `$238c` does not test `$2eac`'s result, so a Base cell on the sea leaves a consumed lord slot and
stale registers (poked case, matched).

### The world build, proven (`py/worldbuild/`)

`py/worldbuild/build_ref.py` models the routines of `$13b9a` that no earlier gate named; `py/worldbuild/gate_build.py` diffs each against the real
68000 (`callcap` from a snapshot stopped at the routine's entry in a build of 24 lands, `cap_land.sh`, plus labelled pokes), over all RAM
except the stack. Counts, bytes matched over states:

| routine | gate | matched |
|---|---|---|
| `$10d1e` `_make_wo` | `d1e` | 22501/22501 over 200 states (planes masked: `$ffa6` writes them) |
| `$4672` `_setup_f`, `$4788` `place_tr` | `forest` | 114947/114947 over 52 |
| `$2eac` `_set_tow` | `town`, `townnat` | 14631/14631 over 330 (returned D0, A0 too); 1516/1516 over 14 natural entries |
| `$1b2a` `_add_ran` | `addrank` | 996/996 over 210 |
| `$1cc4` `_derank` | `derank` | 4241/4241 over 48 |
| `$2906` `_setup_w` | `water` | 262/262 over 24 |
| `$238c` `_setup_k` | `kings` | 44963/44963 over 54 |
| `$1073c` | `towns` | 24433/24433 over 24 |

`$10d1e` (reseed from `$580a0`, parameters as in the table above), then after `$ffa6`, which reseeds the RNG from `$58146` and draws twice
per blob and leaves `$10410` to draw none, rolls `n + 1` sites, `n = rnd % 10 + (8 if $5809c == 0 else 4)`, each `{x = rnd % $2f + 8,
y = rnd % $70 + 8, side = rnd & 3 + 1, kind = rnd % 5 + 1}` (`$111e2` writes x and y), adds the kind's weight (`$111d2`: 1, 1, 5, 9, 17
for kinds 1 to 5) to `$111e0` and to the side's total `$111ca[side-1]`, and ends the stream with a zero longword. Then one of three branches,
chosen by the command-state byte of each side (`$5801c + 6*(side-1) + 4`):

- **B**, some side in state 6 or 8: the sites of a side in 6 or 8 are handed to the last side not in 6 or 8 (all four in 6 or 8: nothing more
  is written); one draw fills the scratch block `$580a6`; every side with a non-zero state gets a start site `{x, y, side, $10}` (plus the
  tail `{D3, $11, D2, $63}` when the last site's word is non-zero) and its `$580c6 + 32*(side-1)` block.
- **A**, no such side and `$5809c == 0` (Play Random Land, live: side states 2, 0, 0, 0 at the entry): each side's block from one draw, then sites move from the heaviest side to
  each side in turn until its weight is at least a quarter of the total (the first movable site of the heaviest side, last of equals, `kind < 6`),
  and a start group is added for side `i` when the **state of side 1** is non-zero or draw bit 1 is set. The test reads side 1's slot on all four
  iterations (`4(A3)` with `A3 = $5801c`; `D4*3` is computed and unused); proven by poked states with side 1 at 0 and the others set, and the reverse.
- **C**, no such side and `$5809c != 0` (briefing preview; `build_land.sh` without `PAGES0=1`): a start site for the local side `$57fff` (0 becomes 1), then four
  draws pick sides 1 to 4 and a side already served (the local side included) gets none; each of the four blocks is filled from one draw.

`$4672` and `$4788` are described in `economy.md` (trees, forest ops, markers); `$4788` plants with probability `1/divisor` per try over the
81 triples of `$488c` (centre first, divisors 2 at the centre to 6 at the edge, irregular), one try when `$5809c != 0` and two when it is 0, so
real random lands (and any other land built with `$5809c == 0`) have denser forests than the `build_land.sh` lands: with `PAGES0=1` land 60 has 304 tree records against 120, land 25 281 against 154; the gate runs both settings. Code reads, not reached by the gates: the
tree pool at `$12c0` and `$4672`'s `$57fb8 == $50` arm (stale `A4`).

`$2eac` takes the first lord slot with byte 5 zero (none: fail), adds `$20` to `$4f914`, and fails with the slot consumed when the four altitude
corners of the cell sum to zero (a Base or lord on the sea). Otherwise it fills the lord (byte 0 side, byte 1 kind, word 4 cell, word 6
`(1 << side) + $14`, word 14 the side block's word 24) and walks the kind's layout (`$3078` offsets to 3-byte `dx, dy, type` entries ending at `$9d`;
`py/town_layouts.py`): it skips an entry whose column leaves the map, whose cell index is `>= $2000` (a negative index passes, and `$16808`
then indexes the buckets with the sign-extended word), whose corners sum to zero, or, unless the kind is 6, whose bucket holds a settlement
(category 2 or `$10`); else it takes the first free settlement slot from slot 1 (none: fail), adds `$12` to `$51536`, sets bit 1 of the flag
plane on the four corners, chains it behind the lord (`2(lord)`, then `8(previous)`), sets owner, category 2 (category `$10` for building type 7),
type, cell and lord offset, and links it into the cell's bucket. It returns D0 = 1 or 0 and A0 = the lord slot.

`$1b2a` (man A1 joins the group of lead A0): a man of another side joins only if his home settlement (`34(A1)`) belongs to the lead's side, and
then changes side; the man is pushed at the head of the roster (`-36(group)`), the count `-24(group)` rises, his lead pointer `28(A1)` is set and
bit 6 of byte 7 raised. `$1cc4` (dismiss, from order `$14`) removes `count >> (posture - 2)` men, each time the roster man with the lowest signed
byte `44 + 33` (the last of equals); posture 2 dismisses everyone, 0 and 1 nobody (the shift count is taken modulo 64), and `$1d70` re-forms the
rest. `$2906` stores in word 22 of each lord that has an owner the offset into `$57f68` of the nearest op by `max(|dx|, |dy|)`, the first of equals
(0 when none).

## How a land ends

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

`$1a4da` is the victory screen (`py/season/victory_run.sh`): it loads
resource `$f` (`$1bd0e`), fades in, draws two text lines (`$19c12` "AFTER A GLORIOUS VICTORY
YOU MUST ...", `$19c36`), waits 2000 ticks of `$6f304` and fades out (`$1a2bc`
reached 392,357 steps after the `$1a4da` hit, then it sits in the wait at `$1a580`; the
rest is code read). When the verdict comes with `$2df6e == 4` and `$580a4 == $c2` (the last land) it
calls `$1a486` instead, which reaches `$1a648` (741,627 steps after the fade, with `$2df6e = 4` and
`$580a4 = $c2` poked), the finale animation (code read): resources `$c` and `$d` are drawn,
then 7 frames, each copying the 32000-byte screen (`$1a7a6`), patching it with the next record
list of a table A6 walks from `$3f768` ((offset, count - 1, longs); a negative offset ends a
frame; `$1a808`), waiting for the vblank flag, flipping (`$187a`) and pausing 2 ticks (30 on
frame 4); it ends with the text "AT LAST I RULE THE WORLD" (`$19c5a`, `$19c7e`) for 2000 ticks.
The delta table comes with the resource (zero in the snapshot) and is not decoded. A resumed
snapshot has no disk in drive A: without `disk scratchpad/powermonger.st` the resource load fails
and `$1bd0e` loops in its retry prompt (`$1bd30`, 481,567 steps after `$1a4da`).

**A natural defeat.** Land 60 run on from `pm121/run/k60_s4.snap` (where the
player's force total is already 0) dissolves the player's captain group
through `$2776` at step 94,725,510 (`A3 = $516c0`, side 1's sub-record 0, no
members left; `scratchpad/pm122/agents/dissolve/nat2/k60_x1.snap`). With no
input from there, `$d23a` posts `$2e` (+605,283 steps), `$6e10` +780,340,
`$d2c8` +780,343 with `word[$51690] = 0` and `$57fce = 0`, and the defeat
screen `$1a5b2` +781,229 (`scratchpad/pm122/end/k60_natloss.png`). The other
three run lands did not end in 300M steps.

**A natural victory.** Mission 1 (campaign land 0; player side 1
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
field conquest `$539a` (`$53f6` 1 hit, `$158cc` 0; lord 0's 10 men all
dead or routed; economy.md §3 "How a settlement changes hands", gate
`py/diff_4f68.py`). Snapshots `scratchpad/pm123/win/`.

*Rule: Proven from the code. Defeat observed both ways (retire and the natural
captain loss); victory observed naturally (mission 1, clicks only).*

## Diplomacy

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

**Forced-goods check** (`scratchpad/pm123/diplo/`, from `offer_a_end.snap`): the player's
envoy was dispatched with `w 5801c 011e2d15` toward side 3's settlement (45,21) on
land 60 and its lead's mode then set to `$76`. With no goods carried, `v = −2`: `$cada` and
`$35f4` run once and nothing is written. With one unit of goods 0, `v = 2`: `$3458` posts
`$2a` into side 3's slot, and the executor's `$34a8` writes `$5810c := $0a` and
`$580cc := $0a` (sides 3 and 1 allied), then `$c9f8`. Re-run: byte-identical `t2_end.snap`.
The unforced walk never arrived: after 180M steps the envoy touched side 3's men first,
which breaks the approach (next paragraph).

**Why an envoy rarely arrives.** Every unforced attempt against a garrisoned lord ended in
`$4c2a` (contact reconciliation, not diplomacy) before `$33b0` ran:

- *Land 25, fully organic (no pokes anywhere in the chain).* The side-1 captain group
  (8 men, `scratchpad/pm121/run/k25_s4.snap`) was sent with order `$10` to its own lord 7's
  town (24,21), a real `take equipment` click, and came back carrying 3 pots pulled from lord
  7's actual stockpile (confirming economy.md §2c: `$61f8`/`$6352` really fill a group's
  `carrying[]`/`supply_acc[]`, not just individual men's equipment). Still carrying them, the
  same group was sent with order `$1e` toward the nearest foreign lord (side 3's lord 4,
  capital at (28,14), 7 cells away). Within 13M steps it hit a hostile unit at (26,17),
  `$4c2a` fired, and the whole group was wiped out in the melee, its 3 pots dropped as a
  ground pile where it died (`scratchpad/pm127/diplo3/`).
- *An earlier snapshot does not help.* The same envoy with zero goods on the identical route
  from `pm121/k25.snap` (0 ticks) and `pm121/run/k25_s1.snap` (50M ticks) died at the same
  cell (31,13) in both runs: the death is a structural feature of the corridor (a garrison
  cluster of 18+ side-3 entities around the capital, confirmed by a spatial object-table
  scan), not something that accumulates over the land's runtime.
- *No escort can be built.* Land 25's side 1 has exactly one captain slot, always (censused
  across the whole `k25`/`k25b` corpus): there is no second group to send ahead, no player
  order grows a group or spawns a captain, and order `$04` (transfer) needs two captains.
  Land 5's apparent second and third captain slots are dead records: groups 1 and 2 are
  `owner 1` but `men 0` from the first snapshot (checked at the land's start, `pm121/k5.snap`,
  and 50M/100M ticks in, `pm121/run/k5_s1.snap`/`k5_s2.snap`, with
  `scratchpad/pm128a/census_groups.py`). An escort could not pre-position ahead of the
  envoy anyway: order `$0c` (march & engage) aimed at an empty cell never commits (`$57fd4`
  stays armed, the group never leaves home, tested at the death cell); it commits only
  against a cell holding something the game already tracks, such as a settlement (the same
  click against lord 4's town at (28,14) committed within 5M steps). Details, commands and
  snapshots: `scratchpad/pm128a/REPORT.md`, `scratchpad/pm128b/REPORT.md` (indexed in
  `ANCHORS.md`).

By the time a settled world has accumulated enough goods for a natural tribute, its territory
is also contested enough that an unescorted envoy rarely completes the walk to a garrisoned
lord. An envoy to a target that is not garrisoned needs no escort, as the next paragraph
shows.

**A natural alliance completes end to end (land 25, no pokes).**
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
`$02` waypoint and the tribute needs the second `$10`. An unescorted envoy
does not inevitably die to contact: the death is specific to a garrisoned target.

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
alliance posted `$1e` and ran to `$34a8` (`run9.cmds`), which is the unallied control.
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
  `$13b1e` (for `$1e`) one whose bit is clear. These three addresses are reads of `+6`,
  not per-tick writers of it.

Combat does not look at `+6`. Any contact between two sides' units runs
`$4bc8` → `$4c2a`, which clears both peace bits, calls `$c5ee` ("The alliance
between ... is broken") when the player is one of them, and applies a −8
relation delta both ways through `$311a`. Replaying the envoy run with the
1 ↔ 3 bits set, the first contact did exactly that (`$4c64`, `$4c7a`, `$c5ee`
1 hit each). An alliance with no contact persists (60M steps, bits unchanged).

**Who proposes.** Order `$1e` is posted only by the UI (`$131c4`, `$1365e`);
the AI's order writer `$6822` posts only `$02/$04/$06/$08/$0c/$22` and, from the follow-up table, `$0e/$10`. In 150M
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

## The campaign

The main menu's four buttons set `$2df6e` (`$78d2..$7908`): 2 Start New
Conquest, 4 Continue Conquest, 6 Play Random Land, 8 Load Data Disk. `$13e8e`
dispatches it:

- **2 / 4 → the conquest map `$1120e`**. Start New Conquest first asks for
  confirmation (`$c48e`) when any land is already conquered. Continue Conquest
  first calls `$aeac` (opens the FILE panel 6, LOAD/SAVE/FORMAT; code read) when the protection
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
land 1 is built. The FILE panel (panel 6, opened by `$aeac`) is the disk save
and load, and the 195 bytes are only the part of the save that the campaign
uses (code read: `$e288` and `$e29c` are `jsr` stubs to `$1bdfe` and `$1bd70`;
`callcap` could not complete either, `system.md` "The save-disk code"):
`D3 == $47` copies `$3f2a0` → `$3f768` (195 bytes, `$77a2`) and calls `$e288`,
which writes **198 sectors from `$3f768`, i.e. RAM `$3f768..$58368`**, to the
slot's sectors; `D3 == $17` calls `$e29c`, which reads those 198 sectors back
over `$3f768..$58368`, and then ORs the first 195 bytes into `$3f2a0`. Everything
above the first 195 bytes of that region (terrain, object array, link block) is
written and overwritten too; whether the game relies on that is not known.
`$b2dc`'s entropy pick of one of 144 lands (`k*$b + $3fb`) belongs to the
briefing preview ("Mission / world setup", README "Driving a later land"), not to the campaign;
Play Random Land sets `$580a0` itself (`$13ece`, above). The pick `$113a8` also ORs the first 196 bytes of
resource `$b` (loaded at `$3f364`) into `$3f2a0` (loop at `$113e4`, `moveq #61` plus `neg.b`; code read), which is
where any `< 0` "not selectable" flags would come from (inferred).

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
The dialog's two formatters (template `$b510`, table `$b472` = words `4`, `$5e`): `$b476` fills "Between Pages @@@@@" with `k = ((word $5809c - $5dc) / $96) >> 2` (land n gives `(n+1) >> 2`, `$5809c = n*$96 + $672`) and `D3 = (rand & 3) + 2`, printing `max(k-D3, -1) + 2` "-" `k-D3 + 7`, so the range is always 5 wide ("17-22") but its start moves with the random D3; `$b4d0` fills "How many @@@@@@ in this land ?" with the noun `$b4e6 + 4 + byte[$b4e6 + word $57ff8]`: Houses, People, Sheep, Trees. `$57ff8` is 0 or 1, so only Houses and People are asked; the table's other two nouns and the trailing "Boats" and "Birds" strings have no index entry (dead data). Gates (`py/ui/gate_between.py`): `$b476` **147/147** (all 144 lands' `$5809c`, three off-grid values, seed `$2df84` poked per case so D3 took 2, 3, 4 and 5), `$b4d0` **4/4**.
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
  (`$1ac5e..$1ac6a`, raw-verified). `$57fd0` is the season *and* the
  mode-`$7c` settlement-heartbeat gate (economy.md §3a), so this rotation is
  what makes the heartbeat + loyalty/revolt system **transiently active in
  mission 1** despite its seed giving `$57fd0 = 4` at world-build. Observed
  rate: always 512 calls per rotation, but the steps per call depend on the land: 118.44M steps per rotation in mission 1 (~231k per call, three writes watched), 85.7M on the Play Random Land snapshot `pm142/rand1.snap` (~167k per call; wraps at 85,853,129 and 84.7M steps in two runs, `py/season/season_run.sh`);
- clears `$57fec` (the call count since the last change, 0..512) / `$57ff6` and ends any weather (`$4bb42`/`$4bb44` := 0).

No population, food or invention maths anywhere in it.

Four details of the routine itself (`py/season/season_run.sh`, `spell_watch.sh`; the
counts are from `pm142/rand1.snap` with `$57ff6` poked to `$0681`, the one value whose
LCG successor is 0, so the first call wraps):

- **The entry gate is dead.** The first instructions add `word[$1ab9e]` to the phase
  word `$1aba0` and return if its high byte did not change. `$1ab90` sets `$1ab9e`
  and clears the phase; its only callers (`$1ab60` at world build, and the wrap)
  both pass `$100`, so the byte changes on every call and `$1abaa` never returns
  early. The byte equals `$57fec & $ff` (`$74` and 116 in `rand1.snap`) because both restart together.
- **The LCG has period 8192 including 0**, so a rotation is exactly 512 calls × 16
  steps (Python check, and 739 calls = 1 + 512 + 226 for two wraps in 125M steps).
  A wrap call stops at x = 0 without copying.
- **The wrap's four sound calls** (`$1acc8`, `$1acec`, `$1ad06`, `$1ad20`: `$1ba3e`
  with ids 0, `($57fd0 >> 1) + 1`, 0, `$a`, and `$58054 ^= 5` between them; 8 hits for 2 wraps).
  Id 0 stops the sound sequence (system.md "The sound driver is a sample player"), so only the last cue is
  probably audible *(inferred)*.
- **One weather spell per season.** `$1ad74` can start a spell only while
  `$4bb44 >= 0`; the wrap sets it to 0 and the spell's end leaves it at -1.
  `$4bb4a` is constant 0 (its only writer is the dead routine below), so the start
  is at `$57fec` = 160 (`$1ad74` at step 25,302,965 in two runs), `$4bb44 := ($57fec & $3f) + $20 = $40` and
  the spell draws 65 times (`$1ad40` 65, `$1ad4a` 1 at step 36,808,977;
  `watch 4bb44` shows `$40`, `$3f`, ..., 0, `$ffff`). Winter gets snow, spring and autumn
  rain, summer none (a summer start finds type 0 and retests on every call). Measured
  second-season spells ran 65 to 66 draws (not explained).
- **`$1aacc..$1ab5e` is dead code** with no sym label: 128 random cells per call of the colour planes
  (`$418ad`/`$438ee`) get their colour byte `$10..$23` or `$40..` recoloured by a level
  word `$4bb4c`, stepped by `$4bb48` on a 14-bit LCG (`$4bb4a`) wrap, probably a
  snow or greening overlay. No `bsr`/`jsr`/`jmp`/pointer reaches it
  (`find_ram_callers` 0, `find_literal_ptr` 0) and `hits` over 40M and 125M steps is 0.

## The AI as modern pseudocode

Everything above, decoupled from the 68000 and from the 2.6 Hz tick, as one loop. It
simplifies `$6522`: the follow-up table is tried first here (the real order is by group
state, "The commander AI `$6522`"), and the `$66e8` target recheck, the fetch-behind-an-enemy
and transfer arms and the food fallback are left out. With the entity modes of `ai.md` it is
the whole autonomous AI; there is nothing else.

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
            # 1. the follow-up table ($6762/$67d0): food -> men -> equipment -> invention, 20 ticks after each
            if obj.state == IDLE and world.clock >= obj.camp_since + 20:
                e = FOLLOWUP.get(obj.prev_state)       # $d (only with camp_phase == 2): GET_FOOD, posture 4; 2: GET_MEN, 3; 3: EQUIP, 2; $a: INVENT, 0
                if e and obj.target.nation == obj.owner_side:
                    obj.posture = e.posture or (world.rng_bits & 3) + 2
                    slot.emit(e.order, obj.target.cell); break
            if obj.state not in (IDLE, 9): continue
            # 2. a small group goes to its own best town for men ($69b4(8))
            if obj.men < 22:
                tgt = nearest_own_lord(obj, word=FIELD_TROOPS, weight=lambda L: L.troops_field)   # troops_field > 1
                if tgt: slot.emit(GET_MEN, tgt.cell); break     # order $08, group state 3
            # 3. escort the captain's group when it is in state $d (Fighting)
            g0 = group.groups[0]
            if k > 0 and g0.state == FIGHTING and g0.camp_phase == 4:
                slot.emit(MARCH, g0.escort_target.cell); break
            # 4. any group: march at the nearest enemy leader ($661a/$68fe/$68ee)
            if obj.men - 4 > 0:
                tgt = nearest_enemy_leader(obj,
                        weight=lambda L: assessment[side][L.side].out >> 2)
                if tgt:
                    d = dist(obj, tgt)                                       # $68ee: D1 = own men - 4 (kept through $68fe)
                    score = (d // 2) * ((obj.men - 4) // 8 + 1) + d // 2      # the trip's food at the eating rate
                    if score <= obj.food:                                    # enough food to get there
                        obj.posture = 4
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
        roll = attacker.group.posture - 2          # field_60 - 2
        kill = (roll == 0) or (roll not in (0,2) and (world.tick + attacker.phase) & 2 != 0)
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
   `max(|dx|,|dy|)` (weighted by a single relationship byte, read from the wrong place: "Diplomacy"); `$68ee` scores it
   only on raw distance × a coarse troop bucket. No terrain cost, no
   choke-point awareness, no "is this the *valuable* target", no coordination
   between a side's own groups. A modern version would run an **influence /
   threat map** and score targets on expected gain vs. expected loss, and let a
   side's groups deconflict (one besieges, one screens).

2. **No economy in the decision loop at all.** The AI never reasons about
   population or building; the only economic sequencing is the follow-up table
   (`$67d0`: food, men, equipment, invention orders chained 20 ticks apart, never planned). A modern
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
   runs in one thread at whatever rate a frame builds. Ticks land ~0.4 s apart
   (a camped group waits 20 of them, about 8 s, between orders) and combat resolves in ~1–4 health/tick. A modern port decouples the
   sim tick from the render, runs the AI on its own budget, and can afford
   per-frame steering while keeping the coarse "issue an order every few
   seconds" cadence that gives PM its feel.

5. **Deterministic tick-count "RNG".** `$57fec` is a counter that advances once per tick (reset every
   season fade, "RNG and determinism"), and the AI uses only its low bits, so the AI and combat replay
   identically from a save.
   Fine for the kill/rout roll's *flavour*, but it means no genuine uncertainty
   — a human learns the exact outcome of a given engagement. Keep the trick for
   cosmetic jitter; use a real seeded PRNG for anything the player can exploit.

6. **Rout, not attrition, decides the AI's fights — and rout is pinned.** The AI
   attacks at posture 4, which forces every kill into a rout, so its
   field combat almost never kills (the player chooses: aggressive kills); territory changes hands by **conquest** (`$539a` → `$550e`, economy.md §3) while
   armies just get scattered and re-form. A modern version would let the AI
   choose its posture from the situation so that its fights have consequences.

## Original names: the developer symbol table

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
`$4bdf0` (`_shots`; the effect slots start one record higher, at `$4be00`), `$4d252` (`_trees`), `$12d88` (`_command`, the startup parser), `$1962` (`its_a_ke`, the keyboard ISR's
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
- **`$4d252` is the tree array, not animals**: the labels are `_trees` (`$4d252`), `_forests` (`$57f68`), `_birds` (`$4c5f4`),
  `_do_fore...` (`$4342`), `at_fores...` (mode `$44`), `at_works` (`$42`), and the census agrees (203 of 203 live entries on byte6 4 tree
  records, none on byte6 8 animals, `py/tree_census.py`; 10M live steps: 28 `$3e`, 24 `$44`, 25 `$42`/`$60dc` hits, 0 `$5ec6`, 3 trees
  felled). The gather modes `$3e..$46`/`$6a` are run by men of every job, not shepherds (shepherds are `$80..$88`); economy.md §2.
- `$1d70` is `_rerank`: it re-forms a group's ranks on every join and roster change (live, "What each order does"), not a
  "send everyone home" step.
- **The farmer cycle is modes `$0c`/`$0e`/`$16`/`$18`/`$24`** (labels `start_fl...`, `in_fligh...`, `at_farme...`, `at_farme...`,
  `farmer_f...`; audit): `init_far` → walk `$10` → `$18` at the field cell (`42/43`) → `$0c` loads the `farm` entry of the
  spline table `$168ee` (`_flights`: `fp1..fp3`, `farm` at cursor `$50`, `pots` at `$76`, `eyes`) → `$0e` walks it (terminator `$7d26`
  = mode `$24`, walk home) → `$16` at home. Census: 275 of 281 live `$0e` men are farmers (11 snapshots); live from
  `m1_s0`, 40M steps: `$15042` 10, `$1507c` (the `food += 2`) 10, `$150b0` 11, `$14e56` 11, `$151c2` 11. So `$0e` is not a
  "patrol", `$18` not a "neutral garrison" and `$16` not a "disband"; `$2984` (`_set_peo...`) builds the village population, two men
  per settlement with a random job (`init_she/fis/far/mer`; one captain per lord of kind > 3), not garrisons (`economy.md` 5a, Proven).
  The farmer job is bit 0 of byte 7 (`$3c08` maps bits 0..3 to `$16`/`$4e`/`$5e`/`$80`), so the one site that sets flag
  bit 0 is `$2cd0`, inside `init_far` (`$2c5a`).
- **Mode `$68` is camp rest, not a marching column** (`rest_in_...`, `a_sitting`, `at_camp`, `in_camp`): 118 of 123 live `$68` men are
  byte6 14, the sitting category; marching men are `$06`/`$08`. `$35f4` (`_make_ca...`) is read to set group state 6 and ring the
  men around the lead in mode `$10`, prev `$20`, which settles into `$68` (static, one positive live match on `m1_ready`: the
  state-6 group's lead is `$68` at its camp marker). `$7c` is the winter state of a parked civilian (`in_winte...`), `$7e` a soldier
  staying at home, `$8a` a captain resting at his town (29 of 29 job 9).
- **Byte 33 is the tool tier** (an item code `2 * (slot + 1)`: 8 Plough, `$0a` Boat, `$0c` Pot; byte 44 holds the weapon codes 2 Pike, 4 Sword, 6 Bow, economy.md §4; modes `$02` and `$8c`
  are 71 of 71 and 17 of 17 with bit 5 set and 33 = `$0a`: `boating`, not "hold position"). Most men carry nothing (byte 33 `0`: 538 of 730 men over six snapshots,
  every local-side man but two); the `$0a` ones are the boat men, and the build puts the boat there: the side setup `$239e..$25c6` copies the mission table's bytes 20 and 22
  into byte 33 of the lead and the followers and, for a side whose command slot state `4(A5)` is 4 (an AI side), then writes `$0a` over it for the lead (`$2498`), each follower
  (`$250e`) and each flag-bit-4 record of the side's lord chains that `$25d6` accepts (`$2596`): on `k0` (preview roll) the three sites hit 2, 22 and 2 times in the build and the settled snapshot has 26 non-local men with
  33 = `$0a` (`scratchpad/pm145/b33/`; 0 local). So "byte 33 is `$0a` on every job" read off `equip_census.py` (which prints only non-zero values) is the AI sides' starting
  boat, not a tool every man holds; no live Plough has been seen (the Plough rule `$160f8` needs a lord with goods). **Byte 45 is health** (the captain
  panel prints `(45 >> 4) & 7` through `healthnames` at `$a2dc`, "Very Sickly" ... "Dead": 11 of 11 `callcap $912a` calls with a poked
  byte return the table's string, and 203 of 225 live persons sit exactly on their `$5ccc` cap, `py/health_check.py`;
  `$5c80` is `_add_str...`, which recovers it to the job's cap).
- **`$3f86c` is `_alts`, the altitude plane**, not a "control byte" or influence field: `$ffa6` (`_fill_al...`) accumulates a random
  walk into it, `$10410` (`_smooth_`) averages neighbours, `$10458` would lay the rivers (it has no direct caller and 0 hits in 20M steps, `graphics.md`); graphics.md already reads it as the height
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

## The game's own text: names for the fields

The UI text tables name the fields the panel code reads, so each name is the developers' word for what the byte means (code read at the selector, plus the live check noted). The text sits in `$9000..$b000`; a
selector returns a string pointer in A5.

| field | selector | the game's names |
|---|---|---|
| group state, `76(A3)` = `0(sub)` | `$90ca`, 9-byte entries from `$9497` | 1 Waiting, 2 Get Food, 3 Get Men, 4 Meeting, 5 Going To, 6 In Camp, 7 Go Home, 8 Attack, 9 Invent, 10 Equip, 11 Pickup, 12 Supply, 13 Fighting, 14 Alliance, 15 Trading, 16 Spying (0 blank). Seen in 5 snapshots: 3, 6, 7, 8, 13; 6 is the player's resting group, 3 and 8 the AI's "get men" and "march and engage". The captain panel's "Job:" row prints this state (`$9486`), not the man's job (12 of 12 panels) |
| lord kind, byte 1 of the `$4e514` record | `$9c80`, words at `$a128` | 1 Village, 2 Hamlet, 3 Town, 4 City, 5 Capital, 6 Base (the layouts of `economy.md` "Buildings and town layouts": a Village is a single FarmHouse, a Hamlet a single FishHut, a Town 5 buildings, a City 9, the Capital 17 round a Tower, a Base a single Tower, mission 1's own lord) |
| building kind, byte 7 of the `$4f916` record | `$9ccc`, words at `$a15a` | 0 TownHall .. 12 Mine (`economy.md`) |
| group posture, `136(A3)` | `$90fe`, from `$9580` | 2 Aggressive, 3 Neutral, 4 Passive (value minus 2) |
| group aggression, `148(A3)` | `$90de`, from `$9530` | 0 PowerMonger, 1 Bellicose, 2 Domineering, 3 Aggressive, 4 Firm, 5 Quite Firm, 6 Weak, 7 Wimp; the panel shows PowerMonger instead when the flag word `$9218` is set (`$9088` sets it on entry, `$90b2` clears it for any group whose `(A3 − $51538) mod $13c` is not 0, i.e. any group but the side's first). **Display only**: two writers, `$2446` (the side-army builder `$238c`: the first group gets word 12 of its `$580a6[32 × side]` block) and `$275c` (`rand & word 12`, every later captain group made by the restructure behind `$25d6`), and one reader, `$90de`, in a whole-image grep of `148(An)` and the sub-record view `72(sub)`; no AI test reads it (code read). Live: the player's first group holds 7 and its panel reads PowerMonger; poking 5 into it still reads PowerMonger (2 of 2 callcaps) while another group holding 7 reads Wimp |
| loyalty line | `$9116` | the captain panel's line is an unconditional `move.w #3,D0`: it always reads "trusting" (`$95c1`; `callcap $9116` on `m1_s0` and `k5_s4` returns A5 = `$95c1` both times). The lord's loyalty is shown on the **house panel**: its "Men: N who are <adjective>" line prints the lord's `loyalty_pressure` (word 14 of the `$4e514` record) as index `word / 75` capped at 7, a negative value giving 0: sycophantic, faithful, loyal, trusting, discontent, untrusting, tratorious, rebellious. A revolt fires at 600, so "rebellious" means 525 or more (house gate 103 of 103; the mapping for values the snapshots do not hold is a code read) |
| speed word | `$9d52` | `(byte16 >> 4) & 3`: 0 hardly, 1 slowly, 2 tirelessly, 3 endlessly (a march speed of 30 reads "slowly", 32 "tirelessly"); the captain panel's "Speed:" row prints byte 16 of the lead as a decimal instead (48 in `m1_s0`, 12 of 12 panels) |
| job | `$9d6e` | `jobnames` `$a200`: 0 soldier, 1 farmer, 2 merchant, 4 fisher, 8 shepherd, 9 leader (bit 4 of byte 7 forces 9) |
| health | `$912a`, `$9e2c` | `healthnames` `$a2dc`, `(byte45 >> 4) & 7`: Very Sickly, Sickly, Very Weak, Weak, Well, Fit, Strong, Very Strong; Dead for a negative owner byte ("Fit" is index 5, in every panel snapshot: "Is Fit", "Strength: Fit") |
| age class, byte 14 | `$a4ae`, words at `$a508` | `(age - 12) / 20` capped at 4: Tender, Young, Mature, Ripe, Great; byte 14 is the man's age in years (`$2e1e` starts every man at 12 to 43), shown as a number by `$a4d6` |
| carried item, byte 33 / 44 | `$9da8` | Nothing, a Pike, a Sword, a Bow, a Plough, a Boat, a Pot, a Catapult, a Cannon (`$a242`) |
| side names | `$9e04`, `$a4ee`, 16 bytes each from `$582f9` | side 1 is the name typed at "What Is Thy Name Oh Lord" ("dave" in `m1_s0`), sides 2 to 4 are Jayne III, Jos XVIII, Harold II (live in `m1_s0` and `k5_s4`); the four defaults are the data `_defplay` `$a29c` (4 × 16 bytes: "Philip II", "Jayne III", "Jos XVIII", "Harold II"), copied to `$582f9` by `_first_s` `$13d2e` (the name-entry screen, called once by `_display` `$12f5a`; code read: it opens the "What Is Thy Name Oh Lord" dialog `$bdc2`, template `$be34`, sets the typing flag `$d03e` and pumps `$7a56`/`$7202` until `$7a36` is 0), which then blanks side 1's slot; an entry left empty falls back to `startbla` `$13e6a` ("Mr X", "Master X", "Miss X", "Mrs X", chosen by `(word[$2df92] + word[$6f306]) & 3`; RETURN with the pointer at x = 0 gave "Mr X", 1 of 1 live), and "Philip II" comes back only through `_restore` `$12e34`'s 64-byte copy; the multi-player menu lists the four sides as White, Blue, Red, Yellow |

Other panels read the same way: the **house panel** (`$9ea1`: House, Town, People and Kingdom names, Food, Men "who are" a job, Near Forest, Stock), the **person panel** (`$a353`: name, rank and
kingdom, health, "lives in a <building> with <n>", job, the carried item, age and years old, "obeys <captain>"; the death line `$a50d` "has died at the Tender age of N, whilst faithfully in the service of ..."),
the mine panel (opener `$a5d8`, template `$a658`, table `$a5f4`: "This Mine belongs to the <Village/Hamlet/Town/City/Capital/Base> of <name> it produces metal that makes the <weapon>s"; all three fields come from the owning lord record `$4e514 + word 14` of the mine record: its kind byte 1 indexes `townname` `$a128` (minus 1), its word 4 seeds `_getname`, and its word 12 is the item offset into `$a242` (2 to `$10`, the weapon; the "s" is a template literal); gate **27/27**, `py/ui/gate_mine.py`: the three natural mines of the `pm143` series plus 24 states with kind, seed and item poked), the tree panel (`$a827`: A Stump, A Pine, An Oak, An Elm, An Ash, the season, "There are birds in the tree"), the animal panel
(`$a095`, selector `$9a12`: category 8 and the carcass category `$1c` read "Sheep", any other category "Cow": the animals of `ai.md` "Shepherds, animals and carrier pigeons" are sheep, and the category `$22` that their update loop also accepts is the cow, which nothing creates) and the pigeon panel ("Pigeon Flying to" a name).
Names of people, houses and towns are made by `$a9ce` (`_getname`, three syllables from `_start_w` `$aa5c`, `_mid_wor` `$aaa4` and `_end_wor` `$aaec`, table `$aa5b` `br ih ea pa rr op sc rv om br it o g fi ...`) from a seed word, so the same record always gets the same name
(`py/ui/gate_getname.py`: **80 of 80** seeds, string, length and the preserved seed `$2df84`, against `callcap $a9ce`). The seed depends on the panel: the person, equipment and death panels use `A3 − $51b66`; a non-first captain `64(A3)` (its lead man); a town (house, person and mine panels) word 4 of the lord record, his cell, so a town's name follows
its lord's position; the pigeon's destination `20(A3)`; a forest word 0 of its `$57f68` record. A side's lord, and the first group of a side, show the typed side name instead (`check_fo` `$a704` for men, the flag `$9218` for the captain panel). `_get_nam` `$bdc2` is not a generator: it opens the "What Is Thy Name Oh Lord" entry panel (template `$be34`)
for the side-1 name field `$582f9`, once, from `_first_s`.

**How a panel opens.** The `master*` symbols are templates, not builders: a `{width/4, height}` pair and a character grid with runs of `@` as placeholders (`masterca` `$921a`, `masterst` `$9712`, `mastereq` `$9878`, `masterob` `$9954`, `masteran` `$a082`, `masterpi` `$a0d4`, `masterho` `$9e76`, `masterpe` `$a328`, `mastertr` `$a7f8`).
An opener (`click_*`) does `lea template,A1 / jsr $7b10` (allocate a panel slot; the grid is built at `$7bac + slot × $320`) `/ lea fmt,A6 / jsr $a91a`, and in `$a91a` the n-th `@` run calls the routine at `A6 + word[n]`, which returns a string pointer in A5 or writes into A4 (the builder's exact rules are in "The panel builder `$a91a`" below). The info panels have no buttons (no `$80` corner cells) and `$7b10` clears their id word, so of the info panels only the captain panel (`$7a3c := 2`) has a nonzero id and none has button codes; the modal dialogs get their id (4 and up) from their opener `$affe` ("Panel slots and dialogs"). There are two ways in. The captain boxes (`$1343a`) call `_click_c` `$9036` (captain panel, `$7a3c := 2`). The **examine tool** (icon `$2c`, `$57fea = 1`) makes a click on a drawn sprite run `$95f6`: the hit test `check_sh` `$12138` runs with every sprite draw and, with `$57fea` set and a click pending, calls it, and it dispatches on the
record's category byte through the word table `cjt` `$9624`: 0, `$e`, `$1a` person (`$9c16`); 2 and `$10` house (`$9a38`, `$10` forced to WorkShop); 4 tree (`$a738`); 6 and `$18` object, fire and boat (`$98ec`); 8, `$1c`, `$22` animal (`$99e0`); `$a` equipment (`$9806`); `$c` death (`$a46c`); `$14` pigeon (`$99ac`); `$1e` mine (`$a5d8`);
`$2c` goods pile (`$9656`, "The goods-pile panel" below); `$12 $16 $20 $24 $26 $28 $2a` open nothing; `$2e`, the table's 24th word (`$9652`), goes to `$b2d4`. That is not a panel opener but the whole land set-up and briefing entry ("The land set-up `$b2d4`" below); no record of category `$2e` has ever been seen, so it is never reached (code read; `callcap $b2d4` cannot return, it stalls in a masked-interrupt wait at `$1ae46`). The table is indexed by the record's byte 6 (even values `$00..$2e`); none of the openers `$a738 $a46c $a5d8 $9656 $b2d4` has a direct caller (`find_ram_callers.py`: 0 hits each), the table is their only entry. Category `$18` is "Boat" in the game's own click text, and the sprite agrees: the record is a fisherman's catch marker (byte 7 `$10`) and `a_object` (`$117b0`) draws frame `$100 + byte 7 = $110`, a rowboat on the pond (`catch_marker_boats.png`; live `bp $1182a`, 30 of 30 marker records drew `$110`). Live from `m1_s0` (`py/ui/uiclick.py`, each with a no-toggle
and a toggle-only control): a Tower at (196,41) opens the house panel, an ash at (218,70) the tree panel ("An Ash in the forest of Mninise / It is Summer"), a man at (202,49) the person panel; without the toggle or without the click nothing opens (0 hits of `$95f6`; `info_click.png`). Gates against `callcap` with the model built from the pre-call RAM only:
person panel **247/247** (47 in `m1_s0`, 200 in `k5_s4`, all six text rows), house panel **103/103** (kind, town, people, kingdom, food, men and loyalty, near forest; the Stock rows are not compared), captain panel **12/12** groups (name, state, aggression and posture, loyalty, health, speed, food, troops, the carrying list; `py/ui/gate_panels.py`, `gate_captain.py`);
the equipment and mine panels were checked by their live text only. The person panel stores no sex: "he/she" is the parity of the man's place in his home settlement's chain (`$9ce8` sets `$9e74` to 0 or 4; a leader is always "he"), the companion shown is the next man, or the previous one for the first. The death panel's age class is `(byte14 − 12) / 20` capped at 4 and its "service of" line
prints the side of the *negated* owner byte. Never seen in 547 scanned snapshots: category `$22` (the Cow), `$1a`, a carcass (`$1c`, "DEAD Sheep"), tree state `$d` (a stump) and the camp fire (`$12`): those panel strings are reachable by the code and nothing produces them.
The panel text is the place to look first when a field's meaning is in doubt: the group-state and mode labels of "Original names", the "Strength" row and the building kinds all agree with it, and
it is what retired the "capital (kind 7)" reading.

**Panel slots and dialogs.** The info panels and the modal dialogs share one table of four 8-byte slots at `$7a36` (word 0 offset to the grid, word 1 packed origin, word 3 of slot 0 = `$7a3c` the dialog id). `$7b10` takes the first free slot; `$affe` is the dialog-slot opener (allocate, else evict a slot whose id word is below 4, then store the id from D7 in `$7a3c` and fill the grid with `$a91a`). `$7a56` draws every active slot and runs each tick (`$130ce`; the menu loops call it at `$cf12`, `$13d82`, `$13e24`: 6 hits per 300000 idle steps in the menu loop, 6 of 6 at `$cf12`). Per four grid cells it calls `$8838`, which composes four 4x6-pixel glyph cells into one 16-pixel, four-plane row group: each cell byte's low two bits pick one of four glyphs packed in a 16-bit word, the rest index a 12-byte, six-row group in the font at `$8976`; rows step 160 bytes and the blit is clipped at `$8834` (live: 53 calls in the first 28,000 steps of the id-`$18` dialog, before the YES click). The click side is `$7658` (README "Dialog buttons by id"); ten ids are dispatched, only id `$18` ("delete all of your conquered lands", `pm142/yes_dlg.snap`) has been clicked live: YES gives `$7658` 1, `$796e` 1, `$7a36` word 0 to 0 and `$3f2a0[0]` 1 to 0; NO gives `$7658` 1, `$796e` 1 and the menu loop reopens the id-`$e` dialog at once (`py/clicks_ui/dlg_click.sh`). The link dialogs do not go through `$affe`: `$ba74` (id `$c`), `$c1be` (id `$12`) and the notice `$c3f6` (`$abcc` to clear, `$7b10` to allocate, then `$a91a`; the first two store the id and the dialog origin in `$7a3c`, `$7a38`, `$7a39` themselves). `$cee6` (`_show_re`) is the one-frame pump of every modal loop that is not the main loop: it toggles `$4bb41` bit 0, runs `$1870`, the chat step `$cf46` when `$d03e` is non-zero, `$7a56` (draw), `$7202` (clicks), `$187a`, `$1a276`, clears the click words `$2df96`/`$2df98` and returns Z when `$7a36` is 0 (no dialog), so `jsr $cee6 / bne` means "wait until the dialog closes" (live: 2 hits per 2M steps with the login dialog open; code read for the rest).

**The panel builder `$a91a`** (`_make_re`). It copies the two header bytes, then each template byte to A4 until the NUL: a byte with bit 7 is remapped through the list at `$a99c` (24 codes, a NUL, then the 24 replacement bytes: `$e5 $b0 $a9 $e6 $df $f0 ...` to `$03 $01 $05 $02 $20 $02 ...`; the low two bits of a cell select a glyph, see `$8838`), and `$f0` is the right border cell (it maps to `$02`) that also pads (below). A `@` makes it call the next formatter (`A6 + word[n]`, n = the run's index). A formatter has two ways to answer. It can return a string pointer in A5: the builder copies one character per template `@` and stops at the run's width, so an over-long string is cut. Or it can write straight into the grid at A4 and add its length to A1 (so it consumes that many template bytes) with A5 = 0, which is what `$e39e` itoa users do (`$9684`, `$96ae`, `$b476`, `$a4d6`, `$b4be`): such text is **not** cut at the run's width, it eats the template's literal bytes after the run, so "-25536 Cannon" (13 characters in a 12-wide run) uses one of the following five spaces. The `@` cells a formatter leaves unused are not printed where they stand: the builder counts them (D6) and prints that many spaces only at the next `$f0`. Text followed by a literal in the middle of a row therefore closes up ("Town of Mycida it", the kind word's unused cells appear at the row's end), and in the goods-pile panel's last row the ornament after the run slides left as the text gets shorter. Gates: the goods-pile panel 99/99 and the mine panel 27/27 compare every interior cell of every row against a model of exactly these rules (code read plus the gates; `$a91a` saves and restores A4 around the call).

**The slot allocator `$7b10`.** It takes the first slot of the four at `$7a36` whose word 0 is 0 and returns D0 = 0 (Z) when all four are in use, in which case an info opener simply does nothing (code read; the dialog opener `$affe` evicts instead). The new panel is always slot 0: the old slot 0's words 0 to 3 are copied into the free slot, and slot 0 receives the new grid offset (the first of `$176 + k*$320` not named by any slot), word 4 = A3's offset from `$51b66` (the record the panel shows; for a dialog, whatever A3 held) and word 3 = 0 (the id; `$affe` and `_click_c` store theirs afterwards). Each further open also moves slot 0's y origin down by 6 (while below `$c8`), and the x origin is pulled left until x + width ≤ `$14`. Live: an examine click on a goods pile held for 300,000 steps opened the same pile twice (`$95f6` and `$7b10` 2 hits each: a held button acts on every tick, nothing de-duplicates by record), leaving slot 0 = grid `$0496`, slot 1 = grid `$0176`, both with word 4 = `$a03c` (= `$4bba2 - $51b66`).

**The goods-pile panel** (`$9656` `click_st`, cjt[`$2c`]; template `$9712` 20 × 12 cells "Stockpile of:", formatter table `$9672` = words `$12`, then `$3c` × 8). A `$2c` record is a pile of goods dropped by a group teardown (the block `$3a50..$3ae8`, code read: it moves `1/2^D0` of the group's food `36(A3)` and goods `84 + 12i(A3)` and a lead's Catapult/Cannon byte 44 into the pile, then `move.b #$2c,6(A0)` at `$3ac8` and registers it with `$16808`; economy.md 2c is the consumer). Its fields: word 10 the food, words 12 to 26 the eight goods in `$a242` order (Pike, Sword, Bow, Plough, Boat, Pot, Catapult, Cannon), words 8 and 28 not read by the panel. Row 2 is `$9684`: it zeroes the item cursor `$970a`, prints the signed food word and " food" (nothing when 0). Rows 3 to 10 are `$96ae`, one call per run: it advances the cursor past zero words to the next non-zero good and prints "<signed n> <name>" where the name is `$a242`'s string without its "a " article, with the final NUL replaced by `s`, or by a space when n ≤ 1 (signed compare); after the last good it returns an empty string. So the panel lists only the goods present, with no gaps, and the display is the whole effect (it changes only `$7a36`, the grid and `$970a`). Gate (`py/ui/gate_stockpile.py`, `callcap $9656` with the food and goods words poked over {0, 1, 2, 3, 10, 99, 300, 5450, 40000}, 10 states per pile plus the natural one, the three `pm143` snapshots with piles): **99/99** on all 18 interior cells of rows 2 to 10. Real click (`py/ui/click_pile.sh`, `vis_at.py` pokes the camera cell `$4bb3a` to bring a pile on screen: `p0k0_s4`, camera `(44,110)`, inspect icon then a click at `(105,69)` on pile `$4bba2`; 150,000-step `hits`): `$95f6 $7b10 $a91a $9656 $9684` 1 each, `$96ae` 15, `$e39e` 2, and the panel read "823 food / 14 Boats" for a pile holding food 823 and a Boat word of 14.

**Dialog openers (code read; none of these four was run by a hits count in this pass).** `$affe` takes the id in D7, the template in A1 and the formatter table in A6, calls `$7b10`, and on success stores D7 in `$7a3c` and runs `$a91a`; with no free slot it frees the first slot whose id word is below 4 (an info panel) and retries, and returns silently when all four hold dialogs. `$aeac` is the FILE panel: it first clears slot 0's word 0 (closing whatever was on top), sets the origin bytes `$7a38 = 8`, `$7a39 = $43`, opens id 6 with template `$b0ad` and table `$af06`, then marks the drive letter in `$e296` ('A' = `$41`) by turning the n-th `$1c` cell of the grid into `$1e`/`$1f`; its table `$af06` (words 4 and `$1e`) holds two formatters whose labels read "SAVE" (`$af3e`, run 1, the `$47` button) and "FORMAT" (`$af43`, run 2, the `$77` button) when `$14e4e == $2c` and blank (`$af4a`) otherwise, so a land that failed the protection check shows both buttons blank (for the save button the dispatcher's own `$14e4e` test, in the panel table above, agrees; whether `$77` tests it was not read). The `$77` button's label is therefore FORMAT, which names `$1ba72` as the disk-format entry (label only; the DISK pass covers the routine). `$af52` is the GAME panel: it clears slot 0 and opens id 8 with template `$b160` and no formatter table (the template has no `@`). `$af6c` is the options panel: it builds the game-speed slider by rewriting the template's `$14 .. $16` run from `$57fee`, then opens id 4 (template `$b03a`, table `$afd6`; one formatter prints a label when the local slot's byte 4 is 2); its "already open" test compares `4` with D0, which the preceding loop loads from slot word 0 (the grid offset), not word 3 (the id), so it may never fire; not tested.

**The land set-up `$b2d4`** (`_protect`, code read to `$b470`). It saves `$580a0..$58368` to `$584c4`, folds the shifter base-address registers `$ff8205/07/09`, `$2df92`, `$6f304`, `$12c9a` and `$2df84` into `$580a0`, reduces it mod `$90` to a land index n (`$5809c := n*$96 + $672`, the page number the briefing asks for; `$580a0 := n*$b + $3fb`), runs the land build (`$fe04 $10768 $10d1e $2266 $ac20 $1073c $10058 $4672 $2984 $238c $2906 $107d6 $b892 $13f60`), sets `$58792 := 3 + (rand & $f)`, picks the question bit `$57ff8`, zeroes `$14e4e` and opens the briefing dialog (id `$a`, template `$b510`). `$b892` (`_count_w`) in that chain writes five words at `$5878c..$58795`: the live-record counts of the lords (`$4e514`, 32-byte records, byte 0 non-zero), settlements (`$4f916`, 18 bytes, byte 5), objects (`$51b66`, 50 bytes, signed byte 5 > 0), the 20-byte records at `$4ccd6` (byte 5 non-zero and byte 7 `$11` or `$12`) and the tree array (`$4d252`, 12 bytes, word 10). Gate `py/link/gate_b892.py`: `callcap` on 25 snapshots against a Python count, 25 of 25 equal (9 distinct vectors, e.g. 3, 11, 42, 3, 203 on `m1_ready`). Role (**inferred**): they are the answers of the briefing's protection question, whose template `$b510` reads "How many @@@@@@ in this land ?" with a four-digit entry parsed by `$b940`, and whose OK handler `$b814` loads `$5878e` and `$57ff8` doubled (the listing from `$b82e` is only partly legible); the compare itself was not driven (no click reached `$b2d4` live). It is the "protection seed" of the earlier reading only in that last part; the routine is the whole entry of a new land.

## Hidden features audit

No cheat keys, debug commands or developer hooks found in the loaded game image. Evidence:

- **Keys.** The only code touching the key array `$2de6c` is the ISR writer (`$1962`), the camera loop `$13762`, the
  serial-link loops (`$1c34e`, `$1c39e..$1c3ae`) and the clear at `$10a6` (scan of the whole image for pointers into
  `$2de00..$2df6b`: 10 hits). There is no "any key" scan and no Ctrl/Alt/CapsLock/Help/Undo/F-key test; the only
  modifier state is the shift flag `$2df8a`, which only selects the shifted ASCII table in the getkey routine
  (`$19c2`, tables `$19e8`/`$1a7a`, UK layout). A live sweep of scancodes `$01..$72` (500,000-step holds in
  `pm78_settle`, reader hits counted with `hits`, RAM diffed against F1): only the four arrow keys change state
  (`$13824` block, each reader body 2 hits; left moved camera X 40 to 38, re-checked). ESC reaches the link
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
  CONNECT sets `$2df6c`; the handshake is "The link handshake `$6eb6`" under "Serial-link states"). With the static string neither role is set. Patching `$123c` in a running
  snapshot is useless (the routine runs once, before the game loads); to test a role, write the slot states.
- **Dormant word `$5809a`** (`_show_de...`, "Original names"; read at `$16640` in a loop over the entity table, written nowhere by an absolute
  operand; 0 in both snapshots). Poking it to 1 raised that loop's `$16738` calls from 54 to 94 per 500k steps and
  `$e6ee` marker draws from 27 to 47, and on 4 of 8 samples added 24-26 bytes of extra dots to the minimap: a
  "draw all sides' markers" switch. Nothing in the image sets it (static; no live write was attempted):
  the only absolute operand of `$5809a` is the read at `$16640`; a byte scan of the RAM image finds the longword
  `$0005809a` once (that read) and no pointer to `$58094..$58098` other than the six `$58098` word accesses; every
  bulk copy or clear that could sweep it starts higher (link/save blocks `$580a0..$58368` at `$6fa2`, `$7150`,
  `$b866`; the campaign pick `$1140e` copies `$14c` (332) bytes to `$580a6`) or lower and stops short (`$58058` clears 16
  words, `$58042` is a 12-entry word table, `$5801c`/`$58016` are the 6-byte command slots, side 0..5). The save
  game (`$3f2a0`, 195 bytes of conquered lands) is not RAM-block data. Treat it as an unset debug flag: reachable only
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
  literal, no PC-relative `lea`, none in the whole-image listing): leftovers of the fixed-map and sound code (`$1adaa` is `nom1`, the name beside `ptr_ech` `$1ada6` in the sample driver's data, `system.md`). `DATA\SPRITE8.DAT`
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
- **Not covered:** the radio click handlers of panel `$c` (the link handshake `$6eb6` and panels `$c`/`$12` are now read, "Serial-link states"); the crack's own title/intro screens and `MREP`; indirect
  writers of any flag. Scripts and raw output: `scratchpad/pm130/audit/` (`keysweep.py`, `sweep_diff.py`, `rw_census.py`);
  the reachability walk `reach_scan.py` there misses dispatch tables (it called `$b892` unreferenced although `$b3d0` calls
  it), which is why "Original names" counts unreferenced routines from the symbol starts instead.

## Open threads

- **Economy / population / invention: see economy.md.** None of it is in the per-tick
  path: `$1abaa` is the seasons and weather (its four `$1ba3e` calls are only the season
  sounds), `$3e06` is the armies eating, the health indicator, the animals, the carrier
  pigeons and the projectile update (`ai.md` "Shepherds, animals and carrier pigeons",
  "Arrows and carrier pigeons"), `$d322` is force-totalling. The land is made by
  `$10d1e`/`$ffa6`/`$2266`/`$ac20`; `$2984` then gives every settlement its two men and each
  man a job, once per build (`economy.md` 5a, Proven: a build runs it once, 8 of 8), and
  `$238c` and `$2906` are proven in "The starting armies" and "The world build, proven".
  Growth after that does not exist (a revolt, `$550e`, only moves a lord and his
  settlements). Still open: which routines of the `$2200`-`$3500` cluster write each side's
  `$580a6` assessment block beyond the campaign table, `$2458` and the diplomacy writers.
- **The AI on a live enemy.** All 25 natural `$661a` attack decisions in the four 200M-step
  runs (lands 0/5/25/60: 8/7/4/6) were captured at `$662a`/`$6632` (`scratchpad/pm122/dec/`,
  `parse.py`). `$68fe` found a target every time, and `$68ee`'s cost (4-66) was always far
  inside the group's food `112(A1)` (24,218-24,671, i.e. the `$5fff` seed of `$26c4` barely
  eaten), so every decision issued the attack order (posture `136(A1) := 4`, `$67ee(12)`);
  the not-enough-food fallback `$69b4(6)` and the no-target path `$69b4(8)` never ran.
  Targets were leaders of every other side, the player's (side 1) in 6 of 25, usually with a
  small `troops_field` (0-18). The food test does not bind at these values: AI armies never
  go hungry.
- **Combat: mechanism closed** ("Combat", `ai.md`). The `$5590` kill branch runs naturally on
  later lands. Remainder: the `$5c80`/`$5bd2` wear path (never fired in 800M later-land
  steps). Projectile type is byte6: `$28` (40, an arrow, from a bow) is common; `$12` (18)
  never appeared.
- **Land setup**: there is no mission-file grammar (campaign lands are the 195-entry `$3f428`
  table, "The campaign" above). Still unreached: the fixed-map branch (`$58148 < $100` →
  `$df52(7)`), which no campaign entry uses (possibly Load Data Disk). Whether the briefing OK
  path reaches `$10d1e` at all is settled: it does not (stored block); see "Mission / world setup".
- **Diplomacy.** A natural alliance is proven end to end (land 25, an ungarrisoned lone town,
  a `$02` waypoint and goods earned by order `$10`, no pokes; "Diplomacy"). Not observed: an
  envoy reaching a *garrisoned* lord (on lands 25 and 5 the side has one live captain, so no
  escort can be built; it needs a land with two) and the panel-`$1a` branch (an envoy
  arriving at the player), which is static only.
- **Order `$0a` (the HOME icon, `$6c16` → `$3c08`).** No run is recorded in "What each order
  does"; `$3c08` itself is proven (`ai.md`, "the regroup / return-home dispatcher").
- **The player's orders ("What each order does")**: each is named from one run. Not yet
  seen: `$04` (needs two captains), `$0e` on a lord with a WorkShop (a campaign land whose
  player lord is of kind 3 or 4, `economy.md` "Buildings and town layouts"), `$10`/`$1c` on a
  pile. Driving a revolt on purpose: take a lord's food (order `$06` on his town is refused,
  it is not ours; a trade adds +8) and then plant a spy to pulse him.
