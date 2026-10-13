# Changelog

## 1.0.2

Fix a native crash during Windows audio object cleanup that could terminate the
app and silence buffered Discord playback. Run Windows audio control in a helper
process with one Python thread, keeping COM object creation and cleanup together.
The helper restarts automatically if it fails; the voice bridge keeps running.

Retain Spotify volume restoration and add helper crash diagnostics in
`data/audio-worker-crash.log`.

Open settings from either a single or double tray click, defer restoration until
the Windows tray callback returns, and log activation and window visibility.

## 1.0.1

Detect and automatically restart a buffered bridge that keeps running silently
while VB-CABLE has audio, including after Windows startup. Recovery checks actual
audio forwarding independently of the voice detection threshold, tolerates brief
gaps, and spaces repeated attempts at least 15 seconds apart.

Add rotating local startup, routing and bridge health logs in `data/runtime.log`.
Logs contain diagnostic measurements and device names; no audio recordings.

## 1.0.0

First public release for Windows x64.

Introduces automatic Spotify volume lowering for Discord, an adjustable voice
threshold, tray controls and optional Windows startup. Includes direct playback
by default, optional VB-CABLE buffering and local timing diagnostics.

Volume timing: 25 ms down, a 1.1-second hold after speech and 250 ms back up.
