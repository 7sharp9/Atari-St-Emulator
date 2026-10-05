# Final Fight fighter AI (pool-2 kind handlers)

How the enemies decide what to do. Evidence tags as in `kernel.md`: **[R]** read in the ROM listing, **[L]** checked live in MAME with a count,
**[S]** read from a saved state, **[I]** inferred. The pool and record layout are in `frame.md`; the player side is in `player.md`. Every fighter
is a pool-2 record whose `+19` selects the handler through the long table at `$5824`; `+20` is the character index within the kind, `+21` the
entrance type, `+96` the difficulty level. The bosses are not pool 2: they are pool 4 records with their own handlers (`boss.md`). The scripts that reproduce each claim are in the README script index.

## Overview

The nine handlers are one design with different attack content. This overview lists what they share; each section below proves its own part and
ends with what it did not prove.

| kind | handler | characters (`+20`) | what it is |
|---|---|---|---|
| 0 | `$21cec` | BRED, DUG, JAKE, SIMONS | the thugs: slot-based formation, combo scripts, a jump attack, prop smashing |
| 1 | `$2813a` | J, TWO.P | thugs with an evasive back-step (dodge by player button edge) |
| 2 | `$2a310` | AXL, SLASH | thugs with a guard that blocks a hit with probability `168/32` and counterattacks |
| 3 | `$2ccac` | ANDORE Jr., ANDORE, G., U., F.ANDORE | big grapplers: shoulder charge, aimed leap, squeeze and slam grabs, ground-shadow child |
| 4 | `$3136c` | G.ORIBER, BILL BULL, WONG WHO | heavy brawlers: jab and kick ops, a charge, stand-off points |
| 5 | `$3514c` | HOLLY WOOD, EL GADO | knife fighters: draw, jab, dash kick, armed swings, weapon throws, jump attack |
| 6 | `$389b8` | ROXY, POISON | flankers: op chains, vault over the player, dodge by probability |
| 7 | `$3c446` | (none) | invisible placeholder that frees itself after 10 to 255 frames (scroll-lock hold, [I]) |
| 8 | `$3c48e` | red fire-bottle thrower (HUD label HOLLY WOOD) | walks to a random column, throws one Molotov at the nearest player, leaves |

**Shared structure.** `$57f2` walks the 13 records and `$5814` jumps through the table at `$5824` by `+19`. A record with `+0` bit 7 set is skipped
for one frame, so init runs on the second frame. `2(A6)` is the life state in every handler: 0 init (`$2fa2` reads health, defence class and the
damage base from the character data by the level `+96`), 2 alive, 4 dying (about 60 frames, the score is queued when it ends), 6 free (`$3878`).
In state 2 each frame runs the grab gate `$412a`, the behaviour dispatch on `3(A6)`, the health check (`+24 != +26` enters the hit reaction, a
negative `+24` the death), the cull `$3bb0` every 8th or 16th frame by `(167(A5) + D7) & mask`, and the box and sprite step `$32aa`. A hit
sets hit-stop 6 on both fighters, stores the attacker in `+60`, the attack id in `+22` and the hit type in `+63`; the type selects the reaction
(stagger about 26 frames, knockdown about 66 frames, then a get-up wait). A stage clear (`299(A5)`) marks every fighter dead on its own phase frame.

**Choosing a target.** Every kind except 7 takes the nearest live player by |dx|; player 1 wins only when strictly nearer, so ties go to player 2
(`$280c8` for kinds 0 to 2, `$3068` for the others; 4 of 4 and 8 of 8 checks with a cloned player 2). A player who is airborne or down
(`+136`, `+137` of the player record) is skipped for attacks.

**Keeping the crowd apart.** Kinds 0 to 2 share eight formation slots around the player (`$28084`) and an attack-token counter `$ff115a` capped by
the rank, and the touch path `$27b00` takes a token past the cap. Kind 3 reserves a (player, side) counter at `$ff116c`, kinds 4 and 5 use stand-off
points of 64 or 144 px, kind 6 a flank slot, and the spawn gate `$3e88` caps how many of each kind live at once.

**Choosing an attack.** A character's pick table (32 bytes, indexed by `rnd & $1f`) names an attack script, a list of step ids ended by `$ff`;
a step is an animation plus an attack box whose `+8` word is a row offset in the damage table. Pauses between steps are random (6 to 14 and 10 to
70 frames). The decision roll against a per-rank threshold (`rnd & $f`) opens an attack, and a second roll against `+143` decides whether a
script chains into another. The only randomness is the 16-bit LFSR `$3c26` on `$ff1150`, shared by every caller, so successive rolls are correlated.

**The difficulty rank.** `168(A5)` rises by one every 600 frames (`172(A5) = 1`; 8 at frame 4151 of `ff_enemies`, 14 by frame 7677) and falls on
player events through `$53b2`. It is read by `$3e88` (spawn caps), by the token caps `$27b88`/`$27bc8`, and at spawn through `169(A5)` into the level
`+96` when the script byte is `$ff`. The level indexes the health word, defence class and damage column of the character data and the attack-roll
thresholds. It does not change walking speed. Kind 8 never reads `168(A5)`.

**Score.** A fighter's death queues a kill award through `$288c` (`player.md`, "Score"): BRED 1000, DUG 1200, JAKE 1400, SIMONS 1600; J 1500
or 2000 by subtype, AXL 2000, SLASH 2500; G.ORIBER 2000, BILL BULL 2500, WONG WHO 3000; HOLLY WOOD 3000, EL GADO 4000; ROXY 2000, POISON 3000;
kind 3 uses 3000 (ANDORE Jr.) and 4000 (the others). A fighter that dies to a hazard (`+105` negative) or is culled off-screen gives nothing.

**Quirks that are the original's, not the emulation's.** `$3a516` loads a per-character mask table pointer into `A0` and never uses it, so
POISON attacks as often as ROXY. Kind 7 indexes a 16-byte delay table with a `$1f` mask, so half its draws read the next instruction's bytes and
the delay runs up to 255 frames. `$27c34` skips the `lea` that loads the other player when the target is player 1. Kind 3's health table overlaps
other data at ranks 15 and 31.

**What was not reached.** The per-kind gates in this document ran on `ff_enemies` (stage 1, one player) or on records spawned into it through the real allocator or the
real script engine. Stage 0 has since been played by a bot from a cold boot through its boss (`py/stage/`, `transitions.md`): its 18 one-player script entries
spawned in order with the fields given here (`py/stage/census.py`), and the kind 4 and kind 6 group of area 2 (`$70782`) spawns only after DAMND's second retreat (`boss.md`);
the other stages and the grounded-death variant of every kind, entrance variants no script uses, and the thrown weapon's damage are open (each section's "Not proven" says how to prove them).

## Shared helpers and kind 0 (BRED, DUG, JAKE, SIMONS)

The kind 0 handler `$21cec` (`$21cec-$2813a`, about 9 KB of code in 26 KB: the rest is animation scripts and tables) drives four characters through
one state machine, selected by `20(A6)`: 0 BRED, 1 DUG, 2 JAKE, 3 SIMONS (names from the game's HUD text; SIMONS [L] 1 sample, the other three in
`frame.md`). Most of the helpers below are shared with kinds 1 and 2 (their handlers hold copies of the same logic) and are called from the others.
Positions are y-up: airborne means `+10 > +14`; fighters keep `+90` (height) at 0. Velocities `+80,+82,+84,+86` are 8.8 px per frame added as
`(v << 8)` to the 16.16 positions. Scripts: `py/ai_kind0/` (`README.md` there). Evidence runs: four fresh runs of `ff_enemies` (`g1` idle, `f1..f3`
scripted Cody inputs), 8450 frames, 21580 kind-0 record-frames, Cody's health topped up when low; a rerun of `f1` gives an identical md5.

### Helpers

`A6` is the record, `D7` the pool-2 loop counter (`12 - array index`), phase staggering is `(167(A5) + D7) & mask`.

| addr | role (from its body) | inputs, outputs | evidence |
|---|---|---|---|
| `$2fa2` | spawn stat init | `92(A6)` = char data base, `96(A6)` = variant v: `24,26,28 = word[base+2v]`, `55 = byte[base+$40+v]`, `92 += v+$60` | [R]; [L] hp 28 BRED, 41 DUG, 64 JAKE at v 0; v 4 gives 36 and 72 |
| `$3878` / `$3a1c` | free the record / clear it (keeps word `+78`) | sets `18=2`, pushes A6 on the free stack `20242(A5)`, `20240(A5)++` | [R]; [L] record empty 1 frame after state 6, 10 of 10 |
| `$3b10` | start animation | D0 char, A1 word-offset table: `32` list ptr, `36` frame record ptr, `40,41` timer word, `42..45` frame bytes +2..+5 (`44` hurt box, `45` attack box), `48,49` frame word +6 | [R]; [L] `44/45` equal the frame record `+4/+5`: 20789 of 20789 |
| `$3b3c` / `$3b76` | advance animation forward / backward | `40--`, at 0 next frame; a negative timer word loops; byte `41` is the frame flag (`$ff` end, `01` active) | [R]; [L] durations: hit stun 26 frames, attack id 6 16 frames |
| `$3bb0` | off-screen removal test | `2(A6)=6` if `x-camx+$80 > $280` or `y-camy+$80 > $200`; run every 8th frame | [R]; no live removal |
| `$3c26` | RNG | D0 = low byte of a 16-bit LFSR on `$ff1150` (seed `$2472`): `S' = (S>>1) \| ((bit1 ^ bit9) << 15)` | [L] 505 of 505 steps, D0 506 of 506 (breakpoint `$3c56`); 506 calls in 2000 frames |
| `$412a`, `$4166`, `$41ba`, `$4234` | grab gate / link check / follow the holder / choose offset table | `$412a`: D0=1 normal, else `66=2`, `3,4,5=0` when `64(A6)` and the holder's `64` are set. `$41ba` copies the holder's position plus an offset from `70(A6)` | [R]; [L] held mode entered 12 times (182 frames) |
| `$32a2`, `$32aa`, `$32be`, `$3264`, `$36dc` | draw if visible / boxes then draw / boxes only / on-screen test / depth-bucket sprite queue | `$3264` sets `1(A6)` from `(x-camx+$30)<=$1e0`, `(y-camy+$80)<=$180`; `$36dc` inserts (A6, ground-`90`) into one of 9 lists at `20542(A5)+66k` | [R]; [L] `1(A6)` equals the test 21364 of 21372 (rest: spawn frames) |
| `$30aa`, `$30d4`, `$315c` | motion with x decel / gravity only / decelerate x to 0 | `vy -= 86; y += vy<<8; vx -= 82; x += vx<<8` | [L] flight vy 896, 824, 752 (gravity `$48`), vx -256 to -236 (decel 20) |
| `$7d6c` | terrain and prop collision at (x, ground) | pushes the fighter out; `88/89` result; stage edge by `$8474`, props of pool `$a` by `$84ae` (stores the prop in `102(A6)`); Z = free | [R]; [L] `102` holds prop addresses; result codes beyond prop contact and edge **[I]** |
| `$44d0`, `$3a52` | spawn a dust effect / allocate an effect slot | effect kind 1 beside the fighter | [R] |
| `$3f7a` | slam damage by the holder `68(A6)` | hp <= A kills, <= A+B halves, else -C; (A,B,C) 15/45/30 when the holder's `20` is 0, else 18/62/40 | [R]; not seen live |
| `$b8a`, `$aaa`, `$9de` | sound cues `$2c` and `$0d` | `$9de` writes the cue ring `388(A5)` when `1(A6)` is set | [L] `$2c` at the frame of a lethal hit, `$0d` at each landing |
| `$288c` | queue a score award | D0 = points-table index (bit 7 = P2) into the byte ring `516(A5)`, write index `30(A5)`; the slot-11 task pops it at `$4b00-$4b5a` and calls `$1a22` (BCD add from the table at `$1b26`) | [L] DUG death wrote `$13` at `$2894`, cleared by `$4b1a`, P1 score `$8130 -> $9330`; BRED plus JAKE together +2400 |
| `$28b4` | enemy-bar push | pushes (A6, 24, 26, 28) into the HUD ring `644(A5)` unless `105(A6)` is set | [R] |
| `$6c7a`, `$6c96` | thrown-body hit test | one candidate per frame (P1, pool 4, pool 2, props); on overlap `$7bba` damage, victim `63=3`, hit-stop 6 on both | [R]; not seen live |
| `$3e88` | spawn gate (from `$5eac`, `$61e8`) | kinds 0-2: spawn only while `$ff1154 < table@$3eda[168(A5)]` (2,2,2,3,3,3,4,4,4,4,4,5,...,9), then `$ff1154++` | [R]; [L] `$ff1154` equals in-use kind 0/1/2 records, 8450 of 8450 |
| `$27a04` (`$27a12`) | a player in view | P1 then P2: `|dx| <= $60`, `|ground dy| <= $80` | [R] |
| `$27a42` | blocked counter | `175(A6)` = `{8,8,10,10,10,10,12,12,12,12,14,14,14,14,16,16}[RNG & $f]` | [R] |
| `$27a62` | target state gate | target `2(A4) > 2`: release token, `3=10`, D0=1; target `136(A4)` (airborne) gives `3=12,4=2`; `137(A4)` (not in a normal state, or state 8, or 3 == 2) gives `3=12,4=4` | [L] 180 calls: 51 airborne, 55 special, 74 pass |
| `$27ab4` | adjacent slot by side | `146 = 3` if the target is right of the fighter else 7 | [L] 32 of 32 |
| `$27ace` | in attack range | D0=1 if `|dy| <= 4` and `|dx|` in `[$28,$48]`; every other path tail-jumps into `$27b00` (so also true when a player is in the melee window) | [R]; [L] 156 attack starts, 55 in range, 8 out |
| `$27b00` (`$27b2a`) | player in the melee window | `|dx| <= $30` and `|dy| <= 9` for P1, then P2: takes a token, sets `144/148`, D0=1 | [L] 49 of 3851 calls |
| `$27b5a` | attack token request | granted if `$ff115a < cap`; cap = `tok1[168(A5)]` = 1 (rank 0-6), 2 (7-12), 3 (13-18), 4, 5, 6 (30,31); for two players (`127(A5)==3`) `tok2` = 2 (0-5), 3 (6-10), 4 (11-15), 5 (16-20), 6 (21-25), 7 (26-29), 8 (30, 31) | [R]; [L] 86 of 86 calls agree (breakpoints on the entry and exits; `127(A5)` poked to 1 and 3 and a fuzz of tokens, rank and mask), `twoplayer.md` |
| `$27c08` / `$27c20` | take / release a token | `136(A6)` 1 or 0, `138(A6)=0`, `$ff115a` +-1 | [L] `$ff115a` equals the kind 0/2 records with `136 != 0`: 8450 of 8450 |
| `$27c34` | abandon-target check | -1 if `299(A5)`; 0 if no player; 1 if the target record is unused, a player's `+142` is set, or (`150(A6)=0`, 8th frame) the other player is within `|dx| <= $50`, `|dy| <= $20`. The `beq` at `$27c6c` skips `lea 1576(A5),A0`, so with target P1 the other-player test reads a stale A0 | [R]; [L] 0 of 4007 calls returned 1 (one player) |
| `$27cb6` / `$27cdc` | face the target (dead zone +-10 px / none) | `46(A6)` | [R] |
| `$27cf6`, `$27d06` | target's `138` flag / slot blocked flag | `138(A4)` is the player's "moved >= 16 px this frame" pulse (`$8eb8`); slot flags `$ff115c` (P1), `$ff1164` (P2) | [L] `138` pulses 8 times in 2000 frames |
| `$27d30`, `$27d76`, `$27e0c` | at the slot / step toward it / speed ramp | at slot: x error -8..+8 and y error -4..+12 against target + `$28084[146]`; steps `152/156`, ramp `$c00/$600` per frame from `160/164 >> 2` to `160/164` | [L] state 16 frames inside the tolerance 2855 of 2857 |
| `$27e84`, `$27f28` | choose a slot side / reshuffle | side: random slot of the fighter's own side (weights 5,6,5 of 16) unless all three are flagged; reshuffle from row `$27f44[146*16 + RNG&$f]` (slots 3 and 7 never move) | [L] state 14 uses only slots 0,1,2,4,5,6 |
| `$280c8` (`$2811a`) | acquire a target | -1 if `298 \| 297(A5)`; 0 no live player; else A0 = nearest live (`2 == 2`) player by `|dx|`, P1 only if strictly closer (ties go to P2) | [R]; [L] one record chose P2 on a tie against a cloned P2; with two real moving players 70 of 70 acquire events agree (33 P1, 37 P2), `twoplayer.md` |
| `$27fc4`, `$2804e` | slot flag refresh (called from `$6026`, outside the kind-0 range) | parks unused player records at the camera; refreshes one of the 8 slots per player per frame (`166(A5) & 7`): flag 4 off the camera window, else the `$7fac` terrain/prop result | [R]; [L] arrays hold 0, 1, 3, 4 |
| `$22b62` | default target | P2 if its record is in use else P1 | [R] |
| `$22b0a` | engage | `$22b62`, face, then `$22b26` (speeds `160=$20000, 164=$10000`, `3=8`, `4=0`, walk anim) | [L] type 0 spawn: `3=8` next frame |
| `$22b26/$22b7c/$22b9a/$22b44`, `$22bac/$22bca`, `$22bdc` | state setters: to 8 / to 10 / re-pick; slow circle speeds `$19900/$cc00` with `3=18`; resume the script (`3=12,4=0`) | | [R] |
| `$22bea`, `$22c04` | stage-clear mass kill; health watcher | `299(A5)`: `129=1, 24=-1, 63=3`; `24 != 26` gives `3=4,4=0` (and cue `$2c` if `24 < 0`) | [L] see hit reaction |
| `$22c68`, `$22cac`, `$22d8e` | script fetch, combo pick, decision at the slot | see Decision logic | [L] |
| `$22e62`, `$22f6a` | lying / death animation start; entrance pose by type (`3b10` with `A1 = $22f88 + word[type]`, type 0 none) | | [R] |

Animation thunks (`moveq #0,D0 / move.b 20(A6),D0 / lea 6(PC),A1 / jmp $3b10`, four words per character, decoded by `py/ai_kind0/anims.py`):
`$22dd4` fall pose; `$22e00` walk A (6 frames of 7 ticks, `137=0`); `$22e1a` walk and wait stance B (4 frames of 8 ticks, `137=1`);
`$22e36/$22ff6/$23020` held poses; `$22e4c` knockdown flight; `$22e62` lying; `$22e78` stand-up (61 frames); `$22e8e` attack id 6; `$22ea4` id 8;
`$22eba` stun for hit type 0 and 4; `$22ed0` stun for 1 and 2; `$22ee6` id 10 (also the prop smash); `$22efc` id 12; `$22f12` id 18 (jump);
`$22f28` landing; `$22f3e` id 14; `$22f54` id 16. [L] pointer-to-thunk match per state: state 12 with `4(A6)` 6, 8, 10, 12, 16, 18 plays
`22e8e` 1034 frames, `22ea4` 214, `22ee6` 251, `22efc` 162, `22f54` 36, `22f12` 47; state 6 plays `22e62` then `22e78` (61 each); death `22e62` 600.
The `26f0e-26fd8` routines pick the same animations by kind (`19(A6)`) through `jmp (A1)` tables for kinds 0-2.

### Fields and globals used by kind 0

`+2` class, `+3` state, `+4,+5` sub-states (state 12: `+4` is the attack or pause id), `+20` character, `+21` entrance type, `+22` attack id of the last
hit, `+23` hit-stop frames (6 on both fighters at a hit), `+30` timer (word in the entrance idle, byte elsewhere), `+31` fade sub-timer, `+47` palette
bank override (`$12..$15` while materialising), `+54` movement direction, `+62` attacker's facing (knock direction), `+63` hit type, `+64,+66,+68,+70`
grab link and mode (`66 = 2` held), `+80,+82` vx and its decel, `+84,+86` vy and gravity, `+88,+89` collision result, `+99` knock variant, `+102` last
prop touched, `+105` kind of the last hitter (0 P1, 1 P2, `$ff` prop: no score), `+128` thrown-wall-hit-once, `+129` killed by stage clear, `+136`
token flag, `+137` stance B flag, `+138` long pointer to the next combo script byte, `+142` attack roll threshold, `+143` combo-continue threshold,
`+144` target index (1 or 2; a word, `move.w` at `$21d52`), `+146` slot id, `+148` target record (word; already a player record at spawn), `+150` re-target cooldown (a word, 180 at acquire), `+152,+156` current x and y step
(16.16), `+160,+164` target steps, `+168` word used by entrance type 9, `+174` moved flag, `+175` blocked countdown. A record whose `+0` has bit 7 set is skipped for
one frame and the bit cleared (`$5806`), so a spawn shows state 0/0 for a frame and runs its init on the next [L].
Globals: `$ff1150` RNG, `$ff1154` alive count of kinds 0-2, `$ff115a` tokens, `$ff115c/$ff1164` slot flags, `166(A5)` frame word (+1 per frame, 8438 of 8442; it
stalled 3 frames at f1 6251-6253), `168(A5)` difficulty rank (+1 per 600 frames: frames 4677, 5277, 5877 in 3 of 4 runs; one run had a change at 6274), `169(A5)` its
low byte, `299(A5)` stage clear.

### States

Class `+2` (dispatch `$21cfa`, index = byte / 2):

| `+2` | entry | meaning | evidence |
|---|---|---|---|
| 0 | `$21d02` | spawn: sub 0 init (`$21d32`), sub 2 hidden wait (`$21df4`, type 7) | [L] 4 spawns, init takes 1 frame |
| 2 | `$21fde` | live: `$412a`; `66 = 0` normal (`$22008`), `66 = 2` held (`$22004` to `$26ff4`); every 8th frame `$3bb0` | [L] 8450 frames |
| 4 | `$21f5e` | dying: sub 0 `30 = $3c`, anim `$22e62`, score award `$288c` (twice, P1 and P2, if `129`); sub 2 counts 60 frames then `+2 = 6`; drawn 3 of 4 frames (`$32a2`) | [L] 10 of 10 deaths: 1 + 60 frames |
| 6 | `$21fd2` | remove: release token, `$ff1154--`, `$3878` | [L] 10 of 10 |

Spawn init (`$21d32`): `14 = 10`, `50 = $d23b4`, clear `129,136,137,138,144,146,148,150,152,156`; `56/92` from the 8-byte record at `$21d12 + 8 * char` (type 9
takes BRED's `$23e7c/$23f2c`); `$2fa2`; `$21e3c` (`142 = byte[$21e5e + 64*char + v]`, `143` = the byte 32 on); `$22b62`; `$27a42`; then by type (`$21db6`): types 0-6, 8, 9 go live
(`+2 = 2, +3 = 0`, `46 = 54`), type 7 in stage 0 (`190(A5) == 0`) hides first, types 10-14 start with `y--`.

Live sub-states `+3` (table `$22026`, state = 2 * index):

| `+3` | handler | meaning | observed |
|---|---|---|---|
| 0 | `$22044` | entrance behaviour by type (below) | 573 frames |
| 2 | `$22450` | `rts` (held-mode idle only) | |
| 4 | `$22452` to `$2730a` | hit reaction | 1522 frames |
| 6 | `$2246c` | lie after a knockdown, then stand up: `4=0` init, `4=2` random wait 1..60, `4=4` anim `$22e78` until its flag, then `$22b26` | 122 frames; waits 20, 50, 30 plus 61 |
| 8 | `$224e2` | acquire (`$280c8`), face, `150 = 180`, then `$22b7c` | 16 episodes, 1 frame each |
| 10 | `$2250e` | choose the slot side (`$27e84`), face, `+3 = 14` | 212 episodes, 1 frame |
| 12 | `$22524` | attack and pause script engine (`+4` ids); frozen while `23(A6)` runs | 8605 frames |
| 14 | `$22798` | chase to the slot | 3355 frames |
| 16 | `$22814` | wait at the slot (70 frames) | 2857 frames; 16 of 47 episodes 71 frames |
| 18 | `$22874` | chase with the slow circle speeds; first checks the player's `138` flag (to 26) | 3312 frames |
| 20 | `$228fa` | start a charge: slow speeds, face, slot 3 or 7, then 18 | 32 episodes, 1 frame |
| 22 | `$2290a` | drop to the ground after a release in the air | not seen live |
| 24 | `$22968` | stand still `rand{5..40}` frames, then 8 | 4 episodes, 13-31 frames |
| 26 | `$229ec` | wait `rand{1..190}`, then the decision | 6 episodes, 25-49 frames |
| 28 | `$22a6e` | smash the prop in `102(A6)`: face it, anim `$22ee6`, when `45(A6)` is set the prop gets `24 = -1, 105 = $ff, 23 = 6` and the fighter `23 = 6`; anim end to 8 | [L] 2 of 2 episodes, 58 frames in all |

Transition counts over the four runs: 14 to 10 86, 14 to 18 42, 14 to 16 33, 14 to 12 26, 14 to 20 17, 14 to 4 6; 10 to 14 212; 12 to 10 55, 12 to 4 8;
16 to 10 28, 16 to 18 10, 16 to 20 9; 18 to 10 28, 18 to 12 25, 18 to 16 12, 18 to 20 6, 18 to 26 6, 18 to 28 2, 18 to 4 4; 20 to 18 32; 8 to 10 16;
4 to 12 10, 4 to dying 10, 4 to 24 4, 4 to 8 3, 4 to 6 1; 24 to 8 3; 26 to 12 4; 28 to 8 2. A fighter whose slot is flagged blocked alternates 10 and 14
every frame (seen once). `hist.py` prints these.

### Entrance types (`+21`, state 0, dispatch `$22070`)

| type | behaviour | evidence |
|---|---|---|
| 0 | engage at once (`$22b0a`) | [L] spawn: `3 = 8` next frame |
| 1-6, 8 | idle, hurt box 0 (invulnerable) for types 1, 2, 3, 5, 8, hittable for 4 and 6: `+30` word = `{60 x4, 120 x7, 180 x10, 240 x7, 300 x4}` frames by `RNG & $3e`; every 8th frame `$27a04` or the timer ends it (`30 = 10, 4 = 4`, then `$22b0a`) | [L] type 2 cold boot: 66 frames with `44 = 0`, woke 12 frames early; types 4 and 6 spawn waiting; type 1 (poked) 162 frames, then 10, then `3 = 8` |
| 7 | stage 0 only: hidden wait `{20, 80}[54]` frames in class 0 with palette bank `47 = $12 + char`, then a 16 px drop (`y += $10`, steps `-3,-2,-2,-2,-1 x5,0,0,-1,0,0,-1,0`) with a 16-step palette fade, then `$22b0a`; other stages engage. Spawned by the door gangs of stage 0 area 0 (pool 8 kind `$23`, `placement.md`; 6 of 6 [L]) | [L] type 7 poked on a fresh record: 80 frames class 0, 48 frames at y 46 to 30, `47` from 18 to 0, then `3 = 8` |
| 9 | `$ff1154++`, `4 = 8`: scripted walk-in at 4 px per frame toward P1, attack anim `$22ee6`, sets `129(A0) = 1` on the player; `168(A6)` must be set by the spawner | [R]; a poked type 9 (no `168`) falls through to `3 = 8` in 1 frame |
| 10-14 | drop from above: `4 = 10`, random hover wait `{36..180}`, `ground = $3f`, fall with `$30d4` and `$7d6c`, landing anim `$22f28`, 6 frames, `$22b0a` | [L] type 10 poked: 17 frames from spawn to `3 = 8` through `5 = 0, 2, 4, 6, 8` |

### Hit reaction (`+3 = 4`, `$2730a`)

`$22c04` runs every frame in live state: `24 != 26` sets `26 = 24`, `3 = 4, 4 = 0`, and calls `$b8a` if `24 < 0`. With `299(A5)` set it marks the fighter on its own
`(167 + D7) & $f == 0` frame (`129 = 1, 24 = -1, 63 = 3`). [L] a poke of `63 = T`, `62 = 1`, hp 10 to 8 on DUG gives state 4 the next frame; the stage-clear poke marked
3 of 3 kind-0 records on frames 4207, 4208, 4209 (exactly their phase frames) and each was removed 62 frames later. `$2732c` sets `46 = !62`, `54 = 62`
(airborne and `63 != 8` counts as type 3), then dispatches on `63` (`$27364`):

| `63` | `+4` | animation | frames [L] | then |
|---|---|---|---|---|
| 0, 4 | 2 | `22eba` | 26 | `$22456`: token holder to `3 = 12` (anim `22e1a`), else `$22b26` |
| 1 | 4 | `22ed0` | 26 | same |
| 2 | 6 | `22ed0` | 26 | same |
| 3, 7 | 8 | `22e4c`, then `22e62` | 66: flight 35 (vy `$380`, vx `$200` away from the attacker, lift `y += $34/$3f/$34` by kind, `$279c0`), bounce 17 (`$280,$280`, dust), slide 13 (vx `$100`, decel `$14`) | `3 = 6` (lie 20/50/30, stand up 61), then 8 |
| 5 | 12 | `23020` set | 38 | `3 = 6` |
| 6 | 14 | facing flipped | 11 | `3 = 6` |
| 8 | 18 (`99 = 1`) | | 66 | `3 = 6` |
| 9; hp < 0 for 0-3, 7, 8 | 20 | | 77 | hp >= 0: `3 = 6`; hp < 0: `+2 = 4`, cue `$2c` |

Hit-stop: `23 = 6` on both fighters; the stun state keeps stepping its animation, the attack and pause handlers freeze. A lethal poke (63 = 0, hp -1): flight 77 frames,
dying 61 (1 + 60), removed 141 frames after the poke, the stage script respawned the record 12 frames later. Held mode (`66 = 2`): `3 = 0` init, `3 = 4` follow
(`$41ba`, pose from the `$22ff6` set by `67(A6)`); damage of type 3 and 5-9 releases it into `3 = 4` (`$27074`), a broken link into `+2 = 2`, `+3 = 22` (airborne) or 24 (`$272e4`);
thrown flight `3 = 6` (`$27108`, four sub-states: `$3f7a`, `$28b4`, `$aaa`, dust). [L] held exits: `2.4.0` 4 times, `2.24` 4 times; the thrown path was not seen.

### Decision logic

```
acquire (state 8):   r = nearest_live_player()                  // $280c8
                     if r > 0 { 144 = r; 148 = &player[r]; face(target); 150 = 180 }
                     speeds 160 = $20000, 164 = $10000; state 10
state 10:            146 = random slot on my side (0..2 left of the player, 4..6 right; other side if all three flagged); state 14
slots (dx, dy from the player, $28084): 0 (-$60,+$12)  1 (-$80,0)  2 (-$60,-$16)  3 (-$40,0)
                                         4 (+$60,+$12)  5 (+$80,0)  6 (+$60,-$16)  7 (+$40,0)
retarget:            only if 150 == 0, on an 8th frame, and the other player is within |dx| <= $50, |dy| <= $20   // $27c34
chase (14, 18):      r = abandon_check(); if r < 0 goto 10; if r > 0 goto 8
                     if in_melee_window()  { take token; state 12, 4 = 0 }              // $27b00, ignores the token cap
                     else if at_slot()     { decide() }                                  // $27d30
                     else { step_toward_slot();
                            if collide() == blocked {
                                 if type != 9 && moved && 88 == 3 && facing == dir && --175 == 0 { state 28 }
                                 else if slot_flag[146] { state 10 } }
                            every 8th frame face(target) }
                     (state 18 first: if player.138 != 0 { state 26 })
wait (16):           on entry 30 = 70; each frame melee window -> 12; not at slot -> 10; --30 == 0 -> decide()
wait (26):           30 = rand{1..190}; melee window -> 12; --30 == 0 -> decide()
decide():            // $22d8e
    if token_held { state 12, 4 = 0; return }
    if (RNG & $f) <= 142 && take_token() { state 20; return }          // cap = tok1[168(A5)]
    s = reshuffle(146); if s >= 0 { 146 = s; slow circle speeds; state 18 } else state 16
charge (20):         face; 146 = (player.x > x) ? 3 : 7; state 18
attack engine (12):  4 == 0: r = abandon_check(); if r < 0 { state 10 } else if r > 0 { release token; state 8 }
                     face(target); if target_gate() { return }      // target dead / airborne / special: wait id 2 or 4, script kept
                     if in_attack_range() { next_script_byte() } else { release token; state 10 }
  next_script_byte:  b = *138++ ; if b >= 0 { 3 = 12; 4 = b }
                     else if (RNG & $1f) < 143 { pick combo; continue } else { clear script; release token; state 10 }
  ids 6..18:         5 = 2, play the attack animation, end on flag 41 < 0 -> 3 = 12, 4 = 0 (anim 22e1a)
  id 2 / 4 (pause):  wait rand{6..14} / rand{10..70} frames, every 8th frame face the target, then 4 = 0
```
Decision counts (`hitc.lua`, 2000 idle frames): `$22d8e` 44 (4 token holders), roll `$22da0` 40, passed `$22dae` 19, token granted `$22db4` 4, reshuffle `$22dc0` 36 (23 circle, 13 wait);
combo fetch `$22c68` 55, end marker `$22c8c` 3; `$27c34` 4007 calls all returning 0. Slot rule after state 20: 32 of 32.

Combo scripts at `$22d68`, picked by selector byte `$22ce8 + 32*char + (RNG & $1f)` (value = combo * 2):

| combo | `+4` values | selector weights out of 32 |
|---|---|---|
| 0 | 6,2,6,2,8,4 | BRED 20, DUG 16, SIMONS 7 |
| 1 | 6,2,6,2,12,4 | DUG 8, JAKE 16, SIMONS 7 |
| 2 | 6,2,6,2,16,4 | BRED 12, SIMONS 6 |
| 3 | 18,4 | JAKE 6, SIMONS 6 |
| 4 | 10,2,10,2,12,4 | DUG 8, JAKE 10 |
| 5 | 14,2,14,2,16,4 | SIMONS 6 |

[L] the attack ids seen per character are inside what those combos reach: BRED {6,8,16}, DUG {6,8,10,12}, JAKE {6,10,12,18}. Thresholds `142` (attack roll) = `6,7,7,8,8,8,8,9,9,9,9,10 x4,...,15`
and `143` (combo continue, out of 32) = `v + 1`; the tables are identical for all four characters. Randomness enters at: entrance idle length, drop wait,
get-up wait, pauses, combo pick and continue, the attack roll, slot choice and reshuffle, the blocked counter. The difficulty rank `168(A5)` enters through the token cap
(`$27b5a`), the alive cap (`$3e88`; [L] 4 alive at ranks 8-11) and, when a script's variant byte has bit 7 set, `96(A6) = 169(A5)` [R] (the live spawns had explicit v 0 and 4).

### Attack set and damage

The attack box `+8` word is the damage row offset, `+11` the victim's hit type (`63`). Box geometry and hit types are the same for all four characters.
Damage is `byte[92(A6 of the attacker) + box +8]`, with `92` already holding the variant column; v 0 values:

| id (`+4`) | anim | box (`45`) | dx, dy, hw, hh | row | type | dmg BRED/DUG, JAKE, SIMONS | combos | [L] events |
|---|---|---|---|---|---|---|---|---|
| 6 | `22e8e` | 1 | 33, 69, 39, 10 | $00 | 0 | 4, 6, 6 | 0, 1, 2 | BRED 24, DUG 7, JAKE 1 |
| 8 | `22ea4` | 7 | 33, 69, 39, 10 | $00 | 3 | 4, 6, 6 | 0 | BRED 6, DUG 6 |
| 10 | `22ee6` | 2 | 30, 69, 48, 10 | $20 | 0 | 8, 12, 12 | 4 | BRED 1, DUG 3, JAKE 1 |
| 12 | `22efc` | 3 | 30, 69, 48, 10 | $20 | 3 | 8, 12, 12 | 1, 4 | DUG 3, JAKE 3 |
| 14 | `22f3e` | 4 | 32, 52, 37, 19 | $60 | 1 | 12, 18, 18 | 5 | not seen |
| 16 | `22f54` | 5 | 32, 52, 37, 19 | $60 | 3 | 12, 18, 18 | 2, 5 | BRED 1 |
| 18 | `22f12` | 6 | 31, 22, 44, 21 | $40 | 3 | 20, 24, 30 | 3 | JAKE v 4: 28 |

Rows rise with v: BRED row 0 is 4,5,6,7,8,8,8,9,... 17 at v 31, row 2 is 20 to 33. [L] `dmgcheck.py`: 59 of 59 damage events on Cody from a single kind-0 attacker equal
the table value, 14 distinct (character, box, v) cases (BRED v 4 box 1 = 8, JAKE v 4 box 2 = 16). Attack animations: ids 6 and 8 last 16 frames (5 + 5 + 5, flag on the last), 10 and 12
22 frames, 14 and 16 40, the jump (18) crouches 5 ticks, then vy `$780`, vx `$280` (decel 5), gravity `$66`, and lands with `$22f28`.

Per character data (base, +`$60` is damage row 0): BRED `$23f2c`, DUG `$24eca`, JAKE `$25e70`, SIMONS `$26e16`; box and animation data `$23e7c`, `$24e1a`, `$25dc0`, `$26d66`.
Hit points by variant: BRED 28 to 96, DUG 41 to 109, JAKE 64 to 126, SIMONS 80 to 142. Defence class `+55`: BRED and DUG 0; JAKE and SIMONS 4, 5, 6, 7, 8
(v 0-6, 7-14, 15-22, 23-30, 31). Kill points (BCD, table `$1b26`, ids `$07, $13, $14, $16`): 1000, 1200, 1400, 1600. Kind 0 never grabs a player (no grab attack box), uses no
weapon and does not run (the circle state is slower than the chase: `$19900/$cc00` against `$20000/$10000`); its specials are the prop smash (state 28) and the jump (id 18).

### Not proven

- Entrance type 9 (needs the spawner's `+168`) and types 11-14; the thrown flight, `$3f7a` and `$6c96`: need a Cody throw or a poked link (`64 = $ff`, `68 = holder`) on a held enemy.
- The `$27c34` abandon branch with a second player (two-player targeting itself is proven, 70 of 70, `twoplayer.md`; the branch's return was not separately counted).
- `$7d6c` result codes other than prop contact and stage edge, `$7fac`, and the meaning of `+42,+43,+48,+49` (sprite attributes).
- The alive-cap and token tables are [R]; only their consequences are [L]. The `169(A5)` variant path has no live spawn.

## Kinds 1, 2 and 3

Kind 1 (`$2813a-$2a310`) is J and TWO.P, kind 2 (`$2a310-$2ccac`) AXL and SLASH, kind 3 (`$2ccac-$3136c`) the ANDORE family. Kinds 1 and 2 are one engine
(`py/ai_kind123/seqdiff.py`: 631 of 767 and 768 instructions identical, the rest is kind 2's guard) and share the kind 0 helpers of the table above
(`$280c8`, `$27b00`, `$27b5a`, `$27d30`, `$27e84`, `$27fc4`, `$3b10`, `$2fa2`, `$7d6c`, `$2730a`); this section does not repeat them. State numbers are decimal
(`3(A6)` = 2 * table index), attack ids are the `+4` values. Scripts and gates: `py/ai_kind123/` (`README.md` there). None of the three kinds is live in a saved state, so
`py/ai_kind123/fdrive.lua` loads `ff_enemies` and emulates the tag-2 allocator `$3892` (`FF_SPAWN`: pops the free stack `20242(A5)`, zeroes `+0..+127` except the
effect-group handle `+78`, writes `+0,+6,+10,+18..+21,+96`, bumps the `$3e88` counter); `FF_NOSCRIPT` parks the stage script (`$ffb1ea = 6`) for a clean arena. Zeroing `+78`
makes the first hit spark `$7b78` fault (address error, vector 3). Saved state `scratchpad/finalfight/ff_kinds123.sta` (frame 4300: ANDORE, SLASH, AXL, TWO.P, J at rank 4, no stage script).

### Identity

The HUD name object is filled by `$5b640` (not `$5b4aa`, which only clears a flag): entry = `A0 + word[A0 + 2*kind] + 32*subtype`, `A0 = $5b682 + word[$5b682 + tag]`; an entry is a
palette, four portrait tiles, a palette and ten name tiles (`$44xx` = ASCII xx); the object keeps the tracked record's tag, kind and subtype in `+18..+20` and the entry address in `+148`
(`py/ai_kind123/names.py`). The table gives, for tag 2:

| kind | `+20` names |
|---|---|
| 0 | 0 BRED, 1 DUG, 2 JAKE, 3 SIMONS |
| 1 | 0 **J**, 1 **TWO.P** |
| 2 | 0 **AXL**, 1 **SLASH** |
| 3 | 0 **ANDORE Jr.**, 1 **ANDORE**, 2 **G.ANDORE**, 3 **U.ANDORE**, 4 **F.ANDORE** |
| 4, 5, 6 | 3, 2, 2 entries (G.ORIBER, BILL BULL, WONG WHO; HOLLY WOOD, EL GADO; ROXY, POISON); kinds 7, 8 alias kind 5's block |

Live [L] (`gates.py names`): after Cody hits a spawned fighter, the HUD object holds the matching entry address and the entry's text reads J, TWO.P, AXL, SLASH, ANDORE Jr., ANDORE,
G.ANDORE, U.ANDORE, F.ANDORE: 9 of 9 (a screenshot montage, `scratchpad/finalfight/p3/b/out/hud_all.png`, shows the same names on screen). So the old "AXL by HUD order" is confirmed.
Note `92(A6)` after `$2fa2` is `base + $60 + rank` (the damage rows), so census names keyed by `92(A6)` hold only at the spawn rank: AXL's base is `$2bf30`, `$2bf94` is rank 4.
`+21` is the entrance variant, `+96` the rank 0..31 (index into every stat table below); `$5ee6` copies script entry bytes 14, 13, 12 to `+96`, `+98` and `+54`, and a negative rank byte becomes `169(A5)`.

### Spawning

The live stage table is `$5f7e` (the word `$726e0` is 2, so `$5aea` never uses `$5f5e`). `py/ai_kind123/script_scan.py` walks it and `spawntable.py` lists tag-2 entries of kinds 1-3
(`stage = 190(A5)`, `area = 191(A5)`; entry address, rank; "2P" = entry byte 15 set: `$5f46` skips the entry unless both player records are in use; "diff" = rank byte `$ff`).
The parser covers the ordinary groups; unusual modes may hide some, so this is a lower bound [R]:

| fighter | entries |
|---|---|
| AXL | 0/0 `$706b4` (rank 4, camera trigger `$3f0`); 1/3 `$70c28` (diff, 2P); 2/2 `$70c28` (2P); 3/1 `$71206`, `$71236` (rank 0); 5/1 `$71646`, `$71696` (0) |
| SLASH | 1/3 `$70c38` (2P); 2/0 `$70a12` (0); 2/2 `$70c38` (2P); 3/0 `$70e92`, `$70ea2` (2P); 3/1 `$71216`, `$71226` (0) |
| J | 0/0 `$706c4` (rank 0, **2P**); 0/1 `$70708` (4); 0/2 `$7076e` (7); 1/1 `$708b0` (2P); 1/3 `$70c08`; 2/0 `$709f2`, `$70a82`; 2/2 `$70c08`; 5/0 `$714d2`; 5/1 `$715f6`, `$71686` |
| TWO.P | 0/1 `$70718` (4); 1/0 `$7082c`; 1/1 `$708c0` (2P); 1/3 `$70c18`; 2/0 `$70a42`; 2/2 `$70c18`; 3/0 `$70e82`, `$70eb2` (2P); 5/1 `$71636` |
| ANDORE Jr. | 1/0 `$7083c` (delay 180, group trigger `$340`); 1/1 `$70880` (`+21 = 4`); 3/0 `$70ec2` (delay 360), `$70ef2` (2P); 5/0 `$71462` (2P) |
| ANDORE | 2/0 `$70a52`; 5/0 `$71452` |
| G, U, F.ANDORE | 2/0 and 2/1: `$70ba4`, `$70bb4` (U, 2P), `$70bc4`, all `+21 = 8` |

The first group of stage 0 (trigger camera x `$3f0`, group `$70676`) holds Dug, Bred, Holly Wood, AXL and J (2P). Live [L]: the cold drive of `plans/plan3.lua` from frame 3000 spawns kind 5 at
3545 and kind 2 at 3665 and **no kind 1 record in 1151 frames**: J is skipped in a one-player game (1 of 1) and spawns in a two-player one (entry `$706c4`, the same segment played with two players: 1 of 1, `twoplayer.md`). Kinds 1 and 2 only ever get `+21 = 0` from the scanned
entries, kind 3 gets 0, 4 and 8.

Throttle (`$3e88`, see the helper table): kinds 0-2 share `$ff1154`; kinds 3-6 each have their own counter at `$ff1155 + kind - 3`, capped by the 32-byte row `$3efa + 32 * (kind - 3)` indexed by
`168(A5)` (kind 3: 1 up to rank 10, 2 up to 18, 3 up to 25, then 4); kinds 7 and up are not counted. Kind 3 frees with `subq.b #1,$ff1155` unless `98(A6)` is set. The attack tokens
(`$ff115a`, caps `$27b88` / `$27bc8`) are kind 0's. Live [L]: three fighters at global rank 8 (token cap 2): `$27b5a` 34 calls, 5 denied, 29 granted, and the count word reached 3 because the
touch path `$27b00` takes a token without the cap.

Difficulty: `168(A5)` (byte `169(A5)`) rises by 1 per 600 frames [L]: 8 at frame 4151, 9 at 4677, then 5277, 5877, 6477, 7077, 7677 (14). It feeds the spawn rank of `$ff` entries, the caps above, and
kind 3 subtypes 2-4, whose rank is `169(A5)` at init (`$2cd7a`) and again every 8th frame (`$2cf22`).

Entrance variants `+21` [L] (one run each, frames from spawn to leaving state 0): kinds 1 and 2 index a word table: 0 engages at once (`3 = 8` at +2); 1-3 wait `{60,120,180,240,300}` frames
(`RNG & $3e`) or until a player is in view (`$27a04`), 192 frames for type 1; 4 and 5 nudge `y` up and drop in (19 frames). Kind 3 indexes a byte-offset table (0, 2, ..., 12): 0 and 2 engage at +2/+3
(type 2 also waits for a player in range), 4 starts the script `$2e84f` (a charge) at +2, 6 the script `$2e853` (leap) at +2, 8, 10 and 12 drop in from above the screen (`y` up to `$110`) and engage at +171, +56, +16.

### Kinds 1 and 2: one engine

Class `+2` (dispatch `$28148` / `$2a31e`, index = byte / 2), as kind 0 [R] [L]: 0 init (`$28150` / `$2a326`: `z = y`, anim `$d23b4`, `56/92` from the 8-byte record per `+20`, `$2fa2`, the three rank bytes,
default target, `$27a42`, then `+2..+5 = 2,0,0,0`); 2 live (`$412a`, state dispatch, health watcher, `$32aa`; `$3bb0` every 8th frame); 4 dying (60 frames, drawn 3 of 4, then 6); 6 free
(`$27c20`, `$ff1154--`, `$3878`). Live [L] after a poked lethal hit (hp -1 at frame 4300, one run per kind): reaction/fall (`4 = 20`, sub 5 = 0, 2, 4, 6) 80 frames (kind 1) or 66 (kind 2), class 4 for 61, record gone at
+143 / +129; kind 3 (state 6): 62 + 61, gone at +125.

| `+3` | kind 1 / kind 2 entry | role |
|---|---|---|
| 0 | `$283ae` / `$2a598` | entrance by `+21`, then acquire |
| 2, 4 | `$285b6` / `$2a7a0` | both are `bra $2730a` (hit reaction table in the kind 0 section); only 4 is set by the handler's own health watcher |
| 6 | `$285d4` / `$2a7be` | lie and get up: `4 = 0` clears speeds, `4 = 2` waits 1..60 frames (random byte table), `4 = 4` plays the get-up anim (`$2908e`) to its end flag, then state 8 (`$28c16`) |
| 8 | `$28648` / `$2a838` | acquire the target (`$280c8`), `150 = 180` |
| 10 | `$28674` / `$2a864` | choose the slot (`$27e84`) |
| 12 | `$2868a` / `$2a87a` | engage: the attack script sequencer, `+4` = attack id |
| 14 | `$28856` / `$2aa12` | walk to the slot (anim `$28f74`: steps 0, 2, 4, 2, 0 px by frame flag `41` through `$28e8a`) |
| 16 | `$288ca` / `$2aa8c` | wait at the slot, `30 = 70`, then decide |
| 18 | `$28924` / `$2aaee` | the same walk code with the slow anim `$28f86` (steps 0, 1.5, 3 px) |
| 20 | `$2898c` / `$2ab5e` | go in: token claimed, slot 3 or 7, then 18 |
| 22 | `$2899c` / `$2ab6e` | fall after a release from a grab in the air (`$272e4` sets `$0216`) |
| 24 | `$289f2` / `$2abd0` | recover after a release on the ground (`$0218`), random wait 5..40 |
| 26 | `$28a72` / `$2ac58` | kind 1: dodge (below); kind 2: nothing sets it |
| 28 | `$28ada` / `$2acda` | kind 1: wait 26..34 frames, then decide; kind 2: guard dodge |
| 30 | `$28b5e` / `$2ad50` | smash the prop in `102(A6)` (`24(prop) = -1`) when `88(A6) == 3` after a walk step with `174` set and `175` steps counted; kind 3 has the same logic in `$2d850` **[R]**, not seen live |

Target, slots and tokens are kind 0's (table above) with these facts for kinds 1-3. The init default target is P2 if its record is in use else P1 (`$28c3c`); state 8 takes the nearer player by `|dx|`
among class-2 records, ties to P2. Live [L] with player 1's record cloned into player 2 (`FF_COPYP2`) at dx +60, 0, -1, +1 from J's distance 128: target 2, 2, 1, 2 (kind 1, 4 of 4); kind 3's `$3068`
(same rule, no class check) gave 2, 2, 1, 2 (4 of 4) (`gates.py target`). The slot table is `$28084`; [L] in 2698 frames waiting at the slot (state 16, `4 = 2`; J, TWO.P, AXL, SLASH, clean arena, 8200 frames each) the
x error was within +-8 and the y error within -12..+4 in 2698 of 2698 (`gates.py slots`). The occupancy bytes `$ff115c/$ff1164` are rewritten by `$28080` one slot per frame per player (4096 byte writes over 2047 frames [L]).

Attack sequencer (state 12): `+4 = 0` picks the next element of the script `138(A6)` (`$28d84`), `2` waits 6..14 frames, `4` waits 10..70 (kind 1 has no `4` in its scripts), any other id sets an
animation and waits for its end flag (`41 < 0`), then `+4 = 0`. A script is chosen by `table[sub][RNG & $1f]` (`$28dc8`, `$2b018`; `py/ai_kind123/atkscripts.py`) and continued after its `$ff`
with probability `143/32`, else the token is released and state 10 follows. Rank bytes: `$281da` / `$2a3c8` read three 32-byte rows per subtype at `+96`: `142` (attack roll `RNG & $f <= 142`),
`143` (continue `< 143`), and `169` (kind 1 dodge roll /32) or `168` (kind 2 guard roll /32); at rank 4: J 4, 2, 4; TWO.P 6, 3, 8; AXL 8, 5, 4; SLASH 8, 5, 8 (`ranktab.py`).

| fighter | pick table (ids, of 32) | scripts (id: `+4` elements) |
|---|---|---|
| J | 0 x4, 2 x4, 4 x9, 6 x9, 8 x6 | 0: 6 2; 2: 10 2; 4: 6 2 6 2 6 2; 6: 6 2 6 2 6 2 6 2 8 2; 8: 6 2 6 2 10 2 |
| TWO.P | 0 x4, 2 x4, 8 x9, 10 x9, 12 x6 | 0, 2, 8 as J; 10: 6 2 6 2 10 2 10 2 12 2; 12: 10 2 10 2 12 2 |
| AXL | 0 x6, 2 x6, 4 x8, 6 x12 | 0: 6 4; 2: 10 4; 4: 6 2 8 4; 6: 6 2 12 4 |
| SLASH | 0 x6, 2 x6, 6 x20 | scripts 0, 2, 6 as AXL |

The decision at the slot (`$28f2e`, kind 2 `$2b0a4`):

```
decide():                                   // after the 70 frame wait in state 16, and on arrival in 14 / 18
  if (136) -> state 12                      // holds a token
  if ((RNG & $f) <= 142 && token_ok()) -> state 20   // $27b5a: count < cap[168(A5)]
  else if ((s = $27f28()) >= 0) { 146 = s; -> state 18 } else -> state 16
```
Live [L] (clean arena, passive Cody): J 13 of 47 rolls passed (28%; 142 = 4 expects 31%), TWO.P 10 of 47 (21%; 142 = 6 expects 44%, about 3 sigma low; the RNG advances one bit per call and is
sampled at near constant strides, so successive rolls are correlated **[I]**); every roll that passed took a token (23 of 23); a script ended 10 + 3 times and continued 1 + 1 times. Per-state frame counts
(J rank 4, passive Cody, 4049 frames; `hist.py`/`edges.py`): 12: 1949 (sub 0: 118, 2: 620, 4: 458, 6: 629, 8: 102, 10: 22), 14: 448, 16: 820, 18: 799, 20: 11, 10: 19; AXL 4049 frames:
12: 2877, 14: 391, 16: 355, 18: 394, 20: 12, 10: 17.

Attack ids, animations, boxes (`anim.py`, `setters.py`, `boxes.py`; tick = one frame; box and type from the attack box, type = `+11` = victim's `+63`):

| `+4` | J, TWO.P | AXL, SLASH |
|---|---|---|
| 6 | anim `$28fe0`, box 3, type 0 | `$2b148` 8+4 ticks wind-up, box 1 (4 ticks), type 2 |
| 8 | `$28ff2`, box 4, type 3 (knockdown) | `$2b15a`, box 2, type 3 |
| 10 | `$28fbc`, 5 ticks wind-up, box 1 (10 ticks), type 0 | `$2b16c`, box 3, type 1 |
| 12 | `$28ff2`, box 4 (same as 8) | `$2b17e`, box 4, type 3 |

(Box 2 of J, `$28fce`, has no caller.) Hit reaction: type -> `+4` [L] 0 -> 2 (14 samples), 1 -> 4 (1), 3 -> 8 (5), the same as the kind 0 table. Held by the player [L] (Cody walks into the fighter): `64 = $ff`, `66 = 2`,
state 4 sub 2 for 160 (kind 1), 300 (kind 2) and 348 (kind 3) frames, released through state 24 (kind 1: 2 of 2, kind 2: 4 of 4) or, for kind 3, its state 10 (at least 3).

Kind 1 pseudocode (kind 2 differs in the dodge and in the guard below):
```
alive: if (linked) held(); else { 150 = max(150 - 1, 0);
  switch (3) {
    8:  (n, P) = nearest(); 144 = n; 148 = P; face(P); 150 = 180; 3 = 10
    10: 146 = pick_slot(); 3 = 14
    14, 18: r = $27c34(); if (r < 0) 3 = 10; else if (r) 3 = 8;
            else if ($27b00()) { token; 3 = 12; 4 = 0 }  else if (at_slot()) decide();
            else { step($27d7a); $7d6c(); if (every 8th frame && occupied[n][146]) 3 = 10 }
    16: if ($27b00()) 3 = 12 else if (!at_slot()) 3 = 10 else if (--30 == 0) decide()
    20: 3 = 18; 146 = (target.x > x) ? 3 : 7
    12: sequencer(4);  4: $2730a();  6: get_up();
  }
  watcher: if (24 != 26) { 26 = 24; 3 = 4; 4 = 5 = 0; if (24 < 0) $b8a(); }       // every frame
           every 16th frame: 299(A5) -> 129 = 1; 24 = -1; 63 = 3
  $32aa(); }
```

### Kind 1: the dodge

`$28eea` runs at the start of every attack sub-state: a new bit `$10` in the target's input byte (`130 & ~131`) while the target's `164`, `165` or `169` is set (player attack flags, cleared at
the end of attacks by `$a70a`, `$abe2`...), then `RNG & $1f < 169(A6)` sets `168 = 1` and `$28c90` goes to state 26 with the back-step anim `$28faa` (flags `$58,$50,$48`: fast steps) and releases the token.
State 26 then picks a slot like 10 and walks to it (`$28a94`), then state 28. While `3(A6) = 26`, the victim handler `$73b8` returns without damage unless the hit type is 7 (`cmpi.w #$21a,2(A3)`) [R]. Live [L]:
with the stage script running and Cody mashing, `$28c90` ran 2 times (39 frames in state 26, 3 in state 28); poking state 26 for 100 frames with Cody attacking: the blocked return `$73e2` 2 of 2 attempts, health
unchanged. In a clean arena (8000 frames mashing) `$28eea` ran only 9 times and saw no button edge (0 of 9), so the dodge is rare against a single engaged fighter.

### Kind 2: the guard

Kind 2 replaces the button-edge dodge by a rolled guard: fields `170` armed, `171` attack seen. The victim handler `$73e4` does `171 |= 1`, hit-stop 6 and records attacker kind, id and type in `105/22/63`; if the type is 7, or bit 7
of the type is set, or `170 >= 0`, it clears `170` and takes the normal path (`$7b10`, `$79d8` scaled damage, `$7b18` spark, `$7aa8`, `$28d0`); if `170 < 0` the hit does no damage (only the `$7b60` spark and `$28d0`).
Each frame: state handler, `$2aee6` (`if (171 && 170) { 3 = 28; 46 = 62 ^ 1; 4 = 5 = 0 }` unless already in state 28; otherwise the health watcher, which also clears `170`), then `$2af80`
(`if (171) { 171 = 0; arm(); }`). `arm()` (`$2af88`) keeps `170 = $ff` inside state 28, else `170 = ($2afb4[RNG & $1f] < 168) ? $ff : 0`: probability `168/32`; it also runs at init, at get-up and at the end of the dodge. State 28
(`$2acda`): `4 = 0` clears speeds, anim `$2b190`, cue `$aca`; `4 = 2` slides `x` by `{5,3,2,1,1}` times the facing and runs `$7d6c`, until the table's `$ff` (29 frames); then with a token it attacks at once (`3 = 12`), else state 8. Live [L]
(clean arena, Cody mashing, 8000 frames): AXL 115 hit attempts, 40 blocked, 75 landed, 20 dodges, 106 rolls with 12 armed (11.3%; 4/32 = 12.5%); SLASH 117 attempts, 53 blocked, 64 landed, 28 dodges, 101 rolls with 25 armed
(24.8%; 8/32 = 25%) (`gates.py guard`); the dodge state lasted 29 frames in 48 of 48 (`3 = 28` runs). The slide is written at `$2ad28` and undone by the terrain probe in the test arena (x unchanged), so its distance is **[I]**.
AXL and SLASH also use `160/164` speed longs (`$2ae08`: `$23300/$11900`, `$2ae82`: `$1e600/$f300`) and `169(A6) = 41(A6)` as walk phase.

### Kind 3: ANDORE Jr., ANDORE, G., U., F.ANDORE

Structure [R] [L]. Classes (`$2ccba`): 0 `$2ccc2`, 2 live `$2cee8`, 4 dying `$2ce60` (60 frames, cue by `+20` `$2cec0`), 6 free `$2ced6`. Init allocates a pool-8 child, kind `$1f` (`$3946`, `128(child) = A6`), whose handler `$1f3b0`
copies the owner's `x` and ground line `+14` each frame: the ground shadow. `$2cd3e` sets `47(A6)` (palette/sprite variant) `{0, $d, $12, $13, $14}[sub]`. All five share the box base `$30e14`; sub 0 and 1 have their own character data (`$30eec`, `$3100c`),
subs 2-4 use `$3112c` (`$3124c` with two players: health 375 instead of 250) with rank `169(A5)`; G, U and F differ only in palette. Live: `66 = 0` normal, `66 = 2` linked (`$2e922`, own table `$2e940` whose only real
entries are 0 `$2e9c0`, 2 `$2e9e6`, 4 `$2ee94`, 6 `$2ef14`).

| `+3` | entry | role |
|---|---|---|
| 0 | `$2cf5a` | entrance by `+21` (above) |
| 2 | `$2d380` | AI: `4 = 0` init, `4 = 2` walk (below) |
| 4 | `$2d4b2` | attack, `+4` = 0..24 (13 sub-states, table `$2d4be`) |
| 6 | `$2e028` -> `$2f106` | hit reaction: first frame faces the attacker, then `+4` by hit type as kind 0 (2, 4, 6, 8, 2, 12, 14, 8, 18, 20); light reactions return to state 2 |
| 8 | `$2e02c` | land and recover |
| 10 | `$2e092` | wait 5..40 frames after a grab release |

AI (state 2) [R]: the target is `$3068` at init and every 180 frames (`141`); the destination `$2e3f6` is a point beside the target at `$50` or `$80` px on the player's side, flipped when the (player, side) reservation counter
at `$ff116c + 2 * player + side` is set (`$2e598` increments, `$2e5a6` decrements; [L] 6 and 5 writes in 1050 frames) or the point is blocked (`$7fac`). Each frame the AI faces the target every 8th frame, switches to the player in the melee window
(`$2e608`: `|dx| <= $30`, `|dy| <= 9`, not down (`137`), not jumping (`90`)) and enters state 4 with `4 = 0`; with `142 != 0` it counts that cooldown (random 30..120) down; on arrival within 9 px (`$2e8c6`) with the target on the
ground `$2e6f4` starts a script at once when `138 = $50`, else with probability `(147 + 1)/32` the charge (id 8, below), else a new destination; `178(A6)` at `>= 250` forces id 24. `147` is
`$2cdc0 + 32 * sub + rank` (sub 0: 3, 4, 4, 5, 5, 6, ...; sub 1: 3, 4, 5, 6, ...; subs 2-4 as 0).

Scripts (`$2e768`, base `$2e790`, script table `$2e79a`; `atkscripts.py 2e790 5 2e79a`). ANDORE Jr. picks the script by `table[RNG & $1f]`: ids 0 x5, 2 x5, 4 x10, 6 x2, 8 x2, 10 x7, 12 x1 of 32, which run (script id: elements) 0: `12 4 6`; 2: `10 2 10 2 12 4 6`;
4: `10 2 10 2 14 4 6`; 6: `10 2 10 2 16 4 6`; 8: `12 2 18 4 6`; 10: `12 2 18 18 4 6`; 12: `10 2 16 2 18 4 6`; ANDORE reweights the same scripts (6 x8, 8 x8, 12 x4); G, U and F use grab-heavy scripts
(`10 2 14 4 6`, `10 2 16 4 6`, `14 4 6`, `16 4 6`, `12 2 18 2 18 4 6`, `12 2 18 2 18 2 18 4 6`, `16 2 18 2 18 4 6`). Every script ends with 4 (long wait) and 6 (retreat).

Attack sub-states `+4` in state 4 [R] [L] (anim scripts decoded by `anim.py`; damage at rank 4 from the table below):

| `+4` | what | evidence |
|---|---|---|
| 0 | sequencer: next script element, else back to state 2 | [L] 53 of 2745 frames |
| 2, 4 | short wait 6..14, long wait 10..70 | [L] |
| 6 | retreat step: random wait, then walking backwards (anim reversed `$3b76`, speed to about 2 px) | [L] the most used, 1126 frames |
| 8 | shoulder charge toward the target on a 32-direction heading (`$31f4`, `$3180`), box 5, type 3 | [R] [L] 16 damage |
| 10 | jab: anim `$2fdec`, box 2, type 0 | [L] id 2 type 0 dmg 9, 12 hits |
| 12 | punch: anim `$2fe00`, box 3, type 3 | [L] id 3 dmg 9, 4 hits |
| 14 | running grab (grab box `$86`, `158 = 0`), then holder mode (state 2, `+4 = 2` in the linked table): 2..6 squeeze cycles (`162` from `$2ea62`) of 21 frames, 9 damage each (type 0), the last with `63 = 3` | [L] holds with 3, 5, 5 cycles (ANDORE Jr.), 6, 5, 4, 2 (G.) |
| 16 | running grab with `158 = 1`: linked `+4 = 4` carry and slam | [L] 114 frame holds, no squeeze cycles (ANDORE, 5 of 5); throw damage 61 (ANDORE), 31 (ANDORE Jr.) |
| 18 | aimed leap: crouch (anim `$30194`, 15..45 frames), `84 = $780`, gravity `$40`, horizontal speed 4 x offset to the target re-aimed every 4th frame | [R] [L] |
| 20 | slam on landing: anim `$300da`, box 7, type 3 | [L] id 7 dmg 16 |
| 22 | long wait (variant of 4) | [R] |
| 24 | jab from the frustration counter | [R] [L] forced |

Clean-arena frame counts (4049 frames each): ANDORE Jr.: state 2: 1227, state 4: 2820 (sub 0: 53, 2: 166, 4: 377, 6: 1126, 10: 247, 12: 96, 14: 22, 16: 17, 18: 488, 20: 228); ANDORE: 927 / 3120; G.ANDORE: 171 (entrance) / 1320 / 2558.
Hit reaction (state 6) [L]: type 0 -> `+4 = 2` (3 samples), type 3 -> 8 (3).

### Characters, stats and damage

Health = `word[base + 2 * rank]`, defence `+55` = `byte[base + 64 + rank]`, damage = `byte[base + $60 + rank + row]`, `row` = word 8 of the attack box (`py/ai_kind123/statstable.py`). Ranks 0 / 4 / 8 / 16 / 31:

| fighter | health | defence | attack id: type, damage |
|---|---|---|---|
| J | 28 / 36 / 42 / 66 / 96 | 0 | 1: 0, 8/12/13/16/21; 3: 0, 2/6/7/10/15; 4: 3, as 3 |
| TWO.P | 64 / 72 / 80 / 96 / 126 | 0 | 1: 16/20/21/24/29; 3, 4: 4/8/9/12/17 |
| AXL | 28 / 36 / 42 / 66 / 96 | 6/6/7/8/10 | 1: 2 and 2: 3, 30/34/35/38/43; 3: 1 and 4: 3, 40/44/45/48/53 |
| SLASH | 42 / 50 / 64 / 80 / 110 | 12/12/13/14/16 | 1, 2: 40/44/45/48/53; 3, 4: 50/54/55/58/63 |
| ANDORE Jr. | 100 / 116 / 132 / 164 / 224 | 4/6/8/12/20 | 1, 4, 5, 7: 15/16/17/20/31 (type 3); 2: 0, 3, 6: 8/9/10/12/17 |
| ANDORE | 200 / 216 / 232 / 264 / 324 | same | 1, 4, 5: 25/26/27/30/41; 2, 3, 6: 10/11/12/15/21; 7: 15/16/17/20/31 |
| G, U, F.ANDORE | 250 (375 with two players; the table reads 160 at rank 15 and 224 at 31 where it overlaps other data) | same | 15/16/17/20/31; 10/11/12/16/31 |

Boxes (dx, dy, hw, hh): J and TWO.P all four 43, 72, 43, 12; AXL and SLASH boxes 1-2 38, 59, 44, 23 and 3-4 29, 59, 57, 19; ANDORE box 1 27, 50, 23, 44, boxes 2-3 56, 73, 51, 19, 5 30, 50, 26, 44, 6 35, 50, 31, 44,
7 16, 22, 51, 22, box 4 empty; hurt boxes of J and TWO.P all 0, 40, 16, 30. Live [L] (`gates.py damage`, clean arena, passive Cody, 8200 frames each): every hit on Cody equals the table at rank 4: J 40 of 40 (id 1: 12, id 3: 6 x35, id 4: 6),
TWO.P 27 of 27 (20, 8, 8), AXL 17 of 17 (34 x13, 44 x4), SLASH 14 of 14 (44 x8, 54 x6). ANDORE Jr.: jab and punch 9, slam 16 (squeeze 9 x10, landing slam 16 x5, throw 31 x2); ANDORE: 11, 11, 16, charge 26, throw 61. Spawn health 36, 72, 36, 50,
116, 216, 250 as tabulated. None of the three kinds picks up or swings a weapon in the code read; only kind 3 throws, jumps and runs.

### Not proven

- State 30 (prop smash) and kind 3's `$2d850`: needs a breakable prop on the walk path with `88 == 3`; an attempt with the prop at x `$540` did not trigger it. Proof: tap `24` of the prop and `102(A6)`.
- States 22 (airborne release) and kind 2 state 26 (looks dead); the two-player throttle table (the token tables are proven, `twoplayer.md`; the alive caps `$3e88` have no two-player term).
- Kind 3: the linked states `$2e9c0`, `$2ee94`, `$2ef14`, `$2e254`, `$2e21c`, hit types 5-9 in state 6, the player flags `164/165/169`, and the throw damage 31/61 (not a box: the `$3f7a`-style release).
- The guard slide distance of AXL; the TWO.P roll rate.
- Kind 1 and 2 entrance variants 1-5 and kind 3's 2, 6, 10, 12 are never produced by the scanned script entries (the placement trigger lists, `placement.md`, place kind 1 variants 1, 2, 3, 5, kind 2 variants 1, 2 and kind 3 variants 4, 6, 10, 12, not exercised live); they were exercised by spawning only.

## Kinds 4 and 5 (G.ORIBER, BILL BULL, WONG WHO; HOLLY WOOD, EL GADO)

Kind 4 is three heavy brawlers, kind 5 two weapon fighters. Both are the common template (init, main, death, despawn, the same held,
thrown, hit-reaction and drop-in code) with different attack content. Everything below was read in `fighters.asm` ranges `$3136c-$33200`
and `$3514c-$36f84` [R] and checked on fighters spawned into `ff_enemies` by `py/ai_kind45/drv.lua` (one fighter, Cody idle or tapping
Button 1, health refilled; the spawn replicates `$3892` and `$5ee6`). Frames are counted after the load (frame 4151). Reruns of two spawn
runs gave identical md5 (2 of 2); the saved states are in `scratchpad/ANCHORS.md`.

### Identity, records, spawns

HUD names are built from `+19`/`+20` by `$5b640` (`frame.md`, "Fighter identity"). Kind 4: `+20 = 0` G.ORIBER, 1 BILL BULL, 2 WONG WHO.
Kind 5: 0 HOLLY WOOD, 1 EL GADO. The HUD showed each of the five names (one screenshot each, and the name tiles in gfx RAM, 5 of 5) [L].

`+20` is the character, `+21` the entrance mode (kind 4: 0, 2, 4, 6, 8; kind 5: 0 walk in, non-zero drop in), `+96` the level. A
character record is `base + 0` 32 health words by level, `base + 64` 32 defence-class bytes by level, `base + $60` the damage rows (32
bytes per row, column = level); `$2fa2` loads `+24 = +26 = +28` and `+55` and leaves `+92 = base + $60 + level`. The attack-box
descriptor's word `+8` is the row offset (32 per row) and `+11` the hit type (bit 7 set: hard hit). Animation and box base `+56` is per
character.

| fighter | `+56` | record | health at level 0 / 7 / 15 / 31 | class | damage by attack box at level 0 (level 31) |
|---|---|---|---|---|---|
| G.ORIBER | `$34cb4` | `$34f0c` | 50 / 64 / 80 / 112 | 0 | box 1 30 (47), 2 30 (47), 3 12 (25), 4 12 (25), 5 8 (21) |
| BILL BULL | `$34d7c` | `$34fcc` | 100 / 114 / 130 / 162 | 0 | 1 12 (21), 2 20 (37), 3 12 (25), 4 12 (25), 5 12 (21) |
| WONG WHO | `$34e44` | `$3508c` | 150 / 164 / 180 / 212 | 1 | 1 12 (22), 2 40 (57), 3 15 (28), 4 15 (28), 5 12 (22) |
| HOLLY WOOD | `$37a88` | `$37b80` | 60 / 110 / 126 / 220 | 0 | boxes 1 to 6 all 8 (20) |
| EL GADO | `$387c0` | `$388b8` | 132 / 182 / 198 / 230 | 1 | boxes 1 to 6 all 11 (24) |

Initial health matched 5 of 5 (50, 100, 150, 60, 132); level 7 HOLLY WOOD 110, level 20 WONG WHO 190 [L]. Damage Cody lost to a spawned
fighter's attack box equalled the table byte in 151 of 151 hits (kind 4: 21, 19, 17; kind 5: 15, 3, 2, 4, 1, 27, 1; level 7: 11; level 20:
13; `gate_dmg.py`) [L]. Attack boxes (dx, dy, half-width, half-height): kind 4 boxes 1, 3, 4 `20, 46, 39, 18`, box 2 `20, 21, 39, 18`,
box 5 `21, 54, 57, 29`; kind 5 boxes 1, 2 `36, 59, 47, 17`, 3, 4 `49, 59, 56, 17`, 5 `21, 11, 31, 14` (EL GADO `31, 21, 56, 25`), 6
`1, 22, 34, 26` (EL GADO `0, 11, 40, 37`); `+11` is 01 or 03 for boxes 1 and 2 and for kind 4 generally, `$81` box 3 and `$83` boxes 4 and 6
of kind 5 [R].

Scores (`$288c` ids, BCD table `$1b26`): G.ORIBER `$17` 2000, BILL BULL `$18` 2500, WONG WHO `$06` 3000, HOLLY WOOD `$06` 3000, EL GADO
`$1d` 4000; the award is enqueued once, when `+2` becomes 6, and the player-1 score rose by exactly that amount in 1 of 1 kill each
[L]. `+105` negative (killed by a prop or hazard) gives no score, positive goes to player 2.

Stage-script entries (`$5f7e`, the live set; `script.py`, `script_ents.py`; stage = `190(A5)`, area = `191(A5)`, cam = trigger x,
`2P` = two-player-only, level `$ff` = rank). Kind 5, 20 entries: stage 0 area 0 cam `$3f0` entry `$706a4` HOLLY WOOD (x 976, y 52, delay 60;
the one spawned in `ff_enemies` [S]); s0 a2 cam `$aa0` `$7073e` HOLLY WOOD (level 7); s1 a0 cam `$340` `$7080c`; s1 a1 cam `$980`
`$708a0`, cam `$ce0` `$708e0` HOLLY WOOD and `$70900` EL GADO; s1 a2 cam `$1000` `$709b4`; s2 a0 cam `$4e0` `$70ac2` EL GADO, `$70af2`
HOLLY WOOD (2P); s3 a0 cam `$b40` `$70f12` HOLLY WOOD, `$70f22` EL GADO, then both again with 2P (`$70f32`, `$70f42`); s5 a0 cam `$600`
`$71492` EL GADO (2P); s5 a1 cam `$24f0` `$716f6` HOLLY WOOD and `$71706` EL GADO with `+21 = 2` (drop in, 2P) and `$71736`, `$71746`
normal; s5 a2 cam `$2d80` `$7183a`, `$7184a`. Kind 4, 14 entries: s0 a1 cam `$6e0` `$706e8` G.ORIBER (`+21 = 6`, level 4) and
`$706f8` BILL BULL (delay 180); s0 a2 cam `$aa0` `$70790` G.ORIBER (level 7); s1 a1 cam `$ce0` `$70910`; s4 a0 cam `$760` `$70fdc`
G.ORIBER, `$70fec` BILL BULL, `$70ffc` WONG WHO, `$7100c` G.ORIBER, all `+21 = 6`, level 0; s5 a0 cam `$600` `$71472` G.ORIBER
(`+21 = 6`, delay 300) and `$71482` BILL BULL; s5 a1 cam `$1f80` `$715e6` WONG WHO and `$71656` BILL BULL (`+21 = 6`); s5 a2 cam
`$2d80` `$7187a`, `$7188a`. These scripts use `+21` 0 or 6 for kind 4 and 0 or 2 for kind 5 only. The kind-4 entries are [R]: no saved
state reaches them.

### Difficulty and spawn caps

`$3e88` (D0 = kind) runs before every tag-2 script spawn: kinds 0 to 2 share the counter `-28332(A5)` capped by `byte[$3eda + rank]`
(2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6 x5, 7 x5, 8 x3, 9 x3 for rank 0 to 31); kinds 3 to 6 have a counter each at `-28331 +
(kind - 3)(A5)` capped by `byte[$3efa + 32*(kind-3) + rank]`. The caps for kind 4 and 5 are 1 for rank 0 to 3, 2 for 4 to 10, 3 for
11 to 18, 4 from 19. The despawn handlers decrement the same counter (kind 4 `-28330`, kind 5 `-28329`). `rank` is the word `168(A5)`
(`frame.md`, "Difficulty counter"): in `ff_enemies` it was 8 at frame 4151, 10 after 1501 frames and 13 after 3001 [L]. `$3e88` accepted
a spawn one below the cap and refused one at the cap for kinds 4 and 5 at ranks 0, 4, 11 and 19 (caps 1, 2, 3, 4), 16 of 16 callcap
runs (`gate_caps.sh`) [L]. A script level byte `$ff`
becomes `169(A5)` (the rank) in `+96`; the level then selects health, class, damage column and the attack-roll masks below. Nothing else
in these two handlers reads the rank.

### Helpers used (roles read from the bodies)

| address | role |
|---|---|
| `$2fa2` | load health (`+24 = +26 = +28`) and `+55` from the record at `+92` by `+96`; `+92 += level + $60` |
| `$3068` | nearest live player by x distance (A0, D3 = 0 or 1); a tie goes to player 2; only player 1 live gives player 1 |
| `$3180` | step by the table at `+50`, direction index `+54` (32 directions; 0 = +y, 8 = +x, 16 = -y, 24 = -x; 1/256 px per frame) |
| `$30d4` / `$315c` | integrate `+80` (vx), `+84` (vy), `+86` (gravity) / decelerate `+80` by `+82` |
| `$31f4` | direction from the fighter to a point, D6 0 to 255 (`(D6 + 4) >> 3 & $1f` is the index) |
| `$3b10`, `$3b1c`, `$3b3c`, `$3b76` | start, start at a pointer, advance, reverse an animation list: entries `{offset.w, duration.b (+40), flag.b (+41)}`, frame record gives `+42..+45` and `+48`; a duration with bit 7 is a loop marker |
| `$3bb0` | off-screen cull: `+2 = 6` when x is outside `[cam - 128, cam + 512]` or y outside `[camy - 128, camy + 384]`; called when `(167(A5) + D7) & 15 == 0` |
| `$32aa` / `$32be` | refresh boxes, queue hit candidates and draw / draw only (a held fighter) |
| `$412a`, `$4234`, `$41ba`, `$4166` | grab link: `+64` set makes `+66 = 2` next frame; pick the follow-offset table by the holder's `+20`; follow the holder (0 follow, +1 released, -1 thrown); link still valid |
| `$7d6c`, `$7fac` | after a move: tile and prop collision (`+88` block class, 3 = prop, `+102` the prop); is a point free |
| `$3f7a` | throw landing damage (`frame.md` damage section) |
| `$288c`, `$28b4` | enqueue a score id; push the HUD enemy-bar entry |
| `$aaa`, `$ab2`, `$b6a`, `$b72`, `$b8a` | sound cues `$0d`, `$0e`, `$26`, `$29`, `$2c` |
| `$44d0`, `$6c7a`, `$6c96` | dust effect at the feet; body-versus-objects contact test of a flying or charging body |

`$3c26` is the shared LFSR. Randomness in these handlers: retarget offset, walk pause, idle length, attack roll, script pick, wind-up and
recovery lengths, sidestep direction.

### Kind 5 (`$3514c`): HOLLY WOOD and EL GADO

States (`+2`, `+3`, `+4`); the evidence column is live frames over 13,000 frames of 24 spawned fighters and the baseline run.

| state | entry | meaning | evidence |
|---|---|---|---|
| `+2 = 0` | `$35160` | init (ground line `+14 = +10`, flags clear, `$36dea`, `$2fa2`); `+21 != 0`: `+136 = player 1`, `+3 = $e`, `y += $120` | [L] 1 frame per spawn |
| `+2 = 2` | `$351ae` | main, `+3` through `$351de` | [L] |
| `+2 = 4` | `$36374` | death; `+3 = 0` flight (4 = 0 launch, 2 first arc, 4 second arc, 6 slide), `+3 = 2` fade in place (`$364de`) | [L] 3 = 0, 110 frames; 3 = 2 [R] |
| `+2 = 6` | `$36538` | decrement `-28329(A5)`, free (`$3878`) | [L] 2 frames, record freed |
| `+3 = 0` | `$351ee` | stand-off walk, `+4`: 0 init, 2 approach, 4 idle, 6 hold at the point, 8 smash a blocking prop | [L] 48, 1769, 1913, 808, 25 frames |
| `+3 = 2` | `$3549a` | attack; `+4` is the op, table below | [L] |
| `+3 = 4` | `$359e4` | back off or flank: 4 = 0 pick a direction, 2 walk 9 to 18 frames in reverse animation, 4 walk to a flank point | [L] 73, 31, 169 |
| `+3 = 6` | `$35ba8` | hit reaction by `+156` | [L] 617 frames |
| `+3 = 8` | `$360c8` | after a grab release: fall if airborne, wait 30 frames, walk | [L] 128 |
| `+3 = $a` | `$36126` | thrown by the player: two bounces, `$3f7a` damage, slide, get up | [L] 174 |
| `+3 = $c` | `$362ca` | wait while the target's `90(A0) != 0`, then retarget and walk | [R] |
| `+3 = $e` | `$362f4` | drop in: vy `-$200`, gravity `-$38`, ground marker (pool 8 kind `$34`, `$20f4e`, copies the owner's x and ground line) | [L] 64 frames; marker y stayed on the ground line 43 of 43 frames |
| `+66 = 2` | `$36ca4` | held by the player (`+3` 0 then 2 follows `$41ba`) | [L] 316 frames |

Attack ops (`+3 = 2`; `+74` is the armed flag, `+76` the weapon record):

| `+4` | entry | action | animation, attack box | live frames |
|---|---|---|---|---|
| 0 | `$354cc` | draw: allocate a pool-6 kind-0 item (`$38ce`), link it (`+74 = 1`), 10 frames, back to walk | `$36e74`, none | 459 |
| 2 | `$35534` | unarmed jab | `$36e34`, box 1 (132 frames with the box, `+74 = 0`) | 507 |
| 4 | `$35552` | unarmed second attack | `$36e44`, box 2 (12) | 25 |
| 6 | `$35570` | dash kick: wait 1, 15, 30, 45 or 60 frames, dash 30 frames (`+142 = +-$700`), breaks a prop it hits | `$36e94`, `$36ea4`, box 5 (233) | 902 |
| 8 | `$35660` | armed swing A | `$36e54`, box 3 (348, `+74 = 1`) | 874 |
| `$a` | `$3567e` | armed swing B | `$36e64`, box 4 (12) | 50 |
| `$c` | `$3569c` | throw the weapon (needs `+74` and an on-screen x): wind-up 30 frames, sound `$0e`, disarm; the item flies on at 7 px per frame | `$36e74`, none | 430 |
| `$e` | `$35732` | jump attack: wait, `+142 = (target.x - x) * 8`, vy `$880`, gravity `-$58`, land | `$36eb4`, box 6 (197, armed) | 1042 |
| `$10` | `$358d4` | recovery of 10 to 70 frames, then the next script byte if the target is lane-aligned and the stand point reached | | 2731 |
| `$12`, `$14` | `$35946`, `$359b8` | walk to a point 64 or 104 px from the target, then the next op | | 20, 30 |

The other animation setters (two characters each, list at `table + word[table + 2*(+20)]`): `$36e24` walk (36 ticks), `$36ec4` drop-in
jump (box 6 present), `$36ed4` landing and recovery, `$36ef4` and `$36f04` flinch, `$36f14` knockdown launch, `$36f34` landing,
`$36f44` grabbed (index `+67`), `$36f78` thrown flight. `$36e84`, `$36ee4`, `$36f24` are not referenced.

```c
/* kind 5, A6 = record, F = 167(A5), D7 = pool loop index */
case 0: init();
case 2:
  if (+66 != 0) held(); else {            /* $412a sets +66 = 2 when +64 != 0 */
    walk(+3 == 0) / attack(2) / sidestep(4) / hitReact(6) / land(8) / thrown($a) / waitTarget($c) / dropIn($e);
    hitCheck();                           /* $36c20, skipped while 299(A5) */
    if (((F + D7) & 15) == 0) cull();
    boxesAndSprite();                     /* $32aa */
  }
hitCheck():
  if (+24 < 0) { if (!+157) { +99 = (+63 == 8); +2 = 4; +3 = +4 = +5 = 0; sound($2c); } }
  else if (+24 != +26) { +26 = +24; if (y != ground && +63 != 8) +63 = 3; +3 = 6; +4 = +5 = 0; }
  /* both: an armed fighter drops the weapon */
walk():                                   /* +3 == 0 */
  case 2: if (--+30 == 0) { if (--+31 == 0) { +31 = 10; retarget(); }
                            +30 = 12; if (rand16() < 4) { +30 = {30,90,60,120}[rand&15]; +4 = 4; return; } }
          turn one step toward (+128,+132) on odd frames; step(+54, table $d28b4);   /* 3.0 px/frame in x, 1.5 in y */
          if (blocked) { if (+88 == 3 && (+164 += {1,2,3,4}[..]) >= 180) { +3 = 0; +4 = 8; } }
          if (target.+90) +3 = $c;  if (|dx| <= 4 && |dy| <= 3) { +4 = 6; +159 = 0; }
  case 4: if (--+30 == 0) { +4 = 2; +30 = 12; +31 = 10; retarget(); }
  if (((F + D7) & 3) == 0) refreshPoint();  attackDecision();  /* every frame */
retarget():                               /* $353d2 */
  release side slot; (+136, +161) = nearest player; +154 = {$90,$40,$40,$40,$40,$90,$90,$40,..}[rand&15];
  +46 = (target.x <= x); point = (target.x + (+46 ? +154 : -154), target.ground); occupy side slot;
attackDecision():                         /* $3656e, $36aa6, $36aec, $3665a */
  for p in {P1, P2}: if (live && +137 == 0 && |px-x| <= 64 && |py-y| <= 9) { +136 = p; choose(); return; }
  if (|target.ground - y| > ~3) { +159 = 0; return; }       /* (ground - y + 4) must be 0..7 */
  if (+159 && --+158 != 0) return;
  if ((mask[sub][level] >> (rand & 15)) & 1) choose(); else { +159 = 1; +158 = 30; }
choose():
  id = +74 ? tabA[sub][bucket][rand&31] : tabU[sub][rand&31];   /* bucket = (max(|dx| - 33, 0) & $e0) / 32 */
  +4 = script[id][0]; +150 = &script[id][1]; +3 = 2; +5 = 0;
  /* a first byte >= $12 is replaced by the next byte when a player is already in the 64 px zone */
/* script ids: 1 [0]  2 [$12 2 2 4]  3 [$12 2 2 6]  4 [$14 6]  5 [$14 8 $a]  6 [$14 8 8 $a]  7 [$14 8 8 8 8 $a]
               8 [$c]  9 [$c $c]  10 [$c $c $c]  11 [$e]   ($ff ends; an op $c reached from $10 first draws a fresh item) */
```

Decision facts. Target is the nearest live player (`$3068`); a player with `+137 != 0` (set for a player in state 3 = 8, in the late
hit phase, in state 3 = 2 or dead, `$8cf8-$8d62`) is ignored. A player inside 64 px in x and 9 in y in state `+3 = 0` was followed by
`+3 = 2` on the next frame in 20 of 22 cases (the other 2 were a hit reaction) [L]. The roll mask is word `[A0 + 2*level]` with `A0 =
$365d6 + word[$365d6 + 2*(+20)]`; its success chance (popcount over 16) rises from 2/16 at level 0 to 15/16 (HOLLY WOOD) or 16/16 (EL GADO)
at level 31; after a miss `+158` counted 30 down to 17 over 14 frames and was cleared to 0 when the fighter left lane alignment [L].
Unarmed picks: HOLLY WOOD ids 1 x10, 2 x8, 3 x8, 4 x6 of 32; EL GADO 16, 4, 7, 5. Armed picks favour 5 to 7 at distance bucket 0 to 3
and only 8 to 11 from bucket 4 up (`$36678`, `$3673a`, [R]). The stand-off distance is 64 or 144 px; because arrival is accepted within
4 px and the zone is 64, a fighter that parks at 68 px attacks only through the lane-aligned roll, and one pinned off the player's lane
by scenery never attacked in 3000 frames (`k5n0`) [L]. Observed standing distances 68 and 128 px [L]. Idle spans were 30, 60 or 90 frames
in 22 of 22 (the table also holds 120), walk spans were multiples of 12 in 22 of 23, walking speed 3.00 and 3.07 px/frame in x for 35 and
61 frames (table 3.0) [L].

Blocking: with `+88 = 3` the counter `+164` gains 1 to 4 per frame; at 180 the fighter plays the smash attack (3 = 0, 4 = 8, box 2 or 4); when
the box becomes active the prop record gets `+24 = $ffff`, `+105 = $ff` and both sides `+23 = 6` (hit-stop). In one run `+164` was `$b6`,
the prop at `$ffba68` went from state 2 to 4 with health `$ffff` in the same frame [L, 1 of 1]. A fighter in hit-stop skips its handler:
spans of 25 frames for 30 of 30 armed swings that connected (18 + 6 + 1) [L].

Hit reaction (`+3 = 6`, `+156 = +63` from the attack box `+11`, set on the frame `+24 != +26`): 0 and 2 flinch `$36ef4`, 1 flinch
`$36f04`, 3 and 7 knockdown with two bounces then slide and get up (6 sub-states), 4 none, 5 and 6 a knockdown that kills if `+24 < 0` after
the landing, 8 as 3 with `+99 = 1`. Seen live: types 0 (218 frames), 1 (120), 3 (262); 2 and 4 to 8 [R]. Thrown by Cody (Button 1 with a
direction held after the grab; Button 2 only releases, 3 = 8): HOLLY WOOD health 60 to 30 in 2 of 2 throws, matching the halving
branch of `$3f7a` [L]. The thrown item: `+64 = $ff`, `+66 = 2` while carried (y = fighter y + `$40`), then released with state 4 and flying
x -7 px per frame at constant y until `+2 = 6` [L]; its hit damage was not observed (Cody was off its line). The item is a blade-shaped
pool-6 kind-0 object by sight (`+19 = 0`, handler `$57a76`, unread) **[I]**.

### Kind 4 (`$3136c`): G.ORIBER, BILL BULL, WONG WHO

| state | entry | meaning | evidence |
|---|---|---|---|
| `+2 = 0` | `$31380` | init (`+21 = 8`: y - 1; `$3305c` sets `+56`, `+92`; `$2fa2`) | [L] |
| `+2 = 2` | `$313b0` | main, `+3` through `$313e0`, hit check `$329e4` (as kind 5), cull every 16th frame | [L] |
| `+2 = 4` | `$327fa` | death: `+3 = 0` flight, `+3 = 2` fade (`$32990`, 40 frames); score id `byte[$32854 + +20]` once at `+2 = 6` (both players if `+163`) | [L] 3 = 0, 159 frames; 3 = 2 [R] |
| `+2 = 6` | `$329d8` | release side slot (`$32fbe`), decrement `-28330(A5)`, free | [L] 3 frames |
| `+3 = 0` | `$313ee` | entrance by `+21`: 0 walk; 2 and 4 wait until a player is within 128 px in x and 32 in y or `+30` (60 to 300 frames) expires (4 then plays a 30-frame wake); 6 start charging (script `[8]`, `3 = 4, 4 = 4`); 8 drop in from above, `$1b428` on landing | [L] all four modes spawned, 130 frames |
| `+3 = 2` | `$31676` | walk (4 = 0 init, 4 = 2 loop `$317e0`) | [L] 5836 frames |
| `+3 = 4` | `$31838` | attack script | [L] 8139 frames |
| `+3 = 6` | `$31e9e` | hit reaction, the kind-5 table: 0, 2 `$31eee`, 1 `$31f42`, 3 and 7 `$31fd8`, 4 `$323e6`, 5 `$3212c`, 6 `$32298`, 8 `$323c0` | [L] 1169 frames, types 0, 1, 3 |
| `+3 = 8` | `$323f8` | stunned wait of 5 to 40 frames after a ground release, then resume the attack (`+154`) or walk | [L] 57 |
| `+3 = $a` | `$3248a` | fall and lie 57 frames after a release in the air | [R] |
| `+3 = $c` | `$32508` | thrown by the player (kind 5's `$a`) | [L] 258 |
| `+66 = 2` | `$326ae` | held | [L] 242 |

```c
/* kind 4, 3 == 2 walk */
if (((F + D7) & 7) == 0) { faceTarget(); if (299(A5)) die(); }
zoneCheck():                                   /* $32a88 */
  near: player live, +137 == 0, |dx| <= 64, |dy| <= 9  -> +157 = 1; +128 = p; 3 = 4;          /* 6 of 6 [L] */
  mid:  |dx| <= 80, |dy| <= 9                           -> +157 = 0; +128 = p; 3 = 4;          /* 8 of 8 [L] */
  else if (|dx| < 160 && target.+137 == 0) { if (!+145) +145 = 30; else if (--+145 == 0) { +145 = 30; if (rollMask[sub][level] bit rand&15) 3 = 4; } }
if (+142) --+142;                                                       /* pause 30, 60, 90 or 120 frames */
else if (!atStandPoint(|dx| <= 9, |dy| <= 9)) {
  if (--+143 == 0) { +143 = 40; if ($2444 >> (rand & 15) & 1) +142 = {30,60,120,60,90,60,30,90,120,90,90,30,60,120,90,60}[rand&15]; +144 = 1; }
  else { animate by (54 >> 4) ^ +46; steer one step per 2 frames; step(+54, table $d23b4); /* 2.0 px/frame */ if (+88 == 3 && (+164 += 1..4) >= 180) { +164 = 0; +146 = $3192f; 3 = 4; 4 = 4; +154 = 1; } }
}
/* 4 = 2: every 8 frames compare nearest player with +136; on a change release/retake the slot and lock for 180 frames;
   every 20 frames re-pick the stand point: side by position, +138 = $40 or $90 (mask $4a92), slot counters at -28304(A5) */
/* 3 == 4 */
case 0: id = byte[$318a4 + 32*(+20) + (rand & 31)]; +150 = id; +146 = &seq[id]; +154 = 1;
case 2: if (!+157 && id <= 6) approach to (target.x +- $3c) else skip;
case 4: if (id != 7 && target.+137) abort; op = *+146++; if (op < 0) 4 = 8 else 4 = 6;
case 6: run op; between ops the target must still be within 9 px of the stand point (else 3 = 2, +154 = 0);
case 8: wait {10..70} frames; 3 = 2.
/* sequences by id: 0 [2]  1 [0 0 2]  2 [0 0 6]  3 [6]  4 [4 4 6]  5 [4 4 8]  6 [8]  7 [8 8]  8 [$a] (blocked path only) */
```

Roll masks (`$32b22 + word[$32b22 + 2*sub]`): chance 2/16 at level 0 rising to 12/16 for G.ORIBER, 6/16 to 15/16 for BILL BULL and WONG
WHO. Script picks per 32 rolls: G.ORIBER 5 x5, 6 x10, 7 x9, others 1 to 2; BILL BULL 0 x5, 1 x6, 2 x6, 3 x4, 4 x4, 5 x3, 6 x2, 7 x2; WONG WHO
3 x5, 4 x5, 5 x6, 6 x7, 7 x6 [R]. Walking was 2 px per frame in 271 frames and 0 in 149 (standing); the pause counter `+142` counted down
from 120 [L].

| op | entry | action | animation, attack box (hit type `+11`) | live frames with the box (G.O. / B.B. / W.W.) |
|---|---|---|---|---|
| 0 | `$31ac0` | jab | `$330d0`, 40 ticks, box 1 | 25 / 295 / 0 |
| 2 | `$31aee` | attack | `$330e2`, box 5 | 0 / 140 / 25 |
| 4 | `$31b1c` | attack | `$330f4`, 45 ticks, box 3 | 168 / 0 / 126 |
| 6 | `$31b4a` | attack | `$33106`, 45 ticks, box 4 | 42 / 21 / 105 |
| 8 | `$31b78` | charge: direction along x or a diagonal, speed class 0, 1, 2 from `$31c4c` (tables `$d2634`, `$d2db4`, `$d3534`: 2.5, 4.0, 5.5 px/frame), stops within 12 px of the target or after 192 frames (`+160`), 30-frame settle | `$33118`, 55 ticks, box 2 | 1004 / 275 / 340 |
| `$a` | `$31a50` | smash the blocking prop at the end of the animation | `$330d0`, box 1 | [R] |

Other setters: `$33088` walk or stand (28 ticks), `$3309a`, `$330ac`, `$330be` entrance poses, `$3312a`, `$3313c` flinch, `$3314e`
knockdown launch, `$33170` landing, `$33182`, `$33194`, `$331a6`, `$331b8` lying, dying and getting up, `$331ca` grabbed (`+67`). The charge
also kills a prop it is stuck against (`$31d36`) [R]. The thrown G.ORIBER lost half its health (50 to 25) in 2 of 2 throws [L].

### Live gates, kinds 4 and 5

`py/ai_kind45/gates.sh` runs them. Damage equals the table byte: 151 of 151 (above). Zones: kind 4 near 6 of 6, mid 8 of 8; kind 5 20 of
22. Attack box per state (`boxmap.py`, kind 5): jab box 1 132 frames, op 4 box 2 12, dash box 5 233, swing A box 3 348, swing B box 4 12,
jump box 6 197, with `+74` 0 for the first three and 1 for the last three; kind 4 ops to boxes as the table. HUD names: the name tiles in gfx RAM equalled the expected text for all five fighters (`gate_names.py`, scroll-1 map, characters 128 bytes apart),
and a wrong name was not found. Off-screen cull: a spawn at x
1608 became `+2 = 6` two frames later and was freed, one at x 1500 stayed [L, 1 of 1 each]. Cody's Button-1 taps killed a kind-4 fighter in 5 hits and
kind-5 fighters too: health below 0, `+2 = 4`, then 6, record freed [L].

### Not proven

Kind 5 `+3 = $c` and the fade death (`+2 = 4, +3 = 2`, both kinds): need an untargetable target (`90(A0) != 0`) or `299(A5) = 1` (poke
`$ff812b`). Knock types 2 and 4 to 8 for these fighters, kind 4 `+3 = $a`, op `$a` and the charge smash: need a release in the air and a
prop in the charge line. Damage and target of the thrown pool-6 item (handler `$57a76`, `$7bba`, `$759c` paths unread). What `90` and
`137` of a player mean beyond the writers listed, `$6c7a`, `$1b428`. The kind-4 stage entries run only as spawn recipes, never from the
script.

## Kind 6 (ROXY, POISON)

Kind 6 (`$389b8`, code `$389b8-$3af24`; animation, box and character data `$3af78-$3c446`) is two characters: `+20 = 0` ROXY and `+20 = 1`
POISON. The names are the HUD's own text: ROXY in 8 of 8 name crops, POISON in 6 of 6 (`py/ai_kind6/` run `K6_SHOTS`; sheet kept in
`scratchpad/finalfight/p3/d/names_sheet.png`) [L]. `$3adee` selects, by `+20`, the animation/box data (`56(A6)`: ROXY `$3c036`, POISON `$3c15e`) and
the character data (`92(A6)`: ROXY `$3c286`, POISON `$3c366`) [R]. They share every state routine, animation table and attack box; they differ in
health, damage rows, palette (`+47`: 0 and `$b`, 1284 of 1284 and 1281 of 1281 samples), the attack-choice table `$3abee` and the score. The
handler has no block, no weapon use, no run and no retreat: it flanks the player, attacks in op chains, vaults over the player, and dodges by
probability. The linear listing `fighters.asm` is misaligned over `$389b8` (its sweep entered at a data table); the recursive-descent lister
`py/ai_kind6/rd_trace.py` produces a clean listing.

### Spawn

A script entry is 16 bytes with `A3` at the delay word [R, checked live]: word 0 delay in frames, word 2 count flag (non-zero registers the record in
the kill list), words 4 and 6 x and y (negative values get a random jitter of -15..+16), byte 8 tag, 9 kind, 10 `+20`, 11 `+21`, 12 `+54`, 13 `+98`,
14 `+96` (`$ff` becomes `169(A5)`), 15 a two-player-only flag. Byte 15 non-zero: with only player 1 active a kind-6 entry never spawned (0 records in
100 frames); with player 2's `+0` set it spawned at frame 5 (1 of 1 each) [L]. The live game always reads table `$5f7e`: `$5b1e` tests the ROM word at
`$726e0` (value 2, non-zero), not a player count; `$5f5e` is an identical copy at `-$134e` [R].

| `190/191(A5)` | entry (`$5f7e` table) | character, `+21` | x, y | note |
|---|---|---|---|---|
| 0, 2 | `$707a0` | ROXY, 4 | 2696, 48 | second group of the first boss area; trigger camera x `$aa0` after a pause command (the pause at `$70780` is released only by DAMND's second retreat at hp <= 100, `boss.md`; killing him before that leaves this group unspawned, 1 of 1 [L]); delay 30 after a kind-4 entry; spawned at relative frame 36 after poking the script pointer to `$70782` and the camera to 2720 [L, 1 of 1] |
| 1, 0 | `$7084c`, `$7085c` | ROXY, POISON; 6 | 800 and 1248, 36 | two-player only |
| 1, 1 | `$70890` | ROXY, 0 | 2400, 33 | |
| 2, 2 | `$70c76`, `$70c96` | ROXY, POISON; 0 | 3392, 64 | POISON two-player only |
| 3, 0 | `$70ed2`, `$70ee2` | ROXY twice; 6 | 1184, 64 and 100 | the y=64 one is two-player only |
| 4, 0 | `$713b4`, `$713d4` | ROXY, POISON; 0 | 8832, 64 | POISON two-player only |
| 5, 1 | `$716b6`, `$716c6` | ROXY, POISON; 4 | 9424, 2104 and 2072 | |
| 5, 2 | `$718aa`, `$718ba`, `$71938`, `$71948` | POISON 0, ROXY 0, ROXY 4, POISON 6 | 11616/2064, 12064/2112, 12832/2104, 12832/2072 | |

The `190/191(A5)` to game-stage naming was not done. The parser (`py/ai_kind6/scripts.py`) also reports an entry at `$715e8`/`$7029a`
(count word 8480) that is a mis-parse of data, not a spawn [I]. A synthetic spawn that writes a script group at `$ffe000` and points the script record
at it goes through the real `$5aea`, `$5e36`, `$5ee6` and `$3892` (`K6_SPAWN` in `k6run.lua`); two runs from the same state give identical RAM.

Spawn limiter `$3e88`: kind 6 uses the counter `-28328(A5)` and the cap `byte[$3f5a + d]` with `d = 168(A5)`: 1 for d 0-3, 2 for 4-10, 3 for 11-18,
4 from 19. Four queued entries at d = 4 gave 2 simultaneous records [L]. A refused entry with count flag 0 is dropped, not queued. State 6
decrements the counter unless `+98` is set [R].

### Record fields

`+2` life state (0 init, 2 alive, 4 dying, 6 free), `+3` behaviour, `+4`/`+5` steps, `+23` hit-stop (a hit sets it to 6; it freezes the attack, hurt,
evade and death states), `+30` countdown, `+46` facing (0 faces right; `$3a94c` sets it from the player's x), `+47` palette, `+50` heading step table
`$d2b34`, `+54` heading 0..31 (8 is +x, 24 is -x) also used as the walk animation index, `+62`/`+63` attacker's facing and hit type, `+66` held-by-player
flag, `+80/82/84/86` vx, vx decay, vy, gravity, `+88` collision class from `$7d6c`, `+96` difficulty `d` (low byte of `168(A5)` at init), `+99` burn
variant, `+102` blocking prop (written by `$84dc`), `+105` killer's kind, `+128` target player pointer, `+132/134` target point, `+136/137` target
index and flank side, `+138` stand-off, `+140` flank slot claimed, `+141` retarget countdown, `+142` heading-snap flag, `+143` pause counter, `+144`
walk segment counter, `+146` dying flag, `+147` attack in progress, `+148` lane timer, `+149` attack id, `+150` op stream pointer, `+154` current op,
`+155` approach timeout, `+156` path pointer, `+160` thrown-landing damage done, `+161` melee-trigger flag, `+162` killed-by-clear flag, `+164` stuck
accumulator. `+31` is unused [R]. Heading steps come from `$d2b34` (16.8 fixed point): 3.5 px per frame in x and 1.75 in y; measured 3 or 4 px per
frame at headings 8 and 24 (442 and 446 of 890 moving frames) [L].

### Life state `2(A6)` and behaviour `3(A6)`

Frames are over two 9000-frame bot runs, one per character (`stat.py`): bot-driven immortal Cody, respawning kind 6, ROXY / POISON.

| `2` | entry | does | evidence |
|---|---|---|---|
| 0 | `$389cc` | init: `14:=10`, `46:=54`, `96:=168(A5)`, clears `161/140/146/162`, `47` by character, `$3adee`, then `$2fa2` (health `word[data+2d]`, defence class `byte[data+$40+d]`, damage base `data+$60+d`) | 18 spawns [L] |
| 2 | `$38a1e` | `$412a`; if `66≠0` the held branch `$3a07a`, else `jsr` through `$38a4e` by `3(A6)`; then `$3a3ae`, `$3bb0` every 16 frames, `$32aa` | below |
| 4 | `$3a1c6` | dying, table `$3a21c` | 944 frames in 15 deaths [L] |
| 6 | `$3a39c` | releases the flank slot, decrements `-28328(A5)`, frees the record (`$3878`) | 15 |

| `3` | entry | behaviour | frames ROXY / POISON |
|---|---|---|---|
| 0 | `$38a5e` | entrance by `+21` (below) | 11 / 7 |
| 2 | `$38dae` | walk and decide | 2274 / 2460 |
| 4 | `$38f70` | attack | 4232 / 3647 |
| 6 | `$3974e` | hurt | 1325 / 1955 |
| 8 | `$39ca8` | evade (backflip) | 402 / 416 |
| 10 | `$39dc2` | fall to the ground after release in the air | not observed [R] |
| 12 | `$39e3e` | get-up wait after release on the ground | 74 / 59 |
| 14 | `$39ed0` | thrown flight (player throw) | 81 / 0 (seen once) |

Transitions of `3` summed over both runs: 0 to 2 18, 2 to 4 133, 2 to 6 20, 2 to 12 8, 4 to 2 98, 4 to 6 27, 4 to 8 5, 6 to 2 32, 6 to 8 10, 8 to 2 17,
12 to 2 4 [L]. Every 16th frame (`(167(A5) + D7) & 15 == 0`, 99 of 99 `$3bb0` executions in 1600 frames) `$3bb0` sets `2(A6) = 6` for a record far
off-screen, which frees it with no score (seen once, ROXY at x 772 with the camera far right) [L].

Entrances (`+21`, table `$38a92` indexed by the byte value / 2):

| `+21` | entry | does |
|---|---|---|
| 0 | `$38a9e` | straight to behaviour 2 |
| 2 | `$38aa2` | dormant: wait `word[$38aca + (rnd & $3e)]` frames (60..300) or until a player is within +-`$80` in x and +-`$20` in y, then behaviour 2 |
| 4 | `$38b6e` | enters the attack behaviour at once with id 13 (op `$e`) |
| 6 | `$38ba6` | the same, facing flipped, id 14 (op `$10`) |
| 8 | `$38be4` | drops in from `$120` above (47 frames), spawns a pool-8 kind `$34` object linked to the record (role unknown), lands, waits 20 frames |
| 10 | `$38c82` | rises from below, then jumps |

The scripts use 0, 4 and 6. Forced spawns of 2, 6 and 8 behaved as above (1 each); 10 was only watched [L]. Init (`$389fa`) also tests
`cmpi.b #$a,20(A6)`, which is dead for characters 0 and 1 [R].

### Decision logic

```
walk()                                         // behaviour 2, $38dae
  if (4(A6) == 0) { 141=$b4; 30=$14; 144=$18; 143=0; 142=1; 148=0; 161=0;
                    pick target = nearer active player by |dx| ($3068 -> 128, 136); flank point ($3a7fa) }
  else            { every 8 frames ($141 countdown): retarget if the other player is nearer ($3068);
                    every 20 frames: release and recompute the flank point }
  if (((167(A5)+D7) & 7) == 0) { face_player(); if (299(A5)) die_by_clear() }
  decide()                                     // $3a4a4, below
  if (143) { 143--; return }                   // pause
  if (arrived(132,134, +-9)) { 142 = 1; return }
  if (--144 == 0) { 144 = 24; if ((1 << (rnd&15)) & $2444) 143 = $38e44[rnd&15] /* 30,60,90,120 */; 142 = 1; return }
  animate_by_heading($3a936); steer_and_step($3a6d2)   // odd frames: heading 54(A6) one step (+-1 of 32) toward the angle to (132,134)
                                               // ($31f4, (angle+4)>>3), or snapped if 142; near the player (+-$28, +-$10) it turns away;
                                               // every frame $3180 adds the heading step; 14 := 10; $7d6c
  if (stuck())  start_attack(id 18, stream $39070 /* op $12 */)   // $38e54: 88(A6)==3 -> 164 += $38e84[rnd&15]; >= 180
  if (((167+D7)&3) == 0 && offscreen_x()) 142 = 1

decide()                                       // $3a4a4
  A: a standing player (90(A0)==0, 137(A0)==0) within |dx|<=$40 and |dy|<=9      -> 161 = 1; engage
  B: a standing player within |dx|<$50 and |dy|<=9                               -> engage
  C: else if the target's ground line is within 9 of y:
        if (148 == 0) 148 = 30; else if (--148 == 0) {
            if (bit (rnd & 15) of word[$3a53e + 2*d] is set && target standing) engage; else 148 = 30 }
     target out of lane: 148 = 0
  engage: 128 = target; release flank slot; 3 = 4; 4 = 5 = 0                    // behaviour 4

attack()                                       // behaviour 4, $38f70; frozen while 23 != 0
  4=0 pick:  band = dx < $40 ? 0 : dx >= $100 ? 7 : 1 + (dx-$40)/$20;           // dx = |player.x - x|
             147 = 1; 149 = id = $3abee[20*256 + 32*band + (rnd & $1f)]; 150 = $3901c + word[$3901c + 2*id]
  4=2 approach (skipped when 161 or id >= 11): stand-off point 132 = player.x +- ($40 if id < 6 else $68) on the near side;
             abort if not walkable ($7fac); walk there (timeout 240 frames); 5=0 at $390a0, 5=2 loops at $390f2
  4=4 fetch: if (id != 13 && target.137 != 0) abort; op = *150++; if op == $ff goto 4=8
  4=6 run op (5(A6) steps); between ops wait $39686[rnd&$1f] (6..14) frames, re-check the stand-off point or abort
  4=8 pause: wait $3970c[rnd&$1f] (10..70) frames, then 3 = 2, 147 = 0     // abort path $39738 does the same at once

on a hit ($7456 -> $3a454): if (2 == 2 && 10 == 14 && 64 == 0 && ((long[$3aaee + 4*d] >> (rnd & $1f)) & 1)) { 3 = 8; 4 = 5 = 0; return no damage }
hurt/die   ($3a3ae, every frame in state 2): hp < 0 -> 2 = 4, sound $2b ($b82); hp != 26 -> 26 = hp; if airborne 63 = 3; 3 = 6; 4 = 5 = 0
```

The attack-start mask is `word[$3a53e + 2*d]`. `$3a516` first loads a per-character pointer into `A0` (`$3a53e + word[$3a53e + 2*char]`, i.e.
`$3a542` for ROXY and `$3a582` for POISON) and then reads the mask with a PC-relative `move.w 6(PC,D1.w)` that ignores it. Both characters therefore
use the same table; POISON's own table at `$3a582` is never read, and entries 0 and 1 of the real table (`$0004`, `$0044`) are the pointer
words. 31 of 31 live evaluations (17 POISON) equalled `word[$3a53e + 2d]`; POISON matched its own table in 0 of 17 [L]. The probability per 30
frames is popcount/16: 5/16 at d = 4, 8/16 at d = 13, 14/16 at d = 32.

Difficulty `d = 168(A5)` rises by 1 every `$536a[172(A5)]` frames (600 at 172 = 0) up to `$5372[172]` (23): 4 at frame 0, 6 at 1000, 9 at 3000, 14
at 6000, 19 at 9000 [L]. It feeds `+96` at spawn and thereby health (ROXY 60..92 by `word[data+2d]`, POISON 120..154; 68 and 130 at d = 4), the
damage rows, the dodge mask `long[$3aaee + 4d]`, the attack-start mask and the spawn cap. It does not change speed [R].

Randomness `$3c26` is used at `$38ab8`, `$38ca6`, `$38e1e`, `$38e2e`, `$38e5c`, `$38fec` (attack id), `$3966a`, `$396fa`, `$39e72`, `$3a482`
(dodge), `$3a516` (attack start), `$3a732` (turn tie-break), `$3a89c` (flank offset: `$90` with probability 6/16, else `$40`) and `$5ef6` (spawn
jitter) [R].

Flank point (`$3a7fa`): side `137` = 1 when `x >= player.x`; a side whose slot counter (`-28296(A5) + 2*136 + 137`) is non-zero is swapped for the
other; `132 = player.x +- (rnd-chosen $40 or $90)`, retried with the other offset and side if `$7fac` rejects the point, `134` = the player's ground
line (minus altitude). Offsets measured: 64 in 87 computations, 144 in 51 [L]. Stand-off during an attack: 64 in 105 frames (id < 6), 104 in 677 frames
(id >= 6) [L].

Checks on the decision (`decide2.py`, 9000-frame bot runs): the chosen id lay inside the 32-entry `$3abee` row of the dx band in 71 of 71 (ROXY)
and 57 of 57 (POISON) attack starts (one and four starts showed no id inside the 8-frame window). Trigger path A / B / C: 49 / 9 / 14 (ROXY) and 37 / 5 / 19
(POISON); lane-timer dwells cluster at 30, 60 and 90 frames, the other C-path dwells (0..47) are not explained by the timer alone. Pauses started
with 30, 90 or 120 (14 events). A fetch with the player's `137 = $ff` aborted at once in 8 of 9 forced tests, and proceeded in 7 of 7 with `137 = 0`
(the exception ran 3 frames) [L]. Dodge: 56 evaluations of `$3a454` past its preconditions (ROXY run) gave 9 dodges, and `(mask >> rnd) & 1` predicted 9 of 9
and 56 of 56 outcomes (breakpoints `$3a48a`, `$3a492`; masks seen for d = 4, 6, 8, 10, 14, 16, 18); the POISON run gave 59 evaluations, 8 dodges, 8 predicted [L]. A two-player probe: with player 2's record
activated nearer than player 1 the target pointer switched to `$ff8628` (1 of 1); player 2 is otherwise unexercised [L].

### Attacks

`$3901c` holds 16 op streams (word offsets, then bytes ending `$ff`); `149(A6)` is the id. The ops run through the table `$39198` (index = op / 2):

| op | entry | anim table | measured behaviour |
|---|---|---|---|
| 0 | `$3921e` | `$3b100` | two punches (screenshot: punch), attack box 1 in two windows, hit type 0 |
| 2 | `$3924c` | `$3b11c` | punch, box 2, type 3 (knockdown) |
| 4 | `$3927a` | `$3b288` | high kick (screenshot), box 3, type 1 |
| 6 | `$392a8` | `$3b29c` | high kick, box 4, type 3 |
| 8 | `$39372` | `$3b4ca` | heavy kick with a hop away (`vy $780`, `vx` +-`$180` away, gravity `$68`), box 6 for about 15 frames; x moves 54..61 away, y peak 110 |
| `$a` | `$392d6` | `$3b3b4` | flying kick toward the player (screenshot: horizontal dive), `vx $280` with decay 5, `vy $780`, box 5; x moves about 79 toward |
| `$c` | `$393e6` | `$3b69e` | leap (`vy $700`, gravity `$38`, `vx = (land - x) * 4`) that lands `$40` behind the player; box 5 on the way down |
| `$e` | `$3947c` | path `$3a992`, then `$3b69e` | hop-run along the path table (about 30 frames) toward the player, then the leap over him |
| `$10` | `$39570` | variant `$3aeee` | the same run, then a short hop to the stand-off point in front of him; facing flipped after it |
| `$12` | `$391ac` | `$3b288` | punches the prop at `102(A6)`: sets its `105 = $ff` and health to -1 (not triggered live) |

Op pose names come from one screenshot each (ops 0, 2, 4, 6, `$a`, `$c`, 8) and from the motion; ops `$e`, `$10`, `$12` from motion and code only.

| id | stream | live damage at d = 4, ROXY / POISON |
|---|---|---|
| 0 | 0, 0, 2 | 7, 7, 7 / 12, 12, 12 |
| 1 | 4, 4, 6 | 14, 14, 14 / 24, 24, 24 |
| 2 | 0, 0, 6 | 7, 7, 14 / 12, 12, 24 |
| 3 | 8 | 40 / 54 |
| 4 | 0, 0, 8 | 7, 7, 40 / 12, 12, 54 |
| 5 | 4, 4, 8 | 14, 14, 40 / 24, 24, 54 |
| 6 | `$a` | 22 / 34 |
| 7 | `$c`, `$a` | 22 / 34 |
| 8 | `$c`, 8 | 40 / 54 |
| 9 | `$c`, 4, 4, 6 | 14, 14, 14 / 24, 24, 24 |
| 10 | `$c`, 4, 4, 8 | 14, 14, 40 / 24, 24, 54 |
| 11 | `$e`, 8 | 40 / 54 |
| 12 | `$e`, 4, 4, 8 | 14, 14, 40 / 24, 24, 54 |
| 13 | `$e` | no hit when forced; the entrance for `+21 = 4` |
| 14 | `$10` | no hit when forced; the entrance for `+21 = 6` |
| 15 | `$12` | `$3b288` anim and prop break; the code starts it as id `$12` from the stuck detector |

Forced from an idle Cody at distance 48 with the approach step on (`runids.sh`); a repeated hit inside a chain is often absorbed by Cody's hit-stun, so
the listed damage is per box window that connected. Ids 6 to 14 hit only when Cody stands where the flying or landing box reaches him.

Attack boxes (`56(A6) + word(56(A6)) + 16*idx`; the geometry is identical for both characters; damage = `byte[data + $60 + damage idx + d]`):

| idx | dx, dy, hw, hh | damage idx | hit type | ROXY d = 0, 4, 16, 31 | POISON d = 0, 4, 16, 31 |
|---|---|---|---|---|---|
| 1 | 32, 64, 32, 16 | 0 | 0 | 5, 7, 10, 15 | 10, 12, 15, 20 |
| 2 | same | 0 | 3 | same | same |
| 3 | 24, 60, 38, 16 | `$20` | 1 | 10, 14, 18, 23 | 20, 24, 28, 33 |
| 4 | same | `$20` | 3 | same | same |
| 5 | 41, 38, 23, 21 | `$40` | 3 | 18, 22, 26, 31 | 30, 34, 38, 43 |
| 6 | 28, 69, 37, 18 | `$60` (sound `$11`) | 3 | 36, 40, 44, 52 | 50, 54, 58, 63 |

All 85 of 85 drops of Cody's health word in the forced runs equalled the table value for the attacker's box and `+96` (`gate_dmg.py`) [L].
Attack choice by `$3abee` (32 entries per dx band): ROXY favours 0-2 (jab and kick chains), 6, 7 and 9 (flying kick and leap chains); POISON favours
3, 4, 5, 8 and 10 (kick-ending chains); beyond dx `$80` both mostly pick 11 and 12 (the run-and-vault chains, with 9 or 10 for the nearer bands) [R].

### Reactions, death, score

Hit type `63(A6)` (from the attacker's box byte 11), handled by `$3974e` through `$3978c`; measured with a poke of `63` and `3 = 6` (1 run each) plus
natural samples:

| type | handler | observed |
|---|---|---|
| 0, 2 | `$3979e` | stagger, 29 frames, no motion |
| 1 | `$397f2` | the same with the second anim |
| 3, 7 | `$39888` | knockdown: launch `vx +-$200`, `vy $380`, gravity `$48`, wall stop, bounce, slide; 81 frames; moves 105 px |
| 4 | `$39c96` | none (back to walk after 2 frames) |
| 5 | `$399dc` | launch `vx +-$280`, 119 px, anim unchanged |
| 6 | `$39b48` | launch in the opposite direction `vx -+$200` |
| 8 | `$39c70`, then the type 3 path | `99 = 1`, anim `$400c`, 81 frames |

From Cody only types 0 and 3 occurred (40 and 9 hurt entries in the two bot runs). After a stagger or knockdown the interrupted op chain resumes
through `$396ac` only if the stand-off point is still reached, otherwise `$39738` clears it. The evade (`3 = 8`) walks a path (`$3a9b0`), hops back
(`vy $780`, `vx` -`$200` by facing) and lands: 93 frames in the sample [L].

Held by the player (`66 = 2`): `$3a09c` and `$3a0ac` follow the holder's offset table (`$4234`, `$41ba`); in `$3a0da` hit types 0-2 keep the hold, 3, 7
and 8 release her to behaviour 6, 5 and 6 release her. A negative result of `$41ba` releases her into the thrown flight (3 = 14), whose landing
calls `$3f7a`. The 22 holds in the two runs ended in hurt 9, get-up 9, thrown 1, and 6 deaths while held [L].

Death (`hp < 0`, `$3a3ae`): `2 = 4`, behaviour 0 for the flight (launch `vx +-$400`, `vy $300`, gravity `$48`, bounce, slide, 4 steps of `4(A6)`) or
behaviour 2 (stand and flash, 40 frames) when `299(A5)` or a loop end triggers it. About 75 frames, then state 6. Entering state 6 `$3a1d2`
queues score row `$17` (ROXY) or `$06` (POISON) through `$288c` into the ring `516(A5)`, consumed by `$4b00`/`$1a22`, which adds the BCD row at
`$1b26`-based rows to the player's `+132` long: 2000 for ROXY, 3000 for POISON. With `162 = 1` (killed by the clear) both players are credited.
15 of 16 state-6 entries in the two bot runs had the exact award (`gate_score.py`); the 16th was the off-screen cull (state 2 straight to 6) [L]. `299(A5)` is set in the boss
handlers (`$3ecc6`, `$4264c`, `$47716`, `$4a29e`, `$4d450`, `$4f9fe`) and at `$c88e`; every fighter dies at its next 8- or 16-frame check, an
interpretation as "kill all regular enemies" is [I].

The victim hook: `$7456` stores `105`, `60`, `22`, `63`, calls `$7a38` (facing), then `$3a454`; a non-zero return ends the handler with no damage
and no hit effect, which is the evade above [R, 9 of 9 live].

### Not proven

- The kind 4 and kind 6 group `$70782` was played to in stage 0 (after DAMND's second release, `boss.md`); no gate of this section was re-run on those script-spawned records.
- Entrances 2, 8, 10 are not used by any script (the placement lists use 2, 8 and 10 for kind 6, `placement.md`); the pool-8 kind `$34` object that entrance 8 spawns is unnamed.
- Op `$12` (breaking a blocking prop) and behaviour 10 have no live trigger; the meaning of `88(A6) = 3` is [I] (the class that `$8474` returns for
  the right screen edge, and the stuck detector's trigger). Proof: place a pool-`$a` prop beside her, or force `3 = 10` in the air.
- Two players: only a retarget to player 2 and the byte-15 spawn gate were seen. Thrown-landing rows `$3fd8`: only the kill case.
- Scripts and states: `py/ai_kind6/README.md`.

## Kinds 7 and 8 (the fire-bottle thrower and the scroll-lock placeholder)

Kind 8 (`$3c48e`) is the red-suited, red-bandana fire-bottle thrower. It never fights in melee: it walks to a random screen column,
throws one lit bottle at the nearest player and leaves the screen. Kind 7 (`$3c446`) is an invisible placeholder record that frees itself
after 10 to 255 frames. Neither is live in a saved state; every [L] below comes from tag-2 records spawned into `ff_enemies` by
`py/ai_kind78/spawn.lua` (the real free-stack pop of `$3892`, fields written as `$5ee6` writes them), with the other enemies cleared. Those
runs are deterministic: one spawn run gives a byte-identical 854,575-byte log in 3 MAME processes, and the promoted `determinism.sh` gives the
same md5 in 2 more; `ff_k8.sta` (frame 4195) reproduces the original run's next 14 frames. The code is listed in `py/ai_kind78/` (`rdis.py`; the `--all`
listing cuts kind 8 at `$3c500` and decodes its tables as garbage).

### Which character

The HUD name selector is `$5b640` (`py/ai_kind78/hudnames.py`): table `$5b682` by tag, a word per kind, then `32 * +20` bytes; the text is
tile words `$44xx` with xx the ASCII code. For tag 2 [R]:

| kind | `+20` = 0, 1, 2, 3 |
|---|---|
| 0 | BRED, DUG, JAKE, SIMONS |
| 1 | J, TWO.P |
| 2 | AXL, SLASH |
| 3 | ANDORE Jr., ANDORE, G.ANDORE, U.ANDORE, F.ANDORE (`+20 = 4` is outside the four-row decode of `hudnames.py`; read directly) |
| 4 | G.ORIBER, BILL BULL, WONG WHO |
| 5 | HOLLY WOOD, EL GADO |
| 6 | ROXY, POISON |
| 7, 8 | the rows of kind 5: HOLLY WOOD, EL GADO, ... |

[L] A kind 8 (`+20 = 0`) pushed into the enemy-HUD ring showed "HOLLY WOOD" with kind 5's portrait, and kind 5 `+20 = 1` showed "EL GADO"
(1 sample each). So kinds 5, 7 and 8 share one name row and two different fighters carry the label HOLLY WOOD (kind 5 `+20 = 0` is the
orange knife fighter). Document kind 8 as the fire-bottle thrower with the HUD label HOLLY WOOD. The name table also settles AXL for kind 2 `+20 = 0` [R].

### Record fields and data

| field | meaning (kind 8) |
|---|---|
| `2` | state: 0 init, 2 active, 4 dying, 6 free |
| `3`, `4`, `5` | mode, step, sub-step (each counts in steps of 2) |
| `23` | hit-stun counter (set to 6 by `$736e`) |
| `30` | frame timer |
| `46` | facing: 0 right, 1 left |
| `47` | `$0c` normal, 0 during the burn launch (draw attribute, [I]) |
| `54` | heading, an index into the root-motion table at `50(A6) = $d2db4` (`$3180` adds its dx, dy): 8 east, `$18` west |
| `62`, `63` | the attacker's facing; the hit-reaction id (box `+11`, low 7 bits) |
| `64`, `66`, `67`, `68`, `70` | grab link (`$412a`, `$41ba`, `$4166`, `$4234`) |
| `74`, `76` | holding a bottle; pointer to the bottle record |
| `80`, `82`, `84`, `86` | vx, friction, vy, gravity (8.8 fixed point per frame; `$30d4` adds, `$315c` brakes) |
| `99` | burning flag |
| `105` | player index of the grabber (from the holder's `+19`) |
| `128`, `129` | saved heading; reaction id in use |
| `130`, `131` | died on a thrown impact; impact already taken |
| `132` | target camera column |
| `134` | target player record pointer (long) |
| `138`, `139` | was walking; was about to throw |
| `140`, `142` | leap vy, gravity |

Init (`$36e12`, `$2fa2`) sets `56 = $37a88` (frame and box data) and `92 = $37c60`. The data at `$37c60` is 32 health words, all `$000a`, so
kind 8 has 10 hp at every difficulty, and 32 defence bytes (all 0) at `$37ca0`; `92` then becomes `$37cc0 + variant(96)`. Death needs hp < 0,
so a kind 8 takes 2 of Cody's punches [L: 10, 10 damage]. The damage table at `$37cc0` overlaps animation data (see "The leap").

### States

| `2(A6)` | entry | role | evidence |
|---|---|---|---|
| 0 | `$3c4a2` | init | [R] [L] 8 of 8 natural runs, 2 script spawns |
| 2 | `$3c504` | active: grab check, mode table `$3c534`, reaction check, cull, sprite | [L] 974 of 974 dispatches |
| 4 | `$3cee2` | dying | [L] 75 of 75 |
| 6 | `$3d0a0` | `jmp $3878` (free the record) | [L] 8 of 8 |

Modes inside state 2 (`3(A6)`, table `$3c534`):

| mode | entry | role | steps (`4(A6)`) |
|---|---|---|---|
| 0 | `$3c540` | walk to a random camera column | 0 `$3c556`, 2 `$3c580`, 4 `$3c5c8` |
| 2 | `$3c62a` | throw the bottle | 0 `$3c640`, 2 `$3c65a`, 4 `$3c67c` |
| 4 | `$3c716` | flee and leave | 0 `$3c72c`, 2 `$3c758`, 4 `$3c784` (leap) |
| 6 | `$3c7aa` | hit reaction | 0 `$3c7ba`, 2 `$3c7d6` (sub-steps by `5(A6)`) |
| 8 | `$3cc8e` | recover after a released grab | 0 `$3cca4`, 2 `$3ccc0`, 4 `$3cce2` |
| 10 | `$3cd3e` | thrown by the player | 0 `$3cd54`, 2 `$3cd80`, 4 `$3ce42`, 6 `$3ce82`, 8 `$3cec2` |

[L] In 8 natural runs and the grab, release and throw runs, the live execution count of every modelled entry above equals the number of
frames the state log dispatches it (21 of 21 for the natural runs, 35 of 35 with the held, thrown and released runs; for example `$3c62a`
408, `$3c716` 298, `$3cd3e` 192, `$3cc8e` 32). Natural durations: mode 0 step 4 20 frames, mode 2 step 2 20 frames, step 4 30 frames.

### Decision logic

```c
void kind8(void) {                          // A6 = record, D7 = dbf counter, phase16 = (167(A5) + D7) & 15
  switch (s2) { case 0: init(); break; case 2: active(); break; case 4: dying(); break; case 6: free_record(); break; }
}
void init(void) {                           // $3c4a2
  if (stage == 0 && area == 2) x = camx - 0x18;              // [L] 1 of 1 (x = $3d8 at cam $3f0); same value the two script entries use
  start_walk_anim(); s2 = 2; ground = y; saved_heading(128) = heading(54);
  fl130 = fl138 = fl139 = fl99 = 0;
  hp = shadow = max = word[$37c60 + variant(96)];             // $2fa2
  if (alloc_tag6() fails) goto free_record;                   // $3d17a: the bottle, tag 6 kind 4, 74 = 1, 76 = ptr, bottle.64 = $ff (held)
  fl47 = $c; target(134) = nearest_player(); face_target();
}
void active(void) {                                           // $3c504
  grab_link_check();                                          // $412a: sets 66 = 2 and 3 = 4 = 5 = 0 when the player has seized it
  if (b66) { held(); return; }                                // $3d224
  mode_table[s3 / 2]();
  react_check();                                              // $3d1b6
  if (phase16 == 0) cull();                                   // $3bb0: x outside [cam - $80, cam + $200] or y outside [camy - $80, camy + $180] -> s2 = 6
  submit_sprite();                                            // jmp $32aa
}
```

Modes 0, 2 and 4 end with `$3d0a4`: when `phase16 == 0` and `299(A5) != 0` the bottle is dropped, s2 = 4, 3/4/5 = 0 and sound `$b8a` plays
(an all-clear kills every fighter) [L] 1 of 1.

```c
// mode 0 ($3c540): reposition
step0: heading = (face == 0) ? 8 : 0x18; steptab(50) = $d2db4; fl138 = 1; start_walk_anim();
       column(132) = coltab[rand() & 0x3e];                  // $3c5ea: 32 words, $40..$140, weighted right
step2: tick_anim(); root_motion();                           // $3b3c, $3180
       if (tile_blocked()) { saved_heading(128) = heading ^ 0x10; goto next; }    // $7d6c: the stage tile-map wall test
       if (abs(camx + column - x) <= 0x10) goto next;
next:  step = 4; timer(30) = 20; fl138 = 0; fl139 = 1;
step4: if (--timer == 0) { s3 = 2; s4 = s5 = 0; }
```

The walk direction is the facing chosen at init (toward the nearest player); it does not turn toward the column. If the column is behind
it, it walks until a tile wall stops it [L] 3 of 3 runs. The column was `$80` in all 8 corpus runs (the LFSR phase was the same). A spawn
placed past the area wall (x > `$4ff` at camera `$3f0`) is pushed back 28 px in one frame by the collision code.

```c
// mode 2 ($3c62a): throw
step0: if (!fl74) goto mode4;
       target(134) = nearest_player(); face_target(); start_anim($36e84);    // wind-up: 3 frames of 10 ticks, event byte on the third
step2: tick_anim();
       if (event_byte(41) != 0) { step = 4; timer = 30; fl139 = 0; fl74 = 0; throw_bottle(); sound($e); }   // 20 frames after step 0 [L] 8 of 8
step4: if (--timer == 0) { s3 = 4; s4 = 0; }
throw_bottle():                                              // $3c68e; bottle = record 76(A6)
   d = target.x - x + 0x50;
   if (d <= 0xa0) vx = ((face == 0) ? +0x50 : -0x50) << 3;                    // near: +-$280, lands about 65 px ahead
   else           vx = (offtab[rand() & 0x1e] + target.x - x) << 3;           // offtab $3c6f6: +80, 0, -80
   bottle.vy = 0x280; bottle.grav = 0x68; bottle.heading = (face == 0) ? 8 : 0x18;
```

[L] Near case vx = `$fd80`; a far case gave `$f930` = (-138 - 80) << 3, as the formula says. A throw flies about 26 frames, lands, and the
bottle stays 60 frames.

```c
// mode 4 ($3c716): flee
step0: heading = saved(128);
       if (heading == 0) { face = (x > camx + 0xc0) ? 0 : 1; heading = (face == 0) ? 8 : 0x18; }   // $3d150: the nearer screen side
       else face = (heading == 8) ? 0 : 1;
       start_walk_anim(); step = 2;
step2: tick_anim(); root_motion();
       if (!tile_blocked()) { if (((167(A5) + D7) & 7) == 0 && (x < camx || x > camx + 0x180)) s2 = 6; }   // $3d126
       else { step = 4; vy(140) = 0x880; grav(142) = -0x58; start_anim($36eb4); }                          // leap, attack box 6
step4: vy += grav; y += vy << 8; root_motion(); tick_anim(); same off-screen test (there is no landing test)
```

The flee direction is the opposite of the walking heading when mode 0 was blocked, otherwise the heading in the script's `+12` byte
(`$18` west; 0 means the nearer side). [L] 3 of 8 runs left by the leap (`$3d126` 287 calls against 230 + 60 step 2 and 4 dispatches, the 3
extra dispatches being the blocked frames); the other 5 walked off. Each fighter throws once: after the throw `74 = 0` and `139 = 0`, so a
released fighter goes to mode 4.

Target selection (`$3068`, at init and at throw start): with both players active it compares |P1.x - x| and |P2.x - x| and keeps P1
only when strictly closer; ties and P2-closer pick P2; lane y is ignored; with one active player it takes that one. [L] single player: `134 =
$ffff8568` in 8 of 8 runs; with P2 poked active, init chose P1 (dx $3c against $8b) and the throw start chose P2 once P2 had moved to
x = `$4ed` (dx 18 against 32): 2 of 2 consistent. Facing: `$3d10c` sets `46 = 0` when the target is to the right. Randomness is the `$3c26`
LFSR only (column, throw spread). `168(A5)` is not read anywhere in `$3c446-$3d392` (0 references), so the difficulty rank does not change kind
8; `96(A6)` (the variant, `169(A5)` when the script byte is `$ff`) only selects a health row and a damage-table offset. `$3e88`, the per-kind
concurrency cap used by the script spawner, lets kind >= 7 through without counting.

### The bottle and the fire

The bottle is a tag-6 kind-4 record (handler `$5957a`); the fire is a tag-`$a` kind-16 record (handler `$54b4a`). **Neither handler has been
read**; what follows is from logs. The bottle is held (`64 = $ff`, the follower code of `$41ba` keeps it at the hand), is released with the
velocities above, and on landing spawns the fire in the same frame, then lasts 60 frames and frees itself through `$38b4`. The fire lasts 86
frames (states (2,0) 11, (2,2) 32, (2,4) 19, (2,6) 24) with an attack box that pulses every other frame. [L] It hit Cody once for 40 damage
(78 to 38, Cody's reaction id 8, attacker `+60` the fire record; this matches `$759c` "kinds 16-18 damage 40"), and it killed a kind 8 that was
hit before its throw (hp 10 to -30), 1 run each. `$3d0d2` pops a held bottle upward (vy `$800`, vx +-`$100`, gravity `$48`) whenever the
fighter is hit, grabbed, killed or all-cleared, so it burns on the spot [L] (hit in mode 0, killed by its own fire; thrown by Cody, Cody burned).

### The leap

Mode 4 step 4 plays animation `$3752c` with attack box 6 (hurt box `$10`). Boxes 1-5 and 7 exist in the data but no animation of kind 8
that was walked uses them. The damage is `byte[$37cc0 + variant(96) + $20]` (all of boxes 1-6 carry the word `$0020` at `+8`), and that
region overlaps animation data. Forcing `45(A6) = 6` beside Cody [L]: variant 0 did 4 damage (78 to 74), variant 4 (the saved state's
`169(A5)`) did 1 (78 to 77). [R] variants 2, 6, 8, 10 would read `$0e`, `$ff`, `$00`, `$00` (14, 255, 0, 0). Spawns with the variant byte
`$ff` exist only in stage 5, so the leap's damage there depends on `169(A5)` through an overlapped table. Cody's reaction to it is id 3
(box `+11 = $83`, knockdown).

### Hit reaction and death

`$3d1b6` runs after the mode handler every active frame:

```c
if (299(A5)) return;
if (hp >= 0) { if (hp == shadow) return; shadow = hp;
               if (y != ground && id63 != 8) id63 = 3;        // hit in the air: knockdown
               s3 = 6; s4 = s5 = 0; drop_bottle(); }          // $3d0d2
else         { if (fl130) return; if (id63 == 8) fl99 = 1;
               s2 = 4; s3 = s4 = s5 = 0; sound($b8a); drop_bottle(); }
```

Mode 6 step 0 (`$3c7ba`) copies `129 = 63`, sets `46 = 62 ^ 1`; step 2 (`$3c7d6`) dispatches by `129` through the 9-entry table
`$3c7e4` (`5(A6)` = 0, 2, 4, ...):

| id | handler | sub-steps | then |
|---|---|---|---|
| 0, 2 | `$3c7f6` | 0 flinch anim `$36ef4`; 2 wait out the first event frame; 4 wait `23(A6)`; 6 tick to the end byte | mode 4 |
| 1 | `$3c88a` | as above, anim `$36f04` | mode 4 |
| 3, 7 | `$3c8aa` | 0 launch pose `$36f14`; 2 wait `23`; 4 flight (vx +-$200, vy $380, g $48) to landing; 6 bounce; 8 slide (`$315c`); 10 get-up crouch, 20 frames | mode 4 |
| 4 | `$3cc78` | no reaction | mode 4 |
| 5 | `$3c9e6` | wait `23`; two bounces (vx $280, vy $380 then $300); slide; hp < 0 check; 57 frames | mode 4 |
| 6 | `$3cb3c` | as 5 with vx $200, vy $300 and one bounce | mode 4 |
| 8 | `$3cc4e` | sets `99 = 1`, `47 = 0`, burn launch anim `$400c`; then the steps of id 3 | mode 4 |

[L] Natural ids: Cody's b1 combo gave attack ids 1, 1, 2, 3 with reaction ids 0, 0, 1, 3 (damage 10, 10, 10, 16); his jump kick attack id
13 with reaction 3 (damage 12); the fire id 8. Ids 2, 4, 5, 6, 7 were forced by poking `63` (27 of 27 reaction entries match their state-log counts).
Id 14 is only written by `$3ce16` and is off the end of the table; forcing it jumps into data and frees the record (never dispatched by
the game). While thrown, lying or in the launch pose the fighter has no hurt box (hurt index 0).

Dying (`$3cee2`, by `3(A6)`): mode 0 steps 0 `$3cf3c` (wait `23`, launch vx +-$400 backwards, vy $300), 2 `$3cf82` (flight, bounce, first
landing: sound `$aaa`, bottle dropped), 4 `$3cff8` (second flight), 6 `$3d038` (slide, then blinks: no sprite on even frames) end in s2 = 6. On
that transition the code pushes event 7 (`$87` for player 2) into the byte ring at `516(A5)` through `$288c`; its consumer is not read. [L]
Cody's score gained 100 per hit and 1000 at the kill event (2 hits, 1 kill, 1 run). Mode 2 (`$3d058`: `$3d080` 1 frame, `$3d094` 40 frames in
place) is reached only by a thrown fighter that died on impact (`130 = 1`): [L] hp poked to 1 and thrown gave 1 and 40 frames. The writes
`3(A6) = 2` at `$3cb04` and `$3cc10` (death at the end of a knockdown slide) are overridden in the same frame by `$3d1b6` (`$3cb04` and
`$3d1f4` each ran once, 1 run), which also plays `$b8a` a second time.

### Held and thrown

`$412a` seizes when `64` is set and the holder still links to it (`66 = 2`). `$3d224` then dispatches `3(A6)`: 0 `$3d246` (`$4234` loads
the offset table by the holder's `+20`, victim tag and kind), 2 `$3d252` (`$41ba` copies the holder's position plus a table offset indexed by
`67(A1)`, then the held pose `$36f44`). `$41ba` returns 0 to keep following, positive to release (mode 8 via `$3d27e`) and `$ff` when the
holder's `67` is negative, which means thrown: mode 10. While held, `$3d2f0` reacts to hp changes (table `$3d318` by `63`): ids 0, 1, 2, 4 stay
held unless hp < 0 (death); ids 3 and 8 release into mode 6; ids 5, 6, 7 set `130 = 1` if hp < 0 and release into mode 6. [L] All four paths
ran with forced ids; Cody's grapple strikes did 9 and 16. Mode 10: vx `$400`, vy `$400`, g `$48`; `$6c96` checks collisions with other fighters
while vx is non-zero ([R] only); the first wall or landing runs `$3ce16` (`63 = $e`, `$3f7a` impact damage, sound `$aaa`, `131 = 1`, HUD push `$28b4`,
and `130 = 1` with the bottle dropped when hp < 0); then bounce, slide, 20 frames, mode 4. Release: [L] clearing Cody's `+64` ended the hold
and the record went to mode 8 (30 frames) and then mode 2 because `139 = 1` (1 run).

### Spawns

The live script list is the second table, `$5f7e`: `$5b1e` does `tst.w $726e0.l`, the ROM word there is `$0002`, so `lea $5f7e` is taken
(`py/ai_kind78/scripts.py`). Entry layout from `$5ee6` and `$5e84`, from the entry start: +0 delay, +2 tracked flag, +4 x, +6 y (bit 15 =
random +-15), +8 tag, +9 kind, +10 and +11 the `+20` and `+21` bytes, +12 heading, +13, +14 variant (`+96`; `$ff` = `169(A5)`), +15
one-player-only. A whole-ROM scan finds all 42 kind 7 and 8 entries inside the script region. Kind 8 (41 entries, `+20 = 0`):

| stage `190` | area `191` | count | entries |
|---|---|---|---|
| 0 | 2 | 2 | `$0707d0` (delay `$f0`), `$0707e0`; heading `$18`; untracked |
| 1 | 2 | 3 | `$070964-$0709a4`; x = `$11a0` |
| 2 | 0 | 4 | `$070b50-$070b80` |
| 2 | 2 | 4 | `$070ca6-$070cd6` |
| 3 | 0 | 4 | `$070f82-$070fb2`; tracked, heading `$18` |
| 5 | 0 | 10 | `$071512-$0715a2`; tracked, variant `$ff` |
| 5 | 1 | 2 | `$071716`, `$071726` |
| 5 | 2 | 12 | `$07176a-$07181a` |

Stage 4 has none. [L] The stage 0 / area 2 pair spawned by the executor itself (190/191 poked to 0/2, script pointer on the third wave block
of that area, camera x `$aa0`, which is the block's trigger): kind 4 and kind 6 first, then the two kind 8 at x = `$a88`, y = `$1c` and `$32`
371 and 373 frames in, hp 10, state 2 (1 run; `script_spawn.sh`). The delay word applies before the entry is spawned.

### Kind 7

State table (`2(A6)`, jump table `$3c452`): 0 `$3c45a` `s2 += 2; 30 = byte[$3c46e + (rand & $1f)]`; 2 `$3c47e` `if (--30 == 0) s2 += 2`; 4 and 6
`$3c48a` `jmp $3878`. It never draws (no `$32aa`), has no hp and no hurt box. [L] 6 of 6 runs: the handler executes delay + 2 times (for
example 80 = 78 + 2), `$3c45a` once, `$3c47e` delay times, `$3c48a` once; delays 78, 78, 10, 10, 40, 46. The table is 16 bytes (`$0a $1e $1e $14 $28 ...`)
but the index mask is `$1f`, so half the draws read the next instruction's bytes (`$53 $2e $00 $1e $66 $04 $54 $2e $00 $02 $4e $75 $4e
$f8 $38 $78`: delays 83, 46, 0 which counts down from 255, 30, 102, 4, 84, 46, 0, 2, 78, 117, 78, 248, 56, 120). 78 and 46 above came from that
over-read (3 of 6 runs). This is a mask bug in the original (`#$1f` where `#$0f` was meant, [I]).

The only entry is stage 5 area 0 (`$0715c2`, x = `$1280`, y = `$820`, tracked, delay 1). The wave block before it has trigger (camera x)
`$1280`, timer `$e10`, count 1 and flag 0; flag 0 makes `$5e0e` set `278(A5) = 1`, which the camera update `$61ed8` reads to skip the camera step (`transitions.md`). So it reads as a timed scroll lock released when the one tracked record disappears [R] header, [I] reading; a test would be
to run stage 5 area 0 to camera x `$1280` and watch `278(A5)` and the script pointer.

### Not proven

- Kind 7's role as a scroll-lock hold ([I], above).
- The exact scoring rule (100 per hit, 1000 per kill): one run each; the consumer of the `516(A5)` ring is unread.
- `$5957a` (bottle) and `$54b4a` (fire) are unread; the fire's box sizes, 86-frame schedule and 40 damage are from logs.
- Reaction ids 2, 4, 5, 6, 7 were forced, not caused by a player attack; drive each Cody move and log `+63`.
- `$6c96` (a thrown body hitting other fighters) is [R] only; throw a kind 8 into a standing enemy and watch its hp.
- Stage 5's leap damage for variants 2, 6, 8, 10 is read from bytes, not run (`spawn.lua` field 7 = 2, 6, 8, 10 with box 6 forced).
- Stage 0 was played through the script (all 18 entries); the entries of stages 1 to 5 were not (the bot stalls at stage 2, `py/stage/README.md`). The target rule with a real player 2 is confirmed (`twoplayer.md`).
