# PowerMonger iso-renderer port

A precursor to porting PowerMonger's isometric terrain view to a modern engine.
Nothing here touches the emulator — it is asset extraction, a reference
renderer, a porting spec, and a toolchain skeleton.

## Layout

| path | what |
|------|------|
| `assets/` | everything the iso renderer reads, extracted from a live RAM image. `manifest.json` gives one line of provenance per file. |
| `SPEC.md` | the porting contract: coordinate systems, projection with exact constants, the triangle/dither rasteriser, sprites, zoom, the frame pipeline, and what a modern port should replace. Written to be implementable without the disassembly. |
| `godot/` | Godot 4.x (.NET) + F# skeleton. Proves the toolchain — F# logic lib loads, assets load, one heightmap mesh renders. `godot/logic/Fill.fs` (81st) is a byte-exact port of the closed rasteriser (`walk_q3` + `ef62_raster` + the `$e420` DDA + the dither fill); not yet wired into `TerrainView.cs`. |

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
  it calls `PmLogic`, builds an `ArrayMesh`, adds a camera. Keep every node
  class here small and delegating.
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

`godot --version` was not on PATH when this was written; the project targets
**Godot 4.3-stable mono**. If you have 4.4+, open in the editor once and let it
re-save `project.godot` / the `Godot.NET.Sdk` version in
`game/PowerMongerPort.csproj`. .NET 8 SDK is assumed (the repo's machine had
9.0/10.0, which roll-forward-covered `net8.0` fine).

Expected result: a flat-shaded green heightmap of the mission-1 island (64x128
grid, island cells x8..45 y41..75), lit by one directional light, viewed from a
fixed 45-degree camera. No dither, no sprites, no PM projection yet — those are
the next steps, and `SPEC.md` is the spec for them.

## Next steps (in `SPEC.md` order)

1. **Wire `Projection.projectGrid` + `Fill.walkQ3` into `TerrainView.cs`.**
   Both are done and byte-exact/cross-verified (see above) — this is now pure
   glue, not a porting problem. Two shapes work: (a) a **software layer** —
   call `Fill.walkQ3` each frame into a `Fill.Buffer`, blit `Index` through
   `assets/palette.json` into an `Image`/`ImageTexture`, show it on a
   `TextureRect` or in a `SubViewport` (closest to PM's own direct-to-shifter
   pipeline, keeps the dither if wanted); or (b) feed `Projection.projectGrid`'s
   corners into the existing `ArrayMesh` build and drop `Fill.fs`'s per-pixel
   dither for a fragment-shader height ramp (`Terrain.flatPaletteIndex`, or the
   `colourByte`→index table in `SPEC.md` §4). **Not attempted this pass** —
   Godot isn't installed in this environment (`godot --version` not on PATH,
   `PowerMongerPort.csproj`'s Godot package reference can't be restored/built
   here), so a C#-side change would ship unverified.
2. Sprites: `assets/sprites/` + `assets/headings.json` + `Sprites.fs` (decode
   stub, 81st), drawn per-cell inline in the grid walk (painter's order — do
   not add a separate sorted pass). Frame base/count per category still needs
   the rip (Task 2 / `SPEC.md` §9 item 3).
3. Camera: 16 yaw steps, 7 zoom levels (`assets/tables.json → zoom_geometry`).
