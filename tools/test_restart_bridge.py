"""Verify packaged automatic forwarding after repeated launches; no Discord use."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import json
import subprocess
import sys
import time
import numpy as np
import sounddevice as sd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from adaptive_volume.process_audio import ProcessCapture

user = C.windll.user32
user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
user.PostThreadMessageW.argtypes = [W.DWORD, W.UINT, W.WPARAM, W.LPARAM]
callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)


def quit_process(process):
    threads = set()
    @callback_type
    def visit(hwnd, data):
        pid = W.DWORD()
        tid = user.GetWindowThreadProcessId(hwnd, C.byref(pid))
        if pid.value == process.pid:
            threads.add(tid)
        return True
    user.EnumWindows(visit, 0)
    for tid in threads:
        user.PostThreadMessageW(tid, 0x0012, 0, 0)
    return process.wait(timeout=10)


results = []
source = next(i for i, d in enumerate(sd.query_devices())
    if d['name'] == 'CABLE Input (VB-Audio Virtual Cable)' and
    sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI')
for attempt in range(2):
    process = subprocess.Popen([str(root / 'dist/AdaptiveVolume/AdaptiveVolume.exe'), '--tray'])
    capture = None
    try:
        time.sleep(3)
        assert process.poll() is None, 'Packaged app exited before test'
        blocks, errors = [], []
        capture = ProcessCapture(process.pid, lambda x, t: blocks.append(x.copy()), errors.append)
        capture.start()
        time.sleep(.5)
        samples = np.arange(48000)
        tone = (.025 * np.sin(2 * np.pi * 440 * samples / 48000)).astype('float32')
        sd.play(np.column_stack([tone, tone]), samplerate=48000, device=source, blocking=True)
        time.sleep(.5)
        capture.stop()
        peak = float(max((np.max(np.abs(x)) for x in blocks), default=0))
        assert peak > .015 and not errors, (peak, errors)
        results.append({'launch': attempt + 1, 'app_pid': process.pid, 'forwarded_peak': peak,
                        'blocks': len(blocks), 'errors': errors})
    finally:
        if capture:
            capture.stop()
        if process.poll() is None:
            code = quit_process(process)
            assert code == 0, code
report = {'automatic_bridge_after_each_restart': True, 'source': 'separate synthetic tone to CABLE Input',
          'scope': 'Digital app output, excludes acoustic listening and Discord', 'results': results}
(root / 'data/restart-bridge-test.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
