"""save_price.py: the S-key save costs gold.  $00b61c: price = max(1186(A5), (level+1)*50-45) where level = 2524(A5) (a byte);
$00df46 builds "THE GODS DEMAND A PRICE TO SAVE YOUR POSITION OF <price>. DO YOU WANT TO PAY. PRESS Y OR N." and takes it from gold
(1188(A5), a longword) when Y is pressed; a paid save raises 1186(A5) by 6*(level+1) at $b664 (undone at $b676 if the disk write
is abandoned).  Start: gameplay_empire.snap; pokes level and gold, presses S, reads the price the game itself shows
(1186(A5) after the prompt is built), then Y and ESC.  Prints per level: formula, measured, gold before/after Y, price after ESC.
    uv run python reversing/cadaver/py/secrets/save_price.py"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *

def poke_byte(r, addr, val):
    base = addr & ~3; cur = bytearray(r.mem(base, 4)); cur[addr - base] = val
    r.cmd(f'w {base:x} {cur.hex()}')

def trial(level, yes=True):
    r = Repl()
    poke_byte(r, A5 + 2524, level)
    r.cmd(f'w {A5 + 1188:x} 000003e8')
    r.cmd('kbd 1f', 's 60000', 'kbd 9f', 's 600000')
    price = r.w(A5 + 1186)
    res = {'level': level, 'formula': (level + 1) * 50 - 45, 'shown': price}
    if yes:
        r.cmd('kbd 15', 's 60000', 'kbd 95', 's 600000')          # Y
        res['gold_after_Y'] = r.l(A5 + 1188)
        r.cmd('kbd 01', 's 60000', 'kbd 81', 's 1500000')         # ESC out of the disk prompt
        res['gold_after_ESC'] = r.l(A5 + 1188); res['price_after_ESC'] = r.w(A5 + 1186)
    r.close()
    return res

if __name__ == '__main__':
    for lv in (0, 1, 4, 9):
        print(trial(lv))
