import re
import subprocess
import sys
from types import ModuleType

import pytest
from cffi import FFI

from ctd import build_ctd_wrapper, build_ctd_wrapper_embedded

BUILDERS = [
    pytest.param(build_ctd_wrapper, id="dynamic-wrapper"),
    pytest.param(build_ctd_wrapper_embedded, id="embedded-wrapper"),
]


@pytest.mark.parametrize("builder", BUILDERS)
def test_builder_loads_complete_valid_cdef(builder: ModuleType) -> None:
    declarations = builder.load_cdef_header(builder.CDEF_HEADER)

    guard_directive = r"^\s*#\s*(?:ifndef|define|endif)\b"
    api_prefix = r"^\s*CTD_(?:DATA_)?API\b"
    assert not re.search(guard_directive, declarations, re.MULTILINE)
    assert not re.search(api_prefix, declarations, re.MULTILINE)

    representative_declarations = [
        "typedef enum ctd_status {",
        "typedef struct ctd_point {",
        "int ctd_global_counter;",
        "typedef int (*ctd_binary_callback)(int left, int right, void *user_data);",
        "typedef struct ctd_accumulator ctd_accumulator;",
        "int ctd_add(int a, int b);",
    ]
    for declaration in representative_declarations:
        assert declaration in declarations

    FFI().cdef(declarations)


def test_wrapper_builds_share_helper_and_produce_identical_cdef() -> None:
    assert (
        build_ctd_wrapper.load_cdef_header
        is build_ctd_wrapper_embedded.load_cdef_header
    )

    dynamic_declarations = build_ctd_wrapper.load_cdef_header(
        build_ctd_wrapper.CDEF_HEADER
    )
    embedded_declarations = build_ctd_wrapper_embedded.load_cdef_header(
        build_ctd_wrapper_embedded.CDEF_HEADER
    )

    assert dynamic_declarations == embedded_declarations


@pytest.mark.parametrize(
    "module_name",
    [
        pytest.param("build_ctd_wrapper", id="dynamic-wrapper"),
        pytest.param("build_ctd_wrapper_embedded", id="embedded-wrapper"),
    ],
)
def test_builder_imports_from_its_script_directory(module_name: str) -> None:
    builder_directory = build_ctd_wrapper.CDEF_HEADER.parent
    subprocess.run(
        [
            sys.executable,
            "-c",
            f"import {module_name}; assert callable({module_name}.load_cdef_header)",
        ],
        cwd=builder_directory,
        check=True,
    )
