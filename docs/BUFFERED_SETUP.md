# Buffered Discord setup

This optional mode delays incoming Discord audio so Spotify can begin fading before you hear a voice. The default queue target is 50 ms. Total delay also includes capture and playback, and the fade may still follow the first syllable.

1. Install [VB-CABLE from its official website](https://vb-audio.com/Cable/) as administrator, then restart Windows.
2. Open Adaptive Volume → **Audio setup** and click **Refresh devices**.
3. Choose **Buffered**, **CABLE Output** as the recording device and your physical headphones/speakers as the output. Leave the buffer at 50 ms initially.
4. Click **Apply audio settings** and enable the app. Check that the bridge is running.
5. In Discord → User Settings → Voice & Video, set **Output Device** to **CABLE Input (VB-Audio Virtual Cable)**. Leave your microphone unchanged.

Route only Discord into the cable. Leave Spotify and other apps on your normal headphones. Do not enable Windows **Listen to this device**; that would duplicate playback outside the app's buffer.

If CABLE Output is missing, press Win + R, enter `mmsys.cpl`, and open Recording. Right-click the list, show disabled devices and enable CABLE Output. Refresh devices in the app afterward.

**Closing the window keeps the bridge running. Pausing music lowering also keeps it running. Quitting stops voice playback through the cable.** Before quitting, set Discord's output back to your headphones. The recovery button opens the Windows mixer and explains how to restore direct voice playback.

If you want Discord to work with the app closed, use Unbuffered mode and keep Discord's output on your headphones instead.

Use Diagnostics for device-reported timing and a local synthetic comparison. The synthetic test excludes VB-CABLE capture, Discord and acoustic playback. No buffer increases happen automatically.
