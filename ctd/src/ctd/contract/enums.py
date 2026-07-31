"""
enums.py
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ctd._ctd_wrapper import ffi, lib


__all__ = (
    "CEnumSpec",
    "members",
)


@dataclass
class CEnumSpec:
    typedef_name: str
    members: dict[str, int]
    tagged_type_name: str | None = None
    ctype: ffi.CType = field(init=False)

    def __post_init__(self) -> None:
        if self.tagged_type_name is None:
            self.tagged_type_name = f"enum {self.typedef_name}"

        self.ctype = ffi.typeof(self.typedef_name)

    def verify(self) -> None:
        ctype: ffi.CType = self.ctype
        assert ctype is not None
        lib_members = {
            member_name: getattr(lib, member_name)
            for member_name in self.members
        }
        assert ctype.kind == "enum"
        assert ctype.cname == self.tagged_type_name
        assert ffi.typeof(self.tagged_type_name) is self.ctype
        assert ctype.relements == self.members
        assert lib_members == self.members
        print(f"Verified '{self.tagged_type_name}'")

    def print_info(self) -> None:
        ctype: ffi.CType = self.ctype
        print(
            f"ctype members:\n    {dir(ctype)}\n",
            f"Typedef name:     {ctype.kind}\n",
            f"Tagged enum type: {ctype.cname}\n",
            f"Enum members:\n     {ctype.relements}\n",
        )


ctd_status = CEnumSpec(
    typedef_name="ctd_status",
    members={
        "CTD_OK": 0,
        "CTD_ERROR_NULL": 1,
        "CTD_ERROR_RANGE": 2,
        "CTD_ERROR_CAPACITY": 3,
        "CTD_ERROR_ALLOCATION": 4,
        "CTD_ERROR_DIVIDE_BY_ZERO": 5,
    },
)


members: tuple[CEnumSpec, ...] = (
    ctd_status,
)
