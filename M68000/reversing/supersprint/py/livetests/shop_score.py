"""shop_score.py - item 3 of the shop ("increase score level taken"): the purchase calls $16084(car, desc), the 6-digit score adder.
Reads the score digits -4846+6*car (blank = 0x80 | digit) around each carousel item's purchase and the descriptor actually passed."""
from lt import *
def to_shop():
    r = Repl2(sscfg.SNAP_RESULTS)
    r.cmd('s 1000000'); r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00')
    out, regs = r.cmd('bp 19984 20000000'); assert regs['PC'] == 0x19984
    return r
def val(d):
    s = 0
    for x in d: s = s * 10 + (x & 0x7f)
    return s
for dial in (2, 4, 8, 12):
    for lvl in (0, 3):
        r = to_shop()
        setwords(r, {A4 - 3914 + 2: 0, A4 - 3954 + 2: 8, A4 - 4066 + 2 * 3: lvl})
        out, regs = r.cmd('bpc 19daa 1 6000000'); assert regs['PC'] == 0x19daa
        setwords(r, {regs['A6'] - 4: dial})
        sc0 = list(r.mem(A4 - 4846 + 6, 6))
        r.cmd('kbd fe 80')
        out, regs = r.cmd('bp 16084 6000000')
        info = ''
        if regs['PC'] == 0x16084:
            sp = regs['A7']
            car = r.words(sp + 4, 1)[0]; dp = struct.unpack('>I', r.mem(sp + 6, 4))[0]
            info = ' $16084 entered: car %d desc @%x = %s' % (car, dp, r.mem(dp, 6).hex())
        out, regs = r.cmd('bpc 1a022 1 6000000')
        sc1 = list(r.mem(A4 - 4846 + 6, 6))
        print('dial %2d (item %d) item-3 level before %d: score %s (%d) -> %s (%d), delta %d;%s' % (dial, [1, 3, 2, 0][dial >> 2], lvl, sc0, val(sc0), sc1, val(sc1), val(sc1) - val(sc0), info), flush=True)
        r.close()
