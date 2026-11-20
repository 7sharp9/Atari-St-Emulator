"""Check the actor pool $31d54 (count $32a3e) of a snapshot taken right after $20e74(n) built a wave against the table
$20e34[n & 15] decoded from the same snapshot: record count, per record behaviour (+16) and life word (+12) =
first + k*step within its group (16-bit wrap), y word (+2) = $f100, and gravity $32a3a per the tail of $20e74
(3; 4 from n 2; 5 from n 4; 6 from n 6).
Usage: pool_check.py <snap> [n]   (n defaults to $32a50, the counter $20fd0 incremented before the build)
Prints 'pool n=<n>: <ok>/<total> records ...' and exits 0 when everything matches."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon, wavetable

def expect_gravity(n):
    g = 3
    if n >= 2: g = 4
    if n >= 4: g = 5
    if n >= 6: g = 6
    return g

def check(ram, n):
    _, groups = wavetable.decode(ram)[n & 15]
    inv = {v: k for k, v in wavetable.NAMES.items()}
    exp = [(inv[kind], (first + k * step) & 0xffff) for kind, cnt, first, step, sh in groups for k in range(cnt)]
    count = struct.unpack('>H', ram[0x32a3e:0x32a40])[0]
    ok = 0
    for i in range(min(count, len(exp))):
        r = ram[0x31d54 + 20 * i: 0x31d54 + 20 * i + 20]
        if ((struct.unpack('>I', r[16:20])[0], struct.unpack('>H', r[12:14])[0]) == exp[i]
                and struct.unpack('>H', r[2:4])[0] == 0xf100):
            ok += 1
    grav = struct.unpack('>H', ram[0x32a3a:0x32a3c])[0]
    return count, len(exp), ok, grav, expect_gravity(n)

if __name__ == '__main__':
    ram = vcommon.load_ram(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else struct.unpack('>H', ram[0x32a50:0x32a52])[0]
    count, ne, ok, grav, eg = check(ram, n)
    good = count == ne and ok == ne and grav == eg
    print(f'pool n={n}: {ok}/{max(count, ne)} records match the table (count {count}, expected {ne}); '
          f'gravity {grav} expected {eg}; {"MATCH" if good else "DIFF"}  [{os.path.basename(sys.argv[1])}]')
    sys.exit(0 if good else 1)
