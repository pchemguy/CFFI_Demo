"""Declarative verification of C enumeration contracts through CFFI.

This module defines the CFFI target binding and the expected enumeration
specifications used to validate an API-mode, out-of-line CFFI extension module.

Before any :class:`CEnumSpec` instance is created, the caller must bind the
generated extension module's ``ffi`` and ``lib`` objects by calling
:meth:`CFFITarget.bind`. The first successful binding becomes the active target.
Repeated binding with the same objects is permitted, while an attempt to bind a
different target raises :class:`RuntimeError`.

Each :class:`CEnumSpec` describes one expected C enumeration. Verification
checks that:

* the typedef resolves to an enumeration type;
* the resolved canonical type name matches the expected tagged enum type;
* the typedef and tagged type resolve to the same CFFI type object;
* the CFFI enumeration metadata contains exactly the expected enumerators and
  values; and
* the same enumerators are exported through the extension module's ``lib``
  interface with the expected values.

The module-level :data:`members` tuple contains the complete set of enumeration
specifications for the target contract.

Typical usage::

    from ctd._ctd_wrapper import ffi, lib
    from ctd.contract import enums

    enums.CFFITarget.bind(ffi, lib)

    for enum_spec in enums.members:
        enum_spec.verify()
        enum_spec.print_info() # For verbose output only.

The contract is intentionally bound at module level because every specification
in :data:`members` describes the same generated CFFI target.

See:
    CFFI documentation, "API Mode, calling the C standard library":
    https://cffi.readthedocs.io/en/latest/overview.html
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


__all__ = (
    "CFFITarget",
    "CEnumSpec",
    "members",
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


@dataclass
class CEnumSpec:
    typedef_name: str
    members: dict[str, int]
    tagged_type_name: str | None = None

    def __post_init__(self) -> None:
        if self.tagged_type_name is None:
            self.tagged_type_name = f"enum {self.typedef_name}"


    def verify(self) -> None:
        if cffi_target is None:
            raise RuntimeError(
                "CFFI target is not initialized; call CFFITarget.bind(ffi, lib) "
                "before creating CEnumSpec instances"
            )

        ffi = cffi_target.ffi
        lib = cffi_target.lib
        ctype: ffi.CType = cffi_target.ffi.typeof(self.typedef_name)

        lib_members = {
            member_name: getattr(lib, member_name)
            for member_name in self.members
        }

        assert ctype.kind == "enum"
        assert ctype.cname == self.tagged_type_name
        assert ffi.typeof(self.tagged_type_name) is ctype
        assert ctype.relements == self.members
        assert lib_members == self.members

        print(f"Verified '{self.tagged_type_name}'")

    def print_info(self) -> None:
        ctype = cffi_target.ffi.typeof(self.typedef_name)

        print(
            f"ctype members:\n    {dir(ctype)}\n",
            f"Type kind:        {ctype.kind}\n",
            f"Typedef name:     {self.typedef_name}\n",
            f"Tagged enum type: {ctype.cname}\n",
            f"Enum members:\n    {ctype.relements}\n",
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
