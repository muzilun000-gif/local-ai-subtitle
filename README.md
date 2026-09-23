# 一键字幕（开源版）· 本地离线 AI 字幕工具

导入视频 → **本地 Whisper 语音识别**（带毫秒级时间轴）→ 校对改字 → **一键导出 SRT**，
可直接导入 **DaVinci Resolve（达芬奇）/ 剪映 / Adobe Premiere**。

**视频全程本地处理，不上传任何云端；模型下载完成后可断网运行。**

## 功能（开源基础版）

- 本地 faster-whisper 语音识别，自动检测语言（支持中文 / 英文），带时间轴
- 字幕校对：点击改字、按光标位置拆分、勾选合并、逐句平移 / 调时长、整片整体偏移
- 视频预览，播放时字幕逐句高亮叠加，点击时间跳转
- 导出 **SRT（UTF-8 with BOM，DaVinci / 剪映 / Premiere 可直接导入）** 与纯文本 TXT
- 校对草稿自动保存，误关页面可恢复

> 需要 **免安装 Windows 完整版**（内置模型与 FFmpeg、批量处理、AI 口语清理、ASS 字幕、
> 卡拉OK逐字样式、直接烧录 MP4、样式模板等）请联系作者。

## 环境要求

- Windows 10/11（Linux / macOS 同样可运行，见文末）
- Python 3.10 及以上
- **FFmpeg** 已安装并加入 PATH（音频提取必需）
- 内存 8GB 及以上；无需独立显卡（有 N 卡可装可选 GPU 依赖加速）

## 安装与运行（Windows）

```bat
:: 1. 获取代码
git clone https://github.com/muzilun000-gif/local-ai-subtitle.git
cd local-ai-subtitle

:: 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

:: 3. 下载识别模型（仅此一步需要联网，small 约 484MB）
python tools\download_model.py small

:: 4. 启动
python backend\main.py
```

浏览器自动/手动打开 http://127.0.0.1:8081 即可使用。
也可双击项目根目录的 `start.bat`（需已完成上面的依赖安装与模型下载）。

> 国内网络下载模型慢，可先执行 `set HF_ENDPOINT=https://hf-mirror.com` 再运行下载脚本。

### 可选：GPU 加速

有 NVIDIA 显卡时额外安装：`pip install -r backend\requirements-gpu.txt`，
程序会自动尝试 CUDA，失败自动回退 CPU。

## 导出后如何使用

- **DaVinci Resolve**：媒体池右键 → 导入字幕（Import Subtitle）→ 选择 SRT，拖到时间线即可
- **剪映**：导入 SRT 文件，或在文本面板选择「本地字幕 → 导入」
- **Premiere**：项目面板导入 SRT，拖入序列即生成字幕轨

## Linux / macOS

使用系统包管理器安装 FFmpeg（如 `sudo apt install ffmpeg` / `brew install ffmpeg`），
其余步骤相同（命令中的路径分隔符改为 `/`）。

## 安全与隐私

见 [PRIVACY.md](PRIVACY.md)：无账号、无遥测、默认仅本机可访问；
需要局域网访问时显式设置 `ALLOW_LAN=1`。

## 许可证

本项目以 [MIT License](LICENSE) 发布；第三方组件许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
