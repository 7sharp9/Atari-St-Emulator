"""fat12.py - minimal FAT12 reader for the Populous disk images: directory, chains, free clusters."""
import struct, zipfile, os, sys


class Fat:
    def __init__(self, d):
        self.d = bytearray(d)
        (self.bps, self.spc, self.res, self.nf, self.nroot, self.tot) = struct.unpack_from('<HBHBHH', d, 11)
        self.spf = struct.unpack_from('<H', d, 22)[0]
        self.root = (self.res + self.nf * self.spf) * self.bps
        self.data = self.root + self.nroot * 32
        self.ncl = (self.tot - self.data // self.bps) // self.spc

    def ent(self, i):
        o = self.res * self.bps + i * 3 // 2
        v = self.d[o] | self.d[o + 1] << 8
        return v >> 4 if i & 1 else v & 0xfff

    def free(self):
        return [i for i in range(2, self.ncl + 2) if self.ent(i) == 0]

    def entries(self, off=None, n=None):
        off = self.root if off is None else off
        n = self.nroot if n is None else n
        for i in range(n):
            e = self.d[off + i * 32: off + i * 32 + 32]
            if e[0] == 0: break
            if e[0] == 0xe5: continue
            name = e[:8].decode('latin1').rstrip() + ('.' + e[8:11].decode('latin1').rstrip() if e[8] != 32 else '')
            yield name, e[11], struct.unpack_from('<H', e, 26)[0], struct.unpack_from('<I', e, 28)[0], off + i * 32

    def chain(self, c):
        out = []
        while 2 <= c < 0xff0 and len(out) < 1000:
            out.append(c); c = self.ent(c)
        return out

    def read(self, name):
        for n, attr, cl, sz, _ in self.entries():
            if n.upper() == name.upper():
                cs = self.spc * self.bps
                b = b''.join(bytes(self.d[self.data + (c - 2) * cs: self.data + (c - 1) * cs]) for c in self.chain(cl))
                return b[:sz]
        raise KeyError(name)


def original():
    from popcfg_local import REPO
    z = zipfile.ZipFile(os.path.join(REPO, 'Populous (1989)(Bullfrog)[cr Replicants].zip'))
    return z.read([x for x in z.namelist() if x.endswith('.st')][0])


if __name__ == '__main__':
    f = Fat(open(sys.argv[1], 'rb').read())
    print('clusters', f.ncl, 'free', f.free())
    for n, attr, cl, sz, _ in f.entries():
        ch = f.chain(cl)
        print('%-12s attr %02x size %6d clusters %3d %s' % (n, attr, sz, len(ch), (ch[0], ch[-1]) if ch else ''))
