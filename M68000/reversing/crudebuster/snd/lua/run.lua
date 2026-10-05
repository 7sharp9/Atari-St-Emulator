-- run.lua: play an input plan (like lua/drive.lua), force latch writes, log every sound event to a text file.
--   SND_DIR  this agent's directory            CB_DIR   reversing/crudebuster/lua (for lib.lua)
--   CB_PLAN  plan file {frame, field, level}   CB_STOP  last frame (default 3000)
--   CMDS     "frame:hexvalue,frame:hexvalue"   latch writes made from Lua through the 68000 address space at the end of that frame
--   MUTE=1   DSW Demo Sounds off (68000 sends nothing in attract)
--   CB_LOAD  state to load at frame 1        LOG  output file
--   POKE     "frame:hexaddr:hexvalue(byte),..." 68000 RAM pokes at the end of a frame
-- Log lines: LAT f v | LRD f v pc | EV f chip a|d value pc | FR f (frame marker every frame with the HuC6280 MPRs and zero page $2000.. counters)
local SND = os.getenv("SND_DIR")
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local S = dofile(SND .. "/lua/snd_lib.lua")
S.install()
if os.getenv("MUTE") == "1" then S.mute_demo() end
local sched = {}
if os.getenv("CB_PLAN") then sched = dofile(os.getenv("CB_PLAN")) end
local cmds = {}
for f, v in (os.getenv("CMDS") or ""):gmatch("(%d+):(%x+)") do cmds[#cmds + 1] = { tonumber(f), tonumber(v, 16) } end
local pokes = {}
for f, a, v in (os.getenv("POKE") or ""):gmatch("(%d+):(%x+):(%x+)") do pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), tonumber(v, 16) } end
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local log = assert(io.open(os.getenv("LOG"), "w"))
local fr = os.getenv("FRAMES") == "1"
local loaded = false
local nlat, nev, nrd = 0, 0, 0
local function flush(f)
  for i = nlat + 1, #S.lat do local e = S.lat[i]; log:write(string.format("LAT %d %02x %06x %06x\n", e[1], e[2], e[3] or 0, e[4] or 0)) end
  for i = nrd + 1, #S.latrd do local e = S.latrd[i]; log:write(string.format("LRD %d %02x %04x\n", e[1], e[2], e[3])) end
  for i = nev + 1, #S.ev do local e = S.ev[i]; log:write(string.format("EV %d %s %s %02x %04x\n", e[1], e[2], e[3], e[4], e[5])) end
  nlat, nev, nrd = #S.lat, #S.ev, #S.latrd
end
emu.register_frame_done(function()
  local f = L.frame()
  if os.getenv("CB_LOAD") and not loaded then loaded = true; manager.machine:load(os.getenv("CB_LOAD")); return end
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  for _, c in ipairs(cmds) do if c[1] == f then L.mem:write_u16(0xbc002, c[2]); log:write(string.format("FORCE %d %02x\n", f, c[2])) end end
  for _, p in ipairs(pokes) do if p[1] == f then L.mem:write_u8(p[2], p[3]) end end
  if fr then log:write(string.format("FR %d\n", f)) end
  flush(f)
  if f >= stop then log:close(); manager.machine:exit() end
end)
