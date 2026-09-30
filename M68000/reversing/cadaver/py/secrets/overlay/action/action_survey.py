"""action_survey.py: the Cadaver 80th-pass Task A proof.  Every scenario starts from gameplay_empire.snap (CAVERN, day 1) or room2_tunnel_entry.snap
(TUNNEL), walks the hero with the joystick to an object, opens the icon panel with the fire button (near an object) or Space/Return (rucksack), picks an
icon, and reads which handler was entered, which ring-304 event was pushed (watch on the ring, entry = [op.w][template ptr.l][word.w], object id = word at
template+4) and what the consumer did.  Each action is repeated from a fresh emulator 3 times; the table prints matches n/3.
    uv run python reversing/cadaver/py/secrets/overlay/action/action_survey.py
Requires only the existing bin/Debug/net8.0/M68000.dll (ATARI_NOTRACE=1 set by Repl).  Writes snapshots under its own directory."""
from drv import *

N = 3
PUSHPC = {0xa40c: (0xa418, 16), 0xa47a: (0xa486, 5), 0xa590: (0xa59c, 5), 0xa5c6: (0xa5d2, 5), 0xa6e6: (0xa6f4, 18), 0xa722: (0xa72e, 27),
          0xa796: (0xa7a4, 26), 0xa7c2: (0xa7ce, 5), 0xa178: (0xa184, 0)}       # pc of `move.w #op,(A0)+` -> (count site, event)

def route(name, start, legs):
    r = Repl(start)
    for bits in legs: walk(r, bits)
    path = OUT + f'sv_{name}.snap'; r.snap(path); p = pos(r); r.close(); return path, p

def act_object_panel(snap, icon):
    r = Repl(snap); t = Tally(r); ids = idmap(r); watch_queue(r)
    open_panel(r, t); ic = icons(r); pick_icon_id(r, t, icon); evs = events(r, ids=ids)
    out = dict(icons=ic, hits=dict(t.tot), evs=evs, gold=r.a5(1188, 4).hex(), cnt=r.a5(2438, 1)[0], t8=type8(r)['recs'][:1], sel=r.a5(1262, 2).hex())
    r.close(); return out

def act_ruck_panel(snap, icon, mode='space', pre=None):
    r = Repl(snap); t = Tally(r); ids = idmap(r); watch_queue(r)
    if pre: pre(r)
    ruck_panel(r, t, mode); ic = icons(r); pick_icon_id(r, t, icon); evs = events(r, ids=ids)
    out = dict(icons=ic, hits=dict(t.tot), evs=evs, gold=r.a5(1188, 4).hex(), cnt=r.a5(2438, 1)[0], t8=type8(r)['recs'][:1], sel=r.a5(1262, 2).hex())
    r.close(); return out

def pushed(evs):
    """the events pushed by the player-action block (not the per-frame 9/7 of the proximity handler $009440)"""
    return [(PUSHPC[pc][1], oid, w) for pc, op, ptr, oid, s, w in evs if pc in PUSHPC]

ROWS = []
def check(label, fn, expect_hits, expect_evs, extra=None):
    ok = 0; last = None
    for i in range(N):
        o = fn(); last = o
        h = all(o['hits'].get(a, 0) >= 1 for a in expect_hits); e = pushed(o['evs']) == expect_evs
        x = extra(o) if extra else True
        ok += 1 if (h and e and x) else 0
    hh = {hex(a): last['hits'].get(a, 0) for a in expect_hits}
    ROWS.append((label, hh, pushed(last['evs']), f'{ok}/{N}', last))
    cons = {hex(a): last['hits'].get(a, 0) for a in (0xfe24, 0xfe5a)}
    print(f'{label:58s} entry {hh}  pushed {pushed(last["evs"])}  consumer(block matched, verbs run) {cons}  gold {last["gold"]}  match {ok}/{N}', flush=True)

if __name__ == '__main__':
    snap = ensure
    print('\n== object panel (fire held near an object opens $009c82; icon chosen with joystick, confirmed with fire; dispatch $00a08c -> $00a0ac table)')
    check('coin  icon 2 take     -> $a136', lambda: act_object_panel(snap('coin'), 2), [0xa08c, 0xa136, 0xa14a, 0xc42a, 0xa184], [(0, 412, None)],
          lambda o: o['gold'] == '00000007' and o['hits'].get(0xfe24, 0) >= 1)
    check('coin  icon 11 examine -> $a3d0', lambda: act_object_panel(snap('coin'), 11), [0xa08c, 0xa3d0, 0xa418], [(16, 412, None)], lambda o: o['hits'].get(0xfe24, 0) >= 1)
    check('pickaxe icon 2 take   -> $a136', lambda: act_object_panel(snap('pick'), 2), [0xa136, 0xa14a, 0xc42a, 0xa184], [(0, 168, None)],
          lambda o: o['cnt'] == 1 and o['t8'] == [(168, 32)])
    check('pickaxe icon 11 examine', lambda: act_object_panel(snap('pick'), 11), [0xa3d0, 0xa418], [(16, 168, None)], lambda o: o['hits'].get(0xfe24, 0) >= 1)
    check('pickaxe icon 10 use   -> $a66a (no push)', lambda: act_object_panel(snap('pick'), 10), [0xa66a], [])
    check('boat  icon 11 examine', lambda: act_object_panel(snap('boat'), 11), [0xa3d0, 0xa418], [(16, 257, None)], lambda o: o['hits'].get(0xfe24, 0) >= 1)
    check('barrel icon 11 examine (no bit 5: generic banner)', lambda: act_object_panel(snap('barrel'), 11), [0xa3d0], [],
          lambda o: o['hits'].get(0xa418, 0) == 0)
    check('barrel icon 9  -> $a5c0 use (potion barrel)', lambda: act_object_panel(snap('barrel'), 9), [0xa5c0, 0xa5d2], [(5, 60, None)])
    check('BOOK  icon 8 read    -> $a292 -> $a474', lambda: act_object_panel(snap('book'), 8), [0xa292, 0xa486], [(5, 488, None)], lambda o: o['hits'].get(0xfe24, 0) >= 1)
    check('TOME  icon 8 read    -> $a292 -> $a474', lambda: act_object_panel(snap('tome'), 8), [0xa292, 0xa486], [(5, 510, None)], lambda o: o['hits'].get(0xfe24, 0) >= 1)
    check('DIARY icon 8 read (class 7: stats window, no push)', lambda: act_object_panel(snap('diary'), 8), [0xa292], [], lambda o: o['hits'].get(0xa486, 0) == 0)
    check('DIARY icon 2 take', lambda: act_object_panel(snap('diary'), 2), [0xa136, 0xa184], [(0, 5, None)], lambda o: o['t8'] == [(5, 120)])
    check('TUNNEL lever icon 7 -> $a448 use', lambda: act_object_panel(snap('lever'), 7), [0xa448, 0xa486], [(5, 144, None)], lambda o: o['hits'].get(0xfe5a, 0) >= 1)
    print('\n== rucksack panel (Space or Return with >= 1 item; $006cce -> $009682 -> $009724 -> $009c82)')
    check('Space  icon 13 select -> $a70e', lambda: act_ruck_panel(ensure('held'), 13, 'space'), [0x6cce, 0x9682, 0x9724, 0xa70e, 0xa72e, 0xa73a], [(27, 168, None)],
          lambda o: o['sel'] == '00a8')
    check('Return icon 13 select (grid $97b4 first, fire, panel)', lambda: act_ruck_panel(ensure('held'), 13, 'return'), [0x6cce, 0x9682, 0x97b4, 0xa70e, 0xa72e], [(27, 168, None)],
          lambda o: o['sel'] == '00a8' and o['hits'].get(0x9c82, 0) == 2)
    print('\ndone')
