"""mk_savedisk.py <src.ram> <out.st> [used-slot-letters] [slotX=ramfile ...]

Builds a PowerMonger save disk in the geometry the game's own formatter `_format_` $1ba72 writes and
`diskio` $d9fc addresses for the save calls (D0 = 0: 10 sectors per track, single-sided, 80 tracks =
800 sectors = 409,600 bytes). Sector 0 is the game's ID sector, taken from RAM $1bb0e of <src.ram>, with
the slot-used flags at +$ec set for the letters given. Bytes 24..27 are overwritten with 0a 00 01 00 (the
game checks only the first long 'POWE'). The emulator no longer needs them: MMU.LoadDiskA ignores a BPB
whose total-sector field does not match the file and takes 10 spt / 1 side from the 409,600-byte size; an
emulator that read "GA ME" there as a BPB would see 9 spt and fail every 10th sector.
slotX=ramfile fills slot X (sectors 198*X+1..) with RAM $3f768..$58368 of that .ram after the SAVE button's
own first step, the 195-byte copy $3f2a0 -> $3f768 ($77a2): that is what SAVE writes (a natural SAVE's
sectors equal RAM at $1bdfe's exit byte for byte, py/roundtrip.sh BP=1).
Repo root: walk up to tools/rdis.py.
"""
import sys
from pathlib import Path
here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools/rdis.py').exists())
src, out = sys.argv[1], sys.argv[2]
used = sys.argv[3] if len(sys.argv) > 3 and '=' not in sys.argv[3] else ''
fills = [a for a in sys.argv[3:] if '=' in a]
ram = Path(src).read_bytes()
img = bytearray(800 * 512)
img[0:512] = ram[0x1bb0e:0x1bb0e + 512]
img[24:28] = bytes([0x0a, 0, 1, 0])
for k in range(26): img[0xec + k] = 0
for c in used.upper(): img[0xec + ord(c) - 65] = 0xff
for a in fills:
    letter, rf = a.split('=', 1)
    s = ord(letter.upper()) - 65
    r = Path(rf).read_bytes()
    blk = bytearray(r[0x3f768:0x58368]); blk[0:195] = r[0x3f2a0:0x3f2a0 + 195]
    img[(198 * s + 1) * 512:(198 * s + 199) * 512] = blk
    img[0xec + s] = 0xff
assert img[0:4] == b'POWE', img[0:4]
Path(out).write_bytes(img)
print(out, len(img), 'used', [chr(65 + k) for k in range(26) if img[0xec + k]])
