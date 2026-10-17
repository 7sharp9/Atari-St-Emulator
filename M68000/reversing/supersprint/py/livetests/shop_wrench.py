"""shop_wrench.py - what the wrench counter -3954(A4) feeds in the shop ($19984 gate, $199de purchase), same snapshot, one variable (the count).

Start: ss_race0.snap (winner's circle) + 1M steps + a joystick-0 fire tap -> stop at the entry of $19984 (as secrets/py/mk_shop.py).  Poke (labelled)
slot 1 flag -3912 = 0 (a playing human) and wrenches -3952 = N.  Then run: does $199de (the purchase screen) start within 400k steps?  If so hold
fire (immediate choice) and run to the end of the purchase ($1a022, `unlk` of $199de) and read the wrench count and the upgrade levels
-4066..-4060 (slot 1) before/after.  Optional item choice: poke the dial word -4(A6) of $199de (item = -8794[dial >> 2]) at $19dfa... (arm `item3`)."""
from lt import *
def to_shop():
    r = Repl2(sscfg.SNAP_RESULTS)
    r.cmd('s 1000000'); r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00')
    out, regs = r.cmd('bp 19984 20000000')
    assert regs['PC'] == 0x19984, hex(regs['PC'])
    return r
for N in (0, 3, 4, 5, 8, 12):
    r = to_shop()
    setwords(r, {A4 - 3914 + 2: 0, A4 - 3954 + 2: N})
    lv0 = r.a4w(-4066, 4)
    out, regs = r.cmd('bpc 199de 1 600000')
    entered = regs['PC'] == 0x199de
    msg = 'wrench N=%2d: purchase screen $199de entered: %s' % (N, entered)
    if entered:
        r.cmd('kbd fe 80')
        out, regs = r.cmd('bpc 1a022 1 6000000')
        msg += '; purchase finished %s; wrench %d -> %d; levels slot 1 %s -> %s' % (regs['PC'] == 0x1a022, N, r.a4w(-3952, 1)[0], lv0, r.a4w(-4066, 4))
        msg += '; slot 0/2 wrench %s' % r.a4w(-3954, 3)
    print(msg, flush=True)
    r.close()

# purchase of each carousel position: poke the dial word -4(A6) of $199de at the loop head $19daa (item = -8794[dial >> 2] = 1,3,2,0)
for dial in (2, 4, 8, 12):
    r = to_shop()
    setwords(r, {A4 - 3914 + 2: 0, A4 - 3954 + 2: 8})
    out, regs = r.cmd('bpc 19daa 1 6000000')
    assert regs['PC'] == 0x19daa
    setwords(r, {regs['A6'] - 4: dial})
    sc0 = list(r.mem(A4 - 4846 + 6, 6)); desc = r.mem(A4 - 8800, 6).hex()
    r.cmd('kbd fe 80')
    out, regs = r.cmd('bpc 1a022 1 6000000')
    print('dial %2d (item %d): wrench 8 -> %d; levels slot 1 %s; slot-1 score digits %s -> %s (descriptor at -8800(A4) = %s)' % (dial, [1, 3, 2, 0][dial >> 2], r.a4w(-3952, 1)[0], r.a4w(-4066, 4), sc0, list(r.mem(A4 - 4846 + 6, 6)), desc), flush=True)
    r.close()
