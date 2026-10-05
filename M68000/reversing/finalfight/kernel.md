# Final Fight task kernel (`$7f0-$97e`, VBL handler `$53e`)

The main 68000 program runs as up to 16 cooperative tasks scheduled by a small kernel in the first
2.4 KB of ROM. Evidence tags: **[R]** read in the ROM listing (`tools/disassemble.py --rom
ff_main.bin --base 0`), **[T]** checked against the per-frame work-RAM trace of the scripted drive
(`lua/ffdrive.lua`, frames 1000-2199, 1200 samples taken at the end of each frame), **[I]** inferred.
`A5 = $ff8000` throughout the kernel.

## Task control blocks

Sixteen 16-byte records at `$ff1000` (`-28672(A5)`), slot = `D0` in the trap calls [R].

| offset | meaning | evidence |
|---|---|---|
| +0 | state (below) | [R] [T] |
| +1 | sleep timer in frames, counts down in state 1; scratch byte `D1` in state 4 after a wake | [R] [T] |
| +2 | saved SR (word) | [R] `$8a6`, `$8ce` |
| +4 | saved PC (long), or entry point of a new task | [R] [T] |
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
| `$0c` | new, not yet started | `trap #0` create `$832` (entry address in `A0`), `trap #7` restart-self `$926` | `$810`: starts at +4 with USP +12 and SR 0 |

The scheduler (`$752-$7ce`) scans slots 0-15 from `$ff1000` for the first state >= 4, saves the
scheduler SP, loads `D1 = state`, and jumps through a table at `$7e4/$7e8/$7ec` = `$7fa/$800/$810`
[R]. `trap #8` (`$97a`) restarts the machine through the reset path `$5e896` [R].

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
- The current-task pointer is `$ffff10b0` (slot 11) at every sampled frame end, a task that
  yields with `trap #4` every frame (state 4, PC `$8b8` in 1028 frames, state 8 in 172).

## Not proven

- The trap handlers were read, not run: no breakpoint or `callcap` on `$8be`, `$88a`, `$832` etc.
  The mapping of trap number to call (`#0` create ... `#8` restart) comes from their bodies.
- The sampling point of `register_frame_done` relative to the VBL interrupt at scanline 240 is not
  established, so "state at frame end" is whatever the last instruction before the callback left.
- What each of slots 0-15 is for (slot 11 as the main/game-flow task, 7 and 8 as one-frame
  sleepers) is not known; naming them needs each task's entry point (`+4` at creation) and body.
