# Atari ST emulator (F#)

A 68000 / Atari ST emulator written in F#, built on a live stream series. It boots
the real TOS 1.00 ROM to the GEM desktop with a working SDL2 window, keyboard and
mouse, reads FAT12 floppy images, and loads and runs real programs off them.

Development is driven by running real code rather than a coverage checklist: the
emulator runs the ROM, or a program off a disk, until it hits an unimplemented
instruction or a wrong result, and each pass closes the next gap. Instruction
coverage is verified against the SingleStepTests 68000 vectors.

## What runs today

- **TOS 1.00** cold-boots to the AES desktop; the SDL2 window is interactive.
- **Disk programs** load through the real ROM via `Pexec`: the Hatari GPL CPU and
  GEMDOS test binaries (`int_test.tos`, `gmdostst.tos`) run to completion.
- **Super Sprint** (1986, Atari Games) runs from its `\AUTO\SSPRINT.PRG`, through
  attract mode into a live, drivable Track 1 race from the window's arrow keys.
- **`A_013.ST`**, a bootable multi-game menu disk with LSD-crunched games, boots
  to its menu; selecting a game runs its in-place depacker and the game.

Case studies with control-flow graphs are under [`M68000/reversing/`](M68000/reversing/).

Timing is instruction-counted, not cycle-accurate. That is enough for GEMDOS
programs and for games whose loop is VBL or Vsync driven; a target needing
cycle-exact raster effects, a cycle-timed loader or timing-based protection is out
of scope until a per-instruction cycle scheduler exists. See "Known gaps" in
[`M68000/DEVELOPING.md`](M68000/DEVELOPING.md).

## Requirements

- **.NET 8 SDK**
- **PowerShell 7** for the `run.ps1` wrapper (the raw `dotnet exec` form works
  without it)
- **SDL2** native library on the path, for the `window` mode (the `Silk.NET.SDL`
  NuGet package is restored automatically)
- A **TOS 1.00 UK ROM dump** named `TOS100UK.IMG` (196608 bytes) placed in
  `M68000/`. It is copyrighted and is not distributed here. Point
  `ATARI_ROM_PATH` at a different dump to override the name.

## Quick start

```
cd M68000
# copy your TOS100UK.IMG into this directory first

./run.ps1 boot 5000000        # cold-boot 5M instructions, per-instruction trace on
./run.ps1 window              # live desktop in an SDL2 window (F12 or close to quit)
./run.ps1 check 5000000        # boot and record registers to checkpoint.txt
./run.ps1 verify 5000000      # boot again and diff registers against checkpoint.txt
./run.ps1 selftest tests/680x0   # 68000 ProcessorTests vectors vs the CPU core
```

`checkpoint.txt` is keyed to your ROM dump and is not committed, so run `check`
once before `verify`.

`run.ps1` builds `M68000.fsproj` once (skip with `-NoBuild`) and then `dotnet
exec`s the DLL from `M68000/` so the ROM and `checkpoint.txt` resolve. Trace is on
for `boot` / `trace` and off elsewhere; `-Trace` forces it on. Run `./run.ps1`
with no arguments for the full subcommand list.

The `selftest` vectors are ~190 MB and are not committed. Fetch them once with
`python tools/fetch_680x0_tests.py`.

### Running a program off a disk

```
./run.ps1 -DiskA path/to/floppy.st window          # mount a real .ST image in drive A
./run.ps1 -DiskA path/to/floppy.st boot 12000000   # headless
```

The FDC models single- and double-sided images, PSG side/drive select, Type I
head movement, the DMA address counter and the `$FF8606` DMA status register:
enough for TOS to read a FAT12 filesystem and `Pexec` a program, and enough to
boot a disk whose boot sector has the `$1234` checksum. Sector writes hit an
in-memory copy only, so the host `.ST` file is never modified. Build a disk with
`tools/make_blank_disk.py` and `tools/add_file_to_disk.py`.

## The REPL

`./run.ps1 repl 100000` (cold boot then a prompt) or `./run.ps1 rrepl <snap>`
(straight from a snapshot) gives an interactive monitor:

| command | meaning |
|---------|---------|
| `s [n]` | step n instructions |
| `r` | dump registers |
| `m <hex> <declen>` | dump memory (length in decimal) |
| `w <hex> <hex>` | write a longword |
| `u <hex> [max]` | run until PC reaches an address |
| `snap <path>` | save a state snapshot |
| `watch <hex> [len]` | report writes to an address (with the writing instruction) |
| `kbd <hexbyte>...` | inject raw IKBD serial bytes (scancodes, mouse or joystick packets) |

## Repository layout

```
M68000/
  MMU.fs            memory map, bus peripherals, FDC, PSG, MFP
  Instructions.fs   opcode pattern table
  68k.fs            CPU core, the shared effective-address decoder, OS-call narrator
  Video.fs          shifter render, SDL2 window, host input -> IKBD
  Program.fs        entry point, CLI modes, the REPL
  run.ps1           build-once / exec-many wrapper
  DEVELOPING.md     the debugging loop, env-var switches, regression net, tools
  tools/            disassembler, CFG builder, disk builders, screendump, gfxview, Hatari trace
  reversing/        control-flow case studies (int_test, gmdostst, supersprint, a_013)
  tests/680x0/      SingleStepTests vectors (downloaded, git-ignored)
```

`tools/hatari_trace.py` drives a local Hatari build as a CPU/OS-trace oracle for
ground-truth peripheral and TOS behaviour; supply your own Hatari.

## Further reading

- [`M68000/DEVELOPING.md`](M68000/DEVELOPING.md) is the working reference: the
  ROM-driven loop, every `ATARI_*` env switch, `selftest` classification, the
  `ATARI_TRACE_EVENTS` + `trace_cfg.py` analysis pipeline, `gfxview.py`, and the
  regression net that every emulator-behaviour change has to pass.
- [`M68000/reversing/*/README.md`](M68000/reversing/) each walk one program from
  load to running, with the disassembly and the walls that were fixed to get
  there.
- 68000 Programmer's Reference: <https://www.nxp.com/files/archives/doc/ref_manual/M68000PRM.pdf>
