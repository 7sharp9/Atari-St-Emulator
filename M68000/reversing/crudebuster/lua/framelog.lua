-- framelog.lua: one CSV line per frame of chosen RAM words/bytes.
--   CB_PLAN, CB_STOP, CB_OUT (framelog.csv), CB_ADDRS "80002:b,8004a:w,8040a:w,..." (b byte, w word, l long)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local sched = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local addrs = {}
for a, w in (os.getenv("CB_ADDRS") or ""):gmatch("(%x+):(%a)") do addrs[#addrs + 1] = { tonumber(a, 16), w } end
local out = io.open((os.getenv("CB_OUT") or ".") .. "/framelog.csv", "w")
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  local t = { tostring(f) }
  for _, x in ipairs(addrs) do
    local v = (x[2] == "b" and L.mem:read_u8(x[1])) or (x[2] == "w" and L.mem:read_u16(x[1])) or L.mem:read_u32(x[1])
    t[#t + 1] = string.format("%x", v)
  end
  out:write(table.concat(t, ","), "\n")
  if f >= stop then out:close(); manager.machine:exit() end
end)
