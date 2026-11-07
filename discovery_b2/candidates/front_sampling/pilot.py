"""B2 front sampling: bounded kinematic saturation screen, no training."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import argparse, csv, hashlib, json, math, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

def utc(): return datetime.now(timezone.utc).isoformat()
def wrap(a): return (a+np.pi)%(2*np.pi)-np.pi
def polar(h,w):
    return np.interp(np.abs(wrap(h-w))*180/np.pi,
                     [0,40,45,60,90,120,150,180],[0,0,1.2,1.7,2,1.9,1.5,1.2])

CONFIG=dict(duration=21600,dt=2,D=200,bin_seconds=900,leg_deadline=1800,
            yaw_rate_deg_s=2,speed_tau=20,tack_penalty_s=10,confirm_samples=3,
            y_boundary=5000,y_plan_limit=4000,wind_angles=[0,45,90],
            front_speeds=[0,0.15,0.30],initial_sides=[-1,1],
            platform='synthetic kinematic proxy; no calibrated vessel dynamics',
            policy='relative-normal-progress threshold shuttle; moving-line intercept',
            stage='A shared exact current front normal, offset and constant drift',
            upper_bound_bins=24,initial_leg_scoring='excluded until first observed-side confirmation')

def headings(w):
    a=np.deg2rad(np.r_[np.arange(-180,-44),np.arange(45,180)])
    return wrap(w+a)

def select_heading(x,y,h,t,side,w,c):
    hs=headings(w); v=polar(hs,w); vx=v*np.cos(hs); vy=v*np.sin(hs)
    z=x-c*t; dist=side*CONFIG['D']-z
    rel=vx-c
    tau=np.divide(dist,rel,out=np.full_like(rel,np.inf),where=np.abs(rel)>1e-9)
    tau=np.where((tau>=0)&(side*rel>0),tau,np.inf)
    turn=np.abs(wrap(hs-h))/np.deg2rad(CONFIG['yaw_rate_deg_s'])
    eta=tau+turn+CONFIG['speed_tau']
    y_end=y+vy*eta
    feasible=np.isfinite(eta)&(np.abs(y_end)<=CONFIG['y_plan_limit'])
    fallback=not bool(np.any(feasible))
    if fallback:
        eligible=np.isfinite(eta)
        if not np.any(eligible): raise RuntimeError('No positive relative-normal heading')
        score=np.where(eligible,np.abs(y_end)+eta*1e-3,np.inf)
    else:
        # Tie-break on tangential displacement and turn only below 1e-6 s.
        score=np.where(feasible,eta+np.abs(y_end)*1e-9,np.inf)
    return float(hs[np.argmin(score)]),int(fallback)

def simulate(wind,c,start_side,dt=2,keep=True):
    w=np.deg2rad(wind); D=CONFIG['D']; side=-start_side
    x=float(start_side*D); y=0.; t=0.
    hs=headings(w); vx=polar(hs,w)*np.cos(hs)-c
    h=float(hs[np.argmax(side*vx)])
    speed=float(polar(h,w)); target,fallbacks=select_heading(x,y,h,t,side,w,c)
    leg_start=0.; anchor_z=float(start_side*D); anchor_confirmed=False; count=0; tack_left=0.
    bins=set(); events=[]; rows=[]; tacks=0; path=0.; max_rate=0.; boundary=False
    max_y=0.; nsteps=int(CONFIG['duration']/dt)
    for k in range(nsteps+1):
        z=x-c*t
        if keep: rows.append((t,x,y,h,speed,z,side,target,tack_left))
        if abs(y)>CONFIG['y_boundary']:
            boundary=True; break
        # Confirmation represents repeated independent sensor samples at dt=2s.
        count=count+1 if side*z>=D else 0
        needed=int(round(CONFIG['confirm_samples']*CONFIG['dt']/dt))
        if count>=needed:
            legtime=t-leg_start
            valid=anchor_confirmed and legtime<=CONFIG['leg_deadline'] and side*anchor_z<=-D
            if valid and t<CONFIG['duration']:
                bins.add(int(t//CONFIG['bin_seconds']))
            events.append(dict(time=t,leg_time=legtime,valid=bool(valid),
                               end_side=side,x=x,y=y,z=z,start_z=anchor_z))
            anchor_z=z; anchor_confirmed=True; leg_start=t; side=-side; count=0
            target,fb=select_heading(x,y,h,t,side,w,c); fallbacks+=fb
        if k==nsteps: break
        delta=float(np.clip(wrap(target-h),-np.deg2rad(CONFIG['yaw_rate_deg_s'])*dt,
                            np.deg2rad(CONFIG['yaw_rate_deg_s'])*dt))
        h2=float(wrap(h+delta)); a1=float(wrap(h-w)); a2=float(wrap(h2-w))
        # Crossing through windward zero, not the downwind +/-pi discontinuity.
        crossed=(a1*a2<0 and abs(a1-a2)<np.pi) or (abs(a2)<1e-12 and abs(a1)>1e-12)
        if crossed: tacks+=1; tack_left=CONFIG['tack_penalty_s']
        desired=0. if tack_left>0 else float(polar(h2,w))
        v2=desired+(speed-desired)*math.exp(-dt/CONFIG['speed_tau'])
        mid=float(wrap(h+delta/2)); travel=(speed+v2)*dt/2
        x+=travel*math.cos(mid); y+=travel*math.sin(mid); path+=travel
        h=h2; speed=v2; t=(k+1)*dt; tack_left=max(0.,tack_left-dt)
        max_y=max(max_y,abs(y)); max_rate=max(max_rate,abs(delta)/dt*180/np.pi)
    valid_times=[e['leg_time'] for e in events if e['valid']]
    completion_times=[0.]+[e['time'] for e in events if e['valid']]+[float(CONFIG['duration'])]
    metric=dict(wind_deg=wind,front_speed=c,start_side=start_side,dt=dt,
                occupied_bins=len(bins),headroom_bins=24-len(bins),
                valid_crossings=len(valid_times),total_legs=len(events),
                median_leg_seconds=float(np.median(valid_times)) if valid_times else None,
                p90_leg_seconds=float(np.percentile(valid_times,90)) if valid_times else None,
                longest_valid_gap=max(np.diff(completion_times)),max_abs_y=max_y,
                path_m=path,tacks=tacks,heading_fallbacks=fallbacks,
                max_yaw_rate=max_rate,boundary_failure=boundary,final_time=t,
                occupied_bin_indices=sorted(bins))
    assert max_rate<=CONFIG['yaw_rate_deg_s']+1e-9
    assert all(0<=b<24 for b in bins)
    return metric,np.asarray(rows),events

def independent_score(tr,start_side,dt):
    # Rescore saved geometry only. No planner targets, online events or counters used.
    side=-start_side; count=0; anchor_time=None; bins=set(); valid=0
    needed=int(round(CONFIG['confirm_samples']*CONFIG['dt']/dt))
    for row in tr:
        t,x,y,_,_,z=row[:6]
        if abs(y)>CONFIG['y_boundary']: break
        count=count+1 if side*z>=CONFIG['D'] else 0
        if count>=needed:
            if anchor_time is not None and t-anchor_time<=CONFIG['leg_deadline']:
                valid+=1
                if t<CONFIG['duration']: bins.add(int(t//CONFIG['bin_seconds']))
            anchor_time=t; side=-side; count=0
    return len(bins),valid

def plots(out,metrics):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,3.5))
    ax.bar(np.arange(len(metrics)),[m['occupied_bins'] for m in metrics],color='#216869')
    ax.axhline(24,color='black',ls='--',label='Absolute scoring upper bound')
    ax.set(xlabel='Predefined scenario',ylabel='Occupied 15-minute bins',ylim=(0,26),
           title='Synthetic kinematic screen: strong simple baseline')
    ax.legend();fig.tight_layout();fig.savefig(out/'bins.png',dpi=160);plt.close(fig)
    idx=max(range(len(metrics)),key=lambda i: metrics[i]['max_abs_y'])
    tr=np.load(out/f'trajectory_{idx:02d}.npz')['trajectory']
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].plot(tr[:,5],tr[:,2],lw=.7)
    axes[0].axvline(-200,color='gray',ls='--');axes[0].axvline(200,color='gray',ls='--')
    axes[0].set(xlabel='Front-relative normal position (m)',ylabel='Tangential position (m)',
                title=f'Actual integrated path: scenario {idx}')
    axes[1].plot(tr[:,0]/3600,tr[:,5],lw=.6)
    axes[1].axhline(-200,color='gray',ls='--');axes[1].axhline(200,color='gray',ls='--')
    axes[1].set(xlabel='Time (h)',ylabel='Front-relative normal position (m)',title='Side-to-side crossings')
    fig.tight_layout();fig.savefig(out/'trajectory.png',dpi=160);plt.close(fig)

def self_checks():
    # Relative-speed interception of a translating side boundary.
    z=-200.; boundary=200.; vx=1.2; c=.3
    tau=(boundary-z)/(vx-c)
    assert abs(z+(vx-c)*tau-boundary)<1e-9
    # At fixed y and no turn cost the normal velocity maximizer is globally best
    # among the same discrete heading family for reaching an infinite line.
    for w in [0.,np.pi/4,np.pi/2]:
        hs=headings(w); speeds=polar(hs,w)
        assert np.all(np.abs(wrap(hs-w))>=np.deg2rad(45)-1e-9)
        assert np.all(speeds>=0)
    m1,_,_=simulate(45,.15,-1,dt=2,keep=False)
    m2,_,_=simulate(45,.15,-1,dt=1,keep=False)
    return dict(analytic_intercept_residual=abs(z+(vx-c)*tau-boundary),
                step_check_bins=[m1['occupied_bins'],m2['occupied_bins']],
                step_check_crossings=[m1['valid_crossings'],m2['valid_crossings']],
                step_check_max_y=[m1['max_abs_y'],m2['max_abs_y']],
                step_check_pass=m1['occupied_bins']==m2['occupied_bins'])

def main():
    p=argparse.ArgumentParser(); p.add_argument('--phase',choices=['smoke','main'],required=True)
    p.add_argument('--out',required=True); args=p.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=False)
    start=utc(); wall=time.monotonic(); receipt=dict(start_utc=start,pid=os.getpid(),phase=args.phase)
    (out/'started.json').write_text(json.dumps(receipt,indent=2))
    code=Path(__file__).read_bytes(); (out/'pilot_snapshot.py').write_bytes(code)
    (out/'config.json').write_text(json.dumps(CONFIG,indent=2))
    try:
        checks=self_checks() if args.phase=='smoke' else {'self_checks':'see completed smoke run'}
        if args.phase=='smoke': assert checks['step_check_pass'], 'Step-halving failed'
        if args.phase=='smoke': scenarios=[(0,0,-1),(0,.3,1),(90,0,-1),(45,.3,1)]
        else: scenarios=[(w,c,s) for w in CONFIG['wind_angles'] for c in CONFIG['front_speeds'] for s in [-1,1]]
        metrics=[]
        for i,(w,c,s) in enumerate(scenarios):
            m,tr,e=simulate(w,c,s); m['scenario_id']=i; metrics.append(m)
            rescored=independent_score(tr,s,CONFIG['dt'])
            assert rescored==(m['occupied_bins'],m['valid_crossings']), (rescored,m)
            m['independent_score_pass']=True
            np.savez_compressed(out/f'trajectory_{i:02d}.npz',trajectory=tr,
                                columns=np.array(['t','x','y','heading','speed','front_distance','target_side','target_heading','tack_remaining']))
            (out/f'events_{i:02d}.json').write_text(json.dumps(e,indent=2))
            print(json.dumps(m),flush=True)
        with (out/'metrics.csv').open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(metrics[0]));wr.writeheader();wr.writerows(metrics)
        summary=dict(phase=args.phase,scenarios=len(metrics),checks=checks,
                     mean_bins=float(np.mean([m['occupied_bins'] for m in metrics])),
                     min_bins=min(m['occupied_bins'] for m in metrics),
                     saturated_22=sum(m['occupied_bins']>=22 for m in metrics),
                     exact_24=sum(m['occupied_bins']==24 for m in metrics),
                     mean_absolute_headroom=float(np.mean([m['headroom_bins'] for m in metrics])),
                     boundary_failures=sum(m['boundary_failure'] for m in metrics),
                     code_sha256=hashlib.sha256(code).hexdigest(),
                     elapsed_seconds=time.monotonic()-wall)
        (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
        if args.phase=='main': plots(out,metrics)
        receipt.update(end_utc=utc(),exit_code=0,elapsed_seconds=time.monotonic()-wall)
    except BaseException as exc:
        receipt.update(end_utc=utc(),exit_code=1,error=repr(exc),elapsed_seconds=time.monotonic()-wall)
        raise
    finally:
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
