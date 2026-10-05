#!/usr/bin/env python3
"""Every `jsr $e1c` (sound-command send) in the 68000 image with the sound id in D7, found without relying on a recursive-descent
listing: a raw scan of the whole 512 KiB image finds the call sites (scan68k.py), then each site's predecessor instruction is
recovered by backward synchronisation (decode forward from every even start in [site-40, site-2] and keep chains that land exactly on the site
with no illegal opcodes).  Also finds D7 loaded two or more instructions earlier and flags computed ids.
Output: callers68k.tsv (site, kind, ids, predecessor chain, handler region)."""
import os, re, struct, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import Disassembler
rom = open(os.path.join(ROOT, 'scratchpad/crudebuster/rom/cbuster_main.bin'), 'rb').read()
dis = Disassembler(rom, rom_base=0)
T = 0xe1c
w = lambda a: (rom[a] << 8) | rom[a + 1]
sites = []
for a in range(0, len(rom) - 6, 2):
    op = w(a)
    if op == 0x4eb8 and w(a + 2) == T: sites.append((a, 'jsr.w', 4))
    elif op == 0x4eb9 and w(a + 2) == 0 and w(a + 4) == T: sites.append((a, 'jsr.l', 6))
    elif op in (0x6100, 0x6000):
        d = w(a + 2); d = d - 0x10000 if d & 0x8000 else d
        if a + 2 + d == T: sites.append((a, 'bsr.w' if op == 0x6100 else 'bra.w', 4))
    elif op in (0x4ef8,) and w(a + 2) == T: sites.append((a, 'jmp.w', 4))
    elif op in (0x4ef9,) and w(a + 2) == 0 and w(a + 4) == T: sites.append((a, 'jmp.l', 6))
# handler table $10418 (153 long pointers): region owner
def L(a): return struct.unpack('>I', rom[a:a + 4])[0]
handlers = sorted((L(0x10418 + 4 * i), i) for i in range(153))
def region(a):
    best = None
    for h, i in handlers:
        if h <= a: best = (h, i)
    return best

def chain_to(start, site):
    a = start; out = []
    while a < site:
        try:
            t, n = dis.decode_one(a)
        except Exception:
            return None
        if t.startswith('illegal') or t.startswith('dc.') or '?' in t: return None
        out.append((a, t)); a = n
    return out if a == site else None

sites_l = sites
# shared tails: another path reaches the `jsr $e1c` through a branch (bra/bcc .b/.w) after loading D7 itself.  Collect those predecessors too.
branch_src = collections.defaultdict(list)
for a in range(0, len(rom) - 4, 2):
    op = w(a)
    if (op & 0xf000) == 0x6000 and (op >> 8) not in (0x61,):     # bra / bcc (not bsr)
        d = op & 0xff
        if d == 0: tgt = a + 2 + (w(a + 2) - 0x10000 if w(a + 2) & 0x8000 else w(a + 2)); ln = 4
        elif d == 0xff: continue
        else: tgt = a + 2 + (d - 256 if d > 127 else d); ln = 2
        branch_src[tgt].append((a, ln))
def ids_before(addr, depth=0):
    """ids loaded into D7 by the instruction chain that ends right before `addr`, following branch sources into addr too (depth 1)"""
    res = set()
    for s0 in range(addr - 2, addr - 42, -2):
        c = chain_to(s0, addr)
        if c:
            t = c[-1][1]
            m = re.match(r'moveq #(-?\d+),D7$', t)
            if m: res.add(int(m.group(1)) & 0xff)
            m = re.match(r'move\.[wbl] #\$([0-9a-f]+),D7$', t)
            if m: res.add(int(m.group(1), 16) & 0xff)
            m = re.match(r'move\.[wbl] #(-?\d+),D7$', t)
            if m: res.add(int(m.group(1)) & 0xff)
    return res
extra = {}
for a, kind, ln in sites:
    ex = set()
    for (b, bl) in branch_src.get(a, []):
        ex |= ids_before(b + 0)   # instruction chain ending at the branch instruction
    extra[a] = ex
res = []
for a, kind, ln in sites:
    chains = {}
    for s in range(a - 2, a - 42, -2):
        c = chain_to(s, a)
        if c:
            chains[s] = c
    # predecessor candidates
    preds = {}
    for s, c in chains.items():
        preds.setdefault(c[-1][1], []).append(s)
    ids = set()
    for t in preds:
        m = re.match(r'moveq #(-?\d+),D7$', t)
        if m: ids.add(int(m.group(1)) & 0xff)
        m = re.match(r'move\.[wbl] #\$([0-9a-f]+),D7$', t)
        if m: ids.add(int(m.group(1), 16) & 0xff)
        m = re.match(r'move\.[wbl] #(-?\d+),D7$', t)
        if m: ids.add(int(m.group(1)) & 0xff)
    res.append((a, kind, sorted(ids), preds))
    res[-1] = (a, kind, sorted(set(ids) | extra.get(a, set())), preds)
def fmtid(i): return '$%02x' % i
with open(os.path.join(HERE, 'callers68k.tsv'), 'w') as f:
    f.write('site\tkind\tids\tpredecessor(s)\tregion(handler type table $10418 index @ addr)\n')
    for a, kind, ids, preds in res:
        r = region(a)
        f.write('%06x\t%s\t%s\t%s\t%s\n' % (a, kind, ','.join(map(fmtid, ids)) or '?', ' | '.join('%s<-%d' % (t, len(s)) for t, s in preds.items()), ('type %d @%x' % (r[1], r[0])) if r else '-'))
print(len(res), 'sites;', sum(1 for r in res if r[2]), 'with immediate id;', [hex(r[0]) for r in res if not r[2]])
