"""anim_model.py: Python transcription of the per-frame animation interpreter ($00af10 loop, $00afc8 step, op handlers $00b08c-$00b154) read from cad_all.asm.
anim block = 10 bytes at rec+rec[14]; template script at template+$28 (word pairs [op][arg]); frame table at template+$28+word(template+34), 8 bytes per frame.
step(T, a) advances one frame pass (one call of $afc8) on bytearray a, returns (events, stopped) where events = list of ('ev13', n), ('cls', n), ('mover', v), ('ruck', ...)."""

def frame_regs(T, a, D6):
    w34 = int.from_bytes(T[34:36], 'big')
    e = 0x28 + w34 + D6 * 8
    a[4:6] = T[e + 2:e + 4]; a[6:8] = T[e + 4:e + 6]

def step(T, a, inst=None):
    """one pass of $afc8 (skipped by the caller when rec+15 bit 0 is set).  returns (events, stopped)"""
    events = []; stopped = False
    D7 = a[3]; A2 = None
    while True:                                   # $afd8
        if a[0] != 0: break
        A2 = 0x28 + 2 * D7
        op = T[A2]
        if op == 0: break
        arg = T[A2 + 1]
        if op == 0xff: a[0] = 0xff; stopped = True; ret = 1
        elif op == 0xfe: a[0] = arg; ret = 1
        elif op == 0xfd: D7 = 0; ret = 0
        elif op == 0xfc: D7 = arg; ret = 0
        elif op == 0xfb: a[2] = 1; D7 = (D7 - 2) & 0xff; ret = 0
        elif op == 0xfa: a[2] = 0; D7 += 1; ret = 0
        elif op == 0xf9: a[0] = 0xfe; stopped = True; ret = 1
        elif op == 0xf8: events.append(('ev13', arg)); D7 += 1; ret = 0
        elif op == 0xf7: events.append(('cls', arg)); D7 += 1; ret = 0
        elif op in (0xf6, 0xf5): events.append(('ctr', op, arg)); D7 += 1; ret = 0
        elif op == 0xf4: events.append(('mover', 1)); D7 += 1; ret = 0
        elif op == 0xf3: events.append(('mover', 3)); D7 += 1; ret = 0
        else: raise ValueError('op %02x' % op)
        a[3] = D7 & 0xff
        if ret != 0: break
    D6 = a[1]                                     # $b008
    commit = False
    if a[0] == 0:                                 # $b020
        D6 = T[A2 + 1]; a[1] = D6; commit = True
    elif a[0] >= 0x80:
        pass                                      # $b04e: just show
    else:
        a[0] -= 1
        if a[0] == 0: commit = True               # $b028
    if commit:
        if a[2]:
            D7 -= 1
            if D7 == 0: a[2] = 0
        else: D7 += 1
        D7 &= 0xff
        D1 = a[9]
        if D1 == 0: a[3] = D7
        else:
            a[8] = (a[8] - 1) & 0xff
            if a[8] < 0x80: pass
            else: a[8] = D1; a[3] = D7
    frame_regs(T, a, D6)
    return events, stopped
