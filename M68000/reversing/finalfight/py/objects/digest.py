#!/usr/bin/env python3
"""digest.py : per pool 8 kind, from the linear listing of its handler range: the state dispatch width, A5 words read or written (other than the frame counter 167 and
the camera 1042/1046), the calls it makes (jsr/bsr/jmp targets outside its own range), the gfx RAM / absolute addresses it uses, the sound cue ids passed to $9e4 (move.w #n,D0 ...),
and the pool allocators it calls. A first-pass map for reading, not a proof."""
import os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
_rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
roots = [int.from_bytes(_rom[0x5872 + 4 * i:0x5872 + 4 * i + 4], 'big') for i in range(60)]
roots.append(0x21e00)
py = sys.executable
SND = re.compile(r'move\.w #\$([0-9a-f]+),D0')
for k in range(60):
    lo, hi = roots[k], roots[k + 1]
    txt = subprocess.run([py, os.path.join(here, 'lst.py'), '%x' % lo, '%x' % hi], capture_output=True, text=True).stdout
    lines = [l for l in txt.splitlines() if l.startswith('  $')]
    a5 = {}; calls = {}; absr = set(); snd = []; alloc = []
    prev = None
    for l in lines:
        ins = l.split(': ', 1)[1]
        for m in re.finditer(r'(-?\d+)\(A5\)', ins):
            o = int(m.group(1))
            if o in (167, 1042, 1046): continue
            a5[o] = a5.get(o, 0) + 1
        m = re.match(r'(jsr|bsr|jmp|bra) \$([0-9a-f]+)(?:\.w|\.l)?$', ins)
        if m:
            t = int(m.group(2), 16)
            if t < lo or t >= hi:
                calls[t] = calls.get(t, 0) + 1
                if t in (0x3892, 0x38ce, 0x390a, 0x3946, 0x3982, 0x39be, 0x39fa, 0x3a52, 0x3a96): alloc.append('%x' % t)
                if t == 0x9e4 and prev:
                    mm = SND.match(prev)
                    if mm: snd.append(mm.group(1))
        for m in re.finditer(r'\$(9[0-9a-f]{5})\.l', ins): absr.add(m.group(1))
        prev = ins
    print('kind $%02x %06x..%06x (%d bytes, %d insns)' % (k, lo, hi, hi - lo, len(lines)))
    print('   A5: ' + ' '.join('%d%s' % (o, '' if n == 1 else 'x%d' % n) for o, n in sorted(a5.items())))
    print('   calls: ' + ' '.join('%x%s' % (t, '' if n == 1 else 'x%d' % n) for t, n in sorted(calls.items())))
    if absr: print('   abs: ' + ' '.join(sorted(absr)))
    if snd: print('   sounds via $9e4: ' + ' '.join(snd))
