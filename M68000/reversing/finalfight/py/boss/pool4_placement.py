"""placement.py: list the placement-record entries ($6026 state tables $636e init, $6346 per-area) whose byte 6 (pool type) is given (default 2 = tag 4, $390a).
Entry (14 bytes, read at $61a8): +0 trigger.w, +2 x.w, +4 y.w, +6 type.b, +7 kind.b (-> +19), +8 w (-> +20/+21), +10 b -> +54, +11 b -> +98, +12 b -> +96."""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
l = lambda a: int.from_bytes(rom[a:a+4], 'big')
sw = lambda a: w(a) - 65536 if w(a) & 0x8000 else w(a)
want = int(sys.argv[1]) if len(sys.argv) > 1 else 2
for name, base in (('init $636e', 0x636e), ('area $6346', 0x6346)):
    for s in range(8):
        p = l(base + 4*s); n = w(p)//2
        for ar in range(n):
            a = p + w(p + 2*ar)
            if name.startswith('area'):
                mode = w(a); a += 2
            else: mode = None
            seen = 0
            while seen < 200:
                seen += 1
                t = sw(a)
                if t < 0:
                    if w(a) == 0x8000 and mode is not None: mode = w(a+2); a += 4; continue
                    break
                if rom[a+6] == want or want < 0:
                    print('%s stage %d area %d @%x mode %s trig=%d x=%d y=%d type=%d kind=%d w8=%04x b10=%02x b11=%02x b12=%02x b13=%02x' % (name, s, ar, a, mode, t, sw(a+2), sw(a+4), rom[a+6], rom[a+7], w(a+8), rom[a+10], rom[a+11], rom[a+12], rom[a+13]))
                a += 14
