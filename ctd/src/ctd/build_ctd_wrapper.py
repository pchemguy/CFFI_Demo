import platform
import re
import sys
from pathlib import Path

from cffi import FFI

PROGRAM_NAME = "CTD"
PREFIX = Path(__file__).resolve().parent

CDEF_HEADER = PREFIX / f"{PROGRAM_NAME.lower()}_api.h"
DYNAMIC = True

if DYNAMIC:
    SOURCES = []
    LIBRARIES = [PROGRAM_NAME.lower()]
else:
    SOURCES = [PREFIX / f"{PROGRAM_NAME.lower()}.c"]
    LIBRARIES = []

C_MACROS = [
    (f"{PROGRAM_NAME.upper()}_C_API", None),
    (f"{PROGRAM_NAME.upper()}_BUILD_{'EXE' if DYNAMIC else 'LIB'}", None),
]

EXTRA_COMPILE_ARGS = []
EXTRA_LINK_ARGS = []
if platform.python_compiler().startswith("MSC"):
    EXTRA_COMPILE_ARGS = ["/TC", "/O2"]
elif sys.platform == "darwin":
    EXTRA_LINK_ARGS = ["-Wl,-rpath,@loader_path"]
elif sys.platform != "win32":
    EXTRA_LINK_ARGS = ["-Wl,-rpath,$ORIGIN"]

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
        r"^CTD_DATA_API[ \t]+",
        "extern ",
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


def main() -> int:
    ffibuilder = FFI()
    declarations = load_cdef_header(CDEF_HEADER)
    ffibuilder.cdef(declarations)

    ffibuilder.set_source(
        WRAPPER_NAME,
        C_SNIPPET,
        sources=[str(source) for source in SOURCES],
        include_dirs=[str(PREFIX), str(PREFIX / "include")],
        libraries=LIBRARIES,
        library_dirs=[str(PREFIX), str(PREFIX / "lib")],
        define_macros=C_MACROS,
        extra_compile_args=EXTRA_COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
    )

    ffibuilder.compile(tmpdir=str(PREFIX), verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
