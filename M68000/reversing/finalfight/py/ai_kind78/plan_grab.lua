-- Cody walks right into the enemy (grab), then after 20 frames presses b1 twice (grapple strikes), later left+b1 (throw)
local t = {}
t[#t+1] = {40, "right", 1}; t[#t+1] = {75, "right", 0}
t[#t+1] = {90, "b1", 1}; t[#t+1] = {94, "b1", 0}
t[#t+1] = {110, "b1", 1}; t[#t+1] = {114, "b1", 0}
t[#t+1] = {140, "left", 1}; t[#t+1] = {142, "b1", 1}; t[#t+1] = {146, "b1", 0}; t[#t+1] = {160, "left", 0}
return t
