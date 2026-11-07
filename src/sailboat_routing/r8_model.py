"""Independent causal forward model: public observed states/commands only.
No real environment, wind field, RNG, target future or scene seed accepted.
"""
import ast,inspect,textwrap,math,copy
from types import MethodType
import numpy as np
from scipy.optimize import least_squares
from .runtime import SeniorModules
from .continuous import ContinuousPhysics
from .obstacle_candidate import ObstacleController
from .frames import LocalFrame
from .r7_dynamic import encode,replay,relative_minimum
from .metrics import segment_circle_clearance
from .planner import NoRouteError,NoLocalTargetError

class CausalModel:
    def __init__(self):
        self.modules=SeniorModules();self.physics=ContinuousPhysics(self.modules,total_time_limit=100000,world_radius_limit=100000)
        self.physics.reset(0,0);self.physics.env.update_wind=lambda:None
        self.policy=ObstacleController(mode='eval');self.wind=np.array([0.,8.]);self.fitted=False
        tree=ast.parse(textwrap.dedent(inspect.getsource(self.modules.environment.Sailboat_nowind_last.step)))
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='state_derivatives')
        node=copy.deepcopy(node);node.name='derivative'
        node.args=ast.parse('def f(self,state,action,t_local,initial_sail,initial_rudder,step_delta_sail,step_delta_rudder,tf):pass').body[0].args
        unit=ast.Module(body=[node],type_ignores=[]);ast.fix_missing_locations(unit)
        ns=dict(self.modules.environment.Sailboat_nowind_last.step.__globals__);exec(compile(unit,'<inherited derivative>','exec'),ns)
        self.derivative=MethodType(ns['derivative'],self.physics.env)
    def set_wind(self,w):
        g=self.modules.globals;g.w_change_v=float(np.linalg.norm(w));g.w_change_d=float(math.atan2(w[1],w[0]))
    def estimate(self,history):
        pairs=list(zip(history[-7:-1],history[-6:])) if len(history)>=7 else list(zip(history[:-1],history[1:]))
        if len(pairs)<3:return dict(wind=self.wind.tolist(),residual=None)
        samples=[]
        for x,y in pairs[::2]:
            mid=(np.asarray(x)+y)/2;mid[3]=x[3]+.5*math.atan2(math.sin(y[3]-x[3]),math.cos(y[3]-x[3]))
            samples.append((mid,np.asarray(y)[4:8]-np.asarray(x)[4:8]))
        def fun(w):
            self.set_wind(w);res=[]
            for m,d in samples:
                pred=self.derivative(m[:8],np.zeros(2),0.,m[8],m[9],0.,0.,1.)[4:8]
                res.extend((pred-d)*np.array([1,1,5,5]))
            return np.asarray(res)
        starts=[self.wind]
        if not self.fitted:starts += [8*np.array([math.cos(a),math.sin(a)]) for a in np.arange(0,2*math.pi,math.pi/3)]
        fits=[least_squares(fun,x,bounds=(-16,16),max_nfev=35,diff_step=1e-3) for x in starts]
        best=min(fits,key=lambda z:np.dot(z.fun,z.fun));self.wind=best.x;self.fitted=True;self.set_wind(self.wind)
        return dict(wind=self.wind.tolist(),residual=float(np.linalg.norm(best.fun)),source='observed_midpoint_acceleration_inverse_dynamics')
    def initialize(self,raw,commands):
        p=self.physics;g=self.modules.globals;p.raw=np.asarray(raw,dtype=np.float32).copy();p.env.state=p.raw.copy();g.state=p.env.state.copy();g.current_state=p.env.state[:12];g.current_time=0.;g.path=[]
        # Actuator setpoints are causal accumulations of actual issued commands.
        target=np.zeros(2);high=p.env.action_space.high.astype(float);limit=np.array([np.pi/2,np.pi/6]);degree=np.pi/180
        for a in commands:target=np.clip(target+np.asarray(a)*high//degree*degree,-limit,limit)
        p.env.target_sail_angle,p.env.target_rudder_angle=target;self.set_wind(self.wind)
    @staticmethod
    def future_obs(obs,delta,own):
        result=[]
        for o in obs:
            if not o['valid']:continue
            q=np.asarray(o['position'])+delta*np.asarray(o['velocity'])
            if np.linalg.norm(q-own)<=1000:result.append(dict(o,position=q.tolist(),time=o['time']+delta))
        return result
    def rollout(self,history,commands,observations,current_frame,target,old_action,horizon,static,goal,navigator=None,hold=0,pending=(),delay=0):
        # All arguments are public causal inputs. Every candidate gets same state/history.
        self.initialize(history[-1],commands);p=self.physics;h=list(history);acts=list(commands);oh=list(observations)
        obs,_=replay(self.policy,current_frame,static,oh,h,acts)
        reproduced=self.policy.act(obs).action
        if not np.array_equal(reproduced,old_action):raise AssertionError('Independent policy continuation differs')
        path=[p.raw[:2].astype(float).tolist()];margins=[];current=np.asarray(current_frame.goal_world);p.set_goal(current);frame=current_frame;valid=True;failure=None;info={'integration_failed':False};queue=[(item[0]-len(commands),item[1]) for item in pending]
        for k in range(int(horizon)):
            before=p.raw.copy();action=old_action if k==0 else self.policy.act(obs).action
            proposed=target
            if k>0 and navigator is not None and k>=hold:
                older=max(0,len(h)-11);velocity=(before[:2]-h[older][:2])/max(1,len(h)-1-older)
                incumbent=None if hold and k==hold else tuple(current)
                try:proposed=navigator.plan(before[:2],before[3],velocity,incumbent,goal,len(commands)+k,oh[-1])
                except (NoRouteError,NoLocalTargetError) as error:
                    valid=False;failure=type(error).__name__;break
            raw,_,_,_,info=p.step(action);h.append(raw);acts.append(action);forecast=self.future_obs(observations[-1],k+1,raw[:2]);oh.append(forecast)
            clear=segment_circle_clearance(before[:2],raw[:2],static)['safety_m']
            for o in observations[-1]:
                if o['valid']:
                    q=np.asarray(o['position']);w=np.asarray(o['velocity']);d,_=relative_minimum(before[:2],raw[:2],q+k*w,q+(k+1)*w);clear=min(clear,d-o['entity_radius']-o['safety_buffer'])
            margins.append(float(clear));path.append(raw[:2].astype(float).tolist())
            if info['integration_failed']:break
            if np.linalg.norm(raw[:2]-goal)<=10:break
            if np.linalg.norm(np.asarray(proposed)-current)>1e-6 and not queue:queue.append((k+1+delay,proposed))
            if queue and queue[0][0]<=k+1:
                _,applied=queue.pop(0);p.set_goal(applied);current=np.asarray(applied);frame=LocalFrame.for_leg(raw[:2],applied);obs,_=replay(self.policy,frame,static,oh,h,acts)
            else:obs=encode(frame,static,forecast,raw,before)
        return dict(path=path,margins=margins,min_margin=float(min(margins,default=-1e9)),terminal_distance=float(np.linalg.norm(np.asarray(path[-1])-goal)),integration_failed=bool(info['integration_failed']),valid=valid,prediction_failure=failure)
    def close(self):self.policy.close();self.physics.close()
