# Run and build from source

These instructions are for developers. To use the app, download the packaged
release using the [README](../README.md).

Use Windows 11 x64 and Python 3.14. The first release used Python 3.14.7;
`requirements-lock.txt` lists the exact dependency versions.

From the project directory:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe app.py
```

Run checks and make a clean release:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\gui_smoke.py
.\.venv\Scripts\python.exe tools\build.py --release
.\.venv\Scripts\python.exe tools\package_zip.py --release
```

The app folder is created in `dist/release/AdaptiveVolume`. The ZIP and SHA-256
checksum file are created in `dist/`. The ZIP contains the executable, runtime
libraries, documentation and license notices. It excludes local settings and test data.

Without `--release`, the build updates `dist/AdaptiveVolume` and preserves its local data. Quit that copy of the app before rebuilding it.

## Additional audio checks

Run these manually when the relevant devices and apps are available:

- `tools/test_process_capture.py` starts a separate audio source and checks process capture.
- `tools/test_spotify.py` briefly changes and restores live Spotify mixer volume.
- `tools/test_restart_bridge.py` plays a quiet tone through VB-CABLE across two app launches. It requires Buffered mode configured in `dist/AdaptiveVolume`; quit any existing copy first.
- `tools/test_bridge_recovery.py` starts cable audio after the bridge, injects silent capture callbacks into otherwise active streams, and checks automatic recovery with the real Windows cable signal meter. It requires the same saved Buffered settings and no running copy of the app.

These tools use test audio rather than Discord calls. For a timing comparison,
use the app's Diagnostics tab. Results and remaining gaps are documented in
[TESTING.md](TESTING.md).

## Source layout

| Module | Responsibility |
| --- | --- |
| `audio.py`, `process_audio.py`, `buffer.py` | Discord capture and optional buffered playback |
| `speech.py`, `envelope.py` | Voice detection and smooth volume timing |
| `volume.py` | Spotify session controls and recovery |
| `controller.py` | Coordinate workers and device retries |
| `gui.py`, `startup.py`, `config.py` | Interface, tray, Windows startup and saved settings |
| `diagnostics.py` | Synthetic timing comparison |

Audio processing runs separately from the interface. Volume control uses Windows
Core Audio; capture and playback use WASAPI, and speech detection uses WebRTC VAD.

## Contributing

For a bug report, include the app version, Windows version, playback mode and
steps to reproduce it. Relevant text from Diagnostics is helpful; remove private
information before sharing it. Conversation recordings are not needed.

For code changes, keep playback independent of the GUI, preserve Spotify's normal
volume and mute state, and run the checks above. Describe what changes for the user
and how you tested it.
