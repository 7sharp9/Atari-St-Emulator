-- Cody: b1 presses 12 frames apart from rel 40 (3-hit combo ends in a knockdown), repeated
local t = {}
for i = 0, 11 do t[#t+1] = {40 + i*12, "b1", 1}; t[#t+1] = {40 + i*12 + 4, "b1", 0} end
return t
