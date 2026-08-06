# ruff: noqa: ANN001, ANN201, I001
from __future__ import annotations

from tests.cffi_types import CffiValue

import sys
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest

CTD_SOURCE_ROOT = Path(__file__).parents[1] / "src"
CTD_MODULE_DIRECTORY = CTD_SOURCE_ROOT / "ctd"
sys.path[:0] = [str(CTD_SOURCE_ROOT), str(CTD_MODULE_DIRECTORY)]


@pytest.fixture(scope="session")
def wrapper_module() -> ModuleType:
    """Import whichever build mode produced the common wrapper module."""
    return import_module("_ctd_wrapper")


@pytest.fixture
def ffi(wrapper_module: CffiValue) -> CffiValue:
    """Return the generated wrapper's CFFI interface."""
    return wrapper_module.ffi


@pytest.fixture
def lib(wrapper_module: CffiValue) -> CffiValue:
    """Return the generated wrapper's CTD library interface."""
    return wrapper_module.lib


@pytest.fixture
def reset_globals(lib: CffiValue) -> Iterator[None]:
    """Expose mutable-global isolation explicitly to tests that need it."""
    lib.ctd_globals_reset()
    yield
    lib.ctd_globals_reset()


@pytest.fixture
def counter_handle(ffi: CffiValue, lib: CffiValue) -> Iterator[object]:
    """Provide one owned opaque counter and release it after the test."""
    handle = lib.ctd_counter_create(10)
    assert handle != ffi.NULL
    yield handle
    lib.ctd_free(handle)


@pytest.fixture
def allocated_sequence(ffi: CffiValue, lib: CffiValue) -> Iterator[tuple[object, int]]:
    """Provide a CTD-owned array to tests that do not exercise deallocation."""
    count = 4
    values = lib.ctd_alloc_sequence_i32(-2, count)
    assert values != ffi.NULL
    yield values, count
    lib.ctd_free(values)
