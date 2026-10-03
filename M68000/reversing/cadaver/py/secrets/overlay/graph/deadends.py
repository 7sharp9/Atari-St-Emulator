"""deadends.py [outdir]: A1 (Cadaver 91st pass).  Which script blocks, flags and items can never be reached from the lineage state (room 90), in the
delete-relaxed closure (relax.py) with the UNLOCK DOOR scroll (the most permissive mode): blocks that never fire, with a reason class (event with no/unread
producer, owner never in a reachable room, gate item unobtainable, no icon for the event), flags nothing writes, and items named by a gate that no reachable
room holds.  Writes <outdir>/deadends.txt."""
import sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from relax import setup
from model import OUTDIR
import effects as fx

def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTDIR
    outdir.mkdir(exist_ok=True)
    sm, rx = setup(spells=True); rx.run()
    w = sm.w; out = []
    rooms = {f[1] for f in rx.prov if f[0] == 'room'}
    items = {f[1] for f in rx.prov if f[0] == 'item'}
    never = [b for b in w.blocks if (b.kind, b.owner, b.idx) not in rx.fired]
    out.append('closure (scripts + UNLOCK DOOR scroll 407) from room 90: %d of %d rooms reachable, %d of %d blocks ever fire' % (len(rooms), len(w.rooms), len(w.blocks) - len(never), len(w.blocks)))
    out.append('rooms never reached: %s' % sorted(set(w.rooms) - rooms))
    by = collections.defaultdict(list)
    for b in never:
        cls = fx.EVENT[b.event][1]
        if cls == 'X': r = 'event %d has NO producer anywhere (event_3_21_static.py)' % b.event
        elif cls == '?': r = 'event %d: producer sites exist but their conditions are unread (not modelled)' % b.event
        elif b.kind == 'room': r = 'room %d never reached' % b.owner if b.owner not in rooms else 'room reached but the block never fires (gate/guard/producer not satisfiable in the model)'
        else:
            rs = w.loc.get(b.owner, [])
            if not any(r in rooms for r in rs): r = 'owner object not in a reachable room (%s)' % (rs or 'no list')
            elif b.event in (18, 26) and not any(it for it in items if ((b.gate[0] << 8) | b.gate[1]) == it): r = 'gate item %d never obtainable' % ((b.gate[0] << 8) | b.gate[1])
            else: r = 'owner reachable but the block never fires (guard, hidden/locked owner or event producer)'
        by[r].append(w.bid(b))
    for r, lst in sorted(by.items(), key=lambda t: -len(t[1])):
        out.append('%4d  %s' % (len(lst), r)); out.append('        ' + ' '.join(lst))
    out.append('')
    out.append('FLAGS (type-4 words) that start non-zero and that no script block ever clears or sets to 0:')
    for n, f in sorted(w.flags.items()):
        if f['word'] and not any(row[2] and (row[1] in (10,) or (row[1] == 27 and row[2][1] == 0)) for (b, row, det, ctx) in w.W.get(('flag', n), [])):
            owners = [r for r, rr in w.rooms.items() if n in rr['doors']]
            out.append('   flag %d $%02x word $%04x doors of rooms %s: %s' % (n, n, f['word'], owners, 'key item %d' % f['word'] if f['word'] < 0x8000 else 'no clearing writer'))
    out.append('')
    out.append('ITEMS named by a gate (verb 34/57, event 18/26 gate word, positive door word) that are never obtainable in the closure:')
    names = set()
    for n in list(w.R):
        if n[0] in ('item', 'item_used') and isinstance(n[1], int): names.add(n[1])
    for f in w.flags.values():
        if 0 < f['word'] < 0x8000: names.add(f['word'])
    for o in sorted(names):
        if o not in items:
            out.append('   item %d %s: in room list %s hidden %s' % (o, w.label.get(o, ''), w.loc.get(o), w.objs[o]['b3'] >> 7 if o in w.objs else '-'))
    (outdir / 'deadends.txt').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))

if __name__ == '__main__':
    main()
