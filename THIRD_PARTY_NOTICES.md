# Third-party notices

Adaptive Volume's application source is MIT licensed. The portable Windows
package includes independently licensed libraries; their notices are included
under `licenses/third-party`.

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

Qt, PySide6 and Shiboken are used under their open-source LGPLv3 option where
applicable. They are dynamically linked and their DLLs remain separate in
`_internal`, so compatible replacements can be supplied. No modifications were
made to their source. GPL and LGPL license texts are included with their notices.
Corresponding upstream sources for the distributed versions are linked above.

The release omits unused Qt PDF, Virtual Keyboard and QML/Quick libraries and
plugins. It retains the Windows platform plugin and the GUI libraries needed by
the app. Microsoft runtime libraries included by the Python/Qt distributions
remain subject to Microsoft's redistribution terms. Additional license notices
for Python's bundled native libraries are included in its license text.

VB-CABLE is optional third-party software distributed separately by VB-Audio.
Its installer is not included in this repository or release.
