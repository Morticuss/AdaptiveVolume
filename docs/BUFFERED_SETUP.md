# Buffered Discord setup

Buffered mode is optional. It adds a short delay to Discord playback so the app
can detect speech and begin lowering Spotify before you hear the voice. For the
standard setup without an extra driver, use the [README](../README.md).

1. Install [VB-CABLE from its official website](https://vb-audio.com/Cable/) as administrator, then restart Windows.
2. Open Adaptive Volume → **Audio setup** and click **Refresh devices**.
3. Choose **Buffered**, **CABLE Output** as the recording device and your physical headphones/speakers as the output. Leave the buffer at 50 ms initially.
4. Click **Apply audio settings**. If the app is paused, enable it from Overview. Check that its status says **Buffered audio bridge running** before changing Discord.
5. In Discord → User Settings → Voice & Video, set **Output Device** to **CABLE Input (VB-Audio Virtual Cable)**. Leave your microphone unchanged.

**CABLE Input** is where Discord sends sound. **CABLE Output** is where Adaptive
Volume receives that sound and forwards it to your headphones. These names refer
to the virtual cable; your microphone's Input Device in Discord stays unchanged.

Leave Spotify and other apps on your normal headphones. Do not enable Windows
**Listen to this device**, which would play a second copy of Discord audio.

If CABLE Output is missing, press Win + R, enter `mmsys.cpl`, and open Recording. Right-click the list, show disabled devices and enable CABLE Output. Refresh devices in the app afterward.

## Keep voice playback working

Closing the window or pausing music lowering keeps voice playback running.
**Quitting the app stops Discord audio through the cable.** Before quitting,
change Discord's output back to your headphones. If audio stops unexpectedly,
**Recover direct voice audio** explains how to restore it.

To return permanently to the standard setup, set Discord's output to your
headphones, choose **Unbuffered** in the app and apply the change.

## Delay

The default **50 ms** buffer is the time the app aims to keep audio queued.
Capture and headphone playback add more delay, so it does not guarantee that
the music fade finishes before a voice becomes audible. The app never increases
this setting automatically. See [testing and limitations](TESTING.md) for what
the Diagnostics timing comparison measures.
