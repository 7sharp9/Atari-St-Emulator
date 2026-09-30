"""Static table of the sound scripts: for every script offset the ops, wait total (sequencer steps = 9 ISR ticks = 37.5 ms), length in bytes,
instruments used, and which trigger routine starts it (live / dead = no caller anywhere).  Also the instruments no live script uses."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
S = dat[198966 + 3684:198966 + 3684 + 10000]
STEP_S = 9 / (2457600 / 50 / 205)
TABLE = [  # offset, trigger, live?
    (0, '$12522 A', 1), (14, '$128e0 H', 1), (28, '$126ae C', 1), (74, '$1294e I', 1), (88, '$1278a E', 1), (166, '$1271c D', 1), (180, '$127f8 F', 1),
    (194, '$129bc J', 0), (208, '$129bc J', 0), (222, '$129bc J', 0), (236, '$12b32 O', 1), (242, '$12a56 K', 1), (272, '$12a8c L', 1), (302, '$12866 G', 1),
    (316, '$125e6 B / $12e30 T', 1), (322, '$12ac2 M', 0), (336, '$12b00 N', 1), (906, '$12d64 Q', 0), (2580, '$12dec S', 1), (3398, '$12c10(0) P', 1),
    (4488, '$12c10(1) P', 1), (5302, '$12c10(2) P', 1), (5916, '$12c10(3) P', 1), (6794, '$12c10(4) P', 1), (7780, '$12da8 R', 1)]


def dump(off):
    p = off; ops = []; wait = 0; insts = set()
    while True:
        op = struct.unpack_from('>h', S, p)[0]; p += 2
        if op < 3:
            a = struct.unpack_from('>h', S, p)[0]; p += 2; ops.append('N%d:i%d' % (op, a)); insts.add(a)
        elif op < 6:
            a = struct.unpack_from('>h', S, p)[0]; p += 2; ops.append('P%d:%d' % (op - 3, a))
        elif op == 6:
            a = struct.unpack_from('>h', S, p)[0]; p += 2; ops.append('W%d' % a); wait += a
        else:
            ops.append('END'); break
    return ops, p, wait, insts


used_live = set(); used_dead = set()
print('%-5s %-22s %-5s %6s %8s %5s  instruments' % ('off', 'trigger', 'live', 'bytes', 'wait', 'sec'))
for off, trig, live in TABLE:
    ops, end, wait, insts = dump(off)
    (used_live if live else used_dead).update(insts)
    print('%-5d %-22s %-5s %6d %8d %5.1f  %s' % (off, trig, 'live' if live else 'DEAD', end - off, wait, wait * STEP_S, sorted(insts)))
print('instruments referenced by live scripts :', sorted(used_live))
print('instruments referenced only by dead scripts:', sorted(used_dead - used_live))
print('instruments referenced by no script (0..34):', sorted(set(range(35)) - used_live - used_dead))
