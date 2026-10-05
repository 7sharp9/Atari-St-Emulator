import os, importlib.util,io,contextlib,sys
log=sys.argv[1]; sys.argv=['anal',log]
spec=importlib.util.spec_from_file_location('anal',os.path.join(os.path.dirname(os.path.abspath(__file__)),'anal.py')); a=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(a)
prev=None
for fr in a.frames:
    for ad,b in fr['recs'].items():
        if b[19]!=8: continue
        t=(int.from_bytes(b[134:138],'big'),b[46],b[2],b[3],b[4],b[5],b[74])
        if t!=prev: print('rel',fr['rel'],'st',t[2:6],'target(134) %06x'%t[0],'face',t[1],'holding74',t[6],'x %04x'%a.w(b,6)); prev=t
