"""Golden CPU preflight for the frozen Aligned run; no formal training."""
import io,unittest
from chapter5_static import *
from test_chapter5_static import StaticRecoveryTests
from v2_v3_static_parity import reward_parts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=output_directory(args.output);c=read_config();bank_path=ROOT/c['static_eval_bank'];before=file_hash(bank_path)
    checks={};torch.manual_seed(101);agent=build_agent(c,'cpu');env=StaticEnvironment(c,'aligned')
    row=scenario(np.random.default_rng(101),c,0,'no_obstacle');obs=env.reset(row)
    checks['reset']=obs.shape==(18,);checks['observation_finite']=bool(np.isfinite(obs).all())
    hist=History(obs,10,'aligned');initial=obs.copy();states=[];actions=[];lstm_calls=[];att=[]
    hook=agent.actor.lstm.register_forward_pre_hook(lambda m,i:lstm_calls.append(len(i)))
    h2=agent.actor.attention.register_forward_hook(lambda m,i,o:att.append(bool(torch.isfinite(o[0]).all() and torch.isfinite(o[1]).all())))
    checks['padding']=True;checks['pairing']=True;checks['normalization_finite']=True;checks['actor_finite']=True;checks['critic_finite']=True;checks['reward_decomposition']=True
    for t in range(12):
        hs,ha=hist.arrays();padding=max(0,10-t)
        if padding:checks['padding'] &= bool(np.array_equal(hs[:padding],np.repeat(initial[None,:],padding,axis=0)) and np.all(ha[:padding]==0))
        if t:
            checks['pairing'] &= bool(np.array_equal(hs[padding:],np.array(states[-10:])) and np.array_equal(ha[padding:],np.array(actions[-10:])))
        norm=lambda x:agent.state_normalizer.normalize(torch.as_tensor(x).unsqueeze(0))
        checks['normalization_finite'] &= bool(torch.isfinite(norm(hs)).all())
        agent.actor.eval();action=act(agent.actor,agent.state_normalizer,obs,hist,'aligned')
        checks['actor_finite'] &= bool(np.isfinite(action).all())
        with torch.no_grad():q=agent.q_critic(state_sequence=norm(hs),action_sequence=torch.tensor(ha).unsqueeze(0),current_state=norm(obs),current_action=torch.tensor(action).unsqueeze(0),single_step_mode=False)
        checks['critic_finite'] &= all(bool(torch.isfinite(v).all()) for v in q)
        flags=[ref_globals.one_check,ref_globals.two_check,ref_globals.three_check]
        nxt,r,term,trunc,info=env.step(action);parts=reward_parts(env,r,trunc,flags)
        checks['reward_decomposition'] &= all(np.isfinite(v) for v in parts.values())
        states.append(obs.copy());actions.append(action.copy());hist.advance(obs,action,nxt);obs=nxt
    checks['zero_hidden_window']=all(n==1 for n in lstm_calls) and hidden_norm(agent.actor)==0
    checks['attention_finite']=all(att);hook.remove();h2.remove();env.close()
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(StaticRecoveryTests)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'regression.txt').write_text(stream.getvalue())
    checks.update(safety_termination=result.wasSuccessful(),strict_checkpoint_load=result.wasSuccessful(),exact_resume=result.wasSuccessful(),evaluation_rng_isolation=result.wasSuccessful(),bank_unchanged=before==file_hash(bank_path))
    write_json(out/'PRETRAIN_SANITY.json',dict(PRETRAIN_SANITY='PASSED' if all(checks.values()) else 'FAILED',checks=checks,regression_tests=result.testsRun,config_sha256=digest(c),bank_file_sha256=before,provenance=provenance(c,load_bank(bank_path)),formal_training_steps=0))
    print(json.dumps(checks,indent=2));assert all(checks.values())
if __name__=='__main__':main()
