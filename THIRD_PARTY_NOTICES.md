# Third-party notices

The Adaptive Volume source uses the [MIT license](LICENSE). Its bundled libraries
have their own licenses, included under `licenses/third-party`. These notices
belong with the distributed app.

| Component | Upstream source |
| --- | --- |
| Python 3.14.7 and standard library | https://www.python.org/downloads/release/python-3147/ |
| PySide6 and Shiboken 6.10.2 | https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.10.2-src/ |
| Qt 6.10.2 | https://download.qt.io/official_releases/qt/6.10/6.10.2/submodules/ |
| NumPy and OpenBLAS | https://github.com/numpy/numpy |
| sounddevice and PortAudio | https://github.com/spatialaudio/python-sounddevice and https://github.com/PortAudio/portaudio |
| pycaw | https://github.com/AndreMiras/pycaw |
| comtypes | https://github.com/enthought/comtypes |
| psutil | https://github.com/giampaolo/psutil |
| WebRTC VAD wheels | https://github.com/daanzu/py-webrtcvad-wheels |
| CFFI and pycparser | https://github.com/python-cffi/cffi and https://github.com/eliben/pycparser |
| PyInstaller bootloader | https://github.com/pyinstaller/pyinstaller |

The included Qt GUI libraries, PySide6 and Shiboken use the LGPLv3 option of their
open-source licenses. Their DLLs are separate files in `_internal`, allowing
compatible library replacements. Their source was not modified; the source
archives and repositories are linked above, and the license texts are included.

Microsoft runtime libraries retain Microsoft's redistribution terms. Notices
for native libraries shipped with Python are included in Python's license text.

VB-CABLE is optional third-party software distributed separately by VB-Audio.
Its installer is not included in this repository or release.
