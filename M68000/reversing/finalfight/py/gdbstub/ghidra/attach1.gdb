set python print-stack full
set pagination off
set confirm off
python import ghidragdb
set architecture m68k
set endian big
target remote 127.0.0.1:23946
ghidra trace connect '127.0.0.1:15433'
ghidra trace start
ghidra trace sync-enable
