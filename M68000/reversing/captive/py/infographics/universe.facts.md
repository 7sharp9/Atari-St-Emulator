# universe.svg: facts and sources

Figure: `gen_universe.py` writes `universe.svg` to `scratchpad/captive/infographics/` (PNG: `rsvg-convert -z 2
universe.svg -o universe.png`) and prints every number it draws (`gen_universe.out` there). Run from `M68000/`:
`uv run python -I reversing/captive/py/infographics/gen_universe.py`. Doc: `reversing/captive/world.md` section 1;
model `reversing/captive/py/world/universe.py`. Inputs: `scratchpad/captive/mission1.snap` (index 0), `star.snap`, and
three callcap deltas in `scratchpad/captive/infographics/data/`, made with
`printf 'w 1ef86 000N0001\ncallcap 302c6 3000000 <dir>/cc_mN.json\nq\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/captive/mission1.snap repl --disk-a scratchpad/captive/tmb097.st`
for N = 1, 7, and the same without the poke for `cc_m0.json`. The script asserts every match listed as proven.

| fact in the figure | source |
|---|---|
| RNG `D0 = (D0 * $5e5 + $29) mod 65536`, output `D1 = ror.w #2` of D0 | disassembly `$3049c..$304a8` (`tools/disassemble.py --snap mission1.snap --linear 3049c 8`); world.md 1 |
| full period: 1509 = 4 * 377 + 1, 41 odd (Hull-Dobell for modulus 2^16); 65,536 steps from 0 return to 0, all 65,536 states visited | computed in the script (iteration) |
| bit k of D0 has period 2, 4, 8, 16, 32 (bits 0..4) | computed (4096-step sequence) |
| chain order seed -> `$30430` (2 discards) -> dots -> moons -> `$3037a/$3039e` (units) -> `$302fa` targets -> `$3032c` sites, D0 passed through | disassembly `$302ca..$302e4`; D0 saved over the unit conversion at `$302d6`/`$302e0` |
| mission 1 step counts: 2; dots 55 (3 zero-field, 1 duplicate rejected); moons 107 (7 duplicate); targets 9 (first forced, 0 occupied retries); sites 150; total 323, final D0 `$0057` | step-counting chain in the script, asserted equal to universe.py and RAM |
| missions 2, 8: 328 and 331 draws, final D0 `$c159` and `$079a`; mission 1 `$0057` | script chain; each equals the low word of D0 at the callcap return (`regN[0]` of cc_m1/cc_m7/cc_m0) |
| model = RAM 51/51, 100/100, 150/150 for indices 0 (snapshot and re-run), 1, 7 | script asserts (universe.py `check` on RAM with each delta applied) |
| output tables 13566(A6) = `$1eacc` (51 longs), 13770(A6) = `$1eb98` (100), 14170(A6) = `$1ed28` (150) | world.md 1; A6 = `$1b5ce` |
| dot fields x = D1 & 31, y = D1 >> 5 & 31, 0 rejected (`beq $30446`), through table `$3047c` | disassembly `$30446..$30476` |
| moon: parent planet 1 + (D1 * 50 >> 16), orbit slot D1 & 7 | disassembly `$303fc..$3042a` |
| target object D0 * 150 >> 16, retry on a used slot (`tst.l`), index 0 forces object 0 first | disassembly `$302fa..$3032a` |
| sites: planets (D0 & 31, D0 >> 5 & 31), moons ((D0 & 15) + 7, (D0 >> 5 & 15) + 7) | disassembly `$3032c..$30378` |
| cell to map units `c * 512 - $2600`; moon offsets +-160 on each axis from `$303d6` | disassembly `$3037a..$303d4`; table read from RAM |
| site byte 0 low nibble repeats every 16 objects 134/134; raw low bit alternates 149/149; planet byte 0 repeats every 32 objects 18/18 | computed on the mission 1 RAM table (raw = byte 0, minus 7 for a moon); follows from the bit periods above |
| panel B: 50 white pixels in the grid box; fit pixel = (66, 73) + 2 * cell puts 50/51 dots on white, the miss is dot 0 (station, cell (6, 6)), 0 white pixels unexplained | script: `tools/snap_render.py` of mission1.snap, searched fit (same method as starscreen.py) |
| target labels 1..10 at their planet; mission 1 targets 1 and 9 share planet slot 1 (BUTRE; 9 is one of its moons) | script (`tgt_by_planet`), objects from the model = RAM |
| panel C: table `$3047c` = {0,1,2,3,5,...,38}, skips 4, 9, ..., 34 (every value 4 mod 5) | RAM bytes, asserted |
| grid lines at pixel x 64, 74, ..., 144 and y 71, 81, ..., 151 = cells -1, 4, ..., 39, 9 each way | script: pixels of colour (180, 144, 108) with more than 40 per column/row in the grid box |
| 0 of 306 dot coordinates (missions 1, 2, 8) are 4 mod 5 | computed from the model dots (= RAM) |
| panel D: seed mission * 150 + object; LCG, `ror.w #8`, LCG, LCG; four nibbles low first index tables `$30706/$30726/$30746/$30766` (16 entries, 1 or 2 letters) | disassembly `$3066e..$306ea` |
| object 13: `$000d -> $4cca -> $ca4c -> $7225 -> $d442`; nibbles 2, 4, 4, d -> P AI CK OT = PAICKOT | computed; equals universe.py `name` |
| screen of star.snap shows PLANET-PAICKOT with 14782(A6) = 14 | rendered star.snap (crop embedded), RAM word asserted; **proven for this one name** |
| first names BUTRE, PHELSTER, SEMA, PEEGE, MIKER; 0 repeats among the 150 mission 1 names; 65,536 spellings | computed by the model, **inferred** (not read off the screen) |
| STATION fixed string at `$306fe` (D3 = 150 branch); PLANET-/MOON- by number at `$2ff6e` | disassembly `$30672`, `$306ec`; world.md 1 |
| panel E: the three maps drawn from the model tables, which equal RAM for each mission | script asserts |

## Flags

- world.md section 1 holds every finding the figure uses: the grid lines at cells -1, 4, ..., 39, the unused table
  entry 0, the 301-long clear, the short-period site bytes, the per-body name seed, the per-stage draw counts and the
  shared planet of targets 1 and 9. Whether the site-byte repetition is visible in play is not checked.
- Names use the same LCG constants as the generator chain but a separate seed per body, `mission * 150 + object`
  (`$30686..$30692`), recomputed on display; they are not drawn from the chain.
