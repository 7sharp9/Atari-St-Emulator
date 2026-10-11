#!/usr/bin/env python3
"""Draw PowerMonger's entity mode graph from out/mode_edges.json (run mode_edges.py first).

usage: build_fsm.py            writes out/fsm_jobs.{dot,svg,png} and out/fsm_army.{dot,svg,png}

Edges are derived from the extracted mode-byte writes only (no edge is typed by hand):
  - a write `31 := Y` gets the previous-mode writes `30 := P` whose nearest mode write (by address, same walk) it is;
  - Y == $10 with prev P: a walk ($10 advance / $12 leg) that ends in mode P, because the arrival `$14fdc` copies byte
    30 into byte 31 (dashed edge S -> P);
  - Y != $10: a direct transition S -> Y (solid); if Y's own handler then writes an unpaired `31 := $10`, Y dwells and
    walks on, ending in the pending prev P (dashed Y -> P);
  - an unpaired `30 := P`: a previous-mode stamp, taken at the record's next walk arrival (dashed, "prev");
  - a dynamic `31 := D0` at $14ef6 is the walk-path terminator `$7d02 + n` of the path the man walks; the two paths
    ever loaded (`farm` $168ee+$50, `pots` $168ee+$76, ai.md walk-path row) are read from the RAM image here;
  - a call from a mode handler (directly or through non-hub callees, depth 2) to a hub routine: dotted edge;
  - a hub's writes on another record (A0/A3/A4, or A1 after a reload) carry the role in the edge label.
Evidence (node fill) is taken from the gates named in ai.md / economy.md, listed in EVID below with their source.
"""
import json, os, struct, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
work = os.environ.get('PM_WORK') or os.path.join(root, 'scratchpad/pm_fig')
out = os.path.join(work, 'out')
D = json.load(open(os.path.join(out, 'mode_edges.json')))
ram = open(os.path.join(root, D['ram']), 'rb').read()

# ---------------------------------------------------------------- labels (ai.md mode tables, economy.md 2a, orig.sym)
LABEL = {
    0x00: 'idle', 0x02: 'afloat step', 0x04: 'in rank (alias)', 0x06: 'in rank: march\\nwith the lead', 0x08: 'lost: walk to\\nrank slot',
    0x0a: 'pre-move dwell', 0x0c: 'load walk path', 0x0e: 'walk the path', 0x10: 'advance to target', 0x12: 'moving leg',
    0x14: 'at the meeting', 0x16: 'farmer home', 0x18: 'farmer at field', 0x1a: 'take food\\nfrom a town', 0x1c: 'get men:\\nsummon the town',
    0x1e: 'go-to arrival', 0x20: 'sit at camp seat', 0x22: 'set men to work', 0x24: 'farmer walks home', 0x26: 'supply line:\\nback to the cell',
    0x28: 'wait for recruits', 0x2a: 'recruit joins', 0x2c: 'pick a target', 0x2e: 'reached the target', 0x30: 'attack arrival',
    0x32: 'melee', 0x34: 'shot cool-down', 0x36: 'chase an animal', 0x38: 'slaughter', 0x3a: 'tree target\\narrival',
    0x3c: 'run away (rout)', 0x3e: 'find a tree', 0x40: 'go to the house\\n(build)', 0x42: 'deliver at\\nWorkShop', 0x44: 'fell the tree',
    0x46: 'dwell, then walk', 0x48: 'obstacle sweep', 0x4a: 'set up sweep', 0x4c: 'captain back\\nat town', 0x4e: 'merchant at\\nhome lord',
    0x50: 'merchant at\\nfar lord', 0x52: 'merchant waits', 0x54: 'merchant\\nstarts a trip', 0x56: 'fisher: go to\\nfishing cell',
    0x58: 'fisher settles', 0x5a: 'fisher: look\\nfor the catch', 0x5c: 'fisher heads home', 0x5e: 'fisher arrives', 0x60: 'fisher delivers\\n(food +4)',
    0x62: 'fisher idle', 0x66: 'at the animal', 0x68: 'resting in camp', 0x6a: 'work spot reached:\\nhead for the deposit', 0x6c: 'lone-man get men',
    0x6e: 'take equipment', 0x72: 'food pile pickup', 0x74: 'supply line:\\ndrop food', 0x76: 'offer alliance', 0x78: 'trade',
    0x7a: 'spy arrives', 0x7c: 'winter park\\n(heartbeat)', 0x7e: 'idle at home\\n(heartbeat)', 0x80: 'shepherd at town',
    0x82: 'shepherd at gate:\\nrelease herd', 0x84: 'shepherd waits', 0x86: 'shepherd rounds\\nup the herd', 0x88: 'shepherd\\ngoes home',
    0x8a: 'captain resting', 0x8c: 'afloat with Boat', 0x8e: 'equip arrival\\n(fight)', 0x90: 'equip arrival\\n(townee)', 0x92: 'do nothing',
}
HUBS = {
    0x3c08: 'send home\\n(flag-driven regroup)', 0x16892: 'goods regroup', 0x5cde: "lord's work order:\\nstamps each man", 0x600a: 'delivery dispatch',
    0x35f4: 'make camp', 0x34f2: 'town summons', 0x1d70: 'rerank followers', 0x4f68: 'target picker', 0x56a6: 'engage',
    0x5590: 'kill-or-rout roll', 0x4bc8: 'set up the fight', 0x5fa0: 'hand out the\\nwork order',
    0x3154: 'order: walk to a town', 0x3248: 'order $08 on a man', 0x3888: 'order $02 go to', 0x38ce: 'order $06 on a cell',
    0x390e: 'order $1a supply line', 0x4a7a: 'order $0c march\\n& engage', 0x6128: 'order $10 on a cell', 0x3956: 'supply line leg',
    0x3da4: 'spy joins town',
}
# role of a hub's write on a record other than the one in A1 (from the routine bodies, ai.md / strategy.md)
ROLE = {(0x35f4, 'A0'): 'each member', (0x35f4, 'A1*'): 'the lead', (0x34f2, 'A1*'): "the town's men",
        (0x1d70, 'A1*'): 'each follower', (0x56a6, 'A3'): 'the target', (0x5590, 'A3'): 'the target',
        (0x5cde, 'A4'): "the lord's men", (0x5fa0, 'A4'): "the lord's men", (0x4bc8, 'A3'): 'the other party',
        (0x3154, 'A1*'): 'the lead', (0x3888, 'A1*'): 'the lead', (0x390e, 'A1*'): 'the lead', (0x4a7a, 'A1*'): 'the lead',
        (0x6128, 'A1*'): 'the lead', (0x3248, 'A0'): 'the lead', (0x38ce, 'A0'): 'the lead'}
# D2/D4 register sources, read from the call sites (mode_edges.json 'calls' + text.lst): see fsm.facts.md
DYN = {(0x16892, '30', 'D2'): [0x8e, 0x90], (0x5cde, '31', 'D2'): [0x40, 0x3e, 0x6a], (0x5fa0, '31', 'D2'): [0x40, 0x3e, 0x6a],
       (0x3154, '30', 'D4'): [0x1a, 0x1c, 0x22, 0x6e, 0x76, 0x78, 0x7a]}

# ---------------------------------------------------------------- evidence (source: ai.md / economy.md / pm_fsm_ref.py)
P_REF = {0x02, 0x04, 0x06, 0x08, 0x0e, 0x10, 0x12, 0x32, 0x68, 0x7c, 0x8a}            # pm_fsm_ref.py index, ai.md Proven blocks
P_FSM15 = {0x14, 0x16, 0x18, 0x24, 0x1a, 0x1c, 0x1e, 0x20, 0x26, 0x28, 0x2a, 0x2c, 0x30, 0x34, 0x2e, 0x36, 0x66, 0x38, 0x3a,
           0x3c, 0x3e, 0x40, 0x44, 0x46, 0x6a, 0x48, 0x4a, 0x4c, 0x4e, 0x50, 0x52, 0x54, 0x5e, 0x56, 0x58, 0x62, 0x5a, 0x5c,
           0x60, 0x72, 0x64, 0x70, 0x7e, 0x8e, 0x90}                                 # ai.md "$15000 page" table
P_SHEP = {0x80, 0x82, 0x84, 0x86, 0x88}                                                # gate_shepherd.py
P_OTHER = {0x42}                                                                       # $600a, gate_orders.py (economy.md 2a)
PROVEN_MODES = P_REF | P_FSM15 | P_SHEP | P_OTHER
PROVEN_HUBS = {0x3c08, 0x16892, 0x5cde, 0x600a, 0x35f4, 0x34f2, 0x1d70, 0x4f68, 0x56a6, 0x5590, 0x4bc8}

COL = {'proven': ('#d9f0d3', '#2e7d32'), 'code': ('#ffffff', '#757575')}
FONT = 'Helvetica'


def hx(v):
    return int(v, 16)


def writes_of(rec, hub=None):
    """[(off, value-or-list, reg, site)] for a walk's mode-byte writes; dynamic sources resolved through DYN."""
    res = []
    for w in rec['writes']:
        reg = w['reg'] + ('*' if w['a1_reloaded'] else '')
        src = w['src']
        if w['size'] == 'w' and src.startswith('#$'):
            v = int(src[2:], 16)
            res.append((31, [(v >> 8) & 0xff], reg, hx(w['site'])))
            res.append((30, [v & 0xff], reg, hx(w['site'])))
            continue
        if src.startswith('#$') or src.startswith('#'):
            v = int(src[2:], 16) if src.startswith('#$') else int(src[1:])
            res.append((w['off'], [v], reg, hx(w['site'])))
        elif hub is not None and (hub, str(w['off']), src) in DYN:
            res.append((w['off'], DYN[(hub, str(w['off']), src)], reg, hx(w['site'])))
        elif hx(w['site']) == 0x14ef6:
            res.append((31, PATH_END, reg, hx(w['site'])))
        # other register sources: the byte-30 copies (save mode) and the $14fdc arrival copy, not edges
    return res


def path_end(cursor):
    a = 0x168ee + cursor
    while True:
        w = struct.unpack_from('>H', ram, a)[0]
        if w >= 0x7d00:
            return w
        a += 4                     # {dx,dy} pairs; the terminator is tested on the first word ($14ea2 movem D0/D1)


PATH_END = []
for cur in (0x50, 0x76):          # the only two cursors ever written to 40(man): $150b0 and $60ca (ai.md walk-path row)
    t = path_end(cur)
    if t >= 0x7d02:
        PATH_END.append(t - 0x7d02)


def pairs(ws):
    """Attach each 30-write to the nearest 31-write of the same register by address."""
    m31 = [w for w in ws if w[0] == 31]
    m30 = [w for w in ws if w[0] == 30]
    got = {i: [] for i in range(len(m31))}
    lone = []
    for p in m30:
        cands = [(abs(p[3] - w[3]), i) for i, w in enumerate(m31) if w[2] == p[2]]
        if cands:
            got[min(cands)[1]].append(p)
        else:
            lone.append(p)
    return [(m31[i], got[i]) for i in range(len(m31))], lone


def closure_calls(rec, depth=1):
    seen, todo, hubs = set(), [(c, 0) for c in rec['calls']], set()
    while todo:
        c, d = todo.pop()
        a = hx(c)
        if a in HUBS:
            hubs.add(a)
            continue
        if c in seen or d >= depth or c not in D['routines']:
            continue
        seen.add(c)
        todo += [(x, d + 1) for x in D['routines'][c]['calls']]
    return hubs


def hub_record(a):
    """A hub's writes: its own walk plus non-hub callees (depth 2)."""
    r = D['routines']['%x' % a]
    ws = writes_of(r, a)
    todo, seen = [(c, 0) for c in r['calls']], set()
    while todo:
        c, d = todo.pop()
        if hx(c) in HUBS or c in seen or d >= 2 or c not in D['routines']:
            continue
        seen.add(c)
        ws += writes_of(D['routines'][c], hx(c))
        todo += [(x, d + 1) for x in D['routines'][c]['calls']]
    # the target picker's arms are a jump table ($4fa2): they are callees of $4f68 itself. The arms share one tail,
    # so the same site is collected once per arm: dedupe.
    ws = sorted(set((o, tuple(v), reg, site) for o, v, reg, site in ws), key=lambda w: w[3])
    return [(o, list(v), reg, site) for o, v, reg, site in ws], closure_calls(r)


def derive():
    """edges: (src, dst, kind, label). kinds: set, walk, prev, call."""
    E = set()
    pending = {}                    # mode Y -> prevs written together with 31 := Y
    unpaired_walk = set()
    srcs = {}
    for m, r in D['modes'].items():
        if r.get('dead'):
            continue
        srcs[('m', hx(m))] = (writes_of(r), closure_calls(r))
    for h in HUBS:
        if '%x' % h in D['routines']:
            srcs[('h', h)] = hub_record(h)
    for (kind, s), (ws, hubs) in srcs.items():
        if kind == 'm':
            ws = [w for w in ws if w[2] == 'A1']
        for (off, ys, reg, site), ps in pairs(ws)[0]:
            role = ROLE.get((s, reg), '' if reg == 'A1' else reg)
            prevs = [v for p in ps for v in p[1]]
            for y in ys:
                if y == 0x10 and prevs:
                    for p in prevs:
                        E.add((kind, s, p, 'walk', role))
                elif y == 0x10:
                    unpaired_walk.add((kind, s))
                    E.add((kind, s, 0x10, 'set', role))
                else:
                    E.add((kind, s, y, 'set', role))
                    for p in prevs:
                        if p != y:
                            pending.setdefault(y, set()).add(p)
        for (off, ps, reg, site) in pairs(ws)[1]:
            role = ROLE.get((s, reg), '' if reg == 'A1' else reg)
            for p in ps:
                E.add((kind, s, p, 'prev', role))
        for h in hubs:
            if h != s:
                E.add((kind, s, h, 'call', ''))
    # the $7d00 terminator ($14efe, mode $92) ends only the fp2 path, which nothing loads (ai.md walk-path row), and
    # $0c only starts the path that $0e walks: keep the terminator edges on $0e alone
    for y in [0x24, 0x6a, 0x92]:
        E.discard(('m', 0x0c, y, 'set', ''))
    E.discard(('m', 0x0e, 0x92, 'set', ''))
    # a mode that dwells and then walks with the prev it was given
    for y, ps in pending.items():
        if ('m', y) in unpaired_walk:
            E.discard(('m', y, 0x10, 'set', ''))
            for p in ps:
                E.add(('m', y, p, 'walk', ''))
    return E


def nid(kind, v):
    return ('m%02x' % v) if kind == 'm' else ('h%x' % v)


def node(kind, v):
    if kind == 'm':
        ev = 'proven' if v in PROVEN_MODES else 'code'
        fill, line = COL[ev]
        return '%s [label="$%02X  %s", shape=box, style="rounded,filled", fillcolor="%s", color="%s"];' % (
            nid(kind, v), v, LABEL.get(v, '?'), fill, line)
    ev = 'proven' if v in PROVEN_HUBS else 'code'
    fill, line = COL[ev]
    return '%s [label="$%X\\n%s", shape=box, style="filled", fillcolor="%s", color="%s", fontsize=10];' % (
        nid(kind, v), v, HUBS[v], fill, line)


def node_label(kind, v):
    return ('$%02X  %s' % (v, LABEL.get(v, '?'))) if kind == 'm' else ('$%X\\n%s' % (v, HUBS[v]))


def write_graph(name, title, lanes, edges, stubs, shared=(), roles=True, adjacent=((0, 1),)):
    """lanes: [(lane name, [row, row, ...])], each row a list of nodes drawn left to right on one rank.

    An edge inside a lane, or from one lane to the next lane down, is drawn as an edge. Any other edge is drawn
    inside one lane against a dashed copy ("ghost") of the far node, so no edge crosses the figure: the ghost
    copies the node of the lane listed in `shared` (the hub lanes), else the far end. A node outside the figure
    becomes the stub `stubs[STUBMAP[node]]`, also as a per-lane ghost."""
    lane_of = {n: i for i, lane in enumerate(lanes) for row in lane[1] for n in row}
    style = {'set': 'style=solid, color="#212121"', 'walk': 'style=dashed, color="#1565c0"',
             'prev': 'style=dashed, color="#6a1b9a"', 'call': 'style=dotted, color="#616161", arrowhead=vee'}
    lines, ghosts = [], {}                  # ghosts: lane -> {gid: (label, is_routine)}

    def ghost(lane, n, incoming):
        """incoming: the ghost is an edge source (placed at the start of the lane's first row), else at the end."""
        if n in lane_of:
            gid = 'g%d_%s' % (lane, nid(*n))
            lab = node_label(*n).replace('  ', ' ').split('\\n')
            lab = (lab[0] + ' ' + lab[1]).rstrip(':') if n[0] == 'h' else ' '.join(lab)
            ghosts.setdefault(lane, {})[gid] = (lab, n[0] == 'h', incoming)
        else:
            sid = STUBMAP[n]
            gid = 'g%d_%s' % (lane, sid)
            ghosts.setdefault(lane, {})[gid] = (stubs[sid], False, False)
        return gid

    drawn = set()
    for (k, s_, d, kind, role) in sorted(edges, key=lambda e: (e[0], e[1], e[2], e[3])):
        src = (k, s_)
        dst = ('h', d) if kind == 'call' else ('m', d)
        if src not in lane_of or (dst not in lane_of and dst not in STUBMAP):
            continue
        if k == 'h' and kind == 'call':
            continue                    # routine -> routine calls (the group teardown $37c2 etc.) are not drawn
        if role == 'the lead':
            role = ''                   # the order lane's title says it
        ls = lane_of[src]
        if dst not in lane_of:
            a_, b_ = nid(*src), ghost(ls, dst, False)
        else:
            ld = lane_of[dst]
            if ld == ls or ((ls, ld) in adjacent and kind != 'call'):
                a_, b_ = nid(*src), nid(*dst)
            elif ls in shared and ld not in shared:
                a_, b_ = ghost(ld, src, True), nid(*dst)
            else:
                a_, b_ = nid(*src), ghost(ls, dst, False)
        lab = role if (role and roles) else ''
        if kind == 'prev':
            lab = ('prev of ' + role) if role else 'prev'
        key = (a_, b_, kind, lab)
        if key in drawn:
            continue
        drawn.add(key)
        lines.append('%s -> %s [%s, constraint=false%s];' % (a_, b_, style[kind], (', label="%s"' % lab) if lab else ''))

    L = ['digraph G {', 'graph [rankdir=TB, fontname="%s", bgcolor="white", nodesep=0.2, ranksep=0.4, pad=0.2, '
         'labelloc=t, labeljust=l, fontsize=18, label=<%s>, newrank=true];' % (FONT, title),
         'node [fontname="%s", fontsize=11, margin="0.06,0.03", height=0.3];' % FONT,
         'edge [fontname="%s", fontsize=9, arrowsize=0.6, color="#333333"];' % FONT]
    firsts = []
    for i, (lname, rows) in enumerate(lanes):
        rows = [list(r) for r in rows]
        L.append('subgraph cluster_%d { label="%s"; labeljust=r; fontsize=13; style="rounded"; color="#9e9e9e"; fontcolor="#212121";' % (i, lname))
        ids = [[nid(*n) for n in row] for row in rows]
        for gid, (lab, is_r, inc) in sorted(ghosts.get(i, {}).items()):
            L.append('  %s [label="%s", shape=box, style="%s", color="#9e9e9e", fontcolor="#424242", fontsize=10%s];' % (
                gid, lab, 'dashed' if is_r else 'rounded,dashed', ''))
            if len(ids) == len(rows):
                ids.append([])                     # the lane's ghosts get their own row under the lane's nodes
            ids[-1].append(gid)
        for row in rows:
            for n in row:
                L.append('  ' + node(*n))
        for r in ids:
            L.append('  { rank=same; %s }' % ' '.join(r))
            if len(r) > 1:
                L.append('  %s [style=invis, weight=5];' % ' -> '.join(r))
        L.append('}')
        for r0, r1 in zip(ids, ids[1:]):
            L.append('%s -> %s [style=invis, weight=20];' % (r0[0], r1[0]))
        firsts.append((ids[0][0], ids[-1][0]))
    for (a_, b_), (c_, d_) in zip(firsts, firsts[1:]):
        L.append('%s -> %s [style=invis, weight=20];' % (b_, c_))
    L += lines
    # legend: one row under the last lane
    L.append('subgraph cluster_legend { label="Legend (node fill = evidence for the handler; every edge is code read from a mode-byte write, py/mode_edges.py)"; fontsize=11; style="rounded"; color="#9e9e9e";')
    L.append('  lg1 [label="proven: gate vs the real 68000", shape=box, style="rounded,filled", fillcolor="%s", color="%s", fontsize=10];' % COL['proven'])
    L.append('  lg2 [label="code read only", shape=box, style="rounded,filled", fillcolor="%s", color="%s", fontsize=10];' % COL['code'])
    L.append('  lg3 [label="$addr routine", shape=box, style=filled, fillcolor="#ffffff", color="#757575", fontsize=10];')
    pts = ' '.join('lg%s [shape=point, width=0.04, color="#ffffff"];' % c for c in 'ABCDEFGH')
    L.append('  ' + pts)
    L.append('  { rank=same; lg1 lg2 lg3 lgA lgB lgC lgD lgE lgF lgG lgH }')
    L.append('  lg1 -> lg2 -> lg3 -> lgA [style=invis]; lgB -> lgC [style=invis]; lgD -> lgE [style=invis]; lgF -> lgG [style=invis];')
    L.append('  lgA -> lgB [label="mode := Y", minlen=2, %s];' % style['set'])
    L.append('  lgC -> lgD [label="walk $10/$12, arrives as Y", minlen=3, %s];' % style['walk'])
    L.append('  lgE -> lgF [label="prev := Y only", minlen=2, %s];' % style['prev'])
    L.append('  lgG -> lgH [label="calls", minlen=2, %s];' % style['call'])
    L.append('}')
    L.append('%s -> lg1 [style=invis, weight=20];' % firsts[-1][1])
    L.append('}')
    dot = os.path.join(out, name + '.dot')
    open(dot, 'w').write('\n'.join(L))
    svg = os.path.join(out, name + '.svg')
    subprocess.run(['dot', '-Tsvg', dot, '-o', svg], check=True)
    subprocess.run(['rsvg-convert', '-b', 'white', '-w', '1800', svg, '-o', os.path.join(out, name + '.png')], check=True)
    print('wrote', svg)


STUBMAP = {}


def stubs_for(dst, stubs):
    return STUBMAP.get(dst)


def M(*vs):
    return [('m', v) for v in vs]


def H(*vs):
    return [('h', v) for v in vs]


def main():
    E = derive()
    json.dump(sorted([list(e) for e in E], key=str), open(os.path.join(out, 'fsm_edges.json'), 'w'), indent=0)
    # ------------------------------------------------ figure 1: the civilian job cycles
    lanes1 = [
        ('Farmer (byte 7 bit 0)', [M(0x18, 0x0c, 0x0e, 0x24, 0x16)]),
        ('Merchant (bit 1)', [M(0x54, 0x50, 0x52, 0x4e)]),
        ('Fisher (bit 2)', [M(0x5e, 0x56, 0x58, 0x5a), M(0x5c, 0x60, 0x62)]),
        ('Shepherd (bit 3)', [M(0x80, 0x84, 0x86, 0x88, 0x82)]),
        ("The lord's work order: timber, building, pots", [H(0x5cde) + M(0x40, 0x3e, 0x44, 0x6a), M(0x46, 0x42) + H(0x600a)]),
        ('Home, winter and regroup', [M(0x7c, 0x7e) + H(0x16892) + M(0x90, 0x8e), H(0x3c08) + M(0x4c, 0x8a)]),
    ]
    STUBMAP.clear()
    stubs1 = {'s_army': 'group, order and combat\\nmodes (army figure)'}
    for v in (0x10, 0x2c, 0x32, 0x68, 0x92, 0x12):
        STUBMAP[('m', v)] = 's_army'
    for v in (0x35f4, 0x5590, 0x4bc8, 0x1d70, 0x56a6, 0x4f68):
        STUBMAP[('h', v)] = 's_army'
    write_graph('fsm_jobs', '<b>PowerMonger entity modes: the civilian job cycles</b><br/><font point-size="11">mode byte 31 of the 50-byte record, '
                'dispatched by the iterator $14b62 through the table $14bb4; edges extracted from the code</font>',
                lanes1, E, stubs1, shared=(4, 5), roles=False, adjacent=())
    # ------------------------------------------------ figure 2: groups, orders, combat
    lanes2 = [
        ('Orders: the executor walks the lead to the target', [H(0x3888, 0x3154, 0x38ce, 0x390e, 0x4a7a, 0x6128, 0x3248)]),
        ('Order arrivals', [M(0x1e, 0x1a, 0x22, 0x6e, 0x76, 0x78, 0x7a), M(0x72, 0x74, 0x26) + H(0x3956) + M(0x30) + H(0x5fa0) + M(0x92)]),
        ('Recruiting and camp', [M(0x1c, 0x6c, 0x28) + H(0x34f2), M(0x14, 0x2a) + H(0x1d70, 0x35f4) + M(0x20, 0x68)]),
        ('Movement and ranks', [M(0x10, 0x12, 0x4a, 0x48), M(0x0a, 0x00, 0x8c, 0x02, 0x06, 0x08)]),
        ('Combat', [M(0x2c) + H(0x4f68) + M(0x2e, 0x32) + H(0x56a6, 0x5590), M(0x34, 0x36, 0x66, 0x38, 0x3a, 0x3c) + H(0x4bc8)]),
    ]
    STUBMAP.clear()
    stubs2 = {'s_home': '$3C08 send home: civilian\\nhome modes (jobs figure)', 's_jobs': 'job modes\\n(jobs figure)'}
    STUBMAP[('h', 0x3c08)] = 's_home'
    for v in (0x7e, 0x16, 0x4e, 0x5e, 0x80, 0x4c, 0x8a, 0x46, 0x3e, 0x40, 0x6a, 0x8e, 0x90, 0x24, 0x7c):
        STUBMAP[('m', v)] = 's_jobs'
    for v in (0x5cde, 0x16892, 0x600a):
        STUBMAP[('h', v)] = 's_jobs'
    write_graph('fsm_army', '<b>PowerMonger entity modes: groups, orders and combat</b><br/><font point-size="11">the lead and his men; '
                'the walk $10/$12 ends in the previous mode (byte 30); edges extracted from the code</font>',
                lanes2, E, stubs2, shared=(2, 3, 4))


main()
