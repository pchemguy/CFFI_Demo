"""
enums.py
"""
from __future__ import annotations

from enum import IntEnum


class CtdStatus(IntEnum):
    CTD_OK = 0
    CTD_ERROR_NULL = 1
    CTD_ERROR_RANGE = 2
    CTD_ERROR_CAPACITY = 3
    CTD_ERROR_ALLOCATION = 4
    CTD_ERROR_DIVIDE_BY_ZERO = 5
