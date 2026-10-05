-- hitc.lua: count executions of listed addresses (and optionally log register values) under god mode + FF_KEYS.
--   FF_ADDRS="22da0,22dae"  hex addresses; FF_HIT_OUT=<file> summary; FF_HIT_LOG=<file> optional per-hit log "frame addr D0 D1 A6"
--   (needs -debug -debugger none: FF_MAMEARGS="-debug -debugger none")
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local dbg = manager.machine.debugger
local out = assert(io.open(os.getenv("FF_HIT_OUT") or "hits.txt", "w"))
local lp = os.getenv("FF_HIT_LOG"); local logf = (lp and lp ~= "") and assert(io.open(lp, "w"))
local m = L.mem
local keys = {}
for fld, a, b in string.gmatch(os.getenv("FF_KEYS") or "", "(%a%w*):(%d+)-(%d+)") do keys[#keys + 1] = { fld, tonumber(a), tonumber(b) } end
local god = os.getenv("FF_GOD") == "1"
local started = false
local counts, order = {}, {}
local extra = os.getenv("FF_HIT_REGS") or ""   -- e.g. "D0,A6" printed in the log lines
emu.register_periodic(function()
  if not started then
    started = true
    for a in string.gmatch(os.getenv("FF_ADDRS") or "", "(%x+)") do
      local fmt, args = "H %s", string.format('"%s"', a)
      if logf then
        dbg:command(string.format('bpset %s,1,{printf "H %s D0=%%08x D1=%%08x A6=%%08x S=%%04x\\n",d0,d1,a6,w@ff1150; g}', a, a))
      else
        dbg:command(string.format('bpset %s,1,{printf "H %s\\n"; g}', a, a))
      end
      order[#order + 1] = a
    end
    dbg:command("go")
  end
end)
local seen = 0
emu.register_frame_done(function()
  local f = L.frame()
  local lvl = {}
  for _, k in ipairs(keys) do lvl[k[1]] = lvl[k[1]] or 0; if f >= k[2] and f < k[3] then lvl[k[1]] = 1 end end
  for fld, v in pairs(lvl) do L.F[fld]:set_value(v) end
  if god then local hp = m:read_u16(0xff8580); if hp < 0x50 then m:write_u16(0xff8580, 0x90); m:write_u16(0xff8582, 0x90) end end
  local log = dbg.consolelog
  for i = seen + 1, #log do
    local a = log[i]:match("^H (%x+)")
    if a then
      counts[a] = (counts[a] or 0) + 1
      if logf then logf:write(string.format("%d %s\n", f, log[i])) end
    end
  end
  seen = #log
  if f >= tonumber(os.getenv("FF_STOP") or "2300") then
    for _, a in ipairs(order) do out:write(string.format("%s %d\n", a, counts[a] or 0)) end
    out:close(); if logf then logf:close() end
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
