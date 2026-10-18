# SimWhy：低门槛工程仿真与物理解释

**没风洞、没实验设备、没昂贵许可证，也可以从可验证的物理假设开始。**

[English README](README.md) · [开源项目索引](catalog/README.md) · [模型局限](docs/assumptions.md)

本仓库不是“万物 AI 一键逆向”的宣传项目。我们把公开的技术现象转化为**可证伪的假设**，用真实数学模型计算，公开每项输入、结果、数值测试和模型缺陷。

### 第一个已运行的实验

公开演示表明，2026 年 10 月 Tesla Roadster 原型车完成过冷气体辅助的短时离地动作。但推进系统的内部参数未公开。本仓库的示例是在**假设参数**下模拟理想高压气体脉冲能否推动类似车辆质量的物体离地，**不是破解 Tesla 的内部设计，也不代表已验证现实可行性**。

只需要 Python 3.10+，无需安装额外包：

```powershell
python -m unittest discover -s tests -v
python -m simwhy run examples/pressurized_jump.json --out results/pulse
python -m simwhy run examples/insufficient_thrust.json --out results/no-lift
```

浏览器打开生成的 `trajectory.svg`，在 `trajectory.csv` 查看每一步的运动、压强、质量流量，在 `summary.json` 查看气体消耗、时间步长敏感性和明确的“未经实物验证”标签。

当前假设参数算得峰值约 **4.12 m**；另一组低推力参数为 **0 m**。它们都是**理想模型结果**，不能用于现实汽车、压力容器或安全决策。高压实际气体、气罐质量、阀门、地面效应、姿态回正和车体强度尚未建模。

### 研究范围

- **目前有**：真实可运行的气体喷流/一维运动模型、两组不同结果、单元与约束测试、SVG 图、CSV/JSON 数据。
- **目前没有**：通用 AI 科学家、Tesla 真实结构模型、六自由度回正控制、风洞级验证或 MATLAB/Fluent 自动连接。
- **下一步候选**：真实气体误差与不确定性、姿态控制模型、火箭回收简化动力学、公开发动机与翼型算例、论文到可执行实验的复现流程。

GitHub 的重点是发布别人**能够运行和质疑**的代码，而不是 AI 生成的空报告。欢迎通过 Issues 提供现象、证据、参数来源和独立校验。**不会未经授权发布师兄的 Simulink 模型、商业 Fluent 文件或受限论文。**

维护者：Heng Yuhang；MIT 开源。
