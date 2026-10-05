-- Cody mashes Button 1: press 3 frames, release 9, from 4160
local t = {}
for f = 4160, 9000, 12 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 3, "b1", 0} end
return t
