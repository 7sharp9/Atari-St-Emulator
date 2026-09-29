"""Render every static asset of one Impossamole world from a gameplay snapshot (README "Worlds", graphics.md).

    uv run python <this> <gameplay.snap> <name> [--out DIR]

Writes, under DIR (default agents/world12/out):
  <name>_tileset.png          the 256-tile bank ($29800), 16 per row, 3x
  <name>_level_tiles.png      the whole level from real tiles (420 block columns, 13440x192), 1x
  <name>_categories.png       the whole level, real art with the $25000 categories tinted over the 8px cells
                              (1 green, 2 blue, 3 magenta, 4 none, 5 orange, 6 yellow, 8 cyan, 9 red), 40 blocks per row
  <name>_level_map.png        level_map.py --rooms render (category colours incl. 5/6/8, room boundaries, exit ticks)
  <name>_sprites_bank1.png    bank 1 ($3b600, 240 frames); frames 160-239 (world file) labelled yellow
  <name>_sprites_bank2.png    bank 2 ($42e00, 172 frames); frames 100-171 (world file) labelled yellow
  <name>_spawn_types.png      spawn_types.py --sheet
  <name>_rooms.txt, <name>_spawn_list.txt, <name>_spawn_types.txt, <name>_checks.txt
The existing tools in reversing/impossamole/py are imported / run unchanged, except that the category tints and
level_map colours are extended (level_map.CATCOL and tiles.CATTINT know only categories 0-4 and 9; Klondike Mine and
The Orient also use 5, 6 and 8, so the stock `--cats` overlay would draw them as plain art / raise KeyError).
"""
import argparse, contextlib, io, os, struct, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
PY = ROOT / 'reversing/impossamole/py'
sys.path.insert(0, str(PY)); sys.path.insert(0, str(ROOT / 'tools'))
import tiles, sprites, spawn_types, level_map                      # noqa: E402
from PIL import Image, ImageDraw                                    # noqa: E402

TINT = {1: (60, 255, 90), 2: (60, 140, 255), 3: (255, 90, 255), 5: (255, 150, 30), 6: (255, 240, 60),
        8: (40, 235, 235), 9: (255, 40, 40)}
LEGEND = {1: 'cat 1', 2: 'cat 2', 3: 'cat 3', 5: 'cat 5', 6: 'cat 6', 8: 'cat 8', 9: 'cat 9 hazard'}
level_map.CATCOL.update({5: (255, 150, 30), 6: (255, 240, 60), 8: (40, 235, 235)})


def world_palette(ram):
    """The world's palette from the pointer table $2166e (index $bb76-1), and whether it equals the live one."""
    w = ram[0xbb76]
    a = struct.unpack_from('>I', ram, tiles.PALTAB + 4 * (w - 1))[0]
    return a, [tiles.st_rgb(x) for x in struct.unpack_from('>16H', ram, a)]


def categories(snap, ram, pal, out):
    _, tl, cls = level_map.load(snap)
    base = tiles.to_image(tiles.level_index_image(ram, 0, tiles.NBLOCKS), pal).convert('RGBA')
    ov = Image.new('RGBA', base.size, (0, 0, 0, 0))
    px = ov.load()
    for r in range(24):
        for c in range(1680):
            k = cls[tl[r][c]]
            if k in TINT:
                for y in range(8):
                    for x in range(8):
                        px[c * 8 + x, r * 8 + y] = TINT[k] + (150,)
    full = Image.alpha_composite(base, ov).convert('RGB')
    per = 40 * 32
    n = (full.width + per - 1) // per
    im = Image.new('RGB', (per, (192 + 12) * n), (30, 30, 30))
    d = ImageDraw.Draw(im)
    for i in range(n):
        im.paste(full.crop((i * per, 0, min((i + 1) * per, full.width), 192)), (0, i * 204 + 12))
        d.text((2, i * 204 + 1), f'blocks {i * 40}-{min(i * 40 + 39, 419)}', fill=(220, 220, 220))
    x = 300
    for k, name in LEGEND.items():
        d.rectangle([x, 2, x + 8, 10], fill=TINT[k]); d.text((x + 12, 1), name, fill=(220, 220, 220)); x += 90
    im.save(out)
    used = {}
    for r in range(24):
        for c in range(1680):
            used[cls[tl[r][c]]] = used.get(cls[tl[r][c]], 0) + 1
    return used


WORLD_FILES = {1: 'MINES', 2: 'ORIENT', 3: 'JUNGLE', 4: 'ICELND', 5: 'BRMUDA'}
EXTRACTED = ROOT / 'scratchpad/impossamole/extracted'


def bank_extents(world):
    """(bank 1 end frame, bank 2 end frame), exclusive, from the LSD! headers of the world's two sprite files:
    <WORLD>22.DAT is unpacked to $40600 (bank 1 from frame 160), <WORLD>33.DAT to $4c400 (bank 2 from frame 100);
    the longword at file offset 4 is the unpacked length. RAM beyond it (Klondike Mine bank 2 frames 160-171) is
    residue of an earlier load, not art."""
    def unpacked(f):
        h = (EXTRACTED / f).read_bytes()[:8]
        assert h[:4] == b'LSD!', f
        return struct.unpack('>I', h[4:8])[0]
    return 160 + unpacked(WORLD_FILES[world] + '22.DAT') // 128, 100 + unpacked(WORLD_FILES[world] + '33.DAT') // 384


def bank_sheet(ram, bank, pal, scale, cols, first_world_frame, end_frame):
    b = sprites.BANKS[bank]
    frames = [f for f in sprites.used_frames(ram, bank) if f < end_frame]
    cw, ch = b['w'] * scale + 2, b['h'] * scale + 2 + 10
    rows_n = (frames[-1] // cols) + 1
    im = Image.new('RGB', (cols * cw, rows_n * ch), (40, 40, 40))
    d = ImageDraw.Draw(im)
    for i in frames:
        f = sprites.frame_image(ram, bank, i, pal).resize((b['w'] * scale, b['h'] * scale), Image.NEAREST)
        x, y = (i % cols) * cw + 1, (i // cols) * ch + 11
        im.paste(f, (x, y))
        d.text((x, y - 10), str(i), fill=(255, 230, 90) if i >= first_world_frame else (200, 200, 200))
    return im


def run_tool(script, *args, out=None):
    r = subprocess.run([sys.executable, str(PY / script), *map(str, args)], capture_output=True, text=True, cwd=ROOT)
    txt = r.stdout + (r.stderr if r.returncode else '')
    if out:
        Path(out).write_text(txt)
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap'); ap.add_argument('name')
    ap.add_argument('--out', default=str(ROOT / 'scratchpad/impossamole/agents/world12/out'))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    n, snap = a.name, Path(a.snap)
    ram = tiles.ram_from_snap(snap)
    live = tiles.palette(snap, ram)
    addr, wpal = world_palette(ram)
    checks = [f'world index $bb76 = {ram[0xbb76]}; world palette ${addr:x} equals the live hardware palette: {wpal == live}']
    pal = live
    im = Image.new('RGB', (16 * 17 + 1, 16 * 17 + 1), (40, 40, 40))
    for t in range(tiles.NTILES):
        im.paste(tiles.to_image(tiles.tile_pixels(ram, t), pal), (1 + (t % 16) * 17, 1 + (t // 16) * 17))
    im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(out / f'{n}_tileset.png')
    tiles.to_image(tiles.level_index_image(ram, 0, tiles.NBLOCKS), pal).save(out / f'{n}_level_tiles.png')
    used = categories(snap, ram, pal, out / f'{n}_categories.png')
    checks.append(f'collision cells (1680x24) by category: {dict(sorted(used.items()))}')
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        sys.argv = ['level_map.py', str(snap), str(out / f'{n}_level_map.png'), '--rooms', '--scale', '2']
        level_map.main()
    checks.append('level_map: ' + buf.getvalue().strip())
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        tiles.check(snap, ram)
    checks.append('tiles --check: ' + buf.getvalue().strip())
    e1, e2 = bank_extents(ram[0xbb76])
    checks.append(f'sprite bank extents from the LSD! headers: bank 1 frames 0-{e1 - 1}, bank 2 frames 0-{e2 - 1}')
    bank_sheet(ram, 1, pal, 3, 16, 160, e1).save(out / f'{n}_sprites_bank1.png')
    bank_sheet(ram, 2, pal, 2, 16, 100, e2).save(out / f'{n}_sprites_bank2.png')
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        sprites.check(snap, ram)
    checks.append('sprites --check:\n' + buf.getvalue().strip())
    run_tool('level_rooms.py', snap, out=out / f'{n}_rooms.txt')
    run_tool('spawn_list.py', snap, out=out / f'{n}_spawn_list.txt')
    run_tool('spawn_types.py', snap, '--sheet', out / f'{n}_spawn_types.png', '--check', out=out / f'{n}_spawn_types.txt')
    (out / f'{n}_checks.txt').write_text('\n'.join(checks) + '\n')
    print('\n'.join(checks))


if __name__ == '__main__':
    main()
