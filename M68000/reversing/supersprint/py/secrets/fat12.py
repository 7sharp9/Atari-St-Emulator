"""fat12.py - minimal FAT12 reader for the Atari ST image: file -> list of (image offset, length) extents, and patch_file()
to write bytes into a copy of the image.  Usage: fat12.py            (prints the root directory and each file's extents)"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import sscfg

class Disk:
    def __init__(s, path):
        s.img = bytearray(open(path, 'rb').read())
        b = s.img
        s.bps = struct.unpack_from('<H', b, 0x0b)[0]; s.spc = b[0x0d]
        s.res = struct.unpack_from('<H', b, 0x0e)[0]; s.nfat = b[0x10]
        s.nroot = struct.unpack_from('<H', b, 0x11)[0]; s.spf = struct.unpack_from('<H', b, 0x16)[0]
        s.fat0 = s.res * s.bps
        s.root = (s.res + s.nfat * s.spf) * s.bps
        s.data = s.root + s.nroot * 32
    def fat(s, c):
        o = s.fat0 + c * 3 // 2
        v = s.img[o] | (s.img[o + 1] << 8)
        return (v >> 4) & 0xfff if c & 1 else v & 0xfff
    def entries(s, dirpos=None, n=None):
        pos = s.root if dirpos is None else dirpos
        n = s.nroot if n is None else n
        for i in range(n):
            e = s.img[pos + i * 32: pos + i * 32 + 32]
            if e[0] == 0: break
            if e[0] == 0xe5 or e[11] & 0x08: continue
            name = e[:8].decode('latin1').rstrip() + ('.' + e[8:11].decode('latin1').rstrip() if e[8:11].strip() else '')
            yield name, e[11], struct.unpack_from('<H', e, 26)[0], struct.unpack_from('<I', e, 28)[0]
    def extents(s, cl, size):
        out = []; csz = s.spc * s.bps; left = size
        while 2 <= cl < 0xff0 and left > 0:
            out.append((s.data + (cl - 2) * csz, min(csz, left))); left -= csz; cl = s.fat(cl)
        return out
    def find(s, path):
        pos, n = None, None
        parts = path.upper().split('/')
        for k, part in enumerate(parts):
            for name, attr, cl, size in s.entries(pos, n):
                if name.upper() == part:
                    if k == len(parts) - 1: return cl, size
                    pos = s.data + (cl - 2) * s.spc * s.bps; n = 16 * s.spc * s.bps // 32 // 16 * 16
                    break
            else:
                raise KeyError(path)
    def file_offsets(s, path):
        cl, size = s.find(path)
        return s.extents(cl, size), size
    def patch(s, path, off, data):
        ext, size = s.file_offsets(path)
        pos = 0
        for start, ln in ext:
            if off < pos + ln and off + len(data) > pos:
                a = max(off, pos); b = min(off + len(data), pos + ln)
                s.img[start + (a - pos): start + (b - pos)] = data[a - off: b - off]
            pos += ln
    def save(s, path): open(path, 'wb').write(s.img)

if __name__ == '__main__':
    d = Disk(sscfg.DISK)
    for e in d.entries(): print(e)
    for f in ('INIT.DAT', 'SUPER1.DAT', 'SUPER.DAT', 'SSPRINT.HSC', 'AUTO/SSPRINT.PRG'):
        ext, size = d.file_offsets(f)
        print(f, size, 'extents', [(hex(a), b) for a, b in ext][:4], '...', len(ext))
        raw = b''.join(bytes(d.img[a:a + b]) for a, b in ext)
        ref = open(os.path.join(sscfg.FILES, f), 'rb').read()
        print('   matches extracted copy:', raw == ref)
