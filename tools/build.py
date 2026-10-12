"""Reproducible Windows distribution with matching executable/window/tray icon."""
from pathlib import Path
import os
import subprocess
import sys
import shutil
from package_support import prepare_distribution
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
release = '--release' in sys.argv
output_root = root / 'dist' / 'release' if release else root / 'dist'
saved_data = output_root / 'AdaptiveVolume' / 'data'
backup = root / 'data' / 'build-settings-backup'
if saved_data.exists() and not release:
    shutil.copytree(saved_data, backup, dirs_exist_ok=True)
assets = root / 'assets'
assets.mkdir(exist_ok=True)
image = Image.new('RGBA', (256, 256))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=60, fill='#192b38')
for x, height in [(60, 44), (94, 96), (128, 144), (162, 96), (196, 44)]:
    draw.rounded_rectangle((x-9, 128-height//2-9, x+9, 128+height//2+9), radius=9, fill='#60d8c0')
icon = assets / 'adaptive-volume.ico'
image.save(icon, sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)])
environment = os.environ.copy()
# Codex's Poppler runtime contains a different ICU ABI with the same DLL name.
# Resolve system Qt dependencies exactly as Windows does for the source app.
windows = Path(os.environ['SystemRoot'])
environment['PATH'] = os.pathsep.join([str(windows / 'System32'), str(windows),
                                      str(Path(sys.executable).parent)])
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
    '--distpath', str(output_root),
    '--windowed', '--name', 'AdaptiveVolume', '--icon', str(icon),
    '--add-data', f'{icon};assets', '--collect-submodules', 'pycaw',
    '--additional-hooks-dir', str(root / 'hooks'),
    '--hidden-import', '_webrtcvad', '--exclude-module', 'PySide6.QtWebEngineCore',
    '--exclude-module', 'PySide6.QtWebEngineWidgets', '--exclude-module', 'PySide6.QtPdf',
    '--exclude-module', 'cv2', '--exclude-module', 'mss',
    '--exclude-module', 'pytest', '--exclude-module', 'tkinter', str(root / 'app.py')],
    cwd=root, env=environment, check=True)
distribution = output_root / 'AdaptiveVolume'
if backup.exists() and not release:
    shutil.copytree(backup, distribution / 'data', dirs_exist_ok=True)
prepare_distribution(root, distribution)
print(distribution / 'AdaptiveVolume.exe')
