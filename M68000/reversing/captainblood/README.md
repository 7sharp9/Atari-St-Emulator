# captainblood: Captain Blood (ERE Informatique / Exxos, 1988), first look

Captain Blood boots from the Zuul #40 compilation menu and runs: the title, the bridge, the galaxy map, hyperspace,
the canyon flight, the planet scan and the UPCOM icon conversation with two races have been reached (the conversation
by a labelled poke that skips the canyon flight, or by the ESC key in flight, see "Running it" and "Canyon flight"). This is the **French build**: the vocabulary is
French, and the crack has overwritten the header text. The reason to reverse it is the conversation system: a
120-word icon vocabulary, a rule list per alien race and a bit array of state; the rule interpreter is decoded and modelled in `rules.md`.

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
  `BLOOD.COM` (the conversation data), `BLOOD.CPT` (the save-game file, see "Galaxy and terrain"), `ARCHE` (a 32,000-byte
  screen), `CLONE` (140 bytes packed, role unknown), `IKON.DTA` (the icons).
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
setup the flight code reaches by `bra $d8c0`. An unsteered flight ends in a shoot-down
screen and a return to the cockpit (`$db16`), so the conversation results below were taken on this poked route. `$d8c8` is also
reached with no poke by holding ESC in flight (`py/canyon/routes.py`, "Canyon flight").

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
| `$b10` | **stream B** (`$783` bytes): three mask bytes per 8 plain-rule elements: required, omit from the reply, not looked for (gated, `rules.md`) |
| `$b10 + $783` | **stream A** (`$2757` bytes): the rules. A record is a header byte (type in the top 3 bits, payload length in the low 5), a flag byte and the payload; each race's list parses exactly to its `$ff` terminator. The record types, flag bits and what they do are in `rules.md`; three races' rules read as words are `tables/izwals_rules.txt`, `croolis_rules.txt`, `yukas_rules.txt` (`py/rules/dump_rules.py <race index>`) |

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

The routines are modelled in Python (`py/rules/cbmodel.py`) and gated against `callcap`: 1750/1750 cases of the
engine and its four sub-routines on the Izwal conversation, with seven broken-model controls that each fail
(`rules.md`, `uv run python reversing/captainblood/py/rules/gate.py`). In short: `$e45a` rolls the ST's random number
(XBIOS 17, `$bd82`) and on 1 roll in 16 sets state bit 7; it runs the leading action records, then walks the race's
stream A. A condition record tests state bits, or for two of the types the clock; a plain record goes to the matcher
`$e6a2`, which compares the player's tokens (`$e3f2`) with the rule's (exact, always, or every required element present
under the stream B masks, some rules behind a coin flip); the matching rule's own payload, less the elements its mask
marks as not echoed, is composed into `$e412` (token 3 inserts a planet's coordinates, 2 a number, read) and drawn into
the alien's line; `$40` records set (positive) or clear (negative) state bits. When no rule replied the scan
restarts from the top, re-rolling, up to the retry counter `$e3ee` allows (the second `$e45a` hit in the census is
that first rescan, entered by a branch). The gate NOPs the redraw call at `$e584` (a poke); the redraw, `$e284` and
`$e344` are not modelled.

Buffers: the player's sentence at `$dc32` (length word) and `$dc34` (8 icons), the alien's line at `$dc44` (8 icons).
`$e3f0` bit 8 means the alien has more to say: an icon click is refused while it is set, and each mouth click then
shows the next part (four parts in a row seen from `u2.snap`).

## Galaxy and terrain

**The table.** 128 planets at `$ba4e`, 4 bytes each: a position word (high byte y, low byte x), a zero byte and a status
byte. The position is `$ba46`, the planet found there `$ba48` (`$ffff` for none). Only the position is random. The status
byte is the planet's 5 bits at state bit `100 + 5*index` of `BLOOD.COM`'s state array (file offset `$810`, runtime
`$61c10`), copied in by `$b942` after `$b830` finishes: it equals the file's bits for 128/128 planets in two arms, so
which index is inhabited, and its race (index >> 4), never changes; only where the index sits on the map does.
Status values are `$02` (53 planets), `$0b` (18), `$12` (10) and `$1b` (47); bit 1 is set on all 128 and bit 4 on 57. A
contact needs status bits 0 and 3: 65 of the 128, 16 each in index groups 0, 1, 3 and 6 and 1 in group 4.
`py/galaxy/status_check.py scratchpad/captainblood/depacked/BLOOD.COM scratchpad/captainblood/galaxy/arms/ctl1.txt`.

**The generator `$b830`** (named from its body; its only caller is `$b7f8`, the start of the game) draws from XBIOS
Random (`$bd82`, trap #14 function 17) from entry 127 down to 0. Entry 127 is one draw with the low byte halved and no
filter. Each later entry draws until the word is `>> 1`, its low byte (x) is in `9..$f6`, the word is in `$801..$78ff` (y
from 8 to 120) and it differs from every entry already placed. Entry 0 is the start planet. The Random routine is TOS
1.00's own (`$fc132c`, from the trap #14 table at `$fc07ce`; the emulator runs the ROM's code): if the seed `$29b8` is 0 it
is set to `(hz200 << 16) | hz200`; each call is `seed = seed * $bb40e62d + 1` and returns `(seed >> 8) & $ffffff`.
`py/galaxy/galaxy_model.py` reproduces the position words from the `_hz_200` count alone: 128/128 on the ordinary run
and on five poked seeds (hz200 2161, 2159, 4000, 1 and 2200); broken-model controls (multiplier, increment, shift, seed
plus one) give 0, 1, 0 and 0 of 128. The y-bound and duplicate rules are read from the code: the gate does not discriminate
them (no draw in these runs hits either), so changing them leaves 128/128.

**Determinism.** The seed is `_hz_200` (`$4ba`) at the first Random call, and the game freezes that count itself: `$bec6`
(`andi.b #$c0,$fffa09`, inside the routine at `$beae`) switches Timer C off 2.4 to 2.5M steps after F3, leaving `$870`
(2160) from there to the galaxy build. The count is `$546` in both the 60M and 150M menu snapshots, so time spent at the
menu or at the title's key wait does not enter it. Ten arms from `f3_33M.snap` with no poke (identical input twice, a
key delay of 1, 500, 3,000, 9,000, 100,000 and 1,000,000 steps, a key hold of 203,000 and 300,000) all give seed
`$3c197fb5` and the same table: 0/128 planets differ in position, 0/128 in status. Arms with the count poked
(`w 4ba <value>` before the title key; a poke) give a wholly different position set for each value (128/128 planets
differ from the ordinary run in position for 2159, 2161, 2200, 4000 and 1; for 2159, 2161 and 4000 at most 1 of 128 coordinate words is shared) with
the status fields unchanged (0/128 differ). The poke at the natural value 2160 reproduces the table (0/128), so the poke
path itself changes nothing. `py/galaxy/arm.sh`, `runarms.sh`, `diffarms.py`.
Same galaxy on every boot: in this emulator, yes, because timing is by step count. On real hardware it depends on the
tick count when the game switches Timer C off, which is the time TOS boot and the loads take and nothing the player does;
one tick of difference gives a different galaxy. That real-hardware variation is inferred from the code and the emulator's
fixed 3000-steps-per-tick timer, not measured on hardware or in another emulator.

**The save file.** `BLOOD.CPT` is a 4096-byte save block (header `$18`, the longs `$f6f8` and `$cb32`, the 256-byte state
array `$61c10`, then 197 longs from `$b9bc`, which includes the galaxy table; file offset of the table `$1b2`). The cockpit's
hit table (`$d58a`, entry 2, handler `$d044`, pointer about (60,36), enabled only on the cockpit screen, left click) loads
it with Fopen/Fread of `$1000` bytes to `$70000`, and `$d106` onwards writes it (Fcreate/Fwrite; read, not run). After the
load click the table equals the file's for 128/128 entries (0/128 before), with the status bytes equal to the generated
galaxy's 128/128; no hz200 in 0..65535 reproduces the file's galaxy, so it is not an output of this generator.
A loaded game therefore has a fixed galaxy whatever the seed was. `py/galaxy/cpt_load.sh` (it includes `cpt_check.py`).
In an ordinary boot to the bridge the game opens `ethnicol.jar` (ten times, failing), `blood_vx`, `blood_k`, `blood_i`,
`blood_p`, `arche`, `ikon.dta` and `blood.com` and never `BLOOD.CPT` (a GEMDOS chain over 17 opener hits; `blood_m` was
not among those captured). `CLONE` has no name string in the image and no opener hit; the FDC trace shows its two sectors
read, but in 10-sector multi-reads, so that is not evidence it is opened (`py/galaxy/fdc_files.py`, with `PACT.TOS` and
`PACT2.TOS` read 0 as the negative control). Its role is unknown.

**Status bit 4** (read, not run). `$10bbc` (`btst #4,$ba4a`, the current planet's status) in the canyon-flight setup
selects `$10a74 = $a0` instead of `$f8`; the reader of `$10a74` was not found. `$b8f6` writes back only status bits 0 to 3
and sets bit 2, so bit 4 comes from the data file; `$fbb0` clears it for the current planet in the scan routine `$fb36`.
- The canyon flight `$10686` seeds a generator at `$f35c` (multiplier `$b0a1`, state `$f384`) from the planet, so the
  terrain is a function of position (read, not run; the flight is in "Canyon flight").

## Canyon flight

The flight is run from `$10686`: setup, then `trap #15` (vector `$beaa`: `jsr (A0)` then `rte`) runs the loop `$10b8a..$10d40` in
supervisor mode, and `bra $d8c0` follows its return. `$d8c0` tests `$10642`: negative goes to `$db16` (cockpit), else `$d8c8`
(the contact setup). The terrain is a 16 KB byte array at `$70400`; a path of 64 entries at `$10a8a` (4 bytes, first word the
byte offset into the array, rows `$400` apart, the path column `$200` in a row) is the player's row sequence, and one render pass
draws the profile of the rows ahead.

| routine | what (named from its body) |
|---|---|
| `$10bde` `canyon_main_loop` | per pass: collision check, row advance, `$10d8c` rows, `$10a0a`, `$107b4`, key byte `$c5c2` |
| `$10c24` `canyon_collision_cmp` | `cmp.w 26(A6),D0`, D0 = `((T[o]+T[o+1])>>1)+1`; D0 above the altitude goes to the bump `$10c2c` |
| `$10c2c` `canyon_bump` | `$10a4a += 1`, speed to 0, waits on Timer A flag `$11a94` (about 3M steps here), the loop goes on; not fatal |
| `$10d14` `canyon_exit_land` | `$11568` touchdown, `$10642` cleared, `rts`: reached by key `$c5c2` = 1 or `$110f6` negative |
| `$10d42` `canyon_exit_shot_down` | reached when the byte `$10a4a` is non-zero; leaves `$10642` = -1, so `$db16` |
| `$11568` `canyon_touchdown` | altitude to max(altitude, terrain)+4, rows until `$10a50` = 2, then the ground scene (`$11624`..`$116ae`) |
| `$10d8c` `canyon_draw_rows`, `$107b4` | wireframe profile of a row from `$70400`; the altitude gauge |
| `$10a0a` `canyon_steer_path` | adds ramps of (x-110)*512 to 13 path entries; integrates the heading `$10a56` |
| `$c746` `flight_packet_handler` | pointer to `$10a62`/`$10a64`, buttons to the speed `$10a54`, y to the altitude |
| `$11348` row generator, `$113ca`/`$113fa` smoothing, `$11014` PRNG (`x*$3171-1` on `$1109e`) | **read only**: no model, no callcap gate |
| `$11126`, `$111da`, `$11248` | landing pad spawn, its lateral test (`|$11120 - row offset| <= $48`), the ravine (read; the spawn and the start of the ravine were observed running, below) |

Variables: `$10a4c` path index; `$10a54` speed 0..22 (right button +1, left -1 per tick, measured); `$10a56` heading; `$10a62`,
`$10a64` pointer x, y inside the flight (relative moves, centre 110, 56; `$c6ce` is not updated); **`$10a66` the altitude** (a
long, the word is its integer part; it is not a distance) and `$10a6a` its ceiling; `$10a74` the shoot-down limit (`$f8`, `$a0` for a
planet with status bit 4); `$10a4b` the bump count; `$110e0` the pad-spawn accumulator (`$100` a row when straight); `$110f6`
the ravine row counter (`$80` down; negative ends the flight through `$10d14`); `$10642` the exit state.

**Proven.** The collision predicate: at `$10c24` D0 equals the model 52/52 and the branch (bump or not) 52/52; without the
+1 D0 0/52, a shifted column 7/52, a `>=` compare branch 12/52 (`uv run python reversing/captainblood/py/canyon/gate_collision.py 40 12`;
the altitude word is poked at each stop, to D0 in 40 cases and D0-1 in 12, because the natural flight is above every row).
The unpoked route: from `q16_d.snap` the click on "land" then ESC (`kbd 01`) held 200,000 steps in flight gives `$d8c8` 1 and the
hit table `$d5e4` (the conversation); the same 18.2M steps with no key give `$d8c8` 0, `$db16` 1 (`routes.py esc`, `routes.py
control`; also `gates.toml` `canyon`). The key must outlast a flight tick (60,000 steps) and the opening descent ignores it.
**A flight with no input ends in a shoot-down, not a crash**: the altitude stays at the ceiling, above `$f8-3`, and after
more than 8 such packets a missile counter `$10642` grows until `$80` is written to the byte `$10a4a` (about 13M steps after the
click). A terrain hit is only a bump.

**Observed, not modelled.** `fly2.py` (right button for speed, y by the terrain lookahead, x untouched, no poke) from `q16_d.snap`
gets the pad spawned (`$10a86` = `$11154`) at 52.7M steps after the click and the ravine started (`$110f6` = 127) at 57.45M, with
10 bumps. The ravine is walls of `$f0..$ff` bytes with a narrow slot that drifts; straight flight bumps at `$110f6` = 107 and a
proportional x controller (`fly3` in the first pass, not promoted) reached 103 by 40M steps and no further. With `ww 110f6 ffff` on
`fly2_landing.snap` (a labelled poke on the flight's own state) `$d8c8` is reached in 12M steps, `$d8c8` 0 without it.
**Inferred:** ESC (scancode 1) as the game's own landing or skip key is not checked against the manual; that Timer A's long wait
is the emulator's fixed-step timer; the ravine's wall and slot geometry (read from RAM dumps).

## Open

1. A steered canyon landing: mouse steering reaches the landing pad and the ravine's start but not its end
   ("Canyon flight"); then the speak census again on that route (the ESC route reaches the conversation screen, the census on
   it is not run).
2. The rule language is modelled (`rules.md`). Open: the vocabulary flag bytes, what the state bits mean beyond the
   three read in `rules.md`, and driving races other than Izwals (3, 4 and 6 are decoded from the data only).
3. The icons as a PNG tied to the vocabulary (the grid mapping `$dc54`, `$dc56`, `$e046`), then scripted sentences.
4. What `CLONE` is (unopened in a boot to the bridge; no name string in the image); who reads `$10a74` and what planet status bit 4 selects (find the reader, then `watch`); `ethnicol.jar`.
5. Real-hardware galaxy variation: the emulator's Timer C is a fixed step count, so only a hardware or cycle-timed run can show how much `_hz_200` at the Timer C shutoff varies between boots.
6. `bp b26e` never stopped (0 hits in 60M steps) though the trace shows `Supexec($b26e)`: not diagnosed.

## Files

| file | what |
|---|---|
| `py/jekdepack.py` | the `JEK!` depacker: `<in> <out>` or `--all <dir> <outdir>`; prints the size and the checksum residue |
| `py/blood_com.py` | parses a depacked `BLOOD.COM`: vocabulary, race table, each race's rule records by type |
| `py/hittab.py` | dumps a snapshot's current hit-test table |
| `py/drive.py` | pointer to (x, y) by exact relative moves, click, settle, snapshot and render |
| `py/canyon/repl.py`, `gate.py` | a persistent REPL wrapper (`Repl`); the gate: the collision predicate 52/52 and the ESC route against its control, also `gates.toml` |
| `py/canyon/gate_collision.py` | the flight's collision test at `$10c24` against the emulator: D0 52/52, branch 52/52, three broken controls fail |
| `py/canyon/routes.py` | `esc`, `control`: `hits` on `$d8c8` from `q16_d.snap`; `landing`, `landctl`: the labelled `$110f6` poke from `fly2_landing.snap` |
| `py/canyon/fly2.py` | closed-loop mouse flight (altitude from the terrain lookahead, right button for speed, x not moved) to the pad and the ravine |
| `py/goto_planet.sh` | bridge to a planet's conversation screen, with the labelled `$d5c0` poke |
| `py/census_speak.sh` | the reply engine under a mouth click against a no-click control |
| `py/galaxy/arm.sh`, `runarms.sh` | the galaxy build from the title's key wait with a chosen key delay, hold and optional `_hz_200` poke; dump of `$ba4e`, `$ba46`, `$29b8`, `$4ba` to `scratchpad/captainblood/galaxy/arms/` |
| `py/galaxy/diffarms.py` | the arms' tables against `ctl1`: `ctl1` 0/128, ordinary-input arms 0/128, poked-seed arms 128/128 in position and 0/128 in status |
| `py/galaxy/galaxy_model.py` | TOS Random plus the `$b830` loop from the `_hz_200` count: 128/128; `--break mul\|add\|shift\|y\|dup\|seed`, an unknown name is an error |
| `py/galaxy/status_check.py` | planet status byte against `BLOOD.COM`'s state bits, 128/128, and the 65 contact-capable planets |
| `py/galaxy/cpt_load.sh`, `cpt_check.py` | the cockpit load button replaces the table with `BLOOD.CPT`'s: 0/128 before, 128/128 after |
| `py/galaxy/fdc_files.py` | which disk files' sectors an FDC trace read (FAT12 chains) |
| `py/rules/cbmodel.py`, `cbdata.py` | the rule interpreter model and the `BLOOD.COM` loader it uses (`blood_com.py` prints at import, so it cannot be imported) |
| `py/rules/gate.py` | the model against `callcap` of `$e45a`, `$e6a2`, `$e58a`, `$e628`, `$e22e`: `TOTAL 1750/1750`; `--break NAME` for the controls; also `gates.toml` |
| `py/rules/drive_pairs.py` | sentences poked into `$dc34`, mouth clicked, reply compared with the model |
| `py/rules/dump_rules.py` | a race's rules as words with the stream B masks: `tables/*_rules.txt` |
| `rules.md` | the rule language: records, flags, masks, engine flow, proof and caveats |
| `title.png`, `bridge.png`, `galaxy_map.png`, `canyon.png`, `upcom_izwals.png`, `upcom_croolis.png` | the milestones |

Working data (`scratchpad/captainblood/`, gitignored): `disk/ZUUL040.MSA`, `zuul40.st`, `files/` (extracted),
`depacked/`, `zuul_depacked.bin` (the engine image from RAM), the snapshots above, `i1.snap`, and the first pass's
logs and `report.md`.
