-- Cody: jump (b2) then attack in the air (b1) 12 frames later, twice
local t = {}
for _, f in ipairs({40, 130}) do
  t[#t+1] = {f, "b2", 1}; t[#t+1] = {f+4, "b2", 0}
  t[#t+1] = {f+14, "b1", 1}; t[#t+1] = {f+18, "b1", 0}
end
return t
