"""services_callcap.py: call the export-table services that can be called in isolation (no VBL waits) and print the result
registers/state, to back the names in the report.  Start snapshot scratchpad/cadaver/gameplay_empire.snap.  callcap prints only
changed bytes, so the 'regN' array of the JSON delta is used for result registers (order D0..D7,A0..A7)."""
import sys, json
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
out = 'scratchpad/cadaver/secrets_out/overlay/out/'
r = Repl()
def call(tag, addr, regs='', steps=200000):
    o = r.cmd('callcap %x %d %ssvc.json %s' % (addr, steps, out, regs))
    head = [l for l in o if l.startswith('---')][0]
    d = json.load(open(out + 'svc.json'))
    rn = d['regN']; reg = lambda n: rn[n] & 0xffffffff
    mem = [(a, old, new) for a, old, new in d['mem'] if 0 <= a - A5 < 4000]
    print('%-34s %-9s D0=$%x D1=$%x A0=$%x  A5-changes: %s' % (tag, 'ok' if 'returned' in head else 'NOT RET', reg(0), reg(1), reg(8), ' '.join('+%d:%02x->%02x' % (a - A5, o_, n) for a, o_, n in mem[:10])))
print('HP %s max %s' % (r.mem(a5(1174), 2).hex(), r.mem(a5(2516), 2).hex()))
call('svc 3  HP change D0=-5', 0x10c8c, 'D0=fffffffb')
call('svc 3  HP change D0=+5', 0x10c8c, 'D0=5')
call('svc 3  HP change D0=+200 (clamped)', 0x10c8c, 'D0=c8')
for lo, hi in ((5, 9), (0, 0), (1, 2)): call('svc 16 random(%d..%d)' % (lo, hi), 0x11544, 'D1=%x D2=%x' % (lo, hi))
call('svc 22 register creature D1=194', 0xe13e, 'D1=c2')
call('svc 2  resolve-by-sign D1=60', 0xc542, 'D1=3c')
call('svc 0  resolve type 6 id 60', 0xc5a8, 'D0=6 D1=3c')
call('svc 12 start timer D1=7 D0=9', 0x10d38, 'D1=7 D0=9')
r.close()
