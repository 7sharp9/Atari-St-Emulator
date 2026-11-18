# Hatari as a second oracle for game routines

Every game model in this repo is judged against this emulator's `callcap` (run one routine from a snapshot, record the
register and memory change). That makes this emulator both the thing a model copies and the judge of the copy: a wrong
instruction or flag in the F# 68000 core would be reproduced by the model and passed by the gate. Hatari is an
independent ST emulator with its own 68000 core (WinUAE's), so running the same routine there from the same state tests
the judge.

## What is proven: one routine call, same state, two CPUs

`py/hatari_callcap.py <snap> <hexaddr> [nth]` does a `callcap` on both emulators and compares the results:

1. This emulator resumes the snapshot, runs to the nth arrival at the routine, saves a snapshot there and callcaps it.
2. Hatari (TOS 1.00 UK, ST, 1 MB, headless) boots for 200 frames; a debugger script then loads the snapshot's RAM over
   its own from address 8 (`loadbin`), sets D0-A7, USP, ISP, SR and PC (`r`), and runs to the return address, where a
   second script saves RAM (`savebin`) and prints the registers.
3. The compare is Hatari's RAM after the call against the snapshot RAM with this emulator's callcap delta applied, over
   `$8-$fffff`, plus the sixteen registers.

`py/gate_hatari_callcap.sh` runs it over eight Virus routines at three calls each from the demo-flight snapshot
`scratchpad/virus/demo/S1b.snap`:

| routine | address | role |
|---|---|---|
| `Ship_Tick` | `$255c2` | the flight model |
| `Pool_UpdateAll` | `$2157c` | the enemy update loop |
| `ObjectPool_UpdateAll` | `$1fa72` | shots, debris, bombs |
| `Landscape_HeightAt` | `$24754` | terrain height lookup |
| `Input_Autopilot` | `$2538c` | the demo pilot |
| `Landscape_BuildGridAndDraw` | `$24098` | the landscape renderer |
| `Attitude_BuildMatrix` | `$1f646` | the orientation matrix |
| `Target_FindNearest` | `$2529a` | the pilot's target search |

Result: **24/24 calls agree** on all 1,048,564 compared RAM bytes and 16/16 registers. The calls cover 139,904
instructions (4 to 82,718 per call) and 10,402 changed bytes; four calls change no memory, so for those only the
registers carry information. Control: with one RAM byte (`$7fff0`) flipped on the Hatari side only, the compare reports
exactly that byte (1,048,563/1,048,564) and fails.

What this shows: for these routines the F# core and Hatari's core compute the same thing, so the Virus models gated on
callcap are not copies of an F# CPU bug in the paths these calls take. It is a sample of 24 calls, not of every
routine or every branch.

## What is proven: a whole game, same start state, two machines

`py/hatari_game.py <snap> <hexaddr> <nticks> [--until <hexaddr>]` lets the game run on Hatari with its interrupts
live, where the call check masks them. Hatari boots for 200 frames, takes the snapshot's RAM and CPU registers
(the status register as the snapshot has it), and runs; a trace breakpoint logs the game state at every arrival at a
once-per-tick routine. This emulator runs from the same snapshot under `stserver` and reads the same ranges at the
same arrivals. The ranges for Virus are the ship (`$270b0`, 12 bytes), fuel, attitude and gravity (`$32a2e`, 14), the
random generator (`$2706e`, 8), the score (`$2708e`, 4), the pool count (`$32a3e`), the wave (`$32a50`) and the whole
128-record actor pool (`$31d54`, 2,560 bytes): 2,602 bytes per tick.

Result, on Virus's first demo flight from `scratchpad/virus/demo/S1b.snap` (game start `$230c0`) to its game over
(this emulator's first arrival at `$25bc0`): **11,782/11,782 arrivals at `Ship_Tick` `$255c2` agree on every range**.
The flight passes through waves 0 to 3, the score changes 1,118 times and ends at 17,526, the generator is in 11,329
different states and the pool in 11,782. Control: with one pool byte (`$31d57`) changed on the Hatari side only, 0/20
arrivals agree and the first difference is reported at that byte. `py/gate_hatari_game.sh` runs the first 2,000 ticks
and the control in about 90 s; `py/gate_hatari_game.sh full` runs the whole flight in about 6 minutes.

The two machines do not agree on time, and the game does not care. This emulator raises the frame interrupt every
12,000 instructions; Hatari counts cycles, and took 50,588 frames for the flight's 11,781 ticks (4.3 per tick, most
often 3). So over this flight nothing in the tick state depends on when an interrupt arrives or on how many frames a
tick takes, and the generator, which is seeded with two constants at `$2300a` and never from a timer
(`../virus/README.md`, "Object scatter and the RNG"), is drawn the same number of times on both.

What this does not show:

- **The start state is this emulator's.** Both runs begin from `S1b.snap`, so the boot, the disk loader and the
  set-up before `$230c0` ran only here. A cold boot of the disk in Hatari, driven through the crack's menu, has not
  been tried.
- **Hatari's hardware registers are its own.** Video, MFP, sound, keyboard and floppy registers are whatever its boot
  of the desktop left; only RAM and the CPU cross over. The demo flight reads no input, so the keyboard and mouse path
  is not exercised.
- **Only the logged ranges are compared**, at tick boundaries, not all of RAM and not the screen.
- **One flight of one game**, flown by the game's own autopilot.

A stop of this emulator's `stserver` at the tick breakpoint is sometimes a return from an interrupt taken there, not a
new arrival: seven such stops in the flight, 6 to 207 instructions after the previous one. The script counts a stop
within 3,000 instructions of the last as the same arrival; with a 64-instruction rule two of them were counted as
ticks and every later tick compared one out of step.

## What the call check leaves out

- **Only RAM and CPU registers are transferred.** Hatari's video, MFP (timer and interrupt chip), sound chip, keyboard
  and floppy registers keep whatever its own boot left. A routine that reads a hardware register is outside this check.
- **Interrupts are masked for the call**, as in `callcap`. Anything that depends on an interrupt arriving mid-routine is
  outside it.
- **The return address differs.** `callcap` pushes `$00DEAD00`; Hatari bus-errors fetching that (it is outside a 1 MB
  machine) before its breakpoint is tested, so the Hatari side returns to `$00FC0000` and the four-byte return slot is
  left out of the compare.
- **Addresses `$0-$7` are not compared**: on a real ST and in Hatari they read from ROM.
- **Cost**: about 3 s per call, almost all of it Hatari's start and 200-frame boot. A 3,496-call corpus one process per
  call would take about 3 hours. Chaining many calls inside one Hatari process (reload RAM at each return) should
  remove most of that; it has not been tried.

## Other uses of Hatari, not tried here

These follow from Hatari's debugger and options as read in its source (`src/debug/*.c`, `src/control.c`,
`src/options.c`), and from the two existing drivers (`reversing/cadaver/py/secrets/hatari_xp_check.py`,
`reversing/populous/py/systems/hatari_edges.py`). None was run in this pass.

- **A whole game from a cold boot in Hatari.** Boot the disk in Hatari, drive the crack's menu and the title through
  the control socket, and log state at each tick as `py/hatari_game.py` does. It adds the boot, the loader and the
  keyboard path to what the whole-game check above covers.
- **Instruction-level first divergence.** `--trace cpu_disasm` gives one line per instruction, comparable with this
  emulator's `ATARI_TRACE=1` log over a bounded window started from the same loaded state.
- **A timing reference.** Hatari's profiler counts cycles per address. This emulator has no cycle counts
  (`sessions/emulator.md` plans them), so Hatari is the available source for how long a routine takes on the real
  machine.
- **Pictures.** `screenshot` and `--avirecord` give Hatari's rendering of a frame, as a check on the video model.

## Running it

`HATARI` names the binary. The default is a universal macOS build of Hatari 2.6.1-devel at
`~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari`, which runs headless with `SDL_VIDEODRIVER=dummy`; a
source build (`DEVELOPING.md`, "macOS") works the same way. Both gates need `scratchpad/virus/demo/S1b.snap`
(`bash reversing/virus/py/demo/capture.sh`). The call gate takes about 90 s and writes
`scratchpad/learning/hatari_callcap/gate.log` plus one directory per call (both emulators' logs, the debugger scripts,
the RAM images); the game gate writes `scratchpad/learning/hatari_game/gate.log` and one directory per run. Neither is
in a `gates.toml`: they depend on a Hatari binary outside the repo.
