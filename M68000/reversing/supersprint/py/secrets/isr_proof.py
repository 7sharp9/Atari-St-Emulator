"""isr_proof.py - live proof of the IKBD ISR $104b6 data paths from the attract snapshot (table at -4802(A4), sticks at -4804/-4803(A4)):
   make -> cell $03, break -> bit0 cleared ($02); scancodes >= $76 ignored; FE/FF header takes the NEXT byte as stick 0/1 state;
   other headers (F8 mouse, F6 status...) are ignored but their data bytes are taken as scancodes; ISR state byte $10544 returns to 0."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_ATTRACT)
def cell(sc): return r.g8(-4802 + sc)
def show(tag): print('%-46s LShift[2a]=%02x  $75=%02x  $76(beyond table)=%02x  stick0=%02x stick1=%02x  hdr-pending=%02x' % (tag, cell(0x2a), cell(0x75), cell(0x76), r.g8(-4804), r.g8(-4803), r.w8(0x10544)))
show('initial')
r.cmd('kbd 2a'); r.cmd('s 20000'); show('kbd 2a (LShift make)')
r.cmd('kbd aa'); r.cmd('s 20000'); show('kbd aa (LShift break)')
r.cmd('kbd 75'); r.cmd('kbd 76'); r.cmd('kbd 7f'); r.cmd('s 20000'); show('kbd 75, 76, 7f (only $75 < $76 stored)')
r.cmd('kbd fe 84'); r.cmd('s 20000'); show('kbd fe 84 (stick 0 = fire+left)')
r.cmd('kbd ff 8a'); r.cmd('s 20000'); show('kbd ff 8a (stick 1 = fire+right+down)')
r.cmd('kbd fe'); r.cmd('s 20000'); show('kbd fe (header only): pending byte set')
r.cmd('kbd 11'); r.cmd('s 20000'); show('kbd 11 (consumed as stick 0 data, NOT a key)')
r.cmd('kbd fd 20 28'); r.cmd('s 20000'); show('kbd fd 20 28 (joystick-both packet: header ignored, data as keys)')
print('cells $20=%02x $28=%02x' % (cell(0x20), cell(0x28)))
r.close()
