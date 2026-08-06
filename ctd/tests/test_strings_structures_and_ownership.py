# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest


def copy_nullable_string(ffi, pointer) -> bytes | None:
    return None if pointer == ffi.NULL else ffi.string(pointer)


def unpack_i32(ffi, pointer, count: int) -> list[int]:
    return list(ffi.unpack(pointer, count))


def copy_descriptor(ffi, descriptor) -> tuple[bytes, list[int]]:
    return ffi.string(descriptor.message), unpack_i32(
        ffi, descriptor.values, descriptor.count
    )


@pytest.mark.parametrize(
    ("initial", "capacity", "status", "expected"),
    [
        pytest.param(b"mixed Case", 11, "CTD_OK", b"MIXED CASE", id="ascii-lowercase"),
        pytest.param(b"UPPER", 6, "CTD_OK", b"UPPER", id="already-uppercase"),
        pytest.param(b"123", 4, "CTD_OK", b"123", id="digits"),
        pytest.param(b"", 1, "CTD_OK", b"", id="empty"),
        pytest.param(
            b"lower", 5, "CTD_ERROR_CAPACITY", b"lower", id="unterminated-capacity"
        ),
    ],
)
def test_ascii_upper(
    ffi, lib, initial: bytes, capacity: int, status: str, expected: bytes
) -> None:
    storage = ffi.new("char[]", initial + b"\0")
    assert lib.ctd_ascii_upper(storage, capacity) == getattr(lib, status)
    assert bytes(ffi.buffer(storage, len(initial))) == expected


def test_copy_string_capacity_failure_does_not_write(ffi, lib) -> None:
    destination = ffi.new("char[]", b"XXXXXXXX")
    required = ffi.new("size_t *", 999)
    assert (
        lib.ctd_copy_string(b"hello", destination, 5, required)
        == lib.CTD_ERROR_CAPACITY
    )
    assert required[0] == 6
    assert bytes(ffi.buffer(destination, 8)) == b"XXXXXXXX"


@pytest.mark.parametrize(
    ("left", "right", "expected_sum", "expected_dot"),
    [
        pytest.param((2.0, 3.0), (4.0, 5.0), (6.0, 8.0), 23.0, id="ordinary"),
        pytest.param((-2.0, -3.0), (4.0, -5.0), (2.0, -8.0), 7.0, id="negative"),
        pytest.param((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), 0.0, id="zero"),
    ],
)
def test_point_operations(ffi, lib, left, right, expected_sum, expected_dot) -> None:
    a = lib.ctd_point_make(*left)
    b = lib.ctd_point_make(*right)
    combined = lib.ctd_point_add(a, b)
    assert combined.x == pytest.approx(expected_sum[0])
    assert combined.y == pytest.approx(expected_sum[1])
    assert lib.ctd_point_dot(ffi.addressof(a), ffi.addressof(b)) == pytest.approx(
        expected_dot
    )


@pytest.mark.parametrize(
    ("kind", "value", "expected_status", "expected"),
    [
        pytest.param("i64", -42, "CTD_OK", -42.0, id="valid-i64"),
        pytest.param("f64", 3.25, "CTD_OK", 3.25, id="valid-f64"),
        pytest.param("invalid", 0, "CTD_ERROR_RANGE", 123.5, id="invalid-discriminant"),
    ],
)
def test_tagged_union_discriminants(
    ffi, lib, kind, value, expected_status, expected
) -> None:
    if kind == "i64":
        tagged = lib.ctd_value_from_i64(value)
    elif kind == "f64":
        tagged = lib.ctd_value_from_f64(value)
    else:
        tagged = lib.ctd_value_from_i64(value)
        tagged.kind = 999
    result = ffi.new("double *", 123.5)
    assert lib.ctd_value_as_f64(ffi.addressof(tagged), result) == getattr(
        lib, expected_status
    )
    assert result[0] == pytest.approx(expected)


def test_descriptor_helper_copies_borrowed_nested_data(ffi, lib) -> None:
    assert copy_descriptor(ffi, lib.ctd_static_descriptor()) == (
        b"static Fibonacci descriptor",
        [8, 13, 21],
    )


def test_owned_greeting_uses_explicit_try_finally(ffi, lib) -> None:
    greeting = lib.ctd_alloc_greeting(b"Pytest")
    assert greeting != ffi.NULL
    try:
        assert copy_nullable_string(ffi, greeting) == b"Hello, Pytest!"
    finally:
        lib.ctd_free(greeting)


def test_allocated_sequence_fixture(ffi, allocated_sequence) -> None:
    values, count = allocated_sequence
    assert unpack_i32(ffi, values, count) == [-2, -1, 0, 1]


def test_counter_handle_fixture(ffi, lib, counter_handle) -> None:
    result = ffi.new("int *", -999)
    assert lib.ctd_counter_add(counter_handle, 5, result) == lib.CTD_OK
    assert result[0] == 15


def test_null_handle_failure_preserves_output(ffi, lib) -> None:
    result = ffi.new("int *", -999)
    assert lib.ctd_counter_get(ffi.NULL, result) == lib.CTD_ERROR_NULL
    assert result[0] == -999


@pytest.mark.parametrize(
    ("count", "is_null"),
    [pytest.param(0, True, id="zero-count"), pytest.param(1, False, id="one-element")],
)
def test_alloc_sequence_null_failure_behavior(
    ffi, lib, count: int, is_null: bool
) -> None:
    pointer = lib.ctd_alloc_sequence_i32(4, count)
    if is_null:
        assert pointer == ffi.NULL
    else:
        assert pointer != ffi.NULL
        lib.ctd_free(pointer)
