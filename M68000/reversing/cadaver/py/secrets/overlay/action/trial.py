from drv import *
def trial(snap, want, label='', pre=None):
    r = Repl(snap)
    if pre: pre(r)
    t = Tally(r)
    before = state(r); t8 = type8(r)
    watch_queue(r)
    open_panel(r, t)
    ic = icons(r); 
    pick_icon_id(r, t, idx)
    evs = events(r)
    after = state(r)
    print(f'--- {label} icon {want} of {ic}')
    print('  hits:', t.show())
    print('  events:', fmt_events(evs))
    print('  state:', after, '| gold', r.a5(1188,4).hex(), 'xp', r.a5(1192,4).hex(), '| type8', type8(r)['count'], type8(r)['recs'][:3], '| kwd', r.a5(2463,1).hex())
    r.close()
    return t.tot, evs
if __name__ == '__main__':
    snap = sys.argv[1]
    for idx in [int(x) for x in sys.argv[2:]]:
        trial(snap, idx)
