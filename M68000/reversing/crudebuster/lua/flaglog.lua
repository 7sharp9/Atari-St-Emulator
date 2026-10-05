-- flaglog.lua: log every change of the kernel flag bytes ($80000-$8005f) per frame, with a plan of inputs.
--   CB_PLAN, CB_STOP, CB_OUT (writes flaglog.txt), CB_LO/CB_HI address range (default 80000-8005f)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local sched = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "9000")
local lo = tonumber(os.getenv("CB_LO") or "80000", 16)
local hi = tonumber(os.getenv("CB_HI") or "8005f", 16)
local out = io.open((os.getenv("CB_OUT") or ".") .. "/flaglog.txt", "w")
local prev = {}
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  local line = {}
  for a = lo, hi do
    local v = L.mem:read_u8(a)
    if prev[a] ~= v then
      if prev[a] ~= nil then line[#line + 1] = string.format("%x:%02x>%02x", a, prev[a], v) end
      prev[a] = v
    end
  end
  if #line > 0 then out:write(string.format("%d %s\n", f, table.concat(line, " "))) end
  if f >= stop then out:close(); manager.machine:exit() end
end)
