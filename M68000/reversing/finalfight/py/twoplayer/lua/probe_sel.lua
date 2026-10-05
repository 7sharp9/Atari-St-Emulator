-- probe_sel.lua: cold boot with FFD_SCHED, log both player records' +20 and +0 every 20 frames from 1200 (select-screen outcome)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local sched = dofile(os.getenv("FFD_SCHED"))
local log = io.open(os.getenv("FFD_LOG"), "w")
emu.register_frame_done(function()
  local f = L.frame()
  L.apply(sched, f)
  if f >= 1200 and f % 20 == 0 then
    log:write(string.format("%d P1 b0=%02x ch=%02x st=%02x%02x | P2 b0=%02x ch=%02x st=%02x%02x\n", f, m:read_u8(0xff8568), m:read_u8(0xff857c), m:read_u8(0xff856a), m:read_u8(0xff856b), m:read_u8(0xff8628), m:read_u8(0xff863c), m:read_u8(0xff862a), m:read_u8(0xff862b)))
    log:flush()
  end
  if f >= 1420 then log:close(); manager.machine:exit() end
end)
