-- per 10 frames: P1 x, y, +88, +89, +90, +102, +80 and the pool-a props (kind, x, y, state)
local f_ = io.open(os.getenv("FFD_TLOG") or (os.getenv("FF_OUT") .. "/p1terrain.log"), "w")
return function(f, L, bots)
  if f % 10 ~= 0 then return end
  local m = L.mem
  local P = 0xff8568
  local props = {}
  for i = 0, 15 do
    local a = 0xffb2e8 + 0xc0 * i
    if m:read_u8(a) ~= 0 then props[#props + 1] = string.format("%06x:k%d x=%04x y=%04x st=%02x%02x", a, m:read_u8(a + 19), m:read_u16(a + 6), m:read_u16(a + 14), m:read_u8(a + 2), m:read_u8(a + 3)) end
  end
  f_:write(string.format("%d P1 x=%04x y=%04x st=%02x%02x b88=%02x b89=%02x b90=%04x b102=%04x vx=%04x | %s\n", f, m:read_u16(P + 6), m:read_u16(P + 14), m:read_u8(P + 2), m:read_u8(P + 3), m:read_u8(P + 88), m:read_u8(P + 89),
    m:read_u16(P + 90), m:read_u16(P + 102), m:read_u16(P + 80), table.concat(props, " ; ")))
  f_:flush()
end
