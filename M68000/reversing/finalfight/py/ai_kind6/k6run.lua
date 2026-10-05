-- k6run.lua (agent D): load a state, inject a synthetic stage-script group through the game's own spawner, run N frames,
-- dump pool 2 + players per frame to <out>/<tag>_frames.bin (13*192 + 2*192 bytes per frame) and a text log.
-- env: FF_DIR (lua dir), FF_OUT, K6_LOAD (state, default k6_pre), K6_TAG, K6_FRAMES (default 600), K6_SPAWN (see below),
--      K6_PLAN (lua file returning {{relframe, field, level}...}), K6_SHOTS (list "a-b,c-d" of relative frames to snapshot)
-- K6_SPAWN = "char:sub:x:y[,char:sub:x:y...]" kind-6 entries (tag 2, kind 6, +20=char, +21=sub) at relative frame 2.
--   entries are written as a stage-script group at $ffe000 and the script record at $ffb1e8 is pointed at it
--   (state 2, trigger word 0 = satisfied at once), so the game's own $5aea/$5e36/$5ee6/$3892 create the record.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local out = os.getenv("FF_OUT")
local tag = os.getenv("K6_TAG") or "k6"
local nframes = tonumber(os.getenv("K6_FRAMES") or "600")
local loadname = os.getenv("K6_LOAD") or "k6_pre"
local plan = os.getenv("K6_PLAN") and dofile(os.getenv("K6_PLAN")) or {}
local shots = {}
for a, b in string.gmatch(os.getenv("K6_SHOTS") or "", "(%d+)-(%d+)") do shots[#shots+1] = {tonumber(a), tonumber(b)} end
local spawn = {}
for c, s, x, y in string.gmatch(os.getenv("K6_SPAWN") or "", "(%d+):(%d+):(%-?%d+):(%d+)") do spawn[#spawn+1] = {tonumber(c), tonumber(s), tonumber(x), tonumber(y)} end
local fb = io.open(string.format("%s/%s_frames.bin", out, tag), "wb")
local loaded, f0 = false, nil
local last_inject, respawns = 0, 0
local A5 = 0xff8000
local SCR = 0xffe000
local function w16(a, v) m:write_u16(a, v) end
local function w8(a, v) m:write_u8(a, v) end
local function w32(a, v) m:write_u32(a, v) end
local function inject()
  local p = SCR
  w16(p, 0x0000); p = p + 2                 -- trigger word: 0 <= camera x
  w16(p, 0x0400); p = p + 2                 -- w16 timeout
  w16(p, 0x0000); p = p + 2                 -- w12 kills expected
  w16(p, 0x0000); p = p + 2                 -- w18
  w16(p, 0x0001); p = p + 2                 -- flag (non zero: no 278(A5))
  local endp = p + 4 + 16 * #spawn
  w32(p, endp); p = p + 4                   -- 24(A6): pointer to the end command
  for i, e in ipairs(spawn) do
    w16(p, i == 1 and 1 or 20); w16(p+2, 0)  -- delay, count flag (0: not registered as a kill target)
    local ex = e[3]
    if os.getenv("K6_REL") == "1" then ex = (m:read_u16(0xff8412) + e[3]) & 0xffff end
    w16(p+4, ex); w16(p+6, e[4])
    w8(p+8, 2); w8(p+9, 6); w8(p+10, e[1]); w8(p+11, e[2])
    w8(p+12, 0); w8(p+13, 0); w8(p+14, 0xff); w8(p+15, tonumber(os.getenv("K6_B15") or "0"))
    p = p + 16
  end
  w16(p, 0x800a); p = p + 2                 -- end command $a: wait, back to the trigger loop
  w16(p, 0x7fff)                            -- next trigger: never
  local r = 0xffb1e8
  w8(r+2, 2); w8(r+3, 0); w8(r+4, 0); w8(r+5, 0); w8(r+22, 0)
  w32(r+6, SCR); w16(r+10, 2)
end
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then
    loaded = true
    manager.machine:load(loadname)
    return
  end
  if not f0 then f0 = f end
  local rel = f - f0
  if rel == 2 and #spawn > 0 then inject(); last_inject = rel end
  if rel == 2 and os.getenv("K6_NATURAL") then
    -- point the stage-script record at a ROM group (hex address of its trigger word) and move the camera and Cody to the trigger x
    local r = 0xffb1e8
    local cam = tonumber(os.getenv("K6_CAMX") or "0")
    w8(r+2, 2); w8(r+3, 0); w8(r+4, 0); w8(r+5, 0); w8(r+22, 0)
    w32(r+6, tonumber(os.getenv("K6_NATURAL"), 16)); w16(r+10, 2)
    w16(0xff8412, cam); w16(0xff8568 + 6, cam + 0x60); w16(0xff8568 + 14, m:read_u16(0xff8568 + 10))
  end
  local respawn = tonumber(os.getenv("K6_RESPAWN") or "0")
  if respawn > 0 and rel > 2 and rel - last_inject >= respawn then
    local alive = false
    for i = 0, 12 do local a = 0xff86e8 + 0xc0 * i; if m:read_u8(a) ~= 0 and m:read_u8(a + 19) == 6 then alive = true end end
    if not alive then inject(); last_inject = rel; respawns = respawns + 1 end
  end
  for _, e in ipairs(plan) do if e[1] == rel then L.F[e[2]]:set_value(e[3]) end end
  for _, s in ipairs(shots) do if rel >= s[1] and rel <= s[2] then L.screen:snapshot(string.format("%s_%04d.png", tag, rel)) end end
  -- K6_POKE="rel|off=val,off=val;rel|..." byte pokes (decimal offsets, hex values) into the first live kind-6 record at relative frame rel
  if os.getenv("K6_POKE") then
    for spec in string.gmatch(os.getenv("K6_POKE"), "[^;]+") do
      local r, list = spec:match("^(%d+)|(.*)$")
      if rel == tonumber(r) then
        for i = 0, 12 do
          local a = 0xff86e8 + 0xc0 * i
          if m:read_u8(a) ~= 0 and m:read_u8(a + 19) == 6 then
            for off, val in string.gmatch(list, "(%d+)=(%x+)") do m:write_u8(a + tonumber(off), tonumber(val, 16)) end
            break
          end
        end
      end
    end
  end
  -- K6_RAM="rel|addr:val,addr:val;..." byte pokes into RAM (hex) at a relative frame
  if os.getenv("K6_RAM") then
    for spec in string.gmatch(os.getenv("K6_RAM"), "[^;]+") do
      local r, list = spec:match("^(%d+)|(.*)$")
      if rel == tonumber(r) then
        for a, v in string.gmatch(list, "(%x+):(%x+)") do m:write_u8(tonumber(a, 16), tonumber(v, 16)) end
      end
    end
  end
  -- K6_FORCE="rel:id,rel:id": poke the first kind-6 record into the attack sub-state running attack id (4(A6)=4 skips the approach)
  if os.getenv("K6_FORCE") then
    for r, id, dx in string.gmatch(os.getenv("K6_FORCE"), "(%d+):(%d+):?(%-?%d*)") do
      if rel == tonumber(r) then
        local base = 0x3901c
        for i = 0, 12 do
          local a = 0xff86e8 + 0xc0 * i
          if m:read_u8(a) ~= 0 and m:read_u8(a + 19) == 6 then
            local off = m:read_u16(base + 2 * tonumber(id))
            if dx ~= "" then
              local px, py = m:read_u16(0xff8568 + 6), m:read_u16(0xff8568 + 10)
              m:write_u16(a + 6, (px + tonumber(dx)) & 0xffff); m:write_u16(a + 10, py); m:write_u16(a + 14, py)
              m:write_u8(a + 46, tonumber(dx) >= 0 and 1 or 0)
            end
            m:write_u8(a + 3, 4); m:write_u8(a + 4, (tonumber(id) <= 10 and os.getenv("K6_APPROACH") == "1") and 2 or 4); m:write_u8(a + 5, 0)
            m:write_u8(a + 149, tonumber(id)); m:write_u32(a + 150, base + off); m:write_u8(a + 147, 1)
            m:write_u8(a + 161, tonumber(os.getenv("K6_F161") or "1"))
            print(string.format("force rel %d id %d at %06x ptr %06x", rel, tonumber(id), a, base + off))
          end
        end
      end
    end
  end
  -- optional helpers: K6_IMMORTAL=1 refills Cody's health word and shadow when below 60; K6_BOT=1 drives Cody at the nearest tag-2 record
  if os.getenv("K6_IMMORTAL") == "1" then
    local hp = m:read_u16(0xff8568 + 24)
    if hp < 60 or hp > 0x8000 then m:write_u16(0xff8568 + 24, 144); m:write_u16(0xff8568 + 26, 144) end
  end
  if os.getenv("K6_BOT") == "1" then
    local px, py = m:read_u16(0xff8568 + 6), m:read_u16(0xff8568 + 10)
    local best, bd = nil, 1e9
    for i = 0, 12 do
      local a = 0xff86e8 + 0xc0 * i
      if m:read_u8(a) ~= 0 and m:read_u8(a + 2) == 2 and m:read_u16(a + 24) < 0x8000 then
        local d = math.abs(m:read_u16(a + 6) - px)
        if d < bd then bd, best = d, a end
      end
    end
    local F = L.F
    for _, k in ipairs({ "left", "right", "up", "down" }) do F[k]:set_value(0) end
    if best then
      local ex, ey = m:read_u16(best + 6), m:read_u16(best + 10)
      local dx = ex - px
      local dy = ey - py
      if dy > 128 then dy = dy - 65536 end
      if dy < -128 then dy = dy + 65536 end
      if dx > 32768 then dx = dx - 65536 end
      if math.abs(dy) > 5 then F[dy > 0 and "up" or "down"]:set_value(1) end
      if math.abs(dx) > 44 then F[dx > 0 and "right" or "left"]:set_value(1)
      elseif math.abs(dy) <= 8 then if rel % 16 == 0 then F.b1:set_value(1) elseif rel % 16 == 4 then F.b1:set_value(0) end end
    else F.b1:set_value(0) end
  end
  fb:write(L.region(0xff86e8, 13 * 0xc0))
  fb:write(L.region(0xff8568, 2 * 0xc0))
  fb:write(L.region(0xff8000, 0x200))   -- A5 globals low part
  if rel >= nframes then
    L.write(string.format("%s/%s_ram.bin", out, tag), L.ram())
    if os.getenv("K6_SAVE") then manager.machine:save(os.getenv("K6_SAVE")) end
    fb:close(); manager.machine:exit()
  end
end)
