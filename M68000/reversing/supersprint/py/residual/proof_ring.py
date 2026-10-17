"""B2's 150-byte header = the top-left quadrant (48x25, 1 bit per pixel, 6 bytes/row) of the shop screen's wheel-surround ring.
$162f2(screen, B2) writes its three words per row into bitplane 0 at screen+$3918 (x = 112, y = 91, 160-byte rows);
$16424(screen) mirrors rows 0..52 of plane 0 horizontally (word order and bit order reversed) into the right half, and
$16466(screen) mirrors the 53 rows from the top half downwards into the lower half.  Differential tests vs callcap with random data, and
the three-step composition against the live shop screen (agents/secrets/snap/shop.snap).  usage: proof_ring.py [trials]"""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from calldiff import CallDiff
from PIL import Image
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
random.seed(2)
def quad(scr, hdr):
    for r in range(25):
        w = struct.unpack_from('>3H', hdr, r * 6)
        for k in range(3): struct.pack_into('>H', scr, 0x3918 + r * 160 + 8 * k, w[k])
def rev16(v): return int('{:016b}'.format(v)[::-1], 2)
def hmirror(scr):
    for row in range(53):
        for col in range(10):
            s = 0x2760 + row * 160 + col * 8; d = 0x27FA + row * 160 - col * 8
            w = struct.unpack_from('>H', scr, s)[0]
            struct.pack_into('>H', scr, d, rev16(w))
def vmirror(scr):
    for row in range(53):
        s = 0x47E0 - row * 160; d = 0x4EC4 + row * 160
        scr[d:d + 160] = scr[s:s + 160]
if __name__ == '__main__':
    cd = CallDiff(); R = cd.ram
    scr = struct.unpack_from('>I', R, A4 - 78)[0]; b2 = struct.unpack_from('>I', R, A4 - 106)[0]
    res = {}
    for name, addr, args in (('$162f2', 0x162F2, lambda: struct.pack('>II', scr, b2)), ('$16424', 0x16424, lambda: struct.pack('>I', scr)), ('$16466', 0x16466, lambda: struct.pack('>I', scr))):
        ok = n = 0; ex = 0
        for t in range(N):
            if name == '$162f2': cd.poke(b2, bytes(random.randrange(256) for _ in range(150)))
            else: cd.poke(scr, bytes(random.randrange(256) for _ in range(0x5200)))
            oc, ch, d = cd.call(addr, args(), presets='A5=a304 A4=1eb44'); assert oc == 'returned', oc
            live = cd.apply(R[scr:scr + 32000], scr, ch); mine = bytearray(R[scr:scr + 32000])
            if name == '$162f2': quad(mine, bytes(R[b2:b2 + 150]))
            elif name == '$16424': hmirror(mine)
            else: vmirror(mine)
            e = sum(a == b for a, b in zip(live, mine)); ok += e; n += 32000; ex += (e == 32000)
        res[name] = (ok, n, ex)
        print('%s screen %d/%d bytes equal, %d/%d trials exact' % (name, ok, n, ex, N))
    cd.close()
    # composition against the live shop screen
    shop = os.path.join(sscfg.WORK, 'agents', 'secrets', 'snap', 'shop.snap')
    S = Ram(shop); hdr = bytes(dat := open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()[0x3140:0x3140 + 150])
    assert bytes(S.b[S.g(-106):S.g(-106) + 150]) == hdr, 'B2 header in RAM differs from SUPER.DAT'
    live = bytes(S.b[S.g(-78):S.g(-78) + 32000]); live2 = bytes(S.b[S.g(-82):S.g(-82) + 32000])
    for nm, lv in (('draw screen', live), ('shown screen', live2)):
        m = bytearray(32000); quad(m, hdr); hmirror(m); vmirror(m)
        # plane-0 words (every 4th word) the composed ring sets, vs the live screen; the live shop screen draws the wheel and text over it
        M = [o for o in range(0, 32000, 2) if m[o:o + 2] != b'\0\0']      # every plane word the ring sets (left arcs plane 0, mirrored right arcs plane 1, the vertical mirror lands 4 bytes to the right: planes 2/3)
        eq = sum(lv[o:o + 2] == bytes(m[o:o + 2]) for o in M)
        sub = sum(1 for o in M if (int.from_bytes(lv[o:o + 2], 'big') & int.from_bytes(m[o:o + 2], 'big')) == int.from_bytes(m[o:o + 2], 'big'))
        print('shop snapshot %s: the ring sets %d plane words; live equals %d, live contains the ring bits in %d' % (nm, len(M), eq, sub))
    # picture: the composed ring (plane 0), rows 88..152, x 96..224, next to the live shop screen's plane 0 over the same window
    full = bytearray(32000); quad(full, hdr); hmirror(full); vmirror(full)
    def plane0(buf):
        img = Image.new('L', (128, 64)); px = img.load()
        for y in range(64):
            for x in range(128):
                X = 96 + x; o = (88 + y) * 160 + (X >> 4) * 8 + ((X >> 3) & 1)
                v = ((buf[o] >> (7 - (X & 7))) & 1) + 2 * ((buf[o + 2] >> (7 - (X & 7))) & 1)
                px[x, y] = (0, 120, 200, 255)[v]
        return img
    W = Image.new('L', (128 * 3 * 2 + 6, 64 * 3)); W.paste(plane0(full).resize((384, 192), Image.NEAREST), (0, 0)); W.paste(plane0(live).resize((384, 192), Image.NEAREST), (390, 0))
    W.save(os.path.join(AGENT, 'out', 'b2_ring.png'))
