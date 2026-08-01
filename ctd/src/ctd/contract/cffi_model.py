from __future__ import annotations

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
    GROUP     = "group"
    ITEM      = "item"
    LENGTH    = "length"
    FIELDS    = "fields"
    ARGS      = "args"
    RESULT    = "result"
    ELLIPSIS  = "ellipsis"
    ABI       = "abi"
    ELEMENTS  = "elements"
    RELEMENTS = "relements"


@dataclass
class CFFICTypes:
    typedef_names: list[str] | None =  field(init=False)
    struct_names:  list[str] | None =  field(init=False)
    union_names:   list[str] | None =  field(init=False)
    typedefs: "dict[str, dict[str, Any]]" = field(default_factory=dict)
    structs:  "dict[str, dict[str, Any]]" = field(default_factory=dict)
    unions:   "dict[str, dict[str, Any]]" = field(default_factory=dict)

    def get_ctypes(self) -> None:
        if cffi_target is None:
            raise RuntimeError(
                "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
                "before creating CEnumSpec instances"
            )

        ffi = cffi_target.ffi
        lib = cffi_target.lib

        ctypes: list[list[str]] = ffi.list_types()
        self.typedef_names, self.struct_names, self.union_names = ctypes

        ctype: ffi.CType

        for name in self.typedef_names:
            ctype = ffi.typeof(name)
            self.typedefs[name] = {
                "ctype": ctype,
                "cname": ctype.cname,
                "kind":  ctype.kind,
            }

        for name in self.struct_names:
            ctype = ffi.typeof(f"struct {name}")
            self.structs[name] = {
                "ctype": ctype,
                "cname": ctype.cname,
                "kind":  ctype.kind,
            }

        for name in self.union_names:
            ctype = ffi.typeof(f"union {name}")
            self.unions[name] = {
                "ctype": ctype,
                "cname": ctype.cname,
                "kind":  ctype.kind,
            }
        
        return ctypes


