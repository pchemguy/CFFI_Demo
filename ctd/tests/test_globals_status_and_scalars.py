# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("constant", "expected"),
    [
        pytest.param("CTD_OK", b"CTD_OK", id="ok"),
        pytest.param("CTD_ERROR_NULL", b"CTD_ERROR_NULL", id="null"),
        pytest.param("CTD_ERROR_RANGE", b"CTD_ERROR_RANGE", id="range"),
        pytest.param("CTD_ERROR_CAPACITY", b"CTD_ERROR_CAPACITY", id="capacity"),
        pytest.param("CTD_ERROR_ALLOCATION", b"CTD_ERROR_ALLOCATION", id="allocation"),
        pytest.param(
            "CTD_ERROR_DIVIDE_BY_ZERO",
            b"CTD_ERROR_DIVIDE_BY_ZERO",
            id="divide-by-zero",
        ),
        pytest.param(None, b"CTD_ERROR_UNKNOWN", id="unknown"),
    ],
)
def test_status_names(ffi, lib, constant: str | None, expected: bytes) -> None:
    status = 999 if constant is None else getattr(lib, constant)
    assert ffi.string(lib.ctd_status_name(status)) == expected


@pytest.mark.parametrize(
    ("operation", "arguments", "expected"),
    [
        pytest.param("ctd_add", (17, 25), 42, id="add-positive"),
        pytest.param("ctd_add", (-17, -25), -42, id="add-negative"),
        pytest.param("ctd_add", (0, 0), 0, id="add-zero"),
        pytest.param("ctd_add", (2**31 - 2, 1), 2**31 - 1, id="add-int-max-adjacent"),
        pytest.param(
            "ctd_add", (-(2**31) + 1, -1), -(2**31), id="add-int-min-adjacent"
        ),
        pytest.param("ctd_negate_i32", (-123,), 123, id="negate-negative"),
        pytest.param("ctd_negate_i32", (0,), 0, id="negate-zero"),
        pytest.param("ctd_negate_i32", (-(2**31),), 2**31 - 1, id="negate-int32-min"),
        pytest.param("ctd_add_u64", (2**64 - 2, 1), 2**64 - 1, id="u64-max-adjacent"),
        pytest.param("ctd_add_u64", (2**64 - 1, 1), 0, id="u64-wrap"),
    ],
)
def test_exact_scalar_operations(
    lib, operation: str, arguments: tuple[int, ...], expected: int
) -> None:
    assert getattr(lib, operation)(*arguments) == expected


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [(3.0, 4.0, 25.0), (-3.0, 4.0, 25.0), (0.0, 0.0, 0.0)],
    ids=["positive", "negative", "zero"],
)
def test_hypot_squared(lib, x: float, y: float, expected: float) -> None:
    assert lib.ctd_hypot_squared(x, y) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("numerator", "denominator", "status", "expected"),
    [
        pytest.param(22.0, 7.0, "CTD_OK", 22.0 / 7.0, id="successful"),
        pytest.param(1.0, 0.0, "CTD_ERROR_DIVIDE_BY_ZERO", 987.25, id="divide-by-zero"),
    ],
)
def test_divide_preserves_output_on_error(
    ffi, lib, numerator: float, denominator: float, status: str, expected: float
) -> None:
    result = ffi.new("double *", 987.25)
    assert lib.ctd_divide(numerator, denominator, result) == getattr(lib, status)
    assert result[0] == pytest.approx(expected)


@pytest.mark.parametrize("mode", ["direct-assignment", "library-mutation"])
def test_mutable_global_counter_is_isolated(lib, reset_globals, mode: str) -> None:
    assert lib.ctd_global_counter == 0
    if mode == "direct-assignment":
        lib.ctd_global_counter = 41
        assert lib.ctd_global_counter == 41
    else:
        assert lib.ctd_global_counter_increment() == 1
        assert lib.ctd_global_counter == 1
