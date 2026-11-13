"""Save the constant inputs the chain needs besides (D0, D2), and say what they hold.

    uv run python -I reversing/captive/py/mapgen/full/mktemplate.py

Writes under scratchpad/captive/mapgen_full/. template_23ca4.bin: the module block at $23ca4 for D0 = 0, D2 = 1
(shafts/capture.py d2_1_0.bin 0 250 1), the template shafts/chain.build() overwrites with every seed-dependent byte. fed_init.bin: federation $1bd3e..$1d9e8 of
mg_ret.snap, equal to every dump's first stop ($23c82, after the clear $23bcc-$23c5a) in 80/80 cases.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "shafts"))
sys.path.insert(0, HERE)
from capture import records
import cmodels  # noqa: F401 (paths)
import models
from common import FED, R
DATA = os.path.join(R, 'scratchpad', 'captive', 'mapgen_full')
cap = os.path.join(DATA, 'shafts', 'd2_1_0.bin')
t = next(iter(records(cap)))['st'][0x23ca4][1]
open(os.path.join(DATA, 'template_23ca4.bin'), 'wb').write(bytes(t))
ram, base = models.code()
open(os.path.join(DATA, 'fed_init.bin'), 'wb').write(bytes(ram[FED - base:0x1d9e8 - base]))
# nonzero runs of the template outside what build() overwrites
skip = set(range(0, 56)) | set(range(56, 56 + 4096)) | {12404, 12405, 12406, 12407, 12408, 12409, 12412, 12413,
        13276, 13277, 13660, 13661, 12418, 12419, 13274, 13275, 13748, 13749}
runs, cur = [], None
for i, v in enumerate(t):
    if v and i not in skip:
        if cur and cur[1] == i - 1:
            cur[1] = i
        else:
            cur = [i, i]; runs.append(cur)
for a, b in runs:
    print(a, b - a + 1, bytes(t[a:b + 1]).hex()[:80])
