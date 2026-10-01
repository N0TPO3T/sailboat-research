import torch
import jax
import jax.numpy as jnp
from torch.utils.dlpack import to_dlpack, from_dlpack
from .sailboat_jax_env import SailboatJaxEnv

class VecSailboatJaxWrapper:
    """
    将 JAX 帆船环境包装为支持 GPU Tensor 的 PyTorch 环境。
    自动处理 JAX 的 vmap (并行化)。
    """
    def __init__(self, num_envs, device='cuda'):
        self.num_envs = num_envs
        self.device = device
        
        # 初始化 JAX 环境
        self._env = SailboatJaxEnv()
        
        # 编译 step 和 reset 函数 (JIT Compilation)
        # 这一步是性能的关键：它将 Python 循环编译为高效的 GPU 核心
        self._step_fn = jax.jit(jax.vmap(self._env.step))
        self._reset_fn = jax.jit(jax.vmap(self._env.reset))
        
        # 状态保持
        self.state = None
        self.rng = jax.random.PRNGKey(0)
        
    def reset(self):
        # 生成 num_envs 个随机种子
        self.rng, split_key = jax.random.split(self.rng)
        split_keys = jax.random.split(split_key, self.num_envs)
        
        # 批量 Reset
        self.state = self._reset_fn(split_keys, split_keys) # Arg2 dummy
        
        # 返回 PyTorch Tensor
        return self._jax_to_torch(self.state.obs_vec)

    def step(self, actions_torch):
        """
        step 接受 PyTorch Tensor 动作，返回 PyTorch Tensors
        """
        # 1. PyTorch -> JAX (Zero-copy ideally)
        # 确保 actions 在正确的 device 上
        if actions_torch.device.type != 'xla': 
            # 如果 JAX 在 GPU 上，to_dlpack 转换很快
            # 注意：如果 JAX 使用 CPU 版本，这里会发生数据复制
            actions_jax = jax.dlpack.from_dlpack(to_dlpack(actions_torch.float()))
        else:
            actions_jax = actions_torch

        # 2. 环境步进
        self.rng, step_rng = jax.random.split(self.rng)
        step_rngs = jax.random.split(step_rng, self.num_envs)
        
        self.state, reward, done, _ = self._step_fn(self.state, actions_jax, step_rngs)
        
        # 3. 自动 Reset 完成的环境
        # JAX 环境通常不会自动 reset，我们需要在这里手动 mask 或者 autoreset
        # 标准做法：env 永远不结束，但提供 done 信号。
        # 如果需要 autoreset，需要在此处加入逻辑：
        # next_state = jnp.where(done, reset_state, next_state)
        # 为保持简单，这里假设算法会处理 done，或者你可以手动添加 autoreset 逻辑。
        # (大多数 Brax/JAX RL 库会自动处理 AutoReset，如果你在外面写 Loop，可能需要加)
        
        # 简单的 Auto-Reset 逻辑:
        self.rng, reset_key = jax.random.split(self.rng)
        reset_keys = jax.random.split(reset_key, self.num_envs)
        fresh_state = self._reset_fn(reset_keys, reset_keys)
        
        # 使用 jnp.where 选择：如果 done 为 True，使用新状态，否则使用旧状态
        # 这一步很关键：JAX 必须保持形状一致
        # 我们需要展开 done 的维度以匹配状态结构 (Tree map)
        
        def where_tree(cond, t1, t2):
            return jax.tree_util.tree_map(lambda x, y: jnp.where(cond[..., None] if x.ndim > 1 else cond, x, y), t1, t2)
            
        self.state = where_tree(done, fresh_state, self.state)
        
        # 3. JAX -> PyTorch
        obs = self._jax_to_torch(self.state.obs_vec)
        rew = self._jax_to_torch(reward)
        don = self._jax_to_torch(done)
        
        return obs, rew, don, {}

    def _jax_to_torch(self, jax_tensor):
        return from_dlpack(jax.dlpack.to_dlpack(jax_tensor)).to(self.device)
