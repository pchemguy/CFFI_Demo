from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2]))

from enum import IntEnum

from _ctd_wrapper import ffi, lib
from contract import model, enums


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


def main() -> int:
    print(dir(enums))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
