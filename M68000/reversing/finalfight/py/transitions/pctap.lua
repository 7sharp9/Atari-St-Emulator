-- pctap.lua: write/read taps on address ranges with the writing PC, riding on stagebot.lua (bot plays).
--   FF_PT_W="ff8412-ff8413,..." write taps   FF_PT_R="..." read taps   FF_PT_LO/HI frame window   FF_PT_OUT file
-- Line: "w|r f pc a mask data" (a = word-aligned bus address; mask 00ff = low byte = a+1, ff00 = high byte = a)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local lo, hi = tonumber(os.getenv("FF_PT_LO") or "0"), tonumber(os.getenv("FF_PT_HI") or "99999")
local fh = assert(io.open(os.getenv("FF_PT_OUT") or (os.getenv("FF_OUT") .. "/pt.log"), "w"))
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
taps = {}
for kind, env in pairs({ w = "FF_PT_W", r = "FF_PT_R" }) do
  for a, b in string.gmatch(os.getenv(env) or "", "(%x+)-(%x+)") do
    local f = function(off, data, mask)
      local fr = L.frame()
      if fr < lo or fr > hi then return end
      local ok, e = pcall(function() fh:write(string.format("%s %d %06x %06x %04x %04x\n", kind, fr, pcreg.value, off, mask, data)) end)
      if not ok then print("TAP ERR " .. tostring(e)) end
    end
    if kind == "w" then taps[#taps + 1] = L.mem:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, f)
    else taps[#taps + 1] = L.mem:install_read_tap(tonumber(a, 16), tonumber(b, 16), "r" .. a, f) end
  end
end
emu.register_frame_done(function() if L.frame() % 50 == 0 then fh:flush() end end)
dofile(os.getenv("FF_DIR") .. "/stagebot.lua")
