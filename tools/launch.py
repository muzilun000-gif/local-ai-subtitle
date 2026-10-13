"""Portable first-run setup and launch on Windows and macOS."""
import argparse
import errno
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import venv
import webbrowser
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
APP_ID = 'local-ai-subtitle'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def interpreter(root=ROOT, platform=None):
    platform = platform or sys.platform
    return root / '.venv' / ('Scripts/python.exe' if platform == 'win32' else 'bin/python')

def identity(port):
    try:
        with HTTP.open(f'http://127.0.0.1:{port}/api/health', timeout=1) as response:
            payload = json.load(response)
            return payload.get('app_id') if isinstance(payload, dict) else None
    except (OSError, ValueError):
        return None

def ensure_environment(python, model, skip_install=False):
    if not python.exists():
        if skip_install:
            raise RuntimeError('Environment missing. Run once without --skip-install.')
        print('首次安装 / First setup: downloading dependencies and a model.', flush=True)
        venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
    if not skip_install:
        stamp = ROOT / '.venv' / 'subtitle-requirements.txt'
        requirements = (ROOT / 'backend/requirements.txt').read_text(encoding='utf-8')
        if not stamp.exists() or stamp.read_text(encoding='utf-8') != requirements:
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'backend/requirements.txt')], check=True)
            stamp.write_text(requirements, encoding='utf-8')
        model_dir = ROOT / 'data/models' / f'models--Systran--faster-whisper-{model}'
        if not all((model_dir / name).is_file() for name in ('model.bin', 'config.json', 'tokenizer.json')):
            subprocess.run([str(python), str(ROOT / 'tools/download_model.py'), model], check=True)
    subprocess.run([str(python), '-c', 'import fastapi, uvicorn, faster_whisper, imageio_ffmpeg; import subprocess; subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-version"],check=True,stdout=subprocess.DEVNULL)'], check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default=os.environ.get('WHISPER_MODEL', 'small'), choices=('tiny','base','small','medium'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8090')))
    parser.add_argument('--setup-only', action='store_true')
    parser.add_argument('--skip-install', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise RuntimeError('Choose a port between 1024 and 65535.')
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        raise RuntimeError('Use Python 3.10–3.13 (3.11 or 3.12 recommended).')
    python = interpreter()
    if not args.setup_only:
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', args.port))
            except OSError as exc:
                if exc.errno != errno.EADDRINUSE:
                    raise
                if identity(args.port) == APP_ID:
                    print('This application is already running.', flush=True)
                    if not args.no_browser:
                        webbrowser.open(f'http://127.0.0.1:{args.port}/')
                    return
                raise RuntimeError(f'Port {args.port} belongs to another application. Use --port 8091.')
    ensure_environment(python, args.model, args.skip_install)
    if args.setup_only:
        print('Setup completed. Run again to open the app.', flush=True)
        return
    env = os.environ.copy()
    env.update(PORT=str(args.port), WHISPER_MODEL=args.model, PYTHONUTF8='1')
    proc = subprocess.Popen([str(python), str(ROOT / 'backend/main.py')], cwd=ROOT, env=env)
    try:
        for _ in range(240):
            if proc.poll() is not None:
                raise RuntimeError('Server exited. See the error above.')
            if identity(args.port) == APP_ID:
                break
            time.sleep(.25)
        else:
            raise RuntimeError('Server did not become ready within 60 seconds.')
        print(f'声序 / Shengxu: http://127.0.0.1:{args.port}/ — Ctrl+C to stop.', flush=True)
        if not args.no_browser:
            webbrowser.open(f'http://127.0.0.1:{args.port}/')
        proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'启动失败 / Launch failed: {exc}', file=sys.stderr)
        print('Check Python version, network access, and README troubleshooting.', file=sys.stderr)
        sys.exit(1)
