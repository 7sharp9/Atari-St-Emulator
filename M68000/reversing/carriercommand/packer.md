# Automation Packer V2.3r (the `LSD!` executable packer)

Carrier Command on the Zuul #45 compilation (`PACT2.PRG`) is wrapped in "AUTOMATION PACKER V2.3r",
as are the disk's other games (`PACT1.PRG`, `PACT3.PRG`, `PACT4.PRG`, `STRAID.PRG`, `FRODON.STA`).
Each is a GEMDOS PRG whose 794-byte text (`$31a`) is the depacker stub and whose data segment is
the packed program, tagged `LSD!`. Addresses below are runtime addresses with the text loaded at
`$a304` (the auto-boot run in `scratchpad/carrier/carrier_auto.st`), so the payload sits at `$a61e`.

The bitstream is the one `tools/lsd_depack.py` already decodes for other Zuul menu-disk files, and
`reversing/impossamole/secrets.md` ties `LSD!` to Automation Packer V2.2f. This document adds the
self-extracting PRG wrapper and the in-place depack that the wrapper relies on.

## Algorithm

LZ77 with fixed prefix codes and no entropy coding (no Huffman, no arithmetic coder). Read from the
stub's depack loop `$a4ce..$a61c`; transcribed in `py/autopack_depack.py`.

- **Payload header**: `LSD!`, u32 unpacked size, u32 packed length.
- **Bit reader**: the stream is consumed backwards from its end. Bits come out MSB first through
  `lsl.b`; when the byte register shifts to zero the shifted-out bit was the sentinel, so the
  next byte is loaded and `roxl.b` shifts a fresh sentinel into bit 0. One shift both returns a bit
  and tests for empty. Literal bytes come from the same backwards byte stream.
- **Tokens**: a flag bit says whether a literal run follows. Then:
  - Literal count, 1..1,038 (`$a53a`): bit 0 means one literal; otherwise tiers of 2, 2, 3 and 10
    bits with bases 1, 4, 7 and 14, where an all-ones value escapes to the next tier.
  - Match length, 2..1,033 (table at `$a594`): unary prefix `0` = 2, `10` = 3, `110` = 4 + 1 bit,
    `1110` = 6 + 2 bits, `1111` = 10 + 10 bits.
  - Offset: a length-2 match takes a flag bit, then 6 bits (0..63) or 9 bits + 64 (64..575)
    (`$a5e4`). Longer matches take a prefix into the table at `$a5d8`: `10` = 5 bits, `0` = 8 bits
    + 32, `11` = 12 bits + 288, so at most 4,383 bytes back.
  - The copy is bytewise from `A1 + offset + length`, so an overlapping match replicates a run.
- **Stop test** (`$a54e`): when the read pointer reaches the first stream byte (header + 12).

## How it depacks in place without overwriting itself

It does not depack onto its own start. Three regions matter, all relative to `tbase` (`$a304`):

| Region | Range (PACT2) |
|---|---|
| stub | `tbase .. tbase+$31a` |
| packed stream | `tbase+$31a+12 .. tbase+$31a+134,660` |
| depack destination | `tbase+$400 .. tbase+$400+323,196` |

1. **The depack writes backwards into a buffer that overlaps the stream.** The destination is
   `tbase+$400` (`$a31c`), and both pointers start at the top and move down: output from
   `dest+size` with `move.b -(A2),-(A1)`, input from the stream end. At the start the write pointer
   is 188,766 bytes above the read pointer. A match usually consumes fewer bytes than it produces and
   closes the gap (36,575 of PACT2's 39,743 matches); a literal run never does (20,737 of 20,737 widen it or
   keep it), and overall the write pointer only ever lands on stream bytes already consumed. The
   condition is that every prefix of the file compresses to no more than its own length plus the
   final gap: the bytes still unread at any moment are the encoding of the part of the file still
   to be written below the write pointer.
   - Measured (`py/autopack_depack.py --gap`; `py/infographics/gen_depack.py` for the live margin): on all
     six packed files on the disk the pointers end 218 bytes apart, `$400 - ($31a + 12)`, the destination
     start minus the stream start, and that is their closest approach. It comes after the last read, though;
     the margin that binds is the closest approach while stream bytes are still unread: 218 for PACT1, PACT4,
     STRAID and FRODON.STA, 219 for PACT2 (Carrier Command) and 220 for PACT3, each a few bytes from the end
     of the file. Lowering PACT2's destination by 219 still depacks it exactly; by 220 corrupts 5 bytes. No
     earlier point comes closer (PACT2 stays above 3,414 until its last 4,096 bytes), because none of these
     programs has an incompressible prefix. A file whose opening bytes expanded under compression
     would close the gap below zero and corrupt its own unread input. Whether the packer refuses or
     pads such a file is not known; nothing in the stub checks.
2. **Relocation runs on the depacked copy** (`$a3a4..$a3fa`). The fixup table follows the unpacked
   image at `dest + $1c + text + data + symbols`; each fixup adds the final `tbase` (from the
   basepage, not the destination address) to a long in the destination copy and clears the table
   entry as it goes (read from the stub. For PACT2 it does not fit: the unpacked PACT2 header has absflag `$ffff` and no fixup table
   follows its 323,196 bytes, and `c80.snap` holds the image at `$296` + file offset, not at `tbase`, so how
   this program reaches its final address is not traced). The basepage's text, data and bss fields are filled from the unpacked header
   (`$a3fc..$a430`).
3. **A 39-byte mover runs from screen memory** (`$a43c..$a46e`). The image must end at `tbase`,
   which is where the stub's own code is, so the stub copies the mover (`$a470..$a494`) to
   `physbase + $7f00`, just past the 32,000 visible bytes, and jumps there. The mover copies
   text + data + bss down by `$400` with an ascending `move.b (A1)+,(A3)+` (safe: destination
   below source), clears the `$41d` bytes above the moved image (the stale top `$400` and 29 more),
   puts the basepage address in `4(A7)` and `D0`, and jumps to `tbase`.

Around the depack the stub switches to supervisor mode (`Super(0)`, `$a366`), prints the banner
(moved down a row on a hi-res screen, `$a350`), clears the first 1,532 bytes of the screen
(`$a338`), and saves palette register 0, which the loop writes as a progress flash (`$a544`) and
the stub restores afterwards (`$a392`). There is no checksum or self-check.

## Ratios against modern compressors

Carrier Command's unpacked PRG, 323,196 bytes (sha256 `0d3938982b8a909de79b52d26824ba05b42980cbcdcd94ce790b912bcfe20448`),
each compressor fed on stdin (no stored filename); the Automation row is the `LSD!` payload alone, 135,486
bytes (41.9%) as the whole packed PRG (`py/infographics/gen_depack.py`):

| Compressor | Bytes | Ratio |
|---|---|---|
| lz4 -9 | 143,721 | 44.5% |
| Automation 2.3r (`LSD!` payload) | 134,660 | 41.7% |
| gzip -9 | 119,914 | 37.1% |
| zstd -19 | 110,368 | 34.1% |
| xz -9e | 97,100 | 30.0% |

Packed file against unpacked for the rest of the disk: PACT1 117,918 / 359,194 (32.8%), PACT3
88,922 / 321,190 (27.7%), PACT4 138,870 / 333,870 (41.6%), STRAID 105,982 / 223,056 (47.5%).

It sits between lz4 and deflate. The gap to gzip is the missing entropy stage and the 4 KB window
against deflate's 32 KB. What it buys is a ~330-byte decoder that needs no buffer beyond the
program's own memory and about 218 bytes of slack (219 binding for this file); zstd and LZMA need kilobytes of decoder and tables
and a separate output buffer. Structurally it belongs with Pack-Ice, LZ4 and the Amiga and C64
crunchers (LZ77, Elias-style tiered lengths, backwards in-place decode); the Pack-Ice relation is
inferred from the shared bitstream, not from any record of who derived what.

## Trivia (unverified, one source)

From the Atarimania entry (https://www.atarimania.com/utility-atari-st-automation-packer_44942.html),
not corroborated elsewhere: Automation Packer, UK, 1989, version 2.31 (the stub says "V2.3r"; the
two are not tied together), credited to Cyrano Jones / The Law, Axe (Superior) and Gibson Gordon.
The Pompey Pirates documented it, said the circulating version had no source or docs, and claimed
their Pompey Packer v1 was faster and smaller (4,220 against 4,562 bytes on their test). It offered
F1..F10 compression levels, multi-file packing and an `AUTO23.S` hook on `TRAP #1` that depacks
files as they are read, the mechanism Impossamole's crack hook uses (`reversing/impossamole/secrets.md`).
A version 5.01 is listed for 1991.

## Running a Zuul game outside the menu

The Zuul #45 copies have `$ffffffff` as the first text long where `STRAID.PRG` and `FRODON.STA`
have `movea.l 4(a7),a5` (`2a6f 0004`); run alone, the program takes a Line-F exception on its
first instruction. Inferred: the menu loader writes the instruction before launching. Restoring
those 4 bytes (file offset `$1c`) is enough for `PACT2.PRG` to depack and run from `\AUTO\`.

## Reproduce

```
python3 -I reversing/carriercommand/py/autopack_depack.py <PACT2.PRG> <out.prg>
python3 -I reversing/carriercommand/py/autopack_depack.py --gap <packed PRG>...
gzip -9 -c <out.prg> | wc -c        # likewise xz -9e, zstd -19, lz4 -9
```

The depacker's output for `PACT2.PRG` matches `tools/lsd_depack.py` run on the extracted payload
byte for byte.
