-- ioport_dump.lua: enumerate every ioport field (tag, name, mask, default, type id) and, for the digital
-- IN0/IN1 fields, measure polarity: live port word idle vs with that field pressed (set_value(1)).
-- Output: <FF_OUT>/ioport.txt
local out = io.open((os.getenv("FF_OUT") or ".") .. "/ioport.txt", "w")
local ports = manager.machine.ioport.ports
local tags = {}
for tag in pairs(ports) do tags[#tags + 1] = tag end
table.sort(tags)
out:write("# port | field | mask | default | type | live idle | live pressed (digital fields only)\n")
local list = {}
for _, tag in ipairs(tags) do
  local names = {}
  for fname in pairs(ports[tag].fields) do names[#names + 1] = fname end
  table.sort(names)
  for _, fname in ipairs(names) do list[#list + 1] = { tag, fname } end
end
local idx, phase, idle_word = 1, 0, nil
emu.register_frame_done(function()
  local f = manager.machine.screens[":screen"]:frame_number()
  if f < 5 then return end
  local e = list[idx]
  if not e then out:close(); manager.machine:exit(); return end
  local p = ports[e[1]]; local fld = p.fields[e[2]]
  if phase == 0 then
    idle_word = p:read()
    if e[1] == ":IN0" or e[1] == ":IN1" then fld:set_value(1) end
    phase = 1
  else
    local pressed = p:read()
    fld:set_value(0)
    local dig = (e[1] == ":IN0" or e[1] == ":IN1")
    out:write(string.format("%s | %s | %04x | %04x | %s | %04x | %s\n", e[1], e[2], fld.mask, fld.defvalue,
      tostring(fld.type), idle_word, dig and string.format("%04x", pressed) or "-"))
    idx = idx + 1; phase = 0
  end
end)
