"""Per-frame call tree from an ATARI_TRACE_EVENTS log (flow events only).
usage: calltree.py ev.bin <frame_start_addr_hex> <frame_index> [maxdepth] [min_total_steps]
A frame = from the Nth call of <frame_start> to the (N+1)th.  Prints the tree with call counts
(same callee from the same parent collapsed) and inclusive steps.  Interrupt handlers are
shown as separate roots (kind 6)."""
import sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../tools"))
import trace_cfg

KCALL, KRET, KINT = 3, 4, 6
path, fs, idx = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
maxd = int(sys.argv[4]) if len(sys.argv) > 4 else 99
_, _, recs = trace_cfg.load(path)
starts = [i for i, r in enumerate(recs) if r[4] == KCALL and (r[2] & 0xFFFFFF) == fs]
a, b = starts[idx], starts[idx + 1]
print(f"frame {idx}: records {a}..{b}, steps {recs[a][0]}..{recs[b][0]} = {recs[b][0]-recs[a][0]}")


class N:
    def __init__(s, addr, step):
        s.addr = addr; s.step = step; s.end = step; s.kids = []; s.n = 1


root = N(fs, recs[a][0])
stack = [root]
for sc, pc, tg, op, kind in recs[a + 1:b]:
    if kind == KCALL:
        n = N(tg & 0xFFFFFF, sc); stack[-1].kids.append(n); stack.append(n)
    elif kind == KINT:
        n = N(-(tg & 0xFFFFFF), sc); stack[-1].kids.append(n); stack.append(n)
    elif kind == KRET:
        if len(stack) > 1:
            stack[-1].end = sc; stack.pop()
for n in stack:
    n.end = recs[b][0]


def merge(kids):
    """collapse same-address siblings into (addr, count, total steps, merged children)"""
    d = collections.OrderedDict()
    for k in kids:
        e = d.setdefault(k.addr, [0, 0, []])
        e[0] += 1; e[1] += k.end - k.step; e[2].extend(k.kids)
    return d


def show(kids, depth):
    if depth > maxd:
        return
    for addr, (cnt, tot, sub) in merge(kids).items():
        nm = ("INT $%06x" % -addr) if addr < 0 else "$%06x" % addr
        print("  " * depth + f"{nm} x{cnt} incl={tot}")
        show(sub, depth + 1)


print("$%06x x1 incl=%d" % (fs, root.end - root.step))
show(root.kids, 1)

# flat counts of all call targets within the frame
c = collections.Counter(r[2] & 0xFFFFFF for r in recs[a:b] if r[4] == KCALL)
print("\nFLAT call-target counts in frame:")
print(" ".join(f"${t:06x}:{n}" for t, n in sorted(c.items())))
