-- census.lua: start level CB_LEVEL (like startlevel.lua), drive a chase-and-punch bot with god mode, and log
--   S  f pool slot <hex of the record>        activation (record+0 bit 7 went 0 -> 1)   (pool A, B, C)
--   D  f pool slot x y                        deactivation
--   F  f  <addr:old>new ...                   changes of flag cells $80000-$8005f (except frame counter/input)
--   V  f  lvl sx sy p1x p1y hp                every 30 frames
--   Q  f  addr:old>new ...                    changes in the player records $80100-$8017f and $80180-$801ff
-- env: CB_LEVEL, CB_STOP, CB_OUT, CB_GOD=1, CB_BOT=1, CB_SHOTS "lo:hi:step", CB_SNAP_NEW=1 (screenshot 3 frames after
--      the first activation of each pool B/C type), CB_NOSTART=1 (do not insert coin/start), CB_SAVE/CB_SAVE_FRAME
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "4000")
local outdir = os.getenv("CB_OUT") or "."
local out = io.open(outdir .. "/census_l" .. want .. ".txt", "w")
local m = L.mem
local cpu = manager.machine.devices[":maincpu"]
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc == 0x146e + 6 or (pc >= 0x1400 and pc < 0x1480) then
    return (data & 0xff) ~= data and data or ((want << 8) | want)
  end
end)
-- CB_TAPS "80400-80402,8040a-8040d": log every write (frame, pc, addr, data) between CB_TAPLO and CB_TAPHI frames
local tapf = {}
local tlo, thi = tonumber(os.getenv("CB_TAPLO") or "0"), tonumber(os.getenv("CB_TAPHI") or "99999")
for lo, hi in (os.getenv("CB_TAPS") or ""):gmatch("(%x+)-(%x+)") do
  local a, b = tonumber(lo, 16), tonumber(hi, 16)
  taps[#taps + 1] = m:install_write_tap(a, b, "t" .. lo, function(off, data, mask)
    local f = L.frame()
    if f >= tlo and f <= thi then out:write(string.format("T %d pc=%06x a=%x d=%04x m=%04x\n", f, cpu.state["CURPC"].value, off, data & 0xffff, mask & 0xffff)) end
  end)
end
local pools = { {0x81000, 0x40, 16, "A"}, {0x81400, 0x40, 32, "B"}, {0x81c00, 0x20, 8, "C"} }
local dump = {}
for n in (os.getenv("CB_DUMP") or ""):gmatch("%d+") do dump[tonumber(n)] = true end
local act, seen, pend = {}, {}, {}
for p = 1, 3 do act[p] = {} for i = 0, pools[p][3] - 1 do act[p][i] = false end end
local prevflag, prevq = {}, {}
local mode = 0
local function setf(name, v) L.F[name]:set_value(v) end
local bot = os.getenv("CB_BOT") ~= "0"
local god = os.getenv("CB_GOD") ~= "0"
local k, stuck, lastsx = 0, 0, -1
emu.register_frame_done(function()
  local f = L.frame()
  if not os.getenv("CB_NOSTART") then
    if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
    elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  end
  -- bot
  if bot and f > 760 and (m:read_u8(0x80040) & 0x80) ~= 0 then
    local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
    local best, bd = nil, 1e9
    for i = 0, 15 do
      local b = 0x81000 + 0x40 * i
      local t = m:read_u8(b + 2)
      if (m:read_u8(b) & 0x80) ~= 0 and t ~= 0xff then
        local ex, ey = m:read_u16(b + 8), m:read_u16(b + 12)
        local d = math.abs(ex - px) + 2 * math.abs(ey - py)
        if d < bd then bd, best = d, {ex, ey} end
      end
    end
    local r, l, u, d, b1 = 0, 0, 0, 0, 0
    if best then
      local dx, dy = best[1] - px, best[2] - py
      if math.abs(dy) > 6 then if dy < 0 then u = 1 else d = 1 end end
      if math.abs(dx) > 44 then if dx > 0 then r = 1 else l = 1 end
      elseif math.abs(dy) <= 10 then
        -- face the enemy: step toward it one frame in four, otherwise attack
        if k % 4 == 0 then if dx > 0 then r = 1 else l = 1 end end
        if k % 8 < 3 then b1 = 1 end
      end
    else
      r = 1
      -- stuck behind a lock with nothing to fight: pulse attack (picks up / throws objects)
      if stuck > 90 and k % 24 < 4 then b1 = 1 end
    end
    if best and stuck > 60 and k % 16 < 4 then b1 = 1 end
    local sx = m:read_u16(0x8040a)
    if sx == lastsx then stuck = stuck + 1 else stuck = 0; lastsx = sx end
    k = k + 1
    setf("right", r); setf("left", l); setf("up", u); setf("down", d); setf("b1", b1)
  end
  if god and f > 760 then
    if (m:read_u8(0x80100) & 0x80) ~= 0 then m:write_u8(0x80113, 0x38) end
  end
  -- pools
  for p = 1, 3 do
    local base, stride, n, nm = table.unpack(pools[p])
    for i = 0, n - 1 do
      local a = base + stride * i
      local on = (m:read_u8(a) & 0x80) ~= 0
      if on and not act[p][i] then
        local t = {}
        for q = 0, stride - 1 do t[#t + 1] = string.format("%02x", m:read_u8(a + q)) end
        out:write(string.format("S %d %s %d %s\n", f, nm, i, table.concat(t)))
        if os.getenv("CB_SNAP_NEW") and p > 1 then
          local key = nm .. m:read_u8(a + 2)
          if not seen[key] then seen[key] = true; pend[#pend + 1] = { f + 3, key } end
        end
      elseif (not on) and act[p][i] then
        out:write(string.format("D %d %s %d %04x %04x\n", f, nm, i, m:read_u16(a + 8), m:read_u16(a + 12)))
      end
      act[p][i] = on
    end
  end
  for j = #pend, 1, -1 do
    if pend[j][1] <= f then L.screen:snapshot(string.format("new_l%d_%s_f%05d.png", want, pend[j][2], f)); table.remove(pend, j) end
  end
  -- flags and player diffs
  local line = {}
  for a = 0x80000, 0x8005f do
    if a < 0x8004a or a > 0x8004b then
      local v = m:read_u8(a)
      if prevflag[a] ~= v then if prevflag[a] ~= nil and not (a >= 0x80050 and a <= 0x80053) then line[#line + 1] = string.format("%x:%02x>%02x", a, prevflag[a], v) end prevflag[a] = v end
    end
  end
  if #line > 0 then out:write(string.format("F %d %s\n", f, table.concat(line, " "))) end
  line = {}
  for a = 0x80100, 0x801ff do
    local v = m:read_u8(a)
    if prevq[a] ~= v then if prevq[a] ~= nil then line[#line + 1] = string.format("%x:%02x>%02x", a, prevq[a], v) end prevq[a] = v end
  end
  if #line > 0 then out:write(string.format("Q %d %s\n", f, table.concat(line, " "))) end
  if f % 30 == 0 then
    out:write(string.format("V %d lvl=%d st=%02x%02x sx=%04x sy=%04x p1x=%04x p1y=%04x hp=%02x\n", f, m:read_u8(0x80046), m:read_u8(0x80040), m:read_u8(0x80041), m:read_u16(0x8040a), m:read_u16(0x80406), m:read_u16(0x80108), m:read_u16(0x8010c), m:read_u8(0x80113)))
  end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("l%d_%05d.png", want, f)) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if dump[f] then L.write(string.format("%s/ram_l%d_%05d.bin", outdir, want, f), L.ram()) end
  if f >= stop then out:close(); manager.machine:exit() end
end)
