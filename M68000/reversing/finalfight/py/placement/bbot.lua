-- bbot.lua: the logging variant of lua/stagebot.lua used by py/placement (README.md here). It is a copy of the pass-4 stagebot.lua (same bot, same states: sb_boss work RAM
-- a0cb6b52...4837 is reproduced with every log on) plus: pool strides per pool (pool 14 is 0x40), FF_BOT_WLOG creator-pc write log, FF_BOT_SLOG early census, FF_BOT_TAP write taps,
-- FF_BOT_BP breakpoint log (-debug), FF_BOT_SAVEAT/SHOT. Differences from the current stagebot.lua: no FF_BOT_HP0/FF_BOT_LEAVE, and the prop fallback reads y at +14.
-- stagebot.lua: play a stage with a state-reading bot instead of spawning enemies.
-- Wraps ffdrive.lua (cold boot to the stage, plus FF_PLAN inputs), then from frame FF_BOT_START takes over player 1's inputs:
-- walk right when no fighter is near, otherwise close on the nearest live pool-2 fighter and tap Button 1 when in range.
-- Environment (all optional; ffdrive.lua's FF_SAVE/FF_STOP/FF_LOAD apply too):
--   FF_BOT_START   first frame the bot drives (default 2450)
--   FF_BOT_GOD     1 (default): top Cody's health word +24 up to +28 every frame and keep lives >= 2 (a poke; reported with every result)
--   FF_BOT_LOG     log file: every 10 frames "f cam script x y hp lives live-counts-per-pool", plus spawn lines for new pool records
--   FF_BOT_CAM     stop (and save FF_SAVE) when the camera x 1042(A5) reaches this value
--   FF_BOT_PROPS   1: with no fighter alive, attack a breakable prop (pool $a, +2 = 2) within 120 px ahead (off by default: it changes the run of stage 0)
--   FF_BOT_STAGE   stop (and save FF_SAVE) when the stage byte 190(A5) reaches this value; FF_BOT_STOPF stops at that frame
--   FF_BOT_SCRIPT  stop (and save FF_SAVE) when the stage-script pointer long at $ffb1ee reaches this value
--   FF_BOT_DUMP    comma list of frames at which every live record of the pools is written to the log ("D" lines)
--   FF_BOT_HOLD    comma list "frame:field:level" extra inputs applied after the bot (rarely needed)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local START = tonumber(os.getenv("FF_BOT_START") or "2450")
local GOD = (os.getenv("FF_BOT_GOD") or "1") == "1"
local CAMSTOP = tonumber(os.getenv("FF_BOT_CAM") or "")
local PROPS = os.getenv("FF_BOT_PROPS") == "1"
local STAGESTOP = tonumber(os.getenv("FF_BOT_STAGE") or "")
local STOPFRAME = tonumber(os.getenv("FF_BOT_STOPF") or "")
local SCRSTOP = tonumber(os.getenv("FF_BOT_SCRIPT") or "")
local LOGF = os.getenv("FF_BOT_LOG") and io.open(os.getenv("FF_BOT_LOG"), "w")
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local P1 = 0xff8568
-- p4/b: every pool with its real stride (pool 14 is 30 records of 64 bytes: $99ac with D2 = $40, updater $5ff4), plus the single $ffb228 record
local pools = { { "2", 0xff86e8, 13, 0xc0 }, { "6", 0xff90a8, 6, 0xc0 }, { "4", 0xff9528, 8, 0xc0 }, { "8", 0xff9b28, 30, 0xc0 }, { "a", 0xffb2e8, 16, 0xc0 },
                { "12", 0xffbee8, 10, 0xc0 }, { "14", 0xffc668, 30, 0x40 }, { "c", 0xffb228, 1, 0xc0 } }
local WLOG = os.getenv("FF_BOT_WLOG") and io.open(os.getenv("FF_BOT_WLOG"), "w")
local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
local function poolof(a)
  for _, p in ipairs(pools) do
    local hi = p[2] + p[3] * p[4]
    if a >= p[2] and a < hi then return p, (a - p[2]) // p[4], (a - p[2]) % p[4] end
  end
end
if WLOG then
  -- write tap on the first word of each record (+0 in-use byte, +1), the tag/kind word (+18) and the +20/+21 word of every pool record
  wtapA = m:install_write_tap(0xffb228, 0xffcde7, "recw", function(offset, data, mask)
    local p, i, off = poolof(offset & 0xffffff)
    if p and (off == 0 or off == 18 or off == 20 or off == 6 or off == 10) then
      WLOG:write(string.format("W %d %s %d %06x pc=%06x off=%d m=%04x d=%04x\n", L.frame(), p[1], i, offset, pcreg.value, off, mask, data))
    end
  end)
  wtapB = m:install_write_tap(0xff86e8, 0xffb227, "recw2", function(offset, data, mask)
    local p, i, off = poolof(offset & 0xffffff)
    if p and (off == 0 or off == 18 or off == 20 or off == 6 or off == 10) then
      WLOG:write(string.format("W %d %s %d %06x pc=%06x off=%d m=%04x d=%04x\n", L.frame(), p[1], i, offset, pcreg.value, off, mask, data))
    end
  end)
end
local seen = {}
local held = {}
local function set(field, v) if held[field] ~= v then held[field] = v; L.F[field]:set_value(v) end end
local function nearest()
  local px, py = m:read_u16(P1 + 6), m:read_u16(P1 + 14)
  local best, bd
  -- pool 2 (13 fighters) and pool 4 (8 records: the boss DAMND is one). Alive: in use, not new, state 0 or 2 (4 dying, 6 gone), health word not negative
  -- (a fighter dies at hp < 0: HOLLY WOOD sits at hp 0 and still fights). y is the ground line +14 (a jumping boss has +10 high in the air).
  for _, p in ipairs({ { 0xff86e8, 13 }, { 0xff9528, 8 } }) do
    for i = 0, p[2] - 1 do
      local a = p[1] + 0xc0 * i
      local st = m:read_u8(a + 2)
      local hp = m:read_u16(a + 24)
      if m:read_u8(a) ~= 0 and m:read_u8(a) < 0x80 and (st == 0 or st == 2) and hp < 0x8000 and (p[1] == 0xff86e8 or hp > 0) then
        local ex, ey = m:read_u16(a + 6), m:read_u16(a + 14)
        local d = math.abs(ex - px) + 2 * math.abs(ey - py)
        if not bd or d < bd then best, bd = { x = ex, y = ey, a = a }, d end
      end
    end
  end
  if PROPS and not best then -- no fighter: a breakable prop (pool $a) just ahead blocks the walk (three barrels held the bot in stage 1 area 1)
    for i = 0, 15 do
      local a = 0xffb2e8 + 0xc0 * i
      if m:read_u8(a) == 1 and m:read_u8(a + 2) == 2 then
        local ex, ey = m:read_u16(a + 6), m:read_u16(a + 14)
        local dx = ex - px
        if dx >= -20 and dx < 120 then
          local d = math.abs(dx) + 2 * math.abs(ey - py)
          if not bd or d < bd then best, bd = { x = ex, y = ey, a = a }, d end
        end
      end
    end
  end
  return px, py, best
end
-- generic write taps: FF_BOT_TAP="lo-hi,lo-hi" (hex) logged to FF_BOT_TAPLOG as "T frame pc addr mask data"
local TAPLOG = os.getenv("FF_BOT_TAPLOG") and io.open(os.getenv("FF_BOT_TAPLOG"), "w")
local PCLO, PCHI = (os.getenv("FF_BOT_TAPPC") or ""):match("^(%x+)-(%x+)$")
PCLO = PCLO and tonumber(PCLO, 16); PCHI = PCHI and tonumber(PCHI, 16)
taps = {}
for lo, hi in string.gmatch(os.getenv("FF_BOT_TAP") or "", "(%x+)-(%x+)") do
  taps[#taps + 1] = m:install_write_tap(tonumber(lo, 16), tonumber(hi, 16), "t" .. lo, function(offset, data, mask)
    if PCLO and (pcreg.value < PCLO or pcreg.value > PCHI) then return end
    local extra = ""
    if pcreg.value == 0x5b66e then -- HUD name builder: the HUD record's tag/kind/+20 at the time (record base = offset - 150 for the low word of +148)
      local b = offset - 150
      extra = string.format(" r=%02x%02x%02x", m:read_u8(b + 18), m:read_u8(b + 19), m:read_u8(b + 20))
    end
    TAPLOG:write(string.format("T %d pc=%06x a=%06x m=%04x d=%04x%s\n", L.frame(), pcreg.value, offset, mask, data, extra))
  end)
end
-- debugger breakpoint logging (needs FF_MAMEARGS="-debug -debugger none"): FF_BOT_BP="addr:fmt:args;addr:fmt:args" ->
-- bpset addr,1,{printf "B <addr> fmt\n",args; g}; lines are copied to FF_BOT_BPLOG as "<frame> <line>"
local BPLOG = os.getenv("FF_BOT_BPLOG") and io.open(os.getenv("FF_BOT_BPLOG"), "w")
local bps_started, bp_seen = false, 0
emu.register_periodic(function()
  if bps_started or not os.getenv("FF_BOT_BP") then return end
  bps_started = true
  local dbg = manager.machine.debugger
  for spec in string.gmatch(os.getenv("FF_BOT_BP"), "[^;]+") do
    local addr, fmt, args = spec:match("^(%x+):([^:]*):?(.*)$")
    dbg:command(string.format('bpset %s,1,{printf "B %s %s"%s; g}', addr, addr, fmt, args ~= "" and ("," .. args) or ""))
  end
  dbg:command("go")
end)
if BPLOG then
  emu.register_frame_done(function()
    local log = manager.machine.debugger.consolelog
    for i = bp_seen + 1, #log do BPLOG:write(string.format("%d %s\n", L.frame(), log[i])) end
    bp_seen = #log
  end)
end
-- early census: S lines from frame FF_BOT_LOGFROM (default 1300, before the bot drives) into FF_BOT_SLOG, same format as the bot log, plus the camera/stage line every 10 frames
local SAVEAT, SHOTAT = {}, {}
for n in string.gmatch(os.getenv("FF_BOT_SAVEAT") or "", "%d+") do SAVEAT[tonumber(n)] = true end
for n in string.gmatch(os.getenv("FF_BOT_SHOT") or "", "%d+") do SHOTAT[tonumber(n)] = true end
local SLOG = os.getenv("FF_BOT_SLOG") and io.open(os.getenv("FF_BOT_SLOG"), "w")
local LOGFROM = tonumber(os.getenv("FF_BOT_LOGFROM") or "1300")
local seen2 = {}
emu.register_frame_done(function()
  local f = L.frame()
  if SHOTAT[f] then L.screen:snapshot(string.format("bb_%d.png", f)) end
  if SAVEAT[f] then manager.machine:save(string.format("bb_%d", f)) end
  if not SLOG then return end
  if f < LOGFROM then return end
  local cam = m:read_u16(0xff8412)
  local scr = m:read_u32(0xffb1ee)
  if f % 10 == 0 then
    SLOG:write(string.format("%d sa=%02x%02x cam=%04x scr=%06x x=%04x y=%04x st=%02x%02x hp=%04x\n", f, m:read_u8(0xff80be), m:read_u8(0xff80bf), cam, scr,
      m:read_u16(P1 + 6), m:read_u16(P1 + 14), m:read_u8(P1 + 2), m:read_u8(P1 + 3), m:read_u16(P1 + 24)))
  end
  for _, p in ipairs(pools) do
    for i = 0, p[3] - 1 do
      local a = p[2] + p[4] * i
      local live = m:read_u8(a) ~= 0
      if live and not seen2[a] then
        seen2[a] = true
        SLOG:write(string.format("S %d pool=%s rec=%d %06x kind=%02x ch=%02x ent=%02x lvl=%02x x=%04x y=%04x hp=%04x cam=%04x scr=%06x\n", f, p[1], i, a,
          m:read_u8(a + 19), m:read_u8(a + 20), m:read_u8(a + 21), m:read_u8(a + 96), m:read_u16(a + 6), m:read_u16(a + 10), m:read_u16(a + 24), cam, scr))
      elseif not live then seen2[a] = nil end
    end
  end
  if f % 50 == 0 then SLOG:flush() end
end)
local DUMPS = {}
for n in string.gmatch(os.getenv("FF_BOT_DUMP") or "", "%d+") do DUMPS[tonumber(n)] = true end
local last_b1 = -100
emu.register_frame_done(function()
  local f = L.frame()
  if f < START then return end
  local cam = m:read_u16(0xff8412)
  local scr = m:read_u32(0xffb1ee)
  if GOD then
    local mx = m:read_u16(P1 + 28)
    if m:read_u16(P1 + 24) < mx and m:read_u8(P1 + 2) == 2 then m:write_u16(P1 + 24, mx) end
    if m:read_u8(P1 + 128) < 2 then m:write_u8(P1 + 128, 2) end
  end
  local px, py, e = nearest()
  local right, left, up, down = 0, 0, 0, 0
  if e then
    local dx, dy = e.x - px, e.y - py
    if dy > 5 then down = 1 elseif dy < -5 then up = 1 end  -- Up lowers the ground-line word +14 (Cody pinned at the lane minimum with Up held, 5000 frames)
    if math.abs(dx) > 40 then if dx > 0 then right = 1 else left = 1 end end
    if math.abs(dx) <= 60 and math.abs(dy) <= 8 and f - last_b1 >= 14 then last_b1 = f end
  else
    right = 1
  end
  set("right", right); set("left", left); set("up", up); set("down", down)
  set("b1", (f - last_b1 < 5) and 1 or 0)
  if LOGF then
    if f % 10 == 0 then
      local c = {}
      for _, p in ipairs(pools) do
        local n = 0
        for i = 0, p[3] - 1 do if m:read_u8(p[2] + p[4] * i) ~= 0 then n = n + 1 end end
        c[#c + 1] = p[1] .. "=" .. n
      end
      LOGF:write(string.format("%d sa=%02x%02x cam=%04x scr=%06x x=%04x y=%04x st=%02x%02x hp=%04x lives=%02x %s\n", f, m:read_u8(0xff80be), m:read_u8(0xff80bf), cam, scr, px, py,
        m:read_u8(P1 + 2), m:read_u8(P1 + 3), m:read_u16(P1 + 24), m:read_u8(P1 + 128), table.concat(c, " ")))
    end
    for _, p in ipairs(pools) do
      for i = 0, p[3] - 1 do
        local a = p[2] + p[4] * i
        local live = m:read_u8(a) ~= 0
        if live and not seen[a] then
          seen[a] = true
          LOGF:write(string.format("S %d pool=%s rec=%d %06x kind=%02x ch=%02x ent=%02x lvl=%02x x=%04x y=%04x hp=%04x cam=%04x scr=%06x\n", f, p[1], i, a,
            m:read_u8(a + 19), m:read_u8(a + 20), m:read_u8(a + 21), m:read_u8(a + 96), m:read_u16(a + 6), m:read_u16(a + 10), m:read_u16(a + 24), cam, scr))
        elseif not live then seen[a] = nil end
      end
    end
    LOGF:flush()
  end
  if LOGF and DUMPS[f] then
    for _, p in ipairs(pools) do
      for i = 0, p[3] - 1 do
        local a = p[2] + p[4] * i
        if m:read_u8(a) ~= 0 then
          LOGF:write(string.format("D %d pool=%s rec=%d %06x b0=%02x b1=%02x st=%02x%02x kind=%02x ch=%02x x=%04x y=%04x hp=%04x p92=%06x\n", f, p[1], i, a,
            m:read_u8(a), m:read_u8(a + 1), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 19), m:read_u8(a + 20), m:read_u16(a + 6), m:read_u16(a + 10),
            m:read_u16(a + 24), m:read_u32(a + 92) & 0xffffff))
        end
      end
    end
  end
  local stg = m:read_u8(0xff80be)
  if (CAMSTOP and cam >= CAMSTOP) or (SCRSTOP and scr >= SCRSTOP) or (STAGESTOP and stg >= STAGESTOP) or (STOPFRAME and f >= STOPFRAME) then
    if LOGF then LOGF:write(string.format("STOP %d cam=%04x scr=%06x\n", f, cam, scr)); LOGF:close() end
    if WLOG then WLOG:close() end
    if TAPLOG then TAPLOG:close() end
    if BPLOG then BPLOG:close() end
    if SLOG then SLOG:close() end
    if os.getenv("FF_SAVE") then
      L.write(string.format("%s/%s_ram.bin", out, os.getenv("FF_SAVE")), L.ram())
      L.write(string.format("%s/%s_gfxram.bin", out, os.getenv("FF_SAVE")), L.region(0x900000, 0x30000))
      L.screen:snapshot(os.getenv("FF_SAVE") .. ".png")
      manager.machine:save(os.getenv("FF_SAVE"))
    end
    manager.machine:exit()
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
