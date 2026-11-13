# trail.svg: facts and sources

Figure: `gen_trail.py` writes `trail.svg` to `scratchpad/captive/infographics/` (PNG:
`rsvg-convert -z 2 trail.svg -o trail.png`). Run from `M68000/` with
`uv run python -I reversing/captive/py/infographics/gen_trail.py [--emu]`; its printout is kept in
`scratchpad/captive/infographics/gen_trail.out`. Emulator results are cached in `data/trail_emu.json` and `data/track_end.snap` (`--emu` re-runs them, about 10 s). Docs:
`reversing/captive/ai.md` "Summary", "Map planes", "Decision rule", "The trail"; `mapgen.md` "Floors and lifts",
"The flow field (plane 2)". States: `agents/ai/req4.snap` (party at the entrance, before moving), `p14.snap`
(after E, E, S), `p2.snap` (after four more S), `g16_adj.snap` and the cached `data/track_end.snap` (p2 + 200 samples),
natural base `base1/in.snap`.

| fact in the figure | source |
|---|---|
| base map: 579 open cells in rows 0-14 of the 64 x 32 grid `$1d9e8`; block floor table `9206(A6)` = 1,2,2,2 / 6,2,2,6 / 6...; entrance column word `9238(A6)` = 12 | read from req4 (mapgen.md "Floors and lifts"; 6 = outside) |
| arrows in A = plane-2 `$1e208` bits 0-2 (dig tree); colour = where the walk ends: lift (24,3) value 5: 449, lift (2,4) value 4: 11, entrance (12,0): 74, a wall: 45; longest walk 68 | per-cell walk in gen_trail.py, asserted equal to `field.py req4.snap`'s Counter (exec'd) and to 449/11/74 |
| dashed rings: lift partners (24,3)-(8,3) and (2,4)-(18,4); through the lifts all 534 reach the entrance | **inferred**: partner = the cell at a block offset on the other floor with lift tile `$31`/`$34`, one candidate each (mapgen.md "Lift offsets"); the through-lift walk is the dig path, not creature behaviour (a creature forgets on 4/5) |
| bits 3-5 equal bits 0-2 except 22 bytes, all with bits 3-5 = 0, 13 of them open | computed on req4 (ai.md "Map planes": 2026 of 2048) |
| party path (12,0) E E S S S S S to (14,5); footprints p14 = 3,3,2, p2 adds 2 at (14,1)..(14,4) | plane-2 diff req4/p14/p2; party `26/28(A6)`; ai.md "The trail" (proven there by `walk.py`, writers `$9332`/`$9336`) |
| 5 of the 6 footprints off the entrance are the dig arrow reversed | computed: footprint = (bits 0-2 + 2) & 3 |
| a mark is the travel direction, not the facing: two E marks while facing `30(A6)` = 2 (S) | computed from req4/p14 (the party strafed, `keys.py` `$6a`); the code reason ($9320-$9336 writes `1764(A6)` & 3, facing + move offset) is the coordinator's reading, not re-checked here |
| catchment of the party's cell (walk on bits 3-5 that stops at the party): 75 in req4 at (12,0), 75 in p14 at (14,1), 75 in p2 at (14,5); the other cells 433 lift (24,3), 10 lift (2,4), 61 wall | computed, asserted; the 75 orange cells in B are the cells that drained to the entrance in req4 (set equality asserted) |
| marks never fade: 0 of 2048 bits-3-5 values differ after 200 samples x 60,000 = 12,000,000 steps | computed p2 vs g16_adj.snap and vs `data/track_end.snap`; bounded to that window, party standing still |
| group 16 (type `$e`, aware, hostile): moves at samples 4, 22, 40, 58, 76: (13,4) step N, turn E, step E to (14,3), turn S, step S to (14,4); then at (14,4) for 124 of 200 samples | **proven**: `track.py p2.snap 200 7` re-run (`--emu`), parsed and asserted |
| reason per move: trail N, trail E (both cells dig-tree values, unchanged since req4), sees P 2 away at (14,3) | gate_decide.py's `model()` on each pre-move state (cell byte from p2, `$10b2c[$e]` = 0 so no attack options); the label set over six RNG values is a single label that matches each move |
| "the rule: attack" while adjacent | model; **inferred** that an attack happens (not observed) |
| sight cross: 23 cells (row -1 off the map), 8 wall, 4 open ones on floor 2 | computed on p2 around (14,5) |
| group 43 at (16,5) at sample 67, not aware; wall (15,5) between | track.py output (flags field `-----`); WANDER for unaware is the gate model |
| gate: 3000/3000 on p2, labels WANDER 1231, TURN 659, FORWARD 422, BEHIND_TURN 257, FORGET 202, SPECIAL 95, ATTACK 68, TURN_ATTACK 66 | **proven**: `gate_decide.py p2.snap 3000 2` re-run |
| natural base 3000/3000; control (`dy > 5`, `rng < $31e0`) 2974/3000 | `gate_decide.py base1/in.snap 3000 2`; control exec'd with those two source replacements on p2 |
| split by branch: sight FORWARD 99, ATTACK 68, TURN 273, TURN_ATTACK 25, BEHIND_TURN 165; trail FORWARD 323, TURN 386, TURN_ATTACK 41, BEHIND_TURN 92, FORGET 202; WANDER unaware 1095, relentless 102, same cell 34 | the gate's own 3000 trial inputs, recovered by running its `main()` against a stub server (asserted: the model's tally on them equals the emulator's tally), split by the model's branch. The labels are proven; the split is the model's |
| sight trials 630, 282 with a wall between, 82 across floors | same recovered trials, walls and floors from p2: the no-wall-test claim is proven on these 282 |

## Flags

- `py/ai/README.md` row "`field.py ... trail` ... after the party moved" runs on `req4.snap`, where the party has not
  moved (party at (12,0), no footprints). ai.md "The trail" repeats it ("433, 10 and 75 after the party's first
  steps"). On `p14.snap`/`p2.snap` field.py reports those 75 as `loop`: field.py does not stop at the party's cell, and
  the party's own cell (14,5) still holds the dig arrow N, a 2-cycle with the footprint at (14,4).
- "74 at the entrance" (bits 0-2) / 75 (bits 3-5) is also the catchment of the party's cell, because in req4 the
  party stands on the entrance; that catchment stays 75 as the party walks (the coordinator's finding, recomputed
  here). ai.md presents the entrance as a sink in its own right.
- ai.md's natural chase calls (14,3) "the party's own breadcrumb", which is true, but group 16 decides there by sight
  (dx 0, dy 2), not from the byte. Its two trail steps read (13,4) = 0 and (13,3) = 3, both the dig tree, unchanged
  since req4. The chase demonstrates trail-following of the dig tree; no observed chase yet reads a footprint.
- ai.md lists only 449 + 11 + 74 = 534 walk ends; 45 of the 579 open cells' dig arrows end against a tile-0 cell, and
  22 plane-2 bytes have bits 3-5 = 0 with bits 0-2 nonzero (9 on tile 0, 13 on tiles `$02`/`$04`/`$08`). The doc
  gives the 2026/2048 count without saying what the 22 are, or that the tile grid and the dig tree disagree.
- Sight crosses floors: floors are blocks of one grid, so the row/column test reaches through the block wall into
  another floor (82 of the 630 sighted gate trials; 4 open cells of floor 2 in the party's cross in p2). ai.md says "no
  wall test" only. That floors are separate levels is itself inferred (mapgen.md), so the "creature on another floor
  sees you" reading is inferred.
- README: the natural-base row says its control gives 2975/3000; the control row on p2 says 2974. Only the p2
  control was re-run here (2974).
- `track.py`'s `s.close()` sits inside the trailing comment on its last line, so it never closes stserver itself
  (the process ends with the script).
- Not drawn, not checked here: the coordinator's code readings that `$88b8` latches the party cell's byte into
  `1766(A6)` and that the lift path (`$9768`/`$977c`) writes no footprint.
