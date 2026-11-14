#!/usr/bin/env python3
"""Prove the Manta fuel rule ($1ce56..$1ce86 in the Manta update $1cab4) against the emulator, tick by tick.

usage: fuel_proof.py [snap] [ticks] [addr=value:width ...]   (default: scratchpad/carrier/manta/m_takeoff.snap, 300;
       4ac=0100:2 sets hull 256, which exercises the +$100 branch)

The rule, read from the code (cc_all.asm, runtime addresses):
    $1ca60  $8e8 = ($8e8 + 1) & 15 ; seq $8fb      -> $8fb = $ff on every 16th main frame (counter wraps to 0), else 0
    $1ce56  if $8fb != 0:
                d0 = ((speed << 4) & $ffff) // 50          speed = slot+6, lsl.w #4 / divu #$32
                if hull (slot+20, signed word) <= 500: d0 += $100
                fuel (slot+10) = max(fuel - d0, 0)         word arithmetic, signed compare
The only code that writes $8fb is the seq at $1ca6e (whole-image scan of the 1 MB RAM image for the word $08fb at an
even address: one writer, four readers $1ce58 $1d202 $1dcdc $1e562, all `tst.b $8fb.w`).

From <snap> (Manta 0 on its first airborne tick; `w 126c 00ff0001` first: the crack's stack leak) this records, at every
entry of $1cab4 (one per main frame): $8fb, slot 0's speed, fuel and hull. It also stops at $1ce56 and $1ce8a while A1
is slot 0 ($498) to read the operands before the rule and the fuel after it, and puts a write watch on $8fb. The
prediction is made per tick from the operands read at $1ce56 and compared with the fuel read at $1ce8a.
Prints 'fuel ticks M match N' last.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
from ccpaths import *
import struct

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

SLOT0 = 0x498


def s16(v):
    v &= 0xffff
    return v - 65536 if v & 0x8000 else v


def predict(flag, speed, hull, fuel):
    """$1ce56..$1ce86."""
    if not flag:
        return fuel
    d0 = (((speed << 4) & 0xffff) // 50) & 0xffff             # lsl.w #4 truncates to a word; divu #50 quotient
    if not s16(hull) > 500:                                    # cmpi.w #$1f4 / bgt (signed)
        d0 = (d0 + 0x100) & 0xffff
    d1 = s16(fuel - d0)                                        # sub.w
    if d1 < 0:                                                 # cmp.w #0 / bge
        d1 = 0
    return d1


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else str(WORK / 'manta' / 'm_takeoff.snap')
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    s = StServer(str(ROOT))
    s('load', snapshot=snap)
    s('poke', addr=0x126c, width=4, value=0x00ff0001)
    for p in sys.argv[3:]:                                     # addr=value:width, hex, as flight_proof.py
        addr, rest = p.split('=')
        val, width = rest.split(':')
        s('poke', addr=int(addr, 16), width=int(width), value=int(val, 16))
    wid = s('watch_add', lo=0x8fb, hi=0x8fb, kind='w', max_events=10000)['id']
    w = lambda a: struct.unpack('>H', s.read(a, 2))[0]
    s('bp_set', addrs=[0x1cab4, 0x1ce56, 0x1ce8a])
    entries, pre, post = [], {}, {}
    pend = None
    n = -1                                                     # main-frame index of the current $1cab4 entry
    steps = 0
    while n < ticks:
        r = s('run', max_steps=400000)
        steps += r['steps']
        assert r['reason'] == 'breakpoint', r
        pc = s.reg('pc') & 0xffffff
        if pc == 0x1cab4:
            n += 1
            if n >= ticks:
                break
            entries.append(dict(flag=s.read(0x8fb, 1)[0], speed=w(SLOT0 + 6), fuel=w(SLOT0 + 10), hull=w(SLOT0 + 20),
                                state=w(SLOT0 + 28), cnt=w(0x8e8)))
        elif n >= 0 and s.reg('a1') == SLOT0:
            if pc == 0x1ce56:
                pre[n] = dict(flag=s.read(0x8fb, 1)[0], speed=w(SLOT0 + 6), fuel=w(SLOT0 + 10), hull=w(SLOT0 + 20))
            else:
                post[n] = w(SLOT0 + 10)
    ev = s('watch_events', id=wid)
    s('bp_clear', addrs=[0x1cab4, 0x1ce56, 0x1ce8a])
    s.close()

    dropped = sum(x['dropped'] for x in ev)
    events = [dict(e, pc=int(e['pc'].lstrip('$'), 16), value=int(e['value'].lstrip('$'), 16)) for x in ev for e in x['events']]
    print(f'{len(entries)} main frames, {steps} steps; $8fb writes: {len(events)}, writer PCs '
          f'{sorted({hex(e["pc"] & 0xffffff) for e in events})}, dropped {dropped}')
    on = [e['step'] for e in events if e['value'] & 0xff]
    print(f'$8fb set (non-zero) {len(on)} times; step gaps {sorted({b - a for a, b in zip(on, on[1:])})}')
    ticks_with_flag = [k for k in pre if pre[k]['flag']]
    print(f'$1ce56 reached for slot 0 on {len(pre)} of {len(entries)} frames; $8fb nonzero there on frames {ticks_with_flag}')
    print(f'$8fb sampled at $1cab4 entry nonzero on frames {[k for k, e in enumerate(entries) if e["flag"]]}')
    print(f'frame: flag speed hull fuel_before fuel_after predicted  (flag ticks and mismatches only)')
    M = N = 0
    fell = 0
    for k in sorted(pre):
        if k not in post:
            continue
        p = pre[k]
        pr = predict(p['flag'], p['speed'], p['hull'], p['fuel'])
        M += 1
        ok = pr == post[k]
        N += ok
        fell += p['fuel'] - post[k]
        if p['flag'] or not ok:
            print(f'{k:4d}: {p["flag"]:#04x} {p["speed"]:5d} {p["hull"]:5d} {p["fuel"]:6d} {post[k]:6d} {pr:6d}{"" if ok else "  MISMATCH"}')
    # the same rule chained across frames from the first fuel value, no per-tick readback
    f = pre[min(pre)]['fuel']
    chain = 0
    for k in sorted(pre):
        if k not in post:
            continue
        chain += (f == pre[k]['fuel'])
        f = predict(pre[k]['flag'], pre[k]['speed'], pre[k]['hull'], f)
    print(f'fuel {pre[min(pre)]["fuel"]} -> {post[max(post)]} over {M} ticks, total fall {fell}; '
          f'fuel at $1ce56 equals the chained prediction on {chain}/{M} ticks')
    # control: the rule with $8fb ignored (subtract every tick) must fail
    ctrl = sum(predict(1, pre[k]['speed'], pre[k]['hull'], pre[k]['fuel']) == post[k] for k in post if k in pre)
    print(f'control (rule applied every tick, ignoring $8fb) matches {ctrl}/{M}')
    print(f'fuel ticks {M} match {N}')


main()
