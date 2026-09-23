"""运行时资源定位：源码开发模式与 PyInstaller 打包模式统一处理。

PyInstaller onedir 布局:
    dist/一键字幕/
    ├── 一键字幕.exe
    ├── _internal/          <- sys._MEIPASS 指向这里
    ├── frontend/           <- 静态前端(随包分发)
    ├── data/models/        <- whisper 模型(随包分发)
    └── ffmpeg/bin/         <- ffmpeg/ffprobe(随包分发)
"""
import sys
from pathlib import Path


def app_root() -> Path:
    """返回应用根目录。
    - 源码模式: 项目根(backend/ 的父目录)
    - PyInstaller onedir: exe 所在目录(_internal 的父目录)
    """
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).parent
    return Path(__file__).resolve().parent.parent


def ffmpeg_dir() -> Path:
    return app_root() / "ffmpeg" / "bin"


def tool_exe(name: str) -> str:
    """定位 ffmpeg/ffprobe: 优先程序自带的可执行文件, 退回系统 PATH。"""
    exe = ffmpeg_dir() / f"{name}.exe"
    if exe.exists():
        return str(exe)
    return name


def is_bundled() -> bool:
    return getattr(sys, "_MEIPASS", None) is not None
