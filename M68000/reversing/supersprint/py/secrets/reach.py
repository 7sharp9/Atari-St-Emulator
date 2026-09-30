"""reach.py - static reachability over the Super Sprint TEXT (ss.asm + ss.img).

Nodes = every `link A6` address, plus every direct call/jump/PC-relative/immediate target that lands in
TEXT and is not inside a link-function extent start (ISRs, crt0 pieces).  A node's extent runs to the next node.
Edges = jsr/bsr/jmp/bra/Bcc targets, `d(PC) == $x`, jsr/jmp/pea/lea d(A5) (thunk -> target), absolute long
immediates / absolute .l operands that land on a node start, plus longwords found in DATA/BSS-init regions and in
the TEXT bytes that point at a node start (function-pointer tables).
Roots: TEXT start (crt0), thunk entries referenced by `d(A5)`, ISR installs are found by immediates.

    python reach.py            -> prints the unreached nodes with size and classification hints
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sscfg

TEXT0, TEXT1, DATA1 = 0xA304, 0x1BFD0, 0x1C4F2
ASM = os.path.join(sscfg.WORK, 'ss.asm')
THUNKS = os.path.join(sscfg.WORK, 'thunks.txt')

line_re = re.compile(r'^\s+\$([0-9a-f]+): (.*)$')


def load():
    ins = []
    for l in open(ASM):
        m = line_re.match(l.rstrip('\n'))
        if m:
            a = int(m.group(1), 16)
            if a < TEXT1:
                ins.append((a, m.group(2)))
    return ins


def thunks():
    t = {}
    for l in open(THUNKS):
        p = l.split()
        t[int(p[0].split('(')[0])] = int(p[1].lstrip('$'), 16)
    return t


ADDR = re.compile(r'\$([0-9a-f]{3,8})')


def refs_of(a, txt, th):
    """return list of (kind, target)"""
    out = []
    mn = txt.split()[0]
    m = re.search(r'== \$([0-9a-f]+)', txt)
    if m and mn in ('jsr', 'jmp', 'bsr', 'pea', 'lea', 'move.l', 'movea.l'):
        out.append(('pcrel', int(m.group(1), 16)))
    elif m:
        out.append(('local', int(m.group(1), 16)))
    m = re.search(r'(-?\d+)\(A5\)', txt)
    if m and mn in ('jsr', 'jmp', 'pea', 'lea'):
        d = int(m.group(1))
        out.append(('thunk', d))
    if mn in ('jsr', 'jmp', 'bsr', 'bra', 'beq', 'bne', 'blt', 'ble', 'bgt', 'bge', 'bcc', 'bcs', 'bpl', 'bmi', 'bhi', 'bls', 'bvc', 'bvs', 'dbf', 'dbra'):
        m = re.search(r'\$([0-9a-f]+)(\.l)?\s*$', txt)
        if m and '(' not in txt and '== ' not in txt:
            out.append(('direct', int(m.group(1), 16)))
    # immediates / absolute longs in TEXT range
    for m in re.finditer(r'#\$([0-9a-f]{4,8})', txt):
        v = int(m.group(1), 16)
        if TEXT0 <= v < TEXT1 and mn in ('move.l', 'movea.l', 'pea', 'lea', 'cmpi.l', 'cmp.l'):
            out.append(('imm', v))
    for m in re.finditer(r'(?<![#\w])\$([0-9a-f]{4,8})\.l', txt):
        v = int(m.group(1), 16)
        if TEXT0 <= v < TEXT1:
            out.append(('abs', v))
    return out


def main():
    ins = load()
    th = thunks()
    addrs = [a for a, _ in ins]
    links = [a for a, t in ins if t.startswith('link')]
    raw = open(sscfg.IMG, 'rb').read()
    # data-word references (function pointer tables): any aligned longword in TEXT/DATA equal to a link addr
    linkset = set(links)
    dataref = {}
    for off in range(0, len(raw) - 3, 2):
        v = int.from_bytes(raw[off:off + 4], 'big')
        if v in linkset:
            dataref.setdefault(v, []).append(TEXT0 + off)
    # node set
    nodes = set(links)
    edges_raw = []  # (site, kind, tgt)
    for a, t in ins:
        for k, v in refs_of(a, t, th):
            edges_raw.append((a, k, v))
    for a, k, v in edges_raw:
        if k in ('direct', 'pcrel', 'imm', 'abs') and TEXT0 <= v < TEXT1:
            # only calls / jumps / pcrel / imm create nodes; plain local branches stay inside extent
            pass
    # thunk targets are nodes
    for d, tgt in th.items():
        nodes.add(tgt)
    # call-type targets not at a link (ISRs etc)
    for a, t in ins:
        mn = t.split()[0]
        if mn in ('jsr', 'bsr'):
            for k, v in refs_of(a, t, th):
                if k in ('direct', 'pcrel', 'abs'):
                    nodes.add(v)
    for a, k, v in edges_raw:
        if k in ('imm',) or (k == 'pcrel'):
            if TEXT0 <= v < TEXT1:
                nodes.add(v)
    nodes.add(TEXT0)
    nl = sorted(n for n in nodes if TEXT0 <= n < TEXT1)
    import bisect

    def node_of(addr):
        i = bisect.bisect_right(nl, addr) - 1
        return nl[i]
    edges = {n: set() for n in nl}
    usedthunks = set()
    for a, k, v in edges_raw:
        src = node_of(a)
        if src == TEXT0 and a < 0xA562:
            continue   # the thunk table's own jmp.l are not edges: a thunk is live only through a d(A5) user
        if k == 'thunk':
            usedthunks.add(v)
            if v in th:
                edges[src].add(node_of(th[v]))
        elif TEXT0 <= v < TEXT1:
            edges[src].add(node_of(v))
    # thunk table region itself is one node (TEXT0..); its own jmp.l edges only reached if the thunk is used
    thunk_node = TEXT0
    for d, tgt in th.items():
        pass
    # data refs: only count if the referencing longword's location is in a node that's reachable? treat as roots later
    dataedges = []
    for v, locs in dataref.items():
        for loc in locs:
            dataedges.append((loc, v))
    # reachability
    seen = set()
    stack = [0xA562]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for e in edges.get(n, ()):
            if e not in seen:
                stack.append(e)
    # data-table refs: a longword at loc pointing to link v.  If loc is in a reachable node's extent or in DATA, mark v
    changed = True
    while changed:
        changed = False
        for loc, v in dataedges:
            src = node_of(loc) if loc < TEXT1 else None
            if (src is None or src in seen) and node_of(v) not in seen:
                st = [node_of(v)]
                while st:
                    n = st.pop()
                    if n in seen:
                        continue
                    seen.add(n)
                    changed = True
                    st.extend(edges.get(n, ()))
    unreached = [n for n in nl if n not in seen]
    ends = {n: (nl[i + 1] if i + 1 < len(nl) else TEXT1) for i, n in enumerate(nl)}
    print('nodes', len(nl), 'reached', len(seen), 'unreached', len(unreached))
    print('used thunk offsets', len(usedthunks), 'of', len(th))
    print('unused thunks:', sorted(set(th) - usedthunks))
    tot = 0
    for n in unreached:
        sz = ends[n] - n
        tot += sz
        dr = dataref.get(n)
        callers = [hex(a) for a, k, v in edges_raw if v == n and k != 'thunk']
        print('%06x-%06x len %5d  callers=%s dataref=%s' % (n, ends[n], sz, callers, [hex(x) for x in dr] if dr else ''))
    print('unreached bytes', tot)
    # second closure using call-type edges only; nodes reached only through pointer-style refs are listed
    callonly = {n: set() for n in nl}
    ptr_sites = {}
    for a, k, v in edges_raw:
        src = node_of(a)
        if k == 'thunk':
            if v in th:
                callonly[src].add(node_of(th[v]))
        elif TEXT0 <= v < TEXT1:
            mn = dict(ins_map)[a].split()[0] if False else None
    ins_map = dict(ins)
    for a, k, v in edges_raw:
        src = node_of(a)
        if k in ('direct', 'pcrel', 'abs', 'imm', 'local') and TEXT0 <= v < TEXT1:
            mn = ins_map[a].split()[0]
            if k == 'imm' or (k == 'pcrel' and mn in ('pea', 'lea', 'move.l', 'movea.l')) or (k == 'abs' and mn in ('pea', 'lea', 'move.l', 'movea.l')):
                ptr_sites.setdefault(node_of(v), []).append(a)
            elif k != 'local':
                callonly[src].add(node_of(v))
    seen2 = set()
    st = [0xA562]
    while st:
        n = st.pop()
        if n in seen2:
            continue
        seen2.add(n)
        st.extend(callonly.get(n, ()))
    print('--- reached ONLY via pointer-style refs (imm / lea / pea / move.l #), not via jsr/jmp/thunk:')
    for n in nl:
        if n in seen and n not in seen2:
            print('%06x len %4d pointer sites %s dataref %s' % (n, ends[n] - n, [hex(x) for x in ptr_sites.get(n, [])], [hex(x) for x in dataref.get(n, [])]))
    print('--- thunk targets used ONLY as function pointers / never called:')


if __name__ == '__main__':
    main()
