"""
enums.py
"""
from __future__ import annotations

from dataclasses import dataclass

from ctd._ctd_wrapper import ffi, lib


__all__ = (
    "CEnumSpec",
    "members",
)


@dataclass
class CEnumSpec:
    name: str
    members: dict[str, int]
    ctype: ffi.CType | None = None

    def __post_init__(self) -> None:
        self.ctype = ffi.typeof(self.name)

    def verify(self) -> None:
        ctype: ffi.CType = self.ctype
        assert ctype is not None
        lib_members = {
            member_name: getattr(lib, member_name)
            for member_name in self.members
        }
        assert ctype.kind == "enum"
        assert ctype.cname == f"enum {self.name}"
        assert self.members == ctype.relements
        assert self.members == lib_members

    def print_info(self) -> None:
        ctype: ffi.CType = self.ctype
        print(
            f"ctype members:\n    {dir(ctype)}\n",
            f"Typedef name:     {ctype.kind}\n",
            f"Tagged enum type: {ctype.cname}\n",
            f"Enum members:\n     {ctype.relements}\n",
        )


members: tuple[CEnumSpec, ...] = (
    "ctd_status",
)


ctd_status = CEnumSpec(
    name="ctd_status",
    members={
        "CTD_OK": 0,
        "CTD_ERROR_NULL": 1,
        "CTD_ERROR_RANGE": 2,
        "CTD_ERROR_CAPACITY": 3,
        "CTD_ERROR_ALLOCATION": 4,
        "CTD_ERROR_DIVIDE_BY_ZERO": 5,
    },
)




