-- like extra_dummy.lua, plus: the dummy's hp (+24, +26, +28) is reset to $300 when it falls below $180 (damage steps stay visible in the log; the reset is a positive step)
local base = dofile(os.getenv("PD") .. "/extra_dummy.lua")
local idx = tonumber(os.getenv("FF_DUMMY") or "12")
return function(f, rel, m, out)
  local a = 0xff86e8 + 0xc0 * idx
  if m:read_u8(a) ~= 0 and m:read_u8(a + 2) == 2 then
    local hp = m:read_u16(a + 24)
    if hp < 0x180 then m:write_u16(a + 24, 0x300); m:write_u16(a + 26, 0x300); m:write_u16(a + 28, 0x300) end
  end
  base(f, rel, m, out)
end
