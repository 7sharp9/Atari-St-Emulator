-- clearpoke.lua: load state CB_LOAD (frame 1), at frame CB_POKE set $80040 bit 4 (level cleared), log flags/level and screenshots.
--   env: CB_LOAD, CB_POKE (frame after load), CB_STOP, CB_SHOTS lo:hi:step, CB_OUT, CB_ADDRS (framelog style)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local poke = tonumber(os.getenv("CB_POKE") or "30")
local unpoke = tonumber(os.getenv("CB_UNPOKE") or "-1")
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local addrs = {}
for a, w in (os.getenv("CB_ADDRS") or "80046:b,80040:b,80041:b,80016:w,804ae:w,8004a:w"):gmatch("(%x+):(%a)") do addrs[#addrs + 1] = { tonumber(a, 16), w } end
local out = io.open((os.getenv("CB_OUT") or ".") .. "/clearpoke.csv", "w")
local loaded, f0 = false, nil
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_LOAD")); return end
  if not f0 then f0 = f end
  local r = f - f0
  if r == poke then m:write_u8(0x80040, m:read_u8(0x80040) | 0x10) end
  if r == unpoke then m:write_u8(0x80040, m:read_u8(0x80040) & 0xef) end
  local t = { tostring(r) }
  for _, x in ipairs(addrs) do
    local v = (x[2] == "b" and m:read_u8(x[1])) or (x[2] == "w" and m:read_u16(x[1])) or m:read_u32(x[1])
    t[#t + 1] = string.format("%x", v)
  end
  out:write(table.concat(t, ","), "\n")
  if r >= slo and r <= shi and (r - slo) % sst == 0 then L.screen:snapshot(string.format("c%05d.png", r)) end
  if r >= stop then out:close(); manager.machine:exit() end
end)
