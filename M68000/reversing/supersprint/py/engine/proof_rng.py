"""Proof of the game's RNG.  thunk 72(A5) -> $a666: rng(n) = (((Random() & $ffff) >> 1) % n); Random() = XBIOS #17 = TOS 1.00 ROM $fc132c:
    seed ($29b8) := seed*$BB40E62D + 1 (32-bit) ; returns (seed >> 8) & $ffffff ; if seed == 0 it is first set to (hz_200<<16)|hz_200 ($4ba).
Differential test: poke seed and n, callcap $a666, compare the returned word and the new seed with the Python formula."""
import sys, os, struct, random, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff

cd = CallDiff()
random.seed(3)
ok = ok_seed = tot = 0
cases = [(1, 5), (0x12345678, 6), (0xFFFFFFFF, 3), (0x80000000, 16), (0x00000001, 100), (0xDEADBEEF, 5)] + \
        [(random.getrandbits(32), random.choice([2, 3, 4, 5, 6, 7, 8, 10, 16, 20, 40, 100])) for _ in range(34)]
for seed, n in cases:
    cd.poke_long(0x29B8, seed)
    oc, ch, d = cd.call(0xA666, struct.pack('>H', n))
    assert oc == 'returned', oc
    new = seed * 0xBB40E62D + 1 & 0xFFFFFFFF
    want = (((new >> 8) & 0xFFFF) >> 1) % n
    got_seed = struct.unpack('>I', bytes(cd.apply(cd.ram[0x29B8:0x29BC], 0x29B8, ch)))[0]
    got = d['regN'][0] & 0xFFFF          # D0 low word after the return (D0 = remainder in the low word after swap)
    tot += 1; ok += (got == want); ok_seed += (got_seed == new)
    if got != want or got_seed != new: print('MISMATCH seed %08x n %d: got %d want %d, seed %08x want %08x' % (seed, n, got, want, got_seed, new))
print('rng(n) return value equal: %d / %d ; new seed equal: %d / %d' % (ok, tot, ok_seed, tot))
# seed==0 path: seed := (hz_200 << 16) | hz_200
hz = struct.unpack('>I', bytes(cd.ram[0x4BA:0x4BE]))[0]
cd.poke_long(0x29B8, 0)
oc, ch, d = cd.call(0xA666, struct.pack('>H', 6))
s0 = ((hz << 16) | (hz & 0xFFFF)) & 0xFFFFFFFF if False else ((hz << 16) & 0xFFFFFFFF) | hz
new = s0 * 0xBB40E62D + 1 & 0xFFFFFFFF
got_seed = struct.unpack('>I', bytes(cd.apply(cd.ram[0x29B8:0x29BC], 0x29B8, ch)))[0]
print('seed==0 path: hz_200=$%x -> seed $%08x (python) vs $%08x (live)' % (hz, new, got_seed))
cd.close()
