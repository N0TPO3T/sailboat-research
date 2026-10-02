#!/usr/bin/env python3
"""Serial bounded admission, real episode capture and paired V0 comparison."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import argparse, csv, json, math, signal, subprocess, time
import numpy as np
from sailboat_routing.admission import file_hash, definition_hash, load_admission
from sailboat_routing.experiments import Budget, output_directory
from sailboat_routing.navigation import run_episode, _write_json
from sailboat_routing.wind_readout import RidgeWindReadout, load_episode, split_episodes
from sailboat_routing.wind_fields import SyntheticWindField
from sailboat_routing.metrics import summarize_paired, METHODS

def protocol():
    d=json.loads((ROOT/'configs/navigation_contract.json').read_text())
    paths=sorted((ROOT/'src/sailboat_routing').glob('*.py'))+sorted((ROOT/'third_party/senior').glob('*.py'))
    paths += [ROOT/'configs/navigation_contract.json',ROOT/'configs/development_suite.json']
    d['source_files']={str(p.relative_to(ROOT)):file_hash(p) for p in paths}
    identity={k+'_sha256':file_hash(ROOT/d[k]) for k in ['actor','normalizer']}
    identity.update(protocol_sha256=definition_hash(d),feature_schema=d['feature_schema'])
    return {'protocol':d,'source_identity':identity}

def check_wind(trace, scene, suite, captured=None):
    field=SyntheticWindField(scene['seed']+100000,math.radians(scene['base_direction_degrees']),scene['profile'],horizon=suite['task_time_limit_s']+1)
    errors=[]
    for row in trace:
        expected=field.sample(row['raw'][:2],row['time'])[1]
        errors.append(abs(math.atan2(math.sin(expected-row['wind_direction_world']),math.cos(expected-row['wind_direction_world']))))
    assert max(errors)<1e-12
    if captured is not None:
        for i,t in enumerate(captured.decision_time):
            assert t==trace[i]['time']
            expected=trace[i]['wind_direction_world']-captured.frame_angle[i]
            assert abs(math.atan2(math.sin(expected-captured.labels_local_rad[i]),math.cos(expected-captured.labels_local_rad[i])))<1e-12
    return max(errors)

def admit(out,budget,suite):
    record=protocol()
    command=[sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-v']
    test=subprocess.run(command,cwd=ROOT,env=__import__('os').environ|{'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=120)
    (out/'tests.log').write_text(test.stdout+test.stderr)
    assert test.returncode==0, 'Regression failed; see tests.log'
    scene=suite['capture_scenarios'][0]
    on=out/'sidepath_on';off=out/'sidepath_off';on.mkdir();off.mkdir()
    a=run_episode(scene,suite,record,on,budget,capture=True)
    b=run_episode(scene,suite,record,off,budget,record_features=False)
    ta=json.loads((ROOT/a['evidence']).read_text());tb=json.loads((ROOT/b['evidence']).read_text())
    assert ta['trajectory']==tb['trajectory'], 'Sidepath changed physical trajectory/actions'
    assert a['complete'] and b['complete'] and a['navigation_success'], 'Pilot did not demonstrate navigation'
    assert a['target_changes']>0 and all(x['continuity_unchanged'] for x in ta['target_changes'])
    ep=load_episode(ROOT/a['dataset']);check_wind(ta['trajectory'],scene,suite,ep)
    changing=dict(suite['capture_scenarios'][1]);changing['id']='admission_slow'
    short=out/'changing_wind';short.mkdir()
    row=run_episode(changing,suite,record,short,budget,max_steps=140)
    trace=json.loads((ROOT/row['evidence']).read_text())['trajectory']
    err=check_wind(trace,changing,suite)
    assert max(x['wind_direction_world'] for x in trace)-min(x['wind_direction_world'] for x in trace)>1e-4
    identity=json.loads((ROOT/'docs/migration_identity.json').read_text())
    assert all(file_hash(ROOT/x['target'])==x['sha256'] for x in identity['migration_files'])
    assert json.loads((ROOT/'runs/stage_a/parity/result.json').read_text())['passed']
    checks={k:True for k in ['matched_assets','migration_parity','finite_dynamics','continuous_physics','causal_memory','feature_noninterference','navigation_demonstrated']}
    evidence=[out/'tests.log',ROOT/a['evidence'],ROOT/b['evidence'],ROOT/row['evidence'],ROOT/'runs/stage_a/parity/result.json',ROOT/'docs/migration_identity.json']
    record.update(schema=2,eligible_for_development=True,checks=checks,evidence=[{'path':str(p.relative_to(ROOT)),'sha256':file_hash(p)} for p in evidence])
    record['limits']='Development interface admission, not universal success; old B failure retained. Changing-wind check is bounded, not a capability estimate.'
    with (ROOT/'runs/navigation_admission.json').open('x') as f:json.dump(record,f,indent=2)
    _write_json(out/'result.json',{'passed':True,'pilot':a,'feature_sidepath_trajectory_error':0,'changing_wind_label_max_error':err,'admission':'runs/navigation_admission.json'})

def capture(out,budget,suite):
    a=load_admission();episodes=out/'episodes';episodes.mkdir()
    _write_json(out/'splits.json',suite['splits'])
    rows=[]
    with (out/'episodes.jsonl').open('x') as f:
        for scene in suite['capture_scenarios']:
            row=run_episode(scene,suite,a,episodes,budget,capture=True)
            assert row['complete'] and 'dataset' in row
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    split=split_episodes([load_episode(ROOT/x['dataset']) for x in rows],suite['splits'])
    _write_json(out/'result.json',{'episodes':rows,'split_counts':{k:len(v) for k,v in split.items()},'source_identity':a['source_identity'],'scope':'Real complete episodes including task failures; no fitting yet'})

def compare(out,budget,suite,model_path):
    a=load_admission();model=RidgeWindReadout.load(model_path,expected_source_identity=a['source_identity'],expected_dimension=270)
    rows=[]
    with (out/'episodes.jsonl').open('x') as f:
        for scene in suite['comparison_scenarios']:
            for method in METHODS:
                row=run_episode(scene,suite,a,out,budget,method=method,model=model if method=='estimated_local' else None)
                rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    result=summarize_paired(rows);result.update(source_identity=a['source_identity'],model_sha256=file_hash(model_path),scope='Fixed development scenes; no final-test/generalization claims')
    _write_json(out/'result.json',result)
    fields=[k for k in rows[0] if k!='source_identity']
    with (out/'episodes.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print(json.dumps(result),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['admit','capture','compare']);p.add_argument('--run-name',required=True);p.add_argument('--model',type=Path)
    args=p.parse_args();budget=Budget('v0_'+args.phase);budget.check();out=output_directory(args.run_name);status='failed'
    def timeout(signum,frame):raise TimeoutError('Cumulative experiment budget exhausted')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(1,budget.limit-budget.used))
    try:
        suite=json.loads((ROOT/'configs/development_suite.json').read_text());_write_json(out/'suite.json',suite)
        if args.phase=='admit':admit(out,budget,suite)
        elif args.phase=='capture':capture(out,budget,suite)
        else:
            if args.model is None:raise ValueError('--model required')
            model=args.model.resolve(strict=True)
            if not model.is_relative_to(ROOT):raise ValueError('Model must be inside NEW_ROOT')
            compare(out,budget,suite,model)
        status='completed'
    except Exception as error:
        _write_json(out/'error.json',{'type':type(error).__name__,'message':str(error)});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);budget.finish(status)
if __name__=='__main__':main()
