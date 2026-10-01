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
    return '%s room %d pos %s z %s health %d xp %d cnt %d ruck %s' % (tag, r.w(ROOM), pos(r), tuple(r.mem(0x3833c, 2)), r.w(HEALTH), r.l(A5 + 1192), t8['count'], t8['recs'][:t8['count']])

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
        elif tok[0] == 'J':
            bits = 0
            for c in tok[1:]: bits |= K[c]
            aim(r, bits, 35000); joy(r, FIRE | bits); n = 0; zmax = 0
            while n < 800000:
                r.cmd('s 20000'); n += 20000; zmax = max(zmax, r.mem(0x3833c, 2)[0])
                if n == 120000: joy(r, bits)
            joy(r, 0); r.cmd('s 100000'); res = 'jump %s zmax %d' % (tok[1:], zmax)
        elif tok == 'H':
            res = 'H'
        else:
            raise SystemExit('bad token ' + tok)
        print('%02d %-8s %s | health %d->%d | %s' % (i, tok, res, h0, r.w(HEALTH), line(r)), flush=True)
        path = od + '%02d_%s.snap' % (i, tok); r.snap(path); r.close(); r = Repl(path); t = Tally(r)
    r.close()

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], sys.argv[3:])
