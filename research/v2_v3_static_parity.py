"""Read-only reference semantic audit. No training and no network modifications."""
import argparse, copy, gzip, json, math, sys, types
from collections import Counter
from pathlib import Path
from chapter5_static import *

PREFIX=ROOT/'research/supplements/yc_attention_121x/saclstm_s14obst_1213'

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,deque)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not math.isfinite(x):return None
    return x

def dump(f,x):f.write(json.dumps(clean(x),allow_nan=False,separators=(',',':'))+'\n')

def obstacle_view(env,row):
    x,y,_,psi=map(float,env.current[:4]); pts=row['obstacles']
    ids=lambda positions:[next(i for i,p in enumerate(pts) if np.linalg.norm(np.array(p)-q[:2])<1e-5) for q in positions]
    detected=env.env._detect_obstacles_in_fov(x,y,psi)
    cache=list(ref_globals.observed_obstacles)
    eligible=[p for p in cache if env.version=='v2' or math.hypot(p[0]-x,p[1]-y)<=150]
    selected=sorted(eligible,key=lambda p:math.hypot(p[0]-x,p[1]-y))[:2]
    return dict(global_positions=pts,detected_ids=ids(detected),cache_ids=ids(cache),selected_ids=ids(selected),
        distances=[math.hypot(p[0]-x,p[1]-y) for p in pts],
        bearings=[(math.atan2(p[1]-y,p[0]-x)-psi+math.pi)%(2*math.pi)-math.pi for p in pts])

def reward_parts(env,total,truncated,flags):
    s=ref_globals.current_state; a=ref_globals.current_action
    scale=.2+sum(.02 for v in a if abs(v)<=np.pi/180)
    progress=float((2*s[10]+s[11])*scale)
    velocity=float(.5*s[4]/(1+abs(s[5]))*scale)
    action=-sum(float(abs(v)//(np.pi/180))*(.2 if env.version=='v2' else .5)*scale for v in a if abs(v)>np.pi/180)
    obstacle=0.
    if env.version=='v2':
        for ox,oy in np.asarray(ref_globals.state[14:18]).reshape(2,2):
            if ox==0 and oy==0:continue
            d=math.hypot(s[0]-ox,s[1]-oy)
            if d<=100:obstacle-=100000*(1/max(d,50)-1/100)**2*scale
    else:
        obstacle=-sum(float(np.exp(-(d-40)/20)) for d in env.env.state[[14,16]] if 0<d<150)
    d=math.hypot(s[0]-ref_globals.state[12],s[1]-ref_globals.state[13])
    milestone=sum(v for threshold,v,flag in zip([375,250,125],[3,5,12],flags) if d<=threshold and flag==0)
    arrival=40 if d<=10 else 0; terminal=-100 if truncated else 0
    parts=dict(progress=progress,velocity=velocity,action=action,obstacle=obstacle,milestone=milestone,arrival=arrival,terminal=terminal,fixed=-.2)
    residual=float(total-sum(parts.values()))
    assert abs(residual)<2e-4,(env.version,residual,parts,total)
    return dict(**parts,total=total,sum_residual=residual)

def episode(row,version,config,actor,norm,path,full=True):
    env=StaticEnvironment(config,'legacy',version);torch.manual_seed(row['policy_seed'])
    actor.reset_hidden_state();actor.train(True);obs=env.reset(row);hist=History(obs,5,'legacy')
    capture={}
    hook=actor.mu_layer.register_forward_hook(lambda m,i,o:capture.update(mu=o.detach().cpu().numpy()[0].copy()))
    normed=lambda a:norm.normalize(torch.as_tensor(a,dtype=torch.float32)).detach().cpu().numpy()
    first_sensing=None; switches=0; previous=None; min_sep=float('inf'); violation=False; endpoint_violation=False
    records=[]
    with gzip.open(path,'wt') as f:
        for t in range(config['episode_limit']):
            pre=env.current.copy(); pre_view=obstacle_view(env,row)
            hbefore=hidden_norm(actor); wind_before=[ref_globals.w_change_v,ref_globals.w_change_d]
            action=act(actor,norm,obs,hist,'legacy')
            flags=[ref_globals.one_check,ref_globals.two_check,ref_globals.three_check]
            nxt,r,term,trunc,info=env.step(action);view=obstacle_view(env,row)
            if first_sensing is None and view['detected_ids']:
                first_sensing=dict(step=t+1,distances=[view['distances'][i] for i in view['detected_ids']])
            selected=view['selected_ids']
            if previous is not None and selected!=previous:switches+=1
            previous=selected;min_sep=min(min_sep,info['minimum_separation']);violation|=info['safety_violation'];endpoint_violation|=info['endpoint_separation']<40
            rec=dict(step=t,boat_before=pre[:10],wind_before=wind_before,obstacle_before=pre_view,
                observation=dict(raw=pre,sensor=obs,normalized=normed(obs)),
                history=dict(stream_state_index=max(0,t-1),stream_action_index=t-1,previous_state=hist.previous,previous_action=hist.previous_action,
                    previous_normalized=normed(hist.previous),attention_token_indices=list(range(max(0,t-4),t+1)),hidden_before=hbefore,hidden_after=hidden_norm(actor)),
                policy=dict(actor_mean=capture['mu'],deterministic_action=action,physical_action=info['physical_action'],dropout=True),
                boat_after=env.current[:10],obstacle_after=view,raw_after=env.current,
                reward=reward_parts(env,r,trunc,flags),
                termination=dict(arrival=term,timeout=info['timeout'],range=info['out_of_bounds'],safety_violation=info['safety_violation'],endpoint_violation=info['endpoint_separation']<40,truncated=trunc),
                minimum_separation=info['minimum_separation'],wind_after=info['wind'])
            dump(f,rec if full else dict(step=t,boat_after=rec['boat_after'],obstacle_after=view,termination=rec['termination'],minimum_separation=rec['minimum_separation']))
            if full:records.append(clean(rec))
            hist.advance(obs,action,nxt);obs=nxt
            if term or trunc:break
    hook.remove();env.close()
    return dict(id=row['id'],version=version,steps=t+1,safe_success=bool(term and not violation),violation=bool(violation),endpoint_violation=bool(endpoint_violation),minimum_separation=clean(min_sep),first_sensing=first_sensing,slot_changes=switches),records

def first(a,b,path=''):
    if isinstance(a,dict):
        for k in a:
            d=first(a[k],b[k],path+'.'+k)
            if d:return d
    elif isinstance(a,list):
        if len(a)!=len(b):return dict(variable=path,v2=a,v3=b)
        for i,(x,y) in enumerate(zip(a,b)):
            d=first(x,y,f'{path}[{i}]')
            if d:return d
    elif isinstance(a,(int,float)) and not isinstance(a,bool):
        if not np.isclose(a,b,rtol=1e-6,atol=1e-6):return dict(variable=path,v2=a,v3=b)
    elif a!=b:return dict(variable=path,v2=a,v3=b)

def compare(a,b):
    groups=['observation','history','policy','boat_after','obstacle_after','raw_after','reward','termination','wind_after']
    result={}
    for x,y in zip(a,b):
        for g in groups:
            if g not in result:
                d=first(x[g],y[g],g)
                if d:result[g]=dict(step=x['step'],**d)
    return dict(first_by_channel=result,compared_steps=min(len(a),len(b)),lengths=[len(a),len(b)])

def probes(config,norm):
    results=[]
    cases=[('representation',0,[[90,30]],[[90,30]]),('cached_behind',0,[[-80,0]],[[-80,0]]),('cached_outside_range',0,[[151,0]],[[151,0]]),
           ('padding',0,[],[]),('sort_tie',0,[[80,60],[80,-60]],[[80,60],[80,-60]]),
           ('fov_inside',0,[[100*math.cos(math.radians(59.999)),100*math.sin(math.radians(59.999))]],[]),
           ('fov_outside',0,[[100*math.cos(math.radians(60.001)),100*math.sin(math.radians(60.001))]],[]),
           ('range_boundary',0,[[150,0]],[]),('range_outside',0,[[150.001,0]],[]),('rotated',math.pi/2,[[0,100]],[[0,100]])]
    for name,heading,pts,cache in cases:
        rec=dict(case=name,versions={})
        for version in ['v2','v3']:
            env=StaticEnvironment(config,'legacy',version)
            row=scenario(np.random.default_rng(7),config,0,'no_obstacle');row['obstacles']=pts;row['initial_state'][3]=heading
            env.reset(row);ref_globals.observed_obstacles=cache.copy()
            selected=env.env._get_two_nearest_obstacles(0,0) if version=='v2' else env.env._get_two_nearest_obstacles(0,0,heading)
            raw=env.current.copy();raw[14:18]=np.array(selected).reshape(-1)
            rec['versions'][version]=dict(detected=env.env._detect_obstacles_in_fov(0,0,heading),slots=selected,normalized_slots=norm.normalize(torch.tensor(raw))[14:].tolist())
            env.close()
        results.append(rec)
    return results

def geometry(row):
    pts=np.array(row['obstacles']);route=np.array([500.,0.]);a=np.zeros(2)
    distances=[segment_distance(a,route,p) for p in pts]
    overlaps=[(i,j) for i in range(len(pts)) for j in range(i) if np.linalg.norm(pts[i]-pts[j])<80]
    # Conservative raster connectivity: 5m grid, inflate by half cell diagonal;
    # bounded rectangle is a proxy only, not sailing reachability.
    xs=np.arange(0,501,5);ys=np.arange(-250,251,5)
    blocked=np.zeros((len(xs),len(ys)),bool)
    for p in pts:blocked|=(xs[:,None]-p[0])**2+(ys[None,:]-p[1])**2< (40+math.sqrt(12.5))**2
    start=(0,50);goal=(100,50);seen={start};q=deque([start]) if not blocked[start] else deque()
    while q:
        i,j=q.popleft()
        for v in [(i-1,j),(i+1,j),(i,j-1),(i,j+1)]:
            if 0<=v[0]<101 and 0<=v[1]<101 and not blocked[v] and v not in seen:seen.add(v);q.append(v)
    return dict(id=row['id'],count=len(pts),nearest_route_distance=min(distances),route_intersecting_circles=sum(d<40 for d in distances),overlapping_pairs=overlaps,
        geometric_path_exists=goal in seen,mean_wind_degrees=row['mean_wind_degrees'],density_per_km2=len(pts)/.25)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--bank-only',action='store_true');args=ap.parse_args()
    out=output_directory(args.output);c=read_config()
    if not args.bank_only:
        # Controlled noise-off comparison: current angle noise is invalid for V2 x/y slots.
        c['noise']['sensor_enabled']=False;c['noise']['actuator_enabled']=False
    actor,critic,norm,hashes=load_weights(PREFIX,15600,c,'legacy')
    write_json(out/'identity.json',dict(config=c,hashes=hashes,source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in [Path(__file__),ROOT/'research/chapter5_static.py',*[ROOT/f'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_{v}.py' for v in ['V2','V3']]]},normalizer=clean({k:v.tolist() if torch.is_tensor(v) else v for k,v in norm.state_dict().items()})))
    if not args.bank_only:
        layouts=[('simple',[[170,25]]),('simple',[[210,-25]]),('simple',[[270,30]]),('medium',[[160,35],[290,-40]]),('medium',[[190,-35],[330,40]]),('medium',[[140,40],[260,-45],[370,45]]),('turn',[[110,0],[230,70]]),('turn',[[120,0],[240,-70]]),('control',[]),('control',[])]
        rows=[]
        for i,(kind,pts) in enumerate(layouts):
            row=scenario(np.random.default_rng(260915+i),c,i,'no_obstacle',90 if i!=9 else 0);row.update(id=f'{kind}_{i:02}',kind=kind,obstacles=pts);row['initial_state'][3]=0;rows.append(row)
        write_json(out/'paired_scenarios.json',dict(scenarios=rows,sha256=digest(rows),difficulty='a priori geometric design labels, not measured difficulty',matched=['initial_state','mean_wind_speed','mean_wind_direction','wind_seed_integer','sensor_seed','actuator_seed','policy_seed'],unmatched=['native wind process V2 AR versus V3 Dryden; same seed does not yield same wind','native actuator integration semantics']))
        write_json(out/'same_state_probes.json',probes(c,norm))
        allresults=[]
        for row in rows:
            r2,t2=episode(row,'v2',c,actor,norm,out/(row['id']+'_v2.jsonl.gz'))
            r3,t3=episode(row,'v3',c,actor,norm,out/(row['id']+'_v3.jsonl.gz'))
            allresults.append(dict(id=row['id'],v2=r2,v3=r3,divergence=compare(t2,t3)))
            write_json(out/'paired_results.json',allresults,exclusive=False);print(row['id'],r2['safe_success'],r3['safe_success'],flush=True)
    else:
        bank=load_bank(ROOT/c['static_eval_bank']);rows=[r for r in bank['scenarios'] if r['obstacles']];results=[]
        for row in rows:
            r,_=episode(row,'v3',c,actor,norm,out/(row['id']+'.jsonl.gz'),full=False);r['geometry']=geometry(row);results.append(r)
            write_json(out/'bank_results.json',dict(bank_sha256=bank['bank_sha256'],episodes=results),exclusive=False)
            print(len(results),row['id'],r['safe_success'],flush=True)
if __name__=='__main__':main()
