-- experiment 2: kill Bred with attack taps (as plan1), then walk right with periodic attack taps
local t = {}
for f = 2210, 2420, 40 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 6, "b1", 0} end
t[#t+1] = {2450, "right", 1}
for f = 2460, 4200, 30 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 5, "b1", 0} end
t[#t+1] = {4250, "right", 0}
return t
