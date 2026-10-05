-- FF_EXTRA: keep prop PA i=FF_PROP (default 13) at Cody's lane (+2) and 0x20 in front of him (facing right); also log pools
local pools = dofile(os.getenv("PD") .. "/extra_pools.lua")
local idx = tonumber(os.getenv("FF_PROP") or "13")
return function(f, rel, m, out)
  local a = 0xffb2e8 + 0xc0 * idx
  if m:read_u8(a) ~= 0 then
    local gy = m:read_u16(0xff8576)
    m:write_u16(a + 10, gy + 2); m:write_u16(a + 14, gy + 2)
    m:write_u16(a + 6, m:read_u16(0xff856e) + 0x20)
  end
  pools(f, rel, m, out)
end
