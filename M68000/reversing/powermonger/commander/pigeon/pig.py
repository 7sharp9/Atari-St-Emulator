"""pig.py: RAM decoders for the order-pigeon investigation (agent pigeon).
Group arrays (strategy.md "$6564", pend_pigeons.py): side s, group k, word n at $51538 + s*$13c + n + 2k.
  n=4 pending, 28 owner, 124 sender (= 48(A1) at $6af2 with A1 = $51538+D2, D2 = s*$13c+$4c+2k), 52 men, 64 lead, 76 state.
Pigeon pool $4c112 + 26*i (i=0 the player's pigeon): +5 owner (copied from sender, $45a8), +6 category ($14 live),
  +8/+10 pos, +15 b15, +16 b16, +18 word18 countdown, +20 rider (lead offset), +23 type, +24 target word."""
import struct, sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
OBJ, GBASE, POOL = 0x51b66, 0x51538, 0x4c112
def H(R, a): return struct.unpack_from('>H', R, a)[0]
def h(R, a): return struct.unpack_from('>h', R, a)[0]
def sb(v): return v - 256 if v > 127 else v
def gaddr(s, k, n): return GBASE + s * 0x13c + n + 2 * k
def groups(R, s):
    out = []
    for k in range(6):
        own = h(R, gaddr(s, k, 28))
        snd = H(R, gaddr(s, k, 124)); lead = H(R, gaddr(s, k, 64))
        out.append(dict(k=k, owner=own, pending=h(R, gaddr(s, k, 4)), men=H(R, gaddr(s, k, 52)), state=H(R, gaddr(s, k, 76)),
                        lead=lead, sender=snd, sender_own=sb(R[OBJ + snd + 5]) if snd else None,
                        lead_own=sb(R[OBJ + lead + 5]) if lead else None, lead_w42=H(R, OBJ + lead + 42) if lead else None))
    return out
def pigeons(R):
    out = []
    for i in range(48):
        p = POOL + 26 * i
        if R[p + 6] == 0: continue
        rider = H(R, p + 20)
        out.append(dict(i=i, addr=p, own=sb(R[p + 5]), cat=R[p + 6], pos=(H(R, p + 8), H(R, p + 10)), t18=h(R, p + 18),
                        b15=R[p + 15], rider=rider, rider_w42=H(R, OBJ + rider + 42), type=R[p + 23], target=H(R, p + 24)))
    return out
def order_status(R, s, k):
    """What happens to an order the harness sends side s's group k now, and what is already on the way to it.
    route: 'none' (no group), 'direct' (sender word 0: the executor runs it in the same pass, $6af6 -> $6b2e),
    'pigeon' (sender alive: a pigeon flies from the sender's position, ~1.2-1.45M steps per 1000 world units),
    'never' (sender's owner byte <= 0: $4562 copies it ($45a8), the pool loop skips owner <= 0 ($417a), the pigeon
    never flies and its record leaks until group k dissolves ($283a)).
    in_flight: live records riding to the lead with owner > 0 (each will run its order on arrival, in arrival order,
    unless the side's first group dissolves first ($27c6 frees owner == side) or group k dissolves ($283a)).
    stuck: records riding to the lead with owner <= 0 (never arrive)."""
    g = groups(R, s)[k]
    if g['owner'] <= 0: route = 'none'
    elif g['sender'] == 0: route = 'direct'
    else: route = 'pigeon' if g['sender_own'] > 0 else 'never'
    mine = [p for p in pigeons(R) if p['i'] and p['rider'] == g['lead']]
    return dict(route=route, pending_word=g['pending'],
                in_flight=[(p['i'], p['type'], p['target'], p['pos']) for p in mine if p['own'] > 0],
                stuck=[(p['i'], p['type'], p['target']) for p in mine if p['own'] <= 0],
                pool_free=sum(1 for i in range(1, 48) if R[POOL + 26 * i + 6] == 0))
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools'))
    from disassemble import ram_from_snap
    R = ram_from_snap(sys.argv[1])
    print('clock', H(R, 0x2df72), 'local', H(R, 0x57ffe))
    for s in range(1, 5):
        for g in groups(R, s):
            if g['owner'] > 0 or g['pending']: print(' side', s, g)
    for p in pigeons(R): print(' pig', p)
    for s in range(1, 5):
        for k in range(6):
            st = order_status(R, s, k)
            if st['route'] != 'none': print(' status', s, k, st)
