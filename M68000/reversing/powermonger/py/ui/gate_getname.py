"""pm140 ui: gate for `_getname` $a9ce (the name generator behind every person, town and forest name in the info panels).

    cd M68000 && .venv/bin/python reversing/powermonger/py/ui/gate_getname.py [snap]

Model (Python) of $a9ce from its body: D0 (word, sign-extended) is loaded into the world RNG seed $2df84 for one draw of
$12c9a (seed*$bb40e62d mod 2^32, 0 -> $bc614e; result (seed >> 8) & $7fff), the seed is put back, then the 15 random bits
pick three syllables: per part 2 bits choose a group (lengths $aa4c = 3,3,2,1; group offsets $aa54 = 0,$18,$30,$40) and
3 bits an entry; the three parts read the tables at $aa5c, +$48, +$90; the first letter is upper-cased (and #$df).
Compared against the real routine by callcap (D0 = seed, A4 = buffer): the bytes written, D1 (the length), the seed left
unchanged.  Prints matched/total; exit 1 on any mismatch."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import *


def model_from(R, d0):
    """The name $a9ce builds for the word d0, from a RAM image R (tables at $aa4c..$aaec)."""
    lens = [int.from_bytes(R[0xaa4c + 2 * i:0xaa4e + 2 * i], 'big') for i in range(4)]
    offs = [int.from_bytes(R[0xaa54 + 2 * i:0xaa56 + 2 * i], 'big') for i in range(4)]
    seed = (d0 - 0x10000 if d0 & 0x8000 else d0) & 0xffffffff          # ext.l D0
    s = ((seed or 0xbc614e) * 0xbb40e62d) & 0xffffffff
    d3 = (s >> 8) & 0x7fff
    out = bytearray()
    for part in range(3):
        g = d3 & 3; d3 >>= 2
        i = d3 & 7; d3 >>= 3
        a = 0xaa5c + part * 0x48 + offs[g] + i * lens[g]
        syl = bytearray(R[a:a + lens[g]])
        if part == 0: syl[0] &= 0xdf
        out += syl
    return out.decode('latin1')


def main(snap):
    R = ram_of(snap)
    seeds = [0, 1, 2, 0x7fff, 0x8000, 0xffff, 0x1234, 0xabcd] + [(i * 2654435761 >> 7) & 0xffff for i in range(1, 57)]
    seeds += [(0x64 + 0x32 * i) & 0xffff for i in range(16)]            # offsets of real men ($51b66 + n*50 style)
    BUF = 0xc0000
    ccs = parse_callcaps(repl(snap, [f'callcap a9ce 5000 D0={s:x} A4={BUF:x}' for s in seeds]))
    ok = 0; bad = []
    for s, cc in zip(seeds, ccs):
        mem = {a: y for a, (x, y) in cc['mem'].items() if BUF <= a < BUF + 32}
        got = bytes(mem.get(BUF + i, 0) for i in range((max(mem) - BUF + 1) if mem else 0)).rstrip(b'\0').decode('latin1')
        d1 = cc['regs'].get('D1', (0, 0))[1] & 0xffff
        seed_ok = not any(0x2df84 <= a < 0x2df88 for a in cc['mem'])
        exp = model_from(R, s)
        if cc['returned'] and got == exp and d1 == len(exp) and seed_ok: ok += 1
        else: bad.append((hex(s), got, exp, hex(d1), seed_ok))
    print(f'getname $a9ce: {ok}/{len(seeds)} seeds match (string, length D1, seed restored)')
    for b in bad[:10]: print('  MISMATCH', b)
    print('first 20:', [(hex(s), model_from(R, s)) for s in seeds[:20]])
    return ok == len(seeds)


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'scratchpad/pm123/win/m1_s0.snap')) else 1)
