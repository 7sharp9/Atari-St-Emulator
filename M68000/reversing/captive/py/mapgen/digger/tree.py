"""Tree census of the digger's carved bases (reversing/captive/mapgen.md, "The digger and rooms").

    uv run python -I <this dir>/dig.py tree <capture.bin> [...]

Reads the emulator's module block at the return from $244b6 (dig_capture.py records). A cell is carved when
0 < G0 < $ff00 (the digger's dig numbers; $ffff is a block wall). Its floor is the block table byte (module bytes
0..15). Graph edges: two orthogonally adjacent carved cells on the same floor; with lifts, also a lift cell on floor k
with an up feature (4, 6, $35, $37) and the cell at (x, y) + the pair's offset (16/24(A6)) on floor k + 1 when that
cell is carved with a down feature (5, 6, $36, $37); and the shafts: consecutive entries of one 13410(A6) group (5
groups of 5 (x, y) byte pairs, one per floor, $ffff unused; placed by $245e2 before the digger), when both are carved.
The flow field $24f4c routes through exactly these ($2503c gives the group's cells 4 or 5). The cyclomatic number E - V + C is 0 exactly when every
connected component is a tree (V = E + 1 per component).

Three views: raw cells; rooms contracted (each 4-connected set of room-floor cells, features $1f $33 $35 $36 $37, is
one node); rooms and structures contracted (also each set of feature $11/$14 cells, the $24c5c blob). Cell-to-cell
adjacencies between two different nodes each count as an edge, so a corridor touching a room twice is a cycle.
"""
UP = (0x04, 0x06, 0x35, 0x37)    # lift ends written by $24902/$248f0 (up, both, and on room floor)
DOWN = (0x05, 0x06, 0x36, 0x37)
ROOM = (0x1f, 0x33, 0x35, 0x36, 0x37)
BLOB = (0x11, 0x14)


def w(b, o):
    return (b[o] << 8) | b[o + 1]


def sw(b, o):
    v = w(b, o)
    return v - 0x10000 if v & 0x8000 else v


def graph(post):
    g0 = [w(post, 56 + 2 * i) for i in range(2048)]
    ft = [post[4168 + 2 * i + 1] for i in range(2048)]
    fl = [post[(((i >> 6) & 0x18) << 3 | (i & 63)) >> 4] for i in range(2048)]
    cells = [i for i in range(2048) if 0 < g0[i] < 0xff00]
    cs = set(cells)
    adj = []
    for i in cells:
        x, y = i & 63, i >> 6
        if x < 63 and i + 1 in cs and fl[i + 1] == fl[i]:
            adj.append((i, i + 1))
        if y < 31 and i + 64 in cs and fl[i + 64] == fl[i]:
            adj.append((i, i + 64))
    lifts = []
    bad = 0
    for i in cells:
        if ft[i] in UP:
            k = fl[i]
            ox, oy = sw(post, 16 + 2 * (k - 1)), sw(post, 24 + 2 * (k - 1))
            x, y = (i & 63) + ox, (i >> 6) + oy
            j = y * 64 + x
            if 0 <= x < 64 and 0 <= y < 32 and j in cs and fl[j] == k + 1 and ft[j] in DOWN:
                lifts.append((i, j))
            else:
                bad += 1
    for g in range(5):
        prev = None
        for e in range(5):
            o = 13410 + 10 * g + 2 * e
            if w(post, o) == 0xffff:
                continue
            j = post[o + 1] * 64 + post[o]
            if prev is not None and prev in cs and j in cs:
                lifts.append((prev, j))
            prev = j
    return cells, ft, adj, lifts, bad


def cyclomatic(nodes, edges):
    par = {n: n for n in nodes}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    c = len({find(n) for n in nodes})
    return len(edges) - len(nodes) + c, c


def contract(cells, ft, adj, classes):
    """Map each cell to a node: one per 4-connected same-class region, else the cell itself."""
    node = {i: i for i in cells}
    for cl in classes:
        par = {i: i for i in cells if ft[i] in cl}

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for a, b in adj:
            if a in par and b in par:
                par[find(a)] = find(b)
        for i in par:
            node[i] = ('r', id(cl), find(i))
    return node


def census(recs):
    """Views: raw cells; each room instance and each structure blob instance contracted to one node (instances from
    the port's carve tags, used only where the port's block equals the emulator's). Pre-placed cells (carved before
    $244b6, by $245e2) are kept as nodes."""
    from dig import Dig
    views = {}
    nb = nmis = badl = 0
    comps, srcs, kinds = {}, {}, {}
    for seed, d2, steps, regs, pre, post in recs:
        d = Dig(pre)
        d.run()
        if bytes(d.m) != post:
            nmis += 1
            continue
        nb += 1
        cells, ft, adj, lifts, bad = graph(post)
        badl += bad
        for i in cells:
            k = d.tag.get(i, ('pre', None))[0]
            kinds[k] = kinds.get(k, 0) + 1
        for name, contr in (('raw', ()), ('rooms+blobs', ('room', 'blob'))):
            node = {}
            for i in cells:
                t = d.tag.get(i, ('pre', None))
                node[i] = t if t[0] in contr else i
            nodes = set(node.values())
            for lname, extra in (('no lifts', []), ('lifts', lifts)):
                par = {x: x for x in nodes}

                def find(a):
                    while par[a] != a:
                        par[a] = par[par[a]]
                        a = par[a]
                    return a
                cyc = 0
                for a, b in adj + extra:
                    na, nb_ = node[a], node[b]
                    if na == nb_:
                        continue
                    ra, rb = find(na), find(nb_)
                    if ra == rb:
                        cyc += 1
                        if name != 'raw':
                            key = (lname,) + tuple(sorted(d.tag.get(c, ('pre', None))[0] for c in (a, b)))
                            srcs.setdefault(key, []).append(seed)
                    else:
                        par[ra] = rb
                c = len({find(x) for x in nodes})
                v = views.setdefault((name, lname), [0, 0])
                v[0] += cyc == 0
                v[1] += cyc
                if name != 'raw' and lname == 'lifts':
                    dig_nodes = {find(node[i]) for i in cells if d.tag.get(i, ('pre',))[0] != 'pre'}
                    comps[len(dig_nodes)] = comps.get(len(dig_nodes), 0) + 1
    print(f'{nb} bases (port block = emulator block; {nmis} skipped); lift up-cells without a carved down partner: '
          f'{badl}')
    print('  carved cells by the routine that carved them:', kinds)
    for (name, lname), (ntree, tot) in views.items():
        print(f'  {name:12s} {lname:9s} forest (E - V + C = 0) in {ntree}/{nb} bases; cycles summed {tot}')
    print('  components holding digger-carved cells (rooms+blobs, lifts):', dict(sorted(comps.items())))
    print('  cycle-closing edges by the carving routines of their two cells (count, first seeds):')
    for k, v in sorted(srcs.items()):
        print(f'    {k}: {len(v)} {sorted(set(v))[:6]}')
