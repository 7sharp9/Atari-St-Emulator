-- tapbot.lua: write taps (FF_W="lo-hi,..." even/odd word ranges) logging "f=<frame> pc=<pc> a=<addr> m=<mask> d=<data>" to FF_TAP_OUT, then runs stagebot.lua
-- (so FF_LOAD / FF_BOT_* / FF_PLAN apply as in py/stage/run.sh). Needs FF_DIR (reversing/finalfight/lua).
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local lo = tonumber(os.getenv("FF_TAP_LO") or "0")
local hi = tonumber(os.getenv("FF_TAP_HI") or "99999999")
local fh = assert(io.open(os.getenv("FF_TAP_OUT"), "w"))
local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
taps = {}
for a, b in string.gmatch(os.getenv("FF_W") or "", "(%x+)-(%x+)") do
  local f = function(offset, data, mask)
    local fr = L.frame()
    if fr >= lo and fr <= hi then fh:write(string.format("f=%d pc=%06x a=%06x m=%04x d=%04x\n", fr, pcreg.value, offset, mask, data)) end
  end
  taps[#taps + 1] = L.mem:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, f)
end
local n = 0
emu.register_frame_done(function() n = n + 1; if n % 600 == 0 then fh:flush() end end)
dofile(os.getenv("FF_DIR") .. "/stagebot.lua")
