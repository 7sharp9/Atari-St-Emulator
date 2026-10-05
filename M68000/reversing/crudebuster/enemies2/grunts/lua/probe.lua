-- probe.lua: isolated enemy probe for Crude Buster pool A types (GRUNTS group).
--   Starts level CB_LEVEL (like objlog.lua), optionally pokes enemies into pool A, places the player, runs a bot, logs per frame
--   every active pool A record and the events below.
--   env: CB_DIR (reversing/crudebuster/lua), CB_LEVEL, CB_STOP, CB_OUT (writes probe.txt), CB_SHOTS lo:hi:step
--     CB_SPAWN  "frame:type:var:x:y;..."   (frame decimal, rest hex) writes a pool A record into the first free slot at that frame (same fields as $21eb6)
--     CB_PLAYER "frame:x:y;..."             (frame decimal, rest hex) pokes P1 x/y words ($80108/$8010c) at that frame
--     CB_SCROLL "frame:sx:sy;..."           (frame decimal, rest hex) pokes the scroll counters $8040a/$80406
--     CB_OR     "frame:addr:mask;..."   (frame decimal, rest hex) ORs mask into the byte at addr (e.g. 81006:88 = hit flags +6 of pool A slot 0: bit 7 hit, bit 3 strong; 81011:40 = +17 bit 6 = hit by a throw)
--     CB_POKES  "frame:addr:byte;..."       (frame decimal, rest hex)
--     CB_NOSCRIPT 1: from frame 715 on, the list A pointer $81e06 is held on the list's $ffff terminator (levels 3-5 only), so only CB_SPAWN enemies exist
--     CB_BOT    0 none, 1 attack nearest pool A record (objlog bot, walks right when none), 2 attack nearest, never walk (stays within 3 px rows)
--     CB_BOTSTOP frame: the bot stops driving inputs from this frame; CB_IN "frame:name:val;..." (frame decimal, name right|left|up|down|b1|b2|b3, val 0/1) sets inputs after the bot
--     CB_BTN    which buttons the bot pulses when in range: "1" (default, punch), "12" etc.
--     CB_HEAL   1 (default): after logging, restore P1 health to $38 whenever it is below $20 (damage events are logged first)
--     CB_SAVE/CB_SAVE_FRAME  save a state; CB_LOAD <name> in run mode loads a state at frame CB_LOAD_FRAME
--   lines:  F <frame> lvl sx sy px py hp f40 f41 n pstate psub score(P1 long $8013c) hiscore(long $80010)   (n = live pool A count; pstate/psub = P1 +24/+25)
--           A <frame> <slot> <64 hex>                          pool A record
--           S <frame> <ownerslot> <otype> <ostate> <ovar> <ctype> <facing> <ox> <oy>   pool C box spawn ($21e8e, owner = A6)
--           D <frame> <old> <new> <pc> <ctype> <cstate> <cframe> <ownerslot> <otype> <ostate> <ovar>   write to P1 health byte $80113
--           B <frame> <slot> <type> <var> x y     pool B record appears (a prop, drop or effect)
--           I <frame> dip=<$80054 $80055>
--           H <frame> <slot> <type> <state> <hp_before> <hp_after>  enemy health change (+5) with writer pc
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local bot = tonumber(os.getenv("CB_BOT") or "0")
local btn = os.getenv("CB_BTN") or "1"
local heal = tonumber(os.getenv("CB_HEAL") or "1")
local out = io.open((os.getenv("CB_OUT") or ".") .. "/probe.txt", "w")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local function parse(env, n)
  local t = {}
  for item in (os.getenv(env) or ""):gmatch("[^;]+") do
    local f = {}
    for v in item:gmatch("[^:]+") do f[#f + 1] = tonumber(v, #f == 0 and 10 or 16) end
    t[#t + 1] = f
  end
  return t
end
local spawns, players, scrolls, pokes, ors = parse("CB_SPAWN"), parse("CB_PLAYER"), parse("CB_SCROLL"), parse("CB_POKES"), parse("CB_OR")
local m = L.mem
local botstop = tonumber(os.getenv("CB_BOTSTOP") or "1000000")
local inputs = {}
for item in (os.getenv("CB_IN") or ""):gmatch("[^;]+") do
  local fr, nm, v = item:match("(%d+):(%w+):(%d)")
  inputs[#inputs + 1] = { tonumber(fr), nm, tonumber(v) }
end
local noscript = tonumber(os.getenv("CB_NOSCRIPT") or "0")
local TERM = { [0] = 0, [1] = 0, [2] = 0, [3] = 0x6c54e, [4] = 0x6c730, [5] = 0x6c9a4 } -- address of the $ffff terminator of list A of each level
local cpu = manager.machine.devices[":maincpu"]
local function a6() return cpu.state["A6"].value end
local function slotof(base) return (base - 0x81000) // 0x40 end
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return (data & 0xff) ~= data and data or ((want << 8) | want) end
end)
-- pool C spawn: the write of the type byte at +2 by $21e8e (move.b D6,2(A5)); A6 = owner, D6 = type, D7 = facing
taps[2] = m:install_write_tap(0x81c00, 0x81cff, "cspawn", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc == 0x21e94 or pc == 0x21e90 or pc == 0x21e92 then -- pc after the write of +2 (CURPC points at the next instruction in a tap)
    -- handled below by D6 check
  end
  if (off & 0x1f) == 2 and pc >= 0x21e72 and pc < 0x21eb6 then
    local o = a6()
    local d6, d7 = cpu.state["D6"].value & 0xff, cpu.state["D7"].value & 0xff
    out:write(string.format("S %d %d %02x %02x %02x %02x %d %04x %04x\n", L.frame(), slotof(o), m:read_u8(o + 2), m:read_u8(o + 3), m:read_u8(o + 16), d6, d7, m:read_u16(o + 8), m:read_u16(o + 12)))
  end
end)
local hp_prev = nil
taps[3] = m:install_write_tap(0x80112, 0x80113, "hp", function(off, data, mask)
  if (mask & 0xff) == 0 then return end
  local pc = cpu.state["CURPC"].value
  local old = m:read_u8(0x80113)
  local new = data & 0xff
  if new == old then return end
  local c = a6()
  local ctype, cstate, cframe, os_, ot, ost, ov = -1, -1, -1, -1, -1, -1, -1
  if c >= 0x81c00 and c < 0x81d00 then
    ctype, cstate, cframe = m:read_u8(c + 2), m:read_u8(c + 3), m:read_u8(c + 20)
    local o = m:read_u32(c + 28)
    if o >= 0x81000 and o < 0x81400 then os_, ot, ost, ov = slotof(o), m:read_u8(o + 2), m:read_u8(o + 3), m:read_u8(o + 16) end
  end
  out:write(string.format("D %d %02x %02x %06x %02x %02x %02x %d %02x %02x %02x\n", L.frame(), old, new, pc, ctype, cstate, cframe, os_, ot, ost, ov))
end)
local function bytes(base)
  local t = {}
  for k = 0, 0x3f do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end
  return table.concat(t)
end
local seenB = {}
local atk_phase = 0
local function set(name, v) L.F[name]:set_value(v) end
local btns = {}
for c in btn:gmatch(".") do btns[#btns + 1] = "b" .. c end
local loadname, loadf = os.getenv("CB_LOAD"), tonumber(os.getenv("CB_LOAD_FRAME") or "0")
emu.register_frame_done(function()
  local f = L.frame()
  if loadname and f == loadf then manager.machine:load(loadname) end
  if f == 600 then set("coin", 1) elseif f == 612 then set("coin", 0)
  elseif f == 700 then set("start1", 1) elseif f == 712 then set("start1", 0) end
  for _, p in ipairs(pokes) do if p[1] == f then m:write_u8(p[2], p[3]) end end
  for _, p in ipairs(ors) do if p[1] == f then m:write_u8(p[2], m:read_u8(p[2]) | p[3]) end end
  for _, p in ipairs(players) do if p[1] == f then m:write_u16(0x80108, p[2]); m:write_u16(0x8010c, p[3]) end end
  for _, p in ipairs(scrolls) do if p[1] == f then m:write_u16(0x8040a, p[2]); m:write_u16(0x80406, p[3]) end end
  for _, p in ipairs(spawns) do
    if p[1] == f then
      for i = 0, 15 do
        local base = 0x81000 + 0x40 * i
        if (m:read_u8(base) & 0x80) == 0 then
          for k = 0, 0x3f do m:write_u8(base + k, 0) end; m:write_u8(base, 0x80); m:write_u8(base + 2, p[2]); m:write_u8(base + 16, p[3]); m:write_u16(base + 8, p[4]); m:write_u16(base + 12, p[5])
          break
        end
      end
    end
  end
  if noscript == 1 and f >= 715 and TERM[want] ~= 0 then m:write_u32(0x81e06, TERM[want]); m:write_u8(0x81e04, m:read_u8(0x81e04) | 0x80) end
  if f == 800 then out:write(string.format("I %d dip=%02x%02x\n", f, m:read_u8(0x80054), m:read_u8(0x80055))) end
  for i = 0, 31 do
    local base = 0x81400 + 0x40 * i
    local t = (m:read_u8(base) & 0x80) ~= 0 and m:read_u8(base + 2) or -1
    if t ~= seenB[i] then
      seenB[i] = t
      if t >= 0 then out:write(string.format("B %d %d %02x %02x %04x %04x\n", f, i, t, m:read_u8(base + 16), m:read_u16(base + 8), m:read_u16(base + 12))) end
    end
  end
  local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
  local hp = m:read_u8(0x80113)
  local running = (m:read_u8(0x80040) & 0x80) ~= 0 and f > 720
  local n = 0
  for i = 0, 15 do
    local base = 0x81000 + 0x40 * i
    if (m:read_u8(base) & 0x80) ~= 0 then n = n + 1; out:write(string.format("A %d %d %s\n", f, i, bytes(base))) end
  end
  out:write(string.format("F %d %d %04x %04x %04x %04x %02x %02x %02x %d %02x %02x %08x %08x\n", f, m:read_u8(0x80046), m:read_u16(0x8040a), m:read_u16(0x80406), px, py, hp, m:read_u8(0x80040), m:read_u8(0x80041), n, m:read_u8(0x80118), m:read_u8(0x80119), m:read_u32(0x8013c), m:read_u32(0x80010)))
  if running and heal == 1 and hp < 0x20 and hp > 0 then m:write_u8(0x80113, 0x38) end
  if bot >= 1 and running and f < botstop then
    local best, bd = nil, 1e9
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 and m:read_u8(base + 3) ~= 2 and m:read_u8(base + 3) ~= 4 then
        local ex, ey = m:read_u16(base + 8), m:read_u16(base + 12)
        local d = math.abs(ex - px) + 3 * math.abs(ey - py)
        if d < bd then best, bd = { ex, ey }, d end
      end
    end
    local l, r, u, d = 0, 0, 0, 0
    local hit = {}
    if best and bd < 400 then
      local dx, dy = best[1] - px, best[2] - py
      if dy < -4 then u = 1 elseif dy > 4 then d = 1 end
      if dx > 36 then r = 1 elseif dx < -36 then l = 1 end
      if math.abs(dx) < 56 and math.abs(dy) < 14 then
        if dx > 0 then r = 1 else l = 1 end
        atk_phase = (atk_phase + 1) % 8
        if atk_phase < 4 then hit = { btns[(f // 8) % #btns + 1] } end
      end
    elseif bot == 1 then
      r = 1
    end
    set("right", r); set("left", l); set("up", u); set("down", d)
    set("b1", 0); set("b2", 0); set("b3", 0)
    for _, b in ipairs(hit) do set(b, 1) end
  end
  for _, i in ipairs(inputs) do if i[1] == f then set(i[2], i[3]) end end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("p%05d.png", f)) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if f >= stop then out:close(); manager.machine:exit() end
end)
