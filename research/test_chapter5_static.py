"""Static protocol, scenario, safety, and exact-resume regression tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import importlib.util
import numpy as np
import torch
import chapter5_static as s


class StaticRecoveryTests(unittest.TestCase):
    def setUp(self):self.config=s.read_config()

    def test_v2_rejects_angle_noise_on_coordinate_slots(self):
        with self.assertRaisesRegex(ValueError,'global obstacle x/y'):
            s.StaticEnvironment(self.config,'legacy','v2')
        self.config['noise']['sensor_enabled']=False
        env=s.StaticEnvironment(self.config,'legacy','v2')
        env.close()

    def test_legacy_and_aligned_pairing(self):
        initial=np.full(18,10.,dtype=np.float32);nxt=np.full(18,11.,dtype=np.float32);action=np.array([.2,-.3],dtype=np.float32)
        legacy=s.History(initial,5,'legacy');aligned=s.History(initial,10,'aligned')
        legacy.advance(initial,action,nxt);aligned.advance(initial,action,nxt)
        self.assertEqual(legacy.states[-1][0],11.);self.assertEqual(aligned.states[-1][0],10.)
        np.testing.assert_array_equal(legacy.previous,aligned.previous)
        self.assertEqual(legacy.indices[-1],1);self.assertEqual(aligned.indices[-1],0)

    def test_bank_frozen_and_balanced(self):
        with tempfile.TemporaryDirectory(dir=s.ROOT/'work') as tmp:
            first=s.make_bank(self.config,Path(tmp)/'a.json');second=s.make_bank(self.config,Path(tmp)/'b.json')
            self.assertEqual(first,second);self.assertEqual(len(first['scenarios']),200)
            self.assertEqual(sum(r['kind']=='no_obstacle' for r in first['scenarios']),100)
            self.assertEqual(len({r['id'] for r in first['scenarios']}),200)
            for row in first['scenarios']:
                if row['kind']=='random_static':
                    self.assertTrue(5<=len(row['obstacles'])<=8)
                    for i,p in enumerate(row['obstacles']):
                        for q in row['obstacles'][i+1:]+[[0,0],[500,0]]:self.assertGreaterEqual(np.linalg.norm(np.array(p)-q),140.)

    def test_wind_and_noise_not_replay_rng(self):
        env=s.StaticEnvironment(self.config,'aligned')
        row=s.scenario(np.random.default_rng(5),self.config,0,'no_obstacle')
        tracks=[]
        try:
            for interference in [0,100]:
                env.reset(row);track=[]
                for _ in range(4):
                    np.random.randn(interference)
                    obs,r,t,tr,info=env.step(np.array([.1,-.1],dtype=np.float32));track.append(np.r_[obs,info['raw'],info['wind'],r])
                tracks.append(np.asarray(track))
        finally:env.close()
        np.testing.assert_array_equal(*tracks)

    def test_static_safety_segment_and_termination(self):
        a=np.array([-2.,39.99]);b=np.array([2.,39.99]);p=np.zeros(2)
        self.assertGreater(np.linalg.norm(a),40.);self.assertGreater(np.linalg.norm(b),40.)
        self.assertLess(s.segment_distance(a,b,p),40.)
        env=s.StaticEnvironment(self.config,'aligned')
        row=s.scenario(np.random.default_rng(1),self.config,0,'no_obstacle');row['obstacles']=[[0.,30.]]
        try:
            env.reset(row);_,reward,term,trunc,info=env.step(np.zeros(2,dtype=np.float32))
            self.assertTrue(info['safety_violation']);self.assertTrue(trunc);self.assertFalse(term)
            self.assertLess(reward,-90.)
        finally:env.close()

    def test_hidden_reset_legacy(self):
        torch.manual_seed(4);actor=s.Actor(18,2,(256,256));actor.history_window_size=5;actor.train()
        normalizer=s.ZScoreNormalizer(18,torch.device('cpu'))
        observations=np.random.default_rng(4).normal(size=(7,18)).astype('float32')
        outputs=[]
        for run in range(2):
            actor.reset_hidden_state();self.assertEqual(s.hidden_norm(actor),0.)
            torch.manual_seed(42);history=s.History(observations[0],5,'legacy');rows=[]
            for i in range(6):
                action=s.act(actor,normalizer,observations[i],history,'legacy');rows.append(action)
                history.advance(observations[i],action,observations[i+1])
            self.assertGreater(s.hidden_norm(actor),0.);self.assertEqual(len(actor.lstm_output_history['static']),5)
            outputs.append(np.asarray(rows))
        np.testing.assert_array_equal(*outputs)

    def test_trace_instrumentation_preserves_legacy_dynamics(self):
        env=s.StaticEnvironment(self.config,'legacy','v3')
        row=s.scenario(np.random.default_rng(29),self.config,0,'no_obstacle')
        original=s.ROOT/'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V3.py'
        spec=importlib.util.spec_from_file_location('unmodified_v3',original);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        traced=env.env.step;outputs=[]
        try:
            for method in [traced,module.Sailboat_obst_v3.step.__get__(env.env)]:
                env.env.step=method;env.reset(row);rows=[]
                for _ in range(3):rows.append(env.step(np.array([.1,-.1],dtype=np.float32))[4]['raw'])
                outputs.append(np.asarray(rows))
        finally:env.close()
        np.testing.assert_array_equal(*outputs)

    def test_freeze_refuses_failed_metrics(self):
        with tempfile.TemporaryDirectory(dir=s.ROOT/'work') as tmp:
            tmp=Path(tmp);evaluation=tmp/'evaluation';evaluation.mkdir()
            s.write_json(evaluation/'summary.json',dict(full_bank_evaluated=True,numerical_gate=False))
            s.write_json(tmp/'review.json',{})
            with self.assertRaises(AssertionError):s.freeze_baseline(evaluation,tmp/'review.json',tmp/'frozen')
            self.assertFalse((tmp/'frozen').exists())

    def test_exact_resume_and_config_guard(self):
        c=copy.deepcopy(self.config);c['noise']['sensor_enabled']=True;c['noise']['actuator_enabled']=True
        c['sac'].update(warmup_steps=10,batch_size=8,update_period=5,updates_per_period=4)
        c['checkpoint_interval']=20
        bank=s.load_bank(s.ROOT/c['static_eval_bank'])
        with tempfile.TemporaryDirectory(dir=s.ROOT/'work') as tmp:
            tmp=Path(tmp)
            full=s.train(c,bank,tmp/'full',40,'cpu',smoke=True,evaluate_checkpoints=False)
            middle=s.train(c,bank,tmp/'split',20,'cpu',smoke=True,evaluate_checkpoints=False)
            resumed=s.train(c,bank,tmp/'split',40,'cpu',resume=middle,smoke=True,evaluate_checkpoints=False)
            a=s.unpack(torch.load(full,weights_only=True));b=s.unpack(torch.load(resumed,weights_only=True))
            for group in ['actor','critic','target']:
                for key in a['agent'][group]:torch.testing.assert_close(a['agent'][group][key],b['agent'][group][key],atol=0,rtol=0)
            np.testing.assert_array_equal(a['loop']['observation'],b['loop']['observation'])
            self.assertEqual(a['agent']['training_step'],b['agent']['training_step'])
            self.assertGreater(a['agent']['training_step'],0)
            for key,value in a['agent']['replay'].items():
                if isinstance(value,torch.Tensor):torch.testing.assert_close(value,b['agent']['replay'][key],atol=0,rtol=0)
            changed=copy.deepcopy(c);changed['seed']+=1
            with self.assertRaises(AssertionError):s.check_resume(a,changed,bank,s.provenance(c,bank))

    def test_checkpoint_evaluation_preserves_training(self):
        c=copy.deepcopy(self.config);c['episode_limit']=5
        c['sac'].update(warmup_steps=10,batch_size=8,update_period=5,updates_per_period=4)
        c['checkpoint_interval']=20
        row=s.scenario(np.random.default_rng(22),c,0,'no_obstacle')
        bank=dict(scenarios=[row],bank_sha256=s.digest([row]))
        with tempfile.TemporaryDirectory(dir=s.ROOT/'work') as tmp:
            tmp=Path(tmp)
            plain=s.train(c,bank,tmp/'plain',40,'cpu',smoke=True,evaluate_checkpoints=False)
            evaluated=s.train(c,bank,tmp/'evaluated',40,'cpu',smoke=True,evaluate_checkpoints=True)
            a=s.unpack(torch.load(plain,weights_only=True));b=s.unpack(torch.load(evaluated,weights_only=True))
            for group in ['actor','critic','target']:
                for key in a['agent'][group]:torch.testing.assert_close(a['agent'][group][key],b['agent'][group][key],atol=0,rtol=0)


if __name__=='__main__':unittest.main(verbosity=2)
