"""a3: inject_answers.py -- run the answering blocks of events 1, 3 and 21 through the real consumer with producer-shaped entries (injected: events 3 and 21 have no producer, event 1's entry shape was read from the
producer by ev1_icon10_callcap.py).  Level 0 (gameplay_empire.snap): [1][object 51][word = item id]: gate operand 3 vs body byte 0 of the item (132 READ LANGUAGE = 3 accepts, 371 READ MAGIC = $14 rejects);
[3][object 114][0]: HEALTH -2.  Level 1 (level1_loaded.snap): [21][object 61][0]: GOLD -= $96; [0][object 61][0] for contrast: GOLD += $96.
Prints hits ($fe24 match, $fe36 gate accepted, $fe5a verbs) and the state delta (object 51 body, health, gold)."""
from probe import *
from consumer_bits import push
SITES = {0xfe24: 'match', 0xfe36: 'gate_ok', 0xfe5a: 'verb'}
def run(snap, entries, watch):
    h = HH.H(snap); r = h.r
    before = watch(h)
    push(h, entries(h))
    hh = r.hits(60000, *SITES)
    after = watch(h)
    h.close()
    return {SITES[a]: hh.get(a, 0) for a in SITES}, before, after
L0 = ROOT + '/scratchpad/cadaver/gameplay_empire.snap'; L1 = ROOT + '/scratchpad/cadaver/level1_loaded.snap'
body51 = lambda h: 'record byte +3 = %02x, block-1 event byte +$11 = %02x' % (h.r.b(h.obj(51) + 3), h.r.b(h.obj(51) + 0x11))
for word, label in ((132, 'item 132 (READ LANGUAGE, body byte 0 = 3)'), (371, 'item 371 (READ MAGIC, body byte 0 = $14)')):
    got, b, a = run(L0, lambda h: [(1, h.obj(51), word)], body51)
    print('event 1 -> object 51, word %d %s: %s' % (word, label, got), '\n   object 51 before:', b, '\n   object 51 after: ', a)
hp = lambda h: (h.r.w(0x38000) if False else None)
got, b, a = run(L0, lambda h: [(3, h.obj(114), 0)], lambda h: h.r.mem(A5 + 1190, 2).hex() + ' ' + h.r.mem(A5 + 1188, 4).hex())
print('event 3 -> object 114 (level 0):', got)
gold = lambda h: h.r.l(A5 + 1188)
for ev in (21, 0):
    got, b, a = run(L1, lambda h: [(ev, h.obj(61), 0)], gold)
    print('event %d -> object 61 (level 1): %s  gold %s -> %s' % (ev, got, b, a))
