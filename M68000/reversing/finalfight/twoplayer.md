# Two players, Guy and Haggar, and player versus player

How a second player enters the game, what changes in the rules when two players are in, how the players hurt each other, and what Guy and Haggar do differently from Cody (`player.md` is Cody's catalogue). Evidence tags as in `kernel.md`: **[R]** read in the ROM listing, **[L]** checked live in MAME with a count, **[S]** read from a saved state, **[I]** inferred. `A5 = $ff8000`; player 1 is the record at `$ff8568` (`1384(A5)`), player 2 `$ff8628` (`1576(A5)`), byte `+19` is the player index (0, 1) and `+20` the character (0 Guy, 1 Cody, 2 Haggar). Scripts, states and the gate list: `py/twoplayer/README.md` (`py/twoplayer/py/char/gates.py` 26 gates, `py/twoplayer/py/pvp/gates.py` 14 gates). Every run is driven through the ioport (`lib.lua` fields, P2 included) from a cold boot or from a saved state; where a bot plays, `FF_BOT_GOD` tops the health word up each frame and says so in the claim.

## Credits, start and the select screen

- **Credits.** Coin 1 and Coin 2 add to the same credit word `76(A5)`: two Coin 2 pulses gave 2 credits and `1 Player Start` then left 1 [L 1/1]. `$11ea` (the start of a game, reading the start buttons through `$850`) sets `127(A5) := 3` and adds 2 to `21616(A5)` when the 2-player button is down, otherwise sets `127 := 1` and adds 1 [R]. A cold-boot 2-player start (frame 1150, `2 Players Start`) took both credits (2 to 0), set `127 = 3` and showed PLAYER SELECT with both players' records marked in use (`+0 = 1`, lives 2) [L 1/1].
- **Select screen.** The P1 cursor starts on Guy, the P2 cursor on Haggar (screenshot, 1/1). One press moves a cursor one step. A cursor skips the character the other player is on or has locked: with P1 on Cody, P2 Left went Haggar to Guy; with P1 locked on Guy, two P2 Left presses ended on Haggar (the cursor wrapped past Guy) [L 2/2]. Two players therefore never share a character. The chosen index ends in `+20` of the record; `+56` and `+92` follow the `$a124` row (`$a10a`: `92 := data pointer`, `56 := box base`, then `$a2d2` adds `+$60` and the rank). Live: Guy `+56 = $10b76`, `+92 = $1105e` (`$10ffa + $60 + rank 4`), Cody `$12910` and `$12be4`, Haggar `$14cfa` and `$14fb2`; all three start at hp `$90` [S/L 3/3]. The code that steps the cursor (`$15b28`, `$15b36`: `129(A4)` wraps 0 to 2; `$15b4a` refuses a step onto the other player's value) is in the player controller tasks (`$1551e` for player 1, `$15d92` for player 2, each one a task whose record is `$ff1204` / `$ff1244`), but `129(A4)` stayed 0 throughout the cold-boot select, so where the first select screen keeps its cursor is not located [I].
- **Player 2's inputs.** The ioport fields `:IN1` "P2 Right / Left / Down / Up / Button 1 / 2 / 3" arrive in `94(A5)` bits 0 to 6 (`01 02 04 08 10 20 40`) and are copied into P2 `+130` the same frame; the P1 control (`92(A5)` to P1 `+130`) agreed [L 7/7 and 2/2]. `+130` has the same bit layout for both players (`player.md`).

## Joining during play

With one player in the game, a coin and `2 Players Start` (frame 2300 and 2330 of a Cody game) [L 1/1]: `127(A5)` goes 1 to 3 on the press, the credit goes 1 to 0 and `21616` gains 1. A PLAYER SELECT box with a 5-second countdown and a portrait appears in player 2's HUD slot (before the join the slot shows INSERT COIN) while the game keeps running. When player 2 confirms (Button 1 at frame 2420) the record becomes live (`+0 = 1`, state 2 sub 2 = the drop-in, hp `$90`, lives 2, character Guy, the default cursor) and the HUD shows the name and a "2P" arrow. TIME went from 29 to 30 at the drop-in: `$30` is the area-0 value of the table `$5210`, so a join reloads TIME [I, one sample]. The difficulty rank did not change (5 before and after). The join test is `$2dc6` with the per-player routines `$2dd8` (P1) and `$2e18` (P2): with the credit mode flag `130(A5)` clear a latched start press sets the bit; otherwise it needs a credit (`126(A5)` or `76(A5)`), takes one (`subq.w #1,76(A5)`, `$2ca8`/`$2cee`) and sets bit 0 or bit 1 of `127(A5)` [R]. `$4f6e` clears `127(A5)` at the end of the game and the post-game task `$5644` sleeps while it is non-zero [R].

## The two masks

`127(A5)` is the **joined** mask: bit 0 player 1, bit 1 player 2, set by the start press. `21610(A5)` is the **in use** mask, recomputed every frame by `$61e24` as `(P1.+0 & 1) | ((P2.+0 & 1) << 1)` (the first instructions of `$61e24`, [R]); in the join run `127` was 3 at frame 2340 and `21610` became 3 at frame 2430, when player 2's `+0` became 1 [L]. The two differ while a player is in the continue scene or still choosing. The attack-token tables test `127`; the health, damage and data-pointer variants below test `21610`.

## What two players change

| site | test | effect |
|---|---|---|
| `$27b60` token request | `127 == 3` | cap table `$27bc8` instead of `$27b88` [R, L] |
| `$5f46` script spawn gate | `P1.+0 & P2.+0` | entries with byte 15 set spawn only with both records in use [R, L] |
| `$2cd94` kind 3 init (ANDORE family) | `21610 == 3` | `92(A6) := $3124c` instead of `$3112c` (`ai.md` has the health and damage columns) [R] |
| `$6b00`, `$6b7c` (hazard `$6af2` and `$6b64` damage to a player) | `21610 == 3` | damage row `+$20` or `+$60` [R] |
| `$9e10` (`$9df6`, a player landing after an enemy's throw) | `21610 == 3` | damage row `+$20` [R] |
| `$4fd6`, `$5046` | `21610 == 3` | when the per-player counters `22162 + 22163(A5)` sum to 9 (`$5046`: 16): with both players in, equal counts set `6(A5) := 0` and unequal counts `4`; with one player in, `2`; any other sum `0` (`transitions.md`) [R] |
| pool 4 kind 0 (`$3d3d6`; DAMND): `$3d45a`, `$3dcc0`, `$406f8`, `$40a94` | `21610 == 3` | hp `$12c` (300) becomes `$1c2` (450); data `$40572` becomes `$40632`; attack table `$3edea` becomes `$3eeea`; target choice [R, L for hp and data] |
| pool 4 kind 1: `$40cb4`, `$428ce`, `$42ad8`, `$41a70` | `21610 == 3` (the last `== 2`) | hp 300 becomes 450; tables `$42e58` / `$42ed8`; data `$45d8c` / `$45e8c`; `$41a70` picks `$42dd8` only for player 2 alone [R] |
| pool 4 kind 2: `$45fb4`, `$460fc`, `$463ac` | `21610 == 3` | hp 300 becomes 450; threshold `$50` becomes `$78`; table `$463d0` / `$463f0` [R] |
| pool 4 kind 3: `$46d24`, `$4766a`, `$4a8a6` | `21610 == 3` | data `$48956` / `$489d6`, tables, a roll [R] |
| pool 4 kind 4: `$4be90`, `$4c9c0`, `$4caac`, `$4d3f0` | `21610 == 3` | hp 500 becomes 650; tables; data `$4e800` / `$4e920` [R] |
| pool 4 kind 5: `$4ea70`, `$4f17a` to `$4fd12`, `$50724`, `$5078c` | `21610 == 3`, bit 0 | hp 600 becomes 900 (and 300 becomes 450); target by mask (one player, the other, or random between both); data `$510ec` / `$5114c` [R] |

The handler containing a pool-4 site is found by address from the table at `$5a52` (`boss.md`). `$41a70` compares the mask with 2 where every sibling compares 3, so the "two-player" table is used there for player 2 alone; whether that is an original slip is [I]. Nothing else reads either mask: the alive caps `$3e88` have no two-player term (no read of `127(A5)` or `21610(A5)` in `$3e88-$3fe2`) [R, all 87 reads of the two bytes listed].

**Script entries.** Byte 15 of a script entry is the two-player flag: `$5f46` refuses the entry unless `P1.+0 & P2.+0` is non-zero; a refused entry is dropped (not queued) and, when its count flag is set, `12(A6)` is decremented (`$5eca`) so a wait-for-clear segment does not wait for it [R]. The stage 0 area 0 segment (trigger camera `$3f0`) has five entries of which `$706c4` (J, kind 1, x 976, y 33) is flagged. Played with the same bot, one player spawned the four unflagged entries and not `$706c4`; two players spawned all five [L 5/5, `py/pvp/p2_entries.py`]. Over all stages the parser (`py/ai_kind45/script.py`, set `$5f7e`) finds 24 flagged entries of 180 (stage 0: 1; stage 1: 6; stage 2: 4; stage 3: 8; stage 5: 5) [R].

**Targeting.** Every pool-2 fighter that acquires a target takes the nearest live player by |dx|, player 1 only when strictly nearer (ties go to player 2). With two real, moving players: 70 of 70 acquire events in two runs agree (33 chose player 1, 37 player 2) [L, `py/pvp/target_check.py`; kinds 0 to 2: `+144` is the word that holds the index, `+148` the record, `+150` the re-target cooldown (180)]. At spawn `+148` already holds a player record (`$28c3c` default: player 2 if its record is in use, else player 1) [L].

**Attack tokens.** `$27b5a` grants a token iff `$ff115a < word[table + 2 * rank]`, `rank = 168(A5)` (capped at 31); a grant adds 1 to `$ff115a`. The table is `$27b88` unless `127(A5) == 3`, then `$27bc8`:

One player, `$27b88`: cap 1 for ranks 0 to 6, 2 for 7 to 12, 3 for 13 to 18, 4 for 19 to 24, 5 for 25 to 29, 6 for 30 and 31. Two players, `$27bc8`: cap 2 for ranks 0 to 5, 3 for 6 to 10, 4 for 11 to 15, 5 for 16 to 20, 6 for 21 to 25, 7 for 26 to 29, 8 for 30 and 31 [R, both tables read from the ROM by the gate].

Live: breakpoints on the entry and the exits of `$27b5a` paired each call with its result, 86 of 86 agree with the rule (20 from `ff_enemies` with `127` poked to 1 and 3, which showed the cap 2 against 3 at rank 8; 66 from a fuzz of tokens, rank and `127`, with both tables and every grant and refusal case) [L, `py/pvp/token_decide.py`]. The touch path `$27b00` takes a token without the cap (tokens reached 2 at rank 4 with cap 1; 445 such grants in 2,350 frames) [L].

**Health and damage at spawn.** For the pool-2 fighters of stage 0 (kinds 0, 1, 2, 4, 5; 17 kind, character and level combinations) `+24` and `+92` are identical with one and two players [L 17/17]. The pool-4 boss (record 7) had hp `$12c` and `92 = $405de` (`$40572 + $60 + 12`) with one player and hp `$1c2` and `92 = $4069c` (`$40632 + $60 + 10`) with two [L 1/1; the two runs spawned it at ranks 12 and 10, so the difference is the code's]. Row for row the two tables differ (rows 0, 1, 2 at level 10: 16, 24, 34 against 13, 20, 28).

## Player versus player

Hit resolution (`$6396`: `$6f6c`, then `$7766`) tests the two players against each other after the fighters. `22195(A5)` is 0 in play (set only by the attract-mode script at `$18330`).

```
pvp():                                            // $7766
  if !(w[21258] && w[21362]) return               // both lane-window headers valid: words 6/8(A0) = $fff4 / $0009 [L], airborne $ffe8 / $0018 [R]
  if (w[P1+90] != 0) != (w[P2+90] != 0) return    // one on a prop level, one on the ground: no contact
  if try(P1 attacks P2, A0 = 21250): hit(D6 = 0)  // $77e0, then $7932
  if try(P2 attacks P1, A0 = 21354): hit(D6 = $80)
try(A, V):  45(A) > 0 (a grab id, bit 7, fails) && 148(V) == 0 && 97(V) == 0 && 44(V) != 0 && 139(A) == 0
            && d = (gy(A) - 90(A)) - (gy(V) - 90(V)) in [-12, +9]       // victim ground line - attacker's in [-9, +12]
            && attack box 112(A) overlaps hurt box 120(V)                // $7932, centres 116/118 and 124/126
hit(A, V):  if 22195(A5) == 0: 148(V) = $64      // $782a: 100 frames of immunity
            60(V) = A; 22(V) = 45(A); 63(V) = type of the attack box (byte 11 of the box, bit 7 = hard)
            soft box:  24(V) -= 1 ($7a18); sound $7b10, spark $7b18 (or $7b30), 23(A) = 23(V) = 6, 104(A) |= 1, 160(A) = $2d, 62(V) = 46(A) ($7a38)
            hard box (weapon ids 10 to 12): 63 &= $7f; 24(V) -= max(1, damage byte >> 3) ($7a1e) [R]
            unless 290(A5): award $7aa8 (word table by attacker character and box row, D6 bit 7 = player 2), then $2934
clash $78c6: both attack boxes have bit 7 and overlap ($7984) -> both stunned (23 = 6), 60 cross-linked, sound $f, no damage [R]
$2934:      pushes (P2 +24, +26, +28) into the player-1 HUD ring 644(A5) and (P1's) into 772(A5): each player's HUD shows the partner as an enemy bar
```

Live (Cody P1, Haggar P2, 40 px apart, `+148` cleared each frame where noted) [L, `py/pvp/gates.py`]:

- Every non-hard attack takes exactly 1 hp: 9 of 9 hits of the Cody chain (ids 1, 2, 3), each with the attacker's award from the box row (100, 300, 500) added to the attacker's score; 3 of 3 for player 2 jabbing player 1 (+100 to player 2, player 1's score stays 0).
- After a hit `+148 = 100`, counting down one per frame (100, 99, 50, 1 sampled); with continuous jabbing the hits land exactly 100 frames apart (100 and 100) [1/1].
- The special spin (`+139`) passes through the partner: 49 frames in sub `$10` with the partner's hp unchanged [1/1]; jump attacks do hit (ids `$0d`, `$0c`, 1 hp each, +100 and +50).
- Depth: a hit lands iff the victim's ground line minus the attacker's is in [-9, +12]: 22 of 22 placements (-16 to +16; the high lane clamps at `$3f`, so the +12 edge was tested with both players on low lanes).
- A partner can kill: with player 2 at hp 0 one jab gave hp -1, the fatal knockdown (state 2 sub 6 for 92 frames), state 4 for 60 frames and the respawn at hp `$90`; player 1 got only the hit award [1/1].
- Screenshots: after a P1 hit the P1 HUD shows a HAGGAR bar and the score 100; after a P2 hit the P2 HUD shows a CODY bar [2/2].
- A kill of a fighter by player 2 awards player 2 (Bred +1000, code `$07`) and player 1 nothing [1/1].

Not exercised: the hard-box divisor, the clash `$78c6` (both players need a hard attack box at once), the airborne lane window, and who gets the `+105` credit when a partner's hit reaches a fighter.

## Guy, Cody and Haggar

Each character is driven from a state in which the character was chosen on the real select screen, on a dummy Bred (hp `$300`, refilled below `$180`, moved next to the player), with `+97 = $ff` so the player cannot be hit. Expectations come from the ROM (`$a124` rows, attack boxes, the player's own `+92`); `py/twoplayer/py/char/gates.py` compares them (26 of 26).

| | Guy | Cody | Haggar |
|---|---|---|---|
| chain limit `$be92` (hits) | 8 (5) | 6 (4) | 4 (3) |
| chain ids | 1, 1, 2, 7, `$0d` | 1, 1, 2, 3 | 1, 1, 2 |
| chain damage | 6, 6, 8, 8, 14 | 10, 10, 10, 16 | 18, 18, 18 |
| chain awards | 100, 100, 200, 250, 350 | 100, 100, 300, 500 | 100, 100, 800 |
| chain hits matching the ROM (id, damage, type, award) | 5 of 5 | 4 of 4 | 3 of 3 |
| jab animation (frames) | 12 | 14 | 22 |
| walk (px per frame, right; down) | 2.067; 0.783 | 1.917; 0.783 | 1.817; 0.683 |
| jump | vx `$300`, vy `$600`, g `$48`, apex +61, 49 frames, landing 7 | vx `$2d0`, same | vx `$260`, same |
| jump attacks (damage) | ids 3 (12), 8 (8) | `$0d` (12), `$0e` (8) | 3 (8, type 3, +300), 4 (20) |
| jump-attack hits matching | 5 of 5 | 4 of 4 | 6 of 6 |
| special | 42 frames, vy `$600`, g `$55`, apex +51, boxes `$0f` to `$18`, 20 damage, type 7, +300 | 49 frames, vy `$700`, apex +70, ids 6 to 9, +400 | 46 frames, grounded (no vertical motion), ids 6 and 9, 20 damage, +400 |
| special hits matching | 4 of 4 | 4 of 4 | 4 of 4 |
| grapple strike damage (counters 2, 4, 6; `$db6e`) | 8, 14, 24 | 9, 16, 28 | 10, 18, 36 |
| strike hit type (`$d8a6`) and award (`$d86e`) | 1, 1, 3; 100, 200, 300 | same | 0, 0, 3; 200, 300, 400 |
| throw | landing -30 | landing -40 | pile driver -50, type 6, +1000 |
| throw turns the player on | the press away from the facing | same | the press toward the facing |

Further measurements: the random drives (2 seeds of 3,000 frames per character) matched the ROM row on every attack-box hit (18 of 18 Guy, 28 of 28 Cody, 30 of 30 Haggar); walk speed ordering is Guy > Cody > Haggar (the +14 up value clamps at the lane limit when the start lane is high, so only the down speed is listed). The ground line axis: **Up raises both `+10` and `+14`, Down lowers them**, 0.8 px per frame unclamped (Cody from `sb_boss` at camera `$aa0`, stage 0 area 2, one input held and the lane poked to `$28`: Up for rel 10 to 40 gave 40, 44, 48, 52, 56, 60, 63 at rel 10, 15, ..., 40, Down for rel 60 to 90 gave 63, 59, 55, 51, 47, 43, 39 at rel 60, 65, ..., 90; `+10` and `+14` equal throughout; clear of both clamps (`updown15.lua`, Up and then Down for 15 frames from `$28`): 40 to 52 and back to 40 in `sb_boss`, 40 to 51 and back to 40 from the stage 0 area 0 state, both words moving together; 6 of 6 runs in the two states; Up held 60 frames from `$10` ended at `$3f` and Down held 60 frames from `$3f` ended at `$10`, the lane limits) [L, `py/twoplayer/py/char/plans/updown30.lua`].

**Grapple differences.** Guy and Cody use the sub-table `$cd24`: a new Button 1 with no direction is a strike (`162 += 2`, sub 6), the direction toward the facing sets `152 = 1` (forward slam, no turn), any other direction `152 = 0` (back throw, the player turns); the throw lands on the victim through `$3f7a` (Guy flat 30, Cody and Haggar flat 40: `$3fd8`). Measured: Guy and Cody turn on the away press and not on the toward press, 4 of 4. Haggar uses `$cfb8` and the selector table `$dab0`, which is the inverse: toward the facing gives `152 = 0` (his sub 8 then turns him, `$d102`), away or up or down gives `152 = 1`; measured 2 of 2. His states: sub 2 entry (6 frames), sub 6 the hold loop (he walks with the victim, `$c016`, and the special test `$bdf4` runs), sub `$a` a strike, sub 8 the pile driver (29 frames against 26 for the others, `$d182` award code 7), sub `$c` the jump. In the hold, Button 2 starts the jump (vy `$600`, g `$40`, apex +69, 54 frames); a new Button 1 within 18 frames of takeoff (`$da34`) sets `165 = $ff` and the landing slams the victim (`63 = 5`, award code `$13`, +1200): -70 damage, 3 of 3 runs with the press at 8, 14 and 20 frames; without the press the victim is released at landing with no damage [L 1/1]. Where the -50 and -70 come from (`$1b428`) is not read.

**Guy's wall jump** (character 0 only; `$acb2` skips it for the others). In the jump's air step (`$ac8e`) the probe `$7e1c` looks 16 px ahead along the horizontal speed; a hit with a pool-a prop (terrain result `+88 = 3`, `+102` = the prop) calls `$bab6`, which needs `190(A5) != 6`, a latched or new Button 2, `vx != 0` and `vx` pointing the way he faces, and enters sub `$16`:

```
sub $16 ($b6ec): step 0: 165 = 169 = 0; 30 = 9; animation $fc4c
                 step 2: if Button 2 not held or Down held: sub 4 (fall)
                         if a new Button 1 ($bb20): 165 = 1 (attack)
                         if 165 | 169 or --30 == 0: bounce ($b75e): flip the facing, 161 = 0
bounce, facing right:  no direction: vx = -$480, decay 0,   vy = $300, g = $38
                       Left held:    vx = -$680, decay -16, vy = $380, g = $58      [facing left: $680/$480, [R]]
```

Live: Guy pinned against the oil drum (kind 8 at x `$2f0`, ground line `$3f`) at x `$2b7`, jump right plus a second Button 2 held 14 frames: sub `$16` for 9 frames of grip, then `vx = $fb80`, vy `$300`, facing flipped, 153 px of travel; with Left held `vx = $f980`, decay `$fff0`, vy `$380`, g `$58`; with Button 1 in the grip the bounce came after 4 frames with `165 = 1`; with Down held he fell at once [L 4 of 4 branches]. Cody and Haggar never entered sub `$16` in the same runs (0 of 2) [L].

## Not proven

- Where the first select screen keeps its cursor (above) and which routine decides the P2 default character on a mid-game join.
- Haggar's back grab at the chain end (`$be9e`, third press with Left held): one trial, no grab, the chain went on to its normal third hit with the facing turned; the scan `$bf0e` was not reached. Probably the facing was already left when `$be9e` ran, so Left read as "toward" (the branch `$beb8`) [I]; prove with a write tap on `46(A6)` and a breakpoint on `$be9e` (mask `A6` with `&ffffff` in debugger expressions: the sign-extended `A5`-based addresses read 0).
- The damage source of Haggar's pile driver and jump slam (`$1b428`), and the fatal-knockdown path for a player thrown by Haggar.
- Pool-4 kinds 1 to 7 and kind 3 (ANDORE) two-player variants beyond the table above: [R] only; DAMND's hp and data pointer are [L].
- PvP weapon hits (the divisor), the clash `$78c6` and the airborne lane window: [R].
- Whether the join reloads TIME from the area table (one sample, the value was the area's start value) and what TIME zero does with two players (in one early bot log both players' hp became `$ffff` in the same sample after the bot stood 13,000 frames behind a prop; not repeated).
- Guy's and Haggar's weapon use and death sounds (`$22`, `$23`, `$24`): [R] only.
