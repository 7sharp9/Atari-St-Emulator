"""a3: second_list_alias.py -- settle 'does any object block use the second list (+$20)?'.  verb_decode.collect() tries, for EVERY type-6 template, the
list at +$10 (count byte 11) and the list at +$20 (count byte 31).  Templates are packed back to back and a header-only template is 16 bytes, so for such
a template +$20 is the next template's +$10 and byte 31 is that template's byte 15.  This script walks the same two lists with the same acceptance test
as collect() but keeps the ADDRESS of every block, then reports (a) the entries labelled +$20, (b) for each, whether the same block address is also
walked as some other object's +$10 list.  Usage (from M68000/): .venv/bin/python reversing/cadaver/py/secrets/overlay/events/second_list_alias.py
Expected: every +$20 entry aliases the +$10 list of the following template (level 0: object 69 -> 70, level 1: object 3 -> 4)."""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
import h as H

class S(H.H):
    def __init__(self, snap):
        self.snap = snap
        s = open(snap, 'rb').read(); off = 5 + 19 * 4 + 2
        self.ram = s[off + 4:off + 4 + 0x100000]
        self.desc = int.from_bytes(self.ram[H.A5 + 96:H.A5 + 100], 'big')
        self._load_static()

def walk(h):
    ram = h.ram
    entries = []   # (oid, start, block_addr, event)
    for oid in range(1000):
        a = h.obj(oid)
        if a is None: continue
        for cntoff, start in ((11, 0x10), (31, 0x20)):
            cnt = ram[a + cntoff]
            if not 0 < cnt < 12: continue
            p = a + start; ok = True; bl = []
            for _ in range(cnt):
                ln = ram[p]
                if ln < 3 or ln > 120: ok = False; break
                if ram[p + ln - 1] == 0x17 or (ln >= 4 and ram[p + ln - 2] == 0x17): bl.append((p, ram[p + 1], ln)); p += ln
                else: ok = False; break
            if ok:
                for (pa, ev, ln) in bl: entries.append((oid, start, pa, ev & 0x7f))
    return entries

def main():
    for tag, snap in (('level 0', 'scratchpad/cadaver/gameplay_empire.snap'), ('level 1', 'scratchpad/cadaver/level1_loaded.snap')):
        h = S(os.path.join(ROOT, snap))
        ent = walk(h)
        first = {e[2]: e for e in ent if e[1] == 0x10}
        second = [e for e in ent if e[1] == 0x20]
        print('%s: %d blocks walked, %d labelled +$20, %d distinct block addresses' % (tag, len(ent), len(second), len(set(e[2] for e in ent))))
        ids = sorted((h.obj(i), i) for i in range(1000) if h.obj(i) is not None)
        for oid, st, pa, ev in second:
            other = first.get(pa)
            nxt = [i for a, i in ids if a == h.obj(oid) + 0x10]
            print('  object %d +$20 event %d block @%06x: also walked as +$10 of object %s; template %d is %d bytes long (next template: %s); its byte 11 = %d, byte 31 = %d'
                  % (oid, ev, pa, other[0] if other else None, oid, ([a for a, i in ids if a > h.obj(oid)][0] - h.obj(oid)),
                     nxt[0] if nxt else None, h.ram[h.obj(oid) + 11], h.ram[h.obj(oid) + 31]))
        n_alias = sum(1 for e in second if e[2] in first)
        print('  aliased to another object\'s +$10 list: %d of %d' % (n_alias, len(second)))

if __name__ == '__main__':
    main()
