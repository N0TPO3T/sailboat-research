# Project Memory

只记录会影响未来研究决策的可靠经验，不作为实验或会话日志。

## 静态避障属于已有基础，不能当成新增贡献

**Tags:** `baseline`, `obstacle-avoidance`, `novelty`

**Conclusion** 师兄已经完成静态避障与历史注意力方法的论文论述和对照分析。

**Evidence** `sailboat_RL/docs/refs/师兄大论文.pdf` §5.2–5.3、§6.3；`PART5/`三组实现及根目录障碍环境。

**Implication** 新工作需明确超出这一基础的任务/机制/证据；不要重新以“添加静态避障/注意力”为创新点。

## 本地演示快照不能直接当论文随机评估协议

**Tags:** `evaluation`, `reproducibility`, `wind`, `seed`

**Conclusion** 这份快照的reset固定了风向与障碍布局，与论文描述的随机分布不同；裸导入和相对路径还绑定原执行环境。

**Evidence** `sailboat_RL/sailboat_s14_obst_V3.py` reset与随机场景注释，论文§5.2.2；`sailboat_RL/PART5/SAC-LSTM-att/parll_lstm_att_normal.py`的gym.make及相对model/runs路径。

**Implication** 比较前冻结并核验环境来源、场景与随机源；“恢复论文协议”作为基线修复，不冒充算法贡献。
此结论仅针对所核查快照，不推断师兄原始训练存在相同问题。
