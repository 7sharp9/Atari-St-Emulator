# starglider: Starglider (Argonaut / Rainbird, 1986), first look

Starglider is a 3D wireframe flight game by Jez San of Argonaut Software, published by Rainbird in 1986. The
player flies an AGAV over the planet Novenia, shooting Egron craft and docking in silos to refuel. The ST
version is hand-written 68000 assembly (5 `LINK` frames and 270 `rts` in the depacked image), so it is analysed
from snapshots, traces and `callcap`, not a decompile.

**What this doc set has established.**
- **Renderer.** It draws hidden-line wireframe: back-face-culled convex faces, each visible edge drawn once by an
  integer Bresenham. The only 3D clip is a near plane, and it has a scale bug (section "The architecture").
- **Objects.** The world is one pool of 64-byte records from a per-level list. Enemies steer a sixteenth of the way
  toward the player each pass through a per-type jump table.
- **Flight.** The craft is flown by three running totals that the mouse and keyboard share.
- **Proof.** Every one of those mechanisms is reproduced by a Python model against the emulator with a match count.

| doc | covers | proof |
|---|---|---|
| [`graphics.md`](graphics.md) | frame, matrices, the 28 models, culling, near and window clip, Bresenham, dust | each stage vs `rref.py`; whole frame 49,368/49,368 viewport bytes on two snapshots; all 28 models 84/84 |
| [`objects.md`](objects.md) | pool and record, type names, AI dispatch, collision, laser, scores, levels, both RNGs | AI pass 750/750 poked + 11/11 natural; collision 600/600; laser 600/600; names 17/17 |
| [`flight.md`](flight.md) | IKBD handler, controls, the flight step, energy and shield, silos, practice mode | flight step 400/400; IKBD streams 30/30; key commands 400/400 |
| [`frontend.md`](frontend.md) | Ice depack, the `.TRA` pictures, the Timer A sample player, screens, text, the HUD | `.TRA` format 64,000/64,000 pixels; HUD poke diffs; the rest read and driven |

Gates: `uv run python tools/gates.py run starglider` (`gates.toml`, 16 gates, about a minute). They need the disk
image and the drive snapshots ("Running it"). Scripts and what each proves: [`py/README.md`](py/README.md). Routine
and field names: [`starglider.sym`](starglider.sym).

## Provenance

The version analysed is the Zuul compilation disk #208 (`Zuul #208.zip`, one file `ZUUL208.MSA`, sha256
`c6bdf36268ca98a548a14eb123b54b537a6d99f8e0f4d9f49d3488918b61157c`), converted with `tools/msa2st.py` to
`scratchpad/starglider/zuul208.st` (839,680 bytes, sha256
`b9b1db94159ebd948cce81f850e125ac2e05466f86ec2310e12364c5810e7a03`). Neither image is committed.

The disk is a five-game menu: a bootable sector (checksum `$1234`) prints a Zuul "anti-virus" banner and waits in
`Bconin`; `\AUTO\LOADER.PRG` (Ice-packed) is the menu, which polls the ACIA data register for F1 to F5 at `$b01e`
and Pexecs `\1.PRG` to `\5.PRG`. Starglider is F2. Its files:

| file | bytes | sha256 (prefix) | role |
|---|---|---|---|
| `2.PRG` | 697 | `ed4345f1` | menu stub: Pexec mode 3 of `\STARGLID.PRG`, then `\STAR.BIN` |
| `STARGLID.PRG` | 10,975 | `4b4c90a7` | Zuul crack intro (Timer A music, scroller); polls `$fffc02` for SPACE at `$ae84`, then `Pterm0` |
| `STAR.BIN` | 247,824 | `f54d5dbd` | the game: Ice-packed GEMDOS program, TEXT at `$ab8c` (basepage `$aa8c`), BSS to `$56264` |
| `TITLE.TRA` | 14,660 | `05468af1` | opened by the game on the title (`Fopen("title.tra")`) |
| `RESULT.TRA` | 7,331 | `a4a5af11` | opened by the game on the title (`Fopen("result.tra")`) |
| `COS_SIN.TAB` | 640 | `640c0671` | on the disk; who reads it is open |

`STARGLID.PRG` and `OVERLAN1.BIN` (game 1's equivalent) have the same size and differ in 314 bytes, between file
offsets 696 and 5294 (the intro's text and data, not compared further).

## Milestones and how they were reached

| milestone | screenshot | how |
|---|---|---|
| title picture, sampled title music | [`title.png`](title.png) | F2 on the menu, SPACE in the crack intro |
| in flight, level 1 | [`flight.png`](flight.png) | any key but G or K on the title |
| define controls | [`controls.png`](controls.png) | K on the title |
| docked in a silo | [`docked.png`](docked.png) | poke `714`, `658` (`frontend.md` section 4) |
| interrogate screen | [`interrogate.png`](interrogate.png) | I while docked |
| pilot rating, high scores | [`rating.png`](rating.png), [`scores.png`](scores.png) | energy poked to 1; score poked for the table |

`bash reversing/starglider/drive.sh` (about 50 s) drives a cold boot through the banner, the menu, the intro and the
title into flight and writes `g_menu`, `g_intro`, `g_title`, `g_game1`, `g_game2` (`.snap` and `.png`) to
`scratchpad/starglider/drive/`. Two runs from cold boot give byte-identical snapshots (5 of 5, `cmp`). The emulator
needed no change to reach flight.

## Running it

```
cd M68000
uv run python tools/msa2st.py "<dir>/ZUUL208.MSA" scratchpad/starglider/zuul208.st
bash reversing/starglider/drive.sh
```

Then `dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/starglider/drive/g_game1.snap repl` (the disk is
remounted from the snapshot's provenance sidecar). Scripts share paths through `py/sgcommon.py`
(`STARGLIDER_WORK` overrides the work directory). The `.TRA` gate also needs the disk's files: `uv run python tools/extract_disk.py scratchpad/starglider/zuul208.st
scratchpad/starglider/files` (it reports `C.D8T`, another game's file, as a FAT overrun; every Starglider file is
contiguous and read exactly).

## The architecture

**Layout.** The game is one program. `$c9e6` sets `A6 = $5bf00`, the block of globals every routine uses, and
installs its own VBL and IKBD handlers. A restart enters at `$ca20` and the title loop at `$ca34`.

**The main-loop pass, `$ca9c..$cac0`.** It takes about 48,000 steps (four VBLs) and runs:
1. `$fb74`, the frame: clear, HUD, view matrix, ground dust, the object lists, drawing every object in view, laser,
   messages;
2. `$d29a`, keys and stick;
3. `$12340`, the flight step;
4. `$125e0`, the per-object AI through the jump table `$12dde`;
5. `$ef7a`, cyclic tables;
6. `$12fa2`, player collision;
7. `$d198`, the level banner;
8. `$13a4e`, the beam wait and buffer flip.

The collision consequences and the energy drain sit inline in the loop at `$cbb4..$cc42`.

**Data structures.**
- **Object pool.** `$5d19a`: 64-byte records, count `472(A6)`.
- **Three lists.** Rebuilt every pass from the pool:
  - near: z within ±`$2020`;
  - active: rotated into view space;
  - view: inside the 2z frustum.
- **Models.** 28 models under one header table, faces carrying their own vertex and edge index lists.
- **Level lists.** One per level, of (type, x cell, z cell, hit points).

**Mechanisms that recur.** The `(v << shift) / z + centre` projection is used by the renderer, the laser hit test
and the dust. The same Q14 `muls; asl.l #2; swap` multiply serves the view matrix, the object matrix and the
projection of every object. Both random generators mix in the mouse x total.

**Behaviours worth knowing.**
- **Near-plane clip.** The clip doubles the intercept, and for an intercept fraction of 0.5 or more its `divs`
  overflows and leaves the endpoint where it was.
- **Window clip.** One input makes the clip loop forever.
- **Colour 10.** The Bresenham's colour 10 jumps into the wrong loop. No model uses that colour.
- **Enemy steering.** Turning ignores the 0/4096 seam, so an enemy facing across it turns the long way round.
- **Shared IKBD path.** A joystick is read as a mouse.

## What the emulator needed

Nothing. The boot sector, the Zuul menu and intro, the Ice depack, both picture loads, the Timer A sample player and
the game ran on the existing build (commit `54efe30`).

## Not exercised in the emulator

- Levels 2 to 4 in play: their object lists were read and `$1523a` gated on them, but no level was completed.
- The radar/scanner view and the gunsight sprite.
- The synthesised sound effects.
- Monochrome mode.
- The name-entry keys beyond A, B, C and Return.
- A natural game over by being shot down: both endings were reached by pokes.
- Whether the near-clip overflow or the endless window clip ever shows in play.
- The control-flow graph and call-graph renders that other games carry (`tools/trace_cfg.py`) were not made.

## Files

| file | what |
|---|---|
| `README.md` | this file |
| `graphics.md`, `objects.md`, `flight.md`, `frontend.md` | topic docs |
| `starglider.sym` | 224 names, merged from the four areas (`tools/merge_sym.py`) |
| `gates.toml` | 16 gates for `tools/gates.py` |
| `drive.sh` | cold boot to flight, five snapshots |
| `py/` | models, gates and drivers ([`py/README.md`](py/README.md)) |
| `models.png` | the 28 wireframe models, decoded from RAM (`py/render/models.py`) |
| `cockpit_tra.png` | `RESULT.TRA` decoded: the cockpit frame (`py/frontend/tra_render.py`) |
| `title.png`, `flight.png`, `controls.png`, `docked.png`, `interrogate.png`, `rating.png`, `scores.png` | milestone screenshots |
