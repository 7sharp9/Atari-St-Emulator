# midwinter: Midwinter (Rainbird / Maelstrom Games, 1989)

Mike Singleton's Midwinter: a war on a frozen island, played through 32 characters who ski,
hang-glide, drive snow buggies and ride cable cars across fractal-looking terrain drawn as
filled 3D polygons. It is the repo's first 3D game. The emulator boots it from a French
compilation disk, runs the menu, the title, the team and character screens and the first-person
ski view with an enemy plane attacking, all unmodified apart from two input-bypass pokes in the
menu (below).

## Provenance

| item | value |
|---|---|
| archive | `Zuul #67.zip` (sha256 `1f853028f6e330b92c480f9b7fa7c0afcffa8b64356b395323b55cf5988f9611`), one file `ZUUL067.MSA` (sha256 `9e2b3d59534ffbd66f5e6e0e94f1d71b117c82b4314456220fdda464aad58316`, 753855 bytes) |
| disk image | `tools/msa2st.py` gives `zuul067.st`, 839680 bytes (82 tracks, 10 sectors, 2 sides), sha256 `07bc54a8bbc8792a67e0d812e6972163649a5994fa7b1083ef6f4390fe413a09` |
| compilation | Zuul (French cracking group) menu disk 67: a boot-sector anti-virus ticker ("ZUUL VOUS PRESENTE SON ANTI-VIRUS V1.0 / CODE PAR STIX"), `\AUTO\MENU67.PRG`, F1 Midwinter, F2 the other game (`PACT2.PRG` names `MORTEL.PRG` and `INFEST.2`) |
| game executable | `1.1` (`LSD!`-packed, 85702 bytes) unpacks to a GEMDOS program, sha256 `10acff2dc6f2fe0fe1207b81bf9d495722263c330261e31b35c8cbb2237445dd`: text `$259a2`, data `$7b8c`, bss 0, no relocation table |
| data | `00.2` .. `60.2`, all `LSD!`-packed; `ZZZZZ.PRG` (packed raw code that installs `$68`/`$70`/`$118`/`$114`) |

The disk images and the archive stay untracked.

## Packing

Every game file is `LSD!`-packed: a byte-buffer variant of Pack-Ice 2.x whose decoder is in the menu's
`PACT.PRG` (text `$1f6` checks the magic, `$2d4` decodes). `tools/lsd_depack.py` is transcribed from that
routine and unpacks all 63 files on the disk; each output is the header's length and each decode consumes the
source to exactly the first data byte. The format has no checksum, so those two checks cannot catch a wrong
literal byte. `PACT.PRG` and `PACT2.PRG` are themselves wrapped twice in the menu's "ZUUL & HIDDEN PACKER V1.2"
stub (ByteKiller-style, `py/bk_stub.py`); `PACT3.PRG` is a Pack-Ice 2.4 self-extracting program, not unpacked.

The unpacked `1.1` is the program in RAM at load base `$800` (text `$800..$261a2`, data to `$2dd2e`). At the
program's first instruction (`u 800` after the menu's F1, `scratchpad/midwinter/entry800.snap`) it differs from
the file in 1300 bytes, all in 14 runs, and every run is a crack patch made by the loader, not depack damage:
`bsr` calls replaced by `nop nop` (`$ffb8`, `$1001a`, `$1003a`), `beq` turned into `bra` (`$10302`, `$10346`),
`jsr $11c7e` into a `bra` (`$c10`), call displacements retargeted (`$ffc6`, `$10028`, `$10050`, `$102f0`), a
routine head replaced by `jmp $500` into a resident loader in low RAM (`$10cd2`), and two rewritten blocks
(`$10e1d..$111ce`, 946 bytes, and `$11c7e..$11e06`, 393 bytes; inferred to be the disk protection and loader).
So the depacker's literals are confirmed everywhere outside those runs.

The program is hand-written assembly: no `LINK A6` frame in the text, 1099 `rts`, 780 `jsr abs.l`, 404 `muls`
and 129 `divs`. The trace and callcap route applies, not a decompile.

## Driving it

`drive.txt` runs from a 20M-step cold-boot snapshot to the first-person ski view; two runs give byte-identical
snapshots at all six milestones (title, options, team, character, decisions, ski):

```
cd M68000
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 20000000 snapshot scratchpad/midwinter/cold20.snap --disk-a scratchpad/midwinter/zuul067.st
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/midwinter/cold20.snap repl --disk-a scratchpad/midwinter/zuul067.st < reversing/midwinter/drive.txt
```

Three emulator gaps had to be worked around, all in input or timing, none in the game:

| where | what the code does | why it stalls here | bypass in `drive.txt` |
|---|---|---|---|
| boot-sector ticker `$172c` | `cmpi.b #$39,$fc02.w / bne $1704`: polls the ACIA data register for space | `MMU.fs` pops the FIFO on a read and returns 0 when empty, and TOS's ISR takes the byte first (the Black Tiger gap) | `w 1732 4e714dfa`: the `bne` becomes a `nop` |
| menu key loop `$a4e4` | reads `$fc02` twice per pass (`cmpi.b #$3d` then `cmpi.b #$3b`) for F1..F3 | the second read always sees 0 after the first popped the byte | the loop is replaced by `move.b #$3b,$a404.l / bra $a500` (F1 stored as the choice) |
| menu VBL `$a5e0` | a fullscreen border-removal routine, mostly timed `nop`s | the emulator raises the VBL every 12,000 instructions, not every 160,256 cycles; the handler runs about 36,000 instructions, so the next VBL is pending when it returns and the main loop never runs (55 handler runs and 0 main-loop hits in 2M steps) | `w a5e0 4e730001`: the handler is an `rte` (no fullscreen menu art) |

A fourth gap affects every mouse-driven game: the REPL's `mouse down l` sends no packet in relative mouse mode,
it only updates the 6301's internal button state. A real IKBD sends a relative packet when a button changes,
and Midwinter reads buttons only from the packet header (`$664a`). `drive.txt` sends raw packets instead:
`kbd fa 00 00` (left down) and `kbd f8 00 00` (release).

## Architecture

`architecture.md` holds the program skeleton with its census counts:

- the vectors and the IKBD ISR (`$6400`; pointer x/y at `$24fa2`/`$24fa6`, buttons `$24fba`);
- the VBL fan-out and the pointer mode `$62b8`;
- the jmp-linked screen graph: each screen sets an icon list at `84(A6)` and waits in `$bcfe`; `$bcaa` hit-tests 32 x 32
  icons, and a longword action table either `jsr`s and redraws or `jmp`s to the next screen;
- the two real frame loops: the map (`$1546`) and the 3D travel frame `$14e00`, with its landscape render `$18304`,
  draw list `$19ce2` and goggle mask `$1bbe6`;
- the cracked loader: file number in `348(A6)`, `jmp $500` into a resident FAT12 loader plus the LSD depacker.

The character screen's watches and running figure are not buttons: its six icons at y 168 are map, decisions,
team, previous, next and S.O.S, and Decisions' ski icon (x 128) starts the first-person view.

## Milestones

| screenshot | screen |
|---|---|
| `title.png` | title, "Insert graphics disk / Press any key when ready" (after F1 in the menu) |
| `options.png` | Game Options (mouse, joystick, mortars, bombers, ...) and PLAY |
| `team.png` | The Team, Capt Stark only at the start |
| `stark.png` | character screen: biography, qualities and skills, icon bar |
| `map.png` | the full island map with its legend (huts, bunkers, cable cars, heat mines, ...) |
| `decisions.png` | Decisions: the travel and action choices |
| `ski.png` | first-person skiing through the goggles: terrain, a building, the HUD (speed, compass, map) |
| `ski_crash.png` | 40M steps later: a hit (inferred: by the enemy plane seen approaching in the frames before), after which the game returns to Decisions with Stark's clock moved from 06:00 to 06:08 |

## Files

| file | what |
|---|---|
| `architecture.md` | vectors, VBL, screen graph, map and 3D frame loops, the cracked loader |
| `midwinter.sym` | routine names (`tools/merge_sym.py` format) |
| `drive.txt` | cold boot (20M) to the ski view, REPL script with the labelled pokes above |
| `repl/` | the REPL scripts behind `architecture.md`'s counts |
| `tables/` | icon/action tables, indirect jump sites, static file-load calls |
| `py/vectors.py` | lists the non-TOS vectors in a snapshot |
| `py/bk_stub.py` | unpacks the menu's ByteKiller-style self-extracting stub |
| `*.png` | milestone screenshots |

`tools/lsd_depack.py` (the game-file depacker) is in the shared tools.

## Not exercised yet

The 3D renderer and terrain, any vehicle other than skis, the enemy AI, recruitment, the other game on the disk,
and anything after the first bomber attack.
