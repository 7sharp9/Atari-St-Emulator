set pagination off
set confirm off
set architecture m68k
set endian big
target remote 127.0.0.1:23946
show architecture
info registers
x/6i $pc
break *0x53e
continue
info registers pc a5 sp ps
x/4i $pc
stepi
x/i $pc
x/8xb 0xff8000
watch *(short *)0xff8054
continue
info registers pc
detach
