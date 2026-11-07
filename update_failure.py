from pathlib import Path
p=Path(__file__).parent/'station.py';s=p.read_text(encoding='utf-8-sig')
s=s.replace("mode='start';last_u", "mode='start';integration_failed=False;last_u")
s=s.replace("if R*j.get('inner',.45)<d<R and", "if R*j.get('inner',.45)<d<R*j.get('outer',1.) and")
s=s.replace("if info['integration_failed']:break", "if info['integration_failed']:\n   integration_failed=True;break")
s=s.replace("inside_fraction=float(np.mean(~outs))", "inside_fraction=float(np.sum(~outs)/j.get('horizon',1200)),observed_fraction=float(np.mean(~outs))")
s=s.replace("max_radius=float(x.max())", "max_radius=float(max(z['d'] for z in trace))")
s=s.replace("completed=len(trace)-1==j.get('horizon',1200)", "completed=(len(trace)-1==j.get('horizon',1200) and not integration_failed),integration_failed=integration_failed,duration_s=len(trace)-1")
p.write_text(s,encoding='utf-8')
