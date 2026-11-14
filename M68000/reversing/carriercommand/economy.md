# Carrier Command: the world, the islands and the supply economy

The archipelago is fixed data. What is generated at the start is the scenery and, through 500 ticks of the
island simulation run at instant-build speed, the layout of buildings on each island. The economy is a set of
per-island stock records joined by a supply graph; goods move between islands as packets that route
themselves over an all-pairs distance matrix maintained a few rows per call.

Proof labels as in `ai.md`. Gate: `py/world/gate_economy.sh` (`gates.toml` "economy"), which reruns the
60M-step watch below from `c_s30.snap` and replays it (the fresh run reproduces the recorded log byte for byte).

| Proof | Count |
|---|---|
| production rule `$2205a`, every stock write at `$220b0` in 60M steps | 175/175 |
| production-line cost writes `$226a8` and step decrements `$226ac` | 14/14, 14/14 |
| packet landings `$22490` | 4/4 |
| distance matrix before every `$21e8a` call against the port, ownership as in `c_s30` and with every free island poked to the player (`py/infographics/gen_routing.py drive`) | 41/41 and 129/129 dumps, 4096/4096 entries each |
| a pool-2 packet's hops `$22192` and dwell times, OBSIDIAN to VULCAN, poked ownership, with and without STAVROS | 14/14 and 14/14 hops, dwell = edge cost 14/14 each, both landed |
| RNG `$192bc`, one call from a set state | 1/1 |

## 1. Islands

The 64 islands come from two tables present in RAM before world creation (`c_mv.snap`): names at `$4d184`
(64 word offsets, then NUL-terminated names: 0 VULCAN ... 63 NEMESIS) and positions at `$4d41a`, 22 bytes per
island: x, y, w, h, the position and heading of the island's main structure (zero for none) and two scenery
seed positions. Runtime coordinates are the word times 512 (`$18028..$18030`); the position panel shows
world / 1677.72 (= 2^24 / 10000).

Proven: `c_mv.snap` holds both tables while the island records are all zero; a `watch` across world creation
shows `$17fe2` filling the records from `$4d41a`, matching `c_s30`'s record 0 byte for byte. `islands.png`
draws the archipelago from these tables with the supply graph of section 3 (`py/world/render_map.py`).

| Record | Base | Stride | Fields |
|---|---|---|---|
| island | `$69b80` | 402 | +0 protected flag (`$ff` on island 0), +2/+6 x/y longs, +10/+12 w/h, +14 area `(w*h)>>16`, +18 32 structure slots of 12 bytes |
| structure slot | record+18 | 12 | +0 type word (the type is its low byte, +1), +4 progress or HP, +6 supported flag / owner-type code, +8/+10 local x/y; slot 0 is a header (type 8) |
| owner | `$69b40` | 1 | 0 free, 1 player, 2 enemy |
| economy | `$66ec0` | 50 | +0 type (0 BASE, 1 RESOURCE, 2 FACTORY, 3 DEFENCE), +2 output stock, +4 its cap (2 x area), +6 count of supported `$2a/$2e/$2b` slots, +7 command-centre flag, +8 materials, +10 their cap, +12 production-line count, +14 up to 3 lines of 12 bytes |

The island panel's AREA is `w*h/10000/250` km^2 (`$b6ec..$b6fc`, inferred).

## 2. World creation and the RNG

"Creating Game World" (`$3cb0`) is only a message (`$3c06`). Creation then runs `$17b9c`, `$17fe2` (island
records from the fixed tables), `$c94c`, `$509e` (fills `$4f1ee` with `$d00` random words, inferred to be the
sea-surface pattern), `$3cd4` (object pools) and `$21e16` (supply network). Within the island set-up:

- `$18610` puts 21 random scenery items (types `$18..$1b`) on each island at random free spots (`$186e6`).
- `$18662` places the starting command centres from the table at `$18c8a`, or `$18cc4` when `$1244 == 0`
  (entries (island, code): code & 3 = island type, (code >> 4) + 1 = owner). In `c_s30` the player has island 0
  (BASE) and the enemy islands 49, 52 (DEFENCE), 50, 54, 56 (FACTORY), 53, 55 (RESOURCE) and 63 (NEMESIS, its
  base); the carriers start at islands 0 and 63 (`$18c76`).
- `$180ec` runs the island tick `$18106` 500 times with `$8d8` set so construction is instant: the starting
  buildings on each island are grown by the simulation, not laid out by hand.

The RNG `$192bc` (also stepped inline by the sound interrupt at `$203ac`, so its sequence depends on timing)
is a 64-bit add-with-carry generator over two longs A:B at `$1230`/`$1234`, not an LCG. In 16-bit words with
X the carry:

```
lo = 2*A.lo; X = carry;  A.lo = lo + B.lo + X (X = carry out);  B.lo = lo
swap the halves of A and B
t = A.lo;  A.lo = A.lo + B.lo + X;  B.lo = t
swap the halves again;  return A
```

Proven: from A:B = `$01234567:$89abcdef`, `callcap 192bc` returns D0 = `$8acf58bd` and leaves `$8acf58bd:$01238ace`,
as `py/world/rng.py` computes.

## 3. The supply graph

Each island has an adjacency list at `$22afa` (32 bytes per island: a count, then pairs of edge cost and
neighbour; bit 15 of the neighbour word is set when the edge is disabled, and the index is masked with `$3fff`).
There are 84 links of cost 8 to 69; 44 of the 64 islands have two or three, nine have one (SPLINTER (38) hangs
off ENDYMION (36) by the dearest link, 69). Two links are one-way, 15 to 16 and 51 to 52, and TREASURE (51)'s only
link is its own one-way link out, so nothing can route to it. `$21f9e` enables an edge only between two islands of the same owner, so taking
an island cuts the other side's routes through it.

`$67b40` is a 64 x 64 word distance matrix (rows of 128 bytes). `$21e16` refills it with `$ffff` (diagonal 0)
when ownership changes, and `$21e8a` relaxes 8 rows per call in place, one call per main-loop pass:
`M[i][k] = min(M[i][k], M[j][k] + c)` over each enabled link (c, j) of row i; after a full sweep of 64 rows it
sweeps again if anything changed, otherwise it clears `$122f`, which packets wait on. It is distance-vector
routing (Bellman-Ford, as in RIP) with islands for routers. Proven call by call against the port in two
ownerships (proof table); with every free island the player's, the last entry changes at call 113 and `$122f`
clears at call 128.

**A stray write (inferred bug).** The island tick at `$18170` reloads A0 with row 63 (`$69ac0`) to test an enemy
island's entry, then stores 500 at `8(A0)` (`$1817e`), which is `M[63][4]`, not the island record's +8 it used two
instructions earlier. The emulator shows the write live between the 7th and 8th relaxation calls, and the port
matches `c_s30`'s stored matrix only with it: the enemy block then sees a 500-cost route to CHARISSA (4). Whether
that moves the enemy's choices (`ai.md` section 2) is not checked. Row 0 is the player's distances, read by the island panel as "DISTANCE TO
BASE" (and the `$d46` column as "DISTANCE TO STOCKPILE", with "ISOLATED" and "RE-ROUTING" when no route
exists, inferred from `$b698..$b844`); row 63 at `$69ac0` is the enemy base's, which the enemy AI scores with
(`ai.md` section 2). The panel's km figure is the edge sum times 65536 / 1573 (inferred).

## 4. Production, lines and packets

`$f254` runs the economy chain every 4th main frame (countdown `$982`; about every 2.4M steps in `c_s30`):
`$2205a` production, `$220cc` and `$2239a` packet movement, `$225d0`, `$22770`, `$228d2`, `$2262c` production
lines and `$22204` resource dispatch.

**Production (proven).** For each island with an owner:

```
stock(+2) = min(stock + rate, cap(+4))
rate = 100 for BASE, 100 * byte(+6) for RESOURCE, 25 * word(+12) for FACTORY, 0 for DEFENCE
```

A free island with the +7 flag set gains `cap / 16` (inferred). In the 60M-step log the BASE and FACTORY
terms decide the result (a wrong base rate or factory multiplier breaks the proof); the RESOURCE rate, the
free-island trickle and the cap clamp are never exercised, because the player holds only Vulcan, so those
three are from code.

**Production lines (proven).** A line in state 1 subtracts its cost (+24 of the record) from the stock each
tick and counts its steps (+18) down; a finished line emits a packet (item, quantity, destination) and reloads
from the recipe table at `$226fe` (6 bytes per item: steps, quantity, cost; items 0..17; item 0 is 15 steps,
quantity 4, cost 100). Vulcan's own line (item `$12`, quantity 255, cost 100, destination 0) costs exactly its
production, which is why its stock looks flat when sampled per tick.

**Packets.** Pool 1 at `$66bc0` (128 x 6 bytes: node, timer, amount, destination) carries resource lots of 200
units from RESOURCE islands to BASE or FACTORY islands (`$22204`, `$22256..$2238e`, inferred). Pool 2 at
`$66710` (200 x 6 bytes: node, timer, item, quantity, destination) carries manufactured items. Each step
`$22192` moves a packet to the enabled neighbour j strictly closer to its destination t with the least
`M[j][t] + c`, and sets its timer to the edge cost c, so a hop lasts as many economy ticks as it costs (proven,
proof table). With no hop an item packet is lost and a resource lot dumped; in the pool-1 path
(`$2214e..$22154`), when stock plus lot exceeds the cap the code stores the packet's destination (`4(A0)`) as the
stock where the cap (`4(A1)`) is expected, which looks like a second bug (from code, not driven). On arrival, a
destination of -1 means the stockpile island `$d46`: items below `$f` add to the counters at `$d74[item]`
(capped at 999), items `$f..$11` add `quantity << 8` to the longs at `$d5c` (capped at `$1fffc0`); item `$12`
to a concrete island adds to its materials, `+8 = min(+8 + quantity, cap(+10))` (proven: 4 landings of 255 on
island 0, each one tick after its packet was created at `$226c0..$226e0`).

## 5. Island buildings

`$18106` ticks one island per main frame (`$8cc` mod 64) and reshuffles the visiting order with the RNG every
64 ticks. Per island it runs the structure handlers through the 8-byte table at `$188d0` (handler, full
strength), recounts quotas (`$181c8`) and builds (`$18528`), all inferred from code:

- Types `$24..$2e` are finished structures (`$183f8`; the command centre `$29` uses `$18410`); their table
  parameter is full strength (4000, 6000, 1000, 1500, ...). Types `$2f..$39` are the same structures under
  construction or being dismantled (`$18378`, consuming materials through `$18334`/`$1834c`; `$34`, the command
  centre under construction, uses `$1842c`).
- Scenery types `$18..$1b` have a 1 in 4 chance per tick to disappear (`$18502`).
- `$18528` builds the highest-weight structure the island's class allows, at most two constructions at once
  (`$8d0`). The class is 0 for a free island, 7 for a base, otherwise the island type, plus 3 when the area is
  at least 2000 (`$18192`); weights are the 10-byte rows at `$5a212`. In weight order: RESOURCE `$28 $26 $27
  $2e $2a`; FACTORY `$2c $28 $26 $27 $2d`; DEFENCE `$25 $28 $26 $27`; BASE `$2c $25 $28 $26 $27 $2a`.

The structure types are numbered only; the strings naming them have not been found.

## 6. Open

- Who starts production lines and chooses their items (the "Set Priorities" screens, `$22770`, `$228d2`).
- A resource-to-factory transfer has not been observed (it needs a second player island).
- The names of structure types `$24..$2e`.
