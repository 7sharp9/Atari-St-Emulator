-- FF_EXTRA: per frame, one "E" line per live pool-2 record: index, st, sub, x, y, hp, +22, +63, +64, +60
return function(f, rel, m, out)
  for i = 0, 12 do
    local a = 0xff86e8 + 0xc0 * i
    if m:read_u8(a) ~= 0 then
      out:write(string.format("E %d %d i=%d st=%02x sub=%02x ss=%02x x=%04x y=%04x hp=%04x b22=%02x b63=%02x b64=%02x b60=%04x b45=%02x b44=%02x\n", f, rel, i, m:read_u8(a+2), m:read_u8(a+3), m:read_u8(a+4),
        m:read_u16(a+6), m:read_u16(a+10), m:read_u16(a+24), m:read_u8(a+22), m:read_u8(a+63), m:read_u8(a+64), m:read_u16(a+60), m:read_u8(a+45), m:read_u8(a+44)))
    end
  end
end
