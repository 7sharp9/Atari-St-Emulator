"""sfx.py - GMUSIC1 decode and a live check of the sample player.

GMUSIC1 = [w n][n x 10-byte records][l L][L bytes of 8-bit samples]; loaded by $afd8 into the
record table $37ec4 and the sample buffer $249b0 (record +6 relocated to an absolute pointer).
Record: +0 b priority, +1 b repeat count, +2 w rate, +4 w length, +6 l offset.

Live check: for each sound k, from game_start.snap poke the VBL request word $36d02 = $42+k
(what the game code writes, e.g. $111fa magnet $4d, $e9ba swamp death $42) and run 200 frames
with `hits` on the Timer A handler $17140, the start routine $16f40 and the stop path $170dc.
The handler outputs one sample per interrupt, so hits($17140) must equal length*(repeat+1).
"""
import os, sys, re, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import WORK, R, DLL, DISK
from popmem import ram, l


def records(path=None):
    d = open(path or os.path.join(WORK, 'files', 'GMUSIC1'), 'rb').read()
    n = struct.unpack_from('>H', d, 0)[0]
    recs = [struct.unpack_from('>BBHHI', d, 2 + 10 * i) for i in range(n)]
    L = struct.unpack_from('>I', d, 2 + 10 * n)[0]
    assert 2 + 10 * n + 4 + L == len(d)
    return recs, d[2 + 10 * n + 4:]


def main():
    recs, data = records()
    src = os.path.join(WORK, 'game_start.snap')
    m = ram(src)
    nb = l(m, 0x36d02) & 0xffff
    env = dict(os.environ, ATARI_NOTRACE='1')
    ok = 0
    print(' k prio rep  rate   len  offset  timerA-data  hits17140 expect  start stop')
    for k, (pri, rep, rate, ln, off) in enumerate(recs):
        poke = 'w 36d02 %08x' % (((0x42 + k) << 16) | nb)
        # window: the emulator delivers ~64 Timer A interrupts per frame (see systems.md), so
        # length*(repeat+1)/64 frames plus a margin, at 125000 steps per frame
        frames = ln * (rep + 1) // 64 + 40
        L = [poke, 'hits %d 17140 16f40 170dc' % (frames * 125000), 'q']
        out = subprocess.run(['dotnet', 'exec', DLL, 'resume', src, 'repl', '--disk-a', DISK],
                             input='\n'.join(L) + '\n', capture_output=True, text=True, cwd=R, env=env).stdout
        h = {}
        for a, c in re.findall(r'\$0*([0-9a-f]+)\s+(\d+)\s+first', out):
            h[int(a, 16)] = int(c)
        # second run: VBL count ($16cec, +1 per VBL in $16d32) from the start to the stop path
        T = [] if '--no-timing' in sys.argv else [poke, 'u 16f40 30000000', 'm 16cec 4', 'r', 'u 170dc 60000000', 'm 16cec 4', 'q']
        o2 = '' if not T else subprocess.run(['dotnet', 'exec', DLL, 'resume', src, 'repl', '--disk-a', DISK],
                            input='\n'.join(T) + '\n', capture_output=True, text=True, cwd=R, env=env).stdout
        v = [int(x.replace(' ', ''), 16) for x in re.findall(r'^((?:[0-9a-f]{2} ){3}[0-9a-f]{2})\s*$', o2, re.M)]
        vbls = v[1] - v[0] if len(v) == 2 else None
        pres, dat = (1, 0x94700 // rate) if rate >= 0x950 else (2, 0x3b600 // rate)
        exp = ln * (rep + 1)
        good = h.get(0x17140) == exp and h.get(0x16f40) == 1 and h.get(0x170dc) == 1
        ok += good
        nominal = 2457600 / (4 if pres == 1 else 10) / (dat & 0xff)
        eff = exp / (vbls / 50.0) if vbls else 0
        print('%2d  $%02x %3d %5d %5d %7d  ctrl %d data %3d  %9s %6d  %5s %4s %s  %5d VBLs: %6.0f Hz (nominal %6.0f)'
              % (k, pri, rep, rate, ln, off, pres, dat & 0xff, h.get(0x17140), exp, h.get(0x16f40),
                 h.get(0x170dc), 'ok' if good else 'MISMATCH', vbls or -1, eff, nominal))
    print('sounds whose sample count = length*(repeat+1), one start, one stop: %d/%d' % (ok, len(recs)))


if __name__ == '__main__':
    main()
