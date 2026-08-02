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
from contract import cffi_model, enums, database


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

    db: database.CFFIModelDB = database.CFFIModelDB()
    cffi_model.CFFITarget.bind(ffi, lib)
    ctypes: cffi_model.CFFICTypes = cffi_model.CFFICTypes()

    ctype_names: list[str] = ctypes.get_ctypes()
    definitions: list[dict[str, Any]] = ctypes.ctypes
    definitions_filtered: dict[str, Any] = [
        {prop: value for prop, value in desc.items() if prop != "ctype"}
        for desc in definitions
    ]

    print("\n==============\n", definitions_filtered, "\n--------------\n")
    # db.attributes_insert(definitions_filtered)
    print(inspect.getmembers(definitions[0]["ctype"]))
    print(definitions[2]["ctype"].fields)
    attr_names: list[str] = [member.value for member in cffi_model.CTypeAttributes if member.value != "name"]

    attrs = {name: getattr(definitions[0]["ctype"], name, None) for name in attr_names}
    
    pprint(definitions)
    print(attr_names)
    print(attrs)
    print(dir(definitions[0]["ctype"].result))

    args = definitions[0]["ctype"].args
    for arg in args:
        print(dir(arg))
    print(dir(args[2].item))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
