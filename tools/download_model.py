"""
预下载 faster-whisper 识别模型到 data/models（安装后运行一次，需要联网）。

用法:
    python tools/download_model.py [模型规格]

示例:
    python tools/download_model.py small    # 默认，中文效果与体积较均衡
    python tools/download_model.py base     # 更小，约 140MB
    python tools/download_model.py medium   # 更准，约 1.5GB

下载完成后即可完全离线使用。
国内网络可设置镜像:  set HF_ENDPOINT=https://hf-mirror.com
"""
import sys
from pathlib import Path

# faster-whisper 支持的常用规格；传错名字时 HuggingFace 会 404，不如提前拦住
KNOWN_SIZES = (
    "tiny", "tiny.en", "base", "base.en", "small", "small.en",
    "medium", "medium.en", "large-v1", "large-v2", "large-v3", "large-v3-turbo",
)


def main(size: str = "small") -> None:
    if size not in KNOWN_SIZES:
        print(f"未知的模型规格: {size}")
        print("可用规格: " + ", ".join(KNOWN_SIZES))
        sys.exit(2)

    root = Path(__file__).resolve().parent.parent / "data" / "models"
    target = root / f"models--Systran--faster-whisper-{size}"
    target.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    print(f"正在下载 Systran/faster-whisper-{size} -> {target}")
    snapshot_download(
        f"Systran/faster-whisper-{size}",
        local_dir=str(target),
    )
    model_bin = target / "model.bin"
    if not model_bin.exists() or model_bin.stat().st_size == 0:
        print("警告: 未找到有效的 model.bin，请检查网络后重试")
        sys.exit(1)
    print(f"完成（model.bin {model_bin.stat().st_size / 1024 / 1024:.0f} MB）。现在可以离线使用了。")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "small")
