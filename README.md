# Sailboat research

本机维护代码与 Git，Ubuntu 主服务器运行实验。研究事实与当前目标分别见 `PROJECT_STATE.md`、`CURRENT_PLAN.md`；操作边界见 `AGENTS.md`。

## 四条研究线

| 分支 | 内容 |
| --- | --- |
| [`main`](https://github.com/N0TPO3T/sailboat-research/tree/main) | 师兄 Sailboat 原历史基线 |
| [`idea/A`](https://github.com/N0TPO3T/sailboat-research/tree/idea/A) | 想法 A：导航路由 |
| [`idea/B`](https://github.com/N0TPO3T/sailboat-research/tree/idea/B) | 想法 B：低速迎风恢复 |
| [`idea/yara`](https://github.com/N0TPO3T/sailboat-research/tree/idea/yara) | 18D → Yara 迁移 |

各方向独立使用分支或 worktree，不混合研究结论。模型、日志与结果继续使用已有 Release；A、B、Yara 的索引见对应分支 `migration/ASSETS.json`。

旧非主线分支已转为 `history/20261108/<原分支名>` 标签，保留来源历史；不再作为日常开发分支。本次仅整理分支、导航和索引，不改动基线实现，不运行实验。

## 代码来源与目录

| 路径 | 来源与职责 |
| --- | --- |
| `sailboat_RL/` | 主仓库直接跟踪的原版参考目录，677 个文件来自提交 `19422525cb337831ca68f53a45661d34f3683ee1`，逐字节保留；不是子模块或第二个工作仓库 |
| `engineering/sailboat_rl/` | 海南工程分支 `143a508c422f746adb7af3577818060053f2620b` 的第四章环境、SAC/SAC-LSTM、续训与评估实现 |
| `engineering/tests/` | 海南工程回归测试；参考环境路径指向同仓库的 `sailboat_RL/` |
| `research/` | 主服务器保存的第五章静态基线恢复、诊断与独立研究工具 |
| `configs/`、`docs/` | 主服务器对应配置与研究说明；历史文档中的旧状态不覆盖根目录当前事实 |
| `model/` | 原研究仓库已跟踪的三套第四章参考检查点 |

`engineering/` 是独立源码根。Windows 默认不区分大小写，不能把 `sailboat_rl/` 和 `sailboat_RL/` 同时放在根目录。参考实现和工程实现职责不同，不能只因名称相似就相互覆盖或删除。

保留的原始海南历史位于标签 `history/20261108/archive/hainan-learner-sync-v2`；另一个恢复出的历史提交位于标签 `history/20261108/archive/hainan-recovered-extra`。主仓库历史保留研究与海南工程两条来源。旧 `N0TPO3T/sailboat_RL` 仓库仅归档留证，不再用于开发或克隆依赖；原始服务器资料与资产保存在来源清单和 GitHub Release 中。

## 克隆与日常 Git

```bash
git clone https://github.com/N0TPO3T/sailboat-research.git
```

原版基线入口是本仓库的 `main`；A、B、Yara 分别在上方表格列出的分支中维护。一次普通克隆即可得到完整源码，不需要 `--recurse-submodules`、`git submodule update` 或旧仓库的访问权限。本仓库是私有仓库，需要 GitHub 认证；不要将令牌写进远程 URL、脚本或仓库文件。

已有工作区先检查本地修改；工作区干净时才执行：

```bash
git pull --ff-only
```

新修改使用工作分支、显式选择提交路径；不强推，不对来源副本执行 `reset --hard` 或 `clean`。不要同时在两台机器修改同一工作分支。

## 本地与服务器

- Windows 正式目录：`C:\Users\74095\hs\SailBoat\sailboat-research`。
- 主服务器工作范围：`ot@172.16.2.249:/home/ot/Students/hs`。
- 主服务器既有项目是部署副本，不是 Git 克隆。同步前比较改动；不可用本地旧版本覆盖未归档的服务器工作。
- 海南下载目录与 `source-backups/` 是来源备份，不是正式开发入口。
- 服务器的 `.venv`、系统依赖、缓存与 GPU 状态不随 Git 同步；Linux 虚拟环境不能复制到 Windows 使用。
- 所有主服务器写入只能在真实路径 `/home/ot/Students/hs/` 内；不修改共享 base、其他学生目录或系统配置。

## 有界 CPU 验证

在独立验证副本中使用已有兼容环境，禁用 GPU、限制 CPU 线程。以下命令不进行训练，输出不得覆盖已有实验：

```bash
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/engineering"
python -B research/smoke_baseline.py --steps 50 --output research/outputs/reference_smoke.json
python -B -m sailboat_rl.evaluation.batch_eval \
  --dvc cpu --model_dir "$PWD/model" \
  --models saclstm_nowind_seed100,sac_nowind_seed100,sac_wind_seed100 \
  --random_episodes 1 --fixed_episodes 0 --max_steps 5 --num_workers 1 \
  --output_dir "$PWD/research/outputs/engine_smoke"
python -B -m unittest discover -s engineering/tests -p 'test_*.py'
```

依赖包括 PyTorch、NumPy、SciPy、Gymnasium、Pandas、Matplotlib、Pygame、stable-baselines3 和 tqdm；原环境版本与运行证据见来源清单及 `PROJECT_STATE.md`。`sailboat_RL/requirements.txt` 是原版记录，不代表已经验证过的跨平台锁文件。

第五章研究工具仍显式复用同仓库中的原版参考目录，不自动替换为海南工程实现。部分第五章工具有 Linux/hs 路径约束；本机负责编辑与版本管理，完整运行验证放主服务器的独立目录。

训练、续训、正式评估、资源调度与检查点选择必须依据当前计划单独执行；本次版本整理不代表训练获准，也不代表旧检查点通过论文复现。

## 大文件与证据

模型库、完整训练 checkpoint、输出与原始备份不直接加入普通 Git。代码、配置、来源清单和必要的小型验证收据由 Git 跟踪；完整源资料归档作为同一私有仓库的 Release 附件保存，下载后先核对 SHA256，再按原路径恢复。历史模型的文件名、能加载或一次有限前向都不证明训练身份、语义兼容或策略性能。

归档按 4 MiB 分卷上传，避免当前网络的大文件上传中断。使用已认证的 GitHub CLI 下载到**新目录**（`GH_TOKEN` 可由环境提供）：

```bash
gh release download consolidated-20261001 --repo N0TPO3T/sailboat-research --pattern "primary-project-complete.tar.gz.part*" --dir restored-assets
```

下载模式同时包含 `.parts.json` 清单和 `.part000` 等分卷。在 `restored-assets` 内用 Python 3.11+ 按清单顺序拼接并核对每卷与整体哈希：

```python
import hashlib, json
from pathlib import Path

manifest = json.loads(Path("primary-project-complete.tar.gz.parts.json").read_text())
with Path(manifest["archive"]).open("xb") as output:
    for part in manifest["parts"]:
        data = Path(part["name"]).read_bytes()
        assert len(data) == part["bytes"]
        assert hashlib.sha256(data).hexdigest() == part["sha256"]
        output.write(data)
with Path(manifest["archive"]).open("rb") as archive:
    assert hashlib.file_digest(archive, "sha256").hexdigest() == manifest["sha256"]
```

整体 SHA256 还必须与 Git 中 `research/validation/consolidation_20261001.json` 核对。然后解压到新的来源目录，不直接覆盖正式工作区。归档根目录中的 `sailboat-research/` 是主服务器原样快照，不含后来整合的 `engineering/`；最终代码应始终从唯一主仓库的 `main` 克隆。只需要原始代码与文字证据时，可改下载 `primary-source.tar.gz.part*` 并使用对应清单。
