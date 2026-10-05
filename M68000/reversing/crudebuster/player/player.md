# Crude Buster: the player and the shared combat engine

Set `cbuster` (World FX), MAME 0.289, decrypted program image `scratchpad/crudebuster/rom/cbuster_main.bin`; every address is a 68000 address of that image.
Claims carry a count and the script that reproduces it (`py/gates.sh` runs all of them from scratch, about 1.5 minutes, up to 5 MAME processes). Anything read from the code
but not run is marked *read*. Frame numbers are logic frames (`$8004a` steps, one per VBL, 58 Hz in play). A button level set by the Lua driver after frame N is first seen by the game
in frame N+1; "frame 0 of a move" below is that frame.

## Decisions in one page

- The player is not an object of the three pools: it is two fixed 128-byte records, P1 `$80100` and P2 `$80180`, updated by `$7626` -> `$7650` -> (mode 0) `$a252`. The two records run
  identical code: P1 and P2 produced identical state sequences in 136 of 136 frames for the jab chain, both jumps and the grab (`py/p1p2_compare.py`). The "character" is the slot, byte +2
  (0 = P1, 1 = P2): it selects only the sprite tables (`$74000[+24][+25][+27][+21][+2]`), the HUD portrait and the join/respawn placement. Combat data does not depend on it. The hero names are
  not in the ROM text (the string table `$20ab-$27ff` has `PLAYER1`, `PLAYER2`, `CONTINUE?`, `PUSH START!`, `INSERT COIN!`, `GAME OVER!`, `NAME`, `NICE FIGHT!`, `STAGE CLEAR`, the staff roll).
- Three buttons, one move set, no special attack and no run: **button 1 = attack (3-hit jab chain)**, **button 2 = jump** (and a roll when pressed with a down-diagonal), **button 3 = grab / throw**
  (pick up props and enemies, then throw them). Checked: b1+b2, b2+b3, b1+b3 and all three pressed together resolve to b1 > b3 > b2 (4 of 4 trials, `lua/plans/moves2.lua`); double-tapping
  a direction does not change the walking speed (2 trials, `lua/plans/dash.lua`). No double-button special exists in the code (the input branches in every action handler test b1, then b3, then b2).
- Everything hostile touches the player through one of five writers of the health byte (+19, maximum `$38` = 56 = seven bar cells of 8): pool C melee hit boxes `$fc9e` (damage `4 x table`), contact
  `$f76e`, pool B projectiles `$1010a`, grab drain `$d75c`, and the player's own fall handlers `$d442`/`$d544`. 83 of 83 logged decrements match the tables below, 0 mismatches.
- Enemies do not run their own hit tests for the player: the pipeline helpers `$2331c` -> `$f82e` (player hits enemy) and `$f4f4` (contact), and the pool C hit-box objects through `$fa10`,
  are shared code. The geometry (`R, L, B, T` boxes, one overlap chain) is verified: player-versus-enemy 397 tests, 71 hits, 0 disagreements (`py/hitbox_gate.py`); enemy melee 2628 calls, 13 hits, 0
  disagreements (`py/melee_gate.py`).
- There is no extra life from score or items (no writer of +20 except the death decrement and the initialisations: *read*, whole-listing grep), no friendly fire from punches (verified, below),
  a level timer that kills both players at 0, and a continue prompt of 10 digits.

## 1. The player record (`$80100`, `$80180`; stride `$80`)

Fields are named from the code that reads and writes them, from the HUD routines that print them (`$3d66` health cells, `$1ab2` number printer descriptors, `$3e84` portrait) and from logs.
"v" = verified by a run (script named), "r" = read from the code.

| off | name | content | evidence |
|---|---|---|---|
| +0 | flags | bit 7 active; bit 6 initialised for this level (`$a3cc` sets it); bit 4 blink = invulnerable, toggled every frame while +54 > 0 (`$a6f2`/`$a6fe`); bit 3 created (`$76ae`, `$1556`); bit 2 victory pose; bits 1-0 **mode**: 0 playing, 1 continue prompt, 2 game-over wait, 3 initials entry (dispatch `$769e`: `$7982`, `$79f0`, `$7d72`, `$7e1c`) | v: P1 `$80`, `$88`, `$c8` at join (`py/gate_2p.py`), `$d9` at the continue prompt (`py/gate_lives.py`); r: modes 2, 3 |
| +1 | busy flags | bit 7 move initialised (animation running), bit 5 busy (blocks new moves), bit 4 jump flag, bits 3, 2, 1, 0 per-move sub-state (bit 2: jump attack) | v: `$24`, `$a4`, `$34`, `$b4` seen in the move logs |
| +2 | slot | 0 = P1, 1 = P2 (written by `$7626`); selects the sprite table and the portrait | v: `py/p1p2_compare.py` |
| +3 | state | 1 while the level-start entrance runs (the jump through the wall, frames 780-879 in level 1, +90 bit 6 set, input ignored), then 0 | v: `lua/reclog.lua` run, `+3` 1 -> 0 at frame 879 |
| +4 | action | 0-7 walk direction (up, up-right, right, down-right, down, down-left, left, up-left; table `$a5c0` maps the held nibble), 8 idle, 9 hurt flinch, `$a` death, `$b` flying (knocked or thrown, also by the partner), `$c` landed and rising, `$d` held by an enemy. Handler table `$a394` | v: 2, 6, 1, 7, 8 (walk logs), 9 (every melee hit), `$a` (timer kill), `$b`, `$c` (partner throw), `$d` (grabber type 4 variant 1); r: the up/down/diagonal handlers |
| +5 | sub-action | 0 none/walking, 1 grab (b3), 2 attack (b1), 3 jump (b2), 4 throw (b3 while carrying), 5 roll (b2 on a down-diagonal), 6 fall off a ledge, 7 turn-around attack, 8 ledge hop (up/down handlers only). Every action handler has a table indexed by +5 (`$a9de`, `$b000`, `$b53a`, `$b932`, `$bc82`) | v: 1, 2, 3, 4, 5, 7 (`py/movetable.py`); r: 6, 8 |
| +6 | jump phase | inside sub-action 3: 0 rising, 1 kick (b1 pressed), 2 air grab, 3 landing, 4/5 carrying variants (`$dba4` table) | v: 0, 1, 3 in the jump logs |
| +7 | facing | 0 right, 1 left | v |
| +8 | x | 16.16 fixed point; the word at +8 is the pixel | v: walking is exactly +1.0 per frame |
| +12 | y | 16.16; the body centre (the street is 448 = `$1c0`); in the air y = ground - height | v |
| +16 / +17 | held / pressed | copies of `$80051` / `$80050` made at `$bbe`: bit 0 up, 1 down, 2 left, 3 right, 4 button 1, 5 button 2, 6 button 3, 7 start | v |
| +18 | direction latch | last held direction while not carrying; picks the get-up variant after a hit | r |
| +19 | **health** | `$38` = 56 at start; 8 per bar cell (`$3d66`: cells at `$a0106` for P1, `$a013a` mirrored for P2) | v |
| +20 | spare lives | 2 at start with the default DIP; printed by `$1ab2` descriptor 4 (`$a0096`) beside the portrait; `$c3e8` decrements; below 0 -> mode 1 | v: 2, 1, 0 then continue (`py/gate_lives.py`) |
| +21, +22 | animation frame, tick | +22 counts ticks, +21 is the frame; a move ends when +21 + 1 equals +29 | v |
| +23 | reaction | written by the damage routines from tables; bit 7 = hit: `$a4a8` starts action 9 (bit 5 selects the longer knockdown variants) | v for bit 7; r for the rest |
| +24, +25, +27 | pose, variant, carry stage | +24 body pose (also indexes the body-box table `$e4d6`), +25 variant (the jab picks 1 or 2 at random through `$ea44` and `$ad00`), +27 carry class (0 empty, 1-3 from +26, 4 pick-up, 5/6 throw, 7, 8 carrying a can) | v |
| +26 | carry flags | 0 empty; `$80` heavy, `$c0` throwable, `$e0` weapon (copied from `$e876[prop type]` or `$c0` for an enemy or partner) | v: `$c0` for the can and the enemies, `$e0` for prop 8, `$80` for prop `$2c` (`lua/carrylab.lua`) |
| +28 | attack flag | the flag word of the attack-box record `$67000[+24][+25][+21][+7]`; the hit test runs only while it is non-zero | v |
| +29 | animation length | 2 for a jab; each b1 press during the move adds 2 (6 becomes 7) up to 7 | v |
| +31 | sound request | played by `$e1c` at the end of `$a252` when +87 bit 7 is set (for example `$4f` at the end of the entrance, `$14` landing, `$18` hard landing, `$46` start of a flinch) | v: `$4f` at frame 879; r: the others |
| +32, +36 | previous x, y | used to undo a move that hits a wall | r |
| +44 | ground y | y before a jump; the jump height is subtracted from it | v |
| +48 | x velocity | 16.16; jump +-1.75, roll +-2 (word), knock-back +-1 or +-4 | v |
| +52 | jump phase | 0..`$80` in steps of 4 per frame; index into the sine table `$eab0` | v |
| +53 | saved pose | pose before the jump or roll; restored on landing | r |
| +54 | invulnerability timer | `$140` (320 frames) after join, respawn and continue, `$14` after getting up; while non-zero bit 4 of +0 blinks and every damage routine skips the player | v: 320 frames for the join blink |
| +56 | counter | frames of pushing against a ledge (`$bf6c`) | r |
| +57, +58 | motion and state flags | +57 bit 7 airborne, 6 on a slope, 5 slope direction, 4/3 pushed against the right/left screen edge. +58 bit 7 holding something (+92 points to it), bit 3 holding the partner, bit 4 held by the partner or an enemy, bit 2 thrown by the partner, bit 1 dead (health reached 0), bit 0 knocked down | v: +58 `$80` after the can, `$88` holding P2, `$10` held (`py/gate_pickup.py`, `py/gate_2p.py`) |
| +60 | **score** | BCD, 4 bytes (`$8013c`), at most `$9999990`; printed by `$1ab2` descriptor 2 at `$a0e88`; cleared by a continue | v |
| +64..+70 | body box | R, L, B, T words, absolute; from `$e498` and the body-box table `$e4d6[+24]` | v |
| +72..+78 | attack box | R, L, B, T words, absolute, valid while +28 is set; from `$e56a` | v |
| +85, +86 | footstep | a dust puff (pool B type `$2b`, variant 18 or 19) every 16 walking frames, three offsets (`$da3c`) | r |
| +87 | event bits | bit 7 sound pending | v |
| +88 | event bits | bit 0 time-out kill (`$1308` sets it when the level timer reaches 0; `$a2e8` zeroes health, sets +58 bit 1), bit 2 forced pose (cutscene), bit 4 grabbed by an enemy | v for bit 0 (health to 0 written by `$a2f0` at the expiry frame), r for the others |
| +90 | scripted-move bits | bit 6 scripted entrance (input cleared in `$a442`), bits 0, 1, 3 side flags of the reaction | v for bit 6 |
| +91 | previous facing | a b1 press with +7 different from +91 and empty hands starts the turn-around attack (+5 = 7) | v |
| +92 | held object | longword pointer to the carried pool A/B record (`$00081400` for the first pool B record) | v |
| +96 | grabber | pointer to the enemy that holds the player (used by action `$d`) | r |
| +104..+117 | terrain probes | attribute words at the feet and ahead from `$ebb0` (map `$60000`), refined by `$f2e8`; `$a868` and `$a938` fill them | r |
| +120..+127 | initials / continue | +120..+122 the three initials (letters `A-Z 0-9 ! , . - ? &`, table `$7fba`), +123 mode bits, +126 continue digit or current letter, +127 tick or cursor | v: digit 9..0 |

The first frame of a level in P1's record is also fixed by `$15d0`: x `$170`, y `$1c0` (level 5: `$7c0`), then the scripted entrance moves it to x `$187`. Respawn (`$c41c`) puts the player at
scroll x + `$80`, scroll y + `$c0` (levels 2 and 5 subtract `$20` inside two scroll ranges), full health, timer `$300`.
The player's x is clamped to [scroll x + `$10`, scroll x + `$f0`] and pushes the scroll when it passes scroll x + `$90` (`$a712`; x - scroll = `$8f`..`$90` while walking right, `lua/plans/walk2.lua`).

## 2. Modes, credits, join-in, timer, continue, game over (v unless marked)

- **Coins and credits** (`$1148`, VBL): coin lines 1 and 2 add per the DIP table `$11f8` / `$1208` (coins, credits): index = inverted DIP bits, default (1,1). Credits are BCD in `$80032`, at most 99.
- **Start**: `$e3c` (VBL): with a credit and no game running, the start button that fired sets `$80100` or `$80180` to `$80`, takes one credit, sets `$80040` bit 7 and restarts the stack
  (`jmp $696`). During a game (`$ee8`) the same button of an *inactive* player joins: record `$80`, credit -1 (blocked while `$80040` bit 3/5/6 or `$80041` bit 3 is set: cutscene, game over, ending).
  Join in play: P2 start pressed at frame 960 -> frame 961 `$80180 = $80`, credit 1 -> 0, frame 962 `$76ae` initialises it (health `$38`, spare lives 2, position = P1's x and y, 320 blink frames).
  8 of 8 checks in `py/gate_2p.py`.
- **Level timer** (`$1308`): BCD word `$80042` starts at `$300` (table `$12f8`, the same for all levels, reset by every respawn: `$c4a0`) and loses 1 every 63 logic frames; printed at the
  top right by `$3c68`. At 0 `$80158` and `$801d8` bit 0 are set: both players' health is zeroed on the next update. Checked: with the timer held at 1, health is written 0 by `$a2f0` at the expiry
  frame (`lua/reclog.lua`, `CB_POKES=80042:0001:w`, frame 1032). The timer stops during the ending (`$80040` bit 6) and the continue prompt (`$8005a` bit 6).
- **Death** (action `$a`, handler `$c334`): 12 animation frames of 16 ticks = 192 frames, then `subq.b #1,+20`: with spare lives left the player respawns (the health refill `$c47e` came 200 and 208 frames after the
  fatal hit in the two logged deaths: 192 animation frames plus the flinch), otherwise +20 is clamped to 0 and +0 gets bit 0 (mode 1). Spare lives went 2, 1, 0, then mode 1 at the third death (`py/gate_lives.py`).
- **Continue prompt** (mode 1, `$79f0`, `$7b2e`): digit +126 starts at 9 and drops every 63 logic frames; the screen takes two VBLs per logic frame, so every digit lasts 126 frames (9 of 9
  steps equal). While the digit runs the default selection is "yes": a start press with a credit and DIP "Allow Continue" (`$80054` bit 6 clear) continues: credit -1, `$76d0` re-runs the player
  start (health `$38`, score cleared, spare lives back to the DIP value, 320 blink frames). Observed: continue at digit 5, 6 frames after it appeared; credits 3 -> 2 (start) -> 1 (continue); health, lives, credit
  and score changed in the same frame (`py/gate_lives.py`, 5 of 5). Holding down moves the selection to "no" (`$8005a` bit 5, *read*); a button press on "no" ends the prompt. Without a continue the countdown
  ends in `$7e10` (record cleared; score below the 10th entry of the table `$80080`) or the initials screen (mode 3, `$7e1c`: 3 letters, left/right steps `$7fba`), `$80040` bit 5 (game over) and
  461 frames later `$80040 = 0` (attract). Measured: record cleared at frame 4981, bit 5 at 4982, attract at 5443.
- **Edge-latched start** (trap for scripts): `$80050` is cleared on the first VBL after each logic step and recomputed every VBL, so when a logic step spans two VBLs (the continue screen and other heavy
  screens) an edge that lands on the first VBL of the pair is lost. A single start press at digit 5 failed in 1 of 1 tries; pressing 2 frames out of every 5 worked (`lua/contlab.lua`).

## 3. Controls and moves

Walking is exactly 1.0 px per frame in the four horizontal directions (136 of 136 frames, `py/gate_move.py`). Up and down do nothing on level 1's street (68 of 68 frames: one lane); they are used on ladders and stairs
(action 0/4 sub-action 7, `$ca7e`, pose 7; level 4 shows y values `$160..$1c0` in 16-pixel steps). There is no run. The facing is set by the last horizontal direction pressed.

### Move table (P1 and P2 identical)

Frame data from the logs of the standard runs (`py/movetable.py`; boxes from the live record, checked against the static table with `py/atkbox.py`). R, L, B, T are offsets from (x, y) for a right-facing player (left-facing mirrors R and L);
y grows downward, so negative B/T are above the body centre. Each hit costs the enemy 1 HP; an attack box is only tested on frames where +28 is set.

| move | input | +5 | total frames | active frames | attack box (R, L, B, T) | notes |
|---|---|---|---|---|---|---|
| jab 1 | b1 (empty hands) | 2 | 12 | 6-11 | 40, 0, -8, -32 | 2 animation frames of 6 ticks; the hit is on frame index 1 |
| jab 2 | b1 during jab 1 | 2 | 24 | 6-11, 18-23 | 40, 0, -8, -32 | +29 becomes 4 |
| jab 3 (finisher) | b1 during jab 2 | 2 | 42 | 6-11, 18-23, 36-41 | variant 1: 24, 0, -8, -64 (tall, short); variant 2: 40, 0, 0, -40 | +29 becomes 7; the variant (+25) is re-rolled at frame indexes 2 and 4 |
| walking jab | b1 while walking | 2 | 12 | 6-11 | 40, 8, 16, -16 (variant 2); 40, 0, -8, -32 (variant 1) | the player stops during the move (x frozen after the first frame) |
| turn-around attack | b1 while the facing differs from the last one (+91) and the hands are empty | 7 | 24, then a fall | 8-23 | 40, 0, 16, -32 (hop kick, pose `$c`) | the player rises 1 px per frame, then +5 = 6 falls (pose `$10`) until landing |
| jump | b2 | 3 | 33 (1 start frame + 32 airborne) | none | none | height = (`$eab0[+52 of the previous frame]` x `$30`) >> 8, peak 48 px; +-1.75 px/frame when a horizontal direction is held; landing is immediate |
| jump kick | b1 during the jump (+6 = 1) | 3 | until landing | from the press to landing (16-31 for a press at air frame 15) | 40, 8, 32, 0 | flag stays set the whole descent |
| roll | b2 with right-down or left-down (not carrying) | 5 | 24 | none | none | +-2 px/frame, pose 4, body box top at -16 instead of -32 |
| grab | b3, empty hands | 1 | 16 | none (pickup test frames 8-15) | pickup box R 36, L 16, B -8, T -16 (up: 20, 0, -48, -64; down actions 3-5: 28, 0, 24, 16) | success on the first overlapping frame of the second half (frame 8) |
| throw | b3 while carrying | 4 | 16 | none | none | the object leaves on frame 1 at 4 px/frame, 24 px above the player |
| weapon swing | b1 while carrying a weapon (+26 = `$e0`, +27 = 3) | 2 | 12 | 6-11 | 40, 8, 16, -16 | the weapon stays in the hands |

Counts: the walking, jump and jab-chain rows are `py/gate_move.py` (372 of 372 checks: 136 walking frames, 31 of 31 jump heights against the formula, 30 of 30 forward-jump steps, jab flags at animation frames 1, 3, 6, 42 frames,
+29 = 7). Chain window (`lua/plans/chain.lua`, `py/gates.sh`): the second b1 press extends the chain only when it is read within frames 2 to 11 of the first move (10 of 10 offsets; at offset 12 the move
has already ended, at 13 and 14 a new jab starts). Without further presses each move ends after its own length (12, 24 or 42 frames). The box rows were read live
(`py/boxes.py`) and equal the table (`py/atkbox.py 0 1 7`, `3 2 2`, `5 2 1`, `12 2 2`).

Priority when several buttons are pressed in the same frame: b1, then b3, then b2 (b1+b2, b2+b3, b1+b3 and b1+b2+b3 gave attack, grab, attack, attack: 4 of 4).

### Grab and carry (the signature move)

`$e5dc` runs every frame while the pose has +27 = 4 and the animation is at frame index 1. It builds the pickup box (`$e71a`, table `$e758[action][facing]`) and tests it against
(a) every live pool A record whose +53 bit 6 is clear, with the record's body box `$6b000[type][state]`, then (b) every live pool B record whose byte 0 bit 3 is clear, with `$68000[type][+3][+4][+20]`,
then (c) the other player (`$e8c6` -> `$e9ac`, only when that player stands or walks: poses 0-3, table `$ea24`). The first overlap wins: P1 +26 and +27 are set (`$c0` / 2 for an enemy or the can, `$e0` / 3 for a weapon, `$80` / 1 for a heavy prop),
+58 bit 7 (bit 3 for a player) and +92 point to it, and the held record gets +17 bit 7 (enemy) or byte 0 bit 3 (prop).
Verified on the level 1 garbage can: grab frame 1599, held state next frame, `+92 = $00081400`, throw read frame 1641, released one frame later, flight 40 frames at exactly +4 px (5 of 5, `py/gate_pickup.py`).
Enemies: a grabbed pool A enemy goes to state `$17` (carried), the throw sets its +17 bit 6, `$22dac` takes 4 HP (`subq.b #4,5(A6)`) and moves it to state 5 (flying) or 4 (dead if HP <= 4): HP 2 -> `$fe`, 3 -> `$ff`
and states `$17` -> 3 -> 4 for all 4 of the 4 enemies that could be grabbed (types 1, 0, 2, 7; types 4 and `$14` stayed out of reach at range; type 9 has +53 bit 6 set and cannot be grabbed) (`py/gate_throw.py`).
Props: carry classes of 8 types tried (`lua/carrylab.lua`): `$0a`, `$09`, `$19`, `$25` -> `$c0`/2 and thrown; `$08` -> `$e0`/3 (weapon, thrown on b3, swung on b1); `$2c` -> `$80`/1 (carried, not thrown by b3
in the 190-frame trial); `$17` and `$1d` (the rubble wall, solid) could not be picked up. The flags per prop type are `$e876` (`py/tables.py`).
Partner: P1 grabbed P2 and threw it (`py/gate_2p.py`): P2 goes to action `$b`, +1 = `$20`, +58 = `$10`; P1 gets +26 = `$c0`, +58 = `$88`; the thrown partner flies 16 frames at +4 px, loses 4 health on landing (`$d442`),
rises for 88 frames (action `$c`, pose `$13`) and blinks 20 frames.

### Characters

There are two slots and one move set. Nothing in the code branches on +2 except the sprite lookup `$a5d0` and the HUD; the logged state sequences of P1 and P2 are identical (136 of 136 frames).
The ROM text has no hero names.

## 4. The shared combat engine (`$22000-$27fff`, `$e000-$ffff`)

All routines below were named from their own bodies (the first branch read to its end); the "role" column is what they do, "also used by" what the callers show.

| routine | role | notes |
|---|---|---|
| `$7626` | update both players | sets +2, calls `$7650` for `$80100`, `$80180` |
| `$a252` | player play update | order: `$a442` input to action, `$e5dc` pickup test, `$e8c6` partner-grab test, action handler (`$a394[+4]`), `$a712` screen clamp, `$e498` body box, `$e56a` attack box, `$a5d0` sprite frame, sound `$e1c` |
| `$a442` | input -> action | `$a5c0` maps the held nibble to +4; +90 bit 6 and `$80041` bit 0 clear the input; button handling is in the action handlers |
| `$a868`, `$a938` | terrain probes | fill +104..+111 and +116 from `$ebb0` and `$f2e8` |
| `$e2a2` | jump height | y = +44 - (`$eab0[+52]` x `$30` >> 8) |
| `$ebb0` | tile attribute at (D6, D7) | map `$60000[level][coarse index]`, word per 16 x 16 tile; plus solid pool B records 24-31 whose byte 0 bit 2 is set (`$ec34`, `$ec7c`) |
| `$ea44` | random number | LFSR in `$81e0e` while a game runs, `$80042` in attract |
| `$2331c` | hit and contact resolver of a pipeline object (pool A types 0-2 and the handlers that call it) | skips hidden objects and states 1, 2; states 4, 5 (flying) call `$fdea` (thrown enemy against the others); otherwise `$f82e` unless +17 bit 5, then `$f4f4` unless +17 bit 2 |
| `$f82e` -> `$f6c4`, `$f8ba` | **player attack against an enemy** | enemy body box `$6b000[type][state]` + (x, y) in D0-D3 against the attack box of P1 then P2 when +28 is set |
| `$f938`.. (`$f8ba` tail) | hit effect | spark = pool B type `$2b` variant 4 (12 when +25 = 2) at the enemy's near edge and the box mid-height; enemy +6 := `$80` | (`$40` if P2) | `{0, 1, 2, 4}[+25]`; sound `{3f, 3f, 40, 3f}[+25]` once per frame |
| `$f96c` | thrown pool B prop against an enemy (prop byte 0 bit 1 set) | prop box `$68000[type][+3][+4][+20]`; enemy +6 := `$84` (`$c4` when the prop's +17 = 1, P2), or `$88` / `$c8` when the prop's byte 0 bit 0 is set (the can, byte `$cb`); the prop gets +6 = `$80` and is consumed. Verified: the thrown can hits a grunt, `$fa04` writes +6 = `$88`, HP 2 -> `$fe` (-4), the can's record is cleared 1 frame later (1 of 1, `lua/plans/canhit.lua`). Enemy-thrown enemies use `$fdea` / `$fe22`: `$88` / `$c8` |
| `$22c56`, `$22ce4` | **enemy takes a hit** | if +6 bit 7: clear it; unless +17 bit 1: HP -= 1 (4 when +6 bit 3); HP <= 0 -> state 2 (dying), else state 1 (hit-stun); `$248bc` awards points |
| `$22dac` | **enemy is grabbed / thrown** | +17 bit 7 -> state `$17`; +17 bit 6 (thrown) -> HP -= 4, state 5 or 4, `$23394` effects and score |
| `$248bc` | score award for a pool A object | table `$24952[type]` (hit, thrown, kill score index + sound), points from the BCD table `$4016`; credited to P1, to P2 when +6 bit 6 is set; `$3fae` adds into +60 |
| `$22540`, `$22612` | animate | `$30000[type][state]` gives the tick limit +19 and the last frame +21; `$f150` draws |
| `$22664` | apply velocity | +22 and +26 longs added to x and y |
| `$22b48`, `$22bd0` | choose the target player | random between P1 and P2 (`$ea44` bit 0), skipping inactive or downed players; copies x, y, pose into +42..+50 |
| `$22c2c` | state-change helper | resets the animation counters when +3 differs from +52 |
| `$2242c` | screen-edge handler of a pool A object | uses the scroll counters `$8040a`, `$80406`: objects far outside are cleared (`$2250c`: 16 longs), those on the edge flag +53 bit 5 and are pulled back |
| `$f4f4` -> `$f690`, `$f700` | **contact damage** | the object's body box (`$f6c4`) against the P1/P2 body box when the player is vulnerable (list below): player health -= `$f78e[type]` (1 for every type except `$3d` and `$4d`), +23 := `$f7de[type]` (`$a0` for types `$24`, `$25`, 0 for `$3e`, `$4e`, `$80` otherwise), player faces the object, spark `$2b` variant 0; **the toucher's own +6 := `$90` (`$d0` for P2) so it loses 1 HP and the player is paid the hit points** |
| `$fa10` -> `$fb8c`, `$fc34` | **enemy melee against a player** | called each frame by the pool C hit-box object (`$22040`, `$22066`, `$22080`, `$220ac`; spawned by `$21eb6`, cleared after the call by `$22526`): box `$69000[C.+2][C.+3][C.+4][C.+20]` + the record's (x, y) against the body box of a vulnerable player; damage below |
| `$1010a` -> `$100b2` | **pool B projectile against a player** | box `$68000[type][+3][+4][+20]`; health -= `$10122[type]` (1 except type 5: 10); +23 := `$1017a[type]` (`$91` types 4, 5; `$81` types `$24`, `$25`) |
| `$21eb6`, `$21efa` | spawn a pool C / pool B record | `$21efa(D6 type, D7 variant)` at A6's (x, y) (hit sparks, dust, bonus drops) |

**Hit-test geometry** (all six chains at `$f8ca`, `$f69a`, `$fb9c`, `$100 1a`, `$e80e`, `$e9bc` are the same): boxes are stored as R, L, B, T with R > L and B > T. With the first box X and the second Y the test is

    overlap(X, Y) = (R_Y >= L_X) and (L_Y < R_X) and (B_Y >= T_X) and (T_Y < B_X)

Player attack: X = enemy body, Y = attack box. Melee: X = the pool C record's box, Y = the player's body box. A body box of 0, 0, 0, 0 (poses `$a`, `$b`, `$d`, `$e`, `$f`, `$12`) cannot be hit; poses 2 and 4 (low) have T = -16 instead of -32; poses 5-9, `$c`, `$10`, `$11` have B = 16 instead of 31.
Verification (`py/hitbox_gate.py`, `py/melee_gate.py`): 40 grunts spawned 24-80 px away while the player jabbed every 6 frames: 397 (frame, enemy) tests with the attack flag set, 71 hits predicted and seen as the enemy's +6 bit 7, 0 predicted-only and 0 seen-only
(the enemy's state at the *start* of the frame decides: a state change later in the same frame is not seen by the test). Melee: 2628 `$fa10` calls logged by a read tap on the table access of `$fbdc`, 13 hits, all predicted, 0 disagreements.

**Player vulnerable** (`$fa10`, `$f4f4`, `$100xx`): +0 bit 7 set, +0 bits 1-0 clear, +0 bit 4 clear (not blinking), +23 bit 7 clear, +24 not in {`$a`, `$b`, `$c`, `$d`, `$e`, `$f`, `$12`, `$13`, `$14`, `$16`, `$17`} (the contact test `$f4f4` uses {8, 9, `$a`, `$c`, `$d`, `$e`, `$f`, `$10`, `$11`, `$12`, `$13`, `$14`, `$16`, `$17`} and does not exclude `$b`), +4 != `$b`, +88 bit 2 clear, +58 bit 4 clear.
There is no invulnerability during the flinch: a second melee hit 8 frames after the first landed on frame 1049 (the pose byte is 0 for one frame between the two animation halves).

**Damage formulas**

    to the player, melee ($fc34):   hp -= 4 * T[(DSW $80054 & $c) / 4][C type]            (byte arithmetic; hp <= 0 -> hp = 0, +58 |= 2)
                                    T indexes: 0 Normal $fd2a, 1 Easy $fcca, 2 Hard $fd5a, 3 Hardest $fd8a
    to the player, contact ($f700): hp -= $f78e[type]       (1)
    to the player, projectile ($100b2): hp -= $10122[type]  (1; type 5: 10)
    to an enemy by the player ($22c56): HP -= 1 per hit;  by a throw ($22dac): HP -= 4;  contact trade: HP -= 1 for the toucher

Normal-difficulty melee damage per pool C type is in `py/tables.py` (`C type 00..03, 05, 06, 0b, 0f, 10, 12, 13, 1c`: 12; `04, 0d (20), 0a, 0c, 14`: 16-20; the boss types up to `$20`: 48). Checked on the default DIP
(Normal): 43 `$fc9e` decrements with attacker C types `00 01 02 0d 13 15 17 26 28` equal `4 x $fd2a[type]` (12, 20, 16 clamped at 0), 30 contact decrements of 1 (attackers A types `00 01 02 04 05 10 15 37`),
10 projectile decrements of 1 and 10 (B types `01`, `05`): 83 of 83, 0 mismatches (`py/dmg_check.py` on `out/dmg_all.txt`; the 35 of 35 that `gates.sh` regenerates are in `out/g_dmg`).
Hard and Hardest tables are *read* only (the DIP was not changed); the Hardest table has bytes >= 128 for types above `$30`, which wrap to small values after the two `add.b D1,D1`.
Other health writers (all *v*): `$d75c` -1 every 16 frames while held by a type 4 variant 1 enemy (165 decrements in the lab, ending in death if not freed; with b1 mashed the hold ended 104 frames after it
started when the enemy died), `$d544` -8 when an enemy-thrown player lands, `$d442` -4 when a partner-thrown player lands.

**Hit-stun, flinch, knock-down**: a melee or contact hit sets +23 bit 7; the next frame `$a4a8` starts action 9 (pose `$d`, two animation frames of 8 ticks = 16 frames, no movement) and +23 is cleared. Types whose reaction code has bit 5 (`$a0`, `$a2`) go on
into the longer knock-down. Enemy hit-stun (state 1) lasts 15 frames in the logs (hit at enemy frame 13, back at 28), and the enemy does not move during it. A killing blow (state 2) flings the type 1 grunt away from the player at 8 px per frame on an arc that peaks 64 px up after 17 frames and lasts about 20 frames (one logged kill, `lua/plans/hit3.lua`; the enemy agents own this). There is no player invulnerability after a hit.

**Score** (+60, `$3fae`, BCD): the table `$4016` has 24 values: 10, 50, 100, 100, 200, 200, 300, 300, 400, 400, 500, 600, 800, 1000, 1000, 1000, 2000, 2000, 3000, 3000, 4000, 5000, 10000, 1000000. Per pool A type,
`$24952` gives the index for a non-lethal hit, a throw and a kill (examples: type 0 and 1: 50 / 100 / 100; type 2: 100 / 100 / 100; type 7: 100 / 200 / 200; type `$14`: 200 / 400 / 400; type 3: 200 / 300 / 500; type 9: 200 / 400 / 1000;
the full list is `py/tables.py`). Checked: jab runs, 6 trials with 11 awards (types 1, 0, 2, 4, 7, `$14`) and throw runs, 4 trials (types 1, 0, 2, 7) all equal the table (`py/gate_score.py`, 0 mismatches). The contact trade also pays points to the
touched player (first contact 50, killing contact 100, frame 1110-1146 of `out/contact2`).
**No extra lives**: nothing adds to +20 (the only writes are `$c3e8` decrement, `$c3ee` clamp and the initialisations `$771e`, `$1588`, `$1666`); nothing awards a life at a score. *Read.* Note the initial spare lives come from `$771e`
(DIP table `$7738` = 2, 3, 0, 1 for the inverted DIP bits 0-1, i.e. 3 lives default (2 spare), 4 lives (3 spare), 1 life (0), 2 lives (1)); a level started directly above 0 with `lua/startlevel.lua` skips
that initialisation and leaves +20 = 0 (5 of 5 bot runs on levels 1-5 read 0).

**Healing**: the only write that raises health in the code is in the pool A type `$3d` handler (`$1e7de`): when the player hits it (its +6 bit 7) and the player's health is below `$30` and its pose below `$d`, health += 8 and the object is deleted; an untouched object blinks after 192 frames and is deleted at 240. *Read*; a bare spawn of type `$3d` (`lua/plans/heal.lua`) is deleted by the handler on its first frame, so the effect was not reproduced (the object is created by another handler). Respawn, continue and the level setup set `$38`.

## 5. Two players

Join-in, grab-and-throw of the partner and the absence of friendly fire from attacks are verified in `py/gate_2p.py` (8 of 8). A three-hit chain of P1 with its attack box over P2's body box for 18 flag frames left P2's health,
action and busy flags unchanged for 80 frames. There is no player-versus-player attack path (`$f8ba` is only reached from enemy handlers); the partner is only affected by `$e9ac` (grab).
Enemies pick their target between the two players at random (`$22b48`).

## 6. HUD fields (from the printers)

`$3d66`: health cells, P1 from `$a0106` rightwards and P2 from `$a013a` leftwards (full cell tile `$2068`, partial cells from `$3e64`/`$3e74`); `$3e84`: portrait item 23-26 for P1 and 27-30 for P2 by health (`$38`, >= `$10`, >= 1, 0);
`$1ab2` descriptors (index: source, tilemap position): 1 hi score `$80010` (`$a0f1c`), 2 P1 score +60 (`$a0e88`), 3 P2 score (`$a0eae`), 4 P1 spare lives +20 (`$a0096`), 5 P2 spare lives (`$a00a8`), 6 credits `$80032` (`$a0f3a`), 0 level number
`$80046`, 18/19 the continue digits +124; 8-17 a debug dump of scroll and player positions (`SCREEN`, `P1XPOS` strings at `$22ec-$2377`); `$3f06` a boss health bar from `$8005c` (cleared when >= `$38`); `$3c68` the timer.
Text items (`$1c8a`) come from the string table at `$20ab-$2294` (`INSERT COIN!`, `PUSH START!`, `CONTINUE?`, `GAME OVER!`, `NAME`, `PLAYER1`, `PLAYER2`).

## 7. The bot (`lua/bot.lua`, item 5)

Starts level `CB_LEVEL` (0-5) like `lua/startlevel.lua`, waits out the scripted entrance, then every frame reads the RAM and presses buttons: walk right, face the nearest live pool A enemy (within `$60` px vertically, states other than 2, 4, 5) and attack
with a button 1 tap every 5 frames inside `CB_RANGE` (36 px). Options: `CB_GOD=1` pokes health and the blink timer (`$80113 = $38`, `$80136 = $7fff`), `CB_SAVEAT="frame:name,..."` saves MAME states, `CB_STOPAT=x:NNN` saves `bot_end`
when the scroll counter reaches a value, `CB_LOAD` resumes from a state, `CB_SHOTS` screenshots, `CB_NOSOLID=1` clears the solid bit of pool B records 24-31, `CB_PLAYER2=1` starts P2 too. Results (5000 frames, god mode):
level 0 stops at the rubble wall (scroll `$200`, x `$2b3`, score 500: the scroll gate is not opened by killing the enemies; a thrown can flies through x `$2c0-$2ff` and the wall record B24 stays unchanged for the whole flight, `out/wall`); levels 1-5 reach scroll `$300`, `$3ed`, `$581`, `$35d`, `$201` with scores 4950, 7500, 8500, 32000, 15600.
The policy does not pick up objects or use ladders, so it stalls at the first scroll gate. Its state files (`bot_end`) are an easy way to get a populated screen.

## 8. Errors in the brief and open items

Brief errors: (1) `$1308` is the level **timer**, not the continue countdown: the continue digit is player-record byte +126 (`$7b2e`), `$80042`-`$80044` is the BCD timer and its frame counter; (2) the HUD number at the top right is the timer ($300 BCD, 1 per 63 frames);
(3) `$22c56`, `$22dac`, `$22540`, `$2331c`, `$2242c`, `$22b48`, `$22c2c` are the pipeline helpers of *pool A* objects (hit taking, grab/throw, animate, hit-and-contact resolver, edge cull, target choice, state change), not routines of the player; the
player's own damage and hit code is in `$e000-$ffff` (`$f82e`, `$f4f4`, `$fa10`, `$100b2`); (4) the "crude bar" and a special attack do not exist in the code: three buttons only; (5) the continue countdown runs at 29 Hz logic rate, one digit per 126 VBLs.

Open: (a) the Hard and Hardest damage tables and the 128+ values at Hardest were not run (DIP unchanged); (b) the escape rule of action `$d` (held by an enemy): observed ending only when the enemy died; (c) action `$c` / sub-actions
6 and 8 (ledge fall, ledge hop) are read, not driven; (d) the rubble wall of level 1 (pool B type `$1d`, solid box x `$2c0-$2ff`, y `$160-$1df`) neither a thrown can nor the dead enemies unlock the scroll; the unlock condition belongs to the world agent
(scroll gate flags `$80400`, `$8044e`, table `$8908`); (e) the mode 2/3 (game-over wait, initials entry) screens were read only; (f) pool B props `$17`, `$1d` cannot be picked up, `$2c` is carried but not thrown by b3 in 190 frames;
(g) per-type enemy HP: types 0, 1, 2, `$14` 2; type 4 1; type 7 3; type 9 `$10` (first frame after the spawn handler; `lua/hitlab.lua`) - the enemy agents own the rest.
