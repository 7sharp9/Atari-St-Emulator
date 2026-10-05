import os, importlib.util,io,contextlib,sys
log=sys.argv[1]; sys.argv=['anal',log]
spec=importlib.util.spec_from_file_location('anal',os.path.join(os.path.dirname(os.path.abspath(__file__)),'anal.py')); a=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(a)
prev=None
for fr in a.frames:
    c=fr['c']; s=(a.w(c,24),c[2],c[3],c[4])
    if s!=prev: print('rel',fr['rel'],'cody hp',s[0],'st',s[1:],'x %04x y %04x'%(a.w(c,6),a.w(c,10)),'r22',c[22],'r63',c[63],'atker %04x'%a.w(c,60)); prev=s
