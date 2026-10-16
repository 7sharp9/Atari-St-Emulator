"""items_chain.py [case ...]: the other unread level-1 blocks through the real consumer, entries injected at 304(A5) of level1_loaded.snap
(shapes: event 18 = [18][front object][held item id], event 5 = [5][object][0]).  Cases (one fresh REPL each):
  scroll   : [18][casket 513][378] (scroll into Rogal's casket), [18][strong box 379][513] (casket into the box), the same again (spent)
  box_cold : [18][379][513] with 513's bit 0 clear (ELSE: THE RECHARGE DIDNT SEEM TO WORK)
  chest129 : [5][chest 129][0] (room 32): MOVE shuriken 673 (room 84) to the chest
  casket329: [5][casket 329][0] (room 8): MOVE STAMINA 475 (room 84) to the casket
  lever237 : [5][lever 237][0] (room 65): SHOW STAMINA 535 and clear 24 maze flags
Run from M68000/: M68000_ROOT=$PWD ATARI_NOTRACE=1 .venv/bin/python reversing/cadaver/py/secrets/overlay/l1_objects/items_chain.py [case ...]"""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.getcwd()
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/l1_objects')
import souls_chain as S
from souls_chain import HH, A5, live_res, SNAP1
S.VERBS = (1, 10, 16, 17, 20, 28, 29, 32, 65, 73)
S.WATCH = [378, 513, 379, 129, 673, 329, 475, 237, 535]
_state = S.state
FLAGS = [0x45 + i for i in range(24)]
def state(h):
    out = _state(h)
    for o in (378, 673, 475, 535):
        a = live_res(h, 6, o)
        if a: out['blk%d' % o] = h.r.mem(a + h.r.b(a + 12), 4).hex(' ')
    out['cur_room'] = h.r.w(A5 + 1166)
    out['maze flags $45-$5c'] = ' '.join('%04x' % h.r.w(live_res(h, 4, f) + 2) for f in FLAGS)
    return out
S.state = state
CASES = {
    'scroll': [(18, 513, 378), (18, 379, 513), (18, 379, 513)],
    'box_cold': [(18, 379, 513)],
    'chest129': [(5, 129, 0)],
    'casket329': [(5, 329, 0)],
    'lever237': [(5, 237, 0)],
}
for c in (sys.argv[1:] or list(CASES)):
    print('== case', c)
    h = HH.H(SNAP1)
    for ev, oid, word in CASES[c]: S.step(h, ev, oid, word)
    h.close()
