"""stuck_live.py <snap>...: list the set pending words 4(group) of non-lead groups on a side whose first group is alive and
that have no live pigeon (pending_census.py's 'orphan' and 'deadpig' classes with 'g0 alive'), and for each one print the
same group across every chunk of its lineage (<name>_c<N>.snap in the same directory): owner, men, pending, state, lead
offset (word 64), whether the lead's owner byte is positive, and the pigeons riding to that lead.
Fields (structure-of-arrays, group k's word n at slot + n + 2k, slot = $51538 + side*$13c) as in pending_census.py."""
import re, sys
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
    if p not in _cache: _cache[p] = ram_from_snap(str(p))
    return _cache[p]

def pigeons(r):
    return [(0x4c112 + 26 * i) for i in range(1, 48) if r[0x4c112 + 26 * i + 6] == 0x14]

def group(r, sd, k):
    slot = 0x51538 + sd * 0x13c; A1 = slot + 2 * k
    lead = (OBJ + s16(w(r, A1 + 64))) & 0xfffff
    return dict(own=s16(w(r, A1 + 28)), men=w(r, A1 + 52), pend=s16(w(r, A1 + 4)), state=w(r, A1 + 76),
                lw=w(r, A1 + 64), lead=lead, leadown=s8(r[lead + 5]), leadmode=r[lead + 31], leadw42=w(r, lead + 42))

def g0alive(r, sd):
    g = group(r, sd, 0); return g['own'] > 0 and g['leadown'] > 0

def cases(r):
    out = []
    pig = pigeons(r)
    for sd in range(1, 5):
        if not g0alive(r, sd): continue
        slot = 0x51538 + sd * 0x13c
        for k in range(1, 6):
            g = group(r, sd, k)
            if g['own'] <= 0 or g['pend'] == 0: continue
            ps = [p for p in pig if w(r, p + 20) == g['lw']]
            if any(s8(r[p + 5]) > 0 for p in ps): continue
            if not ps and any(r[slot:slot + 4]): continue
            out.append((sd, k, g, ['%x own %d' % (p, s8(r[p + 5])) for p in ps]))
    return out

def lineage(sn):
    m = re.match(r'(.*)_c(\d+)\.snap$', sn.name)
    sibs = sorted(sn.parent.glob(m.group(1) + '_c*.snap'), key=lambda p: int(re.search(r'_c(\d+)\.snap$', p.name).group(1)))
    return sibs

if __name__ == '__main__':
    n = 0
    for sn in map(Path, sys.argv[1:]):
        for sd, k, g, ps in cases(ram(sn)):
            n += 1
            print('== %s side %d grp %d pend %d men %d state %d lead %x pigeons-to-lead %s' % (sn.name, sd, k, g['pend'], g['men'], g['state'], g['lead'], ps))
            for c in lineage(sn):
                r = ram(c); h = group(r, sd, k); h0 = group(r, sd, 0)
                ps = ['%x/%d' % (p, s8(r[p + 5])) for p in pigeons(r) if w(r, p + 20) == h['lw']]
                print('   %-18s own %2d men %3d pend %2d st %2d lw %04x leadown %3d m%02x w42 %04x | g0 own %d lead %04x leadown %d | pig %s' % (
                    c.name, h['own'], h['men'], h['pend'], h['state'], h['lw'], h['leadown'], h['leadmode'], h['leadw42'],
                    h0['own'], h0['lw'], h0['leadown'], ps))
    print(n, 'cases')
