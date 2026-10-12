# PowerMonger ST: the system services (sound, save disks, serial link setup)

The code at `$1adcc..$1c3e6` that is neither game logic nor drawing: the sample player, the save-disk routines with their message strings, and the serial link's interrupt setup. Addresses are the runtime addresses of the developers' own build
(`powermonger_orig.sym`, names cut to eight characters). Labels: **proven** has a script and a match count, **live** an emulator command, **code read** a disassembly read, **inferred** a reading the code supports but nothing ran.
The scripts are in `py/sound/` (data under `scratchpad/pm140/agents/sound/`); the palette and fade routines of the same address range are in `graphics.md` "Backdrop pieces, palettes and fades", the event table that feeds the player in `strategy.md` `$127e6`.

## The sound driver is a sample player

`$1af32..$1ba70` is not a tone or music engine. "Ech" is French *échantillon* (sample): a Timer A interrupt writes one PSG volume triple per tick, using registers 8, 9 and 10 as a three-channel DAC, and a per-frame sequencer chains
`(sample, rate)` pairs. The tone and noise generators are switched off (`InitPsg` `$1aeb0` zeroes registers 0..6 and 8..10 and sets register 7 to `(reg7 & $c0) | $3f`). The driver's data sits just before its code: `ptr_ech` `$1ada6` and `nom1` `$1adaa`, which holds the string `B_FLOOD.ECH` (read from RAM; nothing references it, so it is a leftover of a file-loading version of the driver: inferred; `strategy.md` "Hidden features audit").

**The bank** at `$5879a` is filled by the game's loader (which resource is not identified: startup zeroes `$5879a..$6f30c` at `$10ba`, then `$11c0` calls `$df52(9)` just before `NewEcha`; resource 9 is inferred). Word 0 is the number of samples (58), word 1 the number of sequences (56), then longs `tab[i]` from `+4`: `tab[0..55]` are
sequence offsets, `tab[56]` is skipped (the end marker), `tab[57..]` are sample offsets. `_NewEcha` `$1b83c` builds `$2c9a0[i] = bank + tab[i]` (56 longs) and for each sample a 12-byte record at `$2cba6 + 12j`, `{start, start, tab[next] − tab[this]}`; the length is never used for playback (samples are zero-terminated; the last has no end offset).
**Proven: 56/56 sequence pointers and 58/58 sample records equal NewEcha's tables (`py/sound/bank.py`); 57/57 samples have their first zero byte at length − 1 (`dac_table.py`).**

**A sequence** is byte pairs `(sample id, Timer A data)` ended by `$ff`; the rate is 614400 / data (prescale ÷4: data 167 is about 3.7 kHz). Sequence 0 has 232 pairs, sequence 1 1364; many sequences are rests (sample 5 at rate 245 or 255). A call with id n plays sequence n − 1 (ids 0 and 1 both play sequence 0), so the long, music-like
sequences (0, 1, 4, 5, 24, 25, 36, 54) are started by the same call as the effects (`bank_report.txt`).

**A sample** is signed 8-bit PCM. The Timer A routine `Joue` `$1af32` takes `b = *stream++` (the stream pointer is the immediate operand at `$1af3a`, self-modifying); `b = 0` ends the stream (`FinJoue` `$1af6c`: `TACR = 0`, busy `$2c993 = 0`); otherwise `tabconv` `$1af86` (255 entries of 8 bytes) is indexed by `8b`
and two `movep`s write the entry to `$ff8800..` (registers 8, 9, 10). **Proven: 300/300 consecutive interrupt passes** from `pm123/win/m1_s0` (D1 and D0 equal the table entry of the byte at `ptr − 1`; `py/sound/gate_timera.py`), and the PSG registers 8, 9, 10 read back equal the entry's volumes (11, 11, 10).

That the table is a three-channel
volume sum is **inferred** (`dac_table.py`: all 255 entries select registers 8, 9, 10; amplitude falls with the signed byte, Spearman ρ = −0.952, 182 of 253 adjacent steps non-increasing, 195 distinct triples; byte `$ff` indexes 1841 times past the table into code, read as a harmless PSG no-op, inferred).

**The sequencer** `EchInter` `$1b77e` runs once a VBL (called from the VBL handler `$1270` at `$1294`, only when `$2de66 != 0`):

```
if active and not busy:
    (s, r) = seq[2*idx], seq[2*idx + 1]
    if s == $ff: if loop: idx = 0; (s, r) = seq[0..1] else: active = 0; return
    idx++;  $2c998 = s;  $2c99a = r;  PlayEch      // start sample s at rate r: $1af3a = start, TACR = 0, TADR = r, vector $1af32, TACR = 1, busy $2c993 = $ff
```

**Proven: 328/328 `callcap` states against the Python model** (`gate_echinter.py`: all 56 sequences, idx in {0, n − 1, n}, loop 0 and 1, plus the inactive and busy cases). Live from `m1_s0` over 1.5M steps: 125 VBL hits, 126 `EchInter`, 7363 interrupt passes, 12 `PlayEch`, 12 `FinJoue` (the VBL period is 12000 steps).

**The emulator fires Timer A about 59 to 64 times a frame whatever `TADR` says** (`Program.fs` `timerAPeriod`), so the samples play at the wrong speed here; real pitch and tempo cannot be measured on this emulator.

**The API.**

- `_InitEch` `$1b7fc` (startup `$1108`): clears `$2c993/4/6`, calls `$1adcc`, which saves the Timer A vector, installs `Joue`, sets `TADR = $2c99a`, `TACR = 1`.
- `_ClrEcha` `$1b81c` (exit `$120e`): `$2de66 = 0`; `_ClrEch` `$1ae4c` stops the stream and restores the vector.
- `_JoueEch(seq, flags)` `$1b978`: stops the current sequence; if `flags & $80`: idx = 0, `$2cba2 = seq`, `$2c994 = (flags & $20 != 0)` the loop flag, `$2c992 = 1`.
- `_Sample(n, flags)` `$1b9d0`: `flags & $10` only asks (1 if a sequence is active, else −1); otherwise if `n < $2c99c` it runs `JoueEch($2c9a0[n], flags)` and returns 2.
- `_Noise` `$1ba3e` / `_Effect` `$1ba42`: `Sample(max(D0 − 1, 0), $80)`; **the second argument of every caller is ignored**. `$1ba62..$1ba70` are the stripped debug stubs (`_debug_m`, `_setup_d`, `_reset_d` a bare `rts` each, `_debug_s` `move.w #0,D2` / `rts`, the data word `_dbm` between them; `strategy.md` "Original names").

**Call sites of `$1ba3e` (26).**

- Exit `$1206` (id 0).
- `$25f8`, `$2612`, `$286c`, `$2852` (id 0, second argument `$2002` or `$58054 ^ 5`); `$2852` and `$286c` are the end of the group dissolve `$2776`.
- `$26ea` (id `$2c`), `$26fc` (`$3f`), `$271c` (`$2d`), `$76e6` (`$30`).
- `$126ea` (id 0); `$12706` (`($57fd0 >> 1) + 1`, the season sound).
- `_stop_so` `$12726` (ids 0 with second arguments `$81 $82 $84 $88 $2001..$2008`, so it silences everything: sequence 0 with flag `$80`, effect inferred).
- `$128d2` (id `6(A1)`, the event dispatcher).
- The four season and weather sounds of `$1abaa` (`$1acc8`, `$1acec`, `$1ad06`, `$1ad20`).

**Game event to sound, live** (`pm123/win/m1_atk`). The draw preparers raise the pending count of an event (`strategy.md` `$127e6`) and `$127e6` picks the two best. `bpc $128d2` at step 1115548 shows `A1 = $129d0` (entry 14, id 14) and `D0 = $e` at `$1ba42`; `$1b9d0` runs six steps later with 13, setting `$2c992 = 1` with sequence 13 (`$5a09c`, 104 pairs, samples 5, 20, 21); 1843 steps later `EchInter` reaches `PlayEch` with sample 21 at rate 103. Over 20M steps from `m1_atk`: `$1ba3e`, `$1b9d0`, `$1b978` and `$128d2` 2 hits each, `EchInter` 199, `$127e6` 82.

**The event table** `$1290c`: entry 0 is a sentinel, then entries of 14 bytes (pending count, cooldown long 50 ticks, id = index 1..59, channel or −1, priority 99/9/7, flags `$a0`); ids 57..59 have no sequence (`events.txt`).

**Start and stop.** `_start_s` `$126d6` (called at the end of the land build, `$13c60`) plays `$1ba3e(0)` then `$1ba3e(($57fd0 >> 1) + 1)` and clears `$58058..$58077`, `$58054 := 1` (live, natural). `_stop_so` `$12726` (callers `$6eba`, `$774c`, `$d2d2`, `$13ce8`, `$13d1a`) makes 8 `$1ba3e` calls and clears the event table (live: 8 calls, every one `$1b9d0(0, $80)`). `callcap $12726` never returns because the driver spins on an interrupt-cleared flag at `$1ae46`; use the natural hit.

## The file layer: FAT12 reader, FDC driver, depacker

The game does no GEMDOS, BIOS or XBIOS disk call. It carries its own FAT12 reader and a direct WD1772 DMA driver, so its files are read with the game's own code on any disk image (`py/disk/`).

- **`diskio` `$d9fc`** (code read; its reads are live in every load below). D0 bit 0 = drive, D0's high word = sectors per track (forced to 9..11, 10 when 0), D1 = logical sector, D2 = count, D3 low byte = 0 read / 1 write / 2 format; bit 15 of D3 (kept at `-8(A6)`, tested at `$dde8`) adds a busy-wait of 800,000 `subq.l`/`bne` loops (`$dee2`, about 1.8 s at 8 MHz) at the end of the transfer, before `$de4a` deselects the drive. Only the save-slot load `$1bd70` (D3 = `$8000`) and save `$1bdfe` (`$8001`) set it; the other callers (`$d638..$d7b0`, `$1baaa`, `$1bac6`, `$1bd5e`, `$1bea0`) pass 0, 1 or 2 (whole-image raw scan of `bsr`/`jsr` to `$d9fc`, code read), A0 = buffer. It programs the FDC through the DMA registers `$8604..$860d`, polls MFP `$fa01` bit 5 for completion, retries three times with recalibrate and seek, and a `callcap` of `$1bd70` or `$1bdfe` ends in "Loop detected at PC=$1876", the frame wait `$1870` (`tst.w $2df8c / beq`, the flag is set by the VBL handler, which `callcap` masks; the caller of that wait was not identified).
- **`fileio` `$d574`** reads `A:\DIR\NAME.EXT` into A1 (code read; its reads are the live loads below). `$d594` takes the drive letter, `$d5b6` upper-cases and pads to 8.3, `$d62a` reads the boot sector into the geometry variables `$d7e4..$d7ef` (root entries, sectors per FAT, sectors per track, double-sided flag), `$d66e` scans the root directory and descends into `DATA`, `$d6f4` walks the 12-bit FAT chain (`$d770`) and reads runs of contiguous clusters in one `diskio` call. D0 = 0 on success, `-33` file not found, `-1` read error.
- **Resource table `$e0c4`**, 16 entries of 12 bytes: name pointer, destination, last file length (`$def0` returns it from the constant length table `$df12`, which equals the real file sizes; `$df52` stores it at `+8`). `$e084` holds the unpacked sizes, `$e040` the cache slots (`$e03e` enables caching into the pool at `$2c1ba`). `$df52(i)` copies from the cache if the slot is set; otherwise `$d4d2` loads the file at its destination (resource 0's destination is computed, `($2dfa0 + $80) & ~$7f = $2e000`; a missing file restores the palette from `$1afe`, puts up `$1bec8` "PLEASE INSERT THE POWERMONGER DISK" and retries, code read; `$d4d2` also stores resource 0's destination in `[$ff9e]`, the texture pattern pointer, and holds the busy flag `$58014 = 1` while it loads), `$e2b8` unpacks it in place when the file length differs from `$e084`, and the result is copied into the cache.

| i | file | destination | unpacked size |
|---|---|---|---|
| 0 | TEXTURES | `$2e000` | 12928 |
| 1 | QAZ | `$78000` | 32000 |
| 2, 3, 4, 5 | SPRITE16, SPRITE8, SPRITE24, SPRITE32 | `$312a0`, `$33000`, `$37c7c`, `$3af1c` | 7520, 19580, 12960, 17280 |
| 6, 7 | CAP_SPR, BITMAP (not on the disk) | `$3f29c`, `$3f29e` | `$1800`, `$1000` |
| 8 | CAPGRAPH | `$1c700` | 32000 |
| 9 | FX | `$5879a` | 93034 |
| 10, 11 | MAP, MAPDATA | `$3f364` (both) | 97280, 65268 |
| 12, 13, 14, 15 | END_PIC1, END, LOSE, WIN | 0, `$3f768`, 0, `$24400` | 32000, 73310, 32000, 32000 |

All names are `DATA\<NAME>.DAT`. Every on-disk file is crunched, with the unpacked size in its trailer equal to `$e084` (14 of 14; `SPRITE40.DAT` is a plain developer file nothing loads). END (the end-screen resource) loads over `$3f768`, the save buffer. The table's destination 0 for END_PIC1 and LOSE means the caller supplies the screen buffer (not traced).

**`decrunch` `$e2b8`** (A1 = buffer, D0 = packed length) is a header-less backward LZ depacker that works in place: the stream occupies A1..A1+D0, the last three longs are `[bit-buffer seed][checksum seed][unpacked size]`, and output is written downward from A1 + size. Bits are taken LSB first from the longword buffer; each refill reads the next lower long and shifts a sentinel 1 in at the top (so a refill supplies 32 data bits and the seed 0..31). D5 starts as `checksum ^ seed` and is XORed with every longword read; it must be 0 at the end, otherwise the routine spins at `$e352` (a corrupt file hangs, it does not report). Tokens, multi-bit fields MSB first:

| bits | meaning |
|---|---|
| `00` + 3-bit n | literal run of n + 1 bytes (8 bits each) |
| `01` + 8-bit off | copy 2 bytes from `A2 + off` |
| `100` + 9-bit off | copy 3 |
| `101` + 10-bit off | copy 4 |
| `110` + 8-bit v + 12-bit off | copy v + 1 |
| `111` + 8-bit v | literal run of v + 9 bytes |

A copy is `repeat { A2 -= 1; (A2) = (A2 + off) }`, so overlapping copies repeat a pattern; the loop ends when A2 reaches A1. This is the game's own packer, not the "Ice!" packer of the crack (README "Bugs 2 and 3").

**Gates** (`py/disk/`). `gate_decrunch.py` **48/48** (the real routine through `callcap` on 40 synthetic streams from the model's own encoder and 8 real files, byte-identical output plus D5 = 0 and A2 = A1; the checksum-failure spin is not tested). `gate_load.py` **6/6** (`callcap $df52` for resources 0, 2, 3, 4, 5, 9 from `m1_win` with the game disk mounted: the file is read by the game's FAT12 reader and unpacked, and RAM at the destination equals the model's decode of the file extracted from the image, with the `+8` length and cache slot updated). `decrunch_model.py` alone decodes all 14 files with checksum 0.

**Live.** Play Random Land from `m1_win` calls `$df52` twice (indices 1 and 8) and reads no disk (`$d574`, `$d9fc`, `$e2b8` 0 hits in 70M steps): both are in the cache.

## The save-disk code

A save disk is formatted by the game itself. FORMAT, SAVE, LOAD and the "SAVE GAME DOES NOT EXIST" and OVERWRITE? requesters are live from natural FILE-panel drives (see "Evidence" below). A saved game is a slot of 198 sectors (101,376 bytes) read from or written to RAM `$3f768..$58368`; the conquest map is only its first 195 bytes.

- `_format_` `$1ba72` is the file-menu code `$77` of `strategy.md` (its one caller is `$77b8`). It asks for the save disk (`$1bf0a`; CANCEL ends in "FORMAT HAS BEEN CANCELLED", `$1beec`), then probes the inserted disk with `$1bd38`: only when `DATA\SPRITE8.DAT` opens, that is when the game disk is in the drive, does it ask "ARE YOU SURE YOU WANT TO FORMAT THE POWERMONGER DISK?" (`$1bec2`). It formats 800 sectors (`diskio $d9fc`, D3 = 2) with the visible screen `*$2df7c` as the track buffer, and on a failure asks "IS IT WRITE PROTECTED ?" (`$1bf04`: OK retries, CANCEL cancels). It then writes the ID sector `sgmsg` `$1bb0e` (D3 = 1) and repaints the screen from the HUD master `*$e0d4` (`$12ce0`). It sets the pointer animation `$2c1be = $a0` on entry and 0 on exit, and turns the motor off (`$1bf2e`). The stub `$1befe` ("ERROR FORMATTING DISK") has no caller (whole-image scan for direct branches; the only literal hits are odd-aligned data). Live on a zeroed 409,600-byte disk (`py/saveload/format_proof.sh`): FORMAT (170,117) runs `$7740`, `$1ba72`, `$1bf0e` and `$cce2` once each; OK on the save-disk requester runs `$1bd38` once (its three reads of track 0 side 1 find nothing on a one-sided disk, so it asks no ARE YOU SURE), then the FDC takes 80 Write Track commands, 10 sectors each with none skipped, and one sector write of `$1bb0e` to sector 0; `$d9fc` 13 hits. The land repaints and the panel closes. The write-protect and ARE YOU SURE branches are still code read (the emulator has no write-protect tab).
- **Sector 0** is the 512-byte buffer `$1bb0e`: the text "POWERMONGER ST SAVED GAME DISC ... LAST ST PRODUCT FROM BULLFROG!", then at `+$ec` 26 slot-used flags (`save_use` `$1bbfa` is that tail, not a separate table), zero padding to `$1bd0e`. `_is_it_s` `$1bd52` reads sector 0 (D1 = 0, D2 = 1, D3 = 0) into the buffer and compares its first long with `'POWE'`
  (live with the game disk mounted: the buffer becomes the boot sector `60 38 ..` and the compare fails).
- `_dda_loa` `$1bd70` loads a slot. The slot letter is byte `$e296` (the fourth character of the name `A:\WARx.GAM` at `$e290`; nothing opens that name, it is vestigial). The only writer of `$e296` is `$75ce`, `move.b D0,$e296` after `+ 'A'` of the slot-row index that the FILE panel's row handler `$75c4` finds (whole-image grep). Slot = letter − 'A'. It reads 198 sectors (`moveq #58,D2 / neg.b D2` = 198) from sector `slot × 198 + 1` into `$3f768` (D3 = `$8000`), that is RAM `$3f768..$58368`: not only the 195 conquest bytes but the whole region above them. That overlaps resource 13's buffer, the terrain `$438ee`, the group table `$51538`, the object array `$51b66` and the `$580a0..$58368` link/save block, and a LOAD replaces all of them: the loaded land is the saved one (proven: a SAVE then LOAD with 30M steps of play between leaves the range equal to the saved image in 101,376 of 101,376 bytes, and a slot built from another land's RAM replaces the minimap and groups; `py/saveload/roundtrip.sh`, `load_into.sh`). The clock `$2df72` lies outside the range and is neither saved nor reset: it runs on across the load (live: 441 at the save, 628 before the load, 668 after it). The groups' camp stamps (`256(A1)` of each group, written from the clock at `$3720`) are inside the range and are restored, so a loaded group in state 6 makes no camp decision `$65b4` until the destination's clock reaches its stamp + 20 (the signed compare at `$65a0`, `strategy.md`). Proven: k80's block loaded into rand1 at clock 441 gives 0 decisions in 100M steps, 596 with the clock poked to the source's after the load; the only eligible group's stamp 2088 predicts the first decision at clock 2108, about 279.2M steps later, and it comes at clock 2108 after 276,745,802 steps (`py/saveload/camp_stamps.py`). An unused slot shows "SAVE GAME DOES NOT EXIST". The disk carries no checksum: the only checks are the `'POWE'` header and the slot flag.
- `_dda_sav` `$1bdfe` saves: the overwrite prompt `$1bed4` if the flag is set, 198 sectors with D3 = `$8001`, sets the flag, rewrites sector 0. Callers `$e29c` (load) and `$e288` (save). Live on a disk the game formatted itself (`py/saveload/format_proof.sh`): SAVE to slot A, then a second SAVE to slot A runs `$1bdfe` and `$1bed4` once each and shows THIS SAVE GAME ALREADY EXISTS / OVERWRITE?; OK saves again, and a LOAD of slot A gives back the second save's block in 101,376 of 101,376 bytes (the two saves differ in 2,048 bytes, so the slot was rewritten).
- Slots A..D fit an 800-sector disk (4 × 198 + 1 = 793). The FILE panel (`$aeac`, template `$b0ad`, a data block, not code) has four slot rows A..D and shows SAVE and FORMAT only when `$14e4e == $2c` (formatter `$af06`). On screen (from `pm143/run/rand1_s1.snap`: options icon (71,138), then FILE (14,65); the options panel reopens at 128,67 once FILE has been used, FILE then at (142,92)) the panel sits at 128,67 with the slot rows at x 147, y 87/99/111/123 for A..D, LOAD at (170,81), SAVE at (170,99) and FORMAT at (170,117). After a requester has closed (FORMAT, or a SAVE that asked OVERWRITE?), the options panel opens further left and FILE is at (111,92) instead (live, rendered frames). Rows B, C and D each run `$75c4` and `$75ce` once (live, watch `$e296` written `$42`/`$43`/`$44` at `$75ce`). A click on the already-selected row reaches `$7658` but not `$75c4` (live, 0 of 3 positions on A), so it does not rewrite `$e296` (inferred: `radio_on` `$7550` runs only for an unselected `$1c` cell). The panel closes after SAVE.
- **Evidence.** `callcap` cannot run `$1bd70` or `$1bdfe` (the frame wait `$1870` needs the VBL), but a natural FILE-panel drive runs both (`py/saveload/roundtrip.sh`, `ATARI_TRACE_FDC=1`, summarised by `fdc_sectors.py`). SAVE to slot B: `$7740`, `$77a2`, `$e288`, `$1bdfe`, `$1bd52` once each, `$d9fc` 3 times; the FDC reads sector 0, writes logical sectors 199..396 from `$3f768..$58368`, then rewrites sector 0 with the flag `$1bbfa+1 = $ff`. LOAD of slot B: `$7740`, `$12726`, `$e29c`, `$1bd70`, `$1bd52` once each, `$d9fc` twice; the FDC reads sector 0, then 199..396 into `$3f768..$58368`. Both with 0 failed sectors. LOAD of an unused slot reads only sector 0 and opens the requester through `$1bef2`.
  The save disk's geometry is 10 sectors per track on one side, 80 tracks, 800 sectors: `diskio` is called with D0 = 0, whose sectors-per-track field defaults to 10 and whose bit 3 = 0 selects one side (code read `$da04..$da74`), the same 800 sectors `_format_` writes. Sector 0 holds header text where a BPB would be ("GA", "ME" at bytes 24..27), so the emulator's `MMU.LoadDiskA` ignores it (its total-sector field does not match the file) and takes the geometry from the image size, as Hatari does (`M68000/DEVELOPING.md`, "Running a program off a disk image"). An emulator that trusted those bytes would read 9 sectors per track: track 0 sector 10 is then not found three times and LOAD ends in "ERROR READING YOUR FILE" (`$1bef8`, live before the fix). `py/saveload/mk_savedisk.py` builds a 409,600-byte save disk and can fill a slot from any `.ram`, after the SAVE button's 195-byte copy from `$3f2a0`; `py/saveload/format_proof.sh` has the game format one instead.
- `_do_req` `$1bf0e` takes a message pair in A0, turns the drive off (`_turn_mo` `$1bf2e`: PSG register 14 `|= 7`, both drives and the side deselected), calls the requester `$cce2` and returns D0. `_display` `$cce2` (also called by the Load Data Disk path `$13f1c`) takes A0 = two 30-byte lines, clears the edit flag `$d03e`, opens the dialog through `diskmess` `$cd42` (id `$10`, template `$cd82` "DISK STATUS REQUESTER", origin (6, `$43`); its hook returns A5 = the line and steps A3 by 30), pumps `$cee6` until the dialog closes, clears and flips both screen buffers, and returns D0 = `$2df6c` (OK 0, CANCEL 1, from the id-`$10` handler `$7928`). While it is open the pointer is the plain arrow (`$2c1be = 0`; `$142e` steps a non-zero `$2c1be` through `$a0..$280` every 8 ticks); on return it is set to `$a0`. The grid renders under `callcap $cd42` (`py/ui/req_panels.py`). The stubs `$1bec2..$1bf0a` are `lea msg,A0 / bra $1bf0e`:

| stub | message | text |
|---|---|---|
| `$1bec2` | `$1c16c` | ARE YOU SURE YOU WANT TO / FORMAT THE POWERMONGER DISK? |
| `$1bec8` | `$1c0fc` | PLEASE INSERT THE POWERMONGER / DISK INTO DRIVE A: |
| `$1bece`, `$1bf0a` | `$1bf3c` | PLEASE INSERT SAVE GAME DISK / IN DRIVE A: |
| `$1bed4` | `$1bf70` | THIS SAVE GAME ALREADY EXISTS / OVERWRITE? |
| `$1beda` | `$1bfa3` | DISK IN DRIVE A: IS NOT A SAVE GAME DISK |
| `$1bee0` | `$1bfdc` | SAVE HAS BEEN CANCELLED / GAME HAS NOT BEEN SAVED |
| `$1bee6` | `$1c015` | LOAD HAS BEEN CANCELLED / GAME HAS NOT BEEN LOADED |
| `$1beec` | `$1c04f` | FORMAT HAS BEEN CANCELLED / DISK HAS NOT BEEN FORMATTED |
| `$1bef2` | `$1c08a` | SAVE GAME DOES NOT EXIST |
| `$1bef8` | `$1c0a9` | ERROR READING YOUR FILE |
| `$1befe` | `$1c0c8` | ERROR FORMATTING DISK / IN DRIVE A: |
| `$1bf04` | `$1c133` | UNABLE TO WRITE TO DRIVE A: / IS IT WRITE PROTECTED ? |

`$1bd0e`/`$1bd38` (the resource probe and "is the game disk in the drive") and `DATA\SPRITE8.DAT` at `$1bafc` are in `strategy.md` "Hidden features audit".

## The serial link's setup

`_setup_s` `$1c1aa` (once at startup, `$10f6`) points the MFP vectors `$100..$13c` at stubs, most of them `rte`: `$120` flashes the border red, `$138` yellow, `$13c` blue, `$124` and `$12c` clear ISRA bits 1 and 3. It saves `$128` and `$130`, installs `my_tbe` `$1c2b6` at `$128` (clears the busy flag `$5836c`) and `my_rbf` `$1c2d6` at `$130`
(stores `UDR` at `ring[write]`, wraps at the limit `10(A0)`, advances the write index; **no overflow check**), sets the limit `$58372 = 200` and the baud `$5836e = 1200`, and calls `_set_ser` `$1c3e6`, which looks the baud up in the table `$1c464` and sets `TDDR` from `$1c47c` (UCR `$88`, RSR and TSR 1):

| baud | 19200 | 9600 | 4800 | 3600 | 2400 | 2000 | 1800 | 1200 | 600 | 300 | 200 | 150 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TDDR | 01 | 02 | 04 | 05 | 08 | 0a | 0b | 10 | 20 | 40 | 60 | 80 |

`_check_s` `$1c30a` returns `|write − read|` (`callcap` with indices 5 and 3: D0 = 2), `_clear_s` `$1c328` zeroes both indices; `_reset_s` `$1c298` only copies the two vectors into `old_tbe` and `old_rbf`, restores nothing and has no caller. The ring struct at `$58368` (read index `+0`, write `+2`, limit `+10`, data `+12`) and the link states `$1c340` and `$1c390`
are in `strategy.md` "Serial-link states".

**What the setup serves.** The hardware is one USART byte stream with no framing, protocol or error recovery below the game: a blocking write `$1c390`, a blocking read `$1c340`, a 201-byte ring. `_set_ser` does not touch the RBF/TBE enable bits (live `m1_win`: IERA = IMRA = `$3e`, TCDCR `$51`, Timer D running; presumably TOS's boot setting, not traced).

**Users.** Besides the two below, the login dialog's "Modem Message:" field writes to the port: a click on it (the cell above is `$89`, handled at `$7678`) starts the line editor `_edit_st` `$cf46` on the buffer `$58474` (at most 78 characters, shown through the window between the `$8b` and `$8c` cells), and Return sends the text plus CR through `$1c390`. This is presumably a command string for a Hayes modem (inferred). Live (`py/link/modem.repl` on `pm147/link/mp_dialog.snap`): typing `a`, `t`, Return gives the buffer "at\r" and one hit each on `$cffa`, `$d02c` and `$1c390`, which then blocks at `$1c3be` because the emulator has no USART. The same editor serves the side-name entry (`_get_nam` `$bdc2`: buffer `$582f9 + 16 * (side − 1)`, 14 characters), where Return sends nothing. Otherwise the only users are the per-tick order mirroring of slot states 6 and 8 and the connection handshake `$6eb6`, read in `strategy.md` "The link handshake `$6eb6`": probe with `'?'` (`$71fc`), swap the 712-byte setup block `$580a0..$58367` byte for byte in lockstep, compare 8-bit sum checksums, OR the "computer" flags, make the own slot state 6 and the peer's 8, and let the lower-numbered side's block overwrite the other machine's (both then rebuild the same land).

**Evidence.** Proven by `py/link/link_gate.py`: the real routine against a scripted peer (four scenarios, 715 of 715 bytes sent each, RAM equal to the model in the two merge cases). The emulator's MFP is a plain byte array (no USART): TSR bit 7 never sets, so the real `$1c390` spins at `$1c39e` until the gate pokes TSR (`w fffa2a 00010081`) and the busy flag `$5836c` per byte.

## Not exercised

Playback rate (see the Timer A note); `_format_`, `_dda_loa`, `_dda_sav`, `_do_req` and `do_text` were not run live; the loader that fills the sound bank; the event ids behind each of the 59 sound-event classes; the audible effect of `$1b9d0(0, $80)`.
