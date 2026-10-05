"""charlib.py: ROM readers and log readers for the per-character gates (Agent D, Final Fight pass 4).
Character index (+20 of a player record): 0 Guy, 1 Cody, 2 Haggar. Tables are read from the program ROM (scratchpad/finalfight/ff_main.bin).
The log format is pdrive.lua (+ extra_enemy.lua 'E' lines). The player's +92 (damage base + rank + $60) is read from the state's RAM dump."""
import os, sys, collections
here = os.path.dirname(os.path.abspath(__file__))
def _root():
    r = os.environ.get('M68000_ROOT')
    if r: return r
    d = here
    while d != '/' and not os.path.exists(os.path.join(d, 'scratchpad/finalfight/ff_main.bin')): d = os.path.dirname(d)
    return d
root = _root()
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
OUT = os.environ.get('FFD_OUT') or os.path.join(root, 'scratchpad/finalfight/twoplayer/out')   # same default as run/env.sh
def w(a): return int.from_bytes(rom[a:a+2], 'big')
def sw(a):
    v = w(a); return v - 0x10000 if v >= 0x8000 else v
def l(a): return int.from_bytes(rom[a:a+4], 'big')
NAMES = {0: 'guy', 1: 'cody', 2: 'haggar'}
def data_ptr(ch): return l(0xa124 + 8 * ch)
def box_base(ch): return l(0xa124 + 8 * ch + 4)
def attack_box(ch, idx):
    A0 = box_base(ch); a = A0 + (idx & 0x7f) * 16 + w(A0)
    return dict(addr=a, dx=sw(a), dy=sw(a+2), hw=sw(a+4), hh=sw(a+6), off=w(a+8), hit=rom[a+11] & 0x7f, hard=bool(rom[a+11] & 0x80), sound=w(a+12))
def hit_award(ch, off):
    base = 0x7ac6 + w(0x7ac6 + 2 * ch); code = w(base + 2 * (off >> 5)); return code, AMT.get(code & 0x7f)
AMT = {0: 0, 1: 10, 2: 50, 3: 100, 4: 10000, 5: 5000, 6: 3000, 7: 1000, 8: 1, 9: 20, 10: 30, 11: 200, 12: 250, 13: 300, 14: 350, 15: 400, 16: 500, 17: 600, 18: 800, 19: 1200, 20: 1400, 21: 1500, 22: 1600,
       23: 2000, 24: 2500, 25: 15000, 26: 20000, 27: 30000, 28: 50000, 29: 4000, 30: 40000, 31: 100000, 32: 42910, 33: 700}
def strike_damage(ch, step): return w(0xdb6e + 8 * ch + step)
def combo_limit(ch): return w(0xbe92 + 2 * ch)
def walk_threshold(ch): return l(0xc0c4 + 4 * ch)
def jump_speed(ch): return w(0xac76 + 4 * ch), w(0xac78 + 4 * ch)
def state_p92(ch, state='dch%d_1900'):
    d = open(os.path.join(OUT, (state % ch) + '_ram.bin'), 'rb').read(); a = 0x8568
    return int.from_bytes(d[a+92:a+96], 'big') & 0xffffff
def damage_byte(p92, off): return rom[p92 + off]

def load(name):
    rows, ev = [], collections.defaultdict(list)
    for ln in open(os.path.join(OUT, name + '.txt')):
        p = ln.split()
        if ln[0] == 'E':
            d = dict(t.split('=') for t in p[3:]); d['rel'] = int(p[2]); ev[int(d['i'])].append(d); continue
        if ln[0] in 'QC': continue
        d = {t.split('=')[0]: t.split('=')[1] for t in p[2:] if '=' in t}; d['rel'] = int(p[1]); rows.append(d)
    return rows, ev
def bcd(v): return int('%x' % v)
def score(r): return bcd(int(r['scH'] + r['sc'], 16))
def s16(v): return v - 0x10000 if v >= 0x8000 else v
def hits(name, idx=12):
    """hp changes of the dummy record idx: (rel, dhp, victim +22 id, victim +63 type, player row at rel, score delta over rel-1..rel+3)"""
    rows, ev = load(name); by = {r['rel']: r for r in rows}
    out = []; prev = None
    for e in ev[idx]:
        hp = s16(int(e['hp'], 16))
        if prev is not None and hp != prev:
            r = by[e['rel']]
            s0 = score(by[e['rel'] - 1]) if e['rel'] - 1 in by else None
            s1 = score(by[min(e['rel'] + 3, rows[-1]['rel'])])
            out.append((e['rel'], hp - prev, int(e['b22'], 16), int(e['b63'], 16), r, s1 - s0 if s0 is not None else None))
        prev = hp
    return out
