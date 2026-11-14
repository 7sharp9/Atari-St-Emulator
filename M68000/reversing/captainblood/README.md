# captainblood: Captain Blood (ERE Informatique / Exxos, 1988), first look

Captain Blood boots from the Zuul #40 compilation menu and runs: the title, the bridge, the galaxy map, hyperspace,
the canyon flight, the planet scan and the UPCOM icon conversation with two races have been reached (the conversation
by a labelled poke that skips the canyon flight, see "Running it"). This is the **French build**: the vocabulary is
French, and the crack has overwritten the header text. The reason to reverse it is the conversation system: a
120-word icon vocabulary, a rule list per alien race and a bit array of state, located here and not yet decoded.

The engine is one hand-written 68000 image (33,852 bytes at `$adfc..$13238`; 0 LINK frames, 227 RTS, 366 BSR), so
the route is trace and callcap, not a decompile.

Evidence in this file is of three kinds. **Re-run from this directory:** the depacker, the `BLOOD.COM` parse, the
hit-table dump and the speak census. **An agent's first pass, read from its logs and screenshots, not re-run:** the
boot narrative, the milestone drives, the depacked files' match against RAM, the clicks that name hit-table entries.
**Read from code only:** marked "(read)".

## Provenance

- Zip: `Zuul #40.zip`, 716,894 bytes, sha256 `f518f34e616939286531db0f5036585162d0f3d5e425ec3e8ca5081873d11917`.
- It holds `ZUUL040.MSA`, 784,485 bytes, sha256 `9efbcc895a566c399f8330a91177f90708d8bc6758021be5e1dd6a0be730998d`;
  `tools/msa2st.py` gives a `.ST` of 839,680 bytes, sha256
  `e3d21cb81009d71113cb8908562e6befc5cf55756eef35c5eef4cc6964835566`. Neither is committed.
- `AUTO/MENU40.PRG` is the compilation menu. It polls F1 to F10 straight from the keyboard ACIA; F3 runs `PACT3.TOS`,
  which hooks trap #1, depacks files as they are read and `Pexec`s `ZUUL.PRG`, the Captain Blood loader and engine
  (19,618 bytes packed).
- Captain Blood's data files: `BLOOD_I` (title picture), `BLOOD_K`, `BLOOD_M`, `BLOOD_P`, `BLOOD_VX` (8-bit samples),
  `BLOOD.COM` (the conversation data), `BLOOD.CPT`, `ARCHE` (a 32,000-byte screen), `CLONE`, `IKON.DTA` (the icons).
  The rest of the disk belongs to the menu's other two programs.
- Every data file ends in a 12-byte trailer: a checksum seed, the unpacked size, `JEK!`. The packer is a long-word
  bitstream read backwards; `py/jekdepack.py` is a transcription of the hook's depacker (`$ab30..$acdc`). Its
  checksum residue is 0 on all 25 `JEK!` files on the disk, and five depacked files equal RAM byte for byte at their
  load address (`BLOOD_VX` `$4b000`, `BLOOD_M` `$58000`, `BLOOD.COM` `$61400`, `BLOOD_K` `$45fce`, `BLOOD_P` `$35ff0`).
- The loader opens `ethnicol.jar` ten times; the file is not on the disk and the game carries on (not analysed).

## Running it

From `M68000/`, with the work directory `W=scratchpad/captainblood`:

```
uv run python -I tools/msa2st.py $W/disk/ZUUL040.MSA $W/zuul40.st
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 150000000 --disk-a $W/zuul40.st snapshot $W/boot150M.snap
```

That is the menu (its cracktro makes no GEMDOS calls after about 3.5M steps and looks like a hang; it is a key poll).
Then, in a REPL on `boot150M.snap`: `kbd 3d`, `s 3000000`, `kbd bd`, 30M steps reach the title picture and its key
wait (`f3_33M.snap`); `kbd 39`, `s 200000`, `kbd b9`, 30M steps reach the bridge at galaxy position 191/012
(`key1_30M.snap`).

The game installs its own ACIA handler (`$118` -> `$c536`), sets relative mouse mode and reads whole packets, so
`mouse move` and `mouse down l` work as they are. The pointer is the words `$c6ce` (x) and `$c6d0` (y), and the game
resets it between screens: `py/drive.py <in.snap> <out.snap> <x> <y>` reads it back from the snapshot, sends the exact
relative moves, clicks, settles and snapshots.

`py/goto_planet.sh <bridge.snap> <x> <y> <prefix>` goes cockpit, galaxy map, target, hyperspace and "land". **Its
last step pokes the land entry's handler long at `$d5c0` from `$10686` (the canyon flight) to `$d8c8`**, the contact
setup the flight code reaches by `bra $d8c0`. An unsteered flight ends in a crash screen and a return to the cockpit,
and whether a clean flight arrives at `$d8c8` is unproven, so every conversation result below is on a poked route.

| milestone | snapshot (`scratchpad/captainblood/`) | picture |
|---|---|---|
| title and key wait | `f3_33M.snap` | `title.png` |
| bridge, planet view, 191/012 | `key1_30M.snap` | `bridge.png` |
| galaxy map | `c_galaxy2.snap` | `galaxy_map.png` |
| canyon flight | `canyon_1..3.snap` | `canyon.png` |
| conversation, Izwals, planet 113/054 (index 1) | `u2.snap` | `upcom_izwals.png` |
| conversation, Croolis, planet 113/042 (index 16) | `q16_e.snap` | `upcom_croolis.png` |

## Screens and input (read; entries named by clicking them)

Each screen has a hit-test table, selected by the long at `$d586`: a count word, then 8-byte entries of x0, x1, y0,
y1 (bytes; x is tested as `(mouse x + 4) >> 1`) and a handler long whose bit 31 disables the entry. `py/hittab.py
<snap>` dumps the current one. Tables: `$d58a` the bridge and planet view (10 entries), `$d5e4` the conversation (11),
`$d650` the galaxy map (3). The handlers are polled while the pointer is over them (the conversation's mouth handler
runs 9,614 times in 600,000 idle steps) and test a click flag at `$c6cd`.

Conversation entries: `$e046` the icon grid, `$e1b4` the mouth (speak), `$ddb8` and `$ddcc` the two halves of the
sentence line, `$e07e` the vocabulary scroll bar. Bridge: `$eade` the galaxy map, `$ec6e` the jump, `$10686` land,
`$101a4` the planet scan, `$f934` a destroy action.

## The conversation data: `BLOOD.COM` (14,826 bytes, loaded at `$61400`)

`py/blood_com.py <depacked BLOOD.COM>` parses all of it; the file's size is exactly the header's two stream lengths
plus the fixed part (`$b10 + $783 + $2757`).

| offset | what |
|---|---|
| `$20` | **vocabulary**: 120 records of 16 bytes, a flag byte (`$40` 72 times, `$c0` 45, `$41` 3) and a name, 1-based. HEURE, FREQ, COORDONNEES; verbs and qualities (VOULOIR, AIMER, CONNAITRE, TUER, DONNER, TELEPORTER, AMI, ENNEMI ...); names (ARCHE, MAXON, OORXX, CROOLIS-VAR, CROOLIS-ULV, YUKAS, BUGGOL, ONDOYANTE, MIGRAX, IZWAL ... BOW-BOW); digits 0 to 9 at 111 to 120. What the flag bits mean is not known |
| `$810` | **state**: a bit array (runtime `$61c10`). Rule conditions test it and rule actions set and clear it (read); it also holds 5 status bits a planet from bit 100 |
| `$910` | **races**: 16 records of 32 bytes: a name, then the offset and length of the race's part of streams A and B. The offsets are contiguous and sum to the header's lengths. Named: IZWALS, CROOLIS, BUGGOLS, YUKAS, ONDOYANTES, MIGRAX, ESPRITS (record 8); the rest are dots or empty |
| `$b10` | **stream B** (`$783` bytes): a bit mask per rule element (read, not decoded) |
| `$b10 + $783` | **stream A** (`$2757` bytes): the rules. A record is a header byte (type in the top 3 bits, payload length in the low 5), a flag byte and the payload; each race's list parses exactly to its `$ff` terminator |

Rules a race: Yukas 695, Izwals 554, Croolis 324, record 6 (unnamed) 153, Ondoyantes 100, Buggols 3, Migrax 2. By
type bits, Izwals: 461 plain, 43 `$40`, 49 `$80`, 1 `$c0`; only Yukas and Ondoyantes use `$a0`.

A planet's race is its index >> 4 (`$d8f8`; seen for indexes 1 and 16 only, where the stream pointers at `$e3d4` held
the race table's offsets).

**Icons.** `IKON.DTA` (5,528 bytes) is expanded by `$c8a6` into 128 records of 38 bytes at `$60100`, ending where
`BLOOD.COM` starts. `$6007e` maps an icon to a token when the sentence is encoded and `$60000` a token to an icon when
the reply is drawn (read; one reply's tokens `15 09 44 17 15` appeared as icons `31 10 06 3a 31`). The bitmap format is
not decoded.

## The reply engine (census re-run; the logic read)

`py/census_speak.sh`: from `i1.snap` (Izwals, one icon in the player's sentence), a click on the mouth against the
same pointer move with no click, 600,000 steps each:

| routine | click | no click |
|---|---|---|
| `$e344` encode the sentence's icons to tokens | 1 | 0 |
| `$e45a` reply engine entry | 2 | 0 |
| `$e494` rule scan loop | 262 | 0 |
| `$e6a2` rule matcher | 244 | 0 |
| `$e58a` condition test | 11 | 0 |
| `$e22e` compose the reply's tokens | 1 | 0 |
| `$e284` tokens to the alien's icon line | 1 | 0 |

Read from the code, each stage seen running above and none of it modelled: `$e45a` rolls the ST's random number
(XBIOS 17, `$bd82`) and on about 1 roll in 16 sets a state bit; it walks the race's stream A; a condition record tests
a state bit, or for two of the types the clock; a plain record goes to the matcher `$e6a2`, which compares the
player's tokens (`$e3f2`) with the rule's (exact, always, or all present under the stream B masks, some rules with a
coin flip); the matching rule is composed into `$e412` (token 3 inserts a planet's coordinates, 2 a number) and drawn
into the alien's line; type `$40` records set (positive) or clear (negative) state bits; if nothing matched the scan
runs once more, which is the second `$e45a` call.

Buffers: the player's sentence at `$dc32` (length word) and `$dc34` (8 icons), the alien's line at `$dc44` (8 icons).
`$e3f0` bit 8 means the alien has more to say: an icon click is refused while it is set, and each mouth click then
shows the next part (four parts in a row seen from `u2.snap`).

## Galaxy and terrain (read)

- 128 planets at `$ba4e`, 4 bytes each: y, x, a status word. `$b830` places them with the ST's random number call,
  rejecting duplicates. Whether the galaxy is the same on every boot, or on real hardware, is untested. The position
  is `$ba46`, the planet found there `$ba48` (`$ffff` for none). A contact needs status bits 0 and 3: 65 of the 128
  qualify in this run.
- The canyon flight `$10686` seeds a generator at `$f35c` (multiplier `$b0a1`, state `$f384`) from the planet, so the
  terrain is a function of position; the flight code is around `$10800..$11400` and is not read.

## Open

1. A clean canyon landing, so the conversation is reached with no poke (flight loop `$10800..$11400`, speed byte
   `$10a54`, distance word `$10a66`, the packet handler `$c746`); then the speak census again on that route.
2. The rule language as a Python model: matcher `$e6a2`, conditions `$e58a`, actions `$e628`, composer `$e22e`,
   gated against `callcap` of `$e45a` over sentences and state bits with a broken-model control. What stream B and
   the vocabulary flag bytes mean. The race rule for races 3, 4 and 6.
3. The icons as a PNG tied to the vocabulary (the grid mapping `$dc54`, `$dc56`, `$e046`), then scripted sentences.
4. Where the duplicates are tracked (`CLONE`, `BLOOD.CPT` are unread); the planet status bit 4; `ethnicol.jar`.
5. The galaxy's seed: is the random state at game start fixed in this emulator, and what would hardware give.
6. `bp b26e` never stopped (0 hits in 60M steps) though the trace shows `Supexec($b26e)`: not diagnosed.

## Files

| file | what |
|---|---|
| `py/jekdepack.py` | the `JEK!` depacker: `<in> <out>` or `--all <dir> <outdir>`; prints the size and the checksum residue |
| `py/blood_com.py` | parses a depacked `BLOOD.COM`: vocabulary, race table, each race's rule records by type |
| `py/hittab.py` | dumps a snapshot's current hit-test table |
| `py/drive.py` | pointer to (x, y) by exact relative moves, click, settle, snapshot and render |
| `py/goto_planet.sh` | bridge to a planet's conversation screen, with the labelled `$d5c0` poke |
| `py/census_speak.sh` | the reply engine under a mouth click against a no-click control |
| `title.png`, `bridge.png`, `galaxy_map.png`, `canyon.png`, `upcom_izwals.png`, `upcom_croolis.png` | the milestones |

Working data (`scratchpad/captainblood/`, gitignored): `disk/ZUUL040.MSA`, `zuul40.st`, `files/` (extracted),
`depacked/`, `zuul_depacked.bin` (the engine image from RAM), the snapshots above, `i1.snap`, and the first pass's
logs and `report.md`.
