import ctypes as C
from ctypes import wintypes as W
import sys
pid = int(sys.argv[1])
user = C.windll.user32
user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

def child(hwnd, value):
    buf = C.create_unicode_buffer(12000)
    user.GetWindowTextW(hwnd, buf, len(buf))
    if buf.value:
        print(buf.value)
    return True

child_cb = callback_type(child)

def parent(hwnd, value):
    found = W.DWORD()
    user.GetWindowThreadProcessId(hwnd, C.byref(found))
    if found.value == pid:
        child(hwnd, value)
        user.EnumChildWindows(hwnd, child_cb, 0)
    return True

user.EnumWindows(callback_type(parent), 0)
