"""Summarise a lords/loyalty sampling REPL log: per chunk, $57fd0, lord 0/1 side and loyalty_pressure, hit counts.
Usage: python3 lpsum.py <out>"""
import re, sys
t = open(sys.argv[1]).read().splitlines()
hits, lords, season, n = {}, None, None, 0
tot = {}
def emit():
    print(n, 's57fd0=%s' % season, lords, {k: v for k, v in hits.items() if v})
for l in t:
    s = l.strip()
    m = re.match(r'\$(\w+)\s+(\d+)', s)
    if m:
        hits[m.group(1)] = int(m.group(2)); tot[m.group(1)] = tot.get(m.group(1), 0) + int(m.group(2))
    elif re.fullmatch(r'([0-9a-f]{2} ){63}[0-9a-f]{2}', s):
        b = bytes.fromhex(s.replace(' ', ''))
        lords = [(b[o], int.from_bytes(b[o + 14:o + 16], 'big', signed=True), int.from_bytes(b[o+6:o+8],'big'), int.from_bytes(b[o+8:o+10],'big')) for o in (0, 32)]
    elif re.fullmatch(r'[0-9a-f]{2} [0-9a-f]{2}', s):
        season = int(s.replace(' ', ''), 16); emit(); n += 1; hits = {}
print('total', tot)
