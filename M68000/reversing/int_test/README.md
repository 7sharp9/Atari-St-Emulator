# int_test: a 68000 integer-instruction test program

`int_test.tos` is a test program from the Hatari emulator project (GPL v2). It runs 30 small tests of the
68000's integer instructions (ABCD, ADD and its variants, the shifts), prints `OK` or `FAILED` for each, and
exits. It is not a game. It was used here because a correct emulator must pass every test: on this emulator it
runs to completion and passes all 30. It was also the first third-party program loaded from a disk image, and
its control-flow graph (which blocks of code ran and how they connect) was rebuilt from the emulator's log of
calls and branches alone.

Where to find what:

- What does the program do, test by test? "The program" below.
- How was the disk image made and the program run? "How the disk was built", "How it was run".
- What do the call graph and flow graph show? "What the artefacts show".

Terms used here are defined in `../GLOSSARY.md`. This directory was milestone 2 of the repo's early reversing
goals (the only record is the commit message of the commit that added it).

## The program

`int_test.tos` — the CPU integer-arithmetic test from the Hatari source tree
(`tests/cpu/int_test.c` + `int_*.s`), GPL v2, unmodified. A plain single-file GEMDOS
executable: no resource file, no overlay, no protection, no native-feature calls. `main()`
walks a `tests[]` table of 30 functions (`tst_abcd_1` … `tst_shift_8`), printing
`Test '<name>'\t: OK|FAILED\n` for each via `Cconws`, and returns `!(failures == 0)`.

It exercised ABCD (packed decimal add; the emulator had not implemented it, so the first run stopped at the
program's first test until commit `f5ee4d2` added it), ADD/ADDI/ADDQ/ADDX and the
shift group, and **passed every test** (`Pexec mode=0 returned d0=$00000000`).

## How the disk was built

```
cp <hatari>/tests/cpu/int_test.tos .
python tools/make_blank_disk.py inttest_disk.st
python tools/add_file_to_disk.py inttest_disk.st int_test.tos --name INTTEST.PRG --auto
```

`.TOS` is renamed to `.PRG` because TOS only auto-runs `\AUTO\*.PRG`; the file format is
identical.

## How it was run

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 \
ATARI_DISK_A=inttest_disk.st \
ATARI_TRACE_EVENTS=inttest_events.bin \
dotnet exec bin/Debug/net8.0/M68000.dll 12000000
```

TOS boots, reads boot/FAT/root/AUTO/program sectors, `Pexec(0)` loads `\AUTO\INTTEST.PRG`
at basepage `$a204` (text `$a304`, len `$37e`), runs it, it `Pterm`s, and TOS proceeds to
the desktop. `inttest_events.bin.basepages.json` records the load at **step 1 870 804**;
the program's own code executes over **steps ≈1 870 836 – 2 255 910** (~385 k instructions),
after which the RAM is reused by the desktop.

## How the CFG was built

```
python tools/trace_cfg.py inttest_events.bin \
  --steps 1870836 2260000 --range a000 c000 \
  --names inttest.sym \
  --cfg cfg.dot --callgraph callgraph.dot --blocks blocks.txt
dot -Tsvg cfg.dot -o cfg.svg
dot -Tsvg callgraph.dot -o callgraph.svg
```

`--steps` isolates this run from the later desktop reuse of the same address range;
`--range a000 c000` drops the ROM `Cconws`/trap plumbing. `inttest.sym` names `main`, the
crt entry and all 30 `tst_*` functions from the `tests[]` order in `int_test.c`.

## What the artefacts show

- **`callgraph.svg`** — `crt0 → main`, then `main` fanning out to the 30 `tst_*` functions
  (each called once, in table order) and to `Cconws_rom` (`$fc4cee`) 120 times = 4 console
  writes per loop iteration × 30.
- **`cfg.svg` / `blocks.txt`** — the `for (idx = 0; tests[idx].name; idx++)` loop as a
  single hot back-edge (`$a358` `beq`, taken 31×), its body of three `Cconws` trap blocks
  and the indirect `jsr (a2)` to `tests[idx].testfunc` at `$a38a`, and the `if (… != 0)`
  branch at `$a398`. Each `tst_*` block is a straight run to `rts`, hit once.

## Files

| file | what |
|------|------|
| `int_test.tos` | the program (GPL, from Hatari `tests/cpu/`) |
| `inttest_disk.st` | 360 KB single-sided FAT12 image, `\AUTO\INTTEST.PRG` |
| `inttest.sym` | `addr<TAB>name` sidecar (`trace_cfg.py --names`) |
| `cfg.dot` / `cfg.svg` | control-flow graph |
| `callgraph.dot` / `callgraph.svg` | call graph |
| `blocks.txt` | executed basic-block table with hit counts |
