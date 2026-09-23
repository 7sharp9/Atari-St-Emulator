import re,sys
names={'6522':'commander decide','661a':'primary-slot decide','68fe':'score A','68ee':'score B','6a3a':'order executor','15302':'reached-enemy','56a6':'engage','5778':'bookkeep','5590':'kill-or-rout','55f2':'KILL','560a':'ROUT','5bd2':'wear removal','5c10':'wear kill','57f0':'projectile','1d70':'route-expand','25d6':'capture flip','4bc8':'contact reconcile','5c80':'upkeep','1623c':'dying entity','162c8':'-> byte6 10','162d8':'-> byte6 32','2776':'$2776','1b8c':'$1b8c','3c08':'regroup','5cde':'herd-op','550e':'revolt','638c':'army supply','61f8':'supply','60dc':'herd credit','159de':'porter pick up','159a4':'porter drop','3ac8':'goods pile','45f2':'pigeon launch','15462':'byte6 28 (winter)','5e3a':'byte6 30 camp','163b8':'reserve-1'}
# hits_table.py <run-dir> <name>...   (the runland.sh output: <run-dir>/<name>.txt)
rd=sys.argv[1]; runs=sys.argv[2:]
data={}
for r in runs:
    txt=open(f'{rd}/{r}.txt').read()
    blocks=txt.split('--- hits over')[1:]
    data[r]=[]
    for b in blocks:
        d={}
        for m in re.finditer(r'\$([0-9a-f]{6})\s+(\d+)\s+first (-?\d+)', b): d[m.group(1).lstrip('0')]=int(m.group(2))
        data[r].append(d)
print(f"{'routine':28s}"+''.join(f'{r:>28s}' for r in runs))
for a,n in names.items():
    row=f"${a:6s}{n:21s}"
    for r in runs: row+=f"{'/'.join(str(d.get(a,0)) for d in data[r]):>28s}"
    print(row)
