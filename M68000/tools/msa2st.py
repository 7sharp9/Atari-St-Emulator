#!/usr/bin/env python3
"""Convert an Atari ST .MSA disk image to a raw .ST (FAT12 sector) image.

MSA format (big-endian throughout):
  header: magic 0x0E0F, sectors-per-track (u16), sides-1 (u16),
          start track (u16), end track (u16)
  per track (for track in [start,end], for side in [0, sides]):
    data_len (u16)
    if data_len == sectors_per_track*512: that many bytes, stored raw
    else: RLE stream of data_len bytes:
      0xE5 <byte> <count:u16 be>  -> `byte` repeated `count` times
      any other byte              -> literal
"""
import struct
import sys


def convert(data: bytes) -> bytes:
    magic, spt, sides_minus1, start_track, end_track = struct.unpack_from(">HHHHH", data, 0)
    if magic != 0x0E0F:
        raise ValueError(f"not an MSA image (magic={magic:#06x})")
    sides = sides_minus1 + 1
    track_size = spt * 512
    pos = 10
    out = bytearray()
    for track in range(start_track, end_track + 1):
        for side in range(sides):
            (data_len,) = struct.unpack_from(">H", data, pos)
            pos += 2
            chunk = data[pos:pos + data_len]
            pos += data_len
            if data_len == track_size:
                out += chunk
                continue
            expanded = bytearray()
            i = 0
            while i < len(chunk):
                b = chunk[i]
                if b == 0xE5:
                    val = chunk[i + 1]
                    count = struct.unpack_from(">H", chunk, i + 2)[0]
                    expanded += bytes([val]) * count
                    i += 4
                else:
                    expanded.append(b)
                    i += 1
            if len(expanded) != track_size:
                raise ValueError(
                    f"track {track} side {side}: expanded {len(expanded)} bytes, expected {track_size}"
                )
            out += expanded
    return bytes(out)


def main():
    if len(sys.argv) != 3:
        print("usage: msa2st.py <in.msa> <out.st>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        data = f.read()
    st = convert(data)
    with open(sys.argv[2], "wb") as f:
        f.write(st)
    print(f"wrote {len(st)} bytes to {sys.argv[2]}")


if __name__ == "__main__":
    main()
