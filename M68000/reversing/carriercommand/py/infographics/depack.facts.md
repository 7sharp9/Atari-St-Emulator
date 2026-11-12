# depack.svg: facts and sources

Figure: `gen_depack.py` writes `scratchpad/carrier/infographics/depack.svg` (PNG: `rsvg-convert -z 2 depack.svg -o depack.png`).
The depacker is `py/autopack_depack.py`'s loop with a per-token log, run in one shared memory image laid out as the stub
lays it out (stream at tbase+$31a, output at tbase+$400), so a write over an unread stream byte would show as corrupt
output. Before drawing, the script asserts: output equal to `autopack_depack.py`'s and to packer.md's sha256; the
minimum gap and final gap equal to `autopack_depack.min_gap`; destination lowered by the live minimum still correct,
one byte lower corrupt. It also compares the output with the emulator's RAM in `c80.snap` (printed, not asserted).
Doc: `packer.md`.

| fact in the figure | source |
|---|---|
| 134,660-byte payload (12-byte header + 134,648-byte stream) depacks to 323,196 bytes | PACT2.PRG header and LSD! header, read by the script |
| output correct | sha256 `0d39...0448` (packer.md); equal to `autopack_depack.py`; 322,880 of 323,168 bytes after the PRG header equal `c80.snap` RAM at `$296` + file offset (319,068 of 319,072 past the first 4 KB; the rest is presumably variables the game wrote) |
| stub 794 bytes (`$31a`), stream starts at 806, output at `$400` = 1024; 218 apart at the end | PRG header; `DEST_OFS` in autopack_depack.py (packer.md "How it depacks", stub `$a31c`) |
| mover in screen memory slides the image down `$400` (`$a43c`) | packer.md, from code; not checked here |
| before any read: write pointer 324,220, read pointer 135,454 (payload end), gap 188,766 | computed: `$400` + size; `$31a` + payload length |
| pointers per token (B), gap per token on a log scale (C) | per-token log, 60,480 tokens, drawn every 67th |
| gap = 218 + (bytes still to write) - (stream bytes still unread) | algebra on the gap definition, `$400 - ($31a + 12)` = 218 |
| gap never below 3,414 before the last 4,096 bytes written | min over the token log with more than 4,096 bytes to write |
| every literal run widens or keeps the gap (20,737 of 20,737); 36,575 of 39,743 matches shrink it | gap change across each logged token |
| minimum 218 at file offset 0, after the last stream byte is read | per-write log (`tail`) |
| closest while stream bytes remain unread: 219, writing file offset 5 with 4 stream bytes unread | per-write log |
| destination 219 lower: correct; 220 lower: 5 bytes wrong | rerun of the in-place depack with `dest_ofs` lowered |
| other packed files: PACT1, PACT4, STRAID, FRODON.STA closest live gap 218 (one byte lower corrupts 5, 5, 2, 4 bytes), PACT3 220; all six end at 218 | same, on each file in `files/` |
| token fields and ranges: literal count 1..1,038 (tiers 2..4, 5..7, 8..14, 15..1,038), length 2..1,033, offset 0..4,383 | tables in autopack_depack.py (stub `$a53a`, `$a594`, `$a5d8`); literal tiers computed from the tables |
| 20,737 literal runs carry 53,130 bytes, 39,743 matches carry 270,066; longest match 1,023, farthest offset 4,382, longest literal run 906 | token log; the two byte counts sum to 323,196 |
| lz4 -9 143,721, gzip -9 119,914, zstd -19 110,368, xz -9e 97,100; Automation 134,660 (payload incl. header) | run by the script on stdin: lz4 1.9.4, Apple gzip 479, zstd 1.5.6, xz 5.6.4 |

## Flags

- **218 is the closest approach, but not the margin that matters.** packer.md says the closest approach is 218 on all six
  files at the very end. True for the pointer distance, but that minimum is reached after the last stream byte has been
  read, when nothing is left to overwrite. The binding minimum (while unread stream remains) is 219 for PACT2 and 220 for
  PACT3, 218 for the other four; the depack still works with the destination that many bytes lower and breaks one byte
  further (asserted for PACT2, printed for all six). "218 bytes of slack" in "Ratios" is right for four of the six files.
- **"Each token consumes fewer bytes than it produces"** (packer.md "How it depacks", item 1) is false for literal runs:
  every one of the 20,737 runs consumes its bytes plus its count bits and widens or keeps the gap; 3,168 of 39,743 matches
  (short ones whose bits straddle byte loads) do not shrink it either. The gap shrinks overall because matches dominate.
- **Literal count is 1..1,038, not 1..1,039** (packer.md "Algorithm"): the 10-bit tier gives v + 14 + 1 with v at most
  1,023, and the shorter tiers stop one below all ones.
- **Start gap 188,762** (packer.md) is not reproduced: write at `$400` + 323,196 = 324,220 against the payload end
  `$31a` + 134,660 = 135,454 gives 188,766 before any read (188,770 after the first bit-buffer byte). Inferred: the doc
  measured the read pointer 4 bytes higher (A0 before the `subq #4`?); not checked against the stub.
- **gzip and zstd figures in "Ratios"** (119,933, 110,371) are file-mode outputs: from stdin they are 119,914 and 110,368.
  gzip's 19 bytes are the stored name `pact2.unpacked.prg` + NUL; zstd's 3 bytes are presumably the frame's
  content-size field. Percentages unchanged. The Automation row counts the payload (134,660, with header, without the
  794-byte stub); the other-disk ratios in the same section use whole PRG files (PACT2's would be 135,486, 41.9%).
- **Relocation step unclear.** The unpacked PRG has absflag `$ffff` at offset `$1a`, data 0, bss 0, and no fixup table
  inside its 323,196 bytes, so packer.md item 2's fixup walk at `dest + $1c + text + data + symbols` would read past the
  image. In `c80.snap` the image sits at `$296` + file offset (text at `$2b2`), not at tbase `$a304`, so the unpacked
  program moves itself again after the mover (inferred from the RAM match, not traced).
