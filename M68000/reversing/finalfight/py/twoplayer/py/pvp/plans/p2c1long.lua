local t = {}
for f = 10, 300, 14 do t[#t+1] = {f, "b1_2", 1}; t[#t+1] = {f+4, "b1_2", 0} end
return t
