# Current validation — Discord only

The app lowers Spotify only for incoming Discord speech. Game calibration, game audio capture, screen recognition and their dependencies have been removed. No screen capture runs.

Current timing: 25 ms down, hold until 1.1 seconds after estimated audible speech end, 250 ms up. New speech interrupts restoration continuously. Existing settings are preserved across the timing and Discord-only migration. Startup registration and the desktop shortcut keep pointing to the same executable.

19 automated checks pass, covering timing, interrupted fades, buffer operation, Spotify baseline and mute preservation, live noise gating, startup retries and migration from game-enabled settings. Source GUI and native tray smoke passed.

Earlier integration checks verified independent process capture, live Spotify restoration without affecting unrelated apps, and cable forwarding automatically across two packaged app restarts. No Discord call was used for testing.

The 50 ms buffer is a queue target, not total end-to-end latency. Synthetic timing measurements exclude Discord, cable capture and acoustic playback; total delay and predictive fade completion are not guaranteed. The threshold rejects quiet sounds; loud noise can still resemble speech and high thresholds can exclude quiet friends. Physical device reconnection and Windows sign-in are not yet tested.

The frozen GUI explicitly stops workers, restores Spotify and destroys native windows before using a controlled process exit to avoid the known Qt/Python DLL finalizer crash on this host.

Public release preparation: new installations use Unbuffered mode by default, existing saved modes remain unchanged, and smoke checks use a separate instance identifier. The release package includes documentation and runtime notices and excludes all local data. Unused Qt plugins and libraries are removed during packaging.
