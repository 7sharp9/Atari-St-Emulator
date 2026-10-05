-- htap.lua: log every call of the overlap test $7932 (via a write tap on its scratch words) and every write to a
-- record's +60 word ("hit by" pointer) / +24 health word, then run ffdrive.lua (FF_LOAD, FF_PLAN, ...).
--   $7956 writes dx to -28198(A5)=$ff11da on every call; $7978 writes dy to -28194(A5)=$ff11de only if the x axis passed.
-- Lines:  X f= i1= i3= a0= box1= box2= cx1= cx3= hw1= hw2= dx=       (x axis)
--         Y f= dy= cy1= cy3= hh1= hh2=                              (y axis, follows its X line)
--         W f= pc= i= o= d=                                         (writes to +60/+24 of record i)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local lo = tonumber(os.getenv("FF_TAP_LO") or "0")
local hi = tonumber(os.getenv("FF_TAP_HI") or "99999")
local fh = assert(io.open(os.getenv("FF_TAP_OUT") or (os.getenv("FF_OUT") .. "/htap.txt"), "w"))
local cpu = manager.machine.devices[":maincpu"]
local st = cpu.state
local pcreg = st["CURPC"]
local m = L.mem
local BASE, SZ = 0xff8568, 0xc0
local function idx(a) local r = a - BASE; if r >= 0 and r < SZ * 60 and r % SZ == 0 then return r // SZ end return string.format("%06x", a) end
local function idx_of(a) return idx(a) end
local function reg(n) return st[n].value end
local function s16(v) v = v & 0xffff; if v >= 0x8000 then return v - 0x10000 end return v end
xtap = m:install_write_tap(0xff11da, 0xff11db, "x", function(offset, data, mask)
  local fr = L.frame(); if fr < lo or fr > hi or pcreg.value ~= 0x7956 then return end
  local a1, a3, a0, a2, a4 = reg("A1") & 0xffffff, reg("A3") & 0xffffff, reg("A0") & 0xffffff, reg("A2") & 0xffffff, reg("A4") & 0xffffff
  fh:write(string.format("X f=%d i1=%s i3=%s a0=%06x box1=%06x box2=%06x cx1=%d cx3=%d hw1=%d hw2=%d dx=%d att45=%02x att18=%02x vic44=%02x vic18=%02x\n",
    fr, tostring(idx(a1)), tostring(idx(a3)), a0, a2, a4, s16(m:read_u16(a0 + 4)), s16(m:read_u16(a3 + 124)),
    m:read_u16(a2 + 4), m:read_u16(a4 + 4), s16(reg("D3")), m:read_u8(a1 + 45), m:read_u8(a1 + 18), m:read_u8(a3 + 44), m:read_u8(a3 + 18)))
end)
ytap = m:install_write_tap(0xff11de, 0xff11df, "y", function(offset, data, mask)
  local fr = L.frame(); if fr < lo or fr > hi or pcreg.value ~= 0x7978 then return end
  local a1, a3, a0, a2, a4 = reg("A1") & 0xffffff, reg("A3") & 0xffffff, reg("A0") & 0xffffff, reg("A2") & 0xffffff, reg("A4") & 0xffffff
  fh:write(string.format("Y f=%d dy=%d cy1=%d cy3=%d hh1=%d hh2=%d\n", fr, s16(reg("D3")), s16(m:read_u16(a0 + 6)), s16(m:read_u16(a3 + 126)),
    m:read_u16(a2 + 6), m:read_u16(a4 + 6)))
end)
wtap = m:install_write_tap(BASE, 0xffcfff, "arr", function(offset, data, mask)
  local rel = offset - BASE; local o = rel % SZ
  local fr = L.frame(); if fr < lo or fr > hi then return end
  if rel < SZ * 60 then
    if not (o == 60 or o == 24 or o == 64) then return end
    fh:write(string.format("W f=%d pc=%06x i=%d o=%d d=%04x\n", fr, pcreg.value, rel // SZ, o, data))
    local pc = pcreg.value
    if o == 24 and (pc == 0x79fe or pc == 0x7a12) then -- damage subtract: log operands to re-derive D1 from the tables
      local a1, a2, a3 = reg("A1") & 0xffffff, reg("A2") & 0xffffff, reg("A3") & 0xffffff
      local tbl = (m:read_u32(a1 + 92)) & 0xffffff
      local idx = m:read_u16(a2 + 8)
      local base = m:read_u8(tbl + idx)
      local def = m:read_u8(a3 + 55)
      local scaled = base
      if pc == 0x79fe and def ~= 0 then scaled = m:read_u16(0xcea74 + (base << 6) + def * 2) end
      fh:write(string.format("D f=%d pc=%06x i3=%d i1=%s D1=%d tbl=%06x idx=%d base=%d def55=%d derived=%d\n", fr, pc, rel // SZ, tostring(idx_of(a1)), reg("D1") & 0xffff, tbl, idx, base, def, scaled))
    end
  else -- outside the $c0 array: log the absolute address, the checker matches it against victim base + 60/24
    fh:write(string.format("V f=%d pc=%06x a=%06x d=%04x\n", fr, pcreg.value, offset, data))
  end
end)
emu.register_frame_done(function() if L.frame() >= hi then fh:flush() end end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
