"""fdc_files.py <disk.st> <fdc_run.txt> (capture: ATARI_TRACE_FDC=1 REPL run, keep the lines starting "FDC read" and "FDC cmd"; saved copy scratchpad/captainblood/galaxy/fdc_run.txt): which files' sectors the FDC trace read (FAT12 chains from the image). Reports per file: sectors of file, sectors read."""
import sys, re, struct
d = open(sys.argv[1], 'rb').read()
bps, spc, res, nfat, nroot, tot, _, spf, spt, sides = struct.unpack('<HBHBHHBHHH', d[11:11+2] + d[13:14] + d[14:16] + d[16:17] + d[17:19] + d[19:21] + d[21:22] + d[22:24] + d[24:26] + d[26:28])
print('BPB bps=%d spc=%d res=%d nfat=%d nroot=%d tot=%d spf=%d spt=%d sides=%d' % (bps, spc, res, nfat, nroot, tot, spf, spt, sides))
fat = d[res*bps:(res+spf)*bps]
def nxt(c):
    o = c*3//2; v = fat[o] | (fat[o+1] << 8); return (v >> 4) if c & 1 else (v & 0xfff)
rootsec = res + nfat*spf; datasec = rootsec + nroot*32//bps
files = {}
for i in range(nroot):
    e = d[rootsec*bps + i*32: rootsec*bps + i*32 + 32]
    if e[0] in (0, 0xe5) or e[11] & 0x18: continue
    name = (e[:8].decode('latin1').strip() + ('.' + e[8:11].decode('latin1').strip() if e[8:11].strip() else ''))
    c = struct.unpack('<H', e[26:28])[0]; size = struct.unpack('<I', e[28:32])[0]; secs = []
    while 2 <= c < 0xff0:
        secs += [datasec + (c-2)*spc + k for k in range(spc)]; c = nxt(c)
    files[name] = (size, set(secs))
read = set(); 
L = open(sys.argv[2]).read().split('\n'); i = 0
while i < len(L):
    m = re.match(r'FDC read .*track=(\d+) side=(\d+) sector=(\d+)', L[i])
    if m:
        t, s, sc = map(int, m.groups()); cnt = 1
        for j in (i+1, i+2):
            m2 = j < len(L) and re.search(r'transferred=(\d+)', L[j])
            if m2: cnt = int(m2.group(1)); break
        base = (t*sides + s)*spt + sc - 1
        read |= set(range(base, base+cnt))
    i += 1
print('sectors read (distinct):', len(read))
for n in sorted(files, key=lambda n: min(files[n][1]) if files[n][1] else 0):
    sz, secs = files[n]; r = len(secs & read)
    print('%-14s %8d bytes %4d sectors, read %4d' % (n, sz, len(secs), r))
