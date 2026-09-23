"""livecheck.py SITE SNAP NSTEPS OUT.jsonl [TAG]

Live differential check of one AI call site over a natural run. From SNAP, run NSTEPS emulator
steps; every time PC reaches the call site's `jsr` (arguments already pushed at A7):
  - `snap` the machine (pre-state for the model),
  - `callcap <routine>` on the real code from that exact state (full memory delta + regs, restored),
  - apply the Python model to the snapshot RAM and compare the non-stack memory delta
    (and D0 where the caller uses it).
Then let the real call run and continue. Writes one JSON line per call:
  {step, frame, args, match, real_cmd, model_cmd, ...}

SITE: think  $db8c -> $13eda      powers $dbbc -> $13a44
      flat1  $e534 -> $135fc      flat2  $e580 -> $135fc      level $ea7a -> $13816
      step1  $ea8a -> $ef4c       step2  $ecf6 -> $ef4c       dir   $ef86 -> $f6b2
For $ef4c only the god-record bytes ($21e0c..$21e67) are compared: the direction routine's result
and god-record effect come from callcaps of the real $f6b2 / $f2f4 from the same state (labelled
'oracle' in the output); the model under test is the $ef4c "lower the burnt field" rule.
"""
import json, os, struct, sys
from aicfg import *
import ai_ref as A
import ai_ext as X
from livelib import Sess

SITES = {'think': (0xdb8c, 0x13eda), 'powers': (0xdbbc, 0x13a44), 'flat1': (0xe534, 0x135fc),
         'flat2': (0xe580, 0x135fc), 'level': (0xea7a, 0x13816), 'step1': (0xea8a, 0xef4c),
         'step2': (0xecf6, 0xef4c), 'dir': (0xef86, 0xf6b2)}
GOD0, GOD1 = 0x21e0c, 0x21e0c + 2 * 0x2e


def real_delta(cc, sp0, lo=None, hi=None):
    d = {}
    for a, _x0, x1 in cc['mem']:
        if sp0 - 0x1000 <= a < sp0 + 8:
            continue
        if lo is not None and not (lo <= a < hi):
            continue
        d[a] = x1
    return d


def model_delta(pre, mm, lo=None, hi=None):
    lo = 0 if lo is None else lo
    hi = len(mm) if hi is None else hi
    out = {}
    for i in range(lo, hi, 4096):
        j = min(hi, i + 4096)
        if mm[i:j] != pre[i:j]:
            out.update({a: mm[a] for a in range(i, j) if mm[a] != pre[a]})
    return out


def cmd_of(delta_img, pre):
    """god-record command bytes after the call, for the side(s) whose +0..+2/+8 changed."""
    out = []
    for s in (0, 1):
        r = A.rec(s)
        if any(a in delta_img for a in (r, r + 1, r + 2, r + 8, r + 9)):
            g = lambda a: delta_img.get(a, pre[a])
            out.append([s, g(r), g(r + 1), g(r + 2), (g(r + 8) << 8) | g(r + 9)])
    return out


def main():
    site, snap, nsteps, outp = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    tag = sys.argv[5] if len(sys.argv) > 5 else site
    pc, routine = SITES[site]
    tmp_snap, tmp_js, tmp_js2 = P('tmp_%s.snap' % tag), P('tmp_%s.json' % tag), P('tmp_%s_2.json' % tag)
    S = Sess(snap)
    fo = open(outp, 'w')
    n = good = 0
    while S.steps < nsteps:
        if not S.until(pc, nsteps - S.steps):
            break
        sp0 = S.regs['A7']
        pre = S.snapram(tmp_snap)
        pre_b = bytes(pre)
        frame = A.rw(pre, A.FRAME)
        cc = S.callcap(routine, tmp_js)
        ok_run = cc['outcome'] == 'returned'
        d0 = cc['regN'][0] & 0xffff
        mm = bytearray(pre)
        rec = {'step': S.steps, 'frame': frame, 'site': site}
        note = None
        if routine in (0x13eda, 0x13a44):
            side = A.rw(pre, sp0); rec['args'] = [side]
            (A.think_13eda if routine == 0x13eda else A.powers_13a44)(mm, side)
            real, model = real_delta(cc, sp0), model_delta(pre_b, mm)
            match = real == model
        elif routine in (0x135fc, 0x13816):
            cell, side = A.rw(pre, sp0), A.rw(pre, sp0 + 2); rec['args'] = [cell, side]
            ret = (A.flatten_135fc if routine == 0x135fc else A.level_13816)(mm, cell, side)
            real, model = real_delta(cc, sp0), model_delta(pre_b, mm)
            match = real == model
            if routine == 0x135fc:
                match = match and (d0 & 0xff) == ret
        elif routine == 0xf6b2:
            wp, idx = A.rl(pre, sp0), A.sw(pre, sp0 + 4); rec['args'] = [wp, idx]
            try:
                ret = X.f6b2(mm, wp, idx); rec['edit'] = X.LAST; rec['dir'] = A.s16(ret)
                real, model = real_delta(cc, sp0), model_delta(pre_b, mm)
                match = real == model and A.s16(d0) == A.s16(ret)
            except X.NotModelled as e:
                note = 'skip: ' + str(e)
                real, model, match = real_delta(cc, sp0, GOD0, GOD1), {}, None
        else:                                               # $ef4c
            wp, idx = A.rl(pre, sp0), A.sw(pre, sp0 + 4); rec['args'] = [wp, idx]
            inner = 0xf6b2 if X.ef4c_uses_f6b2(pre, wp) else 0xf2f4
            cc2 = S.callcap(inner, tmp_js2)
            dirv = cc2['regN'][0] & 0xffff
            for a, _x0, x1 in cc2['mem']:                   # oracle: inner routine's god-rec writes
                if GOD0 <= a < GOD1: mm[a] = x1
            X.ef4c_lower(mm, wp, dirv)
            real, model = real_delta(cc, sp0, GOD0, GOD1), model_delta(pre_b, mm, GOD0, GOD1)
            match = real == model
            rec['inner'] = '%x' % inner; rec['dir'] = A.s16(dirv)
            rec['edit'] = X.LAST
        match = bool(match and ok_run) if match is not None else None
        rec.update(match=match, outcome=cc['outcome'], real_cmd=cmd_of(real, pre_b), model_cmd=cmd_of(model, pre_b))
        if note: rec['note'] = note
        if match is False:
            rec['real'] = {'%x' % a: v for a, v in sorted(real.items())}
            rec['model'] = {'%x' % a: v for a, v in sorted(model.items())}
        fo.write(json.dumps(rec) + '\n'); fo.flush()
        n += 1; good += bool(match)
    S.close()
    print('%s: %d calls, %d match, steps %d' % (site, n, good, S.steps))


if __name__ == '__main__':
    main()
