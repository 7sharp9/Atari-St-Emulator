-- hudpoke.lua: load FF_LOAD, then push the record FF_POKE_REC (hex address) into P1's enemy-bar ring exactly as $28d0 does
-- ({record ptr, +24, +26, +28} at 644(A5) + 900(A5), index += 8 & $7f) and screenshot FF_POKE_SHOT after FF_POKE_F frames.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local n, f0 = 0, nil
local rec = tonumber(os.getenv("FF_POKE_REC"), 16)
local post = tonumber(os.getenv("FF_POKE_F") or "10")
emu.register_frame_done(function()
  n = n + 1
  if n < 3 then return end
  local f = L.frame()
  if not f0 then f0 = f end
  if f == f0 + 1 then
    local wi = m:read_u16(0xff8000 + 900)
    local e = 0xff8000 + 644 + wi
    m:write_u16(e, rec & 0xffff); m:write_u16(e + 2, m:read_u16(rec + 24)); m:write_u16(e + 4, m:read_u16(rec + 26)); m:write_u16(e + 6, m:read_u16(rec + 28))
    m:write_u16(0xff8000 + 900, (wi + 8) & 0x7f)
  end
  if f == f0 + 1 + post then
    L.screen:snapshot(os.getenv("FF_POKE_SHOT") or "poke.png")
    manager.machine:exit()
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
