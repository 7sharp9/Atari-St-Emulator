import re, collections
def load(path):
    rows=[]
    for l in open(path):
        m=re.match(r'(\S+) slot_side (\d) D7\s+(\d+) own28 (\d) lead_side (\d) st\s+(\d+) men\s+(-?\d+) food\s+(-?\d+) pend (\d) period (\d+) drain/eat (\d+) own_home (\[.*?\]) enemy_home (\[.*?\]) d (\S+) score (\S+)',l)
        if m:
            g=m.groups(); rows.append(dict(snap=g[0],side=int(g[1]),D7=int(g[2]),st=int(g[5]),men=int(g[6]),food=int(g[7]),pend=int(g[8]),per=int(g[9]),own=eval(g[11]),en=eval(g[12]),score=None if g[14]=='None' else int(g[14])))
    return rows
