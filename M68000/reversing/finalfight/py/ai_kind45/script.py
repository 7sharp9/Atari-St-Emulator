"""script.py: decode the stage spawn scripts read by $5aea (state 2 $5b4e, entries spawned by $5e36/$5e84/$5ee6).
Grammar read from the code ($5b12 init, $5b6a modes, $5bde commands, $5c26/$5dfe segment header, $5c46-$5ca0 entries,
$5c68/$5cb6 continuation commands):
  script   = mode.w {cmd | segment}
  mode     = 0..3: the camera coordinate the trigger is compared with ($5b76: 0 camy (stage 3), 1 camx, 2 camy-, 3 camx-)
  cmd      = word with bit 15 set: (w & $fff) 0: next word is a new mode; 2: pause (22(A6)=1); 4: jump to the long at +2
  segment  = trigger.w, header (w16, w12, w18, w_flag, long continuation), entries 16 bytes each until a word with bit 15 set
  entry    = delay.w, track.w, x.w, y.w, tag.b, kind.b, w20.w (+20 high, +21 low), b12 (-> +54), b13 (-> +98), level.b (-> +96), 2p.b
  The word that ends the entry list is the continuation command 0x8000+code ($5c68-$5c7e: 20(A6) = word - $8000, handled at $5cb6).
usage: script.py [set=2] [filter tag:kind]
"""
import sys, os
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def w(a): return int.from_bytes(rom[a:a + 2], 'big')
def sw(a):
    v = w(a); return v - 65536 if v & 0x8000 else v
def l(a): return int.from_bytes(rom[a:a + 4], 'big')
def b(a): return rom[a]
SETS = {1: 0x5f5e, 2: 0x5f7e}
CONT = {0: 'wait-clear+GO', 1: 'next-segment-now', 2: 'stage-end(297)', 3: 'flag291', 4: 'stage-end2', 5: 'pause30'}

def parse(a, seen=None):
    out = []
    mode = w(a); a += 2
    seen = seen or set()
    while a not in seen:
        seen.add(a)
        t = w(a)
        if t & 0x8000:
            c = t & 0xfff
            if c == 0: mode = w(a + 2); out.append(('mode', a, mode)); a += 4
            elif c == 2: out.append(('pause', a)); a += 2
            elif c == 4: out.append(('jump', a, l(a + 2))); a = l(a + 2)
            else: out.append(('cmd?', a, t)); break
            continue
        if t == 0x7fff: out.append(('end-sentinel', a)); break
        seg = {'at': a, 'trigger': t, 'mode': mode}
        h = a + 2
        seg['hdr'] = (w(h), w(h + 2), w(h + 4), w(h + 6), l(h + 8))
        e = h + 12
        ents = []
        while not (w(e) & 0x8000):
            ents.append(dict(addr=e, delay=w(e), track=w(e + 2), x=sw(e + 4), y=sw(e + 6), tag=b(e + 8), kind=b(e + 9), w20=w(e + 10),
                             b12=b(e + 12), b13=b(e + 13), lvl=b(e + 14), p2=b(e + 15)))
            e += 16
        seg['ents'] = ents
        seg['cont'] = w(e) - 0x8000
        seg['cont_at'] = e
        out.append(('seg', seg))
        a = e + 2
        if seg['cont'] in (2, 4): break
    return out

if __name__ == '__main__':
    st = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    flt = sys.argv[2] if len(sys.argv) > 2 else None
    base = SETS[st]
    for si in range(8):
        p = l(base + 4 * si); n = w(p) // 2
        for ai in range(n):
            a = p + w(p + 2 * ai)
            print('== stage %d area %d script %x' % (si, ai, a))
            for it in parse(a):
                if it[0] == 'seg':
                    s = it[1]
                    sel = [e for e in s['ents'] if not flt or ('%x:%x' % (e['tag'], e['kind'])) == flt]
                    if flt and not sel: continue
                    print('  seg @%x trigger %04x mode %d hdr %s cont=%d(%s)' % (s['at'], s['trigger'], s['mode'], s['hdr'][:4], s['cont'], CONT.get(s['cont'])))
                    for e in sel:
                        print('     @%x delay=%d track=%d x=%d y=%d tag=%x kind=%d w20=%04x (+20=%02x +21=%02x) b12=%02x b13=%02x lvl=%02x 2p=%d' % (
                            e['addr'], e['delay'], e['track'], e['x'], e['y'], e['tag'], e['kind'], e['w20'], e['w20'] >> 8, e['w20'] & 255, e['b12'], e['b13'], e['lvl'], e['p2']))
                elif not flt:
                    print('  ', it)
