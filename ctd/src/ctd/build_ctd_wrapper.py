from typing import Sequence
from pathlib import Path
import re
import platform

from cffi import FFI


PROGRAM_NAME = "CTD"
CDEF_HEADER = f"{PROGRAM_NAME.lower()}_api.h"
DYNAMIC = True

if DYNAMIC:
    SOURCES=[]
    LIBRARIES=[PROGRAM_NAME.lower()]
else:
    SOURCES=[f"{PROGRAM_NAME.lower()}.c"]
    LIBRARIES=[]

C_MACROS = [
    (f"{PROGRAM_NAME.upper()}_C_API", None),
    (f"{PROGRAM_NAME.upper()}_BUILD_{'EXE' if DYNAMIC else 'LIB'}", None),
]

EXTRA_COMPILE_ARGS = []
if platform.python_compiler().startswith("MSC"):
    EXTRA_COMPILE_ARGS = ["/TC", "/O2"]

WRAPPER_NAME = f"_{PROGRAM_NAME.lower()}_wrapper"

C_SNIPPET = f"""
    #include "{PROGRAM_NAME.lower()}.h"
"""


def load_cdef_header(path: str | Path) -> str:
    header_path = Path(path)
    declarations = header_path.read_text(encoding="utf-8")

    guard = re.sub(r"[^A-Za-z0-9]", "_", header_path.name).upper()
    escaped_guard = re.escape(guard)

    declarations = re.sub(
        rf"^[ \t]*#[ \t]*ifndef[ \t]+{escaped_guard}[ \t]*(?:\r?\n|$)",
        "",
        declarations,
        flags=re.MULTILINE,
    )

    declarations = re.sub(
        rf"^[ \t]*#[ \t]*define[ \t]+{escaped_guard}[ \t]*(?:\r?\n|$)",
        "",
        declarations,
        flags=re.MULTILINE,
    )

    declarations = re.sub(
        rf"^[ \t]*#[ \t]*endif"
        rf"(?:[ \t]*/\*[ \t]*{escaped_guard}[ \t]*\*/)?"
        rf"[ \t]*(?:\r?\n|$)",
        "",
        declarations,
        flags=re.MULTILINE,
    )

    declarations = re.sub(
        r"^[A-Z][A-Z0-9_]*_API[ \t]+",
        "",
        declarations,
        flags=re.MULTILINE,
    )

    return declarations


def main(argv: Sequence[str] | None = None) -> int:
    ffibuilder = FFI()
    declarations = load_cdef_header(CDEF_HEADER)
    ffibuilder.cdef(declarations)

    ffibuilder.set_source(
        WRAPPER_NAME,
        C_SNIPPET,
        sources=SOURCES,
        include_dirs=[".", "include",],
        libraries=LIBRARIES,
        library_dirs=[".", "lib",],
        define_macros=C_MACROS,
        extra_compile_args=EXTRA_COMPILE_ARGS,
    )

    ffibuilder.compile(verbose=True)


if __name__ == "__main__":
    raise SystemExit(main())
