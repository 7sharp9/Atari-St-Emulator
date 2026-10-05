-- trans.lua: log the phase / stage / area / player-state transitions while stagebot.lua plays.
-- Environment: everything stagebot.lua takes, plus
--   FF_TR_LOG   output file (default <FF_OUT>/trans.log)
--   FF_TR_TAPS  1 (default): write taps with the writing PC on 0..9(A5) (phase words), 190..193(A5), 278..281(A5), 290..301(A5), the camera x 1042(A5), its limits 1078..1081(A5),
--               its modes 1086/1087(A5) and the camera hook step 1100(A5)
--   FF_TR_POKE  comma list "frame:addr:bytes" pokes (hex addr, hex bytes), applied at frame end before the bot runs
-- Lines: "C f <changed fields>" every frame where a tracked field changed; "T f pc addr mask data" for taps; "P f" every 30 frames: position.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local fh = assert(io.open(os.getenv("FF_TR_LOG") or (out .. "/trans.log"), "w"))
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local A5 = 0xff8000
local P1 = 0xff8568
local P2 = 0xff8628
local function u8(a) return m:read_u8(a) end
local function u16(a) return m:read_u16(a) end
local function u32(a) return m:read_u32(a) end
local fields = {
  { "ph", function() return u16(A5) end, "%04x" }, { "ph2", function() return u16(A5 + 2) end, "%04x" }, { "ph4", function() return u16(A5 + 4) end, "%04x" },
  { "ph6", function() return u16(A5 + 6) end, "%04x" }, { "ph8", function() return u16(A5 + 8) end, "%04x" },
  { "sa", function() return u16(A5 + 190) end, "%04x" }, { "seq", function() return u8(A5 + 193) end, "%02x" },
  { "278", function() return u8(A5 + 278) end, "%02x" }, { "279", function() return u8(A5 + 279) end, "%02x" },
  { "290", function() return u8(A5 + 290) end, "%02x" }, { "291", function() return u8(A5 + 291) end, "%02x" },
  { "297", function() return u8(A5 + 297) end, "%02x" }, { "298", function() return u8(A5 + 298) end, "%02x" }, { "299", function() return u8(A5 + 299) end, "%02x" },
  { "300", function() return u8(A5 + 300) end, "%02x" },
  { "p1st", function() return u16(P1 + 2) end, "%04x" }, { "p1s45", function() return u16(P1 + 4) end, "%04x" },
  { "p2st", function() return u16(P2 + 2) end, "%04x" }, { "p1use", function() return u8(P1) end, "%02x" }, { "lives", function() return u8(P1 + 128) end, "%02x" },
  { "time", function() return u8(A5 + 175) end, "%02x" },
  { "score", function() return u32(P1 + 132) end, "%08x" },
  { "scr", function() return u32(0xffb1ee) end, "%06x" }, { "sx", function() return u16(0xffb1e8 + 2) end, "%04x" }, { "pause", function() return u8(0xffb1e8 + 22) end, "%02x" },
  { "21416", function() return u8(A5 + 21416) end, "%02x" }, { "21610", function() return u8(A5 + 21610) end, "%02x" }, { "127", function() return u8(A5 + 127) end, "%02x" },
  { "22162", function() return u16(A5 + 22162) end, "%04x" }, { "22164", function() return u16(A5 + 22164) end, "%04x" },
  { "rlim", function() return u16(A5 + 1078) end, "%04x" }, { "llim", function() return u16(A5 + 1080) end, "%04x" }, { "cmode", function() return u8(A5 + 1086) end, "%02x" },
  { "cstep", function() return u8(A5 + 1100) end, "%02x" }, { "cst", function() return u8(A5 + 1038) end, "%02x" }, { "cam2", function() return u16(A5 + 1170) end, "%04x" },
  { "v116", function() return u16(A5 + 116) end, "%04x" }, { "v118", function() return u16(A5 + 118) end, "%04x" }, { "v120", function() return u16(A5 + 120) end, "%04x" },
  { "rank", function() return u16(A5 + 168) end, "%04x" }, { "rank172", function() return u16(A5 + 172) end, "%04x" }, { "rankfl", function() return u16(A5 + 188) end, "%04x" },
  { "pl2", function() return u16(0xffb1a8 + 2) end, "%04x" }, { "280", function() return u32(A5 + 280) end, "%08x" }, { "284", function() return u32(A5 + 284) end, "%08x" },
}
local last = {}
-- write taps
taps = {}
if (os.getenv("FF_TR_TAPS") or "1") == "1" then
  for _, r in ipairs({ { A5, A5 + 9 }, { A5 + 190, A5 + 193 }, { A5 + 278, A5 + 281 }, { A5 + 290, A5 + 301 }, { A5 + 1042, A5 + 1043 }, { A5 + 1078, A5 + 1081 }, { A5 + 1086, A5 + 1087 }, { A5 + 1100, A5 + 1101 } }) do
    taps[#taps + 1] = m:install_write_tap(r[1], r[2], "w" .. r[1], function(off, data, mask)
      local ok, e = pcall(function() fh:write(string.format("T %d pc=%06x a=%06x m=%04x d=%04x\n", L.frame(), pcreg.value, off, mask, data)) end)
      if not ok then print("TAP ERR " .. tostring(e)) end
    end)
  end
end
-- spawn census of the pools (every frame): "S f pool rec kind +20 +21 x y"
local pools = { { "2", 0xff86e8, 13 }, { "6", 0xff90a8, 6 }, { "4", 0xff9528, 8 }, { "8", 0xff9b28, 30 }, { "a", 0xffb2e8, 16 }, { "12", 0xffbee8, 10 }, { "14", 0xffc668, 10 } }
local seen = {}
local POOLS = (os.getenv("FF_TR_POOLS") or "1") == "1"
local pokes = {}
for f, a, bytes in string.gmatch(os.getenv("FF_TR_POKE") or "", "(%d+):(%x+):(%x+)") do pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), bytes } end
emu.register_frame_done(function()
  local f = L.frame()
  for _, p in ipairs(pokes) do
    if p[1] == f then
      for i = 1, #p[3], 2 do m:write_u8(p[2] + (i - 1) // 2, tonumber(p[3]:sub(i, i + 1), 16)) end
      fh:write(string.format("POKE %d %06x %s\n", f, p[2], p[3]))
    end
  end
  local ch = {}
  for _, fl in ipairs(fields) do
    local v = fl[2]()
    if last[fl[1]] ~= v then
      ch[#ch + 1] = fl[1] .. "=" .. string.format(fl[3], v)
      last[fl[1]] = v
    end
  end
  if POOLS then
    for _, p in ipairs(pools) do
      for i = 0, p[3] - 1 do
        local a = p[2] + 0xc0 * i
        local live = u8(a) ~= 0
        if live and not seen[a] then
          seen[a] = true
          fh:write(string.format("S %d pool=%s rec=%d %06x kind=%02x ch=%02x ent=%02x x=%04x y=%04x hp=%04x\n", f, p[1], i, a, u8(a + 19), u8(a + 20), u8(a + 21), u16(a + 6), u16(a + 10), u16(a + 24)))
        elseif not live then seen[a] = nil end
      end
    end
  end
  if #ch > 0 then fh:write(string.format("C %d %s\n", f, table.concat(ch, " "))) end
  if f % 30 == 0 then
    fh:write(string.format("P %d cam=%04x camy=%04x p1x=%04x p1y=%04x p1y14=%04x hp=%04x 176=%04x\n", f, u16(0xff8412), u16(0xff8416), u16(P1 + 6), u16(P1 + 10), u16(P1 + 14), u16(P1 + 24), u16(A5 + 176)))
  end
  fh:flush()
end)
dofile(os.getenv("FF_DIR") .. "/stagebot.lua")
-- FF_TR_HOLD="f1-f2:field:level,..." extra inputs applied after the bot (this callback is registered last, so it wins); released the frame after f2
local holds = {}
for a, b, fld, lv in string.gmatch(os.getenv("FF_TR_HOLD") or "", "(%d+)%-(%d+):(%w+):(%d)") do holds[#holds + 1] = { tonumber(a), tonumber(b), fld, tonumber(lv) } end
emu.register_frame_done(function()
  local f = L.frame()
  for _, h in ipairs(holds) do
    if f >= h[1] and f <= h[2] then L.F[h[3]]:set_value(h[4])
    elseif f == h[2] + 1 then L.F[h[3]]:set_value(0) end
  end
end)
