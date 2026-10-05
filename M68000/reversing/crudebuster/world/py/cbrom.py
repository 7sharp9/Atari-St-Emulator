"""Shared ROM readers for the WORLD agent (decrypted cbuster program image)."""
import struct, os
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
ROM = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def B(a): return ROM[a]
def W(a): return struct.unpack(">H", ROM[a:a+2])[0]
def L(a): return struct.unpack(">I", ROM[a:a+4])[0]
def SW(a): return struct.unpack(">h", ROM[a:a+2])[0]
def cstr(a, n=64):
    return ROM[a:a+n]
