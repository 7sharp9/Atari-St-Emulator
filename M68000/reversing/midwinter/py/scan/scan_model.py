"""Model of Midwinter's terrain cell scan ($16cf6 and the arms it calls): which cells, in what order.
Cells are (x, y) offsets from the camera cell in world cells (+x east, +y north = grid row - 1)."""
# Tables read from the game ($17140 words, $17150 gate words, $172d0 octant flags); kept here as literals.
WIDTH = [0, 1, 2, 3, 4, 5, 4, 2]        # $17140: side-extension count per ring (word p of the table)
DIAG_GATE = [1, 1, 1, 1, 1, 1, 0, 0]    # $17150: does ring p have the diagonal corner cells
OCT = [                                  # $172d0, 12 flag bytes per heading octant -> $172c4..$172cf
 [1,1,1,1,255,0,0,0,0,1,1,1], [1,1,1,1,1,1,0,0,0,0,255,1], [1,1,1,1,1,1,1,255,0,0,0,0],
 [0,255,1,1,1,1,1,1,1,0,0,0], [0,0,0,1,1,1,1,1,1,1,255,0], [0,0,0,0,255,1,1,1,1,1,1,1],
 [1,255,0,0,0,0,1,1,1,1,1,1], [1,1,1,0,0,0,0,255,1,1,1,1]]
def octant(h): return (h & 0x3fe) >> 7
def scan(h, width=WIDTH, gate=DIAG_GATE, octs=OCT):
    f = octs[octant(h)]
    out = [(0, 0)]
    for p in range(8):
        k = p + 1; n = width[p]
        out.append((0, k))                                     # $161f6: arm north
        if n:
            if f[0]:  out += [(i, k) for i in range(1, n+1)]   # $15a96 east along the north side
            if f[11]: out += [(-i, k) for i in range(1, n+1)]  # $15b82 west
        out.append((k, 0))                                     # $163ba: arm east
        if n:
            if f[3]:  out += [(k, -i) for i in range(1, n+1)]  # $15f32 south along the east side
            if f[2]:  out += [(k, i) for i in range(1, n+1)]   # $15e46 north
        out.append((0, -k))                                    # $1657e: arm south
        if n:
            if f[6]:  out += [(-i, -k) for i in range(1, n+1)] # $15d5a west along the south side
            if f[5]:  out += [(i, -k) for i in range(1, n+1)]  # $15c6e east
        out.append((-k, 0))                                    # $16742: arm west
        if n:
            if f[9]:  out += [(-k, i) for i in range(1, n+1)]  # $1601e north along the west side
            if f[8]:  out += [(-k, -i) for i in range(1, n+1)] # $1610a south
        if gate[p]:                                            # $16906,$16a02,$16afe,$16bfa: corner cells
            for fi, c in ((1, (k, k)), (4, (k, -k)), (7, (-k, -k)), (10, (-k, k))):
                if f[fi] and f[fi] < 128: out.append(c)        # flag 255: vertices only, no list entry
    return out
