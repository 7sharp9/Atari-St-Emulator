# a_013 — a bootable multi-game menu disk, packed games and all

`A_013.ST` is a **bootable** "Automation"-style compilation disk: a custom 68k boot
sector, an `\AUTO\MENU13.PRG` menu, and four crunched games. It is the first disk
the emulator runs that is *booted* rather than loaded through a `\AUTO\*.PRG`. The
delivery chain (boot sector → menu → game select → in-place LSD depack → running
game) needs **no emulator code change** — the real TOS ROM does the sector-0
`$1234` boot and the depackers are plain 68000.

**Menu game 2, Super Sprint** (`SPSPRINT.WAS`) is a packed copy of the engine
`../supersprint/` already drove, so it runs straight through to its attract loop
and track-select. **Menu game 1, Super Hang-On** (`SPHANGON.WAS`) is a different
engine and did need seven general 68000/ST fixes (commit after `5f33079`) to
reach its title screen — see "Menu game 1: Super Hang-On" below.

## The disk

```
A_013.ST   sha256 46d425eb7491a725368c882887d23f449e66e90a5a3dc81a293104d1657a54fa   755712 bytes
```

720 KB FAT12, 80 track / 9 sector / 2 head, **bootable**: boot-sector word-sum is
`$1234` and the first bytes are `60 1c` (`bra.s $1e`). The boot code itself pokes
the palette (`lea $ffff8240,a6` / `move.w #$777,$1e(a6)` at sector offset `$20`)
and chains into normal TOS AUTO-folder execution.

**Not committed** — commercial payloads, `.gitignore`d. Root directory:

| file | size | what |
|------|-----:|------|
| `\AUTO\MENU13.PRG` | 7895 | the menu (LSD-packed — unpacks itself at boot) |
| `INIT.DAT` | 3644 | shared game data |
| `SUPER.DAT` | 105168 | shared graphics |
| `SUPER1.DAT` | 8136 | shared data |
| `SSPRINT.HSC` | 295 | Super Sprint high-score table |
| `SPHANGON.WAS` | 404098 | Super Hang-On, crunched |
| `SPSPRINT.WAS` | 40352 | **Super Sprint, crunched** (cf. `Super Sprint.ST`'s plain 74355-byte `SSPRINT.PRG`) |
| `STKARATE.WAS` | 110396 | ST Karate, crunched |
| `POOL1/2/3.WAS` + `ELECPOOL.BOB` | | Electronic Pool, crunched |

## The boot chain

```
step        event
      ~0     real TOS 1.00 ROM loads boot sector 0, verifies word-sum $1234, jsr's to it
  ~334 000   the "LSD"/LGD boot sector prints  "…The Little Green Desktop…
             http://lgd.fatal-design.com"  (Cconws), installs a resident hook, RTS
             (the hook reprints the banner ~7× through the rest of TOS init)
 6 522 486   TOS AUTO execution: Pexec(mode=5 "") then Pexec(mode=4) — create + go
 6 536 967   Pexec(mode=0, "\AUTO\MENU13.PRG")   basepage $a204, text $a304+$1eaa
 8 036 082   MENU13 Mshrink / Super / Setscreen(log=phys=$78000, rez=0)
             — MENU13 decompacts itself in place (hot loop $a458, bit reader $a5f4)
             then renders the menu and enters a Crawio($ff)+Vsync() key-poll idle
--- inject IKBD "2" ($03 make / $83 break) ---
10 048 236   MENU13: Bconin(2)=$00030032, Setscreen(-1,-1), Super($4db8),
10 048 283   Pexec(mode=0, "spsprint.was")   (pc=$a532)
11 511 813   SPSPRINT.WAS crt0 ($c446): Mshrink(block=$c1b0), Setscreen($78000)
11 536 419   Cconws("         LSD DECOMPACTER  V 1.0 …  WAS (NOT WAS) Proudly…")
             — the LSD depacker ($c55c) unpacks the game backwards into low RAM
13 454 809   Super($4db8), Mshrink(block=$1151a, newsiz=$16e62) — game now at ~$11000
13 480 875   SSPRINT engine start: Malloc($4bbf0), Fopen("init.dat"), Getrez(),
             Supexec($177a0) → Mfpint(6, $177cc)  (installs the IKBD handler),
             Fopen("super1.dat"), Setpalette, double-buffered attract loop
             ($28400 ↔ $78000 per frame) — Track 1 drone-car demo
```

Runs to 90M+ steps with no instruction wall, no loop-detector trip, no crash. The
attract demo renders correctly (`attract.png`). Injecting joystick-0 fire
(`kbd fe 80`) + keyboard fire (`kbd 2a`) walks it to the **SELECT TRACK** and
**PREPARE TO RACE** screens (`prepare.png`), exactly as `../supersprint/`
documents for the unpacked build — it is the same engine at a different load
address.

### Why no emulator change was needed

- **Boot sector**: the real TOS ROM does the sector-0 load / `$1234` check / jump.
  The emulator only has to serve the sectors, which the FDC has done since the
  44th pass. No "boot-sector-execution path" in emulator code — the earlier
  worry (52nd-pass notes) was unfounded.
- **The depackers** (MENU13's self-unpack and the `.WAS` LSD depacker) are plain
  68000: `move.l -(A0),D0` / `lsr.l #1,D0` / `roxl`/`roxr` bit-pump, `eor.l D0,D5`
  running checksum, `move.b D2,-(A2)` backward store, `bsr` to a longword-refill
  helper. Every opcode was already implemented. They are also **not** cycle-timed
  — no `$ffff8209` read-loop, no VSYNC-counted delay — so instruction-counted
  timing runs them fine.
- **Rwabs / FAT12** on this double-sided disk works: `recno=11` (track 0, side 1,
  sector 3) and every higher logical sector read back correctly through the
  existing `.ST` side-interleave in `MMU.tryReadSector`.

## The LSD depacker ($c55c, "LSD DECOMPACTER V 1.0")

A textbook backward LZ/RLE cruncher. Disassembly of the core (from a RAM image of
the running game):

```
c55e  movem.l (a0)+,d0/d1/d5        ; header: src adjust, dst size, checksum seed
c562  movea.l a1,a2                 ; a1 = dst base (from the crt0)
c564  adda.l  d0,a0  /  adda.l d1,a2 ; point src and dst at the END (unpacks down)
c568  move.l  -(a0),d0              ; prime the 32-bit control word
c56a  eor.l   d0,d5                 ; running checksum
loop:
c56c  lsr.l   #1,d0  /  bne .+6  /  bsr c600   ; next control bit (refill if empty)
c574  bcs     c5ac                             ; 1 => match, 0 => literal run
      … literal: read a 3-bit then 7-bit length, copy that many bytes via move.b d2,-(a2)
c5ac  … match:  read a 2-bit selector (c5b0), then 9/12/8-bit length + offset, copy
c600  move.l  -(a0),d0 / eor.l d0,d5 / move #$10,ccr / roxr.l #1,d0 / rts   ; refill longword
c60c  subq.w #1,d1 / (lsr.l #1,d0 ; refill ; roxl.l #1,d2) x N / rts        ; read d1+1 bits into d2
```

`MENU13.PRG` carries the identical routine at `$a5f4` (read-bits) / `$a458`
(copy loop) — the menu is LSD-packed too and unpacks itself before it draws.

## How it was run

```
# headless, narrated:
ATARI_NOTRACE=1 ATARI_TRACE_OS=1 \
  dotnet exec bin/Debug/net8.0/M68000.dll 12000000 --disk-a A_013.ST
# then in a REPL run, at the menu idle loop, inject the game-2 key:
#   kbd 03    (scancode 2 make)
#   kbd 83    (scancode 2 break)
# and keep stepping.
```

`./run.ps1 window -DiskA A_013.ST` boots it in the live SDL2 window; press `2` at
the menu, then drive with the arrow keys (Up = accelerate — see `../supersprint/`).

## How the CFG was built

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_EVENTS=a013_events.bin \
  dotnet exec bin/Debug/net8.0/M68000.dll <repl> --disk-a A_013.ST
#   (REPL: s 10000000 ; kbd 03 ; kbd 83 ; s 40000000 ; q)

python tools/trace_cfg.py a013_events.bin --steps 320000 13600000 --range 400 40000 \
  --names reversing/a_013/a013.sym \
  --callgraph reversing/a_013/callgraph.dot --blocks reversing/a_013/blocks.txt
python tools/trace_cfg.py a013_events.bin --steps 8036082 10048283 --range a304 c1ae \
  --names reversing/a_013/a013.sym --cfg reversing/a_013/cfg.dot
dot -Gnslimit=1 -Gmclimit=1 -Tsvg reversing/a_013/callgraph.dot -o reversing/a_013/callgraph.svg
dot -Gnslimit=1 -Gmclimit=1 -Tsvg reversing/a_013/cfg.dot       -o reversing/a_013/cfg.svg
```

`cfg.dot` is scoped to MENU13's own text (`$a304`–`$c1ae`) in the menu step window;
`callgraph.dot` / `blocks.txt` span boot → menu → depack (`$400`–`$40000`). The
1-instruction "(interrupt)" blocks in the CFG are Timer-C ticks splitting a real
block, not distinct code.

## Menu game 1: Super Hang-On

Selecting `1` at the menu (`kbd 02` / `kbd 82`) runs `SPHANGON.WAS` through the
same `$c55c` LSD depacker, then a genuinely different engine from Super Sprint.
It walled seven times on the way to a running program — every wall a general
68000/ST gap, none Hang-On-specific:

| # | wall | fix |
|---|------|-----|
| 1 | `adda.l (a0)+,an` in the `.WAS` depacker (ADDA.L eamode 3) | ADDA.W/.L onto the shared EA decoder; the old hand-rolled `.L` ladder had no `(An)+` / `-(An)` / `(d8,An,Xn)` |
| 2 | `lea $xxxx.w,an` / `lea d(pc,Xn),an` (LEA eamode 7 regs 0 and 3) | both were `failwith "not implemented"` |
| 3 | music ISR at `$800` never runs → busy-wait on the tick counter at `$89e` hangs | **MFP Timer A** coarse tick (`MMU.RaiseTimerA`, `instructionsPerFrame/64`), gated on `TACR!=0` + `IERA`/`IMRA` bit 5 so TOS never arms it. The ISR is a ~15 kHz software synth; the wait loop reads `(a0)+` timestamps and spins on `cmp.l $89e.w,d6 / bhi` |
| 4 | `movep.w D0,$0(a3)` after `movep.l` (MOVEP opmode 6) | MOVEP: all four opmodes (only `.L` reg→mem existed) |
| 5 | `movep.l Dn,$ffff8800` pokes `$8800/$8802/$8804/$8806`; `$8806` bus-errors → vector-2 loop | PSG decode widened to `$FF8800-$FF88FF` (only bits 0–1 reach the YM2149, so `$FF8804+` mirror `$FF8800-$FF8803` — Hatari `psg.c` says the same) |
| 6 | `move.l $ffff8244,D0` in the raster palette handler bus-errors (ReadLong had no shifter-register case) | added `VideoDisplayRegister` to `MMU.ReadLong` (ReadWord/WriteWord/WriteLong already had it) |
| 7 | `stop #$2100` — opcode `$4e72`, decoded as "unknown instruction" | **STOP** implemented via a new `Cpu.Stopped` flag: `Step()` idles until a pending interrupt outranks the mask STOP loaded into SR, then wakes and takes it |

After all seven, Super Hang-On depacks, initialises, plays its Timer-A music and
renders its title screen correctly (`hangon_title.png` — "SUPER HANG-ON", rider,
"A SOFTWARE STUDIOS PRODUCTION", SEGA, "Press SPACE").

**Where it stops:** pressing SPACE moves it to a post-title screen driven entirely
by a VBL handler (`$15b6`) plus a **Timer-B-event-count raster palette-split**
handler (`$1ae2`–`$1b36`). That handler programs `TBDR` (`$fffffa21`) with a
scanline count and `stop #$2100`s to wait for Timer B to fire exactly that many
HBLs later, walking a per-line palette script. The coarse Timer B this emulator
delivers (~32/frame, not per-scanline, no `TBDR` event counting) can't drive it,
so the script walk never signals "frame complete" and the main state machine —
which is itself `stop`'d waiting for that signal — never advances to the next
screen (it stays black). This is the per-scanline chip scheduler the project has
deliberately not built; the STOP-condition, not a missing instruction.

Run it: REPL `s 10000000` to the menu, `kbd 02` / `kbd 82`, then keep stepping.
The title appears around 100M–150M steps in (most of that is STOP-idle time while
the coarse Timer A music player crawls through the intro sequence).

## Files

| file | what |
|------|------|
| `a013.sym` | `addr<TAB>name` sidecar — 7 defensible names (entry + both LSD depackers) |
| `callgraph.dot` / `.svg` | call graph, boot → menu → depack |
| `cfg.dot` / `.svg` | control-flow graph of MENU13's text during the menu phase |
| `blocks.txt` | executed basic-block table with hit counts (coverage map) |
| `menu.png` | the MENU13 screen — panels overlap (layout is imperfect: an overscan/raster detail the flat timing model doesn't place; the text is all legible) |
| `attract.png` | menu game 2 (Super Sprint) running its Track 1 attract demo |
| `prepare.png` | Super Sprint's "PREPARE TO RACE" screen, reached by injecting joystick + keyboard fire |
| `hangon_title.png` | menu game 1 (Super Hang-On) title screen — reached after the seven fixes above |

Game binaries and `A_013.ST` are **not** included.
