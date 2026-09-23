"""
faster-whisper 识别模块

首次运行自动从 HuggingFace 下载模型(约 75MB / small 模型),
之后完全离线运行。自动尝试 GPU,失败时回退 CPU。
"""
import os
import sys
from pathlib import Path

from _bundle import app_root

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")
MODELS_DIR = app_root() / "data" / "models"
LOCAL_MODEL_DIR = MODELS_DIR / f"models--Systran--faster-whisper-{MODEL_SIZE}"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

_model = None
_device = None


def _setup_gpu_env() -> None:
    """Windows 上 faster-whisper GPU 需要 cublas/cudnn dll,尝试从 pip 包定位。"""
    import site
    candidates = []
    for sp in site.getsitepackages():
        p = Path(sp)
        candidates += [
            p / "nvidia" / "cublas" / "bin",
            p / "nvidia" / "cudnn" / "bin",
            p / "cudnn" / "bin",
        ]
    existing = [str(c) for c in candidates if c.exists()]
    if existing:
        os.environ["PATH"] = os.pathsep.join(existing) + os.pathsep + os.environ.get("PATH", "")


def _load_model():
    global _model, _device
    if _model is not None:
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

    _setup_gpu_env()
    try:
        _model = WhisperModel(model_ref, device="cuda", compute_type="float16",
                              download_root=str(MODELS_DIR))
        _device = "cuda"
        print(f"[transcribe] Whisper '{model_ref}' loaded on GPU", flush=True)
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
