"""anim_op_census.py: census of animation-script opcodes ($f3-$ff) over every type-2 template with +12 bit 2 (script = template+$28 .. +$28+word(+34)), both levels, and the objects using them.
usage: anim_op_census.py SNAP [SNAP...]"""
import sys, collections
from st import St
for snap in sys.argv[1:]:
    s = St(snap)
    cnt = collections.Counter(); who = collections.defaultdict(set); nt = 0
    users = collections.defaultdict(list)
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        users[(s.b(a + 6) << 8) | s.b(a + 7)].append(i)
    for t in range(s.count(2)):
        ta = s.tmpl(t)
        if ta is None: continue
        T = s.mem(ta, s.size(2, t))
        if len(T) < 0x30 or not T[12] & 4 or T[12] & 0x20: continue
        nt += 1
        w34 = int.from_bytes(T[34:36], 'big')
        for k in range(0x28, 0x28 + w34, 2):
            op = T[k]
            if op >= 0xf3: cnt[op] += 1; who[op].add(t)
    print(snap, 'templates with anim:', nt)
    for op in sorted(cnt): print('  op %02x: %3d uses in %2d templates e.g. %s -> objects %s' % (op, cnt[op], len(who[op]), sorted(who[op])[:4], [users[t][:2] for t in sorted(who[op])[:4]]))
