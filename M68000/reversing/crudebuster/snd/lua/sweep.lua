-- sweep.lua: send each latch value CMDS_LO..CMDS_HI to a quiet idle sound CPU and log what the HuC6280 does for WIN frames.
--   One MAME run: boot with the 68000 muted (DSW Demo Sounds off), save a state at frame IDLE, then for every command
--   load that state, write the latch from Lua at relative frame 2 (as the 68000 would, through $bc002), log WIN frames, repeat.
--   env: SND_DIR, LOG, LO (default 0), HI (default 255), WIN (default 300), IDLE (default 150), PRE (optional list "v,v" sent
--   before the measured command, 40 frames apart, e.g. to test commands that depend on a started song)
-- Log: "CMD <v>" blocks; inside: LRD frame value pc | EV frame chip a|d value pc | LAT frame value (68000 writes: must be none)
local SND = os.getenv("SND_DIR")
local S = dofile(SND .. "/lua/snd_lib.lua")
local lo, hi = tonumber(os.getenv("LO") or "0"), tonumber(os.getenv("HI") or "255")
local win = tonumber(os.getenv("WIN") or "300")
local idle = tonumber(os.getenv("IDLE") or "150")
local pre = {}
for v in (os.getenv("PRE") or ""):gmatch("%x+") do pre[#pre + 1] = tonumber(v, 16) end
local statename = os.getenv("STATE") or "sndidle"
S.install()
S.mute_demo()
manager.machine.video.throttled = false
local log = assert(io.open(os.getenv("LOG"), "w"))
local cmd = lo
local phase = "boot"     -- boot -> saved -> loading -> running
local n = 0              -- frames since the load completed
local nev, nlat, nrd = 0, 0, 0
local loadwait = 0
local booted = 0
local function dump()
  for i = nlat + 1, #S.lat do local e = S.lat[i]; log:write(string.format("LAT %d %02x\n", e[1], e[2])) end
  for i = nrd + 1, #S.latrd do local e = S.latrd[i]; log:write(string.format("LRD %d %02x %04x\n", e[1], e[2], e[3])) end
  for i = nev + 1, #S.ev do local e = S.ev[i]; log:write(string.format("EV %d %s %s %02x %04x\n", e[1], e[2], e[3], e[4], e[5])) end
  nlat, nev, nrd = #S.lat, #S.ev, #S.latrd
end
emu.register_frame_done(function()
  booted = booted + 1
  if phase == "boot" then
    if booted >= idle then manager.machine:save(statename); phase = "saved"; loadwait = 3 end
    return
  end
  if phase == "saved" then
    -- the save is carried out at the next frame boundary; load it straight away in the next callbacks
    loadwait = loadwait - 1
    if loadwait <= 0 then manager.machine:load(statename); phase = "loading"; loadwait = 3 end
    return
  end
  if phase == "loading" then
    loadwait = loadwait - 1
    if loadwait <= 0 then
      S.reset(); nev, nlat, nrd = 0, 0, 0
      log:write(string.format("CMD %02x\n", cmd))
      phase = "running"; n = 0
    end
    return
  end
  n = n + 1
  if n == 1 then log:write(string.format("BASE %d\n", S.screen:frame_number())) end
  -- optional prefix commands, 40 frames apart, then the measured command
  local t0 = 2
  for i, v in ipairs(pre) do
    if n == t0 then S.mem:write_u16(0xbc002, v); log:write(string.format("PRE %02x\n", v)) end
    t0 = t0 + 40
  end
  if n == t0 then S.mem:write_u16(0xbc002, cmd); log:write(string.format("SEND %d %02x\n", S.screen:frame_number(), cmd)) end
  dump()
  if n >= t0 + win then
    local tk = 0; for _, c in pairs(S.tick) do tk = tk + c end
    log:write(string.format("TICKS %d\n", tk)); log:write("END\n"); log:flush()
    cmd = cmd + 1
    if cmd > hi then log:close(); manager.machine:exit(); return end
    manager.machine:load(statename); phase = "loading"; loadwait = 3
  end
end)
