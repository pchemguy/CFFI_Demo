from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


__all__ = (
    "CFFITarget",
    "CFFICTypes",
)


@dataclass(frozen=True)
class CFFITarget:
    """A CFFI API out-of-line target.
    
    Attributes:
        ffi: The ``FFI`` object exported by the out-of-line CFFI extension module.
        lib: The library interface object exported by the out-of-line CFFI extension
            module, providing access to declared C functions, variables, and constants.
    """
    ffi: Any
    lib: Any

    @classmethod
    def bind(cls, ffi: Any, lib: Any) -> CFFITarget:
        """Create and install the active CFFI target."""
        global cffi_target

        if cffi_target is None:
            cffi_target = cls(ffi=ffi, lib=lib)
        elif cffi_target.ffi is not ffi or cffi_target.lib is not lib:
            raise RuntimeError("A different CFFI target is already bound")

        return cffi_target


cffi_target: CFFITarget | None = None


class CTypeKinds(StrEnum):
    PRIMITIVE = "primitive"
    POINTER   = "pointer"
    ARRAY     = "array"
    FUNCTION  = "function"
    STRUCT    = "struct"
    UNION     = "union"
    ENUM      = "enum"


class CTypeGroups(StrEnum):
    TYPEDEF = "typedef_names"
    STRUCT  = "names_of_structs"
    UNION   = "names_of_unions"


class CTypeAttributes(StrEnum):
    NAME      = "name"
    CNAME     = "cname"
    KIND      = "kind"
    ITEM      = "item"
    LENGTH    = "length"
    FIELDS    = "fields"
    ARGS      = "args"
    RESULT    = "result"
    ELLIPSIS  = "ellipsis"
    ABI       = "abi"
    ELEMENTS  = "elements"
    RELEMENTS = "relements"


_attr_names: list[str] = [member.value for member in CTypeAttributes]


def _ctype2dict(ctype: ffi.CType) -> dict[str, Any]:
    if cffi_target is None:
        raise RuntimeError(
            "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
            "before creating CEnumSpec instances"
        )

    ffi = cffi_target.ffi

    ctype_dict: dict[str, Any] = {
        attr_name: getattr(ctype, attr_name, None)
        for attr_name in _attr_names if _attr_names != "name"
    }

    result: ffi.CType = getattr(ctype, "result", None)
    result_json: str | None = None if result is None else json.dumps({
        "cname": result.cname,
        "kind":  result.kind,
    }, indent=4)

    elements: dict[int, str] | None = getattr(ctype, "elements", None)
    elements_json: str | None = None if elements is None else json.dumps(
        elements, indent=4, sort_keys=True
    )
    
    relements: dict[int, str] | None = getattr(ctype, "relements", None)
    if relements:
        print(dict(sorted(relements.items(), key=lambda item: item[1])))
    relements_json: str | None = None if relements is None else json.dumps(
        dict(sorted(relements.items(), key=lambda item: item[1])),
        indent=4,
    )
    
    ctype_dict.update({
        "ctype":     ctype,
        "result":    result_json,
        "elements":  elements_json,
        "relements": relements_json,
    })

    return ctype_dict


def _ctypename2dict(name: str) -> dict[str, Any]:
    if cffi_target is None:
        raise RuntimeError(
            "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
            "before creating CEnumSpec instances"
        )

    return {"name": name} | _ctype2dict(cffi_target.ffi.typeof(name))


@dataclass
class CFFICTypes:
    ctype_names: list[str] | None =  field(init=False)
    ctypes: "list[dict[str, Any]]" = field(default_factory=list)

    def get_ctypes(self) -> None:
        if cffi_target is None:
            raise RuntimeError(
                "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
                "before creating CEnumSpec instances"
            )

        ffi = cffi_target.ffi
        lib = cffi_target.lib

        ctype_names: list[str] = sorted(set().union(*ffi.list_types()))
        self.ctype_names = ctype_names
       
        self.ctypes = [_ctypename2dict(ctype_name) for ctype_name in ctype_names]

        return ctype_names
