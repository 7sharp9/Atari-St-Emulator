#!/usr/bin/env python3
"""model_pick.py <allpicks.out>: replay $503c (class 4, hunt a group) + $548a for every `bp 5350` stop in the REPL
output and compare the predicted target with the game's A5. Each stop is followed by `m 51b66 25600`, `m 51500 1000`,
`m 57fed 1`. At $5350 the chosen record's claim byte 32 already holds the tick ($5340): it is treated as unclaimed."""
import re, sys

O = 0x51b66
HEX = re.compile(r'^[0-9a-f]{2}( [0-9a-f]{2})*\s*$')


def w(b, i):
    return int.from_bytes(b[i:i + 2], 'big')


def sb(v):
    return v - 256 if v > 127 else v


def weigh(A1, A3, off_hi, tick, st):
    """$548a. st = [D6, A5, D7]. off_hi: high byte left in D0 by the caller."""
    d1 = abs(w(A1, 8) - w(A3, 8)); d2 = abs(w(A1, 10) - w(A3, 10)); D1 = max(d1, d2)
    if D1 > 0xfff:
        st[2] -= 1; return
    lo = A3[32]
    if lo == tick:
        return
    acc = False
    if A1[44] in (0xe, 0x10, 6):
        acc = True
    else:
        lo = A1[44]
        if sb(A1[44]) > sb(A3[44]):
            acc = True
        else:
            lo = A1[45]
            if sb(A1[45]) >= sb(A3[45]):
                acc = True
            else:
                lo = A1[39]
                acc = lo == 2
    if not acc:
        return
    D0 = (off_hi << 8) | lo
    if sb16(st[0]) > sb16(D1):
        st[0] = D0; st[1] = 'cand'; st.append(None)
        return True


def sb16(v):
    return v - 0x10000 if v & 0x8000 else v


def model(obj, grp, a1off, tick):
    A1 = obj[a1off:a1off + 50]
    t = w(A1, 46); A0 = obj[t:t + 50]; lead_off = t
    if w(A0, 28):
        lead_off = w(A0, 28)
    A2 = obj[lead_off:lead_off + 50]
    g = 0x51538 + w(A2, 42) - 0x51500
    D0 = w(grp, g - 36)
    st = [0xfff, None, 0]; best = None
    while D0:
        A3 = obj[D0:D0 + 50]
        if sb(A3[5]) > 0 and A3[30] != 0x3c:
            st[2] += 1
            if weigh(A1, A3, D0 >> 8, tick, st):
                best = D0
        D0 = w(A3, 26)
    if sb(A2[5]) >= 0 and A2[30] != 0x3c:
        st[2] += 1
        if weigh(A1, A2, 0, tick, st):
            best = lead_off
    return best, lead_off


def main():
    parts = open(sys.argv[1]).read().split('--- breakpoint $00005350 hit')[1:]
    ok = bad = skip = lead_hits = 0
    for p in parts:
        regs = dict(re.findall(r'(A[0-7]):([0-9a-f]{8})', p))
        L = [l for l in p.splitlines() if HEX.match(l)][:3]
        if len(L) < 3:
            continue
        obj = bytearray(bytes.fromhex(L[0].replace(' ', ''))); grp = bytes.fromhex(L[1].replace(' ', ''))
        tick = int(L[2].strip(), 16)
        a1 = int(regs['A1'], 16) - O; a5 = int(regs['A5'], 16) - O
        if obj[a1 + 38] != 4:
            skip += 1; continue
        if obj[a5 + 32] == tick:
            obj[a5 + 32] = (tick - 1) & 0xff     # undo $5340's claim of the chosen record
        pred, lead = model(bytes(obj), grp, a1, tick)
        hit = pred == a5
        ok += hit; bad += not hit
        if a5 == lead:
            lead_hits += 1
        A1 = obj[a1:a1 + 50]
        print('$%05x r39 %d hp %3d wpn %d -> $%05x%s pred $%05x %s' % (O + a1, A1[39], A1[45], A1[44], O + a5,
              ' LEAD' if a5 == lead else '', O + (pred or 0), 'ok' if hit else 'MISMATCH'))
    print(f'class-4 picks: {ok} match, {bad} mismatch; {skip} other-class picks skipped; lead picked {lead_hits}')


main()
