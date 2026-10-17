"""blocks_of.py SNAP ID...: the script blocks of each object (owner, event, gate, verb rows) and, with `refs`, every block anywhere whose operands name one of the ids
(a MOVE, GOMOVE or state write aimed at it).  Static: any level-1 snapshot works (scratchpad/cadaver/level1_loaded.snap; a mid-game snapshot can hold a block the decoder
refuses).  Example: room 6's caps 162/164/166 each GOMOVE the item on top on event 9 gated [1, 124] = id $017c, the post 380 (mechanics.md section 12).
Run from M68000/: M68000_ROOT=$PWD .venv/bin/python reversing/cadaver/py/secrets/overlay/l1_objects/blocks_of.py scratchpad/cadaver/level1_loaded.snap [refs] 380 251"""
import sys, os
def _root():
    if os.environ.get('M68000_ROOT'): return os.environ['M68000_ROOT']
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        assert os.path.dirname(d) != d, 'repo root (tools/rdis.py) not found: set M68000_ROOT'
        d = os.path.dirname(d)
    return d
ROOT = _root(); os.environ.setdefault('M68000_ROOT', ROOT)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/graph')
import model
args = sys.argv[2:]; refs = 'refs' in args; want = set(int(a) for a in args if a != 'refs')
blocks, _ = model.load_blocks(model.Snap(sys.argv[1]))
for b in blocks:
    if refs:
        hit = [(v, name, ta) for d, v, ta, name, ctx in b.rows if any(isinstance(x, int) and x in want for x in ta)]
        if hit:
            print('== %s %s.%d event %d gate %s' % (b.kind, b.owner, b.idx, b.event, b.gate))
            for v, name, ta in hit: print('    %2d %-40s %s' % (v, name[:40], ta))
    elif b.kind == 'obj' and b.owner in want:
        print('== obj %d.%d event %d keep %s gate %s' % (b.owner, b.idx, b.event, b.keep, b.gate))
        for d, v, ta, name, ctx in b.rows: print('   ' + '  ' * d + '%2d %-14s %s' % (v, name, ta))
