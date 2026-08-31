# gmdostst — reversing-goal milestone 3 artefact

Second real, third-party, disk-loaded program run to completion on the emulator, and
the first one that **writes to the floppy**: it exercises the FDC Write Sector path
added in commit `53f6c1a`.

## The program

`gmdostst.tos` — the GEMDOS test from the Hatari source tree
(`tests/gemdos/gmdostst.c` + `get_sr.s`, built with AHCC per `gmdostst.prj`), GPL v2,
unmodified. A plain single-file GEMDOS executable: no resource file, no protection.
`main()` walks a `tests[]` table of three functions, printing
`Test '<name>'\t: OK|FAILED\r\n` for each via `Cconws`, and returns `!(failures == 0)`.

| test | GEMDOS surface it drives |
|------|--------------------------|
| `tst_directories` (`paths`) | `Dgetpath`, `Dcreate` (incl. the `-36 EACCDN` "exists" case), `Dsetpath`, `Ddelete`, `..`, root |
| `tst_files` (`files`) | `Fcreate`, `Fwrite`, `Fclose`, `Fopen`, `Fread`, EOF, `Fdelete` |
| `tst_sys` (`sys`) | `Super(1)` / `Super(0)` / `Super(old)` user⇄supervisor transitions, `get_sr` |

The directory-create and file-write paths make TOS 1.00's GEMDOS do real
read-modify-write cycles on the FAT and directory sectors (`Rwabs` mode 0 then mode 1),
so this is a Write Sector workout as much as a control-flow target. It **passed every
test** — `Pterm(rc=0)`, three `OK` lines, no `FAILED`.

## How the disk was built

```
cp <hatari>/tests/gemdos/gmdostst.tos .
python tools/make_blank_disk.py gmdostst_disk.st
python tools/add_file_to_disk.py gmdostst_disk.st gmdostst.tos --name GMDOSTST.PRG --auto
```

`.TOS` is stored as `.PRG` because TOS only auto-runs `\AUTO\*.PRG`; the file format is
identical. The image is single-sided 80×9 FAT12 and is **never modified by a run** —
FDC writes land in the emulator's in-memory copy only (see `MMU.tryWriteSector`), so
this file stays byte-reproducible from the two commands above.

## How it was run

```
ATARI_NOTRACE=1 ATARI_TRACE_OS=1 ATARI_TRACE_FDC=1 \
ATARI_DISK_A=gmdostst_disk.st \
dotnet exec bin/Debug/net8.0/M68000.dll 12000000
```

`ATARI_TRACE_OS=1` narrates the run: `Dcreate("TESTDIR")`, `Fwrite(h=6, count=$18, …)`,
`Super(stack=$0)` etc. with the `D0` return (and GEMDOS error name for negatives)
against each call. `ATARI_TRACE_FDC=1` shows the `read`/`write` sector traffic each
GEMDOS call generates.

Trace tail (the three tests passing):

```
OS   1935641     Cconws(" OK\r\n")        <- paths
OS   1990262     Cconws(" OK\r\n")        <- files
OS   1999034     Cconws(" OK\r\n")        <- sys
OS   2000646     Pterm(rc=0)
```

## How the CFG was built

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 \
ATARI_DISK_A=gmdostst_disk.st ATARI_TRACE_EVENTS=gmdostst_events.bin \
dotnet exec bin/Debug/net8.0/M68000.dll 3000000

python tools/trace_cfg.py gmdostst_events.bin \
  --steps 1868139 2005000 --range a000 c000 \
  --names gmdostst.sym \
  --cfg cfg.dot --callgraph callgraph.dot --blocks blocks.txt
dot -Tsvg cfg.dot -o cfg.svg
dot -Tsvg callgraph.dot -o callgraph.svg
```

`gmdostst_events.bin.basepages.json` records the load at **step 1 868 139** (basepage
`$a204`, text `$a304+$61c`); the program's own code executes over
**steps ≈1 868 139 – 2 005 000**, after which TOS returns to the desktop and reuses the
address range. `--steps` isolates this run; `--range a000 c000` drops the ROM
`Cconws`/trap plumbing.

`gmdostst.sym` names the entry, the three test functions, `main`, and the four libc
helpers linked in (`get_sr`, `strcmp`, `strlen`, `memcmp`), identified from the call
graph shape and confirmed by disassembly (`get_sr` = `move sr,d0 / rts` at `$a8c6`).
Layout follows the source order in `gmdostst.c`: the tests are defined before `main`,
so `main` sits *after* them at `$a840`.

## What the artefacts show

- **`callgraph.svg`** — `crt0 → main`, `main` calling `tst_directories` / `tst_files` /
  `tst_sys` once each in table order, and `Cconws_rom` (`$fc4cee`) 43 times
  (15 + 12 + 9 + 5 + 2). `tst_directories` calls `strcmp` ×3 and `strlen` ×1;
  `tst_files` calls `memcmp` ×1; `tst_sys` calls `get_sr` ×1.
- **`cfg.svg` / `blocks.txt`** — `tst_directories` is one long straight-line function
  (`$a344`–`$a5f0`): a chain of `trap #1` blocks each followed by a `beq`/`ble` guard
  that bails to a `Cconws(<label>) ; return` on any unexpected GEMDOS result. The
  `main` loop (`$a854` `beq`, taken 4×) has its three-`Cconws` body, the indirect
  `jsr (a2)` to `tests[idx].testfunc` at `$a886`, and the `if (… != 0)` failure branch
  at `$a894`. The `strcmp`/`memcmp`/`strlen` helpers show their small back-edge loops
  (`$a8ce`/`$a904` etc.).

## Files

| file | what |
|------|------|
| `gmdostst.tos` | the program (GPL, from Hatari `tests/gemdos/`) |
| `gmdostst_disk.st` | 360 KB single-sided FAT12 image, `\AUTO\GMDOSTST.PRG` |
| `gmdostst.sym` | `addr<TAB>name` sidecar (`trace_cfg.py --names`) |
| `cfg.dot` / `cfg.svg` | control-flow graph |
| `callgraph.dot` / `callgraph.svg` | call graph |
| `blocks.txt` | executed basic-block table with hit counts |
