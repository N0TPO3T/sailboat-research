"""
5-run evaluator for SAC on sailboat-s14-nowind.
"""

import os

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from SAC_fc import SAC_fc_continuous
from noise_utils_nowind import NoiseManager
from test_5runs_common import EvalConfig, main
from utils_fc import Action_adapter, str2bool


CONFIG = EvalConfig(
    description="SAC sailboat-s14-nowind 5-run evaluation",
    algo_type="fc",
    agent_cls=SAC_fc_continuous,
    action_adapter=Action_adapter,
    str2bool=str2bool,
    noise_manager_cls=NoiseManager,
    default_model_prefix="sac_s14nowind_buf1e6_seed100",
    default_env_name="sailboat-s14-nowind",
    default_net_width=1024,
    output_root_name="test_results_sac_s14_nowind_5runs",
    plot_label="SAC nowind",
)


if __name__ == "__main__":
    main(CONFIG)
