"""place_lib.py: helpers to drive verb 41 PLACE (and 36/44) inside the live game on a throwaway REPL fork and trace the free-space search $008e38
(candidate positions at $008f1c).  The placement array (56(A5), 70-byte entries [x_hi y_hi x_lo y_lo z_hi z_lo ...][ptr at +10]) is the collision set."""
from lib2 import *
import re

PCAND, PSEARCH, PVERB41 = 0x8f1c, 0x8e38, 0x10aaa
REG = re.compile(r'D(\d):([0-9a-f]{8})')

def regs(out):
    d = {}
    for l in out:
        for m in REG.finditer(l): d['D' + m.group(1)] = int(m.group(2), 16)
        for m in re.finditer(r'A(\d):([0-9a-f]{8})', l): d['A' + m.group(1)] = int(m.group(2), 16)
    return d

def sb(v): return v - 256 if v & 128 else v

def crowd(h, blockers, keep_hero=False, subject=60):
    """mark every placement entry deleted (first long = ffffffff) and install blockers [(x_lo, y_lo, x_hi, y_hi, z_lo, z_hi)] in the first entries other than the
    subject's own (the verb removes the subject's entry first, and the search skips an entry whose pointer at +10 is the subject)"""
    r = h.r; p = r.l(A5 + 56); n = r.w(A5 + 1152); rec = h.obj(subject)
    slots = []
    for i in range(n):
        ptr = int.from_bytes(r.mem(p + 70 * i + 10, 4), 'big')
        if i == 0 and keep_hero: continue
        h.poke(p + 70 * i, [0xff] * 4)
        if ptr != rec and not (i == 0): slots.append(i)
    assert len(blockers) <= len(slots), (len(blockers), len(slots))
    for k, (xl, yl, xh, yh, zl, zh) in enumerate(blockers):
        h.poke(p + 70 * slots[k], [xh, yh, xl, yl, zh, zl])
    return p, n

def drive41(h, script, trace=True, maxcand=400, owner=2):
    """inject [script] as object `owner`'s event-5 body, run to the entry of verb 41, then trace the search candidates.
    returns dict(cands=[(x,y,z,D6)], entry=regs at $008e38, outcome)"""
    r = h.r; h.owner = owner
    set_body(h, script); inject5(h)
    out = r.cmd('bp %x 700000' % PVERB41)
    res = dict(stopped41='breakpoint' in out[0] and 'hit' in out[0], cands=[], entry=None, outcome=None)
    if not res['stopped41']: res['outcome'] = 'verb 41 not reached: ' + out[0]; return res
    # run to the search (only if the same-room branch is taken)
    out = r.cmd('bp %x 20000' % PSEARCH)
    if 'hit' not in out[0].split('(')[0] + out[0]: pass
    if 'gave up' in out[0]: res['outcome'] = 'no search (another-room branch)'; return res
    res['entry'] = regs(out)
    while len(res['cands']) < maxcand:
        out = r.cmd('bp %x 5000' % PCAND)
        if 'gave up' in out[0]:
            res['outcome'] = 'search ended'; res['last'] = out[0]; res['pc'] = int(re.search(r'still at \$([0-9a-f]+)', out[0]).group(1), 16) if re.search(r'still at \$([0-9a-f]+)', out[0]) else None
            break
        g = regs(out)
        res['cands'].append((g['D0'] & 255, g['D1'] & 255, g['D2'] & 0xffff, g['D6'] & 0xff, g['D3'] & 0xffff, g['D4'] & 0xffff, g['D5'] & 0xffff))
    return res
