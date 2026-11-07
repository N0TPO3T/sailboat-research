import os,sys
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']: os.environ[k]='1'
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'cache')
import argparse,hashlib,json,time,datetime,platform
import numpy as np
sys.path.insert(0,str(ROOT.parent/'turn_handover'))
from preflight import otter, attitudeEuler, force_bounds, force_to_shaft, shaft_to_force, forces_to_wrench, yaw_priority_allocation

os.environ['MPLCONFIGDIR']=str(ROOT/'cache')

def allocation(v,surge,yaw,lows,highs):
    arm=-v.l1
    difference=float(np.clip(yaw/arm,lows[0]-highs[1],highs[0]-lows[1]))
    lower=max(2*lows[0]-difference,2*lows[1]+difference)
    upper=min(2*highs[0]-difference,2*highs[1]+difference)
    total=float(np.clip(surge,lower,upper))
    forces=np.array([(total+difference)/2,(total-difference)/2])
    return force_to_shaft(v,forces),forces_to_wrench(v,forces),upper

def wrap(x): return (x+np.pi)%(2*np.pi)-np.pi

def path(radius,cruise,rate,brake):
    ds=.25; straight=80.
    s=np.arange(0,2*straight+np.pi*radius+ds/2,ds)
    s[-1]=min(s[-1],2*straight+np.pi*radius)
    x=np.empty_like(s);y=np.empty_like(s);heading=np.empty_like(s);curv=np.zeros_like(s)
    first=s<=straight; arc=(s>straight)&(s<straight+np.pi*radius); last=~(first|arc)
    x[first]=s[first];y[first]=0;heading[first]=0
    a=(s[arc]-straight)/radius
    x[arc]=straight+radius*np.sin(a);y[arc]=radius*(1-np.cos(a));heading[arc]=a;curv[arc]=1/radius
    x[last]=straight-(s[last]-straight-np.pi*radius);y[last]=2*radius;heading[last]=np.pi
    speeds=np.minimum(cruise,rate/np.maximum(curv,1e-8))
    for i in range(len(speeds)-2,-1,-1): speeds[i]=min(speeds[i],np.sqrt(speeds[i+1]**2+2*brake*ds))
    return s,np.c_[x,y],heading,speeds

def run(case,method,params,out,dt=.025):
    v=otter(V_current=case['current'],beta_current=90)
    R=case['radius'];cruise=case['cruise'];s,xy,tangent,plan_speed=path(R,cruise,params['rate'],params['brake'])
    eta=np.zeros(6);nu=np.zeros(6);nu[0]=cruise
    equilibrium=np.array([float(v.D[0,0])*cruise/2]*2)
    actual=force_to_shaft(v,equilibrium)
    iu=0.;iy=0.;idx=0;refspeed=cruise;prior_yaw=0.; filtered_rate=0.; beta_filtered=0.
    rows=[]; visited=set(); entered=None; arc_exit=None; completed=False;act=0; minmargin=1e9; maxerr=0.; ref_t=0.
    prevactual=actual.copy();effort=0.;shaftvariation=0.;reversals=0; prior_sign=np.sign(actual)
    lo,hi=force_bounds(v); derated=False; fault_time=None; lows=np.array([lo,lo]); highs=np.array([hi,hi]); factor=np.ones(2);corner=np.array([[1,.54],[1,-.54],[-1,.54],[-1,-.54]])
    for step in range(round(500/dt)):
        t=step*dt
        lower=max(0,idx-8);upper=min(len(s),idx+81)
        nearest=lower+int(np.argmin(np.sum((xy[lower:upper]-eta[:2])**2,axis=1)))
        idx=max(idx,nearest)
        if not derated and case['rho'] < 1 and s[idx]>=40:
            derated=True;fault_time=t;factor[case['side']]=case['rho'];lows=lo*factor;highs=hi*factor
        target=min(len(s)-1,idx+int(params['lookahead']/.25))
        beta_filtered+=dt/params.get('beta_tau',5.)*wrap(np.arctan2(nu[1],nu[0])-beta_filtered)
        psi_cmd=np.arctan2(xy[target,1]-eta[1],xy[target,0]-eta[0])-beta_filtered # filtered observed sideslip
        epsi=wrap(psi_cmd-eta[5]); yaw_rate_raw=wrap(psi_cmd-prior_yaw)/dt if step else 0.
        prior_yaw=psi_cmd;filtered_rate+=min(1.,dt/.5)*(np.clip(yaw_rate_raw,-.3,.3)-filtered_rate)
        curve_rate=nu[0]/R if 80 < s[idx] < 80+np.pi*R else 0.
        yaw_request=params.get('kp',30)*epsi+params.get('kd',45)*(curve_rate-nu[5])+iy
        want=plan_speed[idx]
        if method=='fixed' and derated: want=min(want,.9*2*float(min(highs))/float(v.D[0,0]))
        if method=='reserve':
            # A mature feasible-force reference governor, no future state lookup.
            _,_,upper_force=allocation(v,0.,yaw_request,lows,highs)
            available=max(0.,upper_force)
            feasible_speed=available/float(v.D[0,0])
            want=min(want,feasible_speed)
        if want < plan_speed[idx]-1e-3:act+=dt
        refspeed+=np.clip(want-refspeed,-params['brake']*dt,.15*dt)
        eu=refspeed-nu[0]
        surge_request=float(v.D[0,0])*refspeed+75*eu+iu
        command,allocated,_=allocation(v,surge_request,yaw_request,lows,highs)
        actual_wrench=forces_to_wrench(v,shaft_to_force(v,actual))
        # Integral state in force units; full actual actuator residual is common.
        iu+=dt*(18*eu+(actual_wrench[0]-surge_request)/1.5)
        iy+=dt*(1.5*epsi+(actual_wrench[1]-yaw_request)/1.5)
        iu=float(np.clip(iu,-120,120));iy=float(np.clip(iy,-50,50))
        nu,actual=v.dynamics(eta,nu,actual,command,dt)
        eta=attitudeEuler(eta,nu,dt)
        if not np.isfinite(np.r_[eta,nu,actual]).all(): raise RuntimeError('nonfinite')
        rotation=np.array([[np.cos(eta[5]),-np.sin(eta[5])],[np.sin(eta[5]),np.cos(eta[5])]])
        hull=corner@rotation.T+eta[:2]
        # Fixed rectangular permissible region, margin 2 vessel lengths.
        margin=min(hull[:,0].min()+4,80+R+4-hull[:,0].max(),hull[:,1].min()+4,2*R+4-hull[:,1].max())
        minmargin=min(minmargin,float(margin));err=float(np.linalg.norm(eta[:2]-xy[nearest]));maxerr=max(maxerr,err)
        course=np.arctan2(nu[0]*np.sin(eta[5])+nu[1]*np.cos(eta[5]),nu[0]*np.cos(eta[5])-nu[1]*np.sin(eta[5]))
        line=0 if s[idx]<80 else (1 if s[idx]>80+np.pi*R else -1)
        cross=abs(eta[1]-(2*R if line==1 else 0))
        valid=line>=0 and cross<=1 and abs(wrap(course-(np.pi if line==1 else 0)))<=np.deg2rad(10) and .8*cruise<=np.linalg.norm(nu[:2])<=1.2*cruise
        if valid and 0<=eta[0]<80:visited.add((line,int(eta[0])))
        if line==1 and arc_exit is None: arc_exit=t
        if line==1 and valid:
            ref_t+=dt
            if entered is None and ref_t>=3:entered=t-3+dt
        else:ref_t=0
        effort+=dt*float(np.sum(abs(shaft_to_force(v,actual))))
        shaftvariation+=float(np.sum(abs(actual-prevactual)));prevactual=actual.copy()
        signs=np.where(abs(actual)>2,np.sign(actual),prior_sign)
        reversals+=int(np.sum(signs*prior_sign<0));prior_sign=signs
        rows.append([t,*eta[:2],eta[5],*nu[:2],nu[5],s[idx],epsi,refspeed,*actual,margin,valid,actual_wrench[0],actual_wrench[1],float(derated),*command,*highs])
        if s[idx]>s[-1]-1 and np.linalg.norm(eta[:2]-xy[-1])<1.5:completed=True;break
    a=np.asarray(rows);out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/f"{case['id']}_{method}.npz",trajectory=a,reference=xy,path_s=s)
    result={'case':case,'method':method,'dt':dt,'params':params,'completed':completed,'safe_completed':completed and minmargin>=0,'fault_time_s':fault_time,'elapsed_s':t+dt,'min_hull_margin_m':minmargin,'max_path_distance_m':maxerr,'valid_line_m':len(visited),'line_capacity_m':160,'stable_return_entry_s':entered,'arc_exit_s':arc_exit,'stable_return_delay_s':None if entered is None or arc_exit is None else entered-arc_exit,'extra_speed_intervention_s':act,'force_activity_Ns':effort,'shaft_variation_rad_s':shaftvariation,'shaft_reversals':reversals,'trajectory_columns':['t','x','y','yaw','u','v','r','path_s','heading_error','speed_reference','shaft_left','shaft_right','hull_margin','valid_sample','actual_X','actual_N','derated','command_left','command_right','left_force_cap','right_force_cap']}
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['dev','main'],required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=False)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.time();results=[]
    common={'rate':.12,'brake':.15,'lookahead':4.}
    if args.mode=='dev':
        for rate in [.08,.12,.18]:
            par={**common,'rate':rate};case={'id':f'dev_rate_{rate}','radius':10.,'cruise':1.5,'current':0.}
            r=run(case,'curvature',par,out);results.append(r);print(json.dumps(r),flush=True)
    else:
        frozen=json.loads((ROOT/'FROZEN_CONFIG.json').read_text(encoding='utf-8-sig'));common=frozen['params']
        for case in frozen['cases']:
            for method in frozen['methods']:
                r=run(case,method,common,out);results.append(r);print(json.dumps(r),flush=True)
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    receipt={'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_s':time.time()-start,'pid':os.getpid(),'mode':args.mode,'python':sys.executable,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'upstream_commit':(ROOT.parent/'turn_handover/upstream_commit.txt').read_text().strip(),'threads':1,'gpu':0,'n_runs':len(results)}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (out/'pilot_snapshot.py').write_bytes(Path(__file__).read_bytes())
if __name__=='__main__':main()




