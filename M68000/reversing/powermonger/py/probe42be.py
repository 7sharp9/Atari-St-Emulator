"""probe42be.py <snap> <mode> <n>: stop at the n-th successive event and dump state.

mode "land": bp $4244 (pigeon landing branch of $3e06) -> dump, bp $42c8 (after the +1) -> dump
mode "launch": bp $16336 (pigeon launch in $1623c) -> dump, bp $16372 -> dump
Dumps: pigeon record $4c112 (26 B), entity table $51b66 (512*50), leaders $4e514 (0x400), settlements $4f916 (0x800).
Output: <outdir>/<snapname>_<mode>.json with a list of events.
Root derived from __file__; output under scratchpad/probe42be/.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'scratchpad/probe42be'
OUT.mkdir(parents=True, exist_ok=True)
EMU = ROOT / 'bin/Debug/net8.0/M68000.dll'
DISK = ROOT / 'scratchpad/powermonger.st'
HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')

DUMPS = [('pigeon', 0x4c112, 26), ('ent', 0x51b66, 512 * 50), ('lead', 0x4e514, 0x400), ('settl', 0x4f916, 0x800)]
STOPS = {'land': (0x4244, 0x42c8), 'launch': (0x16336, 0x16372)}


def main():
    snap, mode, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    maxs = int(sys.argv[4]) if len(sys.argv) > 4 else 150_000_000
    a, b = STOPS[mode]
    cmds = []
    for _ in range(n):
        for addr in (a, b):
            cmds.append(f'bp {addr:x} {maxs}')
            cmds.append('r')
            for _, ad, ln in DUMPS:
                cmds.append(f'm {ad:x} {ln}')
        cmds.append('s 1')
    cmds.append('q')
    p = subprocess.run(['dotnet', 'exec', str(EMU), 'resume', str(ROOT / snap), 'repl', '--disk-a', str(DISK)],
                       input='\n'.join(cmds) + '\n', capture_output=True, text=True,
                       env={**__import__('os').environ, 'ATARI_NOTRACE': '1'})
    lines = p.stdout.splitlines()
    events = []
    cur = None
    hexes = []
    for ln in lines:
        m = re.match(r'--- breakpoint \$([0-9a-f]+) hit \(\d+/\d+\) after (\d+) step', ln)
        if m:
            if cur is not None:
                cur['hex'] = hexes
                events.append(cur)
            cur = {'pc': int(m.group(1), 16), 'steps': int(m.group(2))}
            hexes = []
            continue
        if cur is not None and HEX.match(ln.strip()) and ln.strip():
            hexes.append(ln.strip())
        mm = re.match(r'--- .*?(cap|did not|not reached).*', ln)
        if mm and cur is None:
            print('note:', ln)
    if cur is not None:
        cur['hex'] = hexes
        events.append(cur)
    res = []
    for e in events:
        d = {}
        for (name, _, ln), h in zip(DUMPS, e['hex']):
            d[name] = [int(x, 16) for x in h.split()]
        res.append({'pc': e['pc'], 'steps': e['steps'], **d})
    name = Path(snap).stem
    (OUT / f'{name}_{mode}.json').write_text(json.dumps(res))
    print(name, mode, 'events', len(res), [(hex(e['pc']), e['steps']) for e in res])


main()
