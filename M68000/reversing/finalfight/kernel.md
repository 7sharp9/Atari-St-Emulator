# Final Fight task kernel (`$7f0-$97e`, VBL handler `$53e`)

The main 68000 program runs as up to 16 cooperative tasks scheduled by a small kernel in the first
2.4 KB of ROM. Evidence tags: **[R]** read in the ROM listing (`tools/disassemble.py --rom
ff_main.bin --base 0`), **[T]** checked against the per-frame work-RAM trace of the scripted drive
(`lua/ffdrive.lua`, frames 1000-2199, 1200 samples taken at the end of each frame), **[L]** checked
against the write-tap log of the same drive (`lua/kernel_log.lua`, below), **[I]** inferred.
`A5 = $ff8000` throughout the kernel.

## Task control blocks

Sixteen 16-byte records at `$ff1000` (`-28672(A5)`). The slot argument in `D0` of the trap calls is the
**byte offset** `slot * 16`, not the slot number: `move.w #$70,D0 / movea.l #$6149e,A0 / jsr $826` creates
slot 7 [R] [L] (the `$bea` boot task makes slots 7, 11, 8; `$ee4` makes slot 9). The sleep wrapper `$87e`
takes the frame count in `D0` instead (`D0 = 1` is "until the next VBL").

| offset | meaning | evidence |
|---|---|---|
| +0 | state (below) | [R] [T] [L] |
| +1 | sleep timer in frames, counts down in state 1; scratch byte `D1` in state 4 after a wake | [R] [T] |
| +2 | saved SR (word) | [R] `$8a6`, `$8ce` |
| +4 | saved PC (long), or entry point of a new task | [R] [T] [L] |
| +8 | saved USP | [R] `$8a2` |
| +12 | initial USP of a new task (read at `$81a`) | [R] |

`-28410(A5)` (`$ff1106`) is the current-task pointer (a long; the high word reads `$ffff`, ignored by
the 24-bit bus), `-28414(A5)` the scheduler's saved SP, `-28416(A5)` a "VBL happened" flag set by the
VBL handler and cleared by the scheduler [R].

## States (byte +0)

| value | name used here | set by | consumed by |
|---|---|---|---|
| `$00` | free | `trap #1` exit-self `$852`, `trap #2` kill `$86c` | `trap #0` create refuses a non-free slot (`$83a`, hangs at `$84e`) |
| `$01` | sleeping, timer in +1 | `trap #3` with `D0 != 0` (`$88a`: word `$0100 | D0`) | VBL handler `$5c6-$5de`: `subq.b #1,1(A0)`, at 0 state becomes 4 |
| `$02` | suspended, no timer | `trap #3` with `D0 == 0` (word `$0200`), `trap #5` suspend `$8e6` | `trap #6` wake `$90a` (state 2 only: becomes 4) |
| `$04` | ready, context saved | `trap #4` yield `$8be` (saves USP, SR, PC) | scheduler `$774-$7e2`: any state >= 4 is run |
| `$08` | running | scheduler (`$7fa`, `$810` write 8) | the scheduler also accepts it (jump-table entry `$800`) |
| `$0c` | new, not yet started | `trap #0` create `$832` (entry address in `A0`), `trap #7` restart-self `$926`, and `$938` (below) | `$810`: starts at +4 with USP +12 and SR 0 |

The scheduler (`$752-$7ce`) scans slots 0-15 from `$ff1000` for the first state >= 4, saves the
scheduler SP, loads `D1 = state`, and jumps through a table at `$7e4/$7e8/$7ec` = `$7fa/$800/$810`
[R]. `trap #8` (`$97a`) restarts the machine through the reset path `$5e896` [R].

`$938` is a second create routine: it takes the first free slot of **12-15** (`lea -28480(A5)` is
`$ff10c0`), writes state `$0c`, entry `A0` and the byte `D0` into +1, and returns carry set when all four
are busy [R]. Slots 12-15 are a pool for short-lived tasks; slots 0-11 are fixed roles.

When no lower slot is ready the scheduler reaches slot 11, which yields at the top of every iteration, so
slot 11 runs as the idle loop: with `-28415(A5)` zero the scheduler never executes `stop` between scans
(`$786-$7b6`), and slot 11 ran 117008 times in 2200 frames, about 53 per frame [L]. Every other task
sleeps one frame at a time, so all game logic is frame-locked and slot 11 gets the CPU left over.

## Live check [L]

`lua/kernel_log.lua` installs a write tap on `$ff1000-$ff11ff` (plus optional extra ranges) under
`ffrun.sh`, no debugger, and logs frame, scanline phase, the PC of the writing instruction, address,
mask and data for every write; `lua/kernel_tasks.py` turns it into the lifecycle below. The drive from
cold boot to frame 2200 gives 1,657,594 writes, byte-identical (md5) across two runs, scanline phases
included.

- Every state write comes from the trap body the listing says: `$842`/`$848` create (12 writes of state
  `$0c00`, each followed by the entry long), `$966`/`$96c` pool create (3), `$92a` restart (1), `$858`
  exit-self (4), `$876` kill (3), `$89c` sleep (9186), `$8c2` yield (117008), `$918` wake (1), `$5ce`
  VBL countdown (9584), `$5d4` VBL wake to state 4 (9176). `$8f2` suspend: 0 writes, so `trap #5` is
  unexercised. Creates total 15 = 12 + 3, matching the entry list below.
- Sleep words: `$0101` in 9073 of 9186, `$0102` in 91, `$0105` in 16, and one each of `$010a`, `$0114`,
  `$0119`, `$011e`, `$01b4` and `$0200` (`trap #3` with `D0 = 0`, slot 1).
- The VBL handler's flag write (`$5ba`) happens exactly once in each of 2086 frames, a median 3.8
  scanlines after MAME's frame-done callback (range 3.7-32.3). So `register_frame_done` fires just
  **before** the VBL interrupt: the per-frame work-RAM samples in [T] show the state left by the
  previous frame's tasks, before the countdown at `$5c6` and the next frame's scheduler pass.
- Scanline phase is `(machine time mod frame period) / scan period`; `screen:vpos()` does not exist in
  MAME 0.289's Lua (`screen.frame_period`, `scan_period`, `machine.time:as_double()` do).

## Tasks seen over the drive [L]

Entry addresses are read from the `+4` long written at each create. Roles are named from the task body
(first branch and what it dispatches on) and, where stated, a second observation; **[I]** where the body
alone does not settle it. Slots 4, 10, 13, 14 were never used in frames 0-2200.

| slot | entry | lifetime (frames) | role |
|---|---|---|---|
| 0 | `$000bea` | 114 | boot task: creates slots 7, 11, 8, reads the Service Mode bit into `132(A5)` (`$800018` bit 6, active low) or DSWC bit 7, then `trap #7` restarts itself at `$017076` |
| 0 | `$017076` | 915-1112 (killed by the coin) | top-level state machine: jump table `$17110` on word `$ff1288` (8 entries `$17126..$17c3a`), one pass per frame. State 2 body `$17184` sets up the attract/title screen [R]; its variable keeps its last value (2) after the task dies, it is not "the task is still in state 2" |
| 7 | `$06149e` | 114- | per-frame, one-frame sleeps. Body `$614b0`: only when `132(A5)` (Service Mode) is set and bit 6 of `100(A5)` is held does it fill 32 palette entries at `$908500` with `$4420`; otherwise it returns. A debug aid, **[I]** that it is a test-mode palette flash |
| 8 | `$000ee4` | 915- | input and coin-lockout service: creates slot 9, then per frame runs `$f5c` over two tables, `$f20`, `$f40` and sleeps one frame; `$f40` sets bits 2-3 of `106(A5)` (the upper byte written to `$800030`, data bits 10-11 = coin lockouts, active when 0) while `76(A5)` (credits) is below 9 and clears them from 9 up, so coins are refused at 9 credits [R] **[I]** |
| 9 | `$0010d0` | 915-1169 | credit and start handler: waits for `76(A5) != 0`, reads the start buttons through `$2998`, subtracts 1 or 2 credits (`$115c`, `$1154`) and falls to `$11a2`. `76(A5)` was 0 after Start in the saved state [R] [L] |
| 11 | `$004ac4` | 114- | idle loop: yields every pass, drains the byte ring at `516(A5)` (`$4b00-$4b5a`, read index `32(A5)`, each entry marked `$ff` when taken) through `$1a22`, which is the BCD score add: the ring is the **score award ring** (`$288c` pushes a points-table index, bit 7 = player 2; [L] a DUG kill wrote `$13` at `$2894`, `$4b1a` cleared it, score +1200; `ai.md`), drains the word ring at `324(A5)` (`$4b5c`, written by `jsr $2874`; its consumer's role is not read), and runs the frame-skip release on `101(A5)` bit 7 [R]. The sound cues go through the ring at `388(A5)` (`$9de`/`$9d0`, drained by `$9b2` to `$800180`) |
| 12 (pool) | `$0013ba` | 939-1112 | scripted-sequence player: reads a record from the table at `$68646` indexed by `1(A0)` and dispatches on its second byte through `$13f8`; created in attract mode **[I]** |
| 12 (pool) | `$002738` | 1203-1203, 1317-1397 | coin-counter/lockout pulse: sets bits in `110(A5)` through a table at `$27a8`, sleeps, clears them **[I]** |
| 15 (pool) | `$05d89a` | 1133-1150 | credit jingle: picks a sound id from `76(A5)` and `21632(A5)`, sends it with `jsr $2874`, sleeps 25 frames, sends id+`$80`; created by the coin insert and killed by Start [R] [L] |
| 1 | `$004c16` | 1169- | stage clock: clears about 20 game variables, sleeps 30 frames, then each frame does `addq.w #1,166(A5)` and `bsr $4cc2`, which dispatches on the word `0(A5)` (table `$4cce`, 8 entries `$4cde..$4f7a`) |
| 2 | `$01551e` | 1311- | player 1 controller: `A6 = $ff1204`, byte 0 = 0, dispatches on word 2 of its record (0 = active, 2 = inactive, set when `127(A5)` bit 0 is clear) each frame |
| 3 | `$015d92` | 1311- | player 2 controller: the same code with `A6 = $ff1244`, byte 0 = 1, bit 1 of `127(A5)` |
| 5 | `$005644` | 1169- | post-game flow: sleeps while `127(A5)` (active-player mask) is non-zero; only then does it create slot 4 (`$93a8`) and run the end sequence. Not reached in the drive **[I]** for what the end sequence is |
| 6 | `$05c384` | 1200-1311 | scene task for the screen between Start and the stage (state word `2(A6)`, `A6 = $ff1514`, dispatch `$5c3e8`); the player-select screen by timing, **[I]** |
| 6 | `$05c92e` | 1311- | scene task for the stage (`A6 = $ff1534`, dispatch on byte `2(A6)`, table `$5c956`) **[I]** |

Checks of the saved state at frame 2200 (`ff_gameplay_ram.bin`): P1 record bytes `$ff1204/06` = 0, 0 and
P2 record `$ff1244/46` = `$01`, `$0002`; `127(A5) = 1`; `0(A5) = 6`; TCB states 0 free in slots 0, 4, 9, 10,
12-15, 1 (sleeping) in 1, 2, 3, 5, 6, 7, 8 and 4 (ready) in 11.

### Game phase `0(A5)` and the per-frame pipeline

Slot 1's dispatch word took the values 0 (frame 1169), 2 (1200), 4 (1312) and 6 (1313, still 6 at
frame 2200), written by `$4cde`, `$4d46` and `$4d74`, the bodies the table gives for states 0, 2 and 4 [L].
State 6 (`$4e3a`) is the in-level frame: it calls `$5326`, `$5238`, `$5668`, then `$6396`, `$6026`,
`$61e24` and `$16600` with `$50e` calls (`D0 = $43, $53, $54`) between them, and tests `297(A5)` for the
stage-clear and death exits to states 8, `$a` and `$c` [R]. The pipeline, TIME, the object pools, health, hit boxes and the sprite
list builder are in `frame.md`.

Writing `127(A5)` and `126(A5)` at frame 1150 (`pc $1202`, value `$0101`) is the Start press: both bytes become 1.

## What the trace shows [T]

- The state byte takes exactly the values 0, 1, 2, 4, 8 and `$c` over 1200 frames x 16 slots.
- VBL countdown (`$5c6-$5de`), 7587 state-1 samples with a following frame: of the 178 with timer
  > 1, 177 have state 1 and timer-1 in the next frame and 1 went to state 0 (killed); no sample
  decrements by any other amount. Of the 7409 with timer 1, 7390 are state 1 again with a fresh
  timer (the task ran and slept again within the frame: timer 1 in 7315, 2 in 59, 5 in 15, 10 in 1),
  13 are state 4 or 8 (10 and 3), 5 are state 0 and 1 is state 2. Most tasks sleep one frame at a
  time.
- Saved PC in state 4: slots 2, 3, 5, 6, 7, 8 hold `$884` in every state-4 sample (2, 2, 2, 2, 5, 5
  samples) and slot 11 holds `$8b8` in all 1028 (`$884` and `$8b8` are the addresses after the `trap
  #3` and `trap #4` in their wrappers at `$87e` and `$8b2`).
- The current-task pointer is `$ffff10b0` (slot 11) at every sampled frame end, the idle task.

## Not proven

- The kernel was checked by write taps on the TCB RAM, not by a breakpoint at each trap entry: the
  trap semantics are established from who writes what (above), not from the registers at the call.
  `trap #5` suspend was never executed in 2200 frames; `trap #8` restart-machine likewise.
- The role names marked **[I]** (slots 7, 8, 11, 12, 5, 6) rest on the task body alone. Slot 11's queues
  and the `$50e` calls in the stage frame are not yet traced to their consumers.
- Enemies are not tasks: no create happened between frames 1311 and 2200 while Bred came on screen. Bred is
  record 14 of the object array at `$ff8568` (`frame.md`), updated from the state-6 pipeline.
