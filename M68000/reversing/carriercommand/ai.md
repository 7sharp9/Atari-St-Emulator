# Carrier Command: the enemy carrier and island defences

The computer side is one carrier driven by a small state machine, a 64-island scoring function that picks
where it goes next, and per-structure behaviours on the islands it owns. Difficulty never reaches the
strategic layer: it only tunes the island defences.

Proof labels: **proven** means an emulator observation with a count; **inferred** means read from code only.
Gate: `py/ai/gate_score.py` (`gates.toml` "target").

## 1. The state machine `$1ac8c`

`$1ac8c` runs once per main frame (called from `$3a04`) and is skipped while the game is paused (`$464 == 0`,
the branch at `$39fe`). A main frame is usually 6 VBLs (72,000 steps; the travel countdown `$11c0` fell
`$17f8 -> $1794 -> $1730` over two 7.2M-step stretches, exactly 100 ticks each), but it is not fixed: with
combat on screen ticks came every 48,000 to 72,000 steps, so durations below are in ticks.

`$11be` indexes the 12-long jump table at `$1aca0` (`add.w D0,D0` twice, `movea.l 0(A0,D0.w),A0`, `jmp (A0)`);
entries 6..9 are `rts`. The string "Enemy state " at `$1ac7d` has no reader: a leftover debug label.

| Field | Meaning |
|---|---|
| `$11be` | state |
| `$11ba` | target island |
| `$11bc` | current island |
| `$11c0` | countdown (travel, waits) |
| `$11c2` | hull, `$2000` at start, repaired to at most 12000 |
| `$11c4` | aircraft stock, 8 at start |
| `$11cc` | missile stock (12 in `c_s30`) |
| `$11ce`, `$11c6` | missile cooldown (200 ticks), aircraft cooldown (30 ticks) |
| `$11c8` | meant to count aircraft out; never incremented (below) |
| `$11ca`, `$11d0` | retreat flag (read by the enemy aircraft at `$1a902`), retreat speed |

The carrier itself is the entity at `$5f49a` (x long at +10, z long at +18). **It only exists physically while
it is fighting.** In states 1 to 5 the entity's active bit is clear: travel is just the countdown, and on
arrival the island's position is copied in (`$1ae4c`). On entering state 10 (`$1af20`) it is placed beside the
island, at the island's half-width plus `$456` plus 2000 on one of four sides chosen by the RNG, heading away
from the island, and made active. Proven: the active bit stayed 0 through every travel run, and at engagement
x was the island centre plus 29,384 (11000 + `$4000` + 2000) with heading `$4000`.

| State | Entry | What it does |
|---|---|---|
| 0 | `$1acd0` | init: hull `$2000`, air units 8, missiles 0; state 1 |
| 1 | `$1acf0` | pick a target (section 2); `$11c0 = octdist(carrier, target) / 250`, with the octagonal distance `max + min/2` written inline (`$1ad14`; also `$233d2`, `$23402`, `$234b6` in `$2337a`, not a shared routine); state 5. Waits while the supply-distance matrix is being recomputed (`$122f`, inferred) |
| 5 | `$1ae2e` | travel: `$11c0--`; at 0 the carrier is placed on the target island and the arrival dispatch runs (section 3) |
| 2 | `$1ad44` | at its own island: hull +4 per tick (proven over 40 ticks) |
| 3 | `$1ad8a` | attack a player island (section 4) |
| 4 | `$1ae18` | wait 400 ticks after starting a capture; state 1 |
| 10 | `$1afa2` | fight player units within 150,000 (section 5) |
| 11 | `$1b16e` | retreat (section 5) |

Proven: the travel time. From `scratchpad/carrier/ai/nat/d2.snap`, `$11c0 = $2775` = 10101 = `octdist / 250` for
target 48.

## 2. Choosing the next island `$2337a`

Called only from state 1. It writes a signed score per island into the 64 words at `$232fa` and stores the
first maximum in `$11ba`. With E the enemy carrier's position, H the enemy base (island 63, its record at
`$6fe70`) and `oct(a, b) = max(|dx|, |dy|) + min(|dx|, |dy|) / 2` (an octagonal distance with no multiply):

```
for i in 0..63:                                   # island record $69b80 + 402*i, owner byte $69b40+i
    de = oct(island[i], E)
    s  = -15000 if de > 3,000,000 else floor(-de / 2048)
    dh = oct(island[i], H) >> 14
    s += +dh if owner[i] == enemy else -dh
    area = word at record+14
    if owner == neutral: s += 3000 if area > 2000 else 2000
    if owner == player:  s += 1500 if area > 2000 else 1000
    if owner == enemy:   s -= 4000
    if owner != enemy and any adjacency neighbour n of i has enemy-network distance row63[n] >= 0:
        s += 4000                                  # row 63 of the distance matrix, $69ac0
if owner[0] != enemy and oct(island[0], E) <= 3,000,000:
    score[0] += 5000                               # the player's home island
score[current $11bc] = $8001                       # never stay put
target $11ba = first index of the maximum
```

The enemy goes for the nearest worthwhile island, prefers large unowned ones, strongly prefers islands that
touch its connected supply network, and hops through its own islands (at -4000) only when nothing better is
within reach. The base-distance term adds for its own islands and subtracts for others, so it favours other
islands near its base and its own islands far from it.

**Proof (proven, `py/ai/gate_score.py`).** The model reproduces 1344/1344 score words and the target in 21/21
snapshots taken at the return of `$2337a` (`bp $1ad02`): 13 natural decisions from `c_s30.snap` (`ai/nat/`,
`ai/nat2/`; `nat/d1` and `d2` have the same 64 score words as `nat2/e2` and `e3`, so 11 are distinct; each `nat2` leg forces
the arrival with `w 11c0 00012000`, countdown 1 and hull `$2000`, neither of which `$2337a` reads) and 8
single-variable pokes (`ai/s1..s6b`). Each constant is then nudged in turn; ten of the
eleven terms break all 21 snapshots, so each is load-bearing in the corpus. Two terms are weakly covered:
the small-player-island +1000 breaks 0/21 (no small player island in the corpus: it is inferred from code)
and the home-island +5000 breaks 2/21.

Examples from the pokes: making island 56 neutral lifts its score from -4680 to 6126 with the target
unchanged (s1, s2); with the carrier at island 20, changing only `$69ac0[21]` from -1 to 10 flips the
target from 58 to 20 at the predicted 5137 (s3b, s5).

**A probable game bug (proven).** `$18176..$1817e` writes 500 to the fixed address `$69ac8` (row 63, column 4)
whenever the island being ticked is enemy-owned and connected, instead of the ticked island's own column. So
island 4 always reads as connected to the enemy network and its neighbours (3 and 12) get the +4000. With the
carrier at island 4, `$69ac8 = 500` gives target 12 and `-1` gives target 0, both as the model predicts
(s6a, s6b). `c_s30` already holds the 500.

**The player's home island cannot be captured.** Island 0's record byte 0 is `$ff`; the arrival dispatch
(`$1ae5c`) sends any carrier arriving at a record with a non-zero byte 0 straight back to state 1. The +5000
bonus therefore produces a visit and an immediate re-target (observed once, in a poke run).

## 3. Arrival and capture

At the end of travel (`$1ae6c`):

```
if record.byte0 != 0:   state = 1                       # protected island
elif owner == neutral:  start a capture ($1ae88)
elif owner == player:   state = 3 if hull >= $bb8 else 1
else:                   state = 2                       # own island: resupply
```

A capture places a command centre under construction (structure type `$34`) through `$186e6` with
`6(slot) = $10 | rand(1..3)`. When it completes (`$18466`) it becomes type `$29`; its low two bits set the
island type in the economy record (1 RESOURCE, 2 FACTORY, 3 DEFENCE, names from the `$b87c` table) and
`(6(slot) >> 4) + 1 = 2` sets the owner to enemy, followed by "is now an enemy island!" and a network
recompute (`$21e16`). **The type of a captured island is uniformly random, not a strategic choice.**

Proven: in a run from `c_s30` islands 48, 47, 45 and 51 became enemy-owned with types 1, 1, 2, 1, and the
command-centre slots showed the expected progress words (type `$34` with progress 48 and 28 on islands 41
and 32; type `$29` with 2560 on finished ones). The owner and type write itself was not watched (inferred).

## 4. Attacking a player island

State 3 resolves a round every 250 ticks (`$1b22a`, reload `$94a = $fa`):

```
attack  = min(air units, 4) * $400 + hull / 2
defence = sum over the island's structures of $1b400[type - $25]   # $25: 4096, $26: 512, $27: 512, $28: 768
hits on island  = (rand16 * attack >> 16) / $600   # each: a random structure (not types 0, 7, $24) loses $400 HP
                                                    # ($4 if still under construction); removed at <= 0
hits on carrier = rand * defence                    # each: hull -$400, or an air unit, or a missile
```

The island falls when no type-`$29` command centre remains (`$1b3e8`): "is now a free island", owner 0,
stockpile cleared if it was the stockpile, then the capture of section 3. The enemy gives up when its hull
is at or below `$bb8`.

Proven in part: with island 56 made player-owned and the carrier forced to arrive (`ai/atk2.txt`), state 3
held for 144M steps, the island's `$28` and `$26` structures were destroyed at about 78M and 96M steps and
the missile stock fell 12 to 11 at about 114M. The run did not reach a capture; the formulas are inferred.

## 5. Fighting the player's carrier (states 10 and 11)

A player unit (any active entity of the 9 at `$5df5a`) within Chebyshev 150,000 of the enemy carrier while it
sits at an island moves it to state 10 (`$1b1cc`). Proven: from `ai2/st2.snap` (enemy repairing at island 56)
with the player carrier poked to 100,000 away the state went 2 to 10 on the first tick; at 200,000 it stayed in
state 2 for 40 ticks, repairing +4 per tick.

State 10 (`$1afa2`), proven in its parts as listed:

```
if no player unit within 150,000: back to the arrival logic ($1ae6c)
if hull < 3000 or missiles == 0:  state = 11, $11ca = $ff, $11d0 = 0
count down the missile and aircraft cooldowns
d = Chebyshev(player carrier, enemy carrier)
if d <= 30,000:
    turn toward bearing + $8000 at up to 200 per tick
    if within $800 of it, missiles left, cooldown 0 and a free missile slot:
        fire a missile (type $13) 200 ahead at altitude 140; missiles--; cooldown 200
        then try an aircraft launch
    else stop here: no aircraft inside 30,000 except straight after a missile
else: turn toward the stored heading
launch an aircraft (type $21, fuel 2000) if stock, cooldown 0 and one of the 4 slots at $5f5da is free;
    stock--; cooldown 30
```

Observed: at 100,000 two aircraft were launched 31 ticks apart and no missiles; at a placed distance of 29,384
one missile was fired 21 ticks after engagement with an aircraft in the same tick, missiles 12 to 11, and the
player carrier was destroyed ("GAME OVER / Aircraft Carrier Destroyed!") about 11.8M steps in (what killed it
was not attributed).

`$11c8`, the aircraft-in-the-air counter tested against 4 at `$1b0e0`, is cleared and decremented (fuel out
`$1a924`, docked `$1ab04`, destroyed `$1c1fc`) but never incremented: a raw scan of `$3900..$23600` finds 7
references and no increment, so the real limit is the 4 slots (inferred from the scan).

State 11, retreat (`$1b16e`, proven): entered with hull 2999 or no missiles (both within one tick; at hull 3000
it stayed in 10 and launched an aircraft). The carrier turns to its stored heading at 200 per tick and then
moves along it. When no player unit is within 150,000 it returns to state 1 and becomes inactive: with the
player at 184,384 that happened on the next tick and it set off for island 55 with the hull still 2999; at
140,000 it stayed in state 11 for 5 of 5 ticks. Its speed is set by `$19e54` (`D1 += clamp(D0 - D1, +/-D2)`)
called with the target in D0 and 250 in D1, so it jumps to 248 on the first tick and stays there (248 on all
238 ticks of a run): by appearance swapped operands for a ramp of 2 per tick (the intent is inferred).

## 6. Island defences and difficulty

Only two islands' structures are live at a time. Each island's structures are kept in one of two blocks,
`$62cda` and `$63cec` (stride `$1012`: +1 island index, +2/+6/+10 position, then 64 records of 64 bytes), loaded
when the player's carrier or a craft comes within Chebyshev 130,000 (`$1fbd0`, `$1b550`) and dropped by `$17f64`
when nothing refers to it. Proven: block `$62cda` switched from island 0 to island 56 within 2.4M steps of the
player moving there. `$1930a` sets the context per block: `$a28` the island record, `$a41` neutral (all
structures inert), `$a40` player-owned (structures aim at the enemy), `$a3e` an opposing unit is present.

The dispatcher `$193dc` walks a block's 64-byte records and calls the table at `$19440` by type:

| Type | Handler | Behaviour |
|---|---|---|
| `$28` | `$19c56` | missile site: a timer reloaded with 128..255 ticks; fires (type `$22`, launch at `$19cc6`) at the opposing carrier when it is near this island and within `$456` |
| `$25` | `$19bcc` | drone launcher: every 100 ticks, with an opposing unit present and fewer than `$448` drones out, launches a drone (inferred) |
| `$29` | `$1980c` | command centre: only when difficulty is at least `$4000`, fires a missile (type `$1c`) at the nearest opposing aircraft within 4000 and below altitude 1500 (inferred) |
| `$16` | `$19912` | the drone: fuel 1000, wanders within +/-24,000, attacks an opposing unit within 25,000 (inferred) |

Difficulty is one word, `$446`. It is 0 at the start of the Strategy game and `$2000` in the Action game
(`$3be6`; proven, section 8), and rises in play through `$18d96`, an unsigned add clamped at `$ffff`: `$800` per
destroy event at `$1c042`, `$400` after an ACCB drop (`$1f9e6`), `$aa4` at `$1c1a0`, `$2000` at `$fe06` in the
Action game (inferred). `$18da6` derives the defence parameters:

| Parameter | Formula | Use |
|---|---|---|
| `$448` | 3 if signed `$446 >= $4000`, else 2 | drones per launcher |
| `$44a` | 3, plus `($446 - $8000) / 10000` when bit 15 is set | drone parameter (+38) |
| `$44c` | `1.5 * ($446 >> 10) + $96` | drone speed |
| `$44e` | `0.75 * (($446 >> 6) + $400)` | drone speed |
| `$450` | `($446 >> 4) + $200` | drone and structure armour; `$450 + $800` is patched into code at `$18a1c`/`$18a74` |
| `$452`, `$454` | `($446 >> 10) + $c8`, `($446 >> 6) + $400` | missile speed limit and turn rate |
| `$456` | `$446` if signed `$446 >= $4000`, else `$4000` | missile site range |

**Proven A/B/C** (`ai2/st56.snap`, player carrier 20,000 from island 56's missile site, the same 16M steps, only
`$446` and its derived values changed): difficulty 0 gives 0 launches (range 16384), `$6000` gives 2 (range
24576), `$c000` gives 0. A positive control at difficulty 0 with the carrier 6,536 from the site gave 1 launch.

**Difficulty wraps.** `$446` is raised with an unsigned add but `$448`, `$456` and the command centre's gate
compare it signed (`blt`/`bge` at `$18db2`, `$18e08`), so a difficulty of `$8000` or more reads as the lowest
setting for drones, missile range and the command-centre missiles, while `$44a` (a `bpl` test) does rise. From
the Action game's `$2000` that is about 12 destroy events away; whether a real game reaches it is open.

The scoring function and the state machine never read `$446`: **difficulty changes how hard the islands fight
back, not how the enemy plans.**

## 7. Cheat mode

Proven: typing **GROW OLD ALONG WITH ME** while the game is paused sets `$1185 = $ff` and shows "Cheat Mode
active" (`cheat.png`). The phrase is stored bit-inverted at `$116e` (pointer `$116a`); keys are turned into
ASCII through the scancode table at `$127a` into `$126a`, and the check `$3df2` runs only from the pause loop
(`$39b0`); success unpauses through `$f85e`. In the proof the pause flag was poked (`w 464 0000ff00`), not
clicked.

With cheat mode on, `$3f88` reads keypad keys from the key-state table at `$794` (inferred, none pressed):
keypad + and - set and clear invulnerability `$1186` (read at `$1bbd4` Walrus damage, `$1bc62` Manta damage,
`$1d88e`); keypad 9 prints "Difficulty level is" and `$446`; keypad 1 sets `$7fff` into the field of each of
the 4 Manta and 4 Walrus slots that is probably fuel (`$498+10`, `$572+8`); keypad 2 sets every craft's hull
(+20) to full, `$fa0`; keypad 3 (`$3ec2..$3f48`) teleports each craft on autopilot to its destination, and the
carrier to its own (`vehicles.md` section 5).

## 8. The two games

The title menu's two start buttons differ only in `$1244` and the starting state (proven by clicking each from
`c_mv.snap`, `ai2/menu_0.snap` and `menu_15.snap`):

| Button | `$1244` | Difficulty `$446` | Start | Islands |
|---|---|---|---|---|
| Start Strategy Game | `$ff` (`$fe7e`) | 0 | Vulcan, -4415,-4288 | player 0; enemy 49, 50, 52..56, 63 (`$18c8a`) |
| Start Action Game | 0 (`$fe72`) | `$2000` | Thermopylae, -999,-958 (`$3bc6`) | player 15 (0..8, 10, 12, 14, 18, 25, 26); enemy 37 (`$18cc4`) |

`c_s30.snap` is the Strategy game. The Action game drops the player into the middle of a war already under way,
at a higher difficulty.

## 9. Open

- What destroyed the player's carrier in the state-10 run (missile or aircraft).
- A drone launcher and the command centre's missiles in action: island 56 has neither a launcher nor player
  aircraft near it.
- What structure types `$26` and `$27` do.
