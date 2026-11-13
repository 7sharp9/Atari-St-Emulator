"""Watch the creature-group list for writes to each record's flag byte (+5) and member slot bytes (+9, +17, ...).
regroup_watch.py <snap> <steps> [keys_hex,...] [out.snap]   env POKES=hexaddr:width:hexval,... (labelled pokes, after the keys)
Keys are keypad presses made first (as py/ai/keys.py: $67/$69 turn, $68 forward). The record layout is walked
once after the keys (records do not move unless a group dies; the script re-walks the list at the end and says so
if it changed). Prints, per group: position, flags before/after, every write to +5 with its writer PC and value,
and every write to a member's +1 byte with PC. Then hits on the regroup branch heads over the same steps cannot be
taken from the same run, so the watch is the record: $d390 writes = flags |= $14 (the view lookup $d376)."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import *

s = srv(sys.argv[1]); steps = int(sys.argv[2])
for kk in (sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] else []):
    k = int(kk, 16)
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=300000)

for pk in filter(None, os.environ.get('POKES', '').split(',')):   # LABELLED POKES: env POKES=hexaddr:width:hexval,...
    a, w, v = pk.split(':'); s('poke', addr=int(a, 16), width=int(w), value=int(v, 16)); print('POKE', pk)

def groups():
    a = A6 + 4532; out = []
    while True:
        hdr = s.read(a, 8); sz = struct.unpack('>h', hdr[2:4])[0]
        if sz < 0: return out, a
        out.append((a, hdr, s.read(a + 8, sz - 8))); a += sz

G0, end0 = groups()
print('party', w16(s, 26), w16(s, 28), 'face', w16(s, 30), 'groups', len(G0), 'list end', hex(end0))
wid = s('watch_add', lo='$%x' % (A6 + 4532), hi='$%x' % end0, kind='w', max_events=200000)['id']
r = s('step', n=steps)
ev = s('watch_events', id=wid)[0]
evs = ev['events']
print('events', len(evs), 'dropped', ev['dropped'])
G1, end1 = groups()
print('list end after', hex(end1), 'unchanged' if end1 == end0 else 'CHANGED (a record moved)')
starts = {a: i for i, (a, h, m) in enumerate(G0)}
def owner(addr):
    best = None
    for a, h, m in G0:
        if a <= addr < a + 8 + len(m): best = (a, h, m)
    return best
from collections import defaultdict
by = defaultdict(list)
for e in evs:
    addr = int(e['addr'].lstrip('$'), 16); w = e['width']
    for b in range(w):
        o = owner(addr + b)
        if not o: continue
        off = addr + b - o[0]
        if off == 5 or (off >= 9 and (off - 9) % 8 == 0):
            val = int(e['value'].lstrip('$'), 16) if isinstance(e['value'], str) else e['value']
            byte = (val >> (8 * (w - 1 - b))) & 0xff
            by[(o[0], off)].append((e['step'], e['pc'], byte))
for i, (a, h, m) in enumerate(G0):
    keys = sorted(k for k in by if k[0] == a)
    if not keys: continue
    h1 = s.read(a, 8)
    print(f'group {i} ${a:x} at ({h[0]},{h[1]})->({h1[0]},{h1[1]}) size {struct.unpack(">h", h[2:4])[0]} flags {h[5]:02x}->{h1[5]:02x} slots ' +
          ' '.join(f'{m[1 + 8 * j]:02x}' for j in range(len(m) // 8)) + ' -> ' + ' '.join(f'{b:02x}' for b in s.read(a + 8, len(m))[1::8]))
    for k in keys:
        pcs = defaultdict(int); vals = []
        for st, pc, byte in by[k]:
            pcs[pc] += 1; vals.append(byte)
        print(f'   +{k[1]:<3d} writes {len(by[k])} by PC ' + ', '.join(f'{p}x{n}' for p, n in pcs.items()) +
              ' values ' + ' '.join(f'{v:02x}' for v in vals[:12]) + (' ...' if len(vals) > 12 else ''))
if len(sys.argv) > 4:
    s('save', path=os.path.abspath(sys.argv[4]))
s.close()
