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
| 11 | `$004ac4` | 114- | idle loop: yields every pass, drains the byte ring at `516(A5)` (`$4b00-$4b5a`, read index `32(A5)`, each entry marked `$ff` when taken) through `$1a22`, which is the BCD score add: the ring is the **score award ring** (`$288c` pushes a points-table index, bit 7 = player 2; [L] a DUG kill wrote `$13` at `$2894`, `$4b1a` cleared it, score +1200; `ai.md`), drains the word ring at `324(A5)` (`$4b5c`, written by `jsr $2874`): the **text and tile-draw command ring**, not a sound ring (below, 15 of 15 writes consumed live), and runs the frame-skip release on `101(A5)` bit 7 [R]. The sound cues go through a different ring at `388(A5)` (`$9de`/`$9d0`, pumped by `$984` from the VBL handler to `$800180`; below) |
| 12 (pool) | `$0013ba` | 939-1112 | scripted-sequence player: reads a record from the table at `$68646` indexed by `1(A0)` and dispatches on its second byte through `$13f8`; created in attract mode **[I]** |
| 12 (pool) | `$002738` | 1203-1203, 1317-1397 | coin-counter/lockout pulse: sets bits in `110(A5)` through a table at `$27a8`, sleeps, clears them **[I]** |
| 15 (pool) | `$05d89a` | 1133-1150 | blinking coin/start prompt: picks a text message index (`$22`-`$2b`, "FREE PLAY", "INSERT COIN", "PUSH 1P START"...) from `76(A5)` (credits), `126(A5)` and `21632(A5)`, posts it with `jsr $2874`, sleeps 25 frames, posts index+`$80` (erase), sleeps 12; created by the coin insert and killed by Start [R] [L] (command `$0028` at frame 1134) |
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

## The two deferred rings (text commands `324(A5)`, sound `388(A5)`)

Evidence as above; scripts in `py/engine/` (`README.md` there, gates `ring_static`, `ring_live`, `sound`).

**Text and tile-draw command ring, `324(A5)`.** `$2874` is the writer (`D0 = type << 8 | param`), the slot 11 idle loop the only consumer [R]:

```
ring_put(D0):                      // $2874
  ring[324(A5) + 22(A5)] = D0 ; 22(A5) = (22(A5) + 2) & $3f         // 32 words
idle loop, $4b5c:
  if 24(A5) != 22(A5): c = ring[24(A5) + ...]; if c >= 0:           // $ffff = empty marker, a negative entry stalls the loop
      push A4, D7; $4b94(c); ring[...] = $ffff; 24(A5) = (24(A5) + 2) & $3f
$4b94: D1 = (c & $ff00) >> 6 ; D0 = c & $ff ; jmp *($4ba6 + D1)      // 13 types
```

| type | handler | effect |
|---|---|---|
| 0 | `$1292` | ASCII message from the table `$65f4c` onto the scroll-1 map (`$908000`, plus `$2000` for the player 2 HUD); param bit 7 draws blanks instead (`$12e8`). `$3e` "FINAL FIGHT 900613", `$40` "U.S.A.", `$39` the US warning screen, `$22`-`$2b` coin prompts, `$1c` "CREDIT =", `$1e` the FBI credit, `$00`-`$17` the test-mode menus |
| 1 | `$4be4` | starts the typewriter task `$13ba` (table `$68646`, a delay per glyph in `-28338(A5)`) in pool slots 12-15 (`$938`); with all four busy `$4bda` abandons the dispatch and the same entry is read again |
| 2, 3, 4, 5 | `$2656`, `$2664`, `$2672`, `$2636` | clear scroll 1, 2, 3 (`$4420`, `$3000`, `$0980` words) and the two object lists |
| 6 | `$193c` | high-score panel (message `$2c` and three rows from the pointers at `1292(A5)`) |
| 7 | `$268c` | all four clears and `141(A5) := 0` |
| 8 | `$4c08` | starts the coin-counter and lockout pulse task `$2738` (param = pulse code; the `jmp $2874` wrappers at `$2490-$25aa`) |
| 9 | `$1bf2` | tile-block copy (table `$67046`, four modes); no caller |
| 10 | `$1342` | tile-word strings (table `$6718a`: logos, Japanese text); bit 7 blanks |
| 11 | `$14e8` | big-font strings (table `$681fc`: SELECT PLAYER, GAME OVER, CONTINUE, TIME OVER, BONUS STAGE, ROUND n CLEAR!, GUY/CODY/HAGGAR); bit 7 blanks |
| 12 | `$9eaa` | type 0 with attribute OR `$180`; no caller |

`141(A5)` is a "message pending" handshake: callers set it before posting, type 7 and the task `$13ba` clear it, scenes wait on it (`$184fe`). There are 120 call sites of `$2874` (`py/engine/ringtable.py`): boot and the region screens, the coin wrappers, game over (`$4f2e`, `$9432`), the attract, title and ending sequences (`$17000-$19fff`), the select and continue scenes (`$5c4xx-$5d9xx`) and the test mode (`$5ec7c-$63912`). Live from a cold boot to frame 2300: 15 writes (all by pc `$287c`), 15 consumed (`$4b80`), 15 dispatches (`$4b94`), one `$13ba` and two `$2738` tasks; the commands were `0700 003e 0040 0700 0039 0700 0116 0028 0700 0a00 0b00 0b0c 081f 0200 080e` [L].

**Sound ring, `388(A5)`.** Queue entries: `$9d0` (dropped while `22188(A5)` is set; otherwise queued when `130(A5)` or `22195(A5)` is non-zero, else dropped when `136(A5)` is non-zero, [R]), `$9de` (same, and only when `1(A6)` of the caller's record is non-zero), `$9e4` (no `22188` test) and `$9f8` (ungated; the control wrappers `$a10`-`$a42` send `$f0 $f7 $f1 $f2 $f3 $f4 $f5 $f6 $5f`); `$a48`-`$be6` are 60 one-line wrappers (`move.w #id,D0 / bra $9de`; `$aaa` is id `$0d`). Write index `26(A5)`, read index `28(A5)`, 64 words. The pump `$984` runs from the VBL handler: on an odd frame (bit 0 of `21(A5)`) it pops one entry and writes its low byte to `$800180` (a low byte `$f9` first sends the high byte to `$800188`; only the test mode uses that); on an even frame it writes `$ff`. So the Z80 sees one command per two frames. Live: 26 queued, 26 latch writes in the cold boot, commands two frames apart [L]; a stage 0 play to the boss trigger queued 321 commands and all 321 had a logged return address (`py/engine/sndbp.lua`).

What the sound CPU does with a command byte, measured by injecting every byte `$00`-`$ff` through the real ring into an otherwise silent machine and tapping the Z80's YM2151 and OKI6295 writes (`py/engine/z80sweep.lua`, `idmap.py`; task slots freed, so a poke lab) [L]:

| byte | Z80 response |
|---|---|
| `$00`-`$3f` | OKI phrase id+1 (64 of 64), on a channel the Z80 picks per id |
| `$40`-`$5f` | YM2151 music or jingle, some with a drum phrase (`$42`, `$43`, `$46`, `$47`) on the OKI; no response for `$4a $4b $4d-$4f $56 $59-$5c` |
| `$60`-`$ef` | fold to `id mod $60` (112 of 112 OKI ids; the 68000 never sends them except `$f9` in the test mode) |
| `$f0` | stops the OKI channels and touches the YM (reset), `$f1`-`$ff` no response in the idle machine (control commands, role [I]) |

Callers of the ids (static, `py/engine/soundids.py`; live counts from the stage 0 play):

| ids | caller | evidence |
|---|---|---|
| `$00 $01 $03 $06` | hit sounds read from the attack box (`12(A2)`, `$7b10`) | live 74, 17, 34, 2 |
| `$02 $04 $05 $07 $0a $0b $0c $1c $1d $2f` | player action code only; `$2f` is the swing sound of `$b558/$b58c` | `$2f` live 61; roles of the others [I] |
| `$0d` | knockdown landing: 94 call sites in fighters, bosses and Haggar's throws, paired with the shaker (`frame.md`) | live 42 |
| `$2c` | fighter death (every fighter handler, 45 sites) | live 20 |
| `$16 $17 $18 $0f` | prop break sounds by prop kind (table `$7348`); `$0f` also pickups and the glass panes | `$17`/`$18` live 5/7 |
| `$3b` | GO arrow (`$1b318`) | live 30 |
| `$39 $3a` | select screen cursor and confirm | frames 1251, 1281 |
| `$40 $41 $50` | area and stage music, queued from `$915a` | live |
| `$55`, `$5f` | select screen music, coin jingle | frames 1201, 1112 |
| `$51 $52 $53 $54 $57 $58 $5e` | scene music (game over, title, continue, ending) | callers only; names [I] |
| `$f0 $f2 $f7` | silence (`$f0`); `$f2`/`$f7` as a pair at coin and start | role of the pair [I] |

## Not proven

- The kernel was checked by write taps on the TCB RAM, not by a breakpoint at each trap entry: the
  trap semantics are established from who writes what (above), not from the registers at the call.
  `trap #5` suspend was never executed in 2200 frames; `trap #8` restart-machine likewise.
- The role names marked **[I]** (slots 7, 8, 11, 12, 5, 6) rest on the task body alone. Slot 11's queues
  are traced to their consumers (the score ring `516(A5)`, the text ring above); the `$50e` calls in the stage frame are the test-mode colour bar (`frame.md`).
- Enemies are not tasks: no create happened between frames 1311 and 2200 while Bred came on screen. Bred is
  record 14 of the object array at `$ff8568` (`frame.md`), updated from the state-6 pipeline.
