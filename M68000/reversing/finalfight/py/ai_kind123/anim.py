"""anim.py: decode animation setters and scripts.
 setter ($3b10): D0=index, A1=table; script = A1 + word[A1+2*D0]; 32(A6)=script; 40(A6)=word[script+2] (hi = timer ticks, lo = flag byte 41(A6), bit7 = end of animation);
 36(A6)=frame record = script + word[script] ; record: +0 word, +2..+5 -> 42,43,44,45(A6) (45 = attack box index, 44 = hurt box index), +6 word -> 48(A6).
 $3b3c advances by 4 bytes per step; a negative second word loops: new script pointer = (step+2) + word[step] ... (lea -2(A1,D0.w))."""
import os, sys
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
rw = lambda a: (rom[a] << 8) | rom[a + 1]
rl = lambda a: (rw(a) << 16) | rw(a + 2)
def s16(v): return v - 0x10000 if v >= 0x8000 else v
def script(A1, idx):
    return A1 + rw(A1 + 2 * idx)
def steps(sc, maxn=40):
    """walk the script from its start; returns list of (stepaddr, timer, flag, rec, hurt, atk, w48)"""
    out = []; a = sc; seen = set()
    for _ in range(maxn):
        if a in seen: out.append(('LOOP', a)); break
        seen.add(a)
        D0 = rw(a); B = rw(a + 2)
        rec = a + 2 - 2 + D0 if False else (a + 2) - 2 + D0
        # at $3b10: A1=sc ; D0=(A1)+ ; A1 at sc+2 ; lea -2(A1,D0) = sc+D0
        rec = a + D0
        out.append((a, B >> 8, B & 0xff, rec, rom[rec + 4], rom[rec + 5], rw(rec + 6), rw(rec), rom[rec + 2], rom[rec + 3]))
        if B & 0x8000:
            # loop: $3b50: bpl else lea -2(A1,D0.w),A1 where A1 = step+2, D0 = word(step) -> new script step = step + D0
            tgt = a + D0
            out.append(('LOOPTO', tgt)); break
        if (B & 0xff) & 0x80: out.append(('END',)); break
        a += 4
    return out
def show(A1, idx, tag=''):
    sc = script(A1, idx)
    print('%s script %06x (A1=%06x idx %d)' % (tag, sc, A1, idx))
    for s in steps(sc):
        if s[0] in ('LOOP', 'LOOPTO', 'END'): print('   ', s); continue
        a, t, fl, rec, hu, at, w48, w0, b2, b3 = s
        print('    step %06x timer=%d flag=%02x rec=%06x hurt=%02x atk=%02x w48=%04x rec0=%04x b2/3=%02x/%02x' % (a, t, fl, rec, hu, at, w48, w0, b2, b3))
if __name__ == '__main__':
    A1 = int(sys.argv[1], 16)
    for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 1): show(A1, i)
