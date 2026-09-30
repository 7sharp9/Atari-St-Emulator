"""bootpoison.py FILE BLOCK [STEPS] : cold-boot poison scan.  For every BLOCK-byte block of FILE (INIT.DAT|SUPER1.DAT|SUPER.DAT),
patch a copy of the disk image so that block holds the pattern A5..., cold-boot STEPS (default 4600000, just past the start of the
attract loop), dump RAM, and count the bytes that differ from a clean boot outside the poisoned file's own load buffer.
A block with 0 differing bytes outside its own buffer was never copied/derived anywhere during boot."""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fat12 import *
from ssh import R, AGENT, TMP
from multiprocessing import Pool

BUF = {'INIT.DAT': (0x59736, 5139), 'SUPER1.DAT': (0x61436, 17024), 'SUPER.DAT': (0x28e00, 212650)}

def boot_dump(tag, img_path, steps):
    snap = os.path.join(TMP, 'bp_%s.snap' % tag)
    env = dict(os.environ, ATARI_NOTRACE='1')
    subprocess.run(['dotnet', 'exec', sscfg.DLL, str(steps), 'snapshot', snap, '--disk-a', img_path], env=env, cwd=sscfg.R,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    r = R(snap)
    data = bytearray(); a = 0x200
    while a < 0x100000:
        n = min(0x10000, 0x100000 - a); data += r.mem(a, n); a += n
    r.close(); os.unlink(snap)
    return bytes(data)

def work(args):
    fname, off, ln, steps = args
    tag = '%s_%x' % (fname.split('.')[0], off)
    d = Disk(sscfg.DISK)
    d.patch(fname, off, bytes([0xA5, 0x5A] * (ln // 2 + 1))[:ln])
    img = os.path.join(TMP, 'bp_%s.ST' % tag); d.save(img)
    try:
        data = boot_dump(tag, img, steps)
    finally:
        os.unlink(img)
    return args, data

if __name__ == '__main__':
    fname = sys.argv[1]; blk = int(sys.argv[2]); steps = int(sys.argv[3]) if len(sys.argv) > 3 else 4600000
    size = len(open(os.path.join(sscfg.FILES, fname), 'rb').read())
    clean = boot_dump('clean_' + fname.split('.')[0], sscfg.DISK, steps)
    base, bl = BUF[fname]
    lo = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0
    hi = int(sys.argv[5], 16) if len(sys.argv) > 5 else size
    jobs = [(fname, o, min(blk, size - o), steps) for o in range(lo, min(hi, size), blk)]
    out = []
    with Pool(6) as p:
        for args, data in p.imap(work, jobs):
            _, off, ln, _ = args
            diff = [i + 0x200 for i in range(len(clean)) if clean[i] != data[i]]
            outside = [x for x in diff if not (base <= x < base + bl)]
            out.append({'off': off, 'len': ln, 'diff_total': len(diff), 'diff_outside_buffer': len(outside),
                        'first_outside': ['%x' % x for x in outside[:6]]})
            print('%-10s %06x len %5d diff %6d outside-own-buffer %6d %s' % (fname, off, ln, len(diff), len(outside), ['%x' % x for x in outside[:4]]), flush=True)
    json.dump(out, open(os.path.join(AGENT, 'bootpoison_%s%s.json' % (fname.split('.')[0], '_%x_%x' % (lo, hi) if len(sys.argv) > 4 else '')), 'w'), indent=1)
