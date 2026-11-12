"""Log every trap #9 call (game OS in the low-RAM loader: dispatcher $206, all exits through the crack's
epilogue $16c since the Medway hook at $222) over a drive: entry D7 (function), D0-D2, A0, A1, the caller PC,
a string at A0/A1 when printable, and the returned D0 (the slot movem restores at $16c).

usage: trap9_log.py (--snap <snap> | --boot <disk.st>) <drive> [out.tsv]
  drive: comma list of s:<steps> (run) and k:<hex bytes> (kbd), e.g. s:39999999,k:02,s:30000,k:82,s:170000000
Set STSERVER_DLL to a stserver.dll whose folder holds the current bin/ M68000.dll (the server/bin copy can be
older than the FDC Step-in fix, which this loader needs). The repo root is found by walking up to tools/rdis.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from util import root
from stclient import StServer

def s_at(s, a):
    if a < 0x400 or a > 0xffff0: return ''
    b = s.read(a, 24); t = b.split(b'\0')[0]
    return t.decode('latin1') if t and all(32 <= c < 127 for c in t) else ''

def main():
    R = root(); a = sys.argv[1:]
    s = StServer(R, dll=os.environ.get('STSERVER_DLL'))  # STSERVER_DLL: a stserver.dll beside the current M68000.dll
    if a[0] == '--snap': s('load', snapshot=os.path.abspath(a[1]))
    else: s('boot', disk=os.path.abspath(a[1]))
    drive = a[2].split(','); out = open(a[3], 'w') if len(a) > 3 else sys.stdout
    s('bp_set', addrs=[0x206, 0x16c])
    stack = []
    print('step\tfn\tcaller\td0\td1\td2\ta0\ta1\tstr\tret_d0', file=out)
    for item in drive:
        k, v = item.split(':')
        if k == 'k': s('kbd', bytes=v); continue
        left = int(v)
        while left > 0:
            r = s('run', max_steps=left); left -= r['steps']
            if r['reason'] != 'breakpoint': break
            g = s('regs'); x = lambda n: int(str(g[n]).lstrip('$'), 16)
            pc = x('pc')
            if pc == 0x206:
                sp = x('a7'); caller = int.from_bytes(s.read(sp + 2, 4), 'big') - 2
                stack.append([g['step'], x('d7'), caller, x('d0'), x('d1'), x('d2'), x('a0'), x('a1'),
                              s_at(s, x('a0')) or s_at(s, x('a1'))])
            elif stack:
                e = stack.pop(); ret = int.from_bytes(s.read(x('a7'), 4), 'big')
                print(f'{e[0]}\t{e[1]}\t${e[2]:x}\t${e[3]:x}\t${e[4]:x}\t${e[5]:x}\t${e[6]:x}\t${e[7]:x}\t{e[8]}\t${ret:x}', file=out)
                out.flush()
    s.close()

if __name__ == '__main__':
    main()
