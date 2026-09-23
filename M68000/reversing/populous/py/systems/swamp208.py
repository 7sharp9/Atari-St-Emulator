"""swamp208.py - drive a game to the population-208 swamp monster ($e89c) and record its spawn.

  python swamp208.py run [snap] [chunks] [steps_per_chunk]

run: from $POP_WORK/ai/cg2.snap (ATARI VS ATARI), `u e89c` in chunks; after each chunk print the
frame, the high-water count $3c4e2, live slots (str > 0) below $d0, both populations, and save
$POP_WORK/swamp208/cNN.snap. Stops when PC reaches $e89c and saves at208.snap there.

  python swamp208.py poke <snap> <name>

poke (POKED): run to the next walker-emission scan ($e6c6), give every free slot below $d0 str 1
(only +4, the rest of the record stays), run to $13372 (called from $e8a0, with the natural stack
word as its edge) and save <name>.snap there, plus <name>.after: REPL lines that put the poked +4
words back, for trailrun.py to run straight after the spawn. Prints the trailrun.py environment.
"""
import os, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'powers')))
from pwlib import Repl2, rw, rsw, rl
from popcfg import WORK
OUT = os.path.join(WORK, 'swamp208'); os.makedirs(OUT, exist_ok=True)
ENT, ESZ = 0x3b278, 0x16


def status(r):
    ents = r.mem(ENT, ESZ * 0xd3)
    live = sum(1 for s in range(0xd0) if rsw(ents, s * ESZ + 4) > 0)
    g = r.mem(0x3b22e, 0x20)
    return ('frame %d count %d live<$d0 %d pop %d/%d $3c4c4=%d trails %d,%d'
            % (rw(r.mem(0x3c4c8, 2), 0), rw(r.mem(0x3c4e2, 2), 0), live, rl(g, 0), rl(g, 16),
               rw(r.mem(0x3c4c4, 2), 0), rsw(ents, 0xd1 * ESZ + 4), rsw(ents, 0xd2 * ESZ + 4)))


def run(snap, chunks, steps):
    r = Repl2(snap)
    print('start', status(r), flush=True)
    for c in range(chunks):
        _, regs = r.cmd('u e89c %d' % steps)
        if regs.get('PC') == 0xe89c:
            p = os.path.join(OUT, 'at208.snap'); r.cmd('snap ' + p)
            print('REACHED $e89c', status(r), 'A6 %x A7 %x' % (regs['A6'], regs['A7']), '->', p, flush=True)
            break
        p = os.path.join(OUT, 'c%02d.snap' % c); r.cmd('snap ' + p)
        print('chunk', c, 'PC %x' % regs.get('PC', 0), status(r), flush=True)
    r.close()


def poke(snap, name):
    r = Repl2(snap)
    _, regs = r.cmd('u e6c6 400000000')
    assert regs.get('PC') == 0xe6c6, regs
    assert rw(r.mem(0x3c4c4, 2), 0) == 0, '$3c4c4 already set: the pop-208 spawn has happened'
    ents = r.mem(ENT, ESZ * 0xd0)
    free = [s for s in range(0xd0) if rsw(ents, s * ESZ + 4) <= 0]
    after = []
    for s in free:
        a = ENT + s * ESZ + 4
        after.append('w %x %08x' % (a, rl(ents, s * ESZ + 4)))
        r.cmd('w %x %08x' % (a, 0x10000 | rw(ents, s * ESZ + 6)))
    print('at $e6c6', status(r), '- poked %d free slots' % len(free), flush=True)
    _, regs = r.cmd('u 13372 2000000')
    assert regs.get('PC') == 0x13372, regs
    a7 = regs['A7']; stk = r.mem(a7, 8)
    assert rl(stk, 0) == 0xe8a6, 'return %x' % rl(stk, 0)
    p = os.path.join(OUT, name + '.snap'); r.cmd('snap ' + p)
    open(os.path.join(OUT, name + '.after'), 'w').write('\n'.join(after) + '\n')
    e1, e2 = r.mem(ENT + 0xd1 * ESZ, ESZ), r.mem(ENT + 0xd2 * ESZ, ESZ)
    print('at $13372 A7 %x type %d edge word %04x; trail slots str %d cell %d / str %d cell %d'
          % (a7, rsw(stk, 4), rw(stk, 6), rsw(e1, 4), rw(e1, 8), rsw(e2, 4), rw(e2, 8)))
    print('TRAIL_SNAP=%s TRAIL_A7=%x TRAIL_RET=e8a6 TRAIL_AFTER=%s' % (p, a7, os.path.join(OUT, name + '.after')))
    r.close()


def edges(snap, n):
    """the word $13372 would take as its edge from $e89c: -146(A6) of $db4c, read at entry ($db50)
    and at the unlk ($ef48) of the same call, over n frames."""
    import collections
    r = Repl2(snap)
    seen = collections.Counter(); same = 0; f = 0
    for f in range(n):
        _, regs = r.cmd('u db50 20000000')
        if regs.get('PC') != 0xdb50:
            print('stopped at %x' % regs.get('PC', 0)); break
        a = regs['A6'] - 146
        w0 = rw(r.mem(a, 2), 0)
        _, regs = r.cmd('u ef48 20000000')
        if regs.get('PC') != 0xef48:
            print('$db4c did not return (PC %x): stopping' % regs.get('PC', 0)); break
        assert regs['A6'] - 146 == a, regs
        w1 = rw(r.mem(a, 2), 0)
        same += w0 == w1; seen[w0] += 1
    print('%s: %d frames to frame %d, word at $%x unchanged through $db4c %d/%d; values %s'
          % (os.path.basename(snap), f + 1, rw(r.mem(0x3c4c8, 2), 0), a, same, f + 1,
             ', '.join('%04x x%d' % kv for kv in seen.most_common())))
    r.close()


if __name__ == '__main__':
    if sys.argv[1] == 'edges':
        edges(os.path.abspath(sys.argv[2]), int(sys.argv[3]))
    if sys.argv[1] == 'poke':
        poke(os.path.abspath(sys.argv[2]), sys.argv[3])
    if sys.argv[1] == 'run':
        snap = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else os.path.join(WORK, 'ai', 'cg2.snap')
        run(os.path.abspath(snap), int(sys.argv[3]) if len(sys.argv) > 3 else 20,
            int(sys.argv[4]) if len(sys.argv) > 4 else 200000000)
