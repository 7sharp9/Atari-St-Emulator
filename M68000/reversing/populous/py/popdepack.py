import struct
def depack(src):
    """src = packed stream (after the 8-byte header). Returns bytes."""
    out=bytearray(); i=0; n=len(src)
    while i<n:
        w=struct.unpack_from('>h',src,i)[0]; i+=2
        if w>=0:
            out+=src[i:i+w+1]; i+=w+1
        else:
            off=struct.unpack_from('>H',src,i)[0]; i+=2
            for k in range(-w+1): out.append(out[off+k])
    return bytes(out)
def unpack_file(d, off=0):
    plen,ulen=struct.unpack_from('>II',d,off)
    return depack(d[off+8:off+plen]), ulen
