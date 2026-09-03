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
live palette. `pm_render_ref.py` writes `assets/reference/render_from_assets.png`
(dither fill), `render_flat.png` (height-ramp fill), and `render_compare.png` —
reference terrain (top) over the frame rebuilt from `assets/` (bottom) — and
prints the block-mean dE and the per-index distribution vs the reference.

## Verification status (77th pass)

- **Projection: closed.** `pm_render_ref.py`'s projected 9×9 vertex grid equals
  the game's own `$3f364` corner buffer **byte-exact** (81/81 vertices).
  `EYE`/`HORIZON` confirmed `$ff98`=320 / `$ff96`=130 from the aligned `$ff7c`
  disasm. The 76th's "island ~15-20 px low" was a bad diff against a live frame
  whose camera had drifted from the RAM snapshot; the consistent reference is
  the snapshot's own back buffer `$24400` (= `isoframe.png`, 231/64000 px).
- **Dither: formula closed, pixel match partial.** Real phase (`SPEC.md` §4):
  `A5 = ditherBase + colourByte*128 + (topY & 15)*8`, `+4 B/line`, `+8 B/16-px
  cluster`, two big-endian longs/cluster = planes {0,1},{2,3}. `dither.bin` was
  truncated at 2 KB (phase reaches ~8.5 KB) — now a 16 KB dump. Decoding at
  `colourByte*128` lands on the right palette families (green ramp, water, rock)
  and the rebuilt greens match the reference within ~5 %. `pm_render_ref.py`
  resets the phase per triangle and skips the `$f97e` yaw-quadrant corner remap,
  so its texture is patchy (`assets/reference/render_compare.png`); a
  pixel-exact fill needs the `$e420`–`$e55a` span walker ported. A modern port
  replaces the fill with a shader, so this does not block the port.
- **Sprites / HUD / border / minimap:** category dispatch (`$115e0`) mapped
  (`SPEC.md` §6/§9); the per-category frame rip, HUD glyphs, `$e0d4` master and
  the minimap compositor are still deferred.

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
   `x, h, y` vertices with the projected corners). The maths is exact
   (`SPEC.md` §3 — reproduces the game's `$3f364` byte-for-byte), so no
   `Eye`/`Horizon` re-tune is needed; just feed `EYE`=320 `HORIZON`=130.
2. Fragment-shader the height ramp (drop the dither) — either
   `Terrain.flatPaletteIndex`, or the `colourByte`→index table in `SPEC.md` §4
   (which is what the real dither resolves to); `assets/palette.json` is the
   16 colours. `assets/dither.bin` is there for a faithful stipple.
3. Sprites: `assets/sprites/` + `assets/headings.json`, drawn per-cell inline in
   the grid walk (painter's order — do not add a separate sorted pass).
4. Camera: 16 yaw steps, 7 zoom levels (`assets/tables.json → zoom_geometry`).
