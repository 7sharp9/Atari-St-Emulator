# dither_infographic.html: facts and sources

Page: `reversing/powermonger/dither_infographic.html`. Its builder is `py/dither_atlas.py`, which needs the RAM images
`scratchpad/pm78_settle.ram`, `pm122/agents/dissolve/nat2/k5_x1.ram`, `pm121/cap/k5_22_{0..3}.ram`, `pm74_late.ram`
(no emulator run) and also rewrites `dither_atlas.png` / `dither_triangles.png`. In this pass the page was produced by
the builder's last step only: the template with `__DATA__` replaced by the cached
`scratchpad/pm130/dither/dither_data.json` (checked first: the committed page was byte-identical to that splice).
Docs: `reversing/powermonger/graphics.md` (G), `README.md` (R), `strategy.md` (S), `port/SPEC.md` (P).

| fact on the page | source |
|---|---|
| PowerMonger, Bullfrog / EA 1990, ST; orders to a captain and men rather than steering | R title paragraph; R "What carries the game" |
| island is a height map, drawn in perspective in software, two triangles per cell, 16 yaw steps and zoom | G Summary, "`$fec6`" |
| two colour planes, 8 KB each, offsets 0 and -8257 from `$438ee`; both slope shades baked from altitudes by `$10058` | G "The model is a heightmap grid", "`$10058`" |
| shade 0..15 plus a base, land and coast bases differ | G "`$10058`" (land = shade + `$1f`, coast = shade + `$c` ...) |
| `$10058` proven 125219/125219 over 16 calls | G "`$10058`" (`py/maps/gate_maps.py`) |
| redraw once per tick at normal speed | G "`$f898`" |
| fill copies the same 8 bytes across the span, ends masked | G "`$ef62` -> `$e3e6` -> `$e420`" |
| no texture map, no light model, no palette cycling | G Summary |
| forced 0x1c: mostly back-facing at the mission-1 start pose; few dark pixels on the outline; other poses not measured | G "The `0x1c` override" |
| rock ramp nested ordered dither; grass five non-nested scatters, overlaps 0/32, 48/80, 64/128, 160/192 | G "Ramp structure"; expected-by-chance counts are the page's own `na*nb/256` |
| LCG `x = (x*$24a1 + $24df) & $1fff`, full period; row = x >> 4, bit = x & 15; rows < `$120` copy | P section 4 "Seasons"; S "What `$1abaa` actually is" |
| 4607 of 8191 non-zero values copy, about 9 pixels per call; "about 44 in 100" copy nothing = 3584/8192 | S "What `$1abaa` actually is"; arithmetic |
| pixel at x = 0 never copied; colour 2 in all season sources | S "What `$1abaa` actually is" (`py/season/pixel0.py`) |
| wrap advances the season | P section 4; G "Seasons" |
| "seven RAM images, five lands" for "no map checked" | G pattern-table row 0x04-0x0b |
| 100% on 27 captures from 12 views on lands 0, 5, 25, 60; fill byte-exact vs single-step, 128/128 `$ef62` calls, dither phase on two traced triangles | R "The world is drawn" evidence paragraph (around line 796) |
| builder refuses to build unless the rebuild equals the reference renderer and the fade reproduces pm74_late | `py/dither_atlas.py` docstring and asserts |
| 16 colours on screen; bit-plane layout | general ST knowledge, kept generic; layout also in G "pattern fill" |

## Notes

- Doc disagreement on plane letters: `graphics.md` (per-cell walk and "The land build") names `$438ee` (+0) colour B
  and `$418ad` (-8257) colour A; `ai.md` line 1514 names -8257 colour B and 0 colour A. The old page followed ai.md in its
  summary and legend. The page now names the planes by offset only (+0 / -8257), which both docs agree on.
- Stale framing removed: the old step 2 and the layer menu called the planes "type" and "height", and section 4 said
  the byte "rises with height". G says both planes are slope shades and that height enters only through the projection.
  The data keys (`src: "type" | "height"`) are unchanged; only the labels changed.
- `graphics.md` describes `$10058`'s band arithmetic as "code read, not checked cell by cell" in "`$f898`" but as
  proven 125219/125219 in "`$10058`". The page cites the gate.
- Forced triangles: the page's scene measures 51 of 128 forced with 12 pixels surviving (`pm78_settle.ram`, camera
  36,47); G reports 52 of 128, 3298 px drawn, 6 surviving at the mission-1 start pose (cam 36,47, yaw 15, from
  `probe.fsx`). Different captures and tools; neither number was changed.
- Section 5 says "16 steps per tick" and keeps "8191 steps, about 512 ticks"; P counts the wrap step too (8192 steps).
  Number not changed.
