local t = {}
for f = 10, 600, 14 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f+4, "b1", 0} end
return t
