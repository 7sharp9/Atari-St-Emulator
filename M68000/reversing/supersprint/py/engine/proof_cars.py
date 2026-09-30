"""Differential test of the car blitter transcription (cars.py car_blit) against the live routine $14a4a via callcap.

Each trial pokes one car's x, y, heading, sprite-variant word (-3914) and flag word (-3826), calls $14a4a (arg = car index), and
compares the resulting bytes of the destination screen (-78(A4)) in the sprite's 32x12 footprint with the Python blit applied to
the pre-call screen bytes.  Reports byte-match counts per trial and in total."""
import sys, os, json, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from repl import Repl
from cars import car_blit

snap = sscfg.SNAP_RACE
R = Ram(snap)
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
blk = dat[19798:19798 + 32768]
scr0 = bytes(R.b[R.g(-78):R.g(-78) + 32000])
mono = R.g(-94)
def layer(off_extra):
    def f(mo):
        a = mono + off_extra + mo
        return struct.unpack_from('>I', R.b, a)[0]
    return f
layer0, layer2 = layer(0), layer(16000)
random.seed(7)
tmp = os.path.join(OUT, 'callcap_car.json')
r = Repl(snap)
o, regs = r.cmd('m 0 4')   # Repl.cmd appends its own 'r'; a bare cmd('r') would desync the pipe
sp0 = regs['A7']
tot_ok = tot = 0
trials = int(sys.argv[1]) if len(sys.argv) > 1 else 40
for t in range(trials):
    car = random.randrange(4)
    x = random.randrange(0, 300); y = random.randrange(31, 186)
    head = random.randrange(16)
    var = random.choice([0, 1]); flag = random.choice([0, 1, 0x400, 0x401])
    # word arrays: poke one longword each (car pairs share a longword; write the pair with the other car's current value kept)
    def poke_word(base_off, idx, val):
        a = A4 + base_off + 2 * idx
        a4 = a & ~3
        cur = bytearray(R.b[a4:a4 + 4])
        cur[a - a4:a - a4 + 2] = struct.pack('>H', val & 0xFFFF)
        r.cmd('w %x %02x%02x%02x%02x' % (a4, *cur))
    for off, val in ((-3690, x), (-3698, y), (-3706, head), (-3914, var), (-3826, flag)):
        poke_word(off, car, val)
    r.cmd('w %x %04x0000' % (sp0, car))
    cmdline = 'callcap 14a4a 200000 %s' % tmp
    o, _ = r.cmd(cmdline)
    if not os.path.exists(tmp):
        print("NO JSON; callcap output:", o[:6]); raise SystemExit(1)
    d = json.load(open(tmp))
    assert d['outcome'] == 'returned', d['outcome']
    live = bytearray(scr0)
    for ad, x0, x1 in d['mem']:
        base = R.g(-78)
        if base <= ad < base + 32000:
            live[ad - base] = x1
    mine = bytearray(scr0)
    fl = ((0x80 if flag & 0x400 else 0) | (flag & 1))
    car_blit(mine, blk, car * 16 + head + (64 if var else 0), x, y, layer0, layer2, fl)
    # footprint bytes
    ok = n = 0
    for r_ in range(12):
        for b in range(16):
            o_ = ((x & 0xFFF0) >> 1) + (y + r_) * 160 + b
            n += 1; ok += (live[o_] == mine[o_])
    changed = sum(1 for a, b in zip(live, scr0) if a != b)
    tot_ok += ok; tot += n
    print('trial %2d car%d x=%3d y=%3d h=%2d var=%d flag=%03x: footprint bytes equal %d/%d (game changed %d bytes)' % (t, car, x, y, head, var, flag, ok, n, changed))
r.close()
print('TOTAL footprint bytes equal: %d / %d' % (tot_ok, tot))
