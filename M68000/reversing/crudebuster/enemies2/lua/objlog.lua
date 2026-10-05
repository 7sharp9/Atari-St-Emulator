-- objlog.lua: start level CB_LEVEL, optionally play it with a small bot, log every active pool A / B record each frame.
--   env: CB_DIR (reversing/crudebuster/lua), CB_LEVEL (0-5), CB_STOP (last frame), CB_OUT (dir; writes objlog.txt),
--        CB_BOT (0 = no input, 1 = walk right + attack nearest pool A record), CB_HP (1 = keep P1 health at its start value),
--        CB_SAVE/CB_SAVE_FRAME, CB_SHOTS "lo:hi:step", CB_POKES "frame:addr:byte,..." (hex addr, byte), CB_POOLB (1 = log pool B too)
--        CB_POOLC (1 = log pool C, 32-byte records, C lines)
--        CB_EHP (n>0: clamp every pool A record's health +5 to n each frame: census mode), CB_BOT 2 = unstick jumps, 3 = teleport bot, CB_YREL (hex y offset from the scroll y, levels 4/5), CB_LANEY (decimal y for the teleport bot between fights)
--        CB_X "addr:b|w|l,..." (hex addrs) appended to every F line
--        CB_W "lo-hi" (hex) + CB_WF0 first frame: log writes in that range as `W frame addr data mask pc=` lines
-- lines:  F <frame> lvl sx sy px py hp f40 f41 n   (n = active pool A count)
--         A <frame> <slot> <64 hex bytes>          pool A record ($81000 + $40 slot)
--         B <frame> <slot> <64 hex bytes>          pool B record ($81400 + $40 slot)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local bot = tonumber(os.getenv("CB_BOT") or "0")
local keephp = tonumber(os.getenv("CB_HP") or "1")
local ehp = tonumber(os.getenv("CB_EHP") or "0")
local xaddrs = {}
for a, w in (os.getenv("CB_X") or ""):gmatch("(%x+):(%a)") do xaddrs[#xaddrs + 1] = { tonumber(a, 16), w } end
local logb = tonumber(os.getenv("CB_POOLB") or "0")
local logc = tonumber(os.getenv("CB_POOLC") or "0")
local out = io.open((os.getenv("CB_OUT") or ".") .. "/objlog.txt", "w")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local pokes = {}
for f, a, b in (os.getenv("CB_POKES") or ""):gmatch("(%d+):(%x+):(%x+)") do pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), tonumber(b, 16) } end
local m = L.mem
local cpu = manager.machine.devices[":maincpu"]
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return (data & 0xff) ~= data and data or ((want << 8) | want) end
end)
local wlo, whi = (os.getenv("CB_W") or ""):match("(%x+)-(%x+)")
local wf0 = tonumber(os.getenv("CB_WF0") or "0")
if wlo then
  taps[2] = m:install_write_tap(tonumber(wlo, 16), tonumber(whi, 16), "w", function(off, data, mask)
    local f = L.frame()
    if f >= wf0 then out:write(string.format("W %d %06x %x %x pc=%06x\n", f, off, data, mask, cpu.state["CURPC"].value)) end
  end)
end
local hp0 = nil
local lastp, still, jumpfor = nil, 0, 0
local stall, stallck = 0, -1
local parkx = os.getenv("CB_PARK_AT") and tonumber(os.getenv("CB_PARK_AT"), 16)
local stallmax = tonumber(os.getenv("CB_STALL") or "400")
local atk_phase = 0
local function set(name, v) L.F[name]:set_value(v) end
local function bytes(base)
  local t = {}
  for k = 0, 0x3f do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end
  return table.concat(t)
end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then set("coin", 1) elseif f == 612 then set("coin", 0)
  elseif f == 700 then set("start1", 1) elseif f == 712 then set("start1", 0) end
  for _, p in ipairs(pokes) do if p[1] == f then m:write_u8(p[2], p[3]) end end
  local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
  local hp = m:read_u8(0x80113)
  local running = (m:read_u8(0x80040) & 0x80) ~= 0 and f > 720
  if running and hp0 == nil and hp > 0 then hp0 = hp end
  if running and keephp == 1 and hp0 then m:write_u8(0x80113, hp0) end
  if ehp > 0 then -- census mode: pool A records die from one hit (health clamp)
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 and m:read_u8(base + 5) > ehp and m:read_u8(base + 2) ~= 0x1b then m:write_u8(base + 5, ehp) end
    end
  end
  if os.getenv("CB_CLR81E03") == "1" and f >= 720 then m:write_u8(0x81e03, 0) end -- experiment: release the 'five or more enemies' scroll block before the next player update
  local n = 0
  for i = 0, 15 do
    local base = 0x81000 + 0x40 * i
    if (m:read_u8(base) & 0x80) ~= 0 then n = n + 1; out:write(string.format("A %d %d %s\n", f, i, bytes(base))) end
  end
  if logb == 1 then
    for i = 0, 31 do
      local base = 0x81400 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 then out:write(string.format("B %d %d %s\n", f, i, bytes(base))) end
    end
  end
  if logc == 1 then
    for i = 0, 7 do
      local base = 0x81c00 + 0x20 * i
      if (m:read_u8(base) & 0x80) ~= 0 then
        local t = {}
        for k = 0, 0x1f do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end
        out:write(string.format("C %d %d %s\n", f, i, table.concat(t)))
      end
    end
  end
  local xs = ""
  for _, x in ipairs(xaddrs) do
    local v = (x[2] == "b" and m:read_u8(x[1])) or (x[2] == "w" and m:read_u16(x[1])) or m:read_u32(x[1])
    xs = xs .. string.format(" %x", v)
  end
  out:write(string.format("F %d %d %04x %04x %04x %04x %02x %02x %02x %d%s\n", f, m:read_u8(0x80046), m:read_u16(0x8040a), m:read_u16(0x80406), px, py, hp, m:read_u8(0x80040), m:read_u8(0x80041), n, xs))
  if bot >= 1 and running then
    -- nearest pool A record
    local best, bd = nil, 1e9
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 then
        local ex, ey = m:read_u16(base + 8), m:read_u16(base + 12)
        local d = math.abs(ex - px) + 3 * math.abs(ey - py)
        if d < bd then best, bd = { ex, ey }, d end
      end
    end
    local l, r, u, d = 0, 0, 0, 0
    local hit = 0
    if best and bd < 400 then
      local dx, dy = best[1] - px, best[2] - py
      if dy < -4 then u = 1 elseif dy > 4 then d = 1 end
      if dx > 36 then r = 1 elseif dx < -36 then l = 1 end
      if math.abs(dx) < 56 and math.abs(dy) < 14 then
        if dx > 0 then r = 1 else l = 1 end
        atk_phase = (atk_phase + 1) % 8
        hit = atk_phase < 4 and 1 or 0
      end
    else
      r = 1
    end
    -- unstick: no player movement for 45 frames: jump right (b2) for 30 frames
    local key = px * 65536 + py
    if key == lastp then still = still + 1 else still = 0 end
    lastp = key
    if still >= 45 and bot >= 2 and jumpfor == 0 then jumpfor = 30; still = 0 end
    local jump = 0
    if jumpfor > 0 then jumpfor = jumpfor - 1; jump = 1; r = 1; l = 0; hit = 0 end
    if bot >= 3 then
      -- stall breaker (census only): camera and scroll counters unchanged for CB_STALL (default 500) frames -> clear every pool A record, logged as K
      local ck = m:read_u16(0x8040a) * 65536 + m:read_u16(0x80406)
      if ck == stallck then stall = stall + 1 else stall = 0; stallck = ck end
      if stall >= stallmax then
        stall = 0
        local ts = {}
        for i = 0, 15 do
          local base = 0x81000 + 0x40 * i
          if (m:read_u8(base) & 0x80) ~= 0 then ts[#ts + 1] = string.format("%02x/%02x", m:read_u8(base + 2), m:read_u8(base + 16)) end
          for k = 0, 0x3f do m:write_u8(base + k, 0) end -- all 64 bytes: clearing byte 0 only left a stale state/health that skipped the next spawn's init (found by the GRUNTS agent)
        end
        -- the killed records never run their own clear code: release the boss/event locks as the shared death code would
        m:write_u8(0x80400, m:read_u8(0x80400) & 0xdf); m:write_u8(0x80040, m:read_u8(0x80040) & 0xfb); m:write_u8(0x80041, m:read_u8(0x80041) & 0x7f); m:write_u8(0x81e03, 0)
        out:write(string.format("K %d stall breaker cleared pool A (%s) and the boss locks $80400 bit5, $80040 bit2, $80041 bit7\n", f, table.concat(ts, " ")))
      end
      -- teleport bot: stand beside the nearest on-screen pool A record and attack it; otherwise sit at the scroll trigger x
      local sx = m:read_u16(0x8040a)
      local tgt = nil
      local td = 1e9
      for i = 0, 15 do
        local base = 0x81000 + 0x40 * i
        if (m:read_u8(base) & 0x80) ~= 0 and (m:read_u8(base + 2) ~= 0x1b) then
          local ex, ey = m:read_u16(base + 8), m:read_u16(base + 12)
          if ex > sx - 0x20 and ex < sx + 0x130 then
            local d = math.abs(ex - px)
            if d < td then tgt, td = { ex, ey }, d end
          end
        end
      end
      if parkx and sx >= parkx then tgt = nil end -- CB_PARK_AT: from this scroll x on the bot only parks at the scroll trigger and never attacks (camera lock test)
      if tgt then
        m:write_u16(0x80108, math.max(tgt[1] - 30, sx + 8)); m:write_u16(0x8010c, tgt[2])
        r, l, u, d = 1, 0, 0, 0
        atk_phase = (atk_phase + 1) % 8; hit = atk_phase < 4 and 1 or 0
      else
        m:write_u16(0x80108, sx + 0x92); r, l, u, d, hit = 0, 0, 0, 0, 0 -- scroll request needs x in [sx+$90, sx+$94) once $81e12 bit 0 is set (`$a76e`)
        local sy = m:read_u16(0x80406)
        if (m:read_u8(0x80401) & 0xf) == 0xb and n >= 3 then m:write_u16(0x8010c, 0x1c0) end -- level 4 hang guard: with >= 5 live pool A records and the player at y >= $210 the player routine loops forever at $a7ec..$a85e (observed)
        if (m:read_u8(0x80401) & 0xf) == 0xb and n < 3 then -- cell allows scrolling down (level 4): the player has to walk to y >= $210 (`$a7b4`); a poke into the pit hangs the game
          m:write_u16(0x80108, sx + 0x40); m:write_u16(0x8010c, 0x250); r, d = 0, 0 -- (sx+8, $250) is where the teleport to a lower-area enemy landed in the first run: walkable
        elseif os.getenv("CB_YREL") then m:write_u16(0x8010c, sy + tonumber(os.getenv("CB_YREL"), 16))
        elseif tonumber(os.getenv("CB_LANEY") or "0") ~= 0 then m:write_u16(0x8010c, tonumber(os.getenv("CB_LANEY"))) end
      end
      jump = 0
    end
    set("right", r); set("left", l); set("up", u); set("down", d); set("b1", hit); set("b2", jump)
  end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("o%05d.png", f)) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if f >= stop then out:close(); manager.machine:exit() end
end)
