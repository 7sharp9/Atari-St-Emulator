-- wall jump probe: walk right into the oil drum (prop kind 5 at x $368, spawned at camera $1ca) and stand pinned, then jump right and press jump again in the air.
-- FF_WJ_T0 first jump press frame (default 420), FF_WJ_DT frames from the first press to the second (default 20)
local t0 = tonumber(os.getenv("FF_WJ_T0") or "420")
local dt = tonumber(os.getenv("FF_WJ_DT") or "20")
local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
t[#t+1] = {5, "right", 1}; t[#t+1] = {5, "up", 1}; t[#t+1] = {5 + tonumber(os.getenv("FF_WJ_UP") or "47"), "up", 0}
if t0 > 0 then hold(t0, "b2", 4); hold(t0 + dt, "b2", tonumber(os.getenv("FF_WJ_HOLD") or "4")) end
local b1 = tonumber(os.getenv("FF_WJ_B1") or "-1")   -- frame of a Button 1 pulse (attack during the wall grip), -1: none
if b1 >= 0 then hold(b1, "b1", 4) end
local lf = tonumber(os.getenv("FF_WJ_LEFT") or "-1")   -- frame at which Left is held for 40 frames
if lf >= 0 then hold(lf, "left", 40) end
local dn = tonumber(os.getenv("FF_WJ_DOWN2") or "-1")  -- frame at which Down is held for 30 frames
if dn >= 0 then hold(dn, "down", 30) end
t[#t+1] = {tonumber(os.getenv("FF_WJ_END") or tostring(t0 + 90)), "right", 0}
return t
