# Adaptive Volume

Enjoy Spotify at your normal volume between conversations. Adaptive Volume smoothly lowers the music when your friends speak on Discord, then brings it back when they finish.

A small Windows app with a dark interface, tray controls and local voice detection.

**[Download the latest release](https://github.com/Morticuss/AdaptiveVolume/releases/latest)**

![Adaptive Volume interface](docs/images/app.png)

## Install

1. Download **AdaptiveVolume-1.0.0-windows-x64.zip** from the release page.
2. Right-click the ZIP and choose **Extract All**. Keep the extracted folder somewhere permanent and writable.
3. Open **AdaptiveVolume.exe** inside the folder. No Python installation is needed.
4. Leave Discord's output set to your headphones. The app starts in **Unbuffered** mode and listens automatically.
5. In **Audio setup**, enable **Start with Windows** if you want it to run quietly in the tray whenever you sign in.

Keep the whole folder together: the executable needs its `_internal` folder. Use the Discord and Spotify desktop apps on **Windows 11, 64-bit Intel/AMD**. This is the tested platform. Unbuffered capture requires Windows build 20348 or later; see [Microsoft's process-loopback requirements](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/).

## Use it

- **Lowered music level:** choose how quiet Spotify becomes while someone speaks. The default is 25% of its normal Windows mixer volume.
- **Preview fade:** hear the effect without joining a call.
- **Voice detection:** raise **Minimum voice level** to ignore quiet background noise. Watch the live meter, then set the minimum above the noise but below your quietest friend's voice.
- **Pause:** stop automatic music lowering. **Ctrl + Alt + M** also toggles it.
- **Tray icon:** right-click for the music level slider and quick controls; double-click to open settings. Closing the window keeps the app running.

The voice threshold defaults to **−40 dBFS**. Move right to require louder audio; for example, −30 dBFS is a higher threshold than −40 dBFS. Changes apply immediately and are saved.

Music fades down over **25 ms**, stays lowered until **1.1 seconds after speech ends**, then fades up over **250 ms**. New speech smoothly interrupts the return. Spotify keeps playing, and the app never raises it above your normal mixer level. Your microphone and other apps' volumes are unchanged.

## Optional buffered mode

Unbuffered mode is the simplest setup: Discord always remains audible, even when this app is closed. Music lowering begins after speech is detected.

Buffered mode uses **VB-CABLE** to analyse voice audio before playing it through your headphones. Its initial buffer target is 50 ms, but that does not guarantee a fade before the first syllable or represent total added latency.

See the [buffered setup guide](docs/BUFFERED_SETUP.md) if you want to try it. In this mode, Discord needs the app running to remain audible through the cable.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Music lowers for background noise | Raise the minimum voice level and try **Noise resistant** sensitivity in Audio setup. |
| Quiet friends do not trigger it | Lower the minimum voice level or select a more sensitive detector. |
| Nothing happens | Open Spotify and Discord desktop, check the app is enabled, and confirm the playback mode matches your Discord output. |
| Discord is silent through VB-CABLE | Check the buffered setup guide, or return Discord directly to your headphones and use Unbuffered mode. |
| The app does not start with Windows | Enable **Start with Windows** again after moving the app, and check Windows Settings → Apps → Startup. |

Voice detection can still mistake loud background sounds or notifications for speech. The Diagnostics test uses synthetic audio; it does not measure a complete Discord call or guarantee detection accuracy. Current checks and limitations are listed in [VALIDATION.md](VALIDATION.md).

## Privacy and removal

Audio analysis runs locally. The app does not record conversations, capture screenshots, read game memory or send telemetry. Settings and recovery information are stored in the `data` folder next to the executable. A diagnostic test can save generated synthetic speech and its timing report there.

To remove the app, turn off **Start with Windows**, quit it from the tray, then delete its folder. If you used buffered mode, restore Discord's output to your headphones first and uninstall VB-CABLE separately if desired.

## Development

Built with Python, PySide6, Windows WASAPI, Core Audio and WebRTC VAD. See [BUILDING.md](docs/BUILDING.md) to run, test or package the source.

Licensed under [MIT](LICENSE). Bundled dependencies retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

<sub>Made with GPT-6.1 Sol.</sub>
