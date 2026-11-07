"""R6 explicit controller/interface alternatives; original assets remain unchanged."""
from collections import deque
from time import perf_counter
from dataclasses import dataclass
import math
import sys
import numpy as np
import torch
from .runtime import ROOT, FrozenController, Decision, _load
from .frames import LocalFrame, reencode_controller as legacy_reencode
from .obstacle_candidate import ObstacleController

class WindowController(FrozenController):
    def __init__(self, modules, actor_path, normalizer_path, *, alignment="training", window=10):
        super().__init__(modules,actor_path,normalizer_path)
        assert alignment in ("training","past") and window>0
        self.alignment=alignment; self.window=window
    def reset(self, initial):
        super().reset(initial)
        self.observations=[]; self.actions=[]; self.initial=np.array(initial,copy=True)
    def act(self, observation, *, record_features=False):
        current=np.asarray(observation,dtype=np.float32)
        states=self.observations+([current] if self.alignment=="training" else [])
        acts=([np.zeros(2,dtype=np.float32)]+self.actions if self.alignment=="training" else self.actions)
        states=([self.initial]*(self.window-len(states))+states)[-self.window:]
        acts=([np.zeros(2,dtype=np.float32)]*(self.window-len(acts))+acts)[-self.window:]
        self._capture=record_features
        with torch.inference_mode():
            action,_=self.actor(state_sequence=self.normalizer.normalize(torch.tensor(np.array(states)[None])),
                action_sequence=torch.tensor(np.array(acts)[None],dtype=torch.float32),
                current_state=self.normalizer.normalize(torch.tensor(current[None])),deterministic=True,with_logprob=False)
        self._capture=False; action=action[0].numpy().copy()
        if not np.isfinite(action).all():raise FloatingPointError("Non-finite window action")
        self.observations=(self.observations+[current.copy()])[-self.window:]
        self.actions=(self.actions+[action.copy()])[-self.window:]
        self.previous=current.copy();self.previous_action=action.copy();self.steps+=1
        return Decision(action,None,self.steps)
    def change_frame(self,frame,history,commands):
        n=len(commands); start=max(0,n-self.window)
        self.observations=[frame.encode(history[i],None if i==0 else history[i-1]) for i in range(start,n)]
        self.actions=[np.asarray(a,dtype=np.float32).copy() for a in commands[start:]]
        self.initial=frame.encode(history[0],None)
        self.previous=(self.observations[-1].copy() if self.observations else self.initial.copy())
        self.previous_action=commands[-1].copy() if n else np.zeros(2,dtype=np.float32)
        return frame.encode(history[-1],history[-2] if n else None)

class FeedforwardController:
    def __init__(self,modules):
        previous=sys.modules.get("globals");sys.modules["globals"]=modules.globals
        try:network=_load("r6_fc",ROOT/"third_party/r6_reference/utils_fc.py")
        finally:
            if previous is None:sys.modules.pop("globals",None)
            else:sys.modules["globals"]=previous
        self.actor=network.Actor(14,2,(1024,512,256)).eval().requires_grad_(False)
        prefix=ROOT/"checkpoints/r6_original/sac_s14nowind_buf1e6_seed100"
        self.actor.load_state_dict(torch.load(str(prefix)+"_actor7200.pth",map_location="cpu",weights_only=True),strict=True)
        self.normalizer=network.ZScoreNormalizer(14,torch.device("cpu"))
        self.normalizer.load_state_dict(torch.load(str(prefix)+"_normalizer7200.pth",map_location="cpu",weights_only=True))
    def reset(self,initial):self.steps=0
    def act(self,observation,*,record_features=False):
        with torch.inference_mode():
            action,_=self.actor(current_state=self.normalizer.normalize(torch.tensor(observation[None],dtype=torch.float32)),deterministic=True)
        self.steps+=1
        return Decision(action[0].numpy().copy(),None,self.steps)
    def close(self):pass

@dataclass(frozen=True)
class ObstacleFrame:
    base: LocalFrame
    obstacles: tuple
    distance_mode: str = "center"
    @property
    def angle(self):return self.base.angle
    def wind_to_local(self,value):return self.base.wind_to_local(value)
    def encode(self,raw,previous=None):
        core=self.base.encode(raw,previous); near=[]
        if self.distance_mode=="none":return np.concatenate((core,np.zeros(4,dtype=np.float32)))
        if self.distance_mode not in ("center","boundary40"):raise ValueError(self.distance_mode)
        for obs in self.obstacles:
            delta=np.asarray(obs.center_xy)-np.asarray(raw[:2]);distance=float(np.linalg.norm(delta))
            if self.distance_mode=="boundary40":distance=max(0.,distance-obs.exclusion_radius+40.)
            if distance<=150:
                angle=math.atan2(delta[1],delta[0])-float(raw[3]);near.append((distance,math.atan2(math.sin(angle),math.cos(angle))))
        near.sort();extra=[v for pair in (near+[(0.,0.),(0.,0.)])[:2] for v in pair]
        return np.concatenate((core,np.array(extra,dtype=np.float32)))

class ObstacleFrameFactory:
    def __init__(self,obstacles,distance_mode="center"):self.obstacles=obstacles;self.distance_mode=distance_mode
    def for_leg(self,start,goal):return ObstacleFrame(LocalFrame.for_leg(start,goal),self.obstacles,self.distance_mode)

def change_reference(policy,frame,history,commands):
    started=perf_counter();n=len(commands)
    if isinstance(policy,WindowController):obs=policy.change_frame(frame,history,commands)
    elif isinstance(policy,FeedforwardController):obs=frame.encode(history[-1],history[-2] if n else None)
    elif getattr(policy,"reset_on_switch",False):
        policy.actor.reset_hidden_state()
        obs=frame.encode(history[-1],history[-2] if n else None)
        policy.previous=frame.encode(history[-2],history[-3] if n>1 else None) if n else obs.copy()
        policy.previous_action=commands[-1].copy() if n else np.zeros(2,dtype=np.float32)
        policy.steps=n
    else:return legacy_reencode(policy,frame,history,commands)
    return obs,perf_counter()-started
