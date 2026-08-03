from __future__ import annotations

import os
import sys
import json
from typing import Any
import inspect
from pprint import pprint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2]))

from ctd._ctd_wrapper import ffi, lib
from introspect import cffi_model, enums, database


def main() -> int:
    db: database.CFFIModelDB = database.CFFIModelDB(database=".")
    cffi_model.CFFITarget.bind(ffi, lib)
    ctypes: cffi_model.CFFICTypes = cffi_model.CFFICTypes()

    ffi_names: list[str]
    lib_names: list[str]
    ffi_ctypes: list[dict[str, Any]]
    lib_ctypes: list[dict[str, Any]] 
     
    ffi_names, lib_names, ffi_ctypes, lib_ctypes = ctypes.get_ctypes()

    ffi_ctypes_filtered: dict[str, Any] = [
        {prop: value for prop, value in desc.items() if prop != "ctype"}
        for desc in ffi_ctypes
    ]

    db.ctypes_insert(ffi_ctypes_filtered)

    lib_ctypes_filtered: dict[str, Any] = [
        {prop: value for prop, value in desc.items() if prop != "ctype"}
        for desc in lib_ctypes
    ]

    db.ctypes_insert(lib_ctypes_filtered)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
