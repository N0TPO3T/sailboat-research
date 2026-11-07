"""R9 replay optimization: reconstruct recurrence, omit unused historical action heads.
No history truncation, batching, changed normalization or learned parameters.
"""
from collections import deque
from time import perf_counter
import numpy as np
import torch
from .r7_dynamic import HistoricalFrame

def replay(policy,base,static,observations,history,commands):
    start=perf_counter();t=len(commands)
    assert len(observations)==len(history)==t+1
    frame=HistoricalFrame(base,static,observations)
    encoded=[frame.encode(x,None if i==0 else history[i-1]) for i,x in enumerate(history)]
    actor=policy.actor;actor.reset_hidden_state();zero=np.zeros(2,dtype=np.float32)
    with torch.inference_mode():
        for i in range(t):
            previous=encoded[0 if i==0 else i-1]
            pa=zero if i==0 else np.asarray(commands[i-1],dtype=np.float32)
            state=policy.normalizer.normalize(torch.from_numpy(previous).unsqueeze(0))
            action=torch.from_numpy(pa).unsqueeze(0)
            actor.lstm.flatten_parameters()
            x=actor.fc_input(torch.cat([state,action],dim=1).unsqueeze(1))
            if 'v0' not in actor.hidden_states:
                actor.hidden_states['v0']=(torch.zeros(1,actor.hidden_size),torch.zeros(1,actor.hidden_size))
            h,c=actor.hidden_states['v0']
            out,(hn,cn)=actor.lstm(x,(torch.cat([h],dim=0).unsqueeze(0),torch.cat([c],dim=0).unsqueeze(0)))
            actor.hidden_states['v0']=(hn[0,0:1,:],cn[0,0:1,:])
            out=actor.lstm_ln(out)[:,0,:]
            if 'v0' not in actor.lstm_output_history:
                actor.lstm_output_history['v0']=deque([torch.zeros(actor.hidden_size) for _ in range(actor.history_window_size)],maxlen=actor.history_window_size)
            actor.lstm_output_history['v0'].append(out[0].detach().clone())
    policy.previous=encoded[-2].copy() if t else encoded[0].copy()
    policy.previous_action=np.asarray(commands[-1],dtype=np.float32).copy() if t else zero
    policy.steps=t
    return encoded[-1],perf_counter()-start
