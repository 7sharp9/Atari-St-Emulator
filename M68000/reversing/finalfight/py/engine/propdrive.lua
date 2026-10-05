-- propdrive.lua: pass-5 agent B. Load a state, drive player 1 with relative-frame key levels, apply pokes, count breakpoints (needs -debug), log pool-a/pool-8 records per frame.
-- Environment: PD_LOAD (state), PD_N (frames), PD_KEYS="field:from-to,..." (right left up down b1 b2 b3; relative frames), PD_POKES="rel:hexaddr:hexbytes,...",
--   PD_ADDRS="711a,7156,..." (bpset + printf "H addr a1 a3 a6 d7"), PD_LOG (log file), PD_PROPS=1 (per-frame pool a records), PD_P8=1 (pool 8), PD_GOD=1 (health poke), PD_SHOTS="rel,.."
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local dbg = manager.machine.debugger
local N = tonumber(os.getenv("PD_N") or "300")
local log = assert(io.open(os.getenv("PD_LOG"), "w"))
local keys, pokes, shots = {}, {}, {}
for fld, a, b in string.gmatch(os.getenv("PD_KEYS") or "", "(%a%w*):(%d+)-(%d+)") do keys[#keys + 1] = { fld, tonumber(a), tonumber(b) } end
for r, a, h in string.gmatch(os.getenv("PD_POKES") or "", "(%d+):(%x+):(%x+)") do pokes[#pokes + 1] = { tonumber(r), tonumber(a, 16), h } end
for r in string.gmatch(os.getenv("PD_SHOTS") or "", "(%d+)") do shots[tonumber(r)] = true end
local addrs, counts, bpdone, seen = {}, {}, false, 0
local loaded, base = false, nil
local held = {}
local function set(field, v) if held[field] ~= v then held[field] = v; L.F[field]:set_value(v) end end
emu.register_periodic(function()
  if not bpdone then
    bpdone = true
    for a in string.gmatch(os.getenv("PD_ADDRS") or "", "(%x+)") do
      addrs[#addrs + 1] = a
      dbg:command(string.format('bpset %s,1,{printf "H %s %%x %%x %%x %%x\\n",a1,a3,a6,d7; g}', a, a))
    end
    if #addrs > 0 then dbg:command("go") end
  end
end)
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then loaded = true; manager.machine:load(os.getenv("PD_LOAD")); return end
  base = base or f
  local r = f - base
  local con = dbg and dbg.consolelog
  if con and #addrs > 0 then
    for i = seen + 1, #con do
      local a, a1, a3, a6, d7 = con[i]:match("^H (%x+) (%x+) (%x+) (%x+) (%x+)")
      if a then counts[a] = (counts[a] or 0) + 1; log:write(string.format("HIT r=%d %s a1=%s a3=%s a6=%s d7=%s\n", r, a, a1, a3, a6, d7)) end
    end
    seen = #con
  end
  for _, p in ipairs(pokes) do if p[1] == r then local h = p[3]; for i = 1, #h, 2 do m:write_u8(p[2] + (i - 1) // 2, tonumber(h:sub(i, i + 1), 16)) end; log:write(string.format("POKE r=%d %x\n", r, p[2])) end end
  local lvl = {}
  for _, k in ipairs(keys) do lvl[k[1]] = lvl[k[1]] or 0; if r >= k[2] and r < k[3] then lvl[k[1]] = 1 end end
  for fld, v in pairs(lvl) do set(fld, v) end
  if os.getenv("PD_GOD") == "1" then m:write_u16(0xff8568 + 24, m:read_u16(0xff8568 + 28)); if m:read_u8(0xff8568 + 128) < 2 then m:write_u8(0xff8568 + 128, 2) end end
  if os.getenv("PD_PROPS") == "1" then
    local t = {}
    for i = 0, 15 do
      local a = 0xffb2e8 + 0xc0 * i
      if m:read_u8(a) ~= 0 then t[#t + 1] = string.format("[%d k%d st%d/%d/%d hp%04x x%04x y%04x 128=%02x 133=%02x 135=%02x 136=%02x 60=%04x 63=%02x]", i, m:read_u8(a + 19), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 4), m:read_u16(a + 24), m:read_u16(a + 6), m:read_u16(a + 10), m:read_u8(a + 128), m:read_u8(a + 133), m:read_u8(a + 135), m:read_u8(a + 136), m:read_u16(a + 60), m:read_u8(a + 63)) end
    end
    log:write(string.format("r=%d P1 x=%04x y=%04x st=%02x/%02x hp=%04x sc=%08x cam=%04x props %s\n", r, m:read_u16(0xff856e), m:read_u16(0xff8572), m:read_u8(0xff856a), m:read_u8(0xff856b), m:read_u16(0xff8580), m:read_u32(0xff85ec), m:read_u16(0xff8412), table.concat(t, " ")))
  end
  if os.getenv("PD_P4") == "1" then
    local t = {}
    for i = 0, 7 do local a = 0xff9528 + 0xc0 * i; if m:read_u8(a) ~= 0 then t[#t + 1] = string.format("[%d k%d c%d st%02x/%02x/%02x x%04x y%04x hp%04x 30=%02x]", i, m:read_u8(a + 19), m:read_u8(a + 20), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 4), m:read_u16(a + 6), m:read_u16(a + 10), m:read_u16(a + 24), m:read_u8(a + 30)) end end
    log:write(string.format("P4 r=%d f=%d st=%d/%d 297=%02x 299=%02x 291=%02x P1 x=%04x y=%04x st=%02x/%02x/%02x/%02x cam=%04x %s\n", r, f, m:read_u8(0xff80be), m:read_u8(0xff80bf), m:read_u8(0xff8129), m:read_u8(0xff812b), m:read_u8(0xff8123), m:read_u16(0xff856e), m:read_u16(0xff8572), m:read_u8(0xff856a), m:read_u8(0xff856b), m:read_u8(0xff856c), m:read_u8(0xff856d), m:read_u16(0xff8412), table.concat(t, " ")))
  end
  if os.getenv("PD_ACT") == "1" then
    local a = 0xffb228
    log:write(string.format("ACT r=%d f=%d st=%d/%d 297=%02x 291=%02x 278=%02x 279=%02x 280=%08x 284=%08x cam=%04x,%04x 1116=%04x 918=%04x P1 x=%04x y=%04x st=%02x/%02x/%02x/%02x | b0=%02x k=%02x st=%02x/%02x/%02x/%02x x=%04x y=%04x 30=%02x 128=%08x lim=%04x s22191=%02x/%02x/%02x/%02x\n", r, f, m:read_u8(0xff80be), m:read_u8(0xff80bf), m:read_u8(0xff8129), m:read_u8(0xff8123), m:read_u8(0xff8116), m:read_u8(0xff8117), m:read_u32(0xff8118), m:read_u32(0xff811c), m:read_u16(0xff8412), m:read_u16(0xff8416), m:read_u16(0xff845c), m:read_u16(0xff8396), m:read_u16(0xff856e), m:read_u16(0xff8572), m:read_u8(0xff856a), m:read_u8(0xff856b), m:read_u8(0xff856c), m:read_u8(0xff856d), m:read_u8(a), m:read_u8(a + 19), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 4), m:read_u8(a + 5), m:read_u16(a + 6), m:read_u16(a + 10), m:read_u8(a + 30), m:read_u32(a + 128), m:read_u16(0xff8436), m:read_u8(0xff8000 + 22191), m:read_u8(0xff8000 + 22192), m:read_u8(0xff8000 + 22193), m:read_u8(0xff8000 + 22194)))
  end
  if os.getenv("PD_P8") == "1" then
    local t = {}
    for i = 0, 29 do local a = 0xff9b28 + 0xc0 * i; if m:read_u8(a) ~= 0 then t[#t + 1] = string.format("[%d k%02x c%d st%d x%04x y%04x]", i, m:read_u8(a + 19), m:read_u8(a + 21), m:read_u8(a + 2), m:read_u16(a + 6), m:read_u16(a + 10)) end end
    log:write("P8 r=" .. r .. " " .. table.concat(t, " ") .. "\n")
  end
  if os.getenv('PD_SAVE') then local sr, sn = string.match(os.getenv('PD_SAVE'), '(%d+):([%w_]+)'); if tonumber(sr) == r then L.write(os.getenv('PD_LOG') .. '.' .. sn .. '.ram', L.ram()); manager.machine:save(sn); log:write('SAVED ' .. sn .. ' at r=' .. r .. ' f=' .. f .. '\n') end end
  if shots[r] then L.screen:snapshot(string.format("pd_%04d.png", r)) end
  if r >= N then
    for _, a in ipairs(addrs) do log:write(string.format("COUNT %s %d\n", a, counts[a] or 0)) end
    log:close(); manager.machine:exit()
  end
end)
