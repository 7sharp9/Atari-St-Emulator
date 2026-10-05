-- probe_credit.lua: log credits 76(A5) and the join mask 127(A5) every 10 frames from 1090 (FFD_SCHED = coin / start schedule)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local sched = dofile(os.getenv("FFD_SCHED"))
local log = io.open(os.getenv("FFD_LOG"), "w")
emu.register_frame_done(function()
  local f = L.frame()
  L.apply(sched, f)
  if f >= 1090 and f % 10 == 0 then log:write(string.format("%d cred76=%04x m127=%02x n21616=%04x\n", f, m:read_u16(0xff8000 + 76), m:read_u8(0xff8000 + 127), m:read_u16(0xff8000 + 21616))); log:flush() end
  if f >= 1260 then log:close(); manager.machine:exit() end
end)
