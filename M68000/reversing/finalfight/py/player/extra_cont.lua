-- log changes of the continue-scene record ($ff1576..$ff15b8) and the byte block $ffd690..$ffd6e0 (22160(A5)..), per frame
local regs = { {0xff1570, 0x50}, {0xffd690, 0x50}, {0xff8000 + 296, 4} }
local last = {}
return function(f, rel, m, out)
  for _, r in ipairs(regs) do
    local s = {}
    for a = r[1], r[1] + r[2] - 1 do s[#s+1] = string.format("%02x", m:read_u8(a)) end
    s = table.concat(s)
    if last[r[1]] ~= s then
      out:write(string.format("C %d %d %06x %s\n", f, rel, r[1], s))
      last[r[1]] = s
    end
  end
end
