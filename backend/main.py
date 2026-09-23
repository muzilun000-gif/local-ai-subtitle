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
    allow_origins=["127.0.0.1", "localhost"],
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


def extract_audio(video_path: Path, audio_path: Path) -> None:
    """用 ffmpeg 把视频音频提取为 16kHz 单声道 wav。"""
    cmd = [
        tool_exe("ffmpeg"), "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 提取音频失败: {result.stderr[-800:]}")


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
        await run_in_threadpool(extract_audio, video_path, audio_path)
        result = await run_in_threadpool(transcribe_audio, audio_path, lang)
    except RuntimeError as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
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
