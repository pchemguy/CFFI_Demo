import platform
import sys
from importlib import import_module
from pathlib import Path

from cffi import FFI

_cdef_header = (
    import_module(".cdef_header", __package__)
    if __package__
    else import_module("cdef_header")
)
load_cdef_header = _cdef_header.load_cdef_header


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
    (f"{PROGRAM_NAME.upper()}_{'USE_LIB' if DYNAMIC else 'BUILD_LIB'}", None),
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
