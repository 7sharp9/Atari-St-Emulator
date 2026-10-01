"""pigeon_ledger.py <land.json>...: for each $4244 -> $42c8 event pair captured by py/probe42be.py (scratchpad/probe42be/<snap>_land.json),
compare every lord's troops_field with the 137th rule count (live man, byte6 == 0, home lord via 34(man),
bit 6 clear, leader-flag man only if 42(man)==0) before and after the pigeon landing."""
import json, sys, struct
def W(b, a): return (b[a] << 8) | b[a + 1]
def counts(ent, settl):
    men = {}
    for i in range(512):
        a = 50 * i
        if not (0 < ent[a + 5] < 128) or ent[a + 6] != 0: continue
        fl = ent[a + 7]
        if fl & 0x40: continue
        if fl & 0x10 and W(ent, a + 42) != 0: continue
        lord = W(settl, W(ent, a + 34) + 14)
        men[lord] = men.get(lord, 0) + 1
    return men
for p in sys.argv[1:]:
    ev = json.load(open(p))
    for k in range(0, len(ev), 2):
        pre, post = ev[k], ev[k + 1]
        rows = []
        for tag, e in (('pre', pre), ('post', post)):
            m = counts(e['ent'], e['settl'])
            for li in range(32):
                b = 32 * li
                tf = W(e['lead'], b + 8)
                if e['lead'][b] == 0 and W(e['lead'], b + 4) == 0: continue
                rows.append((tag, li, tf, m.get(b, 0)))
        bad = [r for r in rows if r[2] != r[3]]
        d = [(li, a[2], b[2]) for a, b in zip([r for r in rows if r[0]=='pre'], [r for r in rows if r[0]=='post']) for li in [a[1]] if a[2] != b[2]]
        print(p.split('/')[-1], 'event', k // 2, 'lords', len(rows) // 2, 'tf!=rule', bad, 'tf changes (lord,pre,post)', d)
