"""Decode Impossamole's spawn-type descriptors and draw each type's animation frames (README "Spawn types").

    uv run python reversing/impossamole/py/spawn_types.py <snap> [--sheet out.png] [--check]

Every record of the spawn list ($27200) carries a type byte; `$10474 + 4*type` is the descriptor address. The
descriptor's first byte picks the allocator (`$10046`: 0 = `$10056`, slots 0-5; 1 = `$100ec`, slots 7-11;
2 = `$1021a`, the boss; 3 = `$1037a`). Layouts, read off the allocators:

  kind 0 (`$10056`): +1 height, +2 animation tick count, +3 -> 79(A0), +4 long animation list. Object type word 1,
         so the frames are bank 1 (16x16, `$3b600`).
  kind 1 (`$100ec`): +1/+2 -> 12/13(A0) (hit-box radii), +3 -> 20(A0) (initial horizontal direction, also the entry index into the pointer table at +24)
         (4 bytes each, zero-ended), +4 -> 21(A0) (initial vertical direction, 0 up / 1 down), +5 tick count, +6 hit points 103(A0), +7 contact damage 104(A0),
         +8 word = object type word 0(A0) (1: bank 1 16x16, 2: bank 2 32x24), +10/+12 words -> 8/10(A0) (+12 plus
         +2 is the row count 14(A0)), +14/+16 -> 16/18(A0), +18 word -> 106(A0), +20 long -> 86(A0) (per-enemy
         handler), +24.. animation list pointers.
  kind 2 (`$1021a`): the boss; +28 long animation list, +5/+6 hit points/damage.

An animation pointer addresses a run of sub-animations, each a list of frame words ended by a control word
(`$fffe` loop, `$fffd` hold the last frame, `$ffff` end of list); the first sub-animation is the one the
allocator starts the object in, and the later ones are its other states (for a kind-1 enemy, in order of use by
its handler, not yet decoded). `--check` compares live kind-1 slots
(`$1a5de`, stride 108, descriptor = 94(A0) - 24) with their descriptor's frame list.
"""
import argparse, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiles import ram_from_snap, palette
from sprites import frame_image, BANKS, TRANSPARENT
from PIL import Image, ImageDraw

W = lambda ram, a: struct.unpack_from('>H', ram, a)[0]
L = lambda ram, a: struct.unpack_from('>I', ram, a)[0]


def spawn_records(ram):
    a = 0x27200
    while ram[a:a + 4] == b'\0\0\0\0':
        a += 4
    recs = []
    while W(ram, a) != 0x7fff:
        recs.append((W(ram, a), ram[a + 2] * 8 + 8, ram[a + 3]))
        a += 4
    return recs


def anim_frames(ram, ptr, subs=1):
    """Frames of the animation at ptr. The list is a run of sub-animations, each ended by a control word:
    $fffe (loop this sub-animation), $fffd (hold its last frame) or $ffff (end of the whole list). Returns
    (frames of the first sub-animation, control word that ended it, following sub-animations up to `subs`)."""
    subs_out, cur, a = [], [], ptr
    while len(subs_out) < subs + 1 and a < ptr + 200:
        v = W(ram, a)
        a += 2
        if v >= 0xfff0:
            subs_out.append((cur, v))
            cur = []
            if v == 0xffff:
                break
        elif v >= 0x100:  # a pointer half of the next descriptor, not a frame: the list has run out
            cur = []
            break
        else:
            cur.append(v)
    first = subs_out[0] if subs_out else (cur, None)
    return first[0], first[1], subs_out[1:]


def describe(ram, typ):
    return describe_desc(ram, L(ram, 0x10474 + 4 * typ), typ)


def describe_desc(ram, d, typ=None):
    kind = ram[d]
    r = dict(type=typ, desc=d, kind=kind, bank=1, hp=None, dmg=None, handler=None, anim_set=None)
    if kind == 0:
        r.update(height=ram[d + 1], ticks=ram[d + 2], aux=ram[d + 3], anim=L(ram, d + 4))
    elif kind == 1:
        r.update(width=ram[d + 1], height=ram[d + 2], anim_set=ram[d + 3], ticks=ram[d + 5], hp=ram[d + 6],
                 dmg=ram[d + 7], bank=W(ram, d + 8), handler=L(ram, d + 20),
                 anim=L(ram, d + 24 + 4 * ram[d + 3]), radii=(W(ram, d + 12), W(ram, d + 14), W(ram, d + 16)))
    elif kind == 2:
        r.update(ticks=ram[d + 4], hp=ram[d + 5], dmg=ram[d + 6], bank=2, anim=L(ram, d + 28))
    else:
        r['anim'] = None
    if r.get('anim'):
        r['frames'], r['end'], _ = anim_frames(ram, r['anim'])
    else:
        r['frames'], r['end'] = [], None
    r['states'] = []
    if kind == 1:
        for i in range(12):
            ptr = L(ram, d + 24 + 4 * i)
            if not 0x20000 < ptr < 0x24000:
                break
            r['states'].append((ptr,) + anim_frames(ram, ptr)[:2])
    elif r.get('anim'):
        r['states'].append((r['anim'], r['frames'], r['end']))
    # frames reachable from the entry pointers: the first sub-animation of each pointer plus the next three in
    # memory (the handler steps through those; where one object's list ends and the next begins is not decoded)
    reach = []
    for ptr, _, _ in r['states']:
        first, _, more = anim_frames(ram, ptr, subs=3)
        for f in first + [f for s, _ in more for f in s]:
            if f not in reach:
                reach.append(f)
    r['reach'] = reach
    return r


def sheet(ram, pal, types, counts, scale=2, ncols=2):
    """One row per type: label, handler/anim line, then the frames reachable from its entry pointers."""
    cell = 34 * scale
    per_row = 10
    rows = []
    for t in types:
        r = describe(ram, t)
        nmax = (BANKS[r['bank']]['end'] - BANKS[r['bank']]['base']) // BANKS[r['bank']]['stride']
        fs = [f for f in r['reach'] if f < nmax][:per_row]
        rows.append((r, [frame_image(ram, r['bank'], f, pal) for f in fs]))
    h = 26 + 24 * scale + 6
    colw = 12 + per_row * cell
    nper = (len(rows) + ncols - 1) // ncols
    im = Image.new('RGB', (ncols * colw, nper * h), (40, 40, 40))
    d = ImageDraw.Draw(im)
    for i, (r, frs) in enumerate(rows):
        x0, y = (i // nper) * colw, (i % nper) * h + 4
        hp = '-' if r['hp'] is None else r['hp']
        d.text((x0 + 4, y), f"type {r['type']}  x{counts[r['type']]}  kind {r['kind']}  bank {r['bank']}  hp {hp}  "
                            f"dmg {r['dmg']}  desc ${r['desc']:05x}", fill=(230, 230, 120))
        hd = f"handler ${r['handler']:06x}  " if r['handler'] else ''
        d.text((x0 + 4, y + 11), f"{hd}entry frames {[f[:4] for _, f, _ in r['states']]}", fill=(180, 180, 180))
        for k, f in enumerate(frs):
            f = f.resize((f.width * scale, f.height * scale), Image.NEAREST)
            im.paste(f, (x0 + 4 + k * cell, y + 24))
    return im


def check(ram, snap=None):
    """Live kind-1 slots (7..11 at $1a5de, plus any slot of $1a2ea..) whose 94(A0) points into a descriptor:
    report whether the live frame word 6(A0) is one of that descriptor's animation frames."""
    ok = n = 0
    draw_results = []
    if snap is not None:
        import io, contextlib
        from sprites import check as sprite_check
        with contextlib.redirect_stdout(io.StringIO()):
            draw_results = sprite_check(snap, ram)
    for s in range(0, 20):
        a = 0x1a2ea + s * 108
        typ_word = W(ram, a)
        p = L(ram, a + 94)
        if typ_word not in (1, 2) or not (0x10474 < p - 24 < 0x13000) or s < 6:
            continue
        d = p - 24
        if ram[d] != 1:
            continue
        frames = set(describe_desc(ram, d)['reach'])
        fr = W(ram, a + 6)
        n += 1
        ok += fr in frames
        px = ''
        if snap is not None:
            m = [r for r in draw_results if r['slot'] == s]
            if m:
                px = f"  drawn at ({m[0]['x']},{m[0]['y']}): {m[0]['match']}/{m[0]['total']} opaque pixels equal the screen"
        print(f'slot {s:2d} type word {typ_word} desc ${d:05x} live frame {fr:3d} in descriptor frames: {fr in frames}{px}')
    print(f'{ok}/{n} live frames are in their descriptor frame list')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap')
    ap.add_argument('--sheet')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--scale', type=int, default=2)
    a = ap.parse_args()
    ram = ram_from_snap(Path(a.snap))
    recs = spawn_records(ram)
    counts = {}
    for _, _, t in recs:
        counts[t] = counts.get(t, 0) + 1
    types = sorted(counts)
    print('type count kind bank hp dmg  desc    handler  anim     h  frames')
    for t in types:
        r = describe(ram, t)
        hd = '-' if r['handler'] is None else f"${r['handler']:06x}"
        an = '-' if not r.get('anim') else f"${r['anim']:05x}"
        hp = '-' if r['hp'] is None else r['hp']
        print(f"{t:4} {counts[t]:5} {r['kind']:4} {r['bank']:4} {str(hp):>3} {str(r['dmg']):>3}  ${r['desc']:05x}  {hd:8} {an:8} "
              f"{r.get('height', '-'):>3}  {[f[:6] for _, f, _ in r['states']]}")
    if a.sheet:
        pal = palette(a.snap, ram)
        im = sheet(ram, pal, types, counts, a.scale)
        im.save(a.sheet)
        print('wrote', a.sheet, im.size)
    if a.check:
        check(ram, a.snap)


if __name__ == '__main__':
    main()
