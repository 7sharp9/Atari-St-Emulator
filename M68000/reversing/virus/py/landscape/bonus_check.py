"""The wave-end bonus ($20fb4..$210e6) predicted from the snapshot stopped at $20fb4 and compared with the score in the
snapshot stopped at $210e8 (after the pay loop); both scores are read from the snapshots.
Rule (read from $21030..$210e6): X = max(0, max(0, base - inf) - inf) >> 2; if n <= 4: X >>= 4 - n;
bonus = 8 * (X // 8 + 1)  (the loop adds 8, subtracts 8 from X, and repeats while X >= 0).
inf = object-map ($32a58, 64 KB) cells with bit 5; base $9000 / $64ba / $cb89 by landscape $32a4e = 0 / 1 / 2;
n = $32a50 + 1 (the counter after the increment at $20fd0).
Usage: bonus_check.py <end.snap at $20fb4> <after.snap at $210e8> [inf_once|no_shift]   (the optional word is a control)"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vcommon

def predict(ram, control=None):
    inf = sum(1 for b in ram[0x32a58:0x42a58] if b & 0x20) & 0xffff
    land = struct.unpack('>H', ram[0x32a4e:0x32a50])[0]
    n = struct.unpack('>H', ram[0x32a50:0x32a52])[0] + 1
    base = {0: 0x9000, 1: 0x64ba, 2: 0xcb89}[land]
    x = max(0, base - inf)
    if control != 'inf_once':
        x = max(0, x - inf)
    x >>= 2
    if n <= 4 and control != 'no_shift':
        x >>= 4 - n
    return inf, land, n, 8 * (x // 8 + 1)

if __name__ == '__main__':
    a = vcommon.load_ram(sys.argv[1]); b = vcommon.load_ram(sys.argv[2])
    ctl = sys.argv[3] if len(sys.argv) > 3 else None
    s0 = struct.unpack('>I', a[0x2708e:0x2708e + 4])[0]; s1 = struct.unpack('>I', b[0x2708e:0x2708e + 4])[0]
    inf, land, n, pred = predict(a, ctl)
    print(f'bonus {os.path.basename(sys.argv[1])}: n={n} landscape {land} infected {inf} predicted {pred} observed {s1 - s0} '
          f'{"MATCH" if pred == s1 - s0 else "DIFF"}{" (control " + ctl + ")" if ctl else ""}')
    sys.exit(0 if pred == s1 - s0 else 1)
