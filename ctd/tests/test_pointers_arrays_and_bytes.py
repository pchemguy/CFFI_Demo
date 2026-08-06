# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("pointer", "count", "expected_status", "expected"),
    [
        pytest.param("null", 0, "CTD_OK", 0, id="null-zero-count"),
        pytest.param("null", 1, "CTD_ERROR_NULL", 777, id="null-nonzero-count"),
        pytest.param("array", 3, "CTD_OK", 6, id="non-null-nonzero-count"),
    ],
)
def test_sum_nullable_pointer_contract(
    ffi, lib, pointer: str, count: int, expected_status: str, expected: int
) -> None:
    values = ffi.NULL if pointer == "null" else ffi.new("int32_t[]", [1, 2, 3])
    result = ffi.new("int64_t *", 777)
    assert lib.ctd_sum_i32(values, count, result) == getattr(lib, expected_status)
    assert result[0] == expected


@pytest.mark.parametrize(
    ("values", "factor", "expected"),
    [
        pytest.param([], 9, [], id="empty"),
        pytest.param([7], -2, [-14], id="singleton"),
        pytest.param([1, -2, 3], 3, [3, -6, 9], id="mixed"),
    ],
)
def test_scale_arrays(
    ffi, lib, values: list[int], factor: int, expected: list[int]
) -> None:
    array = ffi.NULL if not values else ffi.new("int32_t[]", values)
    assert lib.ctd_scale_i32(array, len(values), factor) == lib.CTD_OK
    assert ([] if array == ffi.NULL else list(array)) == expected


def test_scale_overflow_does_not_partially_modify_array(ffi, lib) -> None:
    values = ffi.new("int32_t[]", [3, 2**30])
    assert lib.ctd_scale_i32(values, 2, 2) == lib.CTD_ERROR_RANGE
    assert list(values) == [3, 2**30]


@pytest.mark.parametrize(
    ("capacity", "expected_status", "expected_buffer"),
    [
        pytest.param(3, "CTD_ERROR_CAPACITY", [777] * 5, id="below-required"),
        pytest.param(4, "CTD_OK", [10, 11, 12, 13, 777], id="equal-required"),
        pytest.param(5, "CTD_OK", [10, 11, 12, 13, 777], id="above-required"),
    ],
)
def test_sequence_capacity_is_all_or_nothing(
    ffi, lib, capacity: int, expected_status: str, expected_buffer: list[int]
) -> None:
    buffer = ffi.new("int32_t[]", [777] * 5)
    required = ffi.new("size_t *", 999)
    status = lib.ctd_make_sequence_i32(10, 4, buffer, capacity, required)
    assert status == getattr(lib, expected_status)
    assert required[0] == 4
    assert list(buffer) == expected_buffer


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        pytest.param(b"", 0, id="empty"),
        pytest.param(b"A\x00B", 131, id="embedded-nul"),
        pytest.param(b"\x00\xff\x01", 256, id="contains-ff"),
    ],
)
def test_byte_checksum(ffi, lib, payload: bytes, expected: int) -> None:
    data = ffi.NULL if not payload else ffi.new("uint8_t[]", payload)
    result = ffi.new("uint32_t *", 0xDEADBEEF)
    assert lib.ctd_checksum_bytes(data, len(payload), result) == lib.CTD_OK
    assert result[0] == expected


def test_copy_bytes_capacity_failure_does_not_write(ffi, lib) -> None:
    source = ffi.new("uint8_t[]", b"abcd")
    destination = ffi.new("uint8_t[]", b"XXXXX")
    required = ffi.new("size_t *", 999)
    assert (
        lib.ctd_copy_bytes(source, 4, destination, 3, required)
        == lib.CTD_ERROR_CAPACITY
    )
    assert required[0] == 4
    assert bytes(ffi.buffer(destination, 5)) == b"XXXXX"
