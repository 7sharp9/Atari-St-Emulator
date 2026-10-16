#!/usr/bin/env python3
"""standoff.py <run dir> <start snap> [--side K] [-v]: where the captain's lead stands when enemy men aim at him, from a
loop.py --objs replay (<run dir>/objs.bin, object-array samples). The lead is the side's group-0 lead in the start
snapshot (observe.py), checked live (owner = side, flag bit 4) in every sample.

A chase starts at the first sample where a foreign man's word 48 holds the lead's offset (README "How the captain dies":
a $5350 pick writes it). For each: the distance from the man to the lead in map units (256 to a cell, the larger of
|dx| and |dy|), his health and the lead's, and whether the lead is in melee mode $32 at any sample within 1M steps.
A melee entry is a sample where the lead's mode 31 turns $32. Samples are EVERY steps apart (1e5 is about 0.6 tick), so
a chase or melee shorter than that can be missed.

A melee episode runs from an entry to the first sample with the lead out of $32: the engager is the man in the lead's
word 48 at entry, with his health; "aimed" counts the distinct foreign men aimed at the lead during it.
A sequence is the melees from one the lead enters at health >= 85 up to the next such entry; the lead's loss over it
is checked against the summed health of the men he fought (the one-a-tick trade bound). A health drop of 60 or more
between two samples counts as an arrow hit ($52).
Summary line: per run, how it ended (the lead's owner left the side: killed by arrow when the run had an arrow hit
and his last live sample was not in $32, else in melee), the counts, and the last sequence."""
import struct, sys, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observe import observe, load

O = 0x51b66
a = sys.argv[1:]
side = int(a[a.index('--side') + 1]) if '--side' in a else 1
verbose = '-v' in a
run, start = [x for x in a if not x.startswith('-') and not x.isdigit()][:2]


def sb(v):
    return v - 256 if v > 127 else v


def samples(path):
    b = Path(path).read_bytes(); i = 0
    while i < len(b):
        step, n = struct.unpack_from('<QI', b, i); i += 12
        yield step, zlib.decompress(b[i:i + n]); i += n


obs = observe(load(start))
LO = obs['sides'][str(side)]['groups'][0]['lead'] if str(side) in obs['sides'] else obs['sides'][side]['groups'][0]['lead']
H = lambda r, n: struct.unpack_from('>h', r, n)[0]
U = lambda r, n: struct.unpack_from('>H', r, n)[0]

FIGHT = {0x2c, 0x2e, 0x30, 0x32, 0x34}


def fighters(R, lx, ly, reach=4 * 256):
    """men of the side and foreign men in a fight mode (31) within reach of the lead (the larger of |dx|, |dy|)."""
    n = [0, 0]
    for i in range(512):
        r = R[i * 50:i * 50 + 50]
        if r[6] == 0 and sb(r[5]) > 0 and r[31] in FIGHT and max(abs(H(r, 8) - lx), abs(H(r, 10) - ly)) <= reach:
            n[sb(r[5]) != side] += 1
    return n


chases, melee, prev_t, prev_mode, alive_until, last = [], [], {}, None, None, None
arrows, prev_hp = [], None      # a drop of 60 or more between samples: an arrow hit takes $52 ($596a, ai.md)
eps, ep = [], None      # melee episodes: the lead's mode stays $32 from entry to exit
for step, R in samples(Path(run) / 'objs.bin'):
    L = R[LO:LO + 50]
    if sb(L[5]) != side or not L[7] & 0x10:
        if alive_until is None:
            alive_until = step
        break
    lx, ly, lm, lh = H(L, 8), H(L, 10), L[31], sb(L[45])
    if prev_hp is not None and prev_hp - lh >= 60:
        arrows.append(step)
    prev_hp = lh
    if lm == 0x32 and prev_mode != 0x32:
        melee.append((step, lh, U(L, 48)))
        e = R[U(L, 48):U(L, 48) + 50]
        ep = dict(start=step, hp0=lh, engager=O + U(L, 48), eng_hp=sb(e[45]), eng_side=sb(e[5]), aimed=set(), engs={})
        ep['own'], ep['foe'] = fighters(R, lx, ly)
    if lm != 0x32 and ep is not None:
        ep.update(end=step, hp1=lh); eps.append(ep); ep = None
    prev_mode = lm
    cur = {}
    for i in range(512):
        off = i * 50; r = R[off:off + 50]
        if r[6] != 0 or sb(r[5]) <= 0 or sb(r[5]) == side:
            continue
        if U(r, 48) == LO:
            cur[off] = True
            if off not in prev_t:
                d = max(abs(H(r, 8) - lx), abs(H(r, 10) - ly))
                chases.append(dict(step=step, man=O + off, side=sb(r[5]), d=d, hp=sb(r[45]), lead_hp=lh, lead_mode=lm,
                                   weapon=r[44], r39=r[39]))
    prev_t = cur
    if ep is not None:
        ep['aimed'] |= set(cur)
        w = U(L, 48); e = R[w:w + 50]
        if lm == 0x32 and w != LO and e[6] == 0 and sb(e[5]) not in (0, side) and w not in ep['engs']:
            ep['engs'][w] = sb(e[45])          # each man the lead fights, health when first seen in his word 48
    last = (step, lh)
if ep is not None:
    ep.update(end=None, hp1=last[1]); eps.append(ep)

for c in chases:
    c['melee'] = any(c['step'] <= s <= c['step'] + 1_000_000 for s, _, _ in melee)
killed = alive_until is not None
name = '/'.join(Path(run).parts[-2:])
if verbose:
    for c in chases:
        print('  chase %10d $%05x side %d d %5d hp %3d | lead hp %3d mode %02x%s' % (
            c['step'], c['man'], c['side'], c['d'], c['hp'], c['lead_hp'], c['lead_mode'], '  -> melee' if c['melee'] else ''))
    for e in eps:
        print('  melee %10d..%s engager $%05x side %d hp %3d | lead hp %3d -> %3d, men aimed at him %d | fighting within 4 cells: own %d, foe %d | fought %d, their health %d' % (
            e['start'], e['end'] or 'death', e['engager'], e['eng_side'], e['eng_hp'], e['hp0'], e['hp1'], len(e['aimed']), e['own'], e['foe'],
            len(e['engs']), sum(e['engs'].values())))
# a sequence is the melees from the last one the lead entered at health >= 85 to the end of the run or of the next
# such entry; the lead loses at most the summed health of the men he fights in it (one a tick each way, ai.md $1533c)
seqs = []
for e in eps:
    if e['hp0'] >= 85 or not seqs:
        seqs.append(dict(hp0=e['hp0'], fought=0, n=0, hp1=None, men=set(), t0=e['start']))
    q = seqs[-1]; q['fought'] += sum(e['engs'].values()); q['n'] += len(e['engs']); q['hp1'] = e['hp1']
    q['men'] |= {O + w for w in e['engs']}
for q in seqs:
    q['bound'] = q['hp0'] - q['hp1'] <= q['fought']
    # the distance each fought man picked the lead from: his last chase start before the sequence ended
    q['d'] = [max((c for c in chases if c['man'] == m and c['step'] <= (q.get('t1') or 1 << 62)), key=lambda c: c['step'])['d']
              for m in q['men'] if any(c['man'] == m for c in chases)]
if verbose:
    for j, q in enumerate(seqs):
        print('  seq %10d lead %3d -> %3d, fought %d men of health %d%s' % (
            q['t0'], q['hp0'], q['hp1'], q['n'], q['fought'], ' (killing)' if killed and j == len(seqs) - 1 else ''))
how = ('killed by arrow' if arrows and not (killed and prev_mode == 0x32) else 'killed in melee') if killed else 'alive'
print('%-14s %-15s at %10d | melees %d, sequences %d, loss <= fought health in %d | arrow hits %d | %s' % (
    name, how, alive_until or last[0], len(eps), len(seqs), sum(q['bound'] for q in seqs), len(arrows),
    'last sequence: lead %d -> %d, fought %d men of health %d, picked him from %s' % (
        seqs[-1]['hp0'], seqs[-1]['hp1'], seqs[-1]['n'], seqs[-1]['fought'],
        '%d..%d' % (min(seqs[-1]['d']), max(seqs[-1]['d'])) if seqs[-1]['d'] else '-') if seqs else 'no melee'))
