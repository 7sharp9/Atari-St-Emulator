-- experiment 1: from the saved state, tap attack (b1) every 40 frames
local t = {}
for f = 2210, 2600, 40 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 6, "b1", 0} end
return t
