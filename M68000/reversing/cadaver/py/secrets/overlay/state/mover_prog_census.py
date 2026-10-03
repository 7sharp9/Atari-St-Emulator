"""mover_prog_census.py: parse every mover program (bytes after the 14-byte header of rec+rec[13] .. rec+rec[14]) of both levels with the op lengths read from $f920 (00: 4 bytes, 01: 2, 02: 1, 03: 2, 04: 2); a program tiles when it ends exactly at the block end or leaves one pad byte (blocks have even length)
and report whether each program tiles exactly to the block end; counts of ops.  usage: mover_prog_census.py SNAP..."""
import sys, collections
from st import St
LEN = {0: 4, 1: 2, 2: 1, 3: 2, 4: 2}
for snap in sys.argv[1:]:
    s = St(snap); ok = n = 0; ops = collections.Counter(); odd = []; users = collections.defaultdict(list)
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        sz = s.size(6, i); r = s.mem(a, sz)
        if r[15] & 0x80 or r[14] - r[13] <= 14: continue
        n += 1; p = r[13] + 14; good = True; last = None; end = r[14]
        while p < end:
            if p == end - 1 and last == 2: p += 1; break            # the one pad byte of an odd-length block, after the final halt
            op = r[p]
            if op not in LEN: good = False; break
            ops[op] += 1; users[op].append(i); p += LEN[op]; last = op
        if good and p == end: ok += 1
        else: odd.append((i, r[p:end].hex() if p < end else 'overrun'))
    print(snap, 'programs tiling exactly: %d of %d' % (ok, n), 'ops', dict(ops), 'odd', odd[:6])
    for op in (2, 4): print('   op %d used by objects %s' % (op, sorted(set(users[op]))[:10]))
