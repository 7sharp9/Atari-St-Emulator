#!/usr/bin/env python3
"""Hidden keys, the cheat-mode extras and the disabled exception handler in Carrier Command, each against a control.

usage: hidden.py keys        every key trial: the keys pressed against the same snapshot and budget with no key
       hidden.py andy        the exception handler $17918: an illegal opcode with vector 4 pointed at it, and with
                             the vector as shipped
       hidden.py words       decode the manual-word protection table ($9da2's encoding) to stdout

Every run loads c_s30.snap (Strategy game, README "Snapshots") and pokes the crack fix w 126c 00ff0001 first. A key
is a make code then its break code through stserver's kbd (README "Running it": keyboard input works normally);
the cheat trials set $1185 = $ff, the flag the cheat phrase sets (ai.md section 7). Each trial counts PC arrivals at
the address the key's handler reaches (its signal) over the hold and 60,000 steps after the release, and prints
'<name> keys N control M'. PNGs go to $CARRIER_WORK/curio/.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
from ccpaths import *

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

OUT = WORK / 'curio'

# name, make codes, break codes, signal addresses (the first is the one reported), cheat on, hold steps
TRIALS = [
    ('ctrl+V version', [0x1d, 0x2f], [0xaf, 0x9d], [0x16e38], False, 150000),      # $16e24: "Release Version 1.01"
    ('alt+help message', [0x38, 0x62], [0xe2, 0xb8], [0x3adc], False, 150000),      # $3acc: "Yes, I have kicked out the OS"
    ('ctrl+S pause', [0x1d, 0x1f], [0x9f, 0x9d], [0xf84a], False, 150000),          # $3ab6 -> $f84a
    ('ctrl+Q resume', [0x1d, 0x10], [0x90, 0x9d], [0xf85e], False, 150000),         # $3a92 -> $f85e
    ('keypad 6 colour card', [0x6c], [0xec], [0x20e06], True, 150000),              # $20dfa
    ('keypad 6 without cheat', [0x6c], [0xec], [0x20e06], False, 150000),
    ('keypad 8 frame meter', [0x68], [0xe8], [0x17504], True, 150000),              # $174fa toggles $1227
    ('keypad 7 main loops', [0x67], [0xe7], [0x3a04], True, 1200000),               # $3a2e: skip draw and flip
    ('keypad 7 view draws', [0x67], [0xe7], [0x13f8e], True, 1200000),
]


def keys():
    OUT.mkdir(parents=True, exist_ok=True)
    s = StServer(str(ROOT))
    s('load', snapshot=str(ANCHOR))
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    base = s('fork')
    base = base['id'] if isinstance(base, dict) else base
    for name, make, brk, sig, cheat, hold in TRIALS:
        got = []
        for ctl in (False, True):
            s('restore', id=base)
            if cheat:
                s('poke', addr=0x1185, width=1, value=0xff)
            if not ctl:
                s('kbd', bytes=make)
            a = s('hits', steps=hold, addrs=sig)['hits']
            if not ctl:
                s('kbd', bytes=brk)
            b = s('hits', steps=60000, addrs=sig)['hits']
            got.append(a[0]['count'] + b[0]['count'])
            tag = name.split()[0].replace('+', '').lower() + name.split()[1]
            s('render', path=str(OUT / f'{tag}_{"ctl" if ctl else "key"}.png'))
        print(f'{name}: keys {got[0]} control {got[1]}')
    s.close()


def andy():
    OUT.mkdir(parents=True, exist_ok=True)
    for mode in ('handler', 'shipped'):
        s = StServer(str(ROOT))
        s('load', snapshot=str(ANCHOR))
        s('poke', addr=0x126c, width=4, value=0x00ff0001)
        s('poke', addr=0x800, width=2, value=0x4afc)          # ILLEGAL
        if mode == 'handler':
            s('poke', addr=0x10, width=4, value=0x04017918)    # vector 4, tagged as the installer would, one word on
        vec = s('read', addr=0x10, len=4)
        s('set_reg', name='pc', value=0x800)
        r = s('run', max_steps=3000000, until_pc=0x20b4c)       # the dump's final endless loop
        print(f'andy {mode}: vector 4 = {vec}, {r.get("reason")} after {r.get("steps")} steps')
        s('render', path=str(OUT / f'andy_{mode}.png'))
        s.close()


def words():
    m = ram()
    p = 0x4cd1a
    for idx in range(192):
        n = m[p]
        k = ((idx + 1) ^ 0x61) & 0xff
        w = bytes(m[p + 1 + j] ^ (j + 1) ^ k for j in range(n))
        p += 1 + n
        t = bytes(b ^ k for b in m[0x4c65a + idx * 9:0x4c65a + idx * 9 + 9])
        pg, para, word = (int(t[i:i + 3]) for i in (0, 3, 6))    # three right-aligned 3-digit ASCII numbers
        print(f'{idx:3d} {"EGF"[idx // 64]} page {pg:3d} paragraph {para:2d} word {word:2d}  {w.decode("latin-1")}')


if __name__ == '__main__':
    {'keys': keys, 'andy': andy, 'words': words}[sys.argv[1]]()
