# span.svg: facts and sources

Figure: `gen_span.py` writes `scratchpad/carrier/infographics/span.svg` (PNG: `rsvg-convert -z 2 span.svg -o span.png`).
Tables, opcodes and the palette are read from `c_s30.snap`. The script runs the emulator once and caches its raw
output in `span_emu.json` beside the SVG (`--emu` re-runs it): `callcap $494c` for all 64 colour codes, then
`callcap $4678` on 2183 rows (the rows the figure draws plus 2048 verification rows on a random background). Every
pixel drawn is an emulator output row; each is compared with `span_gate.py`'s model (copied into the script).
Doc: `render.md` section 5.

| fact in the figure | source |
|---|---|
| low resolution: 16 pixels per four plane words, bit 15 leftmost, colour bit p in plane p | ST hardware; the panel A words are the emulator's output row |
| colour 9 over colour 6, screen x 37..74: words $07ff/$f800/$f800/$07ff, $ffff/0/0/$ffff, $ffe0/$001f/$001f/$ffe0 | callcap $4678, D1=5 D2=42, row poked to colour 6 |
| left keep mask $4658[5] = $f800, right $476c[10] = $001f | tables read from the snapshot; indices are x & 15 for x = 37 and 74 |
| viewport offset 32, width 256 | the block at $3fea that $6fc points to and A3 holds in the snapshot: (A3) = 32, 16(A3) = 256 |
| middle words written by `move.l A0,(A4)+ / move.l A5,(A4)+` | `disassemble.py --all 4678 48b0` |
| solid: $46c0 := $69 (bvs); 16-byte entry of $49e4 gives four opcodes to $46e8 and $4758, then A0, A5 | `disassemble.py --all 494c 4ae4`; bytes from callcap $494c, codes 0..15 |
| $8D5C = or.w D6,(A4)+ sets, $C75C = and.w D3,(A4)+ clears; opcode k serves plane k | disassembly of $46e8 and $49e4 |
| bvc always taken, bvs never: add.w (A3),D3 adds 32 to 0..255 | from code ($46be..$46c0) |
| dither: $46c0 := $68; $47b4/$47ba = $4b64[c1] + $4ae4[c2]; $47c2/$47c8 the same with each word ror 1 | `disassemble.py` $4968..$49ba; callcap bytes for all 48 dither codes |
| code 32 = colours 1 and 10: $5555aaaa, $0000aaaa, $aaaa5555, $00005555 | callcap $494c D0=$20 |
| pair chosen by bit 0 of D7's high word plus one; the high word is the screen row | from code: $46a0..$46a2 and $47ac; $4598/$45b4 set D7.hi to the row A6 is built from ($1248 + 160 y) |
| 48 dither pairs, codes 16..63; codes 0..15 are equal pairs | `$1544` read from the snapshot (asserted) |
| patch bytes from callcap equal the table derivation | 64/64, computed in the script |
| widening rule xr' = max(xr, prev xl'), xl' = min(xl, prev xr'); $9ee := xr', $9f0 := xl' | `disassemble.py` $4680..$4698; render.md 5 |
| $494c sets $9ee = $7fff, $9f0 = $8001, so the first row is unchanged | $494c..$4952; all 64 callcaps write these bytes |
| two slivers stepping 3 and 4 pixels a row; widened rows 16/16 match | each row a callcap with $9ee/$9f0 poked to the previous row's model result |
| span_gate.py 780/780 rows, 0 tracker mismatches | re-run in this session: `uv run python -I py/render/span_gate.py` |
| all rows 2183/2183 equal the model, $9ee/$9f0 2183/2183 | computed in the script; negative control: flipping the phase and dropping the widening in the model drops it to 531/2183 |
| widening is to close gaps on steep edges | inferred (render.md 5 says so) |
| "most-called routine in the game" | render.md 5 (2079 calls per 1.2M steps); not recomputed here |
| colours | shifter palette registers in c_s30.snap (strategy screen) |

### Prose added for readers new to the game (lead, captions, "How we know")

| claim | source |
|---|---|
| filled-polygon 3D on an 8 MHz 68000 with no FPU or blitter | render.md intro |
| most-called routine, 2079 calls per 1.2M steps (written as "1.2 million emulated instructions": a step is one instruction, `instructionsPerFrame` in `Program.fs`) | render.md 5 |
| `$494c` patches opcodes, branch and immediates per colour; 16 solid, 48 dithers | render.md 5 |
| ST low-resolution bitplane layout, 16 colours | ST hardware, general knowledge (as the row above) |
| interior groups are two longword stores (A0 planes 0-1, A5 planes 2-3); edges masked | render.md 5 |
| 8D5C = or (set), C75C = and (clear); plane 0 first | table above |
| "the filler never decides anything per pixel or per word" | reading of the patched code: the edge and middle paths contain no colour test (render.md 5, disassembly rows above) |
| bvs never / bvc always, because the add cannot overflow | render.md 5 |
| phase from the screen row, pattern fixed to the screen (from code) | render.md 5 |
| widening rule proven, purpose inferred | render.md 5 |
| c_s30 is a Strategy game in progress | README.md snapshot table |
| control 531/2183 | render.md 5; `gen_span.py` |

## Flags

- render.md 5 does not say what D7's high word holds. `$4598`/`$45b4` load it with the screen row used to build A6, so
  the checkerboard is anchored to screen x and y, not to the polygon, and adjacent faces in one dither meet in phase
  (from code, not driven).
- render.md 5 does not say who initialises `$9ee`/`$9f0`: `$494c` writes the sentinels `$7fff`/`$8001` on every call.
  It also does not say that the stored ends are the widened ones (the chain compares with the previous widened
  span, not the raw one); the gate's tracker check models it that way.
- The `bvs`/`bvc` patch works as branch-never/branch-always because the preceding `add.w (A3),D3` cannot overflow;
  the doc names the opcodes but not that trick.
- The doc's ranges `$46e8..$46ee` and `$4758..$475e` name the last word's start; the patched bytes run to `$46ef`
  and `$475f`.
- `span_gate.py` covers 10 of the 64 codes; this script's 2048-row set covers all 64 (no mismatch). The doc's
  780/780 stands as stated.
- The palette is the one in the shifter at the anchor snapshot; whether the 3D view uses the same palette was not
  checked.
