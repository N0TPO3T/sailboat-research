import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from unittest.mock import patch
from types import SimpleNamespace
from sailboat_routing.r9_timing import TimedSupervisor
class Fake:
 def __init__(self):self.predictions=[];self.events=[];self.held=None;self.until=0;self.next_plan=0
 def plan(self,*args):
  self.predictions.append(dict(selected='turn90'));self.held=[100,100];self.until=60
  self.events.append(dict(time=args[5],event='enter'));return (100,100)
 def close(self):pass

def check(wall,slot,expect_status,ready):
 q=TimedSupervisor.__new__(TimedSupervisor);q.cfg=dict(period=60,slot=slot);q.inner=Fake();q.pending=None;q.timeline=[];q.events=[];q.predictions=[];q.log=[]
 args=([0,0],0,[0,0],(500,0),(1000,0),10,[])
 with patch('sailboat_routing.r9_timing.time.perf_counter',side_effect=[0,wall]):assert q.plan(*args)==(500,0)
 for t in range(11,ready):
  a=list(args);a[5]=t;assert q.plan(*a)==(500,0);assert not q.events
 a=list(args);a[5]=ready;out=q.plan(*a)
 assert q.timeline[0]['status']==expect_status
 if expect_status=='delivered':assert out==(100,100) and q.inner.until==ready+61
 else:assert out==(500,0)
 return dict(wall=wall,slot=slot,status=expect_status,ready=ready)
if __name__=='__main__':
 import json
 print(json.dumps([check(2.2,None,'delivered',13),check(2.2,25,'delivered',35),check(26.2,25,'deadline_drop',37),check(60.2,None,'age_drop',71)],indent=2))
