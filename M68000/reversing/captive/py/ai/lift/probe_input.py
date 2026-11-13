"""Which input reaches which move/lift handler: probe_input.py <snap> [input ...]
input = k<hex> (keypad make, 60,000 steps, break, 300,000 steps) or c<x>:<y> (pointer pinned top left, moved by x, y,
left click). Each input runs from the same restored state; prints the hit counts of the handler entries."""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'ai')); from cap import *  # noqa

ADDRS = {0x9016: 'mv9016', 0x901c: 'mv901c', 0x9022: 'mv9022', 0x9028: 'mv9028', 0x902e: 'h902e', 0x906a: 'h906a',
         0x908c: 'h908c', 0x90b0: 'h90b0', 0x90d0: '90d0', 0x90e2: '90e2', 0x9768: '9768', 0x977c: '977c'}

def run(s, steps, tot):
    r = s('hits', steps=steps, addrs=list(ADDRS))
    for h in r['hits']:
        tot[int(h['addr'].lstrip('$'), 16)] += h['count']

def drive(s, inp, tot):
    if inp[0] == 'k':
        k = int(inp[1:], 16)
        s('kbd', bytes=[k]); run(s, 60000, tot); s('kbd', bytes=[k | 0x80]); run(s, 300000, tot)
    else:
        x, y = (int(v) for v in inp[1:].split(':'))
        for _ in range(3):
            s('mouse', action='move', dx=-127, dy=-127); run(s, 30000, tot)
        while x or y:
            dx, dy = min(x, 120), min(y, 120); s('mouse', action='move', dx=dx, dy=dy); run(s, 30000, tot); x -= dx; y -= dy
        s('mouse', action='down', button='l'); run(s, 60000, tot); s('mouse', action='up', button='l'); run(s, 300000, tot)

if __name__ == '__main__':
    s = srv(sys.argv[1]); f = s('fork')['id']
    for inp in sys.argv[2:]:
        s('restore', id=f); tot = dict.fromkeys(ADDRS, 0)
        drive(s, inp, tot)
        print(inp, 'pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30), {ADDRS[a]: n for a, n in tot.items() if n})
    s.close()
