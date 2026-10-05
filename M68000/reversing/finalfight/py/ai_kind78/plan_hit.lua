-- Cody attacks (Button 1 pulses) every 14 frames from rel 33
local t = {}
for f = 33, 600, 14 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 5, "b1", 0} end
return t
