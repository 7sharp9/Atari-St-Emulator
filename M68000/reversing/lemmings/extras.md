# Lemmings: codes, levels, ending, crack

Not lemming behaviour. Found by a parallel agent sweep; its evidence files are in
`scratchpad/lemmings/interesting/` (gitignored; `full.asm` is the `$400`-`$27000` listing, `runrepl.sh`
the runner). Labels: **proven** = driven in the emulator with a count, **read** = from the listing or
data, **guess**. Spot-checked by the parent session: `py/codes.py` reproduces the canonical codes below,
and `py/levels.py` agrees with the level 1 record read from RAM (10 diggers, 10 lemmings).

## Where the code is

The game code starts at `$400`, not `$2000`: the main loop, menus, the end sequence and the protection
debris sit below `$2000`, so a `$2000`-`$27000` listing misses them (the skill-click path at `$1540`-`$1f24`
is there). A snapshot taken at the cracktro's `$a61c` (`lvl1_a.snap`) has `A5 = $c822`, not the game's
`$272d4`: a `callcap` of a game routine needs `A5 = 272d4` set first.

## Access codes (`py/codes.py`)

Generator `$3d40` (10 letters to `$d802`), checker `$404c`. Inputs: level index `n` (`50(A5)`, 0..119, plus
`$a0` for two-player), a nibble `f` (`27(A5)`, 8 at every game-issued code, so read as vestigial) and the
percent rescued `p` (`54(A5)`, from `$2f7e`; read). The 10-byte key `AJHLDHBBCJ` is the first 10 bytes of the
unpacked `LEVELDAT`.

- Proven: 260 of 260 `callcap $3d40` cases (all 140 indices, 80 random `(n,f,p)`, 20 two-player runs) match
  `gen()`. Typed through the game's own entry screen: 18 of 18 valid codes accepted with the right `n` and `f`;
  with `n` pre-poked to 77 so a rejection is visible, 11 of 11 loosely valid strings gave exactly the `n`, `f`
  that `check()` predicts.
- The checker verifies only `c9` (a sum), the low nibbles of `c7`/`c8` and the data bits of `c0`..`c6`; the
  key's own bits, bit 4 of each letter and the 7 `p` bits are ignored. So many strings are valid per level
  (about 10.5 million at `f = 8`; about 1 in 6,525 random strings is accepted somewhere), and `p = 0` works. A code
  carries a level index, not the rating.
- Canonical codes at `f = 8`, `p = 0`: n=0 `BAJHLDJBCN`, n=30 `JBANLMFPDX`, n=60 `MFKBAJLNFU`, n=90
  `NHMFJFALHX`, n=119 `FINLLFKIJS`. Enter a code, then click 1 PLAYER.

## Levels (`py/levels.py`, `py/levels.txt`, `py/ice.py`)

`LEVELnnn` are headerless Pack-Ice (the game's depacker `$49e4`, ported in `ice.py`, checksum verified for
all 25), each four 2048-byte levels. `ODDTABLE` is 80 records of 56 bytes (24 header, 32 name). The slot
table is 180 words in `LEVELDAT` at `$290fc`, indexed by `n` (+160 for two-player). Slot `s` loads
`LEVEL((s-1)>>3)`, level `((s-1)>>1)&3`; an odd `s-1` takes its 12 parameter words and name from
`ODDTABLE[(s-1)>>1]`. `levels.txt` is the decoded catalogue (rate, count, save, time, skill counts, name).

- 140 levels use 100 maps; 40 single-player levels re-skin another's terrain (Fun 1 "Just dig!" = Tricky 15;
  "We all fall down" is one map used four times). Proven by the game's own struct at `$de70` for 9 of 9 codes
  tried, and byte-identical terrain (1992 of 1992) for the shared pairs.
- 40 of 80 `ODDTABLE` records are "This is a non-used duplicate" placeholders (read).
- `n` in 120..159 maps to slot 145 and shows rating "Blue" read past the end of the 4-entry table; `n` 160..179
  are the 20 two-player maps; slots from 180 on are zero. The end-of-game test at `$1184` is `cmp.w #$78` (equality), so
  a typed code with `n` above 119 plays on past the last one-player level. Proven by winning through the edge from
  the menu (`py/overrun.py`; win forced by zeroing `56(A5)`, the required percent, then ESC): code `n = 159` loads
  "Level 10 Rendezvous at the Mountain" (80 lemmings, 75%), the win moves `50(A5)` to `$a0` and the next briefing is
  "There can be only one", a two-player map that plays in one-player mode (one hatch, lemmings walking); the win
  from `n = 179` makes `$b4` (180) and the next briefing shows the previous level's record again ("There can be
  only one", the rating line garbled) and the level starts as a replay of it with a corrupt palette and panel. A level that
  loads no record is not a new level.

## Ending

Poke `20(A3)` (`$26c18`) = 100, `50(A5)` = 119, `52(A5)` = 100, press ESC: "Congratulations! Everbody here at
DMA Design salutes you as a MASTER Lemmings player..." (typo on screen), then `ENDPIC` (`endpic.png`, the
DMA team photo; headerless Ice 32000-byte screen, as are `DMALOGO.IMG` and `PSYGLOGO.IMG`). `ENDSAMPL` is a
Timer-A player writing the three YM volume registers from a 256-entry table (75,140 signed bytes at
`$65a44`); the ISR ran 642 times in 120,000 steps, the 9.6 kHz rate is read from the timer constants, and
that it is applause is a guess.

## Crack and protection traces (read)

- Cracktro text: cracked and filed by Milamber of the BBC, thanks to E.G.B. "for 1 slightly lame
  encryption routine", intro by Andy the Arfling. `"Crack + Files by Milamber!"` at `$e812` sits in front of
  the cracker's replacement file loader (`$e810`, reads the FAT directly through the FDC/DMA).
- Protection debris at entry (`$400`): six NOPs over a removed call at `$4a2`, `bra $d94` skipping 2,100
  high-entropy bytes (`$540`-`$d94`, XOR with 'BISC' does not decrypt it), dead anti-debug code at `$4c8`
  (illegal-instruction vector, `movec`, trace vector). Three `bsr $e80` calls with ASCII tags are now `rts`.
  Only one entry path was found; "unreachable" is not proven.
- The boot sector is a stock resident anti-virus (hooks `hdv_rwabs`). `LEMMINGS.PRG` is Pack-Fire!.
- The game repurposes vector slots `$50`/`$54` as the pointer and size of a 400,000-byte file cache at `$80000`
  (proven in `lvl1_a.snap`).

## Keys and engine

Four programs run in turn (cracktro `$a000`, the loader at `$70000`, an intro program whose own VBL ISR is `$2ad6`,
the game), each with its own input code. The game's ACIA ISR (vector `$18`, installed at `$db4`, helper `$22a8`)
latches only the last scancode, make or break, in `7(A5)`; there is no key-state table and no key buffer, so a
combination or a typed sequence cannot be detected. A whole-listing scan of every reader of that byte (`$1724`,
`$1f38`, `$1f5a`, `$21d8`, `$24e2`) and a single-key sweep of all codes `$01`-`$7f` in level 1, a two-player level, the
menu and the briefing found no cheat, debug, level-skip or add-skills key (proven; combinations are not testable
by construction). What the keys do:

- In a level (`$1f54`, once per main-loop pass): Tab toggles 50/60 Hz (`$2010`, bit 1 of `$ff820a`); Z and X cycle the
  selected skill (`$1f54`, the word the icon click writes); ESC and F9 are the same branch, `$1ffe`, which zeroes the
  clock (`78`/`80`/`82(A5)`) and sets time-up `9(A5) = $ff`, so the level ends at the result screen (not an abort);
  F9 is undocumented in the game (driven, identical hit counts and first-hit steps for both).
- Two-player mode only (`tst.b 16(A5)`): N and M cycle player 2's skill, F1 to F8 (`$3b`-`$42`, `$1724`) set it directly
  (scancode `- $3b`), P toggles pause (`25(A5)`; one-player pause is the panel icon only), Q/A/I/O (`$10`/`$1e`/`$17`/`$18`)
  move player 2's pointer, Space is its button, joystick 1 moves it too, and the right mouse button is player 2's
  click (driven, `watch $26ee4`).
- Menu: only the five icons are hotspots (1 PLAYER, 2 PLAYER, code entry, music/FX, the rating arrows at `$126`);
  25 probe points, gaps and the right button hit nothing. Code entry takes A-Z, Backspace, Del, Left and Right,
  ends at the tenth letter or on ESC (which gives "Incorrect Code"); digits, F-keys, Return, Undo and Help are ignored.
- Mouse: the right button scrolls the level at 4 times the speed (`$c0` against `$30` in 120,000 steps); on the result
  screen left click or Space retries and the right button returns to the menu; the nuke icon needs a double click
  within 5 loop ticks (`$1960`); the panel's `$c0`-`$cf` is decorative.
- Space during the intro animation skips it (the intro's `cmpi.b #$39,$fffffc02` at `$2b02`, handler `$2b9a`, which
  copies the loader to `$70000`; driven: menu setup reached at step 2.99M against 35.95M with no key). Any `kbd` in that stage takes the
  TOS ACIA ISR through a garbage vector into the loader and looks like a hang; `w 3f0 4e734e73` then `w 118 000003f0`
  makes it a harmless RTE.

Timer B palette splits: `$285c` (menu, one split at line 182) and `$28ac` (briefing, a 16-colour palette every
14 lines). The credits and disclaimer scroller (`$d888`-`$dc94`, shown by `$751a`) is ordinary menu text. Code
`$2c04` of the intro names `IntroPart2`, absent from the disk: the crack's replacement loader runs instead (read).

## Leftovers (read unless marked)

- `BasicFX`/`FullFX` loaders (`$48de`, `$48fc`, names at `$dd84`/`$dd8c`) have no caller and no file: dead. The sound
  command builder `$4928` is uncalled too. Effects play from the in-code table at `$1539e` (23 words, index `104(A5)`,
  always an immediate); 14 of the 23 ids are never requested (`0 4 $a $c $10 $11 $12 $14 $16` are).
- Music: 21 tunes, all reachable. The selector `$4864` picks tune `n mod 17` unless the level's special-graphics word
  (`$de8c`) is 1..4, which picks `awesome`, `menace`, `beast2` or `beast1`: Fun 22, Tricky 14, Taxing 15 and Mayhem 22,
  the levels named for them. `mountain` plays at `n = 0` and 119.
- The code-display placeholder `DavidJones` (`$d802`) is overwritten by `$3d40` before it can show.
- Uncalled routines: `$2dea`, `$72e0`, `$2c9c`, `$47d0`, the IKBD joystick-mode sender `$2126` (and `$2116`, reached only
  through a data word). The depacker `$49e4` warm-resets (`jmp $fc0020`) when its checksum fails, so a patched data
  file reboots unless the checksum is fixed.
- Disk audit: 809 used clusters, all owned by a file; free clusters zero; no deleted entries; both FATs identical.
  Every file is named by the loaders (`LEVEL000`-`024`, `GROUND1`-`5`, `OBJECTS1`-`5`, `SPECIAL0`-`3` for special
  graphics 1 to 4, `ODDTABLE`, `LEVELDAT`, 21 music files, `ENDPIC`, `ENDSAMPL`). `MAIN` embeds four 320x200 IFF
  backdrops and DMA's loader labels. The full cracktro scroller also greets many groups and mentions a trainer that is
  not on this disk.

## Not done

A table of all 140 canonical codes, every level's terrain, the result-screen feedback thresholds, the
pixel content of `GROUND`/`OBJECTS` (unused pieces), `INTROPAR`, the `LEVELDAT` 1424-byte blocks.
