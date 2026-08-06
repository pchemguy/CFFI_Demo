# ruff: noqa: ANN001, ANN201, I001
from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

CTD_SOURCE = Path(__file__).parents[1] / "src" / "ctd"
sys.path.insert(0, str(CTD_SOURCE))

from _ctd_wrapper import ffi as wrapper_ffi  # noqa: E402
from _ctd_wrapper import lib as wrapper_lib  # noqa: E402


@pytest.fixture
def ffi():
    """Return the generated wrapper's CFFI interface."""
    return wrapper_ffi


@pytest.fixture
def lib():
    """Return the generated wrapper's CTD library interface."""
    return wrapper_lib


@pytest.fixture
def reset_globals(lib) -> Iterator[None]:
    """Expose mutable-global isolation explicitly to tests that need it."""
    lib.ctd_globals_reset()
    yield
    lib.ctd_globals_reset()


@pytest.fixture
def counter_handle(ffi, lib) -> Iterator[object]:
    """Provide one owned opaque counter and release it after the test."""
    handle = lib.ctd_counter_create(10)
    assert handle != ffi.NULL
    yield handle
    lib.ctd_free(handle)


@pytest.fixture
def allocated_sequence(ffi, lib) -> Iterator[tuple[object, int]]:
    """Provide a CTD-owned array to tests that do not exercise deallocation."""
    count = 4
    values = lib.ctd_alloc_sequence_i32(-2, count)
    assert values != ffi.NULL
    yield values, count
    lib.ctd_free(values)
