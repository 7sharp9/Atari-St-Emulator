"""f4_mask.py: F4 toggles bit 2 of 2499(A5); $006ac6-$006ae6 then strips the left/right bits from the joystick state whenever up or
down is held (keeps fire bit 7 and the up/down pair): a no-diagonals mode.  Start gameplay_empire.snap; holds joystick up+right
(packet $09) for 100,000 steps with F4 off and on and prints the raw port byte 2529(A5) and the masked copy 2243(A5) each main-loop
iteration ($006ac6 hit) for the last 2 iterations.
    uv run python reversing/cadaver/py/secrets/f4_mask.py"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *

def trial(f4, bits=0x09):
    r = Repl()
    if f4:
        r.key(0x3e, 40000, 100000)
    r.cmd('kbd ff', 's 300', f'kbd {bits:02x}', 's 120000')
    out = []
    for _ in range(3):
        r.cmd('s 25000'); out.append((r.a5(2529).hex(), r.a5(2243).hex(), r.a5(2499).hex()))
    r.close()
    return out

if __name__ == '__main__':
    for f4 in (0, 1):
        print('F4', f4, 'up+right held; (2529 raw, 2243 used, 2499 flags) per sample:', trial(f4))
