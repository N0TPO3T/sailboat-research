import argparse
import os
import traceback
import numpy as np
import torch
import gymnasium as gym
import multiprocessing as mp

from utils_lstm_att_normal import str2bool, Action_adapter
from SAC_lstm_att_normal import SAC_lstm_countinuous
from noise_utils import NoiseManager


def parse_args():
    parser = argparse.ArgumentParser(description='Batch test with multi-process parallelism')
    parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
    parser.add_argument('--env_name', type=str, default='sailboat-s14-obst-v3', help='Gym env name')
    parser.add_argument('--model_prefix', type=str, default='saclstm_s14obst_noise_0204', help='Model file prefix')
    parser.add_argument('--model_step', type=int, default=10800, help='Model checkpoint step')
    parser.add_argument('--num_episodes', type=int, default=300, help='Number of episodes for batch test')
    parser.add_argument('--max_e_steps', type=int, default=1000, help='Max steps per episode')
    parser.add_argument('--seed', type=int, default=0, help='Base random seed')
    parser.add_argument('--deterministic', type=str2bool, default=True, help='Use deterministic policy')

    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted factor')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')
    parser.add_argument('--a_lr', type=float, default=1e-4, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=1e-4, help='Learning rate of critic')
    parser.add_argument('--batch_size', type=int, default=256, help='Batch size of training')
    parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
    parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive alpha or not')

    parser.add_argument('--num_envs', type=int, default=4, help='并行进程数（保持原参数名兼容）')

    # 噪声参数（与训练脚本对齐）
    parser.add_argument('--enable_sensor_noise', type=str2bool, default=True, help='Enable sensor noise')
    parser.add_argument('--enable_actuator_noise', type=str2bool, default=True, help='Enable actuator noise')
    parser.add_argument('--sensor_noise_ratio', type=float, default=0.03, help='Sensor noise ratio (default 3%)')
    parser.add_argument('--actuator_noise_ratio', type=float, default=0.03, help='Actuator noise ratio (default 3%)')

    return parser.parse_args()


def check_model_files(model_prefix: str, model_step: int):
    model_files = [
        f'./model/{model_prefix}_actor{model_step}.pth',
        f'./model/{model_prefix}_q_critic{model_step}.pth',
        f'./model/{model_prefix}_normalizer{model_step}.pth',
    ]

    if not os.path.exists('./model'):
        raise FileNotFoundError('模型目录不存在: ./model')

    for model_file in model_files:
        if not os.path.exists(model_file):
            raise FileNotFoundError(f'模型文件不存在: {model_file}')


def episode_success(terminal_obs, info):
    for key in ('is_success', 'success', 'task_success', 'goal_reached'):
        if key in info:
            return bool(info[key])

    if terminal_obs is not None and len(terminal_obs) >= 14:
        final_dist = np.sqrt(
            (terminal_obs[0] - terminal_obs[12]) ** 2 +
            (terminal_obs[1] - terminal_obs[13]) ** 2
        )
        return final_dist <= 10.0

    return False


def split_episodes(num_episodes: int, num_workers: int):
    indices = np.arange(num_episodes)
    chunks = np.array_split(indices, num_workers)
    return [chunk.tolist() for chunk in chunks if len(chunk) > 0]


def worker_run(worker_id: int, episode_indices, opt_dict, result_queue):
    try:
        opt = argparse.Namespace(**opt_dict)
        opt.dvc = torch.device(opt.dvc)

        check_model_files(opt.model_prefix, opt.model_step)

        probe_env = gym.make(opt.env_name)
        probe_env.reset(seed=opt.seed + worker_id)
        opt.state_dim = probe_env.observation_space.shape[0]
        opt.action_dim = probe_env.action_space.shape[0]
        opt.max_action = probe_env.action_space.high.astype(float)
        probe_env.close()

        agent = SAC_lstm_countinuous(**vars(opt))
        agent.load(opt.model_prefix, opt.model_step)

        # 每个进程独立噪声管理器（与训练对齐）
        noise_manager = NoiseManager(
            sensor_noise_ratio=opt.sensor_noise_ratio,
            actuator_noise_ratio=opt.actuator_noise_ratio,
            enable_sensor_noise=opt.enable_sensor_noise,
            enable_actuator_noise=opt.enable_actuator_noise,
            seed=opt.seed + worker_id
        )

        for ep in episode_indices:
            env = gym.make(opt.env_name)
            s_raw, info = env.reset(seed=opt.seed + ep)

            # 初始观测加传感器噪声
            s = noise_manager.add_observation_noise(s_raw)

            prev_state = s.copy()
            prev_action = np.zeros(opt.action_dim, dtype=np.float32)
            env_id = f'proc{worker_id}_ep{ep}'
            agent.actor.reset_hidden_state(env_id)

            done = False
            step = 0
            # 成功判定使用真实末状态，不用噪声状态
            last_obs = s_raw
            last_info = info

            while (not done) and (step < opt.max_e_steps):
                # 策略输入：带噪状态 + 原始上一动作（与训练一致）
                a = agent.select_action(
                    prev_state,
                    prev_action,
                    s,
                    deterministic=opt.deterministic,
                    total_steps=None,
                    env_id=env_id,
                )

                # 执行动作前加执行器噪声
                a_noisy = noise_manager.add_action_noise(a, opt.max_action)
                act = Action_adapter(a_noisy, opt.max_action)

                s_next_raw, _, dw, tr, info = env.step(act)
                # 下一观测加传感器噪声
                s_next = noise_manager.add_observation_noise(s_next_raw)

                prev_state = s.copy()
                prev_action = a.copy()  # 注意：保持原始动作，不是 noisy 动作
                s = s_next
                last_obs = s_next_raw
                last_info = info

                step += 1
                done = bool(dw or tr)

            env.close()

            success = episode_success(last_obs, last_info)
            result_queue.put({
                'type': 'episode_result',
                'episode': ep,
                'steps': step,
                'success': bool(success),
                'worker_id': worker_id
            })

        result_queue.put({
            'type': 'worker_done',
            'worker_id': worker_id
        })

    except Exception as e:
        result_queue.put({
            'type': 'worker_error',
            'worker_id': worker_id,
            'error': str(e),
            'traceback': traceback.format_exc(),
        })


def run_batch_test(opt):
    num_workers = max(1, int(opt.num_envs))
    num_workers = min(num_workers, opt.num_episodes)

    print('=' * 70)
    print(f'开始批量测试: env={opt.env_name}, episodes={opt.num_episodes}')
    print(f'模型: {opt.model_prefix}, step={opt.model_step}')
    print(f'并行进程数: {num_workers}')
    print(
        f'噪声配置: sensor={opt.enable_sensor_noise}({opt.sensor_noise_ratio*100:.1f}%), '
        f'actuator={opt.enable_actuator_noise}({opt.actuator_noise_ratio*100:.1f}%)'
    )
    print('=' * 70)

    episode_splits = split_episodes(opt.num_episodes, num_workers)

    mp_ctx = mp.get_context('spawn')  # Windows 下推荐 spawn
    result_queue = mp_ctx.Queue()

    processes = []
    opt_dict = vars(opt).copy()

    for worker_id, ep_list in enumerate(episode_splits):
        p = mp_ctx.Process(
            target=worker_run,
            args=(worker_id, ep_list, opt_dict, result_queue),
            daemon=False
        )
        p.start()
        processes.append(p)

    done_workers = 0
    success_count = 0
    finished_episodes = 0
    errors = []

    total_workers = len(processes)

    while (finished_episodes < opt.num_episodes) or (done_workers < total_workers):
        msg = result_queue.get()

        if msg['type'] == 'episode_result':
            finished_episodes += 1
            success_count += int(msg['success'])

            # 按完成顺序实时打印
            print(
                f"Episode {msg['episode'] + 1:4d}/{opt.num_episodes} "
                f"| steps={msg['steps']:4d} | success={msg['success']} "
                f"| worker={msg['worker_id']}",
                flush=True
            )

        elif msg['type'] == 'worker_done':
            done_workers += 1

        elif msg['type'] == 'worker_error':
            errors.append(msg)
            break

    if errors:
        for p in processes:
            if p.is_alive():
                p.terminate()
        for p in processes:
            p.join(timeout=2)

        print('\n出现子进程错误：')
        for err in errors:
            print(f"[worker {err['worker_id']}] {err['error']}")
            print(err['traceback'])
        raise RuntimeError('批量测试失败：至少一个子进程报错。')

    for p in processes:
        p.join()

    success_rate = success_count / max(opt.num_episodes, 1)

    print('\n' + '=' * 70)
    print(f'成功回合数: {success_count}/{opt.num_episodes}')
    print(f'成功率: {success_rate * 100:.2f}%')
    print('=' * 70)


if __name__ == '__main__':
    options = parse_args()
    run_batch_test(options)
