-- fieldtap.lua: write taps over the whole object array ($ff8568..$ffb227) logging only chosen record-field byte ranges
--   FF_FIELDS="24-29,44-45,60-61"  (record offsets, inclusive)   FF_TAP_OUT   FF_TAP_LO/HI frame window
-- Line: "f=<frame> pc=<CURPC> i=<record index> o=<record offset> m=<mask> d=<data>"  (16-bit bus: o is the even offset)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local lo = tonumber(os.getenv("FF_TAP_LO") or "0")
local hi = tonumber(os.getenv("FF_TAP_HI") or "99999")
local fh = assert(io.open(os.getenv("FF_TAP_OUT") or (os.getenv("FF_OUT") .. "/ftap.txt"), "w"))
local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
local ranges = {}
for a, b in string.gmatch(os.getenv("FF_FIELDS") or "24-29", "(%d+)-(%d+)") do ranges[#ranges + 1] = { tonumber(a), tonumber(b) } end
local BASE, SZ = 0xff8568, 0xc0
local function want(o) for _, r in ipairs(ranges) do if o >= r[1] and o <= r[2] then return true end end return false end
arr_tap = L.mem:install_write_tap(BASE, BASE + SZ * 60 - 1, "arr", function(offset, data, mask)
  local rel = offset - BASE
  local o = rel % SZ
  if not want(o) and not want(o + 1) then return end
  local fr = L.frame()
  if fr < lo or fr > hi then return end
  fh:write(string.format("f=%d pc=%06x i=%d o=%d m=%04x d=%04x\n", fr, pcreg.value, rel // SZ, o, mask, data))
end)
emu.register_frame_done(function() if L.frame() >= hi then fh:flush() end end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
