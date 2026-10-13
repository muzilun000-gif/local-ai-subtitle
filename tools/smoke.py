"""Real local upload -> transcription -> edited SRT/TXT export on each OS."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
env = os.environ.copy()
env.update(PORT=str(port), WHISPER_MODEL=os.environ.get('WHISPER_MODEL', 'tiny'), PYTHONUTF8='1')
proc = subprocess.Popen([sys.executable, str(ROOT/'backend/main.py')], cwd=ROOT, env=env)
def request(path, data=None, content_type='application/json', timeout=240):
    req = urllib.request.Request(f'http://127.0.0.1:{port}'+path, data=data, headers={'Content-Type':content_type})
    with HTTP.open(req, timeout=timeout) as response:
        return response.read()
try:
    for _ in range(120):
        try:
            assert json.loads(request('/api/health', timeout=1))['app_id']=='local-ai-subtitle'
            break
        except OSError:
            time.sleep(.25)
    else:
        raise AssertionError('Server failed to start')
    subprocess.run([sys.executable, str(ROOT/'tools/launch.py'), '--skip-install', '--no-browser', '--port', str(port)], check=True)
    boundary='subtitle-smoke-boundary'
    media=(ROOT/'docs/demo-input.mp4').read_bytes()
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nzh\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="demo-input.mp4"\r\nContent-Type: video/mp4\r\n\r\n'.encode()+media+f'\r\n--{boundary}--\r\n'.encode())
    result=json.loads(request('/api/upload',body,f'multipart/form-data; boundary={boundary}'))
    assert result['segments'], 'Real speech was not transcribed'
    assert all(s['end']>=s['start']>=0 for s in result['segments'])
    segments=result['segments']
    segments[0]['text']='经过校对的演示字幕'
    for fmt in ('srt','txt'):
        exported=request('/api/export',json.dumps({'segments':segments,'format':fmt}).encode())
        decoded=exported.decode('utf-8-sig')
        assert '经过校对的演示字幕' in decoded
        if fmt=='srt':
            assert '-->' in decoded
    print(json.dumps({'passed':True,'platform':sys.platform,'python':sys.version.split()[0],'segments':len(segments),'model':result['model'],'upload_transcribe_edit_export':True},ensure_ascii=False), flush=True)
finally:
    proc.terminate()
    proc.wait(timeout=15)
