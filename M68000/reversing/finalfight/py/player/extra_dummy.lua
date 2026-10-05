-- FF_EXTRA: keep enemy record FF_DUMMY (pool-2 local index, default 11) next to the player (x + FF_DX, same ground y) while it is on the ground
-- and not in a hit-reaction (+2/+3 states are left alone: only position is forced); log E lines as extra_enemy.lua does.
local base = dofile(os.getenv("PD") .. "/extra_enemy.lua")
local idx = tonumber(os.getenv("FF_DUMMY") or "11")
local dx = tonumber(os.getenv("FF_DX") or "28")
local face = os.getenv("FF_DFACE")
return function(f, rel, m, out)
  local a = 0xff86e8 + 0xc0 * idx
  if m:read_u8(a) ~= 0 and m:read_u16(a + 10) == m:read_u16(a + 14) then
    local px = m:read_u16(0xff856e)
    local right = (m:read_u8(0xff8596) == 0)
    local x = right and px + dx or px - dx
    m:write_u16(a + 6, x)
    m:write_u16(a + 10, m:read_u16(0xff8572)); m:write_u16(a + 14, m:read_u16(0xff8576))
  end
  base(f, rel, m, out)
end
