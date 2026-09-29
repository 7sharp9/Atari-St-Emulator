"""Join live object slots of many snapshots to spawn-type descriptors and to the pixel match of their frame.

    uv run python <this> <name> <snap> [<snap> ...]

For each snapshot, every live type-1/type-2 object slot (sprites.check: frame blitted at its declared (x, y),
opaque pixels equal to the screen, lower bound) is joined to a spawn type:
  slots >= 6 (kind-1 enemies/parts): descriptor = 94(A0) - 24 (README "Spawn types"), type = its index in $10474;
  slots 0-5 (kind-0 pickups/props): 22(A0) is the descriptor's +4 animation list pointer, so every type whose
  descriptor has that pointer is a candidate (several types can share one).
Prints, per spawn-list type of the world, the best pixel match over all snapshots (type, slot, frame, match/total,
snapshot) and lists the types never seen live. Objects a handler spawns itself (projectiles, effects) are joined
only when their descriptor matches.
"""
import io, contextlib, os, struct, sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'reversing/impossamole/py')); sys.path.insert(0, str(ROOT / 'tools'))
import sprites, spawn_types                                        # noqa: E402
from tiles import ram_from_snap                                    # noqa: E402

W = lambda ram, a: struct.unpack_from('>H', ram, a)[0]
L = lambda ram, a: struct.unpack_from('>I', ram, a)[0]


def main():
    name, snaps = sys.argv[1], sys.argv[2:]
    best, seen_snaps = {}, 0
    types = None
    for sp in snaps:
        ram = ram_from_snap(Path(sp))
        if types is None:
            types = sorted({t for _, _, t in spawn_types.spawn_records(ram)})
            descs = {t: L(ram, 0x10474 + 4 * t) for t in range(256)}
            descs = {t: d for t, d in descs.items() if 0x10000 < d < 0x20000}
        with contextlib.redirect_stdout(io.StringIO()):
            res = sprites.check(sp, ram)
        seen_snaps += 1
        for r in res:
            a = 0x1a2ea + r['slot'] * 108
            cands = []
            if r['slot'] >= 6:
                d = L(ram, a + 94) - 24
                cands = [t for t in descs if descs[t] == d]
            else:
                anim = L(ram, a + 22)
                cands = [t for t in descs if ram[descs[t]] == 0 and L(ram, descs[t] + 4) == anim]
            for t in cands:
                key = (r['match'] / max(r['total'], 1), r['match'])
                if t not in best or key > best[t][0]:
                    best[t] = (key, r, Path(sp).name, len(cands))
    print(f'{name}: {seen_snaps} snapshots')
    print('type  best match          slot frame  snapshot                       (candidates sharing the slot)')
    for t in types:
        if t in best:
            key, r, sn, nc = best[t]
            print(f'{t:4}  {r["match"]:4}/{r["total"]:<4} ({key[0]*100:5.1f}%)  {r["slot"]:3} {r["frame"]:4}  {sn:30} {nc if nc > 1 else ""}')
        else:
            print(f'{t:4}  never seen live')


if __name__ == '__main__':
    main()
