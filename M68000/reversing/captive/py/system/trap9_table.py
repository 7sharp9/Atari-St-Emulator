"""Print the trap #9 dispatch table of the low-RAM loader (dispatcher at $206, word-offset table at $228,
function number D7 = 4*index, index <= $20) from a snapshot."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from util import Ram
r = Ram(sys.argv[1]); w = r.sw
for i in range(0x21):
    print(f'fn {4*i:3d} (${4*i:02x})  ${0x228 + w(0x228 + 2*i):04x}')
