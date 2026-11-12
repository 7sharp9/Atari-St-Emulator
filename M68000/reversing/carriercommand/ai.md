# Carrier Command: the enemy carrier and island defences

The computer side is one carrier driven by a small state machine, a 64-island scoring function that picks
where it goes next, and per-structure behaviours on the islands it owns. Difficulty never reaches the
strategic layer: it only tunes the island defences.

Proof labels: **proven** means an emulator observation with a count; **inferred** means read from code only.
Gate: `py/ai/gate_score.py` (`gates.toml` "target").

## 1. The state machine `$1ac8c`

`$1ac8c` runs once per main frame (called from `$3a04`; one main frame is 6 VBLs, 72,000 steps) and is
skipped while the game is paused (`$464 == 0`, the branch at `$39fe`). Proven: the travel countdown `$11c0`
fell `$17f8 -> $1794 -> $1730` over two 7.2M-step stretches, exactly 100 ticks each.

`$11be` indexes the 12-long jump table at `$1aca0` (`add.w D0,D0` twice, `movea.l 0(A0,D0.w),A0`, `jmp (A0)`);
entries 6..9 are `rts`. The string "Enemy state " at `$1ac7d` has no reader: a leftover debug label.

| Field | Meaning |
|---|---|
| `$11be` | state |
| `$11ba` | target island |
| `$11bc` | current island |
| `$11c0` | countdown (travel, waits) |
| `$11c2` | hull, `$2000` at start |
| `$11c4` | air-unit stock, 8 at start |
| `$11cc` | missile stock |
| `$11ce`, `$11c6` | missile and launch cooldowns |
| `$11c8` | enemy aircraft in the air |

The carrier itself is the entity at `$5f49a` (x long at +10, z long at +18).

| State | Entry | What it does |
|---|---|---|
| 0 | `$1acd0` | init: hull `$2000`, air units 8, missiles 0; state 1 |
| 1 | `$1acf0` | pick a target (section 2); `$11c0 = octdist(carrier, target) / 250`; state 5. Waits while the supply-distance matrix is being recomputed (`$122f`, inferred) |
| 5 | `$1ae2e` | travel: `$11c0--`; at 0 the carrier is placed on the target island and the arrival dispatch runs (section 3) |
| 2 | `$1ad44` | resupply at its own island (inferred) |
| 3 | `$1ad8a` | attack a player island (section 4) |
| 4 | `$1ae18` | wait 400 ticks after starting a capture; state 1 |
| 10 | `$1afa2` | engage player units within 150,000 (`$1b1cc` over the 9 entities at `$5df5a`) (inferred) |
| 11 | `$1b16e` | retreat (inferred) |

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
within reach. Islands near its own base are favoured if it owns them and penalised otherwise.

**Proof (proven, `py/ai/gate_score.py`).** The model reproduces 1344/1344 score words and the target in 21/21
snapshots taken at the return of `$2337a` (`bp $1ad02`): 13 natural decisions from `c_s30.snap` (`ai/nat/`,
`ai/nat2/`) and 8 single-variable pokes (`ai/s1..s6b`). Each constant is then nudged in turn; ten of the
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

## 5. Island defences and difficulty

Structures on islands are also entities. The dispatcher `$193dc..$1943a` walks 64-byte entities and calls
the table at `$19440` by the type word at +2 (inferred from code throughout this section):

| Type | Handler | Behaviour |
|---|---|---|
| `$25` | `$19bcc` | every 100 ticks launches a defence drone if the island's active drones are fewer than `$448` |
| `$28` | `$19c56` | every 128..255 ticks fires a missile at the opposing carrier when it is on this island and within `$456` |
| `$29` | `$1980c` | command centre: fires only when difficulty `$446 >= $4000` and a target is within `$fa0` |
| `$16` | `$19912` | the drone: five states (idle, chase, orbit, attack, retreat), speeds from `$44c`/`$44e` |

Difficulty is one word, `$446`. It starts at 0 in the small campaign and `$2000` in the large one (`$3bee`),
and rises with player achievements through `$18d96` (clamped at `$ffff`): `$800` per destroy event at
`$1c042`, `$400` after an ACCB drop (`$1f9e6`), `$2000` at `$fe06`, `$aa4` at `$1c1a0` (inferred). `$18da6`
derives the defence parameters from it:

| Parameter | Formula | Use |
|---|---|---|
| `$448` | 2, or 3 when `$446 >= $4000` | drones per launcher |
| `$44a` | 3, plus `($446 - $8000) / 10000` above `$8000` | drone parameter (+38) |
| `$44c` | `1.5 * ($446 >> 10) + $96` | drone speed |
| `$44e` | `0.75 * (($446 >> 6) + $400)` | drone speed |
| `$450` | `($446 >> 4) + $200` | drone and structure armour; `$450 + $800` is patched into code at `$18a1c`/`$18a74` |
| `$452`, `$454` | `($446 >> 10) + $c8`, `($446 >> 6) + $400` | |
| `$456` | `max($446, $4000)` | missile turret engagement range |

The scoring function and the state machine never read `$446`: **difficulty changes how hard the islands
fight back, not how the enemy plans.**

## 6. Cheat mode

Proven: typing **GROW OLD ALONG WITH ME** while the game is paused sets `$1185 = $ff` and shows "Cheat Mode
active" (`cheat.png`). The phrase is stored bit-inverted at `$116e` (pointer `$116a`); keys are turned into
ASCII through the scancode table at `$127a` into `$126a`, and the check `$3df2` runs only from the pause loop
(`$39b0`); success unpauses through `$f85e`. In the proof the pause flag was poked (`w 464 0000ff00`), not
clicked.

With cheat mode on, `$3f88` reads keypad keys from the key-state table at `$794` (inferred, none pressed):
keypad + and - set and clear invulnerability `$1186` (read at `$1bbd4` Walrus damage, `$1bc62` Manta damage,
`$1d88e`); keypad 9 prints "Difficulty level is" and `$446`; keypad 1 sets `$7fff` into two fields of each of
the 4 aircraft and 4 amphibious-vehicle slots (`$498+10`, `$572+8`); keypad 2 sets `20(slot) = $fa0` in both
arrays; keypad 3 moves each active aircraft to its target position.

## 7. Open

- States 10 and 11 (fighting the player's units and retreat), and the defence handlers, have not been driven.
- `$1244` selects the small (8 enemy islands, `$18c8a`) or large (about 40 enemy, 15 player, `$18cc4`)
  starting layout; `c_s30` is the small one. Which title-menu item sets it is not confirmed.
- A plain run from `ai/nat/d2.snap` stops with a double bus fault about 640M steps later, during travel
  (fault at `$004147ea`, PC `$0202049c`), reproduced twice. Emulator or game: not yet known.
