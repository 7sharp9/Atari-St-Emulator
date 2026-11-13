"""fed_MapGen's base path in Python from (D0, D2) alone, compared with the emulator's returned output.

    uv run python -I reversing/captive/py/mapgen/full/chain_run.py gate <capture_final.bin> [...]     # chain vs emulator, per case
    uv run python -I reversing/captive/py/mapgen/full/chain_run.py encoder <capture_final.bin> [...]  # encoder model from the emulator's $200ee state
    uv run python -I reversing/captive/py/mapgen/full/chain_run.py locks <capture_final.bin> [...]   # lock/key census over the chained bases
    uv run python -I reversing/captive/py/mapgen/full/chain_run.py run <d0> <d2> <out.bin>            # write module, federation block, D0/D5/D6

The start state is constructed, not captured:
  module block: zeros, the 14 output pointers 13684..13740 (A0 = $1d9e8 plus the offsets at $b532, accumulated as
    $20092-$200e6 does), and the constants 12400 = 1, 13208 = $3f, 13624 = $c7, 13628 = 7 (coded-door slots), 13630 = 4;
    then shafts/chain.build() adds the seed-dependent bytes (zones.plan(D0), D0, D2, RNG word ...). The construction
    is checked against the captured template (mktemplate.py, template_23ca4.bin) on every run.
  federation block $1bd3e..$1d9e8: zeros; $ff over the 9 + 2 terminal cells of 13696 / 13700 and the 576-byte lock list
    13720; list headers (size, free, $88828881) at 13724 ($800) and 13716 ($1000). Checked against mg_ret.snap's block.
Then the stages in $23bb0's order (stages/common.STAGES), the encoder $23936, and $200f2's copy of module bytes 0..33
to 13692(A6). The comparison covers the whole module block and federation $1bd3e..$1ea08 (tables, tile layer
13684 = $1d9e8, plane 2 13688 = $1e208) plus the returned D0, D5, D6.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'shafts'))
sys.path.insert(0, HERE)
import cmodels as C  # noqa: E402
import pmodels as P  # noqa: E402
import models  # noqa: E402
import common  # noqa: E402
from shafts import Gen  # noqa: E402
import chain as SC  # noqa: E402  (shafts/chain.py: build, flowfield)

DATA = os.path.join(P.R, 'scratchpad', 'captive', 'mapgen_full')   # output and constant inputs (gitignored)

MLEN = 0x35bc
FED, FTAB, FEND = 0x1bd3e, 0x1d9e8, 0x1ea08
REC = 4 + 3 * (MLEN + FEND - FED) + 12
PTR_OFFSETS = 0xb532      # federation's table of 14 signed word offsets (A1)
SLOT_ORDER = (13684, 13692, 13696, 13700, 13704, 13708, 13712, 13716, 13720, 13724, 13728, 13732, 13740, 13736, 13688)


def fw(addr):
    ram, b = models.code()
    v = (ram[addr - b] << 8) | ram[addr - b + 1]
    return v - 0x10000 if v & 0x8000 else v


def template():
    t = bytearray(MLEN)
    a = 0x1d9e8          # $20092-$200e6: store A0, then adda.w (A1)+ before the next slot
    for i, slot in enumerate(SLOT_ORDER):
        t[slot:slot + 4] = a.to_bytes(4, 'big')
        a = (a + fw(PTR_OFFSETS + 2 * i)) & 0xffffffff
    t[12401], t[13209], t[13625], t[13629], t[13631] = 1, 0x3f, 0xc7, 7, 4
    return t


def gap():
    """$1e1e8..$1e208, between the two layers: not written by the module; mg_ret.snap's bytes."""
    ram, b = models.code()
    return bytearray(ram[0x1e1e8 - b:0x1e208 - b])


def fed_init(m):
    f = bytearray(FTAB - FED)
    def p(slot):
        return int.from_bytes(m[slot:slot + 4], 'big') - FED
    f[p(13696):p(13696) + 22] = b'\xff' * 22   # 13696 (9 cells) and 13700 (2 cells) are adjacent
    f[p(13720):p(13720) + 576] = b'\xff' * 576
    f[p(13724):p(13724) + 8] = bytes.fromhex('080007f888828881')
    f[p(13716):p(13716) + 8] = bytes.fromhex('10000ff888828881')
    return f


def check_constants():
    t = template()
    cap = open(os.path.join(DATA, 'template_23ca4.bin'), 'rb').read()
    built = SC.build(t, 0, 1)
    ok_t = built == bytearray(cap)
    ok_f = fed_init(t) == bytearray(open(os.path.join(DATA, 'fed_init.bin'), 'rb').read())
    return ok_t, ok_f


def stage_fn(stop, callee):
    if stop in models.MODELS_BY_STOP:
        return models.MODELS_BY_STOP[stop]
    for tab in (C.MODELS, P.MODELS, models.MODELS):
        if callee in tab:
            return tab[callee]
    return None


def generate(d0, d2, upto=None, hook=None):
    """Returns (module bytearray, federation $1bd3e..$1ea08 bytearray, (D0, D5, D6)). `hook(name, S)` is called after
    every stage with the stage's callee address. `upto` stops after that callee (before the encoder)."""
    t = template()
    b = SC.build(t, d0, d2)
    g = Gen(b)
    saved = g.W(12404)
    g.shafts()
    g.SW(12404, saved)
    g.reserve()
    g.run()
    g.unreserve()
    SC.flowfield(g.m)
    f = fed_init(t)
    q = int.from_bytes(t[13712:13716], 'big') - FED
    S = models.State(g.m, f)
    for fn in (models.s_25198, models.s_2533a, models.s_25198, models.s_25162):
        fn(S)
    g.m = S.b.a
    g.pass2()
    f[q:q + 50] = g.m[13460:13510]
    S = C.State(g.m, f)
    if hook:
        hook(0x263fa, S)
    i0 = [s for s, _ in common.STAGES].index(0x23cd0) + 1
    for stop, callee in common.STAGES[i0:]:
        if callee == 0x2676c and d2 != 1:
            continue
        stage_fn(stop, callee)(S)
        if hook:
            hook(callee, S)
        if upto == callee:
            return S.b.a, S.f, None
    outa, outb = bytearray(2048), bytearray(2048)
    C.encode(S, outa, outb)
    if hook:
        hook(0x23936, S)
    m = S.b.a
    o = int.from_bytes(m[13692:13696], 'big') - FED
    S.f[o:o + 34] = m[0:34]
    full = S.f + outa + gap() + outb
    regs = (int.from_bytes(m[13748:13750], 'big'), int.from_bytes(m[12392:12396], 'big'),
            int.from_bytes(m[12396:12400], 'big'))
    return m, full, regs


def records(path):
    b = open(path, 'rb').read()
    n = MLEN + FEND - FED
    for i in range(0, len(b), REC):
        r = b[i:i + REC]
        d0, d2 = struct.unpack('>HH', r[:4])
        st = []
        for j in range(3):
            o = 4 + j * n
            st.append((r[o:o + MLEN], r[o + MLEN:o + n]))
        regs = struct.unpack('>III', r[4 + 3 * n:])
        yield {'d0': d0, 'd2': d2, 'pre': st[0], 'post': st[1], 'ret': st[2], 'regs': regs}


def first_diff(a, b, base):
    for i in range(len(b)):
        if a[i] != b[i]:
            return hex(base + i) if base else i
    return None


def gate(paths):
    ok_t, ok_f = check_constants()
    print(f'constructed template == captured template: {ok_t}; constructed federation block == mg_ret.snap: {ok_f}')
    n = ok = okpre = 0
    for p in paths:
        for r in records(p):
            n += 1
            m, full, regs = generate(r['d0'], r['d2'])
            em, ef = r['ret']
            good = m == em and full == ef and tuple(regs) == (r['regs'][0] & 0xffff, r['regs'][1], r['regs'][2])
            ok += good
            if not good:
                # localise: the module block before the encoder, then each output region
                print(f"  miss d2={r['d2']} d0={r['d0']}: module {first_diff(m, em, 0)} fed {first_diff(full, ef, FED)}"
                      f" regs {regs} vs {r['regs']}")
    print(f'chained output == emulator return (module block, federation $1bd3e..$1ea08, D0/D5/D6): {ok}/{n}')


def encoder(paths):
    n = ok = acted = 0
    for p in paths:
        for r in records(p):
            n += 1
            m0, f0 = r['pre']
            m1, f1 = r['post']
            S = C.State(bytearray(m0), bytearray(f0[:FTAB - FED]))
            outa, outb = bytearray(2048), bytearray(2048)
            C.encode(S, outa, outb)
            full = S.f + outa + gap() + outb
            acted += f0 != f1
            if S.b.a == bytearray(m1) and full == bytearray(f1):
                ok += 1
            elif n - ok < 4:
                print(f"  miss d2={r['d2']} d0={r['d0']} module {first_diff(S.b.a, m1, 0)} fed {first_diff(full, f1, FED)}")
    print(f'encoder $23936 from the emulator state at $200ee == state at $200f2: {ok}/{n} ({acted} changed)')


def main():
    a = sys.argv[1:]
    if '--break' in a:
        i = a.index('--break')
        name, val = a[i + 1].split('=')
        C.K[name] = eval(val, {})
        del a[i:i + 2]
    if a[0] == 'gate':
        gate(a[1:])
    elif a[0] == 'encoder':
        encoder(a[1:])
    elif a[0] == "locks":
        import lockcensus as census
        census.main(a[1:])
    elif a[0] == 'run':
        m, full, regs = generate(int(a[1], 0), int(a[2], 0))
        open(a[3], 'wb').write(bytes(m) + bytes(full) + struct.pack('>III', *regs))


if __name__ == '__main__':
    main()
