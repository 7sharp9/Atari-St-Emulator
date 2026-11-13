"""MESSAGE FROM RATT (item type $66): run the text selector $138ae for each value of 407(A6) (labelled poke) under
stserver, stop at the print routine $bb4c and read the string at A0; also print the bytes of $13906 in each snapshot
given, to show the corner text is the same whatever the bases' door codes are.
Usage: ratt_msg.py <snap> [<snap> ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import R, StServer, snappath  # noqa: E402
A6 = 0x1b5ce
s = StServer(R)
for snap in sys.argv[1:]:
    s('load', snapshot=snappath(snap)); s.sp = None
    doors = s.read(A6 + 2330, 32)
    codes = [(int.from_bytes(doors[i + 2:i + 4], 'big') >> 4) & 0x1f for i in range(0, 32, 4) if any(doors[i:i + 4])]
    print(os.path.basename(snap), 'door codes', codes, '$13906:', s.read(0x13906, 48).split(b'\0')[0])
    base = s('fork')['id']
    for k in range(3):
        s('restore', id=base); s.sp = None
        s('poke', addr=A6 + 407, width=1, value=k)
        s.call(0x138ae, stops=[0xbb4c])
        a0 = s.reg('a0')
        print(f'  407(A6)={k}: at $bb4c A0=${a0:06x}', s.read(a0, 48).split(b'\0')[0])
s.close()
