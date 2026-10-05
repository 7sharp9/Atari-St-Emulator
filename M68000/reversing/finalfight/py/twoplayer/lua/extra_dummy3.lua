-- extra_dummy.lua variant for grapples: the dummy is only moved next to the player while the player is not in a grapple (+64 == 0) and the dummy is on the ground and unheld (+64 == 0)
local base = dofile(os.getenv("PD") .. "/extra_enemy.lua")
local idx = tonumber(os.getenv("FF_DUMMY") or "12")
local dx = tonumber(os.getenv("FF_DX") or "28")
return function(f, rel, m, out)
  local a = 0xff86e8 + 0xc0 * idx
  if m:read_u8(a) ~= 0 and m:read_u16(a + 10) == m:read_u16(a + 14) and m:read_u8(0xff8568 + 64) == 0 and m:read_u8(a + 64) == 0 then
    local px = m:read_u16(0xff856e)
    local right = (m:read_u8(0xff8596) == 0)
    m:write_u16(a + 6, right and px + dx or px - dx)
    m:write_u16(a + 10, m:read_u16(0xff8572)); m:write_u16(a + 14, m:read_u16(0xff8576))
  end
  base(f, rel, m, out)
end
