"""Geometric check on the model's list: for 8-adjacent listed cells, is the draw order (list reversed: last entry first)
consistent with view depth along the heading? forward = (sin a, cos a), a = heading/1024*2pi (heading 256 -> +x, from the
footprints: inferred). An inversion = the cell drawn first is nearer along the view axis than the cell drawn after it."""
import sys,os,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import scan_model as M
for h in range(0,1024,64):
    L=M.scan(h); pos={c:i for i,c in enumerate(L)}
    a=h/1024*2*math.pi; fx,fy=math.sin(a),math.cos(a)
    n=inv=0; worst=0
    for (x,y),i in pos.items():
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                c=(x+dx,y+dy)
                if (dx,dy)<=(0,0) or c not in pos: continue
                j=pos[c]; d_i=fx*x+fy*y; d_j=fx*c[0]+fy*c[1]
                if abs(d_i-d_j)<1e-9: continue
                n+=1
                first = (x,y) if i>j else c      # larger list index is drawn first
                other = c if i>j else (x,y)
                df=fx*first[0]+fy*first[1]; do=fx*other[0]+fy*other[1]
                if df<do-1e-9: inv+=1; worst=max(worst,do-df)   # the first-drawn cell is nearer: wrong
    print('heading %4d oct %d adjacent pairs %4d with a depth difference, drawn nearer-first %3d (%.1f%%), worst %.2f cells'%(h,M.octant(h),n,inv,100*inv/n,worst))
