"""stuck_classes.py <snap>...: classify every set pending word 4(group) of a non-lead group (owner > 0) that has no live
pigeon riding to its lead and no queued side record (pending_census.py's 'orphan' and 'deadpig'), by mechanism:

  deadsender  a pigeon rides to the group's lead with owner byte <= 0: $4562 copied it from a dead sender (the record named
              by the sender word, side-record frame +124 = group-offset frame 48(A1), $45a4/$45a8) and $3e06 skips it
              ($417a); '/g0 re-formed' when the sender word is no longer the first group's lead ($25d6 re-filled slot 0)
  in slot     the order is still in the side's command slot ($58016 + 6*side, type byte 1 non-zero) with the group
              selected ($58042[side] = $4c + $13c*side + 2k): $6a3a/$6ac6 has not dispatched it to $4562 yet
  inherited   walking back through the lineage (the run's start snapshot, then its _c<N> chunks) over the snapshots
              where the word is already set, the slot is free (owner <= 0) or has another lead (word 64) in one of them:
              the word was set for a previous group that $2776 dissolved without clearing it, and $25d6 put a new group
              in the slot without clearing it either
  g0 dissolve no pigeon, and the sender word names a dead record: $2776 on the first group freed the pigeon ($27c6)
  transient   none of the above, and a later snapshot of the lineage has the word clear (an order between $6822 and its pigeon,
              or a pigeon in a state the census misses)
  revived     none of the above, the first group's owner word is 0 and the sender word is its stale lead word 64 (the dead
              commander): the commander died, $2776 dissolved his group and freed the side's pigeons ($27c6), and the
              slot-0 pigeon landing $4244 later revived his corpse as a live man (`neg.b 5(A0)` at $4258, byte 7 bits 4..6
              cleared, side := his home settlement's side at $42ac), so the sender no longer looks dead. '/seen' when an
              earlier snapshot of the full lineage (back through the start snapshot's own run) has the record dead (side
              byte <= 0); '/unseen' when death and revival fall inside one chunk (byte 7 bits 4..6 set before, clear after)
  unknown     none of these

Prints the g0-alive cases and the class counts split by whether the side's first group is alive (pending_census.py's
test), then split by whether the chunk ending at the snapshot ran the commander AI ('frozen': 0 hits of $6522 in the
lineage's <name>.txt, the game is back at the main menu).
Group fields are structure-of-arrays: word n of group k at slot + n + 2k, slot = $51538 + side*$13c."""
import collections, re, sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
OBJ = 0x51b66
def w(r, a): return (r[a] << 8) | r[a + 1]
def s16(v): return v - 0x10000 if v & 0x8000 else v
def s8(v): return v - 0x100 if v & 0x80 else v
_cache = {}
def ram(p):
    p = str(p)
    if p not in _cache: _cache[p] = ram_from_snap(p)
    return _cache[p]

def lineage(sn):
    """[start snapshot (from <name>.txt's 'state loaded from' line, if found), c1, c2, ...] and sn's index in it."""
    m = re.match(r'(.*)_c(\d+)\.snap$', sn.name)
    if not m: return [sn], 0
    chunks = sorted(sn.parent.glob(m.group(1) + '_c*.snap'), key=lambda p: int(re.search(r'_c(\d+)\.snap$', p.name).group(1)))
    start = []
    txt = sn.parent / (m.group(1) + '.txt')
    if txt.exists():
        mm = re.search(r'state loaded from (\S+?): PC', txt.read_text(errors='replace'))
        if mm:
            p = ROOT / mm.group(1)
            if p.exists(): start = [p]
    seq = start + chunks
    return seq, [str(p) for p in seq].index(str(sn))

def frozen(sn):
    """'frozen' when the hits block of the chunk that ended at sn (<name>.txt, one block per chunk) has 0 hits of $6522
    (the commander AI no longer runs: the game is over and back at the main menu), 'live' when it has some, '?' without a
    record."""
    m = re.match(r'(.*)_c(\d+)\.snap$', sn.name)
    txt = sn.parent / (m.group(1) + '.txt') if m else None
    if not txt or not txt.exists(): return '?'
    counts = re.findall(r'\$006522\s+(\d+)', txt.read_text(errors='replace'))
    n = int(m.group(2))
    return '?' if len(counts) < n else ('frozen' if counts[n - 1] == '0' else 'live')

def fld(r, sd, k, n): return s16(w(r, 0x51538 + sd * 0x13c + n + 2 * k))

def classify(sn, r, sd, k, deadpig):
    sender = w(r, 0x51538 + sd * 0x13c + 124 + 2 * k)
    if deadpig:
        return 'deadsender' + ('' if sender == w(r, 0x51538 + sd * 0x13c + 64) else '/g0 re-formed')
    if r[0x58016 + 6 * sd + 1] and w(r, 0x58042 + 2 * sd) == 0x4c + 0x13c * sd + 2 * k:
        return 'in slot'
    seq, i = lineage(sn)
    lead = fld(r, sd, k, 64)
    j = i - 1
    while j >= 0:
        q = ram(seq[j])
        if fld(q, sd, k, 4) == 0: break
        if fld(q, sd, k, 28) <= 0 or fld(q, sd, k, 64) != lead: return 'inherited'
        j -= 1
    if sender and s8(r[((OBJ + s16(sender)) & 0xfffff) + 5]) <= 0:
        return 'g0 dissolve'
    for q in seq[i + 1:]:
        if fld(ram(q), sd, k, 4) == 0: return 'transient'
    if fld(r, sd, 0, 28) <= 0 and sender == w(r, 0x51538 + sd * 0x13c + 64):
        a = (OBJ + s16(sender)) & 0xfffff
        fseq, fi = full_lineage(sn)
        hist = [ram(q) for q in fseq[:fi + 1]]
        if any(s8(q[a + 5]) <= 0 for q in hist[:-1]): return 'revived/seen'
        if any(q0[a + 7] & 0x70 and not q1[a + 7] & 0x70 for q0, q1 in zip(hist, hist[1:])): return 'revived/unseen'
    return 'unknown'

def full_lineage(sn):
    """lineage() continued backwards while the start snapshot is itself a _c<N> chunk of an earlier run."""
    seq, i = lineage(sn)
    while seq[0] != sn and re.search(r'_c\d+\.snap$', seq[0].name):
        pre, j = lineage(seq[0])
        if j == 0: break
        seq = pre[:j] + seq; i += j
    return seq, i

if __name__ == '__main__':
    tot = collections.Counter(); fz = collections.Counter(); rows = []
    for sn in map(Path, sys.argv[1:]):
        r = ram(sn)
        pig = [(0x4c112 + 26 * i) for i in range(1, 48) if r[0x4c112 + 26 * i + 6] == 0x14]
        for sd in range(1, 5):
            slot = 0x51538 + sd * 0x13c
            g0lead = (OBJ + fld(r, sd, 0, 64)) & 0xfffff
            g0 = 'g0 alive' if fld(r, sd, 0, 28) > 0 and s8(r[g0lead + 5]) > 0 else 'g0 dead'
            for k in range(1, 6):
                if fld(r, sd, k, 28) <= 0 or fld(r, sd, k, 4) == 0: continue
                ps = [p for p in pig if w(r, p + 20) == w(r, slot + 64 + 2 * k)]
                if any(s8(r[p + 5]) > 0 for p in ps): continue
                if not ps and any(r[slot:slot + 4]): continue
                c = classify(sn, r, sd, k, bool(ps)); f = frozen(sn)
                tot[(c, g0)] += 1; fz[(c, g0, f)] += 1
                rows.append('%s side %d grp %d %s %s %s %s' % (sn.name, sd, k, 'deadpig' if ps else 'orphan', g0, c, f))
    for x in rows:
        if 'g0 alive' in x: print(x)
    for key in sorted(tot): print(key, tot[key])
    print('total', sum(tot.values()))
    print('split by whether the chunk ending at the snapshot ran the commander AI ($6522 hits in <name>.txt):')
    for key in sorted(fz): print(' ', key, fz[key])
