import os, importlib.util,io,contextlib,sys
log=sys.argv[1]; sys.argv=['anal',log]
spec=importlib.util.spec_from_file_location('anal',os.path.join(os.path.dirname(os.path.abspath(__file__)),'anal.py')); a=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(a)
prev=None; seen={}
for fr in a.frames:
    s=fr.get('s')
    if s is not None:
        t=(s[2],s[3],s[4],s[5],int.from_bytes(s[6:10],'big'),int.from_bytes(s[10:12],'big'),s[22])
        if t!=prev: print(fr['rel'],'script rec st',t[:4],'ptr %x'%t[4],'mode',t[5],'b22',t[6],'cam %04x'%fr['cam']); prev=t
    for ad,b in fr['recs'].items():
        k=(ad,b[19],b[20],b[21])
        if k not in seen:
            seen[k]=fr['rel']; print('   rel',fr['rel'],'tag-2 rec %x'%ad,'kind',b[19],'sub',b[20],b[21],'x %04x y %04x'%(a.w(b,6),a.w(b,10)),'cam %04x'%fr['cam'])
