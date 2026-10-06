"""Compare the stub gate (gate_ram.py) with the Lua oracle (oracle.lua) in $GD_OUT: A5/SP/SR at every stop and the work RAM at the dump hits. usage: cmp.py"""
import json, os
out = os.environ["GD_OUT"]
log = json.load(open(out + '/stub_log.json'))
lua = {}
for l in open(out + '/lua_log.txt'):
    p = l.split(); lua[int(p[0])] = tuple(int(x.split('=')[1], 16) for x in p[1:4])
m32 = lambda v: v & 0xffffffff
bad = sum(1 for n, rep, pc, a5, sp, sr in log if lua.get(n) is None or (m32(a5), m32(sp), m32(sr)) != tuple(m32(x) for x in lua[n]))
print('hits compared %d, A5/SP/SR mismatches %d, stops with PC != $53e: %d' % (len(log), bad, sum(1 for x in log if x[2] != 0x53e)))
tot_bad = 0
for f in sorted(int(f.split('_')[2].split('.')[0]) for f in os.listdir(out) if f.startswith('stub_ram_')):
    a = open('%s/stub_ram_%d.bin' % (out, f), 'rb').read(); b = open('%s/lua_ram_%d.bin' % (out, f), 'rb').read()
    diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    tot_bad += len(diff)
    print('hit %4d: %d of %d bytes equal%s' % (f, len(a) - len(diff), len(a), '' if not diff else ', first diff $%x' % (0xff0000 + diff[0])))
raise SystemExit(1 if bad or tot_bad else 0)
