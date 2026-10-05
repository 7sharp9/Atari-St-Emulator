# Final Fight (Capcom CPS1, 1989), reverse-engineering workspace

First arcade subject in this repo. Target set: MAME `ffightuc` (Final Fight, USA 900613), a clone of
`ffight`. MAME 0.289 is the emulator and oracle; the F# core is not involved. The ST tooling that
carries over is the 68000 disassembler (`tools/disassemble.py`, `--rom <flat image> --base 0`) and the
method (census, callcap, gates, claims need a match count).

## ROMs (not committed)

| file | sha256 | role |
|---|---|---|
| `ffight.zip` | `a7cc8894...7eab` | parent set: gfx (`ff-1m/3m/5m/7m`), OKI samples, `ff-32m.8h` (program ROM at `$080000-$0fffff`, not a bank ROM), PLD dumps |
| `ffightub.zip` | `b9f8098e...e49c2` | misnamed: its CRCs are the **`ffightuc`** program ROMs + Z80 `ff_23.12b`, not MAME 0.289's `ffightub` |

MAME looks for `ffightuc.zip` beside `ffight.zip`, so the second file is copied to
`~/mame-roms/ffightuc.zip` (`ffmame.sh` reads `$FF_ROMS`, default `~/mame-roms`). `mame -verifyroms
ffightuc` reports "good" with both present.

## Running

`./ffmame.sh callcap` (spec in `$CALLCAP_SPEC`) or `./ffmame.sh script <file.lua>`. It runs MAME with
`-debug -debugger none -video none -sound none`, which gives Lua a working debugger without a window,
at about 18x real time. MAME's cfg/nvram/state go under `scratchpad/finalfight/run/`.
`lua/dumprom.lua` (`FF_OUT=<dir>`) writes `ff_main.bin` (68000 space `$000000-$0fffff`, sha256
`8535dd51...e6ec`) and `ff_z80.bin` (sound CPU `$0000-$7fff`) for static work:

```
python3 tools/disassemble.py --rom <abs path>/ff_main.bin --base 0 --linear 5e88c 24
```

## Harness facts (checked on this build, MAME 0.289)

- Lua sees the debugger only under `-debug`; `-debugger none` keeps it headless.
- `emu.register_periodic` runs about once per frame **and keeps running while the CPU is stopped on a
  breakpoint**; `dbg.execution_state` is `"stop"` then. There is no `emu.register_pause`; the 0.289
  names are `emu.add_machine_pause_notifier` / `..._resume_notifier`.
- While stopped, `cpu.state["PC"]` reads **2 above** the breakpoint address (`$540` for `bpset 53e`);
  `cpu.state["CURPC"]` is the instruction address. Compare on `CURPC`.
- The stack pointer is `SP` (no `A7`). Registers: `D0-D7 A0-A6 SP USP SR PC CURPC`.
- Setting registers from a periodic callback while the CPU free-runs did not take (PC stayed in the
  idle loop, sentinel never reached). `callcap.lua` therefore stops the CPU at the VBL entry `$53e`
  once per frame, and sets the call up only after `warm` frames of that.

## callcap

`lua/callcap.lua` is the MAME counterpart of the ST `callcap`: warm up, stop at the VBL entry, apply
`regs`/`pokes`, push a sentinel return address, run with `SR=$2700` until the sentinel, then print
`regdelta` and `mem` lines (work RAM and gfx RAM diffed by default). Spec format is in the file header.
Validated on `$50e` (`lua/specs/validate_50e.lua`): the code writes `D0+$4400` to 32 words at
`$908500`, stride 4, when `142(A5)==0`, `132(A5)!=0` and bit 6 of `100(A5)` is set (`A5=$ff8000`).
Live: 32/32 words written (the odd bytes `20`→`53`; the even bytes were already `44`), `D0=$4453`,
`D7=$ffff`, `A0=$908580`, nothing else changed. The negative control with `142(A5)=1`
(`validate_50e_gated.lua`) returns with an empty diff. The check covers one routine in the attract
mode; it does not yet cover a routine that sleeps, yields (`trap #4/#5`) or waits on a VBL flag.

## Hardware and boot

The hardware reference is `hardware.md` (read from `cps1.cpp` 0.289, every address with a source line
and a tag for what the ROM confirms). What the rest of this README depends on: `ffightuc` is board
89624B-3 with **CPS-B-05** (layer control `$800168`, priority masks `$80016a-$800170`, palette control
`$800172`, ID register `$800160` reads `$0005`), not the `CPS_B_04` of `ffight`/`ffightu`; the ROM's
own writes match B-05. The 68000 map is program ROM `$000000-$3fffff` (including `ff-32m.8h` at
`$080000`, no main-CPU bank switching), inputs `$800000` (IN1 word, P1 low byte, P2 high byte) and
`$800018-$80001e` (IN0, DSWA/B/C bytes), coin control `$800030`, CPS-A `$800100-$80013f`, CPS-B
`$800140-$80017f`, sound latches `$800180`/`$800188`, gfx RAM `$900000-$92ffff`, work RAM
`$ff0000-$ffffff`. VBL is one interrupt at scanline 240 (IPL1, vector `$68` by autovector convention,
unconfirmed in the source); there is no raster interrupt on this board. Z80: ROM `$0000-$7fff`, banked
`$8000-$bfff`, RAM `$d000`, YM2151 `$f000`, OKI `$f002`, bank `$f004`, latches `$f008`/`$f00a`.

From the ROM: SSP `$00ff1000`, reset PC `$0005e88c`; the reset code clears the sound latch and coin
registers, then programs the CPS-A layer base pointers (`$800100..$80010e`); VBL vector `$68` ->
`$53e`, which latches scroll registers into CPS-A/B, calls `$984`, `$fac`, `$e46`, then runs a
countdown over 16 sixteen-byte records at `-28672(A5)` (`$ff1000`): state byte 1 counts down to state
4. The idle loop sits in `$7f6-$8c0`. `trap #4/#5` appear at `$8b6`/`$8de`. Reading: a small
cooperative/preemptive task kernel with 16 task control blocks (state, timer, saved SR/PC/USP at
`+2/+4/+8`). **Inferred from code only**; prove it with `callcap` on the trap handlers and a `watch`
on the record states before it goes in a topic doc.

## Next

1. Prove the task kernel (`$7f0-$8c0`; the handlers of `trap #4`/`#5`, vectors 36/37 at `$90`/`$94`,
   not read yet) live, then name its states.
2. Census the object/entity pool the tasks drive and find the game's own readers before naming fields
   (the CLAUDE.md rules on census columns apply unchanged).
3. Graphics: the four 512 KB gfx ROMs load at offsets 0/2/4/6 in `-listxml`, so they are interleaved
   (tile format not yet decoded; MAME's gfx layout in `cps1.cpp` is the reference). Render a sprite
   sheet and commit the PNG with the doc that proves the decode.
