import re

from cffi import FFI

from ctd import build_ctd_wrapper, build_ctd_wrapper_embedded


def test_wrapper_builds_load_the_same_valid_cdef() -> None:
    header = build_ctd_wrapper.CDEF_HEADER

    dynamic_declarations = build_ctd_wrapper.load_cdef_header(header)
    embedded_declarations = build_ctd_wrapper_embedded.load_cdef_header(header)

    assert dynamic_declarations == embedded_declarations
    guard_directive = r"^\s*#\s*(?:ifndef|define|endif)\b"
    api_prefix = r"^CTD_(?:DATA_)?API\b"
    assert not re.search(guard_directive, dynamic_declarations, re.MULTILINE)
    assert not re.search(api_prefix, dynamic_declarations, re.MULTILINE)

    FFI().cdef(dynamic_declarations)
