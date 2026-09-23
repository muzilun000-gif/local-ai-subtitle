"""Generate a Chinese TTS test video for end-to-end checks.

Usage: python make_test_video.py [out_dir]
Requires: edge-tts, ffmpeg on PATH.
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import edge_tts

VOICE = "zh-CN-XiaoxiaoNeural"
GAP_SECONDS = 0.6
SENTENCES = [
    "大家好,欢迎来到一键字幕工具的测试视频。",
    "今天天气非常不错,我们一起去公园散步吧。",
    "人工智能正在改变内容创作的方式。",
    "这就是AI语音识别自动生成的字幕效果,感谢观看。",
]


async def synth_all(out_dir: Path) -> list[Path]:
    clips = []
    for i, text in enumerate(SENTENCES, 1):
        clip = out_dir / f"clip_{i}.mp3"
        await edge_tts.Communicate(text, voice=VOICE).save(str(clip))
        clips.append(clip)
    return clips


def make_gap(out_dir: Path) -> Path:
    gap = out_dir / "gap.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
         "-t", str(GAP_SECONDS), "-c:a", "libmp3lame", str(gap), "-loglevel", "error"],
        check=True,
    )
    return gap


def concat(clips: list[Path], gap: Path, out_dir: Path) -> Path:
    merged = out_dir / "test_voice.mp3"
    lst = out_dir / "concat_list.txt"
    items = []
    for clip in clips:
        items.append(f"file '{clip.name}'")
        items.append(f"file '{gap.name}'")
    lst.write_text("\n".join(items), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:a", "libmp3lame", str(merged), "-loglevel", "error"],
        cwd=out_dir,
        check=True,
    )
    return merged


def make_video(audio: Path, out_dir: Path) -> Path:
    video = out_dir / "test_video.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x1e293b:s=1280x720:r=30",
         "-i", str(audio), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", str(video), "-loglevel", "error"],
        check=True,
    )
    return video


def main() -> None:
    out_dir = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    clips = asyncio.run(synth_all(out_dir))
    gap = make_gap(out_dir)
    merged = concat(clips, gap, out_dir)
    video = make_video(merged, out_dir)
    print(f"OK: {video}")


if __name__ == "__main__":
    main()
