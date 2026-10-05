-- hide.lua: load FF_LOAD state, run FF_HIDE_PRE frames, zero the in-use byte (+0) of the records in FF_HIDE (comma list of hex record addresses),
-- run FF_HIDE_F more frames, snapshot FF_HIDE_SHOT (png name) and exit. A record whose handler is not called draws no sprite, so the pixels that
-- differ from the run without FF_HIDE are that record's sprite. With FF_HIDE empty it takes the reference picture.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local pre = tonumber(os.getenv("FF_HIDE_PRE") or "2")
local post = tonumber(os.getenv("FF_HIDE_F") or "3")
local n = 0
local f0
emu.register_frame_done(function()
  n = n + 1
  if n < 3 then return end
  local f = L.frame()
  if n < 8 then print('hide cb', n, f) end
  if not f0 then f0 = f end
  if f == f0 + pre then
    if os.getenv("FF_HIDE_PRINT") then
      for i = 0, 29 do local a = 0xff9b28 + 0xc0 * i
        if m:read_u8(a) ~= 0 then print(string.format("P8 rec=%d %06x b0=%02x st=%02x%02x kind=%02x +20=%02x +21=%02x x=%04x y=%04x", i, a, m:read_u8(a), m:read_u8(a+2), m:read_u8(a+3), m:read_u8(a+19), m:read_u8(a+20), m:read_u8(a+21), m:read_u16(a+6), m:read_u16(a+10))) end end
    end
    for a in string.gmatch(os.getenv("FF_HIDE") or "", "(%x+)") do m:write_u8(tonumber(a, 16), 0) end
  end
  if f == f0 + pre + post then
    L.screen:snapshot(os.getenv("FF_HIDE_SHOT") or "hide.png")
    manager.machine:exit()
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
