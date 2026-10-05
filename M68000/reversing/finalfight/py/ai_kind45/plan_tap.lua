-- tap Button 1 every 24 frames (held 5 frames), starting at frame 10
local t = {}
for f = 10, 6000, 24 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 5, "b1", 0} end
return t
