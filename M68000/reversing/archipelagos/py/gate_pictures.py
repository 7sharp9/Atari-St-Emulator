#!/usr/bin/env python3
"""gate_pictures.py: the picture islands and the disk parameter blocks, against captures from capture_pictures.sh.

For N = 15, 25, 85 (in the special table $16a58): island_model.py's picture path against the game's map at the
$15b8e return (65,536 cells each), and the 2,048 bytes the game read into its buffer ([$1d55e] ^ $8000) against
island_model.disk_read on cylinder T side 1. For N = 6, 99: the 21-word block the game loaded at $1697a against
island_model.disk_block, then the procedural model's map. Controls (not expected counts): the picture of the next
special island, and the same sectors read from side 0.

usage: uv run python reversing/archipelagos/py/gate_pictures.py
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import island_model as im
from gfxview import load_ram

W = os.path.join(im.d, 'scratchpad', 'archipelagos', 'pic')
disk = open(im.DISK, 'rb').read()

def side0(track, sector, n):
    out = b''
    while len(out) < n:
        o = ((track * 2) * 10 + sector - 1) * 512
        out += disk[o:o + 512]; sector += 1
        if sector > 10: sector, track = 1, track + 1
    return out[:n]

def match(a, b): return sum(x == y for x, y in zip(a, b))

for N in (15, 25, 85):
    ram, _ = load_ram(f'{W}/ent_{N}.snap'); live, _ = load_ram(f'{W}/exit_{N}.snap')
    ref = bytes(live[im.BASE:im.BASE + 0x10000])
    out = im.Model(bytearray(ram)).run(disk)
    buf = (int.from_bytes(live[0x1d55e:0x1d562], 'big') ^ 0x8000) & 0xFFFFF
    print(f'picture N={N}: {match(out, ref)}/65536 cells match; '
          f'buffer {match(im.picture_bits(disk, N, ram), live[buf:buf + 0x800])}/2048 bytes match the side-1 read')
    # controls: the next special island's picture; the same sectors on side 0
    nxt = N + 5
    real = im.picture_bits
    im.picture_bits = lambda dk, n, r: real(dk, nxt, r)
    c1 = match(im.Model(bytearray(ram)).run(disk), ref)
    w = lambda a: ram[a] << 8 | ram[a + 1]
    a = 0x16a58
    while w(a) != N: a += 6
    im.picture_bits = lambda dk, n, r: side0(w(a + 2), w(a + 4), 0x800)
    c2 = match(im.Model(bytearray(ram)).run(disk), ref)
    im.picture_bits = real
    print(f'  control N={N}: picture of {nxt} {c1}/65536, side 0 {c2}/65536')

for N in (6, 99):
    ram, _ = load_ram(f'{W}/ent_{N}.snap'); live, _ = load_ram(f'{W}/exit_{N}.snap')
    blk = bytes(ram[0x1697a:0x1697a + 42])
    words = sum(blk[i:i + 2] == im.disk_block(disk, N)[i:i + 2] for i in range(0, 42, 2))
    m = bytearray(ram); m[0x1697a:0x1697a + 42] = im.disk_block(disk, N)   # the model's block from the disk alone
    out = im.Model(m).run(disk)
    print(f'disk block N={N}: {words}/21 words match; {match(out, bytes(live[im.BASE:im.BASE + 0x10000]))}/65536 cells match')
    c = sum(blk[i:i + 2] == im.disk_block(disk, N - 1)[i:i + 2] for i in range(0, 42, 2))
    print(f'  control N={N}: block of {N - 1} {c}/21 words')
