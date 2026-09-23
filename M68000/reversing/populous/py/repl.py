"""repl.py - drive the emulator REPL interactively (one process, request/response)."""
import subprocess,os,re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg import R, WORK as S
HEX=re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')
class Repl:
    def __init__(s,snap):
        env=dict(os.environ,ATARI_NOTRACE='1')
        s.p=subprocess.Popen(['dotnet','exec','bin/Debug/net8.0/M68000.dll','resume',snap,'repl','--disk-a',S+'/pop_auto.st'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,cwd=R,env=env,bufsize=1)
    def cmd(s,c):
        """send command(s) followed by 'r'; return (lines, regs dict)"""
        s.p.stdin.write(c.rstrip('\n')+'\nr\n'); s.p.stdin.flush()
        out=[]
        while True:
            line=s.p.stdout.readline()
            if not line: raise EOFError('\n'.join(out[-20:]))
            line=line.rstrip('\n'); out.append(line)
            if line.startswith('PC: '): s.p.stdout.readline(); break
        regs={}
        for l in out:
            for m in re.finditer(r'\b([DA][0-7]|PC|USP|SSP):\s*([0-9a-f]{8})',l): regs[m.group(1)]=int(m.group(2),16)
        return out,regs
    def mem(s,a,n):
        out,_=s.cmd('m %x %d'%(a,n))
        bs=bytearray()
        for l in out:
            if HEX.match(l.strip()): bs+=bytes(int(x,16) for x in l.split())
        assert len(bs)==n,(len(bs),n)
        return bytes(bs)
    def close(s):
        try: s.p.stdin.write('q\n'); s.p.stdin.flush()
        except Exception: pass
        s.p.wait()
