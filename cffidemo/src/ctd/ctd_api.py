from __future__ import annotations

from enum import IntEnum

from _ctd_wrapper import ffi, lib


"""
```c
typedef enum ctd_status {
    CTD_OK = 0,
    CTD_ERROR_NULL = 1,
    CTD_ERROR_RANGE = 2,
    CTD_ERROR_CAPACITY = 3,
    CTD_ERROR_ALLOCATION = 4,
    CTD_ERROR_DIVIDE_BY_ZERO = 5
} ctd_status;
```
"""
class CtdStatus(IntEnum):
    OK                   = lib.CTD_OK
    ERROR_NULL           = lib.CTD_ERROR_NULL
    ERROR_RANGE          = lib.CTD_ERROR_RANGE
    ERROR_CAPACITY       = lib.CTD_ERROR_CAPACITY
    ERROR_ALLOCATION     = lib.CTD_ERROR_ALLOCATION
    ERROR_DIVIDE_BY_ZERO = lib.CTD_ERROR_DIVIDE_BY_ZERO


# From C "char *" to Python str
def c_string(pointer: ffi.CData) -> str | None:
    return None if pointer == ffi.NULL else ffi.string(pointer).decode("utf-8")


# From Python str to C "char *"
def to_c_string(text: str | None) -> ffi.CData:
    return ffi.NULL if text is None else ffi.new("char *", text.encode("utf-8"))


def heading(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def status_name(status: CtdStatus) -> str:
    return c_string(lib.ctd_status_name(status)) or "<null>"


def show_status(label: str, status: CtdStatus) -> None:
    print(f"{label}: {status_name(status)} ({status})")


def point_tuple(point: ffi.CData) -> tuple[float, float]:
    return point.x, point.y


"""
```c
const char *ctd_version(void);
```
"""
def ctd_version() -> str:
    return c_string(lib.ctd_version())

