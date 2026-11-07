"""Low-order, reference-conditioned finite course response. No truth/environment input."""
import math
import numpy as np
from .r8_model import CausalModel
from .r7_dynamic import relative_minimum
from .metrics import segment_circle_clearance
from .planner import NoRouteError,NoLocalTargetError

def wrap(a):return math.atan2(math.sin(a),math.cos(a))

def initial(history):
    h=np.asarray(history);v=np.diff(h[-6:,:2],axis=0)
    if len(v):
        speed=float(np.linalg.norm(v[-1]));course=math.atan2(v[-1,1],v[-1,0])
        rates=[wrap(math.atan2(b[1],b[0])-math.atan2(a[1],a[0])) for a,b in zip(v[:-1],v[1:])]
        rate=float(np.median(rates[-3:])) if rates else 0.
        drift=wrap(float(h[-1,3])-course)
    else:speed=float(np.linalg.norm(h[-1,4:6]));course=float(h[-1,3]);rate=0.;drift=0.
    return speed,course,rate,drift

def advance(p,course,rate,speed,target,params,respond=True):
    tau,gain,cap=params
    desired=float(np.clip(gain*wrap(math.atan2(target[1]-p[1],target[0]-p[0])-course),-cap,cap))
    newrate=rate+(desired-rate)*(1-math.exp(-1/tau)) if respond else rate
    newcourse=course+newrate
    q=p+speed*np.array([math.cos(course+.5*newrate),math.sin(course+.5*newrate)])
    return q,newcourse,newrate

class LowOrderModel:
    def __init__(self,params):self.params=params;self.wind=np.zeros(2)
    def estimate(self,history):return {'wind':None,'source':'motion_only_finite_course_response'}
    future_obs=staticmethod(CausalModel.future_obs)
    def rollout(self,history,commands,observations,current_frame,target,old_action,horizon,static,goal,navigator=None,hold=0,pending=(),delay=0):
        assert not pending and delay==0,'This matched comparator is scoped to ideal R8 delivery'
        p=np.array(history[-1][:2],float);speed,course,rate,drift=initial(history)
        current=np.asarray(current_frame.goal_world,float);path=[p.tolist()];margins=[];valid=True;failure=None
        hh=[np.asarray(x[:2],float) for x in history];obs=observations[-1]
        for k in range(int(horizon)):
            proposed=target
            if k>0 and navigator is not None and k>=hold:
                older=max(0,len(hh)-11);velocity=(p-hh[older])/max(1,len(hh)-1-older)
                incumbent=None if hold and k==hold else tuple(current)
                try:proposed=navigator.plan(p,wrap(course+drift),velocity,incumbent,goal,len(commands)+k,obs)
                except (NoRouteError,NoLocalTargetError) as error:valid=False;failure=type(error).__name__;break
            before=p.copy()
            # First interval remains independent of candidate, matching next-step delivery.
            p,course,rate=advance(p,course,rate,speed,current,self.params,respond=k>0)
            hh.append(p.copy());obs=self.future_obs(observations[-1],k+1,p)
            clear=segment_circle_clearance(before,p,static)['safety_m']
            for o in observations[-1]:
                if o['valid']:
                    q=np.asarray(o['position']);v=np.asarray(o['velocity']);dist,_=relative_minimum(before,p,q+k*v,q+(k+1)*v)
                    clear=min(clear,dist-o['entity_radius']-o['safety_buffer'])
            margins.append(float(clear));path.append(p.tolist())
            if np.linalg.norm(p-goal)<=10:break
            current=np.asarray(proposed,float)
        return dict(path=path,margins=margins,min_margin=min(margins,default=-1e9),terminal_distance=float(np.linalg.norm(p-goal)),integration_failed=False,valid=valid,prediction_failure=failure,predictor='low_order_course_response',speed=speed)
    def close(self):pass
