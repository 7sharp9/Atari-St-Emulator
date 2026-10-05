-- Cody holds Right from 4165 to 4600, then Button 1 taps
local t = {{4165, "right", 1}, {4600, "right", 0}}
for f = 4610, 5200, 20 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 3, "b1", 0} end
return t
