"""Generate publication figures and result tables from the saved trials."""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures'; OUT.mkdir(exist_ok=True)
D=pd.read_csv(ROOT/'data/trials.csv')
TEAL='#087F8C'; ORANGE='#D46A32'; INK='#243443'; BLUE='#4977A7'
PALE='#EEF6F5'; GRAY='#83929E'; PURPLE='#79599A'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,
    'axes.titlesize':10,'axes.labelsize':9,'axes.spines.top':False,
    'axes.spines.right':False,'axes.edgecolor':'#77838A',
    'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,
    'text.color':INK,'grid.color':'#DCE4E7','grid.linewidth':.5,
    'pdf.fonttype':42,'ps.fonttype':42,'savefig.facecolor':'white'})

def save(fig,name):
    fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight',pad_inches=.08)
    fig.savefig(OUT/f'{name}.png',dpi=190,bbox_inches='tight',pad_inches=.08)
    plt.close(fig)

def wilson(k,n,z=1.959963984540054):
    p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den
    h=z/den*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return c-h,c+h

def se(values):
    return np.std(values,ddof=1)/np.sqrt(len(values))

def geometry():
    ex=np.load(ROOT/'data/illustration.npz')
    air=ex['air']; route=ex['upright_path']; L=len(air)
    fig=plt.figure(figsize=(8.3,3.7))
    gs=fig.add_gridspec(1,3,width_ratios=[1.45,1,1],wspace=.40)
    ax=fig.add_subplot(gs[0],projection='3d',computed_zorder=False)
    x,y,z=np.indices(air.shape)
    # A front corner is omitted solely in the rendering, never in the solver.
    show=(~air)&~((x>=L//2)&(y<L//2)&(z>=L//2))
    ax.voxels(show,facecolors='#50667438',edgecolor='#203A4515',linewidth=.14,shade=True)
    rr=route+.5
    ax.plot(*rr.T,color=ORANGE,lw=2.5,zorder=30)
    ax.scatter(*rr[[0,-1]].T,color=[TEAL,ORANGE],s=24,depthshade=False,zorder=31)
    ax.set(xlabel='x',ylabel='y',zlabel='z',xlim=(0,L),ylim=(0,L),zlim=(0,L))
    ax.set_xticks([0,8,16]); ax.set_yticks([0,8,16]); ax.set_zticks([0,8,16])
    ax.tick_params(labelsize=7,pad=0)
    ax.set_box_aspect((1,1,1)); ax.view_init(elev=24,azim=-56)
    ax.set_title('(a) Bedrock and a valid 3D route',loc='left',pad=12)
    for a in [ax.xaxis,ax.yaxis,ax.zaxis]: a.pane.fill=False
    z0=7
    plain=air[:,:,z0]
    upright=plain&air[:,:,z0+1]
    for j,arr,title in [(1,plain,'(b) Air at z = 7'),(2,upright,'(c) Two-voxel clearance')]:
        a=fig.add_subplot(gs[j]); a.imshow(arr.T,origin='lower',cmap=ListedColormap([INK,PALE]),vmin=0,vmax=1,extent=(0,L,0,L),interpolation='none')
        a.set_xticks([0,8,16]);a.set_yticks([0,8,16]);a.set(xlabel='x',ylabel='y')
        a.set_title(title,loc='left',pad=12)
        a.set_xticks(np.arange(L+1),minor=True);a.set_yticks(np.arange(L+1),minor=True)
        a.grid(which='minor',color='white',lw=.25,alpha=.6);a.tick_params(which='minor',length=0)
    fig.legend(handles=[Patch(color=INK,label='Blocked / inadmissible'),Patch(facecolor=PALE,edgecolor=GRAY,label='Air / admissible'),Line2D([0],[0],color=ORANGE,lw=2,label='Upright route')],loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.52,-.015))
    save(fig,'01_geometry')

def spanning():
    fig,axs=plt.subplots(1,2,figsize=(7.6,3.3),sharey=True,layout='constrained')
    sweep=D[D.experiment==1]
    for ax,model,title in zip(axs,['point','upright'],['(a) One-voxel graph G','(b) Upright-body graph H']):
        for L,c,marker in [(16,BLUE,'o'),(32,TEAL,'s'),(48,ORANGE,'^')]:
            r=sweep[(sweep.model==model)&(sweep.L==L)].groupby('p').spanning.agg(['sum','count','mean'])
            ci=np.array([wilson(int(a['sum']),int(a['count'])) for _,a in r.iterrows()])
            ax.plot(r.index,r['mean'],color=c,marker=marker,ms=3,lw=1.4,label=f'L = {L}')
            ax.fill_between(r.index,ci[:,0],ci[:,1],color=c,alpha=.09)
        ax.axvline(2/3,color=INK,ls='--',lw=1)
        ax.text(2/3+.009,.31,'p = 2/3',rotation=90,color=INK,fontsize=8)
        ax.set(title=title,xlabel='Air probability p',xlim=(.19,.76),ylim=(-.03,1.03))
        ax.grid(axis='y');ax.legend(loc='lower right',frameon=False,fontsize=8)
    axs[0].axvline(.3116077,color=GRAY,ls=':',lw=1)
    axs[0].text(.3116077-.015,.45,'Point threshold ≈ 0.3116',rotation=90,ha='right',fontsize=7,color=GRAY)
    axs[0].set_ylabel('Opposite-face crossing probability')
    save(fig,'02_spanning')

def structure():
    fig,axs=plt.subplots(1,2,figsize=(7.6,3.2),layout='constrained')
    sub=D[(D.experiment==1)&(D.L==48)]
    for model,c,label in [('point',TEAL,'One voxel'),('upright',ORANGE,'Upright body')]:
        for ax,col in zip(axs,['giant_fraction','useful_face_fraction']):
            g=sub[sub.model==model].groupby('p')[col].agg(['mean','sem'])
            ax.plot(g.index,g['mean'],color=c,marker='o',ms=3,lw=1.7,label=label)
            ax.fill_between(g.index,g['mean']-1.96*g['sem'],g['mean']+1.96*g['sem'],color=c,alpha=.10)
    pp=np.linspace(.2,.75,250)
    axs[1].plot(pp,pp,color=TEAL,ls=':',lw=1,label='Availability p')
    axs[1].plot(pp,pp**2,color=ORANGE,ls=':',lw=1,label='Availability p²')
    for ax in axs:
        ax.axvline(2/3,color=INK,ls='--',lw=1); ax.grid(axis='y')
        ax.set(xlabel='Air probability p',xlim=(.19,.76),ylim=(-.025,1.025))
    axs[0].set(title='(a) Fraction of vertices in largest component',ylabel='Mean largest-component fraction')
    axs[1].set(title='(b) Useful entry locations on x = 0',ylabel='Mean useful fraction of the whole face')
    axs[0].legend(frameon=False,loc='lower right',fontsize=8)
    axs[1].legend(frameon=False,loc='upper left',fontsize=7)
    save(fig,'03_structure')

def routes():
    fig,axs=plt.subplots(1,2,figsize=(7.6,3.2),layout='constrained')
    focus=D[D.experiment==2]
    for model,c,label in [('point',TEAL,'One voxel'),('upright',ORANGE,'Upright body')]:
        sub=focus[focus.model==model]
        r=sub.groupby('L').useful_open_fraction.agg(['mean','sem'])
        axs[0].errorbar(r.index,r['mean'],yerr=1.96*r['sem'],color=c,marker='o',lw=1.5,capsize=3,label=label)
        for L,style in [(16,':'),(64,'-')]:
            vals=np.sort(sub[(sub.L==L)&(sub.random_success==1)].random_length.values/(L-1))
            axs[1].step(vals,np.arange(1,len(vals)+1)/len(vals),where='post',color=c,ls=style,lw=1.6,label=f'{label}, L = {L}')
    axs[0].set(title='(a) Reachability from a random open entry',xlabel='Cube side length L',ylabel='Mean fraction of open entries reaching exit',ylim=(.85,1.003),xticks=[16,32,64])
    axs[1].set(title='(b) Shortest-route detour from one entry',xlabel='Path length / (L − 1)',ylabel='Empirical cumulative probability',ylim=(0,1.02))
    for ax in axs: ax.grid(axis='y');ax.legend(frameon=False,fontsize=7,loc='lower right')
    save(fig,'04_routes')

def phases():
    fig,axs=plt.subplots(1,2,figsize=(7.6,3.05),layout='constrained')
    sub=D[(D.experiment==2)&(D.model=='point')]
    for column,c,label,offset in [('spanning',TEAL,'Air',-.9),('solid_spanning',GRAY,'Bedrock',.9)]:
        r=sub.groupby('L')[column].agg(['sum','count','mean'])
        ci=np.array([wilson(a['sum'],a['count']) for _,a in r.iterrows()])
        axs[0].errorbar(r.index+offset,r['mean'],yerr=[np.maximum(0,r['mean']-ci[:,0]),np.maximum(0,ci[:,1]-r['mean'])],fmt='o-',color=c,lw=1.5,capsize=3,label=label)
    for col,c,label in [('giant_fraction',TEAL,'Air'),('solid_giant',GRAY,'Bedrock')]:
        r=sub.groupby('L')[col].agg(['mean','sem'])
        axs[1].errorbar(r.index,r['mean'],yerr=1.96*r['sem'],fmt='o-',color=c,lw=1.5,capsize=3,label=label)
    for ax in axs:
        ax.set(xlabel='Cube side length L',xticks=[16,32,64],ylim=(0,1.035));ax.grid(axis='y');ax.legend(frameon=False,loc='lower right',fontsize=8)
    axs[0].set(title='(a) Both phases can cross the cube',ylabel='Opposite-face crossing probability')
    axs[1].set(title='(b) Connected space and fragmented obstacles',ylabel='Mean largest component / phase volume')
    save(fig,'05_two_phases')

def tables():
    summary=[]; rows=[]; moments=[]
    for (L,model),g in D[D.experiment==2].groupby(['L','model']):
        dist=g[g.random_success==1].random_length/(L-1)
        entry=g.useful_open_fraction
        r=dict(L=int(L),model=model,n=len(g),spans=int(g.spanning.sum()),
            span_ci=wilson(int(g.spanning.sum()),len(g)),
            giant_mean=g.giant_fraction.mean(),giant_se=se(g.giant_fraction),
            useful_face_mean=g.useful_face_fraction.mean(),
            entry_mean=entry.mean(),entry_se=se(entry),
            random_successes=int(g.random_success.sum()),
            detour_mean=dist.mean(),detour_sd=dist.std(ddof=1),
            detour_median=dist.median(),detour_q95=dist.quantile(.95),
            face_detour_mean=(g.shortest_face/(L-1)).mean(),
            cycles_per_vertex=(g.cycle_rank/g.vertices).mean(),
            solid_spans=int(g.solid_spanning.sum()),solid_giant_mean=g.solid_giant.mean())
        summary.append(r)
        name='One voxel' if model=='point' else 'Upright body'
        rows.append(f"{L} & {name} & {r['spans']}/{len(g)} & {100*r['giant_mean']:.2f} & {100*r['entry_mean']:.2f} & {r['detour_mean']:.3f} & {r['detour_q95']:.3f} " + chr(92)*2)
        p=2/3
        ev=L**3*p if model=='point' else L*L*(L-1)*p*p
        ee=3*L*L*(L-1)*p*p if model=='point' else 2*L*(L-1)**2*p**4+L*L*(L-2)*p**3
        moments.append(dict(L=int(L),model=model,vertices_expected=ev,vertices_mean=g.vertices.mean(),
             vertices_z=(g.vertices.mean()-ev)/se(g.vertices),edges_expected=ee,edges_mean=g.edges.mean(),
             edges_z=(g.edges.mean()-ee)/se(g.edges)))
    (ROOT/'data/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    pd.DataFrame(summary).to_csv(ROOT/'data/summary.csv',index=False)
    (ROOT/'data/moment_checks.json').write_text(json.dumps(moments,indent=2)+'\n')
    (ROOT/'results_rows.tex').write_text('\n'.join(rows)+'\n')
    # Keep the main manuscript's generated table synchronized with these data.
    manuscript=ROOT/'3d_labyrinth.tex'
    if manuscript.exists():
        import re
        tex=manuscript.read_text()
        block='% BEGIN GENERATED RESULTS\n'+'\n'.join(rows)+'\n% END GENERATED RESULTS'
        tex=re.sub(r'% BEGIN GENERATED RESULTS\n.*?\n% END GENERATED RESULTS',
                   lambda _: block,tex,flags=re.S)
        manuscript.write_text(tex)
    print(json.dumps(summary,indent=2));print('Moment checks:',json.dumps(moments,indent=2))

if __name__=='__main__':
    tables();geometry();spanning();structure();routes();phases()
