"""More differential tests (callcap vs Python) for the B5 regions: particle $143ca, 16x8 masked sprite $1416c, 16x8 tile $14262,
small helicopter $13cbc (frame poked into the work buffer -1906(A4) exactly as $13f88 would copy it from B5+$24c0)."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from sprites import *

dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
b5 = bytes(dat[132566:132566 + 30000])
which = sys.argv[1] if len(sys.argv) > 1 else 'all'
trials = int(sys.argv[2]) if len(sys.argv) > 2 else 20
random.seed(21)
cd = CallDiff(); R = cd.ram
back = struct.unpack_from('>I', R, A4 - 78)[0]
def eq(live, mine): return sum(1 for a, b in zip(live, mine) if a == b), len(mine)

if which in ('all', 'tile'):       # $14262(tile, x(group-byte offset/4?), y): dst -78(A4) and stash
    ok = n = 0
    stash = struct.unpack_from('>I', R, A4 - 86)[0]
    for t in range(trials):
        tile = random.randrange(22); xw = random.randrange(0, 40); y = random.randrange(0, 24)   # x arg * 4 = byte offset, y arg * $500
        oc, ch, d = cd.call(0x14262, struct.pack('>HHH', tile, xw, y))
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch); lives = cd.apply(R[stash:stash + 32000], stash, ch)
        mine = bytearray(R[back:back + 32000]); ms = bytearray(R[stash:stash + 32000])
        off = xw * 4 + y * 0x500
        for r in range(8):
            row = b5[0xCC0 + tile * 64 + r * 8:0xCC0 + tile * 64 + r * 8 + 8]
            mine[off + r * 160:off + r * 160 + 8] = row; ms[off + r * 160:off + r * 160 + 8] = row
        a, b = eq(live, mine); a2, b2 = eq(lives, ms); ok += a + a2; n += b + b2
    print('tile $14262 (screen+stash): %d / %d bytes equal over %d trials' % (ok, n, trials))
if which in ('all', 'small'):      # $1416c(frame, x, y): 16x8 masked, plane-3-only transparent, permuted planes, sign-extended words
    ok = n = 0
    for t in range(trials):
        fr = random.randrange(36); x = random.randrange(0, 300); y = random.randrange(0, 190)
        oc, ch, d = cd.call(0x1416C, struct.pack('>Hhh', fr, x, y))
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch); mine = bytearray(R[back:back + 32000])
        nsh = ((~x) & 15) + 1
        base0 = ((x & 0xFFF0) >> 1) + y * 160
        for r in range(8):
            w = struct.unpack_from('>4H', b5, 0x1BC0 + fr * 64 + r * 8)
            V = [rol32(sext16(w[i]), nsh) for i in range(4)]
            D5 = (~V[3] & M32) | V[0] | V[1] | V[2]
            V[3] &= D5
            K = ~D5 & M32
            vh = (V[0] >> 16, V[2] >> 16, V[1] >> 16, V[3] >> 16); vl = (V[0] & 0xFFFF, V[2] & 0xFFFF, V[1] & 0xFFFF, V[3] & 0xFFFF)
            put_group(mine, base0 + r * 160, (K >> 16, K & 0xFFFF), vh, vl)
        a, b = eq(live, mine); ok += a; n += b
    print('16x8 sprite $1416c: %d / %d screen bytes equal over %d trials' % (ok, n, trials))
if which in ('all', 'heli'):       # $13cbc(slot, x, y)
    ok = n = 0
    wk = struct.unpack_from('>I', R, A4 - 1906)[0]
    for t in range(trials):
        slot = random.randrange(4); fr = random.randrange(8); x = random.randrange(0, 290); y = random.randrange(-10, 190)
        cd.poke(wk + slot * 720, b5[0x24C0 + fr * 720:0x24C0 + fr * 720 + 720])
        oc, ch, d = cd.call(0x13CBC, struct.pack('>Hhh', slot, x, y))
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch); mine = bytearray(R[back:back + 32000])
        src = slot * 720; rows = 36; y0 = y; skip = 0
        if y < 0: skip = -y; rows -= skip; y0 = 0
        elif y >= 0xA5: rows -= (y - 0xA4)
        xb = (x & 0xFFF0) >> 1
        rr = []
        for r in range(skip, skip + rows):
            L = struct.unpack_from('>10H', b5, 0x24C0 + fr * 720 + r * 20)
            rr.append(([L[0:4], L[4:8]], [L[8], L[9]]))
        blit_rows_masked_groups(mine, xb, y0, rr, 2)
        a, b = eq(live, mine); ok += a; n += b
    print('helicopter $13cbc: %d / %d screen bytes equal over %d trials' % (ok, n, trials))
if which in ('all', 'puff'):       # $143ca(slot): frame = -4614(A4)[slot] (x32 B at B5+$1240), position words at -4598(A4)+slot*4 (x, y)
    ok = n = 0
    for t in range(trials):
        slot = random.randrange(8); frame = random.randrange(44); x = random.randrange(1, 312); y = random.randrange(0, 190)
        cd.poke_word(A4 - 4614 + 2 * slot, frame); cd.poke_word(A4 - 4598 + 4 * slot, x); cd.poke_word(A4 - 4598 + 4 * slot + 2, y)
        oc, ch, d = cd.call(0x143CA, struct.pack('>H', slot))
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch); mine = bytearray(R[back:back + 32000])
        off = (((x >> 1) & 0xFFF8) + ((x >> 3) & 1)) + y * 160
        for r in range(8):
            pl = b5[0x1240 + frame * 32 + r * 4:0x1240 + frame * 32 + r * 4 + 4]
            opaque = ((~pl[3]) | pl[0] | pl[1] | pl[2]) & 0xFF
            p3 = pl[3] & opaque
            keep = (~opaque) & 0xFF
            for p, v in enumerate((pl[0], pl[1], pl[2], p3)):
                o = off + r * 160 + 2 * p
                if 0 <= o < 32000: mine[o] = (mine[o] & keep) | v
        a, b = eq(live, mine); ok += a; n += b
    print('particle $143ca: %d / %d screen bytes equal over %d trials' % (ok, n, trials))

img = open(os.path.join(sscfg.WORK, 'ss.img'), 'rb').read()
PANEL_OFF = struct.unpack_from('>3H', img, 0x14530 - 0xA304)
ICON_OFF = struct.unpack_from('>4H', img, 0x145DE - 0xA304)
if which in ('all', 'gauge'):      # $144ca(dst, panel): HUD panel caption strip 112x6 (BLUE CAR / RED CAR / YELLOW CAR / DRONE + wrench + LAP), frame +3 when -3914[panel] != 0
    ok = n = 0
    for t in range(trials):
        panel = random.randrange(3); drone = random.randrange(2)
        cd.poke_word(A4 - 3914 + 2 * panel, drone)
        oc, ch, d = cd.call(0x144CA, struct.pack('>IH', back, panel))
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch); mine = bytearray(R[back:back + 32000])
        fr = panel + (3 if drone else 0)
        for r in range(6):
            for g in range(7):
                o = PANEL_OFF[panel] + r * 160 + g * 8
                w0, w1, w2, w3 = struct.unpack_from('>4H', b5, 0x6720 + fr * 336 + r * 56 + g * 8)
                opaque = (w0 | w1 | w2 | (~w3 & 0xFFFF)) & 0xFFFF
                w3 &= opaque; keep = ~opaque & 0xFFFF
                for p, v in enumerate((w0, w1, w2, w3)):
                    cur = (mine[o + 2 * p] << 8) | mine[o + 2 * p + 1]
                    cur = (cur & keep) | v
                    mine[o + 2 * p] = cur >> 8; mine[o + 2 * p + 1] = cur & 255
        a, b = eq(live, mine); ok += a; n += b
    print('HUD caption strip $144ca: %d / %d screen bytes equal over %d trials' % (ok, n, trials))
if which in ('all', 'icon'):       # $1453a(dst, car): wrench-count digit icon 16x6 (human cars 0..2 only), background from the strip at -4944(A4)
    ok = n = 0
    stash = struct.unpack_from('>I', R, A4 - 86)[0]; bgs = struct.unpack_from('>I', R, A4 - 4944)[0]
    for t in range(trials):
        car = random.randrange(3); cnt = random.randrange(14)
        cd.poke_word(A4 - 3914 + 2 * car, 0); cd.poke_word(A4 - 3954 + 2 * car, cnt)
        bgdata = bytes(random.randrange(256) for _ in range(ICON_OFF[car] + 6 * 160 + 16))
        cd.poke(bgs, bgdata)
        oc, ch, d = cd.call(0x1453A, struct.pack('>IH', back, car))
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch); lives = cd.apply(R[stash:stash + 32000], stash, ch)
        mine = bytearray(R[back:back + 32000]); ms = bytearray(R[stash:stash + 32000])
        ic = min(cnt, 9)
        for r in range(6):
            o = ICON_OFF[car] + r * 160
            w0, w1, w2, w3 = struct.unpack_from('>4H', b5, 0x6F00 + ic * 48 + r * 8)
            opaque = (w0 | w1 | w2 | (~w3 & 0xFFFF)) & 0xFFFF
            w3 &= opaque; keep = ~opaque & 0xFFFF
            bgw = struct.unpack_from('>4H', R, bgs + o)
            out = [(bgw[0] & keep) | w0, (bgw[1] & keep) | w1, (bgw[2] & keep) | w2, (bgw[3] & keep) | w3]
            for p in range(4):
                struct.pack_into('>H', mine, o + 2 * p, out[p]); struct.pack_into('>H', ms, o + 2 * p, out[p])
        a, b = eq(live, mine); a2, b2 = eq(lives, ms); ok += a + a2; n += b + b2
    print('HUD icon $1453a (screen+stash): %d / %d bytes equal over %d trials' % (ok, n, trials))

cd.close()
