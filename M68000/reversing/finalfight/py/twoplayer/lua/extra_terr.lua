-- pdrive FF_EXTRA: every 10 frames one "T" line: P1 x, +88, +89, +90, +102, camera x, and the live pool-a props
return function(f, rel, m, out)
  if rel % 10 ~= 0 then return end
  local P = 0xff8568
  local props = {}
  for i = 0, 15 do
    local a = 0xffb2e8 + 0xc0 * i
    if m:read_u8(a) ~= 0 then props[#props + 1] = string.format("%06x:k%d x=%04x y=%04x", a, m:read_u8(a + 19), m:read_u16(a + 6), m:read_u16(a + 14)) end
  end
  out:write(string.format("T %d x=%04x gy=%04x b88=%02x b89=%02x b90=%04x b102=%04x cam=%04x | %s\n", rel, m:read_u16(P + 6), m:read_u16(P + 14), m:read_u8(P + 88), m:read_u8(P + 89), m:read_u16(P + 90),
    m:read_u16(P + 102), m:read_u16(0xff8412), table.concat(props, " ; ")))
end
