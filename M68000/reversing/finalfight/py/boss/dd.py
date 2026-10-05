"""dd.py: reader for the per-frame dumps written by dm.lua (DM_DUMP): per frame a u32 frame number then the ranges of DM_RANGES (default ff8000-ffb300).
usage (module): D = Dump(path, ranges=[(0xff8000,0xffb300)]); D.n, D.frame(i), D.u8(i,addr), D.u16(i,addr), D.rec(i,addr,n)"""
import numpy as np, os, sys
class Dump:
    def __init__(self, path, ranges=((0xff8000, 0xffb300),)):
        self.ranges = ranges
        self.sz = 4 + sum(b - a for a, b in ranges)
        raw = np.memmap(path, dtype=np.uint8, mode='r')
        self.n = len(raw) // self.sz
        self.a = raw[:self.n * self.sz].reshape(self.n, self.sz)
        self.base = ranges[0][0]
    def frame(self, i): return int.from_bytes(bytes(self.a[i, :4]), 'big')
    def off(self, addr):
        o = 4
        for a, b in self.ranges:
            if a <= addr < b: return o + addr - a
            o += b - a
        raise KeyError(hex(addr))
    def u8(self, i, addr): return int(self.a[i, self.off(addr)])
    def u16(self, i, addr): o = self.off(addr); return (int(self.a[i, o]) << 8) | int(self.a[i, o + 1])
    def s16(self, i, addr): v = self.u16(i, addr); return v - 65536 if v & 0x8000 else v
    def u32(self, i, addr): return (self.u16(i, addr) << 16) | self.u16(i, addr + 2)
    def col8(self, addr): o = self.off(addr); return self.a[:, o].astype(np.int32)
    def col16(self, addr): o = self.off(addr); return (self.a[:, o].astype(np.int32) << 8) | self.a[:, o + 1]
    def frames(self): return (self.a[:, 0].astype(np.int64) << 24) | (self.a[:, 1].astype(np.int64) << 16) | (self.a[:, 2].astype(np.int64) << 8) | self.a[:, 3]
BOSS = int(os.environ.get('DM_BOSS', 'ff9a68'), 16)
P1 = 0xff8568
