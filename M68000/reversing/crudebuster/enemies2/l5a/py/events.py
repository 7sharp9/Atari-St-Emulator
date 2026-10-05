"""Summarise the H (player health write), S (hit-box spawn) and Z (sound latch write) lines of a drive5.lua log.
usage: events.py <log> [first_frame]
H: damage = old-new per (writer pc, hit box type, owner type, owner state); S: count of frames a hit box type was spawned per (owner type, state);
Z: sound ids with counts."""
import sys, collections, re
log = sys.argv[1]; f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 721
H = collections.Counter(); S = collections.Counter(); Z = collections.Counter(); Sfr = collections.defaultdict(set)
for l in open(log):
    p = l.split()
    if not p or p[0] not in "HSZ" or len(p[0]) != 1: continue
    f = int(p[1])
    if f < f0: continue
    if p[0] == 'H':
        kv = dict(x.split('=') for x in p if '=' in x)
        old, new = int(kv['old'], 16), int(kv['new'], 16)
        if old == new: continue
        i = p.index('owner')
        H[(p[2], kv['pc'], kv['ctype'], p[i+1], p[i+2], old - new)] += 1
    elif p[0] == 'S':
        kv = dict(x.split('=') for x in p if '=' in x)
        S[(kv['ctype'], kv['owner_type'], kv['owner_state'])] += 1
        Sfr[(kv['ctype'], kv['owner_type'], kv['owner_state'])].add(f)
    else:
        Z[p[2]] += 1
print("H (player, pc, hitbox type, owner type, owner state, damage): count")
for k, v in sorted(H.items()): print("  ", k, v)
print("S (hitbox type, owner type, owner state): frames spawned")
for k, v in sorted(S.items()): print("  ", k, v)
print("Z sounds:", dict(sorted(Z.items())))
