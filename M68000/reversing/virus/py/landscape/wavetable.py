"""Decode the wave table $20e34 (16 pointers to group lists read by $20e92: movem D4-D7,A4) from a snapshot's RAM.
Group = 5 longs: count D4, first life D5, life step D6, velocity shift D7, behaviour A4; a count of 0 ends a list.
Usage: wavetable.py <snap>"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vcommon

NAMES = {0x21776: 'seeder', 0x21ae2: 'chaser', 0x21c42: 'patrol', 0x222dc: 'bomber',
         0x2200c: 'pursuer2', 0x22486: 'attractor', 0x22688: 'mothership'}

def decode(ram):
    ptrs = struct.unpack('>16I', ram[0x20e34:0x20e74])
    blocks = []
    for p in ptrs:
        a = p; g = []
        while True:
            cnt, first, step, sh, beh = struct.unpack('>5I', ram[a:a + 20])
            if cnt == 0:
                break
            a += 20
            g.append((NAMES.get(beh, hex(beh)), cnt, first, step, sh))
        blocks.append((p, g))
    return blocks

if __name__ == '__main__':
    ram = vcommon.load_ram(sys.argv[1])
    bl = decode(ram)
    for n, (p, g) in enumerate(bl):
        print(n, hex(p), ' '.join(f'{k}x{c}(first {f},step {s},sh {sh})' for k, c, f, s, sh in g))
    ok = all(NAMES.get(0) is None for _ in bl) and all(k in NAMES.values() for _, g in bl for k, *_ in g)
    print(f'wave table: {len(bl)} blocks, {len(set(p for p, _ in bl))} distinct, every behaviour pointer known: {ok}')
