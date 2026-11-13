# Captive: the game OS, the disk volume, the Copylock and the crack

Captive brings its own operating system. TOS boots the disk and is then left behind. A loader decoded from
track 0 into low RAM provides a `trap #9` OS: a file system on the game's own track format, which can write
as well as read, a heap allocator, and drive control. On top of it, `fed_BootFile` loads each program file
(an Amiga hunk executable), depacks it in place and calls it. `fed_BootFile` also installs a resident
machine-code monitor on every other exception and trap. `fed_MapGen` opens with a Rob Northen Copylock. Its
key is not used to decrypt anything: the Copylock adds it to a longword that `federation` later checks. The
Medway Boys crack leaves the Copylock in place and patches that longword's starting value instead.

Proof labels: **proven** means an emulator observation (the command is given or named in
`py/system/README.md`); **read** means read from the instruction bodies, not driven. Addresses are runtime absolute.
Snapshots are in `scratchpad/captive/` (`mg_entry.snap`: stopped at `$b5c2`, the `jsr 32(A4)` into `fed_MapGen` on
landing, module at `$1f7b0`, code offset 0 at `$1f7d0`).

## 1. The low-RAM loader and the `trap #9` OS

The game's boot code reads track 0 sectors 2-5 and 7-10 into a buffer. A subtraction pass decodes them
(`$75160`-`$75166`: `sub.l 4092(A1),(A1)+`) into `$206`-`$1180`, and the code then calls `trap #9`.
Proven: `watch 222 6` from a cold boot shows the DMA read of t0 s2 at step 40,055,899 and the decode loop
`$75164` writing `$222` at step 40,062,226 (`cold_watch.sh`). Vector `$a4` (trap 9) holds `$206`. Every
other trap vector holds `$14ee` in `fed_BootFile` (section 4). Proven: `m a0 40` on `mg_entry.snap`.

**Dispatcher** `$206` (read). It saves D0-D7/A0-A6, halves D7, and accepts the function only when D7 is a
multiple of 4 and at most `$82`. It then calls `$228 + word($228 + D7/2)`. The exit at `$222` returns D0-D6/A0-A6
from the stack, so a function returns values by writing into the saved-register slots. `bsr $44c` opens most
functions: it loads A3 = `$8800` (PSG) and A5 = `$8606` (DMA mode), A4 = `$117a` (state block), and clears the
status long `(A4)`. `bra $444` closes them, copying `(A4)` into the caller's D0. A negative status is an error
code (-2 file not found, -4 unit checksum, -10 no `:` in the name, -13 volume not found, -16 bad drive; each
code is set by `moveq` / `bra $9d2` at the cited site).

**Function table** (table from `trap9_table.py mg_entry.snap`; "traced" rows are calls seen with their
registers in `trap9_log.py --boot`, 48 calls from cold boot to the mission 1 screen):

| fn | entry | what it does | label |
|---|---|---|---|
| 0 | `$43c` | store D0 at `$11ce`, then as fn 4 | read |
| 4 | `$43e` | probe drives in mask D1 (`$7ce`: select, read FDC status, keep the drive unless status is `$81`/`$a0`), store the present mask at `12(A4)` | traced (D1 = 3 → 0) |
| 8 | `$3d2` | set the volume-block buffer pointer `$11a0` (= `38(A4)`) to D0, invalidate | traced (`$76a90`, then `$f7590`) |
| 12 | `$3ca` | set the unit buffer pointer `$119c` (= `34(A4)`) to D0, invalidate | traced (`$75090`, then `$f51e0`) |
| 16 / 20 | `$2ea` / `$2f6` | read / write one unit (`$998` / `$9d6`) | read |
| 24 | `$302` | write a file (`$c4e`): look up or create the entry, claim free units in the map (`$d9c`, `$db4`), write them, fill entry bytes 13-19, rewrite the volume block (`$c1c`). Called by `federation` at `$8cce` with D0 = 0, D1 = `$3a8e` | read |
| 28 | `$30e` | load file: A0 = `"vol:name"`, A1 = destination, D1 = maximum (-1 = whole file). Returns the number of bytes loaded, which is the packed length | traced (every module load) |
| 32 | `$826` | poll FDC status until the motor-on bit drops (up to `$9c40` polls), then deselect both drives; D0 is preserved | traced (after each load) |
| 36 / 40 | `$3f2` / `$3ec` | clear / set the TOS floppy lock `$43e`, invalidate | read |
| 44 / 48 / 52 | `$408` / `$41a` / `$422` | on drive D1 (`$3f8` selects it and reads its volume block): mark unit D0 as `$ff` in the map / mark it free (0), then rewrite the volume block (write-protect gives -12) / find a free unit and return its number in the status word | read |
| 56 | `$3a4` | select drive D0, read its volume block, return A0 = the buffer | read |
| 60 | `$3d8` | invalidate the cached unit: `st $118a`, `$118e = -1` | traced |
| 64 | `$39e` | loads the word at `$1186` into D0, which the exit's register restore then overwrites, so it returns nothing | read |
| 68 | `$31e` | delete file A0: clear each map byte equal to its directory index, clear its 16-byte entry, rewrite the volume block (`$32a`) | read |
| 72 | `$380` | rename: look up A0, copy the name at A1 into the entry (`$d5c`), rewrite | read |
| 76 | `$362` | format a volume (`$dd2`): write every unit, then build a fresh volume block with the name hash, the `$fe`/`$fd` reserved units and the six type words | read |
| 80 | `$3a2` | no-op (`rts`) | read |
| 84 | `$3bc` | return A0 = volume buffer, A1 = unit buffer | traced |
| 88 | `$370` | find file A0: returns A0 = its 20-byte directory entry | traced (`$f77c8`... for `fed1:FED_Credits`...) |
| 92 | `$434` | store D0 at `$11ce` | read |
| 96 | `$45c` | find the volume named in A0 (`"Fed1:"`) in drive A or B (`$920`: hash the name, read each drive's volume block, compare its first long) | traced (→ 0) |
| 100 | `$81e` | deselect both drives at once | read |
| 104 | `$1016` | OS initialisation | traced (once, at `$7516c`) |
| 108 | `$f8c` | allocate D1 bytes with flags D0, returns the address | proven (`heap_proof.py`) |
| 112 | `$eac` | free the block at A0 | proven |
| 116 | `$f50` | D0 = largest free block, D1 = total free | proven |
| 120 | `$28a` | get/set drive parameters at `$11c4`: each of D0-D6 that is not negative is stored, then all are returned | traced |
| 124 | `$f1c` | allocate D1 bytes from the top of the last free block, with no header | proven |
| 128 | `$288` | `rts` only | read |

**State block** at A4 = `$117a` (offsets from the reads at the cited code; read):

- `+0` status
- `+8` name hash (`$510`)
- `+12` drive-present mask
- `+16` flag: volume block must be re-read
- `+18` current drive
- `+19+d` head track of drive d (`$ff` = unknown: `$5a8` restores the drive first)
- `+34` unit buffer pointer, `+38` volume buffer pointer, `+42` name pointer, `+58` current directory entry
- `+64` directory index
- `+80` data bytes per unit, `+82` unit bytes, `+86` last unit number (`$a3`)
- `+92`..`+100` geometry from the type word (`$1120`): `+94` sectors per track, `+96` sector size, `+100` DMA sector count per read

The unit decode keys `$eff478ed`/`$bffb7e5e` sit at `-3856`/`-3852(A4)` = `$26a`/`$26e`.

**Reading a unit** `$876` (read):

- Reads sectors 1 to `94(A4)` of the current track into the unit buffer.
- Decodes in place: the first long is inverted; each following long is reduced by a running key that starts at `$26a` and advances by `$26e`.
- Sums the result; a non-zero sum is an error, retried up to five times by `$85e`.
- This is the decode `py/fedfs.py` transcribes.

**Per-unit RLE.** The copy from the unit buffer to the destination (`$6a2`) has a second packer (read). When the
unit's data starts with the long `'PACK'` (`$6d4`: `cmpi.l #$5041434b,(A6)`), the copy run-length decodes it. The
format is an escape byte, then the length; inside the data, escape + value + count expands to a run. This sits
below the file-level LZ, whose files start `RNC\x01` (`fedfs.depack`, the depacker at `$303c`).

**File names** (`$510`, read). A name is `"volume:file"`. The volume part is hashed one character at a time,
uppercased: `D += c; D = rol.l(D, D & 63)`. The file part is matched case-insensitively against 12 bytes of
each of up to 60 directory entries (`$530`).

### Heap

Blocks carry a 16-byte header: `+0` next, `+4` previous, `+8` flags (bit 0 of byte 11 = in use), `+12` size. The
list head is the long at `$1032`; its first block is `$1206`, which holds `fed_BootFile`. Proven,
`heap_proof.py mg_entry.snap 100 4`:

- fn 116 gives largest = total = `$79092`.
- fn 108(flags 4, `$100`) returns `$7c14e`; its header at `$7c13e` reads size `$100`, in use, and the split-off
  remainder at `$7c24e` reads `$78f82` = `$79092 - $100 - $10`.
- fn 112 merges the block back to one free block of `$79092`.
- A marker poked where the block lands survives fn 108 with flags 0 and is zeroed with flags 4 (labelled pokes).

From the body (read): fn 108 rounds the size up to even, takes the first free block large enough, and splits only
when more than `$17` bytes would remain. fn 112 merges with the next and previous blocks when they are free.
fn 124 cuts the request off the end of the last free block without a header (proven: at boot it returns `$f8300`,
`$f7b00`, `$f7590`, `$f51e0`, each the previous minus the request; 4 of 4). `fed_BootFile` uses fn 124 for its
permanent buffers.

## 2. Module launch and boot order

`fed_BootFile` loads each program the same way (read, `$13aa`-`$13ec`; each step traced):

1. `$144c`: fn 88 finds the entry, then fn 108 allocates its directory length (the unpacked length) plus `$110`
   with the caller's flags in D0 (2, 4 or 6).
2. fn 28 with D0 = -1 loads the packed file into the block, and fn 32 turns the motor off.
3. `bsr $303c` depacks it in place.
4. `jsr 32(A3)` calls it past its 32-byte hunk header. There is no relocation step: every program file is a
   single position-independent code hunk (`py/hunks.py`).
5. fn 112 frees the block when the program returns.

Boot order from the trap log (proven, steps from a cold boot through `drive.txt`'s inputs):

| step | event |
|---|---|
| 40,064,261 | fn 104 at `$7516c`: OS initialisation |
| 40,319,014 | fn 28 loads `fed1:fed_BootFile` to `$1216`, returns `$2454` |
| 40.55M - 40.77M | `fed_BootFile` allocates its buffers with fn 124 and moves the OS buffers there (fn 8/12), then fn 96 finds `fed1` |
| 40,910,055 | `Fed_Credits` (a picture) loaded, freed at 41,586,735 |
| 41,640,746 | `fed_Demo` loaded and run (the "Federation" intro); fn 32 at 213,840,216 after Space |
| 214,274,718 | `Case.pic` loaded and run as a program until 221,076,017, when it is freed |
| 221,225,871 | `federation` loaded and run; its own loader (`$1a534`) then loads `Fed_Sounds`, `fed4/5/8.pic`, `fed_MapView` |

So `Case.pic`, despite its name, is a program that runs for about 6.8M steps (about 570 VBLs) between the intro
and the game (proven: load, launch and free in the log). What it shows is not checked.

## 3. The volume block

Unit 1 (track 0 side 1) is the volume block. Its header long is the length in longs (`$15b`); the OS's
buffer holds the data after it. The offsets below are data offsets, as in `fedfs.read_dir`.

| bytes | content | evidence |
|---|---|---|
| 0-3 | `1ce2 0047`: the hash of the volume name `FED1` (`$510`) | proven: computing the hash of `FED1` gives `$1ce20047`; fn 96 compares this long (`$94e`) |
| 4-11 | volume name `fed1`, zero-padded | `volblock.py` |
| 12-23 | six geometry words, one per file type; all `$4b0a` | proven: `volblock.py` |
| 24-187 | allocation map: byte 24+u belongs to unit u and holds the 1-based directory index of the file that owns it; `$fd` = boot unit 0, `$fe` = volume units 1 and 2, 0 = free | proven: `volblock.py`, 31 of 31 files own exactly their units u, u+2, ...; 23 free units |
| 188- | directory: 20-byte entries of name[12], start unit (word), unit count, type, length (long) | `fedfs.read_dir` |

The README's "176-byte table" is bytes 12-187: the type words plus the map. A directory entry's type byte (+15)
selects the geometry word: `$978` reads `12(buf, type*2)` and `$1120` decodes it. For `$4b0a`, `$1120` gives
10 sectors per track, sector size `$80 << 2` = 512, and data bytes per unit 10 x 512 - 8 = 5112 = 1278 longs.
That is the unit size `fedfs` decodes (read; the arithmetic checks against `fedfs.UNIT_DATA`). Readers of the map
(read): the load path `$4b4`, delete `$32a`, find-free `$d9c`, claim `$db4` (it refuses a `$fe` unit) and
format `$dd2`.

## 4. The resident monitor in `fed_BootFile`

`$1498` (read) points vectors `$8`-`$3c` (bus error up to vector 15) at a ladder of
`bsr` instructions at `$14d2`. The return address each `bsr` leaves tells the handler which vector fired. It points
traps #0-#15, except #9, at `$14ee`, which takes the trap number from the low nibble of the `trap` opcode (proven:
the vectors as read in `mg_entry.snap`).

Both paths enter `$1530` (read):

- Writes `'HELP'` to `$200` as a re-entry mark.
- Saves every register to `$2e34` and takes over the trace vector.
- Switches to its own stack, decodes the exception frame and runs a command loop.

The strings in `fed_BootFile` name it: `ratt-wack`, commands `ALTER CLEAR FILL LIMIT REGS REGS2 RESET RESUME UNTIL
PUSER`, `unknown symbol`, `pattern?`, and a complete 68000 mnemonic and condition-code table for its
disassembler. It is Crowther's own debugger, shipped with the game. `federation` has `trap #0`-`#15` calls on
failure paths (for example `moveq #2,D7 / trap #0` at `$dfd2`, when a lookup in `1904(A6)` fails), which would
drop into it. That these are debug breakpoints left in is inferred. No run here has entered the monitor.

## 5. The Copylock in `fed_MapGen`

The first `$870` bytes of `fed_MapGen`'s code are a Rob Northen Copylock ST wrapper. Every instruction from
`$1f84e` to `$2003e` is stored encrypted and decrypted only while it is the next one to run. The generator
proper starts at `$20040` (code offset `$870`), and it is plain. Proven by the text trace in
`py/system/README.md`: 5,622 instructions executed in `$1f84e`-`$2003f`, at 249 distinct PCs, each printed as decrypted. The plain listing
of `mg_entry.snap` at `$20040` matches the traced instructions.

**Entry** (plain, proven by trace):

- `$1f7d6` saves the entry registers to `$20376`.
- fn 60, then fn 96 `"Fed1:"`: if the volume is missing, the wrapper is skipped to `$20040`.
- `$1f7fa` saves vectors `$8`-`$27` to `$2043e`.
- `illegal` at `$1f826` (vector `$10` pointed at `$1f828`) enters supervisor mode and saves all 16 registers.
- `movec` at `$1f836` faults on a 68000 to `$1f846`.
- `$1f848` loads D0-D6/A0-A6 from the code bytes at `$1f84e` itself. These are stage 1's starting keys: they come
  from the program, not the disk.

**Stage 1** (built on the stack at `$f821a` by `$1f84e`-`$1f888`, started by `ori #$a71f,SR` at `$1f88e`, which sets the
trace bit; proven by trace). For each traced instruction:

1. `eor.l D6,(A6)` / `eor.l D6,4(A6)` re-encrypt the previous instruction's 8 bytes.
2. A6 becomes the new PC.
3. `D6 = SR & $a71f`, `D0 += D6`, `D1 += D6`, `D6 ^= D1`, `D6 ^= D2`.
4. The next 8 bytes are decrypted with D6.
5. `add.l D6,$10` keeps a running sum in the illegal-instruction vector.

The key therefore depends on the code's own path through the status register.

**Stage 2** (pushed by `$1f934`-`$1f9a6`, installed at `$1f9b6`; handler at `$f81ca`). The key is the long just before
the instruction plus the long at `$8`, which is cleared at `$1f89c`. The handler also calls `jsr (A2)` whenever the
word at PC-4 is `$cf47`: that is how the untraced FDC routine on the stack (`$1fc12`-`$1fc78`) is run.

**What the decrypted code does** (proven by trace and `ATARI_TRACE_FDC=1`):

1. Selects drive A, side 0, through PSG port A (`$1fcf2`-`$1fd06`).
2. Points DMA at the buffer `$1fd5e`, sets a count of 31 sectors and issues READ TRACK (`$e0`), with a timeout and a
   force-interrupt (`$d0`). This happens three times (`$1fb86`, `D1 = 2`).
3. Scans each buffer for an `$a1`,`$fe` ID-address mark (`$1fb92`-`$1fb9e`). Here it finds none (section 7) and
   returns -1.
4. Turns the motor off (`$1fcde`).
5. Fills the track buffer with `x = x * 17 + 1` from `$a17d19` (`$1fa86`). The module ships with these same bytes:
   the RAM diff below shows no change there.
6. At `$1ff62` it adds the key D0 to the long at the saved A3, `add.l D0,(A6)`. A run to `$1ff66` shows A6 = `$1f280`
   and D0 = 0 (proven, REPL `u 1ff66 800000`).

**Stage 3** (`$1ff74`, the same chained key) runs the wrapper's copy-and-clear routine on the stack, with every length 0
(`$2001c`-`$20030`). It calls fn 60, and the trace handler then clears the trace bit and returns to `$20040`.
`$20040` puts back the saved vectors and the entry registers and clears its `$35bc`-byte variable area.

**The key's only destination** is `$1f280`. That is `federation`'s `15538(A6)` (A6 = `$1b5ce`), which `$b510`-`$b51a`
builds just before the call and passes as A3. `federation` tests it:

- `cmpi.w #$2c76,15540(A6)` at `$dfaa`;
- `tst.w 15538(A6)` at `$6a50`, `$6c46`, `$8ba4`, `$df5c` and `$e0a0`.

Proven: `find_field_writers.py ld_1.snap "15538(A6)" --all` (6 reads, no direct writer). On a correct disk the
key must turn the stored starting value into `$0000 2c76`. The wrapper has no effect on generation. Proven by
`ramdiff.py mg_entry.snap mg_plain.snap`: inside the module image only the entry register save and the vector save
change (both written by the plain prologue), `$1f280` is unchanged, and `$20040` restores the entry registers before
the generator runs. No seed or table passes from the Copylock to the generator. What the six tests gate in
`federation` has not been driven.

## 6. The Medway Boys crack

The crack works without disarming the Copylock. It changes the value the Copylock adds to (proven by
`cold_watch.sh`):

- The original `federation` code at `$b514` (as on the disk and in `fed/federation.code`) is
  `clr.w -(A3); clr.l 1886(A6); move.w #$99d3,-(A3)`, leaving `$99d30000` at `15538(A6)`.
- The OS exit at `$222` reads `bra $140`. The hook word comes out of the game's own track-0 decode (`$75164`,
  step 40,062,226), so the crack is encoded into the disk's loader.
- The Medway menu (`$10452`) writes the code at `$140`-`$16f` at step 40,055,110, after the menu key.
- On every `trap #9` return, `$140` checks whether `$b514` holds `$426342ae`. If it does, it writes
  `clr.l 1886(A6); move.l #$00002c76,-(A3)` over `$b514`-`$b51f`, and then returns through `$16c`
  (`movem.l (A7)+,D0-A6`, `rte`), the original tail.
- The `federation` depacker (`$31b2`) writes the original bytes at step 223,946,750. The hook replaces them at
  step 224,603,006 (`$14e`, `$158`, `$162`), on the next trap.

On the cracked disk the stored value is already `$00002c76`. The Copylock fails, adds 0, and the checks pass.
Inferred: the original disk's key is `$2c76 - $99d30000` = `$662d2c76`. That the original stub at `$222` was
`movem.l (A7)+,D0-A6` is inferred from the saving `movem.l D0-A6` at `$206` and the tail the crack provides at `$16c`.

## 7. Emulator gap: READ TRACK

The emulator does not model the FDC's READ TRACK command (`$e0`). Proven: `ATARI_TRACE_FDC=1` over the
Copylock shows `cmd $e0 (other) ... transferred=0`, then the code's own `$d0` force-interrupt after its timeout.
On this cracked `.ST` the result does not matter, because the crack expects the Copylock to fail. An original disk
image (with a protection track) could never pass its Copylock here.
