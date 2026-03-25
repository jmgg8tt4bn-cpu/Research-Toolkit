# 🩺 VaspDoctor: A Lightweight VASP Diagnostic Tool

**VaspDoctor** is a simple Python script (requiring only `numpy` and `matplotlib`) designed to monitor, diagnose, and visualize VASP structural optimizations in seconds.

## ✨ Key Features
*   📊 **One-Click Plotting**: Auto-generates 6 high-quality trend plots (Energy, Max Force, Drift, SCF steps, etc.) directly from `OUTCAR` and `OSZICAR`.
*   🕵️ **Smart Diagnostics**: Pinpoints the exact "bottleneck atoms" that are preventing force convergence, helping you fix bad initial structures.
*   💾 **Structure Extraction**: Automatically saves the latest atomic coordinates as `POSCAR_latest.vasp` for quick and easy job restarts.
*   🚀 **Zero Configuration**: Plug-and-play in any standard VASP calculation directory without heavy libraries like Pymatgen.
# 🩺 VaspDoctor：VASP 结构优化诊断与可视化分析工具使用说明书

## 1. 脚本简介

`VaspDoctor` 是一个轻量级、无需庞大第三方库（如 Pymatgen/ASE，仅需基础的 numpy 和 matplotlib）的 VASP 后处理 Python 脚本。
它专门用于监控、诊断和可视化 VASP 结构优化（离子步弛豫）过程。

**核心功能：**
1. **数据提取**：自动从 `OUTCAR` 和 `OSZICAR` 中提取每一步的能量、最大力、总体漂移 (Drift)、压力和电子步数 (NELM)。
2. **收敛诊断 (独家特色)**：找出整个优化过程中**最难收敛的“钉子户”原子**（打印出具体是几号原子、什么元素、以及它成为瓶颈的次数），帮你快速定位结构不合理的地方。
3. **一键绘图**：自动生成 6 张高清趋势图，直观展示各项参数的收敛轨迹。
4. **提取最新结构**：将最后一步的原子坐标提取并保存为 `POSCAR_latest.vasp`，方便由于超时断电中断的任务随时续算。

---

## 2. 运行环境与依赖准备

在运行本脚本前，请确保您的环境中安装了 Python 3，以及两个最基础的科学计算库。
如果在超算上没有这两个库，可以使用以下命令安装（通常安装在用户目录下）：
```bash
pip install numpy matplotlib --user
```

---

## 3. 如何使用 (运行方式)

将脚本保存为 `vasp_doctor.py`，然后将其放在 VASP 计算的目录下（即包含 `OUTCAR`, `OSZICAR`, `POSCAR` 的文件夹）。

### 方式一：默认运行（推荐）
直接在终端输入：
```bash
python vasp_doctor.py
```
*脚本会自动读取当前目录下的默认文件：`OUTCAR`、`OSZICAR` 和 `POSCAR`。*

### 方式二：指定文件运行（适用于文件改名或对比分析）
如果您将文件重命名了（例如保存了以前的日志），可以按以下顺序依次传入参数：
```bash
python vasp_doctor.py [OUTCAR路径][OSZICAR路径] [POSCAR路径]
```
*示例*：
```bash
python vasp_doctor.py OUTCAR_step1 OSZICAR_step1 POSCAR_initial
```

---

## 4. 核心参数修改指南 (脚本头部)

如果您想在生成的图片上画出“收敛标准参考线”，或者更改诊断的容忍度，请使用文本编辑器（如 `vim`）打开脚本，修改**最上方**的这几行代码：

```python
# ======================== 可修改参数 ========================
F_MAX_CONVERGENCE = 0.02    # 最大力收敛阈值 (eV/Å)，对应 INCAR 中的 EDIFFG (正值)
DRIFT_CONVERGENCE = 0.005   # 总漂移收敛阈值 (eV/Å)
ENERGY_CONVERGENCE = None    # 能量阈值，填具体数字（如 -500.5）则会在图上画红线
PRESSURE_CONVERGENCE = None  # 压力阈值，填具体数字（如 0.0）则会在图上画线
NELM_CONVERGENCE = None      # SCF步阈值，填具体数字（如 60）则会在图上画线
# ============================================================
```
*(注：填 `None` 表示不在图上绘制该项的参考线。)*

---

## 5. 产出文件说明

运行结束后，除了在终端输出诊断报告外，当前目录下会生成以下文件：

### 📈 可视化图表 (6张 PNG)
1. `plot_summary.png`：**六合一总览图**（包含能量、力、Drift、压力、电子步及最后一步的具体数值总结），最适合直接贴到汇报 PPT 中。
2. `plot_energy.png`：总能量随离子步的演化曲线。
3. `plot_force.png`：最大力 (Max Force) 的对数演化曲线。
4. `plot_drift.png`：晶格总漂移 (Total Drift) 趋势图。
5. `plot_nelm.png`：每个离子步对应的电子步 (SCF) 柱状图（如果柱子经常顶到 60，说明电子步极难收敛）。
6. `plot_pressure.png`：外部压力 (External Pressure) 趋势图（主要针对 ISIF=3 的变晶格优化）。

### 🧱 结构文件 (1个 VASP)
* `POSCAR_latest.vasp`：提取自 `OUTCAR` 最后一步的坐标。
  *(⚠️ 提示：该文件输出的坐标为 **笛卡尔坐标 (Cartesian)**，您可以直接将其重命名为 `POSCAR` 用于后续续算，VASP 可完美识别。)*

---

## 6. 常见使用场景与排错 (Tips)

1. **“力极大 (>1.0) 且降不下来”**
   * **表现**：看脚本终端打印的“最常成为瓶颈的原子”。
   * **对策**：通常是建模时两个原子放得太近（重叠），或者插入的缺陷距离原胞原子太近。请用 VESTA 打开 `POSCAR_latest.vasp`，重点检查被脚本点名的那几个原子。
2. **“Drift 偏高”**
   * **对策**：说明计算精度的设置偏低或者 K 点不足，尝试提高 `ENCUT` 或 `PREC=Accurate`，或者添加 `ADDGRID=.TRUE.`。
3. **“电子步画图失败”**
   * **表现**：报错提示找不到 OSZICAR。
   * **对策**：如果您在提任务时把标准输出重定向到了 `slurm-xxx.out`（例如 `mpirun vasp_std > OSZICAR` 没有写对），请手动将包含 `DAV:` 等字眼的文件重命名为 `OSZICAR`，或通过命令行参数指定该文件。