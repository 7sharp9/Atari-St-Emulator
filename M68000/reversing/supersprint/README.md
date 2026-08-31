# supersprint — a real 1986 commercial game running to its attract mode

The first **commercial** disk-loaded program the emulator runs, as opposed to the GPL
Hatari test binaries in `../int_test/` and `../gmdostst/`. Super Sprint's `\AUTO\SSPRINT.PRG`
loads through the real TOS 1.00 ROM, pulls in its data files, and runs its
intro/credits sequence and double-buffered attract loop indefinitely with no
instruction wall and no crash.

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

Two commits, both plain addressing-mode gaps, both routed through the shared EA
decoder (`x.ResolveEa` / `x.ReadEa` / `x.WriteEa`) — the same migration the
45th–49th passes did for the other instruction families. **No cycle-scheduler
work**; the game's attract loop is driven entirely by `Vsync` / VBL counting,
which the instruction-counted timing already models.

| commit | wall | fix |
|--------|------|-----|
| `2d466ce` | `jsr $cc(a5)` (JSR eamode 5); later `mulu.w #4,d1` (MULU immediate) | JSR/JMP and the MULU.w/MULS.w source operand onto the shared EA decoder |
| `ccbae25` | `addq #n,(d8,An,Xn)` (ADDQ eamode 6) | ADDQ/SUBQ onto the shared EA decoder (new `x.AddSubQ` helper) |

## How it was run

```
unzip "Super Sprint.zip"
ATARI_NOTRACE=1 ATARI_TRACE_OS=1 ATARI_DISK_A="Super Sprint.ST" \
  dotnet exec bin/Debug/net8.0/M68000.dll 40000000
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

The loop repeats a ~4.5M-step cycle (≈375 emulated frames) of animation-burst then
hold, forever. The game **never polls the keyboard** (no `Bconstat` / `Cconis` /
`Kbshift` anywhere in a 40M-step run) — it is a pure timed attract sequence.
`title.png` is the framebuffer (`$f8000`, low-res, 16-colour) dumped at step
27 900 000: the "SUPER SPRINT / Software Studios / a Software Studios production /
TM © 1986 Atari Games, licensed to Electric Dreams" credits screen, rendered
correctly.

## How the CFG was built

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_DISK_A="Super Sprint.ST" \
  ATARI_TRACE_EVENTS=ss_events.bin dotnet exec bin/Debug/net8.0/M68000.dll 30000000

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
| `title.png` | framebuffer at step 27 900 000 — the rendered credits screen |

The game binary and `Super Sprint.ST` are **not** included; see above to rebuild.
