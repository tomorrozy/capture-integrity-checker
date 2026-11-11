# CaptureIntegrityChecker

*[English](README.md) · 简体中文*

> 跑在活体检测之前的“摄像头来源体检”，专门识别那种改了设备名也能冒充物理摄像头的虚拟摄像头。

[![CI](https://github.com/tomorrozy/capture-integrity-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/tomorrozy/capture-integrity-checker/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)

> 当前 v0.1.0 开发中。L1/L2 和验证工具（采集 / 校准 / 消融）都已实现，38 个不依赖硬件的测试，CI 在 ubuntu 和 windows 上、Python 3.10 到 3.13 都过。真机只跑过一轮、范围很窄，数字见[验证](#验证真机但范围有限)；完整矩阵还没做。

---

## 问题在哪

不少开源方案判断虚拟摄像头，靠的是设备名或驱动标签，看到 “OBS Virtual Camera”“ManyCam” 就报警。可这名字太容易改。Linux 上把 v4l2loopback 的 card_label 换成 “HD Pro Webcam C920”，Windows 上改一下 DirectShow 滤镜的 FriendlyName，原来的检测基本就废，成本几乎为零。

这个项目不看名字，去戳摄像头的配置响应：让它反复切分辨率，看切换要多久、报回来的分辨率和你请求的是不是一致、塞一个 1234×567 这种非标准尺寸它接不接。软件虚拟摄像头通常切得飞快，还把你给的分辨率原样收下；物理摄像头一般慢一些，并把奇怪的分辨率悄悄钳到附近的标准值。

**定位**：纵深防御里的一层软信号。不替代活体检测，不做硬拦截，也不吹能终结注入攻击。它想做的只是让“改个名字就能过”这种近乎免费的攻击，变得没那么免费。

## 安装

Python ≥ 3.10，核心零运行时依赖；要真开摄像头探测再加 OpenCV。

```bash
pip install -e ".[dev]"      # 核心 + 测试
pip install -e ".[opencv]"   # 再加 OpenCV，用于探测真实设备
```

目前只能从源码装，PyPI 还在路线图上。

## 两分钟跑起来

```bash
python -m capture_integrity.demo --device 0
```

在拿不到任何一层数据的机器上，它会老老实实给一个中性的 0.5 和 `unavailable`，而不是假装“可信”：

```json
{
  "score": 0.5,
  "signals": {},
  "status": "unavailable",
  "evidence": {
    "descriptor": {"status": "unavailable", "reason": "platform 'win32' not supported in v0.1"},
    "config_response": {"status": "unavailable", "error": "No module named 'cv2'"}
  }
}
```

## 接口

```python
from capture_integrity import CaptureIntegrityChecker

checker = CaptureIntegrityChecker(
    layers=("descriptor", "config_response"),
    probe_budget_ms=1500,
)
result = checker.integrity_score(device="/dev/video0")  # Windows 用整数索引或路径

result.score      # 0~1，越高越可信
result.signals    # 每层可信度（1 - 可疑度）
result.status     # "ok" | "partial" | "unavailable" | "error"
result.evidence   # 原始测量，可审计
```

任何一层都拿不到读数时，`score` 为 0.5、`status` 为 `unavailable`；只有部分层可用时，权重按可用层归一化，`status` 为 `partial`。L1/L2 只读设备元数据和配置响应；L2 会为了计首帧延迟在内存里读一帧随即丢弃，**不落盘、不外传**。

## 三层信号

| 层 | 信号 | 权重 | v0.1 |
|---|---|---|---|
| L1 描述符 | Linux 读 `VIDIOC_QUERYCAP` 的 `driver` / `card` | 0.2 | 仅 Linux |
| L2 配置响应 | 重配置耗时分布、静默截断、奇数分辨率接受度 | 0.7 | 开 |
| L3 取证（规划中） | 帧抖动、缓冲区时间戳、双重 JPEG | 0.1 | 未计分 |

`score = 1 − Σ wᵢ·可疑度ᵢ`，只对返回读数的层做归一化。默认识别规则不依赖训练；ML 后端只留接口。每个分数都附带原始 `evidence` 供审计。

## 接入

它是可加、可回退的：先落地模块，再接进去。放在原有的标签检查之后、活体兜底之前，只贡献一个软信号：

```python
# examples/minimal_integration.py
def combine(existing_trust: float, integrity_score: float, weight: float = 0.3) -> float:
    return (1 - weight) * existing_trust + weight * integrity_score
```

`combine` 只是个一行的示例，不是包导出的函数，换成你自己的融合即可。`unavailable` 保持中性（0.5），所以陌生设备不会把总分往下拽，也永远不会硬拦截。

## 验证（真机，但范围有限）

目标协议是 ≥2 物理 / ≥2 虚拟 + 对抗样本的消融，报 TPR / FPR 和 BPCER @ APCER=0.1。

第一轮真机跑在 Windows + DirectShow 上，1 个内置物理摄像头对 1 个 OBS 虚拟摄像头，只测 L2（Windows 上 L1 用不了），各 10 轮。结果物理 0.00、OBS 0.40，靠的是“非标准分辨率被原样接受”：物理驱动把 1234×567 钳到 1280×720、999×999 钳到 960×540，OBS 则原样收下。计时那条在这个后端上被 DirectShow 的重协商开销盖住了，两边分别约 1.2 秒和 0.47 秒，等于没起作用。所以默认 0.5 的阈值会漏掉 OBS；按 APCER=0.1 校准到 0.4 时，APCER 和 BPCER 都是 0。

完整报告见 [docs/validation.md](docs/validation.md)，原始 CSV 在 [data/](data/)。

这不是 ≥2/≥2 的矩阵，也不是 ISO/IEC 30107-3。完整矩阵得有台 Linux（≥2 物理 + v4l2loopback + 对抗样本）才能做，步骤写在 [docs/collecting.md](docs/collecting.md)。阈值别照搬 0.5，按实际部署校准。

## 边界

- **误报**：响应很快的物理驱动或采集卡可能触发 L2，可用校准档位和可调阈值缓解；FPR 会公开。
- **仍然能被绕过**：重新编译内核模块，或者人为注入延迟。这是个基线，不是完整方案。
- **不是活体检测**：它只看采集链路，不看人脸；要继续放在活体前面，别拿它顶替。
- **v0.1 不做**：Windows/macOS 的描述符探测、HDMI 采集注入、macOS CoreMediaIO。

## 许可

[Apache-2.0](LICENSE)，主要看重它的专利授权条款；商业生物识别系统里用到时这点更省心。
