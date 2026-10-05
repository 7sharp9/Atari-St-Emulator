"""token_check.py <log> : the attack-token counter $ff115a against the cap tables ROM $27b88 (one player) and $27bc8 (127(A5) == 3), indexed by the rank word 168(A5) ($27b5a).
Per frame the log has 'G f tok= rank= m127= m21610= alive012='. Reports, per (cap-table, rank): the maximum token count seen and the cap; a token can be granted only while tok < cap, so max <= cap."""
import sys, collections, os
here = os.path.dirname(os.path.abspath(__file__))
def _root():
    d = here
    while d != '/' and not os.path.exists(os.path.join(d, 'scratchpad/finalfight/ff_main.bin')): d = os.path.dirname(d)
    return d
rom = open(os.path.join(_root(), 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def tab(a): return [int.from_bytes(rom[a + 2 * i:a + 2 * i + 2], 'big') for i in range(32)]
T1, T2 = tab(0x27b88), tab(0x27bc8)
mx = collections.defaultdict(int); n = collections.Counter()
for ln in open(sys.argv[1]):
    if ln[0] != 'G': continue
    t = dict(x.split('=') for x in ln.split()[2:])
    tok, rank, m127 = int(t['tok'], 16), int(t['rank'], 16), int(t['m127'], 16)
    k = ('2P' if m127 == 3 else '1P', rank)
    mx[k] = max(mx[k], tok); n[k] += 1
print('table 1P $27b88:', T1); print('table 2P $27bc8:', T2)
bad = 0
for k in sorted(mx, key=lambda k: (k[0], k[1])):
    cap = (T2 if k[0] == '2P' else T1)[min(k[1], 31)]
    flag = '' if mx[k] <= cap else ' OVER'
    if flag: bad += 1
    print('%s rank %2d frames %5d max tokens %d cap %d%s' % (k[0], k[1], n[k], mx[k], cap, flag))
print('ranks with max > cap:', bad)
