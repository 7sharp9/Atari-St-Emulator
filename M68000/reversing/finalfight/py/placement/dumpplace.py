from placetab import *
import sys
def fmt(e):
    return '%06x trig=%04x x=%04x y=%04x sp=%2d(%s) kind=%02x +20=%02x +21=%02x +54=%02x +98=%02x lvl=%02x p2=%02x'%(e['addr'],e['trig'],e['x'],e['y'],e['sp'],NAMES.get(e['sp'],'?'),e['kind'],e['c20'],e['c21'],e['f54'],e['f98'],e['lvl'],e['p2'])
stages=[int(x) for x in sys.argv[1:]] or range(6)
A0=areas(0x636e); A1=areas(0x6346)
for s in stages:
    for a,addr in enumerate(A0[s]):
        print('== stage',s,'area',a,'INIT list at %x'%addr)
        for e in initlist(addr): print('  ',fmt(e))
    for a,addr in enumerate(A1[s]):
        segs,end=trigmodes(addr)
        print('== stage',s,'area',a,'TRIG list at %x end %x endword %04x'%(addr,end,w(end)))
        for mode,es in segs:
            print('  mode',mode)
            for e in es: print('    ',fmt(e))
