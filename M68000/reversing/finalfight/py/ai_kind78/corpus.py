#!/usr/bin/env python3
"""corpus.py <n>...: for runs out/c_<n>.log/.hits compare, per handler entry, the live execution count (MAME breakpoint) with the
number of frames whose dispatch-time state tuple (the end-of-frame tuple of the previous frame) selects that handler.
The record is followed from its first frame; a record that disappears (state 6 dispatched -> freed) ends the run."""
import os, sys, re, importlib.util, io, contextlib, collections
OUT = os.environ.get('FF_E_OUT') or os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..')), 'scratchpad/finalfight/p3/e/out')
def load(log):
    sys.argv = ['anal', log]
    spec = importlib.util.spec_from_file_location('anal', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anal.py')); a = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(a)
    return a
MODE = {0: 0x3c540, 2: 0x3c62a, 4: 0x3c716, 6: 0x3c7aa, 8: 0x3cc8e, 10: 0x3cd3e}
STEP = {(0, 0): 0x3c556, (0, 2): 0x3c580, (0, 4): 0x3c5c8, (2, 0): 0x3c640, (2, 2): 0x3c65a, (2, 4): 0x3c67c, (4, 0): 0x3c72c, (4, 2): 0x3c758, (4, 4): 0x3c784,
        (6, 0): 0x3c7ba, (6, 2): 0x3c7d6, (8, 0): 0x3cca4, (8, 2): 0x3ccc0, (8, 4): 0x3cce2, (10, 0): 0x3cd54, (10, 2): 0x3cd80, (10, 4): 0x3ce42, (10, 6): 0x3ce82, (10, 8): 0x3cec2}
DYING = {(0,): 0x3cf10, (2,): 0x3d058}
DSTEP = {0: 0x3cf3c, 2: 0x3cf82, 4: 0x3cff8, 6: 0x3d038}
def expected(tuples):
    """tuples: list of dispatch-time (s2,s3,s4,s5) per frame in which the record ran"""
    c = collections.Counter()
    for s2, s3, s4, s5, held in tuples:
        if s2 == 0: c[0x3c4a2] += 1
        elif s2 == 2:
            c[0x3c504] += 1
            if held: continue
            if s3 in MODE: c[MODE[s3]] += 1
            if (s3, s4) in STEP: c[STEP[(s3, s4)]] += 1
        elif s2 == 4:
            c[0x3cee2] += 1
            if s3 == 0:
                c[0x3cf10] += 1; c[DSTEP[s4]] += 1
            elif s3 == 2:
                c[0x3d058] += 1
        elif s2 == 6: c[0x3d0a0] += 1
    return c
def tuples_of(a, kind=8):
    out = []; prev = None
    rows = []
    for fr in a.frames:
        recs = [b for b in fr['recs'].values() if b[19] == kind]
        rows.append((fr['rel'], (recs[0][2], recs[0][3], recs[0][4], recs[0][5]) if recs else None))
    seen = False
    for i, (rel, t) in enumerate(rows):
        if t is None: continue
        # dispatch tuple of the frame that produced t is the previous frame's end tuple; the frame the record was created the end-of-frame
        # tuple (0,0,0,0) is the spawn poke itself (the handler has not run yet)
    # dispatch-time tuples: for each frame where record exists, previous end tuple (or the spawn tuple)
    res = []
    for i in range(1, len(rows)):
        rel, t = rows[i]; prev = rows[i-1][1]
        if prev is not None:
            res.append(prev)           # the handler ran in this frame with the previous end tuple (even if the record then vanished)
    return res
if __name__ == '__main__':
    tot = collections.Counter(); hit = collections.Counter(); runs = 0
    for n in sys.argv[1:]:
        pre = '' if n[:2] in ('c_','g_','f_') else 'c_'
        a = load(os.path.join(OUT, '%s%s.log' % (pre, n)))
        # frames: the record is logged only while its +0 != 0; the last frame (freed by $3878) has t None, but the handler ran: handled by prev
        rows = []
        for fr in a.frames:
            recs = [b for b in fr['recs'].values() if b[19] == 8]
            rows.append((fr['rel'], (recs[0][2], recs[0][3], recs[0][4], recs[0][5], recs[0][66]) if recs else None))
        # include the frame after the last logged one when the final tuple was state 6 (handler 3d0a0 ran and freed it)
        tl = []
        for i in range(1, len(rows)):
            p, c = rows[i-1][1], rows[i][1]
            if p is None: continue
            # held frames (66(A6) != 0 before or after the dispatch, i.e. the seize frame too) run $3d224, not the mode handlers
            held = p[4] != 0 or (c is not None and c[4] != 0)
            tl.append(p[:4] + (held,))
        e = expected(tl); tot.update(e)
        h = {}
        for l in open(os.path.join(OUT, '%s%s.hits' % (pre, n))):
            ad, c = l.split(); h[int(ad, 16)] = int(c)
        for k, v in h.items(): hit[k] += v
        runs += 1
    modelled = set(MODE.values()) | set(STEP.values()) | set(DSTEP.values()) | {0x3c4a2, 0x3c504, 0x3cee2, 0x3cf10, 0x3d058, 0x3d0a0}
    ok = bad = 0
    for k in sorted(set(tot) | set(k for k, v in hit.items() if v)):
        if k not in modelled:
            print('--   %06x live hits=%d (helper or sub-step with no state-log model)' % (k, hit[k])); continue
        flag = 'OK ' if tot[k] == hit[k] else 'DIFF'
        if tot[k] == hit[k]: ok += 1
        else: bad += 1
        print('%s %06x expected(from state log)=%d live hits=%d' % (flag, k, tot[k], hit[k]))
    print('runs', runs, 'modelled entries match', ok, 'mismatch', bad)
