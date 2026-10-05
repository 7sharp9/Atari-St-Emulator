"""gates.py : player-versus-player and two-player gates over the logs of run_pvp.sh, the target and token runs and the stage runs (out/). Each gate prints PASS/FAIL matched/total and what was compared.
Gates: pvp_damage pvp_award pvp_immunity pvp_special pvp_depth pvp_kill p2_inputs p2_award target token entry health"""
import sys, os, re, collections, subprocess
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here); sys.path.insert(0, os.path.join(here, '../char'))
import pvlib as V
import charlib as C
OUT = C.OUT
res = []
def gate(name, ok, tot, note=''):
    res.append((name, ok, tot)); print('%s  %-50s %d/%d  %s' % ('PASS' if ok == tot and tot else 'FAIL', name, ok, tot, note))
def bcd(x): return int('%x' % x)
def load(n): return V.load(os.path.join(OUT, n + '.txt'))
def hits(rows, att, vic):
    out = []
    for i in range(1, len(rows)):
        a, r = rows[i - 1], rows[i]
        if r[vic]['hp'] < a[vic]['hp']: out.append((r['rel'], a[vic]['hp'] - r[vic]['hp'], r[vic]['b22'], r[vic]['b63'], bcd(r[att]['sc']) - bcd(a[att]['sc']), r))
    return out
def g_pvp():
    rows = load('pv_c1_clr'); h = hits(rows, 'p1', 'p2')
    ok = sum(1 for rel, d, id22, t63, ds, r in h if d == 1)
    gate('PvP: every non-hard attack takes exactly 1 hp', ok, len(h), 'P1 Cody chain on P2 Haggar, ids %s' % sorted(set(x[2] for x in h)))
    awards = [(id22, ds, C.hit_award(1, C.attack_box(1, id22)['off'])[1]) for rel, d, id22, t63, ds, r in h]
    gate('PvP: the attacker is awarded the hit award of the box row', sum(1 for i, ds, e in awards if ds == e), len(awards), str(sorted(set(awards))))
    rows = load('pv_p2c1'); h = hits(rows, 'p2', 'p1')
    gate('PvP: P2 hitting P1: 1 hp, +100 to P2 (bit 7 of the award)', sum(1 for rel, d, id22, t63, ds, r in h if d == 1 and ds == 100 and r['p1']['sc'] == 0), len(h), 'P1 score stays 0')
def g_immunity():
    rows = load('pv_c1'); h = hits(rows, 'p1', 'p2')
    gaps = [h[i][0] - h[i - 1][0] for i in range(1, len(h))]
    t = [r['p2']['b148'] for r in rows if r['rel'] in (h[0][0], h[0][0] + 1, h[0][0] + 50, h[0][0] + 99)]
    gate('PvP: +148 = 100 after a hit, counts down 1 per frame, next hit 100 frames later', int(t == [100, 99, 50, 1] and all(g == 100 for g in gaps)), 1, 'b148 %s, hit gaps %s' % (t, gaps))
def g_special():
    rows = load('pv_jump1')
    sp = [r for r in rows if r['p1']['sub'] == 0x10]
    ok = int(len(sp) > 20 and all(r['p2']['hp'] == sp[0]['p2']['hp'] for r in sp) and sp[0]['p2']['hp'] == 143)
    gate('PvP: the special spin (+139) does not hit the partner', ok, 1, '%d frames in sub $10 with 1 prior hit (hp 143), hp unchanged' % len(sp))
def g_depth():
    ok = tot = 0; table = []
    for name in ['pv_dy_%d' % d for d in (-16, -14, -13, -12, -11, -9, -5, 0, 5, 8, 9, 10, 11, 13, 16)] + ['pv_dyb_%d' % d for d in (-11, -10, -9, 11, 12, 13, 14)]:
        rows = load(name); r = rows[13]; diff = r['p2']['gy'] - r['p1']['gy']
        hit = any(rows[i]['p2']['hp'] < rows[i - 1]['p2']['hp'] for i in range(1, len(rows)))
        exp = -9 <= diff <= 12
        tot += 1; ok += (hit == exp); table.append((diff, hit))
    gate('PvP: hit iff victim ground line - attacker ground line in [-9, +12]', ok, tot, 'window words %s' % load('pv_c1')[0]['g']['w1'])
def g_kill():
    rows = load('pv_kill')
    t = V.changes(rows, 'p2', ['st', 'hp'])
    first = [c for c in t if c[2] == 65535][0][0]
    st4 = [c for c in t if c[1] == 4][0][0]
    st0 = [c for c in V.changes(rows, 'p2', ['st']) if c[0] > st4 and c[1] == 0][0][0]
    sc = V.changes(rows, 'p1', ['sc'])
    gate('PvP: hp 0 and one jab: hp -1, fatal knockdown, state 4 after 92 frames, respawn 60 frames later', int(st4 - first == 93 and st0 - st4 == 60 and [bcd(x[1]) for x in sc] == [0, 100]), 1,
         'hit rel %d, state 4 at %d, state 0 at %d, P1 score %s' % (first, st4, st0, [bcd(x[1]) for x in sc]))
def g_inputs():
    rows = load('pv_keys'); seen = {}
    for r in rows:
        g = r['g']
        if g['i94'] != 0: seen.setdefault(g['i94'], set()).add(g['i130b'])
    ok = sum(1 for k in (1, 2, 4, 8, 0x10, 0x20, 0x40) if seen.get(k) == {k})
    p1 = {r['g']['i92'] for r in rows if r['g']['i92']}
    gate('P2 inputs: 94(A5) bits 0..6 -> P2 +130 the same frame', ok, 7, 'P1 control: 92(A5) values %s' % sorted(p1))
def g_p2award():
    rows = load('pv_kill_p2')
    s2 = [bcd(c[1]) for c in V.changes(rows, 'p2', ['sc'])]; s1 = [bcd(c[1]) for c in V.changes(rows, 'p1', ['sc'])]
    kill = [s2[i] - s2[i - 1] for i in range(1, len(s2))]
    gate('P2 kills Bred: +1000 to P2, nothing to P1', int(1000 in kill and s1 == [0]), 1, 'P2 score steps %s, P1 %s' % (kill, s1))
def g_target():
    ok = bad = 0
    for n in ('tgt_a.t', 'tgt_b.t'):
        out = subprocess.run([sys.executable, os.path.join(here, 'target_check.py'), os.path.join(OUT, n)], capture_output=True, text=True).stdout
        m = re.search(r'match (\d+), mismatch (\d+)', out); ok += int(m.group(1)); bad += int(m.group(2))
    gate('2P target rule (nearest by |dx|, P1 only if strictly nearer)', ok, ok + bad, 'two runs, kinds 0 to 2 acquire events')
def g_token():
    ok = tot = 0
    for n in ('bpe1', 'bpe3', 'bpf1', 'bpf2'):
        out = subprocess.run([sys.executable, os.path.join(here, 'token_decide.py'), os.path.join(OUT, n + '.txt')], capture_output=True, text=True).stdout
        m = re.search(r'calls paired (\d+) rule matches (\d+)', out); tot += int(m.group(1)); ok += int(m.group(2))
    gate('token request $27b5a: granted iff tokens < cap (tables $27b88 / $27bc8 by 127(A5) == 3)', ok, tot, 'breakpoints on entry and exits, four runs')
def g_entry():
    out = subprocess.run([sys.executable, os.path.join(here, 'p2_entries.py'), os.path.join(OUT, 'p1boss.log'), os.path.join(OUT, 'p2boss.log')], capture_output=True, text=True).stdout
    m = [l for l in out.splitlines() if 'flag 1' in l]
    ok = int(len(m) == 1 and 'one-player log 0, two-player log 1' in m[0])
    flag0 = [l for l in out.splitlines() if 'flag 0' in l]
    ok2 = sum(1 for l in flag0 if 'one-player log 1, two-player log 1' in l)
    gate('script byte 15 (two-player flag): $706c4 spawns only with two players', ok + ok2, 1 + len(flag0), 'the four unflagged entries of the segment spawn in both')
def g_health():
    def H(path):
        d = {}
        for ln in open(path):
            if ln[0] != 'H': continue
            t = dict(x.split('=') for x in ln.split()[2:] if '=' in x)
            d[(t['pool'], int(t['k']), int(t['ch']), int(t['lvl']))] = (t['hp'], t['p92'], t['21610'])
        return d
    a, b = H(os.path.join(OUT, 'tgt_1p.t')), H(os.path.join(OUT, 'tgt_a.t'))
    same = [k for k in a if k in b and k[0] == '2']
    ok = sum(1 for k in same if a[k][:2] == b[k][:2])
    gate('pool-2 fighters of stage 0: same health and damage table with two players', ok, len(same), 'kinds 0 1 2 4 5, %d (kind, character, level) combinations in both runs' % len(same))
    d1 = [v for k, v in a.items() if k[0] == '4']; d2 = [v for k, v in b.items() if k[0] == '4']
    gate('pool-4 record 7 (boss) health 300 -> 450 and damage table +$c0 with two players', int(d1 and d2 and d1[0][0] == '012c' and d2[0][0] == '01c2' and d1[0][2] == '01' and d2[0][2] == '03'), 1, '1P %s, 2P %s (p92 = table + $60 + level)' % (d1, d2))
if __name__ == '__main__':
    for g in (g_pvp, g_immunity, g_special, g_depth, g_kill, g_inputs, g_p2award, g_target, g_token, g_entry, g_health):
        try: g()
        except Exception as e: gate(g.__name__, 0, 1, 'error %r' % (e,))
    print('%d/%d gates PASS' % (sum(1 for n, o, t in res if o == t and t), len(res)))
