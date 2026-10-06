-- stagebot.lua: play a stage with a state-reading bot instead of spawning enemies.
-- Wraps ffdrive.lua (cold boot to the stage, plus FF_PLAN inputs), then from frame FF_BOT_START takes over player 1's inputs:
-- walk right when no fighter is near, otherwise close on the nearest live pool-2 fighter and tap Button 1 when in range.
-- Environment (all optional; ffdrive.lua's FF_SAVE/FF_STOP/FF_LOAD apply too):
--   FF_BOT_START   first frame the bot drives (default 2450)
--   FF_BOT_GOD     1 (default): top Cody's health word +24 up to +28 every frame and keep lives >= 2 (a poke; reported with every result)
--   FF_BOT_LOG     log file: every 10 frames "f cam script x y hp lives live-counts-per-pool", plus spawn lines for new pool records
--   FF_BOT_CAM     stop (and save FF_SAVE) when the camera x 1042(A5) reaches this value
--   FF_BOT_HP0     1: treat a pool-4 record at hp 0 as alive (the rule is hp >= 0). Off by default only to keep the states sb_boss (a0cb6b52...) and sb_s1 that the pass-4 proofs start from: with it on, the bot chases DAMND from his allocation at frame 7810 and the run differs
--   FF_BOT_LANEFIX 1: Up raises the lane word (the measured mapping); off by default, see the comment at the use
--   FF_BOT_PROPS   1: with no fighter alive, attack a breakable prop (pool $a, +2 = 2) within 120 px ahead (off by default: it changes the run of stage 0)
--   FF_BOT_LURE    1: when the nearest target has stood within $80 px outside the camera window for 120 frames, walk to mid-screen instead of at it (a kind 3 fighter parks its destination `$50`/`$80` px beside the player,
--                  off screen when the player hugs the locked camera's edge: stage 2 area 0, `ai.md`). Off by default: it changes the run
--   FF_BOT_UNSTICK 1: when Right has not moved the player for 45 frames, press Down (physically lowers the lane), then Up on the next stall, for 40 frames, and with FF_BOT_PROPS prefers a prop ahead for 600 frames (stage 2 area 2: a DOOR prop at x $888 walls every lane). Stage 2 area 0 past the
--                  second lock: the lane y >= $30 is blocked at x $3a0 by terrain codes 7 and 8 (a curb), the rows below it are open (`placement.md`, "Terrain codes"). Off by default
--                  FF_BOT_UNSTICK also selects the stage 2 to 5 prop rules: FLAME props (kinds $10, $11) are never targeted, and a prop is swung at only with the lane aligned (|dy| <= 5; 12 once the lane has not moved for 40 frames)
--   FF_BOT_PROPRANGE  dx within which the bot swings at a prop (default 60, as in the states sb_s1 and sb_s6; 48 clears stage 3's first props)
--   FF_BOT_LEAVE   stop when the stage byte 190(A5) differs from this value (after the subway it is 6, not 2); with FF_SAVE_PREFIX=<p> the state is saved as <p><new stage byte>
--   FF_BOT_STAGE   stop (and save FF_SAVE) when the stage byte 190(A5) reaches this value; FF_BOT_STOPF stops at that frame
--   FF_BOT_SCRIPT  stop (and save FF_SAVE) when the stage-script pointer long at $ffb1ee reaches this value
--   FF_BOT_DUMP    comma list of frames at which every live record of the pools is written to the log ("D" lines)
--   FF_BOT_HOLD    comma list "frame:field:level" extra inputs applied after the bot (rarely needed)
-- stagebot_opt.lua: same decisions, log and RAM as stagebot.lua. m:read_u8(a) costs 0.85 us (userdata method lookup), the cached function ru8(m, a) 0.25 us:
-- every per-frame access below goes through cached functions, fields are read only for records in use, and no table is created per frame.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local ru8, ru16, ru32, wu8, wu16 = m.read_u8, m.read_u16, m.read_u32, m.write_u8, m.write_u16
local frame_number, scr_dev = L.screen.frame_number, L.screen
local abs = math.abs
local START = tonumber(os.getenv("FF_BOT_START") or "2450")
local GOD = (os.getenv("FF_BOT_GOD") or "1") == "1"
local CAMSTOP = tonumber(os.getenv("FF_BOT_CAM") or "")
local HP0 = os.getenv("FF_BOT_HP0") == "1"
local LANEFIX = os.getenv("FF_BOT_LANEFIX") == "1"
local PROPS = os.getenv("FF_BOT_PROPS") == "1"
local LURE = os.getenv("FF_BOT_LURE") == "1"
local lure_since
local UNSTICK = os.getenv("FF_BOT_UNSTICK") == "1"
local PROPRANGE = tonumber(os.getenv("FF_BOT_PROPRANGE") or "60") -- swing at a prop only within this dx; walking stops at 45, so a value above it can swing out of reach for ever (stage 3: whiffing at dx 58)
local unstick_x, unstick_still, unstick_until, unstick_dir = nil, 0, -1, "up"
local STAGESTOP = tonumber(os.getenv("FF_BOT_STAGE") or "")
local LEAVE = tonumber(os.getenv("FF_BOT_LEAVE") or "")
local SAVEPFX = os.getenv("FF_SAVE_PREFIX")
local STOPFRAME = tonumber(os.getenv("FF_BOT_STOPF") or "")
local SCRSTOP = tonumber(os.getenv("FF_BOT_SCRIPT") or "")
local LOGF = os.getenv("FF_BOT_LOG") and io.open(os.getenv("FF_BOT_LOG"), "w")
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local P1 = 0xff8568
local pools = { { "2", 0xff86e8, 13 }, { "6", 0xff90a8, 6 }, { "4", 0xff9528, 8 }, { "8", 0xff9b28, 30 }, { "a", 0xffb2e8, 16 },
                { "12", 0xffbee8, 10 }, { "14", 0xffc668, 30, 0x40 } }
local seen = {}
local held = {}
local function set(field, v) if held[field] ~= v then held[field] = v; L.F[field]:set_value(v) end end
local lane_py, lane_still = nil, 0
local f_now, prop_first_until = 0, -1
local ne_x, ne_y, ne_a, ne_prop -- the target nearest() found (ne_a == nil: none), kept in upvalues instead of a table per frame
local function nearest()
  local px, py = ru16(m, P1 + 6), ru16(m, P1 + 14)
  local bd
  ne_a = nil
  -- pool 2 (13 fighters) then pool 4 (8 records: the boss DAMND is one), strict < so the first of equals wins. Alive: in use, not new, state 0 or 2 (4 dying, 6 gone), health word not negative
  -- (a fighter dies at hp < 0: HOLLY WOOD sits at hp 0 and still fights; DAMND too, see FF_BOT_HP0). y is the ground line +14 (a jumping boss has +10 high in the air).
  for pass = 1, 2 do
    local base, cnt, p2
    if pass == 1 then base, cnt, p2 = 0xff86e8, 13, true else base, cnt, p2 = 0xff9528, 8, false end
    for i = 0, cnt - 1 do
      local a = base + 0xc0 * i
      local b0 = ru8(m, a)
      if b0 ~= 0 and b0 < 0x80 then
        local st = ru8(m, a + 2)
        if st == 0 or st == 2 then
          local hp = ru16(m, a + 24)
          if hp < 0x8000 and (HP0 or p2 or hp > 0) then
            local ex, ey = ru16(m, a + 6), ru16(m, a + 14)
            local d = abs(ex - px) + 2 * abs(ey - py)
            if not bd or d < bd then ne_x, ne_y, ne_a, ne_prop, bd = ex, ey, a, false, d end
          end
        end
      end
    end
  end
  if PROPS and (not ne_a or f_now < prop_first_until) then -- no fighter (or stuck: FF_BOT_UNSTICK): a breakable prop (pool $a) just ahead blocks the walk (three barrels held the bot in stage 1 area 1)
    local pbd, pa, pxx, pyy
    for i = 0, 15 do
      local a = 0xffb2e8 + 0xc0 * i
      if ru8(m, a) == 1 and ru8(m, a + 2) == 2 and (not UNSTICK or ru8(m, a + 19) < 0x10 or ru8(m, a + 19) > 0x11) then -- kinds 16 and 17 are FLAME hazards (stage 3), not breakable
        local ex, ey = ru16(m, a + 6), ru16(m, a + 10) -- props keep no ground line copy at +14
        local dx = ex - px
        if dx >= -20 and dx < 120 then
          local d = abs(dx) + 2 * abs(ey - py)
          if not pbd or d < pbd then pa, pxx, pyy, pbd = a, ex, ey, d end
        end
      end
    end
    if pa then ne_x, ne_y, ne_a, ne_prop = pxx, pyy, pa, true end
  end
  return px, py
end
local DUMPS = {}
for n in string.gmatch(os.getenv("FF_BOT_DUMP") or "", "%d+") do DUMPS[tonumber(n)] = true end
local last_b1 = -100
local NP = #pools
local fmt, concat = string.format, table.concat
emu.register_frame_done(function()
  local f = frame_number(scr_dev)
  if f < START then return end
  local cam = ru16(m, 0xff8412)
  local scr = ru32(m, 0xffb1ee)
  if GOD then
    local mx = ru16(m, P1 + 28)
    if ru16(m, P1 + 24) < mx and ru8(m, P1 + 2) == 2 then wu16(m, P1 + 24, mx) end
    if ru8(m, P1 + 128) < 2 then wu8(m, P1 + 128, 2) end
  end
  f_now = f
  local px, py = nearest()
  local e = ne_a
  local right, left, up, down = 0, 0, 0, 0
  if LURE and e and not ne_prop and ((ne_x < cam and ne_x >= cam - 0x80) or (ne_x >= cam + 0x180 and ne_x < cam + 0x200)) then lure_since = lure_since or f else lure_since = nil end
  if lure_since and f - lure_since >= 120 then
    local tx = cam + 0xc0
    if px < tx - 12 then right = 1 elseif px > tx + 12 then left = 1 end
  elseif e then
    local dx, dy = ne_x - px, ne_y - py
    -- Measured (py/twoplayer, 6 of 6 runs): Up RAISES +10 and +14 by 0.8 px per frame, lane limits `$10` and `$3f`. The default mapping below is the opposite and is kept only because the
    -- states sb_boss and sb_s1 come from it (enemies walk up to the bot, so it still kills them); FF_BOT_LANEFIX=1 selects the correct one.
    if LANEFIX then
      if dy > 5 then up = 1 elseif dy < -5 then down = 1 end
    else
      if dy > 5 then down = 1 elseif dy < -5 then up = 1 end
    end
    if abs(dx) > (ne_prop and 45 or 40) then if dx > 0 then right = 1 else left = 1 end end
    -- a prop does not walk to the bot: swing only when the lane is aligned (a swing at |dy| 6..12 whiffs and its animation blocks the lane change for ever: stage 3 area 0, a DRUMCAN 12 px off);
    -- if the lane has not moved for 40 frames while misaligned (terrain row, stage 2 area 2's door at dy 9) swing from where the bot stands
    if ne_prop and abs(dy) > 5 and py == lane_py then lane_still = lane_still + 1 else lane_still = 0 end
    lane_py = py
    local ry = (ne_prop and UNSTICK) and (lane_still >= 40 and 12 or 5) or 8
    if abs(dx) <= (ne_prop and PROPRANGE or 60) and abs(dy) <= ry and f - last_b1 >= 14 then last_b1 = f end
  else
    right = 1
  end
  if UNSTICK then
    if px == unstick_x and right == 1 and left == 0 then unstick_still = unstick_still + 1 else unstick_still = 0 end
    unstick_x = px
    if unstick_still >= 45 then unstick_still = 0; unstick_until = f + 40; prop_first_until = f + 600; unstick_dir = (unstick_dir == "down") and "up" or "down" end
    if f < unstick_until then if unstick_dir == "down" then down, up = 1, 0 else up, down = 1, 0 end end
  end
  set("right", right); set("left", left); set("up", up); set("down", down)
  set("b1", (f - last_b1 < 5) and 1 or 0)
  if LOGF then
    local wrote = false
    if f % 10 == 0 then
      local c = {}
      for pi = 1, NP do
        local p = pools[pi]
        local n, base, stride = 0, p[2], p[4] or 0xc0
        for i = 0, p[3] - 1 do if ru8(m, base + stride * i) ~= 0 then n = n + 1 end end
        c[pi] = p[1] .. "=" .. n
      end
      LOGF:write(fmt("%d sa=%02x%02x cam=%04x scr=%06x x=%04x y=%04x st=%02x%02x hp=%04x lives=%02x tgt=%s %s\n", f, ru8(m, 0xff80be), ru8(m, 0xff80bf), cam, scr, px, py,
        ru8(m, P1 + 2), ru8(m, P1 + 3), ru16(m, P1 + 24), ru8(m, P1 + 128), e and fmt("%06x:%04x,%04x%s", ne_a, ne_x, ne_y, ne_prop and "p" or "") or "-", concat(c, " ")))
      wrote = true
    end
    for pi = 1, NP do
      local p = pools[pi]
      local base, stride = p[2], p[4] or 0xc0
      for i = 0, p[3] - 1 do
        local a = base + stride * i
        if ru8(m, a) ~= 0 then
          if not seen[a] then
            seen[a] = true
            LOGF:write(fmt("S %d pool=%s rec=%d %06x kind=%02x ch=%02x ent=%02x lvl=%02x x=%04x y=%04x hp=%04x cam=%04x scr=%06x\n", f, p[1], i, a,
              ru8(m, a + 19), ru8(m, a + 20), ru8(m, a + 21), ru8(m, a + 96), ru16(m, a + 6), ru16(m, a + 10), ru16(m, a + 24), cam, scr))
            wrote = true
          end
        else seen[a] = nil end
      end
    end
    if wrote then LOGF:flush() end -- an empty buffer flushed nothing before either
  end
  if LOGF and DUMPS[f] then
    for _, p in ipairs(pools) do
      for i = 0, p[3] - 1 do
        local a = p[2] + (p[4] or 0xc0) * i
        if m:read_u8(a) ~= 0 then
          LOGF:write(string.format("D %d pool=%s rec=%d %06x b0=%02x b1=%02x st=%02x%02x kind=%02x ch=%02x x=%04x y=%04x hp=%04x p92=%06x\n", f, p[1], i, a,
            m:read_u8(a), m:read_u8(a + 1), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 19), m:read_u8(a + 20), m:read_u16(a + 6), m:read_u16(a + 10),
            m:read_u16(a + 24), m:read_u32(a + 92) & 0xffffff))
        end
      end
    end
    LOGF:flush()
  end
  local stg = ru8(m, 0xff80be)
  if (CAMSTOP and cam >= CAMSTOP) or (SCRSTOP and scr >= SCRSTOP) or (STAGESTOP and stg >= STAGESTOP) or (LEAVE and stg ~= LEAVE and f > 1) or (STOPFRAME and f >= STOPFRAME) then
    if LOGF then LOGF:write(string.format("STOP %d cam=%04x scr=%06x stage=%d\n", f, cam, scr, stg)); LOGF:close() end
    local sname = SAVEPFX and (SAVEPFX .. ((LEAVE and stg == LEAVE) and ("stuck" .. stg) or stg)) or os.getenv("FF_SAVE") -- a run that hit the frame limit never overwrites the state it started from
    if sname then
      L.write(string.format("%s/%s_ram.bin", out, sname), L.ram())
      L.write(string.format("%s/%s_gfxram.bin", out, sname), L.region(0x900000, 0x30000))
      L.screen:snapshot(sname .. ".png")
      manager.machine:save(sname)
    end
    manager.machine:exit()
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
