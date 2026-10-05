-- prop PA i=13: explicit drop in byte +21 (bit 7 clear): FF_DROP (default $25); Cody hp FF_CHP (default none); Cody to x=$0520 y=$1a facing right; clear grapple link
local drop = tonumber(os.getenv("FF_DROP") or "0x25")
local t = {
 {0, 0xff85a8, 1, 0}, {0, 0xff85aa, 1, 0}, {0, 0xff856b, 1, 0}, {0, 0xff856c, 1, 0},
 {0, 0xff856e, 2, 0x0520}, {0, 0xff8572, 2, 0x001a}, {0, 0xff8576, 2, 0x001a}, {0, 0xff8596, 1, 0},
 {0, 0xffbcbd, 1, drop},
}
if os.getenv("FF_CHP") then local h = tonumber(os.getenv("FF_CHP")); t[#t+1] = {0, 0xff8580, 2, h}; t[#t+1] = {0, 0xff8582, 2, h} end
return t
