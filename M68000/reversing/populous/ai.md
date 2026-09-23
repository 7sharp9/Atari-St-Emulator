# Populous (Atari ST): computer opponent AI

All addresses are runtime absolute (TEXT at $ad58). "Proven" means the reconstruction in
`py/ai_ref.py` reproduces the real routine's full memory delta under `callcap` (see Verification).
Inferred items are marked as such.

## 1. Architecture

The computer god has no private "brain" loop. Both sides are driven through the same per-side
**god record** (`god_rec`, $21e0c + side*$2e). Each frame:

1. `$db4c` (walkers_tick) increments the frame counter `$3c4c8`, then for side 0 and 1:
   if `rec.busy == 0` call `$13eda` (ai_think); if still not busy call `$13a44` (ai_powers).
   While iterating the walkers it also calls the land levellers `$135fc` / `$13816`, and
   `$ef4c`/`$f6b2` post raise/lower commands for computer-side walkers.
2. `$1e712` (god_commands_exec) clears `rec.busy` for every side with `rec.ctrl == 1` when
   `frame % rec.reaction == 0` ($1eab6..$1eaea, `divu`), then executes `rec.cmd` for both
   sides, then `$1eef4` clears the command bytes.

A decision routine writes at most one command per call and sets `busy = 1` (except the swamp
cast, see 3.2). So the AI makes at most one decision per `reaction` frames. The routines run
for the human side too, but the human's `busy` is never cleared (`ctrl == 0`), so they are inert
unless that side is switched to computer control.

### 1.1 god_rec ($21e0c side 0, $21e3a side 1; $2e bytes)

| off | size | meaning |
|---|---|---|
| +0 | b | command (0 none, 1 raise, 2 lower, 3 earthquake, 4 swamp, 5 move papal magnet, 6 volcano, 7-10 paint walkers, 11-13 paint objects, 14 icon/menu) |
| +1,+2 | b,b | command x, y (cell = y*64+x). For cmd 14, +1 = argument, +2 = sub-command |
| +6 | w | controller: 1 = computer (AI + busy clearing), 0 = human |
| +8 | w | busy: 1 = decided, wait for next reaction tick |
| +12 | w | rating / inverse aggression, 1..10 (1 best/most aggressive) |
| +14 | w | options mask: 1 modify land, 2 attack towns, 4 attack leader, 8 earthquake, $10 swamp, $20 knight, $40 volcano, $80 flood, $100 armageddon |
| +16 | w | reaction interval in frames, 1..10 (1 fastest) |
| +18 | w | power-cast counter c (quake/swamp cycle) |
| +20 | w | castles this frame (settlements with strength >= 3050) |
| +22 | w | other settlements ($3b22c copy) |
| +24 | w | swamp cap: set at land init to +26 + 1 + rand%5 |
| +26 | w | earthquake quota: rand%3 at land init ($bcc8) |
| +28 | w | target hold counter (2 when a magnet target is set) |
| +30 | w | target cell |
| +32 | w | minimap dot colour for this side's walkers (5 good, 1 evil; `graphics.md`, Minimap) |
| +34 | l | ptr: enemy settlement with the largest size value ($18206) |
| +38 | l | ptr: enemy oldest settlement (largest frame - birth age); falls back to an enemy walker in state 2 |
| +42 | l | ptr: own newest settlement |

Fields +20..+42 are rebuilt every frame by `$db4c` ($dc74-$dcdc reset, $e3ae/$e428/$e4a0/$ea32 set).

### 1.2 side_state ($3b226 + side*16)

| off | meaning |
|---|---|
| +0 w | leader walker index + 1 (0 = no leader) |
| +2 w | papal magnet cell (init $820 = 32,32) |
| +4 w | walker mode: 0 go to magnet, 1 settle, 2 gather, 3 fight (init 1). Mode meanings inferred from `$f2f4` (3 prefers enemy walkers, 2 prefers own walkers) and `$f6b2` (0 walks toward magnet) |
| +6 w | settlement count (non-castle) |
| +8 l | total population strength (sum of walker +4) |
| +12 l | mana (init 399; +1 every other frame in `$db4c`, plus settlement income) |

### 1.3 Power costs (longs, DATA)

| addr | value | used by |
|---|---|---|
| $21988 | 10 | raise/lower base cost (actual cost 10 + 4*points changed) |
| $2198c | 200 | move papal magnet |
| $21990 | 2500 | earthquake |
| $21994 | 5000 | swamp |
| $21998 | 7500 | knight |
| $2199c | 10000 | volcano |
| $219a0 | 40000 | flood |
| $219a4 | 80000 | armageddon |

## 2. Where the options come from

### Conquest
`$b316` copies the level record `$22ad8` (conquest level data; loader not traced here) into both god records:

| level byte | goes to | shown as |
|---|---|---|
| $22ad8 | computer +12 | "HIS RATING IS" string 9+(10-v)/2: 10 VERY POOR .. 1-2 VERY GOOD |
| $22ad9 | computer +16 | "HIS REACTIONS ARE" 4+(10-v)/2: 10 VERY SLOW .. 1-2 VERY FAST |
| $22ada | computer +14 = (v<<3)\|7 | his powers (bit0 quake .. bit5 armageddon) |
| $22adb | human +14 = (v<<3)\|7 | your powers |
| $22adc | `$219b2` game flags | build/swamp/water rules |
| $22add | landscape | |

So in conquest the computer can always modify land, attack towns and attack leader (bits 0-2);
only its power set, rating and reaction come from the level. GENESIS: rating 10, reaction 10,
powers 0 (computer +14 = 7), human +14 = $1ff.

### Custom game, "OPTIONS FOR EVIL" (`$1c05a`, reached via cmd 14/7 from `$1f0fa`)
Menu items at $22000 + i*$2e (x.w, y.w, flags.w, text). Items 1-9 toggle bit (1<<(i-1)) of
`rec.+14` ($1c580): MODIFY LAND=1, ATTACK TOWNS=2, ATTACK LEADER=4, EARTHQUAKES=8, SWAMP=$10,
KNIGHT=$20, VOLCANO=$40, FLOOD=$80, ARMAGEDDON=$100. The two sliders store 0..9 from the click
x ($1c5bc, $1c630), and on entry and OK the record is converted with `v = 10 - v`
($1c0f0, $1c13a, $1c6fc, $1c746):
- AGGRESSION slider s (LOW=0 .. HIGH=9) -> `+12 = 10 - s` (HIGH aggression = rating 1).
- RATE slider s (SLOW=0 .. FAST=9) -> `+16 = 10 - s` (FAST = act every frame).
CANCEL restores the whole record from a copy ($1c6d0). Conquest "rating" and custom
"aggression" are the same variable.

### Game options `$219b2` (conquest from $22adc; custom from GAME OPTIONS menu)
1 water fatal (else harmful), 2 swamps bottomless (else shallow), 4 cannot build (no land
modification), 8 only build up (no lowering), $10 build near towns (else near people).
Strings mapped at $1aa7c-$1abba. The AI obeys 4 and 8 itself (see 3.3); $10 and 1 are not read by
the AI routines.

### HUMAN VS ATARI / ATARI VS ATARI / computer assistance (`$1b046`)
GAME SETUP items at $22286 + i*$2e. HUMAN VS ATARI ($1b8b2): `god_rec[me].ctrl = 0`, and in one
player mode `god_rec[other].ctrl = 1`. ATARI VS ATARI ($1b95c): `god_rec[me].ctrl = 1` (plus the
other side in one-player). In a serial game the same flag on your own side is what the other
machine reports as "COMPUTER ASSISTANCE" (strings $22d2a/$22d58). There is no separate
assistance AI: the human side simply runs `$13eda`/`$13a44`/levellers with its own record.
Anti-tamper: `$13372` (checksum $3c4b4 vs $21d58+$12312378) and `$db4c` at walker 20
($3c4c0 vs $21d4c+$14725836, $e182) set both sides' ctrl = 1; the latter also sets `$3d524`
(the armageddon state).

## 3. Decision logic (proven, 4800/4800 callcap matches)

### 3.1 ai_think $13eda(side) - where to send the people

```
r = god_rec[side]; st = side_state[side]; en = side_state[!side]
if (s16(r.castles + r.houses) < r.rating*2 + 15            ; signed
    or (frame % 90) < r.rating + 10):                      ; unsigned, $13f3a
    if st.mode == 0:                                       ; stop chasing the magnet
        cmd14/1 x = 1 + rng()%3   ; random settle/gather/fight, busy
    return
own = leader(side); foe = leader(!side)
if own == 0:
    if st.mode != 0: cmd14/1 x=0 (go to magnet), busy, r.hold = 0
    return                                                ; walkers go to the magnet to make a leader
if own.cell == r.tgt and r.hold: r.hold--                 ; leader reached target
if own.strength < 6000:                                   ; grow the leader
    if r.hold: if st.magnet != r.tgt: cmd5 at r.tgt, busy; return
    else:      if st.magnet != r.own_newest.cell:
                   cmd5 at own_newest.cell; r.tgt = cell; r.hold = 2; busy; return
    if st.mode != 0: cmd14/1 x=0, busy
    return
if foe and own.strength > foe.strength + 500 and en.mode == 0:   ; attack leader
    if r.opts & 4:
        if st.mode != 0: cmd14/1 x=0, busy
        elif st.magnet != en.magnet: cmd5 at en.magnet, busy
    return
if r.opts & 2:                                            ; attack towns
    t = r.enemy_strongest
    if st.magnet != t.cell and r.hold == 0: cmd5 at t.cell; r.tgt = t.cell; r.hold = 2; busy; return
    if st.mode != 0: cmd14/1 x=0, busy
```
Command 5 costs 200 mana and is refused by `$111be` if mana < 200 or the side has no leader.
Command 14/1 sets `side_state.mode` directly ($1f0fa case 1).

### 3.2 ai_powers $13a44(side) - divine intervention

Order and thresholds (`mana` = side_state+12, comparisons are signed `>`):
```
if busy: return
if opts&$100 and mana > 80999 and pop[side] > pop[!side]: cmd14/3 armageddon, busy; return
if opts&$80  and mana > 41999:                              cmd14/4 flood, busy; return
if opts&$20  and own leader exists and leader.strength > 3000:
    if mana > 8000: cmd14/5 knight, busy
    return                          ; NOTE: returns even when it cannot afford the knight
if r.enemy_oldest == 0: return
if mana > 10500 and opts&$40: cmd6 volcano at target(); busy; c = 0; return
if mana > 5500 and opts&$10
   and not (c < r.quake_quota and opts&8)
   and not (c > r.swamp_cap and opts&$40)
   and enemy leader exists and (no own leader or foe.strength > own.strength):
    c++; cmd4 swamp at enemy leader cell   ; NOT busy
    return
if mana > 3000 and r.enemy_oldest.state == 1 and opts&8
   and (c < r.quake_quota or (opts & $50) == 0):
    cmd3 earthquake at target(); busy; c++
```
`target()` = `$13dce`: if the side has no leader and the cell under its own magnet is occupied by
an enemy walker ($37fd4), strike the magnet cell; otherwise strike
(oldest_enemy.x - 3, oldest_enemy.y - 3), clamped at 0.
Resulting cycle when all three are allowed: `quake_quota` (0-2) earthquakes, then swamps on the
enemy leader until c > swamp_cap, then nothing cheaper until volcano mana, and the volcano resets c.

### 3.3 Land modification

`ai_flatten_site $135fc(cell, side)`, called from `$db4c` for each housed walker (state 1) of a
side that is not busy, when `$33be4[cell] == 0` and (walker+$14 == 0 or its size changed or
`$37eb6`), result stored in walker+$14; also called unconditionally when `$33be4[cell] != 0`,
the side's previous-frame (houses + 3*castles) < 3 and frame > 250.
```
if !(opts&1): return 0;  if flags&4: return 4
h0 = height[x0][y0]
for (dx,dy) in table $227d8 (9x9, order: columns -4,-3,+4,+3,-2,+2,-1,+1,0; rows -4..+4):
    p = (x0+dx, y0+dy); skip unless 0<=px<=64 and 0<=py<=64
    o = obj[py*64+px]
    if o == $2f and !(flags&8): obj++ ; lower p ; busy; return 0
    d = h0 - height[p]
    if d > 0: raise p; busy; return 0
    if (d < 0 or o == $42 or o == $35) and !(flags&8): lower p; busy; return 0
return 1                                   ; site flat: not revisited until the house changes
```
`ai_level_walker_cell $13816(cell, side)`, called for each moving walker (state 2) when not busy:
requires mana >= 20, houses <= 50, opts&1, !(flags&4). With s = sum of the 4 corner heights,
q = s/4, r = s%4 (s == 1 ignored): r == 3 -> raise the first corner equal to q; r == 1 -> lower the
first corner above q (unless flags&8). Corners visited (x0,y0),(x0,y0+1),(x0+1,y0),(x0+1,y0+1).
Other AI land edits (not diff-tested): `$ef4c` posts lower at a computer walker's cell standing on
obj $42 when not busy and flags&$c == 0; `$f6b2` posts raise at a computer walker's cell when its
step is blocked ($18198 == 3) or the next cell is obj $35 (swamp, flags&8 clear).
Raise/lower cost 10 + 4 per height point changed ($1186c/$116fa); nothing happens below 10 mana.
Object codes: $2f rock, $35 swamp (walkers die on it, $e9b8), $42 burnt field of a destroyed house.

## 4. Strategy notes (derived from the code)

- Reaction speed is a hard rate limit: at most one land edit, magnet move or power per
  `reaction` frames, and all three compete for the same slot. VERY SLOW (10) = one action per
  10 ticks.
- Rating/aggression gates offence: until the AI owns `2*rating + 15` settlements (35 at VERY
  POOR, 17 at VERY GOOD) it never moves its magnet to attack; it only flips between settle,
  gather and fight at random, and only when it was in magnet mode. Even after that, it spends
  `rating + 10` of every 90 frames in that passive mode.
- Its leader is fed first: while its leader is below 6000 strength it parks the magnet on its
  own newest town. Killing or swamping its leader resets it to "go to magnet" and wastes turns.
- It attacks your leader only when its leader is more than 500 stronger and your side is in
  magnet mode. Keeping your walkers in settle/gather/fight mode makes it attack towns instead,
  and the town it picks is always your largest one (+34).
- Knight lock-out: with the knight power allowed and a leader above 3000, the AI casts nothing
  cheaper than a knight until it has 8001 mana. Armageddon needs 81000 mana and more total
  population than you; flood 42000.
- Earthquakes and volcanoes target 3 cells up-left of your oldest settlement, so the effect is
  predictable; swamps go on your leader's cell only when your leader is stronger than its own.
- It never lowers land when "only build up" is set and never touches land when "cannot build"
  is set; it ignores "build near towns" (not read by the AI).
- Its settlement levelling works on a 9x9 corner area and one point per action, so a sea or cliff
  inside that square burns mana (10 + 4/point) repeatedly.

## 5. Verification

`py/ai_diff.py` loads game_start.snap, g40.snap and g90.snap, and for each routine generates
randomized states (options, rating, counters, leaders, strengths, magnets, mana at every
threshold +-1, frame, RNG seed, 9x9 height/object patches, flags), writes them with `w`, pokes the
stack arguments at the entry SP, runs `callcap <routine>` on the real code, and compares the full
non-stack memory delta (and $135fc's returned D0 byte) with `ai_ref.py`:

| routine | matches | branch coverage (model outcome: count) |
|---|---|---|
| $13eda | 1200/1200 | mode set 378, magnet move 232, counter-only 18, none 572 |
| $13a44 | 1200/1200 | armageddon 19, flood 150, knight 163, volcano 100, swamp 59, quake 33, none 676 |
| $135fc | 1200/1200 | raise 420, lower 514, ret0 90, ret1 52, ret4 124 |
| $13816 | 1200/1200 | raise 42, lower 33, none 1125 |

Command: `python py/ai_diff.py 400 7`.
Live check (GENESIS, computer rating 10, reaction 10, no player input): `$13eda` runs for side 1
at each busy clear ($1eaea) and never posts a magnet or mode command, as the model predicts (4
settlements < 35 and mode 1, so it only acts in mode 0; power options are 0). The levellers do
act: from game_start (frame 285) the computer's corner heights diverge by 14 corners at frame
475, 111 at frame 1328 and 207 at frame 2161, all in its south-east start area, and its mana is
spent down to single digits early on, then banked (7485 at frame 2161) once its sites are flat. No
menu-driven custom or Atari-vs-Atari game was run.

## 6. Open questions and cross-references
- Resolved by the other areas: `$33be4`, which gates `$135fc`, is the per-cell altitude (`terrain.md`
  section 1). Why the gate treats altitude 0 differently is not traced. $2f is rock and $42 a burnt field (`terrain.md`, `mechanics.md`); +34 ranks by the
  `$18206` land value, which is also the settlement capacity (`mechanics.md` 4.1). `$2287e` is the
  surrender flag (`mechanics.md` 6).
- ONE PLAYER while in two-player mode ($1b452) writes `ctrl` of `my_side` twice (0 then 1); looks like
  a source bug, not run.
