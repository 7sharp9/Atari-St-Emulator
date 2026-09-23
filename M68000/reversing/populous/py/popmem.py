"""popmem.py - shared helpers for the terrain agent.
img(): POPULOUS.GOD relocated image (text+data+bss) at runtime base $ad58.
ram(snap): RAM of an emulator snapshot (absolute addresses)."""
import struct, os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg import WORK as S
BASE = 0xad58
_img = None
def img():
    global _img
    if _img is None:
        _img = b'\0'*BASE + open(os.path.join(S, 'pop_ad58.img'), 'rb').read()
    return _img
def ram(path):
    s = open(path, 'rb').read(); off = 5+19*4+2; ln = struct.unpack_from('<I', s, off)[0]
    return s[off+4:off+4+ln]
def w(m, a): return struct.unpack_from('>H', m, a)[0]
def sw(m, a): return struct.unpack_from('>h', m, a)[0]
def l(m, a): return struct.unpack_from('>I', m, a)[0]
def cstr(m, a):
    e = m.index(b'\0', a); return m[a:e].decode('latin1')
def apply_callcap(base, json_path):
    """RAM after a callcap = base RAM with the JSON memory delta applied."""
    import json
    d = json.load(open(json_path)); m = bytearray(base)
    for a, _x0, x1 in d['mem']:
        m[a] = x1
    return bytes(m), d
