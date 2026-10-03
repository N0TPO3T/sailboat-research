#!/usr/bin/env python3
"""R3 small analysis extension: unchanged R2 paired metrics plus actual risk application joins."""
from pathlib import Path
import json,sys,argparse,statistics
from analyze_r2 import analyze,write_csv
ROOT=Path(__file__).resolve().parents[1]
def risk_evidence(folder):
    rows=json.loads((folder/'analysis_rows.json').read_text());records=[]
    for row in rows:
        raw=ROOT/row['evidence'];log=raw.with_name('r3_decisions.json')
        if not log.exists():continue
        data=json.loads(raw.read_text());events=json.loads(log.read_text())
        applied={c['selected_at']:c for c in data['target_changes']}
        attempts=[x for x in events if x['attempt']]
        changes=[x for x in attempts if x.get('proposed_change',x.get('changed',False))]
        actual=[x for x in changes if x['time'] in applied]
        records.append(dict(scene_id=row['scene_id'],variant=row['variant'],
            decision_calls_risk=sum(x['risk_detected'] for x in events),risk_time_steps=len({x['time'] for x in events if x['risk_detected']}),attempts=len(attempts),
            proposed_changes=len(changes),actual_risk_changes=len(actual),
            nearest_obstacle_receding_attempts=sum(x.get('closing_speed') is not None and x['closing_speed']<=0 for x in attempts),
            attempts_with_all_trigger_obstacles_net_receding=sum(bool(x['risk_obstacles']) and all(o['closing_speed'] is not None and o['closing_speed']<=0 for o in x['risk_obstacles']) for x in attempts),
            missing_terminal_plan_record=row['reason'] in ['NoRouteError','NoLocalTargetError'] and not any(x.get('error') for x in events),
            safe_arrival=row['success'],first_actual_risk_time=actual[0]['time'] if actual else None,
            evidence=str(log.relative_to(ROOT))))
    write_csv(folder/'risk_mechanisms.csv',records)
    total={}
    for v in sorted({x['variant'] for x in records}):
        rr=[x for x in records if x['variant']==v]
        total[v]={k:sum(x[k] for x in rr) for k in ['decision_calls_risk','risk_time_steps','attempts','proposed_changes','actual_risk_changes','nearest_obstacle_receding_attempts','attempts_with_all_trigger_obstacles_net_receding','missing_terminal_plan_record']}
        total[v].update(episodes=len(rr),episodes_with_actual_risk_change=sum(x['actual_risk_changes']>0 for x in rr))
    (folder/'risk_summary.json').write_text(json.dumps(total,indent=2))
    return total
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--reference');a=ap.parse_args()
    folder=Path(a.folder).resolve();analyze(folder,a.reference);print(json.dumps(risk_evidence(folder),indent=2))
