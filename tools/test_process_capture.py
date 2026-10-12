import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import time
import json
import numpy as np
from adaptive_volume.process_audio import ProcessCapture

child = subprocess.Popen([sys.executable, str(Path(__file__).with_name('test_source.py'))])
blocks = []
capture = ProcessCapture(child.pid, lambda block, now: blocks.append(block.copy()))
try:
    capture.start()
    capture.ready.wait(6)
    time.sleep(3)
finally:
    capture.stop()
    child.terminate()
    child.wait()
result = {'error': capture.error, 'blocks': len(blocks),
          'frames': sum(len(x) for x in blocks),
          'peak': float(max((np.max(np.abs(x)) for x in blocks), default=0))}
print(json.dumps(result, indent=2))
if result['error'] or result['peak'] < .001:
    sys.exit(1)
