# Changelog

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
