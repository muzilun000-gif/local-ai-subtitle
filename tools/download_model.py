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


def main(size: str = "small") -> None:
    root = Path(__file__).resolve().parent.parent / "data" / "models"
    target = root / f"models--Systran--faster-whisper-{size}"
    target.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    print(f"正在下载 Systran/faster-whisper-{size} -> {target}")
    snapshot_download(
        f"Systran/faster-whisper-{size}",
        local_dir=str(target),
    )
    if not (target / "model.bin").exists():
        print("警告: 未找到 model.bin，请检查网络后重试")
        sys.exit(1)
    print("完成。现在可以离线使用了。")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "small")
