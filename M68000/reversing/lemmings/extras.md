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
- `n` in 120..159 maps to slot 145 and shows rating "Blue" read past the end of the 4-entry table; `n >= 160`
  is a two-player level, and `n = 180` loads nothing and gives an empty split-screen level (proven, screenshots
  in the evidence dir).

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

Tab toggles 50/60 Hz (`$2010`, bit 1 of `$ff820a`; proven over two presses), Z/X cycle the selected skill
(`$1f54`; the same word as the icon click), Space is the mouse button on prompts, ESC aborts the level. Two-player
mode has keyboard pointer controls in the ISR `$21a4` (read). No other cheat or debug keys; code entry is the
level select. Timer B palette splits: `$285c` (menu, one split at line 182) and `$28ac` (briefing, a 16-colour
palette every 14 lines). Credits and a disclaimer scroller are in the data (read).

## Not done

A table of all 140 canonical codes, every level's terrain, the result-screen feedback thresholds, the
`BasicFX`/`FullFX` callers.
