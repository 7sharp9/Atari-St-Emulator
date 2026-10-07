# PowerMonger iso-renderer port

A Godot 4.x + F# port of PowerMonger's isometric terrain view: asset extraction, a
Python reference renderer, a porting spec, an F# logic library, a live Godot scene and a
frame stepper. Nothing here touches the emulator. The renderer reproduces the game's
frames pixel for pixel on the captures checked (`SPEC.md` Status); what is still open is
listed under "Status" below.

## Layout

| path | what |
|------|------|
| `assets/` | everything the iso renderer reads, extracted from a live RAM image. `manifest.json` gives one line of provenance per file. |
| `SPEC.md` | the porting contract: coordinate systems, projection with exact constants, the triangle/dither rasteriser, sprites, zoom, the frame pipeline, and what a modern port should replace. Written to be implementable without the disassembly. |
| `godot/` | Godot 4.x (.NET) + F# skeleton, **running live**. `godot/logic/Fill.fs` ports the closed rasteriser (`ef62_raster` + the `$e420` DDA + the dither fill) and all 4 yaw-quadrant grid walks (`planQ0`-`planQ3`, dispatched by `plan`/`walk`) at any zoom; `godot/logic/Season.fs` the seasons' grass colours; `godot/logic/Weather.fs` rain and snow; `godot/logic/Equipment.fs` the equipment exchange (`$160f8`, `$16892`) with its stale-register credit bug kept (`Original`) or removed (`Corrected`), gated by `../py/equip_check.fsx`, called by nothing yet because the port has no entity simulation; `godot/logic/Scene.fs` interleaves each cell's sprites after its triangles, as the game does; `godot/game/TerrainView.cs` wires it into a real scene — arrow keys pan the camera, PageUp/PageDown rotate it through all 16 yaw steps, Y cycles the season. |
| `stepper/` | Slow-motion replay of one frame in the game's own draw order, a triangle or sprite at a time (Mibo.Raylib, F# only, same `PmLogic` code). See "Frame stepper" below. |

## Status

Done: the projection, the rasteriser and all four yaw-quadrant walks (F# `Fill.fs`, byte-exact
against the Python reference and the game); sprites of every category seen on 37 lands, drawn
inline in the game's own order; seasons, rain and snow; zoom 1-7 in the logic library; the
HUD minimap; a Godot scene with panning, rotation and a season key; a stepper that replays one
frame a triangle or sprite at a time. 27 frames from 12 views on lands 0, 5, 25 and 60 match the
game's screen pixel for pixel, and terrain away from sprites matches at 99.7-99.96%
(`SPEC.md` §6 "Scoring a capture").

Open (the full list, with the reasons, is `SPEC.md` Status):

- Godot runs at zoom 4 only; the stepper and the Godot view do not draw weather; `Equipment.fs`
  is called by nothing, because the port has no entity simulation.
- Category `byte6` 18, 28, 34, 36, 38 and 42 were never seen drawn; `byte6` 6 has no established
  role; the plough and siege-engine overlays and the `$119b2` overlay are ported from the code but
  never seen on screen.
- HUD glyph sheet and compass panel are not decoded as assets; whether a territory change re-bakes
  the minimap is undecided.
- Dropping the per-pixel dither for a fragment-shader height ramp (`Terrain.flatPaletteIndex`, or the
  colour-byte table in `SPEC.md` §4), or a `SubViewport` instead of a scaled `TextureRect`, is optional
  and not started.

Scripts that exist only in the gitignored `scratchpad/` are listed once, in `SPEC.md` Status
("Scratch-only scripts"); the verification record below names them as scratch where it cites them.

## Frame stepper

```
cd stepper
dotnet run                                   # window
dotnet run -- --selfcheck                    # replay == Scene.render: 16 yaws, zooms 1-7
dotnet run -- --playtest                     # continuous play sustains, loops, survives a
                                             # camera/season change, still pauses on a step key
dotnet run -- --export <dir> [cell|strip|shape]  # one PNG per chunk boundary (3x)
dotnet run -- --shot <png> <step> [g] [n] [w] [yN] [sN] [zN] [cX,Y]
                                             # window at a step, screenshot, exit:
                                             # yaw N, season N, zoom N, camera cell X,Y
dotnet run -- --assets ../assets_k60 ...     # any of the above on another export
```

Keys: P play/pause (continuous -- loops back to the start at the end of the
frame rather than stopping); Right/Left/Space one triangle or sprite (Space
steps forward, same as Right -- no need to press it while playing, since
playback already advances on its own); Down/Up one cell; PgDn/PgUp one strip
(one pass of the walk's outer loop, 2 x zoom cells); Home/End; `+`/`-` speed.
Any of Right/Left/Down/Up/PgDn/PgUp/Home/End/Space pauses continuous play, the
way scrubbing to a specific step should. W/A/S/D move the camera a cell; Q/E
rotate it; `[`/`]` zoom in/out (1-7, keeping the centre cell, as `$13f60`
does); Y the next season -- none of these pause continuous play, they just
rebuild the view under it and keep looping. G the projected corner grid; N
each cell's position in the walk;
B the `$78000` backdrop; C the rain/snow overlay (`Weather.fs`, `$1a856`),
kind picked by the current season (`Weather.kindForSeason`) and animated
through its 4-frame phase while on. It opens on the view `entities.json` was
captured in (mission-1 start: cell 36,47, yaw 15, zoom 4, season 2). The
records cover the whole map, so every camera cell has its sprites. Moving,
rotating or zooming flips the dither phase, as `$f898` does; a season change
does not.

`Replay.build` draws each `Scene.Step` on its own into a `Fill.Buffer.Logged()`
buffer, which records every pixel write in order (spans top row first, left to
right; sprite rows top first), so the frame can be rebuilt to any single pixel
and rewound freely. The ST writes 16-pixel words, so per-pixel playback is finer
than the hardware; the order of spans, rows and shapes is the game's.
`--export` frames go through `ffmpeg` for GIFs, e.g.
`ffmpeg -framerate 8 -i frame_%03d.png -vf "split[a][b];[a]palettegen=max_colors=32[p];[b][p]paletteuse=dither=none" out.gif`.

Regenerate the assets:

```
python3 tools/pm_export.py                 # -> reversing/powermonger/port/assets/
python3 tools/pm_render_ref.py             # rebuild a frame from assets/ alone, diff vs reference
```

`pm_export.py` reads `scratchpad/pm74_late.ram` (the settled mission-1 iso view;
regenerate per `../README.md` if it is gone) and a frame-dump record for the
live palette; `export_entities` reads `pm88_f1` (`--entities-ram`). `assets_k60/` is the
same export for land 60 (`scratchpad/pm120/k60_iso.ram`, built per `../README.md` "Driving a
later land"). `pm_render_ref.py` writes `assets/reference/render_from_assets.png`
(dither fill), `render_flat.png` (height-ramp fill), and `render_compare.png`,
reference terrain (top) over the frame rebuilt from `assets/` (bottom), and
prints the block-mean dE and the per-index distribution vs the reference.

## Verification record

Grouped by topic. Counts and scripts are as measured; `scratchpad/` paths are scratch only (see
`SPEC.md` Status). Planes are named as `../graphics.md` names them (`SPEC.md` §2).

### Terrain, rasteriser and quadrants

- `godot/logic/Fill.fs` is a 1:1 port of `tools/pm_render_ref.py`'s `walk_q*` / `ef62_raster` /
  `_fixed_slope` / `_dda_walk` / `dither_index`, cross-checked on synthetic triangles (every
  rasteriser path: general split, flat-top, the `$f134` reorder, the `0x1c` coast-force, the mid-vertex
  slope switch, water shimmer) and a synthetic 8 x 8-cell grid exercising both diagonal-selector
  branches: identical coverage counts and pixel-index hashes. `Terrain.Map`'s flag-plane accessor is
  `DiagonalSelector`.
- The three other yaw-quadrant walks (`Fill.walkQ0`/`walkQ1`/`walkQ2`, `Fill.plan`/`walk`
  dispatching as `$f97e`/`$f982` do) are live-trace-verified at a yaw in each range (the vertex
  assignment and the colour-plane choice at the first `$ef62` call after resuming to the settled PC)
  and cross-checked byte-exact against the F# port on synthetic data exercising every CLEAR/SET
  branch and both comparison directions (`scratchpad/pm83_synth_check.{py,fsx}`, scratch only). The
  entry points are `$f98e` / `$fa9a` / `$fbb4`; the `$f98c` / `$fa98` / `$fbb2` carried by older notes
  are each 2 bytes low.
- Live single-step of a quadrant-2 capture (`pm83_q2c`): all 128/128 `$ef62` calls of a frame match
  the game, the dither `A5` phase on two traced triangles and the `$e420` span endpoints of a 27-row
  triangle are byte-exact (`SPEC.md` §9).
- The camera-change dither phase (`[$ffa2]` flips by 128 at `$f8e4`, `Fill.withPhase`): three yaws of
  `pm88_f1` rotated in the emulator score terrain exact-index 43.5 / 46.7 / 47.1% without it and
  93.8 / 84.6 / 91.1% with it.
- The span walker draws rows `0 .. totalRows-1`. Drawing the extra bottom row puts a one-pixel line of
  wrong colour on every triangle (29 px per `pm88_f1` frame).

### The 64 px inset and the right-edge clip

`$ef62`'s own clip (`screenX <= 255`) runs on the raw `$3f364` vertex, before the +64 inset applied
later through the `$e420` draw pointer. `ef62_raster`/`_dda_walk` take an `x_inset` parameter so the
clip shifts with the coordinate space, and `TerrainView.cs` shifts at blit time: it reads the buffer at
`(x - 64, y)`, not `(x, y)`, which would draw the terrain 64 px too far left. A synthetic triangle
straddling the raw X = 255 boundary covers identical pixel sets in raw and inset mode up to the +64
shift (56/56), and a real GPU screenshot at yaw step 11 shows the silhouette shifting right by that
amount (`assets/reference/godot_screenshot_yaw11_q2_85th.png` against `godot_screenshot_yaw11_q2.png`).
The inset is a coverage fix, not an accuracy fix: the exact-index score of the poor `pm83_q*c` captures
does not improve with it, because their reference buffers are the problem (`SPEC.md` §9 "Ruled-out
causes").

### Sprites and the entity pass

The `byte6` dispatch, the frame formulas and the positions are in `SPEC.md` §6. Port side:
`Sprites.fs` (`EntityRec`, `EntityCtx`, `entityFrame`, `blitEntity`, `drawEntities`,
`drawEntitiesArr`, `frameForProp`, `propTileOffset`, `propJitter`, `propScreenPos`, `decodeFrameWord`,
`Sprites.recordJitter`, `Sprites.packedLerp`, `Sprites.placeEntity`).

- **Synthetic cross-check.** Against `pm_render_ref.draw_entities` on identical synthetic corners and
  record fields: 13/13 cases byte-identical, `byte6 ∈ {0, 4, 8, 14, 24}` (men with the `+0x40` armed
  gate and the melee-to-nothing case, props with the `r7 ∈ {0x0d, 0x0e}` special cases and the
  tile-set offset, animals, banners, and the `$1182a` centroid markers; scratch only).
- **Real record stream.** On the 53-record stream of `pm88_f1.ram` with its `$3f364` corners:
  2881/2881 covered pixels, `byte6 ∈ {0,4,6,8,14,24}`.
- **Entity export.** `tools/pm_export.py` `export_entities` writes `assets/entities.json`:
  `render_entities[]` (the whole map's `$47970` bucket walk with the signed `$51b66` offset and the
  record address, 276 records) and `entity_ctx` (the per-frame constants). `byte6 == 4` jitter depends on
  the camera window and is recomputed per frame (`Sprites.recordJitter` reproduces the 53 stored jitters
  at the capture camera). At two cells panned in the emulator (`scratchpad/pm119/pan_{e,w}`, scratch
  only) the exported records draw the same frame as each capture's own records (identical at `pan_e`;
  at `pan_w` one man had moved).
- **Inline draw order.** Each cell's sprites are drawn after its triangles (`Fill.plan` returns the
  walk as data, `Scene.steps` interleaves, `Scene.render` draws). Inline beats sprites-last on every
  captured frame, including three rotated in the emulator: `pm88_f1` 96.80% against 89.17% exact
  (measured before the later sprite and phase fixes; current scores are under "Later lands" below),
  and the game agrees with inline at 1159 of the 1178 pixels where the two orders differ.
  `pm_render_ref.py` draws inline too (a `_cell_done` hook per walk handler) and equals `Scene.render`
  on all 15178 drawn pixels of `pm88_f1` (`../py/parity.py`). The settlement building (`byte6 == 2`, the
  fort's keep) is part of this: `pm88_f1` scores 96.80% with it and 95.93% without.
- **Later lands.** Everything a later land draws is ported except `byte6` 18 and 28 (`SPEC.md` §6
  "Every category"). `Sprites.placeEntity` returns every frame a record draws, in order (these
  categories draw two to ten). `EntityRec` has `B15`, `B32`, `W18`, `Icons`, `B33`, `B44` and
  `pm_export.py` writes them (loaders treat them as 0 in older exports). `Sprites.packedLerp` is
  `$11f1a` word for word; without the borrow between the packed x and y halves about one sprite in ten
  is a pixel off.
- **All-pairs score.** With each snapshot's state scored against the screen in the *next* `$f898`
  snapshot, 27 frames from 12 views on lands 0, 5, 25 and 60 match pixel for pixel, water tick included
  (`scratchpad/pm121/allpairs.txt`, scratch only). The inline scores on the mission-1 captures are
  99.69-99.99%; `pm78_settle` stays 94.62% because its two buffers disagree.

#### Gates

| gate | result |
|------|--------|
| `order_test.fsx` (`SPEC.md` §6) | 99.99 / 94.62 / 99.69 / 99.97 / 99.92 / 99.81 |
| `baseline.fsx` | the 160 terrain hashes unchanged |
| stepper `--selfcheck` | 23/23 on `assets` and `assets_k60` |
| walkthrough `showboat verify` | clean |
| logic, stepper and Godot builds | build (the `pm118/` scripts are scratch only) |

### Seasons, pan, zoom, weather, a second land

- **Seasons** (`SPEC.md` §4 "Seasons"). `Season.fs` ports `$1ab60` and `$1abaa`; `Season.fading`
  reproduces the whole 16 KB table byte for byte on seven captures; the Hatari screenshots match the
  settled season 2 at 88-89% of terrain pixels. `assets/dither.bin` needs no per-season export: the live
  slots are recomputed from the sources it already holds. `dither.bin` (`pm74_late`) and `entities.json`
  (`pm88_f1`) differ in season state because the game is in a fade: `pm88_f1` is one tick into the
  fade into season 2, so it shows season 1's grass under season 2's trees.
- **Zoom** (`SPEC.md` §5). The walks take loop counts and start offsets from the `$fe04` geometry, so
  `Fill.planQ*` is the same code over N x N cells; against emulator captures at zooms 1-7, terrain away
  from sprites matches 99.2-99.7% and sprite pixels 74-84%. `sprites/prop32_sheet_raw.bin` is the 32 x 32
  building sheet (27 frames per sheet). `Projection.projectGrid` is float and agrees with the game's
  corners within a pixel at 78-95% of vertices; the exact integer reconstruction is scratch only.
  A mid-render capture records the tick after the one its displayed frame used, so scorers try all four
  water ticks.
- **Weather** (`SPEC.md` §7). `Weather.draw` ports `$1a856` from `assets/weather.bin`; winter and autumn
  frames of land 5 match the game. The stepper and the Godot view do not draw it.
- **A second land.** `assets_k60/` against mission 1's `assets/`: the four sprite sheets (`$33000`,
  `$37c7c`, `$312a0`, `$3af1c`), the palette, HUD tables, strings and headings are byte-identical; the
  backdrop differs in the minimap (rows 6-133) and the side-shield strip under it (rows 134-152, x 7-63),
  `dither.bin` only in slots `$1d-$2e` (a different point of the season fade), `tables.json` only in
  `height_bias_fec4`. Scored against the screen in the next `$f898` snapshot at the RAM's water tick
  (camera (45,74), yaw `$f0`) the frame matches pixel for pixel; the stepper's `--shot` and the game's
  screen give the same colour at five sampled ST coordinates.

### The minimap

`pm_render_ref.draw_minimap` (diagnostic) matches the master 100% from the `$418ae` source and 94.5%
from colour plane B (the stand-in a from-scratch port uses); `TerrainView.cs` draws the panel with a
camera-window box (`assets/reference/godot_screenshot_minimap_90th.png`). Mapping, palette table and the
per-frame deltas are in `SPEC.md` §7 "The HUD minimap" (cell (x, y) of `$418ad` is pixel (x, y + 6);
the port's origin `(1, 6)` is relative to `$418ae`).

### The Godot scene

Godot 4.7.2-stable mono, .NET 8. `TerrainView.cs` (a `Node2D`) builds a `Fill.Buffer` from
`Projection.projectGrid` and `Scene.render` whenever the camera changes, blits `Index` through
`assets/palette.json` into an `Image` shown on a `TextureRect` (nearest filter, magenta = uncovered),
over the `$78000` master (`assets/backdrop.bin`). Arrow keys pan (clamped to the planes' bounds),
PageUp / PageDown rotate through all 16 yaw steps, Y cycles the season.

Verified with real GPU screenshots, not just a build: `godot --quit-after 5 --write-movie <path>.png`
(not `--headless`, whose `dummy` driver returns a null image), cameras `36,47` and `28,40`, yaw step 3
(quadrant 0) and 11 (quadrant 2): `assets/reference/godot_screenshot_{cam36_47,cam28_40,yaw3_q0,yaw11_q2,entities_91st,
backdrop_118th,inline_118th,minimap_90th}.png`, with `render_faithful.png` (the Python reference render)
matching the cam 36,47 shot by eye.

**Project layout trap.** `Godot.NET.Sdk` writes its build output relative to the csproj's own
directory, so the csproj sits at the Godot project root (`godot/PowerMongerPort.csproj`) and the sources stay
in `game/`; a csproj inside `game/` fails at runtime with "Cannot instantiate C# script ... class could not
be found" and no build error.
## Why F# for logic, C# for Godot glue, no GDScript

Godot's .NET support runs its **source generators on C# only** — `[Export]`,
`_Process`, signals, `[GodotClass]` all need the C# generator. F# can reference
Godot's assemblies and subclass `Node`, but you lose the editor integration and
hit sharp edges (generic node methods, the `partial` requirement). So:

- **`godot/logic/` (F#)** — pure logic, zero Godot reference: `Terrain.fs`
  decodes `terrain.bin`, `Projection.fs` ports the `$fecc`/`$ff7c` projection
  maths from `SPEC.md`. This is where the interesting, testable code lives —
  terrain decode, the projection, the entity step (`$14b62`-style), sampling.
  F#'s records + pattern matching fit the 68000 struct/FSM shape well.
- **`godot/game/` (C#)** — thin node layer. `TerrainView.cs` is the only class:
  it calls `PmLogic` and blits the result to screen. Keep every node class
  here small and delegating. The `.csproj` itself lives at the Godot project
  root (`godot/PowerMongerPort.csproj`), not inside `game/` — see "The Godot scene" above
  for why that placement matters (it's not cosmetic).
- **No GDScript** — a second language with no share of the logic, and it can't
  call the F# lib without a C# shim anyway.

## Building the skeleton

```
cd godot
# copy or symlink the asset pack where Godot's res:// can see it:
cp -r ../assets assets          # (or: ln -s ../assets assets  on a real FS)
dotnet build PowerMongerPort.sln
godot4 --path . scenes/Main.tscn      # or open project.godot in the editor
```

The project's `config_version`/features say 4.3 and load, build and run under 4.7.2 with no re-save;
if a future Godot major bump complains, open the project once in the editor and let it re-save
`project.godot`. .NET 8 SDK is assumed (`net8.0`, roll-forward covers newer installed SDKs).

Expected result: the mission-1 island at camera cell (36,47), yaw `$f0`, over the `$78000` master, with its
trees, banner ring and men (`assets/reference/godot_screenshot_inline_118th.png`). Arrow keys pan, PageUp /
PageDown rotate, Y cycles the season; all re-render live.
