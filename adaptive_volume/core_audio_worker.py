"""Keep Core Audio COM objects on a single thread in a separate process.

comtypes pointers can contain cycles. Python may finalize them on whichever
thread triggers GC, including PortAudio callbacks, outside their COM apartment.
This process has one Python thread and never owns the voice playback bridge.
"""
import logging
import multiprocessing as mp
import time

log = logging.getLogger(__name__)


def routing_status(executable, buffered):
    from pycaw.utils import AudioUtilities
    from .volume import all_sessions
    names = {d.id: d.FriendlyName for d in AudioUtilities.GetAllDevices()}
    found = []
    for endpoint, session in all_sessions():
        try:
            if session.State == 1 and session.Process and session.Process.name().lower() == executable.lower():
                found.append(names.get(endpoint, endpoint))
        except Exception:
            continue
    if not found:
        return 'No Discord audio session yet. Buffered output: CABLE Input. Unbuffered output: your headphones.'
    if buffered:
        return ('Discord cable routing detected' if all('cable input' in d.lower() for d in found)
                else 'Discord is not fully routed to CABLE Input. Change its Output Device in Voice & Video.')
    return ('Switch Discord output back to your headphones for unbuffered playback.'
            if any('cable' in d.lower() for d in found) else 'Direct Discord output detected')


def _run(gain, buffered, executable, stop, status):
    import gc
    import comtypes
    import faulthandler
    from .config import data_dir
    from .runtime_log import configure
    from .volume import SpotifyVolume, cable_peak
    configure()
    crash_file = None
    try:
        data_dir().mkdir(parents=True, exist_ok=True)
        crash_file = (data_dir() / 'audio-worker-crash.log').open('a', encoding='utf-8')
        faulthandler.enable(crash_file, all_threads=True)
    except OSError:
        pass
    # Import initializes COM on this process's sole Python thread. Explicit
    # initialization is balanced before returning to multiprocessing cleanup.
    comtypes.CoInitialize()
    volume = SpotifyVolume()
    refresh = 0.
    previous_route = None
    meter_warning = False
    log.info('Core Audio worker started')
    try:
        while not stop.wait(.002):
            now = time.perf_counter()
            volume.apply(gain.value)
            if now < refresh:
                continue
            refresh = now + 1
            snapshot = {'spotify_count': len(volume.sessions), 'error': volume.error}
            try:
                volume.refresh()
                snapshot['spotify_count'] = len(volume.sessions)
                route = routing_status(executable, buffered.value)
                snapshot['routing_status'] = route
                if route != previous_route:
                    log.info('Routing: %s', route)
                    previous_route = route
                if buffered.value:
                    try:
                        if cable_peak() > .001:
                            snapshot['cable_signal_time'] = time.perf_counter()
                    except Exception:
                        if not meter_warning:
                            log.exception('Cable signal meter unavailable')
                            meter_warning = True
            except Exception as exc:
                snapshot['error'] = f'Audio session discovery will retry: {exc}'
            # A Pipe sends only plain data synchronously; no Queue feeder thread
            # may collect COM cycles in this process.
            status.send(snapshot)
            gc.collect()
    finally:
        try:
            volume.restore()
        finally:
            volume.sessions.clear()
            del volume
            gc.collect()
            comtypes.CoUninitialize()
            status.close()
            log.info('Core Audio worker stopped; normal Spotify volume restored')
            if crash_file:
                faulthandler.disable()
                crash_file.close()


class CoreAudioWorker:
    def __init__(self, settings):
        self.settings = settings
        self.context = mp.get_context('spawn')
        self.gain = self.context.Value('d', 1.)
        self.buffered = self.context.Value('b', settings.buffered)
        self.stop_event = self.context.Event()
        self.process = None
        self.status = None
        self.next_start = 0.

    def update(self, gain):
        self.gain.value = gain
        self.buffered.value = self.settings.buffered
        now = time.perf_counter()
        snapshot = {}
        if self.process and not self.process.is_alive():
            log.error('Core Audio worker exited: code=%s; restarting without stopping voice playback', self.process.exitcode)
            self.process.join()
            self.process.close()
            self.process = None
            self.status.close()
            self.status = None
            snapshot['error'] = 'Windows audio control restarted; voice playback remains running.'
        if self.process is None and now >= self.next_start:
            self.next_start = now + 2
            self.stop_event.clear()
            self.status, sender = self.context.Pipe(duplex=False)
            self.process = self.context.Process(target=_run,
                args=(self.gain, self.buffered, self.settings.discord_exe,
                      self.stop_event, sender), name='Windows audio control', daemon=True)
            try:
                self.process.start()
            finally:
                sender.close()
        if self.status:
            try:
                while self.status.poll():
                    snapshot.update(self.status.recv())
            except (EOFError, OSError):
                pass  # Restart the exited worker on the next update.
        return snapshot

    def close(self):
        self.stop_event.set()
        if self.process:
            self.process.join(4)
            if self.process.is_alive():
                # Only stop the hung helper; the app's bridge lives elsewhere.
                log.error('Core Audio worker did not shut down; stopping helper')
                self.process.terminate()
                self.process.join(2)
            if not self.process.is_alive():
                self.process.close()
                self.process = None
        if self.status:
            self.status.close()
            self.status = None
