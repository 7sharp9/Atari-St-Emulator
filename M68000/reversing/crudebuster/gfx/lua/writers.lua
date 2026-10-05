-- writers.lua: census of the 68000 instructions (PPC) that write each video-related region, for a drive.
--   same env as dumpframes.lua (CB_DIR CB_PLAN CB_POKE CB_STOP CB_OUT); writes $CB_OUT/writers.txt: "region ppc count first_frame"
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local out = os.getenv("CB_OUT") or "."
local sched = {}
if os.getenv("CB_PLAN") then sched = dofile(os.getenv("CB_PLAN")) end
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local pokes = {}
for tok in (os.getenv("CB_POKE") or ""):gmatch("[^,]+") do
  local f, a, v, s, o = tok:match("^(%d+):(%x+):(%x+):?(%d*):?([oc]?)$")
  pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), tonumber(v, 16), tonumber(s ~= "" and s or "1"), o }
end
local cpu = manager.machine.devices[":maincpu"]
local st = cpu.state
local mem = L.mem
local count, first = {}, {}
local regions = {
  { "pf_c0_pf1", 0xa0000, 0xa1fff }, { "pf_c0_pf2", 0xa2000, 0xa3fff }, { "rs_c0_1", 0xa4000, 0xa47ff }, { "rs_c0_2", 0xa6000, 0xa67ff },
  { "pf_c1_pf1", 0xa8000, 0xa9fff }, { "pf_c1_pf2", 0xaa000, 0xabfff }, { "rs_c1_1", 0xac000, 0xac7ff }, { "rs_c1_2", 0xae000, 0xae7ff },
  { "sprram", 0xb0000, 0xb07ff }, { "ctl0", 0xb5000, 0xb500f }, { "ctl1", 0xb6000, 0xb600f },
  { "pal_lo", 0xb8000, 0xb8fff }, { "pal_ext", 0xb9000, 0xb9fff },
  { "spl0_83800", 0x83800, 0x83bff }, { "spl1_83400", 0x83400, 0x837ff }, { "spl2_83000", 0x83000, 0x833ff }, { "spl3_82c00", 0x82c00, 0x82fff },
  { "spl4_82800", 0x82800, 0x82bff }, { "spl5_82400", 0x82400, 0x827ff }, { "spl6_82000", 0x82000, 0x823ff },
}
taps = {}
for i, r in ipairs(regions) do
  local name = r[1]
  taps[i] = mem:install_write_tap(r[2], r[3], name, function(off, data, mask)
    local ppc = st["CURPC"].value
    local key = name .. " " .. string.format("%06x", ppc)
    count[key] = (count[key] or 0) + 1
    if not first[key] then first[key] = L.frame() end
  end)
end
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  for _, p in ipairs(pokes) do
    if p[1] == f then
      for i = 0, p[4] - 1 do
        local b = (p[3] >> (8 * (p[4] - 1 - i))) & 0xff
        if p[5] == "o" then b = b | mem:read_u8(p[2] + i) elseif p[5] == "c" then b = mem:read_u8(p[2] + i) & ~b end
        mem:write_u8(p[2] + i, b)
      end
    end
  end
  if f >= stop then
    local fh = assert(io.open(out .. "/writers.txt", "w"))
    for k, v in pairs(count) do fh:write(string.format("%s %d %d\n", k, v, first[k])) end
    fh:close()
    manager.machine:exit()
  end
end)
