-- FFD_EXTRA: log, every frame in FFD_JLO..FFD_JHI (default all), the join-related globals into FFD_TLOG
local f_ = io.open(os.getenv("FFD_TLOG"), "w")
local lo, hi = tonumber(os.getenv("FFD_JLO") or "0"), tonumber(os.getenv("FFD_JHI") or "99999")
return function(f, L, bots)
  if f < lo or f > hi then return end
  local m = L.mem
  local A5 = 0xff8000
  local P2 = 0xff8628
  f_:write(string.format("%d m127=%02x m21610=%02x cred76=%04x rank168=%04x ctr276=%04x rank172=%04x TIME175=%02x ctr176=%04x n21616=%04x n21628=%04x P1=%02x%02x%02x P2[b0=%02x b1=%02x st=%02x sub=%02x ss=%02x ch=%02x x=%04x gy=%04x hp=%04x lv=%02x b129=%02x] 21417=%02x 130A5=%02x\n",
    f, m:read_u8(A5 + 127), m:read_u8(A5 + 21610), m:read_u16(A5 + 76), m:read_u16(A5 + 168), m:read_u16(A5 + 276), m:read_u16(A5 + 172), m:read_u8(A5 + 175), m:read_u16(A5 + 176),
    m:read_u16(A5 + 21616), m:read_u16(A5 + 21628), m:read_u8(0xff8568), m:read_u8(0xff856a), m:read_u8(0xff856b),
    m:read_u8(P2), m:read_u8(P2 + 1), m:read_u8(P2 + 2), m:read_u8(P2 + 3), m:read_u8(P2 + 4), m:read_u8(P2 + 20), m:read_u16(P2 + 6), m:read_u16(P2 + 14), m:read_u16(P2 + 24), m:read_u8(P2 + 128), m:read_u8(P2 + 129),
    m:read_u8(A5 + 21417), m:read_u8(A5 + 130)))
  f_:flush()
end
