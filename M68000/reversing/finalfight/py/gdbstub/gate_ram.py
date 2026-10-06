"""Stub gate client: Z0 at the VBL entry $53e, continue N times, record A5/SP/SR at every stop and the 64 KB work RAM at the listed hits.
usage: gate_ram.py <port> <dump hits csv>   env GD_OUT (output dir). Writes stub_ram_<n>.bin, stub_regs_<n>.txt, stub_log.json."""
import sys, os, json
from rsp import RSP
port = int(sys.argv[1]); dumps = [int(x) for x in sys.argv[2].split(',')]
out = os.environ["GD_OUT"]; os.makedirs(out, exist_ok=True)
c = RSP(port); c.init()
print('Z0', c.bp(0x53e))
log = []
for n in range(1, max(dumps) + 1):
    r = c.cont(timeout=30)
    g = c.regs()
    w = [int(g[i * 8:(i + 1) * 8], 16) for i in range(16)]   # d0-d7 a0-a5 fp sp
    ps, pc = int(g[128:132], 16), int(g[132:140], 16)
    log.append((n, r.decode(), pc, w[13], w[15], ps))
    if n in dumps:
        open('%s/stub_ram_%d.bin' % (out, n), 'wb').write(c.mem(0xff0000, 0x10000))
        open('%s/stub_regs_%d.txt' % (out, n), 'w').write(g + '\n')
        print('hit', n, r.decode(), 'pc=%x a5=%x sp=%x sr=%x' % (pc, w[13], w[15], ps))
json.dump(log, open(out + '/stub_log.json', 'w'))
print('pcs', sorted(set(hex(x[2]) for x in log)), 'a5', sorted(set(hex(x[3]) for x in log)))
c.unbp(0x53e)
