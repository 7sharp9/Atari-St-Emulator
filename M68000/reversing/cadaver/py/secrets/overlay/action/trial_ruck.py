from drv import *
def trial_ruck(snap, want, mode='space', label='', pre=None, watch=True):
    r = Repl(snap)
    if pre: pre(r)
    t = Tally(r)
    print(f'--- {label} rucksack panel via {mode}, icon {want}')
    print('  before:', state(r), 'held', r.a5(1236,2).hex(), 'gold', r.a5(1188,4).hex())
    if watch: watch_queue(r)
    ruck_panel(r, t, mode)
    print('  panel: icons', icons(r), 'cnt', r.a5(2303,1).hex(), '2302', r.a5(2302,1).hex(), 'front', r.a5(2128,2).hex(), 'fcls', r.a5(2476,1).hex(), 'held', r.a5(1236,2).hex(), 'pc', hex(r.pc()))
    ok = True
    try: path = pick_icon_id(r, t, want)
    except AssertionError as e: print('  NAV FAILED', e); ok = False
    evs = events(r) if watch else []
    print('  hits:', t.show())
    print('  events:', fmt_events(evs))
    print('  after:', state(r), '2463', r.a5(2463,1).hex(), '2438', r.a5(2438,1).hex(), 'type8', type8(r)['recs'][:3], 'gold', r.a5(1188,4).hex(), 'pc', hex(r.pc()))
    r.snap(OUT + f'tr_{label}_{want}.snap') if label else None
    r.close()
    return t.tot, evs
if __name__ == '__main__':
    trial_ruck(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'space', 'x')
