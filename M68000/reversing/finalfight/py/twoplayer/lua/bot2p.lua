-- bot2p.lua: cold boot, character select (one or two players), then state-reading bots play stage 0 (derived from stagebot.lua).
-- Environment (FF_DIR, FF_OUT as the wrappers set them):
--   FF_CH1 / FF_CH2   character index 0 Guy, 1 Cody, 2 Haggar for P1 / P2 (FF_CH2=-1: one player, default 1 and -1)
--   FF_BOT_START      first frame the bots drive (default 1800); FF_BOT_GOD 1 (default) tops each player's health word +24 up to +28 and keeps lives >= 2
--   FF_BOT_P1 / FF_BOT_P2  1 (default) the bot plays that player; 0 leaves it idle
--   FF_BOT_LOG        log: every 10 frames "f sa= cam= scr= P1 P2 live-counts", S lines for new pool records (as stagebot.lua), D lines at FF_BOT_DUMP frames
--   FF_BOT_CAM / FF_BOT_STAGE / FF_BOT_STOPF / FF_BOT_SCRIPT   stop conditions (as stagebot.lua); FF_SAVE state name saved at the stop
--   FF_LOAD           load a saved state at frame 1 instead of the cold boot (then FF_CH1/2 are ignored)
--   FFD_SCHED         extra {frame, field, level} schedule file (applied after the select schedule)
--   FFD_EXTRA         lua file run each frame as function(f, L, bots) (pokes, taps)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local ch1 = tonumber(os.getenv("FF_CH1") or "1")
local ch2 = tonumber(os.getenv("FF_CH2") or "-1")
local START = tonumber(os.getenv("FF_BOT_START") or "1800")
local GOD = (os.getenv("FF_BOT_GOD") or "1") == "1"
local DRIVE = { (os.getenv("FF_BOT_P1") or "1") == "1", (os.getenv("FF_BOT_P2") or "1") == "1" }
local CAMSTOP = tonumber(os.getenv("FF_BOT_CAM") or "")
local STAGESTOP = tonumber(os.getenv("FF_BOT_STAGE") or "")
local STOPFRAME = tonumber(os.getenv("FF_BOT_STOPF") or "")
local SCRSTOP = tonumber(os.getenv("FF_BOT_SCRIPT") or "")
local NOATK = (os.getenv("FF_BOT_NOATK") or "0") == "1"   -- the bots never press Button 1: enemies pile up and stay alive (GOD)
local STUCKSTOP = tonumber(os.getenv("FF_BOT_STUCKSTOP") or "")  -- stop (and save) when P1 has not moved for this many frames
local LOGF = os.getenv("FF_BOT_LOG") and io.open(os.getenv("FF_BOT_LOG"), "w")
local out = os.getenv("FF_OUT")
local PREC = { 0xff8568, 0xff8628 }
local FLD = { { "right", "left", "up", "down", "b1", "b2", "b3" }, { "right2", "left2", "up2", "down2", "b1_2", "b2_2", "b3_2" } }
local pools = { { "2", 0xff86e8, 13 }, { "6", 0xff90a8, 6 }, { "4", 0xff9528, 8 }, { "8", 0xff9b28, 30 }, { "a", 0xffb2e8, 16 },
                { "12", 0xffbee8, 10 }, { "14", 0xffc668, 10 } }
local seen, held = {}, {}
local function set(field, v) if held[field] ~= v then held[field] = v; L.F[field]:set_value(v) end end

-- select schedule
local sched = {}
local function add(f, field, v) sched[#sched + 1] = { f, field, v } end
local twop = ch2 >= 0
add(1100, "coin", 1); add(1112, "coin", 0)
if twop then
  add(1120, "coin", 1); add(1132, "coin", 0)
  add(1150, "start2", 1); add(1162, "start2", 0)
else
  add(1150, "start1", 1); add(1162, "start1", 0)
end
for i = 1, ch1 do add(1220 + 16 * i, "right", 1); add(1226 + 16 * i, "right", 0) end
if twop then
  local pos = 2
  local n = 0
  -- P2 moves left from Haggar; a cursor never rests on the other player's character (observed: it skips it)
  local target = ch2
  while pos ~= target do
    pos = pos - 1
    if pos == ch1 then pos = pos - 1 end
    n = n + 1
    add(1250 + 16 * n, "left2", 1); add(1256 + 16 * n, "left2", 0)
  end
end
add(1290, "b1", 1); add(1302, "b1", 0)
if twop then add(1310, "b1_2", 1); add(1322, "b1_2", 0) end
if os.getenv("FFD_SCHED") then for _, e in ipairs(dofile(os.getenv("FFD_SCHED"))) do sched[#sched + 1] = e end end
local shots = {}
for n in string.gmatch(os.getenv("FFD_SHOTS") or "", "%d+") do shots[tonumber(n)] = true end
local extra = os.getenv("FFD_EXTRA") and dofile(os.getenv("FFD_EXTRA"))

local function nearest(p)
  local P = PREC[p]
  local px, py = m:read_u16(P + 6), m:read_u16(P + 14)
  local best, bd
  for _, pl in ipairs({ { 0xff86e8, 13 }, { 0xff9528, 8 } }) do
    for i = 0, pl[2] - 1 do
      local a = pl[1] + 0xc0 * i
      local st = m:read_u8(a + 2)
      local hp = m:read_u16(a + 24)
      if m:read_u8(a) ~= 0 and m:read_u8(a) < 0x80 and (st == 0 or st == 2) and hp < 0x8000 and (pl[1] == 0xff86e8 or hp > 0) then
        local ex, ey = m:read_u16(a + 6), m:read_u16(a + 14)
        local d = math.abs(ex - px) + 2 * math.abs(ey - py)
        if not bd or d < bd then best, bd = { x = ex, y = ey, a = a }, d end
      end
    end
  end
  return px, py, best
end
local DUMPS = {}
for n in string.gmatch(os.getenv("FF_BOT_DUMP") or "", "%d+") do DUMPS[tonumber(n)] = true end
local last_b1 = { -100, -100 }
local stuck = { { x = -1, n = 0 }, { x = -1, n = 0 } }
local bots = { P = PREC }
emu.register_frame_done(function()
  local f = L.frame()
  local lf = os.getenv("FF_LOAD")
  if lf and not bots.loaded then bots.loaded = true; manager.machine:load(lf); return end
  if not lf then L.apply(sched, f) elseif os.getenv("FFD_SCHED") then L.apply(sched, f) end
  local cam = m:read_u16(0xff8412)
  local scr = m:read_u32(0xffb1ee)
  if f >= START or lf then
    for p = 1, 2 do
      local P = PREC[p]
      if m:read_u8(P) ~= 0 then
        if GOD then
          local mx = m:read_u16(P + 28)
          if m:read_u16(P + 24) < mx and m:read_u8(P + 2) == 2 then m:write_u16(P + 24, mx) end
          if m:read_u8(P + 128) < 2 then m:write_u8(P + 128, 2) end
        end
        if DRIVE[p] then
          local px, py, e = nearest(p)
          local right, left, up, down = 0, 0, 0, 0
          if e then
            local dx, dy = e.x - px, e.y - py
            if dy > 5 then up = 1 elseif dy < -5 then down = 1 end  -- +14 grows with Up (walkd run: Up 40 frames took y from $10 to $37)
            if math.abs(dx) > 40 then if dx > 0 then right = 1 else left = 1 end end
            if math.abs(dx) <= 60 and math.abs(dy) <= 8 and f - last_b1[p] >= 14 then last_b1[p] = f end
          else
            right = 1
            -- anti-stuck: a prop in the lane blocks walking (observed: P1 pinned 13000 frames); when x has not changed for 60 frames hit it, then step off the lane
            local st = stuck[p]
            if px == st.x then st.n = st.n + 1 else st.x = px; st.n = 0 end
            if st.n > 60 and not STUCKSTOP then
              if (st.n // 8) % 2 == 0 then last_b1[p] = f - 14 + 1 end
              if st.n > 160 then if (st.n // 40) % 2 == 0 then up = 1 else down = 1 end end
            end
          end
          local F = FLD[p]
          set(F[1], right); set(F[2], left); set(F[3], up); set(F[4], down)
          set(F[5], (not NOATK and f - last_b1[p] < 5) and 1 or 0)
        end
      end
    end
  end
  if extra then extra(f, L, bots) end
  if shots[f] then L.screen:snapshot(string.format("bot_%05d.png", f)) end
  if LOGF and f >= START then
    if f % 10 == 0 then
      local c = {}
      for _, p in ipairs(pools) do
        local n = 0
        for i = 0, p[3] - 1 do if m:read_u8(p[2] + 0xc0 * i) ~= 0 then n = n + 1 end end
        c[#c + 1] = p[1] .. "=" .. n
      end
      local function pl(P)
        return string.format("%d:%02x%02x x=%04x y=%04x hp=%04x lv=%02x", m:read_u8(P), m:read_u8(P + 2), m:read_u8(P + 3), m:read_u16(P + 6), m:read_u16(P + 14), m:read_u16(P + 24), m:read_u8(P + 128))
      end
      LOGF:write(string.format("%d sa=%02x%02x cam=%04x scr=%06x P1[%s] P2[%s] %s\n", f, m:read_u8(0xff80be), m:read_u8(0xff80bf), cam, scr, pl(PREC[1]), pl(PREC[2]), table.concat(c, " ")))
    end
    for _, p in ipairs(pools) do
      for i = 0, p[3] - 1 do
        local a = p[2] + 0xc0 * i
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
        local a = p[2] + 0xc0 * i
        if m:read_u8(a) ~= 0 then
          LOGF:write(string.format("D %d pool=%s rec=%d %06x b0=%02x b1=%02x st=%02x%02x kind=%02x ch=%02x x=%04x y=%04x hp=%04x p92=%06x\n", f, p[1], i, a,
            m:read_u8(a), m:read_u8(a + 1), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 19), m:read_u8(a + 20), m:read_u16(a + 6), m:read_u16(a + 10),
            m:read_u16(a + 24), m:read_u32(a + 92) & 0xffffff))
        end
      end
    end
  end
  local stg = m:read_u8(0xff80be)
  if STUCKSTOP and f > 2000 and stuck[1].n >= STUCKSTOP then STOPFRAME = f end
  if (CAMSTOP and cam >= CAMSTOP) or (SCRSTOP and scr >= SCRSTOP) or (STAGESTOP and stg >= STAGESTOP) or (STOPFRAME and f >= STOPFRAME) then
    if LOGF then LOGF:write(string.format("STOP %d cam=%04x scr=%06x\n", f, cam, scr)); LOGF:close() end
    if os.getenv("FF_SAVE") then
      L.write(string.format("%s/%s_ram.bin", out, os.getenv("FF_SAVE")), L.ram())
      L.screen:snapshot(os.getenv("FF_SAVE") .. ".png")
      manager.machine:save(os.getenv("FF_SAVE"))
    end
    manager.machine:exit()
  end
end)
