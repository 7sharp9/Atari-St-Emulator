# PowerMonger iso-renderer port

A precursor to porting PowerMonger's isometric terrain view to a modern engine.
Nothing here touches the emulator — it is asset extraction, a reference
renderer, a porting spec, and a toolchain skeleton.

## Layout

| path | what |
|------|------|
| `assets/` | everything the iso renderer reads, extracted from a live RAM image. `manifest.json` gives one line of provenance per file. |
| `SPEC.md` | the porting contract: coordinate systems, projection with exact constants, the triangle/dither rasteriser, sprites, zoom, the frame pipeline, and what a modern port should replace. Written to be implementable without the disassembly. |
| `godot/` | Godot 4.x (.NET) + F# skeleton. Proves the toolchain — F# logic lib loads, assets load, one heightmap mesh renders. Not the full renderer. |

Regenerate the assets:

```
python3 tools/pm_export.py                 # -> reversing/powermonger/port/assets/
python3 tools/pm_render_ref.py             # rebuild a frame from assets/ alone, diff vs reference
```

`pm_export.py` reads `scratchpad/pm74_late.ram` (the settled mission-1 iso view;
regenerate per `../README.md` if it is gone) and a frame-dump record for the
live palette. `pm_render_ref.py` writes `scratchpad/pm76_render_compare.png` —
reference terrain (top) over the same frame rebuilt from `assets/` (bottom).

## Verification status

`pm_render_ref.py` reproduces the **island silhouette, footprint orientation
and height shading** from `assets/` alone (`assets/reference/render_compare.png`).
That proves the export is complete: every input the renderer needs is present
and produces a recognisable mission-1 island.

**Not closed to a pixel diff** (see `SPEC.md` section 9): the vertical
calibration of the perspective divide (island sits ~15-20 px low) and the phase
into the dither table (lands on blue/brown, not the green ramp). Both are a
camera/shader re-tune that a modern port does against a screenshot anyway;
neither blocks starting the port.

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

1. Port `Projection.projectGrid` into the mesh build (replace the trivial
   `x, h, y` vertices with the projected corners) and re-tune `Eye`/`Horizon`
   against `assets/reference/isoframe.png` — closes Open Question 1.
2. Fragment-shader the height ramp (drop the dither) — `Terrain.flatPaletteIndex`
   is the ramp; `assets/palette.json` is the 16 colours.
3. Sprites: `assets/sprites/` + `assets/headings.json`, drawn per-cell inline in
   the grid walk (painter's order — do not add a separate sorted pass).
4. Camera: 16 yaw steps, 7 zoom levels (`assets/tables.json → zoom_geometry`).
