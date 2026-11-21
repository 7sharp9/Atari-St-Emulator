# Starglider front end: loading, pictures, sound, screens and the HUD

Everything around the flight engine: how `STAR.BIN` unpacks itself, the two pictures it loads, the sampled sound
played through the YM volume registers, the title and game-over flow, the interrogate screen, and the cockpit display.
Addresses are runtime absolute; `N(A6)` is the global block at `$5bf00`. Scripts are in `py/frontend/`. This area had
one pass: the picture format is gated, most of the rest is read from the code and confirmed by driving the screen,
and the HUD has a poke test.

## 1. Loading

**Unpacking `STAR.BIN`.**
- The file is a GEMDOS program whose body is a Pack-Ice 2.x stream (`ICE!` at file offset `$1ba`, `$3c652` bytes
  packed, `$4bb26` unpacked).
- The stub at `$ab8c..$ad2a` (bit reader `$ac3c`, tables `$acee..$ad2a`) depacks it in place. The result is itself a
  GEMDOS image (text `$4b6d8`, ending at `$56264`). The stub relocates that image, moves it to `$ab8c`, clears BSS
  and jumps there.
- The image starts with `bra $c9e6`, the game entry. It sets `A6 = $5bf00` and `A7 = $2393c`, enters supervisor mode,
  initialises the display (`$1382c`) and installs the input handlers (`$b62a`, `flight.md` section 1).

**The depacker.** `ice_depack.py` is transcribed from that stub. It finishes with the source pointer exactly at 12 on
all three streams it was run on. This is the Ice algorithm as Starglider ships it:
- Matches copy D4 + 2 bytes.
- Literal-length codes use 2, 2, 3, 8 or 15 bits (compare values 3, 3, 7, `$ff`, `$7fff`; added 1, 4, 7, `$e`,
  `$10d`).
- Match lengths add 0, 1, 2, 4 or 8 with 0, 0, 1, 2 or 10 extra bits.
- Offsets are 8, 5 or 12 bits (added `$1f`, −1, `$11f`), with a 6- or 9-bit special case for D4 = 0.

`tools/lsd_depack.py`'s inferred Ice path fails on these streams ("match out of range").

**Files.** The game opens exactly two files, with plain `Fopen`/`Fread $8000` to `$70000`/`Fclose` (`$f576..$f600`):
`title.tra` and `result.tra`. The GEMDOS trace through 100M steps, including the launch, shows nothing else.
- The names `SHAPE.DAT`, `star.snd` and `clare1..4.snd` at `$151b6..$1522e` are never opened (leftovers, inferred).
- `COS_SIN.TAB` on the disk is never opened. The game's sine tables are built into the image (`graphics.md`
  section 2).

**Who unpacks the pictures.** The game does not. The `.TRA` files on the Zuul disk are Ice-packed, and the Zuul
launcher `2.PRG` leaves a resident trap #1 hook behind (`$84 → $a690`). After every real `Fread` the hook unpacks an
`ICE!` buffer in place (`$a6de`). The original release presumably shipped them unpacked (inferred).

## 2. The `.TRA` pictures

Both files unpack to `$7d90` bytes:
- A `$90`-byte header: a 16-byte nibble permutation table at +0 and 16 ST palette words at +`$14`.
- 32,000 bytes of **chunky** 4-bit pixels, 160 bytes per row, high nibble left.

`$15656` converts the chunky body to the ST's planar screen. A variant, `$156c4`, applies the permutation table; what
the table is for is not known.
- `title.tra` is the title artwork, kept planar at `$68022` with its palette at `$68002`.
- `result.tra`, despite its name, is the empty cockpit, [`cockpit_tra.png`](cockpit_tra.png). It is kept at `$60022`
  and is the frame of the flight screen and the background of the credits page.

**Proof.** `tra_render.py --check` prints three lines:
- "depack vs game RAM bytes equal: 32144/32144";
- "title.tra chunky body vs displayed planar screen: 64000/64000";
- "header palette == live palette: True".

## 3. Sampled sound

All the game's sampled sound goes through one Timer A routine that plays 8-bit samples as a three-channel YM volume
DAC.

**Starting a sample.** `$c5dc` returns if the sound flag `715` is off. Otherwise it reads a parameter block in low
memory: pointer `$a0`, length `$a4`, TACR `$2cf` and TADR `$2d0`. It then:
- installs `$c684` on Timer A (`$134`);
- turns off all YM tone and noise channels (mixer register 7 = `$3f`);
- enables the timer.

**The handler, `$c684`.** It reads the next sample byte through an absolute address that it increments in its own
code (the long at `$c68c`). The byte indexes three 256-byte tables (`$c6d6`, `$c7d6`, `$c8d6`), and the three results
go to YM volume registers 8, 9 and 10 with `movep.w`. The remaining length is at `$c9e2`; at zero, `$c9d6` stops the
timer.

**The samples.** The rate is 2,457,600 / 50 / TADR.

| data | length | rate | played by |
|---|---|---|---|
| `$2a340` | `$2bc00` (18.2 s) | TADR 5, 9830.4 Hz | title music (`$ce1c`) |
| `$23940` | `$1b80` | TADR 8, 6144 Hz | missile launch (L, `$d52e`) |
| `$254c0` | `$1d00` | 6144 Hz | docking complete (`$10246`) |
| `$271c0` | `$1680` | 6144 Hz | low energy, 606 < `$2ee0` (`$cae6`) |
| `$28840` | `$1b00` | 6144 Hz | low energy, 606 < `$2ee0` (`$cb28`) |

The sample loader `$df0c..$df84` adds `$80` to every byte, turning signed samples into table indices.
`export_samples.py` writes each sample as a WAV, approximating the summed level of the three volume registers. The
three-table sum is monotonic for only 210 of 256 entries, so the amplitude is approximate, and the WAVs have not been
checked by ear or against Hatari. The rate and length are exact.

**Synthesised effects.** `$ac9c` (D0 = effect id, D1 = parameter) plays everything else. It returns while a sample
is playing (`$c9e2` not 0), when sound is off, or when `$29c` is set. Otherwise it dispatches through the 8-byte
entries of the table `$c3e0` to `$ad0c`, which drives the YM from a second Timer A handler, `$adb4`. `$acce`
silences everything. The effect table has not been decoded.

## 4. Screens and flow

**The title, `$ca34..$ca72`.**
- It alternates the title picture (`$e6e6`) with a credits page drawn over the cockpit (`$e70e`, text at `$e732`),
  one page per pass of `$44c` clock ticks.
- It restarts the music whenever it has finished.
- K opens DEFINE AGAV CONTROLS ([`controls.png`](controls.png), `flight.md` section 2).
- G opens the object gallery, but only in practice mode.
- Any other key, Space included, goes straight into flight with "YOU NOW HAVE MANUAL CONTROL!" and the LEVEL 1 banner.
  There is no launch prompt at the start of a game.

**Docked.** The docked screen ([`docked.png`](docked.png), `$cb58..$cbb0`) reads "Lasers and Shields replenished.
Press SPACE BAR to launch, or I to Interrogate computer."

**The interrogate screen, `$d5d0..$d6fc`** ([`interrogate.png`](interrogate.png)). It is reached only while docked.
Each page:
- shows one database entry: its name, two lines of description, and its model drawn by the game's own `$f6a8` and
  turning by `$40` per pass;
- starts the model at distance `$1e00` and brings it in by `$64` per pass down to `$400`.

Space shows the next page and E returns to the dock. The names and the type table are in `objects.md` section 2.

**Game over.**
- An energy or shield underflow (`flight.md` section 4) shows its message (`$cd34`). The game then waits for a key or
  `$12c` ticks.
- `$13596` shows the AGAV PILOT RATING ([`rating.png`](rating.png)): shots fired, hits scored, silo dockings, hits on
  the AGAV and accuracy. The grades run ROOKIE, AVERAGE, ABOVE AVERAGE, ACCURATE, DEADLY, SUPER FLYER, ACE PILOT,
  COMMANDER, plus CHEAT!?! (strings at `$13650`).
- `$b99c` checks the score against the ten BCD longs at `$c31e` (names at `$c0b2..`) and asks for a name.
- The game restarts at `$ca20`.

Poking the score (`w c098 09999999`) and the energy to 1 reached the name entry. Typing ABC and Return gave the STAR
SCORES table with ABC at 09999999 ([`scores.png`](scores.png)).

## 5. Text

`$bcba` and `$bd0a` are indirect jumps (`movea.l 60(A6)/56(A6),A5; jmp (A5)`) through a vector table that `$1382c`
fills for the display mode (`706` bit 1).

**Colour.** `60 = $bdf0`, `56 = $be78`. `$bdf0` prints a NUL-terminated string:
- A0 is the screen address and A1 the string.
- CR is ignored and LF moves down 8 rows.
- A byte with bit 7 set changes the plane mask `$c57c`, which is the colour.
- Glyphs are 8 bytes at `$21914 + (c − $20) · 8`, blitted by `$bfb0`.

`$be78` is the same with a cursor (`$c1f8` column, `$c1fa` row, `$c1fc` pointer).

**Monochrome.** `$bcc0`/`$bd10` print with 32-byte glyphs at `$21c74` through `$c052`.

## 6. The cockpit display

The text items in the top bar:
- **Score:** the BCD long at `$c098`. `$b91a` adds a BCD amount with `abcd` and prints the 8 digits (`$c0a8`) at
  screen offset `296(A6)`.
- **Top-right box:** `646(A6)`, the most recent award, printed as four hex digits by `$f60e`. Because awards are BCD,
  the hex digits read as decimal. `$fc12` copies the pending award `212` into it each pass.
- **Compass letter:** N, E, S or W from the yaw (`$10ac4..$10b50`).

The bottom row:
- The two-digit pairs under the scanner are the craft's grid cell, x / `$290` and z / `$290`, each mod 100
  (`$10a34..$10ac0`). They are not a score.
- The digit at the bottom left is the missile count `632` (`$10b54`).

**`$103fe` draws the gauges** (colour mode only):
- the left vertical gauge, from altitude (−y >> 6 & 31, flashing below 8);
- the right vertical gauge, from speed (`542` >> 4 & 31);
- three bars from shield `608`, energy `606` and laser `650` (each >> 11 & 31), with patterns from `$10bb2`; energy
  blinks on `638`;
- two animated icons from `$118b6`/`$118f6`.

**Proof.** `hud_poke.py` pokes one global, runs 300,000 steps and diffs the rendered screen against a no-poke control
from the same snapshot. Each poke changes only its own area:

| poke | changed area (x, y) |
|---|---|
| energy `606` | 240..271, 145..148 |
| shield `608` | 52..69, 145..148 |
| `646` | 241..270, 1..6 (57 pixels) |
| missiles `632` | 65..70, 192..197 |
| altitude `304` | 38..41, 171..198 |
| score `$c098` | the score digits |

A control poke at an unused address changes 0 pixels. The speed gauge is not proven, because `$12340` rewrites the
speed every pass; it would need the poke at `$103fe`'s entry.

## Open

- The `.TRA` permutation table's role.
- The synthesised effect table `$c3e0` and its handler `$adb4`.
- The sampled sound checked against Hatari.
- Esc's target `$eb7e`.
- The red icon next to the compass.
- The name-entry code `$ba2a/$ba92`.
- A census of all 410 text calls per 68 passes.
