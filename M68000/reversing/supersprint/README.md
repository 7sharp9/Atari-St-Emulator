# supersprint — a real 1986 commercial game, driven into a live race

The first **commercial** disk-loaded program the emulator runs, as opposed to the GPL
Hatari test binaries in `../int_test/` and `../gmdostst/`. Super Sprint's `\AUTO\SSPRINT.PRG`
loads through the real TOS 1.00 ROM, pulls in its data files, runs its
intro/credits sequence and double-buffered attract loop, and — with IKBD input
(injected 55th pass, wired to the live window's arrow keys 56th pass) — leaves
attract, walks its track-select / "PREPARE TO RACE" menu, starts an actual Track 1
race, and lets a window player drive the joystick car a full lap. No instruction
wall, no crash.

## The MFP Timer B raster split (built 61st pass, verified 63rd)

Super Sprint installs an MFP Timer B event-count ISR (`$f9ea`, vector `$120`,
`TBCR=$08`) that rewrites the `$ffff8240` palette from a `movem.l <16 words>`
table. The 61st pass built the per-scanline scheduler that drives it
(`MMU.HblTick`, one tick per `instructionsPerFrame/300` steps), and the frame
recorder gained a per-scanline palette row-record. The 63rd pass verified the
payoff by frame-diffing:

- **`raster_split.png` vs `raster_flat.png`** — the "PREPARE TO RACE" ready
  screen rendered with the per-scanline palettes vs with one flat VBL-time
  palette. The three ready-cars (blue / yellow / red is the correct Super
  Sprint lineup) get their colours from a 3–4 band raster split; with a flat
  palette the bottom car and the centre text come out blue/olive. ~4.6 % of the
  frame's pixels differ between the two renders. The SELECT TRACK screen splits
  the same way.
- **But the split is not scanline-stable.** Across the captured prep frames the
  middle band boundary jitters between row ~35 and row ~53 (and the lower one
  between ~113 and ~149) frame to frame — on the row-35 frames it cuts through
  the two top cars and mis-colours them (the "two red cars" look). Real
  hardware places the `$ffff8240` write on the exact scanline the game's TBDR
  count selects, every frame. Our Timer B is still an instruction-count tick
  (`HblTick` every `instructionsPerFrame/300` steps, and 300 ≠ the real ~313
  lines/frame), so the split lands within a band or two of where it should but
  wobbles. `raster_split.png` is a good-case frame. A jitter-free split needs
  the real per-instruction cycle budget the project has not built.
- **The on-track race itself is flat.** Across 80+ consecutive captured race
  frames every scanline carries the same palette, and a `watch $ffff8240`
  during racing catches **zero** writes — the in-race Timer B ISR is
  counter-only. So the earlier "road/sky gradient is a flat colour" caveat was
  right about the race, wrong about the cause: it is Super Sprint's design, not
  a missing scheduler.

(The 61st-pass note that the split's changed palette entries "aren't painted by
any on-screen pixel" was an artefact of the recorder writing a frame's screen
beside the *previous* frame's row-records; fixed 63rd pass — the write is now
held back one frame so screen and row-records match.)

## The program

*Super Sprint* — arcade game © 1986 Atari Games, Atari ST conversion by Software
Studios, published by Electric Dreams. The copy used is the cracked scene release
`Super Sprint.zip` (moduslak.org) sitting in the repo root.

**The game binary and disk image are commercial and are not committed here.** To
reproduce, unzip that archive yourself:

```
unzip "Super Sprint.zip"          # -> "Super Sprint.ST"
#   Super Sprint.zip   sha256 d65b7ae216b628df6ff72df278388aedac6234c1484f49fb7b22972981248321
#   Super Sprint.ST    sha256 dc1f47fe6d5c55521cd3814ef867326a40ec7d412999047874e63bbce0cf719e   (368640 bytes)
```

`Super Sprint.ST` is a 360 KB single-sided FAT12 image, non-bootable BPB
(`eb30…`, boot-checksum `$0736` ≠ `$1234`). Root directory:

| file | what |
|------|------|
| `\AUTO\SSPRINT.PRG` | the game (74355-byte GEMDOS executable, magic `$601a`, text 72908 / data 1314 / bss 11124, 105 bytes of relocations, no symbol table) |
| `INIT.DAT` | 5139 bytes, loaded first |
| `SUPER1.DAT` | 17024 bytes |
| `SUPER.DAT` | 212650 bytes — the bulk of the intro graphics |
| `SSPRINT.HSC` | 295 bytes, high-score table |

No resource file, no `.RSC`, no protection track — a plain `\AUTO\` auto-run, the
same Pexec(0) path `int_test` and `gmdostst` already use.

## What it needed from the emulator

### To reach attract (52nd pass)

Two commits, both plain addressing-mode gaps, both routed through the shared EA
decoder (`x.ResolveEa` / `x.ReadEa` / `x.WriteEa`) — the same migration the
45th–49th passes did for the other instruction families. **No cycle-scheduler
work**; the attract loop is driven entirely by `Vsync` / VBL counting, which the
instruction-counted timing already models.

| commit | wall | fix |
|--------|------|-----|
| `2d466ce` | `jsr $cc(a5)` (JSR eamode 5); later `mulu.w #4,d1` (MULU immediate) | JSR/JMP and the MULU.w/MULS.w source operand onto the shared EA decoder |
| `ccbae25` | `addq #n,(d8,An,Xn)` (ADDQ eamode 6) | ADDQ/SUBQ onto the shared EA decoder (new `x.AddSubQ` helper) |

### To reach a race (55th pass)

No instruction walls. Two peripheral-behaviour gaps:

| commit | wall | fix |
|--------|------|-----|
| `dab30e5` | a joystick report ($FE/$FF + state byte) only ever delivered its header byte | the keyboard ACIA re-raises its MFP channel-6 IRQ while bytes remain in the RX FIFO, so the game's own single-byte-per-interrupt IKBD handler at `$104b6` sees the whole packet (EnqueueIkbd drops a packet in at once; real bytes arrive 1.28 ms / one IRQ apart) |
| *this commit* | on leaving attract the game installs its own VBL + **MFP Timer B** event-count handler (vector `$120`) and its engine never advanced without Timer B ticks | a **coarse** Timer B interrupt, delivered on an instruction count like the existing Timer C — enough to run the game's counter-only Timer B ISR and unblock the engine, not enough to place a mid-frame `$ffff8240` write at a specific raster line |

## How it was run

```
unzip "Super Sprint.zip"
ATARI_NOTRACE=1 ATARI_TRACE_OS=1 \
  dotnet exec bin/Debug/net8.0/M68000.dll 40000000 --disk-a "Super Sprint.ST"
# or:  ./run.ps1 -DiskA "Super Sprint.ST" -Trace boot 40000000
```

`ATARI_TRACE_OS=1` narrates the run. Trace summary:

```
OS    365242  Pexec(mode=0, "\AUTO\SSPRINT.PRG", …)      load at step 1 811 361
                                                          basepage $a204, text $a304+$11ccc,
                                                          data $1bfd0+$522, bss $1c4f2+$2b74
OS   1838003  Fopen("init.dat")   / Fread $493e0
OS   1861148  Getrez()  / Super(0) / Super($4db8)
OS   1861479  Setscreen(log=$ffffffff, phys=$ffffffff, rez=0)   (query current)
OS   1896121  Fopen("super1.dat") / Fread
OS   2343479  Fopen("super.dat")  / Fread $493e0   (the 208 KB graphics load)
OS   2779392  Fopen("ssprint.hsc")
OS   2952121  Setscreen(log=$21100, phys=$21100)   \  double-buffered attract loop:
OS   3000158  Setscreen(log=$f8000, phys=$f8000)   /  flip every emulated frame,
              …  periodic Setpalette($1d5d0 / $1d610)   with Vsync-only "hold" phases
              …  in between (title screen sitting still)
```

The loop repeats a ~4.5M-step cycle (≈375 emulated frames), cycling through the
title screen, an in-attract **gameplay demo** (drone cars running Track 1), and the
credits screen. It uses no GEMDOS/BIOS keyboard call (no `Bconstat` / `Cconis` /
`Kbshift` in a 40M-step run) — but it is **not** input-blind: it installs its own
IKBD ACIA interrupt handler at `$104b6` (vector `$118`) that maintains a scancode
key-state table at `-4802(a4)` and a 2-byte joystick-state table at `-4804(a4)`,
and the attract loop polls the joystick table for a fire press.

- `title.png` — framebuffer (`$f8000`, low-res, 16-colour) at step 34 000 000: the
  "SUPER SPRINT / © 1986 Atari Games" logo screen (F1 car bursting through), correct.
- `gameplay.png` — the overhead Track 1 attract demo (drone cars mid-lap): correct
  playfield, cars, barriers, trees, shadows, `TRACK 1` / `DRONE LAP` text.

## Driving it into a race (55th pass)

The IKBD handler at `$104b6` decodes the IKBD "joystick event reporting" packet
format: a `$FE` (joystick 0) or `$FF` (joystick 1) header byte, then one state
byte (bit 7 = fire, bits 0–3 = directions), and stores the state byte at
`-4804(a4)` / `-4803(a4)`. Keyboard bytes go through the same handler into
`keytable[scancode]` (`$3` on make, bit 0 cleared on break). A helper at `$105a0`
reads "input channel N": N=0 synthesises a joystick byte from specific keys
(`$1E`/`$2C`/`$26` → left, `$20`/`$2D`/`$28` → right, LShift/RShift/Alt → fire —
no accelerate bit), N=2/3 return the raw joystick-0/1 bytes. The menu maps player
0 to channel 0 (keyboard), players 1–2 to the joysticks.

So a run driven purely by injected IKBD packets (`kbd` in the REPL, or
`ATARI_KEY_INPUT`):

1. **attract → track select:** inject `fe 80` (joystick-0 fire). The game runs
   `Supexec($f988)` (installs the VBL + Timer B raster handlers) and
   `Supexec($12b9c)` (PSG sound init) and draws the **SELECT TRACK** screen —
   `trackselect.png`.
2. **join players:** `kbd 2a` (LShift = keyboard fire) adds player 0; `fe 80` adds
   a joystick player. Each joined slot switches from "PRESS ACCELERATE TO PLAY" to
   "PREPARE TO RACE" and the screen becomes the three-cars ready screen with a
   countdown — `prepare.png`.
3. **race:** the countdown expires, the game flood-fills the track bitmap into a
   collision map (`$15080`), and Track 1 starts — `race.png`: correct playfield,
   HUD (`BLUE CAR` / `RED CAR` / `DRONE` lap panels), grandstands, trees, the drone
   car doing timed laps. Stable over 15M+ steps of racing.

The road/sky palette is flat, not banded — see the raster-split caveat at the top.

## Playing it from the live window (56th pass)

The 55th pass left the human car sitting on the grid: the SDL2 window fed the
keyboard and mouse into IKBD but never sent a joystick report, and the keyboard
synth (channel 0) has no accelerate bit. `Video.fs` now also emits a joystick-0
report (`$FE` + state byte, coalesced to one packet per frame on any key edge,
exactly like the mouse packet) from the arrow cluster:

| host key | joystick bit | effect |
|----------|-------------|--------|
| Up arrow    | `$80` (fire) | **accelerate** — Super Sprint reads the fire bit as the gas pedal |
| Left arrow  | `$04`        | steer left |
| Right arrow | `$08`        | steer right |
| Down arrow  | `$02`        | joystick "down" (unused by Super Sprint; brake/reverse in games that read it) |

So from the window: boot with `--disk-a "Super Sprint.ST"`, tap **Up** once to
leave attract, tap **Up** again to join as the joystick player (the centre "PRESS
ACCELERATE TO PLAY" slot, channel 2), wait out the countdown, then hold **Up** to
drive and **Left**/**Right** to steer.

Verified headlessly through the same `EnqueueIkbd` path: injecting `fe 80` in a
race puts `$80` in the joytable at `-4804(a4)` and the joined car pulls off the
grid; `fe 00` leaves it parked. Holding fire with periodic `fe 84` / `fe 88`
steering drives the red player car a full lap of Track 1 (grid → up the left side
→ across the top → down the right → along the bottom → back past the gantry, DRONE
LAP advancing 0→2) with no instruction wall. `race.png` is a real frame from that
run — the red car on the top straight approaching a wrench bonus, drones spread
around the circuit.

### The "status bar glitch" — investigated 53rd pass, not an emulator bug

The 52nd pass flagged the top band (the three `BLUE/RED/YELLOW CAR` panels with
their lap-time readouts) as "garbled multicolour pixels". It isn't a rendering
fault: that band is the **grandstand crowd** — hundreds of 1–2px spectator sprites
on white bench rows, drawn by the glyph/sprite blitters at `$152xx`–`$154xx`. At
320×200 shown small it reads as speckle; zoom in and it is a coherent crowd, and it
is drawn identically across all three panels (a decode bug would corrupt them
unevenly — it doesn't). Every text glyph, the lap-time digits, the car icons and
the whole playfield render correctly, and the CPU selftest wrong-answer lane is
unchanged. Confirmed by tracing every write into `$f8000`+`$21100` rows 0–29 over
several frames: the only writers are that crowd/glyph blitter and the per-frame
dirty-rect restore (`movem.l` copy at `$14252` from the offscreen HUD stash at
`$59736`) — no stray blit, no wrong screen base, no half-applied `Setpalette`.
(The RED/centre panel showing a clean readout box + a TV-monitor icon while the
other two sit on crowd texture is the intended attract layout, not a defect.)

## How the CFG was built

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_EVENTS=ss_events.bin \
  dotnet exec bin/Debug/net8.0/M68000.dll 30000000 --disk-a "Super Sprint.ST"

python tools/trace_cfg.py ss_events.bin --steps 1811361 12000000 \
  --range a300 1c000 --names supersprint.sym \
  --callgraph callgraph.dot --blocks blocks.txt
python tools/trace_cfg.py ss_events.bin --steps 1811361 12000000 \
  --range 15300 16800 --names supersprint.sym --cfg cfg.dot
dot -Tsvg callgraph.dot -o callgraph.svg
dot -Gnslimit=1 -Gmclimit=1 -Tsvg cfg.dot -o cfg.svg   # iteration caps: the
                                                        # auto-named graph is wide
```

`ss_events.bin.basepages.json` records the load at step 1 811 361. The step window
`1811361 12000000` covers the load, all five file reads and the first full attract
cycle. `blocks.txt` is scoped to the program's own address range (`$a304`–`$1bfd0`)
plus the handful of TOS trap-handler blocks its GEMDOS/BIOS calls return through.
`cfg.dot` is scoped tighter, to `$15300`–`$16800`, one of the densest regions of
the attract-mode logic (the `$153xx` and `$165xx`–`$167xx` clusters).

## What the artefacts show

- **`supersprint.sym`** — only four names are defensible without a symbol table:
  `entry` (`$a304`, `jmp $a562`), `crt0` (`$a562`: `movea.l 4(a7),a5` / basepage
  walk / `Mshrink` / … — a textbook C runtime startup), `thunk_table`
  (`$a30a`…`≈$a560`, a run of `jmp xxxxxx.l` trampolines the game calls indirectly
  via `jsr d(a5)` with `a5` = basepage + `$100`), and `hot_driver` (`$1399e`), the
  per-frame worker.
- **`callgraph.svg`** — the thunk table fanning out to the real routines, and
  `hot_driver` driving the frame: it calls the `$a394 → $111fa` thunk 548× and the
  `$a39a → $105a0` thunk 1500× over the traced window. `sub_fc0748` (the TOS trap
  dispatcher) and `timer_c_handler` show as the ROM/IRQ leaves.
- **`cfg.svg` / `blocks.txt`** — 783 executed basic blocks. The `$a3xx` blocks are
  all single `jmp`s (the thunk table); the real straight-line and loop structure is
  in `$14000`–`$17000`. `blocks.txt` doubles as the coverage map: this is exactly
  the slice of the 72 KB program the intro/attract path exercises.

## Files

| file | what |
|------|------|
| `supersprint.sym` | `addr<TAB>name` sidecar (`trace_cfg.py --names`) — 4 entries |
| `callgraph.dot` / `callgraph.svg` | call graph, whole program |
| `cfg.dot` / `cfg.svg` | control-flow graph, `$15300`–`$16800` |
| `blocks.txt` | executed basic-block table with hit counts (coverage map) |
| `title.png` | framebuffer at step 34 000 000 — the "SUPER SPRINT / © 1986 Atari Games" logo screen |
| `gameplay.png` | framebuffer during the in-attract Track 1 drone-car demo (the top band is the grandstand crowd, not a glitch — see above) |
| `trackselect.png` | the **SELECT TRACK** screen, reached from attract by injecting a joystick fire press (55th pass) |
| `prepare.png` | the three-cars "PREPARE TO RACE" ready screen with the pre-race countdown (55th pass) |
| `race.png` | a live Track 1 race frame — the red player car mid-lap on the top straight, driven from injected joystick-0 packets (56th pass); HUD lap panels, grandstands, drones spread round the circuit |
| `raster_split.png` / `raster_flat.png` | the "PREPARE TO RACE" ready screen rendered with the per-scanline Timer B palette split vs one flat palette (63rd pass) — the split is what colours the three ready-cars blue / yellow / red |
| `gfxview.md` + `gfx_*.png` | looking at the palettes and decoded bitmaps in RAM with `tools/gfxview.py` (54th pass) — the `$1d3xx` title-fade palette ramp, a whole-RAM contact sheet, the title bitmap decoded from `$f8000` |

The game binary and `Super Sprint.ST` are **not** included; see above to rebuild.
