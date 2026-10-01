"""play.py <start.snap> <tag> <tokens...>: natural-input driver, reload (snapshot, close, reopen) after every token.
Tokens: U D L R (hold to stall or room change); gR<n> gL<n> gD<n> gU<n> (hold until x lead >= / <= n or y lead >= / <= n, 5,000-step chunks);
w<n> (wait n steps); P (probe the object in front); I<n> (open the panel and pick icon id n, tally printed); SP (Space, rucksack panel of the held item, icon id by next token 'I');
H (health/xp/rucksack line).  Snapshots: <outdir>/<tag>/NN_<token>.snap (default outdir: $CAD_OUT/play).  Paths derive from __file__."""
import sys, os
HD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HD + '/../lib')   # shared lib/ (CAD_OUT = scratch dir for the lib's own output)
from route_lib import *
K = {'U': UP, 'D': DOWN, 'L': LEFT, 'R': RIGHT}
SITES = [0xa136, 0xa184, 0xa494, 0xa43c, 0xa448, 0xa486, 0xa59c, 0xa5c0, 0xa5d2, 0xa1e0, 0xa19e, 0xa682, 0xa6f4, 0xa70e, 0xc42a, 0xc30e, 0xc3d4, 0x1007e, 0xfe24, 0xfe5a, 0x10aaa, 0x10c8c, 0x11256, 0x104e2]

def line(r, tag=''):
    t8 = type8(r)
    return '%s room %d pos %s z %s health %d xp %d var4 %d sel %s cnt %d ruck %s' % (tag, r.w(ROOM), pos(r), tuple(r.mem(0x3833c, 2)), r.w(HEALTH), r.l(A5 + 1192), r.b(A5 + 2286), r.a5(1262, 2).hex(), t8['count'], [x[0] for x in t8['recs'][:t8['count']]])

def gems(r, ids=(164, 186, 187, 189, 190, 290)):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = []
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and r.w(t + 4) in ids: out.append('%d:%s/z%d-%d' % (r.w(t + 4), ','.join(map(str, e[0:4])) if e[0] != 255 else 'del', e[5], e[4]))
    return ' '.join(out)

def dyn(r):
    """live dynamic entries (instance id >= 900, rect not deleted): the room 27 guard creature (class 3) and its fireball (class 128)"""
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = []
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and e[0] != 255 and r.w(t + 4) >= 900: out.append((r.w(t + 4), tuple(e[0:4])))
    return out

def wait_quiet(r, chunk=25000, seen_cap=1500000, cap=4000000):
    """WQ: room 27's event 14 creates a guard creature (object 127) after the hero has stood on the south strip; it later fires a fireball (3x3, z 10..13) south along x 14..16
    (-10 when it meets the hero).  Wait here (hero outside the column) until a guard has been seen and is gone again, then settle 50,000 steps."""
    seen = False; n = 0
    while n < cap:
        r.cmd('s %d' % chunk); n += chunk
        d = dyn(r)
        if d: seen = True
        elif seen: r.cmd('s 50000'); return 'quiet after %d steps' % n
        elif n >= seen_cap: return 'no guard seen in %d steps' % n
    return 'cap %d reached, dyn %s' % (cap, dyn(r))

def select_gem(r, t, want, tmp):
    """SG<id>: select a carried item by id, independent of its recency: Return (grid), n RIGHT pulses, FIRE (icon panel of that grid cell), icon $d (select), sel id `1262(A5)` must be `want`.
    The grid cursor does not start at a fixed cell (diag3.py: from the first throw state n pulses -> list index n-1, from the second one -> index 0), so n = 1, 2, ... is searched from a snapshot
    (the wrong item is merely selected, never thrown); the first n that selects `want` is kept.  Returns (r, t, text)."""
    r.snap(tmp); recs = [x[0] for x in type8(r)['recs'][:type8(r)['count']]]
    for n in range(1, 10):
        tap(r, t, 0x1c)
        for _ in range(n): pulse(r, t, RIGHT)
        t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
        cell = r.a5(2122, 2).hex()
        pick_icon_id(r, t, 0xd); t.run(150000)
        got = r.w(A5 + 1262)
        if got == want: return r, t, 'selected %d with %d RIGHT pulses (grid cell %s) of %s' % (want, n, cell, recs)
        r.close(); r = Repl(tmp); t = Tally(r)
    raise AssertionError(('no pulse count selects', want, recs))

def run(start, tag, tokens, outdir=None):
    od = (outdir or OUT + 'play') + '/' + tag + '/'; os.makedirs(od, exist_ok=True)
    r = Repl(start); t = Tally(r)
    print(line(r, 'start'), flush=True)
    for i, tok in enumerate(tokens):
        h0 = r.w(HEALTH)
        if tok in K:
            room, p = hold(r, K[tok]); res = '%s -> room %d %s' % (tok, room, p)
        elif tok[0] == 'g' and tok[1] in K:
            mv = K[tok[1]]; n = int(tok[2:])
            cond = {'R': lambda p: p[0] >= n, 'L': lambda p: p[0] <= n, 'D': lambda p: p[1] >= n, 'U': lambda p: p[1] <= n}[tok[1]]
            res = '%s -> %s' % (tok, goto(r, mv, cond))
        elif tok[0] == 'w':
            r.cmd('s %d' % int(tok[1:])); res = tok
        elif tok == 'P':
            pr = probe(r); res = 'probe ' + str(pr and (pr[0], pr[1], pr[3], pr[4]))
        elif tok == 'SP':
            ruck_panel(r, t, 'space'); res = 'space panel icons %s sel %s' % (icons(r), r.a5(1262, 2).hex())
        elif tok[0] == 'I':
            t.reset(); n = int(tok[1:], 16)
            # panel may already be open (after SP): open it with fire only if the previous token was not SP
            if tokens[i - 1] != 'SP': open_panel(r, t)
            pth = pick_icon_id(r, t, n); t.run(150000, sites=SITES); res = 'icon %x path %s hits %s' % (n, ''.join(pth), t.show())
        elif tok[0] == 'G':
            # INJECTED: verb 35 (give object <id>) through the real consumer, then 100,000 steps; the only non-natural token
            tmp = od + 'give_tmp.snap'; r.snap(tmp); r.close()
            import h as H_
            H_.TMP = od + 'h'; os.makedirs(H_.TMP, exist_ok=True)
            hh = H_.H(tmp); i = int(tok[1:]); H_.real(hh, [0x23, i >> 8, i & 255, 0x17], steps=200000); hh.r.cmd('s 100000')
            r = hh.r; res = 'give %d (INJECTED verb 35)' % i
        elif tok[0] == 'F':
            # throw: fire held (optionally with a direction bit: FL FR FU FD) for 200,000 steps, release, settle 300,000; prints where gem entries lie
            bits = FIRE | (K[tok[1]] if len(tok) > 1 else 0)
            joy(r, bits); r.cmd('s 200000'); joy(r, 0); r.cmd('s 300000')
            res = 'throw ' + gems(r)
        elif tok == 'WQ':
            res = wait_quiet(r)
        elif tok[:2] == 'SG':
            t.reset(); r, t, res = select_gem(r, t, int(tok[2:]), od + 'sg_tmp.snap')
        elif tok == 'H':
            res = 'H'
        else:
            raise SystemExit('bad token ' + tok)
        print('%02d %-8s %s | health %d->%d | %s' % (i, tok, res, h0, r.w(HEALTH), line(r)), flush=True)
        path = od + '%02d_%s.snap' % (i, tok); r.snap(path); r.close(); r = Repl(path); t = Tally(r)
    r.close()

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], sys.argv[3:])
