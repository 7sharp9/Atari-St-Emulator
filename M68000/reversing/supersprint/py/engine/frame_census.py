"""Per-frame call census of a race frame: run from one page flip ($1464a) for the length of one frame and count how often every
function entry runs (REPL `hits`), then print the executed functions with the static call graph (jsr/bsr and A5-thunk calls
from ss.asm) restricted to executed functions, rooted at the race loop $be40.
usage: frame_census.py [snap] [frames]"""
import sys, os, re, bisect, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from repl import Repl

snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
nframes = int(sys.argv[2]) if len(sys.argv) > 2 else 1
funcs = []
for l in open(os.path.join(sscfg.WORK, 'ss.c')):
    m = re.match(r'// ==== ([0-9a-f]{8}) (\S+)', l)
    if m: funcs.append((int(m.group(1), 16), m.group(2)))
funcs.sort(); starts = [f[0] for f in funcs]
names = dict(funcs)
thunks = {}
for l in open(os.path.join(sscfg.WORK, 'thunks.txt')):
    m = re.match(r'(\d+)\(A5\)\s+\$([0-9a-f]+)', l)
    if m: thunks[int(m.group(1))] = int(m.group(2), 16)
# static edges
edges = collections.defaultdict(set)
cur = None
for l in open(os.path.join(sscfg.WORK, 'ss.asm')):
    m = re.match(r'\s+\$([0-9a-f]{6}): (.*)', l)
    if not m: continue
    a = int(m.group(1), 16); t = m.group(2)
    i = bisect.bisect_right(starts, a) - 1
    f = starts[i]
    mm = re.match(r'(?:jsr|bsr|jmp)\s+(-?\d+)\(A5\)', t)
    if mm and int(mm.group(1)) in thunks:
        edges[f].add(thunks[int(mm.group(1))]); continue
    mm = re.search(r'== \$([0-9a-f]+)', t)
    if mm and (t.startswith('jsr') or t.startswith('bsr')):
        edges[f].add(int(mm.group(1), 16)); continue
    mm = re.match(r'(?:jsr|bsr)\s+\$([0-9a-f]+)\.l', t)
    if mm: edges[f].add(int(mm.group(1), 16))
r = Repl(snap)
r.cmd('u 1464a 200000')
r.cmd('s 1')
o, _ = r.cmd('hits 40000 1464a')
first = [int(re.search(r'first (\d+)', l).group(1)) for l in o if '$01464a' in l][0]
L = first * nframes if nframes > 1 else first
print('frame length ~ %d steps' % first)
r.cmd('u 1464a 200000')
r.cmd('s 1')
addrs = ' '.join('%x' % a for a, _ in funcs)
o, _ = r.cmd('hits %d %s' % (first - 2, addrs))
cnt = {}; firstlast = {}
for l in o:
    m = re.match(r'\s+\$([0-9a-f]+)\s+(\d+)\s+first (-?\d+)\s+last (-?\d+)', l)
    if m and int(m.group(2)) > 0:
        cnt[int(m.group(1), 16)] = int(m.group(2)); firstlast[int(m.group(1), 16)] = (int(m.group(3)), int(m.group(4)))
r.close()
print('executed functions in one frame: %d of %d' % (len(cnt), len(funcs)))
seen = set()
def show(f, d):
    print('%s$%05x %-28s x%d' % ('  ' * d, f, names.get(f, ''), cnt.get(f, 0)))
    if f in seen: return
    seen.add(f)
    for g in sorted(edges.get(f, ())):
        if g in cnt: show(g, d + 1)
show(0xbe40, 0)
rest = [f for f in cnt if f not in seen]
print('executed but not under $be40 (ISR / other entries):', ' '.join('$%x(x%d)' % (f, cnt[f]) for f in sorted(rest)))

print('\nexecution order (step of first entry within the frame, count, last entry):')
for f in sorted(cnt, key=lambda a: firstlast[a][0]):
    print('  step %5d  $%05x %-26s x%d  last %d' % (firstlast[f][0], f, names.get(f, ''), cnt[f], firstlast[f][1]))
