# digger.svg: facts and sources

Figure: `gen_digger.py` writes `digger.svg` to `scratchpad/captive/infographics/` (PNG: `rsvg-convert -z 2 digger.svg
-o digger.png`). Run from `M68000/`: `uv run python -I reversing/captive/py/infographics/gen_digger.py` (about 3
minutes; it prints every number it draws, log in `scratchpad/captive/infographics/gen_digger.out`). The emulator's
flow field for the seed is cached in `data/seed5.json` (remade by `gen.py` when missing). `DIGGER_CACHE=1` reuses the
corpus numbers of the previous run (`data/corpus_cache.json`) for layout work only. Doc: `reversing/captive/mapgen.md`, sections "Floors and lifts", "The digger and rooms", "The flow
field (plane 2)". Port: `reversing/captive/py/mapgen/digger/dig.py`, used unmodified; the script subclasses it to
observe calls.

Seed: base 5 (D0 = 5, D1 = 0, D2 = 1, D3 = 0), the record in `scratchpad/captive/mapgen_digger/d2_1_0.bin`. The script
asserts the port's whole module block after `$244b6` (13,756 bytes: G0, G1, G2, room list, RNG words, every variable)
and D1-D7 equal the emulator capture byte for byte.

| fact in the figure | source |
|---|---|
| 3 floors over 12 blocks, entrance column 23 on floor 1, lift offsets (16, 24) and (16, -8) | port block, module bytes 0..55 (mapgen.md "Floors and lifts"); agrees with `zones.py model 5` |
| panel A colour = G0 carve number, 1..2392; final D4 2393 | port block G0 = emulator capture; mapgen.md "The turtle" (`$24f3c`) |
| 914 carves: 510 corridor, 202 room (17 rooms), 188 blob (10 blobs), 10 lift ends, 3 shaft, entrance twice (#2); 915 carved cells, 2 pre-placed shaft cells | port carve calls by routine (`Traced.carve`); pre-placed = carved cells the port never wrote |
| 10 lifts, each pair drawn from near end to far end | `Traced.lift` successes; every pair's difference equals the floor pair's offset |
| the dig ends on its restart budget | `dig.run()` return; mapgen.md "End" |
| whole generator call 3,830,954 instructions | `gen.py data/seed5.json 5,0,1,0` (emulator, stserver), `steps` |
| B: turtle on (21,3) #2280 tests (21,4): 2 of 4 uncarved (also touches (21,5) #489), refused; the retry tests (22,3): 3 of 4, carved as #2281 | `Traced.count` after each step, grid copied at that moment; the turtle's position is the saved one (`48`/`50(A6)`); proven by the gate (port = emulator) |
| B: 368 of the 2,702 carve tests after a step pass | same; the other passes come from the restart path (`$245a8`), which is not counted here; failed tests include the test that follows every room and blob |
| C: low 3 bits 0/1 turn; 2/3 with word > `$ccb0` lift; else <= `$7ad` blob, <= `$8f48` room, else forward | `dig.py` `step` (`$24872`); mapgen.md "Each step" |
| C: chances 25.0% turn, 39.7% room, 28.0% forward, 5.0% lift, 2.2% blob | computed from the band widths (3.00%, 52.97%, 23.99%, 20.04%) and the selector split, assuming a uniform word |
| C: 520 fresh words; seen 123 turn, 207 room, 146 forward, 30 lift, 14 blob; expected 130.0, 206.6, 145.7, 26.1, 11.7 | `Traced.step` with D7 = 9 (a fresh word, `$244f4`) |
| C: 1,761 retries; retried room words: 434 calls, 0 rooms; corpus 626,856 retried room calls, 0 rooms (274,740 first-try room words gave all 25,771 rooms) | port over the 1000 D2 = 1 captures, each asserted equal to the emulator |
| C: retried lift words made 6 of the 10 lifts (3 on a fresh word, 1 from a restart) | `Traced` |
| C: 578 restarts | decrements of the restart counter `12414(A6)` (431 of them restart lift attempts, `$2458a`); 270 in-bounds lift attempts gave the +1s (300 + 270 - 578 = -8 at the end) |
| D: emulator G2 = model on 915/915 open cells | `flowfield.model` on the port's post-digger grids vs G2 from `gen.py` (final, after all stages) |
| D: arrows lead from all 915 open cells to the entrance; longest walk 115 steps; summed over all 915 walks, 3 steps go to a higher number (that these are lift or shaft steps is inferred, not checked) | walk of the emulator's G2, lifts through the floor offsets |
| D: window cells (17..31, 0..6); entrance G2 0 (north) | same |
| E: forests 0/1000 raw, 819/1000 rooms and blobs contracted (232 cycle edges: 228 blob next to a shaft cell, 3 corridor next to a shaft cell, 1 corridor next to corridor), 503/1000 with lifts and shafts as edges; one component in every base | `digger/tree.py` census run by the script on the 1000 captures, parsed from its printout; equals mapgen.md "Loops" |
| E: base 5 has 0 cycle edges contracted, 0 with lifts (156 raw) | the census's graph and contraction, applied to base 5 |
| creatures follow the field | **inferred** (mapgen.md "Use in play", ai.md) |

## Flags

- mapgen.md's caption "a five-block base" under `mapgen_base_d0_5.png` is wrong or unclear: D0 = 5 has 12 blocks on
  3 floors (`zones.py model 5`; mask `$fff6` marks 14, two leftovers became 6). "D0 = 5" is the only reading that holds.
- `dig_capture.py`'s per-record step count is not the digger's instruction count: seed 1 records 124,841,478 where
  `stages.py` gives 1,708,805 for `$244b6` (D0 = 1, D2 = 1), and seed 5 records 141,752,663 while gen.py's whole
  call takes 3,830,954. The README does not use the field; it should be fixed or dropped. Not drawn.
- mapgen.md "Each step" does not give the selector values (0/1 turn, 2/3 lift up/down, 4..7 fall through to the size
  test), and its lift bullet omits that the lift needs selector 2 or 3; `dig.py`'s docstring has them.
- New, not in mapgen.md: a retry keeps the word and redraws only the selector, and a retried room word never carved a
  room in 626,856 retries over the corpus. A non-turn selector repeats the same check from the same cell and heading,
  so it fails again (the reason is inferred from the code; the count is from the gated port). Retries help only via a
  turn or for lift words. Worth a sentence in "Failure and restarts".
- mapgen.md "Failure and restarts" calls the 300 a "budget of 300 restarts", but each in-bounds lift attempt adds 1
  back; base 5 used 578 restart decrements. "Restart counter" with that note is accurate; "300 restarts" is not.
- "Each arrow therefore points one step down the dig order": room cells are numbered in rows with gaps (D4 + 8r, +2
  per cell, +8 per pillar) and blob walks revisit cells, so arrows descend the carve number, not strictly the dig
  path, and over all 915 walks in base 5, 3 steps go uphill (inferred: lift or shaft partners). The claim that every cell
  reaches the entrance holds (915/915 in base 5).

## Explanatory text (lead, "How to read", "Takeaway", "How we know")

| claim in the added text | source |
|---|---|
| Captive is a real-time dungeon crawler; four droids raid bases on a series of planets | `README.md` opening paragraph |
| each base is computed by `fed_MapGen` from a 16-bit base number D0 and a mode D2; the same pair gives the same base; the Python port from (D0, D2) alone reproduces the output in 400 of 400 bases | mapgen.md opening ("The whole base is a function of two arguments", **Proven** 400 of 400) |
| the turtle has a position and a heading, draws one random word per step and turns, moves, or makes a room, blob or lift | mapgen.md "The digger and rooms" ("The turtle", "Each step") |
| blob = looped cave | mapgen.md "Blobs" ("Result: a looped cave") |
| 3-of-4 rule: a corridor never breaks into another passage; per floor the corridors are a perfect maze (one route between two corridor cells: the definition of a perfect maze / tree) | mapgen.md "Carve rule", "Loops" (last line); "perfect maze" and "tree" are the standard definitions |
| grid of 16 blocks of 16 x 8, each on one floor or outside (6) | mapgen.md "Floors and lifts" ("Blocks") |
| a lift keeps its position within its block, on a neighbouring floor; the turtle digs on from the far end | mapgen.md "Lift offsets", "Each step" (stands on the far end) |
| a shaft is a chain of entries on consecutive floors laid out before the dig; its door is opened when a corridor reaches it | mapgen.md opening bullets, "Shafts and reservations", "Opening shafts" |
| 2392 highest carve number | generator printout (`maxn`), already in the legend |
| chance combines bands with the turn test on the low 3 bits (2 of 8 values) | `dig.py` selector, Flags below (selector values 0/1 turn) |
| a retry keeps its word and repeats the same check, so a room that fails once is never built | this file, "Flags" (626,856 retried room calls, 0 rooms); mapgen.md "Failure and restarts" |
| carve number falls along the arrows at every step but 3 (inferred lift or shaft steps), down to the entrance #2 | mapgen.md "The flow field (plane 2)"; table row D above; `g0[ent]` = 2 |
| forest, E - V + C = 0, V cells, E same-floor adjacencies, C pieces | mapgen.md "Loops"; the equivalence with "no cycle" is standard graph theory |
| loops come from rooms and blobs and shafts; lifts and shafts add routes between floors | mapgen.md "Loops" |
| port = register-level translation that must leave the whole 13,756-byte block equal; gate 1000/1000; control 2 of 4 gives 0/1000 | mapgen.md "The digger and rooms" ("Proof", "Controls"); 13,756 from this file's header |
| G0 holds carve numbers, G2 the arrow | mapgen.md "Carving" (`$24f3c` writes D4 into G0), "The flow field" (value into G2 byte 0) |
| a step / instruction count is 68000 instructions run by the emulator | emulator convention (`DEVELOPING.md`) |
