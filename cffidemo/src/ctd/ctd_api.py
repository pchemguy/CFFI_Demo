from __future__ import annotations

from _ctd_wrapper import ffi, lib


def c_string(pointer) -> str | None:
    return None if pointer == ffi.NULL else ffi.string(pointer).decode("utf-8")
