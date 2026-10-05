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

`./ffrun.sh <script.lua>` is the second wrapper: no `-debug`, `-nothrottle` (about 4-8x real time with
RAM dumps), same `scratchpad/finalfight/run/` directories. Use it for input-driven scripts
(`lua/lib.lua`, `ffdrive.lua`, `resume_check.lua`, `ioport_dump.lua`, `kernel_log.lua`); use `ffmame.sh` for `callcap`.
Both wrappers export `SDL_VIDEODRIVER=dummy`: with `-video none` alone macOS still makes `mame` the
frontmost (full-screen-looking) app on every run. A Lua `install_write_tap` handle must be kept in a
global, or a garbage collection silently removes the tap (a short probe never collected, the drive did).

## Driving the game

`FF_SAVE=ff_gameplay ./ffrun.sh $PWD/lua/ffdrive.lua` plays the scripted drive from a cold boot and
saves the state at the end of frame 2200 (about 9 s of wall time; `FF_TRACE=1 FF_TRACE_LO/HI` dumps
work RAM per frame to `<FF_OUT>/tmp/`, `FF_VARIANT=ctl` is the control run without the walk-test
presses, `FF_LOAD=<state>` loads one at frame 1). Inputs are set in `emu.register_frame_done` with
`field:set_value(1/0)`; a level set at the end of frame N is what the game reads from N+1.
`ioport.txt` lists the 36 ioport fields (`:IN0`, `:IN1`, `:DSWA/B/C`, polarity measured: all active low;
Coin 1 reads `$00fe` only from the frame after a multi-frame hold).

| frames | input | result |
|---|---|---|
| 1100-1112 | Coin 1 | `CREDIT =1` on the title screen (credit byte `$ff804d`) |
| 1150-1162 | P1 Start | SELECT PLAYER, cursor on Guy |
| 1250-1256 | Right | cursor on Cody |
| 1280-1292 | Button 1 | confirm Cody |
| 1370-1700 | none | scripted stage intro: Cody walks in and kicks the barrels by himself; Right/Left held at 1500-1580 give identical x at every frame, so input is ignored |
| 1800+ | Right, Left, Up, Down | the walk test below |
| 2040-2195 | Right | Bred appears and grapples Cody; state saved at 2200 (`gameplay.png`) |

A hold-right test before about frame 1700 reads as "input does nothing"; test after the intro.

Proven (`lua/analyze_inputs.py`, per-frame work-RAM trace of frames 1790-2029, reproduced from the
promoted scripts): player x word `$ff856e` changed in 59 of 60 Right frames (steps +1/+2, monotone, the
missing one is the one-frame latency), 39 of 40 Left (-1/-2), 0 on 81 idle frames and 0 in the other
axis's phases; y word `$ff8572` changed in 19 of 30 Up frames and 16 of 20 Down (it clamps at 44..63);
the control run stays at x=194, y=44 over the same frames and its work RAM equals the drive's through
frame 1800 and first differs at 1801. Also seen (names inferred from behaviour, no game reader of them
identified): `$ff805c` rises `$0100`, `$0101` while Right is held (an input shadow?). Named later from
their readers (`frame.md`): `$ff85dc` is Cody's attack-box centre x (`+116` of his record), `$ff85ee` the P1
score (`+134`, BCD in hundreds; `$0300`, `$0600`, `$1600` against HUD 300, 600, 1600 in 6 of 6 screenshots),
`$ff8580` his health (`+24`), `175(A5)` TIME.

Determinism and resume: work RAM at frame 2200 sha256 `79ed3cc1...0b2c` and gfx RAM
`d6fbca5f...d8b0` are identical over three cold boots; a state loaded in
a fresh MAME matches a fresh run's next 6 frames of work RAM byte for byte (6 of 6). The `.sta` file
itself differs by one byte of device state between boots: compare RAM, not the file.

## Harness facts (checked on this build, MAME 0.289)

- Lua sees the debugger only under `-debug`; `-debugger none` keeps it headless.
- `emu.register_periodic` runs about once per frame **and keeps running while the CPU is stopped on a
  breakpoint**; `dbg.execution_state` is `"stop"` then. There is no `emu.register_pause`; the 0.289
  names are `emu.add_machine_pause_notifier` / `..._resume_notifier`.
- While stopped, `cpu.state["PC"]` reads **2 above** the breakpoint address (`$540` for `bpset 53e`);
  `cpu.state["CURPC"]` is the instruction address. Compare on `CURPC`.
- The stack pointer is `SP` (no `A7`). Registers: `D0-D7 A0-A6 SP USP SR PC CURPC`.
- `emu.register_frame_done` works without `-debug`. `manager.machine:save("n")`/`:load("n")` work from
  it (file `<state_dir>/ffightuc/n.sta`; the load applies before the next callback and restores the
  screen frame counter). `screen:snapshot(name)` renders under `-video none` (384x224). Ports:
  `manager.machine.ioport.ports[":IN0"].fields["Coin 1"]:set_value(1)`.
- Not tested: the drive with `-debug` on (`callcap.lua`'s stop at `$53e` may interact with the frame callback).
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
`$53e` latches scroll registers into CPS-A/B, reads the inputs into `84..103(A5)`, calls `$984`, `$fac`,
`$e46`, then counts down the sleep timers of the task records. The task kernel (16 records at
`$ff1000`, `trap #0..#8` as create/exit/kill/sleep/yield/suspend/wake/restart/reset) is in `kernel.md`.
The in-level frame (TIME, the object pools, health, hit boxes, damage, the sprite list builder) is in `frame.md`.

## Scripts

Lua (run through `ffrun.sh`, or `ffmame.sh` for `-debug` ones; all wrap `ffdrive.lua`, `FF_LOAD=<state>` starts
from a saved state, `FF_STOP=<frame>`):

| script | what it does |
|---|---|
| `lua/ffdrive.lua` | the cold-boot drive and state save; `FF_PLAN=<plan.lua>` adds `{frame, field, level}` input entries (`lua/plans/`), `FF_CENSUS=<file>` logs the live records per frame, `FF_SHOT_*` takes screenshots. `plans/plan3.lua` is the drive to `ff_enemies` (`FF_SAVE=ff_enemies FF_SAVE_FRAME=4150 FF_PLAN=...`) |
| `lua/tap.lua`, `fieldtap.lua`, `htap.lua` | write/read taps on word ranges (`FF_W`, `FF_R`), on record byte ranges over the object pools (`FF_FIELDS`), and on the overlap-test operands |
| `lua/hpbar.lua`, `recdump.lua` | per-frame HUD bar tiles with Cody's and Bred's health words; per-frame records of Cody and Bred (`FF_PRESS` holds Button 1) |
| `lua/hitcount.lua` | count executions of listed addresses (`FF_ADDRS`, needs `FF_MAMEARGS="-debug -debugger none"`) |
| `lua/occ.lua`, `spawnlog.lua`, `poke_hp.lua` | pool occupancy per frame; spawn writes with the camera and script pointer; the lives and health poke |
| `py/hpcheck.py`, `boxcheck.py`, `hitcheck.py` | gates: HUD bar versus health, box derivation versus `$32c4`, the overlap test versus 818 live calls |
| `py/hudbar.py`, `hudenemy.py`, `namesheet.py`, `poolcensus.py` | HUD pixel width versus health, enemy-name sheets, the census of `ff_enemies` |
| `py/rd.py`, `jt.py`, `callers.py` | read ROM or state words, resolve a `move.w 6(PC,Dn.w),D1 / jmp 2(PC,D1.w)` table (pass the address of the `move.w`), find direct callers |

Gates run this pass from fresh runs: health bar 1100/1100, `+24` writer `$7a12` 8/8, box derivation 1100/1100, overlap
818/818, a third cold boot of `ff_enemies` with identical work RAM (`2657a253...b0ae`) and gfx RAM (`1a4357c4...e94a`),
and the original cold drive (`ff_gameplay`) still giving `79ed3cc1...0b2c` after the `ffdrive.lua` extension.

## Next

1. Get the pools no stage-1 run fills (tags 4, 6, `$12`, `$14`, pool 8, `$ffb228`): drive past the first boss
   or into stage 2 from a saved state, then census and `py/hitcheck.py` again. Name the three unnamed props
   and confirm AXL (`frame.md` "Fighter identity").
2. Read what `frame.md` lists as unread: `$6026`/`$61e24`/`$27fc4`, the player-versus-player path
   `$7766-$7920`, the kind handlers behind `$70c6`/`$70e6`/`$759c`, the continue screen.
3. Trace slot 11's ring-buffer consumers (`516(A5)`, `324(A5)`, `$1a22`), the `jsr $2874` senders and the sound
   queue at `388(A5)` (`$9d0`/`$9b2` write `$800180`), and read the Z80 side.
4. Graphics: `hardware.md` has the layouts and mapper ranges; the plane/byte order across
   `ff-5m/7m/1m/3m` is inferred. Decode one known tile, render a sheet, commit the PNG with the doc.
