# Run and build from source

Use 64-bit Windows and Python 3.14. The release was built with Python 3.14.7. Exact dependency versions are recorded in `requirements-lock.txt`.

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

The portable release contains the executable, runtime dependencies, documentation and license notices. Personal settings, generated audio, logs and developer tools are excluded. The release output is under `dist/release/`; the ZIP and checksum file are under `dist/`.

Without `--release`, the build updates `dist/AdaptiveVolume` and preserves its local data. Quit that copy of the app before rebuilding it.

Integration tools are explicit opt-in checks. `test_spotify.py` temporarily changes and restores live Spotify mixer volume. `test_restart_bridge.py` needs VB-CABLE and the non-release packaged app; it plays a quiet test tone. Other audio tests use generated audio and never join or test through Discord.

## Source layout

| Module | Responsibility |
| --- | --- |
| `audio.py`, `process_audio.py`, `buffer.py` | Discord capture and optional buffered playback |
| `speech.py`, `envelope.py` | Voice detection and smooth volume timing |
| `volume.py` | Spotify session controls and recovery |
| `controller.py` | Coordinate workers and device retries |
| `gui.py`, `startup.py`, `config.py` | Interface, tray, Windows startup and saved settings |
| `diagnostics.py` | Synthetic timing comparison |

Audio processing runs separately from the interface. There is no game detection or screen capture.
