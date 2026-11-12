"""Press keypad keys from a snapshot and save: keys.py <snap> <out.snap> <hex,...>; prints party pos/facing after each."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
s = srv(sys.argv[1])
for k in sys.argv[3].split(','):
    k = int(k, 16)
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=300000)
    print(hex(k), 'pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30))
s('save', path=os.path.abspath(sys.argv[2])); s.close()
