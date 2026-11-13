# routing.svg: facts and sources

Figure: `gen_routing.py` writes `scratchpad/carrier/infographics/routing.svg` (PNG: `rsvg-convert -z 2 routing.svg -o routing.png`).
Doc: `economy.md` sections 1, 3 and 4. The routing code is ported in the script from the disassembly
(`scratchpad/carrier/cc_all.asm`): `$21f9e` link enable, `$21e16` reset, `$21e8a` relaxation, `$22192` next hop, and the
pool handlers `$220cc`/`$2239a` that call it. Graph, costs, owners, positions and names are read from `c_s30.snap`.

`gen_routing.py drive` adds four emulator runs from `c_s30` (logs in `scratchpad/carrier/infographics/routing_drive/`).
Each pokes a state through the REPL (owners, link bits as `$21f9e` would set them, the matrix as `$21e16` leaves it,
`$df0`/`$de8`/`$dec`, `$122e`/`$122f`) and lets the game's own main loop run:

- `fill_c_s30`, `fill_late`: `u 21e8a` then a dump of the 8 KB matrix and the two flags before every call, plus a
  `watch` on `$69ac8` (row 63, column 4). Compared with the port call by call.
- `route_late`, `route_cut`: a pool-2 packet poked into slot 199 (`$66bba`: node 46, timer 1, item `$12`, quantity 1,
  destination 0) and a `watch` on its 6 bytes: each hop is a node write at `$223fa` and a timer write at `$223fe`, each
  tick a decrement at `$223b2`, the landing the `st` at `$2240e`. Owners re-read at the end were unchanged.

| fact in the figure | source |
|---|---|
| 64 islands, 84 links (undirected pairs, the two one-way links included), edge costs 8..69 | `$22afa` in c_s30, counted by the script |
| island positions and names | `$4d41a` (x, y), `$4d184`; economy.md 1 (the tables are identical in c_s30 and c_mv) |
| enemy islands 49, 50, 52..56, 63; the player holds only VULCAN 0 | `$69b40` in c_s30; economy.md 2 |
| "hypothetical ownership": every island free in c_s30 poked to the player (56 player islands) | choice made for the figure; labelled in panel A |
| a link is on only when both ends have the same owner; a free island's links are all off | `$21f9e` read; the port's bits equal c_s30's bits on every link |
| edge cost = the packet timer for that hop, in economy ticks | `$22126..$2212a`, `$223fa..$223fe`; drive: decrements between hops equal the cost, 14/14 and 14/14 |
| route OBSIDIAN 46 to VULCAN 0: 46 42 39 30 29 28 27 25 18 15 11 9 5 1 0, 14 hops, cost 227 | port; drive `route_late` 14/14 hops, landed |
| with STAVROS 28 free: 46 42 39 30 34 31 61 62 17 15 11 9 5 1 0, 14 hops, cost 300 | port; drive `route_cut` 14/14 hops, landed (ownership poked from the start, not changed mid-route) |
| freeing DUESSA 5 instead cuts 47 more player islands off VULCAN | port: islands with `M[k][0] = $ffff`, excluding 5 itself and TREASURE 51 (already isolated) |
| next hop: among enabled neighbours strictly closer to t (`M[j][t] < M[u][t]`), the one with least `M[j][t] + c`; first wins a tie | `$22192` read |
| no hop: an item packet (pool 2) is discarded; a resource lot (pool 1) is added to the current island's stock | `$223f8`/`$22406`; `$22124`/`$22130..$22154` read, not driven |
| a packet on a free island is discarded; packets wait with timer 1 while `$122f` is set | `$220f6`, `$223c4`; `$22102`, `$223d8`; drive: 4 timer-1 retries at `$22496` before the first hop |
| matrix `$67b40`, 64 x 64 words; reset to `$ffff` with diagonal 0 | `$21e16` read; dumps before call 1 |
| 8 rows per call, in place; after 8 calls a full sweep; repeat while `$122e` was cleared; then clear `$122f` | `$21e8a` read; drive: `$122e`/`$122f` equal the port's before every call |
| one call per main-loop pass while `$122f` is set | `$39c0..$39c6` read; drive: median 71,999 steps (c_s30 owners) and 83,997 (late owners) between calls |
| panel B frames: 64, 100, 1182, 1641, 2709, 3098 finite entries at reset and after 1, 8, 16, 48, 113 calls | port, equal to the emulator dumps at those calls |
| late ownership: last change at call 113, `$122f` cleared at call 128 (16 sweeps) | port; drive `fill_late` matches all 129 dumps (before calls 1..128 and the state after 128) |
| 3098 = 55 x 55 (VULCAN's component) + 1 (TREASURE 51 alone) + 8 x 8 (enemy) + 8 (column 4 of the enemy rows) | counted from the final matrix |
| matrix equal to the port in every dump: see the "Checked" line; c_s30's converged matrix equals the port's 4096/4096 | script, from the logs and the snapshot |
| the stray 500: `$1817e` writes `#$1f4` to `8(A0)` with A0 = `$69ac0` | `$18170..$1817e` read; drive: the watch on `$69ac8` fired at pc `$1817e` between the 7th and 8th calls in both fill runs |
| "distance-vector routing (RIP's Bellman-Ford)" | interpretation: each row is relaxed from its neighbours' rows, which is the Bellman-Ford update RIP uses |

### Prose added for readers new to the game (lead, captions, "How we know")

| claim | source |
|---|---|
| player's and computer's carriers compete for a 64-island archipelago; held islands form a supply network | README.md opening paragraph; economy.md 3 |
| goods travel as packets island to island; no route stored; a few rows of the table per main-loop pass | economy.md 3, 4 |
| distance-vector routing, as in RIP | economy.md 3 ("Bellman-Ford, as in RIP"); "early internet routers" is general knowledge |
| a link is usable only when both ends share an owner; capturing cuts the other side's routes | economy.md 3 |
| VULCAN 0 is the player's base | economy.md 3 (row 0 is read by the island panel as "DISTANCE TO BASE"); README.md (`c_s30`, carrier at Vulcan) |
| economy tick: the economy chain runs every 4th main frame | economy.md 4 (`$f254`, countdown `$982`) |
| `$122f` described as the "busy" flag packets wait on, timer held at 1 | economy.md 3; drive (4 timer-1 retries) |
| 3098 split as 55 x 55 + 1 + 8 x 8 + 8 | table above; "which no link reaches" for TREASURE 51 is economy.md 3 ("nothing can route to it") |
| "one sweep is not enough, because a row can only copy distances its neighbours' rows already hold" | generic property of in-place Bellman-Ford relaxation; the call counts are the port's, checked by `fill_late` |
| a packet stores node, timer, item, quantity, destination | economy.md 4 (pool 2 layout) |
| proven / inferred labels | ai.md opening "Proof labels", which economy.md follows |

## Flags

- **`$1817e` writes into the distance matrix (inferred bug).** In the island tick, `$1814a..$18158` set `+2 = 500` and
  `+8 = +10 / 4` on the record at `$8c4` (only when `$8d8`, instant build, is set), then for an enemy island that row 63
  can reach, `$18170` reloads A0 with `$69ac0` and `$1817e` stores 500 at `8(A0)`: `M[63][4]`, not the island's `+8`.
  This runs at normal speed too (the `beq` at `$18148` skips only the first two stores). Evidence: c_s30's matrix differs
  from a clean relaxation in exactly 8 cells, column 4 of the enemy rows, each `500 + M[i][63]`; with `M[63][4] = 500`
  the port matches 4096/4096; the watch caught the write live. Effect: the enemy rows read CHARISSA 4 as reachable at
  500+, which `ai.md` 2's row-63 scoring would see; not checked there. The intent (500 materials for enemy islands
  connected to NEMESIS) is inferred.
- **Pool-1 no-route clamp looks wrong.** `$22142..$22154`: stock + lot over the cap stores `4(A0)`, the packet's
  destination, as the stock, where `4(A1)` (the cap) is expected. From code, not driven.
- **economy.md 3, "bit 15 set when the edge is disabled":** the bit is on the neighbour word of the (cost, neighbour)
  pair (`$21ea6`/`$21ea8`, `$21fd2`/`$21fd8` on `(A0)` = pair + 2); the index is masked with `$3fff`.
- **Two links are one-way:** NAIADES 15 lists BEACON 16 but not the reverse, and TREASURE 51 lists FEARS EDGE 52 but
  not the reverse. TREASURE's only link is that one, so it can send but nothing can route to it. Not in the doc.
- **economy.md 3, "SPLINTER (38) hangs alone off ENDYMION (36)":** true (one link, cost 69, the dearest in the table),
  but nine islands have a single link (6, 13, 22, 38, 44, 51, 58, 59, 60). Degree counts: 1: 9, 2: 20, 3: 24, 4: 9,
  5: 1, 6: 1, so "most have two or three" holds (44 of 64).
- **economy.md 3 labels the relaxation and routing from code;** the drives here are emulator checks of both (matrix
  per call, two packet routes hop by hop and their dwell times). The doc's proof table does not list them; the drives
  poke ownership rather than play it.
- **Who calls `$21e16`:** world creation (`$3c32`) and four ownership-change sites (`$184c4`, `$1adc0`, `$1c0a4`,
  `$1c280`, each beside the "is now a friendly / enemy / free island" messages). `$3b8a` calls `$21f9e` alone. The doc does
  not say a capture triggers the rebuild; read from code, not driven.
- **Proof label of the stray write differs between docs.** `economy.md` 3 and this figure call it an "inferred bug";
  `ai.md` 2 heads the same write "A probable game bug (proven)", on the strength of the s6a/s6b pokes that change the
  enemy's target as the model predicts. The write itself is observed live here; "bug" and its intent are the
  inferred part. The figure keeps "inferred".
