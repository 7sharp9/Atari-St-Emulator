"""motion.py <ch> : walk speed, jump and special kinematics of a character from the logs a1_ch<ch> (plan a1: no enemies) and walk_ch<ch> (plan walk1), against the ROM tables
(walk steps $c15e/$c19e, jump vx $ac76, special body, the vy/gravity words written at the start of each move)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charlib as C
ch = int(sys.argv[1])
def load(n): return C.load(n)[0]
w = load('walk_ch%d' % ch)
def seg(rows, lo, hi, key='x'):
    a = [r for r in rows if lo <= r['rel'] <= hi]
    return a
# walk1: right 20..80, left 120..180, up 220..280, down 320..380, right+up 420..480, left+down 520..580
def disp(rows, lo, hi, k): return int(rows[hi][k], 16) - int(rows[lo][k], 16)
print(C.NAMES[ch], 'ROM step x %04x y %04x  accumulator threshold %06x  jump vx %04x/%04x' % (C.w(0xc15e + 2 * ch), C.w(0xc19e + 2 * ch), C.walk_threshold(ch), *C.jump_speed(ch)))
by = {r['rel']: r for r in w}
def X(rel): return int(by[rel]['x'], 16)
def G(rel): return int(by[rel]['gy'], 16)
print('walk right  20->80 : dx %d in 60 frames = %.3f px/frame' % (X(80) - X(20), (X(80) - X(20)) / 60.0))
print('walk left  120->180: dx %d = %.3f px/frame' % (X(180) - X(120), (X(180) - X(120)) / 60.0))
print('walk up    220->280: dy %d = %.3f px/frame' % (G(280) - G(220), (G(280) - G(220)) / 60.0))
print('walk down  320->380: dy %d = %.3f px/frame' % (G(380) - G(320), (G(380) - G(320)) / 60.0))
print('diag r+u   420->480: dx %d dy %d' % (X(480) - X(420), G(480) - G(420)))
a = load('a1_ch%d' % ch)
last = None; seq = []
for r in a:
    k = (r['st'], r['sub'])
    if k != last: seq.append((r['rel'], r['sub'], r)); last = k
for rel, sub, r in seq:
    if sub in ('0e', '10', '14', '12'):
        end = next((q['rel'] for q in a if q['rel'] > rel and q['sub'] != sub), a[-1]['rel'])
        rows = [q for q in a if rel <= q['rel'] < end]
        apex = max(int(q['y'], 16) - int(q['gy'], 16) for q in rows)
        print('sub %s rel %4d..%4d (%d frames) apex +%d px  vx %s vy %s  boxes %s' % (sub, rel, end - 1, end - rel, apex, r['vx'], max((q['vy'] for q in rows), key=lambda s: int(s.split('/')[0], 16) if int(s.split('/')[0], 16) < 0x8000 else 0), sorted(set(q['b45'] for q in rows))))
