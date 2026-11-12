"""bsp_order.py - compare the game's own BSP drawing order with py/render/model.py's walk, for every far-routine ($8e68)
model draw in a run.

usage: bsp_order.py <snap> [steps] [outjson] [poke=<hexaddr>:<width>:<hexvalue> ...]   (run from M68000/; the stserver.dll in server/bin)
For each entry to $8e68 the probe (own stserver process) stops at:
  $8e8c (first arrival, after $940a): reads the view-space vertex table at ($8de), the game's plane side flags at ($8e2),
         the object centre $a7c/$a80/$a84 and A0 = the BSP stream start;
  $8ee0 every leaf item visited (A0 = its flag byte), $8ef4 every back-face result (D0 of $9426),
  $8f14 / $8f9e every polygon filled (A0 = its index list; $8f14 the clipping path that writes $9de, $8f9e the
         unclipped path $44a6 that does not), and the routine's return address.
Then it runs model.py's walk (side flags and face tests from the same vertices and centre) and compares, per draw:
plane flags, the visited item sequence, the polygon sequence, and the sign of every back-face result."""
import pathlib as _pl, sys as _sys, json, struct
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'render')); _sys.path.insert(0, str(_here))
from ccpaths import *
_sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer
import model as M
from bsp_survey import tree

args = [a for a in _sys.argv[1:] if not a.startswith('poke=')]
# poke=<hexaddr>:<width>:<hexvalue>, applied after the load and again at every $8e68 stop (so a game rewrite of an
# object's angle between frames is undone before the next frame's object pass)
pokes = [tuple(int(x, 16) if i != 1 else int(x) for i, x in enumerate(a[5:].split(':'))) for a in _sys.argv[1:] if a.startswith('poke=')]
snap = args[0]; budget = int(args[1]) if len(args) > 1 else 600000
outp = _pl.Path(args[2]) if len(args) > 2 else WORK / 'infographics' / 'bsp' / 'order.json'
s = StServer(str(ROOT)); s('load', snapshot=snap)
def do_pokes():
    for a, w, v in pokes: s('poke', addr=a, width=w, value=v)
do_pokes()
H = lambda v: int(str(v).lstrip('$'), 16)
def s16(v): v &= 0xffff; return v - 65536 if v & 0x8000 else v
def s32(v): v &= 0xffffffff; return v - (1 << 32) if v & 0x80000000 else v
tab = s.read(0x4c4ce, 4 * 99); ids = {struct.unpack_from('>I', tab, 4 * i)[0]: i for i in range(99)}
s('bp_set', addrs=[0x8e68])
draws = []; left = budget; step0 = int(s('regs')['step'])
while left > 0:
    r = s('run', max_steps=left); left -= r['steps']
    if r['reason'] != 'breakpoint': break
    do_pokes()
    rg = s('regs'); a0 = H(rg['a0']); mid = ids.get(a0 - 4, ids.get(a0 - 8))   # $9066 enters $8e68 past its LOD long
    sp = H(rg['a7']); ret = struct.unpack('>I', s.read(sp, 4))[0]
    d = dict(model=mid, addr=a0 - 4, step=int(rg['step']), ret=ret, items=[], faces=[], polys=[])
    s('bp_clear'); s('bp_set', addrs=[0x8e8c, 0x8ee0, 0x8ef4, 0x8f14, 0x8f9e, ret])
    first = True
    while True:
        r = s('run', max_steps=200000); left -= r['steps']
        if r['reason'] != 'breakpoint': d['error'] = r; break
        rg = s('regs'); pc = H(rg['pc'])
        if pc == ret: break
        if pc == 0x8e8c and first:
            first = False
            vtp = struct.unpack('>I', s.read(0x8de, 4))[0]; flp = struct.unpack('>I', s.read(0x8e2, 4))[0]
            raw = s.read(vtp, 6 * 128)
            d['vt'] = [tuple(s16(struct.unpack_from('>h', raw, 6 * i + 2 * k)[0]) for k in range(3)) for i in range(128)]
            d['flags'] = list(s.read(flp, 72)); d['bsp'] = H(rg['a0'])
            d['c'] = [s32(struct.unpack('>I', s.read(a, 4))[0]) for a in (0xa7c, 0xa80, 0xa84)]
            d['clipflag'] = s.read(0x121a, 1)[0]
        elif pc == 0x8ee0:
            # an interrupt taken at the breakpoint returns to it and stops there again: drop the repeat (the walk
            # advances A0 past every item, so the same item twice in a row is never a real second visit)
            if d['items'] and d['items'][-1] == H(rg['a0']): d['reentry'] = d.get('reentry', 0) + 1
            else: d['items'].append(H(rg['a0']))
        elif pc == 0x8ef4:
            # one face test per item: a second stop for the same item is the same interrupt re-entry
            if len(d['faces']) == len(d['items']): d['reentry'] = d.get('reentry', 0) + 1
            else: d['faces'].append(s32(H(rg['d0'])))
        elif pc in (0x8f14, 0x8f9e):
            if d['polys'] and d['polys'][-1][0] == H(rg['a0']): d['reentry'] = d.get('reentry', 0) + 1
            else: d['polys'].append((H(rg['a0']), pc))
        s('step', n=1)
    draws.append(d)
    s('bp_clear'); s('bp_set', addrs=[0x8e68])
s.close()

# ---- compare with model.py -------------------------------------------------------------------
RAM = M.RAM
tot = dict(draws=0, flags=0, flags_ok=0, items=0, items_ok=0, polys=0, polys_ok=0, faces=0, faces_ok=0, seq_ok=0)
per = {}; HDR = {}
MODEL_ADDR = {i: a for a, i in ids.items()}
for d in draws:
    if 'bsp' not in d or d['model'] is None: continue
    # model.py reads stream bytes from the anchor RAM: they must be the same bytes the game walks
    m = dict(vt=d['vt'], bsp=d['bsp'])
    # planes and stream start from model.py's own header parse (builder run by callcap from c_s30.snap)
    if d['model'] not in HDR:
        pm_ = M.parse(MODEL_ADDR[d['model']], M.build(MODEL_ADDR[d['model']]))
        HDR[d['model']] = (pm_['planes'], pm_['bsp'])
    m['planes'], hbsp = HDR[d['model']]; np_ = len(m['planes'])
    assert hbsp == d['bsp'], (d['model'], hex(hbsp), hex(d['bsp']))   # the game walks the stream model.py decodes
    c = tuple(d['c'])
    want_flags = [0xff if M.dot(d['vt'], t, c) >= 0 else 0 for t in m['planes']]
    got_flags = d['flags'][:np_]
    # model.py's walk, instrumented: visited items, face results, polygon index-list addresses
    seq_items, seq_polys, seq_faces = [], [], []
    # node planes >= np are not planes: $940a sets entry 64 to $ff (st 64(A2)) and builders such as $a60a set 65
    # (sle/seq 65(A2)); those entries are taken from the game's own table, the rest computed here
    flags = [f == 0xff for f in want_flags] + [False] * (72 - np_)
    for k in range(np_, 72): flags[k] = d['flags'][k] == 0xff
    pseudo = set()
    def leaf(p):
        n = RAM[p]; p += 1
        for _ in range(n):
            seq_items.append(p); f = RAM[p]; p += 1
            if f & 1:
                tri = RAM[p:p+3]; p += 3; end = p + RAM[p]; p += 1
                v = M.dot(d['vt'], tri, c); seq_faces.append(v)
                if v < 0: p = end; continue
            if f & 2:
                k = RAM[p]; p += 1
                for _ in range(k):
                    nv = RAM[p]; p += 1; seq_polys.append(p); p += nv + 1
            if f & 4: k = RAM[p]; p += 1 + 3 * k
            if f & 8: k = RAM[p]; p += 1 + 4 * k
        return p
    def node(p):
        b = RAM[p]
        if b & 0x80: return leaf(p + 1)
        off = (RAM[p+1] << 8) | RAM[p+2]; a = p + 3
        if b >= np_: pseudo.add((b, d['flags'][b]))
        if flags[b]: node(a); return node(a + off)
        node(a + off); return node(a)
    try: node(d['bsp'])
    except IndexError: print('walk failed: model', d['model'], 'planes', np_, 'step', d['step']); raise
    def ctl_node(p, out):
        b = RAM[p]
        if b & 0x80:
            return
        off = (RAM[p+1] << 8) | RAM[p+2]; a = p + 3
        order = (a + off, a) if flags[b] else (a, a + off)
        for q in order: ctl_node(q, out)
    rev = []
    def rnode(p):
        b = RAM[p]
        if b & 0x80:
            q = p + 1; n = RAM[q]; q += 1
            for _ in range(n):
                f = RAM[q]; q += 1
                if f & 1:
                    tri = RAM[q:q+3]; q += 3; end = q + RAM[q]; q += 1
                    if M.dot(d['vt'], tri, c) < 0: q = end; continue
                if f & 2:
                    k = RAM[q]; q += 1
                    for _ in range(k):
                        nv = RAM[q]; q += 1; rev.append(q); q += nv + 1
                if f & 4: k = RAM[q]; q += 1 + 3 * k
                if f & 8: k = RAM[q]; q += 1 + 4 * k
            return
        off = (RAM[p+1] << 8) | RAM[p+2]; a = p + 3
        if flags[b]: rnode(a + off); rnode(a)
        else: rnode(a); rnode(a + off)
    rnode(d['bsp'])
    gp = [a for a, _ in d['polys']]
    fo = sum(1 for g, w in zip(d['faces'], seq_faces) if (g < 0) == (w < 0)) if len(d['faces']) == len(seq_faces) else 0
    io = sum(1 for g, w in zip(d['items'], seq_items) if g == w) if len(d['items']) == len(seq_items) else 0
    po = sum(1 for g, w in zip(gp, seq_polys) if g == w) if len(gp) == len(seq_polys) else 0
    same = gp == seq_polys and d['items'] == seq_items and got_flags == want_flags
    d['cmp'] = dict(pseudo=sorted(pseudo), rev_differs=(rev != [a for a, _ in d['polys']]), np=np_, want_flags=want_flags, got_flags=got_flags, model_items=seq_items, model_polys=seq_polys,
                    model_faces=seq_faces, items_ok=io, polys_ok=po, faces_ok=fo, same=same)
    tot['ctl_rev_differs'] = tot.get('ctl_rev_differs', 0) + (np_ > 0 and d['cmp']['rev_differs']); tot['draws_with_planes'] = tot.get('draws_with_planes', 0) + (np_ > 0)
    tot['neg_faces'] = tot.get('neg_faces', 0) + sum(v < 0 for v in seq_faces)
    tot['fast_path'] = tot.get('fast_path', 0) + sum(pc == 0x8f9e for _, pc in d['polys'])
    tot['reentry_dropped'] = tot.get('reentry_dropped', 0) + d.get('reentry', 0)
    tot['draws'] += 1; tot['flags'] += np_; tot['flags_ok'] += sum(a == b for a, b in zip(got_flags, want_flags))
    tot['items'] += len(seq_items); tot['items_ok'] += io; tot['polys'] += len(seq_polys); tot['polys_ok'] += po
    tot['faces'] += len(seq_faces); tot['faces_ok'] += fo; tot['seq_ok'] += same
    pm = per.setdefault(d['model'], [0, 0, 0]); pm[0] += 1; pm[1] += same; pm[2] += len(gp)
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(dict(snap=str(snap), budget=budget, step0=step0, draws=draws), indent=0))
print('snap', snap, 'steps', budget, 'from step', step0)
print('per model (draws, identical, polygons):', dict(sorted(per.items())))
print('totals', tot)
for d in draws:
    if 'cmp' in d and not d['cmp']['same']:
        print('MISMATCH model', d['model'], 'step', d['step'], d['cmp']['got_flags'], d['cmp']['want_flags'],
              [hex(a) for a, _ in d['polys']][:8], [hex(a) for a in d['cmp']['model_polys']][:8])
for d in draws:
    if 'cmp' in d and d['cmp']['np']: print('model', d['model'], 'step', d['step'], 'flags', d['cmp']['got_flags'], 'c', d['c'], 'polys', len(d['polys']))
print('wrote', outp)
