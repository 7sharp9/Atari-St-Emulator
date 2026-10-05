"""Hit-box damage: table prediction vs live. Prediction: byte [hit box type] of the table chosen by the dip ($80054 & $c, pointer table $fcba, `$fc34`) times 4.
Live: H lines of a drive5.lua log whose pc is $fc9e (box hit) -> old-new; grouped by hit box type. A D line (dip) is logged at frame 800.
usage: dmg_check.py <log> ..."""
import sys, os, collections
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
for log in sys.argv[1:]:
    dip = None; live = collections.defaultdict(collections.Counter)
    for line in open(log):
        p = line.split()
        if p and p[0] == 'D': dip = int(p[2].split('=')[1], 16)
        if p and p[0] == 'H' and 'pc=00fc9e' in line:
            kv = dict(x.split('=') for x in p if '=' in x)
            live[kv['ctype']][int(kv['old'], 16) - int(kv['new'], 16)] += 1
    idx = ((dip or 0) & 0xc)
    tab = l(0xfcba + idx)
    print(log, "dip54=%s table $%06x" % (hex(dip) if dip is not None else "?", tab))
    for ct, c in sorted(live.items()):
        t = int(ct, 16)
        print(f"   hit box type {t:02x}: table byte {rom[tab+t]} x4 = {rom[tab+t]*4}; live damage counts {dict(c)}")
