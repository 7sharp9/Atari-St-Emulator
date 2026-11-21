"""Census of the text printer $bcba (indirect: jmp (60(A6)) = $bdf0, the 8x8 colour string printer): from a snapshot,
stop at each of the next N calls with `bp bcba`, read A0 (screen address), A1 (string), the colour byte $c57c and the
return address, and decode the string from RAM at that moment. Prints one row per call, then a tally per call site.
usage: text_census.py [snap=g_game1] [N=40] [budget per bp=400000] [pre-steps=0] [pokes...]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon

def census(snap, n=40, budget=400000, pre=0, pokes=()):
    cmds = list(pokes) + (['s %d' % pre] if pre else [])
    for i in range(n):
        cmds += ['bp bcba %d' % budget, 'r', 'm c57c 1', 'bt 1']
    o = fe_repl.run(snap, cmds)
    ram = None
    rows = []
    # each bp stop prints a register dump; split on 'CPU Registers' blocks that are followed by PC: 0000bcba
    blocks = re.split(r'-+\nCPU Registers\n', o)
    for b in blocks:
        m = re.search(r'PC: 0000bcba', b)
        if not m:
            continue
        g = lambda k: int(re.search(k + r':([0-9a-f]{8})', b).group(1), 16)
        ra = re.search(r'return address \(A7\) = \$([0-9a-f]{8})', b)
        col = re.search(r'\n([0-9a-f]{2}) \n', b)
        rows.append(dict(a0=g('A0'), a1=g('A1'), a6=g('A6'), ret=int(ra.group(1), 16) if ra else None))
    return rows, o

if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else sgcommon.SNAP_GAME1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 400000
    pre = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    pokes = sys.argv[5:]
    rows, o = census(snap, n, budget, pre, pokes)
    ram = sgcommon.load_ram(snap)
    for r in rows:
        print('a0=%06x a1=%06x ret=%s' % (r['a0'], r['a1'], '%06x' % r['ret'] if r['ret'] else '?'))
