-- Cody taps Button 1 (attack) every 25 frames from 4160, release after 4 frames
local t = {}
for f = 4160, 7000, 25 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 4, "b1", 0} end
return t
