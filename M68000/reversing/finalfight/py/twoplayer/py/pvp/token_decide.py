"""token_decide.py <bp log...> : pair each entry of $27b5a (E: rank 168(A5), 127(A5), tokens $ff115a) with the exit that follows it (R1 granted via $27c1e, R0 refused at $27b74 (one-player table) or $27b84
(two-player table)) and compare with the rule: granted iff tokens < cap, cap = word[$27b88 + 2*rank] (127(A5) != 3) or word[$27bc8 + 2*rank] (127(A5) == 3); a grant also adds 1 to $ff115a."""
import sys, os, re, collections
here = os.path.dirname(os.path.abspath(__file__))
def _root():
    d = here
    while d != '/' and not os.path.exists(os.path.join(d, 'scratchpad/finalfight/ff_main.bin')): d = os.path.dirname(d)
    return d
rom = open(os.path.join(_root(), 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def cap(tab, rank): return int.from_bytes(rom[tab + 2 * min(rank, 31):tab + 2 * min(rank, 31) + 2], 'big')
for path in sys.argv[1:]:
    L = [l.split(' ', 2)[2].strip() for l in open(path) if ' B ' in l]
    ok = bad = 0; stats = collections.Counter(); stray = 0
    i = 0
    while i < len(L):
        m = re.match(r'E rank=(\d+) m127=(\d+) tok=(\d+)', L[i])
        if not m:
            if L[i].startswith('R1'): stray += 1
            i += 1; continue
        rank, m127, tok = map(int, m.groups())
        r = L[i + 1] if i + 1 < len(L) else ''
        c = cap(0x27bc8 if m127 == 3 else 0x27b88, rank)
        exp = 1 if tok < c else 0
        got = 1 if r.startswith('R1') else 0 if r.startswith('R0') else None
        table = '2P' if m127 == 3 else '1P'
        if got == exp: ok += 1
        else: bad += 1; print('MISMATCH', L[i], r, 'cap', c)
        stats[(table, rank, tok, c, got)] += 1
        i += 2
    print(path, 'calls paired', ok + bad, 'rule matches', ok, 'mismatches', bad, 'melee-path grants (R1 without an entry)', stray)
    for k in sorted(stats): print('   table %s rank %2d tokens %d cap %d -> %s : %d' % (k[0], k[1], k[2], k[3], 'granted' if k[4] else 'refused', stats[k]))
