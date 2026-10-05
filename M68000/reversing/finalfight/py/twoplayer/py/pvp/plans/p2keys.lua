-- P2 presses each input in turn (12 frames each, 8 frames apart); P1 presses b1 once at 130 and Right at 150 for the control
local t = {}
local names = { "right2", "left2", "down2", "up2", "b1_2", "b2_2", "b3_2" }
for i, n in ipairs(names) do local f = 5 + (i - 1) * 24; t[#t+1] = {f, n, 1}; t[#t+1] = {f + 12, n, 0} end
t[#t+1] = {180, "right", 1}; t[#t+1] = {192, "right", 0}
t[#t+1] = {200, "b3", 1}; t[#t+1] = {212, "b3", 0}
return t
