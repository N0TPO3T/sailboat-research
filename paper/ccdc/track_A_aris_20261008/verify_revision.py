"""Read-only recomputation from frozen traces; no navigation or training runs."""
from pathlib import Path
import json, zipfile, math, statistics, hashlib, re

P = Path(__file__).resolve().parent
archive = P.parent / 'r13_revision/R13_REPRODUCTION_internal.zip'

def segment(p0, p1, q0, q1, radius):
    r = [p0[i]-q0[i] for i in range(2)]
    d = [(p1[i]-q1[i])-r[i] for i in range(2)]
    den = sum(x*x for x in d)
    a = min(1., max(0., -sum(r[i]*d[i] for i in range(2))/den)) if den > 1e-12 else 0.
    return math.hypot(*(r[i]+a*d[i] for i in range(2))) - radius

with zipfile.ZipFile(archive) as z:
    traces = [json.loads(z.read(n)) for n in z.namelist() if n.endswith('trace.json')]
assert len(traces) == 72
rows = [d['row'] for d in traces]
largest_error = 0.
intervals = 0
for trace in traces:
    tr, sc, row = trace['trajectory'], trace['scene'], trace['row']
    dynamic, static = math.inf, math.inf
    for a,b in zip(tr,tr[1:]):
        intervals += 1
        p0,p1 = a['raw'][:2],b['raw'][:2]
        for vessel in sc['vessels']:
            q0 = [vessel['position'][i]+a['time']*vessel['velocity'][i] for i in range(2)]
            q1 = [vessel['position'][i]+b['time']*vessel['velocity'][i] for i in range(2)]
            dynamic = min(dynamic,segment(p0,p1,q0,q1,85))
        for obs in sc['static']:
            static = min(static,segment(p0,p1,obs['center_xy'],obs['center_xy'],obs['entity_radius']+60))
    for value,key in [(dynamic,'min_dynamic_margin'),(static,'min_static_margin')]:
        if math.isfinite(value):
            err = abs(value-row[key]); largest_error=max(largest_error,err)
            # Recompute in Python float64; historical static evaluator keeps
            # float32 positions during subtraction. Allow 0.1 mm, far below
            # the smallest reported incursion (over 0.1 m).
            assert err < 1e-4,(row['scene_id'],row['variant'],key,value,row[key])
    assert row['success'] == (row['arrived'] and dynamic>0 and static>0)
variants = ['reactive','simple','sampled']
safe = {v:sum(r['success'] for r in rows if r['variant']==v) for v in variants}
assert list(safe.values()) == [19,23,24]
lookup = {(r['scene_id'],r['variant']):r for r in rows}
scene_ids = sorted({r['scene_id'] for r in rows})
pair_stats={}
for v,base in [('simple','reactive'),('sampled','reactive'),('sampled','simple')]:
    delta=[lookup[(s,v)]['time_s']-lookup[(s,base)]['time_s'] for s in scene_ids if lookup[(s,v)]['success'] and lookup[(s,base)]['success']]
    wins=sum(lookup[(s,v)]['success'] and not lookup[(s,base)]['success'] for s in scene_ids)
    losses=sum(not lookup[(s,v)]['success'] and lookup[(s,base)]['success'] for s in scene_ids)
    pair_stats[v+'-'+base]={'common_safe_n':len(delta),'mean_seconds':statistics.mean(delta),'median_seconds':statistics.median(delta),'max_seconds':max(delta),'wins':wins,'losses':losses}
families={f:{v:sum(r['success'] for r in rows if r['family']==f and r['variant']==v) for v in variants} for f in sorted({r['family'] for r in rows})}
source=P.parent/'track_A_submit'
orig=(source/'manuscript.md').read_text(encoding='utf8')
current=(P/'manuscript.md').read_text(encoding='utf8')
assert re.findall(r'\$\$(.*?)\$\$',orig,re.S)==re.findall(r'\$\$(.*?)\$\$',current,re.S)
assert [b for b in orig.split('\n\n') if b.startswith('|')]==[b for b in current.split('\n\n') if b.startswith('|')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'archive_sha256':sha(archive),'raw_traces':len(traces),'recomputed_intervals':intervals,'max_margin_error_m':largest_error,'safe':safe,'families':families,'paired':pair_stats,'cpu_seconds':{v:sum(r['cpu_seconds'] for r in rows if r['variant']==v) for v in variants},'equations_unchanged':True,'tables_unchanged':True,'new_navigation_runs':0,'training':False,'original_pdf_preserved':sha(source/'manuscript.pdf')==sha(P/'manuscript_round0_original.pdf')}
(P/'REVISION_VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
