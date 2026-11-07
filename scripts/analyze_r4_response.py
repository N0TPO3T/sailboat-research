#!/usr/bin/env python3
"""Descriptive manoeuvre windows from seen, real Relay trajectories only."""
from pathlib import Path
import argparse,csv,json,math,statistics,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def wrap(x):return (x+math.pi)%(2*math.pi)-math.pi
def distribution(values):
    return dict(n=len(values),median=float(np.median(values)),p90=float(np.quantile(values,.9)),maximum=max(values)) if values else dict(n=0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');args=ap.parse_args();out=Path(args.run)
    old=ROOT/'runs/r3_ccdc_20261003T121146Z/final';rows=json.loads((old/'rows.json').read_text())
    chosen=[x for x in rows if x['variant'] in ['relay_m120','relay_m160'] and x['scene_id'].startswith('s2271_')]
    segments=[];planning=[]
    for row in chosen:
        file=ROOT/row['evidence'];d=json.loads(file.read_text());tr=d['trajectory'];duration=int(tr[-1]['time'])
        if duration==0:continue
        starts=[(0,tr[1]['target'])]+[(int(e['applied_at']),e['target']) for e in d['target_changes']]
        for i,(t,q) in enumerate(starts):
            next_t=starts[i+1][0] if i+1<len(starts) else duration
            end=min(t+120,next_t,duration);p=np.array(tr[t]['raw'][:2]);q=np.array(q);delta=q-p;distance=float(np.linalg.norm(delta))
            if distance<1e-8:continue
            direction=delta/distance;left=np.array([-direction[1],direction[0]])
            xy=np.array([x['raw'][:2] for x in tr[t:end+1]])-p
            bearing=math.atan2(direction[1],direction[0]);initial_error=abs(wrap(tr[t]['raw'][3]-bearing));threshold=max(math.radians(10),initial_error*.5)
            errors=[abs(wrap(x['raw'][3]-bearing)) for x in tr[t:end+1]]
            responding=[j for j in range(1,len(errors)-2) if max(errors[j:j+3])<=threshold]
            response=responding[0] if initial_error>=math.radians(20) and responding else None
            status='not_required_small_heading_difference' if initial_error<math.radians(20) else 'responded' if response is not None else 'not_observed_full_window' if end==t+120 else 'censored_by_target_change' if next_t<duration else 'episode_ended_without_response'
            segment=dict(scene_id=row['scene_id'],variant=row['variant'],episode_success=row['success'],episode_reason=row['reason'],target_index=i,applied_at=t,end_at=end,window_s=end-t,target_distance_m=distance,initial_heading_error_deg=math.degrees(initial_error),initial_body_speed_mps=math.hypot(*tr[t]['raw'][4:6]),max_lateral_excursion_m=float(np.max(np.abs(xy@left))),signed_lateral_end_m=float(xy[-1]@left),along_target_progress_m=float(xy[-1]@direction),heading_response_s=response,response_status=status,end_reason='window_120s' if end==t+120 else 'target_change' if next_t<duration else row['reason'])
            segments.append(segment)
        for e in json.loads(file.with_name('r2_decisions.json').read_text()):
            planning.append(dict(scene_id=row['scene_id'],variant=row['variant'],time=e['time'],reason=e['reason'],margin=e['margin'],own_clearance=e['own_clearance'],fallback=e['fallback'],target_distance=math.dist(e['position'],e['target'])))
    keys=list(segments[0]);
    with (out/'response_segments.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(segments)
    with (out/'planning_space.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(planning[0]));w.writeheader();w.writerows(planning)
    from collections import Counter
    summary={'scope':'Seen seed2271, all72scenes x Relay120/160. Actual target segments; windows end at120s, next application or episode end. Not IID samples or safety bounds. Heading-error reduction is an observational proxy, not required sailing/tacking semantics.','episodes':len(chosen),'scenes':len({x['scene_id'] for x in chosen}),'segments':len(segments),'response_status':dict(Counter(x['response_status'] for x in segments)),'by_distance':{},'by_heading':{},'planning':{}}
    for name,select in [('short_le_150',lambda x:x['target_distance_m']<=150),('mid_150_350',lambda x:150<x['target_distance_m']<=350),('long_gt_350',lambda x:x['target_distance_m']>350)]:
        ss=[x for x in segments if select(x)];full=[x for x in ss if x['window_s']==120]
        summary['by_distance'][name]={'segments':len(ss),'full120':len(full),'response_status':dict(Counter(x['response_status'] for x in ss)),'full120_lateral_m':distribution([x['max_lateral_excursion_m'] for x in full]),'full120_progress_m':distribution([x['along_target_progress_m'] for x in full]),'observed_response_s':distribution([x['heading_response_s'] for x in ss if x['heading_response_s'] is not None])}
    for lo,hi in [(0,30),(30,90),(90,181)]:
        ss=[x for x in segments if lo<=x['initial_heading_error_deg']<hi];full=[x for x in ss if x['window_s']==120]
        summary['by_heading'][f'{lo}_{hi}']={'segments':len(ss),'full120':len(full),'full120_lateral_m':distribution([x['max_lateral_excursion_m'] for x in full]),'response_status':dict(Counter(x['response_status'] for x in ss))}
    for v in ['relay_m120','relay_m160']:
        ss=[x for x in planning if x['variant']==v];cap=int(v[-3:]);summary['planning'][v]={'calls':len(ss),'clipped':sum(x['margin']<cap-.001 for x in ss),'fallback':sum(x['fallback'] for x in ss),'margin':distribution([x['margin'] for x in ss]),'target_distance':distribution([x['target_distance'] for x in ss])}
    (out/'response_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
