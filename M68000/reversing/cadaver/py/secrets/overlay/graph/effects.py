"""effects.py: A1 (Cadaver 91st pass) classification of every verb row into graph reads/writes, and of every event into
its trigger (producer) description.  A node is (kind, key); an effect is (rw, node, detail).  Verb semantics are the ones of
`secrets.md` "Verb table" (callcap-proven by verbs2/verb_effects2.py), the operand typing is `model.typed`.  Where the
decode and the doc disagree the note is in NOTES at the bottom (printed by graph.py).
Gate byte semantics are the gate routines of table $00fe84 (read from the listing; see GATE_NOTE)."""
from model import VARBASE, TIMERBASE

ACTOR = 0xffff

# event -> (trigger text, class)   class: P player-driven, E engine/room-driven, S script-queued, ? producer unread, X no producer
EVENT = {
    0:  ('TAKE icon 2 of this object ($00a136) or verb 35 PUT IN RUCK', 'P'),
    1:  ('producers $00a114/$00fa62 unread', '?'),
    3:  ('NO PRODUCER (event_3_21_static.py)', 'X'),
    4:  ('producer $00f328 unread; gate word', '?'),
    5:  ('operate/read/use icon (3,4,7,8,9,$e) on this object ($00a448,$00a486,$00a5d2,$00a59c,$00a7ce)', 'P'),
    6:  ('every entry into this room ($00eae4)', 'E'),
    7:  ('proximity: facing this object, every frame ($0095d8)', 'P'),
    9:  ('contact/touch of this object ($0095c0, $008a34)', 'P'),
    10: ('producer $009286 (region test) unread', '?'),
    11: ('producer $00f69c unread', '?'),
    12: ('producer $00f9a2 unread; gate byte', '?'),
    13: ('producer $00b0f0 unread; gate byte', '?'),
    14: ('room tick ($0090aa, byte 2 timer)', 'E'),
    15: ('hero overlaps region N of the room ($0092b4)', 'P'),
    16: ('EXAMINE icon $b ($00a3d0; needs template byte 3 bit 5)', 'P'),
    17: ('a non-hero object overlaps region N ($0092da)', 'P'),
    18: ('APPLY held item (icon $c, $00a6f4) to this object; gate word = item object id', 'P'),
    19: ('verb 9 raised on the current room ($4013)', 'S'),
    20: ('verb 42 countdown expiry on the room ($4014)', 'S'),
    21: ('NO PRODUCER (event_3_21_static.py)', 'X'),
    23: ('kill: verb 50, $00fb24, overlay kill sites', 'S'),
    24: ('spell cast in the room ($00f0a0); gate = spell id', 'P'),
    25: ('producer $00f0c8 unread', '?'),
    26: ('GIVE held item (icon $f, $00a7a4) to this class-$c object; gate word = item object id', 'P'),
    27: ('SELECT icon $d ($00a72e): Space with an item', 'P'),
    28: ('first entry into this room ($00e8a6)', 'E'),
}

GATE_NOTE = {
    0: 'none', 1: 'byte == class byte of the touching object ($00fece)', 3: 'none', 4: 'word == 1156(A5) ($00ff26)',
    5: 'none', 6: 'none', 7: 'none', 9: 'word: <0 passes any, else == 1156(A5) ($00ff10)', 10: 'byte0 == 1167(A5), byte1 == 1157(A5) ($00fefc)',
    11: 'none', 12: 'byte == 1157(A5) ($00ff98)', 13: 'byte == 1157(A5) ($00ff98)', 14: 'none', 15: 'region byte == 1157(A5) ($00feea)',
    16: 'none (keep-bit bookkeeping $00ff88)', 17: 'region byte == 1157(A5) ($00feea)', 18: 'word == 1156(A5) = held item OBJECT id ($00ff38)',
    19: 'byte == 1157(A5) ($00ff98)', 20: 'byte == 1157(A5) ($00ff98)', 21: 'none', 22: 'none',
    23: 'pays gold/XP from the class block ($00ff4e)', 24: 'spell id byte ($00febe)', 25: 'none', 26: 'word == 1156(A5) = given item OBJECT id ($00ff26)',
    27: 'none', 28: 'none'}


def gate_text(event, gate):
    if event in (4, 9, 18, 26) and len(gate) == 2:
        w = (gate[0] << 8) | gate[1]
        return 'word %d' % w if w < 0x8000 else 'word $%04x(any)' % w
    if gate:
        return ' '.join('%d' % g for g in gate)
    return ''


def varname(off):
    if VARBASE <= off < TIMERBASE: return ('var', off - VARBASE)
    if TIMERBASE <= off < TIMERBASE + 64: return ('timerbyte', off - TIMERBASE)
    return ('a5', off)


def effects(owner_obj, v, a, ctx_room=None):
    """-> list of (rw, node, detail).  owner_obj: the owning object id (object blocks) or None (room blocks: actor = the mover)."""
    me = ('exist', owner_obj) if owner_obj is not None else ('exist', 'ACTOR')
    def obj(o):
        return owner_obj if o == ACTOR and owner_obj is not None else ('ACTOR' if o == ACTOR else o)
    W, R = 'W', 'R'
    E = []
    if v == 0:  E.append((W, ('exist', obj(a[0])), 'DELETE'))
    elif v == 1: E.append((W, ('exist', obj(a[0])), 'SHOW (clear hidden bit, place, draw)'))
    elif v == 2: E.append((W, me, 'DELETE self'))
    elif v == 3: E.append((W, ('anim', obj(a[0])), 'GOANI'))
    elif v == 4: E.append((W, ('anim', obj(a[0])), 'STOPANI'))
    elif v in (5, 85): E.append((W, ('xp', 0), 'XP'))
    elif v == 6: E += [(W, ('gold', 0), '+%d' % a[0]), (W, ('xp', 0), '+n/4')]
    elif v == 86: E += [(W, ('gold', 0), 'word'), (W, ('xp', 0), 'word/4')]
    elif v == 13: E.append((W, ('gold', 0), '-%d' % a[0]))
    elif v == 45: E.append((W, ('health', 0), '%+d' % (a[0] - 0x10000 if a[0] >= 0x8000 else a[0])))
    elif v == 7: E.append((W, ('creature', a[0]), 'REGISTER'))
    elif v == 8: E.append((W, ('creature', a[0]), 'UNREGISTER'))
    elif v == 9: E.append((W, ('roomev19', a[0]), 'verb 9 raises event 19 (gate %d) on the current room' % a[0]))
    elif v == 10: E.append((W, ('flag', a[0]), 'CLEAR (word := 0)'))
    elif v == 27: E.append((W, ('flag', a[0]), 'SET word := $%04x' % a[1]))
    elif v == 61: E.append((R, ('flag', a[0]), 'COND flag non-zero'))
    elif v == 11: E.append((W, ('mover', obj(a[0])), 'GOMOVE'))
    elif v == 12: E.append((W, ('mover', obj(a[0])), 'STOPMOVE'))
    elif v == 16: E.append((R, ('state0', obj(a[0])), 'COND bit0'))
    elif v == 17: E.append((W, ('state0', obj(a[0])), 'bit0 := 1'))
    elif v == 18: E.append((W, ('state0', obj(a[0])), 'bit0 := 0'))
    elif v == 24: E.append((W, ('state0', obj(a[0])), 'bit0 ^= 1'))
    elif v == 19: E.append((R, ('state1', obj(a[0])), 'COND bit1'))
    elif v == 20: E.append((W, ('state1', obj(a[0])), 'bit1 := 1'))
    elif v == 21: E.append((W, ('state1', obj(a[0])), 'bit1 := 0'))
    elif v == 25: E.append((W, ('state1', obj(a[0])), 'bit1 ^= 1'))
    elif v == 26: E.append((W, ('exist', obj(a[0])), 'HIDE'))
    elif v == 29: E.append((W, ('spent', owner_obj), 'block spent'))
    elif v == 30: E.append((R, ('state0', obj(ACTOR)), 'COND own bit0'))
    elif v == 31: E.append((W, ('state0', obj(ACTOR)), 'own bit0 := 0'))
    elif v == 32: E.append((W, ('state0', obj(ACTOR)), 'own bit0 := 1'))
    elif v == 33: E.append((W, ('state0', obj(ACTOR)), 'own bit0 ^= 1'))
    elif v == 34: E.append((R, ('item', a[0]), 'COND object %d in the rucksack (record word +0)' % a[0]))
    elif v == 35: E += [(W, ('item', obj(a[0])), 'PUT IN RUCK'), (W, ('exist', obj(a[0])), 'leaves its room'), (W, ('ev0', obj(a[0])), 'queues event 0')]
    elif v == 36: E.append((W, ('exist', obj(a[0])), 'CREATE clone at (%d,%d,%d,f%d) in this room' % tuple(a[1:5])))
    elif v == 37: E.append((W, ('tele', a[0]), 'TELEPORT room %d at (%d,%d,%d)' % tuple(a[:4])))
    elif v == 38: E.append((W, ('var', a[0]), 'VAR := %d' % a[1]))
    elif v == 39: E.append((W, ('var', a[0]), 'VAR += %d' % a[1]))
    elif v == 40: E.append((R, ('var', a[0]), 'COND var %s %d' % (['>', '<', '==', '!='][min(a[1], 3)], a[2])))   # byte order n, op, value ($010c06-$010c12)
    elif v == 41: E += [(W, ('exist', obj(a[0])), 'PLACE in room %s at (%d,%d,%d)' % ('this' if a[1] == 254 else a[1], a[2], a[3], a[4])),
                        (W, ('roomlist', a[1] if a[1] != 254 else 'this'), 'object %s joins the list' % obj(a[0]))]
    elif v == 42: E.append((W, ('roomev20', a[0]), 'verb 42: room countdown %d ticks, then event 20 gate %d' % (a[1], a[0])))
    elif v == 43: E.append((R, ('exist', obj(a[0])), 'COND object in room %s' % ('this' if a[1] == 254 else a[1])))
    elif v == 44: E += [(R, ('exist', obj(a[0])), 'position source'), (W, ('exist', obj(a[1])), 'CREATE clone next to %s' % obj(a[0]))]
    elif v == 47: E.append((R, ('exist', obj(a[0])), 'COND exists'))
    elif v == 49: E.append((W, ('timer', a[0]), 'ARM timer %d for %d ticks' % (a[0], a[1])))
    elif v == 50: E.append((W, ('ev23', obj(a[0])), 'KILL (event 23)'))
    elif v == 51: E.append((W, ('level', a[0] + 1), 'START LEVEL %d' % (a[0] + 1)))
    elif v in (54, 55, 77, 78, 92): E.append((W, ('lock', obj(a[0])), {54: 'LOCK (+15 bit2 := 1)', 55: 'UNLOCK (+15 bit2 := 0)', 77: 'UNLOCK CHEST', 78: 'UNTRAP CHEST', 92: 'CLEAR CHEST'}[v]))
    elif v == 56: E.append((R, ('exist', obj(a[0])), 'COND in box'))
    elif v == 57: E.append((R, ('item', a[0]), 'COND selected object (1262(A5)) == %d' % a[0]))
    elif v == 60: E.append((R, ('gold', 0), 'BUY prompt'))
    elif v in (62, 63):
        k = varname(a[0]); E.append((W, k, ('SET' if v == 62 else 'ADD') + ' %d' % a[1]))
    elif v == 64: E.append((R, varname(a[0]), 'COND mem op'))
    elif v == 65: E.append((W, ('field', obj(a[0])), 'class byte +1 += %d' % a[1]))
    elif v == 66: E.append((W, ('q66', obj(a[0])), 'queue class record operand %d' % a[1]))
    elif v == 67: E.append((W, ('acti', obj(a[0])), 'GOACTI'))
    elif v == 68: E.append((W, ('acti', obj(a[0])), 'STOPACTI'))
    elif v == 69: E.append((W, ('exist', obj(a[0])), 'MOVE record bytes +3,+4,+5'))
    elif v == 73: E += [(R, ('exist', obj(a[0])), 'position source'), (W, ('exist', obj(a[1])), 'MOVE to the position and room of %s' % obj(a[0]))]
    elif v == 76: E.append((R, ('shield', a[0]), 'COND shield bit'))
    elif v == 79: E.append((W, ('rand', 0), 'RANDOM %d..%d' % (a[0], a[1])))
    elif v == 80: E.append((R, ('rand', 0), 'COND rand == %d' % a[0]))
    elif v == 81: E += [(R, ('var', a[0]), 'copy var'), (W, ('rand', 0), '2520 := var')]
    elif v == 82: E.append((W, ('itemtmpl', a[0]), 'DELETE rucksack entries with template idx %d' % a[0]))
    elif v == 84: E.append((W, ('exist', obj(a[1])), 'CREATE clone relative to %s' % obj(a[0])))
    elif v == 90: E.append((W, ('poison', 0), 'POISON'))
    elif v == 93: E.append((W, ('field', obj(a[0])), 'DIRTY POTION'))
    elif v == 88: E.append((R, ('tick2489', 0), 'COND n == 2489(A5)'))
    elif v == 91: E.append((R, ('tmpl', obj(ACTOR)), 'COND template idx'))
    return E


def gate_reads(event, gate):
    """events whose gate names an item/region/spell: -> list of (node, detail)"""
    out = []
    if event in (18, 26) and len(gate) == 2:
        w = (gate[0] << 8) | gate[1]
        out.append((('item_used', w), 'event %d gate: held/given item object %d' % (event, w)))
    if event in (15, 17) and gate: out.append((('region', gate[0]), 'region %d' % gate[0]))
    if event in (19, 20) and gate: out.append((('roomev%d' % event, gate[0]), 'verb %d argument %d' % (9 if event == 19 else 42, gate[0])))
    if event == 24 and gate: out.append((('spell', gate[0]), 'spell %d' % gate[0]))
    return out
