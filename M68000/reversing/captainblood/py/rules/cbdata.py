"""BLOOD.COM data helpers for the rule model (no literal absolute paths: repo root found via tools/rdis.py)."""
import struct, os
def repo_m68():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != '/' and not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        d = os.path.dirname(d)
    return d
M68 = repo_m68()
COM = os.path.join(M68, 'scratchpad/captainblood/depacked/BLOOD.COM')
BASE = 0x61400
def load():
    b = open(COM, 'rb').read()
    lenB, lenA = struct.unpack('>II', b[4:12])
    vocab = []
    for i in range(120):
        r = b[0x20+16*i:0x30+16*i]
        vocab.append((r[0], r[1:].split(b'\0')[0].decode('latin1')))
    B0 = 0xb10; A0 = B0 + lenB
    races = []
    for i in range(16):
        r = b[0x910+32*i:0x930+32*i]
        name = r[:16].decode('latin1').strip('\0 ').strip()
        offA, offB = struct.unpack('>II', r[16:24]); la, lb = struct.unpack('>HH', r[24:28])
        races.append(dict(i=i, name=name, offA=offA, offB=offB, lenA=la, lenB=lb,
                          A=BASE + A0 + offA, B=BASE + B0 + offB))
    return b, vocab, races
def records(b, race):
    """list of (addr_in_RAM, hdr, flag, payload bytes) up to the terminator"""
    a = race['A'] - BASE; out = []
    while b[a] != 0xff:
        h = b[a]; L = h & 0x1f
        out.append((BASE + a, h, b[a+1], bytes(b[a+2:a+2+L])))
        a += 2 + L
    return out
