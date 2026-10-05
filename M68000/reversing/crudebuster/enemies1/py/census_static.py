"""Static census of the level scripts: counts per (type, variant) for lists A and B, levels 0-2, as markdown.  usage: census_static.py [levels...]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from scripts import A, B
lv = [int(x) for x in sys.argv[1:]] or [0, 1, 2]
for name, T in (("A", A), ("B", B)):
    print("List %s" % name)
    types = sorted({(e["type"], e["var"]) for l in lv for e in T[l]})
    print("| type/var | " + " | ".join("L%d" % l for l in lv) + " |")
    print("|---|" + "---|" * len(lv))
    for t, v in types:
        print("| %d / %d | " % (t, v) + " | ".join(str(sum(1 for e in T[l] if (e["type"], e["var"]) == (t, v))) for l in lv) + " |")
    print("| total | " + " | ".join(str(len(T[l])) for l in lv) + " |")
