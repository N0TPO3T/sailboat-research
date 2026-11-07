from pathlib import Path
p=Path(__file__).parent/'station.py'
s=p.read_text(encoding='utf-8-sig')
s=s.replace("x=np.array([z['d'] for z in trace]);outs=x>R;best=cur=0", "trace.append(dict(t=len(trace),raw=p.raw.tolist(),d=float(np.linalg.norm(p.raw[:2]-center)),desired_heading=None,mode='terminal',wind=m.globals.w_change_d,wind_speed=m.globals.w_change_v,command=None))\n x=np.array([z['d'] for z in trace[:-1]]);outs=x>R;best=cur=0")
s=s.replace("completed=len(trace)==j.get('horizon',1200)","completed=len(trace)-1==j.get('horizon',1200)")
s=s.replace("cpu_s=time.process_time()-cpu", "actuator_variation_rad=float(np.abs(np.diff(np.array([z['raw'][8:10] for z in trace]),axis=0)).sum()),max_heel_deg=float(max(abs(math.degrees(z['raw'][2])) for z in trace)),cpu_s=time.process_time()-cpu")
p.write_text(s,encoding='utf-8')
