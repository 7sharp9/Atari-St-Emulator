"""census_heli.py [POS ...]: crash car 1 of the live Track-1 race (ss_prep.snap) at a chosen screen position (heli_flows.POS) by
poking the safe-position words -3754/-3762(A4)[1] (1/8 px) and the crash flag -3778(A4)[1] = 1 ($b3fc then starts the pickup
helicopter), then census every call of the small ($13cbc, 8 frames of 720 B at SUPER.DAT+0x205d6+0x24c0) and large ($13d58, 8 frames
of 1040 B at +0x3b40) helicopter blitters: arguments (frame, x, y) at 4(A7)..8(A7).  Prints the frames drawn per blitter and the
SUPER.DAT file-offset range each frame covers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
B5 = 0x205d6
POS = {'left_top': (20, 20), 'left_bot': (20, 180), 'right_top': (290, 20), 'right_bot': (290, 180), 'mid': (160, 100),
       'left_mid': (20, 100), 'right_mid': (290, 100), 'top_mid': (160, 12), 'bot_mid': (160, 188)}

def run(pos, blitter, car=1, maxhits=200, per_hit=400000):
    x, y = POS[pos]
    r = Repl2(sscfg.SNAP_RACE)
    for off, v in ((3754, x * 8), (3762, y * 8), (3778, 1)):
        ad = A4 - off + 2 * car; old = r.mem(ad, 4)
        r.cmd('w %x %04x%s' % (ad, v, old[2:].hex()))
    seen = []
    for _ in range(maxhits):
        o, regs = r.cmd2('bpc %x 1 %d' % (blitter, per_hit))
        if regs['PC'] != blitter: break
        a = r.mem(regs['A7'] + 4, 6)
        seen.append(tuple(int.from_bytes(a[k:k + 2], 'big', signed=True) for k in (0, 2, 4)))
    r.close()
    return seen

if __name__ == '__main__':
    for p in sys.argv[1:] or list(POS):
        for name, bl, off, sz in (('prep $13f88', 0x13f88, None, None), ('small', 0x13cbc, 0x24c0, 720), ('large', 0x13d58, 0x3b40, 1040)):
            s = run(p, bl)
            if bl == 0x13f88:      # arguments (8,10,12)(A6) = (flags, shift, frame): sheet frame = 4*(flags&1) + frame; large sheet if arg0&2
                fr = sorted(set((bool(t[0] & 2), 4 * (t[0] & 1) + t[2]) for t in s))
                print(p, name, 'calls', len(s), '(large?, sheet frame)', fr, 'raw', s, flush=True); continue
            fr = sorted(set(t[0] for t in s))
            print(p, name, 'calls', len(s), 'frames', fr,
                  'file bytes', ['%x-%x' % (B5 + off + f * sz, B5 + off + (f + 1) * sz) for f in fr], flush=True)
