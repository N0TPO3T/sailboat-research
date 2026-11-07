"""Preserve reviewer requests and verbatim final responses, never hidden reasoning."""
import json, datetime, shutil
from pathlib import Path
P=Path(__file__).resolve().parent
root=P.parents[2]
trace=root/'.aris/traces/auto-paper-improvement-loop/2026-10-08_run01'
trace.mkdir(parents=True,exist_ok=True)
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
meta={'skill':'auto-paper-improvement-loop','run_id':'2026-10-08_run01','executor':'codex','executor_family':'openai','review_independence':'same-family, fresh context each round','acceptance_status':'provisional','project_dir':str(root),'artifact_dir':str(P)}
(trace/'run.meta.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
for n in (1,2):
    request=P/f'review_round{n}_request.json'
    response=P/f'review_round{n}.md'
    if request.exists():shutil.copy2(request,trace/f'{n:03d}-round-{n}-review.request.json')
    if response.exists():
        shutil.copy2(response,trace/f'{n:03d}-round-{n}-review.response.md')
        m={'call_number':n,'purpose':f'round-{n}-review','recorded_at':now,'agent_id':f'/root/paper_review_round{n}','model':'gpt-6-astra','reasoning_effort':'xhigh','reviewer_family':'openai','review_independence':'same-family, fresh context','acceptance_status':'provisional','status':'ok'}
        (trace/f'{n:03d}-round-{n}-review.meta.json').write_text(json.dumps(m,indent=2),encoding='utf8')
events=root/'.aris/meta/events.jsonl';events.parent.mkdir(parents=True,exist_ok=True)
seen=events.read_text(encoding='utf8') if events.exists() else ''
with events.open('a',encoding='utf8') as out:
    for n in (1,2):
        key=f'2026-10-08-paper-round-{n}'
        if (P/f'review_round{n}.md').exists() and key not in seen:
            out.write(json.dumps({'event':'review_trace','event_id':key,'skill':'auto-paper-improvement-loop','purpose':f'round-{n}-review','agent_id':f'/root/paper_review_round{n}','trace_path':str(trace),'status':'ok'})+'\n')
print(trace)
