-- dm.lua: Agent A (pass 4) harness. Loads a saved state, plays player 1 with an optional bot, pokes, logs the pool-4 boss and writes per-frame RAM dumps and breakpoint counts.
-- Environment (all optional except DM_LOAD):
--   DM_LOAD     state name in <run>/sta/ffightuc/ (without .sta)
--   DM_STOPF    absolute frame at which to exit (default load frame + 600)
--   DM_BOT      0 (default): no input except DM_KEYS; 1: the stagebot rule (walk right when nobody near, close on the nearest pool 2 / pool 4 fighter, tap Button 1)
--               2: like 1 but only tap when the boss (pool 4) is the nearest, and never walk away
--   DM_GOD      1 (default): top Cody's +24 up to +28 each frame in state 2 and keep lives >= 2 (a poke; reported)
--   DM_KEYS     "field:from-to,field:from-to" absolute-frame input levels (right, left, up, down, b1, b2, b3)
--   DM_POKES    "frame:hexaddr:hexbytes,..." byte pokes applied at the end of the frame (before the bot)
--   DM_LOG      text log file: one line per DM_LOGN frames with the boss record fields
--   DM_LOGN     log interval (default 10)
--   DM_DUMP     binary per-frame dump file: u32 frame, then ranges DM_RANGES (default "ff8000-ffb300"), from frame DM_DUMPLO (default load frame)
--   DM_SAVE     state name to save (and RAM dump <out>/<name>_ram.bin) when: DM_SAVEF reached, or boss hp (+24 of $ff9a68) <= DM_SAVEHP
--   DM_ADDRS    hex addresses to count with bpset (needs DM_DEBUG=1 in mame.sh); DM_HITLOG per-hit log "frame addr D0 D1 A0 A1 A6"
--   DM_OUT      output directory (default <FF_DIR>/..)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local dbg = manager.machine.debugger
local BOSS = tonumber(os.getenv("DM_BOSS") or "ff9a68", 16)
local P1 = 0xff8568
local out = os.getenv("DM_OUT") or "."
local load_name = assert(os.getenv("DM_LOAD"))
local STOPF = tonumber(os.getenv("DM_STOPF") or "")
local BOT = tonumber(os.getenv("DM_BOT") or "0")
local GOD = (os.getenv("DM_GOD") or "1") == "1"
local LOGN = tonumber(os.getenv("DM_LOGN") or "10")
local logf = os.getenv("DM_LOG") and io.open(os.getenv("DM_LOG"), "w")
local keys = {}
for fld, a, b in string.gmatch(os.getenv("DM_KEYS") or "", "(%a%w*):(%d+)-(%d+)") do keys[#keys + 1] = { fld, tonumber(a), tonumber(b) } end
local pokes = {}
for f, a, h in string.gmatch(os.getenv("DM_POKES") or "", "(%d+):(%x+):(%x+)") do pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), h } end
local ranges = {}
for a, b in string.gmatch(os.getenv("DM_RANGES") or "ff8000-ffb300", "(%x+)-(%x+)") do ranges[#ranges + 1] = { tonumber(a, 16), tonumber(b, 16) } end
local dumpf = os.getenv("DM_DUMP") and io.open(os.getenv("DM_DUMP"), "wb")
local dumplo = tonumber(os.getenv("DM_DUMPLO") or "0")
local savename, savef, savehp = os.getenv("DM_SAVE"), tonumber(os.getenv("DM_SAVEF") or ""), tonumber(os.getenv("DM_SAVEHP") or "")
local saved = false
local held = {}
-- DM_SPAWN="kind:ch:x:y:lvl@frame,..." : a pool-4 record built like $390a + $61f8 (tag 4: pop the free stack word list at 20280(A5)/20282(A5), +0 = 1, x, y, +18 = 4, +19 = kind, +20 = ch, +96 = lvl (-1: 169(A5)))
local spawns = {}
for k, c, x, y, l, f in string.gmatch(os.getenv("DM_SPAWN") or "", "(%d+):(%d+):(%d+):(%d+):(-?%d+)@(%d+)") do spawns[#spawns + 1] = { tonumber(k), tonumber(c), tonumber(x), tonumber(y), tonumber(l), tonumber(f) } end
local function spawn4(k, c, x, y, l)
  local A5 = 0xff8000
  if m:read_u16(A5 + 20280) == 0 then return nil end
  local p = m:read_u32(A5 + 20282)
  local a = m:read_u16(p); if a >= 0x8000 then a = a | 0xffff0000 end
  a = a & 0xffffff
  m:write_u16(p, 0); m:write_u32(A5 + 20282, p + 2); m:write_u16(A5 + 20280, m:read_u16(A5 + 20280) - 1)
  for o = 0, 191 do m:write_u8(a + o, 0) end
  m:write_u8(a, 1); m:write_u16(a + 6, x); m:write_u16(a + 10, y); m:write_u8(a + 18, 4); m:write_u8(a + 19, k); m:write_u8(a + 20, c)
  m:write_u8(a + 96, l < 0 and m:read_u8(A5 + 169) or l)
  return a
end
local function set(field, v) if held[field] ~= v then held[field] = v; L.F[field]:set_value(v) end end
-- breakpoints
local wps = {}
local addrs, counts, hitlog = {}, {}, os.getenv("DM_HITLOG") and io.open(os.getenv("DM_HITLOG"), "w")
local bpdone, seen = false, 0
emu.register_periodic(function()
  if not bpdone then
    bpdone = true
    for a in string.gmatch(os.getenv("DM_ADDRS") or "", "(%x+)") do
      addrs[#addrs + 1] = a
      dbg:command(string.format('bpset %s,1,{printf "H %s %%08x %%08x %%08x %%08x %%08x\\n",d0,d1,a0,a1,a6; g}', a, a))
    end
    for a, n in string.gmatch(os.getenv("DM_WPS") or "", "(%x+):(%d+)") do
      wps[#wps + 1] = a
      dbg:command(string.format('wpset %s,%s,w,1,{printf "W %s %%08x %%08x %%08x\\n",pc,wpdata,a6; g}', a, n, a))
    end
    if #addrs > 0 or #wps > 0 then dbg:command("go") end
  end
end)
local function nearest()
  local px, py = m:read_u16(P1 + 6), m:read_u16(P1 + 14)
  local best, bd
  for _, p in ipairs({ { 0xff86e8, 13 }, { 0xff9528, 8 } }) do
    for i = 0, p[2] - 1 do
      local a = p[1] + 0xc0 * i
      local st, hp = m:read_u8(a + 2), m:read_u16(a + 24)
      if BOT == 2 and p[1] ~= 0xff9528 then
      elseif m:read_u8(a) ~= 0 and m:read_u8(a) < 0x80 and (st == 0 or st == 2) and hp < 0x8000 then
        local ex, ey = m:read_u16(a + 6), m:read_u16(a + 14)
        local d = math.abs(ex - px) + 2 * math.abs(ey - py)
        if not bd or d < bd then best, bd = { x = ex, y = ey, a = a }, d end
      end
    end
  end
  return px, py, best
end
local last_b1 = -100
local loaded, f0 = false, nil
local function bossline(f)
  local b = BOSS
  local function u8(o) return m:read_u8(b + o) end
  return string.format("%d cam=%04x scr=%06x cx=%04x cy=%04x chp=%04x | b0=%02x st=%02x%02x %02x%02x%02x x=%04x y=%04x g=%04x hp=%04x/%04x 41=%02x 63=%02x 66=%02x 148=%02x 160=%02x 161=%02x 163=%02x 164=%02x 165=%02x 168=%02x 169=%02x 174=%02x f44=%02x%02x",
    f, m:read_u16(0xff8412), m:read_u32(0xffb1ee), m:read_u16(P1 + 6), m:read_u16(P1 + 14), m:read_u16(P1 + 24),
    u8(0), u8(2), u8(3), u8(4), u8(5), u8(6 + 0) * 0 + 0, m:read_u16(b + 6), m:read_u16(b + 10), m:read_u16(b + 14), m:read_u16(b + 24), m:read_u16(b + 28),
    u8(41), u8(63), u8(66), u8(148), u8(160), u8(161), u8(163), u8(164), u8(165), u8(168), u8(169), u8(174), u8(44), u8(45))
end
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then
    loaded = true
    manager.machine:load(load_name)
    return
  end
  if not f0 then f0 = f; STOPF = STOPF or (f + 600) end
  if logf and (f - f0) % LOGN == 0 then logf:write(bossline(f) .. "\n"); logf:flush() end
  if dumpf and f >= dumplo then
    local t = { string.char((f >> 24) & 255, (f >> 16) & 255, (f >> 8) & 255, f & 255) }
    for _, r in ipairs(ranges) do
      for a = r[1], r[2] - 1, 2 do local v = m:read_u16(a); t[#t + 1] = string.char(v >> 8, v & 255) end
    end
    dumpf:write(table.concat(t))
  end
  local log = dbg and dbg.consolelog
  if log and (#addrs > 0 or #wps > 0) then
    for i = seen + 1, #log do
      local wa, wpc, wv, wa6 = log[i]:match("^W (%x+) (%x+) (%x+) (%x+)")
      if wa and hitlog then hitlog:write(string.format("%d W %s pc=%s val=%s a6=%s\n", f, wa, wpc, wv, wa6)) end
      local a, d0, d1, a0, a1, a6 = log[i]:match("^H (%x+) (%x+) (%x+) (%x+) (%x+) (%x+)")
      if a then
        counts[a] = (counts[a] or 0) + 1
        if hitlog then hitlog:write(string.format("%d %s %s %s %s %s %s\n", f, a, d0, d1, a0, a1, a6)) end
      end
    end
    seen = #log
  end
  for sf in string.gmatch(os.getenv("DM_SHOT") or "", "(%d+)") do
    if tonumber(sf) == f then L.screen:snapshot(string.format("%s_%d.png", os.getenv("DM_SHOTNAME") or "dm", f)) end
  end
  if not saved and savename and ((savef and f >= savef) or (savehp and m:read_u16(BOSS + 24) <= savehp and m:read_u16(BOSS + 24) > 0 and m:read_u8(BOSS) ~= 0)) then
    saved = true
    L.write(string.format("%s/%s_ram.bin", out, savename), L.ram())
    L.screen:snapshot(savename .. ".png")
    manager.machine:save(savename)
    if logf then logf:write(string.format("SAVED %s at %d\n", savename, f)) end
  end
  if f >= STOPF then
    if logf then logf:write(string.format("END %d\n", f)); for _, a in ipairs(addrs) do logf:write(string.format("COUNT %s %d\n", a, counts[a] or 0)) end; logf:close() end
    if hitlog then hitlog:close() end
    if dumpf then dumpf:close() end
    manager.machine:exit()
  end
  for _, sp in ipairs(spawns) do
    if sp[6] == f then
      local a = spawn4(sp[1], sp[2], sp[3], sp[4], sp[5])
      if logf then logf:write(string.format("SPAWN %d kind %d at %s\n", f, sp[1], a and string.format("%06x", a) or "none")) end
    end
  end
  for _, p in ipairs(pokes) do
    if p[1] == f then
      local h = p[3]
      for i = 1, #h, 2 do m:write_u8(p[2] + (i - 1) // 2, tonumber(h:sub(i, i + 1), 16)) end
    end
  end
  if GOD then
    local mx = m:read_u16(P1 + 28)
    if m:read_u16(P1 + 24) < mx and m:read_u8(P1 + 2) == 2 then m:write_u16(P1 + 24, mx) end
    if m:read_u8(P1 + 128) < 2 then m:write_u8(P1 + 128, 2) end
  end
  local lvl = {}
  if BOT > 0 then
    local px, py, e = nearest()
    local right, left, up, down = 0, 0, 0, 0
    if e then
      local dx, dy = e.x - px, e.y - py
      if dy > 5 then down = 1 elseif dy < -5 then up = 1 end
      if math.abs(dx) > 40 then if dx > 0 then right = 1 else left = 1 end end
      if math.abs(dx) <= 60 and math.abs(dy) <= 8 and f - last_b1 >= 14 then last_b1 = f end
    elseif BOT == 1 then right = 1 end
    lvl.right, lvl.left, lvl.up, lvl.down = right, left, up, down
    lvl.b1 = (f - last_b1 < 5) and 1 or 0
  end
  for _, k in ipairs(keys) do lvl[k[1]] = lvl[k[1]] or 0; if f >= k[2] and f < k[3] then lvl[k[1]] = 1 end end
  for fld, v in pairs(lvl) do set(fld, v) end
end)
