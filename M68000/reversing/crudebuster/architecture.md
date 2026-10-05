# Crude Buster: architecture of the 68000 program

Proven items carry a count and the script that reproduces it (`py/kernel/gates.sh` runs all of them, about 3 minutes). Anything read from the code but not run is labelled *read*;
anything guessed from names, screenshots or order is labelled *inferred*. Addresses are 68000 addresses of the decrypted program image (`scratchpad/crudebuster/rom/<set>_main.bin`,
set `cbuster`; the other four sets differ in the program ROM, so these addresses are the `cbuster` (World FX) ones).

## Hardware and address map

From the MAME driver (`cbuster.cpp`, read):

| range | what |
|---|---|
| `$000000-$07ffff` | program ROM (code `$0-$2bfff`, then data: `$2d000-$2ffff` erased, maps/scripts/tables above) |
| `$080000-$083fff` | work RAM (16 KiB), stack top `$84000` |
| `$0a0000-$0a2fff` / `$0a8000-$0aafff` | tilemap chip 0 / chip 1, two playfields each (chip 0: 8x8 chars pf1 + 16x16 pf2; chip 1: two 16x16) |
| `$0a4000 $0a6000 $0ac000 $0ae000` | rowscroll RAM |
| `$0b0000-$0b07ff` | sprite RAM, buffered: a write to `$0bc000` latches it |
| `$0b5000 / $0b6000` | tilemap control, chip 0 / 1 (write only) |
| `$0b8000 / $0b9000` | palette, low / extension halves (2048 entries) |
| `$0bc000` read P1_P2 (word: low byte P1, high byte P2, active low), `$0bc002` read DSW / write sound latch, `$0bc004` protection, `$0bc006` read COINS (bit 3 = VBLANK) / write clears IRQ4 |

The sound CPU is a HuC6280 with its own 64 KiB program (identical in all five sets); the 68000 talks to it only through the latch at `$bc002`.

## Boot and vectors

- Reset: SSP `$84000`, PC `$600`. `$600` sets `$b5000 = $90`, writes `$bc006` (IRQ4 clear), zeroes `$80000-$83fff` (4096 longs), calls the video init `$8038` and the clears `$cc2`, enables interrupts (`$2300`), does the protection handshake, then falls into the attract loop `$66c`.
- 33 vectors are used (bus/address error, illegal and so on, traps, autovectors 1 to 7). **Only level 4 (VBL, `$b1e`) is real**; the other 32 point below `$400` at a crash dumper (`$100-$3b6`: prints registers and a stack dump into the text layer through `$3ee`, then spins at `$3b8`). Gate: `static_gate.py`.
- Protection (`$bc004`): the program writes a key byte and reads back a response, and jumps to the failure screen `$1a68` (palette, text, sound `$4f`, then it hangs) on a mismatch. Checks sit at `$654` (`$9a` -> `0`), `$13e2` (`$9a`, `$0e` -> `$0e`), `$11d2` (`$9a`, `$02` -> `$63`), `$1218`, `$1380` and in each level setup (`$8284-$85d8`: the level key). The port is MAME's `prot_w`/`prot_r` table (response and layer-priority flag `m_pri` by key); a cold boot plus the demo levels shows the pairs `$9a -> 0`, `$0e -> $0e` (x2), `$f1 -> $36` (level 1 setup `$839a`), `$80 -> $2e` (level 2 setup `$83da`) (`lua/protlog.lua`, one 10,500-frame cold boot, 6 of 6 reads equal the table). So the key also selects the layer priority (`graphics.md`).

## The frame

One logic step per VBL: in play, `$8004a` (the logic frame counter) advanced by exactly 1 in **1600 of 1600** steps (frames 800-2400 of `plans/play1.lua`) and `$80002` was 0 in all of them (`py/kernel/framecount_gate.py`).

VBL handler `$b1e` (read): counts VBLs since the last logic step in `$80002`; if the main loop is waiting (`$bbe` sets bit 7 of `$80000` and spins until the handler clears it) it resets `$80002`, increments `$8004a`, clears the flag and latches the sprite buffer (`$810c`: writes `$bc000`). Then, every VBL: palette mailboxes `$70f0/$7324/$74b6/$7526` (consume the words `$80008/$8000a/$8000c/$8000e`, copy 512-byte palette blocks into `$b8000`/`$b9000`, animate and blink entries by `$8004a`), coin input `$1148`, controller read `$f5c`, credits/start `$e3c`; finally it clears IRQ4 and busy-waits until `$bc007` bit 3 (VBLANK) drops, so the handler lasts the whole blanking interval.

Main loop of a play frame (`$6be`, read): wait `$bbe`; `$1308` continue countdown; `$126c` "insert coin / credits" line; `$3d66`/`$3f06` health bars of P1 and P2 into the text layer; `$3e84`; players `$7626`; `$1948` and `$7fe4` (level-specific per-frame logic, bosses); **the object dispatcher `$10254`**; `$18cc` (a lone `rts`); `$da2` (builds sprite RAM from seven source lists, count in `$8004e`, then blanks the rest to fill 256 entries). Then: `$80040` bit 4 (level cleared) goes to `$71c`; both players inactive (`$80100`/`$80180` bit 7 clear) goes to game over; otherwise loop.

The levels: `$80046` is the level 0-5 (six levels). `$71c`: level+1 > 5 sets `$80040` bit 6 and runs the ending `$5fba` (state word `$80016` through a table at `$600e`), else the level byte goes up, `$8624` (a grid wipe, eight effects in table `$8758`, effect id in `$804ae`; there is no score tally), `$172a` (the clear sequence: three 128-frame text pages `NICE FIGHT!`, `STAGE n CLEAR`, `GO TO NEXT STAGE!`, then the stage card, which loops until `$80040` bit 4 clears) and back to the per-level setup `$1488` (clears `$8004a`, loads palettes `$706e`/`$7098` (`$708c` = `$1111 $2121 $3131 $4141 $5151 $6162`, `$70b6` = 1-6), music `$e1c` from tables at `$1532`/`$153e` (levels 0-5 = 1, 7, 9, 8, 7, 6 in a game; 6, 7, 9, 8, 7, 6 in the demo), scroll/level data, the players' reset `$154a`). Game over sets bit 5 and returns to the attract loop `$66c` (`clr.w $80040`).

Start of a game (read): `$e3c`, called **from the VBL handler**, on a start press with a credit in `$80032` (BCD, `sbcd`) sets `$80040` bit 7 and `jmp $696`, which resets the stack to `$84000` and enters the game from interrupt context (the interrupted attract is abandoned). Credits: `$1148` adds per coin using a coin-per-credit table at `$11f8` indexed by the dip switches. Observed: coin held at frame 600 gives `CREDIT 1`, start at 700 begins level 1 at about frame 720 (`plans/play1.lua`).

Attract loop `$66c` (`world/world.md` section 1 has the full frame table; the cold-boot cycle with no input is 5,526 frames after the first 4306): `$8038`, protection `$13e2`, intro `$4a9e` (state word `$80016`, seven states through table `$4b2a`...: skyline loading, `NEW YORK A.D.2010`, sun and silhouette, nuclear dome text, `20 YEARS AFTER`, `AND NOW`, the two heroes), then repeatedly `$4076` (title: logo, `INSERT COIN`; `$80041` bit 2 set for the phase), `$762` (two-player demo: levels 1, 2, 3 in turn, demo 0 from frame 4307, 633 recorded frames), `$6c94` (best scores, ending with the `DATA EAST PRESENTS` logo) and the story again. `$80016` is shared by `$4a9e`, `$4076`, `$6c94` and `$5fba`. The demo: `$83e`/`$8ce` fill both player flags and point the input reader at recorded streams; `$fec`/`$10b2` replay pairs (held input byte, repeat count) from ROM `$5c000` (P1) and `$5d000` (P2), pointer tables `$5e000`/`$5f000`. **3798 of 3798 frames** of the three demos' expanded streams equal the attract run's inputs (`world/py/demo_check.py`); a fresh game fed the same streams follows the demo for 386 to 536 of 633 frames, then drifts by 1-2 px (cause inferred: enemy random numbers).

## Input and sound

- Controllers: `$faa` reads `$bc001` (P1) and `$bc000` (P2), inverts them, and keeps held bits in `$80051`/`$80053` and newly pressed bits in `$80050`/`$80052` (bit 7 start, bits 4-6 buttons, bits 0-3 up/down/left/right as in the port). DIP switches: `$f94` stores the inverted `$bc002` word at `$80054` (low byte `$80055` is SW1: bit 6 = flip; bit 7 of `$80054` = demo sounds on).
- Sound: every music or effect request goes through `$e1c`, which writes the byte in D7 to `$bc002` unless demo sounds are off and no game is running. The only other latch write is `move.w #$13,$bc002` at `$11ee` (coin sound, after the protection check). 94 `jsr $e1c` sites exist; a recursive listing finds only 27 of them, a raw scan of the image all (`sound.md`).

## Objects

Three pools, each a table of record pointers (`py/kernel/static_gate.py`, all PASS):

| pool | records | table | type handlers | content (read, to be named by the mechanics pass) |
|---|---|---|---|---|
| A | 16 x `$40` at `$81000` | `$10358` | 80, `$10418`, code `$10778-$21fff` (78 distinct) | enemies, bosses, the health item (type 61, `$1e706`, +8 energy) and other items (59 explosion, 60 `BUTTON!!`, 62 timer object); types 0-2 share `$10778` |
| B | 32 x `$40` at `$81400` | `$10398` | 84, `$10558`, code `$28000-$2bfff` (46 distinct) | props, hazards, decoration and comic hit text; liftable props show a 192-frame `PICKUP!!` hint in stages 1-3; **no pick-up items and no score for destroying a prop** (`world/world.md` section 4) |
| C | 8 x `$20` at `$81c00` | `$106a8` | 44, `$106c8`, code `$22000-$22fff` (5 distinct) | **enemy attack hit boxes**: one frame each, re-created by the owner every frame; damage `4 x` a ROM table at `$fcba` (four DIP rows; 16 of 16 overlapping types match row 0); `$220ac`/`$2227c` are multi-frame (`world/world.md` section 6) |

`$10254` (read): first the two script spawners `$f388` (list A) and `$f438` (list B), then for each pool every record whose byte 0 has bit 7 set gets `handler[record+2]` called with A6 = the record. Pool A also counts its live records in `$81e02` and sets `$81e03` bit 7 when the count is 5 or more; `$f388` does not spawn while that flag is set. **Gate** (`throttle_gate.py`, 4000-frame play of `plans/walk1.lua`): 21 of 21 list A spawns happened with fewer than 5 live pool A records and the block flag clear at the previous frame's end; the flag was set whenever the count reached 5 (11 of 11 change events with count >= 5). So at most five script enemies are alive at once. Players are not in the pools: P1 is `$80100`, P2 `$80180` (stride `$80`), updated by `$7626`. Shared engine helpers (movement, animation, collision, damage) are in `$22000-$27fff`; the type-1-to-3 handler `$10778` calls `$22c56`, `$22dac`, a state dispatch on `record+3`, `$22540`, `$2331c`, `$2242c`.

Record fields proven by the spawn gate: `+0` bit 7 active (`$80` set by the spawner, other bits such as `$40`/`$08` appear on live records), `+2` type, `+8` x word, `+12` y word, `+16` variant byte. `+3` is the handler's state (read from `$10778`'s dispatch and the type-18 handler `$1654c`).

### Level scripts

`$6c000` (list A) and `$6d000` (list B) each hold six longword pointers (one per level, index `$80046`) to 8-byte entries ending in `$ffff` (`static_gate.py`):

| level | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| list A entries (enemies) | 42 | 33 | 59 | 32 | 60 | 47 |
| list B entries (props) | 26 | 57 | 25 | 34 | 28 | 6 |

Entry: word trigger, byte type, byte variant, word x, word y. Bit 15 of the trigger selects the compared scroll counter: clear compares against `$8040a` (horizontal), set against `$80406` (vertical; **no entry of the 449 uses it**, stage 6 climbs through its scroll map); an entry fires when the trigger is at or below the counter (horizontal) or equal to it (vertical). The spawner copies type to `+2`, variant to `+16`, x to `+8`, y to `+12` of the first free record and advances the list by 8; list A spawns at most one entry per frame and drops the entry if its 16 records are all in use, list B spawns every due entry in the frame and, if the type's bit 7 is set, searches from record 24 instead of record 0 (and clears that bit). **Gate** (`spawn_gate.py`): 32 of 32 entries the two pointers passed over in the 4000-frame play matched a newly active record with the entry's type, variant, x and y in the same frame. The scroll counters (`$8040a` x, `$80406` y, high byte = page, origin `$100`) start at `$100`, except level 5 where `$80406` starts at `$700`. Scrolling is driven by the per-level page map `$8908` (blocked directions, hold zone, forced scroll, end of area), stops while `$80400` bit 5 is set (25 handlers set it, 12 clear it) and while 5 pool A records live (`world/world.md` section 2.2).

## Flags

Named from their handlers with a check per bit in `world/world.md` section 7 (writers from the linear listing, observed transitions with frame numbers). Summary:

| cell | bit | name |
|---|---|---|
| `$80040` | 7 / 6 / 5 / 4 | game running (start `$eda`, cleared by `$758`) / game completed (ending) / game over (blocks joining) / level cleared: set by the **player's** victory pose (`$c86a`, `$ca6e` are in the player handler; `$20bd4` is pool A type 72, levels 3-5), consumed at `$6f4`, cleared `$da14`; a poke runs the full clear sequence |
| | 3 / 2 | victory: set when a boss that raised `$80041` bit 7 finishes dying (each player then enters action `$f`, the victory pose, and bit 4 follows 255 frames later: frames 14626, 14627, 14882 of a natural god-mode level 0 run, `enemies1/enemies1.md` 6.2) / boss fight (17 setting handlers, enables the boss energy bar `$3f06`; observed `80>84` at frame 4250 and `84>80` at 6738 while boss energy `$8005c` fell `$10` to 0) |
| `$80041` | 0 / 2 / 3 / 4 / 7 | transition (wipes) / title screen / clear sequence / continue prompt / boss event B (set by 7 of the 17 boss handlers) |
| `$80014` | 4 / 3 / 1, 0 | demo armed / demo replaying / developers' record switches (never set) |
| `$8005a` | 7 / 6 / 5 | continue accepted / continue running / continue button held |
| `$80400` | 5 / 7 / 6 | lock holder alive / scroll frozen / forced scroll |
| `$8005c` | | boss energy |

## Corrections to what a first look suggests

- The listing from `tools/rdis.py` is not whole-program: it does not follow the `lea ... / movea.l 0(A0,D0.w),A0 / jsr (A0)` longword state tables inside the type handlers (they print as `ori.b` garbage), so flag-writer scans must use the linear listing `tools/disassemble.py --rom <img> --base 0 --all 0 2d000`. The first scan of `$80040` bit 4 found no writer; the linear listing found `$c86a`.
- The first table in `$10418` looked like a crash-dump pointer (`$164`): it is not; the 80-entry pool A table starts at `$10418` with `$10778`.
