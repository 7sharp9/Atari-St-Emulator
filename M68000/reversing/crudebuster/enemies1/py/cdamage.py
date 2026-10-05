"""Damage per pool C hit object type and difficulty: table[C type] * 4, pointer table $fcba (order Normal, Easy, Hard, Hardest = ($80054 & $c) / 4 for the default DIP settings).
usage: cdamage.py [c types...]"""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
R = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
tabs = [struct.unpack(">I", R[0xfcba + 4*i:0xfcbe + 4*i])[0] for i in range(4)]
for c in ([int(x) for x in sys.argv[1:]] or range(44)):
    print("C%-2d  Normal %2d  Easy %2d  Hard %2d  Hardest %2d" % ((c,) + tuple(R[a + c] * 4 for a in tabs)))
