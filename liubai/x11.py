"""Small EWMH bridge for KWin/X11, using the system libX11 directly."""

import ctypes as C
import ctypes.util
import os


class ClientMessage(C.Structure):
    _fields_ = [("type", C.c_int), ("serial", C.c_ulong), ("send_event", C.c_int),
                ("display", C.c_void_p), ("window", C.c_ulong),
                ("message_type", C.c_ulong), ("format", C.c_int), ("data", C.c_long * 5)]


class Event(C.Union):
    _fields_ = [("client", ClientMessage), ("pad", C.c_long * 24)]


def _message(window: int, name: str, values: list[int | str]) -> bool:
    if not os.environ.get("DISPLAY"):
        return False
    library = ctypes.util.find_library("X11")
    if not library:
        return False
    x = C.CDLL(library)
    x.XOpenDisplay.argtypes = [C.c_char_p]
    x.XOpenDisplay.restype = C.c_void_p
    x.XDefaultRootWindow.argtypes = [C.c_void_p]
    x.XDefaultRootWindow.restype = C.c_ulong
    x.XInternAtom.argtypes = [C.c_void_p, C.c_char_p, C.c_int]
    x.XInternAtom.restype = C.c_ulong
    x.XSendEvent.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_long, C.POINTER(Event)]
    x.XFlush.argtypes = [C.c_void_p]
    x.XCloseDisplay.argtypes = [C.c_void_p]
    display = x.XOpenDisplay(None)
    if not display:
        return False
    try:
        event = Event()
        event.client.type = 33  # ClientMessage
        event.client.send_event = 1
        event.client.display = display
        event.client.window = window
        event.client.message_type = x.XInternAtom(display, name.encode(), 0)
        event.client.format = 32
        for index, value in enumerate(values):
            event.client.data[index] = x.XInternAtom(display, value.encode(), 0) if isinstance(value, str) else value
        result = x.XSendEvent(display, x.XDefaultRootWindow(display), 0, (1 << 20) | (1 << 19), C.byref(event))
        x.XFlush(display)
        return bool(result)
    finally:
        x.XCloseDisplay(display)


def set_above(window: int, enabled: bool) -> bool:
    return _message(window, "_NET_WM_STATE", [int(enabled), "_NET_WM_STATE_ABOVE", 0, 1])


def set_desktop(window: int, all_desktops: bool, current: int = 0) -> bool:
    return _message(window, "_NET_WM_DESKTOP", [0xFFFFFFFF if all_desktops else current, 1])


def current_desktop() -> int:
    # Read only one numeric property; no shell interpolation.
    import subprocess
    try:
        result = subprocess.run(["xprop", "-root", "_NET_CURRENT_DESKTOP"], capture_output=True, text=True, timeout=2)
        return int(result.stdout.rsplit("=", 1)[-1].strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0
