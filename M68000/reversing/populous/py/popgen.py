"""popgen.py - Python reproduction of Populous (Atari ST) landscape generation.
  rand()      = $16702   seed word $3d52e
  raise_pt()  = $bf60    height map $34be4, 65x65 words, index y*65+x
  walk()      = $bebc    random-walk hill builder
  gen_land()  = $be84    walk(2,4) walk(4,2) walk(3,3)   (args = x-step range, y-step range)
  tiles()     = $c0ee    per-cell derived maps ($33be4 base height, $36e78 shape)
CLI: python popgen.py <seed_hex> [prerolls]  -> prints a height histogram."""
import sys
N = 65
class Gen:
    def __init__(self, seed):
        self.seed = seed & 0xffff
        self.h = [0]*(N*N)
        self.raises = 0            # $37f8a
        self.bbox = [0x7fff, -1, 0x7fff, -1]
    def rand(self):
        # $16702: move.w seed,D0; mulu #$24a1,D0; addi.w #$24df,D0; bclr #15,D0; move.w D0,seed
        self.seed = ((self.seed * 0x24a1) + 0x24df) & 0x7fff
        return self.seed
    def raise_pt(self, x, y):
        # $bf60
        if x > 64 or x < 0 or y > 64 or y < 0:
            return 0
        i = y*N + x
        h = self.h
        if h[i] < 8:
            self.raises += 1
            h[i] += 1
            # neighbour order exactly as $bfb4..$c0d0: E, SE, S, SW, W, NW, N, NE
            # the comparison reads the raw array (row wrap / out-of-array reads only
            # matter when the neighbour is itself out of range, and raise_pt rejects those)
            for dx, dy in ((1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)):
                j = i + dy*N + dx
                nv = h[j] if 0 <= j < N*N else self._outside(j)
                if h[i] - nv > 1:
                    self.raise_pt(x+dx, y+dy)
            b = self.bbox
            b[0] = min(b[0], x); b[1] = max(b[1], x); b[2] = min(b[2], y); b[3] = max(b[3], y)
        return h[i]
    def _outside(self, j):
        return 0x7fff   # never triggers a call; any call would be rejected by the range test anyway
    def lower_pt(self, x, y):
        # $d262 (mirror of $bf60): see terrain.md
        if x > 64 or x < 0 or y > 64 or y < 0:
            return 0
        i = y*N + x
        h = self.h
        if h[i] > 0:
            self.raises += 1
            h[i] -= 1
            for dx, dy in ((1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)):
                j = i + dy*N + dx
                nv = h[j] if 0 <= j < N*N else -0x8000
                if nv - h[i] > 1:
                    self.lower_pt(x+dx, y+dy)
        return h[i]
    @staticmethod
    def _mod(a, b):
        # 68000 divs remainder: sign follows the dividend (a is 0..32767 here)
        r = abs(a) % abs(b)
        return -r if a < 0 else r
    def walk(self, rx, ry):
        # $bebc(rx = 8(A6), ry = 10(A6))
        x = self._mod(self.rand(), 64)
        y = self._mod(self.rand(), 64)
        while self.raise_pt(x, y) != 6:
            x += self._mod(self.rand(), rx*2+1) - rx
            y += self._mod(self.rand(), ry*2+1) - ry
            x = min(max(x, 0), 64)
            y = min(max(y, 0), 64)
    def gen_land(self):
        self.walk(2, 4); self.walk(4, 2); self.walk(3, 3)
        return self.h
class World(Gen):
    """Gen + the derived per-cell maps (64x64, index y*64+x)."""
    def __init__(self, seed):
        super().__init__(seed)
        self.alt = [0]*4096      # $33be4 cell altitude
        self.shape = [0]*4096    # $36e78 cell shape / terrain code
        self.feat = [0]*4096     # $3c522 cell feature (trees 0x32-0x34, buildings ...)
    def tiles(self, x0, y0, x1, y1):
        # $c0ee(x0,y0,x1,y1): recompute cells x0..x1 (outer), y0..y1 (inner)
        h = self.h
        for x in range(x0, x1+1):
            for y in range(y0, y1+1):
                c = y*64 + x; i = y*65 + x
                a, b, cc, d = h[i], h[i+1], h[i+66], h[i+65]
                s = (a + b + cc + d) >> 2
                bits = (a > s) | (b > s) << 1 | (cc > s) << 2 | (d > s) << 3
                if self.shape[c] == 0x2f and (bits or s):
                    bits = self.shape[c]
                else:
                    self.shape[c] = bits
                if s and not bits:
                    s -= 1; bits = 0xf
                if s == 0 and bits not in (0xf, 0):
                    bits += 0x10
                self.alt[c] = s
                if self.shape[c] == 0x2f:
                    bits = 0x2f
                else:
                    self.shape[c] = bits
                if bits == 0:
                    self.feat[c] = 0
    def scatter(self):
        # $12e06: 22 clusters; clusters 0-6 = rocks (shape 0x2f-0x31), 7-21 = trees (feature 0x32-0x34)
        for k in range(22):
            v = 0x2f if k < 7 else 0x32
            r1 = self.rand(); r2 = self.rand()
            for _ in range(30):
                x = self.rand() % 9 + r1 % 59
                y = self.rand() % 9 + r2 % 59
                if 0 <= x < 64 and 0 <= y < 64:
                    c = y*64 + x
                    if self.shape[c] != 0 and self.shape[c] != 0x2f:
                        if v == 0x2f:
                            self.shape[c] = self.rand() % 3 + 0x2f
                        else:
                            self.feat[c] = self.rand() % 3 + 0x32
def build_world(seed, prerolls=4):
    """$b316 terrain part: seed, 4 rand() calls in $bbd4, $be84, $c0ee(0,0,63,63), $12e06."""
    wd = World(seed)
    for _ in range(prerolls):
        wd.rand()
    wd.gen_land(); wd.tiles(0, 0, 63, 63); wd.scatter()
    return wd
def generate(seed, prerolls=4):
    g = Gen(seed)
    for _ in range(prerolls):
        g.rand()
    g.gen_land()
    return g
if __name__ == '__main__':
    sys.setrecursionlimit(100000)
    g = generate(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    from collections import Counter
    print(sorted(Counter(g.h).items()))
