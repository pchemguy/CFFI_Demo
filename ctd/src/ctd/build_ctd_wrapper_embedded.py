import platform
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

# True: link the wrapper against the target shared library.
# False: embed the target library in the wrapper and export
#        its symbols for diagnostic inspection.
DYNAMIC = False

if DYNAMIC:
    SOURCES = []
    LIBRARIES = [PROGRAM_NAME.lower()]
else:
    SOURCES = [PREFIX / f"{PROGRAM_NAME.lower()}.c"]
    LIBRARIES = []

C_MACROS = [
    (f"{PROGRAM_NAME.upper()}_TEST", None),
    (f"{PROGRAM_NAME.upper()}_{'USE' if DYNAMIC else 'BUILD'}_LIB", None),
]

EXTRA_COMPILE_ARGS = []
if platform.python_compiler().startswith("MSC"):
    EXTRA_COMPILE_ARGS = ["/TC", "/O2"]

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
    )

    ffibuilder.compile(tmpdir=str(PREFIX), verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
