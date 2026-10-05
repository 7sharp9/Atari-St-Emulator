-- FF_EXTRA: log live records of pools 6 ($ff90a8,6), 4 ($ff9528,8), 8 ($ff9b28,30), $a ($ffb2e8,16), $12 ($ffbee8,10), $14 ($ffc668,10, 64 bytes) when their +0 byte changes or each 20 frames
local pools = { {"P6", 0xff90a8, 6, 0xc0}, {"P4", 0xff9528, 8, 0xc0}, {"P8", 0xff9b28, 30, 0xc0}, {"PA", 0xffb2e8, 16, 0xc0}, {"P12", 0xffbee8, 10, 0xc0}, {"P14", 0xffc668, 10, 0x40} }
local last = {}
return function(f, rel, m, out)
  for _, p in ipairs(pools) do
    for i = 0, p[3] - 1 do
      local a = p[2] + p[4] * i
      local b0 = m:read_u8(a)
      local key = p[1] .. i
      local sig = string.format("%02x%02x%02x%02x%02x", b0, m:read_u8(a+2), m:read_u8(a+3), m:read_u8(a+19), m:read_u8(a+4))
      if b0 ~= 0 and (last[key] ~= sig or rel % 400 == 0) or (b0 == 0 and last[key] and last[key]:sub(1,2) ~= "00") then
        out:write(string.format("%s %d %d i=%d b0=%02x st=%02x sub=%02x ss=%02x kind=%02x w20=%04x x=%04x y=%04x gy=%04x hp=%04x b97=%02x b44=%02x b45=%02x h120=%08x hx=%04x hy=%04x b18=%02x\n", "Q" .. p[1], f, rel, i, b0, m:read_u8(a+2), m:read_u8(a+3), m:read_u8(a+4), m:read_u8(a+19), m:read_u16(a+20), m:read_u16(a+6), m:read_u16(a+10), m:read_u16(a+14), m:read_u16(a+24), m:read_u8(a+97), m:read_u8(a+44), m:read_u8(a+45), m:read_u32(a+120), m:read_u16(a+124), m:read_u16(a+126), m:read_u8(a+18)))
      end
      last[key] = sig
    end
  end
end
