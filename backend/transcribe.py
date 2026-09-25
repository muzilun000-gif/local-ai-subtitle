"""
faster-whisper 识别模块

首次运行自动从 HuggingFace 下载模型(small 约 484MB),
之后完全离线运行。

设备选择:
- 源码运行: 先探测 CUDA,可用则用 GPU(float16) 并做一次试跑,任一步失败回退 CPU(int8)
- PyInstaller 打包版: 固定 CPU(int8),不依赖客户机 GPU 驱动
"""
import os
import site
import sys
import threading
from pathlib import Path

from _bundle import app_root

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")
MODELS_DIR = app_root() / "data" / "models"
LOCAL_MODEL_DIR = MODELS_DIR / f"models--Systran--faster-whisper-{MODEL_SIZE}"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

_model = None
_device = None
_model_lock = threading.Lock()      # 防止并发上传时重复加载模型
_dll_handles: list = []             # 持有 add_dll_directory 句柄, 释放会导致 CUDA 库被卸载


def _setup_gpu_env() -> None:
    """把 pip 装的 CUDA 运行库(cublas/cudnn)目录注册给 Windows 加载器。

    注意: Python 3.8+ 在 Windows 上不再用 PATH 搜索 DLL 依赖,
    必须调用 os.add_dll_directory, 否则 ctranslate2 仍会报
    "Library cublas64_12.dll is not found or cannot be loaded"。
    """
    roots = list(site.getsitepackages())
    try:
        roots.append(site.getusersitepackages())
    except Exception:
        pass

    dirs = []
    for sp in roots:
        for rel in (("nvidia", "cublas", "bin"), ("nvidia", "cudnn", "bin"), ("cudnn", "bin")):
            p = Path(sp).joinpath(*rel)
            if p.exists():
                dirs.append(p)

    for d in dirs:
        try:
            _dll_handles.append(os.add_dll_directory(str(d)))
        except Exception:
            pass
    # 部分 ctranslate2 旧版本仍走 PATH, 一并写入
    if dirs:
        os.environ["PATH"] = os.pathsep.join(str(d) for d in dirs) + os.pathsep + os.environ.get("PATH", "")


def _cuda_available() -> bool:
    """真探测: ctranslate2 能加载 CUDA 库并看到设备才算可用。"""
    try:
        import ctranslate2
        n = ctranslate2.get_cuda_device_count()
    except Exception as e:
        print(f"[transcribe] CUDA 探测失败({e}), 使用 CPU", flush=True)
        return False
    if n < 1:
        print("[transcribe] 未检测到可用的 CUDA 设备, 使用 CPU", flush=True)
        return False
    return True


def _warmup(model) -> None:
    """用 0.5 秒静音做一次极短推理, 强制触发 CUDA 库加载。

    ctranslate2 的 CUDA 库是**延迟加载**的: 构造模型时不碰 cublas/cudnn,
    直到第一次推理才去加载。所以只把 WhisperModel(...) 包在 try 里是兜不住的
    —— 必须在 try 内真正跑一次推理, 否则缺库的机器会在首次上传时才 500。
    """
    import numpy as np
    silence = np.zeros(8000, dtype="float32")   # 0.5s @ 16kHz
    list(model.transcribe(silence, beam_size=1, vad_filter=False)[0])


def _load_model():
    global _model, _device
    if _model is not None:
        return _model, _device

    with _model_lock:
        if _model is not None:          # 双检锁: 并发请求只加载一次
            return _model, _device

        from faster_whisper import WhisperModel

        # Local pre-downloaded copy -> fully offline, never touch the Hub.
        model_ref = str(LOCAL_MODEL_DIR) if (LOCAL_MODEL_DIR / "model.bin").exists() else MODEL_SIZE

        # 打包发布版: 统一 CPU(int8)。不依赖客户机 GPU 驱动/额外 dll, 保证任何机器可用
        if getattr(sys, "_MEIPASS", None):
            _model = WhisperModel(model_ref, device="cpu", compute_type="int8",
                                  download_root=str(MODELS_DIR))
            _device = "cpu"
            print("[transcribe] 打包版固定 CPU(int8)", flush=True)
            return _model, _device

        # 源码版: 探测 -> 构造 -> 试跑, 任一环节失败都回退 CPU
        if _cuda_available():
            _setup_gpu_env()
            try:
                m = WhisperModel(model_ref, device="cuda", compute_type="float16",
                                 download_root=str(MODELS_DIR))
                _warmup(m)
                _model, _device = m, "cuda"
                print(f"[transcribe] Whisper '{model_ref}' loaded on GPU (cuda/float16)", flush=True)
                return _model, _device
            except Exception as e:
                print(f"[transcribe] GPU 不可用({e}), 回退 CPU", flush=True)

        _model = WhisperModel(model_ref, device="cpu", compute_type="int8",
                              download_root=str(MODELS_DIR))
        _device = "cpu"
        print(f"[transcribe] Whisper '{model_ref}' loaded on CPU (int8)", flush=True)
        return _model, _device


def transcribe_audio(audio_path: Path, language: str | None = None) -> dict:
    """识别音频,返回带时间轴的 segments。language=None 自动检测。"""
    model, device = _load_model()
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,       # None=自动检测, 指定 'zh'/'en' 等强制语言
        beam_size=5,
        vad_filter=True,         # 过滤静音段
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments = []
    for seg in segments_iter:
        text = seg.text.strip()
        if not text:
            continue
        segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": text,
        })

    return {
        "language": info.language,
        "segments": segments,
        "device": device,
        "model_size": MODEL_SIZE,
    }


def get_model_info() -> dict:
    return {
        "model_size": MODEL_SIZE,
        "device": _device,
        "loaded": _model is not None,
    }
