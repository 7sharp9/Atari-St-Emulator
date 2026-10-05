-- reclog.lua: start level CB_LEVEL (as startlevel.lua), play CB_PLAN, log RAM regions every frame.
--   env: CB_DIR (reversing/crudebuster/lua), CB_LEVEL, CB_PLAN, CB_STOP, CB_OUT (dir), CB_REGIONS "80100:80,80180:80" (hex addr:len bytes),
--        CB_LOAD state name (in $CB_RUN/sta/cbuster) loaded at frame 1; then CB_PLAN/CB_SPAWNS/CB_FROM/CB_STOP frames are emulator frames (about 2 + n)
--        CB_SPAWNSB like CB_SPAWNS for pool B props (first free record 0..23)
--        CB_FROM first frame to log (default 700), CB_POKES "addr:val:size,..." applied every frame (e.g. god mode)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local plan = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local from = tonumber(os.getenv("CB_FROM") or "700")
local regs = {}
for a, n in (os.getenv("CB_REGIONS") or "80100:80"):gmatch("(%x+):(%x+)") do regs[#regs + 1] = { tonumber(a, 16), tonumber(n, 16) } end
local pokes = {}
for a, v, s in (os.getenv("CB_POKES") or ""):gmatch("(%x+):(%x+):(%a)") do pokes[#pokes + 1] = { tonumber(a, 16), tonumber(v, 16), s } end
local spawns = {}
for fr, ty, va, xs, ys in (os.getenv("CB_SPAWNS") or ""):gmatch("(%d+):(%x+):(%x+):(%w+):(%w+)") do spawns[#spawns + 1] = { tonumber(fr), tonumber(ty, 16), tonumber(va, 16), xs, ys } end
local spawnsB = {}
for fr, ty, va, xs, ys in (os.getenv("CB_SPAWNSB") or ""):gmatch("(%d+):(%x+):(%x+):(%w+):(%w+)") do spawnsB[#spawnsB + 1] = { tonumber(fr), tonumber(ty, 16), tonumber(va, 16), xs, ys } end
local cpu = manager.machine.devices[":maincpu"]
taps = {}
taps[1] = L.mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
-- CB_TAPS "addr:len,addr:len" (hex): log every 68000 byte write into those ranges: frame pc addr old new  (only bytes the write actually covers)
local tapout = io.open((os.getenv("CB_OUT") or ".") .. "/taps.txt", "w")
for a, n in (os.getenv("CB_TAPS") or ""):gmatch("(%x+):(%x+)") do
  a = tonumber(a, 16); n = tonumber(n, 16)
  local lo, hi = a, a + n - 1
  taps[#taps + 1] = L.mem:install_write_tap(lo & ~1, hi | 1, "t" .. a, function(off, data, mask)
    local w = off & ~1
    local pc = cpu.state["CURPC"].value
    if pc >= 0xbbe and pc < 0xbd4 then return end -- frame_done pokes of this script happen in the main-loop wait
    if mask & 0xff00 ~= 0 and w >= lo and w <= hi then
      tapout:write(string.format("%d %06x %06x %02x %02x\n", L.frame(), pc, w, L.mem:read_u8(w), (data >> 8) & 0xff))
    end
    if mask & 0x00ff ~= 0 and w + 1 >= lo and w + 1 <= hi then
      tapout:write(string.format("%d %06x %06x %02x %02x\n", L.frame(), pc, w + 1, L.mem:read_u8(w + 1), data & 0xff))
    end
  end)
end
-- CB_FA10=1: log every call of the enemy-melee test $fa10 (entry: the first table read of $fbdc): frame, A6 record (32 bytes), player +0..+127 head, and a HIT line when the health writer $fc9e fires
local calls
if os.getenv("CB_FA10") == "1" then
  calls = io.open((os.getenv("CB_OUT") or ".") .. "/calls.txt", "w")
  taps[#taps + 1] = L.mem:install_read_tap(0x69000, 0x69fff, "fa10", function(off, data, mask)
    local pc = cpu.state["CURPC"].value
    if pc < 0xfbdc or pc > 0xfbf4 or off ~= 0x69000 + 4 * L.mem:read_u8(cpu.state["A6"].value + 2) then return end
    local a6 = cpu.state["A6"].value
    local r = {}
    for k = 0, 31 do r[#r + 1] = string.format("%02x", L.mem:read_u8(a6 + k)) end
    local p = {}
    for k = 0, 127 do p[#p + 1] = string.format("%02x", L.mem:read_u8(0x80100 + k)) end
    calls:write(string.format("CALL %d %06x %s %s\n", L.frame(), a6, table.concat(r), table.concat(p)))
  end)
  taps[#taps + 1] = L.mem:install_write_tap(0x80112, 0x80113, "hit", function(off, data, mask)
    if cpu.state["CURPC"].value == 0xfc9e then calls:write(string.format("HIT %d\n", L.frame())) end
  end)
end
local out = io.open((os.getenv("CB_OUT") or ".") .. "/reclog.txt", "w")
local loaded = false
emu.register_frame_done(function()
  local f = L.frame()
  if os.getenv("CB_LOAD") then
    if not loaded then loaded = true; manager.machine:load(os.getenv("CB_LOAD")); return end
  end
  if os.getenv("CB_LOAD") then -- plan frames are counted from the load
  elseif f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  for _, e in ipairs(plan) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  for _, sp in ipairs(spawns) do
    if sp[1] == f then -- spawn into the first free pool A record; x: "pN" = player x + N (N signed decimal), else hex; y: "q" = player y word, else hex
      local px = L.mem:read_u16(0x80108)
      local x = sp[4]:sub(1, 1) == "p" and (px + tonumber(sp[4]:sub(2))) or tonumber(sp[4], 16)
      local y = sp[5] == "q" and L.mem:read_u16(0x8010c) or tonumber(sp[5], 16)
      for i = 0, 15 do
        local a = 0x81000 + i * 0x40
        if L.mem:read_u8(a) & 0x80 == 0 then
          L.mem:write_u8(a, 0x80); L.mem:write_u8(a + 2, sp[2]); L.mem:write_u8(a + 16, sp[3])
          L.mem:write_u16(a + 8, x & 0xffff); L.mem:write_u16(a + 12, y & 0xffff)
          break
        end
      end
    end
  end
  for _, sp in ipairs(spawnsB) do -- same as CB_SPAWNS but into pool B ($81400, 32 records)
    if sp[1] == f then
      local px = L.mem:read_u16(0x80108)
      local x = sp[4]:sub(1, 1) == "p" and (px + tonumber(sp[4]:sub(2))) or tonumber(sp[4], 16)
      local y = sp[5] == "q" and L.mem:read_u16(0x8010c) or tonumber(sp[5], 16)
      for i = 0, 23 do
        local a = 0x81400 + i * 0x40
        if L.mem:read_u8(a) & 0x80 == 0 then
          L.mem:write_u8(a, 0x80); L.mem:write_u8(a + 2, sp[2]); L.mem:write_u8(a + 16, sp[3])
          L.mem:write_u16(a + 8, x & 0xffff); L.mem:write_u16(a + 12, y & 0xffff)
          break
        end
      end
    end
  end
  if f >= from then
    for _, p in ipairs(pokes) do
      if p[3] == "b" then L.mem:write_u8(p[1], p[2]) elseif p[3] == "w" then L.mem:write_u16(p[1], p[2]) else L.mem:write_u32(p[1], p[2]) end
    end
    local t = { tostring(f) }
    for _, r in ipairs(regs) do
      local s = {}
      for a = r[1], r[1] + r[2] - 1 do s[#s + 1] = string.format("%02x", L.mem:read_u8(a)) end
      t[#t + 1] = table.concat(s)
    end
    out:write(table.concat(t, " "), "\n")
  end
  if f >= stop then out:close(); tapout:close(); if calls then calls:close() end manager.machine:exit() end
end)
