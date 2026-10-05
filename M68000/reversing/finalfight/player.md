# Final Fight player mechanics

The player record's state machine, the move set, taking damage, pickups, weapons, props, score, lives and the continue scene. Evidence tags as in
`kernel.md`: **[R]** read in the ROM listing, **[L]** live in MAME with a count, **[S]** saved state, **[I]** inferred. The record layout is in
`frame.md`; the enemy side is `ai.md`.

Reproduction: every [L] count below comes from `py/player/` (`gates.sh` regenerates all logs from `ff_enemies` and checks them against ROM-derived
expectations, 19 gates; `py/player/README.md`). `A5 = $ff8000`, player 1 record `A6 = $ff8568`.

## Characters and inputs

The character index `+20` of a player record is **0 Guy, 1 Cody, 2 Haggar** (the select screen order; the live player has `+20 = 1`, `+56 = $12910`, `+92 = $12be4`, HUD "CODY").
Per-character tables are indexed by it (`$a124`: `+92` data pointer and `+56` box base pairs); every table named "Cody" below is entry 1, not entry 0.

Input byte `+130` (previous frame `+131`; a new press is `+130 & ~+131`): bit 0 right, 1 left, 2 down, 3 up, 4 button 1 (attack), 5 button 2 (jump), 6 button 3
(read only by the grapple code, `$ce7a`). Bits 0 to 5 driven live (values 01, 02, 04, 08, 10, 20, 30 logged), bit 6 [R].

Fields of the player record beyond `frame.md`, all [R] unless tagged:

| off | meaning |
|---|---|
| +3, +4, +5 | sub-state, step inside it (`4(A6)`; the punch chain step is `4(A6)` = 0, 2, 4, 6), third level |
| +23 | hit-stop counter: 6 on both fighters at a connected hit, sub-states freeze while it is non-zero [L] (6, 5, ... 0 after the first jab) |
| +40, +41 | animation frame counter and flags; `41(A6)` negative = the animation ended (`$3b1c` starts a script, `$3b3c` advances it; a script is `{word offset to a frame block, word duration*256 + flags}`, the block's bytes 2..5 become `42..45` with `44` hurt box and `45` attack box; `py/player/anim.py` decodes it) |
| +62, +63 | hit direction, hit type 0..9 (`11(A2) & $7f` of the attack box) |
| +64, +66, +68 | grapple: `64 = 1` holder, `$ff` held; `66` mode 0 free, 2 grapple [L]; `68` partner record |
| +74, +76 | carrying a weapon, its record |
| +80/+82, +84/+86 | vx and its decay, vy and gravity (8.8 px): `$30aa` does `v -= decay` (vx) and `v -= g` (vy), `pos += v << 8` [L: vy `$600` g `$48` jump, vy `$700` g `$55` special] |
| +97 | hurt-box disable timer (`$32c4` gives no hurt box while non-zero), counted down in `$a7de` [L] |
| +104 | bit 0: "my hit connected", set by the hit handlers (`$718e`, `$73a4`); gates the special's health cost [L] |
| +136, +137, +139, +140 | airborne; "untargetable by the enemy AI" (`$8cf0-$8d62`: sub 8, sub 6 with `4(A6) > 6`, sub 2, `$ff` when the state is not 2; read by the fighter handlers only); special active; respawn drop |
| +142 | respawn flag, set by `$a144`, consumed by state 0 |
| +144, +146/+147 | extra-life state, next threshold word (`$4ab4` adds the BCD repeat word through `-(A2)` from `148(A6)`, so it writes bytes 147 and 146) [L] |
| +148 | player-versus-player immunity: set to `$64` when the other player hits this one (`$782a`, unless `22195(A5)`), no hit lands while it is non-zero (`$77e8`), counted down by 1 per frame in state 2 (`$a660`) [L: 100, 99, 50, 1 sampled, hits 100 frames apart; `twoplayer.md`] |
| +149 | "enemy ahead" bits for the knife (one pool per frame, `167(A5) & 3`, `$bce8`; character 1 only) |
| +150, +151, +152, +153 | weapon-pickup cooldown (`$23` after a pickup); grab cooldown; throw direction (1 forward slam, 0 back throw); grab hold timer (30, 50, 70, 90, 110 or 130 frames from `$d7b6`, the held enemy breaks free at 0) |
| +154, +1 | blink enable; visible flag (`$8dea`: `+1` is cleared on frames where `+97 & 4`) [L] |
| +160, +162/+163, +164 | combo window timer (`$2d` = 45 frames after a connected hit), combo counter (step * 2), chain-active flag [L] |
| +161, +165, +169 | jump-button latch (wall jump), air-attack-once flags |
| +170, +174, +184, +188 | walk distance accumulator, walk animation index, x and y step table pointers (`$c0fc`) |

## Top-level states (`+2`)

The byte takes the values 0, 2, 4, 6, 8, 10, 12 (word table `$a566`, the index is the byte).

| `+2` | entry | what it does | evidence |
|---|---|---|---|
| 0 | `$a574` | spawn: `$9d76` places the record from the camera and a per-stage offset; a normal start goes to state 2 sub 0; with `142(A6)` set (respawn) y += `$100`, `+97 = $b4`, `+154 = 1`, state 2 sub 2 | [L] 1 frame at each respawn (2 runs) |
| 2 | `$a64e` | alive (below) | [L] 2469 of 3001 frames in a random drive |
| 4 | `$a5aa` | dying: sub 0 sets `30 = $3c`, sub 2 counts it down (60 frames); then `$53b2` (difficulty drop), lives `-1` (BCD, `$a5fe`); lives left: `$1e5a` and `$a144` (refill `24/26` from `28`, clear fields, `142 = 1`, state 0); lives 0: `0(A6) = 0`, `19(A6)` saved to `22198(A5)`, state 6. Sub-table `$a5b6` has 2 entries | [L] 60 frames, lives 2 to 1; lives 1 to 0 then state 6 |
| 6 | `$a62e` | inactive record (clears `0, 1, 44`); the continue scene runs instead of the pipeline | [L] 768 frames |
| 8 | `$dc08` | area-intro scripted walk-in, one sub-table per stage and area (`190/191(A5)`); every area starts in state 8 sub 0 (`$a414`, table `$a446` holds `$08000000` for all of them), the handlers are tabulated in `transitions.md` | [L] 166 frames (subs 0, 2, 4, 6); stage 0 area 0 362 frames ending in state 2 sub `$10`, stage 1 area 0 155 frames |
| 10 | `$e8e8` | area-clear walk-out, entered at `$9d26` when `297(A5) != 0` and the player stands on the ground; a carried weapon becomes points (`$e962`: kind 0 500, kind 1 1000, kind 2 800, kind 3 none) | [L] 315 frames in the DAMND area (sub 0, sub 2 step 0 for 80 frames, a back-jump, a walk, sub 4, an 81-frame fade, sub 8); no score or TIME bonus is paid between areas (0 changes in 695 frames); sub-states, targets and the 297 protocol in `transitions.md` |
| 12 | `$c840` | scripted scene entered at `$9d5c` when `291(A5) != 0` (x constants `$6b0-$710`, flags `22191/22193/22194(A5)`) | [L] reached by poking `291(A5) := 1`: state 12 one frame later, 299 := 1 for 80 frames, sub 2 and sub 4, then it parks at sub 4 step 4 with TIME frozen (`transitions.md`); the real scene is [I] stage 5 area 0 |

Death and respawn timeline [L, lives poked to 2]: knockdown to rel 72, state 4 at 73, state 4 sub 2 for 59 frames, state 0 at 133 (lives 2 to 1, hp `$90`), drop-in
for 20 frames (y `$d0` to `$33`, `+97 = $b4` counting down by 1 per frame), landing sub `$12` at 154, idle from 161. At the landing a pool-8 record of kind `$1b`
(`$1f1a4`; `+20` = character, follows the player, 180-frame timer `$b4`) is created (role [I]: respawn-protection marker). Blink: `+1 == !(+97 & 4)` while `+154`
is set [L] 179 of 179 frames: 4 frames visible, 4 hidden, 180 frames in all. The protection is `+97 > 0` (no hurt box); `+137 = $ff` only during the drop.

## State 2 sub-states (`3(A6)`, table `$a7a6`, free mode `66(A6) = 0`)

Live counts are frames of `rand1b` (3001 frames, random inputs, no healing, one death).

| `3` | entry | role | notes and evidence |
|---|---|---|---|
| 0 | `$a962` | stand | direction to sub `$a` (`$bfc6`); floor probe `$ba96`; jump `$bafa`; attack `$bc36`. [L] 52 |
| 2 | `$a9ac` | respawn drop-in | vy `-$600`, g `$48`; lands to sub `$12`. [L] 20 |
| 4 | `$aa4e` | fall (terrain probe `$7cd4` negative in `$ba96`) | [R] |
| 6 | `$ace2` | hit reaction | selector by `63(A6)`, below. [L] 579 |
| 8 | `$aaa2` | get up after a knockdown; any new press sets `40(A6) = 1` | no hurt box, `+137 = $ff`. [L] 79 frames with no input (3 of 3), 74 with random presses; 221 |
| `$a` | `$ab12` | walk: 8 directions (`$c006`, `$c02c`), steps from `$c0d0`; the animation advances when the accumulated step passes `$c0c4[char]` | the walk frames carry the grab box `$8f`. [L] 462 (box `$8f` in 1267 of 1343 frames over four logs) |
| `$c` | `$ab5a` | walk-stop: a 6-frame skid, then the idle animation; stays until a direction or button | [L] 9 |
| `$e` | `$abb6` | jump | below. [L] 465 |
| `$10` | `$b25a` | special (character 1 body `$b2be`) | below. [L] 252 |
| `$12` | `$b396` | landing recovery, 6 to 7 frames; the jump-kick box can still be active in frame 1 | [L] 30 |
| `$14` | `$b3e8` | punch chain (character 1 body `$b51c`) | below. [L] 209 |
| `$16` | `$b6ec` | wall-jump bounce, character 0 only (`$acb2` skips it for the others; `$bab6` needs a wall hit from `$7e1c`, a latched jump press, `190(A5) != 6`) | [R] |
| `$18` | `$b854` | pick-up crouch, 10 frames, no hurt box | [L] 29 (4 of 4 pickups 10 frames) |
| `$1a` | `$b892` | recovery after a grapple, 15 frames; jump, attack and special are allowed at its end | [L] 10 |
| `$1c` | `$b8c6` | hop away (anim `$13d16`, `97 >= $22`) | [R] |
| `$1e` | `$b952` | weapon throw (the animation ends by clearing `74`, `76`) | [L] 9 (1 of 1: kind 0, no enemy in reach) |
| `$20` | `$b9a8` | weapon swing or stab, animation by weapon kind (`$c7f0`) | [L] 9; 6 swings per weapon without wear |
| `$22` | `$b9f0` | stagger after a grab that failed validation (`$ce8e`) | [R] |

Grapple mode `66 = 2` is set by `$412a` one frame after the hit resolver links `64/68` (`$74ee`) [L 5 of 5 walk-in grabs]). Its sub-table is `$cd24` (characters 0 and 1; character 2
uses `$cfb8`, selected through the long table `$a6bc`): 0 `$cd3c` entry, 2 `$cd82` hold loop [L 96 frames], 4 `$ce02` held by an enemy [R], 6 `$ce9a` strike [L],
8, `$a`, `$c` `$cf20` throw [L 26 frames in sub 8], `$e` `$d428` and `$10` `$d5da` player thrown by an enemy (landing damage `$9df6`) [R]. In the hold loop `$d8be`
acts on a new Button 1 (Guy and Cody; Haggar's `$da76` with the selector table `$dab0` is the inverse and his sub-table has different numbering, `twoplayer.md`): no direction = strike chain; direction toward the facing = forward slam (`152 = 1`, no turn); any other direction = back throw (`152 = 0`, facing flips) [L: Guy and Cody turn on the away press, 4 of 4; Haggar turns on the toward press, 2 of 2];
a new Button 2 = jump out (`$da99e`, clears `64/66/152`) [L]; a new Button 3 = release [R].

## Per-frame order (pseudo-code; [R], with the [L] results in the move table)

```
state2(A6):                                  // $a64e
  if link_ok(): 66 = 2; 3 = 0; 4 = 0          // $412a: 64 != 0, partner valid, 66 == 0 -> grapple next frame
  if 66 == 0: table_a7a6[3]();  $ba7e (160/162 window), $a87c (damage check), 97--, 150--, $36dc
  else:       (char == 2 ? $cf9c : $cd18)[3]();  $a6c8 (damage check), 97--
  148--, 151--; if 45 < 0: 45 = 0
  $4a34()                                     // extra life
  $9ce0()                                     // 297 != 0 and grounded: state 10; 291 != 0: state 12
ground(A6):                                   // sub 0, $a, $c, $1a
  if floor_probe() < 0: 3 = 4                 // $ba96
  if new(b2): 64 = 66 = 0; 3 = $e             // $bafa
  if special_ok(): 3 = $10                    // $bdf4: new b1 or b2, both held, 24 > 0, 190(A5) != 6; applied after the jump test, so it wins
  elif new(b1):
      if item_here():                3 = $18  // $9b14: pool $12, state 2, |dx| <= 22, |dy| <= 11
      elif 150 == 0 and weapon_here(): 74 = 1; 76 = w; 64(w) = $ff; 76(w) = A6; 150 = $23; 3 = $18   // $9c72: pool 6
      elif 74:  weapon_attack()               // kind != 0: 3 = $20; kind 0: char 1 with an enemy ahead (+149) 3 = $20, else $1e
      else:     162 = (160 != 0) ? 162 + 2 : 0; 160 = 0
                if 162 < limit[char]:  3 = $14; 4 = 162.low          // limit $be92: 8, 6, 4 (all 4 in stage 6)
                elif 162 == limit:     if direction_away: back_grab() else { 3 = $14; 4 = limit }
                else:                  162 = 0; 3 = $14; 4 = 0
hit_taken():                                  // $a87c: 24 != 26
  3 = 6; 4 = 0; clear 162/160/164/152; 26 = 24; release a carried weapon link; if 24 < 0 and the reaction ends: death sound ($b4a/$b52/$b5a), state 4
```

## Move set (character 1, Cody)

Attack-box catalogue (ROM; `py/player/boxes.py`, `dmg.py`, `ffchar.py`): the id is `45(A6) & $7f`, the damage row is box `+8 / $20`, the damage is the byte at that row for the
current rank (`92 = data + rank + $60`, `$a2d2`), the type is box `+11 & $7f` (bit 7 hard hit), the award is word `$7ae6 + 2*row` through `$1b26`.

| id | dx, dy, hw, hh | row | dmg | type | award per hit |
|---|---|---|---|---|---|
| 01 | 33, 69, 39, 10 | 0 | 10 | 0 | 100 |
| 02 | 38, 48, 45, 10 | 1 | 10 | 1 | 300 |
| 03 | 43, 53, 50, 19 | 2 | 16 | 3 | 500 |
| 04-0b | spin set (06: 17, -4, 32, 67; 07: 51, 1, 66, 69; 08: -8, -4, 22, 69; 09: -46, -4, 67, 69; 04, 05, 0b empty) | 3 | 20 | 7 | 400 |
| 0c | 47, 34, 38, 33 | 4 | 14 | 3 | 50 |
| 0d | 27, 54, 38, 43 | 5 | 12 | 3 | 100 |
| 0e | 17, 47, 29, 33 | 6 | 8 | 2 | 200 |
| 0f | 12, 42, 10, 36 (used with bit 7 set as the `$8f` grab box) | 0 | 10 | 0 | n/a |
| 10 | 87, 47, 24, 11 | 7 | 30 | 3 hard | 200 |
| 11 | 92, 31, 58, 11 | 8 | 30 | 3 hard | 200 |
| 12 | 92, 31, 58, 11 | 9 | 20 | 3 hard, sound `$1f` | 200 |
| 13 | 17, 47, 29, 33 | 10 | 16 | 2 | 300 |

| move | input | sub, step | numbers | live check |
|---|---|---|---|---|
| walk | direction | `$a`, `$c` | x 1.95 px per frame, y 0.80 (step words `$1f3`, `$cc`); up and right clamp to the camera window (`$8e46`) | 2 of 2 against the ROM tables (left 113 px in 58 frames, down 47 px) |
| punch chain | Button 1 on the ground (`$bc36`) | `$14`, `4(A6)` = 0, 2, 4, 6 | ids 1, 1, 2, 3; dmg 10, 10, 10, 16; types 0, 0, 1, 3; awards 100, 100, 300, 500; animation lengths 14, 14, 18, 34 frames; the next step needs a press within 45 frames of a connected hit, a missed press always restarts at step 0; limit 6 gives 4 hits | 4 of 4 hits (id, dmg, type, score all equal the ROM); 7 whiffs all at step 0 |
| back throw at the chain end | at the limit step, new Button 1 with a direction away from the facing (`$be9e`, `$bf0e`) | grapple at once, sub 8 | the nearest alive grounded enemy in front within 128 px and the depth lane (pool 2, then 4) is grabbed and thrown over the shoulder; characters 0 and 1 turn (`46(A6)` flips), character 2 does not | 1 of 1: grapple from the press, facing flips, landing -40, +300 |
| jump | new Button 2 (`$bafa`) | `$e`: step 0 init, 2 crouch (6 frames), 4 air (42 frames) | vy `$600`, g `$48`, apex +61 px, about 54 frames; the direction is read at the end of the crouch (or on a new press): vx `$2d0` decaying 5 per frame, facing set from it; no direction = vertical | 6 jumps, vy `$0600` seen |
| jump attack, diagonal | Button 1 in the air, vx != 0, moving toward the facing (`$bb96`) | id 0c | 14 dmg, type 3, +50 | 1 of 1 |
| jump attack, vertical | Button 1 in the air, vx = 0 | id 0d | 12 dmg, type 3, +100 | 2 of 2 |
| jump attack, down | down + Button 1, moving forward or vertical | id 0e | 8 dmg, type 2, +200 | 2 of 2 |
| jump attack, down backwards | down + Button 1 while moving against the facing | id 13 | 16 dmg, type 2, +300 | [R] |
| special | Buttons 1 and 2 both held with at least one new, `24 > 0`, `190(A5) != 6` (`$bdf4`; a same-frame press wins over the jump) | `$10` | vy `$700`, g `$55`, apex +71 px, about 45 frames airborne, boxes 4 to `$b` (front 6 and 7, back 8 and 9), one hit per side, 20 dmg, type 7, +400; cost `24 -= 8` at the end only if `104` is set (an enemy or a prop was hit), floored at 0; no hurt box during the spin; also reachable at the end of a hit stun (`$ae18`) | hit: -8 (2 of 2); no hit, props removed: 0 (1 of 1); hp 3: runs, ends at hp 0 and Cody lives (1 of 1); hp 0: the same press gives a normal punch (1 of 1) |
| grab | walk into an enemy | walk frames carry box `$8f` | overlap `$74ee` sets `64/68`; `$412a` sets `66 = 2` | 5 of 5 |
| grapple strikes | Button 1, no direction | grapple sub 6 | `sub.w` of 8, 9, 16, 28 on counter 0, 2, 4, 6 (`$db6e`, unscaled); awards 100, 100, 200, 300 (`$d86e`); hit types 1, 1, 1, 3 (`$d8a6`) | Dug -9, -16, -28 and +100, +200, +300 (3 of 3); the first press only enters the hold |
| forward slam, back throw | direction + Button 1 | grapple sub 8, `152` 1 or 0 | +300 (code `$0d`); the victim takes the landing rule of `$3f7a` | forward 1 of 1, back 2 of 2, landing rule 4 of 4 |
| jump out | Button 2 in a grapple | `$e` | clears `64/66/152` | 1 of 1 |
| pick up | Button 1 over an item or weapon | `$18` | below | 24 of 24 item runs, 3 weapons |
| weapon | Button 1 while carrying | `$20` or `$1e` | kind 0, enemy in reach: stab id 10 (30 dmg, reach 63 to 111 px), no enemy: throw; kind 1 swing id 11 (30); kind 2 swing id 12 (20, sound `$1f`); all hard type 3, +200 | 3 of 3 against the ROM |

## Damage taken, i-frames

`$a87c` and `$a6c8` compare `24(A6)` with its shadow `26(A6)` (the hit handlers write only `24`): a difference sends the record to sub 6 with `4 = 0`, clears the combo state and
sets `26 = 24`. The selector `$ad04` maps `63(A6)` to `4(A6)`; a handler that sees `24 < 0` goes to `4 = $14`, and in the air every type except 8 becomes 3.

| `63` | `4(A6)` | meaning | live |
|---|---|---|---|
| 0, 4, 6 | 2 | stun A | 14 events, 26 to 27 frames |
| 1 | 4 | stun B | 2 events, 27 frames |
| 2 | 6 | stun C | 1 event, 27 frames |
| 3, 7 | 8 | knockdown arc: `5(A6)` 0 init (flip, vx `$200`, vy `$380`, y `+$14`), 2 air (29 frames), 4 bounce (vx `$100`, vy `$280`, 17), 6 slide (13), then sub 8 | 6 events, 61 frames to the get-up |
| 5 | `$c` | variant knockdown (`$afe6`) | [R] |
| 8 | `$12` | hazard variant (`99 = 1`; `97 = $96` if the attacker is a tag `$a` kind `$11` object) | [R] |
| any, `24 < 0` | `$14` | fatal knockdown: 45 + 28 + 16 frames in the arc, then state 4 | 1 event, 92 frames |

The hit-stop is `23(A6) = 6` [L]. There is no hurt box (`44 = 0`) in sub `$10`, sub `$18`, sub 6 once `4 >= 8` and sub 8 [L], and the end of sub `$18` raises `97` to at least 10 (`$b882`, [R]).
Enemy damage on Cody is the unscaled `$7a04` (`frame.md`).

## Items, weapons, props

**Items** (pool `$12`, 10 records at `$ffbee8`, `+20` = type, effect `$9b88`, pickup `$9b14`): 24 of 24 combinations checked at Cody hp `$20` and `$90`, the type chosen by poking the prop's explicit drop byte.

| type | heal (cap `$90`, hard-coded in `$9c44`) | at full health, or with no heal | code |
|---|---|---|---|
| 0-2 | `$80` | 10,000 | 4 |
| 3-7 | `$40` | 5,000 | 5 |
| 8-12 | `$20` | 3,000 | 6 |
| 13-19 | `$10` | 1,000 | 7 |
| 20-21 | none | 10,000 always | 4 |
| 22-26 | none | 5,000 | 5 |
| 27-30 | none | 3,000 | 6 |
| 31-34 | none | 1,000 | 7 |
| 35 | heal `$40` or code `$20` (42,910) | [R]; type 35 was never picked up in the run (no `sub $18`), reason unknown | |
| 36-38 | `rts` | | [R] |

**Weapons** (pool 6, 6 records at `$ff90a8`, updater `$5962`, 6 kinds `$57a76`, `$5828e`, `$58b1c`, `$5935e`, `$5957a`, `$59b2e`): a drop byte `D2 >= $24` creates kind `D2 - $24`
(`$5a9a4`, allocator `$38ce`). Kinds 0, 1, 2 are picked up by Cody [L]; kinds 3 and 4 spawned but Button 1 started a grapple instead (2 of 2), kind 5 vanished within 115 frames:
[I] enemy-side objects. Pickup `$9c72`: record in use, `64 == 0`, `74 == 0`, `|x diff + $16| <= $2c`, `|y diff + $b| <= $16`. Use: the move table. Names (knife, sword, pipe) are [I]; a carried weapon at area clear is converted to points (state 10).

**Breakable props** (pool `$a`, 16 records at `$ffb2e8`, updater `$59a4`, 19 kinds `$515a6, $517b6, $51bfc, $52018, $522e6, $52476, $526f4, $5298c, $52d3e, $52f84, $5368a, $53f68, $5423c, $5440a, $545dc, $5477a, $54b4a, $54df8, $551e2`):
stage 1 holds only kind 5. Hit handlers (`$70f4`): default `$7156` for kinds 0, 2 to 8, 10, 18 (attacker `19(A1)` into `105`, `60 = A1`, hit type, sound `$7334`, scaled damage `$79d8`, spark, facing `$7a38`, hit-stop 6,
`104 |= 1`, `160 = $2d`, per-hit award `$7aa8`, HUD queue `$28d0`); own handlers for kind 1 `$711a`, 9 `$71a2`, 11 `$7220`, 12 `$7222`, 13 `$722a`, 14 `$7232`; kinds 15 to 17 `$7332` (`rts`). Kind 5 has hp 0, so one hit
breaks it (state 4, then 6, the record is freed 22 frames later [L]); +100 for a jab, +500 on the break (`$10`) [L]. Break awards [R]: kind 0 `$21` 700, 3 `$11` 600, 4 `$07` 1000, 5 `$10` 500, 6 and 7 `$12` 800, 8 `$15` 1500, 10 `$06` 3000.
The depth window of a prop hit is per kind (`$34c4`; kind 5: prop ground y 0 to 10 above the player's; a prop 1 below is never hit, [L]).

**Drop rule** (`$5a934`, called by the break handlers of kinds 0, 2 to 8, 10): if `105(A6)` is not negative and `$5abe0` fires, `D2 = $14` or `$15` (type 20 or 21, 10,000 points); otherwise `D2 = 21(A6)`: bit 7 clear = explicit type, bit 7 set =
random from table `$5a9e0`, row `(21 & $f) * 32 + (LFSR & $1f)` (`$3c26`), value `$80` = no drop. `D2 < $24` creates a pool-12 item at the prop's ground y minus 2, else a weapon. `$5abe0` fires when the killing player has a new press
of right, left, down, up or Button 2 (mask `$2f`) on the frame the break handler runs, then half the time each type; kind 2 props test both players. [L] 1 of 1: a press that landed on the kill frame turned an explicit type-3 drop into `$14`;
presses one or two frames earlier or later kept type 3 (4 of 4).

## Score and lives

The score is an 8-digit BCD longword at `+132` (`$ff85ec`) in points, capped at 9,999,999; the low word `$ff85ee` is what `frame.md` calls `+134`. Every award goes through `$288c` (queue at `516(A5)`, bit 7 = player 2; the slot-11 idle
task `$4afc` pops it into `$1a22`, which adds `$1b26[code]`). Codes: 02 50, 03 100, 04 10,000, 05 5,000, 06 3,000, 07 1,000, 09 20, 0a 30, 0b 200, 0c 250, 0d 300, 0e 350, 0f 400, 10 500, 11 600, 12 800, 13 1,200, 14 1,400,
15 1,500, 16 1,600, 17 2,000, 18 2,500, 19 15,000, 1a 20,000, 1b 30,000, 1c 50,000, 1d 4,000, 1e 40,000, 1f 100,000.
Sources: per damaging hit (`$7aa8`, the box table above; live equal to the ROM for ids 1, 2, 3, 0c, 0d, 0e, 10, 11, 12); grapple strikes 100, 100, 200, 300; a throw or slam 300; items; the area-clear weapon bonus; and kills, where each fighter handler
sends `table[+20]` (5 of 5 live with a breakpoint on `$288c`):

| kind (handler) | table | awards by `+20` |
|---|---|---|
| 0 (`$21cec`) | `$21fbe` | Bred `$07` 1,000, Dug `$13` 1,200, Jake `$14` 1,400, 3 `$16` 1,600 |
| 1 (`$2813a`) | `$28328` | `$15`, `$17` |
| 2 (`$2a310`) | `$2a50e` | 0 `$17` 2,000, 1 `$18` (the record that gave 2,000 live is the kind-2 record) |
| 3 (`$2ccac`) | `$2cec0` | `$06`, `$1d` x4, `$ff` |
| 4 (`$3136c`) | `$32854` | `$17`, `$18`, `$06`, `$ff` |
| 5 (`$3514c`) | `$363a4` | Holly Wood `$06` 3,000, 1 `$1d` |
| 6 (`$389b8`) | `$3a220` | `$17`, `$06` |

Extra life [L 1 of 1]: `$4a34` (when `130(A5) != 0`) compares the score high word with `146(A6)`. The first threshold comes from the DIP tables at `$dfe`-`$e0a` indexed by `100(A5) & $60`; the saved state has `100(A5) = $0b`, table `$dfe`: the
first life at 100,000. Score 99,900 plus 100 plus 500 gave lives 2 to 3 two frames after the crossing, sound `$5e`. The next threshold then reads `$6675` (BCD of `$0010 + $ffff`, from the repeat word `$ffff`), unreachable under the cap,
so one extra life per game at the default DIPs. The other tables are `$e02` (200,000, then none), `$e06` (100,000, then every 200,000 by its repeat word `$0020`) and `$e0a` (none) [R].
Initial lives `+128 = 133(A5) = 2` ([S] RAM; the HUD shows `+128 - 1`); a continue restores `+128 = 2`, hp `$90`, keeps the score and adds 1 to its last digit [L].

## Continue scene

When the last life is lost the record goes to state 6 and `$4e9c` sets `21416(A5)`; phase 6 then runs `jmp $5da78` every frame instead of the pipeline (record `$ff1576`, `-27274(A5)`; its state byte `2(A6)`, sub `3(A6)`).
[L] (3 runs): the scene starts 61 frames after the player record clears; it shows `CONTINUE n / INSERT COIN` for 360 frames (the word at `26(A6)` runs `$168` to 0), then GAME OVER, a palette fade (counters `22/24(A6)`) and the attract loop.
With a coin (credit byte `$ff804d`) and Start pressed during the countdown the scene accepts (state word `$400`), shows PLAYER SELECT with its own countdown, and the player respawns about 350 frames after the Start press with lives 2.
`$5db3c` restores `190/191(A5)` and the camera; `$a158` (P1) and `$a18a` (P2) preserve `132, 129, 144, 146` over the re-initialisation and call `$a13c`, `$a09a`, `$a144`.
`22188(A5)` is not part of this: it is the attract-demo flag (`22189(A5)` the demo character; tested at `$a0c2`, `$2b84`, `$4cf2`, `$5aea`). The scene's sub-states (`$5dbc4`, `$5dc08`, `$5e2f2`) are [R] only.

## Per-character tables

| item | Guy (0) | Cody (1) | Haggar (2) |
|---|---|---|---|
| data / box base (`$a124`) | `$10ffa` / `$10b76` | `$12b80` / `$12910` | `$14f4e` / `$14cfa` |
| max health, defence class (`+55`) | `$90`, 0 | `$90`, 0 | `$90`, 0 (constant over all 32 ranks) |
| attack ids / damage rows | 29 (`$1d`), 13 rows | 19 (`$13`), 11 rows | 18 (`$12`), 10 rows |
| damage rows 0.. (hex) | 06 08 0c 0e 0e 14 08 08 1e 1e 1e 14 10 | 0a 0a 10 14 0e 0c 08 1e 1e 14 10 | 12 12 08 14 14 0a 0f 1e 14 10 |
| chain limit (`$be92`) | 8 (5 hits) | 6 (4 hits) | 4 (3 hits); 4 for all in stage 6 |
| walk step x, y (`$c15e`, `$c19e`) | `$219`, `$100` | `$1f3`, `$cc` | `$1d9`, `$b3` |
| walk accumulator (`$c0c4`) | `$6c000` | `$72800` | `$55000` |
| jump vx (`$ac76`) | `$300` | `$2d0` | `$260` |
| special body (`$b276`) | `$b27c` (vy `$600`) | `$b2be` (vy `$700`, [L]) | `$b300` |
| chain body (`$b404`) | `$b40a` | `$b51c` | `$b5fc` |
| grapple code (`$a6bc`) | `$cd18` | `$cd18` | `$cf9c` |
| grapple strike damage (`$db6e`) | 8 8 14 24 | 8 9 16 28 | 8 10 18 36 |
| grapple strike award (`$d86e`) | 100 100 200 300 | 100 100 200 300 | 200 200 300 400 |
| thrown-victim landing rule (`$3fd8`) | 15 / 45 / 30 | 18 / 62 / 40 | 18 / 62 / 40 |
| per-hit award table (`$7ac6` + offset 6, `$20`, `$36`) | `$7acc` | `$7ae6` | `$7afc` |
| special rules | wall jump (sub `$16`) | knife stab only with an enemy ahead (`$bcb2`) | no turn on the back grab (`$bee2`); sound `$a92` on the down air attack (`$bbfa`) |
| death sound (`$b4a`, `$b52`, `$b5a`) | `$22` | `$23` | `$24` |

The animation pointer tables (about 35 four-entry tables in `$c3c4-$c840`) are per character as well.

Guy's and Haggar's rows were run live from states with the character chosen on the select screen: chain ids and damage rows 5 of 5 (Guy) and 3 of 3 (Haggar) against the ROM, jump attacks 5 of 5 and 6 of 6, specials 4 of 4 each, grapple strikes 3 of 3 each (damage, type, award), the thrown-victim landing rule for Guy (-30) and Cody (-40), 18, 28 and 30 attack-box hits of random drives equal to the ROM rows. Measured: walk 2.067 / 1.917 / 1.817 px per frame, jab animations 12 / 14 / 22 frames, specials 42 / 49 / 46 frames (Haggar's has no vertical motion), Guy's wall jump (sub `$16`) and Haggar's pile driver and jump slam, all in `twoplayer.md`.

## Not proven

- Hit types 2 (seen once), 4, 5, 7, 8, 9 on the player: poke `63(A6)` with sub 6 `4 = 0`, or find the enemy attack boxes that carry them.
- Sub 4 (pit fall), `$1c`, `$22`, the held-by-enemy grapple subs 4, `$e`, `$10` (sub `$16` is Guy's wall jump, [L] in `twoplayer.md`; Guy's and Haggar's combos, specials and throws are proven live there).
- The rest of state 12 (the scene's own steps) and the stage-6 behaviour (`$bdf4`, `$bab6` disabled when `190(A5) = 6`); the per-stage scripts of states 8 and 10 are tabulated in `transitions.md`.
- Item names, prop names, weapon names, pool-6 kinds 3 to 5, item type 35, the continue scene's sub-states and digit timing (player 2, mid-game joining and `127(A5)` are proven in `twoplayer.md`).
- The role of the pool-8 kind `$1b` record ([I] respawn marker); the tag `$a` hit handlers of kinds 1, 9, 12 to 14 beyond reading.
