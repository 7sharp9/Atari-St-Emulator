# octdist.svg: facts and sources

Figure: `gen_octdist.py` writes `scratchpad/carrier/infographics/octdist.svg` (PNG: `rsvg-convert -z 2 octdist.svg -o octdist.png`).
The error curve is computed from the game's integer formula; the heat map is `py/ai/score.py` run on
`ai/nat/d1.snap`, taken at the return of `$2337a` (`bp $1ad02`). Doc: `ai.md` sections 1 and 2.

| fact in the figure | source |
|---|---|
| distance = max(\|dx\|,\|dy\|) + min(\|dx\|,\|dy\|) / 2: `sub.l`/`bpl`/`neg.l` twice, `cmp.l D0,D1`/`bcs`/`exg`, `asr.l #1,D1`, `add.l D1,D0` | disassembly of `$233d2..$233ea` (`tools/disassemble.py --snap c_s30.snap --all 2337a 23520`); ai.md 2 |
| inlined, not a routine: three copies in `$2337a` (`$233d2`, `$23402`, `$234b6`) and one in state 1 for the travel countdown (`$1ad14..$1ad2c`, then `divu #$fa`) | same listing, and `--all 1acf0 1ad44` |
| exact on the axes; at most +11.80% at 26.57 deg (and 63.43); +6.07% at 45 deg; mean +8.68% over angle | computed: integer formula at radius 3,000,000 every 0.001 deg; agrees with sqrt(5)/2 - 1 = 11.803% at atan(1/2) |
| contour max + min/2 = R has corners on the axes and at (2R/3, 2R/3); comes in to 0.894 R | algebra (x + y/2 = R with x = y gives 2R/3); R / 1.118 = 2,683,281 for R = 3,000,000 |
| never short before truncation; `asr.l #1` loses at most half a unit | x + y/2 >= sqrt(x^2 + y^2) iff x >= 3y/4, true for x >= y; the integer form is short only for tiny vectors (e.g. (1,1) gives 1) |
| score = -oct/2048 (`asr.l #8`, `asr.l #3`), -15000 beyond 3,000,000 (`$2dc6c0`) | ai.md 2; listing `$233ec..$233fe` |
| +3000/+2000 free, -4000 own, +4000 network neighbour, base term, current island `$8001` | ai.md 2; score.py |
| model = game on d1: 64/64 words, first maximum 55 HADES (-4357) = `$11ba` 55; carrier at 56 KOUYATE | `gen_octdist.py` (asserts it); names from `c_mv.snap` `$4d184` (economy.md 1) |
| corpus gate 1344/1344 words, 21/21 targets | `gate_score.py`, re-run this session |
| in d1 every island within octagonal 3,000,000 is enemy-owned (49, 50, 52..55, 63); by true distance 48 is also inside | computed from island records `$69b82/$69b86` and carrier `$5f4a4/$5f4ac` in d1 |
| 48 TWILIGHT: true 2,929,444, octagonal 3,233,024 (+10.4%), scores -8271; with true distance it would score 5325 and be picked | score; counterfactual (score.py with the distance replaced by `isqrt`), **computed, not run in the game** |
| the game picks 48 on the next decision, from 55 | d2.snap / e3.snap: `$11bc` 55, `$11ba` 48 |
| panel D: model pick = game `$11ba` in all 11 of `ai/nat2/e2..e12` | `gen_octdist.py` (asserts it) |
| true distance changes 3 of 11 picks: e2 (48 past the cutoff), e4 (51: octagonal 3,040,768, true 2,752,325), e6 (46 nearer, 1,110,500 vs 1,144,186, but at 28 deg reads +11.8%, 47 at 83 deg +5.4%) | counterfactual, computed; **inferred** that the game would play differently, since nothing downstream of the pick was run |

## Flags

- There is no distance routine to give an address for. `ai.md` 1 writes `octdist(carrier, target)` as if it
  were one; the sequence is inlined four times (`$233d2`, `$23402`, `$234b6`, `$1ad14`). Other games' docs or
  `vehicles.md` ranges may have further copies; not searched.
- The "13 natural decisions" in `ai.md` 2's proof contain two duplicates: `ai/nat/d1` and `d2` equal `ai/nat2/e2`
  and `e3` word for word in the score table at `$232fa` and in the carrier entity. Distinct natural decisions are
  11. The 1344/1344 count is still correct as a count of words checked.
- The nat2 chain is not fully natural: `nat2/script.txt` pokes `w 11c0 00012000` before each leg, which sets
  the travel countdown to 1 and also writes `$11c2` (hull) to `$2000`. `$2337a` reads neither, so the scores
  are unaffected, but the arrivals are forced and the hull is reset each leg.
- The blog IDEAS entry's "at most 11.8% over (computed)" is confirmed; it holds for the real-valued formula. The
  integer form is exact on the axes only up to the dropped half unit.
