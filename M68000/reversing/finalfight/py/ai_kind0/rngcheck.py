# gate: $3c26 is a 16-bit LFSR on the word at $ff1150: S' = (S >> 1) | ((bit1 ^ bit9) << 15), returned D0 = low byte of S'
# input: hitc.lua log of "3c56" with S=%04x (state AFTER the step) and D0; checks consecutive calls S_{n+1} == step(S_n) and D0 == S & 0xff
import re, sys
def step(s):
    b = ((s >> 1) ^ (s >> 9)) & 1
    return (s >> 1) | (b << 15)
S = []; D = []
for l in open(sys.argv[1]):
    m = re.search(r'D0=([0-9a-f]+) .* S=([0-9a-f]+)', l)
    if m: D.append(int(m.group(1), 16)); S.append(int(m.group(2), 16))
ok = sum(1 for a, b in zip(S, S[1:]) if step(a) == b)
okd = sum(1 for d, s in zip(D, S) if d == (s & 0xff))
print('calls', len(S), 'step(S_n)==S_n+1:', ok, 'of', len(S) - 1, ' D0==low byte of S:', okd, 'of', len(S))
