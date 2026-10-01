from utils import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from datetime import datetime
from SAC import SAC_countinuous
import gymnasium as gym
import os, shutil
import argparse
import torch
import globals
import time
from tqdm import tqdm
from stable_baselines3.common.vec_env import SubprocVecEnv
# from torch.utils.tensorboard import summary
from torchsummary import summary


'''Hyperparameter Setting'''
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=100, help='which model to load')

parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(10000), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(100e3), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(3e3), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=50, help='Training Fraquency, in stpes')

parser.add_argument('--gamma', type=float, default=0.99, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=3e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=3e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.12, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=4, help='Number of parallel environments')
opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc) # from str to torch.device
print(opt)


# def make_env(env_id, seed):
#     def _init():
#         env = gym.make(env_id)
#         env.seed(seed)
#         return env
#     return _init

def main():
    EnvName = ['sailboat-v1']
    BrifEnvName = ['SV1']

    # Build Env
    # env_fns = [make_env(EnvName[opt.EnvIdex], opt.seed + i) for i in range(opt.num_envs)]
    # env = SubprocVecEnv(env_fns)
    env = gym.make(EnvName[opt.EnvIdex], render_mode = "human" if opt.render else None)
    eval_env = gym.make(EnvName[opt.EnvIdex])
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)

    # opt.max_action = float(env.action_space.high[0])   #remark: action space【-max,max】
    # opt.max_e_steps = env._max_episode_steps
    opt.max_e_steps = 300
    print(f'Env:{EnvName[opt.EnvIdex]}  state_dim:{opt.state_dim}  action_dim:{opt.action_dim}  '
          f'max_a_s:{opt.max_action[0]}  max_a_r:{opt.max_action[1]} min_a_s:{env.action_space.low[0],env.action_space.low[1]}  max_e_steps:{opt.max_e_steps}')

    # act = env.action_space.sample()
    # a = Action_adapter_reverse(act, opt.max_action)
    # print('act:', act, 'a:', a)

    # Seed Everything
    env_seed = opt.seed
    torch.manual_seed(opt.seed)
    torch.cuda.manual_seed(opt.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print("Random Seed: {}".format(opt.seed))

    # Build SummaryWriter to record training curves
    if opt.write:
        from torch.utils.tensorboard import SummaryWriter
        timenow = str(datetime.now())[0:-10]
        timenow = ' ' + timenow[0:13] + '_' + timenow[-2::]
        writepath = 'runs/{}'.format(BrifEnvName[opt.EnvIdex]) + timenow
        if os.path.exists(writepath): shutil.rmtree(writepath)
        writer = SummaryWriter(log_dir=writepath)


    # Build DRL model
    if not os.path.exists('model'): os.mkdir('model')
    agent = SAC_countinuous(**vars(opt)) # var: transfer argparse to dictionary
    actor = agent.actor
    critic = agent.q_critic
    device_str = str(opt.dvc)
    # 包装类来适配 forward 方法的参数
    class ActorWrapper(torch.nn.Module):
        def __init__(self, actor):
            super(ActorWrapper, self).__init__()
            self.actor = actor

        def forward(self, x):
            # 确保返回第一个值（即输出张量）
            output, _, _ = self.actor(x, deterministic=True, with_logprob=False)
            return output

    wrapped_actor = ActorWrapper(actor)

    summary(wrapped_actor, (opt.state_dim,), device=device_str)
    summary(critic, [(opt.state_dim,), (opt.action_dim,)], device=device_str)
    if opt.Loadmodel: agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)

    if opt.render:
        while True:
            score = evaluate_policy(env, agent, turns=1)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        start_time = time.time()
        with tqdm(total=opt.Max_train_steps, desc='Training') as pbar:
            while total_steps < opt.Max_train_steps:
                s, info = env.reset(seed=env_seed)  # Do not use opt.seed directly, or it can overfit to opt.seed
                env_seed += 1
                done = False

                '''Interact & trian'''
                while not done:
                    if total_steps < (5*opt.max_e_steps):
                        act = env.action_space.sample()  # act∈[-max,max]
                        a = Action_adapter_reverse(act, opt.max_action)  # a∈[-1,1]
                    else:
                        a = agent.select_action(s, deterministic=False)  # a∈[-1,1]
                        act = Action_adapter(a, opt.max_action)  # act∈[-max,max]
                    s_next, r, dw, tr, info = env.step(act)  # dw: dead&win; tr: truncated
                    # r = Reward_adapter(r, opt.EnvIdex)
                    done = (dw or tr)

                    agent.replay_buffer.add(s, a, r, s_next, dw)
                    s = s_next
                    total_steps += 1

                    pbar.update(1)

                    '''train if it's time'''
                    # train 50 times every 50 steps rather than 1 training per step. Better!
                    if (total_steps >= 2*opt.max_e_steps) and (total_steps % opt.update_every == 0):
                        for j in range(opt.update_every):
                            agent.train()

                    '''record & log'''
                    if total_steps % opt.eval_interval == 0:
                        ep_r = evaluate_policy(eval_env, agent, turns=3)
                        if opt.write: writer.add_scalar('ep_r', ep_r, global_step=total_steps)
                        elapsed_time = time.time() - start_time
                        print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                            f'Episode Reward:{ep_r}, Elapsed Time:{elapsed_time:.2f}s')

                    '''save model'''
                    if total_steps % opt.save_interval == 0:
                        agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
        env.close()
        eval_env.close()


if __name__ == '__main__':
    main()