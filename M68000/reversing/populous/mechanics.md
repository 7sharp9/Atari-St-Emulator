# Populous (Atari ST): people, settlements, mana

All addresses are runtime absolute (POPULOUS.GOD TEXT at $ad58). "Verified" means checked against the
emulator with the scripts in `py/`; "inferred" means read from code but not exercised.

## 1. Where it runs

The main loop `$b510` (one iteration per game frame) calls, when neither `$3b274` nor `$3b276` is set
(both non-zero only in the non-simulating paint/setup modes):

- `$12f84` moving hazard effects in entity slots $d1/$d2 (section 7);
- `$db4c` **entity update**: the whole people/settlement/mana simulation, once per frame.

`$3b222` toggles 0/1 every main-loop iteration (`$b6a2`); it drives the half-rate mana tick and the
walker sprite animation phase. `$3c4c8` is the frame counter (incremented at `$db58`).

## 2. Data structures

### 2.1 Entity record, `$3b278 + 0x16*i`

Slots 0..$cf (208) are people/settlements; `$3c4e2` is the high-water count (trimmed at `$dd2e` while the
last slot has str 0). Slots $d1, $d2 (`$3c46e`) are the two hazard effects run by `$12f84`.
A free slot is any with str <= 0.

| off | size | name | meaning |
|---|---|---|---|
| +0 | b | flags | state bits, table below |
| +1 | b | side | 0 = good, 1 = evil |
| +2 | b | range | walker look-ahead in cells for `$f2f4`; a settlement increments it (max 4) each time it emits a walker, and the walker inherits it |
| +3 | b | weapon | combat class = `$3b248[level]` of the settlement that last updated/emitted it (0..10, castle 20); merges keep the max |
| +4 | w | str | population (settlement) or strength (walker); entity is dead/free when <= 0; capped 32000 on merge |
| +6 | w | t6 | settlement: frame it was founded (`$3c4c8`); fighting: index of the opponent; paused (0x20/0x40): pause counter; ruin (0x80): countdown |
| +8 | w | cell | map cell, y*64+x (x = cell&63, y = cell>>6) |
| +10 | w | off | cell offset of the last step (the walker is animating from cell-off to cell) |
| +12 | w | anim | walker: step phase 0..7; settlement: sprite = $20+level, $2a castle; other states own sprite ranges ($55 celebrate, $5d drown, $65 paused, $82/$86/$8a/$46 fight) |
| +14 | l | knight | non-zero = knight; value = pointer to the enemy entity it hunts |
| +18 | w | last | previous cell, cleared when it no longer equals cell-off |
| +20 | b | aiflag | three unrelated uses: in a settlement the cached result of `ai_flatten_site $135fc` (0 not flat, 1 flat, 4 cannot build; written `$e540`, read `$e4fc`, cleared in an emitted walker `$e802`); in a walker 1 on a new knight (`$12c86`), "report my next win to the AI" (`$108b8`, section 3.5, any winner with +20 set, knight or not); in the hazard slots $d1/$d2 the effect type (`$13372`) |
| +21 | b | lastdir | `$f6b2`'s memory: a direct step stores the direction taken, a fallback step the opposite of the direction taken; the fallback skips the direction equal to +21 |

Flags (`$db4c` dispatch at `$df76..$edac`; animation by `$101a0`):

| value/bit | state | per-frame handling |
|---|---|---|
| ==1 | settlement | grows, earns mana, emits walkers (section 4) |
| ==2 | walker | animates; every 8th frame takes one step (section 3) |
| bit 3 (8) | fighting; exactly 8 = the attacker, which runs `$1063a` each frame. A settlement under attack is 9 and is frozen |
| bit 2 (4) | celebrating after a win, anim $55..$57, then cleared |
| bit 4 ($10) | in water (set as $12: any entity whose cell becomes water, `$e136`) |
| bits 5/6 ($20/$40) | paused (anim $65), losing `$37eb0` str per frame; cleared when t6 passes 14, or by a merge into it. $40 = no legal move (`$ef4c` 999, t6 = 7: 8 frames). $20 = wait for a follower (`$eb8c`, t6 = 0): see 3.3 |
| bit 7 ($80) | ruin / corpse, str 1, t6 counts down from 40 then str 0 |

Occupancy: `$37fd4` byte per cell = entity index+1 (0 empty). `$38fd8` word per cell = walker visit
count (incremented when a walker leaves a cell, `$f29e`). Terrain class `$36e78` byte per cell
(0 water, $0f flat unclaimed, $1f/$20 flat claimed by good/evil, $2f..$31 rock, $35 swamp, $42 ruined
ground); building overlay `$3c522` byte per cell ($21..$29 houses, $2a castle, $29..$2c castle walls,
+$15 when burnt). The terrain area owns these maps; here they are only read.

### 2.2 Side record, `$3b226 + 16*side`

| off | addr (side 0 / 1) | meaning |
|---|---|---|
| +0 w | $3b226 / $3b236 | leader = entity index+1, 0 = none |
| +2 w | $3b228 / $3b238 | papal magnet cell (mirrored in `$3c4ca` / `$3d526`) |
| +4 w | $3b22a / $3b23a | command mode: 0 go to magnet, 1 settle, 2 gather, 3 fight |
| +6 w | $3b22c / $3b23c | towns this frame (non-castle settlements) |
| +8 l | $3b22e / $3b23e | population = sum of str of all live entities of the side, rebuilt each frame |
| +12 l | $3b232 / $3b242 | mana |

`$3affe` = the human's side, `$22284` = the other side. `$3c4c6` = entity shown in the query panel (index+1).

### 2.3 Per-side options/AI record, `$21e0c + 0x2e*side` (DATA segment)

Fields used here: +0 b AI request code (1 = raise land at (+1,+2), 2 = at a ruin), +1/+2 b request x/y,
+6 w computer-controlled flag (1), +8 w AI request pending (the AI planners `$13eda`/`$13a44`/`$135fc`/
`$13816` only run while it is 0), +14 w permitted-power mask ("OPTIONS FOR ..." menu): bit 3 earthquake,
4 swamp, 5 knight, 6 volcano, 7 flood, 8 armageddon (bits 0..2 = modify land / attack towns / attack
leader, the "OPTIONS FOR EVIL" items 1-3, `ai.md` section 2), +16 w aggression/rate used in the score.
+34/+38/+42 l are the planner's "biggest town", "oldest town", "a walker" pointers written by `$db4c`.
The AI area documents the rest.

### 2.4 Game options `$219b2` (menu `$1bc0e`, bit = 1 << row/2)

bit 0 water is fatal, bit 1 swamps bottomless, bit 2 cannot build, bit 3 only build up, bit 4 build near
towns. `$219b0` = computer opponent present.

### 2.5 LAND header tables (read by `load_land` `$14be8` from `landN`, values for land 0)

| addr | contents |
|---|---|
| $37eb0 w | 1: strength lost per walker step (drowning costs 2x per frame) |
| $24998 [11] | growth per 8 frames by level: 0 1 1 2 2 3 3 3 4 4 5 |
| $3b20c [11] | mana per 8 frames by level: 0 0 0 0 1 2 3 4 5 6 20 |
| $3b248 [11] | weapon class by level: 0 1 2 3 4 5 6 7 8 10 20 |
| $3c4fe [11] | mana for capturing/destroying a town by level: 50 100 200 ... 900, castle 2000 |
| $3c4e8 [3] | mana for killing a walker: 100, knight 1000, leader 3000 |

Level index = settlement sprite - $20 (0..9 houses, 10 castle).

## 3. Walkers

### 3.1 Step clock
`$101a0` advances anim; a walker (flags 2) returns "step now" when anim wraps from 7, i.e. one step every
8 frames. On a step (`$e98a..$eace`): swamp check, then `$ef4c` (decide+move), then str -= `$37eb0`.
A walker therefore loses 1 strength per cell walked. Verified: 137/138 steps (the one miss was a walker
that absorbed a merge in the same step).

### 3.2 Choosing a direction
`$ef4c(e, idx)` calls `$f6b2` when the side's mode is 0, the walker is a knight (+14 != 0) or
Armageddon (`$3d524`) is on; otherwise `$f2f4`. Both return a cell **offset** (0 = stay/settle, 999 =
no move).

**`$f2f4`** (settle / gather / fight). Locals `best[5]` = 5 (distances), `res[5]` (offsets), `minv` = 9999:

```
d = -1
for k in 0..8:                                  ; 9 rays
    if d == 0 and k == 1: d = (rand() & 7) + 1  ; exactly one $16702 call per $f2f4
    else: d += 1
    if d == 9: d = 0
    off = $22b4e[d]                             ; 0, N, E, S, W, NE, SE, SW, NW
    cell = e.cell
    for dist in 0 .. e.range-1:                 ; e+2
        if $18198(cell, off) != 0: break        ; water, rock $2f, off map: the ray ends
        cell += off
        if shape[cell] == $0f and dist < best[0]:            ; (0) land to settle
            if d == 0:
                if $18206(side, cell) != 0: best[0]=dist; res[0]=0; continue
            elif no overlay[cell+$22b4e[j]] in $21..$2c for j = 9..16 (on-map cells):
                best[0]=dist; res[0]=off; continue
        if d == 0: continue
        o = occupant[cell]
        if o and o-1 != idx:
            t = entity[o-1]
            if t.flags & 8 and dist < best[1]: best[1]=dist; res[1]=off; continue    ; (1) a battle
            if t.side != side and dist < best[2]: best[2]=dist; res[2]=off; continue  ; (2) enemy walker or town
            if t.flags & 2 and dist < best[3]: best[3]=dist; res[3]=off; continue     ; (3) friendly walker
        if off != e.off:                                      ; (4) least visited, not straight on
            v = visits[cell]                                  ; unsigned
            if v < minv or (v == minv and dist < best[4]): minv=v; best[4]=dist; res[4]=off
if mode == 3 and best[2] != 5: return res[2]    ; fight: nearest enemy
if mode == 2 and best[3] != 5: return res[3]    ; gather: nearest friendly walker
for i in 0..4: if best[i] != 5: return res[i]
return 999
```

Consequences:
- **The rotation skips a neighbour.** The rays are own cell, r..8, own cell again, 1..r-2 with
  r = (rand&7)+1: direction r-1 is never scanned in 7 of 8 calls. It changed 41/684, 71/867 and 85/874
  live decisions against a full 8-way scan (a source bug is *inferred* from the loop's shape).
- A ray continues past a hit (only a blocked step ends it); each category keeps its nearest hit, ties
  to the ray scanned first. The own-cell ray records only category 0.
- Category 0 on a neighbour ray checks only the 8 distance-2 cells round the candidate for buildings,
  not ring 1. On the own-cell ray it asks `$18206`, and only when the own cell is unclaimed `$0f`: a
  walker on claimed land never settles through category 0.
- The occupant map marks the cell a walker is *leaving* (set at `$f2d2` as it steps, cleared at
  `$f018` on its next step) and also holds settlements, so "enemy" includes enemy towns.

**`$f6b2`** (magnet / leader / knight):

```
if e.knight:
    t = e.knight
    if e.cell == t.cell or t.str <= 0 or t.side == side or t.flags & $80: $fe00(e)   ; $f6ca..$f714
    goal = e.knight.cell
elif leader(side) == 0:
    if magnet(side) == e.cell: leader(side) = idx+1; if $3c4c6 == 0: $3c4c6 = idx+1
    goal = magnet(side)
elif leader(side)-1 == idx: goal = magnet(side)
else: goal = entity[leader(side)-1].cell
h = word[$225c8 + ((sgn(gx-x)+1)*3 + sgn(gy-y))*2] ; table from $225c6: 7 6 5 / 0 0 4 / 1 2 3; dx = dy = 0 gives N
r = $18198(e.cell, dir8[h])                        ; dir8 = $225a4: N NE E SE S SW W NW
if r == 0 and not (e.knight and shape[e.cell+dir8[h]] == $35): e+21 = dir8[h]; return dir8[h]
if r == 2 and armageddon:                          e+21 = dir8[h]; return dir8[h]
if (god[side].ctrl == 1 or armageddon) and (!(opts & 4) or armageddon):   ; busy is not checked
    if r == 3: god[side].cmd = 1 (raise) at e.cell, busy = 1
    elif shape[e.cell+dir8[h]] == $35 and !(opts & 8) and !armageddon: god[side].cmd = 1 at that cell, busy = 1
j = h-1
repeat 8:                                          ; tries h-1, h, h+1 .. h+6
    wrap j to 0..7; o = dir8[j]
    if $18198(e.cell, o) == 0 and o != sext(e+21) and not (e.knight and shape[e.cell+o] == $35):
        e+21 = dir8[$22ae2[j]]; return o           ; stores the OPPOSITE of the step taken
    j += 1
e+21 = dir8[$22ae2[j]]                             ; j = h+7 unwrapped: reads past the 8-entry table
return 999
```

So a leader standing on the magnet steps off it to the north and back; rock is passable under
Armageddon only on the direct heading; only shape `$2f` blocks (`$30/$31` are walkable); a knight
never steps into swamp, and its raise-at-swamp request is the only way past one; the raise request
overwrites any pending command.

`$fe00(e)` (knight target): e+14 = e itself; then over entities 0..`$3c4e2`-1 of the other side with
str > 0 and not a ruin ($80), so fighting, drowning and paused enemies and towns all count, it takes
the smallest |dx|+|dy| of the cell coordinates (`$207b2` abs); only a strictly smaller distance
replaces, so ties go to the lowest index. With no enemy the knight targets itself, heads north and
re-acquires on every step. Distance is the only criterion, so a knight never gives up on a target
across the sea.

`$18198(cell,off)` returns 0 land, 1 off-map/wraps, 2 rock $2f, 3 water.

Proof (`py/walker/`): `walker_ref.py` against `callcap` over randomized neighbourhoods, modes,
leaders, magnets, knights, Armageddon and seeds on 3 snapshots: `$f2f4` **1200/1200** and `$f6b2`
**1200/1200** (full memory delta and D0; every category, both mode overrides, 999, rock under
Armageddon, 55 water and 12 swamp raise posts). In play, through popdrive clicks only (a magnet walk
and five one-corner raises bridging the human's island to the south-west evil towns, then the gather
or fight icon), every live `$ef4c` decision was predicted, **8000/8000** over four runs, and every
walker's cell at every frame, gather **19451/19451** (935 frames), fight **19480/19480** (903
frames), island runs **12932/12932** (703 frames).

### 3.3 After the decision (`$ef4c`)
- 999: flags |= $40, t6 = 7: an 8-frame pause (code-read; no live decision returned 999).
- The follower pause, flag $20 (`$eb8c`, in the per-frame walker code after the step): for walker B,
  if `A = occupant[B.cell]-1` is another entity with A < $d0, A.anim == 0 and A not in water, then
  A.flags |= $20, A.anim = $65, A.t6 = 0. Since the occupant mark is the cell a walker is leaving and
  anim 0 is the frame of a step, this reads: **B is heading into the cell A has just stepped out of,
  so A waits for B.** B's next step finds A on its cell and merges into it or, if enemies, attacks it;
  `$feca` clears the pause. It is side-blind. Live (three runs): the trigger rule held for 69/69,
  74/75 and 94/95 pauses (the two misses are end-of-frame capture artefacts: the candidate B merged,
  re-stepped or was paused itself in the same frame); 203 of 239 ended in a merge, mostly after 7-8
  frames (the follower's step interval), otherwise after the full 15; a paused walker lost 1 str per
  frame in 1424/1435 paused frames (the rest were merge frames).
- The entity already registered at the walker's current cell (`$37fd4`) decides an interaction:
  enemy not fighting -> `$10e7e` start a fight (both get bit 3, t6 = each other, and they share one
  cell); same side -> `$feca` merge; entity already fighting -> `$11006` joins the fight by merging into
  whichever of the two combatants is on its side.
- Merge `$feca(i, j)` (walker i into entity j; `$11006` joins a fight through it):
  ```
  if i.knight: if j.flags == 1: return      (a knight meeting its own settlement: nothing happens at all)
               j.knight = i.knight          (the pointer moves: j becomes the knight)
  j.str = min(i.str + j.str, 32000); leader and query selection move from i to j
  if j > i: population[i.side] -= i.str     (j was already counted this frame)
  j.weapon = max; i.str = 0; j.flags &= $9f (unpause); j.anim = 0
  ```
  A walker that walks into its own town therefore adds its strength to the town population.
- Direction 0 (settle here) and not a knight: flags = 1, t6 = frame, footprint claimed by `$10366`.
- Otherwise: visit count++ and occupancy set on the cell being left, cell += dir, off = dir.

### 3.4 Water and swamp
- On a step, standing on swamp ($35) kills the walker (`$10068`); the swamp cell reverts to $0f unless
  swamps are bottomless (option bit 1).
- Any entity whose cell becomes water (terrain lowered/flooded) becomes flags $12. Each frame it loses
  2 x `$37eb0`; with "water is fatal" it dies at once. It recovers (bit 4 cleared) if the cell becomes land.
  A settlement caught this way is first un-claimed and turns into a walker.

### 3.5 Combat, `$1063a` (run each frame by the attacker, flags == 8)
With O = entity[t6] (opponent) and S = self, using the game RNG `$16702`
(seed `$3d52e`: s = ((s*$24a1 mod 2^16) + $24df) & $7fff):

    X = (rand%3+1) * O.str        ; first call
    Y = (rand%3+1) * S.str        ; second call
    m = min(X, Y)                 ; (Y if X > Y else X)
    O.str -= (m/100) * S.weapon + 10
    S.str -= (m/100) * O.weapon + 10      ; integer division truncating toward zero

Both <= 0: both die. Otherwise the survivor wins via `$108b8(winner, loser)`.
Verified 18/18 rounds exactly (str of both sides and the RNG seed), 6/6 resolutions consistent.

`$108b8(winner, loser)`: battles won `$3c514[winner.side]`++. Mana transfer amount e:
- loser a walker: 100, knight 1000, the side's leader 3000 (`$3c4e8`).
- loser a settlement: `$3c4fe[level]` (100 if sprite out of range). **Raze** when the winner has a
  knight pointer and non-zero str; otherwise the town is taken over: the old footprint is released,
  and if `$18206` gives the winner's cell a value it becomes a settlement of the winner's side (the
  old record is discarded); else it stays a walker. The raze: the loser becomes a ruin ($80, str 1,
  t6 40) and the winner flags 2. Of a town's 17 footprint cells, those passing `$18198` with the
  loser's colour ($1f + loser side) become $42; a castle (centre feature $2a) uses all 25 cells
  without the step check, and its ring-1 wall features $29..$2c get +$15. The centre feature
  ($20..$2a) gets +$15 (burnt) and the loser's occupant mark is cleared.
- then, for both kinds: the winner's cell occupant becomes the winner if it was empty or the loser;
  if the winner's aiflag (+20) is set, god_rec[winner.side] +30 = winner cell, +28 = 2 and aiflag -= 1
  (a new knight has 1, so its first win sets the AI's magnet target once); if the loser's aiflag is
  set, god_rec[loser.side] +28 = 0.

Then winner flags |= 4 (celebrate), mana[winner] += e, mana[loser] -= e floored at -250 (`$21984`).
Observed: leader killed -> +3000 / -3000 clipped to -250.

Proof of the knight rules (`py/powers/`): under `callcap`, `$fe00` 240/240 (84 ties, 62 with no
enemy), `$feca` 240/240 (121 knight-pointer moves, 33 refused merges into a settlement) and `$108b8`
240/240 (73 town razes, 68 castle razes, 99 walker losers). In play, a knight cast through the UI
(with a land corridor built so it can reach the enemy, `knight_scn.py`) was followed for 1100 frames:
every direction/re-target call **133/133** (127 kept the target, 6 re-acquired), every merge **18/18**
and every raze **3/3** (towns e6, e4 and e12, re-targeting e6 -> e4 -> e12 -> e3) matched the model on
the full state. Without the corridor that knight walks its heading into the shore of its own island
and starves by frame ~720. The non-knight take-over path was not exercised.

## 4. Settlements

### 4.1 Land value and building size, `$18206(side, cell)`
Over the 17 cells centre + ring 1 + four ring-2 axis/diagonal cells (`$22b4e[0..16]`):
- off-map: ignored; rock: value -= 15;
- flat (own claimed colour or $0f): value = 50 on the first hit, then += 15 each;
- centre not flat: return 0;
- any other building overlay ($21..$2c) in the 16 surrounding cells: return 0 (a castle's own wall
  pieces are allowed and counted in `$3b002`).
Values below 35 become 0; exactly 305 (all 17 flat) becomes 3050 = castle. Side effects: `$3b002` is
cleared and counts the castle wall pieces seen, and `$37eb6` is set when a footprint cell is unclaimed
`$0f` (both reproduced by the power models under `callcap`; `people_model.py` does not track them).

Sprite/level: value < 3050 -> $20 + value*10/305 (levels 0..9), else $2a castle (level 10).
Capacity = value (castle 3050). Value 0 makes the settlement leave as a walker next frame.
Verified: 4122/4122 settlement sprites over 400 frames.

### 4.2 Per-frame settlement update (`$e22e..$e968`)
Every frame: recompute value and sprite; if the value is 0, or the settlement holds a knight, or
Armageddon is on, it becomes a walker (flags 2).
Every 8th frame (`$3c4c8 & 7 == 0`):

    mana[side] += $3b20c[level]
    weapon      = $3b248[level]
    if str > capacity:                 ; emit a walker into the first free slot
        child.str = str - capacity/2 ; parent.str = capacity/2
        child: flags 2, same side/cell/weapon/range, parent.range += 1 (max 4)
        (leader and query selection follow the child if the parent held them)
    str += $24998[level]

Every 8th frame, a castle of a computer-controlled side with str > 305 whose side is **not** busy gets
capacity 305 instead of 3050 and sets the side busy (`$e5a6..$e638`): an AI action, so the castle then
emits a walker (verified 332/332 live, `ai.md` 3.4). If the table is full
(208), `$13372(1)` spawns a swamp trail, once per game (`$3c4c4`; `systems.md` 1.3, not run). Verified: settlement str 4122/4122,
weapon 516/516, emitted walkers 12/12 (str, side, cell).

### 4.3 Claiming land, `$10366(e, release)`
The footprint is the cell-offset table `$22b4e` (25 words): 0, the 8 neighbours (-64, 1, 64, -1, -63,
65, 63, -65), the 8 cells two out (-128, 2, 128, -2, -126, 130, 126, -130), then the 8 that complete
the 5x5 (-127, -62, 66, 129, 127, 62, -66, -129). A town uses the first 17, a castle all 25; cells
`$18198` rejects as off the map are skipped.
Founding marks the 17 footprint cells that are $0f as side colour ($1f/$20) and writes the sprite into
the overlay at the centre; a castle claims all 25 cells and writes the wall sprites `$225b4`. Release
(`release` != 0): if the centre overlay is `$2a` (castle), clear the overlay on all 25 cells;
otherwise on the first 9, then the centre; on every footprint cell a map byte equal to `$1f + side`
reverts to `$0f` (proven live over the Armageddon vacate, section 5).

## 5. Mana

Per side (`$db4c`):
- +1 every other frame (when `$3b222` != 0), both sides;
- +`$3b20c[level]` per settlement every 8 frames (only level >= 4 earns; castle 20);
- +/- combat transfers (section 3.5), floor -250.
Verified: side mana 774/774 frame transitions, population 774/774, town counts 800/800 (26 frames
excluded because a merge/fight changed totals mid-loop).

Power costs = unlock thresholds `$21984[]`, each behind the gate in terrain.md section 4 (mana >=
cost, not armageddon, not paused, the side's power bit; paint mode skips it):

| routine | power | cost | score bonus (`$36cea`, human only) |
|---|---|---|---|
| `$116fa` / `$1186c` | lower / raise land | needs 10; pays 4*points_changed + 10 (`$37f8a`) | - |
| `$111be` | papal magnet (needs a leader) | 200 | - |
| `$12350` | earthquake | 2500 | 25 |
| `$12a14` | swamp (30 tries in 7x7) | 5000 | 50 |
| `$12ba0` | knight (needs a leader; it gets +20 = 1 and a `$fe00` target, the magnet moves to it unless paused, the side loses its leader; a settlement holding it becomes a walker with its whole population next frame) | 7500 | 150 |
| `$1263c` | volcano | 10000 | 100 |
| `$11f6a` | flood (all heights -1) | 40000 | 250 |
| `$12d26` | armageddon (clears knights, `$3d524`=1) | 80000 | 5000 |

`$21984` = -250 (floor), 10, 200, 2500, 5000, 7500, 10000, 40000, 80000, 160000, 1999999. The mana bar
`$da52` positions the marker between the bracketing thresholds. Raise/lower can drive mana negative
because only 10 is checked before the charge.

Armageddon (`$3d524` != 0), per frame in `$db4c`:
- `$dec4`: both side magnets (`$3b228`, `$3b238`), `$3c4ca` and `$3d526` are set to cell $820 (32,32);
- `$e270`: every settlement is vacated whatever its land value: flags `(f & ~1) | 2`, +12 = +10 = 0,
  `$10366(e, 1)` releases its footprint (4.3);
- all walkers steer with `$f6b2` (3.2; rock is passable on the direct heading), so the populations
  meet at the centre and fight (3.5); the power gate and raise/lower refuse everything while it is
  on (`terrain.md` 4, `ai.md` 5).

Verified on an Armageddon cast by the computer (`ai.md` 5, run M: `M0.snap`, cast at frame 1066,
GAME LOST at 1506, human 0, evil 838) with `py/endgame/brawlcheck.py` over a `capframes.py` capture
of all 441 brawl frames: magnets **441/441**, the 20 settlements vacated on the first frame **20/20**,
no settlement after any frame **441/441**, the whole terrain map and overlay after the frame equal to
the entry state with the vacated footprints released **441/441**, side populations **421/421** (frames
without a fight or new entity). `fightcheck.py` from `M1.snap` (frame 1067) over the same brawl: 14
fights, rounds **12/12**, 2 resolutions (not modelled: the loser's mana went to -250, the winner's
rose by 3000).

## 6. Population, win/lose, score

`$db4c` end (`$ee3c`): if the human side's population is 0 or it surrendered (`$2287e` = side),
`$1c858(1)` (lost); else if the other side's population is 0 (or it surrendered), `$1c858(0)` (won).
Population bar `$d482`: height = pop*31/50000 + 1.

`$2287e` (surrendered side) is -1 after `reset_world_state` (`$bdee`) and is set to `$3affe` by GAME
SETUP > SURRENDER THIS GAME (`$1bafe`).

`$1c858(lost)` score screen: seven rows at `$225d8 + $2e*r`, "you" = entities whose side byte equals
`$3affe`, everything else "him":

| row | value (you, him) |
|---|---|
| GAME LOST / WON | `lost == 1` |
| BATTLES WON | `$3c514[side]` (signed words) |
| NUMBER OF KNIGHTS | entities 0..`$3c4e2`-1 with knight != 0 and str != 0 (any non-zero word) |
| NUMBER OF TOWNS | flags == 1 exactly, str != 0, sprite != $2a |
| NUMBER OF CASTLES | flags == 1 exactly, str != 0, sprite == $2a |
| YOUR SCORE | `ltoa` of the final score (`$18306`) |

```
score = $36cea
if battles[you] > battles[him]: score += 5000            ; signed
for bit in 8, $10, ... $100:                             ; earthquake .. armageddon
    if not (god[you].+14 & bit): score += 1000
    if god[him].+14 & bit:       score += 1000
if $219b0: score += (10 - god[him].+16) * 15             ; muls, signed
if lost == 0: score *= 10
if score < 500: score = 500
if score > 555555: score = 515090
```

(The clamp keeps the `divu #10` conversion at `$18336` from overflowing: inferred reason.) It draws one
button, TRY IT AGAIN after a lost conquest game (`$21d5e` != -1), else NEW GAME, and waits for a click
in it. Then: `$21efa` = 1 (no reader found); after a won conquest game `$1d0e6(score)` (terrain.md 3);
the **third protection check** at `$1d032`: if `$3c4b0` != `$21466 + $15151515`, clear `$219b0` (no
computer opponent) and the 25 words of `$22b4e` (footprint offsets) (both sides hold `$54ac0842`, the
loader's patch value, so the check passes on the crack); the human god record's ctrl = 0; and
`new_world(0, -1)`.

Verified: `py/endgame/score_diff.py 100 7`, **200/200** randomized `callcap` states of `$1c858` (entity
arrays of 0..120 entities, battles, sides, both power masks, the computer's +16, `$219b0`, scores up to
700000 or negative; compared all 7 rows, `$36cea`, the button caption, `$21d52`, `$3d528`, `$16ed4`
and no other byte outside the screen and stack; 157 scores unclamped). `real_scores.py`: **56/56**
fields over 7 real end states: win and loss by zeroing one side's strengths, a natural Armageddon loss
(no other change: evil won the brawl), an Armageddon win with poked strengths (50300), a win on world
2470 (71450), a surrender through GAME SETUP, and a custom-game loss (6115).

## 7. Other entity-array users
- `$12f84` / `$13372`: the two trail effects in slots $d1/$d2, spawned at frame $1000 and once when
  the entity table is full; they walk one cell every 8 frames, mark trees, swamp or rock beside the
  path and kill what they cross. They are not power effects. `systems.md` 1.
- `$d482`: query panel for the selected entity.
- Key checks, not checksums: at entity index $14 `$db4c` compares `$3c4c0` with `$21d4c+$14725836`,
  at index $12 the trace vector (read by the supervisor peek `$15fe2`) with `2*$21d54`; a mismatch sets
  `$3d524` (Armageddon) and both sides' ctrl = 1. Both constants equal the crack loader's key
  $54ac0842, so they pass (`systems.md` 2).

## 8. Snapshot contents

game_start.snap (frame 285): 8 entities. Good: 3 settlements (0 at (10,3) str 78 level 2, 1 at (6,4) str
63 level 3, 2 at (9,13) str 50 level 2) and walker 7 at (8,4) str 42 just emitted. Evil: 4 settlements
(3 (57,60), 4 (26,59), 5 (56,55), 6 (26,56)). Leaders: good = entity 2, evil = entity 5 (settlements
can hold the leader). Both modes = 1 (settle), magnets at $820. Mana 542 / 42; population 191 / 78.
g90.snap: 13 entities; 5 new walkers/settlements (7..12). Evil mana stays near 0 because the computer
spends it on raising land. late1..4.snap: without input the array barely changes (the 400-frame run
from game_start is the evidence used here).

## 9. Scripts (`py/`)
- `dument.py <snap>`: print the entity array.
- `capframes.py <snap> <n> <out>`: capture RAM at entry/exit of `$db4c` for n frames.
- `people_model.py <capture>`: Python model of section 4/5 rules and the per-field match report.
  Regenerate: `python py/capframes.py $POP_WORK/game_start.snap 400 run400.bin; python py/people_model.py run400.bin`
  (a 21 MB capture; the one used here is kept at `$POP_WORK/agents/people/fr/run400.bin`).
- `fightcheck.py <snap> <n>`: forces Armageddon and checks `$1063a` rounds against the model.
- `repl.py`: interactive REPL driver.
- `walker/` (data in `$POP_WORK/walker/`): `walker_ref.py` models `$18198`, `$18206`, `$f2f4`, `$fe00`,
  `$f6b2` and the `$ef4c` dispatch; `walker_diff.py 400 7` the callcap corpus (2400/2400);
  `capcalls.py <snap> <n> <out>` records every live `$ef4c` call; `livecheck.py <calls> [<frames>]`
  checks live decisions and per-frame walker cells; `quirk.py` counts decisions a full 8-way scan
  would change; `pause_study.py` the flag-$20 pauses; `campaign.py`, `campaign2.py`, `mkmode.py` are
  the UI-driven play that made `snaps/near`, `front`, `gather1`, `fight1`.
- `endgame/` (data in `$POP_WORK/endgame/`): `score_ref.py` the `$1c858` model, `score_diff.py 100 7`
  (200/200), `real_scores.py` (56/56 over the 7 end states), `next_diff.py 60 3` (65/65), `ui_next.py`,
  `ui_names.py` (45/45), `boot_check.py` (35/35), `placement.py` (28/28), `brawlcheck.py <capture>`
  the Armageddon brawl (section 5; capture `$POP_WORK/endgame/brawl/M460.bin` from
  `capframes.py $POP_WORK/ai/M0.snap 460`); `win1.py`, `armend.py`,
  `armwin.py`, `surrender.py`, `customlose.py` make the end states; `typename.py`, `startgame.py`,
  `next1.py`, `brief1.py`, `retry.py`, `setupseed.py`, `boot_mode.py` drive the screens.
- `powers/` (data in `$POP_WORK/powers/`): `powers_ref.py` models the six powers, `$fe00`, `$feca`
  and `$108b8`; `pw_diff.py 40 2026` + `pw_diff.py 40 77` the callcap corpus (2305/2305); `cast.py`
  and `knight_scn.py` the UI casts (entry/exit snapshots compared on the full state); `live.py <snap>
  1100 retarget merge resolve` the knight's natural calls; `ktrack.py` prints knights and targets.

## 10. Open questions
- The `$ef4c` writes after the decision (settle, merge, fight start, occupancy and visit counts, the
  lower request on a `$42` cell) are checked only through the frame-by-frame walker cells, not
  diff-tested on their own.
- A knight merging into a friendly walker never happened in play (proven by `callcap` only), and the
  non-knight take-over of a town in `$108b8` (`$10366` release/claim) is not modelled.
- Fight mode drew only 5 human "attack enemy" decisions in the live run (the bridge brought walkers
  mostly into contact with their own side).
