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


def verify_enums() -> None:
    enums.CFFITarget.bind(ffi, lib)

    for member in enums.members:
        member.verify()
        member.print_info()


"""
```c
const char *ctd_version(void);
```
"""
def ctd_version() -> str:
    return c_string(lib.ctd_version())


def main() -> int:
    # verify_enums()
    #print(dir(ffi))
    
    #ctypes = ffi.list_types()
    #pretty_json = json.dumps(ctypes, indent=4)
    #print(pretty_json)

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
    
    #print(inspect.getmembers(definitions[0]["ctype"]))
    #print(definitions[2]["ctype"].fields)
    attr_names: list[str] = [member.value for member in cffi_model.CTypeAttributes if member.value != "name"]

    attrs = {name: getattr(ffi_ctypes[0]["ctype"], name, None) for name in attr_names}
    
    #pprint(ffi_ctypes)
    #print(attr_names)
    #print(attrs)
    #print(dir(ffi_ctypes[0]["ctype"].result))

    #args = ffi_ctypes[0]["ctype"].args
    #for arg in args:
    #    print(dir(arg))
    #print(dir(args[2].item))

    #field = ffi_ctypes[3]["ctype"].fields[1][1]

    print("\n\n-----------------------------------\n\n")

    #print(set(dir(lib)) - ctypes.enum_members)
    #print("\n\n-----------------------------------\n\n")

    #print(ctypes.enum_members)

    #for name in dir(lib):
    #    try:
    #        print(f"name: {name}. ctype: {ffi.typeof(getattr(lib, name))}.")
    #    except TypeError:
    #        print(f"name: {name}. ctype: {None}.")

    print(ctypes.lib_names)

    #for name in ctypes.lib_names:
    #    try:
    #        print(f"name: {name}. ctype: {ffi.typeof(getattr(lib, name))}.")
    #    except TypeError:
    #        print(f"name: {name}. ctype: {type(getattr(lib, name))}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
