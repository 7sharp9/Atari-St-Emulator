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
  set-up before `$230c0` ran only here. The next section removes this limit.
- **Hatari's hardware registers are its own.** Video, MFP, sound, keyboard and floppy registers are whatever its boot
  of the desktop left; only RAM and the CPU cross over. The demo flight reads no input, so the keyboard and mouse path
  inside the game is not exercised.
- **Only the logged ranges are compared**, at tick boundaries, not all of RAM and not the screen.
- **One flight of one game**, flown by the game's own autopilot.

A stop of this emulator's `stserver` at the tick breakpoint is sometimes a return from an interrupt taken there, not a
new arrival: seven such stops in the flight, 6 to 207 instructions after the previous one. The script counts a stop
within 3,000 instructions of the last as the same arrival; with a 64-instruction rule two of them were counted as
ticks and every later tick compared one out of step.

## What is proven: the same flight from a cold boot of the disk in Hatari

`py/hatari_boot.py <ours.json>` gives Hatari nothing from this emulator. Hatari boots a copy of
`scratchpad/virus/aha.st` itself; the keys `../virus/drive.sh` sends here go in over Hatari's control socket (F1 at
the crack's menu until the trainer runs, then N five times and Return until Virus's seed code at `$2300a` executes);
after that no key is sent and the title and the "Press R" page time out into the demo. As `demo/capture.sh` does
here, the game start is the first `$230c0` after the first enemy spawn `$20e74`; from there the same trace breakpoint
logs the same ranges at every `Ship_Tick`, and they are compared with this emulator's flight from `S1b.snap`
(`ours.json` of the section above).

Result: **11,782/11,782 arrivals agree on every range**, to the game over. Control: with pool byte `$31d57` changed
by Hatari's debugger at the game start, 0/20 arrivals agree. `py/gate_hatari_boot.sh` runs 2,000 ticks and the
control in about 2 minutes, `py/gate_hatari_boot.sh full` the whole flight in about 5.

So Hatari's own floppy controller, loader, keyboard path through TOS and the two menus, and its own set-up of Virus
lead to the game state this emulator reaches. The keys are sent on wall-clock time against a fast-forwarded machine,
so the frame they land on differs from boot to boot: in six boots the trainer was first seen at frame 1,770 to
1,845 and the game started at frame 5,855 to 6,150. The interval from `$2300a` to the game start was 1,326 frames
in every one of them, and the flight was the same in each for as long as it was logged (11,782, 2,000, 1,132 and 50
ticks; the other two were controls).

At the game start Hatari saves all of RAM, which is compared with `S1b.snap` (the counts are from the whole-flight
boot; they vary by a few tens between boots, 527 to 592 in four boots):

| region | bytes differing |
|---|---|
| `$8-$afff` (system variables, TOS and GEMDOS data, the supervisor stack) | 498 |
| `$b000-$6feff` (Virus's code and data) | 1 |
| `$6ff00-$6ffff` (the user stack below `$70000`) | 50 |
| `$70000-$fffff` (the two screen buffers and above) | 0 |
| all of `$8-$fffff` | 549 of 1,048,568 |

The one byte in Virus's own memory is `$62a65`, the last key make code its keyboard handler stores (`../virus/demo.md`,
"Where the inputs enter"): `$1c` (Return) here and 0 on Hatari. Inferred, not driven: the Return that leaves the
trainer reaches Virus's handler here and not there, because the key is held for a different time relative to the
load. The sixteen CPU registers D0-A7 are equal. The status register is `$0000` here and `$0300` on Hatari: this
emulator raises no horizontal-blank interrupt, and TOS's handler for it is what sets the mask to 3
(`DEVELOPING.md`, "MAME as a second oracle for the ST core", model gap 1). Neither difference reaches the tick state in 11,782 ticks.

What this still does not show: the demo reads no input, so the keyboard and mouse path inside the game is not
exercised; only the logged ranges are compared after the start; and it is one flight of one game.

## What is proven: a whole callcap corpus inside one Hatari flight

Because the flight is the same on both machines, Hatari's own run passes through every call this emulator's `callcap`
corpus was taken from, so one Hatari process can check a whole corpus. `py/hatari_calls.py <snap> <ticks.log>` lets
Hatari fly from `S1b.snap` with interrupts live and logs, with two trace breakpoints, the registers and the routine's
inputs at every entry of `Input_Autopilot` `$2538c` and the registers and its outputs at every return (`$255d4`; the
routine has one caller, the `bsr.w` at `$255d0`). Each call is compared with this emulator's `callcap` of the same
natural entry, from the pilot corpus that gates the pilot model (`../virus/demo.md`, "The pilot";
`../virus/py/pilot/capture_pilot.py`).

Result, from a fresh capture: **3,496/3,496 calls agree at entry** (D0-A7, the five condition codes and the 3,341
input bytes the capture dumps: pilot words, ship, matrix, pool count, tick, countdown and the pool) **and 3,496/3,496
at return** (D0-A6 against `callcap`'s register changes, A7 four above its entry value, and the 33 output bytes, pilot
words `$270a2`, matrix `$270d4` and countdown `$62a60`, against the entry dump with `callcap`'s memory changes applied).
`callcap` records no write outside those three ranges and the stack below the entry A7 in any of the calls, so they
are all the memory the routine changes. Control: with `$62a60` raised by one by Hatari's debugger at the first entry,
0/20 calls agree and call 0 is reported at that byte. `py/gate_hatari_calls.sh` runs the capture, the 3,496 calls and
the control in about 3 minutes, against about 3 hours for one Hatari process per call.

This is the corpus the pilot model is gated on (model == `callcap` 3,496/3,496), so for that model the judge has been
checked on every call it judged, not on a sample. It differs from the one-call check above in what it compares: the
call runs unmasked inside the game on Hatari and masked under `callcap` here, and only the routine's inputs and
outputs are compared, not all of RAM. The same script fits any routine with one call site and a corpus that dumps
its inputs; a routine with several callers needs one return breakpoint per caller.

## What the call check leaves out

- **Only RAM and CPU registers are transferred.** Hatari's video, MFP (timer and interrupt chip), sound chip, keyboard
  and floppy registers keep whatever its own boot left. A routine that reads a hardware register is outside this check.
- **Interrupts are masked for the call**, as in `callcap`. Anything that depends on an interrupt arriving mid-routine is
  outside it.
- **The return address differs.** `callcap` pushes `$00DEAD00`; Hatari bus-errors fetching that (it is outside a 1 MB
  machine) before its breakpoint is tested, so the Hatari side returns to `$00FC0000` and the four-byte return slot is
  left out of the compare.
- **Addresses `$0-$7` are not compared**: on a real ST and in Hatari they read from ROM.
- **Cost**: about 3 s per call, almost all of it Hatari's start and 200-frame boot. For a whole corpus use the
  in-flight check of the section above.

## Other uses of Hatari, not tried here

These follow from Hatari's debugger and options as read in its source (`src/debug/*.c`, `src/control.c`,
`src/options.c`), and from the two existing drivers (`reversing/cadaver/py/secrets/hatari_xp_check.py`,
`reversing/populous/py/systems/hatari_edges.py`). None has been run.

- **Instruction-level first divergence.** `--trace cpu_disasm` gives one line per instruction, comparable with this
  emulator's `ATARI_TRACE=1` log over a bounded window started from the same loaded state.
- **A timing reference.** Hatari's profiler counts cycles per address. This emulator has no cycle counts
  (`sessions/emulator.md` plans them), so Hatari is the available source for how long a routine takes on the real
  machine.
- **Pictures.** `screenshot` and `--avirecord` give Hatari's rendering of a frame, as a check on the video model.

## Running it

`HATARI` names the binary. The default is a universal macOS build of Hatari 2.6.1-devel at
`~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari`, which runs headless with `SDL_VIDEODRIVER=dummy`; a
source build (`DEVELOPING.md`, "macOS") works the same way. All three gates need `scratchpad/virus/demo/S1b.snap`
(`bash reversing/virus/py/demo/capture.sh`). The call gate takes about 90 s and writes
`scratchpad/learning/hatari_callcap/gate.log` plus one directory per call (both emulators' logs, the debugger scripts,
the RAM images); the game gate writes `scratchpad/learning/hatari_game/gate.log` and one directory per run. The boot gate needs
`scratchpad/virus/aha.st` and this emulator's side from the game gate (`t2000/ours.json`, or `flight1/ours.json` for
`full`), and writes `scratchpad/learning/hatari_boot/gate.log`. The corpus gate takes its own fresh capture into
`scratchpad/learning/hatari_calls/`. None is in a `gates.toml`: they depend on a Hatari
binary outside the repo.
