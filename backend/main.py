"""
一键字幕（开源基础版）- 本地离线 AI 字幕工具后端

导入视频 -> ffmpeg 提取音频 -> faster-whisper 本地识别(带时间轴)
-> 前端校对编辑 -> 导出 SRT / 纯文本。

全程本地处理，默认只监听 127.0.0.1；设置 ALLOW_LAN=1 才允许局域网访问。
"""
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from transcribe import transcribe_audio, get_model_info
from _bundle import app_root, is_bundled, tool_exe

BASE_DIR = app_root()
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
AUDIO_DIR = BASE_DIR / "data" / "audio"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"
FRONTEND_DIR = BASE_DIR / "frontend"

for d in (UPLOAD_DIR, AUDIO_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# 打包后为无窗口程序: stdout/stderr 落盘便于排查问题
if is_bundled():
    try:
        (BASE_DIR / "data" / "logs").mkdir(parents=True, exist_ok=True)
        _log_f = open(BASE_DIR / "data" / "logs" / "server.log", "a", encoding="utf-8")
        sys.stdout = _log_f
        sys.stderr = _log_f
    except Exception:
        pass

app = FastAPI(title="一键字幕（开源版）API")
app.add_middleware(
    CORSMiddleware,
    # Origin 必须带 scheme, 写成 "127.0.0.1" 是匹配不上的; 端口可能自定义, 故用正则
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


class Segment(BaseModel):
    start: float
    end: float
    text: str


class ExportRequest(BaseModel):
    segments: list[Segment]
    format: str = "srt"  # srt | txt


class MediaInputError(Exception):
    """上传的文件本身有问题(损坏/空文件/无音频流)。

    属于用户输入错误 -> 返回 400 + 可读中文提示,
    而不是把 ffmpeg 的裸 stderr 抛给用户(小白看不懂,还容易误以为是软件坏了)。
    """


class ToolMissingError(Exception):
    """运行环境缺少必需的外部程序(FFmpeg) -> 返回 500 + 可操作的中文提示。"""


# ffmpeg 常见报错 -> 用户能看懂的中文提示(按下标顺序匹配,越具体越靠前)
_FFMPEG_HINTS = (
    ("moov atom not found", "文件损坏或上传不完整,请重新上传该文件"),
    ("invalid data found when processing input", "这不是有效的音视频文件,或文件已损坏"),
    ("does not contain any stream", "该文件不含音频轨道,无法识别字幕"),
    ("permission denied", "文件被其他程序占用,请关闭后重试"),
    ("no such file or directory", "文件不存在或已被移动"),
    ("error opening input", "无法打开该文件,可能已损坏"),
)


def _ffmpeg_friendly(stderr: str) -> str:
    """把 ffmpeg 的英文报错归类成一句中文提示。"""
    low = (stderr or "").lower()
    for needle, msg in _FFMPEG_HINTS:
        if needle in low:
            return msg
    return "无法从该文件提取音频,可能是文件损坏或格式不受支持"


def _ffmpeg_exe() -> str:
    """定位 ffmpeg: 优先程序自带的可执行文件, 其次系统 PATH。

    都找不到时给出可操作提示 —— 否则 subprocess 会抛
    FileNotFoundError, 用户只会看到 "[WinError 2] 系统找不到指定的文件"。
    """
    exe = tool_exe("ffmpeg")
    if os.path.isabs(exe) or shutil.which(exe):
        return exe
    raise ToolMissingError(
        "未找到 FFmpeg, 本工具需要它来提取音频。\n"
        "请先安装并加入系统 PATH, 然后重启本程序:\n"
        "  · Windows: 执行  winget install Gyan.FFmpeg  或从 ffmpeg.org 下载后把 bin 目录加入 PATH\n"
        "  · macOS:   brew install ffmpeg\n"
        "  · Linux:   sudo apt install ffmpeg"
    )


def _remove_quietly(*paths: Path) -> None:
    """失败时清掉半成品文件, 避免 data/ 目录里堆积垃圾。"""
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


def extract_audio(video_path: Path, audio_path: Path) -> None:
    """用 ffmpeg 把视频音频提取为 16kHz 单声道 wav。"""
    cmd = [
        _ffmpeg_exe(), "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        # 原始 stderr 只写进日志方便排障; 给用户的是友好提示
        print(f"[extract_audio] ffmpeg 退出码 {result.returncode}: {result.stderr[-800:]}", flush=True)
        raise MediaInputError(_ffmpeg_friendly(result.stderr))


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...), language: str = Form("auto")):
    """接收视频/音频，提取并本地识别。language: auto|zh|en..."""
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv", ".wmv", ".mp3", ".wav", ".m4a"}:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    job_id = uuid.uuid4().hex[:12]
    video_path = UPLOAD_DIR / f"{job_id}{ext}"
    audio_path = AUDIO_DIR / f"{job_id}.wav"

    lang = None if language in ("auto", "", "None") else language
    try:
        with open(video_path, "wb") as f:
            await run_in_threadpool(shutil.copyfileobj, file.file, f)

        # 空文件/被截断的上传: 早报错, 不要白跑一遍 ffmpeg 和模型
        if video_path.stat().st_size < 1024:
            raise MediaInputError("文件内容为空或上传不完整,请重新上传该文件")

        await run_in_threadpool(extract_audio, video_path, audio_path)
        result = await run_in_threadpool(transcribe_audio, audio_path, lang)
    except MediaInputError as e:
        import traceback
        traceback.print_exc()
        _remove_quietly(video_path, audio_path)
        raise HTTPException(400, str(e))
    except ToolMissingError as e:
        import traceback
        traceback.print_exc()
        _remove_quietly(video_path, audio_path)
        raise HTTPException(500, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        _remove_quietly(video_path, audio_path)
        raise HTTPException(500, f"处理失败: {e}")

    return {
        "job_id": job_id,
        "language": result["language"],
        "segments": result["segments"],
        "model": get_model_info(),
    }


def _fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


@app.post("/api/export")
async def export_subtitles(req: ExportRequest):
    """把校对后的字幕导出为 SRT 或 TXT。"""
    if not req.segments:
        raise HTTPException(400, "字幕内容为空")

    job_id = uuid.uuid4().hex[:12]
    if req.format == "txt":
        out_path = OUTPUT_DIR / f"{job_id}.txt"
        content = "\n".join(seg.text.strip() for seg in req.segments if seg.text.strip())
    else:
        out_path = OUTPUT_DIR / f"{job_id}.srt"
        lines = []
        for i, seg in enumerate(req.segments, 1):
            lines.append(f"{i}")
            lines.append(f"{_fmt_srt_time(seg.start)} --> {_fmt_srt_time(seg.end)}")
            lines.append(seg.text.strip())
            lines.append("")
        content = "\n".join(lines)

    out_path.write_text(content, encoding="utf-8-sig")  # BOM: DaVinci/剪映/PR 兼容性更好
    return FileResponse(
        out_path,
        filename=f"subtitles.{req.format}",
        media_type="application/octet-stream",
    )


@app.get("/api/model")
async def model_info():
    return get_model_info()


# 静态托管前端(放到路由注册之后,避免吞掉 /api)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import threading
    import uvicorn
    # 默认仅本机可访问；显式设置 ALLOW_LAN=1 才监听 0.0.0.0 供局域网使用
    allow_lan = os.environ.get("ALLOW_LAN", "") in ("1", "true", "yes")
    host = "0.0.0.0" if allow_lan else "127.0.0.1"
    port = int(os.environ.get("PORT", 8081))
    if is_bundled():
        # 打包发布版(windowed 无控制台): 服务起来后自动打开默认浏览器
        def _open_browser():
            import time
            import webbrowser
            time.sleep(2.0)
            try:
                webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception:
                pass
        threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host=host, port=port)
