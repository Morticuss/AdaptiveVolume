"""Windows process-loopback capture through the documented WASAPI interface.

This observes an application; it never injects into it or changes its output.
The COM completion handler is kept alive until asynchronous activation completes.
"""
import ctypes as C
from ctypes import wintypes as W
import threading
import time
import uuid
import numpy as np

HRESULT = C.c_long
P = C.c_void_p


class GUID(C.Structure):
    _fields_ = [('raw', C.c_ubyte * 16)]

    def __init__(self, value):
        super().__init__()
        self.raw[:] = uuid.UUID(value).bytes_le


class WaveFormat(C.Structure):
    _pack_ = 1
    _fields_ = [('tag', W.WORD), ('channels', W.WORD), ('rate', W.DWORD),
                ('bytes_sec', W.DWORD), ('align', W.WORD), ('bits', W.WORD), ('extra', W.WORD)]


class Parameters(C.Structure):
    _fields_ = [('activation', C.c_int), ('pid', W.DWORD), ('mode', C.c_int)]


class Blob(C.Structure):
    _fields_ = [('size', W.ULONG), ('data', P)]


class VariantValue(C.Union):
    _fields_ = [('blob', Blob), ('padding', C.c_ubyte * 16)]


class PropVariant(C.Structure):
    _fields_ = [('vt', W.WORD), ('r1', W.WORD), ('r2', W.WORD), ('r3', W.WORD), ('value', VariantValue)]


def method(ptr, slot, result, *args):
    table = C.cast(ptr, C.POINTER(C.POINTER(P))).contents
    return C.WINFUNCTYPE(result, P, *args)(table[slot])


def checked(hr, context):
    if hr < 0:
        raise OSError(f'{context}: WASAPI error 0x{hr & 0xffffffff:08X}')


class Completion:
    def __init__(self):
        self.event = threading.Event()
        self.client = P()
        self.error = None
        self.refs = 1
        accepted = {uuid.UUID(x).bytes_le for x in (
            '00000000-0000-0000-C000-000000000046',
            '41D949AB-9862-444A-80F6-C261334DA5EB',
            '94EA2B94-E9CC-49E0-C0FF-EE64CA8F5B90')}

        def query(this, iid, out):
            if C.string_at(iid, 16) in accepted:
                out[0] = this
                self.refs += 1
                return 0
            out[0] = None
            return -2147467262

        def add(this):
            self.refs += 1
            return self.refs

        def release(this):
            self.refs -= 1
            return self.refs

        def completed(this, operation):
            try:
                activation_hr = HRESULT()
                result = method(operation, 3, HRESULT, C.POINTER(HRESULT), C.POINTER(P))(
                    operation, C.byref(activation_hr), C.byref(self.client))
                checked(result, 'GetActivateResult')
                checked(activation_hr.value, 'Process audio activation')
            except Exception as exc:
                self.error = exc
            finally:
                self.event.set()
            return 0

        self.callbacks = [
            C.WINFUNCTYPE(HRESULT, P, P, C.POINTER(P))(query),
            C.WINFUNCTYPE(W.ULONG, P)(add), C.WINFUNCTYPE(W.ULONG, P)(release),
            C.WINFUNCTYPE(HRESULT, P, P)(completed)]
        self.table = (P * 4)(*[C.cast(f, P).value for f in self.callbacks])
        self.object = (P * 1)(C.cast(self.table, P).value)
        self.ptr = C.cast(self.object, P)


# Retain timed-out asynchronous callbacks: Windows may invoke them after timeout.
_pending = []


class ProcessCapture:
    def __init__(self, pid, on_audio, on_error=lambda msg: None, endpoint=None):
        self.pid, self.on_audio, self.on_error = pid, on_audio, on_error
        self.endpoint = endpoint
        self.stop_event = threading.Event()
        self.thread = None
        self.ready = threading.Event()
        self.error = None

    def start(self):
        self.thread = threading.Thread(target=self._run, name=f'WASAPI-{self.pid}', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(6)

    def _run(self):
        ole = C.OleDLL('ole32')
        ole.CoInitializeEx(None, 0)
        client, capture, operation = P(), P(), P()
        completion = None
        started = False
        try:
            if self.endpoint:
                import comtypes
                from pycaw.utils import AudioUtilities
                from pycaw.constants import EDataFlow, DEVICE_STATE
                device = next((d for d in AudioUtilities.GetAllDevices(
                    data_flow=EDataFlow.eRender.value, device_state=DEVICE_STATE.ACTIVE.value)
                    if d.FriendlyName == self.endpoint), None)
                if device is None:
                    raise ValueError('Selected render device is unavailable')
                interface = device._dev.Activate(comtypes.GUID('1CB9AD4C-DBFA-4C32-B178-C2F568A703B2'),
                                                 comtypes.CLSCTX_ALL, None)
                client = C.cast(interface, P)
                method(client, 1, W.ULONG)(client)  # Own a separate native reference.
            else:
                completion = Completion()
                params = Parameters(1, self.pid, 0)  # Include target process tree.
                variant = PropVariant()
                variant.vt = 65  # VT_BLOB
                variant.value.blob = Blob(C.sizeof(params), C.cast(C.pointer(params), P))
                activate = C.WinDLL('Mmdevapi').ActivateAudioInterfaceAsync
                activate.argtypes = [W.LPCWSTR, C.POINTER(GUID), C.POINTER(PropVariant), P, C.POINTER(P)]
                activate.restype = HRESULT
                iid = GUID('1CB9AD4C-DBFA-4C32-B178-C2F568A703B2')
                checked(activate('VAD\\Process_Loopback', C.byref(iid), C.byref(variant),
                                 completion.ptr, C.byref(operation)), 'ActivateAudioInterfaceAsync')
                if not completion.event.wait(5):
                    _pending.append((completion, params, variant, operation))
                    operation = P()
                    raise TimeoutError('Process audio activation timed out')
                if completion.error:
                    raise completion.error
                client = completion.client
            fmt = WaveFormat(1, 2, 48000, 192000, 4, 16, 0)
            checked(method(client, 3, HRESULT, C.c_int, W.DWORD, C.c_longlong,
                           C.c_longlong, C.POINTER(WaveFormat), P)(
                               client, 0, 0x80020000, 1000000, 0, C.byref(fmt), None), 'Initialize')
            capture_iid = GUID('C8ADBD64-E71E-48A0-A4DE-185C395CD317')
            checked(method(client, 14, HRESULT, C.POINTER(GUID), C.POINTER(P))(
                client, C.byref(capture_iid), C.byref(capture)), 'GetService')
            checked(method(client, 10, HRESULT)(client), 'Start')
            started = True
            self.ready.set()
            next_size = method(capture, 5, HRESULT, C.POINTER(W.UINT))
            get_buffer = method(capture, 3, HRESULT, C.POINTER(P), C.POINTER(W.UINT),
                                C.POINTER(W.DWORD), C.POINTER(C.c_ulonglong), C.POINTER(C.c_ulonglong))
            release_buffer = method(capture, 4, HRESULT, W.UINT)
            while not self.stop_event.wait(.002):
                count = W.UINT()
                checked(next_size(capture, C.byref(count)), 'GetNextPacketSize')
                while count.value:
                    data, frames, flags, qpc = P(), W.UINT(), W.DWORD(), C.c_ulonglong()
                    checked(get_buffer(capture, C.byref(data), C.byref(frames), C.byref(flags), None, C.byref(qpc)), 'GetBuffer')
                    try:
                        if flags.value & 2:
                            block = np.zeros((frames.value, 2), np.float32)
                        else:
                            raw = C.string_at(data, frames.value * 4)
                            block = np.frombuffer(raw, '<i2').reshape(-1, 2).astype(np.float32) / 32768
                    finally:
                        checked(release_buffer(capture, frames.value), 'ReleaseBuffer')
                    # The callback timestamp is the sample's estimated audible end,
                    # not the later time when this polling thread happened to run.
                    end = qpc.value / 10000000 + frames.value / 48000 if qpc.value and not flags.value & 4 else time.perf_counter()
                    self.on_audio(block, end)
                    checked(next_size(capture, C.byref(count)), 'GetNextPacketSize')
        except Exception as exc:
            self.error = str(exc)
            self.ready.set()
            self.on_error(self.error)
        finally:
            if started:
                method(client, 11, HRESULT)(client)
            for ptr in (capture, client, operation):
                if ptr:
                    method(ptr, 2, W.ULONG)(ptr)
            ole.CoUninitialize()
