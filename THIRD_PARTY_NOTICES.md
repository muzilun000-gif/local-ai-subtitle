# 第三方组件与许可证声明

本项目（一键字幕开源版）以 **MIT License** 发布，许可证全文见根目录 [LICENSE](LICENSE)。
本软件在运行时使用以下第三方组件；各组件版权归其各自权利人所有。

## 随本仓库分发的组件

| 组件 | 用途 | 许可证 | 来源 |
|---|---|---|---|
| Source Han Sans SC（思源黑体）Regular/Bold | 界面与字幕预览字体 | SIL OFL 1.1（含 Reserved Font Name 'Source'） | Adobe / Google，许可证副本见 `frontend/fonts/OFL.txt` |

## 通过 pip 安装的 Python 依赖

| 组件 | 用途 | 许可证 |
|---|---|---|
| faster-whisper | 语音识别封装（含 Silero VAD 模型，MIT） | MIT |
| CTranslate2 | 高性能推理引擎 | MIT |
| onnxruntime | VAD 静音过滤推理 | MIT |
| Silero VAD（随 faster-whisper 分发） | 语音活动检测模型 | MIT |
| PyAV（av） | 音视频解码 | BSD-3-Clause |
| tokenizers | 分词器 | Apache-2.0 |
| huggingface_hub | 模型下载/引用 | Apache-2.0 |
| FastAPI | Web 服务框架 | MIT |
| Uvicorn | ASGI 服务器 | BSD-3-Clause |
| Starlette | FastAPI 底层框架 | BSD-3-Clause |
| Pydantic | 数据校验 | MIT |
| python-multipart | 表单/文件上传 | Apache-2.0 |
| NumPy | 数值计算 | BSD-3-Clause |

## 语音识别模型

- 默认使用 `Systran/faster-whisper-small` 模型权重，由 OpenAI Whisper（MIT）模型转换而来，
  模型卡与许可见 https://huggingface.co/Systran/faster-whisper-small 。
- 模型不随本仓库分发，需在安装后通过 `tools/download_model.py` 自行下载（仅此一步需要联网）。

## 外部程序（需用户自行安装，不随本仓库分发）

- **FFmpeg / FFprobe**：音频提取所必需。FFmpeg 是自由软件，官方版本依据编译选项分别以
  LGPL 2.1+ 或 GPL 2+/GPL3 发布，下载与源码见 https://ffmpeg.org 。
  本软件以独立进程方式调用系统已安装的 ffmpeg，不包含、不链接其二进制文件。
  请按你所下载的 FFmpeg 构建版本遵守对应许可证。

## 测试工具（可选，普通用户无需安装）

- edge-tts：生成测试语音，GPL-3.0；仅用于 `tests/` 与 `requirements-dev.txt`，不参与运行时。

## 说明

- 本项目不附 PyInstaller 打包产物；如需免安装 Windows 完整版（内置模型/FFmpeg、批量处理、
  AI 口语清理、ASS、卡拉OK逐字样式、烧录 MP4、模板等），请联系作者获取。
- 如发现本声明有遗漏或不准确之处，欢迎提 issue，我们会及时更正。
