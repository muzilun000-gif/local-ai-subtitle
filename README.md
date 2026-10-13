# 声序 · 本地 AI 字幕工作台

**[Download ZIP / 下载源码包](https://github.com/muzilun000-gif/local-ai-subtitle/archive/refs/heads/main.zip)** · [English guide](README.en.md) · [原创测试视频](docs/demo-input.mp4) · [实际导出的 SRT](docs/demo-output.srt)

导入视频或音频 → 本机 Whisper 识别 → 修改文字、拆分合并、调整时间 → 导出 SRT/TXT。适合需要本地处理、再把字幕带入剪辑软件的人。

![实际识别与校对界面](docs/screenshot.png)

视频在本机处理，无账号、无遥测。首次安装需要联网下载依赖和模型；模型准备好后识别可以离线使用。识别准确率和耗时取决于音频、模型和硬件，结果仍需校对。

## Windows / Mac 安装

这是**源码启动包**，先安装 Python，再由脚本配置环境；当前没有免安装 EXE/DMG。

1. 安装 **Python 3.11 或 3.12**（支持范围3.10–3.13），下载 ZIP 后完整解压到一个可写文件夹。
2. Windows 双击 `start.bat`；Mac 运行 `start-mac.command`。
3. 首次脚本会创建本项目的 `.venv`、安装依赖、下载默认 small 模型（约484MB）。FFmpeg 由依赖包提供，无需另配 PATH。
4. 就绪后自动打开 `http://127.0.0.1:8090`。导入本包测试视频试用；结束时在终端按 Ctrl+C 停止服务。

Mac 如果文件没有执行权限，在解压后的文件夹运行 `chmod +x start-mac.command`。也可用下面的直接启动方式：

```sh
# macOS
python3 tools/launch.py
```

```bat
:: Windows（已安装 Python 3.12 时）
py -3.12 tools\launch.py
```

较小模型和其他端口：`python tools/launch.py --model base --port 8091`（Mac 用 python3）。模型下载中断可重跑启动器；下载完成前不可断网。国内网络不通时可以显式设置 `HF_ENDPOINT=https://hf-mirror.com` 使用第三方镜像，也可以保留默认官方源。镜像并非本项目运营，请自行选择。

## 真实演示材料

`docs/demo-input.mp4` 是原创合成语音测试片段；`docs/demo-output.srt` 是通过本工具识别后，人工修改标点并由界面实际下载的字幕。截图来自同一流程，没有用静态假数据伪装识别成功。

**本轮验证：Mac / Apple Silicon / Python 3.13，完成导入、本地识别、校对及 SRT/TXT 导出。Windows 测试配置已提供，云端尚未运行，不把它写成已通过。**

## 功能与边界

- faster-whisper 本地识别，支持选择中文/英文或自动检测语言。
- 逐句改字、按光标拆分、勾选合并、调整单句或整片时间。
- 视频预览与字幕高亮；导出 UTF-8 BOM 的 SRT 和纯文本。
- 草稿存在当前浏览器本地，仍应导出并备份重要字幕。
- Mac 使用 CPU int8；Windows 无 CUDA 也可走 CPU，GPU 加速是可选项。
- 这是开源基础版；项目管理、双语字幕、质量中心等完整版功能没有包含在此源码包。

导出的 SRT 可导入支持 SRT 的剪辑软件。本轮未对每一款剪辑软件和版本做导入验收。

## 排错

| 情况 | 处理 |
| --- | --- |
| 缺少正确的 Python | 安装3.11/3.12，重开终端；Mac 自带旧 Python 可能不适用 |
| 安装或模型下载失败 | 保留终端错误；检查联网，重跑启动器，不需要删除原视频 |
| 端口被其他程序占用 | 使用 `--port 8091`，启动器不会把其他服务当成自己的页面 |
| FFmpeg 未找到 | 用启动器重新完成依赖安装；直接运行后端时也需安装 requirements.txt |
| 上传后识别失败 | 检查素材是否有音轨、模型是否完整；本包限制 PyAV<19 避免已复现的兼容问题 |
| 下载后移动整个文件夹 | `.venv` 不可跨机器搬运；在新位置删除仅运行环境 `.venv` 后重建，保留 data 和原文件 |

## 开发和自检

```sh
python tools/launch.py --setup-only --model tiny
# macOS
.venv/bin/python tools/smoke.py
```

Windows 最后一行改为 `.venv\Scripts\python tools\smoke.py`。测试实际上传演示视频、识别并校对、检查 SRT/TXT，不仅检查页面能否打开。开发运行请使用自己选择的模型；small 更适合中文，tiny 仅用于轻量流程检查。

## 许可与隐私

[MIT License](LICENSE) · [第三方许可](THIRD_PARTY_NOTICES.md) · [隐私说明](PRIVACY.md)。服务默认仅监听本机；需要局域网时才显式开启 ALLOW_LAN，谨慎分享访问范围。
