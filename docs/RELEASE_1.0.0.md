# Adaptive Volume 1.0.0

A small Windows app that automatically lowers Spotify while your friends speak
on Discord and smoothly brings it back afterward.

## Download and install

1. Download **AdaptiveVolume-1.0.0-windows-x64.zip** below.
2. Extract the ZIP and open **AdaptiveVolume.exe** inside the extracted folder.
3. Keep Discord on your headphones. The default **Unbuffered** mode listens automatically; no driver or Python installation is required.
4. Choose your lowered music level and voice threshold. Optionally enable **Start with Windows** in Audio setup.

The ZIP includes the executable, its `_internal` runtime folder, setup guides and
license notices. Keep the whole folder together. This is an unsigned portable
build for Windows 11 on 64-bit Intel/AMD systems; Windows ARM is not supported.
`SHA256SUMS.txt` contains the ZIP checksum.

## Features

- Spotify-only volume control; playback, microphone and other app volumes stay unchanged.
- 25 ms fade down, 1.1-second quiet hold after speech, and 250 ms fade up.
- Configurable lowered level, preview button and shared tray slider.
- Adjustable minimum voice level with a live meter to filter quiet background noise.
- Dark interface, automatic listening, optional Windows startup and Ctrl + Alt + M toggle.
- Saved settings, Spotify volume recovery and automatic audio-device retries.
- Optional VB-CABLE buffered playback with a 50 ms initial queue target.
- Local audio analysis, with no conversation recording, telemetry or game detection.

## Notes

Voice detection can still mistake loud background sounds for speech or miss quiet
voices. Unbuffered mode lowers music after detection. Buffered mode may begin
fading earlier, but neither its 50 ms setting nor the synthetic timing test
guarantees total added delay or a completed fade before the first syllable.
If Discord is routed into VB-CABLE, keep the app running; otherwise use direct
headphone output with Unbuffered mode.

19 automated checks and packaged launch/exit checks passed locally. Tests used
synthetic audio rather than Discord calls. Windows sign-in and physical device
reconnection remain unverified. See the README and validation guide for details.

<sub>Made with GPT-6.1 Sol.</sub>
