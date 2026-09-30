"""Decode the level directory (the '881990' sector) and every block of each Cadaver disk image that has one.
No emulator needed.  The directory is a flat list of (start sector, sector count) pairs after a 16-byte header
('881990', then five words: day, month, year, hour, minute of the build, inferred).  Each pair is a block that is
either LZHUF (4-byte big-endian expanded length, then the bit stream; cad_lzh.py) or raw; a block is called lzh when
cad_lzh.decode_block() expands it and the output's own first long equals expanded_length-4 (every lzh block found
satisfies this), raw otherwise.  Levels are the runs of pairs ending at each raw block (the raw block is the third
pair of a one-disk record, stride 5 pairs = 20 bytes = `mulu #$14` at $00bac8; the two-disk Level disk has stride 7).
Run:  python3 reversing/cadaver/py/secrets/disk2_levels.py   (from M68000/)"""
import glob, os, struct, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from cad_lzh import decode_block
M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..')); REPO = os.path.dirname(M68)
for p in sorted(glob.glob(os.path.join(REPO, 'Cadaver', '**', '*.st'), recursive=True)):
    d = open(p, 'rb').read(); i = d.find(b'881990')
    if i < 0 or i % 512: print(os.path.relpath(p, REPO), ': no level directory'); continue
    pairs = []
    for n in range(0, (512 - 16) // 4):
        s, c = struct.unpack_from('>HH', d, i + 0x10 + 4 * n)
        if c == 0: break
        pairs.append((s, c))
    kinds = []; info = []
    for s, c in pairs:
        blk = d[s * 512:(s + c) * 512]; ln = struct.unpack('>I', blk[:4])[0]
        kind = 'raw'; detail = 'first long $%08x' % ln
        if 16 <= ln <= 0x200000:
            try:
                out, used = decode_block(blk)
                if struct.unpack('>I', out[:4])[0] == ln - 4: kind = 'lzh'; detail = 'expanded %d, stream %d/%d bytes' % (ln, used, len(blk) - 4)
            except Exception: pass
        kinds.append(kind); info.append(detail)
    raws = [n for n, k in enumerate(kinds) if k == 'raw']
    stride = raws[1] - raws[0] if len(raws) > 1 else len(pairs)
    print('%s: directory at sector %d, build stamp words %s, %d blocks (%d lzh, %d raw), level stride %d pairs = %d bytes, %d levels' % (
        os.path.relpath(p, REPO), i // 512, struct.unpack_from('>5H', d, i + 6), len(pairs), kinds.count('lzh'), kinds.count('raw'), stride, stride * 4, len(pairs) // stride))
    first = raws[0] - 2 if raws else 0
    for n, (s, c) in enumerate(pairs):
        lvl, res = divmod(n - (raws[0] - 2 if raws else 0), stride)
        print('  L%d res%d sector %4d +%3d (%6d bytes): %s %s' % (lvl, res, s, c, c * 512, kinds[n], info[n]))
