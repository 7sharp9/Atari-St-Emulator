"""Annotated listing of a pool A type handler: state entry labels and names of the shared helpers.  usage: showtype.py <type> [state ...]
(with state numbers only those state bodies are printed; a state body runs from its entry to the next state entry or the handler end)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import states
SYM = {0x22c56: "hit_normal", 0x22dac: "hit_special", 0x22540: "anim_update", 0x2331c: "touch_and_hit_tests", 0x2242c: "bounds_or_despawn",
       0x22664: "apply_velocity", 0x226e4: "move_wall(D0,D1,D2,D3)", 0x22b48: "pick_target_player", 0x22bd0: "load_target_pos(+42,+44,+46,+47,+50)",
       0x22c2c: "state_changed()", 0x2280c: "arc_setup_to_player_y(D7)", 0x22844: "arc_setup(D7)", 0x22856: "arc_step", 0xe1c: "sound(D7)", 0xea44: "random",
       0x21e72: "spawn_obj(D6=?,D7=dir)", 0x21eb6: "spawn_obj2(D6,D7)", 0x21efa: "spawn_effect(D4=x,D5=y,D6,D7)", 0x1c8a: "spawn_A(D7=type)", 0x2250c: "despawn",
       0x234e6: "state_hurt", 0x2397e: "state_die", 0x22ecc: "state_grabbed", 0x23ac0: "state_fall_a", 0x23748: "state_fall_b", 0x23248: "state_a", 0x22e30: "state_17",
       0x2288c: "land_a", 0x228f4: "land_b", 0x2297a: "land_c", 0x22a4a: "land_d", 0x22ab0: "land_e", 0x2267e: "terrain_probe(D0,D1)", 0x248bc: "score_drop", 0x23394: "hit_effect", 0x233cc: "hit_effect2"}
def main():
    t = int(sys.argv[1]); only = [int(x, 16) for x in sys.argv[2:]]
    s, e = states.hrange(t)
    labels = {}
    tabs = states.tables(t)
    ents = {}
    for a, T, ent in tabs:
        for i, v in enumerate(ent):
            if s <= v < e: ents.setdefault(v, []).append(i)
    lines = []
    for l in states.LIN:
        m = re.match(r"\s+\$([0-9a-f]+):\s*(.*)", l)
        if not m: continue
        a = int(m.group(1), 16)
        if s <= a < e: lines.append((a, m.group(2)))
    sel = None
    if only:
        starts = sorted(ents)
        keep = set()
        for st in only:
            for v, ids in ents.items():
                if st in ids:
                    nxt = [x for x in starts if x > v]
                    keep.add((v, nxt[0] if nxt else e))
        lines = [(a, t_) for a, t_ in lines if any(lo <= a < hi for lo, hi in keep)]
    for a, text in lines:
        if a in ents: print("  ; ---- state %s ----" % ",".join("%x" % i for i in ents[a]))
        m = re.search(r"\$([0-9a-f]+)\.l$", text) or re.search(r"== \$([0-9a-f]+)$", text)
        note = ""
        if m and text.startswith(("jsr", "bsr")) and int(m.group(1), 16) in SYM: note = "   ; " + SYM[int(m.group(1), 16)]
        elif text.startswith("bsr"):
            m2 = re.search(r"\$([0-9a-f]+)$", text)
            if m2 and int(m2.group(1), 16) in SYM: note = "   ; " + SYM[int(m2.group(1), 16)]
        print("  $%06x: %s%s" % (a, text, note))
if __name__ == "__main__": main()
