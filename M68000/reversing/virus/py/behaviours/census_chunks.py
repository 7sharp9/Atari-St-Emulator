"""Per-wave hits census of one chain game: chunked `hits` over every behaviour entry, reading the wave word ($32a50),
tick word ($32a44) and pool count ($32a3e) after each chunk.

    python3 census_chunks.py <game NNN> <total steps> [chunk steps]
Output: W/behaviours/census_gNNN.{raw,jsonl} (W = $VIRUS_WORK or scratchpad/virus).
"""
import os, re, subprocess, sys

import bh
R = bh.ROOT
W = bh.BW
game = int(sys.argv[1]); total = int(sys.argv[2]); chunk = int(sys.argv[3]) if len(sys.argv) > 3 else 25_000_000
ENT = "21776 21792 21894 21976 219de 21ae2 21afe 21c42 21c64 21d08 21df6 21f00 2200c 2202c 22164 221ac 222dc 22316 22486 224a6 22688 226ac 2279a 228de 22722 20206 201b4 25306 225d6 216d6 20fb4".split()
snap = f'{bh.STARTS}/main_g{game:03d}.snap'
lines = []
for _ in range(total // chunk):
    lines += [f'hits {chunk} ' + ' '.join(ENT), 'm 32a3c 22']
lines.append('q')
env = dict(os.environ, ATARI_NOTRACE='1')
raw = f'{W}/census_g{game:03d}.raw'
if os.environ.get('REPARSE') and os.path.exists(raw):
    class P: pass
    p = P(); p.stdout = open(raw).read(); p.returncode = 'reparse'
else:
  p = subprocess.run(['dotnet', 'exec', f'{R}/bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input='\n'.join(lines) + '\n',
                   capture_output=True, text=True, cwd=R, env=env)
  open(raw, 'w').write(p.stdout)
# parse: blocks of hits lines followed by an m dump
out = []; cur = {}
for l in p.stdout.splitlines():
    m = re.match(r'\s+\$0*([0-9a-f]+)\s+(\d+)\s+first', l)
    if m: cur[m.group(1)] = int(m.group(2)); continue
    if re.match(r'^([0-9a-f]{2} ){10,}', l):
        out.append((cur, l)); cur = {}
def dec(l):
    b = bytes.fromhex(l.replace(' ', ''))
    return dict(nobj=int.from_bytes(b[0:2], 'big'), npool=int.from_bytes(b[2:4], 'big'), tick44=int.from_bytes(b[8:10], 'big'), wave=int.from_bytes(b[20:22], 'big'))
import json
open(f'{W}/census_g{game:03d}.jsonl', 'w').write(''.join(json.dumps(dict(dec(l), hits=c)) + '\n' for c, l in out))
print(len(out), 'chunks; rc', p.returncode)
