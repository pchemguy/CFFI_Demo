"""
model.py
"""
from __future__ import annotations

from enum import StrEnum
from dataclasses import dataclass
from typing import TypeAlias, Any


__all__ = (
    "CTypeName",
    "CBuiltinType",
    "CEnumSpec",
    "CVariable",
    "CConstant",
    "CFieldSpec",
    "CStructSpec",
)


CTypeName: TypeAlias = CBuiltinType | str


class CBuiltinType(StrEnum):
    BOOL = "_Bool"

    CHAR = "char"
    SIGNED_CHAR = "signed char"
    UNSIGNED_CHAR = "unsigned char"

    SHORT = "short"
    UNSIGNED_SHORT = "unsigned short"

    INT = "int"
    UNSIGNED_INT = "unsigned int"

    LONG = "long"
    UNSIGNED_LONG = "unsigned long"

    LONG_LONG = "long long"
    UNSIGNED_LONG_LONG = "unsigned long long"

    FLOAT = "float"
    DOUBLE = "double"

    INT8 = "int8_t"
    UINT8 = "uint8_t"
    INT16 = "int16_t"
    UINT16 = "uint16_t"
    INT32 = "int32_t"
    UINT32 = "uint32_t"
    INT64 = "int64_t"
    UINT64 = "uint64_t"

    SIZE = "size_t"
    PTRDIFF = "ptrdiff_t"
    INTPTR = "intptr_t"
    UINTPTR = "uintptr_t"

    VOID_POINTER = "void *"
    CHAR_POINTER = "char *"
    CONST_CHAR_POINTER = "const char *"


@dataclass(frozen=True)
class CEnumSpec:
    typedef_name: str
    tag_name: str
    definition: type[IntEnum]


@dataclass(frozen=True)
class CVariable:
    name: str
    type: CTypeName


@dataclass(frozen=True)
class CConstant:
    name: str
    type: CTypeName
    value: Any


@dataclass(frozen=True)
class CFieldSpec:
    name: str
    type: CTypeName


@dataclass(frozen=True)
class CStructSpec:
    typedef_name: str
    tag_name: str
    fields: tuple[CFieldSpec, ...]
