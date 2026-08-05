from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import _cffi_backend


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


class CFieldAttributes(StrEnum):
    BITSHIFT = "bitshift"
    BITSIZE  = "bitsize"
    FLAGS    = "flags"
    OFFSET   = "offset"
    TYPE     = "type"


_fattr_names: list[str] = [member.value for member in CFieldAttributes]


class CTypeAttributes(StrEnum):
    NAME      = "name"
    CATEGORY  = "category"
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


def _ctype2dict(ctype: "ffi.CType", seen: set = None) -> dict[str, Any]:
    if cffi_target is None:
        raise RuntimeError(
            "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
            "before creating CEnumSpec instances"
        )

    if seen is None:
        seen = set()

    if ctype in seen:
        return {
            "cname": ctype.cname,
            "kind":  ctype.kind,
            "recursive": True,
        }   
    
    ffi = cffi_target.ffi

    ctype_dict: dict[str, Any] = {}
    for attr_name in _attr_names:
        attr_value = getattr(ctype, attr_name, None)
        if not attr_value is None:
            ctype_dict[attr_name] = attr_value

    if isinstance(ctype_dict.get("item"), ffi.CType):
        ctype_dict["item"] = _ctype2dict(ctype_dict["item"], seen)

    if isinstance(ctype_dict.get("fields"), (tuple, list)):
        ctype_dict["fields"] = _process_field(ctype_dict["fields"], seen)

    if isinstance(ctype_dict.get("args"), (tuple, list)):
        ctype_dict["args"] = [_ctype2dict(arg, seen) for arg in ctype_dict["args"]]

    if isinstance(ctype_dict.get("result"), ffi.CType):
        ctype_dict["result"] = _ctype2dict(ctype_dict["result"], seen)

    return ctype_dict


def _process_field(fields: list | tuple, seen: set) -> list[dict[str, Any]]:
    fields_list: list[dict[str, Any]] = []
    for field in fields:
        field_name: str = field[0]
        field_value = field[1]
        field_dict: dict[str, Any] = {"name": field_name}

        if isinstance(field_value, _cffi_backend.CField):
            for fattr_name in _fattr_names:
                fattr_value = getattr(field_value, fattr_name, None)
                if fattr_value is None:
                    continue
        
                if isinstance(fattr_value, cffi_target.ffi.CType):
                    field_dict[fattr_name] = _ctype2dict(fattr_value, seen)
                else:
                    field_dict[fattr_name] = fattr_value
        else:
            field_dict["field_object"] = field_value

        fields_list.append(field_dict)
    
    return fields_list


def _ffiname2dict(name: str) -> dict[str, Any]:
    if cffi_target is None:
        raise RuntimeError(
            "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
            "before creating CEnumSpec instances"
        )

    ctype: "ffi.CTypes" = cffi_target.ffi.typeof(name)
    return {"name": name, "category": "ffi_typedef", "ctype": ctype} | _ctype2dict(ctype)


def _libname2dict(name: str) -> dict[str, Any]:
    if cffi_target is None:
        raise RuntimeError(
            "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
            "before creating CEnumSpec instances"
        )

    try:
        ctype: "ffi.CTypes" = cffi_target.ffi.typeof(getattr(cffi_target.lib, name))
    except TypeError:
        return {
            "name": name,
            "category": "instance",
            "ctype": None,
            "cname": f"NA - {str(type(getattr(cffi_target.lib, name)))}",
        }

    return {"name": name, "category": "lib_global", "ctype": ctype} | _ctype2dict(ctype)


@dataclass
class CFFICTypes:
    ffi_names: list[str] | None = field(init=False)
    lib_names: list[str] | None = field(init=False)
    ffi_ctypes: list[dict[str, Any]] = field(default_factory=list)
    lib_ctypes: list[dict[str, Any]] = field(default_factory=list)
    enum_members: set[str] = field(default_factory=set)

    def get_ctypes(self) -> None:
        if cffi_target is None:
            raise RuntimeError(
                "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
                "before creating CEnumSpec instances"
            )

        ffi = cffi_target.ffi
        lib = cffi_target.lib

        ffi_names: list[str] = sorted(set().union(*ffi.list_types()))
        self.ffi_names = ffi_names
        self.ffi_ctypes = [_ffiname2dict(ffi_name) for ffi_name in ffi_names]

        for ctype in self.ffi_ctypes:
            self.enum_members.update(ctype.get("relements") or {})

        lib_names: list[str] = list(set(dir(lib)) - set(self.enum_members))
        self.lib_names = lib_names
        self.lib_ctypes = [_libname2dict(lib_name) for lib_name in lib_names]

        return ffi_names, lib_names, self.ffi_ctypes, self.lib_ctypes
