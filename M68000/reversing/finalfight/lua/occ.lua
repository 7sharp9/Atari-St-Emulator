-- occ.lua: per-frame occupancy of the arrays the $5668 callees walk (record in use = byte 0 non-zero).
-- Arrays: P players(2x192 @1384) B pool2(13x192 @1768) C pool6(6x192 @4264) D pool4(8x192 @5416) E pool8(30x192 @6952)
--  S specials(@12712,12776,12840 x64) G (16x192 @13032) H (10x192 @16104) I (30x64 @18024) J (45 groups: word+long @19944 -> 6x64 records)
-- Line: "f=<frame> <arr><idx>:b18/b19/b2/b3 ..." for records with byte0 != 0.  FF_OCC_OUT; walk Right from FF_WALK_LO, Button 1 pulses
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_OCC_OUT") or "occ.txt", "w"))
local m = L.mem
local lo = tonumber(os.getenv("FF_WALK_LO") or "2480")
local A5 = 0xff8000
local arrs = {
  { "P", 1384, 2, 192 }, { "B", 1768, 13, 192 }, { "C", 4264, 6, 192 }, { "D", 5416, 8, 192 }, { "E", 6952, 30, 192 },
  { "S", 12712, 3, 64 }, { "G", 13032, 16, 192 }, { "H", 16104, 10, 192 }, { "I", 18024, 30, 64 },
}
emu.register_frame_done(function()
  local f = L.frame()
  L.F.right:set_value((f >= lo) and 1 or 0)
  L.F.b1:set_value((f >= lo and f % 40 < 4) and 1 or 0)
  if f < 2201 then return end
  local t = {}
  for _, a in ipairs(arrs) do
    for i = 0, a[3] - 1 do
      local base = A5 + a[2] + i * a[4]
      if m:read_u8(base) ~= 0 then
        t[#t + 1] = string.format("%s%d:%02x/%02x/%02x/%02x", a[1], i, m:read_u8(base + 18), m:read_u8(base + 19), m:read_u8(base + 2), m:read_u8(base + 3))
      end
    end
  end
  for g = 0, 44 do
    local e = A5 + 19944 + 6 * g
    local w, p = m:read_u16(e), m:read_u32(e + 2) & 0xffffff
    if w < 0x8000 or true then
      for i = 0, 5 do
        local base = p + 64 * i
        if base >= 0xff0000 and m:read_u8(base) ~= 0 then
          t[#t + 1] = string.format("J%d.%d:w%04x/%02x/%02x/%02x/%02x", g, i, w, m:read_u8(base + 18), m:read_u8(base + 19), m:read_u8(base + 2), m:read_u8(base + 3))
        end
      end
    end
  end
  out:write(string.format("f=%d %s\n", f, table.concat(t, " ")))
  if f % 200 == 0 then out:flush() end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
