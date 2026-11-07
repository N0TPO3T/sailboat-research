"""Read frozen records and regenerate the manual's tables. No simulation/training."""
import argparse,csv,hashlib,json,math,shutil,statistics,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
def dump(name,obj):
    (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def csvout(name,rows):
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def mdtable(cols,rows):
    return '\n'.join(['| '+' | '.join(cols)+' |','|'+'|'.join(['---']*len(cols))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path);ap.add_argument('--archive',type=Path);a=ap.parse_args()
    if a.source:
        (HERE/'evidence').mkdir(exist_ok=True);(HERE/'figures').mkdir(exist_ok=True)
        for f in (a.source/'evidence').iterdir():
            if f.is_file():shutil.copy2(f,HERE/'evidence'/f.name)
        for name in ['figure1_interface.png','figure2_confirmation.png','figure5_rescue.png','figure6_adverse.png','figure3_guard.png','figure4_prediction.png']:
            shutil.copy2(a.source/'figures'/name,HERE/'figures'/name)
        dump('SOURCE_IDENTITY.json',{'source_directory':str(a.source),'files':{str(f.relative_to(a.source)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [a.source/'manuscript.md',a.source/'SUPPLEMENT.md',*sorted((a.source/'evidence').glob('*'))] if f.is_file()},'operation':'copy and aggregate records; no scientific code change or new experiment'})
    e=HERE/'evidence'; manifest=json.loads((e/'confirmation.json').read_text(encoding='utf-8-sig'));scenes={}
    for job in manifest['jobs']:
        s=job['scene'];sid=s['id']
        if sid in scenes:assert scenes[sid]==s
        scenes[sid]=s
    rows=list(csv.DictReader((e/'episodes.csv').open(encoding='utf-8-sig')))
    rows=[r for r in rows if r['stage']=='confirmation'];assert len(rows)==72 and len(scenes)==24
    by={(r['scene_id'],r['variant']):r for r in rows};assert len(by)==72
    variants=['reactive','simple','sampled']; names=['几何导航','简化预测','详细预测'];family={'mixed_pressure':'组合条件','underway_crossing':'交叉会遇','underway_overtaking':'追越','endpoint':'终点附近受阻','nonconflict':'非冲突'}
    safe=lambda r:r['success'].lower()=='true'
    rawcheck={'performed':False}
    if a.archive:
        with zipfile.ZipFile(a.archive) as z:
            checked=0;init={};initial=[]
            for n in z.namelist():
                if '/confirmation/' not in n or not n.endswith('/trace.json'):continue
                t=json.loads(z.read(n));r=t['row']; c=by[(r['scene_id'],r['variant'])]
                for key in ['time_s','cpu_seconds','path_length_m','min_dynamic_margin']:
                    assert math.isclose(float(c[key]),float(r[key]),abs_tol=1e-8,rel_tol=1e-10),(n,key)
                for key in ['success','arrived']:assert c[key].lower()==str(r[key]).lower()
                state=t['trajectory'][0]['raw'];sid=r['scene_id']
                if sid in init:assert state==init[sid]
                init[sid]=state
                checked+=1
            assert checked==72
            for sid in scenes:
                initial.append({'scene_id':sid,'initial_raw':json.dumps(init[sid])})
            csvout('INITIAL_STATES.csv',initial)
            frozen=json.loads((e/'freeze.json').read_text(encoding='utf-8-sig'));checks={}
            for n,h in frozen['sources'].items(): checks[n]=hashlib.sha256(z.read(n)).hexdigest()==h
            assert all(checks.values())
            for n in ['requirements.lock','README.md']:
                (HERE/('RECOVERY_'+n)).write_bytes(z.read(n))
            rawcheck={'performed':True,'rows_checked':checked,'checks':'CSV vs raw trace.row selected numeric/boolean fields; initial states same within scenario; not independent reintegration','frozen_source_hashes':checks,'archive_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest()}
    summary=[];paired=[];scenerows=[];detail=[]
    for v,n in zip(variants,names):
        rr=[r for r in rows if r['variant']==v]
        summary.append({'method':n,'variant':v,'n':len(rr),'safe':sum(safe(r) for r in rr),'arrived':sum(r['arrived']=='True' for r in rr),'min_dynamic_margin_m':min(float(r['min_dynamic_margin']) for r in rr),'cpu_total_s':sum(float(r['cpu_seconds']) for r in rr),'activated_tasks':sum(int(r['interventions'])>0 for r in rr)})
    for sid,s in scenes.items():
        q=s['vessels'][0]; scenerows.append({'scene_id':sid,'family':family[s['family']],'wind':s['profile'],'base_direction_deg':s['base_direction_degrees'],'seed':s['seed'],'target_initial_xy_m':json.dumps(q['position']),'target_velocity_xy_m_s':json.dumps(q['velocity']),'static':json.dumps(s['static'])})
        rr=[by[(sid,v)] for v in variants];pair=all(safe(r) for r in rr[1:]);dt=int(rr[2]['time_s'])-int(rr[1]['time_s']) if pair else None
        paired.append({'scene_id':sid,'included':pair,'simple_safe':safe(rr[1]),'detailed_safe':safe(rr[2]),'detailed_minus_simple_s':dt})
        line={'scene_id':sid,'family':family[s['family']],'wind':s['profile']}
        for v,r in zip(variants,rr):
            for k in ['success','arrived','time_s','min_dynamic_margin','min_static_margin','path_length_m','cpu_seconds','reason']:line[v+'_'+k]=r[k]
        detail.append(line)
    ds=[x['detailed_minus_simple_s'] for x in paired if x['included']]
    pairsummary={'n':len(ds),'faster':sum(d<0 for d in ds),'equal':sum(d==0 for d in ds),'slower':sum(d>0 for d in ds),'min_s':min(ds),'max_s':max(ds),'mean_s':statistics.mean(ds),'median_s':statistics.median(ds)}
    assert pairsummary=={'n':23,'faster':5,'equal':13,'slower':5,'min_s':-136,'max_s':308,'mean_s':7,'median_s':0}
    csvout('SCENES_24.csv',scenerows);csvout('RESULTS_24.csv',detail);csvout('PAIRED_TIMES.csv',paired)
    groups=[]
    for f in family:
        for w in ['stable','fast']:
            ids=[sid for sid,s in scenes.items() if s['family']==f and s['profile']==w]
            groups.append([family[f],w,len(ids),*[f'{sum(safe(by[(sid,v)]) for sid in ids)}/{len(ids)}' for v in variants]])
    dump('RECOMPUTED_RESULTS.json',{'summary':summary,'paired_time':pairsummary,'family_wind':groups,'raw_record_check':rawcheck})
    lines=['# 附录：24个场景的逐项结果','以下表格由随附脚本从记录生成；退出时间不自动等于到达时间。显示值按3位小数四舍五入，完整精度见CSV。','## 场景参数',mdtable(['场景','类别','风况','基础风向/°','目标初始位置/m','目标速度/(m/s)'],[[s['scene_id'],s['family'],{'stable':'恒定','fast':'变化'}[s['wind']],f"{s['base_direction_deg']:.3f}",'('+', '.join(f'{v:.3f}' for v in json.loads(s['target_initial_xy_m']))+')','('+', '.join(f'{v:.3f}' for v in json.loads(s['target_velocity_xy_m_s']))+')'] for s in scenerows]),'## 安全标签与记录时间','✓ 表示安全完成；×表示未安全完成。每格依次为安全标签、记录时间/s、最小动态裕度/m。精确值、是否到达及退出原因见 RESULTS_24.csv。']
    drows=[]
    for sid in scenes:
        cells=[]
        for v in variants:
            r=by[(sid,v)];cells.append(f"{'✓' if safe(r) else '×'}；{r['time_s']}；{float(r['min_dynamic_margin']):.3f}")
        drows.append([sid,*cells])
    lines.append(mdtable(['场景',*names],drows));lines+=['## 未安全完成记录',mdtable(['场景','方法','到达','退出原因','时间/s','动态裕度/m'],[[r['scene_id'],names[variants.index(r['variant'])],r['arrived'],r['reason'],r['time_s'],f"{float(r['min_dynamic_margin']):.6f}"] for r in rows if not safe(r)])]
    (HERE/'附录_逐场景结果.md').write_text('\n\n'.join(lines),encoding='utf-8')
    print(json.dumps({'summary':summary,'paired':pairsummary,'rawcheck':rawcheck},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
