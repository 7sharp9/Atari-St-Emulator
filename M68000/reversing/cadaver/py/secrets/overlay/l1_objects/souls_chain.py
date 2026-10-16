"""souls_chain.py [case ...]: the SOULS RETURNED chain of level 1 through the real consumer $00fdbc, entries injected at the write pointer
304(A5) of level1_loaded.snap (producer shapes from secrets.md: event 18 = [18][front object][held item id], event 4 = [4][mover][target id]).
Cases (one fresh REPL each):
  chain    : [18][611][227] (ashes on the urn), then [4][611][413] (urn lands on Capt. Axel), then [4][731][413] (emerald lands on Axel)
  urn_cold : [4][611][413] with 611's bit 0 clear (the ELSE branch)
  gem_first: [4][731][413] with 611's bit 1 clear (IF fails, block kept)
  wrong    : [18][611][228] (a different item: gate rejects)
  urn426   : [18][426][227] then [4][426][417] (the second urn, room 29: SHOW 434)
Prints the consumer hits ($fe24 match, $fe36 gate accepted, $fe5a verb) per push and the state of every object the blocks name.
Run from M68000/: M68000_ROOT=$PWD ATARI_NOTRACE=1 .venv/bin/python reversing/cadaver/py/secrets/overlay/l1_objects/souls_chain.py [case ...]"""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.getcwd()
OUTDIR = ROOT + '/scratchpad/cadaver/l1_objects'; os.makedirs(OUTDIR, exist_ok=True); os.environ['OUTDIR'] = OUTDIR
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/events')
from probe import *          # HH, A5, live_res
from consumer_bits import push
import repl as _repl
SNAP1 = ROOT + '/scratchpad/cadaver/level1_loaded.snap'
SITES = {0xfe24: 'match', 0xfe36: 'gate_ok', 0xfe5a: 'verb'}
VERBS = (0, 1, 17, 20, 26, 28, 29, 32, 85)   # DELETE, SHOW, state0 of obj, state1 of actor, HIDE, MESSAGE, spent, state0 of actor, XP
WATCH = [611, 227, 413, 414, 415, 416, 417, 418, 785, 786, 787, 788, 789, 419, 684, 731, 426, 434]

def state(h):
    out = {}
    for o in WATCH:
        a = live_res(h, 6, o)
        if a is None: out[o] = 'GONE'; continue
        out[o] = 'xyz=%s b3=%02x room=%d' % (tuple(h.r.mem(a, 3)), h.r.b(a + 3), h.r.b(a + 10))
    out['XP'] = h.r.l(A5 + 1192)
    out['type8n'] = h.r.b(A5 + 2438)
    return out

def show(tag, before, after):
    print('   ', tag)
    for k in before:
        mark = '' if before[k] == after[k] else '   <-- changed'
        if mark or k == 'XP': print('      %-6s %s -> %s%s' % (k, before[k], after[k], mark))

def step(h, ev, oid, word, steps=3000000):
    b = state(h)
    push(h, [(ev, live_res(h, 6, oid), word)])
    vs = {h.tab[v]: 'v%d' % v for v in VERBS}
    hh = h.r.hits(steps, *SITES, *vs)
    a = state(h)
    got = {SITES[x]: hh.get(x, 0) for x in SITES}
    got.update({vs[x]: hh.get(x, 0) for x in vs})
    show('[%d][obj %d][word %d] %s' % (ev, oid, word, got), b, a)
    return got, b, a

CASES = {
    'chain': [(18, 611, 227), (4, 611, 413), (4, 731, 413), (4, 731, 413)],
    'urn_cold': [(4, 611, 413)],
    'gem_first': [(4, 731, 413)],
    'wrong': [(18, 611, 228)],
    'urn426': [(4, 426, 417), (18, 426, 227), (4, 426, 417)],
}
if __name__ == '__main__':
    for c in (sys.argv[1:] or list(CASES)):
        print('== case', c)
        h = HH.H(SNAP1)
        for ev, oid, word in CASES[c]: step(h, ev, oid, word)
        h.close()
