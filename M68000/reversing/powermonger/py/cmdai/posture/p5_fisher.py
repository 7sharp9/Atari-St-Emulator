"""p5_fisher.sh summary: per arm, the fisherman's mode (byte 31) and prev mode (byte 30) values, fishing-mode writes, job-byte (bytes 6..7) writers and a per-10M dump."""
import re, sys, collections, pathlib
O = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
FISH = {0x56, 0x58, 0x5a, 0x5c, 0x5e, 0x60, 0x62}
W = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) Write(Byte|Word) \$([0-9a-f]+) <- \$([0-9a-f]+)')
for p in (5, 3):
    modes, prevs, writers = collections.Counter(), collections.Counter(), collections.Counter()
    fish_writes = 0
    for l in open(O / f'p{p}_mode.err'):
        m = W.search(l)
        if not m: continue
        step, pc, sz, a, v = m.groups(); a = int(a, 16); v = int(v, 16)
        b = {0x51cb0: [], 0x51cb1: []}
        vals = [v] if sz == 'Byte' else [v >> 8, v & 0xff]
        for i, x in enumerate(vals):
            addr = a + i
            if addr == 0x51cb1: modes[x] += 1; writers[pc] += 1; fish_writes += x in FISH
            elif addr == 0x51cb0: prevs[x] += 1
    jobw = collections.Counter()
    for l in open(O / f'p{p}_job.err'):
        m = W.search(l)
        if m: jobw[(m.group(2), m.group(4), m.group(5))] += 1
    dumps = [bytes.fromhex(l.strip()) for l in open(O / f'p{p}_mode.out') if re.fullmatch(r'([0-9a-f]{2} ){49}[0-9a-f]{2}\s*', l)]
    print(f'== posture {p}: {sum(modes.values())} mode writes, {fish_writes} to fishing modes')
    print('  mode values', {f'${k:02x}': n for k, n in sorted(modes.items())})
    print('  prev values', {f'${k:02x}': n for k, n in sorted(prevs.items())})
    print('  job-byte writes (pc, addr, value)', dict(jobw))
    print('  per-10M dump: side/byte7/prev/mode', ' '.join(f'{d[5]}/{d[7]:02x}/{d[30]:02x}/{d[31]:02x}' for d in dumps))
