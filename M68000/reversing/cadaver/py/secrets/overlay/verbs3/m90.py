"""m90.py: verb 90 POISON ($010f7c) measured by callcap (operand layout, writes) and live through the consumer $00fdbc (level 1's own contact blocks of #808 and #746,
event 9 injected): per-interval health loss, how the poison ends, re-poison, immunity byte 2347, death.  `<label> ok|BAD` lines + per-verb tallies.
Run: cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/m90.py   (about 3 minutes)"""
from lib2 import *
import lib2, re

T_DEC, T_EXP, HPFN, DEATH = 0x903e, 0x904a, 0x10c8c, 0x10cd4
# level 1 overlay: timer 0 handler $4d04e (poison end), timer 1 handler $4d064 (poison tick)
H0, H1 = 0x4d04e, 0x4d064

def state(r):
    return dict(hp=r.w(A5 + 1174), p=r.b(A5 + 2434), t0=r.b(A5 + 2308), t1=r.b(A5 + 2309), s0=r.b(A5 + 2360), s1=r.b(A5 + 2361), n=r.b(A5 + 2307), lst=r.mem(A5 + 2412, 4).hex())

def run():
    # ============ callcap
    for snap, tag in ((SNAP0, 'L0'), (SNAP1, 'L1')):
        h = H(snap); r = h.r
        q0 = r.l(A5 + 304); n0 = r.w(A5 + 1154); st0 = state(r)
        d = h.call(90, [10, 40, 10])
        e = after(h, d, q0, 8)
        chk('verb 90 %s [0a 28 0a]: consumes 3 bytes; 2434(A5) %d -> %d (strength), timer 0 2308(A5) -> %d and reload 2360(A5) -> %d (duration $28), timer 1 2309(A5) -> %d and reload 2361(A5) -> %d (interval $0a), armed count 2307(A5) %d -> %d, list 2412(A5) = %s' % (
            tag, st0['p'], afterb(h, d, A5 + 2434), afterb(h, d, A5 + 2308), afterb(h, d, A5 + 2360), afterb(h, d, A5 + 2309), afterb(h, d, A5 + 2361), st0['n'], afterb(h, d, A5 + 2307), after(h, d, A5 + 2412, 4).hex()),
            d['ret'] and d['da1'] == 3 and afterb(h, d, A5 + 2434) == 10 and afterb(h, d, A5 + 2308) == 40 and afterb(h, d, A5 + 2360) == 40 and afterb(h, d, A5 + 2309) == 10 and afterb(h, d, A5 + 2361) == 10
            and afterb(h, d, A5 + 2307) == st0['n'] + 2 and after(h, d, A5 + 2412, 2) == bytes([0, 1]))
        chk('verb 90 %s: also queues a ring entry %s = [opcode $0008][long $%08x = 2142(A5) = $1e, the sound id][word]; 304(A5) += 8, 1154(A5) %d -> %d; 2142(A5) -> $%x' % (
            tag, e.hex(), int.from_bytes(e[2:6], 'big'), n0, afterw(h, d, A5 + 1154), afterw(h, d, A5 + 2142)),
            e[:2] == bytes([0, 8]) and int.from_bytes(e[2:6], 'big') == 0x1e and afterl(h, d, A5 + 304) == q0 + 8 and afterw(h, d, A5 + 1154) == n0 + 1 and afterw(h, d, A5 + 2142) == 0x1e)
        # only these addresses change (A5 fields + the ring entry)
        st, oth = h.structural(d['delta'])
        names = sorted(set(w.split('+')[0] if False else w for w, o, n in st))
        chk('verb 90 %s: the whole memory delta is %d bytes (2434, 2307, 2308/2309, 2360/2361, 2412/2413, 2142, 304/1154 and the ring entry); health 1174(A5) untouched' % (tag, len(d['delta'])), 1174 + A5 not in d['delta'] and 1175 + A5 not in d['delta'] and len(d['delta']) < 40, sorted(hex(a) for a in d['delta'])[:50])
        # timers already armed: values replaced, count unchanged, list unchanged
        h.poke(A5 + 2307, [2]); h.poke(A5 + 2308, [5, 6]); h.poke(A5 + 2360, [5]); h.poke(A5 + 2412, [0, 1, 0xff])
        d = h.call(90, [3, 7, 2])
        chk('verb 90 %s with timers 0 and 1 already armed (5, 6): replaced by 7 and 2, reloads 7 and 2, armed count stays 2, strength 3' % tag,
            d['ret'] and afterb(h, d, A5 + 2308) == 7 and afterb(h, d, A5 + 2309) == 2 and afterb(h, d, A5 + 2360) == 7 and afterb(h, d, A5 + 2361) == 2 and afterb(h, d, A5 + 2307) == 2 and afterb(h, d, A5 + 2434) == 3)
        h.close()

    # ============ live (level 1)
    def live_run(label, obj, inject_steps_after, extra=None, hp=None, max_chunks=260, pre=None, reinject_after_hit=None, obj2=None):
        h = H(SNAP1); r = h.r
        if hp is not None: h.poke(A5 + 1174, [hp >> 8, hp & 255])
        if pre: pre(h)
        base = state(r)
        inject5(h, obj, 0, 9)
        series = []; tot = dict.fromkeys((T_DEC, T_EXP, H0, H1, HPFN, DEATH, 0xfe24), 0)
        tick = 0; hit_tick = []; first = True; inj2 = False
        hh = r.hits(60000, *tot)                      # let the consumer run the block (the frame loop drains the ring about every 25,000 steps)
        for k in hh: tot[k] += hh[k]
        s_after = state(r)
        steps = 60000
        prev_hits = tot[HPFN]
        for i in range(max_chunks):
            hh = r.hits(100000, *tot); steps += 100000
            for k in hh: tot[k] += hh[k]
            s = state(r); series.append((steps, s['hp'], s['p'], s['t0'], s['t1'], s['n'], tot[HPFN], tot[H0], tot[H1]))
            if reinject_after_hit is not None and not inj2 and tot[HPFN] >= 1:
                reinject_after_hit -= 1
                if reinject_after_hit < 0:
                    inject5(h, obj2 or obj, 0, 9); inj2 = True; series.append(('reinject', s['t0'], s['t1']))
            if s['n'] == 0 and (reinject_after_hit is None or inj2) and tot[H0] >= 1: break
            if tot[DEATH]: break
        end = state(r); h.close()
        return dict(base=base, s_after=s_after, end=end, tot=tot, series=series, steps=steps)

    res = live_run('#808', 808, 3000)
    b, a, e, t = res['base'], res['s_after'], res['end'], res['tot']
    chk('live[v90]  L1 #808 event 9 injected (its own block `90 0a 28 0a`): consumer matched %d, 60,000 steps later: 2434 %d -> %d, timers 0/1 = %d/%d, reloads %d/%d, armed count %d -> %d, list %s' % (t[0xfe24], b['p'], a['p'], a['t0'], a['t1'], a['s0'], a['s1'], b['n'], a['n'], a['lst']),
        a['p'] == 10 and a['t0'] == 40 and a['t1'] == 10 and a['s0'] == 40 and a['s1'] == 10 and a['n'] == b['n'] + 2 and a['lst'][:4] == '0001')
    chk('live[v90]  ... health %d -> %d after %d steps: the poison ended (2434 = %d, timer-0 handler $%x ran %d times), the tick handler $%x ran %d times, the health routine $%x ran %d times: loss %d = 3 x strength 10' % (
        b['hp'], e['hp'], res['steps'], e['p'], H0, t[H0], H1, t[H1], HPFN, t[HPFN], b['hp'] - e['hp']),
        b['hp'] - e['hp'] == 30 and t[HPFN] == 3 and t[H0] == 1 and e['p'] == 0)
    chk('live[v90]  ... both timers end together: tick handler $%x ran %d times (ticks 10, 20, 30 hurt; at tick 40 timer 0 is first in the list, clears 2434, then the tick handler finds 2434 = 0, skips its `move.b #$ff,1(A0)` re-arm and the timer is removed), armed count %d, list %s' % (H1, t[H1], e['n'], e['lst']),
        t[H1] == 4 and e['n'] == 0 and e['lst'] == 'ffffffff', e)
    # the health series: the drops
    drops = [(s[0], s[1]) for s in res['series'] if s[0] != 'reinject']
    prev = b['hp']; ev = []
    for s in res['series']:
        if s[0] == 'reinject': continue
        if s[1] != prev: ev.append((s[0], prev, s[1])); prev = s[1]
    print('  health changes (steps, from, to):', ev)
    chk('live[v90]  ... health changes in the 100,000-step series: %s (three drops of 10, about 4,250,000 steps = 10 timer ticks of 17 frame-service calls apart)' % [(x[1] - x[2]) for x in ev], [x[1] - x[2] for x in ev] == [10, 10, 10])
    if len(ev) == 3:
        gaps = [ev[1][0] - ev[0][0], ev[2][0] - ev[1][0]]
        chk('live[v90]  ... gaps between the drops %s steps (interval 10 ticks); first drop at %d steps after the injection' % (gaps, ev[0][0]), all(abs(g - gaps[0]) <= 200000 for g in gaps) and abs(gaps[0] - 10 * 17 * 25000) < 1200000)
    # control
    h = H(SNAP1); r = h.r; hp0 = r.w(A5 + 1174); r.hits(2000000, 0xfe24); chk('live[v90]  control without injection: health %d -> %d over 2,000,000 steps, 2434(A5) = %d' % (hp0, r.w(A5 + 1174), r.b(A5 + 2434)), r.w(A5 + 1174) == hp0 and r.b(A5 + 2434) == 0); h.close()

    # second block: #746 (the instance level 1's rooms 10, 18, 28 and 39 create at their entry) behaves the same
    res = live_run('#746', 746, 3000)
    b, a, e, t = res['base'], res['s_after'], res['end'], res['tot']
    chk('live[v90]  L1 #746 event 9 injected: 2434 -> %d, timers %d/%d, health %d -> %d, health routine ran %d' % (a['p'], a['t0'], a['t1'], b['hp'], e['hp'], t[HPFN]), a['p'] == 10 and a['t0'] == 40 and a['t1'] == 10 and b['hp'] - e['hp'] == 30 and t[HPFN] == 3)

    # re-poison during the poison by a second object: timers re-armed (duration restarts), count unchanged
    res = live_run('#808 then #746', 808, 3000, reinject_after_hit=8, max_chunks=400, obj2=746)
    b, e, t = res['base'], res['end'], res['tot']
    chk('live[v90]  #808 injected, and #746 about 2 timer ticks (900,000 steps) after the first health loss: total health loss %d, health routine ran %d (first drop, then 3 more after the restart: 4 x 10), end armed count %d, steps %d' % (b['hp'] - e['hp'], t[HPFN], e['n'], res['steps']),
        b['hp'] - e['hp'] == 40 and t[HPFN] == 4 and e['p'] == 0 and e['n'] == 0)
    # the same object twice: its event-9 block has no keep bit (event byte $09, not $89), so the consumer marks it spent after the first run
    res = live_run('#808 twice', 808, 3000, reinject_after_hit=8, max_chunks=400)
    b, e, t = res['base'], res['end'], res['tot']
    chk('live[v90]  #808 injected twice (second time 9 chunks after the first loss): the block is one-shot (event byte $09 without bit 7 -> $ff after its first run): total loss %d, health routine ran %d, consumer matches %d' % (b['hp'] - e['hp'], t[HPFN], t[0xfe24]),
        b['hp'] - e['hp'] == 30 and t[HPFN] == 3)

    # immunity byte 2347 stops the loss (the health routine returns at once)
    def imm(h): h.poke(A5 + 2347, [1])
    res = live_run('#808 with 2347 = 1 (poked)', 808, 3000, pre=imm)
    b, e, t = res['base'], res['end'], res['tot']
    chk('live[v90]  with 2347(A5) = 1 (poked, the byte `$010c8c` tests first): health %d -> %d, health routine entered %d times, poison still ends (2434 = %d)' % (b['hp'], e['hp'], t[HPFN], e['p']), b['hp'] == e['hp'] and t[HPFN] == 3 and e['p'] == 0)

    # death: health 25 -> at the third tick health reaches -5 -> $010cd4
    res = live_run('#808 with health 25', 808, 3000, hp=25)
    b, e, t = res['base'], res['end'], res['tot']
    chk('live[v90]  health poked to 25: after the third tick (25 - 30 < 0) the death path $%x was entered %d times (health routine %d times), health byte afterwards %d' % (DEATH, t[DEATH], t[HPFN], e['hp']), t[DEATH] >= 1 and t[HPFN] == 3)
    # health exactly 10: the second tick brings it to 0 = death too (beq)
    res = live_run('#808 with health 20', 808, 3000, hp=20)
    b, e, t = res['base'], res['end'], res['tot']
    chk('live[v90]  health poked to 20: the second tick brings it to exactly 0, death path entered %d times (the routine treats 0 as dead: bmi and beq both go to $010cd4), health routine %d times' % (t[DEATH], t[HPFN]), t[DEATH] >= 1 and t[HPFN] == 2)

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
    print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
