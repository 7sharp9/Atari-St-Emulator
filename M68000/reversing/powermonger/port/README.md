# PowerMonger iso-renderer port

A precursor to porting PowerMonger's isometric terrain view to a modern engine.
Nothing here touches the emulator — it is asset extraction, a reference
renderer, a porting spec, and a toolchain skeleton.

## Layout

| path | what |
|------|------|
| `assets/` | everything the iso renderer reads, extracted from a live RAM image. `manifest.json` gives one line of provenance per file. |
| `SPEC.md` | the porting contract: coordinate systems, projection with exact constants, the triangle/dither rasteriser, sprites, zoom, the frame pipeline, and what a modern port should replace. Written to be implementable without the disassembly. |
| `godot/` | Godot 4.x (.NET) + F# skeleton, **running live**. `godot/logic/Fill.fs` ports the closed rasteriser (`ef62_raster` + the `$e420` DDA + the dither fill) and all 4 yaw-quadrant grid walks (`walkQ0`-`walkQ3`, dispatched by `walk`); `godot/game/TerrainView.cs` wires it into a real scene — arrow keys pan the camera, PageUp/PageDown rotate it through all 16 yaw steps. |

Regenerate the assets:

```
python3 tools/pm_export.py                 # -> reversing/powermonger/port/assets/
python3 tools/pm_render_ref.py             # rebuild a frame from assets/ alone, diff vs reference
```

`pm_export.py` reads `scratchpad/pm74_late.ram` (the settled mission-1 iso view;
regenerate per `../README.md` if it is gone) and a frame-dump record for the
live palette. `pm_render_ref.py` writes `assets/reference/render_from_assets.png`
(dither fill), `render_flat.png` (height-ramp fill), and `render_compare.png` —
reference terrain (top) over the frame rebuilt from `assets/` (bottom) — and
prints the block-mean dE and the per-index distribution vs the reference.

## Verification status (83rd pass)

- **All 4 yaw-quadrant grid-walk handlers are ported and wired in.**
  `Fill.walkQ0`/`walkQ1`/`walkQ2` join the 78th/80th's `walkQ3`, dispatched by
  `Fill.walk` (mirrors `$f97e`/`$f982`'s `((yaw+8)>>5)&6` select). `TerrainView`
  now has real camera rotation: PageUp/PageDown step `YawSteps` through all 16
  values (arrow keys still pan the camera cell).
- **Trace-verified, not guessed.** For each of q0/q1/q2, rotated the live
  camera via the keypad-poke recipe (below) to a yaw in that quadrant's range,
  captured RAM, resumed to the settled PC, and dumped registers at the first
  `$ef62` call — the vertex assignment (which corner went to D0/D1/D2) and the
  colour-plane choice (type vs height) matched the disassembly-derived port
  exactly at every cell checked (one per quadrant; SPEC.md §4 has the
  addresses and register values). Also fixed a stale-address bug this
  surfaced: the true entry points are `$f98e`/`$fa9a`/`$fbb4`, not the
  `$f98c`/`$fa98`/`$fbb2` an earlier pass recorded (2 bytes low each).
- **Cross-checked against the F# port byte-exact** on synthetic corner/terrain
  data designed to exercise every CLEAR/SET branch and both comparison
  directions (`scratchpad/pm83_synth_check.py` + `.fsx`, `dotnet fsi`, same
  method as the 81st's `walkQ3` check) — identical covered-pixel sets for all
  three new handlers.
- **Re-verified live in Godot with real GPU screenshots** at two more camera
  angles: yaw step 3 (quadrant 0, `$30`) and yaw step 11 (quadrant 2, `$b0`) —
  `assets/reference/godot_screenshot_yaw{3_q0,11_q2}.png`. Both show a
  distinctly different island silhouette from the mission-1-start q3 shots,
  through the same `RenderFrame()` path.
- **Score against real captures is lower for the new quadrants** (35-50 %
  exact-index vs q3's 94 %, `pm_render_ref.py --ram` on
  `scratchpad/pm83_q{0,1,2}c.ram`) — this is the *already-documented* residual
  (tall coast-slope dither needs a multi-segment DDA chain the port doesn't
  model, SPEC.md §9 item 1) showing up more at these camera angles, not a new
  geometry bug: the live-trace check above confirms the vertex/colour
  assignment is exact.

## Verification status (82nd pass)

- **`Fill.walkQ3` + `Projection.projectGrid` are wired into `TerrainView.cs`
  and run live in real Godot — verified with actual screenshots, not just a
  build.** Godot 4.7.2-stable mono is installed at
  `C:\Users\Dave\Documents\GitHub\Godot_v4.7.2-stable_mono_win64` (the 81st
  pass's environment didn't have it on `PATH`; this one does). Shape (1) from
  "Next steps" below: `TerrainView` (now `Node2D`, was `Node3D`) builds a
  `Fill.Buffer` from `Projection.projectGrid` + `Fill.walkQ3` each time the
  camera cell changes, blits `Index` through `assets/palette.json` into an
  `Image`, and shows it on a `TextureRect` (`TextureFilter = Nearest`, magenta
  = uncovered, same convention as `render_faithful.png`). Arrow keys pan
  `CamCellX`/`CamCellY` (clamped to the terrain planes' bounds) and re-render
  — yaw is fixed to quadrant 3 (`$f0`), the only grid-walk handler ported.
- **Verified two ways:** `dotnet build PowerMongerPort.sln` (0 errors), and
  real GPU screenshots — `godot.exe --quit-after 5 --write-movie <path>.png`
  (NOT `--headless`: headless maps to the `dummy` rendering driver, which
  returns a null image from `get_viewport().get_texture().get_image()`; the
  normal `windows`/Vulkan driver renders for real even with no interactive
  session). Two camera cells (`36,47` mission-1 start; `28,40`) produce two
  different island slices from the same `RenderFrame()` code path —
  `assets/reference/godot_screenshot_cam36_47.png` /
  `_cam28_40.png`. The `36,47` shot's island silhouette and dither texture
  match `assets/reference/render_faithful.png` (the Python reference render)
  by eye — same shape, same dark-ridge patch, same speckle pattern.
- **Found and fixed a real structural bug, not a porting bug:**
  `Godot.NET.Sdk` writes its C# build output to
  `$(MSBuildProjectDirectory)/.godot/mono/temp/bin/<config>/`, i.e. relative
  to wherever the `.csproj` itself sits — NOT to the Godot project root found
  by walking up to `project.godot`. The skeleton's original layout put
  `PowerMongerPort.csproj` inside `game/`, so the build output landed in
  `game/.godot/mono/temp/bin/Debug/` while Godot's runtime script loader only
  ever looks under the *project root's* `.godot/mono/temp/bin/Debug/` — every
  script instantiation failed with "Cannot instantiate C# script ... class
  could not be found", silently, with no build error (`dotnet build` and even
  `godot --build-solutions` both "succeed"). Fixed by moving the `.csproj` to
  the project root (`port/godot/PowerMongerPort.csproj`); the `.cs` sources
  stay in `game/` (default SDK glob still finds them). This was exactly the
  kind of thing the 81st pass's "ship unverified C#" concern was about — it
  would not have been caught without an actual Godot install.

## Verification status (81st pass)

- **`godot/logic/Fill.fs`: the closed rasteriser is now F#, byte-exact.**
  `walkQ3` / `ef62Raster` / `fixedSlope` / `ditherIndex` are a 1:1 port of
  `tools/pm_render_ref.py`'s `walk_q3` / `ef62_raster` / `_fixed_slope` /
  `dither_index` — cross-checked against the Python reference on synthetic
  triangles (every rasteriser path: general split, flat-top, the `$f134`
  reorder, the `0x1c` coast-force, the mid-vertex slope switch, water
  shimmer) and a synthetic 8×8-cell grid (both `walk_q3` diagonal-selector
  branches): identical coverage counts and pixel-index hashes. `PmLogic.fsproj`
  builds clean. Not yet wired into `TerrainView.cs` — see "Next steps".
- `Terrain.Map`'s flag-plane accessor renamed `SeaStatic` → `DiagonalSelector`
  (it was still named for the pre-78th "corners unmoved, skip fill" reading).

### 80th-pass verification status (superseded above for the rasteriser; still current for projection/dither/sea)

- **Projection: closed.** `pm_render_ref.py`'s projected 9×9 vertex grid equals
  the game's own `$3f364` corner buffer **byte-exact** (81/81 vertices).
  `EYE`/`HORIZON` confirmed `$ff98`=320 / `$ff96`=130.
- **Quadrant-3 walk + rasteriser: closed, 96 % coverage, ~94 % exact-index.**
  `pm_render_ref.py --ram` ports `$fccc` + `$ef62` + the real `$e420` 16.16 DDA
  span walker (`_fixed_slope`, `_dda_walk`) from the game's own `$3f364`
  corners (+64 px inset). Against `scratchpad/pm78_settle.ram` it covers 96 %
  of the game's real per-frame terrain layer and scores **~94 % exact / ~95 %
  within ±1** palette index (`pm74_late` 93.9 %, `pm70_iso` 93.4 %). The
  `--assets` path still uses the naive quadrant-0 walk (shape proof only).
- **No "sea fill" (79th).** The composed `$1c700` buffer differs from the
  `$78000` master **only** in the island blob + a few sprites — the open sea
  (idx 14/15) is byte-identical, **baked into the master** (`$13b9a`, once per
  mission). A per-frame port draws only the projected 8×8 grid; a full frame
  composites that over the master. `render_faithful_composite.png` shows it.
- **Dither phase: closed (80th).** Live single-step of `$e420` showed `A5`
  wraps **modulo 128** inside the colour's slot (`SPEC.md` §4): `A5 =
  $2e000 + colourByte*128 + ((8*y) mod 128)`. This killed the 79th's empirical
  `DITHER_COLOUR_BIAS = -1`, which was compensating for the missing wrap and
  only happened to be right for 16–32 px-tall triangles.
- **Residual (≈6 %):** unit sprites on the hill (`walk_q3` is terrain-only),
  the tall `0x1c` coast slopes (game dithers idx 1-7, port lands nearer flat),
  a ~1 px NE island edge, and the other 3 quadrant handlers
  (`$f98c`/`$fa98`/`$fbb2`, camera rotation — not ported).
- **Sprites: `$11f82` decode closed** (8×11 four-bitplane, `[mask,p0,p1,p2,p3]`
  per row; `sheet_contact.png` decodes as the 4 faction-colour man blocks).
  **HUD / border / minimap:** category dispatch (`$115e0`) mapped
  (`SPEC.md` §6/§9); per-category frame rip, HUD glyphs, the `$78000` master
  build and the minimap compositor are still deferred (Task 2, not started).

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
  root (`godot/PowerMongerPort.csproj`), not inside `game/` — see "Verification
  (82nd pass)" above for why that placement matters (it's not cosmetic).
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

Confirmed 82nd pass with a real install: **Godot 4.7.2-stable mono**. The
project's `config_version`/features still say 4.3 and loaded/built/ran fine
under 4.7.2 with no re-save needed; if a future Godot major bump complains,
open once in the editor and let it re-save `project.godot`. .NET 8 SDK is
assumed (`net8.0`, roll-forward covers newer installed SDKs fine).

Expected result: the mission-1 island, dithered, at camera cell (36,47), yaw
`$f0` — see `assets/reference/godot_screenshot_cam36_47.png`. Arrow keys pan
the camera (clamped to the terrain planes' bounds); PageUp/PageDown rotate it
through all 16 yaw steps (`assets/reference/godot_screenshot_yaw{3_q0,
11_q2}.png` show two rotated views), all live re-render. Magenta = uncovered
(the `$78000` master — HUD, stone border, baked sea — isn't exported yet,
Task 2).

## Next steps (in `SPEC.md` order)

1. ~~Wire `Projection.projectGrid` + `Fill.walkQ3` into `TerrainView.cs`~~ —
   **done, 82nd pass** (software-layer shape: `Fill.Buffer` → `Image` →
   `TextureRect`). Two follow-ups if wanted, not required: (a) drop the
   per-pixel dither for a fragment-shader height ramp (shape (b) from the
   81st's options — `Terrain.flatPaletteIndex`, or the `colourByte`→index
   table in `SPEC.md` §4), or (b) a `SubViewport` instead of a scaled
   `TextureRect` if the port ever needs the raster to composite with other
   Godot nodes (UI, sprites) rather than being the whole screen.
2. Sprites: `assets/sprites/` + `assets/headings.json` + `Sprites.fs` (decode
   stub, 81st), drawn per-cell inline in the grid walk (painter's order — do
   not add a separate sorted pass). Frame base/count per category still needs
   the rip (Task 2 / `SPEC.md` §9 item 3).
3. ~~Camera: the other 3 `pm_grid_walk_q*` handlers~~ — **done, 83rd pass**
   (`Fill.walkQ0`/`walkQ1`/`walkQ2`, dispatched by `Fill.walk`; PageUp/PageDown
   in `TerrainView.cs`). Remaining camera gap: **zoom** — 7 discrete geometry
   sets (`assets/tables.json → zoom_geometry`), `Projection.Params.Zoom`/`Half`
   are wired but only the zoom-index-4 constants have been exported/tested.
4. The `$78000` master (HUD + stone border + baked sea) isn't exported —
   `TerrainView`'s uncovered pixels stay magenta until it is (Task 2).
5. The residual rasteriser inaccuracy (SPEC.md §9 item 1: the tall `0x1c`
   coast-slope multi-segment dither spread) is more exposed at yaws other than
   `$f0` (35-50% exact-index at q0/q1/q2 vs q3's 94%, `pm_render_ref.py --ram`
   on `scratchpad/pm83_q{0,1,2}c.ram`) — LOW priority per the 81st/82nd's own
   framing, but now affects most of the camera's range, not just the ~6%
   residual at the mission-1 start yaw.
