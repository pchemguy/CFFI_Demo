"""
enums.py
"""
from __future__ import annotations

from enum import IntEnum


__all__ = (
    "CtdStatus",
)


"""
```c
typedef enum ctd_status {
    CTD_OK = 0,
    CTD_ERROR_NULL = 1,
    CTD_ERROR_RANGE = 2,
    CTD_ERROR_CAPACITY = 3,
    CTD_ERROR_ALLOCATION = 4,
    CTD_ERROR_DIVIDE_BY_ZERO = 5
} ctd_status;
```
"""
class CtdStatus(IntEnum):
    OK                   = lib.CTD_OK
    ERROR_NULL           = lib.CTD_ERROR_NULL
    ERROR_RANGE          = lib.CTD_ERROR_RANGE
    ERROR_CAPACITY       = lib.CTD_ERROR_CAPACITY
    ERROR_ALLOCATION     = lib.CTD_ERROR_ALLOCATION
    ERROR_DIVIDE_BY_ZERO = lib.CTD_ERROR_DIVIDE_BY_ZERO
