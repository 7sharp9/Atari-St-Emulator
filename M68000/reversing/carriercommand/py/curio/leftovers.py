#!/usr/bin/env python3
"""Carrier Command leftovers and the title view, each against a control (README "Hidden keys and leftovers").

usage: leftovers.py meter [--break]   $118e against the $7688 arrivals between two $17534 stops (--break counts $7624)
       leftovers.py title             the view-33 handler $15978 runs at the title (c_eng.snap) and the main loop does not;
                                      keypad + and - step the entity type with the cheat flag poked
       leftovers.py spawn             forced call of the unreferenced $3dbc and of the damage helper $1e462
       leftovers.py dump              the unreferenced debug print $14048, shown by a poke of view 0's table entry
       leftovers.py census <budget> <snap>...   hits census of the candidate addresses over snapshots (with controls)

Every run loads c_s30.snap (or c_eng.snap for 'title') and pokes the crack fix w 126c 00ff0001 first. Pokes and forced
calls are named in the output lines. PNGs go to $CARRIER_WORK/curio/leftovers/.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
from ccpaths import *
import struct

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

OUT = area_dir('curio/leftovers')


def server(snap=ANCHOR):
    s = StServer(str(ROOT))
    s('load', snapshot=str(snap))
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    return s


def W(s, a, n=2): return int.from_bytes(s.read(a, n), 'big')
def fid(s):
    f = s('fork'); return f['id'] if isinstance(f, dict) else f


def meter(broken=False):
    s = server()
    s('poke', addr=0x1185, width=1, value=0xff)                 # poke: the cheat flag
    s('kbd', bytes=[0x68]); s('run', max_steps=100000); s('kbd', bytes=[0xe8])      # keypad 8 toggles the meter
    r = s('run', max_steps=3000000, until_pc=0x17534)
    ok = 0
    for k in range(6):
        sa = r['step']; f = fid(s)
        r2 = s('run', max_steps=3000000, until_pc=0x17534)
        read_there = W(s, 0x118e)                              # what the meter reads at the next stop
        s('restore', id=f)
        h = s('hits', steps=r2['step'] - sa, addrs=[0x7688, 0x7624])
        c = {x['addr']: x['count'] for x in h['hits']}
        counted = c['$007624'] if broken else c['$007688']
        ok += counted == read_there
        s('restore', id=f); r = s('run', max_steps=3000000, until_pc=0x17534)
    s('render', path=str(OUT / 'meter_keypad8.png'))
    print(f'meter {"broken " if broken else ""}$118e = arrivals between stops: {ok}/6 windows')
    s.close()


def title():
    s = server(WORK / 'c_eng.snap')
    base = fid(s)
    r = s('hits', steps=3000000, addrs=[0x15978, 0x3a04, 0x3df2, 0x14048])
    c = {x['addr']: x['count'] for x in r['hits']}
    print(f'title view33 $15978 arrivals {c["$015978"]} main loop $3a04 {c["$003a04"]} cheat check $3df2 {c["$003df2"]} dump $14048 {c["$014048"]}')
    for name, mk, bk, want in (('plus', 0x4e, 0xce, 2), ('minus', 0x4a, 0xca, 73)):
        s('restore', id=base)
        s('poke', addr=0x1185, width=1, value=0xff)             # poke: the cheat flag
        s('run', max_steps=200000)
        s('kbd', bytes=[mk]); s('run', max_steps=150000); s('kbd', bytes=[bk]); s('run', max_steps=300000)
        t = W(s, 0x64d12)
        print(f'title keypad {name}: type 1 -> {t}, expected {want}: {int(t == want)}/1')
        if name == 'plus': s('render', path=str(OUT / 'title_viewer.png'))
    s('restore', id=base)
    s('run', max_steps=200000)
    s('kbd', bytes=[0x4e]); s('run', max_steps=150000); s('kbd', bytes=[0xce]); s('run', max_steps=300000)
    print(f'title keypad plus without the cheat flag: type -> {W(s, 0x64d12)} (control, expected 1)')
    s.close()


def spawn():
    s = server(); s('run', max_steps=300000)
    base = fid(s)
    s.call_resume(0x3dbc)                                       # forced call of the unreferenced routine
    e = s.read(0x5f5da, 64)
    typ, pos = struct.unpack('>h', e[2:4])[0], struct.unpack('>iii', e[10:22])
    s('run', max_steps=600000)
    moved = struct.unpack('>i', s.read(0x5f5da + 10, 4))[0]
    s('restore', id=base); s('run', max_steps=600000)
    ctl = s.read(0x5f5da, 64)
    print(f'forced $3dbc: slot $5f5da type {typ} at {pos}: {int(typ == 33 and pos == (5000, 500, -10000))}/1; x after 600000 steps {moved}; control slot all zero: {int(not any(ctl))}/1')
    ok = 0
    for dmg, want in ((10, 90), (5000, 0)):
        s('restore', id=base); s.call_resume(0x3dbc)
        s('poke', addr=0x5f5da + 20, width=2, value=100)       # poke: hull 100
        s.call_resume(0x1e462, a1=0x5f5da, a4=0x5e95a, d0=dmg, max_steps=200000)   # forced call
        ok += struct.unpack('>h', s.read(0x5f5da + 20, 2))[0] == want
    print(f'forced $1e462 hull 100 after damage 10 and 5000: {ok}/2')
    s.close()


def dump():
    s = server(); s('run', max_steps=300000)
    s('poke', addr=0x13fbc, width=4, value=0x14048)             # poke: view 0's handler := the debug print
    for _ in range(3): s('run', max_steps=100000)
    s('render', path=str(OUT / 'debug_dump_as_view0.png'))
    print('dump rendered with view 0 -> $14048 (poke); first $e14 word', W(s, 0xe14))
    s.close()


def census():
    budget = int(sys.argv[2])
    addrs = [0x3dbc, 0x1f7d4, 0x1f7e4, 0x1e462, 0x1ecaa, 0x1ecb6, 0x2119e, 0x19e1c, 0x14048, 0x15978,
             0x3a04, 0x13f8e, 0x208c0, 0x1ac8c]                 # the last four are positive controls
    for sp in sys.argv[3:]:
        s = server(sp)
        r = s('hits', steps=budget, addrs=addrs)
        print(sp, [(h['addr'], h['count']) for h in r['hits']], flush=True)
        s.close()


if __name__ == '__main__':
    m = sys.argv[1]
    {'meter': lambda: meter('--break' in sys.argv), 'title': title, 'spawn': spawn, 'dump': dump, 'census': census}[m]()
