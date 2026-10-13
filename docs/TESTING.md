# Testing and limitations

## What has been checked

Version 1.0.0 passed 19 automated tests and the GitHub Windows build workflow.
The checks cover fade timing, new speech during restoration, noise thresholds,
saved settings, audio buffering, device retry logic and Spotify volume recovery.

Version 1.0.1 passed 24 automated tests, including regressions for active but silent bridge
streams, normal source silence and quiet audio below the voice threshold. A local
test used the real VB-CABLE signal meter and generated audio, deliberately replaced
capture data with silence while both streams remained active, and verified that
automatic reopening restored capture and playback samples. Native GUI and tray
checks passed. This reproduces the recovery failure in a controlled test; it does
not establish the exact cause of the reported cold-boot Discord silence.

Version 1.0.2 moves Windows audio COM objects into a helper process with one
Python thread after crash logs showed COM pointer cleanup on GUI and PortAudio
callback threads. A real VB-CABLE test forced 167 collections in the main process
and terminated the helper while audio played. The helper restarted, the same
capture/playback streams stayed active, and rendered audio continued. The largest
observed callback age was approximately 6 ms. This checks helper crash containment
and thread ownership; it does not guarantee uninterrupted playback through all
possible driver, bridge-process or Windows failures.

Additional local checks verified the Windows interface and tray menu, capture
from a separate audio process, and VB-CABLE forwarding across two app restarts.
Live Spotify checks confirmed volume restoration and that unrelated apps kept
their original levels. The packaged app passed launch, exit and generated-audio tests.

Audio tests used a separate test app or computer-generated speech. They did not
use a Discord call. Windows sign-in and physical headphone disconnection and
reconnection have not been tested; their recovery logic has automated coverage.

## What to expect

- Loud noise or Discord notifications can resemble speech. A higher minimum voice level rejects more quiet sounds, but can also miss quiet speakers.
- Unbuffered mode responds after speech is detected. It cannot lower music before a person starts talking.
- The Buffered mode's 50 ms setting controls the app's audio queue. Actual delay also includes capture and playback, so a fade before the first syllable is not guaranteed.
- The Diagnostics comparison measures generated audio through the app's queue and Windows playback path. It excludes VB-CABLE input, a Discord call and the physical headphones.

Windows 11 x64 is the tested platform. Process-specific capture uses a Windows
API requiring build 20348 or later, as documented in
[Microsoft's loopback sample](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/).

## Packaging detail

On the development PC, Qt crashed during DLL cleanup after the packaged GUI had
closed. The app therefore explicitly stops its workers, restores Spotify and
destroys its windows before ending the packaged process. The launch/exit check
confirms that this cleanup completed. See the comments in `app.py` for the implementation.
