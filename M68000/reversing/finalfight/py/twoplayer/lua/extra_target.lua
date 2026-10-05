-- extra_target.lua: per frame log of every live pool-2 fighter's target fields and both players' x and state (FFD_TLOG). Returned function is called by bot2p.lua.
local f_ = io.open(os.getenv("FFD_TLOG") or (os.getenv("FF_OUT") .. "/target.log"), "w")
local seenh = {}
return function(f, L, bots)
  local m = L.mem
  local lo = tonumber(os.getenv("FFD_TLO") or "0")
  if f < lo then return end
  for i = 0, 12 do
    local a = 0xff86e8 + 0xc0 * i
    if m:read_u8(a) ~= 0 and m:read_u8(a) < 0x80 then
      f_:write(string.format("T %d rec=%d k=%d ch=%d st=%02x%02x x=%04x y=%04x t144=%04x t148=%04x c150=%04x t134=%08x hp=%04x\n", f, i, m:read_u8(a + 19), m:read_u8(a + 20), m:read_u8(a + 2), m:read_u8(a + 3),
        m:read_u16(a + 6), m:read_u16(a + 14), m:read_u16(a + 144), m:read_u16(a + 148), m:read_u16(a + 150), m:read_u32(a + 134), m:read_u16(a + 24)))
    end
  end
  for _, pl in ipairs({ { "2", 0xff86e8, 13 }, { "4", 0xff9528, 8 } }) do
    for i = 0, pl[3] - 1 do
      local a = pl[2] + 0xc0 * i
      local alive = m:read_u8(a) ~= 0 and m:read_u8(a) < 0x80 and m:read_u8(a + 2) == 2
      if alive and not seenh[a] then
        seenh[a] = true
        f_:write(string.format("H %d pool=%s rec=%d k=%d ch=%d ent=%d lvl=%d hp=%04x h26=%04x h28=%04x def64=%02x p92=%06x 127=%02x 21610=%02x rank=%04x\n", f, pl[1], i, m:read_u8(a + 19), m:read_u8(a + 20), m:read_u8(a + 21), m:read_u8(a + 96),
          m:read_u16(a + 24), m:read_u16(a + 26), m:read_u16(a + 28), m:read_u8(a + 64), m:read_u32(a + 92) & 0xffffff, m:read_u8(0xff8000 + 127), m:read_u8(0xff8000 + 21610), m:read_u16(0xff8000 + 168)))
      elseif not alive then seenh[a] = nil end
    end
  end
  f_:write(string.format("G %d tok=%04x rank=%04x m127=%02x m21610=%02x alive012=%04x\n", f, m:read_u16(0xff115a), m:read_u16(0xff8000 + 168), m:read_u8(0xff8000 + 127), m:read_u8(0xff8000 + 21610), m:read_u16(0xff1154)))
  f_:write(string.format("P %d p1 %d x=%04x y=%04x st=%02x%02x p2 %d x=%04x y=%04x st=%02x%02x\n", f, m:read_u8(0xff8568), m:read_u16(0xff856e), m:read_u16(0xff8576), m:read_u8(0xff856a), m:read_u8(0xff856b),
    m:read_u8(0xff8628), m:read_u16(0xff862e), m:read_u16(0xff8636), m:read_u8(0xff862a), m:read_u8(0xff862b)))
end
