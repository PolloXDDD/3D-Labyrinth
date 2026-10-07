"""Reproduce the 3D Labyrinth experiments (no Minecraft installation needed).

Run: python simulate.py
Requires Python, NumPy, SciPy, and a C++ compiler (g++ by default).
Every (experiment, size, probability index, trial) has its own SeedSequence.
"""
from pathlib import Path
import csv
import ctypes
import json
import math
import os
import platform
import subprocess
import time
import numpy as np
import scipy
from scipy import ndimage

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
MASTER_SEED = 20261006
PROBS = [.20,.25,.28,.30,.32,.34,.38,.42,.46,.50,.55,.60,2/3,.75]
STRUCTURE = ndimage.generate_binary_structure(3, 1)

def load_bfs():
    target = ROOT / '_bfs.so'
    source = ROOT / 'bfs.cpp'
    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        subprocess.run([os.environ.get('CXX','g++'), '-O3', '-std=c++17',
                        '-shared', '-fPIC', str(source), '-o', str(target)], check=True)
    f = ctypes.CDLL(str(target)).face_bfs
    f.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int,
                  ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                  ctypes.POINTER(ctypes.c_int)]
    f.restype = ctypes.c_int
    return f

BFS = load_bfs()

def shortest(mask, start=-1, path=False):
    arr = np.ascontiguousarray(mask, dtype=np.uint8)
    parent = np.empty(arr.size, np.int32) if path else None
    goal = ctypes.c_int(-1)
    length = BFS(arr.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                 *arr.shape, int(start),
                 None if parent is None else parent.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
                 ctypes.byref(goal))
    if not path:
        return length
    route = []
    v = goal.value
    while v >= 0:
        route.append(np.unravel_index(v,arr.shape))
        v = int(parent[v])
    return length, np.array(route[::-1],dtype=int).reshape(-1,3)

def rng_for(experiment, L, pi, trial, stream=0):
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(
        [MASTER_SEED,experiment,L,pi,trial,stream])))

def graph_metrics(mask):
    labels, count = ndimage.label(mask, structure=STRUCTURE)
    sizes = np.bincount(labels.ravel(), minlength=count+1)
    sizes[0] = 0
    n = int(mask.sum())
    far = np.unique(labels[-1])
    far = far[far != 0]
    useful = np.isin(labels[0],far) if len(far) else np.zeros(mask.shape[1:],bool)
    opens = int(mask[0].sum())
    edges = sum(int(np.count_nonzero(np.take(mask,range(mask.shape[a]-1),axis=a)
                    & np.take(mask,range(1,mask.shape[a]),axis=a))) for a in range(3))
    return dict(vertices=n,edges=edges,components=int(count),
                giant_fraction=float(sizes.max()/n) if n else 0.,
                spanning=int(useful.any()),
                useful_face_fraction=float(useful.mean()),
                useful_open_fraction=float(useful.sum()/opens) if opens else 0.,
                cycle_rank=edges-n+int(count))

def verify():
    # Independent small-graph checks against a straightforward Python BFS.
    from collections import deque
    def reference(m,start):
        d={}
        seeds=np.argwhere(m[0]) if start<0 else None
        pts=[(0,int(y),int(z)) for y,z in seeds] if start<0 else [np.unravel_index(start,m.shape)]
        q=deque()
        for v in pts:
            if m[v]: d[v]=0; q.append(v)
        while q:
            v=q.popleft()
            if v[0]==m.shape[0]-1: return d[v]
            for a in range(3):
                for sign in (-1,1):
                    u=list(v); u[a]+=sign; u=tuple(u)
                    if 0<=u[a]<m.shape[a] and m[u] and u not in d:
                        d[u]=d[v]+1; q.append(u)
        return -1
    rg=np.random.default_rng(712)
    for shape in [(3,3,3),(4,3,2),(5,4,4)]:
        for _ in range(16):
            m=rg.random(shape)<.55
            for start in [-1,int(rg.integers(np.prod(shape[1:])) )]:
                a=shortest(m,start); b=reference(m,start)
                assert a==b,(shape,start,a,b)
            a,route=shortest(m,path=True)
            assert (a>=0)==bool(graph_metrics(m)['spanning'])
            if a>=0:
                assert len(route)==a+1 and route[0,0]==0 and route[-1,0]==shape[0]-1
                assert m[tuple(route.T)].all() and (np.abs(np.diff(route,axis=0)).sum(1)==1).all()
    for L in [3,5]:
        m=np.ones((L,L,L),bool)
        g=graph_metrics(m)
        assert g['edges']==3*L*L*(L-1) and shortest(m)==L-1
        assert g['cycle_rank']==g['edges']-L**3+1
    return '96 BFS comparisons; 48 route/component checks; full-lattice checks: PASS'

def run():
    DATA.mkdir(exist_ok=True)
    checks=verify()
    rows=[]
    t0=time.perf_counter()
    for experiment,sizes,probs,trials in [
        (1,[16,32,48],PROBS,200),
        (2,[16,32,64],[2/3],300),
    ]:
        for L in sizes:
            for pi,p in enumerate(probs):
                for trial in range(trials):
                    air=rng_for(experiment,L,pi,trial).random((L,L,L))<p
                    solid=graph_metrics(~air) if experiment==2 else None
                    for model,mask in [('point',air),('upright',air[:,:,:-1]&air[:,:,1:])]:
                        g=graph_metrics(mask)
                        row=dict(experiment=experiment,L=L,p=p,p_index=pi,trial=trial,
                                 model=model,air_fraction=float(air.mean()),**g)
                        row.update(solid_spanning='' if solid is None else solid['spanning'],
                                   solid_giant='' if solid is None else solid['giant_fraction'],
                                   shortest_face='',random_start='',random_length='',random_success='')
                        if experiment==2:
                            row['shortest_face']=shortest(mask)
                            entries=np.flatnonzero(mask[0].ravel())
                            if len(entries):
                                start=int(rng_for(experiment,L,pi,trial,1 if model=='point' else 2).choice(entries))
                                length=shortest(mask,start)
                                row.update(random_start=start,random_length=length,random_success=int(length>=0))
                            else:
                                row.update(random_start=-1,random_length=-1,random_success=0)
                        rows.append(row)
                print(f'experiment={experiment} L={L} p={p:.6f} trials={trials}',flush=True)
                # Incremental checkpoint; no expensive world needs to be retained.
                with open(DATA/'trials.csv','w',newline='') as f:
                    wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    # One specified illustration, without acceptance/rejection or selection for appearance.
    sample=rng_for(3,16,0,0).random((16,16,16))<2/3
    lp,pp=shortest(sample,path=True)
    lh,ph=shortest(sample[:,:,:-1]&sample[:,:,1:],path=True)
    np.savez_compressed(DATA/'illustration.npz',air=sample,point_path=pp,upright_path=ph)
    metadata=dict(master_seed=MASTER_SEED,bit_generator='PCG64',
        seed_fields=['master_seed','experiment','L','p_index','trial','stream'],
        sweep=dict(sizes=[16,32,48],probabilities=PROBS,trials=200),
        focus=dict(sizes=[16,32,64],probabilities=[2/3],trials=300),
        independent_cubes=9300,graph_observations=len(rows),
        illustration=dict(experiment=3,L=16,p=2/3,p_index=0,trial=0,
                          point_length=lp,upright_length=lh),
        python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        compiler=subprocess.check_output([os.environ.get('CXX','g++'),'--version'],text=True).splitlines()[0],
        elapsed_seconds=time.perf_counter()-t0,verification=checks)
    (DATA/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2),flush=True)

if __name__=='__main__':
    run()
