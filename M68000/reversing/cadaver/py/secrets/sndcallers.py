import re,sys,collections
L=[]
for l in open('cad_all.asm'):
    m=re.match(r'\s+\$([0-9a-f]+): (.*)',l)
    if m: L.append((int(m.group(1),16),m.group(2)))
targets={0x158f8:'PlaySound',0x15aec:'StopSound',0x15ae0:'StopSound2(flag)',0x15aaa:'StartSet',0x15ba6:'ClearPending',0x15bbc:'QueueNoStart',0x15b9a:'Repick',0x15bf4:'InstallVoice',0x15c70:'Dispatch',0x15b3e:'Repick3e',0x15a7e:'Start',0x158dc:'VblDisp'}
pat=re.compile(r'(jsr|bsr|jmp|bra)\s+\$([0-9a-f]+)')
res=collections.defaultdict(list)
for i,(a,t) in enumerate(L):
    m=pat.match(t)
    if m and int(m.group(2),16) in targets and a<0x19000:
        tgt=int(m.group(2),16)
        d0=None
        for j in range(i-1,max(0,i-8),-1):
            tj=L[j][1]
            mm=re.match(r'(moveq|move\.w|move\.l|move\.b) #\$?(-?[0-9a-f]+),D0$',tj)
            if mm:
                d0=tj; break
            if re.search(r',D0$',tj) or re.search(r'\bD0\b',tj.split(',')[-1]):
                d0=tj; break
        res[tgt].append((a,t,d0))
for tgt,v in res.items():
    print('==',hex(tgt),targets[tgt],len(v))
    for a,t,d in v: print('  $%06x %-22s | %s'%(a,t,d))
