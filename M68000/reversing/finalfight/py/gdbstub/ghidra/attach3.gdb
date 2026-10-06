ghidra trace tx-start "ram"
ghidra trace putmem 0xff0000 0x1000
ghidra trace putmem 0xff1000 0x1000
ghidra trace putmem 0xff2000 0x1000
ghidra trace putmem 0xff3000 0x1000
ghidra trace putmem 0xff4000 0x1000
ghidra trace putmem 0xff5000 0x1000
ghidra trace putmem 0xff6000 0x1000
ghidra trace putmem 0xff7000 0x1000
ghidra trace putmem 0xff8000 0x1000
ghidra trace putmem 0xff9000 0x1000
ghidra trace putmem 0xffa000 0x1000
ghidra trace putmem 0xffb000 0x1000
ghidra trace putmem 0xffc000 0x1000
ghidra trace putmem 0xffd000 0x1000
ghidra trace putmem 0xffe000 0x1000
ghidra trace putmem 0xfff000 0x1000
ghidra trace tx-commit
ghidra trace tx-start "regs"
ghidra trace putreg
ghidra trace tx-commit
