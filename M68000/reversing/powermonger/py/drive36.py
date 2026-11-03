"""drive36.py <snap> <chaser_hex> <target_hex> [ticks] [steps_per_tick]
Poke the chaser into mode $36 (prev $66) with 48(A1) = target offset, run, dump both records after each slice.
Repo root derived from __file__; writes only under scratchpad/drive36/."""
import subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'scratchpad/drive36'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap

snap, ch, tg = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
ticks = int(sys.argv[4]) if len(sys.argv) > 4 else 8
per = int(sys.argv[5]) if len(sys.argv) > 5 else 220000
r = ram_from_snap(ROOT / snap)
toff = tg - 0x51b66
l30 = bytes([0x66, 0x36, r[ch + 32], r[ch + 33]]).hex()
l48 = (toff.to_bytes(2, 'big') + bytes([r[ch + 50], r[ch + 51]])).hex()
settl = 0x4f916 + int.from_bytes(r[ch+34:ch+36],'big')
lord = 0x4e514 + int.from_bytes(r[settl+14:settl+16],'big')
cmds = []
cmds.append('m %x 12' % lord)
cmds.append('w %x %s' % (ch + 30, l30))
cmds.append('w %x %s' % (ch + 48, l48))
def dump():
    cmds.append('m %x 50' % ch)   # decimal 50? checked below
    cmds.append('m %x 50' % tg)
dump()
for _ in range(ticks):
    cmds.append('s %d' % per)
    dump()
cmds.append('m %x 12' % lord)
cmds.append('q')
cf, of = OUT / 'd36.cmds', OUT / 'd36.out'
cf.write_text('\n'.join(cmds) + '\n')
with open(cf) as fi, open(of, 'w') as fo:   # one bounded REPL run; ATARI_NOTRACE keeps it from tracing every step
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', 'scratchpad/powermonger.st'],
                   stdin=fi, stdout=fo, stderr=subprocess.STDOUT, cwd=ROOT, env={**__import__('os').environ, 'ATARI_NOTRACE': '1'}, check=True)
txt = of.read_text().splitlines()
import re
toks = []
lordtxt = []
for ln in txt:
    if re.fullmatch(r'(?:[0-9a-f]{2} ?)+', ln.strip()):
        toks += ln.split()
        if len(ln.split()) == 12: lordtxt.append(ln.strip())
print('lord rec %x (settl %x): before %s | after %s' % (lord, settl, lordtxt[0] if lordtxt else '?', lordtxt[-1] if lordtxt else '?'))
print('hex tokens', len(toks), 'expected per dump (dec 50 / hex 80):', len(toks) / (2 * (ticks + 1)))
toks = toks[12:-12]
n = len(toks) // (2 * (ticks + 1))
def b(rec, i): return int(rec[i], 16)
for k in range(ticks + 1):
    c = toks[(2 * k) * n:(2 * k + 1) * n]
    t = toks[(2 * k + 1) * n:(2 * k + 2) * n]
    print('t%d chaser: side %d cat %02x f7 %02x mode %s/%s dwell %s%s pos %s%s,%s%s tgt48 %s%s | target: side %02x cat %02x f7 %02x mode %s/%s pos %s%s,%s%s' % (
        k, b(c, 5), b(c, 6), b(c, 7), c[30], c[31], c[18], c[19], c[8], c[9], c[10], c[11], c[48], c[49],
        b(t, 5), b(t, 6), b(t, 7), t[30], t[31], t[8], t[9], t[10], t[11]))
