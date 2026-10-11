"""tree_weather.py - does deforestation change the weather? One-variable trial on the tree array `$4d252`.

    cd M68000 && uv run python reversing/powermonger/py/season/tree_weather.py <snap> <arm> [steps]      # arm: control | felled | empty

From <snap> (default use: scratchpad/pm142/rand1.snap) it pokes `$57ff6 := $0681` (the first `$1abaa` call wraps,
as py/season/season_run.sh does) and, per arm, one change to the trees:
  control  nothing else
  felled   every live tree's state byte +7 := $0d (the value h_mode44_fell `$156d0` writes when a man fells it)
  empty    g_tree_count `$4e512` := $000c (the array length world-build starts from: no live tree)
then counts `hits` over the weather path (`$1ad2a` entry, `$1ad74` start test, `$1ad8c` spell started, `$1ad40` draw,
`$1ad4a` spell end, `$1a856` overlay draw, `$1ac3c` season wrap) and dumps `$4bb42`, `$57fd0`, `$57fec` at the end.
Output: $PM_WORK/<arm>.{cmds,txt} (default scratchpad/pm150/weather/trial).
"""
import os
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap  # noqa: E402

snap, arm = sys.argv[1], sys.argv[2]
steps = int(sys.argv[3]) if len(sys.argv) > 3 else 125_000_000
out = Path(os.environ.get('PM_WORK', ROOT / 'scratchpad/pm150/weather')) / 'trial'
out.mkdir(parents=True, exist_ok=True)

r = ram_from_snap(snap)
w = lambda a: int.from_bytes(r[a:a + 2], 'big')
n = w(0x4e512)
live = [o for o in range(0x4d252 + 12, 0x4d252 + n, 12) if w(o + 10)]
lines = ['w 57ff6 %04x%04x' % (0x0681, w(0x57ff8))]           # keep the word after $57ff6
if arm == 'felled':
    for o in live:                                            # longword at +4 keeps +4..+6, sets +7
        lines.append('w %x %02x%02x%02x0d' % (o + 4, r[o + 4], r[o + 5], r[o + 6]))
elif arm == 'empty':
    lines.append('w 4e512 000c%04x' % w(0x4e514))
elif arm != 'control':
    sys.exit('arm must be control, felled or empty')
lines += ['hits %d 1ad2a 1ad74 1ad8c 1ad40 1ad4a 1a856 1ac3c 156d0 1ac9a' % steps,
          'm 4bb42 4', 'm 57fd0 2', 'm 57fec 2', 'm 4e512 2', 'q']
(out / f'{arm}.cmds').write_text('\n'.join(lines) + '\n')
print(f'{arm}: {len(live)} live trees, {len(lines) - 6} pokes')
env = dict(os.environ, ATARI_NOTRACE='1')
with open(out / f'{arm}.txt', 'w') as f:
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'],
                   stdin=open(out / f'{arm}.cmds'), stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
