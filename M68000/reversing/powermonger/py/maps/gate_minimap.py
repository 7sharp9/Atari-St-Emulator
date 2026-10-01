"""gate_minimap.py: `$107d6` (the minimap) vs maps_ref.minimap_107d6, pixel exact, 4 modes x 4 settled snapshots.

    cd M68000 && .venv/bin/python reversing/powermonger/py/maps/gate_minimap.py

Each case pokes `$58098` (`w 58098 000<m>0000`; `$5809a` = 0 in all snapshots) and callcaps `$107d6`; the real byte delta in the
32000-byte buffer at [$e0d4] is applied to the pre-state and compared with the transcription's buffer: matching bytes / 32000 and
matching pixels (a pixel = 4 plane bits). Also renders the buffer's minimap strip (x 0..62, y 6..133) of the real result to
scratchpad/pm140/agents/maps/minimap_m<mode>_<snap>.png for the first snapshot.
"""
import json, os, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/maps"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
import maps_ref as M
SNAPS = ['scratchpad/pm123/win/m1_s0.snap', 'scratchpad/pm121/run/k5_s4.snap', 'scratchpad/pm121/k0.snap', 'scratchpad/pm78_settle.snap']
OUT = DATA / 'gate'; OUT.mkdir(exist_ok=True)
tb = tp = 0
for s in SNAPS:
    for mode in range(4):
        js = OUT / ('mm_%s_%d.json' % (Path(s).stem, mode))
        cmds = ['w 58098 %04x0000' % mode, 'callcap 107d6 20000000 %s' % js.relative_to(ROOT).as_posix(), 'q']
        subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', s, 'repl', '--disk-a', 'scratchpad/powermonger.st'],
                       input='\n'.join(cmds) + '\n', capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'), timeout=600)
        j = json.load(open(js))
        if j.get('outcome') != 'returned':
            print(s, mode, 'FAIL', j.get('outcome')); continue
        ram0 = bytearray(ram_from_snap(str(ROOT / s)))
        ram0[0x58098:0x5809a] = mode.to_bytes(2, 'big')
        base = int.from_bytes(ram0[0xe0d4:0xe0d8], 'big')
        real = bytearray(ram0)
        for a, b0, b1 in j['mem']:
            if 0 <= a < len(real): real[a] = b1
        mine = bytearray(ram0)
        M.minimap_107d6(mine, mode)
        nb = sum(1 for a in range(base, base + 32000) if real[a] == mine[a])
        def pix(buf, x, y):
            o = base + y * 160 + (x >> 4) * 8 + ((x >> 3) & 1); bit = 0x80 >> (x & 7)
            return sum(((buf[o + 2 * p] & bit) != 0) << p for p in range(4))
        npx = sum(1 for y in range(200) for x in range(320) if pix(real, x, y) == pix(mine, x, y))
        outside = sum(1 for a, b0, b1 in j['mem'] if not (base <= a < base + 32000) and b0 != b1 and a < 0x100000)
        tb += nb; tp += npx
        print('%-28s mode %d: steps=%-7s bytes %d/32000 pixels %d/64000 (real writes outside the buffer: %d)' % (Path(s).name, mode, j['steps'], nb, npx, outside))
        if s == SNAPS[0]:
            from PIL import Image
            img = Image.new('RGB', (63, 128)); px = img.load()
            pal = [(r_ * 36, g * 36, b * 36) for r_, g, b in [(0,0,0)]*16]
            for y in range(128):
                for x in range(63):
                    px[x, y] = (pix(real, x, y + 6) * 17,) * 3
            img.resize((252, 512), Image.NEAREST).save(DATA / ('minimap_idx_m%d.png' % mode))
print('TOTAL bytes %d/%d pixels %d/%d' % (tb, 16 * 32000, tp, 16 * 64000))
