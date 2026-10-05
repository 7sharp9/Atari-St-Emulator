import os, sys, re, importlib.util, io, contextlib
log = sys.argv[1]
sys.argv = ['anal', log]
spec = importlib.util.spec_from_file_location('anal', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anal.py')); a = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(a)
prev = None
for fr in a.frames:
    for ad, b in fr['p6'].items():
        s = (b[2], b[3], b[4], b[5], b[19], b[20], b[64], b[45], b[44])
        if s != prev:
            print('rel', fr['rel'], 'p6 %x' % ad, 'st', s[:4], 'kind', s[4], 'sub', s[5], 'b64', s[6], 'a45', s[7], 'a44', s[8], 'x %04x y %04x' % (a.w(b, 6), a.w(b, 10)), 'vx %04x vy %04x' % (a.w(b, 80), a.w(b, 84)), 'b54', b[54], 'b74', b[74])
            prev = s
