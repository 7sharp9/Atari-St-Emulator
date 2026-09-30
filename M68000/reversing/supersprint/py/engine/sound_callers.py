"""Who calls each sound-trigger routine: thunk offsets, callers (function containing the call), and the arg pushed just before."""
import sys, os, re, bisect, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
TRIG = {0x12522: 'A dual voice @0', 0x125e6: 'B dual voice @316', 0x126ae: 'C @28 prio<4', 0x1271c: 'D @166 prio<3', 0x1278a: 'E @88 prio<4',
        0x127f8: 'F @180 prio<1', 0x12866: 'G @302 prio<1', 0x128e0: 'H @14 prio<2', 0x1294e: 'I @74 prio<1', 0x129bc: 'J 3-voice @194/208/222',
        0x12a56: 'K @242', 0x12a8c: 'L @272', 0x12ac2: 'M ch1 @322', 0x12b00: 'N @336', 0x12b32: 'O @236', 0x12c10: 'P tune n',
        0x12d64: 'Q @906', 0x12da8: 'R @7780', 0x12dec: 'S @2580', 0x12e30: 'T @316', 0x12bb4: 'fadeout', 0x12bdc: 'isidle', 0x12450: 'engine pitch',
        0x12b84: 'noise=1f', 0x12b9c: 'noise=5'}
funcs = []
for l in open(os.path.join(sscfg.WORK, 'ss.c')):
    m = re.match(r'// ==== ([0-9a-f]{8}) (\S+)', l)
    if m: funcs.append((int(m.group(1), 16), m.group(2)))
funcs.sort(); starts = [f[0] for f in funcs]
thunks = {}
for l in open(os.path.join(sscfg.WORK, 'thunks.txt')):
    m = re.match(r'(\d+)\(A5\)\s+\$([0-9a-f]+)', l)
    if m: thunks[int(m.group(1))] = int(m.group(2), 16)
rev = collections.defaultdict(list)
for k, v in thunks.items(): rev[v].append(k)
lines = open(os.path.join(sscfg.WORK, 'ss.asm')).read().split('\n')
calls = collections.defaultdict(list)
for i, l in enumerate(lines):
    m = re.match(r'\s+\$([0-9a-f]{6}): (jsr|bsr) (.*)', l)
    if not m: continue
    a = int(m.group(1), 16); t = m.group(3)
    tgt = None
    mm = re.match(r'(-?\d+)\(A5\)', t)
    if mm and int(mm.group(1)) in thunks: tgt = thunks[int(mm.group(1))]
    mm = re.search(r'== \$([0-9a-f]+)', t)
    if mm: tgt = int(mm.group(1), 16)
    if tgt in TRIG:
        # argument: look back up to 6 lines for a push of a word/imm
        arg = ''
        for j in range(i - 1, max(i - 7, 0), -1):
            if 'move.w' in lines[j] and '-(A7)' in lines[j]:
                arg = lines[j].split(':', 1)[1].strip(); break
        f = starts[bisect.bisect_right(starts, a) - 1]
        calls[tgt].append((a, f, arg))
for t in sorted(TRIG):
    print('$%05x %-28s thunk %s' % (t, TRIG[t], ','.join('%d(A5)' % x for x in rev.get(t, []))))
    for a, f, arg in calls.get(t, []):
        print('     called at $%05x in $%05x   %s' % (a, f, arg))
